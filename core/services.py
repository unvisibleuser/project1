import logging

from django.conf import settings
from django.core.mail import EmailMessage
from google import genai

logger = logging.getLogger(__name__)

def get_gemini_client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_gemini_response(prompt: str) -> str:
    """Send the user's prompt to Gemini and return the text response."""
    client = get_gemini_client()
    result = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )

    text = getattr(result, 'text', None)
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def send_result_email(to_email: str, prompt: str, response_text: str) -> None:
    """Email the Gemini output to the logged-in (test) user."""
    subject = "Your Gemini response"
    body = (
        "Here is the response to your prompt:\n\n"
        f"Prompt:\n{prompt}\n\n"
        f"Response:\n{response_text}"
    )
    email = EmailMessage(subject=subject, body=body, to=[to_email])
    email.send(fail_silently=False)
