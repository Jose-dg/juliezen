from __future__ import annotations
from typing import Any, Dict, Optional

from .exceptions import GatewayConfigurationError


class GatewaySettings:
    """Wrapper around organization metadata for fulfillment gateway."""

    def __init__(self, metadata: Dict[str, Any]):
        self.raw = (metadata or {}).get("fulfillment_gateway") or {}
        print(f"--- SETTINGS: RAW FULFILLMENT GATEWAY METADATA ---\n{self.raw}")
        if not isinstance(self.raw, dict):
            raise GatewayConfigurationError("metadata.fulfillment_gateway debe ser un objeto JSON.")

    @property
    def distributor_company(self) -> str:
        value = self.raw.get("distributor_company") or self.raw.get("distributor") or ""
        return str(value).strip()

    @property
    def default_warehouse(self) -> Optional[str]:
        warehouse = self.raw.get("default_warehouse")
        if warehouse:
            return str(warehouse)
        distributor = self.raw.get("distributor")
        if isinstance(distributor, dict):
            value = distributor.get("warehouse")
            if value:
                return str(value)
        return None

    @property
    def create_sales_order(self) -> bool:
        return bool(self.raw.get("create_sales_order", True))

    @property
    def serial_status(self) -> str:
        return str(self.raw.get("serial_status") or "Available")

    @property
    def backorder_retry_seconds(self) -> int:
        backorder = self.raw.get("backorder") or {}
        try:
            return int(backorder.get("retry_delay_seconds") or 900)
        except (TypeError, ValueError):
            return 900

    @property
    def item_map(self) -> Dict[str, Any]:
        mapping = self.raw.get("item_map") or {}
        return mapping if isinstance(mapping, dict) else {}

    def seller_config(self, source: str) -> Dict[str, Any]:
        sellers = self.raw.get("sellers") or {}
        config = sellers.get(source) if isinstance(sellers, dict) else {}
        return config if isinstance(config, dict) else {}

    def metadata_item_mapping(
        self,
        *,
        source: str,
        seller_company: str,
        source_item_code: str,
    ) -> Optional[Dict[str, Any]]:
        mapping = self.item_map.get(source) if isinstance(self.item_map, dict) else {}
        if not isinstance(mapping, dict):
            return None
        company_map = (
            mapping.get(seller_company)
            or mapping.get(seller_company.upper())
            or mapping.get("*")
        )
        if not isinstance(company_map, dict):
            return None
        entry = company_map.get(source_item_code) or company_map.get(source_item_code.upper())
        if isinstance(entry, dict):
            return entry
        if isinstance(entry, str):
            return {"target_item_code": entry}
        return None

    def resolve_seller_company(self, source: str, payload: Dict[str, Any]) -> str:
        """Infer seller company from payload + metadata."""
        explicit = payload.get("company_seller") or payload.get("seller_company") or payload.get("company")
        if explicit:
            return str(explicit).strip()

        config = self.seller_config(source)
        print(f"--- SETTINGS: SELLER CONFIG for source '{source}' ---\n{config}")
        default_company = config.get("default_company") or self.raw.get("default_seller_company")

        if source == "shopify":
            selector = config.get("company_selector") or {}
            print(f"--- SETTINGS: COMPANY SELECTOR ---\n{selector}")
            company = self._resolve_shopify_company(selector, payload)
            print(f"--- SETTINGS: RESOLVED SHOPIFY COMPANY ---\n{company}")
            if company:
                return company

        if source == "erpnext":
            invoice_company = payload.get("company")
            if invoice_company:
                return str(invoice_company)

        return str(default_company or "").strip()

    def _resolve_shopify_company(self, selector: Dict[str, Any], payload: Dict[str, Any]) -> str:
        if not isinstance(selector, dict):
            return ""
        source = selector.get("source")
        prefix = selector.get("prefix")
        if source == "tags" and prefix:
            tags_raw = payload.get("tags")
            if isinstance(tags_raw, str):
                for tag in (tag.strip() for tag in tags_raw.split(",")):
                    if tag.startswith(prefix):
                        company = tag[len(prefix) :].strip()
                        if company:
                            return company
        domain_map = selector.get("domain_map") or {}
        if isinstance(domain_map, dict):
            domain = payload.get("_shopify_domain") or payload.get("domain")
            print(f"--- SETTINGS: DOMAIN FROM PAYLOAD ---\n{domain}")
            if domain:
                mapped = domain_map.get(domain) or domain_map.get(str(domain).lower())
                print(f"--- SETTINGS: MAPPED COMPANY FROM DOMAIN_MAP ---\n{mapped}")
                if mapped:
                    return str(mapped)
        return ""
