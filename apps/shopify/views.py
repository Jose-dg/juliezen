from django.http import HttpRequest, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

class ShopifyWebhookView(APIView):
    """Handles incoming webhooks from Shopify."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        from apps.shopify.services import process_shopify_webhook
        print(f"\n{'--'*20} [VIEW] Shopify Webhook Received {'--'*20}")
        return process_shopify_webhook(request)

