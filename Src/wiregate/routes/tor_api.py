from flask import (Blueprint, request)
import os
import shutil
import subprocess
import requests
import re
import logging
from ..modules.App import (
    ResponseObject
)

from ..modules.ConfigEnv import (TORRC_PATH, DNS_TORRC_PATH)

import time
import socket

logger = logging.getLogger('wiregate')
import glob

tor_blueprint = Blueprint('tor', __name__)


@tor_blueprint.route('/tor/config', methods=['GET'])
def API_get_tor_config():
    logger.debug(" Entering get_tor_config()")
    try:
        configs = {}
        logger.debug(f" Checking for torrc at {TORRC_PATH}")
        if os.path.exists(TORRC_PATH):
            logger.debug(" Found main torrc file")
            with open(TORRC_PATH, 'r') as f:
                configs['main'] = f.read()
                logger.debug(f" Read {len(configs['main'])} bytes from main config")

        logger.debug(f" Checking for DNS torrc at {DNS_TORRC_PATH}")
        if os.path.exists(DNS_TORRC_PATH):
            logger.debug(" Found DNS torrc file") 
            with open(DNS_TORRC_PATH, 'r') as f:
                configs['dns'] = f.read()
                logger.debug(f" Read {len(configs['dns'])} bytes from DNS config")
        
        # Get current plugin type from torrc
        current_plugin = 'obfs4'  # default
        logger.debug(" Determining current plugin type")
        if configs.get('main'):
            logger.debug(" Checking main config content")
            if 'webtunnel' in configs['main']:
                logger.debug(" Found webtunnel plugin")
                current_plugin = 'webtunnel'
            elif 'snowflake' in configs['main']:
                logger.debug(" Found snowflake plugin")
                current_plugin = 'snowflake'
            else:
                logger.debug(" Using default obfs4 plugin")

        logger.debug(" Returning successful response")
        return ResponseObject(
            status=True,
            data={
                'configs': configs,
                'currentPlugin': current_plugin
            }
        )
    except Exception as e:
        logger.debug(f" Error occurred: {str(e)}")
        logging.error(f"Error reading Tor config: {str(e)}")
        return ResponseObject(
            status=False,
            message=f"Failed to load Tor configurations: {str(e)}",
            data=None
        )

@tor_blueprint.route('/tor/plugins', methods=['GET'])
def API_get_tor_plugins():
    logger.debug(" Getting available Tor plugins")
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
        logger.debug(f" Error getting plugins: {str(e)}")
        return ResponseObject(
            status=False,
            message=f"Failed to get available plugins: {str(e)}",
            data={
                'plugins': ['obfs4', 'webtunnel', 'snowflake']  # Fallback defaults
            }
        )

@tor_blueprint.route('/tor/config/update', methods=['POST'])
def API_update_tor_config():
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
            logger.debug(f" Sent HUP signal to Tor config: {config_path}")
        
        except subprocess.CalledProcessError as e:
            return ResponseObject(status=False, 
                                message=f"Failed to restart Tor: {e.stderr.decode()}")
            
        return ResponseObject(status=True, message="Configuration updated successfully")
    
    except Exception as e:
        return ResponseObject(status=False, message=f"Failed to update configuration: {str(e)}")

@tor_blueprint.route('/tor/plugin/update', methods=['POST'])
def API_update_tor_plugin():
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
def API_refresh_tor_bridges():
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

@tor_blueprint.route('/tor/process/control', methods=['POST'])
def API_control_tor_process():
    log_file = "tor_process_control.log"
    with open(log_file, "a") as log:
        log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Starting Tor process control ===\n")
        try:
            data = request.get_json()
            action = data.get('action')  # 'start' or 'stop'
            config_type = data.get('configType', 'main')
            
            log.write(f"Action: {action}\n")
            log.write(f"Config type: {config_type}\n")
            
            if not action or action not in ['start', 'stop']:
                log.write(f"ERROR: Invalid action: {action}\n")
                return ResponseObject(status=False, message="Invalid action. Use 'start' or 'stop'")
                
            # Log VANGUARD environment variable (masked)
            vanguard = os.environ.get('VANGUARD', '')
            masked_vanguard = "****" if vanguard else "NOT SET"
            log.write(f"VANGUARD environment variable: {masked_vanguard}\n")
            if not vanguard:
                log.write("WARNING: VANGUARD environment variable is not set\n")
            
            # Execute torflux with appropriate action (same pattern as traffic-weir)
            log.write(f"Executing: ./torflux -config {config_type} -action {action}\n")
            cmd = ['./torflux', '-config', config_type, '-action', action]
            try:
                from ..modules.Security import execute_secure_command
                result = execute_secure_command(cmd[0], cmd[1:])
            except ImportError:
                # Fallback to subprocess with restricted shell
                import subprocess
                result = subprocess.run(['/WireGate/restricted_shell.sh'] + cmd, 
                            capture_output=True, text=True)
                result = {
                    'success': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            log.write(f"Command stdout: {result['stdout']}\n")
            log.write(f"Command stderr: {result['stderr']}\n")
            logger.debug(f" {action.capitalize()}ed Tor process for {config_type} configuration")
            log.write(f"Successfully {action}ed Tor process for {config_type} configuration\n")
            
            if result['success']:
                return ResponseObject(
                    status=True, 
                    message=f"Tor process {action}ed successfully",
                    data={'action': action, 'configType': config_type}
                )
            else:
                error_msg = f"Failed to {action} Tor: {result['stderr']}"
                log.write(f"ERROR: {error_msg}\n")
                log.write(f"Command exit code: {result['returncode']}\n")
                return ResponseObject(status=False, message=error_msg)
                
        except Exception as e:
            error_msg = f"Failed to control Tor process: {str(e)}"
            log.write(f"EXCEPTION: {error_msg}\n")
            import traceback
            log.write(f"Traceback: {traceback.format_exc()}\n")
            return ResponseObject(status=False, message=error_msg)
        finally:
            log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Tor process control completed ===\n\n")

@tor_blueprint.route('/tor/process/status', methods=['GET'])
def API_get_tor_status():
    try:
        status = {
            'main': False,
            'dns': False
        }
        
        # Check if main Tor process is running
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(1)
            conn.connect(('127.0.0.1', 9051))
            conn.close()
            status['main'] = True
        except:
            pass
            
        # Check if DNS Tor process is running
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(1)
            conn.connect(('127.0.0.1', 9054))
            conn.close()
            status['dns'] = True
        except:
            pass
            
        return ResponseObject(
            status=True,
            data=status
        )
    except Exception as e:
        logger.debug(f" Error getting Tor status: {str(e)}")
        return ResponseObject(status=False, message=f"Failed to get Tor status: {str(e)}")

@tor_blueprint.route('/tor/logs/files', methods=['GET'])
def API_get_tor_log_files():
    try:
        config_type = request.args.get('configType', 'main')
        
        # Use the same log directory for both config types
        log_dir = "/var/log/tor"
        
        # Get list of log files
        log_files = []
        if os.path.exists(log_dir):
            # Include the appropriate log file based on config type
            main_log_file = "dnslog" if config_type == 'dns' else "log"
            if os.path.exists(f"{log_dir}/{main_log_file}"):
                log_files.append(main_log_file)
            # Add any other log files
            log_files.extend([os.path.basename(f) for f in glob.glob(f"{log_dir}/*.log") if os.path.basename(f) != main_log_file])
            # Add notices.log if it exists
            if os.path.exists(f"{log_dir}/notices.log") and "notices.log" not in log_files:
                log_files.append("notices.log")
        
        return ResponseObject(
            status=True,
            data={'files': log_files}
        )
    except Exception as e:
        logger.debug(f" Error getting log files: {str(e)}")
        return ResponseObject(status=False, message=f"Failed to get log files: {str(e)}")

@tor_blueprint.route('/tor/logs', methods=['GET'])
def API_get_tor_logs():
    try:
        config_type = request.args.get('configType', 'main')
        lines = int(request.args.get('lines', 100))
        file_name = request.args.get('file', '')
        
        # If no file specified, use the default log file based on config type
        if not file_name:
            file_name = "dnslog" if config_type == 'dns' else "log"
        
        # Validate lines parameter
        if lines <= 0 or lines > 5000:
            lines = 100  # Default to 100 if invalid
        
        # Use the same log directory for both config types
        log_dir = "/var/log/tor"
        log_path = os.path.join(log_dir, file_name)
        
        # Check if file exists
        if not os.path.exists(log_path):
            return ResponseObject(
                status=False,
                message=f"Log file not found: {file_name}"
            )
        
        # Read the last N lines from the log file
        content = ""
        try:
            # Use tail command for efficiency with large files
            result = subprocess.run(
                ['tail', '-n', str(lines), log_path],
                capture_output=True,
                text=True,
                check=True
            )
            content = result.stdout
        except subprocess.CalledProcessError:
            # Fallback to Python implementation if tail fails
            with open(log_path, 'r') as f:
                content = ''.join(f.readlines()[-lines:])
        
        return ResponseObject(
            status=True,
            data={'content': content}
        )
    except Exception as e:
        logger.debug(f" Error getting logs: {str(e)}")
        return ResponseObject(status=False, message=f"Failed to get logs: {str(e)}")

@tor_blueprint.route('/tor/logs/clear', methods=['POST'])
def API_clear_tor_logs():
    try:
        data = request.get_json()
        config_type = data.get('configType', 'main')
        file_name = data.get('file', '')
        
        # If no file specified, use the default log file based on config type
        if not file_name:
            file_name = "dnslog" if config_type == 'dns' else "log"
        
        # Use the same log directory for both config types
        log_dir = "/var/log/tor"
        log_path = os.path.join(log_dir, file_name)
        
        # Check if file exists
        if not os.path.exists(log_path):
            return ResponseObject(
                status=False,
                message=f"Log file not found: {file_name}"
            )
        
        # Clear the log file (truncate to zero size)
        with open(log_path, 'w') as f:
            pass
        
        return ResponseObject(
            status=True,
            message=f"Log file cleared successfully"
        )
    except Exception as e:
        logger.debug(f" Error clearing logs: {str(e)}")
        return ResponseObject(status=False, message=f"Failed to clear logs: {str(e)}")


