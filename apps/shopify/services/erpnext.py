import logging

from apps.erpnext.models import ERPNextCredential
from apps.erpnext.services.client import ERPNextClient

logger = logging.getLogger(__name__)

class ShopifyToErpNextService:
    """
    Service to process a Shopify order and create a Sales Invoice in ERPNext.
    """

    def __init__(self, organization_id: str, order_data: dict):
        self.organization_id = organization_id
        self.order_data = order_data
        self.credential = self._get_credential()
        self.client = self._get_client()

    def _get_credential(self) -> ERPNextCredential:
        """Get the active ERPNext credential for the organization."""
        credential = ERPNextCredential.objects.for_company(self.organization_id)
        if not credential:
            raise Exception(f"No active ERPNext credential found for organization {self.organization_id}")
        return credential

    def _get_client(self) -> ERPNextClient:
        """Get an instance of the ERPNextClient."""
        return ERPNextClient(self.credential)

    def process(self) -> dict:
        """
        Process the Shopify order and create a Sales Invoice in ERPNext.
        """
        logger.info(
            "Processing Shopify order %s for organization %s",
            self.order_data.get("name"),
            self.organization_id,
        )

        # TODO: Implement the mapping from Shopify order to ERPNext Sales Invoice
        # For now, just returning a placeholder response.

        si_doc = self._build_sales_invoice()

        try:
            inserted = self.client.insert_doc("Sales Invoice", si_doc)
            invoice_name = inserted.get("name")
            submitted = self.client.submit_doc("Sales Invoice", invoice_name)
            return {
                "invoice_name": invoice_name,
                "outbound_request": si_doc,
                "submitted_response": submitted,
            }
        except Exception as e:
            logger.exception("Failed to create Sales Invoice in ERPNext.")
            raise e

    def _build_sales_invoice(self) -> dict:
        """
        Build the Sales Invoice document from the Shopify order data.
        This is a placeholder implementation.
        """
        customer_name = self.order_data.get("customer", {}).get("first_name", "") + " " + self.order_data.get("customer", {}).get("last_name", "")
        return {
            "customer": customer_name or "Default Customer",
            "items": [
                {
                    "item_code": item.get("sku"),
                    "qty": item.get("quantity"),
                    "rate": item.get("price"),
                }
                for item in self.order_data.get("line_items", [])
            ],
            # Add other required fields here
        }
