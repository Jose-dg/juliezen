
from django.urls import path

from .views import ShopifyWebhookView

app_name = "shopify"

urlpatterns = [
    path("webhook/", ShopifyWebhookView.as_view(), name="webhook"),
]
