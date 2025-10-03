"""Service layer for Alegra domain."""

from .erpnext_invoice import process_erpnext_pos_invoice

__all__ = ["process_erpnext_pos_invoice"]
