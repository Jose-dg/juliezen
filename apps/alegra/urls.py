from django.urls import path

from apps.integrations.views import WebhookGateway

app_name = "alegra"

urlpatterns = [
    path("<uuid:organization_id>/webhook/", WebhookGateway.as_view(), name="webhook"),
]
