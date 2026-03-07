from django.db.models import Sum


def calculate_group_summary(group, transactions, request_user):
    """
    Calculate group totals, member breakdown, and settlements based on partial splitting.
    """
    from apps.group.models import Person

    # Pre-fetch split_between to avoid N+1 issues
    transactions = transactions.prefetch_related("split_between")

    # 1. Basic totals (for display only)
    total_expenses_val = transactions.filter(type="expense").aggregate(
        total=Sum("amount")
    )["total"]
    total_expenses = (
        float(total_expenses_val) if total_expenses_val is not None else 0.0
    )

    total_income_val = transactions.filter(type="income").aggregate(
        total=Sum("amount")
    )["total"]
    total_income = float(total_income_val) if total_income_val is not None else 0.0

    # 2. Initialize tracking for all members
    people = Person.objects.filter(group=group)
    # member_stats stores {person_id_or_None: {stats}}
    member_stats = {}

    # Owner setup
    owner_name = " ".join(
        filter(None, [request_user.first_name, request_user.last_name])
    )
    if not owner_name.strip():
        owner_name = request_user.email
    full_owner_name = owner_name + " (Owner)"

    member_stats[None] = {
        "id": None,
        "name": full_owner_name,
        "spent": 0.0,
        "paid_settle": 0.0,
        "received_settle": 0.0,
        "must_pay_total": 0.0,
    }

    for p in people:
        member_stats[p.id] = {
            "id": p.id,
            "name": p.name,
            "spent": 0.0,
            "paid_settle": 0.0,
            "received_settle": 0.0,
            "must_pay_total": 0.0,
        }

    # 3. Process each transaction
    for t in transactions:
        amount = float(t.amount)
        if t.type == "expense":
            # Track who paid (Contribution)
            payer_id = t.person_id  # None if owner
            if payer_id in member_stats:
                member_stats[payer_id]["spent"] += amount

            # Determine participants for this transaction
            involved_ids = [p.id for p in t.split_between.all()]

            # If nothing is selected, the user wants to split with everyone
            if not involved_ids:
                participants = list(member_stats.keys())
            else:
                participants = involved_ids.copy()
                if t.include_owner:
                    participants.append(None)

            share = amount / len(participants) if participants else 0
            for p_id in participants:
                if p_id in member_stats:
                    member_stats[p_id]["must_pay_total"] += share

        elif t.type == "income":
            # Settlement from t.person to t.to_person
            from_id = t.person_id
            to_id = t.to_person_id
            if from_id in member_stats:
                member_stats[from_id]["paid_settle"] += amount
            if to_id in member_stats:
                member_stats[to_id]["received_settle"] += amount

    # 4. Finalize member breakdown
    member_summary = []
    for m_id, stats in member_stats.items():
        # Contribution is what they actually gave to the group: (Spent) + (Paid Settle) - (Received Settle)
        contribution = stats["spent"] + stats["paid_settle"] - stats["received_settle"]
        net_balance = contribution - stats["must_pay_total"]

        member_summary.append(
            {
                "id": stats["id"],
                "name": stats["name"],
                "total_income": round(stats["received_settle"], 2),
                "total_expense": round(stats["spent"], 2),
                "paid_settlement": round(stats["paid_settle"], 2),
                "fair_share": round(stats["must_pay_total"], 2),
                "net_balance": round(net_balance, 2),
                "balance": round(contribution, 2),  # Keeping for backward compatibility
            }
        )

    # 5. Settlement logic (Smallest number of payments)
    creditors = [
        [m["name"], m["net_balance"]] for m in member_summary if m["net_balance"] > 0.01
    ]
    debtors = [
        [m["name"], abs(m["net_balance"])]
        for m in member_summary
        if m["net_balance"] < -0.01
    ]

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    settlements = []
    c_idx, d_idx = 0, 0
    while c_idx < len(creditors) and d_idx < len(debtors):
        creditor_data = creditors[c_idx]
        debtor_data = debtors[d_idx]

        c_name, c_amount = creditor_data[0], float(creditor_data[1])
        d_name, d_amount = debtor_data[0], float(debtor_data[1])

        settle_amount = min(c_amount, d_amount)

        if settle_amount > 0.01:
            settlements.append(
                {"from": d_name, "to": c_name, "amount": round(settle_amount, 2)}
            )
            c_amount -= settle_amount
            d_amount -= settle_amount
            creditor_data[1] = c_amount
            debtor_data[1] = d_amount

        if c_amount < 0.01:
            c_idx += 1
        if d_amount < 0.01:
            d_idx += 1

    return {
        "summary": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": total_expenses,
            "fair_share_per_person": round(
                total_expenses / len(member_stats) if member_stats else 0, 2
            ),
        },
        "member_summary": member_summary,
        "settlements": settlements,
    }
