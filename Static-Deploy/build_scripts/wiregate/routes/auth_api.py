
import hashlib
import bcrypt
import pyotp
from datetime import datetime
import ldap
from flask import Flask, Blueprint, request, session, make_response, jsonify
from ..modules.DashboardConfig import DashboardConfig
from ..modules.shared import ResponseObject
from ..modules.Core import AllDashboardLogger, APP_PREFIX
from ..modules.shared import app


auth_blueprint = Blueprint('auth', __name__)

@app.before_request
def auth_req():
    if request.method.lower() == 'options':
        return ResponseObject(True)

    DashboardConfig.APIAccessed = False
    if "api" in request.path:
        if str(request.method) == "GET":
            AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message=str(request.args))
        elif str(request.method) == "POST":
            content_type = request.headers.get('Content-Type', '')
            try:
                # Attempt to parse the JSON body of the request
                body = request.get_json()
                if body is None:
                    # If get_json() returns None, the body is empty or not JSON
                    raise ValueError("Empty or invalid JSON body")
                body_repr = str(body)
            except Exception as e:
                # If parsing fails, check if Content-Type is multipart/form-data
                if 'multipart/form-data' in content_type:
                    try:
                        # Attempt to parse multipart/form-data
                        # This will not parse the body but ensures it's multipart
                        _ = request.form  # Accessing form to trigger parsing
                        body_repr = "multipart/form-data"
                    except Exception:
                        # If parsing multipart fails, respond with 415
                        response = make_response(jsonify({
                            "status": False,
                            "message": "Invalid multipart/form-data body",
                            "data": None
                        }), 415)
                        return response
                else:
                    # If Content-Type is neither JSON nor multipart/form-data, respond with 415
                    response = make_response(jsonify({
                        "status": False,
                        "message": "Unsupported Media Type. Only application/json and multipart/form-data are supported.",
                        "data": None
                    }), 415)
                    return response
            # Log the details of the POST request, including query parameters and body
            AllDashboardLogger.log(
                str(request.url),
                str(request.remote_addr),
                Message=f"Request Args: {str(request.args)} Body: {body_repr}"
            )

    authenticationRequired = DashboardConfig.GetConfig("Server", "auth_req")[1]
    d = request.headers
    if authenticationRequired:
        apiKey = d.get('wg-dashboard-apikey')
        apiKeyEnabled = DashboardConfig.GetConfig("Server", "dashboard_api_key")[1]

        def constant_time_compare(val1: str, val2: str) -> bool:
            """
            Compare two strings in constant time to prevent timing attacks.
            """
            if len(val1) != len(val2):
                return False
            result = 0
            for x, y in zip(val1.encode(), val2.encode()):
                result |= x ^ y
            return result == 0
        
        def verify_api_key(provided_key: str, valid_keys: list) -> bool:
            """
            Verify API key in constant time to prevent timing attacks.
            Returns True if the key is valid, False otherwise.
            """
            if not provided_key or not valid_keys:
                return False
                
            # Use constant time comparison for each key
            result = False
            for valid_key in valid_keys:
                # Using OR operation to maintain constant time
                result |= constant_time_compare(provided_key, valid_key.Key)
            return result

        if apiKey is not None and len(apiKey) > 0 and apiKeyEnabled:
            apiKeyExist = verify_api_key(apiKey, DashboardConfig.DashboardAPIKeys)
            
            AllDashboardLogger.log(str(request.url), str(request.remote_addr),
                               Message=f"API Key Access: {('true' if apiKeyExist else 'false')} - Key: {apiKey}")
            if not apiKeyExist:
                DashboardConfig.APIAccessed = False
                response = Flask.make_response(app, {
                    "status": False,
                    "message": "API Key does not exist",
                    "data": None
                })
                response.content_type = "application/json"
                response.status_code = 401
                return response
            DashboardConfig.APIAccessed = True
        else:
            DashboardConfig.APIAccessed = False
            if ('/static/' not in request.path and "username" not in session
                    and (f"{(APP_PREFIX if len(APP_PREFIX) > 0 else '')}/" != request.path
                         and f"{(APP_PREFIX if len(APP_PREFIX) > 0 else '')}" != request.path)
                    and "validateAuthentication" not in request.path and "authenticate" not in request.path
                    and "getDashboardConfiguration" not in request.path and "getDashboardTheme" not in request.path
                    and "getDashboardVersion" not in request.path
                    and "sharePeer/get" not in request.path
                    and "isTotpEnabled" not in request.path
                    and "locale" not in request.path
            ):
                response = Flask.make_response(app, {
                    "status": False,
                    "message": "Unauthorized access.",
                    "data": None
                })
                response.content_type = "application/json"
                response.status_code = 401
                return response


@auth_blueprint.route('/handshake', methods=["GET", "OPTIONS"])
def API_Handshake():
    return ResponseObject(True)


@auth_blueprint.get('/validateAuthentication')
def API_ValidateAuthentication():
    token = request.cookies.get("authToken")
    if DashboardConfig.GetConfig("Server", "auth_req")[1]:
        if token is None or token == "" or "username" not in session or session["username"] != token:
            return ResponseObject(False, "Invalid authentication.")
    return ResponseObject(True)


@auth_blueprint.get('/requireAuthentication')
def API_RequireAuthentication():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "auth_req")[1])


def authenticate_ldap(username, password):
    """
    Authenticate user against LDAP server
    Returns (success, user_data, error_message)
    """
    if not DashboardConfig.GetConfig("LDAP", "enabled")[1]:
        return False, None, "LDAP authentication not enabled"

    try:
        # Initialize LDAP connection
        ldap_server = DashboardConfig.GetConfig("LDAP", "server")[1]
        ldap_port = DashboardConfig.GetConfig("LDAP", "port")[1]
        use_ssl = DashboardConfig.GetConfig("LDAP", "use_ssl")[1]
        
        uri = f"{'ldaps' if use_ssl else 'ldap'}://{ldap_server}:{ldap_port}"
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        # Bind with service account if provided
        bind_dn = DashboardConfig.GetConfig("LDAP", "bind_dn")[1]
        bind_password = DashboardConfig.GetConfig("LDAP", "bind_password")[1]
        
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        
        # Search for user
        search_base = DashboardConfig.GetConfig("LDAP", "search_base")[1]
        search_filter = DashboardConfig.GetConfig("LDAP", "search_filter")[1]
        
        # Replace %s with actual username
        search_filter = search_filter % username
        
        # Search for user
        results = conn.search_s(
            search_base,
            ldap.SCOPE_SUBTREE,
            search_filter,
            ['dn', 'mail', 'givenName', 'sn']
        )
        
        if not results:
            return False, None, "User not found"
            
        user_dn = results[0][0]
        user_attrs = results[0][1]
        
        # Verify group membership if required
        if DashboardConfig.GetConfig("LDAP", "require_group")[1]:
            group_dn = DashboardConfig.GetConfig("LDAP", "group_dn")[1]
            group_filter = f"(&(objectClass=group)(member={user_dn}))"
            group_results = conn.search_s(
                group_dn,
                ldap.SCOPE_SUBTREE,
                group_filter
            )
            if not group_results:
                return False, None, "User not in required group"
        
        # Authenticate user
        try:
            conn.simple_bind_s(user_dn, password)
        except ldap.INVALID_CREDENTIALS:
            return False, None, "Invalid credentials"
            
        # Get user attributes
        user_data = {
            "username": username,
            "email": user_attrs.get('mail', [b''])[0].decode('utf-8'),
            "firstname": user_attrs.get('givenName', [b''])[0].decode('utf-8'),
            "lastname": user_attrs.get('sn', [b''])[0].decode('utf-8')
        }
        
        return True, user_data, None
        
    except ldap.LDAPError as e:
        return False, None, f"LDAP Error: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.unbind_s()

@auth_blueprint.post('/authenticate')
def API_AuthenticateLogin():
    data = request.get_json()
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        return ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])

    # Check if LDAP is enabled
    ldap_enabled = DashboardConfig.GetConfig("LDAP", "enabled")[1]
    
    if ldap_enabled:
        success, user_data, error = authenticate_ldap(data['username'], data['password'])
        if not success:
            AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                                 Message=f"LDAP Login failed: {data['username']} - {error}")
            return ResponseObject(False, error)
            
        # LDAP authentication successful
        authToken = hashlib.sha256(f"{data['username']}{datetime.now()}".encode()).hexdigest()
        session['username'] = authToken
        session['user_data'] = user_data  # Store user data in session
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        resp.set_cookie("authToken", authToken)
        session.permanent = True
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                             Message=f"LDAP Login success: {data['username']}")
        return resp
        
    # Continue with existing local authentication if LDAP is not enabled
    valid = bcrypt.checkpw(data['password'].encode("utf-8"),
                           DashboardConfig.GetConfig("Account", "password")[1].encode("utf-8"))
    totpEnabled = DashboardConfig.GetConfig("Account", "enable_totp")[1]
    totpValid = False
    if totpEnabled:
        totpValid = pyotp.TOTP(DashboardConfig.GetConfig("Account", "totp_key")[1]).now() == data['totp']

    if (valid
            and data['username'] == DashboardConfig.GetConfig("Account", "username")[1]
            and ((totpEnabled and totpValid) or not totpEnabled)
    ):
        authToken = hashlib.sha256(f"{data['username']}{datetime.now()}".encode()).hexdigest()
        session['username'] = authToken
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        resp.set_cookie("authToken", authToken)
        session.permanent = True
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message=f"Login success: {data['username']}")
        return resp
    AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message=f"Login failed: {data['username']}")
    if totpEnabled:
        return ResponseObject(False, "Sorry, your username, password or OTP is incorrect.")
    else:
        return ResponseObject(False, "Sorry, your username or password is incorrect.")

@auth_blueprint.get('/signout')
def API_SignOut():
    resp = ResponseObject(True, "")
    resp.delete_cookie("authToken")
    return resp
