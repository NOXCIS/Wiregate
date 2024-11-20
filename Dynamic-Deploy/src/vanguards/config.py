""" This file contains configuration defaults, options parsing, and config
    file code.
"""
import argparse
import ipaddress
import os
import socket
import sys

from . import bandguards
from . import rendguard
from . import vanguards
from . import control

from . import logger
from .logger import plog

try:
  from configparser import ConfigParser, Error
except ImportError:
  from configparser import ConfigParser, Error

from dotenv import load_dotenv

VANGUARDS_CONF = ".env"

# Check if .env file exists
if os.path.exists(VANGUARDS_CONF):
    with open(VANGUARDS_CONF, 'r') as file:
        # Read the first non-empty line that isn't just a comment
        for line in file:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('#'):
                load_dotenv()
                break

################# Global options ##################

ENABLE_VANGUARDS=True

ENABLE_RENDGUARD=True

ENABLE_BANDGUARDS=True

ENABLE_LOGGUARD=True

ENABLE_CBTVERIFY=False

ENABLE_PATHVERIFY=False

# State file location
STATE_FILE = "vanguards.state"

# Config file location
_CONFIG_FILE = "vanguards.conf"

# Loglevel
LOGLEVEL = "NOTICE"

# Log to file instead of stdout
LOGFILE = ""

# If true, write/update vanguards to torrc and then exit
ONE_SHOT_VANGUARDS = True

CLOSE_CIRCUITS = True

ctrl_pass = os.environ.get('VANGUARD')
CONTROL_IP = "127.0.0.1"
CONTROL_PORT = "9051"
CONTROL_SOCKET = ""
CONTROL_PASS = ctrl_pass

_RETRY_LIMIT = None

def setup_options():
  global CONTROL_IP, CONTROL_PORT, CONTROL_SOCKET, CONTROL_PASS, STATE_FILE
  global ENABLE_BANDGUARDS, ENABLE_RENDGUARD, ENABLE_LOGGUARD, ENABLE_CBTVERIFY
  global ENABLE_PATHVERIFY
  global LOGLEVEL, LOGFILE
  global ONE_SHOT_VANGUARDS, ENABLE_VANGUARDS

  parser = argparse.ArgumentParser()

  parser.add_argument("--state", dest="state_file",
                      default=os.environ.get("VANGUARDS_STATE", STATE_FILE),
                      help="File to store vanguard state")

  parser.add_argument("--generate_config", dest="write_file", type=str,
                      help="Write config to a file after applying command args")

  parser.add_argument("--loglevel", dest="loglevel", type=str,
                      help="Log verbosity (DEBUG, INFO, NOTICE, WARN, or ERROR)")

  parser.add_argument("--logfile", dest="logfile", type=str,
                      help="Log to LOGFILE instead of stdout")

  parser.add_argument("--config", dest="config_file",
                      default=os.environ.get("VANGUARDS_CONFIG", _CONFIG_FILE),
                      help="Location of config file with more advanced settings")

  parser.add_argument("--control_ip", dest="control_ip", default=CONTROL_IP,
                    help="The IP address of the Tor Control Port to connect to (default: "+
                    CONTROL_IP+")")
  parser.add_argument("--control_port", type=str, dest="control_port",
                      default=CONTROL_PORT,
                      help="The Tor Control Port to connect to (default: "+
                      "tries both 9050 and 9151)")

  parser.add_argument("--control_socket", dest="control_socket",
                      default=CONTROL_SOCKET,
                      help="The Tor Control Socket path to connect to "+
                      "(default: try /run/tor/control, then control port)")
  parser.add_argument("--control_pass", dest="control_pass",
                      default=CONTROL_PASS,
                      help="The Tor Control Port password (optional) ")

  parser.add_argument("--retry_limit", dest="retry_limit",
                      default=_RETRY_LIMIT, type=int,
                      help="Reconnect attempt limit on failure (default: Infinite)")

  parser.add_argument("--one_shot_vanguards", dest="one_shot_vanguards",
                      action="store_true",
                      help="Set and write layer2 and layer3 guards to Torrc and exit.")

  parser.add_argument("--disable_vanguards", dest="vanguards_enabled",
                      action="store_false",
                      help="Disable setting any layer2 and layer3 guards.")
  parser.set_defaults(vanguards_enabled=ENABLE_VANGUARDS)

  parser.add_argument("--disable_bandguards", dest="bandguards_enabled",
                      action="store_false",
                      help="Disable circuit side channel checks (may help performance)")
  parser.set_defaults(bandguards_eabled=ENABLE_BANDGUARDS)

  parser.add_argument("--disable_logguard", dest="logguard_enabled",
                      action="store_false",
                      help="Disable Tor log monitoring (may help performance)")
  parser.set_defaults(logguard_enabled=ENABLE_LOGGUARD)

  parser.add_argument("--disable_rendguard", dest="rendguard_enabled",
                      action="store_false",
                      help="Disable rendezvous misuse checks (may help performance)")
  parser.set_defaults(rendguard_enabled=ENABLE_RENDGUARD)

  parser.add_argument("--enable_cbtverify", dest="cbtverify_enabled",
                      action="store_true",
                      help="Enable Circuit Build Time monitoring")
  parser.set_defaults(cbtverify_enabled=ENABLE_CBTVERIFY)

  parser.add_argument("--enable_pathverify", dest="pathverify_enabled",
                      action="store_true",
                      help="Enable path selection monitoring")
  parser.set_defaults(pathverify_enabled=ENABLE_PATHVERIFY)

  options = parser.parse_args()

  (STATE_FILE, CONTROL_IP, CONTROL_PORT, CONTROL_SOCKET, CONTROL_PASS,
   ENABLE_BANDGUARDS, ENABLE_RENDGUARD, ENABLE_LOGGUARD, ENABLE_CBTVERIFY,
   ENABLE_PATHVERIFY, ONE_SHOT_VANGUARDS, ENABLE_VANGUARDS) = \
      (options.state_file, options.control_ip, options.control_port,
       options.control_socket, options.control_pass,
       options.bandguards_enabled, options.rendguard_enabled,
       options.logguard_enabled,
       options.cbtverify_enabled, options.pathverify_enabled,
       options.one_shot_vanguards, options.vanguards_enabled)

  if options.loglevel != None:
    LOGLEVEL = options.loglevel
  logger.set_loglevel(LOGLEVEL)

  if options.logfile != None:
    LOGFILE = options.logfile

  if LOGFILE != "":
    logger.set_logfile(LOGFILE)

  if options.write_file != None:
    config = generate_config()
    config.write(open(options.write_file, "w"))
    plog("NOTICE", "Wrote config to "+options.write_file)
    sys.exit(0)

  # If control_ip is a domain name, try to resolve it.
  if options.control_ip != None:
    try:
      _ = ipaddress.ip_address(options.control_ip)
    except ValueError:
      try:
        # We're fine with AF_INET, stem supports only IPv4 addresses anyway.
        addr = socket.getaddrinfo(options.control_ip, None, socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        CONTROL_IP = addr[0][4][0]
      except socket.gaierror:
        plog("ERROR", "Failed to resolve hostname "+options.control_ip)
        sys.exit(1)

  plog("DEBUG", "Applied command line options")

  return options

# Avoid a big messy dict of defaults. We already have them.
def get_option(config, section, option, default):
  try:
    if type(default) == bool:
      ret = config.get(section, option) == "True"
    else:
      ret = type(default)(config.get(section, option))
  except Error as e:
    return default
  return ret

def get_options_for_module(config, module, section):
  for param in dir(module):
    if param.isupper() and param[0] != '_':
      val = getattr(module, param)
      setattr(module, param,
              get_option(config, section, param.lower(), val))

def set_options_from_module(config, module, section):
  config.add_section(section)
  for param in dir(module):
    if param.isupper() and param[0] != '_':
      val = getattr(module, param)
      config.set(section, param, str(val))

def generate_config():
  config = ConfigParser(allow_no_value=True)
  set_options_from_module(config, sys.modules[__name__], "Global")
  set_options_from_module(config, vanguards, "Vanguards")
  set_options_from_module(config, bandguards, "Bandguards")
  set_options_from_module(config, rendguard, "Rendguard")
  set_options_from_module(config, rendguard, "Logguard")

  return config

def apply_config(config_file):
  config = ConfigParser(allow_no_value=True)

  config.readfp(open(config_file, "r"))

  get_options_for_module(config, sys.modules[__name__], "Global")
  get_options_for_module(config, vanguards, "Vanguards")
  get_options_for_module(config, bandguards, "Bandguards")
  get_options_for_module(config, rendguard, "Rendguard")
  get_options_for_module(config, rendguard, "Logguard")

  # Special cased CLOSE_CIRCUITS option has to be transfered
  # to the control.py module
  setattr(control, "_CLOSE_CIRCUITS", CLOSE_CIRCUITS)


  plog("NOTICE", "Vanguards successfilly applied config options from "+
       config_file)
