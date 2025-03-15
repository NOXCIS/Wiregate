import threading

from typing import Any
from json import JSONEncoder
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider


import time

from .modules.App import (
    app
)
from .modules.Logger.Log import Log

from .modules.DashboardConfig import (
    DashboardConfig, DashboardAPIKey
)

from .modules.Core import (

    PeerShareLink,
    PeerJob, Configuration, Peer, APP_PREFIX,
    Configurations

)


from .modules.Jobs.PeerJobs import AllPeerJobs
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


CORS(app, resources={rf"{APP_PREFIX}/api/*": {
    "origins": "*",
    "methods": "DELETE, POST, GET, OPTIONS",
    "allow_headers": ["Content-Type", "wg-dashboard-apikey"]
}})

from .routes.api import api_blueprint  
from .routes.tor_api import tor_blueprint
from .routes.traffic_weir_api import traffic_weir_blueprint
from .routes.email_api import email_blueprint
from .routes.peer_jobs_api import peer_jobs_blueprint
from .routes.ldap_auth_api import ldap_auth_blueprint
from .routes.data_charts_api import data_chart_blueprint
from .routes.auth_api import auth_blueprint
from .routes.utils_api import utils_blueprint
from .routes.locale_api import locale_blueprint
from .routes.snapshot_api import snapshot_api_blueprint







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





def backGroundThread():
    global Configurations
    print(f"[WireGate] Background Thread #1 Started", flush=True)
    time.sleep(10)
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
        time.sleep(10)


def peerJobScheduleBackgroundThread():
    with app.app_context():
        print(f"[WireGate] Background Thread #2 Started", flush=True)
        time.sleep(10)
        while True:
            AllPeerJobs.runJob()
            time.sleep(15)


def waitressInit():
    _, app_ip = DashboardConfig.GetConfig("Server", "app_ip")
    _, app_port = DashboardConfig.GetConfig("Server", "app_port")
    return app_ip, app_port


def startThreads():
    bgThread = threading.Thread(target=backGroundThread)
    bgThread.daemon = True
    bgThread.start()
    
    scheduleJobThread = threading.Thread(target=peerJobScheduleBackgroundThread)
    scheduleJobThread.daemon = True
    scheduleJobThread.start()

def gunicornConfig():
    """
    Returns the host and port configuration for Gunicorn.
    """
    return waitressInit()








