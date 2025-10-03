from django.urls import path

from .views import AlegraWebhookView

app_name = "alegra"

urlpatterns = [
    path("<uuid:organization_id>/webhook/", AlegraWebhookView.as_view(), name="webhook"),
]
