# Copyright(C) 2025 NOXCIS [https://github.com/NOXCIS]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from wiregate.modules.shared import get_timestamped_filename
from wiregate.dashboard import waitressInit, startThreads
from wiregate.modules.Core import InitWireguardConfigurationsList
from wiregate.dashboard import app, app_ip, app_port
from logging.handlers import RotatingFileHandler
from flask import request, g
from time import strftime
import time, logging


@app.before_request
def before_request():
    """Store the start time of the request."""
    g.start_time = time.time()

@app.after_request
def after_request(response):
    """Log access details after the request is processed."""
    # Safeguard in case g.start_time is not set
    start_time = getattr(g, 'start_time', time.time())
    response_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
    
    # Format log entry
    timestamp = strftime('[%Y-%b-%d %H:%M]')
    log_entry = (
        f"{timestamp} "
        f"User-Agent: {request.user_agent.string} "
        f"IP: {request.remote_addr} "
        f"Referrer: {request.referrer or 'No Referrer'} "
        f"Method: {request.method} "
        f"Scheme: {request.scheme} "
        f"Path: {request.full_path} "
        f"Status: {response.status_code} "
        f"Response Time: {response_time} ms"
    )
    logger.info(log_entry)
    
    return response

if __name__ == "__main__":
    print("Starting Wiregate Dashboard...", flush=True)
    InitWireguardConfigurationsList(startup=True)
    
    waitressInit()
    # Start background threads
    startThreads()
    log_filename = get_timestamped_filename()
    handler = RotatingFileHandler(log_filename, maxBytes=1000000, backupCount=3)

    logger = logging.getLogger('wiregate')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    app.run(host=app_ip, debug=True, port=app_port)

    

    # Start the Waitress server with access logging enabled
    #waitress.serve(
    #    app,
    #    host=app_ip,
    #    port=app_port,
    #    threads=8, 
    #)

    # Initialize logger 
    # Set up the rotating file handler with dynamic filename
    