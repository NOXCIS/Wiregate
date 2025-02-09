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
from . DashboardConfig import DashboardConfig   # Import from the correct module
import base64




class EmailSender:
    def __init__(self, DashboardConfig):
        self.smtp = None
        self.DashboardConfig = DashboardConfig
        if not os.path.exists('../attachments'):
            os.mkdir('../attachments')
        
    def Server(self):
        return self.DashboardConfig.GetConfig("Email", "server")[1]
    
    def Port(self):
        return self.DashboardConfig.GetConfig("Email", "port")[1]
    
    def Encryption(self):
        return self.DashboardConfig.GetConfig("Email", "encryption")[1]
    
    def Username(self):
        return self.DashboardConfig.GetConfig("Email", "username")[1]
    
    def Password(self):
        return self.DashboardConfig.GetConfig("Email", "email_password")[1]
    
    def SendFrom(self):
        return self.DashboardConfig.GetConfig("Email", "send_from")[1]

    def ready(self):
        print(self.Server())
        return len(self.Server()) > 0 and len(self.Port()) > 0 and len(self.Encryption()) > 0 and len(self.Username()) > 0 and len(self.Password()) > 0

    def send(self, receiver, subject, body, includeAttachment=False, attachmentName="", attachmentData=None):
        if self.ready():
            try:
                self.smtp = smtplib.SMTP(self.Server(), port=int(self.Port()))
                self.smtp.ehlo()
                if self.Encryption() == "STARTTLS":
                    self.smtp.starttls()
                self.smtp.login(self.Username(), self.Password())
                
                # Create message using the updated create_message method
                message, error = self.create_message(
                    receiver,
                    subject,
                    body,
                    from_address=self.Username(),
                    from_name=self.SendFrom(),
                    includeAttachment=includeAttachment,
                    attachmentName=attachmentName,
                    attachmentData=attachmentData
                )
                
                if error:
                    return False, error
                    
                self.smtp.sendmail(self.Username(), receiver, message.as_string())
                self.smtp.close()
                return True, None
            except Exception as e:
                return False, f"Send failed | Reason: {e}"
        return False, "SMTP not configured"
    
    def create_message(self, receiver, subject, body, from_address, from_name, includeAttachment=False, attachmentName="", attachmentData=None):
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = formataddr((Header(from_name).encode(), from_address))
        message["To"] = receiver
        message.attach(MIMEText(body, "plain"))
        
        # If the attachment is requested and we have the data available in memory
        if includeAttachment and attachmentName and attachmentData is not None:
            # Create a MIME attachment from the in-memory data
            attachment = MIMEBase("application", "octet-stream")
            # If the configuration is text, encode it as UTF-8 bytes
            attachment.set_payload(attachmentData.encode("utf-8"))
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", f"attachment; filename={attachmentName}")
            message.attach(attachment)
        
        return message, None


