import uuid

from django.db import models
from django.db.models import JSONField


class OrganizationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    metadata = JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrganizationQuerySet.as_manager()

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name