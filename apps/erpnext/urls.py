
from django.urls import path

from apps.integrations.views import ERPNextPOSWebhookView

from . import views

app_name = "erpnext"

urlpatterns = [
    path("items/<str:item_code>/",views.ItemDetailView.as_view(),name="item-detail"),
    path("sales-orders/",views.SalesOrderListView.as_view(), name="sales-order-list"),
    path("actions/create-sales-invoices/",views.CreateSalesInvoicesView.as_view(), name="create-sales-invoices"),
    path("stock-levels/", views.StockLevelListView.as_view(), name="stock-level-list"),
    path(
        "organizations/<uuid:organization_id>/webhooks/pos-invoice/",
        ERPNextPOSWebhookView.as_view(),
        name="pos-invoice-webhook",
    ),
]
