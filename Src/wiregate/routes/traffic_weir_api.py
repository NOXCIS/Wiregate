from flask import Blueprint, request
import subprocess
import logging
from ..modules.App import ResponseObject
from ..modules.Core import Configurations
from ..modules.DataBase import get_redis_manager
# Import SecureCommand with fallback
try:
    from ..modules.Security import execute_secure_command
except ImportError:
    # Fallback function if SecureCommand is not available
    def execute_secure_command(command, args=None):
        import subprocess
        if args is None:
            args = []
        cmd = ['/WireGate/restricted_shell.sh', command] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
from urllib.parse import unquote

traffic_weir_blueprint = Blueprint('traffic_weir', __name__)
logger = logging.getLogger('wiregate')



@traffic_weir_blueprint.post('/set_peer_rate_limit')
def API_set_peer_rate_limit():
    """Set traffic rate limit for a WireGuard peer"""
    data = request.get_json()
    
    # Update required parameters
    if not all(k in data for k in ['interface', 'peer_key', 'upload_rate', 'download_rate', 'scheduler_type']):
        return ResponseObject(False, "Missing required parameters")
    
    try:
        # Validate scheduler type
        scheduler_type = data['scheduler_type']
        if scheduler_type not in ["htb", "hfsc", "cake"]:
            return ResponseObject(False, "Invalid scheduler type. Must be 'htb', 'hfsc', or 'cake'")
            
        # Get configuration object for the interface
        config = Configurations.get(data['interface'])
        if not config:
            return ResponseObject(False, f"Interface {data['interface']} not found")
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(data['peer_key'])
        if not found:
            return ResponseObject(False, f"Peer {data['peer_key']} not found in interface {config.Name}")
        
        # Get allowed IPs from the peer
        allowed_ips = peer.allowed_ip
        logger.debug(f" Getting allowed IPs for peer {peer.id}: {allowed_ips}")
        if not allowed_ips:
            logger.debug(f" No allowed IPs found for peer {peer.id}")
            return ResponseObject(False, "No allowed IPs found for peer")
        
        # Validate rates are positive numbers and convert to integer
        try:
            upload_rate = int(float(data['upload_rate']))
            download_rate = int(float(data['download_rate']))
            if upload_rate < 0 or download_rate < 0:
                return ResponseObject(False, "Rates must be positive numbers")
        except ValueError:
            return ResponseObject(False, "Invalid rate values")
            
        # Validate protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return ResponseObject(False, f"Invalid or unsupported protocol: {protocol}")
            
        # Store rates and scheduler type in database using Redis
        manager = get_redis_manager()
        updates = {
            'upload_rate_limit': upload_rate,
            'download_rate_limit': download_rate,
            'scheduler_type': scheduler_type
        }
        success = manager.update_record(config.Name, peer.id, updates)
        if not success:
            return ResponseObject(False, f"Failed to update rate limits in database for peer {peer.id}")
        
        # Execute traffic-weir command with both rates, scheduler type, and allowed IPs
        cmd = [
            '/WireGate/traffic-weir',
            '-interface', config.Name,
            '-peer', peer.id,
            '-upload-rate', str(upload_rate),
            '-download-rate', str(download_rate),
            '-protocol', protocol,
            '-scheduler', scheduler_type,
            '-allowed-ips', allowed_ips
        ]
        result = execute_secure_command(cmd[0], cmd[1:])
        
        success_msg = f"Successfully configured rate limiting for peer {peer.id} on interface {config.Name}"
        if success_msg in result['stdout']:
            return ResponseObject(True, success_msg)
        elif result['returncode'] != 0:
            error_msg = f"Failed to set rate limits. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return ResponseObject(False, error_msg)
        else:
            return ResponseObject(False, "Unexpected response from traffic-weir")
            
    except Exception as e:
        return ResponseObject(False, f"Error setting rate limits: {str(e)}")

@traffic_weir_blueprint.get('/get_peer_rate_limit')
def API_get_peer_rate_limit():
    """Get traffic rate limit for a WireGuard peer"""
    interface = request.args.get('interface')
    # Use unquote_plus to properly handle '+' characters
    peer_key = unquote(request.args.get('peer_key', '').replace(' ', '+'))
    
    if not interface or not peer_key:
        return ResponseObject(False, "Missing required parameters")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(interface)
        if not config:
            return ResponseObject(False, f"Interface {interface} not found")
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(peer_key)
        if not found:
            return ResponseObject(False, f"Peer {peer_key} not found in interface {config.Name}")
            
        # Get rate limits from database using Redis - check both main and restricted tables
        manager = get_redis_manager()
        
        # Try main table first
        peer_data = manager.get_record(interface, peer.id)
        if peer_data:
            rate_limit_results = [peer_data]
        else:
            # Try restricted table
            peer_data = manager.get_record(f"{interface}_restrict_access", peer.id)
            if peer_data:
                rate_limit_results = [peer_data]
            else:
                rate_limit_results = []
        
        # Handle different database result formats
        if rate_limit_results:
            result = rate_limit_results[0]
            # Try different ways to access the data
            if hasattr(result, 'upload_rate_limit'):
                db_upload_rate = result.upload_rate_limit
                db_download_rate = result.download_rate_limit
                db_scheduler_type = result.scheduler_type
            elif isinstance(result, dict):
                db_upload_rate = result.get('upload_rate_limit', 0)
                db_download_rate = result.get('download_rate_limit', 0)
                db_scheduler_type = result.get('scheduler_type', 'htb')
            else:
                # Fallback: try to access by index if it's a tuple/row
                try:
                    db_upload_rate = result[0] if len(result) > 0 else 0
                    db_download_rate = result[1] if len(result) > 1 else 0
                    db_scheduler_type = result[2] if len(result) > 2 else 'htb'
                except (IndexError, TypeError):
                    db_upload_rate = 0
                    db_download_rate = 0
                    db_scheduler_type = 'htb'
        else:
            db_upload_rate = 0
            db_download_rate = 0
            db_scheduler_type = 'htb'
        db_upload_rate = db_upload_rate or 0
        db_download_rate = db_download_rate or 0

        # Return in the format expected by the frontend
        return ResponseObject(
            status=True,
            message="Rate limits retrieved successfully",
            data={
                "upload_rate": float(db_upload_rate),
                "download_rate": float(db_download_rate),
                "scheduler_type": db_scheduler_type
            }
        )
        
    except Exception as e:
        logger.debug(f" Error getting rate limits: {str(e)}")
        return ResponseObject(False, f"Error getting rate limits: {str(e)}")

@traffic_weir_blueprint.post('/remove_peer_rate_limit')
def API_remove_peer_rate_limit():
    """Remove traffic rate limit for a WireGuard peer"""
    data = request.get_json()
    
    # Validate required parameters
    if not all(k in data for k in ['interface', 'peer_key']):
        return ResponseObject(False, "Missing required parameters")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(data['interface'])
        if not config:
            return ResponseObject(False, f"Interface {data['interface']} not found")
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(data['peer_key'])
        if not found:
            return ResponseObject(False, f"Peer {data['peer_key']} not found in interface {config.Name}")
        
        # Get protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return ResponseObject(False, f"Invalid or unsupported protocol: {protocol}")
        
        # Get allowed IPs and scheduler type from database using Redis
        manager = get_redis_manager()
        peer_data = manager.get_record(config.Name, peer.id)
        
        if not peer_data:
            return ResponseObject(False, "Could not find peer data in database")
        
        allowed_ips = peer_data.get('allowed_ip')
        if not allowed_ips:
            return ResponseObject(False, "Could not find allowed IPs for peer")
        
        scheduler_type = peer_data.get('scheduler_type', 'htb')
        
        # Clear rate limits in database
        updates = {
            'upload_rate_limit': None,
            'download_rate_limit': None,
            'scheduler_type': None
        }
        success = manager.update_record(config.Name, peer.id, updates)
        if not success:
            return ResponseObject(False, f"Failed to clear rate limits in database for peer {peer.id}")
        
        # Execute traffic-weir command with remove flag, protocol, scheduler type and allowed IPs
        cmd = [
            '/WireGate/traffic-weir',
            '--interface', config.Name,
            '--peer', peer.id,
            '--protocol', protocol,
            '--scheduler', scheduler_type,
            '--allowed-ips', allowed_ips,
            '--remove'
        ]
        
        result = execute_secure_command(cmd[0], cmd[1:])
        
        if result['returncode'] != 0:
            error_msg = f"Failed to remove rate limits. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return ResponseObject(False, error_msg)

        return ResponseObject(True, f"Rate limits removed successfully for peer {peer.id} on interface {config.Name}")
        
    except Exception as e:
        return ResponseObject(False, f"Error removing rate limits: {str(e)}")

@traffic_weir_blueprint.get('/get_interface_scheduler')
def API_get_interface_scheduler():
    """Get the scheduler type for an interface if any peer has it set"""
    interface = request.args.get('interface')
    
    logger.debug(f" get_interface_scheduler called with interface: {interface}")
    
    if not interface:
        logger.debug(" Missing interface parameter")
        return ResponseObject(False, "Missing interface parameter")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(interface)
        logger.debug(f" Retrieved config for interface {interface}: {config is not None}")
        
        if not config:
            logger.debug(f" Interface {interface} not found")
            return ResponseObject(False, f"Interface {interface} not found")
        
        # Query for any peer with a non-zero rate limit and their scheduler type using Redis
        manager = get_redis_manager()
        
        # Get all peers from the interface
        all_peers = manager.get_all_records(interface)
        logger.debug(f" Found {len(all_peers)} peers in interface {interface}")
        
        # Find peers with rate limits set
        rate_limited_peers = []
        for peer_data in all_peers:
            upload_limit = peer_data.get('upload_rate_limit', 0)
            download_limit = peer_data.get('download_rate_limit', 0)
            scheduler_type = peer_data.get('scheduler_type', '')
            
            # Check if peer has rate limits set
            if (scheduler_type and scheduler_type.strip() and 
                (upload_limit and upload_limit > 0) or (download_limit and download_limit > 0)):
                rate_limited_peers.append(peer_data)
        
        logger.debug(f" Found {len(rate_limited_peers)} rate-limited peers")
        
        # Get the first scheduler type found
        result_dict = None
        if rate_limited_peers:
            result_dict = {'scheduler_type': rate_limited_peers[0].get('scheduler_type', 'htb')}
        
        logger.debug(f" Result as dict: {result_dict}")
        
        # If no peers have rate limits set, return unlocked with default scheduler
        if not result_dict:
            logger.debug(" No rate-limited peers found")
            return ResponseObject(
                status=True,
                message="No rate-limited peers found",
                data={
                    "scheduler_type": "htb",  # Default scheduler type
                    "locked": False
                }
            )
        
        # Return the found scheduler type and locked status
        response_data = {
            "scheduler_type": result_dict['scheduler_type'] if result_dict else 'htb',
            "locked": True  # Locked because we found an active rate limit
        }
        logger.debug(f" Returning response data: {response_data}")
        
        return ResponseObject(
            status=True,
            message="Interface scheduler type retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.debug(f" Error in get_interface_scheduler: {str(e)}")
        return ResponseObject(False, f"Error getting interface scheduler: {str(e)}")

@traffic_weir_blueprint.post('/nuke_interface')
def API_nuke_interface():
    """Remove all traffic control qdiscs from an interface"""
    data = request.get_json()
    
    # Validate required parameter
    if 'interface' not in data:
        return ResponseObject(False, "Missing interface parameter")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(data['interface'])
        if not config:
            return ResponseObject(False, f"Interface {data['interface']} not found")
        
        # Get protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return ResponseObject(False, f"Invalid or unsupported protocol: {protocol}")
        
        # Execute traffic-weir command with nuke flag
        cmd = [
            '/WireGate/traffic-weir',
            '--interface', config.Name,
            '--protocol', protocol,
            '--nuke'
        ]
        
        result = execute_secure_command(cmd[0], cmd[1:])
        
        if result['returncode'] != 0:
            error_msg = f"Failed to nuke interface. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return ResponseObject(False, error_msg)
            
        success_msg = f"Successfully nuked all traffic control on interface {config.Name}"
        return ResponseObject(True, success_msg)
        
    except Exception as e:
        return ResponseObject(False, f"Error nuking interface: {str(e)}")