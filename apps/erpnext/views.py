import logging

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import ERPNextCredential
from .services import ERPNextClient, ERPNextClientError
from .serializers import ItemSerializer

logger = logging.getLogger(__name__)


class ItemDetailView(APIView):
    """API View to retrieve details for a specific Item from ERPNext."""

    # In a real scenario, you would add permission classes, e.g.:
    # permission_classes = [IsAuthenticated]

    def get(self, request, item_code: str, *args, **kwargs):
        # The Organization is expected to be on the request object
        # thanks to the OrganizationContextMiddleware.
        organization = getattr(request, "organization", None)
        if not organization:
            return Response(
                {"error": "Organization context not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credential = ERPNextCredential.objects.active().filter(organization_id=organization.id).first()
        if not credential:
            return Response(
                {"error": "Active ERPNext credentials for this organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            client = ERPNextClient(credential=credential)
            item_data = client.get_item(item_code=item_code)
        except ERPNextClientError as e:
            logger.error("Failed to fetch item %s for org %s: %s", item_code, organization.id, e)
            return Response(
                {"error": "Failed to communicate with ERPNext.", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("An unexpected error occurred while fetching item %s for org %s", item_code, organization.id)
            return Response(
                {"error": "An unexpected internal error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = ItemSerializer(data=item_data)
        serializer.is_valid() # is_valid() is safe to call without raising exceptions on a pass-through serializer
        return Response(serializer.data)


class SalesOrderListView(APIView):
    """API View to retrieve a list of Sales Orders from ERPNext."""

    def get(self, request, *args, **kwargs):
        organization = getattr(request, "organization", None)
        if not organization:
            return Response(
                {"error": "Organization context not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credential = ERPNextCredential.objects.active().filter(organization_id=organization.id).first()
        if not credential:
            return Response(
                {"error": "Active ERPNext credentials for this organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Extract filters and fields from query parameters
        # Example: /api/erpnext/sales-orders/?filters=[["status","=","To Bill"]]&fields=["name","customer"]
        try:
            filters = request.query_params.get("filters")
            fields = request.query_params.get("fields")
            limit = int(request.query_params.get("limit", 20))
            offset = int(request.query_params.get("offset", 0))

            client = ERPNextClient(credential=credential)
            orders_data = client.list_sales_orders(
                filters=filters,
                fields=fields,
                limit=limit,
                offset=offset
            )
        except ERPNextClientError as e:
            logger.error("Failed to fetch sales orders for org %s: %s", organization.id, e)
            return Response(
                {"error": "Failed to communicate with ERPNext.", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("An unexpected error occurred while fetching sales orders for org %s", organization.id)
            return Response(
                {"error": "An unexpected internal error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(orders_data)


class CreateSalesInvoicesView(APIView):
    """Triggers a background task to create Sales Invoices from all pending Sales Orders."""

    def post(self, request, *args, **kwargs):
        organization = getattr(request, "organization", None)
        if not organization:
            return Response(
                {"error": "Organization context not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Import the task here to avoid circular dependency issues at startup
        from .tasks import create_invoices_from_pending_orders_task

        # Dispatch the background task
        create_invoices_from_pending_orders_task.delay(organization_id=str(organization.id))

        return Response(
            {"message": "Process to create Sales Invoices has been started in the background."},
            status=status.HTTP_202_ACCEPTED,
        )


class StockLevelListView(APIView):
    """API View to retrieve stock levels from ERPNext Bin doctype."""

    def get(self, request, *args, **kwargs):
        organization = getattr(request, "organization", None)
        if not organization:
            return Response(
                {"error": "Organization context not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credential = ERPNextCredential.objects.active().filter(organization_id=organization.id).first()
        if not credential:
            return Response(
                {"error": "Active ERPNext credentials for this organization not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Build filters from query parameters
            query_filters = []
            item_code = request.query_params.get("item_code")
            warehouse = request.query_params.get("warehouse")

            if item_code:
                query_filters.append(["item_code", "=", item_code])
            if warehouse:
                query_filters.append(["warehouse", "=", warehouse])

            client = ERPNextClient(credential=credential)
            stock_data = client.get_stock_levels(filters=str(query_filters) if query_filters else None)

        except ERPNextClientError as e:
            logger.error("Failed to fetch stock levels for org %s: %s", organization.id, e)
            return Response(
                {"error": "Failed to communicate with ERPNext.", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("An unexpected error occurred while fetching stock levels for org %s", organization.id)
            return Response(
                {"error": "An unexpected internal error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(stock_data)