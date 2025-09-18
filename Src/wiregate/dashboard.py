import threading

from typing import Any
from json import JSONEncoder
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider


import time

from .modules.App import (
    app
)
from .modules.Logger import Log

from .modules.DashboardConfig import (
    DashboardConfig, DashboardAPIKey
)

from .modules.Async import thread_pool, process_pool

from .modules.Core import (

    PeerShareLink,
    PeerJob, Configuration, Peer, APP_PREFIX,
    Configurations

)
from .modules.ConfigEnv import DASHBOARD_MODE, ALLOWED_ORIGINS
from .modules.Security import security_manager, secure_headers


from .modules.Jobs import AllPeerJobs
class ModelEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, 'toJson'):
            return o.toJson()
        else:
            return super(ModelEncoder, self).default(o)

class CustomJsonEncoder(DefaultJSONProvider):
    def __init__(self, app):
        super().__init__(app)

    def default(self, o):
        if (isinstance(o, Configuration)
                or isinstance(o, Peer)
                or isinstance(o, PeerJob)
                or isinstance(o, Log)
                or isinstance(o, DashboardAPIKey)
                or isinstance(o, PeerShareLink)):
            return o.toJson()
        return super().default(self, o)

app.json = CustomJsonEncoder(app)

_, WG_CONF_PATH = DashboardConfig.GetConfig("Server", "wg_conf_path")
_, app_ip = DashboardConfig.GetConfig("Server", "app_ip")
_, app_port = DashboardConfig.GetConfig("Server", "app_port")


# Configure CORS based on environment
if DASHBOARD_MODE == 'production' and '*' not in ALLOWED_ORIGINS:
    # Production mode with specific allowed origins
    CORS(app, resources={rf"{APP_PREFIX}/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": "DELETE, POST, GET, OPTIONS",
        "allow_headers": ["Content-Type", "wg-dashboard-apikey"],
        "supports_credentials": True
    }})
else:
    # Development mode or wildcard allowed
    CORS(app, resources={rf"{APP_PREFIX}/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": "DELETE, POST, GET, OPTIONS",
        "allow_headers": ["Content-Type", "wg-dashboard-apikey"]
    }})

# Import core route modules with fallbacks
try:
    from .routes.api import api_blueprint
except ImportError:
    from flask import Blueprint
    api_blueprint = Blueprint('api', __name__)

try:
    from .routes.tor_api import tor_blueprint
except ImportError:
    from flask import Blueprint
    tor_blueprint = Blueprint('tor', __name__)

try:
    from .routes.traffic_weir_api import traffic_weir_blueprint
except ImportError:
    from flask import Blueprint
    traffic_weir_blueprint = Blueprint('traffic_weir', __name__)

try:
    from .routes.email_api import email_blueprint
except ImportError:
    from flask import Blueprint
    email_blueprint = Blueprint('email', __name__)

try:
    from .routes.peer_jobs_api import peer_jobs_blueprint
except ImportError:
    from flask import Blueprint
    peer_jobs_blueprint = Blueprint('peer_jobs', __name__)
# Import route modules with fallbacks
try:
    from .routes.ldap_auth_api import ldap_auth_blueprint
except ImportError:
    from flask import Blueprint
    ldap_auth_blueprint = Blueprint('ldap_auth', __name__)

try:
    from .routes.data_charts_api import data_chart_blueprint
except ImportError:
    from flask import Blueprint
    data_chart_blueprint = Blueprint('data_chart', __name__)

try:
    from .routes.auth_api import auth_blueprint
except ImportError:
    from flask import Blueprint
    auth_blueprint = Blueprint('auth', __name__)

try:
    from .routes.utils_api import utils_blueprint
except ImportError:
    from flask import Blueprint
    utils_blueprint = Blueprint('utils', __name__)

try:
    from .routes.locale_api import locale_blueprint
except ImportError:
    from flask import Blueprint
    locale_blueprint = Blueprint('locale', __name__)
# Import snapshot_api with fallback
try:
    from .routes.snapshot_api import snapshot_api_blueprint
except ImportError:
    # Create a dummy blueprint if snapshot_api is not available
    from flask import Blueprint
    snapshot_api_blueprint = Blueprint('snapshot_api', __name__)







app.register_blueprint(api_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(tor_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(email_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(traffic_weir_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(peer_jobs_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(ldap_auth_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(data_chart_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(auth_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(utils_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(locale_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(snapshot_api_blueprint, url_prefix=f'{APP_PREFIX}/api')

# Add security headers to all responses
@app.after_request
def add_security_headers(response):
    return secure_headers(response)

# 404 error handler for API routes
@app.errorhandler(404)
def not_found_error(error):
    from flask import request, jsonify
    
    # If it's an API request, return JSON response
    if request.path.startswith(f'{APP_PREFIX}/api'):
        return jsonify({
            "status": False,
            "message": "API endpoint not found",
            "data": None,
            "error": "404 Not Found"
        }), 404
    
    # For non-API requests, serve the frontend (let Vue router handle 404)
    from flask import send_from_directory
    import os
    return send_from_directory(
        os.path.abspath("./static/app/dist"), 
        'index.html'
    )





def backGroundThread():
    global Configurations
    print(f"[WireGate] Background Thread #1 Started", flush=True)
    time.sleep(10)
    
    # Counter for update checks (check every 360 iterations = 1 hour)
    update_check_counter = 0
    
    while True:
        with app.app_context():
            for c in Configurations.values():
                if c.getStatus():
                    try:
                        c.getPeersTransfer()
                        c.getPeersLatestHandshake()
                        c.getPeersEndpoint()
                        c.getPeersList()
                        c.getRestrictedPeersList()
                    except Exception as e:
                        print(f"[WireGate] Background Thread #1 Error: {str(e)}", flush=True)
            
            # Check for updates every hour (360 iterations * 10 seconds = 3600 seconds)
            # This will only run after the initial update check is triggered from the frontend
            update_check_counter += 1
            if update_check_counter >= 360:
                try:
                    from .routes.utils_api import _background_update_check
                    _background_update_check()
                    print(f"[WireGate] Update check completed", flush=True)
                except Exception as e:
                    print(f"[WireGate] Update check error: {str(e)}", flush=True)
                update_check_counter = 0  # Reset counter
                
        time.sleep(10)


def peerJobScheduleBackgroundThread():
    with app.app_context():
        print(f"[WireGate] Background Thread #2 Started", flush=True)
        time.sleep(10)
        while True:
            AllPeerJobs.runJob()
            time.sleep(15)




def startThreads():
    # Start thread pool for I/O operations
    thread_pool.start_pool()
    print("[WireGate] Thread pool started with 20 workers")
    
    # Start process pool for CPU-intensive operations
    process_pool.start_pool()
    print("[WireGate] Process pool started with 4 workers")
    
    bgThread = threading.Thread(target=backGroundThread)
    bgThread.daemon = True
    bgThread.start()
    
    scheduleJobThread = threading.Thread(target=peerJobScheduleBackgroundThread)
    scheduleJobThread.daemon = True
    scheduleJobThread.start()
    

def stopThreads():
    """Stop thread pool and process pool, cleanup resources"""
    try:
        thread_pool.stop_pool()
        print("[WireGate] Thread pool stopped")
    except Exception as e:
        print(f"[WireGate] Error stopping thread pool: {e}")
    
    try:
        process_pool.stop_pool()
        print("[WireGate] Process pool stopped")
    except Exception as e:
        print(f"[WireGate] Error stopping process pool: {e}")








