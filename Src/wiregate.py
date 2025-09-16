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


from wiregate.dashboard import app, app_ip, app_port
from wiregate.modules.Core import InitWireguardConfigurationsList, InitRateLimits
from wiregate.dashboard import startThreads, stopThreads
from wiregate.modules.DataBase import check_and_migrate_sqlite_databases
import logging
import uvicorn
import sys
import time
import argparse
import configparser
import os
import signal
import atexit
from asgiref.wsgi import WsgiToAsgi
    

from datetime import datetime
date = datetime.today().strftime('%Y_%m_%d_%H_%M_%S')

# Global variable to track if we're shutting down
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    if shutdown_requested:
        print(f"\n[WIREGATE] Force shutdown requested (signal {signum})")
        sys.exit(1)
    
    print(f"\n[WIREGATE] Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True
    
    # Stop threads and cleanup
    try:
        stopThreads()
        print("[WIREGATE] Threads stopped successfully")
    except Exception as e:
        print(f"[WIREGATE] Error stopping threads: {e}")
    
    # Exit gracefully
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    if not shutdown_requested:
        print("\n[WIREGATE] Normal shutdown requested")
        try:
            stopThreads()
            print("[WIREGATE] Threads stopped successfully")
        except Exception as e:
            print(f"[WIREGATE] Error stopping threads: {e}")

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
    
    # Default options for Uvicorn
    options = {
        'host': app_ip,
        'port': int(app_port),
        'log_level': 'info',
        'access_log': True,

    }
    
    # Try to load from default config file location if not specified
    config_path = args.config if args.config else './db/wsgi.ini'
    
    # Load options from config file if it exists
    if os.path.exists(config_path):
        print(f"Loading configuration from {config_path}")
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
                
                print(f"Loaded configuration successfully")
        except Exception as e:
            print(f"Error loading configuration file: {e}")
    else:
        if args.config:
            print(f"Warning: Specified config file {config_path} not found")
        else:
            print(f"No config file found at default location (./db/wsgi.ini), using defaults")
    
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
        print(f"\nStarting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    elif 'ssl_certfile' in options and 'ssl_keyfile' in options:
        print(f"\nStarting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    else:
        print(f"\nStarting Wiregate Dashboard on http://{app_ip}:{app_port}")
    
    # Check for and migrate any existing SQLite databases to Redis
    print("Checking for SQLite databases to migrate...")
    if check_and_migrate_sqlite_databases():
        print("✓ SQLite databases migrated to Redis")
    else:
        print("✓ No SQLite databases found to migrate")
    
    InitWireguardConfigurationsList(startup=True)
    InitRateLimits()
    startThreads()
    
    # Convert Flask WSGI app to ASGI for Uvicorn compatibility
    asgi_app = WsgiToAsgi(app)
    
    # Remove workers option to avoid Uvicorn warning/crash
    if 'workers' in options:
        del options['workers']
    # Start Uvicorn server
    uvicorn.run(asgi_app, **options)