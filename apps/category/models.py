from django.db import models

from apps.common.models import BaseModel


class ExpenseCategory(BaseModel):
    """
    Stores expense categories such as Food, Bills, Travel, etc.
    """

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
