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
    path("api/alegra/", include(("apps.alegra.urls", "alegra"), namespace="alegra")),
    path("api/erpnext/", include(("apps.erpnext.urls", "erpnext"), namespace="erpnext")),
    path("api/shopify/", include(("apps.shopify.urls", "shopify"), namespace="shopify")),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
