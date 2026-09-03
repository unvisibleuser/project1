from rest_framework import serializers


class PromptRequestSerializer(serializers.Serializer):
    """Validates the incoming prompt text and recipient email from the user."""
    prompt = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=5000)
    recipient_email = serializers.EmailField(required=True, allow_blank=False)