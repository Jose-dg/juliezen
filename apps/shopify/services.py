
import logging
from typing import Any, Dict

from apps.erpnext.services import ERPNextClient
from apps.erpnext.models import ERPNextCredential

logger = logging.getLogger(__name__)


class ShopifyToErpNextService:
    """
    Service to convert a Shopify order into an ERPNext Sales Invoice.
    """

    def __init__(self, organization_id: str, order_data: Dict[str, Any]):
        self.organization_id = organization_id
        self.order_data = order_data

    def process(self):
        """Main method to process the Shopify order."""
        erpnext_credential = self._get_erpnext_credential()
        erpnext_client = ERPNextClient(erpnext_credential)

        sales_invoice_payload = self._build_sales_invoice_payload()

        # Insert the Sales Invoice as a draft
        draft_invoice = erpnext_client.insert_doc("Sales Invoice", sales_invoice_payload)
        invoice_name = draft_invoice.get("name")

        if not invoice_name:
            raise Exception("Failed to create Sales Invoice draft.")

        # Submit the Sales Invoice
        erpnext_client.submit_doc("Sales Invoice", invoice_name)

        logger.info(
            f"Successfully created and submitted Sales Invoice {invoice_name} for organization {self.organization_id}"
        )

    def _get_erpnext_credential(self) -> ERPNextCredential:
        """Retrieves the active ERPNext credential for the organization."""
        credential = ERPNextCredential.objects.active().filter(organization_id=self.organization_id).first()
        if not credential:
            raise Exception(f"No active ERPNext credentials for organization {self.organization_id}")
        return credential

    def _build_sales_invoice_payload(self) -> Dict[str, Any]:
        """Transforms the Shopify order data into an ERPNext Sales Invoice payload."""
        
        customer_name = self.order_data.get("customer", {}).get("first_name", "") + " " + self.order_data.get("customer", {}).get("last_name", "")

        items = []
        for line_item in self.order_data.get("line_items", []):
            items.append({
                "item_code": line_item.get("sku"),
                "qty": line_item.get("quantity"),
                "rate": line_item.get("price"),
            })

        payload = {
            "customer": customer_name.strip(),
            "posting_date": self.order_data.get("created_at").split("T")[0],
            "items": items,
            # Add other necessary fields here
        }

        return payload
