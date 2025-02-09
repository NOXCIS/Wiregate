import os
import configparser
import pyotp
import bcrypt
import secrets
import ipaddress
from typing import Any

from . shared import (
    sqlSelect, sqlUpdate
)

from ..Utilities import ValidateDNSAddress

#from . DashboardAPIkey import DashboardAPIKey

from . config import (
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
    wgd_remote_endpoint
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
                "type": "sqlite"
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
        existingTable = sqlSelect(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'DashboardAPIKeys'").fetchall()
        if len(existingTable) == 0:
            sqlUpdate(
                "CREATE TABLE DashboardAPIKeys (Key VARCHAR NOT NULL PRIMARY KEY, CreatedAt DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')), ExpiredAt VARCHAR)")

    def __getAPIKeys(self) -> list[DashboardAPIKey]:
        keys = sqlSelect(
            "SELECT * FROM DashboardAPIKeys WHERE ExpiredAt IS NULL OR ExpiredAt > datetime('now', 'localtime') ORDER BY CreatedAt DESC").fetchall()
        fKeys = []
        for k in keys:
            fKeys.append(DashboardAPIKey(*k))
        return fKeys

    def createAPIKeys(self, ExpiredAt=None):
        newKey = secrets.token_urlsafe(32)
        sqlUpdate('INSERT INTO DashboardAPIKeys (Key, ExpiredAt) VALUES (?, ?)', (newKey, ExpiredAt,))

        self.DashboardAPIKeys = self.__getAPIKeys()

    def deleteAPIKey(self, key):
        sqlUpdate("UPDATE DashboardAPIKeys SET ExpiredAt = datetime('now', 'localtime') WHERE Key = ?", (key,))
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

        if self.__config[section][key] in ["1", "yes", "true", "on"]:
            return True, True

        if self.__config[section][key] in ["0", "no", "false", "off"]:
            return True, False

        if section == "WireGuardConfiguration" and key == "autostart":
            return True, list(filter(lambda x: len(x) > 0, self.__config[section][key].split("||")))

        return True, self.__config[section][key]

    def toJson(self) -> dict[str, dict[Any, Any]]:
        the_dict = {}

        for section in self.__config.sections():
            the_dict[section] = {}
            for key, val in self.__config.items(section):
                if key not in self.hiddenAttribute:
                    the_dict[section][key] = self.GetConfig(section, key)[1]
        return the_dict


DashboardConfig = DashboardConfig()