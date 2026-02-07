from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from apps.category.models import ExpenseCategory
from apps.category.serializers import ExpenseCategoryCreateSerializer
from apps.common.utils import first_error_message, success_response, error_response
from apps.common import messages
from rest_framework.permissions import IsAuthenticated


class ExpenseCategoryCreateView(ListCreateAPIView):
    """
    Create a new expense category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseCategoryCreateSerializer
    queryset = ExpenseCategory.objects.all().order_by("id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        category = serializer.save()

        return success_response(
            message=messages.EXPENSE_CATEGORY_CREATED_SUCCESSFULLY,
            data=ExpenseCategoryCreateSerializer(category).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class ExpenseCategoryRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete an expense category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseCategoryCreateSerializer
    queryset = ExpenseCategory.objects.all()
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        category = serializer.save()

        return success_response(
            message=messages.EXPENSE_CATEGORY_UPDATED_SUCCESSFULLY,
            data=self.get_serializer(category).data,
        )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()  # HARD DELETE

        return success_response(message=messages.EXPENSE_CATEGORY_DELETED_SUCCESSFULLY)
