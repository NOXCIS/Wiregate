import ldap
from flask import Blueprint, request
from wiregate.modules.DashboardConfig import DashboardConfig
from wiregate.modules.shared import ResponseObject

ldap_auth_blueprint = Blueprint('ldap_auth', __name__)


@ldap_auth_blueprint.get('/getLDAPSettings')
def API_GetLDAPSettings():
    """Get LDAP settings (excluding sensitive data)"""
    settings = {}
    for key in ["enabled", "server", "port", "use_ssl", "domain", "bind_dn",
                "search_base", "search_filter", "require_group", "group_dn"]:
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
        # Create temporary connection with provided settings
        uri = f"{'ldaps' if data['use_ssl'] else 'ldap'}://{data['server']}:{data['port']}"
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        if data['bind_dn'] and data['bind_password']:
            conn.simple_bind_s(data['bind_dn'], data['bind_password'])
            
        # Test search
        results = conn.search_s(
            data['search_base'],
            ldap.SCOPE_SUBTREE,
            '(objectClass=*)',
            [],
            limit=1
        )
        
        return ResponseObject(True, "Connection successful")
    except ldap.LDAPError as e:
        return ResponseObject(False, f"LDAP Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.unbind_s()
