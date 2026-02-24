from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from apps.group.models import Group, Person, GroupTransaction
from apps.group.serializers import (
    GroupCreateSerializer,
    PersonCreateSerializer,
    PersonDetailSerializer,
    GroupTransactionSerializer,
)
from apps.common.utils import first_error_message, success_response, error_response


class GroupCreateListView(ListCreateAPIView):
    """
    Create and list groups for logged-in user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GroupCreateSerializer

    def get_queryset(self):
        return Group.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        group = serializer.save()

        return success_response(
            message="Group created successfully",
            data=GroupCreateSerializer(group).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class GroupRetrieveView(APIView):
    """
    Retrieve a specific group with its details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        # Get summary for the group
        transactions = GroupTransaction.objects.filter(group=group)
        total_income = (
            transactions.filter(type="income").aggregate(total=Sum("amount"))["total"]
            or 0
        )
        total_expenses = (
            transactions.filter(type="expense").aggregate(total=Sum("amount"))["total"]
            or 0
        )
        balance = float(total_income) - float(total_expenses)

        # Member breakdown
        member_summary = []

        # Owner
        owner_name = " ".join(
            filter(None, [request.user.first_name, request.user.last_name])
        )
        if not owner_name.strip():
            owner_name = request.user.email

        owner_income = (
            transactions.filter(person__isnull=True, type="income").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        owner_expense = (
            transactions.filter(person__isnull=True, type="expense").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        member_summary.append(
            {
                "id": None,
                "user_id": request.user.id,
                "name": owner_name + " (Owner)",
                "total_income": owner_income,
                "total_expense": owner_expense,
                "balance": float(owner_income) - float(owner_expense),
            }
        )

        # People
        people = Person.objects.filter(group=group)
        for person in people:
            p_income = (
                transactions.filter(person=person, type="income").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )
            p_expense = (
                transactions.filter(person=person, type="expense").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

            member_summary.append(
                {
                    "id": person.id,
                    "name": person.name,
                    "total_income": p_income,
                    "total_expense": p_expense,
                    "balance": float(p_income) - float(p_expense),
                }
            )

        group_data = GroupCreateSerializer(group).data
        group_data["summary"] = {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
        }
        group_data["member_summary"] = member_summary

        return success_response(data=group_data)


class PersonCreateListView(ListCreateAPIView):
    """
    Create and list people in a specific group.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PersonCreateSerializer

    def get_queryset(self):
        group_id = self.kwargs.get("group_id")
        return Person.objects.filter(
            group_id=group_id, group__user=self.request.user
        ).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id")

        # Verify group exists and belongs to user
        try:
            Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        data = request.data.copy()
        data["group"] = group_id

        serializer = self.get_serializer(data=data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        person = serializer.save()

        return success_response(
            message="Person added to group successfully",
            data=PersonDetailSerializer(person).data,
        )

    def list(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id")

        # Verify group exists and belongs to user
        try:
            group = Group.objects.get(id=group_id, user=request.user)  # noqa: F841
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Add owner as a virtual person in the list
        owner_name = " ".join(
            filter(None, [request.user.first_name, request.user.last_name])
        )
        if not owner_name.strip():
            owner_name = request.user.email

        owner_data = {
            "id": None,
            "user_id": request.user.id,
            "name": owner_name + " (You)",
            "phone": str(getattr(request.user, "phone_number", "")),
            "email": request.user.email,
            "is_owner": True,
        }

        # Prepend owner to the list of people
        data = [owner_data] + serializer.data
        return success_response(data=data)


class PersonRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a person in a group.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PersonDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "person_id"

    def get_queryset(self):
        group_id = self.kwargs.get("group_id")
        return Person.objects.filter(group_id=group_id, group__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            person = self.get_object()
        except Person.DoesNotExist:
            return error_response(message="Person not found")

        serializer = self.get_serializer(person)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        try:
            person = self.get_object()
        except Person.DoesNotExist:
            return error_response(message="Person not found")

        # Only allow updating name
        data = request.data.copy()
        serializer = self.get_serializer(person, data=data, partial=True)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        person = serializer.save()

        return success_response(
            message="Person updated successfully",
            data=self.get_serializer(person).data,
        )

    def destroy(self, request, *args, **kwargs):
        try:
            person = self.get_object()
        except Person.DoesNotExist:
            return error_response(message="Person not found")

        person.delete()

        return success_response(message="Person deleted successfully")


class GroupTransactionCreateListView(ListCreateAPIView):
    """
    Create and list transactions for a specific group.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GroupTransactionSerializer

    def get_queryset(self):
        group_id = self.kwargs.get("group_id")
        return GroupTransaction.objects.filter(
            group_id=group_id, group__user=self.request.user
        ).order_by("-date")

    def create(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id")

        # Verify group exists and belongs to user
        try:
            group = Group.objects.get(id=group_id, user=request.user)  # noqa: F841
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        data = request.data.copy()
        data["group"] = group_id

        serializer = self.get_serializer(data=data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        transaction = serializer.save()

        return success_response(
            message="Group transaction created successfully",
            data=GroupTransactionSerializer(transaction).data,
        )

    def list(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id")

        # Verify group exists and belongs to user
        try:
            group = Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Calculate group totals
        total_income = (
            queryset.filter(type="income").aggregate(total=Sum("amount"))["total"] or 0
        )
        total_expenses = (
            queryset.filter(type="expense").aggregate(total=Sum("amount"))["total"] or 0
        )
        balance = float(total_income) - float(total_expenses)

        # Calculate per-member breakdown
        member_summary = []

        # 1. Owner (Logged-in User) breakdown
        owner_name = " ".join(
            filter(None, [request.user.first_name, request.user.last_name])
        )
        if not owner_name.strip():
            owner_name = request.user.email

        owner_income = (
            queryset.filter(person__isnull=True, type="income").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        owner_expense = (
            queryset.filter(person__isnull=True, type="expense").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        member_summary.append(
            {
                "id": None,
                "user_id": request.user.id,
                "name": owner_name + " (Owner)",
                "total_income": owner_income,
                "total_expense": owner_expense,
                "balance": float(owner_income) - float(owner_expense),
            }
        )

        # 2. People breakdown
        people = Person.objects.filter(group=group)
        for person in people:
            p_income = (
                queryset.filter(person=person, type="income").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )
            p_expense = (
                queryset.filter(person=person, type="expense").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

            member_summary.append(
                {
                    "id": person.id,
                    "name": person.name,
                    "total_income": p_income,
                    "total_expense": p_expense,
                    "balance": float(p_income) - float(p_expense),
                }
            )

        data = {
            "transactions": serializer.data,
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "balance": balance,
            },
            "member_summary": member_summary,
        }
        return success_response(data=data)


class GroupTransactionRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a group transaction.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GroupTransactionSerializer
    lookup_field = "id"
    lookup_url_kwarg = "transaction_id"

    def get_queryset(self):
        group_id = self.kwargs.get("group_id")
        return GroupTransaction.objects.filter(
            group_id=group_id, group__user=self.request.user
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            transaction = self.get_object()
        except GroupTransaction.DoesNotExist:
            return error_response(message="Transaction not found")

        serializer = self.get_serializer(transaction)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        try:
            transaction = self.get_object()
        except GroupTransaction.DoesNotExist:
            return error_response(message="Transaction not found")

        data = request.data.copy()
        # Prevent updating type
        if "type" in data:
            data.pop("type")

        serializer = self.get_serializer(transaction, data=data, partial=True)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        transaction = serializer.save()

        return success_response(
            message="Transaction updated successfully",
            data=self.get_serializer(transaction).data,
        )

    def destroy(self, request, *args, **kwargs):
        try:
            transaction = self.get_object()
        except GroupTransaction.DoesNotExist:
            return error_response(message="Transaction not found")

        transaction.delete()

        return success_response(message="Transaction deleted successfully")
