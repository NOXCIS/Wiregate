"""
Pydantic request models for FastAPI
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    totp: Optional[str] = Field(default=None)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Username contains invalid characters')
        return v
    
    @field_validator('totp')
    @classmethod
    def validate_totp(cls, v):
        if v is not None and not re.match(r'^[0-9]{6}$', v):
            raise ValueError('TOTP must be 6 digits')
        return v


class ConfigurationCreate(BaseModel):
    """Configuration creation request"""
    ConfigurationName: str = Field(..., min_length=1, max_length=100)
    Address: str
    ListenPort: int = Field(..., ge=1, le=65535)
    PrivateKey: str
    PreUp: Optional[str] = None
    PostUp: Optional[str] = None
    PreDown: Optional[str] = None
    PostDown: Optional[str] = None
    Protocol: Optional[str] = Field(default="wg")
    Backup: Optional[str] = None
    # AmneziaWG 1.5 CPS fields
    I1: Optional[str] = None
    I2: Optional[str] = None
    I3: Optional[str] = None
    I4: Optional[str] = None
    I5: Optional[str] = None
    
    @field_validator('Protocol')
    @classmethod
    def validate_protocol(cls, v):
        if v not in ['wg', 'awg']:
            raise ValueError('Protocol must be "wg" or "awg"')
        return v
    
    @field_validator('I1', 'I2', 'I3', 'I4', 'I5')
    @classmethod
    def validate_cps_format(cls, v):
        """Validate CPS format for I1-I5 fields"""
        if v is None or v == "":
            return v
        
        # Basic CPS format validation - matches tags <b hex>, <c>, <t>, <r length>, <rc length>, <rd length>
        import re
        
        # Pattern for individual tags
        hex_tag = r'<b\s+0x[0-9a-fA-F]+>'
        counter_tag = r'<c>'
        timestamp_tag = r'<t>'
        random_tag = r'<r\s+(\d+)>'
        random_ascii_tag = r'<rc\s+(\d+)>'  # Random ASCII characters (a-z, A-Z)
        random_digit_tag = r'<rd\s+(\d+)>'  # Random digits (0-9)
        
        # Combined pattern
        pattern = f'^({hex_tag}|{counter_tag}|{timestamp_tag}|{random_tag}|{random_ascii_tag}|{random_digit_tag})+$'
        
        if not re.match(pattern, v):
            raise ValueError(f'Invalid CPS format. Expected tags like <b 0xHEX>, <c>, <t>, <r LENGTH>, <rc LENGTH>, <rd LENGTH>')
        
        # Validate random length constraints for all variable-length tags
        all_length_tags = re.findall(r'<(?:r|rc|rd)\s+(\d+)>', v)
        for length_str in all_length_tags:
            length = int(length_str)
            if length <= 0 or length > 1000:
                raise ValueError(f'Random length {length} must be between 1 and 1000')
        
        return v


class PeerCreate(BaseModel):
    """Peer creation request"""
    name: Optional[str] = Field(default="", max_length=100)
    public_key: str
    private_key: Optional[str] = ""
    allowed_ips: List[str]
    DNS: Optional[str] = ""
    endpoint_allowed_ip: Optional[str] = ""
    preshared_key: Optional[str] = ""
    mtu: Optional[int] = Field(default=1420, ge=0, le=1460)
    keepalive: Optional[int] = Field(default=21, ge=0)
    bulkAdd: Optional[bool] = False
    bulkAddAmount: Optional[int] = Field(default=0, ge=0)
    preshared_key_bulkAdd: Optional[bool] = False


class PeerUpdate(BaseModel):
    """Peer update request"""
    id: str
    name: str
    private_key: str
    preshared_key: str
    DNS: str
    allowed_ip: str
    endpoint_allowed_ip: str
    mtu: int = Field(..., ge=0, le=1460)
    keepalive: int = Field(..., ge=0)


class PeerBulkAction(BaseModel):
    """Bulk peer action request"""
    peers: List[str] = Field(..., min_items=1)


class JobCreate(BaseModel):
    """Job creation request"""
    JobID: Optional[str] = None
    Configuration: str
    Peer: str
    Field: str
    Operator: Optional[str] = None
    Value: str
    CreationDate: Optional[str] = None
    ExpireDate: Optional[str] = None
    Action: str
    
    @field_validator('Field')
    @classmethod
    def validate_field(cls, v):
        if v not in ['total_receive', 'total_sent', 'total_data', 'date', 'weekly']:
            raise ValueError('Invalid field')
        return v
    
    @field_validator('Operator')
    @classmethod
    def validate_operator(cls, v):
        if v is not None and v not in ['eq', 'neq', 'lgt', 'lst']:
            raise ValueError('Invalid operator')
        return v
    
    @field_validator('Action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['allow', 'restrict', 'delete', 'rate_limit']:
            raise ValueError('Invalid action')
        return v
    
    @field_validator('Value')
    @classmethod
    def validate_value(cls, v, info):
        """Validate value based on field type"""
        # info.data contains the other field values in Pydantic v2
        field = info.data.get('Field') if hasattr(info, 'data') else None
        action = info.data.get('Action') if hasattr(info, 'data') else None
        
        # For rate_limit action, value should be JSON
        if action == 'rate_limit':
            try:
                import json
                rates = json.loads(v)
                if 'upload_rate' not in rates or 'download_rate' not in rates:
                    raise ValueError("Rate limit must specify upload_rate and download_rate")
            except json.JSONDecodeError:
                raise ValueError("Rate limit value must be valid JSON")
        
        return v


class ShareLinkCreate(BaseModel):
    """Share link creation request"""
    Configuration: str
    Peer: str
    ExpireDate: Optional[str] = None


class ShareLinkUpdate(BaseModel):
    """Share link update request"""
    ShareID: str
    ExpireDate: Optional[str] = None


class EmailSend(BaseModel):
    """Email send request"""
    Receiver: str
    Subject: Optional[str] = ""
    Body: Optional[str] = ""
    IncludeAttachment: Optional[bool] = False
    ConfigurationName: Optional[str] = None
    Peer: Optional[str] = None


class RateLimitSet(BaseModel):
    """Rate limit setting request"""
    interface: str
    peer_key: str
    upload_rate: int = Field(..., ge=0)
    download_rate: int = Field(..., ge=0)
    scheduler_type: str
    
    @field_validator('scheduler_type')
    @classmethod
    def validate_scheduler(cls, v):
        if v not in ['htb', 'hfsc', 'cake']:
            raise ValueError('Scheduler must be htb, hfsc, or cake')
        return v


class DashboardConfigUpdate(BaseModel):
    """Dashboard configuration update request"""
    section: str
    key: str
    value: Any


class APIKeyCreate(BaseModel):
    """API key creation request"""
    neverExpire: bool = False
    ExpiredAt: Optional[str] = None


class WelcomeFinish(BaseModel):
    """Welcome setup completion request"""
    username: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=8)
    repeatNewPassword: str = Field(..., min_length=8)
    
    @field_validator('repeatNewPassword')
    @classmethod
    def passwords_match(cls, v, info):
        if hasattr(info, 'data'):
            new_password = info.data.get('newPassword')
            if new_password and v != new_password:
                raise ValueError('Passwords do not match')
        return v


class TorConfigUpdate(BaseModel):
    """Tor configuration update request"""
    type: str = 'main'
    content: str
    plugin: Optional[str] = None
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        if v not in ['main', 'dns']:
            raise ValueError('Type must be main or dns')
        return v


class TorPluginUpdate(BaseModel):
    """Tor plugin update request"""
    plugin: str
    configType: str = 'main'
    useBridges: bool = True
    
    @field_validator('plugin')
    @classmethod
    def validate_plugin(cls, v):
        if v not in ['obfs4', 'webtunnel', 'snowflake']:
            raise ValueError('Invalid plugin')
        return v
    
    @field_validator('configType')
    @classmethod
    def validate_config_type(cls, v):
        if v not in ['main', 'dns']:
            raise ValueError('ConfigType must be main or dns')
        return v


class TorProcessControl(BaseModel):
    """Tor process control request"""
    action: str
    configType: str = 'main'
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['start', 'stop']:
            raise ValueError('Action must be start or stop')
        return v
    
    @field_validator('configType')
    @classmethod
    def validate_config_type(cls, v):
        if v not in ['main', 'dns']:
            raise ValueError('ConfigType must be main or dns')
        return v


class LDAPSettings(BaseModel):
    """LDAP settings update request"""
    enabled: Optional[bool] = None
    server: Optional[str] = None
    port: Optional[int] = Field(default=389, ge=1, le=65535)
    use_ssl: Optional[bool] = None
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    search_base: Optional[str] = None
    search_filter: Optional[str] = None
    require_group: Optional[bool] = None
    group_dn: Optional[str] = None
    attr_username: Optional[str] = None
    attr_email: Optional[str] = None
    attr_firstname: Optional[str] = None
    attr_lastname: Optional[str] = None
    domain: Optional[str] = None

