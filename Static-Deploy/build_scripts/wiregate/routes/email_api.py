from flask import (Blueprint, request, redirect, url_for, session)
import os
from uuid import uuid4
from jinja2 import Template

from ..modules.shared import (
    ResponseObject
)

from ..modules.Email import (
    EmailSenderFactory
)

from ..modules.Core import (
    Configurations
)

from ..modules.DashboardConfig import DashboardConfig

email_blueprint = Blueprint('email', __name__)

@email_blueprint.get('/email/ready')
def API_Email_Ready():
    try:
        email_sender = EmailSenderFactory.create(None)
        ready_status = email_sender.ready()
        return ResponseObject(ready_status)
    except Exception as e:
        # Optionally log the error here
        return ResponseObject(False, message=str(e))

@email_blueprint.post('/email/send')
def API_Email_Send():
    data = request.get_json()
    if "Receiver" not in data:
        return ResponseObject(False, "Please specify receiver")
    
    try:
        email_sender = EmailSenderFactory.create(None)
        success, message = email_sender.send(
            data['Receiver'],
            data.get('Subject', ''),
            data.get('Body', ''),
            data.get('IncludeAttachment', False),
            data.get('AttachmentName', '')
        )
        return ResponseObject(success, message)
    except Exception as e:
        return ResponseObject(False, str(e))

@email_blueprint.post('/email/previewBody')
def API_Email_PreviewBody():
    data = request.get_json()
    body = data.get('Body', '')
    if len(body) == 0:
        return ResponseObject(False, "Nothing to preview") 
    if ("ConfigurationName" not in data.keys() 
            or "Peer" not in data.keys() or data.get('ConfigurationName') not in Configurations.keys()):
        return ResponseObject(False, "Please specify configuration and peer")
    
    configuration = Configurations.get(data.get('ConfigurationName'))
    fp, p = configuration.searchPeer(data.get('Peer'))
    if not fp:
        return ResponseObject(False, "Peer does not exist")

    try:
        template = Template(body)
        download = p.downloadPeer()
        body = template.render(peer=p.toJson(), configurationFile=download)
        return ResponseObject(data=body)
    except Exception as e:
        return ResponseObject(False, message=str(e))

@email_blueprint.get('/email/oauth/<provider>/start')
def API_Email_OAuth_Start(provider):
    try:
        if provider == 'gmail':
            from ..modules.Email import GoogleEmailSender
            sender = GoogleEmailSender()
            auth_url = sender.get_authorization_url()
            session['oauth_state'] = auth_url['state']
            return ResponseObject(True, data={'authUrl': auth_url['url']})
        
        elif provider == 'outlook':
            from ..modules.Email import OutlookEmailSender
            sender = OutlookEmailSender()
            auth_url = sender.get_authorization_url()
            session['oauth_state'] = auth_url['state']
            return ResponseObject(True, data={'authUrl': auth_url['url']})
            
        return ResponseObject(False, f"Unsupported OAuth provider: {provider}")
    
    except Exception as e:
        return ResponseObject(False, str(e))

@email_blueprint.get('/email/oauth/<provider>/callback')
def API_Email_OAuth_Callback(provider):
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code or not state:
            return ResponseObject(False, "Missing authorization code or state")
            
        if state != session.get('oauth_state'):
            return ResponseObject(False, "Invalid state parameter")
            
        if provider == 'gmail':
            from ..modules.Email import GoogleEmailSender
            sender = GoogleEmailSender()
            sender.handle_oauth_callback(code)
            
        elif provider == 'outlook':
            from ..modules.Email import OutlookEmailSender
            sender = OutlookEmailSender()
            sender.handle_oauth_callback(code)
            
        return redirect(url_for('dashboard.settings'))
        
    except Exception as e:
        return ResponseObject(False, str(e))
