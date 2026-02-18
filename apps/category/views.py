from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from django.db.models import Sum
from apps.category.models import Category, Transaction
from apps.category.serializers import (
    CategoryCreateSerializer,
    TransactionSerializer,
    FinancialSummarySerializer,
)
from apps.common.utils import first_error_message, success_response, error_response
from apps.common import messages
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes,
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    ),
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    ),
)
class CategoryCreateView(ListCreateAPIView):
    """
    Create a new category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategoryCreateSerializer
    queryset = Category.objects.all().order_by("id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        category = serializer.save()

        return success_response(
            message=messages.EXPENSE_CATEGORY_CREATED_SUCCESSFULLY,
            data=CategoryCreateSerializer(category).data,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        type_filter = request.query_params.get("type")
        if type_filter in ["income", "expense"]:
            queryset = queryset.filter(type=type_filter)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class CategoryRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update (name only), or delete a category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategoryCreateSerializer
    queryset = Category.objects.all()
    lookup_field = "id"
    http_method_names = ["get", "patch", "delete"]

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return success_response(data=serializer.data)

    @extend_schema(request=CategoryCreateSerializer, responses=CategoryCreateSerializer)
    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        # Only allow updating name
        if "name" not in request.data:
            return error_response(message="Only name field can be updated", status=400)

        # Check if new name conflicts with existing category of same type
        new_name = request.data.get("name").strip()
        if (
            Category.objects.filter(name__iexact=new_name, type=category.type)
            .exclude(id=category.id)
            .exists()
        ):
            return error_response(
                message="Category with this name already exists for this type",
                status=400,
            )

        category.name = new_name
        category.save()

        serializer = self.get_serializer(category)
        return success_response(
            message="Category name updated successfully",
            data=serializer.data,
        )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()  # HARD DELETE

        return success_response(message=messages.EXPENSE_CATEGORY_DELETED_SUCCESSFULLY)


class TransactionCreateView(ListCreateAPIView):
    """
    Create and list transactions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by("-date")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        transaction = serializer.save()

        return success_response(
            message="Transaction created successfully",
            data=TransactionSerializer(transaction).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Calculate totals (based on type)
        total_income = (
            queryset.filter(type="income").aggregate(total=Sum("amount"))["total"] or 0
        )
        total_expenses = (
            queryset.filter(type="expense").aggregate(total=Sum("amount"))["total"] or 0
        )
        balance = float(total_income) - float(total_expenses)

        data = {
            "transactions": serializer.data,
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "balance": balance,
            },
        }
        return success_response(data=data)


class TransactionRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a transaction.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        transaction = self.get_object()
        serializer = self.get_serializer(transaction)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        transaction = self.get_object()
        data = request.data.copy()
        # Prevent updating type
        if "type" in data:
            data.pop("type")
        serializer = self.get_serializer(transaction, data=data, partial=True)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        transaction = serializer.save()

        return success_response(
            message="Transaction updated successfully",
            data=self.get_serializer(transaction).data,
        )

    def destroy(self, request, *args, **kwargs):
        transaction = self.get_object()
        transaction.delete()

        return success_response(message="Transaction deleted successfully")


class FinancialSummaryView(APIView):
    """
    Get financial summary for the user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FinancialSummarySerializer

    def get(self, request):
        user = request.user

        # Calculate total income
        total_income = (
            Transaction.objects.filter(user=user, category__type="income").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Calculate total expenses
        total_expenses = (
            Transaction.objects.filter(user=user, category__type="expense").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Calculate balance
        balance = float(total_income) - float(total_expenses)

        data = {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
        }

        return success_response(data=data)
