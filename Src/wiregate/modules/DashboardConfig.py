import os
import configparser
import pyotp
import bcrypt
import secrets
import ipaddress
from typing import Any


from .DataBase import (
    sqlSelect, sqlUpdate
)

from .Utilities import ValidateDNSAddress

#from . DashboardAPIkey import DashboardAPIKey

from .Config import (
    DASHBOARD_VERSION, DASHBOARD_CONF,
    wgd_config_path,
    wgd_welcome,
    wgd_app_port,
    wgd_auth_req,
    wgd_user,
    wgd_pass,
    wgd_global_dns,
    wgd_peer_endpoint_allowed_ip,
    wgd_keep_alive,
    wgd_mtu,
    wgd_remote_endpoint,
    redis_host,
    redis_port,
    redis_db,
    redis_password,
    postgres_host,
    postgres_port,
    postgres_db,
    postgres_user,
    postgres_password,
    postgres_ssl_mode
)

class DashboardAPIKey:
    def __init__(self, Key: str, CreatedAt: str, ExpiredAt: str):
        self.Key = Key
        self.CreatedAt = CreatedAt
        self.ExpiredAt = ExpiredAt

    def toJson(self):
        return self.__dict__

class DashboardConfig:

    def __init__(self):
        if not os.path.exists(DASHBOARD_CONF):
            open(DASHBOARD_CONF, "x")
        self.__config = configparser.ConfigParser(strict=False)
        self.__config.read_file(open(DASHBOARD_CONF, "r+"))
        self.hiddenAttribute = ["totp_key", "auth_req"]
        self.__default = {
            "Account": {
                "username": wgd_user,
                "password": wgd_pass,
                "enable_totp": "false",
                "totp_verified": "false",
                "totp_key": pyotp.random_base32()
            },
            "Server": {
                "wg_conf_path": wgd_config_path,
                "iptable_rules_path": "./iptable-rules",
                "app_prefix": "",
                "app_ip": "0.0.0.0",
                "app_port": wgd_app_port,
                "auth_req": wgd_auth_req,
                "version": DASHBOARD_VERSION,
                "dashboard_refresh_interval": "60000",
                "dashboard_sort": "status",
                "dashboard_theme": "dark",
                "dashboard_api_key": "false",
                "dashboard_language": "en"
            },
            "Peers": {
                "peer_global_DNS": wgd_global_dns,
                "peer_endpoint_allowed_ip": wgd_peer_endpoint_allowed_ip,
                "peer_display_mode": "grid",
                "remote_endpoint": wgd_remote_endpoint,
                "peer_MTU": wgd_mtu,
                "peer_keep_alive": wgd_keep_alive

            },
            "Other": {
                "welcome_session": wgd_welcome
            },
            "Database": {
                "redis_host": redis_host,
                "redis_port": redis_port,
                "redis_db": redis_db,
                "redis_password": redis_password,
                "postgres_host": postgres_host,
                "postgres_port": postgres_port,
                "postgres_db": postgres_db,
                "postgres_user": postgres_user,
                "postgres_password": postgres_password,
                "postgres_ssl_mode": postgres_ssl_mode,
                "cache_enabled": True,
                "cache_ttl": 300
            },
            "Email":{
                "server": "",
                "port": "",
                "encryption": "",
                "username": "",
                "email_password": "",
                "send_from": "",
                "email_template": ""
            },
            "WireGuardConfiguration": {
                "autostart": ""
            },
            "LDAP": {
                "enabled": "false",
                "server": "",
                "port": "389",
                "use_ssl": "false",
                "bind_dn": "",
                "bind_password": "",
                "search_base": "",
                "search_filter": "(sAMAccountName=%%s)",
                "require_group": "false",
                "group_dn": "",
                "attr_username": "sAMAccountName",
                "attr_email": "mail",
                "attr_firstname": "givenName",
                "attr_lastname": "sn",
                "domain": ""
            }
        }

        for section, keys in self.__default.items():
            for key, value in keys.items():
                exist, currentData = self.GetConfig(section, key)
                if not exist:
                    self.SetConfig(section, key, value, True)
        self.__createAPIKeyTable()
        self.DashboardAPIKeys = self.__getAPIKeys()
        self.APIAccessed = False
        self.SetConfig("Server", "version", DASHBOARD_VERSION)

    def __createAPIKeyTable(self):
        # Check if table exists using database-agnostic approach
        from wiregate.modules.DataBase import get_redis_manager
        manager = get_redis_manager()
        
        # Use the appropriate method based on database type
        if hasattr(manager, 'table_exists'):
            # PostgreSQL/Redis manager
            table_exists = manager.table_exists('DashboardAPIKeys')
        else:
            # SQLite manager - check using PRAGMA
            try:
                result = sqlSelect("SELECT name FROM sqlite_master WHERE type='table' AND name='DashboardAPIKeys'").fetchall()
                table_exists = len(result) > 0
            except:
                table_exists = False
        
        if not table_exists:
            sqlUpdate(
                "CREATE TABLE IF NOT EXISTS DashboardAPIKeys (Key VARCHAR NOT NULL PRIMARY KEY, CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, ExpiredAt TIMESTAMP)")

    def __getAPIKeys(self) -> list[DashboardAPIKey]:
        keys = sqlSelect(
            "SELECT * FROM DashboardAPIKeys WHERE ExpiredAt IS NULL OR ExpiredAt > CURRENT_TIMESTAMP ORDER BY CreatedAt DESC").fetchall()
        fKeys = []
        for k in keys:
            fKeys.append(DashboardAPIKey(*k))
        return fKeys

    def createAPIKeys(self, ExpiredAt=None):
        newKey = secrets.token_urlsafe(32)
        sqlUpdate('INSERT INTO DashboardAPIKeys (Key, ExpiredAt) VALUES (%s, %s)', (newKey, ExpiredAt,))

        self.DashboardAPIKeys = self.__getAPIKeys()

    def deleteAPIKey(self, key):
        sqlUpdate("UPDATE DashboardAPIKeys SET ExpiredAt = CURRENT_TIMESTAMP WHERE Key = %s", (key,))
        self.DashboardAPIKeys = self.__getAPIKeys()

    def __configValidation(self, key, value: Any) -> tuple[bool, str]:
        if type(value) is str and len(value) == 0:
            return False, "Field cannot be empty!"
        if key == "peer_global_dns":
            return ValidateDNSAddress(value)
        if key == "peer_endpoint_allowed_ip":
            value = value.split(",")
            for i in value:
                try:
                    ipaddress.ip_network(i, strict=False)
                except Exception as e:
                    return False, str(e)
        if key == "wg_conf_path":
            if not os.path.exists(value):
                return False, f"{value} is not a valid path"
        if key == "password":
            if self.GetConfig("Account", "password")[0]:
                if not self.__checkPassword(
                        value["currentPassword"], self.GetConfig("Account", "password")[1].encode("utf-8")):
                    return False, "Current password does not match."
                if value["newPassword"] != value["repeatNewPassword"]:
                    return False, "New passwords does not match"
        # Database password validation
        if key in ["redis_password", "postgres_password"]:
            if isinstance(value, dict) and "currentPassword" in value:
                # Password change validation
                current_password = self.GetConfig("Database", key)[1]
                if not self.__checkPassword(value["currentPassword"], current_password.encode("utf-8")):
                    return False, "Current password does not match."
                if value["newPassword"] != value["repeatNewPassword"]:
                    return False, "New passwords do not match."
        return True, ""

    def generatePassword(self, plainTextPassword: str):
        return bcrypt.hashpw(plainTextPassword.encode("utf-8"), bcrypt.gensalt())

    def __checkPassword(self, plainTextPassword: str, hashedPassword: bytes):
        return bcrypt.checkpw(plainTextPassword.encode("utf-8"), hashedPassword)

    def SetConfig(self, section: str, key: str, value: any, init: bool = False) -> tuple[bool, str]:
        if key in self.hiddenAttribute and not init:
            return False, None

        if not init:
            valid, msg = self.__configValidation(key, value)
            if not valid:
                return False, msg

        if section == "Account" and key == "password":
            if not init:
                value = self.generatePassword(value["newPassword"]).decode("utf-8")
            else:
                value = self.generatePassword(value).decode("utf-8")
        
        # Handle database password hashing
        if section == "Database" and key in ["redis_password", "postgres_password"]:
            if not init and isinstance(value, dict) and "newPassword" in value:
                # Password change - hash the new password
                value = self.generatePassword(value["newPassword"]).decode("utf-8")
            elif init:
                # Initial setup - hash the password
                value = self.generatePassword(value).decode("utf-8")

        if section == "Server" and key == "wg_conf_path":
            if not os.path.exists(value):
                return False, "Path does not exist"

        if section not in self.__config:
            self.__config[section] = {}

        if key not in self.__config[section].keys() or value != self.__config[section][key]:
            if type(value) is bool:
                if value:
                    self.__config[section][key] = "true"
                else:
                    self.__config[section][key] = "false"
            elif type(value) in [int, float]:
                self.__config[section][key] = str(value)
            elif type(value) is list:
                self.__config[section][key] = "||".join(value).strip("||")
            else:
                self.__config[section][key] = value
            return self.SaveConfig(), ""
        return True, ""

    def SaveConfig(self) -> bool:
        try:
            with open(DASHBOARD_CONF, "w+", encoding='utf-8') as configFile:
                self.__config.write(configFile)
            return True
        except Exception as e:
            return False

    def GetConfig(self, section, key) -> tuple[bool, any]:
        if section not in self.__config:
            return False, None

        if key not in self.__config[section]:
            return False, None

        value = self.__config[section][key]
        
        # Handle boolean values - check for common boolean patterns
        if value in ["1", "yes", "true", "on"]:
            return True, True
        if value in ["0", "no", "false", "off"]:
            return True, False

        if section == "WireGuardConfiguration" and key == "autostart":
            return True, list(filter(lambda x: len(x) > 0, value.split("||")))
        
        # Mask database passwords when retrieving
        if section == "Database" and key in ["redis_password", "postgres_password"]:
            return True, "***"  # Always return masked password

        # Handle numeric values for database configuration
        if section == "Database" and key in ["redis_port", "redis_db", "postgres_port", "cache_ttl"]:
            try:
                return True, int(value)
            except (ValueError, TypeError):
                return True, value

        return True, value

    def toJson(self) -> dict[str, dict[Any, Any]]:
        the_dict = {}

        for section in self.__config.sections():
            the_dict[section] = {}
            for key, val in self.__config.items(section):
                if key not in self.hiddenAttribute:
                    the_dict[section][key] = self.GetConfig(section, key)[1]
        return the_dict


DashboardConfig = DashboardConfig()