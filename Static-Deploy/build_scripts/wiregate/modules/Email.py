import os.path
import smtplib
from abc import ABC, abstractmethod
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import Optional, Tuple
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from msal import ConfidentialClientApplication
from . DashboardConfig import DashboardConfig   # Import from the correct module
import secrets

class BaseEmailSender(ABC):
    @abstractmethod
    def ready(self) -> bool:
        pass

    @abstractmethod
    def send(self, receiver: str, subject: str, body: str, 
             include_attachment: bool = False, 
             attachment_name: str = "") -> Tuple[bool, Optional[str]]:
        pass

    def create_message(self, receiver, subject, body, from_address, from_name, includeAttachment=False, attachmentName=""):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = formataddr((Header(from_name).encode(), from_address))
        message["To"] = receiver
        message.attach(MIMEText(body, "plain"))

        if includeAttachment and len(attachmentName) > 0:
            attachmentPath = os.path.join('../attachments', attachmentName)
            if os.path.exists(attachmentPath):
                attachment = MIMEBase("application", "octet-stream")
                with open(attachmentPath, 'rb') as f:
                    attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header("Content-Disposition", f"attachment; filename= {attachmentName}")
                message.attach(attachment)
                return message, None
            return None, "Attachment does not exist"
        return message, None

class SMTPEmailSender(BaseEmailSender):
    def __init__(self, provider='smtp'):
        if not os.path.exists('../attachments'):
            os.mkdir('../attachments')
        self.smtp = None
        self.provider = provider
    
    def ready(self):
        required_fields = ['username', 'email_password', 'send_from']
        if self.provider == 'smtp':
            required_fields.extend(['server', 'port', 'encryption'])
        return all(DashboardConfig.GetConfig("Email", field)[0] for field in required_fields)

    def send(self, receiver, subject, body, includeAttachment=False, attachmentName=""):
        if not self.ready():
            return False, "SMTP not configured"

        try:
            _, username = DashboardConfig.GetConfig("Email", "username")
            _, password = DashboardConfig.GetConfig("Email", "email_password")
            _, send_from = DashboardConfig.GetConfig("Email", "send_from")
            
            # Configure server based on provider
            if self.provider == 'gmail':
                server = 'smtp.gmail.com'
                port = 587
                encryption = 'STARTTLS'
            elif self.provider == 'outlook':
                server = 'smtp.office365.com'
                port = 587
                encryption = 'STARTTLS'
            elif self.provider == 'cloudflare':
                server = 'smtp.cloudflare.email'
                port = 587
                encryption = 'STARTTLS'
            else:  # Custom SMTP
                _, server = DashboardConfig.GetConfig("Email", "server")
                _, port = DashboardConfig.GetConfig("Email", "port")
                _, encryption = DashboardConfig.GetConfig("Email", "encryption")
                port = int(port)
            
            if encryption == "SSL/TLS":
                self.smtp = smtplib.SMTP_SSL(server, port=port)
            else:
                self.smtp = smtplib.SMTP(server, port=port)
                self.smtp.ehlo()
                if encryption == "STARTTLS":
                    self.smtp.starttls()
            
            self.smtp.login(username, password)
            
            message, error = self.create_message(
                receiver, subject, body, username, send_from, 
                includeAttachment, attachmentName
            )
            if error:
                self.smtp.close()
                return False, error

            self.smtp.sendmail(username, receiver, message.as_string())
            self.smtp.close()
            return True, None
            
        except Exception as e:
            if hasattr(self, 'smtp') and self.smtp:
                try:
                    self.smtp.close()
                except:
                    pass
            return False, f"Send failed | Reason: {e}"

class GoogleEmailSender(BaseEmailSender):
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self):
        self.credentials = None
        self._load_credentials()

    def _load_credentials(self):
        # Implementation for loading/refreshing Google OAuth credentials
        if os.path.exists('token.json'):
            self.credentials = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                self.credentials = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(self.credentials.to_json())

    def ready(self) -> bool:
        return self.credentials and self.credentials.valid

    def send(self, receiver: str, subject: str, body: str,
             include_attachment: bool = False, 
             attachment_name: str = "") -> Tuple[bool, Optional[str]]:
        try:
            service = build('gmail', 'v1', credentials=self.credentials)
            message = self._create_message(receiver, subject, body)
            service.users().messages().send(userId='me', body=message).execute()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_authorization_url(self):
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            self.SCOPES,
            redirect_uri='http://localhost:5000/api/email/oauth/gmail/callback'
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return {'url': auth_url, 'state': state}

    def handle_oauth_callback(self, code):
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            self.SCOPES,
            redirect_uri='http://localhost:5000/api/email/oauth/gmail/callback'
        )
        flow.fetch_token(code=code)
        self.credentials = flow.credentials
        with open('token.json', 'w') as token:
            token.write(self.credentials.to_json())

class OutlookEmailSender(BaseEmailSender):
    def __init__(self):
        self.app = ConfidentialClientApplication(
            client_id=DashboardConfig.GetConfig("Email", "ms_client_id")[1],
            client_credential=DashboardConfig.GetConfig("Email", "ms_client_secret")[1],
            authority="https://login.microsoftonline.com/common"
        )
        self._state = None  # Add state storage

    def ready(self) -> bool:
        # Check if Microsoft Graph API credentials are configured
        required_fields = ['ms_client_id', 'ms_client_secret', 'ms_tenant_id']
        return all(DashboardConfig.GetConfig("Email", field)[0] for field in required_fields)

    def send(self, receiver: str, subject: str, body: str,
             include_attachment: bool = False, 
             attachment_name: str = "") -> Tuple[bool, Optional[str]]:
        try:
            # Use Microsoft Graph API to send email
            result = self.app.acquire_token_silent(["https://graph.microsoft.com/.default"], 
                                                 account=None)
            if not result:
                result = self.app.acquire_token_for_client(
                    ["https://graph.microsoft.com/.default"])

            if "access_token" in result:
                # Send email using Microsoft Graph API
                endpoint = "https://graph.microsoft.com/v1.0/users/me/sendMail"
                email_msg = {
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "text", "content": body},
                        "toRecipients": [{"emailAddress": {"address": receiver}}]
                    }
                }
                response = requests.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {result['access_token']}"},
                    json=email_msg
                )
                response.raise_for_status()
                return True, None
            return False, "Failed to acquire token"
        except Exception as e:
            return False, str(e)

    def get_authorization_url(self):
        # Generate a random state parameter
        self._state = secrets.token_urlsafe(32)
        
        auth_url = self.app.get_authorization_request_url(
            scopes=['https://graph.microsoft.com/.default'],
            redirect_uri='http://localhost:5000/api/email/oauth/outlook/callback',
            state=self._state  # Pass the state parameter
        )
        return {'url': auth_url, 'state': self._state}

    def handle_oauth_callback(self, code):
        result = self.app.acquire_token_by_authorization_code(
            code,
            scopes=['https://graph.microsoft.com/.default'],
            redirect_uri='http://localhost:5000/api/email/oauth/outlook/callback'
        )
        if 'access_token' not in result:
            raise Exception("Failed to acquire token")

class CloudflareEmailSender(BaseEmailSender):
    def __init__(self):
        self.api_token = DashboardConfig.GetConfig("Email", "cf_api_token")[1]
        self.account_id = DashboardConfig.GetConfig("Email", "cf_account_id")[1]

    def ready(self) -> bool:
        required_fields = ['cf_api_token', 'cf_account_id', 'send_from']
        return all(DashboardConfig.GetConfig("Email", field)[0] for field in required_fields)

    def send(self, receiver: str, subject: str, body: str,
             include_attachment: bool = False, 
             attachment_name: str = "") -> Tuple[bool, Optional[str]]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "to": [receiver],
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
                "from": DashboardConfig.GetConfig("Email", "send_from")[1]
            }

            response = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/email/routing/send",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return True, None
        except Exception as e:
            return False, str(e)

class EmailSenderFactory:
    @staticmethod
    def create(_):  # Accept but ignore the config parameter
        status, provider = DashboardConfig.GetConfig("Email", "provider")
        if not status or not provider:
            # Default to SMTP if no provider is specified
            return SMTPEmailSender()
            
        if provider in ['smtp', 'gmail', 'outlook', 'cloudflare']:
            return SMTPEmailSender(provider)
        
        raise ValueError(f"Unsupported email provider: {provider}")

# Main class for backward compatibility
class EmailSender:
    def __init__(self, config=None):
        self.smtp = None
        self.config = config or DashboardConfig

    def ready(self) -> bool:
        """Check if email configuration is ready"""
        required_fields = ['provider', 'username', 'email_password', 'send_from']
        
        # Check if Email configuration exists
        if not self.config.GetConfig("Email", "provider")[0]:
            return False
            
        # Verify all required fields are present
        for field in required_fields:
            exists, value = self.config.GetConfig("Email", field)
            if not exists or not value:
                return False
                
        return True

    def create_message(self, receiver: str, subject: str, body: str, 
                      username: str, send_from: str, 
                      include_attachment: bool = False,
                      attachment_name: str = "") -> Tuple[Optional[MIMEMultipart], Optional[str]]:
        """Create email message with optional attachment"""
        try:
            message = MIMEMultipart()
            message['From'] = send_from
            message['To'] = receiver
            message['Subject'] = subject
            message.attach(MIMEText(body, 'html'))

            if include_attachment and attachment_name:
                attachment_path = os.path.join('./attachments', attachment_name)
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'r') as f:
                        part = MIMEApplication(f.read(), Name=attachment_name)
                        part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
                        message.attach(part)
                    os.remove(attachment_path)
                else:
                    return None, "Attachment file not found"

            return message, None
        except Exception as e:
            return None, str(e)

    def send(self, receiver: str, subject: str, body: str, 
             include_attachment: bool = False, 
             attachment_name: str = "") -> Tuple[bool, Optional[str]]:
        """Send email using configured provider"""
        if not self.ready():
            return False, "Email not configured"

        try:
            _, provider = self.config.GetConfig("Email", "provider")
            _, username = self.config.GetConfig("Email", "username")
            _, password = self.config.GetConfig("Email", "email_password")
            _, send_from = self.config.GetConfig("Email", "send_from")

            # Create message
            message, error = self.create_message(
                receiver, subject, body, username, send_from,
                include_attachment, attachment_name
            )
            if error:
                return False, error

            # Configure SMTP based on provider
            if provider == 'gmail':
                self.smtp = smtplib.SMTP('smtp.gmail.com', 587)
                self.smtp.starttls()
            elif provider == 'outlook':
                self.smtp = smtplib.SMTP('smtp.office365.com', 587)
                self.smtp.starttls()
            elif provider == 'cloudflare':
                self.smtp = smtplib.SMTP('smtp.cloudflare.email', 587)
                self.smtp.starttls()
            else:  # Custom SMTP
                _, server = self.config.GetConfig("Email", "server")
                _, port = self.config.GetConfig("Email", "port")
                _, encryption = self.config.GetConfig("Email", "encryption")
                
                if encryption == "SSL/TLS":
                    self.smtp = smtplib.SMTP_SSL(server, port=int(port))
                else:
                    self.smtp = smtplib.SMTP(server, port=int(port))
                    if encryption == "STARTTLS":
                        self.smtp.starttls()

            # Login and send
            self.smtp.login(username, password)
            self.smtp.sendmail(send_from, receiver, message.as_string())
            self.smtp.quit()
            return True, None

        except Exception as e:
            if self.smtp:
                try:
                    self.smtp.quit()
                except:
                    pass
            return False, f"Send failed: {str(e)}"