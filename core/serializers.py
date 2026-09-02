from rest_framework import serializers
from .models import PromptLog

class PromptRequestSerializer(serializers.Serializer):
    """Validates the incoming prompt text from the user."""
    prompt = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=5000)


class PromptLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptLog
        fields = ['id', 'prompt', 'response', 'email_sent', 'error', 'created_at']
        read_only_fields = fields