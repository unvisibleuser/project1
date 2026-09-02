from django.contrib import admin
from .models import PromptLog
# Register your models here.

@admin.register(PromptLog)
class PromptLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'recipient_email', 'created_at', 'email_sent']
    list_filter = ['email_sent', 'created_at']
    search_fields = ['user__username', 'user__email', 'recipient_email', 'prompt']