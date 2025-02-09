import os
import socket


# Import Enviorment
DASHBOARD_VERSION = 'jiaotu-beta-v0.4'
DASHBOARD_MODE = None
CONFIGURATION_PATH = os.getenv('CONFIGURATION_PATH', '.')
DB_PATH = os.path.join(CONFIGURATION_PATH, 'db')
if not os.path.isdir(DB_PATH):
    os.mkdir(DB_PATH)
DASHBOARD_CONF = os.path.join(CONFIGURATION_PATH, 'db', 'wg-dashboard.ini')
WG_CONF_PATH = None
UPDATE = None


TORRC_PATH = "/etc/tor/torrc"
DNS_TORRC_PATH = "/etc/tor/dnstorrc"




wgd_config_path = os.environ.get('WGD_CONF_PATH') or "/etc/wireguard"
wgd_welcome = os.environ.get('WGD_WELCOME_SESSION') or "true"
wgd_app_port = os.environ.get('WGD_REMOTE_ENDPOINT_PORT') or "10086"
wgd_auth_req = os.environ.get('WGD_AUTH_REQ') or "true"
wgd_user = os.environ.get('WGD_USER') or "admin"
wgd_pass = os.environ.get('WGD_PASS') or "admin"
wgd_global_dns = os.environ.get('WGD_DNS') or "1.1.1.1"
wgd_peer_endpoint_allowed_ip = os.environ.get('WGD_PEER_ENDPOINT_ALLOWED_IP') or "0.0.0.0/0, ::/0"
wgd_keep_alive = os.environ.get('WGD_KEEP_ALIVE') or "21"
wgd_mtu = os.environ.get('WGD_MTU') or "1420"
wgd_remote_endpoint = os.environ.get('WGD_REMOTE_ENDPOINT') or "0.0.0.0"

if wgd_remote_endpoint == '0.0.0.0':
    try:
        # Get the default IP address using a socket trick
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))  # Connecting to a public IP
            wgd_remote_endpoint = s.getsockname()[0]
    except Exception:
        wgd_remote_endpoint = '0.0.0.0'  # Fallback if socket fails
