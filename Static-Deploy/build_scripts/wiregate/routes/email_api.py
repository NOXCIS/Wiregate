from flask import (Blueprint, request, send_file)
import os
from uuid import uuid4
from jinja2 import Template

from ..modules.shared import (
    ResponseObject
)

from ..modules.Email import (
    EmailSender
)

from ..modules.Core import (
    Configurations,
    DashboardConfig
)

from ..modules.DashboardConfig import DashboardConfig

email_blueprint = Blueprint('email', __name__)




@email_blueprint.get('/email/ready')
def API_Email_Ready():
    email_sender = EmailSender(DashboardConfig)
    return ResponseObject(email_sender.ready())

@email_blueprint.post('/email/send')
def API_Email_Send():
    data = request.get_json()
    if "Receiver" not in data.keys():
        return ResponseObject(False, "Please at least specify receiver")
    
    # Default no attachment
    attachmentName = ""
    attachmentData = None
    
    if "ConfigurationName" in data.keys() and "Peer" in data.keys():
        if data.get('ConfigurationName') in Configurations.keys():
            configuration = Configurations.get(data.get('ConfigurationName'))
            fp, p = configuration.searchPeer(data.get('Peer'))
            if fp:
                # Get the configuration file data from the peer
                download = p.downloadPeer()
                # Configure the attachment name and data
                attachmentName = download['fileName']
                attachmentData = download['file']
                # You can also process a template if needed here
                template = Template(data.get('Body', ''))
                data['Body'] = template.render(peer=p.toJson(), configurationFile=download)
    
    # Now call the email sender passing the attachmentData directly
    email_sender = EmailSender(DashboardConfig)
    s, m = email_sender.send(
        data.get('Receiver'),
        data.get('Subject', ''),
        data.get('Body', ''),
        includeAttachment=data.get('IncludeAttachment', False),
        attachmentName=attachmentName,
        attachmentData=attachmentData
    )
    return ResponseObject(s, m)

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

