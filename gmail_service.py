import os
import base64
import logging
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Scopes required: modify allows reading email and removing UNREAD label
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self):
        """Authenticates with the Gmail API via OAuth2."""
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Error refreshing credentials, re-authenticating: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"'{self.credentials_path}' tidak ditemukan! "
                        "Silakan unduh file credentials OAuth dari Google Cloud Console dan simpan di folder ini."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail service successfully authenticated.")
        return self.service

    def get_unread_emails(self, max_results: int = 10):
        """
        Retrieves unread emails from the inbox.
        Returns a list of dicts with email metadata and body content.
        """
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

        # Extract email body
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

        # Check direct body
        data = payload.get('body', {}).get('data')
        mime_type = payload.get('mimeType', '')

        if data:
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            if 'text/html' in mime_type:
                soup = BeautifulSoup(decoded, 'html.parser')
                text += soup.get_text(separator=' ')
            else:
                text += decoded

        # Check multipart parts
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

        # Clean excess whitespaces
        cleaned = " ".join(text.split())
        return cleaned

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

