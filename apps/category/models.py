from django.db import models

from apps.common.models import BaseModel


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
