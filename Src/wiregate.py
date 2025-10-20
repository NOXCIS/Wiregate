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


from wiregate.modules.DashboardConfig import DashboardConfig
from wiregate.dashboard import stopThreads
import logging
import uvicorn
import sys
import time
import argparse
import configparser
import os
import signal
import atexit

# Set up logger
logger = logging.getLogger(__name__)
    

from datetime import datetime
date = datetime.today().strftime('%Y_%m_%d_%H_%M_%S')

# Global variable to track if we're shutting down
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    if shutdown_requested:
        logger.critical(f"Force shutdown requested (signal {signum})")
        sys.exit(1)
    
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True
    
    # Stop threads and cleanup with timeout
    try:
        stopThreads()
        logger.info("Threads stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping threads: {e}")
    
    # Exit immediately after cleanup
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    if not shutdown_requested:
        logger.info("Normal shutdown requested")
        try:
            stopThreads()
            logger.info("Threads stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping threads: {e}")

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    
    # Register cleanup function for normal exit
    atexit.register(cleanup_on_exit)
    
    # Add argument parser
    parser = argparse.ArgumentParser(description='Wiregate Dashboard Server')
    parser.add_argument('--config', type=str, help='Path to configuration file (defaults to ./db/wsgi.ini)')
    parser.add_argument('--workers', type=int, help='Number of worker processes')
    parser.add_argument('--threads', type=int, help='Number of threads per worker')
    parser.add_argument('--loglevel', type=str,
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Logging level')
    parser.add_argument('--daemon', type=bool, help='Run in daemon mode (True/False)')
    # Add SSL certificate and key arguments
    parser.add_argument('--ssl', action='store_true', help='Enable SSL/HTTPS')
    parser.add_argument('--certfile', type=str, help='Path to SSL certificate file')
    parser.add_argument('--keyfile', type=str, help='Path to SSL private key file')
    args = parser.parse_args()
    
    # Get app configuration
    _, app_ip = DashboardConfig.GetConfig("Server", "app_ip")
    _, app_port = DashboardConfig.GetConfig("Server", "app_port")
    
    # Default options for Uvicorn
    options = {
        'host': app_ip,
        'port': int(app_port),
        'log_level': 'info',
        'access_log': True,
        'loop': 'asyncio',
        'http': 'h11',
        'lifespan': 'on',
        'timeout_keep_alive': 5,
        'timeout_graceful_shutdown': 5,  # Reduced from 30 to 5 seconds
    }
    
    # Try to load from default config file location if not specified
    config_path = args.config if args.config else './db/wsgi.ini'
    
    # Load options from config file if it exists
    if os.path.exists(config_path):
        logger.debug(f"Loading configuration from {config_path}")
        config = configparser.ConfigParser()
        try:
            config.read(config_path)
            # Support both 'uvicorn' and 'gunicorn' sections for backward compatibility
            config_section = None
            if 'uvicorn' in config:
                config_section = config['uvicorn']
            elif 'gunicorn' in config:
                config_section = config['gunicorn']
                
            if config_section:
                # Override defaults with config file values
                if 'workers' in config_section:
                    options['workers'] = int(config_section['workers'])
                if 'log_level' in config_section or 'loglevel' in config_section:
                    log_level = config_section.get('log_level', config_section.get('loglevel', 'info'))
                    options['log_level'] = log_level.lower()
                
                # Handle SSL configuration from config file
                ssl_enabled = False
                if 'ssl' in config_section:
                    ssl_enabled = config_section.getboolean('ssl')
                    
                if ssl_enabled:
                    if 'certfile' in config_section and 'keyfile' in config_section:
                        options['ssl_certfile'] = config_section['certfile']
                        options['ssl_keyfile'] = config_section['keyfile']
                
                logger.debug("Loaded configuration successfully")
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
    else:
        if args.config:
            logger.warning(f"Specified config file {config_path} not found")
        else:
            logger.debug("No config file found at default location (./db/wsgi.ini), using defaults")
    
    # Override with command-line arguments (highest precedence)
    if args.workers is not None:
        options['workers'] = args.workers
    if args.loglevel is not None:
        options['log_level'] = args.loglevel.lower()
    
    # Set up logging based on the chosen log level
    log_level = options['log_level'].upper()
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='[%Y-%m-%d %H:%M:%S]'
    )
    
    # Handle SSL configuration (command line takes precedence)
    if args.ssl:
        if not args.certfile or not args.keyfile:
            parser.error("--ssl requires --certfile and --keyfile")
        options['ssl_certfile'] = args.certfile
        options['ssl_keyfile'] = args.keyfile
        logger.info(f"Starting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    elif 'ssl_certfile' in options and 'ssl_keyfile' in options:
        logger.info(f"Starting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    else:
        logger.info(f"Starting Wiregate Dashboard on http://{app_ip}:{app_port}")
    
    # Import FastAPI app (lifespan events handle all initialization)
    from wiregate.modules.App import fastapi_app as final_app
    
    # Remove workers option to avoid Uvicorn warning/crash
    if 'workers' in options:
        del options['workers']
    # Start Uvicorn server
    uvicorn.run(final_app, **options)