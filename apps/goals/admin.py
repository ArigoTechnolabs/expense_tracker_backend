from django.contrib import admin
from .models import Goal, GoalCategory, GoalEntry


@admin.register(GoalCategory)
class GoalCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "target_amount",
        "expected_date",
        "saved_amount",
        "remaining_amount",
    )
    list_filter = ("category", "user")
    search_fields = ("user__email", "category__name")


@admin.register(GoalEntry)
class GoalEntryAdmin(admin.ModelAdmin):
    list_display = ("goal", "amount", "date", "created_at")
    list_filter = ("goal__user", "date")
