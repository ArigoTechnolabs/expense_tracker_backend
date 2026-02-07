from django.urls import path
from apps.category import views

urlpatterns = [
    path("", views.ExpenseCategoryCreateView.as_view(), name="category-create"),
    path(
        "<int:id>/",
        views.ExpenseCategoryRetrieveUpdateDeleteView.as_view(),
        name="expense-category-detail",
    ),
]
