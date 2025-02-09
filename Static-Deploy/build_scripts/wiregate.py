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
from wiregate.dashboard import app, app_ip, app_port
from wiregate.modules.Core import InitWireguardConfigurationsList
from wiregate.dashboard import startThreads
import logging
import os
from logging.handlers import RotatingFileHandler
from waitress import serve

def configure_logger():
    logger = logging.getLogger('wiregate')
    logger.setLevel(logging.INFO)
    
    # File handler configuration
    log_filename = get_timestamped_filename()
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    file_handler = RotatingFileHandler(log_filename, maxBytes=1000000, backupCount=3)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Stream handler configuration for console logging
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    
    return logger

logger = configure_logger()

if __name__ == "__main__":
    logger.info("Starting Wiregate Dashboard...")
    InitWireguardConfigurationsList(startup=True)
    startThreads()  # Start any background threads

    # Use waitress for production (non-debug mode) to leverage its integrated logging
    #if app.debug:
    app.run(host=app_ip, port=app_port, debug=True)
    #else:
    #serve(app, host=app_ip, port=app_port, threads=8)

    

    # Start the Waitress server with access logging enabled
    #waitress.serve(
    #    app,
    #    host=app_ip,
    #    port=app_port,
    #    threads=8, 
    #)

    # Initialize logger 
    # Set up the rotating file handler with dynamic filename
    