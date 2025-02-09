import threading

from typing import Any
from json import JSONEncoder
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider



from .modules.shared import (
    app
)
from .modules.Log import Log

from .modules.DashboardConfig import (
    DashboardConfig, DashboardAPIKey
)

from .modules.Core import (

    PeerShareLink,
    PeerJob, Configuration, Peer, APP_PREFIX

)

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
from .routes.api import backGroundThread, peerJobScheduleBackgroundThread
from .routes.traffic_weir_api import traffic_weir_blueprint
from .routes.email_api import email_blueprint





# Initialize logger
# Set up the rotating file handler with dynamic filename
#log_filename = get_timestamped_filename()
#handler = RotatingFileHandler(log_filename, maxBytes=1000000, backupCount=3)

#logger = logging.getLogger('wiregate')
#logger.setLevel(logging.INFO)
#logger.addHandler(handler)

#AllPeerShareLinks: PeerShareLinks = PeerShareLinks()
#AllPeerJobs: PeerJobs = PeerJobs()
#JobLogger: PeerJobLogger = PeerJobLogger()
#AllDashboardLogger: DashboardLogger = DashboardLogger()







app.register_blueprint(api_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(tor_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(email_blueprint, url_prefix=f'{APP_PREFIX}/api')
app.register_blueprint(traffic_weir_blueprint, url_prefix=f'{APP_PREFIX}/api')


'''
API Routes
'''



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













