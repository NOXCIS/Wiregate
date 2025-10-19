"""
FastAPI LDAP Auth Router
Migrated from ldap_auth_api.py Flask blueprint
"""
from ldap3 import Server, Connection, SIMPLE, ALL
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..models.requests import LDAPSettings
from ..modules.DashboardConfig import DashboardConfig
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

# Create router
router = APIRouter()


@router.get('/getLDAPSettings', response_model=StandardResponse)
async def get_ldap_settings(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get LDAP settings (excluding sensitive data)"""
    settings = {}
    for key in ["enabled", "server", "port", "use_ssl", "domain", "bind_dn",
                "search_base", "search_filter", "attr_username", "require_group", "group_dn"]:
        settings[key] = DashboardConfig.GetConfig("LDAP", key)[1]
    
    return StandardResponse(status=True, data=settings)


@router.post('/saveLDAPSettings', response_model=StandardResponse)
async def save_ldap_settings(
    settings_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Save LDAP settings"""
    try:
        for key, value in settings_data.items():
            DashboardConfig.SetConfig("LDAP", key, value)
        return StandardResponse(status=True, message="Settings saved successfully")
    except Exception as e:
        return StandardResponse(status=False, message=f"Failed to save settings: {str(e)}")


@router.post('/testLDAPConnection', response_model=StandardResponse)
async def test_ldap_connection(
    test_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Test LDAP connection using provided settings"""
    try:
        # Build the LDAP URI from the settings
        uri = f"{'ldaps' if test_data['use_ssl'] else 'ldap'}://{test_data['server']}:{test_data['port']}"
        server = Server(uri, get_info=ALL)
        
        # Create a connection using ldap3
        conn = Connection(
            server,
            user=test_data['bind_dn'],
            password=test_data['bind_password'],
            authentication=SIMPLE
        )
        if not conn.bind():
            return StandardResponse(
                status=False,
                message=f"Bind failed: {conn.result}"
            )
        
        # Test search on the provided base DN
        search_successful = conn.search(
            test_data['search_base'],
            '(objectClass=*)',
            attributes=['*'],
            size_limit=1
        )
        if not search_successful:
            return StandardResponse(
                status=False,
                message=f"Search failed: {conn.result}"
            )
        
        return StandardResponse(status=True, message="Connection successful")
        
    except Exception as e:
        return StandardResponse(status=False, message=f"LDAP Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.unbind()

