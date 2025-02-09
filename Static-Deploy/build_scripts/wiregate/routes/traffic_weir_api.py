from flask import Blueprint, request
import subprocess
from ..modules.shared import ResponseObject
from ..modules.Core import Configurations
from ..modules.shared import sqlSelect, sqlUpdate
from urllib.parse import unquote

traffic_weir_blueprint = Blueprint('traffic_weir', __name__)



@traffic_weir_blueprint.post('/set_peer_rate_limit')
def set_peer_rate_limit():
    """Set traffic rate limit for a WireGuard peer"""
    data = request.get_json()
    
    # Validate required parameters
    if not all(k in data for k in ['interface', 'peer_key', 'upload_rate', 'download_rate']):
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
            
        # Store rates as integers in database
        sqlUpdate(
            "UPDATE '%s' SET upload_rate_limit = ?, download_rate_limit = ? WHERE id = ?" % config.Name,
            (upload_rate, download_rate, peer.id)
        )
        
        # Execute traffic-weir command with both rates
        cmd = [
            './traffic-weir',
            '-interface', config.Name,
            '-peer', peer.id,
            '-upload-rate', str(upload_rate),
            '-download-rate', str(download_rate),
            '-protocol', protocol
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
def get_peer_rate_limit():
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
            
        # Get rate limits from database
        rate_limit_results = sqlSelect(
            "SELECT upload_rate_limit, download_rate_limit FROM '%s' WHERE id = ?" % interface,
            (peer.id,)
        ).fetchall()
        
        db_upload_rate = rate_limit_results[0]['upload_rate_limit'] if rate_limit_results else 0
        db_download_rate = rate_limit_results[0]['download_rate_limit'] if rate_limit_results else 0
        db_upload_rate = db_upload_rate or 0
        db_download_rate = db_download_rate or 0

        # Return in the format expected by the frontend
        return ResponseObject(
            status=True,
            message="Rate limits retrieved successfully",
            data={
                "upload_rate": float(db_upload_rate),
                "download_rate": float(db_download_rate)
            }
        )
        
    except Exception as e:
        print(f"[DEBUG] Error getting rate limits: {str(e)}")
        return ResponseObject(False, f"Error getting rate limits: {str(e)}")

@traffic_weir_blueprint.post('/remove_peer_rate_limit')
def remove_peer_rate_limit():
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
        
        # Clear rate limits in database
        sqlUpdate(
            "UPDATE '%s' SET upload_rate_limit = NULL, download_rate_limit = NULL WHERE id = ?" % config.Name,
            (peer.id,)
        )
        
        # Execute traffic-weir command with remove flag and protocol
        cmd = [
            './traffic-weir',
            '--interface', config.Name,
            '--peer', peer.id,
            '--protocol', protocol,
            '--remove'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return ResponseObject(False, f"Failed to remove rate limits: {result.stderr}")
            
        return ResponseObject(True, f"Rate limits removed successfully for peer {peer.id} on interface {config.Name}")
        
    except Exception as e:
        return ResponseObject(False, f"Error removing rate limits: {str(e)}")