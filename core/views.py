import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import render

from .serializers import PromptRequestSerializer
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

        # 1. Call Gemini
        try:
            response_text = generate_gemini_response(prompt, user=request.user)
        except Exception as exc:
            logger.exception("Gemini generation failed")
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
            return Response(
                {
                    "prompt": prompt,
                    "response": response_text,
                    "recipient_email": recipient_email,
                    "email_sent": True,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Gmail sending failed")
            return Response(
                {
                    "prompt": prompt,
                    "response": response_text,
                    "recipient_email": recipient_email,
                    "email_sent": False,
                    "email_warning": str(exc),
                },
                status=status.HTTP_200_OK,
            )