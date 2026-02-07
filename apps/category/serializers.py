from rest_framework import serializers
from apps.category.models import ExpenseCategory
from apps.common import messages


class ExpenseCategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an expense category.
    """

    class Meta:
        model = ExpenseCategory
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        """
        Validate that the expense category name is unique.
        """
        if ExpenseCategory.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(messages.EXPENSE_CATEGORY_ALREADY_EXISTS)
        return value.strip()
