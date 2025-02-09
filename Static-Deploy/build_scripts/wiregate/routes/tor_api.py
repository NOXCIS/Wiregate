from flask import (Blueprint, request)
import os
import shutil
import subprocess
import requests
import re
import logging
from ..modules.shared import (
    ResponseObject
)

from ..modules.config import (TORRC_PATH, DNS_TORRC_PATH)

tor_blueprint = Blueprint('tor', __name__)


@tor_blueprint.route('/tor/config', methods=['GET'])
def get_tor_config():
    print("[DEBUG] Entering get_tor_config()")
    try:
        configs = {}
        print(f"[DEBUG] Checking for torrc at {TORRC_PATH}")
        if os.path.exists(TORRC_PATH):
            print("[DEBUG] Found main torrc file")
            with open(TORRC_PATH, 'r') as f:
                configs['main'] = f.read()
                print(f"[DEBUG] Read {len(configs['main'])} bytes from main config")

        print(f"[DEBUG] Checking for DNS torrc at {DNS_TORRC_PATH}")
        if os.path.exists(DNS_TORRC_PATH):
            print("[DEBUG] Found DNS torrc file") 
            with open(DNS_TORRC_PATH, 'r') as f:
                configs['dns'] = f.read()
                print(f"[DEBUG] Read {len(configs['dns'])} bytes from DNS config")
        
        # Get current plugin type from torrc
        current_plugin = 'obfs4'  # default
        print("[DEBUG] Determining current plugin type")
        if configs.get('main'):
            print("[DEBUG] Checking main config content")
            if 'webtunnel' in configs['main']:
                print("[DEBUG] Found webtunnel plugin")
                current_plugin = 'webtunnel'
            elif 'snowflake' in configs['main']:
                print("[DEBUG] Found snowflake plugin")
                current_plugin = 'snowflake'
            else:
                print("[DEBUG] Using default obfs4 plugin")

        print("[DEBUG] Returning successful response")
        return ResponseObject(
            status=True,
            data={
                'configs': configs,
                'currentPlugin': current_plugin
            }
        )
    except Exception as e:
        print(f"[DEBUG] Error occurred: {str(e)}")
        logging.error(f"Error reading Tor config: {str(e)}")
        return ResponseObject(
            status=False,
            message=f"Failed to load Tor configurations: {str(e)}",
            data=None
        )

@tor_blueprint.route('/tor/plugins', methods=['GET'])
def get_tor_plugins():
    print("[DEBUG] Getting available Tor plugins")
    try:
        # Default available plugins
        plugins = ['obfs4', 'webtunnel', 'snowflake']
        
        # Return in the format expected by the frontend
        return ResponseObject(
            status=True,
            data={
                'plugins': plugins
            }
        )
    except Exception as e:
        print(f"[DEBUG] Error getting plugins: {str(e)}")
        return ResponseObject(
            status=False,
            message=f"Failed to get available plugins: {str(e)}",
            data={
                'plugins': ['obfs4', 'webtunnel', 'snowflake']  # Fallback defaults
            }
        )

@tor_blueprint.route('/tor/config/update', methods=['POST'])
def update_tor_config():
    try:
        data = request.get_json()
        config_type = data.get('type', 'main')
        content = data.get('content')
        plugin = data.get('plugin')
        
        if not content:
            return ResponseObject(status=False, message="No configuration content provided")
            
        config_path = TORRC_PATH if config_type == 'main' else DNS_TORRC_PATH
        
        # Backup existing config
        if os.path.exists(config_path):
            shutil.copy2(config_path, f"{config_path}.bak")
            
        # Write new config
        with open(config_path, 'w') as f:
            f.write(content)
            
        # Send HUP signal via torflux instead of killing process
        config_type = 'main' if config_path == TORRC_PATH else 'dns'
        try:
            subprocess.run(['./torflux', '-config', config_type], 
                        check=True, 
                        capture_output=True)
            print(f"[DEBUG] Sent HUP signal to Tor config: {config_path}")
        
        except subprocess.CalledProcessError as e:
            return ResponseObject(status=False, 
                                message=f"Failed to restart Tor: {e.stderr.decode()}")
            
        return ResponseObject(status=True, message="Configuration updated successfully")
    
    except Exception as e:
        return ResponseObject(status=False, message=f"Failed to update configuration: {str(e)}")

@tor_blueprint.route('/tor/plugin/update', methods=['POST'])
def update_tor_plugin():
    try:
        data = request.get_json()
        plugin = data.get('plugin')
        config_type = data.get('configType', 'main')
        use_bridges = data.get('useBridges', True)
        
        if not plugin:
            return ResponseObject(status=False, message="No plugin specified")
            
        config_path = TORRC_PATH if config_type == 'main' else DNS_TORRC_PATH
        
        # Read current config
        with open(config_path, 'r') as f:
            config_lines = f.readlines()
            
        # Keep all lines except UseBridges, Bridge, and ClientTransportPlugin entries
        new_config = [line for line in config_lines 
                     if not line.startswith('Bridge') and 
                     not line.startswith('UseBridges') and
                     not line.startswith('ClientTransportPlugin')]
            
        # Add plugin line if not present
        plugin_line = f"ClientTransportPlugin {plugin} exec /usr/local/bin/{plugin}\n"
        new_config.append(plugin_line)

        # Add bridges configuration if enabled
        if use_bridges:
            new_config.insert(0, "UseBridges 1\n")  # Add at the beginning
            if plugin == 'snowflake':
                new_config.extend([
                    "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn\n",
                    "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn\n"
                ])
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(new_config)
            
        return ResponseObject(
            status=True,
            message=f"Configuration updated successfully",
            data={'config': ''.join(new_config)}
        )
    except Exception as e:
        return ResponseObject(status=False, message=f"Failed to update configuration: {str(e)}")

@tor_blueprint.route('/tor/bridges/refresh', methods=['POST'])
def refresh_tor_bridges():
    try:
        data = request.get_json()
        plugin = data.get('plugin')
        config_type = data.get('configType', 'main')
        
        if not plugin:
            return ResponseObject(status=False, message="No plugin specified")
            
        config_path = TORRC_PATH if config_type == 'main' else DNS_TORRC_PATH
        
        # Get new bridges based on plugin type
        if plugin == 'webtunnel':
            BRIDGEDB_URL = "https://bridges.torproject.org/bridges?transport=webtunnel"
            response = requests.get(BRIDGEDB_URL)
            bridges = re.findall(r'(webtunnel [^<]*)<br/>', response.text)
        elif plugin == 'obfs4':
            BRIDGEDB_URL = "https://bridges.torproject.org/bridges?transport=obfs4"
            response = requests.get(BRIDGEDB_URL)
            bridges = re.findall(r'(obfs4 [^<]*)<br/>', response.text)
            bridges = [bridge.replace('&#43;', '+') for bridge in bridges]
        else:
            return ResponseObject(status=False, message="Invalid plugin type for bridge refresh")

        if not bridges:
            return ResponseObject(status=False, message="No bridges found")

        # Read current config
        with open(config_path, 'r') as f:
            config_lines = f.readlines()
            
        # Remove old bridge lines and add new ones
        new_config = []
        for line in config_lines:
            if not line.startswith('Bridge'):
                new_config.append(line)
                
        # Add UseBridges directive if not present
        if not any('UseBridges 1' in line for line in new_config):
            new_config.append('UseBridges 1\n')
            
        # Add new bridges
        for bridge in bridges:
            new_config.append(f'Bridge {bridge}\n')
            
        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(new_config)
            
        return ResponseObject(
            status=True,
            message=f"Bridges refreshed successfully",
            data={'config': ''.join(new_config)}
        )
    except Exception as e:
        return ResponseObject(status=False, message=f"Failed to refresh bridges: {str(e)}")


