import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import render

from .models import PromptLog
from .serializers import PromptLogSerializer, PromptRequestSerializer
from .services import generate_gemini_response, send_user_gmail_email


logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def home(request):
    return render(request, 'home.html')


class GeneratePromptView(APIView):
    """POST prompt & recipient_email -> calls Gemini -> sends email via user's Gmail OAuth."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PromptRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data['prompt']
        recipient_email = serializer.validated_data['recipient_email']

        log = PromptLog.objects.create(
            user=request.user,
            prompt=prompt,
            recipient_email=recipient_email,
        )

        # 1. Call Gemini
        try:
            response_text = generate_gemini_response(prompt)
            log.response = response_text
            log.save(update_fields=['response'])
        except Exception as exc:
            logger.exception("Gemini generation failed")
            log.error = str(exc)
            log.save(update_fields=['error'])
            return Response(
                {"detail": "Failed to generate response.", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 2. Email the result via User's Gmail OAuth account
        try:
            send_user_gmail_email(
                user=request.user,
                to_email=recipient_email,
                prompt=prompt,
                response_text=response_text,
            )
            log.email_sent = True
            log.save(update_fields=['email_sent'])
        except Exception as exc:
            logger.exception("Gmail sending failed")
            log.error = str(exc)
            log.save(update_fields=['error'])
            data = PromptLogSerializer(log).data
            data['email_warning'] = str(exc)
            # 200 OK because generation succeeded, but email sending had an issue
            return Response(data, status=status.HTTP_200_OK)

        return Response(PromptLogSerializer(log).data, status=status.HTTP_201_CREATED)


class PromptHistoryView(APIView):
    """GET the current user's last 20 prompts/responses."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logs = PromptLog.objects.filter(user=request.user)[:20]
        return Response(PromptLogSerializer(logs, many=True).data)