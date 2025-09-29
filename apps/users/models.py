import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    style_preferences = models.JSONField(default=dict, blank=True)
    size_profile = models.JSONField(default=dict, blank=True)
    shopping_behavior = models.JSONField(default=dict, blank=True)

    # Configuración para login con email
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = "users_user"
