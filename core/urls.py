"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API endpoints (comentadas temporalmente para resolver errores de importación)
    path("api/alegra/", include(("apps.alegra.urls", "alegra"), namespace="alegra")),
    # path("api/integrations/", include("apps.integrations.urls")),
    # Health check
    # path("", include("core.urls")),
    # path("api/organizations/", include("apps.organizations.urls")),
    # path("api/recommendations/", include("apps.recommendations.urls")),
    # path("api/notifications/", include("apps.notifications.urls")),
    # path("api/users/", include("apps.users.urls")),
    # Auth
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
