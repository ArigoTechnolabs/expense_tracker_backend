from django.db.models import Sum


def calculate_group_summary(group, transactions, request_user):
    """
    Calculate group totals, member breakdown, and settlements.
    """
    from apps.group.models import Person

    # Total Group Expense is the sum of all 'expense' type transactions
    # 'income' type in groups represents settlements between members (P1 to P2)
    total_expenses_val = transactions.filter(type="expense").aggregate(
        total=Sum("amount")
    )["total"]
    total_expenses = (
        float(total_expenses_val) if total_expenses_val is not None else 0.0
    )

    # Balance is traditionally TotalIncome - TotalExpenses
    # In groups, we treat income as internal, but let's show external if any
    # Actually, as per user, income is P1 to P2
    total_income_val = transactions.filter(type="income").aggregate(
        total=Sum("amount")
    )["total"]
    total_income = float(total_income_val) if total_income_val is not None else 0.0

    member_summary = []

    # 1. Owner (Logged-in User) breakdown
    owner_name = " ".join(
        filter(None, [request_user.first_name, request_user.last_name])
    )
    if not owner_name.strip():
        owner_name = request_user.email
    full_owner_name = owner_name + " (Owner)"

    o_spent_val = transactions.filter(person__isnull=True, type="expense").aggregate(
        total=Sum("amount")
    )["total"]
    o_paid_settle_val = transactions.filter(
        person__isnull=True, type="income"
    ).aggregate(total=Sum("amount"))["total"]
    o_received_settle_val = transactions.filter(
        to_person__isnull=True, type="income"
    ).aggregate(total=Sum("amount"))["total"]

    o_spent = float(o_spent_val) if o_spent_val is not None else 0.0
    o_paid_settle = float(o_paid_settle_val) if o_paid_settle_val is not None else 0.0
    o_received_settle = (
        float(o_received_settle_val) if o_received_settle_val is not None else 0.0
    )

    member_summary.append(
        {
            "id": None,
            "user_id": request_user.id,
            "name": full_owner_name,
            "total_income": o_received_settle,  # They received this much from others
            "total_expense": o_spent,  # They spent this much for the group
            "paid_settlement": o_paid_settle,  # They paid this much to others
            "balance": o_spent - o_received_settle + o_paid_settle,  # Net contributed
        }
    )

    # 2. People breakdown
    people = Person.objects.filter(group=group)
    for person in people:
        p_spent_val = transactions.filter(person=person, type="expense").aggregate(
            total=Sum("amount")
        )["total"]
        p_paid_settle_val = transactions.filter(person=person, type="income").aggregate(
            total=Sum("amount")
        )["total"]
        p_received_settle_val = transactions.filter(
            to_person=person, type="income"
        ).aggregate(total=Sum("amount"))["total"]

        p_spent = float(p_spent_val) if p_spent_val is not None else 0.0
        p_paid_settle = (
            float(p_paid_settle_val) if p_paid_settle_val is not None else 0.0
        )
        p_received_settle = (
            float(p_received_settle_val) if p_received_settle_val is not None else 0.0
        )

        member_summary.append(
            {
                "id": person.id,
                "name": person.name,
                "total_income": p_received_settle,
                "total_expense": p_spent,
                "paid_settlement": p_paid_settle,
                "balance": p_spent - p_received_settle + p_paid_settle,
            }
        )

    # Settlement logic
    total_members = len(member_summary)
    settlements = []
    fair_share = 0.0

    if total_members > 0:
        # Each person's share of the group cost
        fair_share = total_expenses / total_members

        creditors = []
        debtors = []

        for m in member_summary:
            m["fair_share"] = round(fair_share, 2)

            # Net balance: Contribution - FairShare
            # Contribution is (Expenses Paid) + (Settlements Paid) - (Settlements Received)
            contribution = float(m["balance"])
            net_position = contribution - fair_share
            m["net_balance"] = round(net_position, 2)

            if net_position > 0.01:
                creditors.append([m["name"], net_position])
            elif net_position < -0.01:
                debtors.append([m["name"], abs(net_position)])

        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        c_idx, d_idx = 0, 0
        while c_idx < len(creditors) and d_idx < len(debtors):
            # creditors = [[name, amount], ...]
            # debtors = [[name, amount], ...]
            creditor_data = creditors[c_idx]
            debtor_data = debtors[d_idx]

            c_name = str(creditor_data[0])
            c_amount = float(creditor_data[1])
            d_name = str(debtor_data[0])
            d_amount = float(debtor_data[1])

            settle_amount = min(c_amount, d_amount)

            if settle_amount > 0.01:
                settlements.append(
                    {"from": d_name, "to": c_name, "amount": round(settle_amount, 2)}
                )

                c_amount = c_amount - settle_amount
                d_amount = d_amount - settle_amount

                # Update back in the list
                creditor_data[1] = c_amount
                debtor_data[1] = d_amount

            if c_amount < 0.01:
                c_idx += 1
            if d_amount < 0.01:
                d_idx += 1

    return {
        "summary": {
            "total_income": total_income,  # Total amount settled/transferred
            "total_expenses": total_expenses,  # Total group cost
            "balance": total_expenses,  # This can be used for UI
            "fair_share_per_person": round(fair_share, 2),
        },
        "member_summary": member_summary,
        "settlements": settlements,
    }
