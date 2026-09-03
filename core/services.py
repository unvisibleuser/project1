import base64
import logging
from email.message import EmailMessage

from decouple import config
from django.conf import settings
from google import genai
from google.genai import types
import requests

logger = logging.getLogger(__name__)


def get_gemini_client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_gemini_response(prompt: str) -> str:

    client = get_gemini_client()
    system_prompt = config('SYSTEM_PROMPT')

    config_params = {
        'temperature': 0.7,
    }
    if system_prompt:
        config_params['system_instruction'] = system_prompt

    gen_config = types.GenerateContentConfig(**config_params)

    result = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=gen_config,
    )

    text = getattr(result, 'text', None)
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def get_user_google_credentials(user):
    """Retrieve user's Google OAuth2 access token from django-allauth SocialToken."""
    from allauth.socialaccount.models import SocialToken

    token_obj = SocialToken.objects.filter(account__user=user, account__provider='google').first()
    if not token_obj or not token_obj.token:
        raise ValueError("No active Google OAuth token found. Please sign in with Google.")

    return token_obj.token


def send_user_gmail_email(user, to_email: str, prompt: str, response_text: str) -> dict:
    """Send an email directly from the logged-in user's Gmail account via the Gmail REST API."""
    access_token = get_user_google_credentials(user)

    # Build MIME message
    msg = EmailMessage()
    msg.set_content(
        f"Here is the Gemini AI response to your prompt:\n\n"
        f"--- Prompt ---\n{prompt}\n\n"
        f"--- Response ---\n{response_text}\n"
    )
    msg['To'] = to_email
    msg['From'] = user.email or 'me'
    msg['Subject'] = "Your Gemini Response"

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    resp = requests.post(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        headers=headers,
        json={'raw': raw_message},
        timeout=15,
    )

    if not resp.ok:
        logger.error("Gmail API error (%s): %s", resp.status_code, resp.text)
        try:
            err_json = resp.json()
            err_msg = err_json.get('error', {}).get('message', resp.text)
        except Exception:
            err_msg = resp.text

        if resp.status_code in (401, 403):
            raise RuntimeError(f"Google authorization expired. Please log out and sign in with Google again to generate a new access token.")

        raise RuntimeError(f"Gmail API error ({resp.status_code}): {err_msg}")

    return resp.json()
