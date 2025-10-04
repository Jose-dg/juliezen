
import logging
from urllib.parse import urljoin

import requests
from django.conf import settings

from .models import ERPNextCredential

logger = logging.getLogger(__name__)


class ERPNextClientError(Exception):
    """Custom exception for ERPNext client errors."""


class ERPNextClient:
    """Client to interact with the ERPNext API."""

    def __init__(self, credential: ERPNextCredential):
        if not isinstance(credential, ERPNextCredential):
            raise TypeError("A valid ERPNextCredential object is required.")
        self.credential = credential
        self.base_url = str(self.credential.erpnext_url)
        self.api_key = str(self.credential.api_key)
        self.api_secret = str(self.credential.api_secret)

    def _get_headers(self) -> dict[str, str]:
        """Constructs the authentication headers."""
        return {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict | list:
        """Makes a generic request to the ERPNext API."""
        full_url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()

        try:
            response = requests.request(
                method,
                full_url,
                headers=headers,
                timeout=settings.REQUESTS_TIMEOUT if hasattr(settings, 'REQUESTS_TIMEOUT') else 15,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(
                "ERPNext API HTTP Error for org %s: %s - %s",
                self.credential.organization_id,
                e.response.status_code,
                e.response.text,
            )
            raise ERPNextClientError(f"HTTP Error: {e.response.status_code} - {e.response.text}") from e
        except requests.exceptions.RequestException as e:
            logger.error(
                "ERPNext API Request Error for org %s: %s", self.credential.organization_id, e
            )
            raise ERPNextClientError(f"Request failed: {e}") from e

    def get_item(self, item_code: str) -> dict:
        """Fetches a single Item document from ERPNext."""
        endpoint = f"/api/resource/Item/{item_code}"
        response = self.request("GET", endpoint)
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        raise ERPNextClientError("Invalid response format for get_item")

    def list_sales_orders(self, filters: list | None = None, fields: list | None = None, limit: int = 20, offset: int = 0) -> list:
        """Fetches a list of Sales Order documents from ERPNext."""
        endpoint = "/api/resource/Sales Order"
        params = {
            "limit_page_length": limit,
            "limit_start": offset,
        }
        if fields:
            params["fields"] = str(fields) # ERPNext expects a string like '["name", "customer"]'
        if filters:
            params["filters"] = str(filters) # ERPNext expects a string like '[["status", "=", "To Bill"]]'

        response = self.request("GET", endpoint, params=params)
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        raise ERPNextClientError("Invalid response format for list_sales_orders")

    def create_sales_invoice_from_order(self, sales_order_name: str) -> dict:
        """Calls the ERPNext method to create a Sales Invoice from a Sales Order."""
        # This uses the 'make_sales_invoice' function from ERPNext's selling controller.
        # It requires the source document name to be passed.
        endpoint = "/api/method/erpnext.controllers.selling_controller.make_sales_invoice"
        payload = {
            "source_name": sales_order_name,
            "doc_type": "Sales Order",
        }
        response = self.request("POST", endpoint, json=payload)
        if isinstance(response, dict) and "message" in response and "docs" in response["message"]:
            return response["message"]["docs"][0]
        raise ERPNextClientError("Invalid response format for create_sales_invoice_from_order")

    def get_stock_levels(self, filters: list | None = None, fields: list | None = None, limit: int = 100, offset: int = 0) -> list:
        """Fetches stock level data from the Bin doctype."""
        endpoint = "/api/resource/Bin"
        params = {
            "limit_page_length": limit,
            "limit_start": offset,
        }
        if fields:
            params["fields"] = str(fields)
        if filters:
            params["filters"] = str(filters)

        response = self.request("GET", endpoint, params=params)
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        raise ERPNextClientError("Invalid response format for get_stock_levels")

