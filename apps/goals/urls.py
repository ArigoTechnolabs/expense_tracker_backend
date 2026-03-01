from django.urls import path
from .views import (
    GoalCategoryListCreateView,
    GoalCategoryRetrieveUpdateDeleteView,
    GoalListCreateView,
    GoalRetrieveUpdateDeleteView,
    GoalEntryListCreateView,
    GoalEntryRetrieveUpdateDeleteView,
)

urlpatterns = [
    # Goal Categories
    path(
        "categories/",
        GoalCategoryListCreateView.as_view(),
        name="goal-category-list-create",
    ),
    path(
        "categories/<int:id>/",
        GoalCategoryRetrieveUpdateDeleteView.as_view(),
        name="goal-category-retrieve-update-delete",
    ),
    # Goals
    path("", GoalListCreateView.as_view(), name="goal-list-create"),
    path(
        "<int:id>/",
        GoalRetrieveUpdateDeleteView.as_view(),
        name="goal-retrieve-update-delete",
    ),
    # Goal Entries
    path("entries/", GoalEntryListCreateView.as_view(), name="goal-entry-list-create"),
    path(
        "entries/<int:id>/",
        GoalEntryRetrieveUpdateDeleteView.as_view(),
        name="goal-entry-retrieve-update-delete",
    ),
]
