import os
import socket


# Import Enviorment
DASHBOARD_VERSION = 'flat-bridge-v0.0.1'
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

# Redis Database Settings
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', '6379'))
redis_db = int(os.getenv('REDIS_DB', '0'))
redis_password = os.getenv('REDIS_PASSWORD')

# PostgreSQL Database Settings
postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
postgres_db = os.getenv('POSTGRES_DB', 'wiregate')
postgres_user = os.getenv('POSTGRES_USER', 'wiregate_user')
postgres_password = os.getenv('POSTGRES_PASSWORD', 'wiregate_postgres_password')
postgres_ssl_mode = os.getenv('POSTGRES_SSL_MODE', 'disable')

# Security Settings
DASHBOARD_MODE = os.getenv('DASHBOARD_MODE', 'development')  # development, production
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',') if os.getenv('ALLOWED_ORIGINS') else ['*']
MAX_REQUEST_SIZE = int(os.getenv('MAX_REQUEST_SIZE', '16777216'))  # 16MB default
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))  # requests per minute
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds
BRUTE_FORCE_MAX_ATTEMPTS = int(os.getenv('BRUTE_FORCE_MAX_ATTEMPTS', '5'))  # max failed attempts
BRUTE_FORCE_LOCKOUT_TIME = int(os.getenv('BRUTE_FORCE_LOCKOUT_TIME', '900'))  # 15 minutes
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour
SECURE_SESSION = os.getenv('SECURE_SESSION', 'true').lower() == 'true'

# Database Type Settings
DASHBOARD_TYPE = os.getenv('DASHBOARD_TYPE', 'simple')  # simple (SQLite), scale (PostgreSQL + Redis)
