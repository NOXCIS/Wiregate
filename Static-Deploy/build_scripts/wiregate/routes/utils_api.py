from flask import Blueprint, request
import json, ipaddress, logging
from datetime import datetime
from icmplib import ping, traceroute
from wiregate.modules.shared import ResponseObject
from wiregate.modules.Core import Configurations
from wiregate.modules.config import DASHBOARD_VERSION

utils_blueprint = Blueprint('utils', __name__)

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
                print(e)
            return ResponseObject(data=result)
        except Exception as exp:
            return ResponseObject(False, exp)
    else:
        return ResponseObject(False, "Please provide ipAddress")


@utils_blueprint.get('/getDashboardUpdate')
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
