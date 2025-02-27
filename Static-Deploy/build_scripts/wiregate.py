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
import os
from gunicorn.app.base import BaseApplication
import sys
import time
import argparse  # Add this import

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
    parser.add_argument('--workers', type=int, default=4, help='Number of worker processes')
    parser.add_argument('--threads', type=int, default=2, help='Number of threads per worker')
    parser.add_argument('--loglevel', type=str, default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Logging level')
    parser.add_argument('--daemon', type=bool, default=True, 
                       help='Run in daemon mode (True/False)')
    args = parser.parse_args()
    
    # Convert loglevel to uppercase to ensure consistency
    log_level = args.loglevel.upper()
    
    # Configure root logger
    logging.basicConfig(level=log_level)

    def typewriter_print(text, delay=0.02, color_cycle=None, line_delay=0.02):
        colors = color_cycle or ['\033[91m', '\033[92m', '\033[93m', 
                               '\033[94m', '\033[95m', '\033[96m']  # ANSI color codes
        for i, line in enumerate(text.split('\n')):
            color = colors[i % len(colors)]
            sys.stdout.write(color)  # Set line color
            for char in line:
                sys.stdout.write(char)
                sys.stdout.flush()
                time.sleep(delay)
            sys.stdout.write('\033[0m')  # Reset color
            print()
            time.sleep(line_delay)  # Delay between lines

    title_art = """
=========================================
▗▖ ▗▖▗▄▄▄▖▗▄▄▖ ▗▄▄▄▖ ▗▄▄▖ ▗▄▖▗▄▄▄▖▗▄▄▄▖
▐▌ ▐▌  █  ▐▌ ▐▌▐▌   ▐▌   ▐▌ ▐▌ █  ▐▌   
▐▌ ▐▌  █  ▐▛▀▚▖▐▛▀▀▘▐▌▝▜▌▐▛▀▜▌ █  ▐▛▀▀▘
▐▙█▟▌▗▄█▄▖▐▌ ▐▌▐▙▄▄▖▝▚▄▞▘▐▌ ▐▌ █  ▐▙▄▄▖
========================================="""
    byline = "By Noxcis"
    
    typewriter_print(title_art, delay=0.00625, color_cycle=[
        '\033[91m',  # Red
        '\033[92m',  # Green
        '\033[93m',  # Yellow
        '\033[96m'   # Cyan
    ], line_delay=0.000625)
    typewriter_print(byline, delay=0.000625, color_cycle=['\033[97m'], line_delay=0)

    # Overwrite with royal purple main art and white byline
    lines = title_art.count('\n') + 1 + 1  # +1 for byline, +1 for line count offset
    sys.stdout.write(f'\033[{lines}A')  # Move cursor up
    print('\033[92m' + title_art + '\n\033[97m' + byline + '\033[0m')  # Royal Purple art, white byline
    
    
    print(f"\nStarting Wiregate Dashboard on http://{app_ip}:{app_port}")

    InitWireguardConfigurationsList(startup=True)
    InitRateLimits()
    startThreads()
    # Configure Gunicorn
    options = {
        'bind': f'{app_ip}:{app_port}',
        'workers': args.workers,
        'threads': args.threads,
        'accesslog': '-',  # Log to stdout
        'errorlog': '-',   # Log to stderr
        'loglevel': log_level.lower(),  # Gunicorn expects lowercase
        'daemon': args.daemon,
        'capture_output': True,
        'preload_app': True,
        'logger_class': 'gunicorn.glogging.Logger',
        'logconfig_dict': {
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
    }


    
    GunicornApp(app, options).run()


    #app.run(host=app_ip, port=app_port, debug=True)