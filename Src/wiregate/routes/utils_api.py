"""
FastAPI Utils Router
Migrated from utils_api.py Flask blueprint
"""
import logging
import json
import ipaddress
import requests
from datetime import datetime
from icmplib import ping, traceroute
from fastapi import APIRouter, Query, Depends
from typing import Dict, Any, Optional

from ..models.responses import StandardResponse
from ..modules.Core import Configurations
from ..modules.Config import DASHBOARD_VERSION
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()

# Global cache for update information
_update_cache = {
    'last_check': None,
    'data': None,
    'error': None
}


def get_changelog_for_version(version):
    """Return changelog data for a specific version from local changelog file."""
    try:
        import os
        # Path to the local changelog file
        changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "Docs", "CHANGELOG.md")
        
        # Initialize an empty dictionary to store the parsed changelog
        changelog_map = {}
        
        # Read the changelog content from local file
        if os.path.exists(changelog_path):
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read().strip().split('\n')
        else:
            logger.warning(f"Changelog file not found at {changelog_path}")
            return []
        
        # Parse the content
        current_version = None
        
        for line in content:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line defines a version (starts with ##)
            if line.startswith('## '):
                current_version = line.replace('## ', '').strip()
                changelog_map[current_version] = []
            # If this is a changelog item for the current version (starts with -)
            elif line.startswith('-') and current_version:
                item = line.replace('-', '', 1).strip()
                changelog_map[current_version].append(item)
        
        # Handle "latest" version request
        if version == "latest":
            versions = list(changelog_map.keys())
            if versions:
                latest_version = versions[0]  # Assuming first version is latest
                result = changelog_map[latest_version]
                logger.info(f"Requested latest version, showing: {latest_version} with {len(result)} items")
                return result
            else:
                logger.warning(f"No versions found in changelog")
                return []
        
        # Return the changelog items for the requested version only
        result = changelog_map.get(version, [])
        if result:
            logger.info(f"Found {len(result)} changelog items for version {version}")
            return result
        else:
            # No changelog available for this specific version
            logger.info(f"No changelog found for version {version}")
            return []
            
    except Exception as e:
        logger.error(f"Error reading changelog: {str(e)}")
        logger.debug(f"Failed to read changelog, returning empty list")
        return []


def _background_update_check():
    """Background function to check for updates without blocking the UI"""
    global _update_cache
    
    try:
        # Replace with your actual Docker Hub repository
        docker_hub_repo = "noxcis/wiregate"
        list_tags_url = f"https://hub.docker.com/v2/repositories/{docker_hub_repo}/tags"
        
        # Use a longer timeout for background check
        response = requests.get(list_tags_url, timeout=10)
        
        if response.status_code == 200:
            tags_data = response.json()
            tags = tags_data.get('results', [])
            
            if tags:
                parsed_tags = []
                for tag in tags:
                    try:
                        tag_name = tag.get('name', '')
                        last_pushed_str = tag.get('tag_last_pushed', tag.get('last_updated', ''))
                        
                        if last_pushed_str:
                            last_pushed = datetime.fromisoformat(last_pushed_str.replace('Z', '+00:00'))
                            parsed_tags.append({
                                'name': tag_name,
                                'last_pushed': last_pushed
                            })
                    except Exception:
                        continue
                
                if parsed_tags:
                    sorted_tags = sorted(parsed_tags, key=lambda x: x['last_pushed'], reverse=True)
                    latest_tag = sorted_tags[0]['name']
                    latest_pushed = sorted_tags[0]['last_pushed']
                    
                    docker_hub_url = f"https://hub.docker.com/r/{docker_hub_repo}/tags?page=1&name={latest_tag}"
                    
                    # Always fetch changelog for the latest version
                    changelog_items = get_changelog_for_version(latest_tag)
                    
                    if latest_tag and latest_tag != DASHBOARD_VERSION:
                        logger.info(f"Update available: {latest_tag} (current: {DASHBOARD_VERSION})")
                        logger.info(f"Changelog items for {latest_tag}: {len(changelog_items)} items")
                        _update_cache = {
                            'last_check': datetime.now(),
                            'data': {
                                'url': docker_hub_url,
                                'changelog': changelog_items,
                                'version': latest_tag,
                                'message': f"{latest_tag} is now available for update!"
                            },
                            'error': None
                        }
                    else:
                        # Even when on latest version, show the latest changelog
                        logger.info(f"Already on latest version: {DASHBOARD_VERSION}")
                        logger.info(f"Showing latest changelog for version {latest_tag}: {len(changelog_items)} items")
                        _update_cache = {
                            'last_check': datetime.now(),
                            'data': {
                                'url': docker_hub_url,
                                'changelog': changelog_items,
                                'version': latest_tag,
                                'message': "You're on the latest version"
                            },
                            'error': None
                        }
        
    except Exception as e:
        logger.warning(f"Background update check failed: {e}")
        # Even if update check fails, try to fetch changelog as fallback
        try:
            changelog_items = get_changelog_for_version("latest")
            _update_cache = {
                'last_check': datetime.now(),
                'data': {
                    'changelog': changelog_items,
                    'version': "latest",
                    'message': "Update check failed, but showing latest changelog"
                },
                'error': str(e)
            }
        except Exception as changelog_error:
            logger.warning(f"Failed to fetch changelog as fallback: {changelog_error}")
            _update_cache = {
                'last_check': datetime.now(),
                'data': None,
                'error': str(e)
            }


@router.get('/ping/getAllPeersIpAddress', response_model=StandardResponse)
async def get_all_peers_ip_address(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get all peer IP addresses for ping tool"""
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
                    logger.warning(f"{p.id} - {c.Name}")
                    continue
                if len(list(ip.hosts())) == 1:
                    parsed.append(str(list(ip.hosts())[0]))
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
    
    return StandardResponse(status=True, data=ips)


@router.get('/ping/execute', response_model=StandardResponse)
async def execute_ping(
    ipAddress: str = Query(..., description="IP address to ping"),
    count: int = Query(..., description="Number of ping packets"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Execute ping command to IP address"""
    try:
        if not ipAddress or not count:
            return StandardResponse(
                status=False,
                message="Please specify an IP Address (v4/v6) and count"
            )
        
        result = ping(ipAddress, count=count, source=None)
        
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
        
        return StandardResponse(status=True, data=data)
        
    except Exception as exp:
        return StandardResponse(status=False, message=str(exp))


@router.get('/traceroute/execute', response_model=StandardResponse)
async def execute_traceroute(
    ipAddress: str = Query(..., description="IP address to traceroute"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Execute traceroute to IP address"""
    if not ipAddress or len(ipAddress) == 0:
        return StandardResponse(
            status=False,
            message="Please provide ipAddress"
        )
    
    try:
        tracerouteResult = traceroute(ipAddress, timeout=1, max_hops=64)
        result = []
        for hop in tracerouteResult:
            if len(result) > 1:
                skipped = False
                for i in range(result[-1]["hop"] + 1, hop.distance):
                    result.append({
                        "hop": i,
                        "ip": "*",
                        "avg_rtt": "*",
                        "min_rtt": "*",
                        "max_rtt": "*"
                    })
                    skipped = True
                if skipped:
                    continue
            
            result.append({
                "hop": hop.distance,
                "ip": hop.address,
                "avg_rtt": hop.avg_rtt,
                "min_rtt": hop.min_rtt,
                "max_rtt": hop.max_rtt
            })
        
        try:
            r = requests.post(
                f"http://ip-api.com/batch?fields=city,country,lat,lon,query",
                data=json.dumps([x['ip'] for x in result])
            )
            d = r.json()
            for i in range(len(result)):
                result[i]['geo'] = d[i]
        except Exception as e:
            logger.error(f"Error in ping operation: {e}")
        
        return StandardResponse(status=True, data=result)
        
    except Exception as exp:
        return StandardResponse(status=False, message=str(exp))


@router.get('/getCurrentVersionChangelog', response_model=StandardResponse)
async def get_current_version_changelog(
    version: str = Query(..., description="Version to get changelog for"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get changelog for a specific version"""
    try:
        changelog_items = get_changelog_for_version(version)
        return StandardResponse(
            status=True,
            message=f"Changelog for {version}",
            data={
                'changelog': changelog_items,
                'version': version
            }
        )
    except Exception as e:
        logger.error(f"Failed to get changelog for version {version}: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get changelog for version {version}"
        )


@router.get('/getDashboardUpdate', response_model=StandardResponse)
async def get_dashboard_update(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get dashboard update information from cache"""
    global _update_cache
    
    # Only return cached data - no direct API calls to prevent blocking
    if _update_cache['last_check'] and _update_cache['data']:
        return StandardResponse(
            status=True,
            message=_update_cache['data']['message'],
            data=_update_cache['data']
        )
    elif _update_cache['last_check'] and _update_cache['error']:
        return StandardResponse(
            status=False,
            message=_update_cache['error']
        )
    else:
        # No cached data available yet - trigger background check
        try:
            import threading
            def run_update_check():
                _background_update_check()
            
            # Run update check in a separate thread to avoid blocking
            update_thread = threading.Thread(target=run_update_check, daemon=True)
            update_thread.start()
            
            return StandardResponse(
                status=False,
                message="Update check started - please refresh in a moment"
            )
        except Exception as e:
            logger.warning(f"Failed to start background update check: {e}")
            return StandardResponse(
                status=False,
                message="Update check in progress - please try again later"
            )

