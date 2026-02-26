from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.group.models import Group, Person, GroupTransaction
from apps.group.serializers import (
    GroupCreateSerializer,
    PersonCreateSerializer,
    PersonDetailSerializer,
    GroupTransactionSerializer,
)
from apps.common.utils import first_error_message, success_response, error_response
from apps.group.utils import calculate_group_summary


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
            data=GroupCreateSerializer(group, context={"request": request}).data,
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

    @extend_schema(
        responses={200: GroupCreateSerializer},
        description="Retrieve a specific group with its summary and member breakdown.",
    )
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        # Get transactions for the group
        from apps.group.models import GroupTransaction

        transactions = GroupTransaction.objects.filter(group=group)

        # Get summary, member breakdown and settlements using utility
        summary_data = calculate_group_summary(group, transactions, request.user)

        group_data = GroupCreateSerializer(group, context={"request": request}).data
        group_data.update(summary_data)

        return success_response(data=group_data)

        return success_response(data=group_data)

    @extend_schema(
        request=GroupCreateSerializer,
        responses={200: GroupCreateSerializer},
        description="Update group name or photo. Send only the fields you wish to change.",
    )
    def patch(self, request, group_id):
        """
        Update group name or photo.
        """
        try:
            group = Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        serializer = GroupCreateSerializer(
            group, data=request.data, partial=True, context={"request": request}
        )

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        group = serializer.save()

        # Re-use GET logic or return a simple success, returning the new group data with URL
        return success_response(
            message="Group updated successfully",
            data=GroupCreateSerializer(group, context={"request": request}).data,
        )

    @extend_schema(
        responses={204: None},
        description="Delete a group and all its associated data (Member/Persons and Transactions).",
    )
    def delete(self, request, group_id):
        """
        Delete group and all associated transactions/people (CASCADE).
        """
        try:
            group = Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        # Cascade delete is handled by the model ForeignKey relationships
        group.delete()

        return success_response(message="Group deleted successfully")


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

    @extend_schema(
        request=PersonCreateSerializer(many=True),
        responses={201: PersonDetailSerializer(many=True)},
        description="Add multiple people to a group. Accepts an array of person objects.",
    )
    def create(self, request, *args, **kwargs):
        group_id = kwargs.get("group_id")

        # Verify group exists and belongs to user
        try:
            Group.objects.get(id=group_id, user=request.user)
        except Group.DoesNotExist:
            return error_response(message="Group not found")

        # Support both single object and list of objects
        is_many = isinstance(request.data, list)

        if is_many:
            data = []
            for item in request.data:
                if isinstance(item, dict):
                    item_copy = item.copy()
                    item_copy["group"] = group_id
                    data.append(item_copy)
                else:
                    return error_response(message="Invalid data format in list")
        else:
            data = request.data.copy()
            data["group"] = group_id

        serializer = self.get_serializer(data=data, many=is_many)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        person_or_people = serializer.save()

        return success_response(
            message=(
                "People added to group successfully"
                if is_many
                else "Person added to group successfully"
            ),
            data=PersonDetailSerializer(person_or_people, many=is_many).data,
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

        # Calculate summary, member breakdown and settlements
        summary_data = calculate_group_summary(group, queryset, request.user)

        data = {"transactions": serializer.data, **summary_data}
        return success_response(data=data)
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
