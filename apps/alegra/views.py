from django.shortcuts import get_object_or_404
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization
from apps.integrations.exceptions import WebhookValidationError
from apps.integrations.models import IntegrationMessage
from .models import AlegraCredential
from apps.integrations.tasks import process_integration_message
from apps.integrations.utils import record_integration_message


class AlegraWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request, organization_id, *args, **kwargs):
        organization = get_object_or_404(Organization, id=organization_id)
        payload = request.data if isinstance(request.data, dict) else request.data.dict()
        try:
            credential = self._get_credential(organization)
            self._validate_secret(request, credential)
        except WebhookValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        event_type = payload.get("event") or payload.get("type", "")
        external_reference = ""
        if payload.get("id"):
            external_reference = str(payload["id"])
        else:
            data = payload.get("data")
            if isinstance(data, dict) and data.get("id"):
                external_reference = str(data["id"])

        idempotency_key = payload.get("idempotency_key") or external_reference

        message = record_integration_message(
            organization_id=organization.id,
            direction=IntegrationMessage.DIRECTION_INBOUND,
            integration=IntegrationMessage.INTEGRATION_ALEGRA,
            event_type=event_type,
            payload=payload,
            external_reference=external_reference,
            idempotency_key=idempotency_key,
        )

        message.mark_dispatched(http_status=status.HTTP_202_ACCEPTED)
        process_integration_message.delay(str(message.id))

        return Response(
            {
                "status": "accepted",
                "message_id": str(message.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def _get_credential(self, organization) -> AlegraCredential:
        credential = (
            AlegraCredential.objects.active()
            .filter(organization_id=organization.id)
            .exclude(webhook_secret__isnull=True)
            .exclude(webhook_secret="")
            .order_by("-updated_at")
            .first()
        )
        if not credential:
            raise WebhookValidationError("No hay webhook secret configurado para la organización")
        return credential

    def _validate_secret(self, request, credential: AlegraCredential) -> None:
        secret = request.headers.get("X-Alegra-Webhook-Secret") or request.META.get("HTTP_X_ALEGRA_WEBHOOK_SECRET")
        if not secret:
            raise WebhookValidationError("Falta cabecera de validación del webhook")
        stored_secret = credential.webhook_secret or ""
        if not constant_time_compare(secret, stored_secret):
            raise WebhookValidationError("Webhook secret inválido")
