from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.group.models import Group, Person, GroupTransaction


class PersonDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving person details.
    """

    class Meta:
        model = Person
        fields = ("id", "group", "name", "email", "phone", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and listing groups.
    """

    people = PersonDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "photo", "people", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        return value.strip()

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class PersonCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and listing people in a group.
    """

    class Meta:
        model = Person
        fields = ("id", "group", "name", "email", "phone", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        return value.strip()

    def validate_phone(self, value):
        return value.strip()

    def validate(self, attrs):
        group = attrs.get("group")
        phone = attrs.get("phone")

        if not phone or not phone.strip():
            raise serializers.ValidationError({"phone": "Phone cannot be empty."})

        phone = phone.strip()

        # Check if a person with this phone already exists in this group
        # We check both active and soft-deleted persons to avoid IntegrityError
        if Person.objects.filter(group=group, phone__iexact=phone).exists():
            raise serializers.ValidationError(
                {
                    "phone": "A person with this phone number already exists in this group."
                }
            )

        attrs["phone"] = phone
        return attrs


class GroupTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for group transactions.
    """

    person_name = serializers.SerializerMethodField()
    to_person_name = serializers.SerializerMethodField()
    category_name = serializers.ReadOnlyField(source="category.name")

    def _get_owner_name(self, user):
        full_name = " ".join(
            filter(
                None, [getattr(user, "first_name", ""), getattr(user, "last_name", "")]
            )
        )
        name = full_name if full_name.strip() else user.email
        return name + " (Owner)"

    @extend_schema_field(serializers.CharField())
    def get_to_person_name(self, obj):
        if obj.to_person:
            return obj.to_person.name
        return self._get_owner_name(obj.user)

    class Meta:
        model = GroupTransaction
        fields = (
            "id",
            "group",
            "person",
            "person_name",
            "to_person",
            "to_person_name",
            "category",
            "category_name",
            "type",
            "amount",
            "payment_type",
            "date",
            "note",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def validate(self, attrs):
        group = attrs.get("group")
        person = attrs.get("person")  # From Person
        to_person = attrs.get("to_person")  # To Person
        type = attrs.get("type", "expense")
        amount = attrs.get("amount", 0)

        # Ensure person belongs to group
        if person and group and person.group_id != group.id:
            raise serializers.ValidationError("Person must belong to the group.")

        # Ensure to_person belongs to group
        if to_person and group and to_person.group_id != group.id:
            raise serializers.ValidationError("To-Person must belong to the group.")

        # Category is compulsory for expense, but optional for income
        category = attrs.get("category")
        if type == "expense" and not category:
            raise serializers.ValidationError(
                {"category": "Category is compulsory for expense transactions."}
            )

        # Validation for Income (Settlement)
        if type == "income":
            # Allow to_person to be null (represented as Owner/Logged-in User)
            if person == to_person:
                sender_label = person.name if person else "The Owner"
                raise serializers.ValidationError(
                    f"{sender_label} cannot send a settlement payment to themselves."
                )

            # Optional: Check if amount exceeds settlement needed
            # We need current summary for this
            from apps.group.utils import calculate_group_summary
            from apps.group.models import GroupTransaction

            transactions = GroupTransaction.objects.filter(group=group)
            summary = calculate_group_summary(
                group, transactions, self.context["request"].user
            )

            # Find the sender in member_summary
            sender_name = None
            if person:
                sender_name = person.name
            else:
                user = self.context["request"].user
                sender_name = " ".join(filter(None, [user.first_name, user.last_name]))
                if not sender_name.strip():
                    sender_name = user.email
                sender_name += " (Owner)"

            member = next(
                (m for m in summary["member_summary"] if m["name"] == sender_name), None
            )
            if member:
                net_balance = member.get("net_balance", 0)
                # If netBalance is negative, they owe money.
                # Settlement amount shouldn't exceed debt.
                if net_balance >= -0.01:
                    raise serializers.ValidationError(
                        f"{sender_name} does not owe any money to settle."
                    )

                debt_amount = abs(net_balance)
                if float(amount) > debt_amount + 0.01:
                    raise serializers.ValidationError(
                        f"Amount {amount} exceeds the required settlement of {debt_amount}."
                    )

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
