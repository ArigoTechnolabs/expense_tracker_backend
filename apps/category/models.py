from django.db import models

from apps.common.models import BaseModel
from django.utils import timezone


class Category(BaseModel):
    """
    Stores categories for both income and expenses such as Food, Bills, Travel, Salary, etc.
    """

    TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="expense")

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        unique_together = ("name", "type")


class Transaction(BaseModel):
    """
    Stores transactions for income and expenses.
    """

    TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="expense")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=50, default="cash")
    date = models.DateField()
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.type} - {self.category.name} - {self.amount}"

    class Meta:
        ordering = ["-date"]


class Emi(BaseModel):
    """
    Stores EMI details to track Equated Monthly Installments.
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(
        default=timezone.now, help_text="The date the EMI starts"
    )
    end_date = models.DateField(default=timezone.now, help_text="The date the EMI ends")
    due_day = models.PositiveSmallIntegerField(
        default=1, help_text="The day of the month the EMI is due (1-31)"
    )
    reminder_time = models.TimeField(help_text="Time of day to send the reminder")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    last_processed_date = models.DateField(
        null=True, blank=True, help_text="Last date the EMI expense was added"
    )
    last_notified_date = models.DateField(
        null=True, blank=True, help_text="Last date a reminder was sent"
    )

    def __str__(self):
        return f"{self.user.email} - {self.name} - {self.amount}"
