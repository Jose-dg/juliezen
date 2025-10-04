import logging
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.alegra.models import AlegraCredential
from apps.integrations.exceptions import AlegraAPIError, AlegraCredentialError
from apps.integrations.models import IntegrationMessage
from apps.integrations.services.alegra_client import AlegraClient

logger = logging.getLogger(__name__)


@dataclass
class ContactData:
    id: str
    raw: Dict[str, Any]


def process_erpnext_pos_invoice(message: IntegrationMessage) -> Dict[str, Any]:
    """Process an ERPNext POS Invoice payload and create the invoice in Alegra."""

    payload = message.payload or {}
    organization_id = message.organization_id

    credential = _get_active_credential(organization_id)
    client = AlegraClient(organization_id, credential=credential)

    contact = _ensure_contact(client, payload, credential)
    invoice_payload = _build_invoice_payload(payload, contact.id, credential)

    external_reference = payload.get("name") or payload.get("external_reference") or str(message.id)
    response = client.request(
        "POST",
        "/invoices",
        json=invoice_payload,
        event_type="erpnext.pos_invoice.create",
        external_reference=external_reference,
    )

    logger.info(
        "[ALEGRA][INVOICE][%s] Created invoice external_reference=%s response_id=%s",
        organization_id,
        external_reference,
        response.get("id") if isinstance(response, dict) else None,
    )

    return {
        "invoice_payload": invoice_payload,
        "invoice_response": response,
    }


def _get_active_credential(organization_id: UUID) -> AlegraCredential:
    credential = (
        AlegraCredential.objects.active()
        .filter(organization_id=organization_id)
        .order_by("-updated_at")
        .first()
    )
    if not credential:
        raise AlegraCredentialError("No hay credenciales activas de Alegra para la organización")
    return credential


def _ensure_contact(
    client: AlegraClient,
    payload: Dict[str, Any],
    credential: AlegraCredential,
) -> ContactData:
    """Ensure the customer associated with the invoice exists in Alegra."""

    raw_customer = payload.get("customer")
    if isinstance(raw_customer, dict):
        customer_data = raw_customer
    else:
        customer_data = {
            "code": raw_customer,
            "name": payload.get("customer_name"),
            "custom_alegra_id": payload.get("customer_custom_alegra_id"),
            "identification_type": payload.get("customer_identification_type"),
            "identification": payload.get("customer_identification"),
            "email": payload.get("contact_email"),
            "phone": payload.get("customer_phone"),
        }

    customer_code = _normalize_str(customer_data.get("code")) or _normalize_str(payload.get("customer_code"))
    customer_name = _normalize_str(customer_data.get("name")) or _normalize_str(payload.get("customer_name")) or "Cliente"
    alegra_id = _normalize_str(customer_data.get("custom_alegra_id"))
    identification_type = _normalize_str(customer_data.get("identification_type"))
    identification = _normalize_str(customer_data.get("identification"))
    email = _normalize_str(customer_data.get("email")) or _normalize_str(payload.get("contact_email"))
    phone = _normalize_str(customer_data.get("phone"))

    contact = _find_contact(client, alegra_id, customer_code, customer_name, email, identification)
    if contact:
        _maybe_update_contact(client, contact, customer_name, email, phone)
        return ContactData(id=str(contact["id"]), raw=contact)

    create_payload = _build_contact_payload(
        customer_name,
        customer_code,
        email,
        phone,
        identification_type,
        identification,
        customer_data.get("address") or {},
        credential,
    )
    try:
        created_contact = client.request(
            "POST",
            "/contacts",
            json=create_payload,
            event_type="erpnext.contact.create",
            external_reference=customer_code or customer_name,
        )
        contact_id = created_contact.get("id")
        if not contact_id:
            raise AlegraAPIError("Alegra no devolvió un ID de contacto al crearlo")
        return ContactData(id=str(contact_id), raw=created_contact)
    except AlegraAPIError as exc:
        logger.warning("[ALEGRA] Contact creation failed: %s", exc)
        fallback_contact = _find_contact(client, alegra_id, customer_code, customer_name, email, identification)
        if fallback_contact:
            logger.info("[ALEGRA] Using existing contact after creation failure: %s", fallback_contact.get("id"))
            return ContactData(id=str(fallback_contact.get("id")), raw=fallback_contact)
        raise


def _build_contact_payload(
    customer_name: str,
    customer_code: str | None,
    email: str | None,
    phone: str | None,
    identification_type: str | None,
    identification: str | None,
    address: Dict[str, Any],
    credential: AlegraCredential,
) -> Dict[str, Any]:
    metadata = credential.metadata or {}
    first_name, last_name = _split_name(customer_name)
    identification_number = _normalize_str(identification) or _normalize_str(customer_code) or ""
    if not identification_number:
        identification_number = f"AUTO-{first_name.upper()}"

    identification_kind = identification_type or metadata.get("default_identification_type", "CC")
    numeric_types = {"CC", "NIT", "TI", "CE"}
    if identification_kind and identification_kind.upper() in numeric_types:
        identification_number = _only_digits(identification_number)
        if not identification_number:
            # Cambiamos a un tipo genérico que permite letras
            identification_kind = metadata.get("generic_identification_type", "OTHER")
            identification_number = customer_code or "AUTO-ID"
    if not identification_kind:
        identification_kind = metadata.get("default_identification_type", "CC")

    payload: Dict[str, Any] = {
        "nameObject": {
            "firstName": first_name,
            "lastName": last_name,
            "secondLastName": "",
        },
        "identificationObject": {
            "type": identification_kind,
            "number": identification_number,
        },
        "kindOfPerson": metadata.get("default_kind_of_person", "PERSON_ENTITY"),
        "regime": metadata.get("default_regime", "SIMPLIFIED_REGIME"),
        "type": "client",
    }
    if email:
        payload["email"] = email
        payload["emailSecondary"] = email
    if phone:
        payload["mobile"] = phone
        payload["phonePrimary"] = phone

    address_payload = _build_address_payload(address)
    if address_payload:
        payload["address"] = address_payload

    return payload


def _maybe_update_contact(
    client: AlegraClient,
    contact: Dict[str, Any],
    customer_name: str,
    email: str | None,
    phone: str | None,
) -> None:
    needs_update = False
    updates: Dict[str, Any] = {}

    name_object = contact.get("nameObject") or {}
    current_full_name = " ".join(filter(None, [name_object.get("firstName"), name_object.get("lastName")]))
    if customer_name.strip() and customer_name.strip() != current_full_name.strip():
        first_name, last_name = _split_name(customer_name)
        updates["nameObject"] = {
            "firstName": first_name,
            "lastName": last_name,
            "secondLastName": name_object.get("secondLastName", ""),
        }
        needs_update = True

    if email and contact.get("email") != email:
        updates["email"] = email
        updates["emailSecondary"] = email
        needs_update = True

    if phone and contact.get("mobile") != phone:
        updates["mobile"] = phone
        updates["phonePrimary"] = phone
        needs_update = True

    if not needs_update:
        return

    try:
        client.request(
            "PUT",
            f"/contacts/{contact.get('id')}",
            json=updates,
            event_type="erpnext.contact.update",
            external_reference=str(contact.get("id")),
        )
    except AlegraAPIError as exc:
        logger.warning("[ALEGRA] Unable to update contact %s: %s", contact.get("id"), exc)


def _find_contact(
    client: AlegraClient,
    alegra_id: str | None,
    customer_code: str | None,
    customer_name: str | None,
    email: str | None,
    identification: str | None,
) -> Dict[str, Any] | None:
    identifiers = [identification, customer_code]
    if alegra_id:
        try:
            contact = client.request(
                "GET",
                f"/contacts/{alegra_id}",
                event_type="erpnext.contact.fetch",
                external_reference=customer_code or alegra_id,
            )
            if contact and contact.get("id"):
                return contact
        except AlegraAPIError as exc:
            logger.warning("[ALEGRA] Fetch contact by custom_alegra_id failed: %s", exc)

    finder_term = email or customer_code or customer_name
    if not finder_term:
        return None

    try:
        matches = client.request(
            "GET",
            "/contacts",
            params={"term": finder_term},
            event_type="erpnext.contact.lookup",
            external_reference=customer_code or customer_name,
        )
    except AlegraAPIError as exc:
        logger.warning("[ALEGRA] Contact lookup failed: %s", exc)
        return None

    normalized_identifiers = {(_normalize_str(value) or "").strip() for value in identifiers if value}
    normalized_identifiers.add((_normalize_str(email) or "").strip())

    for contact in _as_list(matches):
        if alegra_id and str(contact.get("id")) == alegra_id:
            return contact
        identification_object = contact.get("identificationObject", {})
        number = (_normalize_str(identification_object.get("number")) or "").strip()
        if number and number in normalized_identifiers:
            return contact
        if email and contact.get("email") == email:
            return contact

    return None


def _build_address_payload(address: Dict[str, Any]) -> Dict[str, Any]:
    if not address:
        return {}
    return {
        "address": address.get("line1") or address.get("name") or "",
        "city": address.get("city") or "",
        "department": address.get("state") or "",
        "country": address.get("country") or "",
        "zipCode": address.get("postal_code") or "",
    }


def _build_invoice_payload(
    payload: Dict[str, Any],
    contact_id: str,
    credential: AlegraCredential,
) -> Dict[str, Any]:
    metadata = credential.metadata or {}
    posting_date = payload.get("posting_date") or payload.get("date")
    due_date = payload.get("due_date") or posting_date
    grand_total = payload.get("grand_total") or payload.get("total")
    if grand_total is None:
        raise ValidationError("El payload de ERPNext no incluye 'grand_total'")

    item_map = metadata.get("item_map", {})
    items: List[Dict[str, Any]] = []
    for item in _as_list(payload.get("items")):
        item_code = _normalize_str(item.get("item_code"))
        alegra_item_id = item.get("alegra_id") or item_map.get(item_code or "")
        line: Dict[str, Any] = {
            "name": item.get("item_name") or item.get("description") or item_code or "",
            "description": item.get("description") or "",
            "code": item_code or "",
            "reference": item_code or "",
            "quantity": float(item.get("qty") or 1),
            "price": float(item.get("rate") or item.get("amount") or 0),
            "discount": float(item.get("discount") or 0),
        }
        if alegra_item_id:
            line["item"] = {"id": _maybe_int(alegra_item_id)}
        items.append(line)

    taxes: List[Dict[str, Any]] = []
    for tax in _as_list(payload.get("taxes")):
        taxes.append(
            {
                "name": tax.get("account_head") or "Impuesto",
                "percentage": float(tax.get("rate") or 0),
                "amount": float(tax.get("tax_amount") or 0),
            }
        )

    if not posting_date:
        posting_date = timezone.now().date().isoformat()

    total_amount = float(grand_total)

    invoice_payload: Dict[str, Any] = {
        "client": {"id": contact_id},
        "date": posting_date,
        "dueDate": due_date,
        "items": items,
        "stamp": {"generateStamp": credential.auto_stamp_on_create},
        "paymentForm": metadata.get("default_payment_form", "CASH"),
        "type": metadata.get("default_invoice_type", "NATIONAL"),
        "operationType": metadata.get("default_operation_type", "STANDARD"),
        "status": metadata.get("default_invoice_status", "open"),
    }

    payments = _build_payments(payload.get("payments") or [], metadata, total_amount, due_date)
    invoice_payload["payments"] = payments

    if payments:
        invoice_payload["paymentMethod"] = payments[0].get("paymentMethod", metadata.get("default_payment_method_key", "CASH"))
    else:
        invoice_payload["paymentMethod"] = metadata.get("default_payment_method_key", "CASH")

    number_template_id = credential.number_template_id or metadata.get("number_template_id")
    if number_template_id:
        invoice_payload["numberTemplate"] = {"id": number_template_id}

    number_template_prefix = metadata.get("number_template_prefix")
    number_template_number = metadata.get("number_template_next")
    if number_template_prefix or number_template_number:
        invoice_payload.setdefault("numberTemplate", {})
        if number_template_prefix:
            invoice_payload["numberTemplate"]["prefix"] = number_template_prefix
        if number_template_number:
            invoice_payload["numberTemplate"]["number"] = number_template_number

    if payload.get("remarks"):
        invoice_payload["observations"] = str(payload.get("remarks"))[:500]

    naming_series = payload.get("naming_series") or payload.get("name")
    if naming_series:
        invoice_payload.setdefault("internalId", str(naming_series))

    is_pos_flag = payload.get("is_pos")
    if isinstance(is_pos_flag, str):
        is_pos_flag = is_pos_flag.lower() in {"1", "true", "yes"}
    invoice_payload["pointOfSale"] = bool(is_pos_flag)

    if taxes:
        invoice_payload["taxTotals"] = taxes

    return invoice_payload


def _build_payments(
    payments_payload: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    total_amount: float,
    due_date: str | None,
) -> List[Dict[str, Any]]:
    if not due_date:
        due_date = timezone.now().date().isoformat()

    account_map = metadata.get("payment_account_map", {})
    method_map = metadata.get("payment_method_map", {})
    default_account_id = str(metadata.get("default_payment_account_id", "1"))
    default_method_key = metadata.get("default_payment_method", "transfer")
    default_method_tag = metadata.get("default_payment_method_key", "CASH")

    payments: List[Dict[str, Any]] = []
    if payments_payload:
        for payment in payments_payload:
            mode = _normalize_str(payment.get("mode_of_payment")) or "DEFAULT"
            amount = float(payment.get("amount") or 0)
            if not amount:
                continue
            account_id = str(account_map.get(mode, default_account_id))
            payment_method_tag = method_map.get(mode, default_method_tag)
            payment_method = method_map.get(mode, default_method_key)
            payments.append(
                {
                    "account": {"id": account_id},
                    "date": due_date,
                    "amount": amount,
                    "paymentMethod": payment_method or default_method_key,
                }
            )
        if payments:
            return payments

    # fallback single payment covering full total
    return [
        {
            "account": {"id": default_account_id},
            "date": due_date,
            "amount": total_amount,
            "paymentMethod": default_method_key,
        }
    ]


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return "Cliente", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _maybe_int(value: Any) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _as_list(value: Any) -> List[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]
