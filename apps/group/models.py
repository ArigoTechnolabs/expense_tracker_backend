from django.db import models
from django.core.validators import RegexValidator
from apps.common.models import BaseModel
from apps.category.models import Category


class Group(BaseModel):
    """
    Groups created by users to manage shared expenses.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="created_groups"
    )
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="group_icons/", null=True, blank=True)

    def __str__(self):
        return f"{self.name} (Owner: {self.user.email})"

    class Meta:
        unique_together = ("user", "name")
        ordering = ["-created_at"]


class Person(BaseModel):
    """
    People added to a specific group for expense splitting.
    """

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=17, validators=[phone_regex])
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    class Meta:
        unique_together = ("group", "phone")
        ordering = ["-created_at"]


class GroupTransaction(BaseModel):
    """
    Transactions within a group where one person pays and it's split among group members.
    Similar to regular transactions but linked to a group and person.
    """

    TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    PAYMENT_TYPE_CHOICES = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("upi", "UPI"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="group_transactions"
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="transactions"
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="group_transactions",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="expense")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPE_CHOICES, default="cash"
    )
    date = models.DateField()
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        person_label = self.person.name if self.person else str(self.user.email)
        return f"{self.user.email} - {self.group.name} - {person_label} - {self.amount}"

    class Meta:
        ordering = ["-date"]
