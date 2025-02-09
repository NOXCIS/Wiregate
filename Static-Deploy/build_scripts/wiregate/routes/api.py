import os, hashlib, bcrypt, pyotp
import psutil, logging, json, ipaddress
import re, shutil, requests


from datetime import datetime
from icmplib import ping, traceroute
import time

from flask import (
    Flask, Blueprint, request, render_template, 
    session, jsonify, make_response, Response
)

from ..modules.shared import (
    app, ResponseObject, sqlUpdate, 
    DASHBOARD_VERSION
)

from ..modules.Core import (
    DashboardConfig,  Configuration, PeerJob, Locale, ArchiveUtils,
    Configurations, AllPeerShareLinks, AllPeerJobs,
    JobLogger, AllDashboardLogger, 
    InitWireguardConfigurationsList, get_backup_paths,
    APP_PREFIX,
)
from ..modules.config import wgd_config_path

from ..Utilities import (
    RegexMatch, GenerateWireguardPublicKey,
    GenerateWireguardPrivateKey
)



api_blueprint = Blueprint('api', __name__)




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


@api_blueprint.route('/handshake', methods=["GET", "OPTIONS"])
def API_Handshake():
    return ResponseObject(True)


@api_blueprint.get('/validateAuthentication')
def API_ValidateAuthentication():
    token = request.cookies.get("authToken")
    if DashboardConfig.GetConfig("Server", "auth_req")[1]:
        if token is None or token == "" or "username" not in session or session["username"] != token:
            return ResponseObject(False, "Invalid authentication.")
    return ResponseObject(True)


@api_blueprint.get('/requireAuthentication')
def API_RequireAuthentication():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "auth_req")[1])


@api_blueprint.post('/authenticate')
def API_AuthenticateLogin():
    data = request.get_json()
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        return ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])

    if DashboardConfig.APIAccessed:
        authToken = hashlib.sha256(f"{request.headers.get('wg-dashboard-apikey')}{datetime.now()}".encode()).hexdigest()
        session['username'] = authToken
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        resp.set_cookie("authToken", authToken)
        session.permanent = True
        return resp
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


@api_blueprint.get('/signout')
def API_SignOut():
    resp = ResponseObject(True, "")
    resp.delete_cookie("authToken")
    return resp


@api_blueprint.route('/config-status-stream')
def stream_config_status():
    def get_all_statuses():
        # Create a dictionary of configuration names and their status
        return {name: config.getStatus() for name, config in Configurations.items()}
        
    def event_stream():
        while True:
            # Check configurations status using the helper function
            configs = get_all_statuses()
            yield f"data: {json.dumps(configs)}\n\n"
            time.sleep(0.1)  # More efficient than 10s

    return Response(event_stream(), mimetype="text/event-stream")


@api_blueprint.route(f'/getConfigurations', methods=["GET"])
def API_getConfigurations():
    InitWireguardConfigurationsList()
    return ResponseObject(data=[wc for wc in Configurations.values()])


@api_blueprint.route(f'/addConfiguration', methods=["POST"])
def API_addConfiguration():
    data = request.get_json()
    requiredKeys = [
        "ConfigurationName", "Address", "ListenPort", "PrivateKey"
    ]
    for i in requiredKeys:
        if i not in data.keys():
            return ResponseObject(False, "Please provide all required parameters.")

    # Check duplicate names, ports, address
    for i in Configurations.values():
        if i.Name == data['ConfigurationName']:
            return ResponseObject(False,
                                  f"Already have a configuration with the name \"{data['ConfigurationName']}\"",
                                  "ConfigurationName")
        if str(i.ListenPort) == str(data["ListenPort"]):
            return ResponseObject(False,
                                  f"Already have a configuration with the port \"{data['ListenPort']}\"",
                                  "ListenPort")
        if i.Address == data["Address"]:
            return ResponseObject(False,
                                  f"Already have a configuration with the address \"{data['Address']}\"",
                                  "Address")

    # Create iptables-rules directory if it doesn't exist
    iptables_dir = "./iptable-rules"
    if not os.path.exists(iptables_dir):
        try:
            os.makedirs(iptables_dir)
        except Exception as e:
            return ResponseObject(False, f"Failed to create iptables directory: {str(e)}")

    backup_mode = "Backup" in data.keys()

    if backup_mode:
        # Existing backup mode handling
        config_name = data["Backup"].split("_")[0]
        backup_paths = get_backup_paths(config_name)
        backup_file = os.path.join(backup_paths['config_dir'], data["Backup"])
        backup_sql = os.path.join(backup_paths['config_dir'], data["Backup"].replace('.conf', '.sql'))
        backup_iptables = os.path.join(backup_paths['config_dir'], data["Backup"].replace('.conf', '_iptables.json'))

        if not os.path.exists(backup_file):
            return ResponseObject(False, "Backup configuration file does not exist")

        # Copy configuration file
        try:
            wg_conf_path = os.path.join(
                DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                f'{data["ConfigurationName"]}.conf'
            )
            shutil.copy(backup_file, wg_conf_path)
        except Exception as e:
            return ResponseObject(False, f"Failed to copy configuration file: {str(e)}")

        # Create and initialize the configuration
        try:
            Configurations[data['ConfigurationName']] = Configuration(
                name=data['ConfigurationName']
            )
        except Exception as e:
            if os.path.exists(wg_conf_path):
                os.remove(wg_conf_path)
            return ResponseObject(False, f"Failed to initialize configuration: {str(e)}")

        # Restore database if it exists
        if os.path.exists(backup_sql):
            try:
                with open(backup_sql, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # Update table names to match new configuration name
                            line = line.replace(
                                f'"{data["Backup"].split("_")[0]}"',
                                f'"{data["ConfigurationName"]}"'
                            )
                            sqlUpdate(line)
            except Exception as e:
                # Cleanup on failure
                Configurations[data['ConfigurationName']].deleteConfiguration()
                Configurations.pop(data['ConfigurationName'])
                return ResponseObject(False, f"Failed to restore database: {str(e)}")

        # Restore iptables scripts if they exist
        if os.path.exists(backup_iptables):
            try:
                with open(backup_iptables, 'r') as f:
                    scripts = json.load(f)

                # Map of script types to configuration attributes and file suffixes
                script_mapping = {
                    'preup_script': ('PreUp', '-preup.sh'),
                    'postup_script': ('PostUp', '-postup.sh'),
                    'predown_script': ('PreDown', '-predown.sh'),
                    'postdown_script': ('PostDown', '-postdown.sh')
                }

                # Create and restore all script types
                for script_key, (config_attr, suffix) in script_mapping.items():
                    if script_key in scripts:
                        script_path = os.path.join(iptables_dir, f"{data['ConfigurationName']}{suffix}")
                        with open(script_path, 'w') as f:
                            f.write(scripts[script_key])
                        os.chmod(script_path, 0o755)

                        # Update configuration's corresponding attribute to point to new script
                        setattr(Configurations[data['ConfigurationName']],
                                config_attr,
                                script_path)

            except Exception as e:
                # Cleanup on failure
                Configurations[data['ConfigurationName']].deleteConfiguration()
                Configurations.pop(data['ConfigurationName'])
                return ResponseObject(False, f"Failed to restore iptables scripts: {str(e)}")


    else:
        # Handle new configuration creation with all IPTables scripts
        try:
            config_name = data['ConfigurationName']

            # Create all IPTables scripts (PreUp, PostUp, PreDown, PostDown)
            script_types = {
                'PreUp': '-preup.sh',
                'PostUp': '-postup.sh',
                'PreDown': '-predown.sh',
                'PostDown': '-postdown.sh'
            }

            script_paths = {}
            for script_type, suffix in script_types.items():
                if script_type in data and data.get(script_type):
                    script_path = os.path.join(iptables_dir, f"{config_name}{suffix}")
                    with open(script_path, 'w') as f:
                        f.write("#!/bin/bash\n\n")
                        f.write(f"# IPTables {script_type} Rules for {config_name}\n")
                        f.write(data.get(script_type, ''))
                    os.chmod(script_path, 0o755)
                    script_paths[script_type] = script_path

            # Update data with script paths for Configuration creation
            for script_type, path in script_paths.items():
                data[script_type] = path

            # Create the configuration
            Configurations[config_name] = Configuration(data=data)

        except Exception as e:
            # Cleanup on failure - remove any created script files
            for script_path in script_paths.values():
                if os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                    except:
                        pass
            return ResponseObject(False, f"Failed to create configuration: {str(e)}")

    # Handle AmneziaWG specific setup
    if data.get("Protocol") == "awg":
        try:
            conf_file_path = os.path.join(wgd_config_path, f'{data["ConfigurationName"]}.conf')
            symlink_path = os.path.join("/etc/amnezia/amneziawg", f'{data["ConfigurationName"]}.conf')

            if not os.path.islink(symlink_path):
                os.symlink(conf_file_path, symlink_path)
                print(f"Created symbolic link: {symlink_path} -> {conf_file_path}")
            else:
                print(f"Symbolic link for {data['ConfigurationName']} already exists, skipping...")

        except Exception as e:
            print(f"Warning: Failed to create AmneziaWG symlink: {str(e)}")

    return ResponseObject()


@api_blueprint.get('/toggleConfiguration/')
def API_toggleConfiguration():
    configurationName = request.args.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")
    toggleStatus, msg = Configurations[configurationName].toggleConfiguration()
    return ResponseObject(toggleStatus, msg, Configurations[configurationName].Status)


@api_blueprint.post('/updateConfiguration')
def API_updateConfiguration():
    data = request.get_json()
    requiredKeys = ["Name"]
    for i in requiredKeys:
        if i not in data.keys():
            return ResponseObject(False, "Please provide these following field: " + ", ".join(requiredKeys))
    name = data.get("Name")
    if name not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")

    status, msg = Configurations[name].updateConfigurationSettings(data)

    return ResponseObject(status, message=msg, data=Configurations[name])


'''
Edit Raw Config API
'''


@api_blueprint.get('/getConfigurationRawFile')
def API_GetConfigurationRawFile():
    configurationName = request.args.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    return ResponseObject(data={
        "path": Configurations[configurationName].configPath,
        "content": Configurations[configurationName].getRawConfigurationFile()
    })


@api_blueprint.post('/updateConfigurationRawFile')
def API_UpdateConfigurationRawFile():
    data = request.get_json()
    configurationName = data.get('configurationName')
    rawConfiguration = data.get('rawConfiguration')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")
    if rawConfiguration is None or len(rawConfiguration) == 0:
        return ResponseObject(False, "Please provide content")

    status, err = Configurations[configurationName].updateRawConfigurationFile(rawConfiguration)

    return ResponseObject(status=status, message=err)


'''
Iptable Script Get API
'''


@api_blueprint.post('/getConfigTablesPreUp')
def API_GetConfigTablesPreUp():
    data = request.get_json()
    configurationName = data.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    script_paths = Configurations[configurationName].getPreUp()

    if not script_paths:
        return ResponseObject(False, "No PreUp scripts found")

    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"

    return ResponseObject(data={
        "paths": script_paths,
        "contents": script_contents,
        "raw_preup":    Configurations[configurationName].PreUp
    })


@api_blueprint.post('/getConfigTablesPostUp')
def API_GetConfigTablesPostUp():
    data = request.get_json()
    configurationName = data.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    script_paths = Configurations[configurationName].getPostUp()

    if not script_paths:
        return ResponseObject(False, "No PostUp scripts found")

    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"

    return ResponseObject(data={
        "paths": script_paths,
        "contents": script_contents,
        "raw_postup": Configurations[configurationName].PostUp
    })


@api_blueprint.post('/getConfigTablesPostDown')
def API_GetConfigTablesPostDown():
    data = request.get_json()
    configurationName = data.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    script_paths = Configurations[configurationName].getPostDown()

    if not script_paths:
        return ResponseObject(False, "No PostDown scripts found")

    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"

    return ResponseObject(data={
        "paths": script_paths,
        "contents": script_contents,
        "raw_postdown": Configurations[configurationName].PostDown
    })


@api_blueprint.post('/getConfigTablesPreDown')
def API_GetConfigTablesPreDown():
    data = request.get_json()
    configurationName = data.get('configurationName')
    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    script_paths = Configurations[configurationName].getPreDown()

    if not script_paths:
        return ResponseObject(False, "No PreDown scripts found")

    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"

    return ResponseObject(data={
        "paths": script_paths,
        "contents": script_contents,
        "raw_predown": Configurations[configurationName].PreDown
    })


'''
Iptable Script Update API
'''


@api_blueprint.post('/updateConfigTablesPreUp')
def API_UpdateConfigTablesPreUp():
    data = request.get_json()
    configurationName = data.get('configurationName')
    script_content = data.get('content')

    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    if script_content is None:
        return ResponseObject(False, "Please provide script content")

    config = Configurations[configurationName]
    script_paths = config.getPreUp()

    if not script_paths:
        return ResponseObject(False, "No PreUp script path found")

    try:
        # Update each script file
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            # Make executable
            os.chmod(path, 0o755)

        return ResponseObject(True, "PreUp script updated successfully")
    except Exception as e:
        return ResponseObject(False, f"Failed to update script: {str(e)}")


@api_blueprint.post('/updateConfigTablesPostUp')
def API_UpdateConfigTablesPostUp():
    data = request.get_json()
    configurationName = data.get('configurationName')
    script_content = data.get('content')

    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    if script_content is None:
        return ResponseObject(False, "Please provide script content")

    config = Configurations[configurationName]
    script_paths = config.getPostUp()

    if not script_paths:
        return ResponseObject(False, "No PostUp script path found")

    try:
        # Update each script file
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            # Make executable
            os.chmod(path, 0o755)

        return ResponseObject(True, "PostUp script updated successfully")
    except Exception as e:
        return ResponseObject(False, f"Failed to update script: {str(e)}")


@api_blueprint.post('/updateConfigTablesPreDown')
def API_UpdateConfigTablesPreDown():
    data = request.get_json()
    configurationName = data.get('configurationName')
    script_content = data.get('content')

    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    if script_content is None:
        return ResponseObject(False, "Please provide script content")

    config = Configurations[configurationName]
    script_paths = config.getPreDown()

    if not script_paths:
        return ResponseObject(False, "No PreDown script path found")

    try:
        # Update each script file
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            # Make executable
            os.chmod(path, 0o755)

        return ResponseObject(True, "PreDown script updated successfully")
    except Exception as e:
        return ResponseObject(False, f"Failed to update script: {str(e)}")


@api_blueprint.post('/updateConfigTablesPostDown')
def API_UpdateConfigTablesPostDown():
    data = request.get_json()
    configurationName = data.get('configurationName')
    script_content = data.get('content')

    if configurationName is None or len(
            configurationName) == 0 or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide a valid configuration name")

    if script_content is None:
        return ResponseObject(False, "Please provide script content")

    config = Configurations[configurationName]
    script_paths = config.getPostDown()

    if not script_paths:
        return ResponseObject(False, "No PostDown script path found")

    try:
        # Update each script file
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            # Make executable
            os.chmod(path, 0o755)

        return ResponseObject(True, "PostDown script updated successfully")
    except Exception as e:
        return ResponseObject(False, f"Failed to update script: {str(e)}")


@api_blueprint.post('/deleteConfiguration')
def API_deleteWireguardConfiguration():
    data = request.get_json()
    if "Name" not in data.keys() or data.get("Name") is None or data.get("Name") not in Configurations.keys():
        return ResponseObject(False, "Please provide the configuration name you want to delete")

    config_name = data.get("Name")

    # Delete iptables script files before deleting configuration
    script_types = ['-preup.sh', '-postup.sh', '-predown.sh', '-postdown.sh']
    iptables_dir = "./iptable-rules"

    for script_suffix in script_types:
        script_path = os.path.join(iptables_dir, f"{config_name}{script_suffix}")
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
                print(f"Deleted iptables script: {script_path}")
        except Exception as e:
            print(f"Warning: Failed to delete iptables script {script_path}: {str(e)}")

    # Delete the configuration
    status = Configurations[config_name].deleteConfiguration()

    if status:
        Configurations.pop(config_name)
    return ResponseObject(status)


@api_blueprint.post('/renameConfiguration')
def API_renameConfiguration():
    data = request.get_json()
    keys = ["Name", "NewConfigurationName"]
    for k in keys:
        if (k not in data.keys() or data.get(k) is None or len(data.get(k)) == 0 or
                (k == "Name" and data.get(k) not in Configurations.keys())):
            return ResponseObject(False, "Please provide the configuration name you want to rename")

    status, message = Configurations[data.get("Name")].renameConfiguration(data.get("NewConfigurationName"))
    if status:
        Configurations.pop(data.get("Name"))
        Configurations[data.get("NewConfigurationName")] = Configuration(data.get("NewConfigurationName"))
    return ResponseObject(status, message)


@api_blueprint.get('/getConfigurationBackup')
def API_getConfigurationBackup():
    """Get backups for a specific configuration with organized structure"""
    configurationName = request.args.get('configurationName')
    if configurationName is None or configurationName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    return ResponseObject(data=Configurations[configurationName].getBackups())


@api_blueprint.get('/getAllConfigurationBackup')
def API_getAllConfigurationBackup():
    """Get all configuration backups with organized structure"""
    data = {
        "ExistingConfigurations": {},
        "NonExistingConfigurations": {}
    }

    # Get base backup directory
    backup_dir = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')

    # Handle existing configurations
    existingConfiguration = Configurations.keys()
    for config_name in existingConfiguration:
        backups = Configurations[config_name].getBackups(True)
        if backups:
            data['ExistingConfigurations'][config_name] = backups

    # Handle non-existing configurations
    if os.path.exists(backup_dir):
        # Look for backup directories that don't match existing configurations
        for dir_name in os.listdir(backup_dir):
            dir_path = os.path.join(backup_dir, dir_name)
            if os.path.isdir(dir_path) and dir_name not in existingConfiguration:
                backups = []
                files = [(f, os.path.getctime(os.path.join(dir_path, f)))
                         for f in os.listdir(dir_path)
                         if os.path.isfile(os.path.join(dir_path, f))]
                files.sort(key=lambda x: x[1], reverse=True)

                for f, _ in files:
                    if RegexMatch(r"^(.*)_(.*)\.(conf)$", f):
                        s = re.search(r"^(.*)_(.*)\.(conf)$", f)
                        date = s.group(2)
                        backup_info = {
                            "filename": f,
                            "backupDate": date,
                            "content": open(os.path.join(dir_path, f), 'r').read()
                        }

                        # Check for associated backup files
                        sql_file = f.replace(".conf", ".sql")
                        if os.path.exists(os.path.join(dir_path, sql_file)):
                            backup_info['database'] = True
                            backup_info['databaseContent'] = open(os.path.join(dir_path, sql_file), 'r').read()

                        iptables_file = f.replace(".conf", "_iptables.json")
                        if os.path.exists(os.path.join(dir_path, iptables_file)):
                            backup_info['iptables_scripts'] = True
                            with open(os.path.join(dir_path, iptables_file), 'r') as iptables_f:
                                backup_info['iptablesContent'] = iptables_f.read()

                        backups.append(backup_info)

                if backups:
                    data['NonExistingConfigurations'][dir_name] = backups

    return ResponseObject(data=data)


@api_blueprint.get('/createConfigurationBackup')
def API_createConfigurationBackup():
    """Create a backup for a specific configuration using organized structure"""
    configurationName = request.args.get('configurationName')
    if configurationName is None or configurationName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")

    success = Configurations[configurationName].backupConfigurationFile()
    return ResponseObject(
        status=success,
        data=Configurations[configurationName].getBackups() if success else None
    )


@api_blueprint.post('/deleteConfigurationBackup')
def API_DeleteConfigurationBackup():
    try:
        data = request.get_json()
        if 'configurationName' not in data or 'backupFileName' not in data:
            return ResponseObject(False, "Missing required parameters")

        config_name = data['configurationName']
        backup_file = data['backupFileName']

        # Get backup paths
        backup_timestamp = backup_file.replace(f'{config_name}_', '').replace('.conf', '')
        backup_paths = get_backup_paths(config_name, backup_timestamp)

        # Delete backup files if they exist
        files_to_delete = [
            backup_paths['conf_file'],
            backup_paths['sql_file'],
            backup_paths['iptables_file']
        ]

        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)

        # Check if config backup directory is empty and remove it if so
        if len(os.listdir(backup_paths['config_dir'])) == 0:
            os.rmdir(backup_paths['config_dir'])

        return ResponseObject(True, "Backup deleted successfully")

    except Exception as e:
        logging.error(f"Error deleting backup: {str(e)}")
        return ResponseObject(False, f"Failed to delete backup: {str(e)}")


@api_blueprint.post('/restoreConfigurationBackup')
def API_restoreConfigurationBackup():
    """Restore a backup using organized structure"""
    try:
        if request.is_json:
            data = request.get_json()
            configuration_name = data.get("configurationName")
            backup_file_name = data.get("backupFileName")
            backup_file = None

            if not configuration_name or not backup_file_name:
                return ResponseObject(False, "Configuration name and backup file name are required")

        else:
            backup_file = request.files.get("backupFile")
            if not backup_file:
                return ResponseObject(False, "No backup file uploaded")

            # Extract configuration name from backup filename
            backup_filename = backup_file.filename
            match = re.search(r"^(.+?)_\d{14}_complete\.7z$", backup_filename)
            if not match:
                return ResponseObject(False, f"Invalid backup filename format: {backup_filename}")

            configuration_name = match.group(1)
            backup_file_name = None

        # Create temp directory for processing
        temp_dir = os.path.join(
            DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
            'WGDashboard_Backup',
            'temp'
        )
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        try:
            if backup_file:
                # Handle uploaded 7z file
                if not backup_file.filename.endswith('.7z'):
                    return ResponseObject(False, "Uploaded file must be a .7z archive")

                # Save uploaded file
                file_path = os.path.join(temp_dir, backup_file.filename)
                backup_file.save(file_path)

                # Verify and extract the archive
                is_valid, error_msg, extracted_files = ArchiveUtils.verify_archive(
                    open(file_path, 'rb').read()
                )

                if not is_valid:
                    return ResponseObject(False, f"Invalid backup archive: {error_msg}")

                # Create configuration if it doesn't exist
                if configuration_name not in Configurations.keys():
                    Configurations[configuration_name] = Configuration(configuration_name)

                # Get backup paths for the configuration
                backup_paths = get_backup_paths(configuration_name)

                # Save extracted files to appropriate locations
                for filename, content in extracted_files.items():
                    if filename.startswith('iptable-rules/'):
                        # Handle iptables rules
                        rules_dir = os.path.join(
                            DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
                        )
                        os.makedirs(rules_dir, exist_ok=True)
                        file_path = os.path.join(rules_dir, os.path.basename(filename))
                    else:
                        # Handle regular backup files
                        file_path = os.path.join(backup_paths['config_dir'], filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    with open(file_path, 'wb') as f:
                        f.write(content)

                    if filename.endswith('.sh'):
                        os.chmod(file_path, 0o755)

            else:
                # Handle native backup restore
                if configuration_name not in Configurations.keys():
                    return ResponseObject(False, "Configuration does not exist")

                success = Configurations[configuration_name].restoreBackup(backup_file_name)
                if not success:
                    return ResponseObject(False, "Failed to restore backup")

            return ResponseObject(True, "Backup restored successfully")

        finally:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    except Exception as e:
        return ResponseObject(False, f"Error restoring backup: {str(e)}")


@api_blueprint.get('/downloadConfigurationBackup')
def API_downloadConfigurationBackup():
    """Download a backup with enhanced script handling"""
    try:
        config_name = request.args.get('configurationName')
        backup_name = request.args.get('backupFileName')
        print(f"Download requested for config: {config_name}, backup: {backup_name}")

        if not config_name or not backup_name:
            return ResponseObject(False, "Configuration name and backup filename are required")

        # Get timestamp from backup filename
        timestamp = backup_name.split('_')[1].split('.')[0]
        backup_paths = get_backup_paths(config_name, timestamp)

        if not os.path.exists(backup_paths['conf_file']):
            return ResponseObject(False, "Backup file not found")

        try:
            # Collect all backup files
            files_dict = {}

            # Add main configuration file
            with open(backup_paths['conf_file'], 'rb') as f:
                files_dict[os.path.basename(backup_paths['conf_file'])] = f.read()

            # Add SQL backup if it exists
            if os.path.exists(backup_paths['sql_file']):
                with open(backup_paths['sql_file'], 'rb') as f:
                    files_dict[os.path.basename(backup_paths['sql_file'])] = f.read()

            # Add iptables backup if it exists
            if os.path.exists(backup_paths['iptables_file']):
                # First add the iptables.json file itself
                with open(backup_paths['iptables_file'], 'rb') as f:
                    files_dict[os.path.basename(backup_paths['iptables_file'])] = f.read()

                # Then process the scripts referenced in iptables.json
                with open(backup_paths['iptables_file'], 'r') as f:
                    scripts = json.load(f)
                # Include all script files if they exist
                script_types = ['preup', 'postup', 'predown', 'postdown']
                for script_type in script_types:
                    script_key = f"{script_type}_script"
                    if script_key in scripts:
                        script_name = f"{config_name}-{script_type}.sh"
                        script_path = os.path.join("./iptable-rules", script_name)
                        if os.path.exists(script_path):
                            with open(script_path, 'rb') as sf:
                                files_dict[f"iptable-rules/{script_name}"] = sf.read()

            # Create archive with integrity checks
            archive_data, _, combined_checksum = ArchiveUtils.create_archive(files_dict)

            # Create response
            response = make_response(archive_data)
            response.headers['Content-Type'] = 'application/x-7z-compressed'
            response.headers['Content-Disposition'] = \
                f'attachment; filename="{config_name}_{timestamp}_complete.7z"'
            response.headers['Content-Length'] = len(archive_data)
            response.headers['X-Archive-Checksum'] = combined_checksum

            return response

        except Exception as e:
            return ResponseObject(False, f"Error creating backup archive: {str(e)}")

    except Exception as e:
        return ResponseObject(False, f"Error processing download request: {str(e)}")


@api_blueprint.post('/uploadConfigurationBackup')
def API_uploadConfigurationBackup():
    """Upload and process a backup using organized structure"""
    try:
        if 'files' not in request.files:
            return ResponseObject(False, "No file part in request")

        files = request.files.getlist('files')
        if not files or len(files) != 1:
            return ResponseObject(False, "Please upload exactly one backup archive")

        file = files[0]
        if file.filename == '':
            return ResponseObject(False, "File name is empty")

        if not file.filename.endswith('.7z'):
            return ResponseObject(False, "Only .7z backup archives are allowed")

        # Extract configuration name from filename
        match = re.search(r"^(.+?)_\d{14}_complete\.7z$", file.filename)
        if not match:
            return ResponseObject(False, f"Invalid backup filename format: {file.filename}")

        config_name = match.group(1)
        backup_paths = get_backup_paths(config_name)

        # Read and verify the archive
        archive_data = file.read()
        is_valid, error_msg, extracted_files = ArchiveUtils.verify_archive(archive_data)

        if not is_valid:
            return ResponseObject(False, f"Invalid backup archive: {error_msg}")

        # Save verified files to appropriate locations
        saved_files = []
        for filename, content in extracted_files.items():
            # Skip iptables rules files as they're handled by restoreConfig
            if filename.startswith('iptable-rules/'):
                continue

            # Handle regular backup files
            file_path = os.path.join(backup_paths['config_dir'], filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(content)
            saved_files.append(filename)

            if filename.endswith('.sh'):
                os.chmod(file_path, 0o755)

        return ResponseObject(
            True,
            "Backup archive verified and extracted successfully",
            {"saved_files": saved_files}
        )

    except Exception as e:
        return ResponseObject(False, f"Error processing backup: {str(e)}")


@api_blueprint.get('/getDashboardConfiguration')
def API_getDashboardConfiguration():
    return ResponseObject(data=DashboardConfig.toJson())


@api_blueprint.post('/updateDashboardConfigurationItem')
def API_updateDashboardConfigurationItem():
    data = request.get_json()
    if "section" not in data.keys() or "key" not in data.keys() or "value" not in data.keys():
        return ResponseObject(False, "Invalid request.")
    valid, msg = DashboardConfig.SetConfig(
        data["section"], data["key"], data['value'])
    if not valid:
        return ResponseObject(False, msg)

    if data['section'] == "Server":
        if data['key'] == 'wg_conf_path':
            Configurations.clear()
            InitWireguardConfigurationsList()

    return ResponseObject(True, data=DashboardConfig.GetConfig(data["section"], data["key"])[1])


@api_blueprint.get('/getDashboardAPIKeys')
def API_getDashboardAPIKeys():
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key'):
        return ResponseObject(data=DashboardConfig.DashboardAPIKeys)
    return ResponseObject(False, "WGDashboard API Keys function is disabled")


@api_blueprint.post('/newDashboardAPIKey')
def API_newDashboardAPIKey():
    data = request.get_json()
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key'):
        try:
            if data['neverExpire']:
                expiredAt = None
            else:
                expiredAt = datetime.strptime(data['ExpiredAt'], '%Y-%m-%d %H:%M:%S')
            DashboardConfig.createAPIKeys(expiredAt)
            return ResponseObject(True, data=DashboardConfig.DashboardAPIKeys)
        except Exception as e:
            return ResponseObject(False, str(e))
    return ResponseObject(False, "Dashboard API Keys function is disbaled")


@api_blueprint.post('/deleteDashboardAPIKey')
def API_deleteDashboardAPIKey():
    data = request.get_json()
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key'):
        if len(data['Key']) > 0 and len(
                list(filter(lambda x: x.Key == data['Key'], DashboardConfig.DashboardAPIKeys))) > 0:
            DashboardConfig.deleteAPIKey(data['Key'])
            return ResponseObject(True, data=DashboardConfig.DashboardAPIKeys)
    return ResponseObject(False, "Dashboard API Keys function is disbaled")


@api_blueprint.post('/updatePeerSettings/<configName>')
def API_updatePeerSettings(configName):
    data = request.get_json()
    id = data['id']
    if len(id) > 0 and configName in Configurations.keys():
        name = data['name']
        private_key = data['private_key']
        dns_addresses = data['DNS']
        allowed_ip = data['allowed_ip']
        endpoint_allowed_ip = data['endpoint_allowed_ip']
        preshared_key = data['preshared_key']
        mtu = data['mtu']
        keepalive = data['keepalive']
        wireguardConfig = Configurations[configName]
        foundPeer, peer = wireguardConfig.searchPeer(id)
        if foundPeer:
            return peer.updatePeer(name, private_key, preshared_key, dns_addresses,
                                   allowed_ip, endpoint_allowed_ip, mtu, keepalive)
    return ResponseObject(False, "Peer does not exist")


@api_blueprint.post('/resetPeerData/<configName>')
def API_resetPeerData(configName):
    data = request.get_json()
    id = data['id']
    type = data['type']
    if len(id) == 0 or configName not in Configurations.keys():
        return ResponseObject(False, "Configuration/Peer does not exist")
    wgc = Configurations.get(configName)
    foundPeer, peer = wgc.searchPeer(id)
    if not foundPeer:
        return ResponseObject(False, "Configuration/Peer does not exist")
    return ResponseObject(status=peer.resetDataUsage(type))


@api_blueprint.post('/deletePeers/<configName>')
def API_deletePeers(configName: str) -> ResponseObject:
    data = request.get_json()
    peers = data['peers']
    if configName in Configurations.keys():
        if len(peers) == 0:
            return ResponseObject(False, "Please specify one or more peers")
        configuration = Configurations.get(configName)
        return configuration.deletePeers(peers)

    return ResponseObject(False, "Configuration does not exist")


@api_blueprint.post('/restrictPeers/<configName>')
def API_restrictPeers(configName: str) -> ResponseObject:
    data = request.get_json()
    peers = data['peers']
    if configName in Configurations.keys():
        if len(peers) == 0:
            return ResponseObject(False, "Please specify one or more peers")
        configuration = Configurations.get(configName)
        return configuration.restrictPeers(peers)
    return ResponseObject(False, "Configuration does not exist")


@api_blueprint.post('/sharePeer/create')
def API_sharePeer_create():
    data: dict[str, str] = request.get_json()
    Configuration = data.get('Configuration')
    Peer = data.get('Peer')
    ExpireDate = data.get('ExpireDate')
    if Configuration is None or Peer is None:
        return ResponseObject(False, "Please specify configuration and peers")
    activeLink = AllPeerShareLinks.getLink(Configuration, Peer)
    if len(activeLink) > 0:
        return ResponseObject(True,
                              "This peer is already sharing. Please view data for shared link.",
                              data=activeLink[0]
                              )
    status, message = AllPeerShareLinks.addLink(Configuration, Peer, ExpireDate)
    if not status:
        return ResponseObject(status, message)
    return ResponseObject(data=AllPeerShareLinks.getLinkByID(message))


@api_blueprint.post('/sharePeer/update')
def API_sharePeer_update():
    data: dict[str, str] = request.get_json()
    ShareID: str = data.get("ShareID")
    ExpireDate: str = data.get("ExpireDate")

    if ShareID is None:
        return ResponseObject(False, "Please specify ShareID")

    if len(AllPeerShareLinks.getLinkByID(ShareID)) == 0:
        return ResponseObject(False, "ShareID does not exist")

    status, message = AllPeerShareLinks.updateLinkExpireDate(ShareID, ExpireDate)
    if not status:
        return ResponseObject(status, message)
    return ResponseObject(data=AllPeerShareLinks.getLinkByID(ShareID))


@api_blueprint.get('/sharePeer/get')
def API_sharePeer_get():
    data = request.args
    ShareID = data.get("ShareID")
    if ShareID is None or len(ShareID) == 0:
        return ResponseObject(False, "Please provide ShareID")
    link = AllPeerShareLinks.getLinkByID(ShareID)
    if len(link) == 0:
        return ResponseObject(False, "This link is either expired to invalid")
    l = link[0]
    if l.Configuration not in Configurations.keys():
        return ResponseObject(False, "The peer you're looking for does not exist")
    c = Configurations.get(l.Configuration)
    fp, p = c.searchPeer(l.Peer)
    if not fp:
        return ResponseObject(False, "The peer you're looking for does not exist")

    return ResponseObject(data=p.downloadPeer())


@api_blueprint.post('/allowAccessPeers/<configName>')
def API_allowAccessPeers(configName: str) -> ResponseObject:
    data = request.get_json()
    peers = data['peers']
    if configName in Configurations.keys():
        if len(peers) == 0:
            return ResponseObject(False, "Please specify one or more peers")
        configuration = Configurations.get(configName)
        return configuration.allowAccessPeers(peers)
    return ResponseObject(False, "Configuration does not exist")


@api_blueprint.post('/addPeers/<configName>')
def API_addPeers(configName):
    if configName in Configurations.keys():
        try:
            data: dict = request.get_json()

            bulkAdd: bool = data.get("bulkAdd", False)
            bulkAddAmount: int = data.get('bulkAddAmount', 0)
            preshared_key_bulkAdd: bool = data.get('preshared_key_bulkAdd', False)

            public_key: str = data.get('public_key', "")
            allowed_ips: list[str] = data.get('allowed_ips', "")

            endpoint_allowed_ip: str = data.get('endpoint_allowed_ip',
                                                DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1])
            dns_addresses: str = data.get('DNS', DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1])
            mtu: int = data.get('mtu', int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1]))
            keep_alive: int = data.get('keepalive', int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1]))
            preshared_key: str = data.get('preshared_key', "")

            if type(mtu) is not int or mtu < 0 or mtu > 1460:
                mtu = int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1])
            if type(keep_alive) is not int or keep_alive < 0:
                keep_alive = int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1])
            if len(dns_addresses) == 0:
                dns_addresses = DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1]
            if len(endpoint_allowed_ip) == 0:
                endpoint_allowed_ip = DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1]
            config = Configurations.get(configName)
            if not bulkAdd and (len(public_key) == 0 or len(allowed_ips) == 0):
                return ResponseObject(False, "Please provide at least public_key and allowed_ips")
            if not config.getStatus():
                config.toggleConfiguration()
            availableIps = config.getAvailableIP()
            if bulkAdd:
                if type(preshared_key_bulkAdd) is not bool:
                    preshared_key_bulkAdd = False

                if type(bulkAddAmount) is not int or bulkAddAmount < 1:
                    return ResponseObject(False, "Please specify amount of peers you want to add")
                if not availableIps[0]:
                    return ResponseObject(False, "No more available IP can assign")
                if bulkAddAmount > len(availableIps[1]):
                    return ResponseObject(False,
                                          f"The maximum number of peers can add is {len(availableIps[1])}")
                keyPairs = []
                for i in range(bulkAddAmount):
                    newPrivateKey = GenerateWireguardPrivateKey()[1]
                    keyPairs.append({
                        "private_key": newPrivateKey,
                        "id": GenerateWireguardPublicKey(newPrivateKey)[1],
                        "preshared_key": (GenerateWireguardPrivateKey()[1] if preshared_key_bulkAdd else ""),
                        "allowed_ip": availableIps[1][i],
                        "name": f"BulkPeer #{(i + 1)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "DNS": dns_addresses,
                        "endpoint_allowed_ip": endpoint_allowed_ip,
                        "mtu": mtu,
                        "keepalive": keep_alive
                    })
                if len(keyPairs) == 0:
                    return ResponseObject(False, "Generating key pairs by bulk failed")
                config.addPeers(keyPairs)
                return ResponseObject()

            else:
                if config.searchPeer(public_key)[0] is True:
                    return ResponseObject(False, f"This peer already exist")
                name = data.get("name", "")
                private_key = data.get("private_key", "")

                for i in allowed_ips:
                    if i not in availableIps[1]:
                        return ResponseObject(False, f"This IP is not available: {i}")

                status = config.addPeers([
                    {
                        "name": name,
                        "id": public_key,
                        "private_key": private_key,
                        "allowed_ip": ','.join(allowed_ips),
                        "preshared_key": preshared_key,
                        "endpoint_allowed_ip": endpoint_allowed_ip,
                        "DNS": dns_addresses,
                        "mtu": mtu,
                        "keepalive": keep_alive
                    }]
                )
                return ResponseObject(status)
        except Exception as e:
            print(e)
            return ResponseObject(False, "Add peers failed. Please see data for specific issue")

    return ResponseObject(False, "Configuration does not exist")


@api_blueprint.get("/downloadPeer/<configName>")
def API_downloadPeer(configName):
    data = request.args
    if configName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    configuration = Configurations[configName]
    peerFound, peer = configuration.searchPeer(data['id'])
    if len(data['id']) == 0 or not peerFound:
        return ResponseObject(False, "Peer does not exist")
    return ResponseObject(data=peer.downloadPeer())

@api_blueprint.get("/downloadAllPeers/<configName>")
def API_downloadAllPeers(configName):
    if configName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    configuration = Configurations[configName]
    peerData = []
    untitledPeer = 0
    for i in configuration.Peers:
        file = i.downloadPeer()
        if file["fileName"] == "UntitledPeer_" + configName:
            file["fileName"] = str(untitledPeer) + "_" + file["fileName"]
            untitledPeer += 1
        peerData.append(file)
    return ResponseObject(data=peerData)

@api_blueprint.get("/getAvailableIPs/<configName>")
def API_getAvailableIPs(configName):
    if configName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    status, ips = Configurations.get(configName).getAvailableIP()
    return ResponseObject(status=status, data=ips)

@api_blueprint.get('/getWireguardConfigurationInfo')
def API_getConfigurationInfo():
    configurationName = request.args.get("configurationName")
    if not configurationName or configurationName not in Configurations.keys():
        return ResponseObject(False, "Please provide configuration name")
    return ResponseObject(data={
        "configurationInfo": Configurations[configurationName],
        "configurationPeers": Configurations[configurationName].getPeersList(),
        "configurationRestrictedPeers": Configurations[configurationName].getRestrictedPeersList()
    })

@api_blueprint.get('/getDashboardTheme')
def API_getDashboardTheme():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "dashboard_theme")[1])

@api_blueprint.get('/getDashboardVersion')
def API_getDashboardVersion():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "version")[1])

@api_blueprint.get('/getDashboardProto')
def API_getDashboardProto():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "protocol")[1])

@api_blueprint.post('/savePeerScheduleJob/')
def API_savePeerScheduleJob():
    data = request.json
    print(f"\n[DEBUG] Received job data: {json.dumps(data, indent=2)}")
    
    if "Job" not in data.keys():
        return ResponseObject(False, "Please specify job")
    job: dict = data['Job']
    
    # Validate weekly schedule format
    if job['Field'] == 'weekly':
        print(f"\n[DEBUG] Processing weekly schedule. Value: {job['Value']}")
        try:
            if not job['Value']:
                return ResponseObject(False, "Weekly schedule cannot be empty")
                
            schedules = job['Value'].split(',')
            print(f"[DEBUG] Split schedules: {schedules}")
            
            for schedule in schedules:
                try:
                    print(f"\n[DEBUG] Processing schedule: {schedule}")
                    
                    # First, split on the hyphen to separate the time range
                    time_range_parts = schedule.strip().split('-')
                    print(f"[DEBUG] Time range parts: {time_range_parts}")
                    
                    if len(time_range_parts) != 2:
                        print(f"[DEBUG] Invalid time range format")
                        return ResponseObject(False, f"Invalid time range format: {schedule}")
                    
                    # Get the day from the first part (before the first colon)
                    start_parts = time_range_parts[0].split(':', 1)
                    print(f"[DEBUG] Start parts: {start_parts}")
                    
                    if len(start_parts) != 2:
                        print(f"[DEBUG] Invalid start time format")
                        return ResponseObject(False, f"Invalid start time format: {time_range_parts[0]}")
                    
                    day = start_parts[0]
                    start_time = ':'.join(start_parts[1].split(':')[:2])  # Take only HH:MM
                    end_time = ':'.join(time_range_parts[1].split(':')[:2])  # Take only HH:MM
                    
                    print(f"[DEBUG] Parsed values - Day: {day}, Start: {start_time}, End: {end_time}")
                    
                    # Validate day
                    try:
                        day_num = int(day)
                        print(f"[DEBUG] Day number: {day_num}")
                        if not (0 <= day_num <= 6):
                            print(f"[DEBUG] Invalid day number: {day_num}")
                            return ResponseObject(False, "Weekly schedule day must be between 0 (Monday) and 6 (Sunday)")
                    except ValueError as e:
                        print(f"[DEBUG] Day number conversion error: {e}")
                        return ResponseObject(False, f"Invalid day number: {day}")
                    
                    # Validate time format (HH:MM)
                    try:
                        print(f"[DEBUG] Attempting to parse times - Start: {start_time}, End: {end_time}")
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        end_dt = datetime.strptime(end_time, '%H:%M')
                        print(f"[DEBUG] Parsed times successfully - Start: {start_dt}, End: {end_dt}")
                        
                        # Validate time range
                        if start_dt >= end_dt:
                            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                            print(f"[DEBUG] Invalid time range: {start_dt} >= {end_dt}")
                            return ResponseObject(False, f"Invalid time range for {day_names[day_num]}: end time must be after start time")
                            
                    except ValueError as e:
                        print(f"[DEBUG] Time parsing error: {e}")
                        return ResponseObject(False, f"Time must be in HH:MM format: {start_time} or {end_time}")
                    
                except Exception as e:
                    print(f"[DEBUG] Schedule processing error: {str(e)}")
                    return ResponseObject(False, f"Invalid schedule format: {str(e)}")
                
            # Validate no duplicate days
            days = [s.split('-')[0].split(':', 1)[0].strip() for s in schedules]
            print(f"[DEBUG] Checking for duplicate days: {days}")
            if len(days) != len(set(days)):
                print(f"[DEBUG] Found duplicate days")
                return ResponseObject(False, "Duplicate days are not allowed")
                
        except Exception as e:
            print(f"[DEBUG] Top-level error: {str(e)}")
            return ResponseObject(False, f"Invalid weekly schedule format: {str(e)}")

    print("[DEBUG] Validation completed successfully")
    if "Peer" not in job.keys() or "Configuration" not in job.keys():
        return ResponseObject(False, "Please specify peer and configuration")
    configuration = Configurations.get(job['Configuration'])
    f, fp = configuration.searchPeer(job['Peer'])
    if not f:
        return ResponseObject(False, "Peer does not exist")

    s, p = AllPeerJobs.saveJob(PeerJob(
        job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
        job['CreationDate'], job['ExpireDate'], job['Action']))
    if s:
        return ResponseObject(s, data=p)
    return ResponseObject(s, message=p)

@api_blueprint.post('/deletePeerScheduleJob/')
def API_deletePeerScheduleJob():
    data = request.json
    if "Job" not in data.keys():
        return ResponseObject(False, "Please specify job")
    job: dict = data['Job']
    if "Peer" not in job.keys() or "Configuration" not in job.keys():
        return ResponseObject(False, "Please specify peer and configuration")
    configuration = Configurations.get(job['Configuration'])
    f, fp = configuration.searchPeer(job['Peer'])
    if not f:
        return ResponseObject(False, "Peer does not exist")

    s, p = AllPeerJobs.deleteJob(PeerJob(
        job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
        job['CreationDate'], job['ExpireDate'], job['Action']))
    if s:
        return ResponseObject(s, data=p)
    return ResponseObject(s, message=p)

@api_blueprint.get('/getPeerScheduleJobLogs/<configName>')
def API_getPeerScheduleJobLogs(configName):
    if configName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    data = request.args.get("requestAll")
    requestAll = False
    if data is not None and data == "true":
        requestAll = True
    return ResponseObject(data=JobLogger.getLogs(requestAll, configName))


'''
Tools
'''


@api_blueprint.get('/ping/getAllPeersIpAddress')
def API_ping_getAllPeersIpAddress():
    ips = {}
    for c in Configurations.values():
        cips = {}
        for p in c.Peers:
            allowed_ip = p.allowed_ip.replace(" ", "").split(",")
            parsed = []
            for x in allowed_ip:
                try:
                    ip = ipaddress.ip_network(x, strict=False)
                except ValueError as e:
                    print(f"{p.id} - {c.Name}")
                if len(list(ip.hosts())) == 1:
                    parsed.append(str(ip.hosts()[0]))
            endpoint = p.endpoint.replace(" ", "").replace("(none)", "")
            if len(p.name) > 0:
                cips[f"{p.name} - {p.id}"] = {
                    "allowed_ips": parsed,
                    "endpoint": endpoint
                }
            else:
                cips[f"{p.id}"] = {
                    "allowed_ips": parsed,
                    "endpoint": endpoint
                }
        ips[c.Name] = cips
    return ResponseObject(data=ips)


import requests


@api_blueprint.get('/ping/execute')
def API_ping_execute():
    if "ipAddress" in request.args.keys() and "count" in request.args.keys():
        ip = request.args['ipAddress']
        count = request.args['count']
        try:
            if ip is not None and len(ip) > 0 and count is not None and count.isnumeric():
                result = ping(ip, count=int(count), source=None)

                data = {
                    "address": result.address,
                    "is_alive": result.is_alive,
                    "min_rtt": result.min_rtt,
                    "avg_rtt": result.avg_rtt,
                    "max_rtt": result.max_rtt,
                    "package_sent": result.packets_sent,
                    "package_received": result.packets_received,
                    "package_loss": result.packet_loss,
                    "geo": None
                }

                try:
                    r = requests.get(f"http://ip-api.com/json/{result.address}?field=city")
                    data['geo'] = r.json()
                except Exception as e:
                    pass
                return ResponseObject(data=data)
            return ResponseObject(False, "Please specify an IP Address (v4/v6)")
        except Exception as exp:
            return ResponseObject(False, exp)
    return ResponseObject(False, "Please provide ipAddress and count")


@api_blueprint.get('/traceroute/execute')
def API_traceroute_execute():
    if "ipAddress" in request.args.keys() and len(request.args.get("ipAddress")) > 0:
        ipAddress = request.args.get('ipAddress')
        try:
            tracerouteResult = traceroute(ipAddress, timeout=1, max_hops=64)
            result = []
            for hop in tracerouteResult:
                if len(result) > 1:
                    skipped = False
                    for i in range(result[-1]["hop"] + 1, hop.distance):
                        result.append(
                            {
                                "hop": i,
                                "ip": "*",
                                "avg_rtt": "*",
                                "min_rtt": "*",
                                "max_rtt": "*"
                            }
                        )
                        skip = True
                    if skipped: continue
                result.append(
                    {
                        "hop": hop.distance,
                        "ip": hop.address,
                        "avg_rtt": hop.avg_rtt,
                        "min_rtt": hop.min_rtt,
                        "max_rtt": hop.max_rtt
                    })
            try:
                r = requests.post(f"http://ip-api.com/batch?fields=city,country,lat,lon,query",
                                  data=json.dumps([x['ip'] for x in result]))
                d = r.json()
                for i in range(len(result)):
                    result[i]['geo'] = d[i]

            except Exception as e:
                print(e)
            return ResponseObject(data=result)
        except Exception as exp:
            return ResponseObject(False, exp)
    else:
        return ResponseObject(False, "Please provide ipAddress")


@api_blueprint.get('/getDashboardUpdate')
def API_getDashboardUpdate():
    try:
        # Replace with your actual Docker Hub repository
        docker_hub_repo = "noxcis/wiregate"

        # Docker Hub API URL to list tags
        list_tags_url = f"https://hub.docker.com/v2/repositories/{docker_hub_repo}/tags"

        # Send a request to Docker Hub to list all tags
        response = requests.get(list_tags_url, timeout=5)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            tags_data = response.json()

            # Get the results (list of tags)
            tags = tags_data.get('results', [])

            if not tags:
                return ResponseObject(False, "No tags found in the repository")

            # Create a list to store parsed tags with their details
            parsed_tags = []

            # Iterate through tags and parse details
            for tag in tags:
                try:
                    # Extract tag name and last pushed timestamp
                    tag_name = tag.get('name', '')

                    # Use tag_last_pushed for most accurate timestamp
                    last_pushed_str = tag.get('tag_last_pushed', tag.get('last_updated', ''))

                    # Convert timestamp to datetime
                    if last_pushed_str:
                        last_pushed = datetime.fromisoformat(last_pushed_str.replace('Z', '+00:00'))

                        parsed_tags.append({
                            'name': tag_name,
                            'last_pushed': last_pushed
                        })
                except Exception as tag_parse_error:
                    logging.error(f"Error parsing tag {tag}: {tag_parse_error}")

            # Sort tags by last pushed date
            if parsed_tags:
                sorted_tags = sorted(parsed_tags, key=lambda x: x['last_pushed'], reverse=True)
                latest_tag = sorted_tags[0]['name']
                latest_pushed = sorted_tags[0]['last_pushed']

                # Create Docker Hub URL
                docker_hub_url = f"https://hub.docker.com/r/{docker_hub_repo}/tags?page=1&name={latest_tag}"

                # Compare with current version
                if latest_tag and latest_tag != DASHBOARD_VERSION:
                    return ResponseObject(
                        message=f"{latest_tag} is now available for update!",
                        data=docker_hub_url
                    )
                else:
                    return ResponseObject(
                        message="You're on the latest version",
                        data=docker_hub_url
                    )

            return ResponseObject(False, "Unable to parse tags")

        # If request was not successful
        return ResponseObject(False, f"API request failed with status {response.status_code}")

    except requests.RequestException as e:
        logging.error(f"Request to Docker Hub API failed: {str(e)}")
        return ResponseObject(False, f"Request failed: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error in Docker Hub update check: {str(e)}")
        return ResponseObject(False, f"Unexpected error: {str(e)}")


'''
Sign Up
'''


@api_blueprint.get('/isTotpEnabled')
def API_isTotpEnabled():
    return (
        ResponseObject(data=DashboardConfig.GetConfig("Account", "enable_totp")[1] and
                            DashboardConfig.GetConfig("Account", "totp_verified")[1]))


@api_blueprint.get('/Welcome_GetTotpLink')
def API_Welcome_GetTotpLink():
    if not DashboardConfig.GetConfig("Account", "totp_verified")[1]:
        DashboardConfig.SetConfig("Account", "totp_key", pyotp.random_base32())
        return ResponseObject(
            data=pyotp.totp.TOTP(DashboardConfig.GetConfig("Account", "totp_key")[1]).provisioning_uri(
                issuer_name="WireGate"))
    return ResponseObject(False)


@api_blueprint.post('/Welcome_VerifyTotpLink')
def API_Welcome_VerifyTotpLink():
    data = request.get_json()
    totp = pyotp.TOTP(DashboardConfig.GetConfig("Account", "totp_key")[1]).now()
    if totp == data['totp']:
        DashboardConfig.SetConfig("Account", "totp_verified", "true")
        DashboardConfig.SetConfig("Account", "enable_totp", "true")
    return ResponseObject(totp == data['totp'])


@api_blueprint.post('/Welcome_Finish')
def API_Welcome_Finish():
    data = request.get_json()
    if DashboardConfig.GetConfig("Other", "welcome_session")[1]:
        if data["username"] == "":
            return ResponseObject(False, "Username cannot be blank.")

        if data["newPassword"] == "" or len(data["newPassword"]) < 8:
            return ResponseObject(False, "Password must be at least 8 characters")

        updateUsername, updateUsernameErr = DashboardConfig.SetConfig("Account", "username", data["username"])
        updatePassword, updatePasswordErr = DashboardConfig.SetConfig("Account", "password",
                                                                      {
                                                                          "newPassword": data["newPassword"],
                                                                          "repeatNewPassword": data[
                                                                              "repeatNewPassword"],
                                                                          "currentPassword": "admin"
                                                                      })
        if not updateUsername or not updatePassword:
            return ResponseObject(False, f"{updateUsernameErr},{updatePasswordErr}".strip(","))

        DashboardConfig.SetConfig("Other", "welcome_session", False)
    return ResponseObject()



Locale = Locale()


@api_blueprint.get('/locale')
def API_Locale_CurrentLang():
    return ResponseObject(data=Locale.getLanguage())


@api_blueprint.get('/locale/available')
def API_Locale_Available():
    return ResponseObject(data=Locale.activeLanguages)


@api_blueprint.post('/locale/update')
def API_Locale_Update():
    data = request.get_json()
    if 'lang_id' not in data.keys():
        return ResponseObject(False, "Please specify a lang_id")
    Locale.updateLanguage(data['lang_id'])
    return ResponseObject(data=Locale.getLanguage())


@api_blueprint.get('/systemStatus')
def API_SystemStatus():
    try:
        # CPU Information
        try:
            cpu_percpu = psutil.cpu_percent(interval=0.5, percpu=True)
            cpu = psutil.cpu_percent(interval=0.5)
        except Exception as e:
            cpu_percpu = []
            cpu = None
            logging.warning(f"Could not retrieve CPU information: {e}")

        # Memory Information
        try:
            memory = psutil.virtual_memory()
            try:
                swap_memory = psutil.swap_memory()
            except AttributeError:
                # Some systems might not have swap
                swap_memory = None
        except Exception as e:
            memory = None
            swap_memory = None
            logging.warning(f"Could not retrieve memory information: {e}")

        # Disk Information
        try:
            disks = psutil.disk_partitions(all=False)  # Only physical devices
            disk_status = {}
            for d in disks:
                # Skip certain filesystem types on specific platforms
                if d.fstype in ('squashfs', 'devfs', 'fdescfs', 'devtmpfs'):
                    continue
                try:
                    detail = psutil.disk_usage(d.mountpoint)
                    disk_status[d.mountpoint] = {
                        "total": detail.total,
                        "used": detail.used,
                        "free": detail.free,
                        "percent": detail.percent
                    }
                except (OSError, PermissionError) as disk_e:
                    logging.warning(f"Could not retrieve disk information for {d.mountpoint}: {disk_e}")
        except Exception as e:
            disk_status = {}
            logging.warning(f"Could not retrieve disk partitions: {e}")

        # Network Information
        try:
            network = psutil.net_io_counters(pernic=True, nowrap=True)
            network_status = {}
            for interface, stats in network.items():
                # Skip loopback interfaces on Unix-like systems
                if interface in ('lo', 'lo0'):
                    continue
                network_status[interface] = {
                    "byte_sent": stats.bytes_sent,
                    "byte_recv": stats.bytes_recv
                }
        except Exception as e:
            network_status = {}
            logging.warning(f"Could not retrieve network information: {e}")

        # Process Information
        try:
            processes = []
            for proc in psutil.process_iter():
                try:
                    with proc.oneshot():  # Improve performance by getting all info at once
                        # Get process info safely
                        name = proc.name()
                        try:
                            cmdline = ' '.join(proc.cmdline())
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            cmdline = name
                        
                        # Get CPU and memory info
                        cpu_percent = proc.cpu_percent(interval=None)
                        mem_percent = proc.memory_percent()
                        
                        processes.append({
                            "name": name,
                            "command": cmdline,
                            "pid": proc.pid,
                            "cpu_percent": cpu_percent,
                            "memory_percent": mem_percent
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as proc_e:
                    logging.warning(f"Error getting process info: {proc_e}")
                    continue

            # Sort and get top 10 processes
            cpu_top_10 = sorted(
                [p for p in processes if p['cpu_percent'] is not None],
                key=lambda x: x['cpu_percent'],
                reverse=True
            )[:10]

            memory_top_10 = sorted(
                [p for p in processes if p['memory_percent'] is not None],
                key=lambda x: x['memory_percent'],
                reverse=True
            )[:10]
        except Exception as e:
            cpu_top_10 = []
            memory_top_10 = []
            logging.warning(f"Could not retrieve process information: {e}")

        # Construct status dictionary with platform-aware null checks
        status = {
            "cpu": {
                "cpu_percent": cpu,
                "cpu_percent_per_cpu": cpu_percpu,
            },
            "memory": {
                "virtual_memory": {
                    "total": getattr(memory, 'total', None),
                    "available": getattr(memory, 'available', None),
                    "percent": getattr(memory, 'percent', None)
                },
                "swap_memory": {
                    "total": getattr(swap_memory, 'total', None),
                    "used": getattr(swap_memory, 'used', None),
                    "percent": getattr(swap_memory, 'percent', None)
                } if swap_memory else None
            },
            "disk": disk_status,
            "network": network_status,
            "process": {
                "cpu_top_10": cpu_top_10,
                "memory_top_10": memory_top_10
            }
        }

        return ResponseObject(data=status)

    except Exception as global_e:
        logging.error(f"Unexpected error in system status API: {global_e}")
        return ResponseObject(
            data={},
            error=f"Failed to retrieve system status: {str(global_e)}",
            status_code=500
        )


@app.get('/')
def index():
    return render_template('index.html')


def backGroundThread():
    global Configurations
    print(f"[WGDashboard] Background Thread #1 Started", flush=True)
    time.sleep(10)
    while True:
        with app.app_context():
            for c in Configurations.values():
                if c.getStatus():
                    try:
                        c.getPeersTransfer()
                        c.getPeersLatestHandshake()
                        c.getPeersEndpoint()
                        c.getPeersList()
                        c.getRestrictedPeersList()
                    except Exception as e:
                        print(f"[WGDashboard] Background Thread #1 Error: {str(e)}", flush=True)
        time.sleep(10)


def peerJobScheduleBackgroundThread():
    with app.app_context():
        print(f"[WGDashboard] Background Thread #2 Started", flush=True)
        time.sleep(10)
        while True:
            AllPeerJobs.runJob()
            time.sleep(15)
