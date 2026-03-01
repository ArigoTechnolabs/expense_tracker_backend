from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from apps.common.utils import first_error_message, success_response, error_response
from .models import Goal, GoalCategory, GoalEntry
from .serializers import GoalSerializer, GoalCategorySerializer, GoalEntrySerializer


class GoalCategoryListCreateView(ListCreateAPIView):
    """
    List and create goal categories.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalCategorySerializer
    queryset = GoalCategory.objects.all().order_by("name")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        category = serializer.save()
        return success_response(
            message="Goal category created successfully",
            data=self.get_serializer(category).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class GoalCategoryRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a goal category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalCategorySerializer
    queryset = GoalCategory.objects.all()
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        category = serializer.save()
        return success_response(
            message="Goal category updated successfully",
            data=self.get_serializer(category).data,
        )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()
        return success_response(message="Goal category deleted successfully")


class GoalListCreateView(ListCreateAPIView):
    """
    List and create goals for the logged-in user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        goal = serializer.save()
        return success_response(
            message="Goal created successfully", data=self.get_serializer(goal).data
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class GoalRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a goal.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        goal = self.get_object()
        serializer = self.get_serializer(goal)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        goal = self.get_object()
        serializer = self.get_serializer(goal, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        goal = serializer.save()
        return success_response(
            message="Goal updated successfully", data=self.get_serializer(goal).data
        )

    def destroy(self, request, *args, **kwargs):
        goal = self.get_object()
        goal.delete()
        return success_response(message="Goal deleted successfully")


class GoalEntryListCreateView(ListCreateAPIView):
    """
    List and create savings entries for goals.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalEntrySerializer

    def get_queryset(self):
        return GoalEntry.objects.filter(goal__user=self.request.user).order_by("-date")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        # Verify the goal belongs to the user
        goal = serializer.validated_data["goal"]
        if goal.user != request.user:
            return error_response(
                message="You do not have permission to add entries to this goal."
            )

        entry = serializer.save()
        return success_response(
            message="Savings entry added successfully",
            data=self.get_serializer(entry).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # Optional: filter entries by goal_id
        goal_id = request.query_params.get("goal_id")
        if goal_id:
            queryset = queryset.filter(goal_id=goal_id)

        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class GoalEntryRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a goal savings entry.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoalEntrySerializer
    lookup_field = "id"

    def get_queryset(self):
        return GoalEntry.objects.filter(goal__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        entry = self.get_object()
        serializer = self.get_serializer(entry)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        entry = self.get_object()
        serializer = self.get_serializer(entry, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(message=first_error_message(serializer.errors))

        # Verify goal ownership if goal is being updated
        if "goal" in serializer.validated_data:
            goal = serializer.validated_data["goal"]
            if goal.user != request.user:
                return error_response(
                    message="You do not have permission to use this goal."
                )

        entry = serializer.save()
        return success_response(
            message="Savings entry updated successfully",
            data=self.get_serializer(entry).data,
        )

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        entry.delete()
        return success_response(message="Savings entry deleted successfully")
