from django.urls import path
from apps.category import views

urlpatterns = [
    path("", views.CategoryCreateView.as_view(), name="category-create"),
    path(
        "<int:id>/",
        views.CategoryRetrieveUpdateDeleteView.as_view(),
        name="category-detail",
    ),
    path(
        "transactions/",
        views.TransactionCreateView.as_view(),
        name="transaction-create",
    ),
    path(
        "transactions/<int:id>/",
        views.TransactionRetrieveUpdateDeleteView.as_view(),
        name="transaction-detail",
    ),
    path("summary/", views.FinancialSummaryView.as_view(), name="financial-summary"),
]
