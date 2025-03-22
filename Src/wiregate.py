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
from wiregate.dashboard import startThreads
import logging
from gunicorn.app.base import BaseApplication
import sys
import time
import argparse
import configparser  # Add this import
import os  # Add this import

# Add new Gunicorn application class
class GunicornApp(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application
    

from datetime import datetime
date = datetime.today().strftime('%Y_%m_%d_%H_%M_%S')


if __name__ == "__main__":
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
    
    # Default options
    options = {
        'bind': f'{app_ip}:{app_port}',
        'workers': 4,
        'threads': 2,
        'accesslog': '-',  # Log to stdout
        'errorlog': '-',   # Log to stderr
        'loglevel': 'INFO',
        'daemon': True,
        'capture_output': True,
        'preload_app': True,
        'logger_class': 'gunicorn.glogging.Logger',
    }
    
    # Try to load from default config file location if not specified
    config_path = args.config if args.config else './db/wsgi.ini'
    
    # Load options from config file if it exists
    if os.path.exists(config_path):
        print(f"Loading configuration from {config_path}")
        config = configparser.ConfigParser()
        try:
            config.read(config_path)
            if 'gunicorn' in config:
                gunicorn_section = config['gunicorn']
                # Override defaults with config file values
                if 'workers' in gunicorn_section:
                    options['workers'] = int(gunicorn_section['workers'])
                if 'threads' in gunicorn_section:
                    options['threads'] = int(gunicorn_section['threads'])
                if 'loglevel' in gunicorn_section:
                    options['loglevel'] = gunicorn_section['loglevel'].lower()
                if 'daemon' in gunicorn_section:
                    options['daemon'] = gunicorn_section.getboolean('daemon')
                
                # Handle SSL configuration from config file
                ssl_enabled = False
                if 'ssl' in gunicorn_section:
                    ssl_enabled = gunicorn_section.getboolean('ssl')
                    
                if ssl_enabled:
                    if 'certfile' in gunicorn_section and 'keyfile' in gunicorn_section:
                        options['certfile'] = gunicorn_section['certfile']
                        options['keyfile'] = gunicorn_section['keyfile']
                else:
                    # Explicitly remove certfile and keyfile if SSL is disabled
                    if 'certfile' in options:
                        del options['certfile']
                    if 'keyfile' in options:
                        del options['keyfile']
                    
                # Handle other gunicorn options from config file
                for key in ['capture_output', 'preload_app']:
                    if key in gunicorn_section:
                        options[key] = gunicorn_section.getboolean(key)
                # Handle any additional gunicorn options present in config
                for key, value in gunicorn_section.items():
                    if key not in options and key not in ['ssl', 'certfile', 'keyfile']:
                        options[key] = value
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
    if args.threads is not None:
        options['threads'] = args.threads
    if args.loglevel is not None:
        options['loglevel'] = args.loglevel.lower()
    if args.daemon is not None:
        options['daemon'] = args.daemon
    
    # Set up logging based on the chosen log level
    log_level = options['loglevel'].upper()
    logging.basicConfig(level=log_level)
    
    # Set up logconfig_dict
    options['logconfig_dict'] = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'generic',
                'stream': 'ext://sys.stdout'
            },
            'access_file': {
                'class': 'logging.FileHandler',
                'filename': f'./log/access_{date}.log',
                'formatter': 'generic'
            },
            'error_file': {
                'class': 'logging.FileHandler',
                'filename': f'./log/error_{date}.log',
                'formatter': 'generic',
                'level': log_level
            }
        },
        'formatters': {
            'generic': {
                'format': '%(asctime)s [%(levelname)s] %(message)s',
                'datefmt': '[%Y-%m-%d %H:%M:%S]',
                'class': 'logging.Formatter'
            }
        },
        'loggers': {
            'gunicorn.access': {
                'handlers': ['console', 'access_file'],
                'level': log_level,
                'propagate': False
            },
            'gunicorn.error': {
                'handlers': ['console', 'error_file'],
                'level': log_level,
                'propagate': False
            }
        }
    }
    
    # Handle SSL configuration (command line takes precedence)
    if args.ssl:
        if not args.certfile or not args.keyfile:
            parser.error("--ssl requires --certfile and --keyfile")
        options['certfile'] = args.certfile
        options['keyfile'] = args.keyfile
        print(f"\nStarting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    elif 'certfile' in options and 'keyfile' in options:
        print(f"\nStarting Wiregate Dashboard with SSL on https://{app_ip}:{app_port}")
    else:
        # Ensure certfile and keyfile are removed if SSL is disabled
        if 'certfile' in options:
            del options['certfile']
        if 'keyfile' in options:
            del options['keyfile']
        print(f"\nStarting Wiregate Dashboard on http://{app_ip}:{app_port}")
    
    InitWireguardConfigurationsList(startup=True)
    InitRateLimits()
    startThreads()
    
    # Choose between Gunicorn with SSL or Flask development server
    if args.ssl:
        # Use Gunicorn with SSL (recommended for production)
        GunicornApp(app, options).run()
    else:
        # For development only
        #GunicornApp(app, options).run()
        app.run(host=app_ip, port=app_port, debug=True)