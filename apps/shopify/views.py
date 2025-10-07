import base64
import hashlib
import hmac
import json

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ShopifyStore
from .tasks import process_shopify_order


class ShopifyWebhookView(APIView):
    """Handles incoming webhooks from Shopify."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        shopify_domain = request.headers.get("X-Shopify-Shop-Domain")
        if not shopify_domain:
            return Response(
                {"detail": "Missing X-Shopify-Shop-Domain header."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            store = ShopifyStore.objects.get(shopify_domain=shopify_domain)
        except ShopifyStore.DoesNotExist:
            return Response(
                {"detail": f"Shopify store not found for domain: {shopify_domain}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # TODO: Re-enable signature validation once Shopify shared secret is confirmed.
        # if not self._validate_webhook(request, store.webhook_shared_secret):
        #     return Response(
        #         {"detail": "Webhook signature validation failed."},
        #         status=status.HTTP_403_FORBIDDEN,
        #     )

        process_shopify_order.delay(str(store.organization_id), request.data)

        return Response(status=status.HTTP_202_ACCEPTED)

    def _validate_webhook(self, request: HttpRequest, secret: str) -> bool:
        """Validates the HMAC-SHA256 signature of the webhook."""
        signature = request.headers.get("X-Shopify-Hmac-Sha256")
        if not signature:
            return False

        computed_hmac = hmac.new(
            secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).digest()
        computed_hmac_b64 = base64.b64encode(computed_hmac)

        return hmac.compare_digest(computed_hmac_b64, signature.encode("utf-8"))
