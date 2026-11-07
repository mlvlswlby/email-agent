import os
import json
import base64
import logging
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self):
        """
        Authenticates with the Gmail API via OAuth2.
        
        Priority order for token:
          1. GMAIL_TOKEN_JSON environment variable (for cloud/server deployment)
          2. token.json file on disk (for local development)

        Priority order for credentials:
          1. GMAIL_CREDENTIALS_JSON environment variable (for cloud/server deployment)
          2. credentials.json file on disk (for local development)
        """
        creds = None

        # --- Load token ---
        token_env = os.environ.get("GMAIL_TOKEN_JSON")
        if token_env:
            try:
                token_data = json.loads(token_env)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                logger.info("Loaded Gmail token from environment variable GMAIL_TOKEN_JSON.")
            except Exception as e:
                logger.warning(f"Failed to parse GMAIL_TOKEN_JSON env var: {e}")
        elif os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            logger.info("Loaded Gmail token from token.json file.")

        # --- Refresh if expired ---
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Gmail token refreshed successfully.")
                # Persist refreshed token back to file if running locally
                if not os.environ.get("GMAIL_TOKEN_JSON") and os.path.exists(self.token_path):
                    with open(self.token_path, 'w') as f:
                        f.write(creds.to_json())
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")
                creds = None

        # --- Run OAuth flow if no valid credentials (local only) ---
        if not creds or not creds.valid:
            if os.environ.get("GMAIL_TOKEN_JSON"):
                raise RuntimeError(
                    "GMAIL_TOKEN_JSON is set but credentials are invalid or expired. "
                    "Please re-run the agent locally to generate a fresh token.json, "
                    "then update the GMAIL_TOKEN_JSON environment variable on Render."
                )

            # Load credentials.json (from env var or file)
            credentials_env = os.environ.get("GMAIL_CREDENTIALS_JSON")
            if credentials_env:
                import tempfile
                cred_data = json.loads(credentials_env)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    json.dump(cred_data, tmp)
                    tmp_path = tmp.name
                flow = InstalledAppFlow.from_client_secrets_file(tmp_path, SCOPES)
                os.unlink(tmp_path)
            elif os.path.exists(self.credentials_path):
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
            else:
                raise FileNotFoundError(
                    f"'{self.credentials_path}' tidak ditemukan! "
                    "Silakan unduh file credentials OAuth dari Google Cloud Console."
                )

            creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info("New OAuth token obtained and saved to token.json.")

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail service successfully authenticated.")
        return self.service

    def get_unread_emails(self, max_results: int = 10):
        """Retrieves unread emails from the inbox."""
        if not self.service:
            self.authenticate()

        results = self.service.users().messages().list(
            userId='me',
            q='is:unread in:inbox',
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        email_list = []

        for msg_summary in messages:
            msg_id = msg_summary['id']
            msg_data = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            parsed_email = self._parse_message(msg_data)
            if parsed_email:
                email_list.append(parsed_email)

        return email_list

    def _parse_message(self, msg_data: dict) -> dict:
        """Parses headers and extracts clean text body from an email message payload."""
        msg_id = msg_data.get('id')
        headers = msg_data.get('payload', {}).get('headers', [])

        subject = ""
        sender = ""
        date = ""

        for header in headers:
            name = header.get('name', '').lower()
            if name == 'subject':
                subject = header.get('value', '')
            elif name == 'from':
                sender = header.get('value', '')
            elif name == 'date':
                date = header.get('value', '')

        body = self._extract_body(msg_data.get('payload', {}))

        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body.strip()
        }

    def _extract_body(self, payload: dict) -> str:
        """Recursively extracts plain text or stripped HTML from email payload parts."""
        text = ""

        data = payload.get('body', {}).get('data')
        mime_type = payload.get('mimeType', '')

        if data:
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            if 'text/html' in mime_type:
                soup = BeautifulSoup(decoded, 'html.parser')
                text += soup.get_text(separator=' ')
            else:
                text += decoded

        parts = payload.get('parts', [])
        for part in parts:
            part_mime = part.get('mimeType', '')
            part_body = part.get('body', {})
            part_data = part_body.get('data')

            if part_data:
                decoded = base64.urlsafe_b64decode(part_data).decode('utf-8', errors='ignore')
                if part_mime == 'text/plain':
                    text += decoded + "\n"
                elif part_mime == 'text/html' and not text:
                    soup = BeautifulSoup(decoded, 'html.parser')
                    text += soup.get_text(separator=' ') + "\n"

            if 'parts' in part:
                text += self._extract_body(part) + "\n"

        return " ".join(text.split())

    def mark_as_read(self, msg_id: str):
        """Removes the UNREAD label from an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked email {msg_id} as read.")
        except Exception as e:
            logger.error(f"Failed to mark email {msg_id} as read: {e}")
