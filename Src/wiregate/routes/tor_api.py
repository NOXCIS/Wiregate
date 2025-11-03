"""
FastAPI Tor Router
Migrated from tor_api.py Flask blueprint
"""
import os
import shutil
import subprocess
import requests
import re
import logging
import time
import socket
import glob
from fastapi import APIRouter, Query, Depends
from typing import Dict, Any, List

from ..models.responses import StandardResponse
from ..models.requests import TorConfigUpdate, TorPluginUpdate, TorProcessControl
from ..modules.Config import TORRC_PATH, DNS_TORRC_PATH
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.get('/tor/config', response_model=StandardResponse)
async def get_tor_config(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get Tor configuration files"""
    logger.debug("Entering get_tor_config()")
    try:
        configs = {}
        logger.debug(f"Checking for torrc at {TORRC_PATH}")
        if os.path.exists(TORRC_PATH):
            logger.debug("Found main torrc file")
            with open(TORRC_PATH, 'r') as f:
                configs['main'] = f.read()
                logger.debug(f"Read {len(configs['main'])} bytes from main config")
        
        logger.debug(f"Checking for DNS torrc at {DNS_TORRC_PATH}")
        if os.path.exists(DNS_TORRC_PATH):
            logger.debug("Found DNS torrc file")
            with open(DNS_TORRC_PATH, 'r') as f:
                configs['dns'] = f.read()
                logger.debug(f"Read {len(configs['dns'])} bytes from DNS config")
        
        # Get current plugin type from each config
        plugins = {}
        logger.debug("Determining current plugin type for each config")
        
        def detect_plugin(config_content):
            """Detect plugin type from config content by checking ClientTransportPlugin directive"""
            if not config_content:
                return 'obfs4'
            
            # Search for ClientTransportPlugin directive
            lines = config_content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('ClientTransportPlugin'):
                    # Extract plugin name from: ClientTransportPlugin <plugin> exec ...
                    parts = line.split()
                    if len(parts) >= 2:
                        plugin = parts[1]
                        if plugin in ['obfs4', 'webtunnel', 'snowflake']:
                            return plugin
            # If no ClientTransportPlugin found, check for plugin keywords as fallback
            if 'webtunnel' in config_content:
                return 'webtunnel'
            elif 'snowflake' in config_content:
                return 'snowflake'
            return 'obfs4'
        
        # Detect plugin for main config
        if configs.get('main'):
            logger.debug("Checking main config content")
            plugins['main'] = detect_plugin(configs['main'])
            logger.debug(f"Detected plugin for main: {plugins['main']}")
        else:
            plugins['main'] = 'obfs4'
        
        # Detect plugin for DNS config
        if configs.get('dns'):
            logger.debug("Checking DNS config content")
            plugins['dns'] = detect_plugin(configs['dns'])
            logger.debug(f"Detected plugin for DNS: {plugins['dns']}")
        else:
            plugins['dns'] = 'obfs4'
        
        logger.debug(f"Detected plugins: {plugins}")
        logger.debug("Returning successful response")
        return StandardResponse(
            status=True,
            data={
                'configs': configs,
                'plugins': plugins
            }
        )
    except Exception as e:
        logger.debug(f"Error occurred: {str(e)}")
        logger.error(f"Error reading Tor config: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to load Tor configurations: {str(e)}"
        )


@router.get('/tor/plugins', response_model=StandardResponse)
async def get_tor_plugins(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get available Tor plugins"""
    logger.debug("Getting available Tor plugins")
    try:
        plugins = ['obfs4', 'webtunnel', 'snowflake']
        
        return StandardResponse(
            status=True,
            data={'plugins': plugins}
        )
    except Exception as e:
        logger.debug(f"Error getting plugins: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to get available plugins: {str(e)}",
            data={'plugins': ['obfs4', 'webtunnel', 'snowflake']}
        )


@router.post('/tor/config/update', response_model=StandardResponse)
async def update_tor_config(
    config_update: TorConfigUpdate,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update Tor configuration"""
    try:
        if not config_update.content:
            return StandardResponse(
                status=False,
                message="No configuration content provided"
            )
            
        config_path = TORRC_PATH if config_update.type == 'main' else DNS_TORRC_PATH
        
        # Backup existing config
        if os.path.exists(config_path):
            shutil.copy2(config_path, f"{config_path}.bak")
            
        # Write new config
        with open(config_path, 'w') as f:
            f.write(config_update.content)
            
        # Send HUP signal via torflux
        config_type = 'main' if config_path == TORRC_PATH else 'dns'
        try:
            subprocess.run(
                ['./torflux', '-config', config_type],
                check=True,
                capture_output=True
            )
            logger.debug(f"Sent HUP signal to Tor config: {config_path}")
        except subprocess.CalledProcessError as e:
            return StandardResponse(
                status=False,
                message=f"Failed to restart Tor: {e.stderr.decode()}"
            )
            
        return StandardResponse(
            status=True,
            message="Configuration updated successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update configuration: {str(e)}"
        )


@router.post('/tor/plugin/update', response_model=StandardResponse)
async def update_tor_plugin(
    plugin_update: TorPluginUpdate,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update Tor plugin"""
    try:
        config_path = TORRC_PATH if plugin_update.configType == 'main' else DNS_TORRC_PATH
        
        # Read current config
        with open(config_path, 'r') as f:
            config_lines = f.readlines()
            
        # Keep all lines except UseBridges, Bridge, and ClientTransportPlugin
        new_config = [
            line for line in config_lines 
            if not line.startswith('Bridge') and 
            not line.startswith('UseBridges') and
            not line.startswith('ClientTransportPlugin')
        ]
            
        # Add plugin line
        plugin_line = f"ClientTransportPlugin {plugin_update.plugin} exec /usr/local/bin/{plugin_update.plugin}\n"
        new_config.append(plugin_line)
        
        # Add bridges configuration if enabled
        if plugin_update.useBridges:
            new_config.insert(0, "UseBridges 1\n")
            if plugin_update.plugin == 'snowflake':
                new_config.extend([
                    "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn\n",
                    "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn\n"
                ])
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(new_config)
            
        return StandardResponse(
            status=True,
            message=f"Configuration updated successfully",
            data={'config': ''.join(new_config)}
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update configuration: {str(e)}"
        )


@router.post('/tor/bridges/refresh', response_model=StandardResponse)
async def refresh_tor_bridges(
    refresh_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Refresh Tor bridges from BridgeDB"""
    try:
        plugin = refresh_data.get('plugin')
        config_type = refresh_data.get('configType', 'main')
        
        if not plugin:
            return StandardResponse(
                status=False,
                message="No plugin specified"
            )
            
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
            return StandardResponse(
                status=False,
                message="Invalid plugin type for bridge refresh"
            )
        
        if not bridges:
            return StandardResponse(
                status=False,
                message="No bridges found"
            )
        
        # Read current config
        with open(config_path, 'r') as f:
            config_lines = f.readlines()
            
        # Remove old bridge lines and add new ones
        new_config = [line for line in config_lines if not line.startswith('Bridge')]
                
        # Add UseBridges directive if not present
        if not any('UseBridges 1' in line for line in new_config):
            new_config.append('UseBridges 1\n')
            
        # Add new bridges
        for bridge in bridges:
            new_config.append(f'Bridge {bridge}\n')
            
        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(new_config)
            
        return StandardResponse(
            status=True,
            message=f"Bridges refreshed successfully",
            data={'config': ''.join(new_config)}
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to refresh bridges: {str(e)}"
        )


@router.post('/tor/process/control', response_model=StandardResponse)
async def control_tor_process(
    control_data: TorProcessControl,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Control Tor process (start/stop)"""
    log_file = "tor_process_control.log"
    with open(log_file, "a") as log:
        log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Starting Tor process control ===\n")
        try:
            log.write(f"Action: {control_data.action}\n")
            log.write(f"Config type: {control_data.configType}\n")
            
            # Log VANGUARD environment variable (masked)
            vanguard = os.environ.get('VANGUARD', '')
            masked_vanguard = "****" if vanguard else "NOT SET"
            log.write(f"VANGUARD environment variable: {masked_vanguard}\n")
            if not vanguard:
                log.write("WARNING: VANGUARD environment variable is not set\n")
            
            # Execute torflux
            log.write(f"Executing: ./torflux -config {control_data.configType} -action {control_data.action}\n")
            cmd = ['./torflux', '-config', control_data.configType, '-action', control_data.action]
            
            try:
                from ..modules.Security import execute_secure_command
                result = execute_secure_command(cmd[0], cmd[1:])
            except ImportError:
                import subprocess
                result = subprocess.run(
                    ['/WireGate/restricted_shell.sh'] + cmd,
                    capture_output=True,
                    text=True
                )
                result = {
                    'success': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            
            log.write(f"Command stdout: {result['stdout']}\n")
            log.write(f"Command stderr: {result['stderr']}\n")
            logger.debug(f"{control_data.action.capitalize()}ed Tor process for {control_data.configType} configuration")
            log.write(f"Successfully {control_data.action}ed Tor process for {control_data.configType} configuration\n")
            
            if result['success']:
                return StandardResponse(
                    status=True,
                    message=f"Tor process {control_data.action}ed successfully",
                    data={'action': control_data.action, 'configType': control_data.configType}
                )
            else:
                error_msg = f"Failed to {control_data.action} Tor: {result['stderr']}"
                log.write(f"ERROR: {error_msg}\n")
                log.write(f"Command exit code: {result['returncode']}\n")
                return StandardResponse(status=False, message=error_msg)
                
        except Exception as e:
            error_msg = f"Failed to control Tor process: {str(e)}"
            log.write(f"EXCEPTION: {error_msg}\n")
            import traceback
            log.write(f"Traceback: {traceback.format_exc()}\n")
            return StandardResponse(status=False, message=error_msg)
        finally:
            log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Tor process control completed ===\n\n")


@router.get('/tor/process/status', response_model=StandardResponse)
async def get_tor_status(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get Tor process status"""
    try:
        status_dict = {
            'main': False,
            'dns': False
        }
        
        # Check if main Tor process is running
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(1)
            conn.connect(('127.0.0.1', 9051))
            conn.close()
            status_dict['main'] = True
        except:
            pass
            
        # Check if DNS Tor process is running
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(1)
            conn.connect(('127.0.0.1', 9054))
            conn.close()
            status_dict['dns'] = True
        except:
            pass
            
        return StandardResponse(
            status=True,
            data=status_dict
        )
    except Exception as e:
        logger.debug(f"Error getting Tor status: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to get Tor status: {str(e)}"
        )


@router.get('/tor/logs/files', response_model=StandardResponse)
async def get_tor_log_files(
    configType: str = Query(default='main', description="Config type (main/dns)"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get list of Tor log files"""
    try:
        log_dir = "/var/log/tor"
        
        # Get list of log files
        log_files = []
        if os.path.exists(log_dir):
            main_log_file = "dnslog" if configType == 'dns' else "log"
            if os.path.exists(f"{log_dir}/{main_log_file}"):
                log_files.append(main_log_file)
            
            # Add any other log files
            log_files.extend([
                os.path.basename(f) for f in glob.glob(f"{log_dir}/*.log")
                if os.path.basename(f) != main_log_file
            ])
            
            # Add notices.log if it exists
            if os.path.exists(f"{log_dir}/notices.log") and "notices.log" not in log_files:
                log_files.append("notices.log")
        
        return StandardResponse(
            status=True,
            data={'files': log_files}
        )
    except Exception as e:
        logger.debug(f"Error getting log files: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to get log files: {str(e)}"
        )


@router.get('/tor/logs', response_model=StandardResponse)
async def get_tor_logs(
    configType: str = Query(default='main', description="Config type (main/dns)"),
    lines: int = Query(default=100, ge=1, le=5000, description="Number of lines to retrieve"),
    file: str = Query(default='', description="Log file name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get Tor logs"""
    try:
        # Validate configType
        if configType not in ['main', 'dns']:
            return StandardResponse(
                status=False,
                message="Invalid config type. Must be 'main' or 'dns'"
            )
        
        # If no file specified, use default based on config type
        file_name = file if file else ("dnslog" if configType == 'dns' else "log")
        
        # Validate filename to prevent path traversal
        from ..modules.Security import security_manager
        is_valid, error_msg = security_manager.validate_filename(file_name)
        if not is_valid:
            return StandardResponse(
                status=False,
                message=f"Invalid log file name: {error_msg}"
            )
        
        # Additional path traversal check
        if '..' in file_name or os.path.isabs(file_name) or '/' in file_name or '\\' in file_name:
            return StandardResponse(
                status=False,
                message="Invalid log file name: path traversal detected"
            )
        
        # Use the same log directory for both config types
        log_dir = "/var/log/tor"
        log_path = os.path.join(log_dir, file_name)
        
        # Ensure resolved path is within log directory
        resolved_log = os.path.abspath(log_path)
        resolved_dir = os.path.abspath(log_dir)
        if not resolved_log.startswith(resolved_dir):
            return StandardResponse(
                status=False,
                message="Invalid log file path: path outside allowed directory"
            )
        
        # Check if file exists
        if not os.path.exists(log_path):
            return StandardResponse(
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
        
        return StandardResponse(
            status=True,
            data={'content': content}
        )
    except Exception as e:
        logger.debug(f"Error getting logs: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to get logs: {str(e)}"
        )


@router.post('/tor/logs/clear', response_model=StandardResponse)
async def clear_tor_logs(
    clear_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Clear Tor logs"""
    try:
        config_type = clear_data.get('configType', 'main')
        file_name = clear_data.get('file', '')
        
        # If no file specified, use default based on config type
        if not file_name:
            file_name = "dnslog" if config_type == 'dns' else "log"
        
        # Use the same log directory for both config types
        log_dir = "/var/log/tor"
        log_path = os.path.join(log_dir, file_name)
        
        # Check if file exists
        if not os.path.exists(log_path):
            return StandardResponse(
                status=False,
                message=f"Log file not found: {file_name}"
            )
        
        # Clear the log file (truncate to zero size)
        with open(log_path, 'w') as f:
            pass
        
        return StandardResponse(
            status=True,
            message=f"Log file cleared successfully"
        )
    except Exception as e:
        logger.debug(f"Error clearing logs: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to clear logs: {str(e)}"
        )

