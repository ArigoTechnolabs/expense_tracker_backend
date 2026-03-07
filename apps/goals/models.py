from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import BaseModel


class GoalCategory(BaseModel):
    """
    Categories for goals like New Bike, Vacation, etc.
    """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Goal Categories"


class Goal(BaseModel):
    """
    Represents a saving goal for a user.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="goals"
    )
    category = models.ForeignKey(
        GoalCategory, on_delete=models.CASCADE, related_name="goals"
    )
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expected_date = models.DateField()

    def clean(self):
        if self.expected_date and self.expected_date <= timezone.now().date():
            raise ValidationError(
                {"expected_date": "Expected date must be in the future."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def saved_amount(self):
        return self.entries.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def remaining_amount(self):
        saved = self.saved_amount
        remaining = self.target_amount - saved
        return max(0, remaining)

    def __str__(self):
        return f"{self.user.email} - {self.category.name} - {self.target_amount}"


class GoalEntry(BaseModel):
    """
    Manual entries for amount saved towards a goal.
    """

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="entries")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.goal.category.name} - {self.amount} on {self.date}"

    class Meta:
        ordering = ["-date", "-created_at"]
