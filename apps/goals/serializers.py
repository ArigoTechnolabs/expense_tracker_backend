from rest_framework import serializers
from django.utils import timezone
from .models import Goal, GoalCategory, GoalEntry


class GoalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalCategory
        fields = ["id", "name", "created_at", "updated_at"]


class GoalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalEntry
        fields = ["id", "goal", "amount", "date", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GoalSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")
    saved_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Goal
        fields = [
            "id",
            "user",
            "category",
            "category_name",
            "target_amount",
            "expected_date",
            "saved_amount",
            "remaining_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_expected_date(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError("Expected date must be in the future.")
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
