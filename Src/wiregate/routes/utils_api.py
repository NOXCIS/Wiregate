from flask import Blueprint, request
import json, ipaddress, logging
import requests
from datetime import datetime
from icmplib import ping, traceroute
from ..modules.App import ResponseObject
from ..modules.Core import Configurations
from ..modules.ConfigEnv import DASHBOARD_VERSION

utils_blueprint = Blueprint('utils', __name__)
logger = logging.getLogger('wiregate')

'''
Tools
'''


@utils_blueprint.get('/ping/getAllPeersIpAddress')
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
                    logger.warning(f"{p.id} - {c.Name}")
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


@utils_blueprint.get('/ping/execute')
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


@utils_blueprint.get('/traceroute/execute')
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
                logger.error(f"Error in ping operation: {e}")
            return ResponseObject(data=result)
        except Exception as exp:
            return ResponseObject(False, exp)
    else:
        return ResponseObject(False, "Please provide ipAddress")


@utils_blueprint.get('/getCurrentVersionChangelog')
def API_getCurrentVersionChangelog():
    """Get changelog for a specific version"""
    version = request.args.get('version')
    if not version:
        return ResponseObject(False, "Version parameter is required")
    
    try:
        changelog_items = get_changelog_for_version(version)
        return ResponseObject(True, f"Changelog for {version}", {
            'changelog': changelog_items,
            'version': version
        })
    except Exception as e:
        logging.error(f"Failed to get changelog for version {version}: {e}")
        return ResponseObject(False, f"Failed to get changelog for version {version}")


@utils_blueprint.get('/getDashboardUpdate')
def API_getDashboardUpdate():
    global _update_cache
    
    # Only return cached data - no direct API calls to prevent blocking
    # This endpoint should be very fast since it only returns cached data
    if _update_cache['last_check'] and _update_cache['data']:
        return ResponseObject(True, _update_cache['data']['message'], _update_cache['data'])
    elif _update_cache['last_check'] and _update_cache['error']:
        return ResponseObject(False, _update_cache['error'])
    else:
        # No cached data available yet - background thread hasn't run yet
        # Trigger a background update check if none has been attempted
        try:
            import threading
            def run_update_check():
                _background_update_check()
            
            # Run update check in a separate thread to avoid blocking
            update_thread = threading.Thread(target=run_update_check, daemon=True)
            update_thread.start()
            
            return ResponseObject(False, "Update check started - please refresh in a moment")
        except Exception as e:
            logging.warning(f"Failed to start background update check: {e}")
            return ResponseObject(False, "Update check in progress - please try again later")


def get_changelog_for_version(version):
    """Return changelog data for a specific version by fetching from GitHub."""
    try:
        # URL to the raw changelog file on GitHub
        changelog_url = "https://raw.githubusercontent.com/NOXCIS/Wiregate/refs/heads/main/Docs/CHANGELOG.md"
        
        # Initialize an empty dictionary to store the parsed changelog
        changelog_map = {}
        
        # Fetch the changelog content
        response = requests.get(changelog_url, timeout=5)
        
        if response.status_code == 200:
            # Parse the content
            current_version = None
            content = response.text.strip().split('\n')
            
            for line in content:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line defines a version (starts with ## or ends with :)
                if line.startswith('## '):
                    current_version = line.replace('## ', '').strip()
                    changelog_map[current_version] = []
                elif line.endswith(':'):
                    current_version = line.replace(':', '').strip()
                    changelog_map[current_version] = []
                # If this is a changelog item for the current version (starts with -)
                elif line.startswith('-') and current_version:
                    item = line.replace('-', '', 1).strip()
                    changelog_map[current_version].append(item)
            
            # Return the changelog items for the requested version, or latest if not found
            result = changelog_map.get(version, [])
            if result:
                logging.info(f"Found {len(result)} changelog items for version {version}")
                return result
            else:
                # Fallback: return the latest available version's changelog
                versions = list(changelog_map.keys())
                if versions:
                    latest_version = versions[0]  # Assuming first version is latest
                    result = changelog_map[latest_version]
                    logging.info(f"Version {version} not found, showing latest available: {latest_version} with {len(result)} items")
                    return result
                else:
                    logging.warning(f"No versions found in changelog")
                    return []
        else:
            logging.error(f"Failed to fetch changelog: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        logging.error(f"Error fetching changelog: {str(e)}")
        # Return empty list if fetch fails - no need for hardcoded fallback
        logging.debug(f"Failed to fetch changelog, returning empty list")
        return []

# Global cache for update information
_update_cache = {
    'last_check': None,
    'data': None,
    'error': None
}

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
                    
                    if latest_tag and latest_tag != DASHBOARD_VERSION:
                        changelog_items = get_changelog_for_version(latest_tag)
                        logging.info(f"Update available: {latest_tag} (current: {DASHBOARD_VERSION})")
                        logging.info(f"Changelog items for {latest_tag}: {len(changelog_items)} items")
                        _update_cache = {
                            'last_check': datetime.now(),
                            'data': {
                                'url': docker_hub_url,
                                'changelog': changelog_items,
                                'message': f"{latest_tag} is now available for update!"
                            },
                            'error': None
                        }
                    else:
                        # Even when on latest version, show the latest changelog for user reference
                        changelog_items = get_changelog_for_version(latest_tag)
                        logging.info(f"Already on latest version: {DASHBOARD_VERSION}")
                        logging.info(f"Showing latest changelog for version {latest_tag}: {len(changelog_items)} items")
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
        logging.warning(f"Background update check failed: {e}")
        _update_cache = {
            'last_check': datetime.now(),
            'data': None,
            'error': str(e)
        }

# Background update checking is now handled by the main dashboard thread system
