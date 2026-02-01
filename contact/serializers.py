from rest_framework import serializers
from .models import ContactSubmission


class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "message"]

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()

    def validate_message(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()
