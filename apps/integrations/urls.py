from django.urls import path

from .views import ERPNextPOSWebhookView, WebhookGateway

app_name = "integrations"

urlpatterns = [
    path("alegra/<uuid:organization_id>/webhook/", WebhookGateway.as_view(), name="alegra"),
    path(
        "erpnext/<uuid:organization_id>/webhook/pos-invoice/",
        ERPNextPOSWebhookView.as_view(),
        name="erpnext-pos",
    ),
]
