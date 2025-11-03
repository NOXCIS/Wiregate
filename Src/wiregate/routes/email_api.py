"""
FastAPI Email Router
Migrated from email_api.py Flask blueprint
"""
from fastapi import APIRouter, Depends
from jinja2 import Template, Environment, select_autoescape

# Create Jinja2 environment with auto-escaping enabled for security
jinja_env = Environment(
    autoescape=select_autoescape(['html', 'xml'])
)
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..models.requests import EmailSend
from ..modules.Share.Email import EmailSender
from ..modules.Core import Configurations
from ..modules.DashboardConfig import DashboardConfig
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

# Create router
router = APIRouter()


@router.get('/email/ready', response_model=StandardResponse)
async def email_ready(
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Check if email server is ready"""
    email_sender = EmailSender(DashboardConfig)
    is_ready = email_sender.ready()
    return StandardResponse(status=is_ready)


@router.post('/email/send', response_model=StandardResponse)
async def email_send(
    email_data: EmailSend,
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Send email with optional peer configuration attachment"""
    # Default no attachment
    attachmentName = ""
    attachmentData = None
    body = email_data.Body or ""
    
    if email_data.ConfigurationName and email_data.Peer:
        if email_data.ConfigurationName in Configurations.keys():
            configuration = Configurations.get(email_data.ConfigurationName)
            fp, p = configuration.searchPeer(email_data.Peer)
            if fp:
                # Get the configuration file data from the peer
                download = p.downloadPeer()
                # Configure the attachment name and data
                attachmentName = download['fileName']
                attachmentData = download['file']
                # Process template if needed (with auto-escaping for security)
                template = jinja_env.from_string(body)
                body = template.render(peer=p.toJson(), configurationFile=download)
    
    # Send email
    email_sender = EmailSender(DashboardConfig)
    s, m = email_sender.send(
        email_data.Receiver,
        email_data.Subject or '',
        body,
        includeAttachment=email_data.IncludeAttachment or False,
        attachmentName=attachmentName,
        attachmentData=attachmentData
    )
    
    return StandardResponse(status=s, message=m)


@router.post('/email/previewBody', response_model=StandardResponse)
async def email_preview_body(
    preview_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Preview email body with template rendering"""
    body = preview_data.get('Body', '')
    
    if len(body) == 0:
        return StandardResponse(
            status=False,
            message="Nothing to preview"
        )
    
    if ("ConfigurationName" not in preview_data or 
        "Peer" not in preview_data or 
        preview_data.get('ConfigurationName') not in Configurations.keys()):
        return StandardResponse(
            status=False,
            message="Please specify configuration and peer"
        )
    
    configuration = Configurations.get(preview_data.get('ConfigurationName'))
    fp, p = configuration.searchPeer(preview_data.get('Peer'))
    
    if not fp:
        return StandardResponse(
            status=False,
            message="Peer does not exist"
        )
    
    try:
        # Use auto-escaping template environment for security
        template = jinja_env.from_string(body)
        download = p.downloadPeer()
        rendered_body = template.render(peer=p.toJson(), configurationFile=download)
        return StandardResponse(status=True, data=rendered_body)
    except Exception as e:
        return StandardResponse(status=False, message=str(e))

