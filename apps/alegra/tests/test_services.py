import uuid
from unittest import mock

from django.test import SimpleTestCase

from apps.alegra.services import erpnext_invoice
from apps.integrations.models import IntegrationMessage


class ProcessERPNextInvoiceTests(SimpleTestCase):
    def setUp(self) -> None:
        self.organization_id = uuid.uuid4()
        self.credential = mock.Mock()
        self.credential.metadata = {
            "default_identification_type": "CC",
            "default_kind_of_person": "PERSON_ENTITY",
            "default_regime": "SIMPLIFIED_REGIME",
            "default_payment_account_id": "5",
            "default_payment_method": "transfer",
            "default_payment_method_key": "CASH",
            "default_payment_form": "CASH",
            "default_invoice_type": "NATIONAL",
            "default_operation_type": "STANDARD",
            "number_template_id": 19,
        }
        self.credential.number_template_id = 19
        self.credential.auto_stamp_on_create = True

    @mock.patch.object(erpnext_invoice, "_get_active_credential")
    @mock.patch("apps.alegra.services.erpnext_invoice.AlegraClient")
    def test_process_invoice_creates_contact_and_invoice(self, mock_client_cls, mock_get_credential):
        mock_client = mock.Mock()
        mock_client.request.side_effect = [
            [],
            {"id": "C-123"},
            {"id": "INV-123"},
        ]
        mock_client_cls.return_value = mock_client
        mock_get_credential.return_value = self.credential

        payload = {
            "doctype": "POS Invoice",
            "event": "on_submit",
            "name": "POS-INV-000123",
            "posting_date": "2025-10-02",
            "currency": "COP",
            "grand_total": 52000,
            "customer": "CF-0001",
            "customer_name": "Consumidor Final",
            "items": [
                {
                    "item_code": "PIN-PSN-50K",
                    "item_name": "PIN PlayStation 50.000",
                    "description": "Código digital PSN $50.000",
                    "qty": 1,
                    "rate": 50000,
                    "amount": 50000,
                },
                {
                    "item_code": "SRV-FEE",
                    "item_name": "Cargo servicio",
                    "description": "Trámite y activación inmediata",
                    "qty": 1,
                    "rate": 2000,
                    "amount": 2000,
                },
            ],
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "IVA 0% - DIEM",
                    "rate": 0,
                    "tax_amount": 0,
                }
            ],
        }

        message = IntegrationMessage(
            organization_id=self.organization_id,
            integration=IntegrationMessage.INTEGRATION_ALEGRA,
            direction=IntegrationMessage.DIRECTION_INBOUND,
            status=IntegrationMessage.STATUS_RECEIVED,
            event_type="on_submit",
            payload=payload,
        )

        result = erpnext_invoice.process_erpnext_pos_invoice(message)

        mock_client_cls.assert_called_once_with(self.organization_id, credential=self.credential)
        self.assertEqual(mock_client.request.call_count, 3)
        method, path = mock_client.request.call_args_list[-1].args[:2]
        self.assertEqual((method, path), ("POST", "/invoices"))

        invoice_payload = result["invoice_payload"]
        self.assertEqual(invoice_payload["client"], {"id": "C-123"})
        self.assertEqual(len(invoice_payload["items"]), 2)
        self.assertEqual(invoice_payload["payments"][0]["amount"], 52000.0)
        self.assertEqual(result["invoice_response"], {"id": "INV-123"})
