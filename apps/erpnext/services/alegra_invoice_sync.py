import logging
from typing import Any, Dict

from apps.integrations.exceptions import WebhookValidationError
from apps.integrations.models import IntegrationMessage
from apps.organizations.models import Organization
from apps.alegra.models import AlegraCredential
from apps.alegra.client import AlegraClient

logger = logging.getLogger(__name__)

class ERPNextToAlegraInvoiceService:
    def __init__(self, message: IntegrationMessage):
        self.message = message
        self.organization = self._load_organization(message.organization_id)
        self.payload = message.payload # The ERPNext webhook payload

        self.alegra_credential = self._load_alegra_credential(self.organization)
        self.alegra_client = AlegraClient(self.alegra_credential)

    def process(self) -> Dict[str, Any]:
        # 1. Parse ERPNext payload
        erpnext_invoice_data = self._parse_erpnext_payload()

        # 2. Check/Create Customer in Alegra
        alegra_customer_id = self._get_or_create_alegra_customer(erpnext_invoice_data["customer"])

        # 3. Prepare Alegra invoice payload
        alegra_invoice_payload = self._prepare_alegra_invoice_payload(erpnext_invoice_data, alegra_customer_id)

        # 4. Create Invoice in Alegra
        alegra_invoice_response = self.alegra_client.create_invoice(alegra_invoice_payload)

        # 5. Handle response and update ERPNext (optional, if needed)
        # ...

        return {"alegra_invoice_id": alegra_invoice_response.get("id")}

    def _load_organization(self, organization_id) -> Organization:
        organization = Organization.objects.filter(id=organization_id).first()
        if not organization:
            raise WebhookValidationError(f"Organización {organization_id} no encontrada.")
        return organization

    def _load_alegra_credential(self, organization: Organization) -> AlegraCredential:
        credential = (
            AlegraCredential.objects.active()
            .filter(organization_id=organization.id)
            .order_by("-updated_at")
            .first()
        )
        if not credential:
            raise WebhookValidationError("No hay credenciales activas de Alegra para la organización.")
        return credential

    def _parse_erpnext_payload(self) -> Dict[str, Any]:
        payload = self.payload
        customer_data = payload.get("customer", {})
        address_data = customer_data.get("address", {})

        parsed_data = {
            "source": payload.get("source"),
            "doctype": payload.get("doctype"),
            "event": payload.get("event"),
            "company": payload.get("company"),
            "name": payload.get("name"),
            "posting_date": payload.get("posting_date"),
            "currency": payload.get("currency"),
            "grand_total": payload.get("grand_total"),
            "pos_profile": payload.get("pos_profile"),
            "naming_series": payload.get("naming_series"),
            "customer": {
                "code": customer_data.get("code"),
                "name": customer_data.get("name"),
                "custom_alegra_id": customer_data.get("custom_alegra_id"),
                "identification_type": customer_data.get("identification_type"),
                "identification": customer_data.get("identification"),
                "email": customer_data.get("email"),
                "phone": customer_data.get("phone"),
                "address": {
                    "name": address_data.get("name"),
                    "line1": address_data.get("line1"),
                    "line2": address_data.get("line2"),
                    "city": address_data.get("city"),
                    "state": address_data.get("state"),
                    "country": address_data.get("country"),
                    "postal_code": address_data.get("postal_code"),
                },
            },
            "items": [
                {
                    "item_code": item.get("item_code"),
                    "item_name": item.get("item_name"),
                    "description": item.get("description"),
                    "item_group": item.get("item_group"),
                    "qty": item.get("qty"),
                    "rate": item.get("rate"),
                    "amount": item.get("amount"),
                    "warehouse": item.get("warehouse"),
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
        customer_identification = erpnext_customer_data.get("identification")

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
            # Assuming Alegra can create items by name and infer tax if rate is provided
            # In a real scenario, you might need to map item_code to Alegra product ID
            alegra_items.append({
                "id": None, # Placeholder, might need to search/create Alegra product
                "name": item.get("item_name") or item.get("item_code"),
                "price": {
                    "price": item.get("rate"),
                    # Tax mapping is complex. Assuming simple tax rate or ID lookup.
                    # For now, we'll omit explicit tax ID and let Alegra calculate if possible.
                    # Or, if ERPNext taxes map directly to Alegra taxes, we'd do that here.
                },
                "quantity": item.get("qty"),
            })

        # Alegra's API might expect taxes at the item level or as a separate array.
        # For simplicity, we'll assume taxes are handled by item price or calculated by Alegra.
        # If explicit tax lines are needed, this section would be more complex.
        # For now, we'll just pass the total amount and let Alegra handle tax calculation if possible.

        invoice_name = erpnext_invoice_data.get("name")
        pos_profile = erpnext_invoice_data.get("pos_profile")
        alegra_payload = {
            "date": erpnext_invoice_data.get("posting_date"),
            "client": {
                "id": alegra_customer_id
            },
            "items": alegra_items,
            "total": erpnext_invoice_data.get("grand_total"),
            "dueDate": erpnext_invoice_data.get("posting_date"), # Assuming due date is same as posting date for simplicity
            "observations": f"ERPNext Invoice: {invoice_name}",
            "anotations": f"ERPNext POS Profile: {pos_profile}",
            "status": "open", # Assuming initial status is open
            "type": "invoice", # Assuming it's a standard invoice
            # Alegra handles numbering automatically, so no 'number' field here unless specified.
        }

        # Add payments if available and Alegra supports adding payments during invoice creation
        # This is a simplification; often payments are added separately.
        # For now, we'll omit payments from the invoice creation payload.
        # if erpnext_invoice_data.get("payments"):
        #     alegra_payload["payments"] = [
        #         {
        #             "date": erpnext_invoice_data.get("posting_date"),
        #             "amount": p.get("amount"),
        #             "type": p.get("mode_of_payment").lower() # Needs mapping to Alegra payment types
        #         }
        #         for p in erpnext_invoice_data["payments"]
        #     ]

        return alegra_payload