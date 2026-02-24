from django.urls import path
from apps.group import views

urlpatterns = [
    # Group endpoints
    path("", views.GroupCreateListView.as_view(), name="group-create-list"),
    path("<int:group_id>/", views.GroupRetrieveView.as_view(), name="group-retrieve"),
    # Person endpoints
    path(
        "<int:group_id>/people/",
        views.PersonCreateListView.as_view(),
        name="person-create-list",
    ),
    path(
        "<int:group_id>/people/<int:person_id>/",
        views.PersonRetrieveUpdateDeleteView.as_view(),
        name="person-detail",
    ),
    # Group Transaction endpoints
    path(
        "<int:group_id>/transactions/",
        views.GroupTransactionCreateListView.as_view(),
        name="group-transaction-create-list",
    ),
    path(
        "<int:group_id>/transactions/<int:transaction_id>/",
        views.GroupTransactionRetrieveUpdateDeleteView.as_view(),
        name="group-transaction-detail",
    ),
]
