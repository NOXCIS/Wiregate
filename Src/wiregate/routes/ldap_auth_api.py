from ldap3 import Server, Connection, SIMPLE, ALL, NTLM
from flask import Blueprint, request
from ..modules.DashboardConfig import DashboardConfig
from ..modules.App import ResponseObject

ldap_auth_blueprint = Blueprint('ldap_auth', __name__)


@ldap_auth_blueprint.get('/getLDAPSettings')
def API_GetLDAPSettings():
    """Get LDAP settings (excluding sensitive data)"""
    settings = {}
    for key in ["enabled", "server", "port", "use_ssl", "domain", "bind_dn",
                "search_base", "search_filter", "attr_username", "require_group", "group_dn"]:
        settings[key] = DashboardConfig.GetConfig("LDAP", key)[1]
    return ResponseObject(data=settings)

@ldap_auth_blueprint.post('/saveLDAPSettings')
def API_SaveLDAPSettings():
    """Save LDAP settings"""
    data = request.get_json()
    try:
        for key, value in data.items():
            DashboardConfig.SetConfig("LDAP", key, value)
        return ResponseObject(True, "Settings saved successfully")
    except Exception as e:
        return ResponseObject(False, f"Failed to save settings: {str(e)}")

@ldap_auth_blueprint.post('/testLDAPConnection')
def API_TestLDAPConnection():
    """Test LDAP connection using provided settings"""
    data = request.get_json()
    try:
        # Build the LDAP URI from the settings
        uri = f"{'ldaps' if data['use_ssl'] else 'ldap'}://{data['server']}:{data['port']}"
        server = Server(uri, get_info=ALL)
        
        # Create a connection using ldap3
        conn = Connection(
            server,
            user=data['bind_dn'],
            password=data['bind_password'],
            authentication=SIMPLE
        )
        if not conn.bind():
            return ResponseObject(False, f"Bind failed: {conn.result}")

        # Test search on the provided base DN
        search_successful = conn.search(
            data['search_base'],
            '(objectClass=*)',
            attributes=['*'],
            size_limit=1
        )
        if not search_successful:
            return ResponseObject(False, f"Search failed: {conn.result}")
        
        return ResponseObject(True, "Connection successful")
    except Exception as e:
        return ResponseObject(False, f"LDAP Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.unbind()
