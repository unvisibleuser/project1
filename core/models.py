from django.db import models
from django.conf import settings


# Create your models here.
class PromptLog(models.Model):
    """Stores every prompt a user submits, Gemini's response, and whether the email went out."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompt_logs',
    )
    prompt = models.TextField()
    response = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.created_at:%Y-%m-%d %H:%M}"