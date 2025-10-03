from django.urls import include, path

app_name = "integrations"

urlpatterns = [
    path("alegra/", include(("apps.alegra.urls", "alegra"), namespace="alegra")),
]
