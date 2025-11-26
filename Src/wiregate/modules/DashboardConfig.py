import os
import configparser
import pyotp
import bcrypt
import secrets
import ipaddress
import logging
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


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
    wgd_app_prefix,
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
    def __init__(self, Key: str, CreatedAt: str, ExpiredAt: Optional[str]):
        self.Key = Key
        self.CreatedAt = CreatedAt
        self.ExpiredAt = ExpiredAt

    def toJson(self) -> Dict[str, Any]:
        return self.__dict__


class PasswordManager:
    """Manages password hashing and validation"""
    
    @staticmethod
    def hash_password(plain_text_password: str) -> bytes:
        """Hash a plain text password using bcrypt"""
        return bcrypt.hashpw(plain_text_password.encode("utf-8"), bcrypt.gensalt())
    
    @staticmethod
    def verify_password(plain_text_password: str, hashed_password: bytes) -> bool:
        """Verify a plain text password against a hashed password"""
        return bcrypt.checkpw(plain_text_password.encode("utf-8"), hashed_password)
    
    @staticmethod
    def validate_password_change(current_password: str, new_password: str, repeat_password: str, stored_hash: str) -> Tuple[bool, str]:
        """Validate a password change request"""
        if new_password != repeat_password:
            return False, "New passwords do not match."
        try:
            if not PasswordManager.verify_password(current_password, stored_hash.encode("utf-8")):
                return False, "Current password does not match."
        except Exception as e:
            logger.warning(f"Password verification error: {e}")
            return False, "Password verification failed."
        return True, ""


class APIKeyManager:
    """Manages API key operations"""
    
    def __init__(self):
        # Use asyncio.run() since __init__ can't be async
        import asyncio
        asyncio.run(self._ensure_table_exists())
        self.DashboardAPIKeys = asyncio.run(self._get_api_keys())
    
    async def _ensure_table_exists(self):
        """Ensure the DashboardAPIKeys table exists"""
        from wiregate.modules.DataBase import get_redis_manager
        manager = await get_redis_manager()
        
        # Use the appropriate method based on database type
        if hasattr(manager, 'table_exists'):
            # PostgreSQL/Redis manager
            table_exists = manager.table_exists('DashboardAPIKeys')
        else:
            # SQLite manager - check using PRAGMA
            try:
                cursor = await sqlSelect("SELECT name FROM sqlite_master WHERE type='table' AND name='DashboardAPIKeys'")
                result = cursor.fetchall()
                table_exists = len(result) > 0
            except Exception as e:
                logger.warning(f"Failed to check if DashboardAPIKeys table exists: {e}")
                table_exists = False
        
        if not table_exists:
            await sqlUpdate(
                "CREATE TABLE IF NOT EXISTS DashboardAPIKeys (Key VARCHAR NOT NULL PRIMARY KEY, CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, ExpiredAt TIMESTAMP)")
    
    async def _get_api_keys(self) -> list[DashboardAPIKey]:
        """Get all active API keys"""
        logger.debug("[APIKeyManager._get_api_keys] Fetching API keys from database...")
        try:
            cursor_result = await sqlSelect(
                "SELECT * FROM DashboardAPIKeys WHERE ExpiredAt IS NULL OR ExpiredAt > CURRENT_TIMESTAMP ORDER BY CreatedAt DESC")
            
            if cursor_result is None:
                logger.warning("[APIKeyManager._get_api_keys] sqlSelect returned None")
                return []
            
            keys = cursor_result.fetchall()
            if keys is None:
                logger.warning("[APIKeyManager._get_api_keys] fetchall() returned None")
                return []
            
            logger.debug(f"[APIKeyManager._get_api_keys] Raw query returned {len(keys)} rows")
            fKeys = []
            for k in keys:
                if k is None:
                    logger.warning("[APIKeyManager._get_api_keys] Skipping None row")
                    continue
                
                try:
                    # Handle both dict-like objects and tuples
                    if hasattr(k, 'get') and callable(getattr(k, 'get', None)):
                        # Dict-like object (from SQLiteCursor or PostgreSQLCursor)
                        # Try both uppercase and lowercase column names (PostgreSQL converts to lowercase)
                        key_value = None
                        for col_name in ['Key', 'key', 'KEY']:
                            if hasattr(k, col_name):
                                key_value = getattr(k, col_name)
                                break
                            elif hasattr(k, 'get'):
                                key_value = k.get(col_name)
                                if key_value is not None:
                                    break
                        
                        created_at = None
                        for col_name in ['CreatedAt', 'createdat', 'CREATEDAT', 'created_at']:
                            if hasattr(k, col_name):
                                created_at = getattr(k, col_name)
                                break
                            elif hasattr(k, 'get'):
                                created_at = k.get(col_name)
                                if created_at is not None:
                                    break
                        
                        expired_at = None
                        for col_name in ['ExpiredAt', 'expiredat', 'EXPIREDAT', 'expired_at']:
                            if hasattr(k, col_name):
                                expired_at = getattr(k, col_name)
                                break
                            elif hasattr(k, 'get'):
                                expired_at = k.get(col_name)
                                if expired_at is not None:
                                    break
                        
                        if key_value is None:
                            logger.warning(f"[APIKeyManager._get_api_keys] Skipping row with None key_value. Available attributes: {[attr for attr in dir(k) if not attr.startswith('_')]}")
                            continue
                        
                        logger.debug(f"[APIKeyManager._get_api_keys] Processing key: {str(key_value)[:10] if key_value else 'None'}... (expires: {expired_at})")
                        fKeys.append(DashboardAPIKey(key_value, created_at, expired_at))
                    elif hasattr(k, 'Key'):
                        # Direct attribute access
                        key_value = getattr(k, 'Key', None)
                        created_at = getattr(k, 'CreatedAt', None)
                        expired_at = getattr(k, 'ExpiredAt', None)
                        
                        if key_value is None:
                            logger.warning("[APIKeyManager._get_api_keys] Skipping row with None key_value (direct access)")
                            continue
                        
                        logger.debug(f"[APIKeyManager._get_api_keys] Processing key (direct): {str(key_value)[:10] if key_value else 'None'}... (expires: {expired_at})")
                        fKeys.append(DashboardAPIKey(key_value, created_at, expired_at))
                    else:
                        # Tuple (legacy format)
                        if not k or len(k) == 0:
                            logger.warning("[APIKeyManager._get_api_keys] Skipping empty tuple row")
                            continue
                        if k[0] is None:
                            logger.warning("[APIKeyManager._get_api_keys] Skipping tuple row with None key")
                            continue
                        logger.debug(f"[APIKeyManager._get_api_keys] Processing tuple key: {str(k[0])[:10] if k[0] else 'None'}...")
                        fKeys.append(DashboardAPIKey(*k))
                except Exception as row_error:
                    logger.error(f"[APIKeyManager._get_api_keys] Error processing row: {row_error}. Row type: {type(k)}, Row: {k}")
                    continue
            logger.debug(f"[APIKeyManager._get_api_keys] Returning {len(fKeys)} active API keys")
            return fKeys
        except Exception as e:
            logger.error(f"[APIKeyManager._get_api_keys] Error fetching API keys: {e}", exc_info=True)
            return []
    
    async def create_api_key(self, expired_at: Optional[str] = None) -> str:
        """Create a new API key"""
        logger.debug(f"[APIKeyManager.create_api_key] Creating new API key (expired_at: {expired_at})")
        new_key = secrets.token_urlsafe(32)
        logger.debug(f"[APIKeyManager.create_api_key] Generated key: {new_key[:20]}...")
        
        try:
            result = await sqlUpdate('INSERT INTO DashboardAPIKeys (Key, ExpiredAt) VALUES (%s, %s)', (new_key, expired_at,))
            logger.debug(f"[APIKeyManager.create_api_key] SQL update result: {result}")
            if not result:
                logger.error("[APIKeyManager.create_api_key] SQL update returned False - insert may have failed")
            else:
                logger.debug("[APIKeyManager.create_api_key] SQL insert successful")
            
            self.DashboardAPIKeys = await self._get_api_keys()
            logger.debug(f"[APIKeyManager.create_api_key] Refreshed API keys list. Total keys: {len(self.DashboardAPIKeys)}")
            return new_key
        except Exception as e:
            logger.error(f"[APIKeyManager.create_api_key] Error creating API key: {e}", exc_info=True)
            raise
    
    async def delete_api_key(self, key: str) -> None:
        """Delete (expire) an API key"""
        logger.debug(f"[APIKeyManager.delete_api_key] Attempting to delete key: {key[:20] if key else 'None'}...")
        try:
            result = await sqlUpdate("UPDATE DashboardAPIKeys SET ExpiredAt = CURRENT_TIMESTAMP WHERE Key = %s", (key,))
            logger.debug(f"[APIKeyManager.delete_api_key] SQL update result: {result}")
            if not result:
                logger.error("[APIKeyManager.delete_api_key] SQL update returned False - update may have failed")
            else:
                logger.debug("[APIKeyManager.delete_api_key] SQL update successful")
            
            self.DashboardAPIKeys = await self._get_api_keys()
            logger.debug(f"[APIKeyManager.delete_api_key] Refreshed API keys list. Remaining keys: {len(self.DashboardAPIKeys)}")
        except Exception as e:
            logger.error(f"[APIKeyManager.delete_api_key] Error deleting API key: {e}", exc_info=True)
            raise
    
    async def get_api_keys(self) -> list[DashboardAPIKey]:
        """Get all active API keys"""
        return await self._get_api_keys()


class ConfigManager:
    """Manages INI configuration file operations"""
    
    def __init__(self, config_path: str, default_config: dict):
        self.config_path = config_path
        self.hidden_attributes = ["totp_key", "auth_req"]
        
        # Ensure config file exists
        if not os.path.exists(config_path):
            try:
                with open(config_path, "x") as f:
                    pass
            except OSError as e:
                logger.error(f"Failed to create config file {config_path}: {e}")
                raise
        
        # Load config
        self._config = configparser.ConfigParser(strict=False)
        try:
            with open(config_path, "r+", encoding='utf-8') as config_file:
                self._config.read_file(config_file)
        except Exception as e:
            logger.warning(f"Failed to read config file, using defaults: {e}")
        
        # Initialize defaults
        for section, keys in default_config.items():
            for key, value in keys.items():
                exist, _ = self.get_config(section, key)
                if not exist:
                    self.set_config(section, key, value, init=True)
    
    def get_config(self, section: str, key: str, masked: bool = True) -> Tuple[bool, Any]:
        """Get a configuration value"""
        if section not in self._config:
            return False, None
        
        if key not in self._config[section]:
            return False, None
        
        value = self._config[section][key]
        
        # Handle boolean values - check for common boolean patterns
        if value in ["1", "yes", "true", "on"]:
            return True, True
        if value in ["0", "no", "false", "off"]:
            return True, False
        
        if section == "WireGuardConfiguration" and key == "autostart":
            return True, list(filter(lambda x: len(x) > 0, value.split("||")))
        
        # Mask database passwords when retrieving (unless masked=False for internal use)
        if section == "Database" and key in ["redis_password", "postgres_password"]:
            if masked:
                return True, "***"  # Return masked password for API/public access
            else:
                return True, value  # Return actual password for internal use
        
        # Handle numeric values for database configuration
        if section == "Database" and key in ["redis_port", "redis_db", "postgres_port", "cache_ttl"]:
            try:
                return True, int(value)
            except (ValueError, TypeError):
                return True, value
        
        return True, value
    
    def set_config(self, section: str, key: str, value: Any, init: bool = False) -> Tuple[bool, str]:
        """Set a configuration value"""
        if key in self.hidden_attributes and not init:
            return False, "Cannot modify hidden attribute"
        
        if section not in self._config:
            self._config[section] = {}
        
        # Convert value to string for storage
        if type(value) is bool:
            str_value = "true" if value else "false"
        elif type(value) in [int, float]:
            str_value = str(value)
        elif type(value) is list:
            str_value = "||".join(value).strip("||")
        else:
            str_value = value
        
        if key not in self._config[section].keys() or str_value != self._config[section][key]:
            self._config[section][key] = str_value
            return self.save_config(), ""
        return True, ""
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, "w+", encoding='utf-8') as config_file:
                self._config.write(config_file)
            return True
        except Exception as e:
            logger.error(f"Failed to save config file {self.config_path}: {e}")
            return False
    
    def to_json(self) -> Dict[str, Dict[Any, Any]]:
        """Convert configuration to JSON dictionary"""
        the_dict = {}
        for section in self._config.sections():
            the_dict[section] = {}
            for key, _ in self._config.items(section):
                if key not in self.hidden_attributes:
                    the_dict[section][key] = self.get_config(section, key)[1]
        return the_dict


class DashboardConfig:
    """Facade class that uses ConfigManager, APIKeyManager, and PasswordManager"""
    
    def __init__(self):
        # Initialize default configuration
        default_config = {
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
                "app_prefix": wgd_app_prefix,
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
        
        # Initialize managers
        self._config_manager = ConfigManager(DASHBOARD_CONF, default_config)
        self._api_key_manager = APIKeyManager()
        self._password_manager = PasswordManager()
        
        # Backward compatibility attributes
        self.hiddenAttribute = self._config_manager.hidden_attributes
        self.DashboardAPIKeys = self._api_key_manager.DashboardAPIKeys
        self.APIAccessed = False
        
        # Set version
        self.SetConfig("Server", "version", DASHBOARD_VERSION)
    
    def _validate_config(self, key: str, value: Any) -> Tuple[bool, str]:
        """Validate configuration value"""
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
                stored_hash = self.GetConfig("Account", "password", masked=False)[1]
                if not self._password_manager.verify_password(
                        value["currentPassword"], stored_hash.encode("utf-8")):
                    return False, "Current password does not match."
                if value["newPassword"] != value["repeatNewPassword"]:
                    return False, "New passwords do not match"
        # Database password validation
        if key in ["redis_password", "postgres_password"]:
            if isinstance(value, dict) and "currentPassword" in value:
                # Password change validation - need actual hash to compare, so use masked=False
                current_password_hash = self.GetConfig("Database", key, masked=False)[1]
                valid, msg = self._password_manager.validate_password_change(
                    value["currentPassword"], 
                    value["newPassword"], 
                    value["repeatNewPassword"],
                    current_password_hash
                )
                if not valid:
                    return False, msg
        return True, ""
    
    def GetConfig(self, section: str, key: str, masked: bool = True) -> Tuple[bool, Any]:
        """Get configuration value (backward compatible)"""
        return self._config_manager.get_config(section, key, masked)
    
    def SetConfig(self, section: str, key: str, value: Any, init: bool = False) -> Tuple[bool, str]:
        """Set configuration value (backward compatible)"""
        if key in self.hiddenAttribute and not init:
            return False, "Cannot modify hidden attribute"
        
        if not init:
            valid, msg = self._validate_config(key, value)
            if not valid:
                return False, msg
        
        # Handle password hashing
        if section == "Account" and key == "password":
            if not init:
                value = self._password_manager.hash_password(value["newPassword"]).decode("utf-8")
            else:
                # Only hash if the password is not already hashed (bcrypt hashes start with $2b$)
                if isinstance(value, str) and not value.startswith('$2b$'):
                    value = self._password_manager.hash_password(value).decode("utf-8")
        
        # Handle database password hashing
        if section == "Database" and key in ["redis_password", "postgres_password"]:
            if not init and isinstance(value, dict) and "newPassword" in value:
                # Password change - hash the new password
                value = self._password_manager.hash_password(value["newPassword"]).decode("utf-8")
            elif init:
                # Initial setup - hash the password
                value = self._password_manager.hash_password(value).decode("utf-8")
        
        if section == "Server" and key == "wg_conf_path":
            if not os.path.exists(value):
                return False, "Path does not exist"
        
        return self._config_manager.set_config(section, key, value, init)
    
    def SaveConfig(self) -> bool:
        """Save configuration (backward compatible)"""
        return self._config_manager.save_config()
    
    def toJson(self) -> Dict[str, Dict[Any, Any]]:
        """Convert configuration to JSON (backward compatible)"""
        return self._config_manager.to_json()
    
    # API Key methods (backward compatible)
    async def createAPIKeys(self, ExpiredAt: Optional[str] = None) -> None:
        """Create API key (backward compatible)"""
        await self._api_key_manager.create_api_key(ExpiredAt)
        self.DashboardAPIKeys = await self._api_key_manager.get_api_keys()
    
    async def deleteAPIKey(self, key: str) -> None:
        """Delete API key (backward compatible)"""
        await self._api_key_manager.delete_api_key(key)
        self.DashboardAPIKeys = await self._api_key_manager.get_api_keys()
    
    # Password methods (backward compatible)
    def generatePassword(self, plainTextPassword: str) -> bytes:
        """Generate password hash (backward compatible)"""
        return self._password_manager.hash_password(plainTextPassword)


DashboardConfig = DashboardConfig()