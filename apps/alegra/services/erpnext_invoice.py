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

    customer_code = payload.get("customer") or payload.get("customer_code")
    customer_name = payload.get("customer_name") or payload.get("customer") or "Cliente"
    email = (payload.get("contact_email") or payload.get("email") or None) or None
    if email == "":
        email = None

    finder_term = email or customer_code or customer_name
    if finder_term:
        try:
            matches = client.request(
                "GET",
                "/contacts",
                params={"term": finder_term},
                event_type="erpnext.contact.lookup",
                external_reference=customer_code or customer_name,
            )
            for contact in _as_list(matches):
                identification = contact.get("identificationObject", {})
                if customer_code and identification.get("number") == customer_code:
                    return ContactData(id=str(contact.get("id")), raw=contact)
                if email and contact.get("email") == email:
                    return ContactData(id=str(contact.get("id")), raw=contact)
        except AlegraAPIError as exc:
            logger.warning("[ALEGRA] Contact lookup failed: %s", exc)

    create_payload = _build_contact_payload(customer_name, customer_code, email, credential)
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


def _build_contact_payload(
    customer_name: str,
    customer_code: str | None,
    email: str | None,
    credential: AlegraCredential,
) -> Dict[str, Any]:
    metadata = credential.metadata or {}
    first_name, last_name = _split_name(customer_name)
    identification_number = customer_code or f"AUTO-{first_name.upper()}"

    payload: Dict[str, Any] = {
        "nameObject": {
            "firstName": first_name,
            "lastName": last_name,
            "secondLastName": "",
        },
        "identificationObject": {
            "type": metadata.get("default_identification_type", "CC"),
            "number": identification_number,
        },
        "kindOfPerson": metadata.get("default_kind_of_person", "PERSON_ENTITY"),
        "regime": metadata.get("default_regime", "SIMPLIFIED_REGIME"),
        "type": "client",
    }
    if email:
        payload["email"] = email
        payload["emailSecondary"] = email

    return payload


def _build_invoice_payload(
    payload: Dict[str, Any],
    contact_id: str,
    credential: AlegraCredential,
) -> Dict[str, Any]:
    metadata = credential.metadata or {}
    posting_date = payload.get("posting_date") or payload.get("date")
    grand_total = payload.get("grand_total") or payload.get("total")
    if grand_total is None:
        raise ValidationError("El payload de ERPNext no incluye 'grand_total'")

    items: List[Dict[str, Any]] = []
    for item in _as_list(payload.get("items")):
        items.append(
            {
                "name": item.get("item_name") or item.get("description") or item.get("item_code"),
                "description": item.get("description") or "",
                "code": item.get("item_code") or "",
                "reference": item.get("item_code") or "",
                "quantity": float(item.get("qty") or 1),
                "price": float(item.get("rate") or item.get("amount") or 0),
                "discount": float(item.get("discount") or 0),
            }
        )

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
        "dueDate": posting_date,
        "items": items,
        "payments": [
            {
                "account": {"id": str(metadata.get("default_payment_account_id", "1"))},
                "date": posting_date,
                "amount": total_amount,
                "paymentMethod": metadata.get("default_payment_method", "transfer"),
            }
        ],
        "stamp": {"generateStamp": credential.auto_stamp_on_create},
        "paymentForm": metadata.get("default_payment_form", "CASH"),
        "paymentMethod": metadata.get("default_payment_method_key", "CASH"),
        "type": metadata.get("default_invoice_type", "NATIONAL"),
        "operationType": metadata.get("default_operation_type", "STANDARD"),
    }

    number_template_id = credential.number_template_id or metadata.get("number_template_id")
    if number_template_id:
        invoice_payload["numberTemplate"] = {"id": number_template_id}

    if taxes:
        invoice_payload["taxTotals"] = taxes

    return invoice_payload


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return "Cliente", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _as_list(value: Any) -> List[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]
