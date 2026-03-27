from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from django.db.models import Sum
from apps.category.models import Category, Transaction
from apps.category.serializers import (
    CategoryCreateSerializer,
    TransactionSerializer,
    FinancialSummarySerializer,
    DashboardSerializer,
    TransactionListResponseSerializer,
)
from apps.common.utils import first_error_message, success_response, error_response
from apps.common import messages
from apps.goals.models import Goal
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiTypes,
)
import calendar


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    ),
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    ),
)
class CategoryCreateView(ListCreateAPIView):
    """
    Create a new category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategoryCreateSerializer
    queryset = Category.objects.all().order_by("id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        category = serializer.save()

        return success_response(
            message=messages.EXPENSE_CATEGORY_CREATED_SUCCESSFULLY,
            data=CategoryCreateSerializer(category).data,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter categories by type (income or expense)",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
                location=OpenApiParameter.QUERY,
            )
        ],
        description="List categories with optional type filter",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        type_filter = request.query_params.get("type")
        if type_filter in ["income", "expense"]:
            queryset = queryset.filter(type=type_filter)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class CategoryRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update (name only), or delete a category.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategoryCreateSerializer
    queryset = Category.objects.all()
    lookup_field = "id"
    http_method_names = ["get", "patch", "delete"]

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category)
        return success_response(data=serializer.data)

    @extend_schema(request=CategoryCreateSerializer, responses=CategoryCreateSerializer)
    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        # Only allow updating name
        if "name" not in request.data:
            return error_response(message="Only name field can be updated", status=400)

        # Check if new name conflicts with existing category of same type
        new_name = request.data.get("name").strip()
        if (
            Category.objects.filter(name__iexact=new_name, type=category.type)
            .exclude(id=category.id)
            .exists()
        ):
            return error_response(
                message="Category with this name already exists for this type",
                status=400,
            )

        category.name = new_name
        category.save()

        serializer = self.get_serializer(category)
        return success_response(
            message="Category name updated successfully",
            data=serializer.data,
        )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.delete()  # HARD DELETE

        return success_response(message=messages.EXPENSE_CATEGORY_DELETED_SUCCESSFULLY)


def get_month_date_range(request):
    """
    Helper function to determine the date range for filtering.
    Defaults to the current month if no parameters are provided.
    Logic:
    1. If start_date and end_date are provided, use them.
    2. If month and year are provided, use that month.
    3. If only year is provided, use the entire year.
    4. Otherwise, default to the current month.
    """
    today = timezone.now().date()
    start_date_param = request.query_params.get("start_date")
    end_date_param = request.query_params.get("end_date")
    month_param = request.query_params.get("month")
    year_param = request.query_params.get("year")

    # 1. Start and End Date Range
    if start_date_param and end_date_param:
        try:
            start_date = timezone.datetime.strptime(start_date_param, "%Y-%m-%d").date()
            end_date = timezone.datetime.strptime(end_date_param, "%Y-%m-%d").date()
            return start_date, end_date
        except (ValueError, TypeError):
            pass

    # Determine Year (default to current year)
    try:
        year = int(year_param) if year_param else today.year
    except (ValueError, TypeError):
        year = today.year

    # 2. Month and Year
    if month_param:
        try:
            month = int(month_param)
            if 1 <= month <= 12:
                last_day = calendar.monthrange(year, month)[1]
                start_date = today.replace(year=year, month=month, day=1)
                end_date = today.replace(year=year, month=month, day=last_day)
                return start_date, end_date
        except (ValueError, TypeError):
            pass

    # 3. Only Year
    if year_param and not month_param:
        start_date = today.replace(year=year, month=1, day=1)
        end_date = today.replace(year=year, month=12, day=31)
        return start_date, end_date

    # 4. Default: Current Month
    start_date = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = today.replace(day=last_day)
    return start_date, end_date


class TransactionCreateView(ListCreateAPIView):
    """
    Create and list transactions.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Base queryset for transactions, ordered by date descending.
        """
        return Transaction.objects.filter(user=self.request.user).order_by("-date")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        transaction = serializer.save()

        return success_response(
            message="Transaction created successfully",
            data=TransactionSerializer(transaction).data,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="month",
                description="Filter by month (1-12). Defaults to current month.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="year",
                description="Filter by year. Defaults to current year.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="start_date",
                description="Filter by start date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="end_date",
                description="Filter by end date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="category_id",
                description="Filter by category ID.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="type",
                description="Filter by transaction type (income or expense).",
                required=False,
                type=OpenApiTypes.STR,
                enum=["income", "expense"],
            ),
            OpenApiParameter(
                name="min_amount",
                description="Filter by minimum amount.",
                required=False,
                type=OpenApiTypes.DECIMAL,
            ),
            OpenApiParameter(
                name="max_amount",
                description="Filter by maximum amount.",
                required=False,
                type=OpenApiTypes.DECIMAL,
            ),
            OpenApiParameter(
                name="payment_type",
                description="Filter by payment type (e.g., cash, online).",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="search",
                description="Search in notes.",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: TransactionListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        from apps.group.models import GroupTransaction
        from apps.goals.models import GoalEntry
        from django.db.models import Q

        # 1. Determine Date Range (Default: Current Month)
        # This solves the requirement: "by default the transactions of the current month"
        start_date, end_date = get_month_date_range(request)

        # 2. Extract Other Filters
        category_id = request.query_params.get("category_id")
        transaction_type = request.query_params.get("type")
        min_amount = request.query_params.get("min_amount")
        max_amount = request.query_params.get("max_amount")
        payment_type = request.query_params.get("payment_type")
        search = request.query_params.get("search")

        # 3. Get and Filter Regular Transactions
        transactions = Transaction.objects.filter(
            user=self.request.user, date__range=[start_date, end_date]
        )

        # Apply additional filters to regular transactions
        if category_id:
            transactions = transactions.filter(category_id=category_id)
        if transaction_type:
            transactions = transactions.filter(type=transaction_type)
        if min_amount:
            transactions = transactions.filter(amount__gte=min_amount)
        if max_amount:
            transactions = transactions.filter(amount__lte=max_amount)
        if payment_type:
            transactions = transactions.filter(payment_type__icontains=payment_type)
        if search:
            transactions = transactions.filter(note__icontains=search)

        transactions = transactions.order_by("-date")
        transaction_serializer = TransactionSerializer(transactions, many=True)

        # 4. Get and Filter Group Transactions (Owner's perspective)
        # Note: Filtering by category_id on Group Transactions only if it's a regular category filter
        group_transactions = GroupTransaction.objects.filter(
            Q(user=self.request.user)
            & (Q(person__isnull=True) | Q(to_person__isnull=True)),
            date__range=[start_date, end_date],
        )

        if transaction_type:
            # We filter by display type later, but here we can pre-filter known certainties
            if transaction_type == "expense":
                group_transactions = group_transactions.filter(person__isnull=True)
            elif transaction_type == "income":
                group_transactions = group_transactions.filter(
                    to_person__isnull=True, type="income"
                )

        if min_amount:
            group_transactions = group_transactions.filter(amount__gte=min_amount)
        if max_amount:
            group_transactions = group_transactions.filter(amount__lte=max_amount)
        if payment_type:
            group_transactions = group_transactions.filter(
                payment_type__icontains=payment_type
            )
        if search:
            group_transactions = group_transactions.filter(note__icontains=search)
        if category_id:
            group_transactions = group_transactions.filter(category_id=category_id)

        group_transactions = group_transactions.order_by("-date")

        # Prepare combined data
        combined_data = []

        # Add regular transactions to combined data
        for item in transaction_serializer.data:
            item["is_group_transaction"] = False
            item["group_id"] = None
            item["group_name"] = None
            item["is_goal_entry"] = False
            item["goal_id"] = None
            combined_data.append(item)

        # Totals calculation (for the filtered period)
        total_income = float(
            transactions.filter(type="income").aggregate(total=Sum("amount"))["total"]
            or 0
        )
        total_expenses = float(
            transactions.filter(type="expense").aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # 5. Process Group Transactions
        for gt in group_transactions:
            # Determine type from Owner's perspective
            is_owner_payer = gt.person_id is None
            is_owner_receiver = gt.to_person_id is None

            display_type = None
            if is_owner_payer:
                display_type = "expense"
            elif is_owner_receiver and gt.type == "income":
                display_type = "income"

            if not display_type:
                continue

            combined_data.append(
                {
                    "id": gt.id,
                    "user": gt.user.id,
                    "type": display_type,
                    "category": gt.category.id if gt.category else None,
                    "category_name": gt.category.name
                    if gt.category
                    else "Group: " + gt.group.name,
                    "category_type": display_type,
                    "amount": str(gt.amount),
                    "payment_type": gt.payment_type,
                    "date": gt.date.strftime("%Y-%m-%d"),
                    "note": gt.note,
                    "is_group_transaction": True,
                    "group_id": gt.group.id,
                    "group_name": gt.group.name,
                    "is_goal_entry": False,
                    "goal_id": None,
                    "created_at": gt.created_at.isoformat(),
                    "updated_at": gt.updated_at.isoformat(),
                }
            )

            # Update summary totals
            if display_type == "income":
                total_income += float(gt.amount)
            else:
                total_expenses += float(gt.amount)

        # 6. Get and Filter Goal Entries
        # Goal entries are always 'expense' types (savings outflow)
        if not transaction_type or transaction_type == "expense":
            goal_entries = GoalEntry.objects.filter(
                goal__user=self.request.user, date__range=[start_date, end_date]
            )

            # Apply amount filters
            if min_amount:
                goal_entries = goal_entries.filter(amount__gte=min_amount)
            if max_amount:
                goal_entries = goal_entries.filter(amount__lte=max_amount)

            for ge in goal_entries:
                combined_data.append(
                    {
                        "id": ge.id,
                        "user": self.request.user.id,
                        "type": "expense",
                        "category": None,
                        "category_name": "Goal: " + ge.goal.category.name,
                        "category_type": "expense",
                        "amount": str(ge.amount),
                        "payment_type": "cash",
                        "date": ge.date.strftime("%Y-%m-%d"),
                        "note": f"Saved towards {ge.goal.category.name}",
                        "is_group_transaction": False,
                        "group_id": None,
                        "group_name": None,
                        "is_goal_entry": True,
                        "goal_id": ge.goal.id,
                        "created_at": ge.created_at.isoformat(),
                        "updated_at": ge.updated_at.isoformat(),
                    }
                )
                total_expenses += float(ge.amount)

        # Sort combined data by date (descending)
        combined_data.sort(key=lambda x: x["date"], reverse=True)

        balance = total_income - total_expenses

        data = {
            "transactions": combined_data,
            "summary": {
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "balance": round(balance, 2),
                "filtered_from": start_date.strftime("%Y-%m-%d"),
                "filtered_to": end_date.strftime("%Y-%m-%d"),
            },
        }
        return success_response(data=data)


class TransactionRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a transaction.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        transaction = self.get_object()
        serializer = self.get_serializer(transaction)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        transaction = self.get_object()
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
        transaction = self.get_object()
        transaction.delete()

        return success_response(message="Transaction deleted successfully")


class FinancialSummaryView(APIView):
    """
    Get financial summary for the user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FinancialSummarySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="month",
                description="Filter by month (1-12). Defaults to current month.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="year",
                description="Filter by year. Defaults to current year.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="start_date",
                description="Filter by start date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="end_date",
                description="Filter by end date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
        ]
    )
    def get(self, request):
        user = request.user
        from apps.group.models import GroupTransaction
        from apps.goals.models import GoalEntry

        # Determine Date Range (Default: Current Month)
        start_date, end_date = get_month_date_range(request)

        # 1. Regular Transactions
        reg_income = (
            Transaction.objects.filter(
                user=user, type="income", date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        reg_expense = (
            Transaction.objects.filter(
                user=user, type="expense", date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # 2. Group Transactions (Owner's Perspective)
        # Owner as Sender (outflow)
        grp_outflow = (
            GroupTransaction.objects.filter(
                user=user, person__isnull=True, date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Owner as Receiver (inflow - only for settlement/income type)
        grp_inflow = (
            GroupTransaction.objects.filter(
                user=user,
                to_person__isnull=True,
                type="income",
                date__range=[start_date, end_date],
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # 3. Goal Entries
        goal_expense = (
            GoalEntry.objects.filter(
                goal__user=user, date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        total_income = float(reg_income) + float(grp_inflow)
        total_expenses = float(reg_expense) + float(grp_outflow) + float(goal_expense)
        balance = total_income - total_expenses

        data = {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "balance": round(balance, 2),
            "filtered_from": start_date.strftime("%Y-%m-%d"),
            "filtered_to": end_date.strftime("%Y-%m-%d"),
        }

        return success_response(data=data)


class DashboardView(APIView):
    """
    Get a comprehensive dashboard summary for the user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="month",
                description="Filter by month (1-12). Defaults to current month.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="year",
                description="Filter by year. Defaults to current year.",
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="start_date",
                description="Filter by start date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="end_date",
                description="Filter by end date (YYYY-MM-DD).",
                required=False,
                type=OpenApiTypes.DATE,
            ),
        ]
    )
    def get(self, request):
        user = request.user
        from apps.group.models import GroupTransaction
        from apps.goals.models import GoalEntry

        # Determine Date Range (Default: Current Month)
        # Requirement: "dashboard, it should be by default the transactions of the current month"
        today = timezone.now().date()
        start_date, end_date = get_month_date_range(request)

        # 1. Summary (For the selected/default period)
        month_reg_income = (
            Transaction.objects.filter(
                user=user, type="income", date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        month_reg_expense = (
            Transaction.objects.filter(
                user=user, type="expense", date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        month_grp_outflow = (
            GroupTransaction.objects.filter(
                user=user, person__isnull=True, date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        month_grp_inflow = (
            GroupTransaction.objects.filter(
                user=user,
                to_person__isnull=True,
                type="income",
                date__range=[start_date, end_date],
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        month_goal_expense = (
            GoalEntry.objects.filter(
                goal__user=user, date__range=[start_date, end_date]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        total_income = float(month_reg_income) + float(month_grp_inflow)
        total_expenses = (
            float(month_reg_expense)
            + float(month_grp_outflow)
            + float(month_goal_expense)
        )
        balance = total_income - total_expenses

        # 2. Category Breakdown (Selected period expenses)
        category_breakdown = (
            Transaction.objects.filter(
                user=user, type="expense", date__range=[start_date, end_date]
            )
            .values("category__name")
            .annotate(amount=Sum("amount"))
            .order_by("-amount")
        )

        breakdown_total = sum(float(item["amount"]) for item in category_breakdown)

        formatted_breakdown = []
        for item in category_breakdown:
            amt = float(item["amount"])
            pct = round((amt / breakdown_total * 100), 2) if breakdown_total > 0 else 0
            formatted_breakdown.append(
                {
                    "category": item["category__name"],
                    "amount": amt,
                    "percentage": pct,
                }
            )

        # 3. Goal Progress (Top 3 active goals)
        goals = Goal.objects.filter(user=user).order_by("expected_date")[:3]
        goal_data = []
        for goal in goals:
            saved = float(goal.saved_amount)
            target = float(goal.target_amount)
            percentage = (saved / target * 100) if target > 0 else 0
            goal_data.append(
                {
                    "id": goal.id,
                    "name": goal.category.name,
                    "target": target,
                    "saved": saved,
                    "percentage": round(percentage, 2),
                }
            )

        # 4. Recent Transactions (Last 5 combined)
        recent_reg = Transaction.objects.filter(user=user).order_by("-date")[:5]
        recent_list = []
        for t in recent_reg:
            recent_list.append(
                {
                    "id": f"reg_{t.id}",
                    "type": t.type,
                    "category": t.category.name,
                    "amount": float(t.amount),
                    "date": t.date.strftime("%Y-%m-%d"),
                    "is_group": False,
                }
            )

        recent_grp = GroupTransaction.objects.filter(
            Q(user=user) & (Q(person__isnull=True) | Q(to_person__isnull=True))
        ).order_by("-date")[:5]
        for gt in recent_grp:
            # Type from owner perspective
            display_type = gt.type
            if gt.person is None:
                display_type = "expense"
            elif gt.to_person is None and gt.type == "income":
                display_type = "income"

            recent_list.append(
                {
                    "id": f"grp_{gt.id}",
                    "type": display_type,
                    "category": f"Group: {gt.group.name}",
                    "amount": float(gt.amount),
                    "date": gt.date.strftime("%Y-%m-%d"),
                    "is_group": True,
                    "is_goal_entry": False,
                }
            )

        recent_goal_entries = GoalEntry.objects.filter(goal__user=user).order_by(
            "-date"
        )[:5]
        for ge in recent_goal_entries:
            recent_list.append(
                {
                    "id": f"goal_{ge.id}",
                    "type": "expense",
                    "category": f"Goal: {ge.goal.category.name}",
                    "amount": float(ge.amount),
                    "date": ge.date.strftime("%Y-%m-%d"),
                    "is_group": False,
                    "is_goal_entry": True,
                }
            )

        for i in range(len(recent_list)):
            if "is_goal_entry" not in recent_list[i]:
                recent_list[i]["is_goal_entry"] = False

        recent_list.sort(key=lambda x: x["date"], reverse=True)
        recent_list = recent_list[:5]

        # 5. Monthly Trend (Last 6 Months)
        six_months_ago = today - timedelta(days=180)  # noqa: F841
        trends = []
        for i in range(5, -1, -1):
            temp_date = today - timedelta(days=i * 30)
            month_start = temp_date.replace(day=1)
            # Find last day of current month in loop
            if month_start.month == 12:
                next_month = month_start.replace(
                    year=month_start.year + 1, month=1, day=1
                )
            else:
                next_month = month_start.replace(month=month_start.month + 1, day=1)
            month_end = next_month - timedelta(days=1)

            inc = (
                Transaction.objects.filter(
                    user=user, type="income", date__range=[month_start, month_end]
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )
            exp = (
                Transaction.objects.filter(
                    user=user, type="expense", date__range=[month_start, month_end]
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )

            goal_exp = (
                GoalEntry.objects.filter(
                    goal__user=user, date__range=[month_start, month_end]
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )

            trends.append(
                {
                    "month": month_start.strftime("%b"),
                    "income": float(inc),
                    "expense": float(exp) + float(goal_exp),
                }
            )

        data = {
            "summary": {
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "balance": round(balance, 2),
                "filtered_from": start_date.strftime("%Y-%m-%d"),
                "filtered_to": end_date.strftime("%Y-%m-%d"),
            },
            "category_breakdown": formatted_breakdown,
            "goal_progress": goal_data,
            "recent_transactions": recent_list,
            "monthly_trend": trends,
        }

        return success_response(data=data)


class EmiCreateView(ListCreateAPIView):
    """
    Create and list EMIs.
    """

    permission_classes = [IsAuthenticated]
    from apps.category.serializers import EmiSerializer

    serializer_class = EmiSerializer

    def get_queryset(self):
        from apps.category.models import Emi

        return Emi.objects.filter(user=self.request.user).order_by("start_date")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        emi = serializer.save()
        return success_response(
            message="EMI created successfully",
            data=self.get_serializer(emi).data,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class EmiRetrieveUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an EMI.
    """

    permission_classes = [IsAuthenticated]
    from apps.category.serializers import EmiSerializer

    serializer_class = EmiSerializer
    lookup_field = "id"

    def get_queryset(self):
        from apps.category.models import Emi

        return Emi.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        emi = self.get_object()
        serializer = self.get_serializer(emi)
        return success_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        emi = self.get_object()
        serializer = self.get_serializer(emi, data=request.data, partial=True)
        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            return error_response(message=msg)

        emi = serializer.save()
        return success_response(
            message="EMI updated successfully",
            data=self.get_serializer(emi).data,
        )

    def destroy(self, request, *args, **kwargs):
        emi = self.get_object()
        emi.delete()
        return success_response(message="EMI deleted successfully")
