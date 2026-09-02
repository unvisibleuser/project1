import base64
import logging
from email.message import EmailMessage

from django.conf import settings
from google import genai
import requests

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


def get_user_google_credentials(user):
    """Retrieve and refresh user's Google OAuth2 credentials from django-allauth SocialToken."""
    from allauth.socialaccount.models import SocialToken, SocialApp
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleAuthRequest

    token_obj = SocialToken.objects.filter(account__user=user, account__provider='google').first()
    if not token_obj:
        raise ValueError("No connected Google account found for this user. Please log in with Google.")

    client_id = None
    client_secret = None
    if token_obj.app:
        client_id = token_obj.app.client_id
        client_secret = token_obj.app.secret
    else:
        app_config = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP', {})
        client_id = app_config.get('client_id')
        client_secret = app_config.get('secret')

    creds = Credentials(
        token=token_obj.token,
        refresh_token=token_obj.token_secret,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=['https://www.googleapis.com/auth/gmail.send'],
    )

    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            token_obj.token = creds.token
            token_obj.save(update_fields=['token'])
        except Exception as exc:
            logger.warning("Could not refresh Google OAuth token: %s", exc)

    return creds


def send_user_gmail_email(user, to_email: str, prompt: str, response_text: str) -> dict:
    """Send an email directly from the logged-in user's Gmail account via the Gmail REST API."""
    creds = get_user_google_credentials(user)

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
        'Authorization': f'Bearer {creds.token}',
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
        raise RuntimeError(f"Gmail API error ({resp.status_code}): {err_msg}")

    return resp.json()
