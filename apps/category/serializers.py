from rest_framework import serializers
from apps.category.models import Category, Transaction


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a category.
    """

    class Meta:
        model = Category
        fields = ("id", "name", "type", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        name = attrs.get("name")
        type_value = attrs.get("type")
        if Category.objects.filter(name__iexact=name, type=type_value).exists():
            raise serializers.ValidationError(
                "Category with this name and type already exists."
            )
        return attrs

    def validate_name(self, value):
        return value.strip()


class CategoryListQuerySerializer(serializers.Serializer):
    """
    Serializer for category list query parameters.
    """

    type = serializers.ChoiceField(
        choices=[("income", "Income"), ("expense", "Expense")], required=False
    )


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for transactions.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_type = serializers.CharField(source="category.type", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "user",
            "type",
            "category",
            "category_name",
            "category_type",
            "amount",
            "payment_type",
            "date",
            "note",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate(self, attrs):
        # Ensure category type matches transaction type
        category = attrs.get("category")
        transaction_type = attrs.get("type")
        if category and transaction_type and category.type != transaction_type:
            raise serializers.ValidationError(
                "Category type must match transaction type."
            )
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class FinancialSummarySerializer(serializers.Serializer):
    """
    Serializer for financial summary response.
    """

    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    filtered_from = serializers.DateField(required=False)
    filtered_to = serializers.DateField(required=False)


class DashboardSerializer(serializers.Serializer):
    """
    Serializer for the main dashboard view data.
    """

    summary = FinancialSummarySerializer()
    category_breakdown = serializers.ListField(child=serializers.DictField())
    goal_progress = serializers.ListField(child=serializers.DictField())
    recent_transactions = serializers.ListField(child=serializers.DictField())
    monthly_trend = serializers.ListField(child=serializers.DictField())


class EmiSerializer(serializers.ModelSerializer):
    """
    Serializer for EMI tracking.
    """

    class Meta:
        from apps.category.models import Emi

        model = Emi
        fields = (
            "id",
            "user",
            "name",
            "amount",
            "start_date",
            "end_date",
            "due_day",
            "reminder_time",
            "category",
            "is_active",
            "last_processed_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "last_processed_date",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        from django.utils import timezone

        today = timezone.now().date()

        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be after the start date."}
            )

        if end_date and end_date < today:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be in the past at creation/update."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TransactionListResponseSerializer(serializers.Serializer):
    """
    Serializer for the combined transaction list response.
    """

    transactions = serializers.ListField(child=serializers.DictField())
    summary = FinancialSummarySerializer()
