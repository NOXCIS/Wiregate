"""
FastAPI Traffic Weir Router
Migrated from traffic_weir_api.py Flask blueprint
"""
import logging
from fastapi import APIRouter, Query, Depends
from urllib.parse import unquote
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..models.requests import RateLimitSet
from ..modules.Core import Configurations
from ..modules.DataBase import get_redis_manager
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

# Import SecureCommand with fallback
try:
    from ..modules.Security import execute_secure_command
except ImportError:
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

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.post('/set_peer_rate_limit', response_model=StandardResponse)
async def set_peer_rate_limit(
    rate_limit_data: RateLimitSet,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Set traffic rate limit for a WireGuard peer"""
    try:
        # Get configuration object for the interface
        config = Configurations.get(rate_limit_data.interface)
        if not config:
            return StandardResponse(
                status=False,
                message=f"Interface {rate_limit_data.interface} not found"
            )
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(rate_limit_data.peer_key)
        if not found:
            return StandardResponse(
                status=False,
                message=f"Peer {rate_limit_data.peer_key} not found in interface {config.Name}"
            )
        
        # Get allowed IPs from the peer
        allowed_ips = peer.allowed_ip
        logger.debug(f"Getting allowed IPs for peer {peer.id}: {allowed_ips}")
        if not allowed_ips:
            logger.debug(f"No allowed IPs found for peer {peer.id}")
            return StandardResponse(
                status=False,
                message="No allowed IPs found for peer"
            )
        
        # Validate protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return StandardResponse(
                status=False,
                message=f"Invalid or unsupported protocol: {protocol}"
            )
            
        # Store rates and scheduler type in database
        manager = await get_redis_manager()
        updates = {
            'upload_rate_limit': rate_limit_data.upload_rate,
            'download_rate_limit': rate_limit_data.download_rate,
            'scheduler_type': rate_limit_data.scheduler_type
        }
        success = manager.update_record(config.Name, peer.id, updates)
        if not success:
            return StandardResponse(
                status=False,
                message=f"Failed to update rate limits in database for peer {peer.id}"
            )
        
        # Execute traffic-weir command
        cmd = [
            '/WireGate/traffic-weir',
            '-interface', config.Name,
            '-peer', peer.id,
            '-upload-rate', str(rate_limit_data.upload_rate),
            '-download-rate', str(rate_limit_data.download_rate),
            '-protocol', protocol,
            '-scheduler', rate_limit_data.scheduler_type,
            '-allowed-ips', allowed_ips
        ]
        result = execute_secure_command(cmd[0], cmd[1:])
        
        success_msg = f"Successfully configured rate limiting for peer {peer.id} on interface {config.Name}"
        if success_msg in result['stdout']:
            return StandardResponse(status=True, message=success_msg)
        elif result['returncode'] != 0:
            error_msg = f"Failed to set rate limits. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return StandardResponse(status=False, message=error_msg)
        else:
            return StandardResponse(status=False, message="Unexpected response from traffic-weir")
            
    except Exception as e:
        return StandardResponse(status=False, message=f"Error setting rate limits: {str(e)}")


@router.get('/get_peer_rate_limit', response_model=StandardResponse)
async def get_peer_rate_limit(
    interface: str = Query(..., description="Interface name"),
    peer_key: str = Query(..., description="Peer public key"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get traffic rate limit for a WireGuard peer"""
    # Use unquote to properly handle '+' characters
    peer_key = unquote(peer_key.replace(' ', '+'))
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(interface)
        if not config:
            return StandardResponse(
                status=False,
                message=f"Interface {interface} not found"
            )
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(peer_key)
        if not found:
            return StandardResponse(
                status=False,
                message=f"Peer {peer_key} not found in interface {config.Name}"
            )
            
        # Get rate limits from database
        manager = await get_redis_manager()
        
        # Try main table first
        peer_data = manager.get_record(interface, peer.id)
        if not peer_data:
            # Try restricted table
            peer_data = manager.get_record(f"{interface}_restrict_access", peer.id)
        
        if peer_data:
            db_upload_rate = peer_data.get('upload_rate_limit', 0) or 0
            db_download_rate = peer_data.get('download_rate_limit', 0) or 0
            db_scheduler_type = peer_data.get('scheduler_type', 'htb') or 'htb'
        else:
            db_upload_rate = 0
            db_download_rate = 0
            db_scheduler_type = 'htb'
        
        return StandardResponse(
            status=True,
            message="Rate limits retrieved successfully",
            data={
                "upload_rate": float(db_upload_rate),
                "download_rate": float(db_download_rate),
                "scheduler_type": db_scheduler_type
            }
        )
        
    except Exception as e:
        logger.debug(f"Error getting rate limits: {str(e)}")
        return StandardResponse(status=False, message=f"Error getting rate limits: {str(e)}")


@router.post('/remove_peer_rate_limit', response_model=StandardResponse)
async def remove_peer_rate_limit(
    remove_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Remove traffic rate limit for a WireGuard peer"""
    if not all(k in remove_data for k in ['interface', 'peer_key']):
        return StandardResponse(
            status=False,
            message="Missing required parameters"
        )
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(remove_data['interface'])
        if not config:
            return StandardResponse(
                status=False,
                message=f"Interface {remove_data['interface']} not found"
            )
        
        # Find and validate the peer exists
        found, peer = config.searchPeer(remove_data['peer_key'])
        if not found:
            return StandardResponse(
                status=False,
                message=f"Peer {remove_data['peer_key']} not found in interface {config.Name}"
            )
        
        # Get protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return StandardResponse(
                status=False,
                message=f"Invalid or unsupported protocol: {protocol}"
            )
        
        # Get allowed IPs and scheduler type from database
        manager = await get_redis_manager()
        peer_data = manager.get_record(config.Name, peer.id)
        
        if not peer_data:
            return StandardResponse(
                status=False,
                message="Could not find peer data in database"
            )
        
        allowed_ips = peer_data.get('allowed_ip')
        logger.debug(f"Retrieved allowed_ips from database: '{allowed_ips}'")
        if not allowed_ips:
            return StandardResponse(
                status=False,
                message="Could not find allowed IPs for peer"
            )
        
        scheduler_type = peer_data.get('scheduler_type', 'htb')
        
        # Clear rate limits in database
        updates = {
            'upload_rate_limit': None,
            'download_rate_limit': None,
            'scheduler_type': None
        }
        success = manager.update_record(config.Name, peer.id, updates)
        if not success:
            return StandardResponse(
                status=False,
                message=f"Failed to clear rate limits in database for peer {peer.id}"
            )
        
        # Execute traffic-weir command with remove flag
        cmd = [
            '/WireGate/traffic-weir',
            '-interface', config.Name,
            '-peer', peer.id,
            '-protocol', protocol,
            '-scheduler', scheduler_type,
            '-allowed-ips', allowed_ips,
            '-remove'
        ]
        
        logger.debug(f"Constructed command: {cmd}")
        result = execute_secure_command(cmd[0], cmd[1:])
        
        if result['returncode'] != 0:
            error_msg = f"Failed to remove rate limits. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return StandardResponse(status=False, message=error_msg)
        
        return StandardResponse(
            status=True,
            message=f"Rate limits removed successfully for peer {peer.id} on interface {config.Name}"
        )
        
    except Exception as e:
        return StandardResponse(status=False, message=f"Error removing rate limits: {str(e)}")


@router.get('/get_interface_scheduler', response_model=StandardResponse)
async def get_interface_scheduler(
    interface: str = Query(..., description="Interface name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get the scheduler type for an interface if any peer has it set"""
    logger.debug(f"get_interface_scheduler called with interface: {interface}")
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(interface)
        logger.debug(f"Retrieved config for interface {interface}: {config is not None}")
        
        if not config:
            logger.debug(f"Interface {interface} not found")
            return StandardResponse(
                status=False,
                message=f"Interface {interface} not found"
            )
        
        # Query for any peer with a non-zero rate limit and their scheduler type
        manager = await get_redis_manager()
        
        # Get all peers from the interface
        all_peers = manager.get_all_records(interface)
        logger.debug(f"Found {len(all_peers)} peers in interface {interface}")
        
        # Find peers with rate limits set
        rate_limited_peers = []
        for peer_data in all_peers:
            upload_limit = peer_data.get('upload_rate_limit', 0)
            download_limit = peer_data.get('download_rate_limit', 0)
            scheduler_type = peer_data.get('scheduler_type', '')
            
            # Check if peer has rate limits set
            if (scheduler_type and scheduler_type.strip() and 
                ((upload_limit and upload_limit > 0) or (download_limit and download_limit > 0))):
                rate_limited_peers.append(peer_data)
        
        logger.debug(f"Found {len(rate_limited_peers)} rate-limited peers")
        
        # If no peers have rate limits set, return unlocked with default scheduler
        if not rate_limited_peers:
            logger.debug("No rate-limited peers found")
            return StandardResponse(
                status=True,
                message="No rate-limited peers found",
                data={
                    "scheduler_type": "htb",  # Default scheduler type
                    "locked": False
                }
            )
        
        # Return the found scheduler type and locked status
        response_data = {
            "scheduler_type": rate_limited_peers[0].get('scheduler_type', 'htb'),
            "locked": True  # Locked because we found an active rate limit
        }
        logger.debug(f"Returning response data: {response_data}")
        
        return StandardResponse(
            status=True,
            message="Interface scheduler type retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.debug(f"Error in get_interface_scheduler: {str(e)}")
        return StandardResponse(status=False, message=f"Error getting interface scheduler: {str(e)}")


@router.post('/nuke_interface', response_model=StandardResponse)
async def nuke_interface(
    nuke_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Remove all traffic control qdiscs from an interface"""
    if 'interface' not in nuke_data:
        return StandardResponse(
            status=False,
            message="Missing interface parameter"
        )
    
    try:
        # Get configuration object for the interface
        config = Configurations.get(nuke_data['interface'])
        if not config:
            return StandardResponse(
                status=False,
                message=f"Interface {nuke_data['interface']} not found"
            )
        
        # Get protocol
        protocol = config.get_iface_proto()
        if protocol not in ["wg", "awg"]:
            return StandardResponse(
                status=False,
                message=f"Invalid or unsupported protocol: {protocol}"
            )
        
        # Execute traffic-weir command with nuke flag
        cmd = [
            '/WireGate/traffic-weir',
            '-interface', config.Name,
            '-protocol', protocol,
            '-nuke'
        ]
        
        result = execute_secure_command(cmd[0], cmd[1:])
        
        if result['returncode'] != 0:
            error_msg = f"Failed to nuke interface. Exit code: {result['returncode']}\n"
            error_msg += f"stdout: {result['stdout']}\n"
            error_msg += f"stderr: {result['stderr']}\n"
            error_msg += f"Command: {' '.join(cmd)}"
            return StandardResponse(status=False, message=error_msg)
            
        success_msg = f"Successfully nuked all traffic control on interface {config.Name}"
        return StandardResponse(status=True, message=success_msg)
        
    except Exception as e:
        return StandardResponse(status=False, message=f"Error nuking interface: {str(e)}")

