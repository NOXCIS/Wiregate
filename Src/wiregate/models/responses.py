"""
Pydantic response models for FastAPI
"""
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """Standard API response format matching existing ResponseObject"""
    status: bool = Field(default=True, description="Status of the operation")
    message: Optional[str] = Field(default=None, description="Message describing the result")
    data: Optional[Any] = Field(default=None, description="Response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": True,
                "message": "Operation successful",
                "data": {"key": "value"}
            }
        }


class ErrorResponse(BaseModel):
    """Error response format"""
    status: bool = Field(default=False, description="Always False for errors")
    message: str = Field(description="Error message")
    data: Optional[Any] = Field(default=None, description="Error details")
    error: Optional[str] = Field(default=None, description="Error type or code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": False,
                "message": "Operation failed",
                "data": None,
                "error": "ValidationError"
            }
        }


class ConfigurationResponse(BaseModel):
    """Configuration data response"""
    Status: bool
    Name: str
    PrivateKey: str
    PublicKey: str
    Address: str
    ListenPort: str
    PreUp: str
    PreDown: str
    PostUp: str
    PostDown: str
    SaveConfig: bool
    DataUsage: Dict[str, float]
    ConnectedPeers: int
    TotalPeers: int
    Protocol: str


class PeerResponse(BaseModel):
    """Peer data response"""
    id: str
    name: str
    private_key: str
    DNS: str
    endpoint_allowed_ip: str
    total_receive: float
    total_sent: float
    total_data: float
    endpoint: str
    status: str
    latest_handshake: str
    allowed_ip: str
    cumu_receive: float
    cumu_sent: float
    cumu_data: float
    traffic: List[Any]
    mtu: int
    keepalive: int
    remote_endpoint: str
    preshared_key: str
    upload_rate_limit: int
    download_rate_limit: int
    scheduler_type: str
    jobs: List[Any]
    ShareLink: List[Any]


class SystemStatusResponse(BaseModel):
    """System status response"""
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    process: Dict[str, Any]


class RateLimitInfo(BaseModel):
    """Rate limit information"""
    current_requests: int
    limit: int
    window: int
    reset_time: int
    remaining_requests: int
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None
    burst_requests: Optional[int] = None
    sliding_requests: Optional[int] = None


class AuthenticationResponse(BaseModel):
    """Authentication response"""
    status: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    welcome_session: Optional[bool] = None

