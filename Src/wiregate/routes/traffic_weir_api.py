from flask import Blueprint, request
import subprocess
from ..modules.App import ResponseObject
from ..modules.Core import Configurations
from ..modules.DataBase.DataBaseManager import sqlSelect, sqlUpdate
from urllib.parse import unquote

traffic_weir_blueprint = Blueprint('traffic_weir', __name__)



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
        if scheduler_type not in ["htb", "hfsc"]:
            return ResponseObject(False, "Invalid scheduler type. Must be 'htb' or 'hfsc'")
            
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
        print(f"[DEBUG] Getting allowed IPs for peer {peer.id}: {allowed_ips}")
        if not allowed_ips:
            print(f"[DEBUG] No allowed IPs found for peer {peer.id}")
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
            
        # Store rates and scheduler type in database
        sql = "UPDATE '%s' SET upload_rate_limit = ?, download_rate_limit = ?, scheduler_type = ? WHERE id = ?" % config.Name
        params = (upload_rate, download_rate, scheduler_type, peer.id)
        sqlUpdate(sql, params)
        
        # Execute traffic-weir command with both rates, scheduler type, and allowed IPs
        cmd = [
            './traffic-weir',
            '-interface', config.Name,
            '-peer', peer.id,
            '-upload-rate', str(upload_rate),
            '-download-rate', str(download_rate),
            '-protocol', protocol,
            '-scheduler', scheduler_type,
            '-allowed-ips', allowed_ips
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        success_msg = f"Successfully configured rate limiting for peer {peer.id} on interface {config.Name}"
        if success_msg in result.stdout:
            return ResponseObject(True, success_msg)
        elif result.returncode != 0:
            error_msg = f"Failed to set rate limits. Exit code: {result.returncode}\n"
            error_msg += f"stdout: {result.stdout}\n"
            error_msg += f"stderr: {result.stderr}\n"
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
            
        # Get rate limits from database - check both main and restricted tables
        rate_limit_results = sqlSelect(
            "SELECT upload_rate_limit, download_rate_limit, scheduler_type FROM '%s' WHERE id = ?" % interface,
            (peer.id,)
        ).fetchall()
        
        # If not found in main table, check restricted table
        if not rate_limit_results:
            rate_limit_results = sqlSelect(
                "SELECT upload_rate_limit, download_rate_limit, scheduler_type FROM '%s_restrict_access' WHERE id = ?" % interface,
                (peer.id,)
            ).fetchall()
        
        db_upload_rate = rate_limit_results[0]['upload_rate_limit'] if rate_limit_results else 0
        db_download_rate = rate_limit_results[0]['download_rate_limit'] if rate_limit_results else 0
        db_scheduler_type = rate_limit_results[0]['scheduler_type'] if rate_limit_results else 'htb'
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
        print(f"[DEBUG] Error getting rate limits: {str(e)}")
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
        
        # Get allowed IPs from database
        peer_data = sqlSelect(
            "SELECT allowed_ip FROM '%s' WHERE id = ?" % config.Name,
            (peer.id,)
        ).fetchone()
        
        allowed_ips = peer_data['allowed_ip'] if peer_data else None
        
        if not allowed_ips:
            return ResponseObject(False, "Could not find allowed IPs for peer")
        
         # Clear rate limits in database
        sqlUpdate(
            "UPDATE '%s' SET upload_rate_limit = NULL, download_rate_limit = NULL WHERE id = ?" % config.Name,
            (peer.id,)
        )
        
        # Execute traffic-weir command with remove flag, protocol and allowed IPs
        cmd = [
            './traffic-weir',
            '--interface', config.Name,
            '--peer', peer.id,
            '--protocol', protocol,
            '--allowed-ips', allowed_ips,
            '--remove'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return ResponseObject(False, f"Failed to remove rate limits: {result.stderr}")
            
       

        return ResponseObject(True, f"Rate limits removed successfully for peer {peer.id} on interface {config.Name}")
        
    except Exception as e:
        return ResponseObject(False, f"Error removing rate limits: {str(e)}")

@traffic_weir_blueprint.get('/get_interface_scheduler')
def API_get_interface_scheduler():
    """Get the scheduler type for an interface if any peer has it set"""
    interface = request.args.get('interface')
    
    print(f"[DEBUG] get_interface_scheduler called with interface: {interface}")
    
    if not interface:
        print("[DEBUG] Missing interface parameter")
        return ResponseObject(False, "Missing interface parameter")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(interface)
        print(f"[DEBUG] Retrieved config for interface {interface}: {config is not None}")
        
        if not config:
            print(f"[DEBUG] Interface {interface} not found")
            return ResponseObject(False, f"Interface {interface} not found")
        
        # Query for any peer with a non-zero rate limit and their scheduler type
        sql = f"""
            SELECT DISTINCT scheduler_type 
            FROM '{interface}' 
            WHERE scheduler_type IS NOT NULL 
            AND scheduler_type != '' 
            AND (upload_rate_limit > 0 OR download_rate_limit > 0) 
            LIMIT 1
        """
        print(f"[DEBUG] Executing SQL query: {sql}")
        
        result = sqlSelect(sql).fetchone()
        print(f"[DEBUG] SQL query result: {result}")
        
        # Convert result to dict for debugging
        result_dict = dict(result) if result else None
        print(f"[DEBUG] Result as dict: {result_dict}")
        
        # If no peers have rate limits set, return unlocked with default scheduler
        if not result:
            print("[DEBUG] No rate-limited peers found")
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
        print(f"[DEBUG] Returning response data: {response_data}")
        
        return ResponseObject(
            status=True,
            message="Interface scheduler type retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        print(f"[DEBUG] Error in get_interface_scheduler: {str(e)}")
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
            './traffic-weir',
            '--interface', config.Name,
            '--protocol', protocol,
            '--nuke'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Failed to nuke interface. Exit code: {result.returncode}\n"
            error_msg += f"stdout: {result.stdout}\n"
            error_msg += f"stderr: {result.stderr}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return ResponseObject(False, error_msg)
            
        success_msg = f"Successfully nuked all traffic control on interface {config.Name}"
        return ResponseObject(True, success_msg)
        
    except Exception as e:
        return ResponseObject(False, f"Error nuking interface: {str(e)}")