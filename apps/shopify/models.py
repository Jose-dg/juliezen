import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _




class ShopifyStore(models.Model):
    """Represents a Shopify store integration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True, verbose_name=_("Organization ID"))
    shopify_domain = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Shopify Domain"),
        help_text=_("The .myshopify.com domain of the store."),
    )
    webhook_shared_secret = models.TextField(
        verbose_name=_("Webhook Shared Secret"),
        help_text=_("The shared secret for validating webhooks from Shopify."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Shopify Store")
        verbose_name_plural = _("Shopify Stores")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.shopify_domain