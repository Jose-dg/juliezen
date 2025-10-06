# services.py (o donde tengas ERPNextClient)
import json
import logging
from urllib.parse import urljoin
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class ERPNextClientError(Exception):
    pass

class ERPNextClient:
    def __init__(self, credential):
        # ... igual que el tuyo ...
        self.base_url = str(credential.erpnext_url).rstrip("/") + "/"
        self.api_key = str(credential.api_key)
        self.api_secret = str(credential.api_secret)

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(self, method: str, endpoint: str, **kwargs):
        full_url = urljoin(self.base_url, endpoint.lstrip("/"))
        headers = self._get_headers()
        try:
            resp = requests.request(
                method,
                full_url,
                headers=headers,
                timeout=getattr(settings, "REQUESTS_TIMEOUT", 15),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error("ERPNext HTTP %s: %s", e.response.status_code, e.response.text)
            raise ERPNextClientError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except requests.exceptions.RequestException as e:
            logger.error("ERPNext request error: %s", e)
            raise ERPNextClientError(str(e)) from e

    # ---------- LISTADOS ----------
    def list_sales_orders(self, filters=None, fields=None, limit=50, offset=0) -> list:
        endpoint = "/api/resource/Sales Order"
        params = {
            "limit_page_length": limit,
            "limit_start": offset,
        }
        if fields:
            params["fields"] = json.dumps(fields)   # JSON correcto
        if filters:
            params["filters"] = json.dumps(filters) # JSON correcto
        data = self.request("GET", endpoint, params=params)
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        raise ERPNextClientError("Invalid response format for list_sales_orders")

    def get_item(self, item_code: str) -> dict:
        """Fetches a single Item document from ERPNext."""
        endpoint = f"/api/resource/Item/{item_code}"
        response = self.request("GET", endpoint)
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        raise ERPNextClientError("Invalid response format for get_item")

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

    # ---------- MAPPER SO -> SI ----------
    def map_sales_order_to_invoice(self, sales_order_name: str) -> dict:
        """Devuelve el doc de Sales Invoice (AÚN no guardado) mapeado desde una Sales Order."""
        endpoint = "/api/method/erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice"
        payload = {"source_name": sales_order_name}
        data = self.request("POST", endpoint, json=payload)
        # Respuesta típica: {"message": {...doc...}} ó {"data": {...}} según versión
        doc = data.get("message") or data.get("data")
        if not isinstance(doc, dict):
            raise ERPNextClientError("Mapper returned unexpected payload")
        return doc

    # ---------- INSERT / SUBMIT ----------
    def insert_doc(self, doctype: str, doc: dict) -> dict:
        """Inserta un documento (docstatus=0)."""
        endpoint = f"/api/resource/{doctype.replace(' ', '%20')}"
        data = self.request("POST", endpoint, json=doc)
        return data.get("data") or data.get("message") or data

    def submit_doc(self, doctype: str, name: str) -> dict:
        """Submit de un documento existente (docstatus=1)."""
        endpoint = f"/api/resource/{doctype.replace(' ', '%20')}/{name}"
        payload = {"docstatus": 1}
        data = self.request("PUT", endpoint, json=payload)
        return data.get("data") or data.get("message") or data

    # ---------- ATOMIC: crear y enviar SI desde SO ----------
    def create_and_submit_invoice_from_order(self, so_name: str, *, update_stock=False, posting_date=None, due_date=None) -> dict:
        # 1) Mapear
        si_doc = self.map_sales_order_to_invoice(so_name)

        # 2) Ajustes antes de insertar
        si_doc.setdefault("update_stock", 1 if update_stock else 0)
        if posting_date:
            si_doc["set_posting_time"] = 1
            si_doc["posting_date"] = posting_date
        if due_date:
            si_doc["due_date"] = due_date

        # (opcional) asegurarte de no duplicar pagos automáticos del POS:
        # si_doc["is_pos"] = 0

        # 3) Insertar (docstatus = 0)
        inserted = self.insert_doc("Sales Invoice", si_doc)
        name = inserted.get("name")

        # 4) Submit (docstatus = 1)
        submitted = self.submit_doc("Sales Invoice", name)
        return submitted