from rest_framework import serializers
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

    def get_person_name(self, obj):
        if obj.person:
            return obj.person.name
        # If no person, display transaction as user's own
        user = obj.user
        full_name = " ".join(
            filter(
                None, [getattr(user, "first_name", ""), getattr(user, "last_name", "")]
            )
        )
        return full_name if full_name.strip() else user.email

    class Meta:
        model = GroupTransaction
        fields = (
            "id",
            "group",
            "person",
            "person_name",
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
        person = attrs.get("person")

        # Ensure person belongs to the specified group when provided
        if person and group and person.group_id != group.id:
            raise serializers.ValidationError(
                "Person must belong to the specified group."
            )

        # It's valid for person to be omitted (meaning user's own transaction)
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
