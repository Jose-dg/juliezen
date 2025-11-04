import logging
from typing import Any, Dict, List
from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.integrations.exceptions import WebhookValidationError, AlegraAPIError, AlegraCredentialError
from apps.integrations.models import IntegrationMessage
from apps.organizations.models import Organization
from apps.alegra.models import AlegraCredential
from apps.alegra.client import AlegraClient

logger = logging.getLogger(__name__)

class ERPNextToAlegraInvoiceService:
    ALLOWED_ALEGRA_IDENTIFICATION_TYPES = {
        "NIT",
        "CC",
        "CE",
        "TI",
        "PPN",
        "RC",
    }

    def __init__(self, message: IntegrationMessage):
        self.message = message
        self.organization = self._load_organization(message.organization_id)
        self.payload = message.payload # The ERPNext webhook payload

        self.alegra_credential = self._load_alegra_credential(self.organization)
        self.alegra_client = AlegraClient(
            organization_id=self.organization.id,
            base_url=self.alegra_credential.base_url,
            api_key=self.alegra_credential.email,
            api_secret=self.alegra_credential.token,
            timeout_s=self.alegra_credential.timeout_s,
            max_retries=self.alegra_credential.max_retries,
        )

    def process(self) -> Dict[str, Any]:
        self._set_status(IntegrationMessage.STATUS_PROCESSING_CUSTOMER)
        # 1. Parse ERPNext payload
        erpnext_invoice_data = self._parse_erpnext_payload()

        # 2. Check/Create Customer in Alegra
        alegra_customer_id = self._get_or_create_alegra_customer(erpnext_invoice_data["customer"])

        self._set_status(IntegrationMessage.STATUS_PROCESSING_INVOICE)
        # 3. Prepare Alegra invoice payload
        alegra_invoice_payload = self._prepare_alegra_invoice_payload(erpnext_invoice_data, alegra_customer_id)

        self._set_status(IntegrationMessage.STATUS_CREATING_INVOICE)
        # 4. Create Invoice in Alegra
        created_alegra_invoice = self.alegra_client.create_invoice(alegra_invoice_payload)

        self._set_status(IntegrationMessage.STATUS_PROCESSED)
        return created_alegra_invoice

    def _load_organization(self, organization_id: str) -> Organization:
        try:
            return Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise WebhookValidationError(f"Organization {organization_id} not found.")

    def _load_alegra_credential(self, organization: Organization) -> AlegraCredential:
        try:
            return AlegraCredential.objects.get(organization=organization, is_active=True)
        except AlegraCredential.DoesNotExist:
            raise WebhookValidationError(f"Alegra credentials for organization {organization.id} not found.")

    def _parse_erpnext_payload(self) -> Dict[str, Any]:
        payload = self.payload
        if not payload:
            raise WebhookValidationError("ERPNext webhook payload is empty.")

        # Basic validation
        if not all(k in payload for k in ["name", "customer", "items"]):
            raise WebhookValidationError("Invalid ERPNext payload structure.")

        parsed_data = {
            "name": payload.get("name"),
            "posting_date": payload.get("posting_date"),
            "pos_profile": payload.get("pos_profile"),
            "customer": {
                "name": payload.get("customer_name"),
                "email": payload.get("contact_email"),
                "phone": payload.get("contact_mobile"),
                "identification": payload.get("tax_id"),
                "identification_type": payload.get("custom_document_type"),
                "custom_alegra_id": payload.get("custom_alegra_id"),
                "code": payload.get("customer"),
                "address": {
                    "line1": payload.get("address_display"),
                    "city": payload.get("city"),
                }
            },
            "items": [
                {
                    "item_code": item.get("item_code"),
                    "item_name": item.get("item_name"),
                    "qty": item.get("qty"),
                    "rate": item.get("rate"),
                    "amount": item.get("amount"),
                }
                for item in payload.get("items", [])
            ],
            "taxes": [
                {
                    "charge_type": tax.get("charge_type"),
                    "account_head": tax.get("account_head"),
                    "rate": tax.get("rate"),
                    "tax_amount": tax.get("tax_amount"),
                }
                for tax in payload.get("taxes", [])
            ],
            "payments": [
                {
                    "mode_of_payment": payment.get("mode_of_payment"),
                    "amount": payment.get("amount"),
                }
                for payment in payload.get("payments", [])
            ],
        }
        return parsed_data

    def _get_or_create_alegra_customer(self, erpnext_customer_data: Dict[str, Any]) -> str:
        alegra_customer_id = erpnext_customer_data.get("custom_alegra_id")
        customer_code = erpnext_customer_data.get("code")
        customer_name = erpnext_customer_data.get("name")
        customer_email = erpnext_customer_data.get("email")
        customer_identification = self._extract_customer_identification(erpnext_customer_data)
        customer_identification_type = self._normalize_identification_type(erpnext_customer_data)

        logger.info(
            "[ALEGRA] Customer data for Alegra: "
            f"identification_type={customer_identification_type}, "
            f"identification={customer_identification}"
        )

        # 1. Try to find by custom_alegra_id (if provided by ERPNext)
        if alegra_customer_id:
            try:
                customer = self.alegra_client.get_customer(alegra_customer_id)
                if customer: # Alegra's get_customer might return None or raise error
                    return str(customer["id"])
            except Exception as e:
                logger.warning(f"Alegra customer lookup by custom_alegra_id {alegra_customer_id} failed: {e}")

        # 2. Try to find by identification (NIT/DNI)
        if customer_identification:
            try:
                customers = self.alegra_client.search_customers(query=customer_identification)
                if customers and customers[0].get("id"):
                    return str(customers[0]["id"])
            except Exception as e:
                logger.warning(f"Alegra customer lookup by identification {customer_identification} failed: {e}")

        # 3. Try to find by email
        if customer_email:
            try:
                customers = self.alegra_client.search_customers(query=customer_email)
                if customers and customers[0].get("id"):
                    return str(customers[0]["id"])
            except Exception as e:
                logger.warning(f"Alegra customer lookup by email {customer_email} failed: {e}")

        # 4. If not found, create a new customer
        if not customer_name:
            raise WebhookValidationError("Customer name is required to create a new Alegra customer.")

        new_customer_payload = {
            "name": customer_name,
            "email": customer_email,
            "phone": erpnext_customer_data.get("phone"),
            "identification": customer_identification,
            "identificationType": customer_identification_type,
            "address": {
                "address": erpnext_customer_data.get("address", {}).get("line1"),
                "city": erpnext_customer_data.get("address", {}).get("city"),
            },
            "type": "client", # Assuming it's always a client
        }
        # Remove None values to avoid Alegra API errors
        new_customer_payload = {k: v for k, v in new_customer_payload.items() if v is not None}
        if new_customer_payload.get("address"): # Remove empty address if all fields are None
            new_customer_payload["address"] = {k: v for k, v in new_customer_payload["address"].items() if v is not None}
            if not new_customer_payload["address"]:
                new_customer_payload.pop("address")

        self._set_status(IntegrationMessage.STATUS_CREATING_CUSTOMER)
        try:
            created_customer = self.alegra_client.create_customer(new_customer_payload)
            if created_customer and created_customer.get("id"):
                logger.info(f"Created new Alegra customer: {created_customer['id']} for ERPNext customer {customer_code}")
                # Optionally, update ERPNext with custom_alegra_id here if ERPNext supports it
                return str(created_customer["id"])
        except Exception as e:
            logger.error(f"Failed to create new Alegra customer for ERPNext customer {customer_code}: {e}")
            raise WebhookValidationError(f"Failed to create Alegra customer: {e}") from e

        raise WebhookValidationError("Could not find or create Alegra customer.")

    def _prepare_alegra_invoice_payload(self, erpnext_invoice_data: Dict[str, Any], alegra_customer_id: str) -> Dict[str, Any]:
        alegra_items = []
        for item in erpnext_invoice_data.get("items", []):
            alegra_items.append({
                "id": None, 
                "name": item.get("item_name") or item.get("item_code"),
                "price": {
                    "price": item.get("rate"),
                },
                "quantity": item.get("qty"),
            })

        invoice_name = erpnext_invoice_data.get("name")
        pos_profile = erpnext_invoice_data.get("pos_profile")
        alegra_payload = {
            "date": erpnext_invoice_data.get("posting_date"),
            "client": {
                "id": alegra_customer_id
            },
            "items": alegra_items,
            "dueDate": erpnext_invoice_data.get("posting_date"), 
            "observations": f"ERPNext Invoice: {invoice_name}",
            "anotations": f"ERPNext POS Profile: {pos_profile}",
            "status": "open", 
            "type": "invoice", 
        }

        return alegra_payload

    def _extract_customer_identification(self, erpnext_customer_data: Dict[str, Any]) -> str:
        identification = (erpnext_customer_data.get("identification") or "").strip()
        if not identification:
            raise WebhookValidationError(
                "Customer identification is required to synchronize invoices with Alegra."
            )
        return identification

    def _normalize_identification_type(self, erpnext_customer_data: Dict[str, Any]) -> str:
        raw_type = erpnext_customer_data.get("identification_type")
        if raw_type is None:
            raise WebhookValidationError(
                "Customer identification_type is required to synchronize invoices with Alegra."
            )

        normalized = str(raw_type).strip().upper()
        if not normalized:
            raise WebhookValidationError(
                "Customer identification_type cannot be empty when sending data to Alegra."
            )

        if normalized not in self.ALLOWED_ALEGRA_IDENTIFICATION_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_ALEGRA_IDENTIFICATION_TYPES))
            raise WebhookValidationError(
                f"Unsupported identification_type '{raw_type}' for Alegra. Allowed values: {allowed}."
            )

        return normalized

    def _set_status(self, status: str):
        self.message.status = status
        self.message.save(update_fields=["status"])
