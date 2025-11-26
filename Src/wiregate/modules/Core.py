import shutil, configparser, psutil
import os, subprocess, uuid, datetime, time
import ipaddress, json, re
import logging
import asyncio
import aiofiles
import secrets
import hashlib
from typing import Optional, Any

from datetime import datetime, timedelta

logger = logging.getLogger('wiregate')
 
from .DashboardConfig import DashboardConfig
from .Utilities import (
    StringToBoolean, ValidateIPAddressesWithRange,
    ValidateDNSAddress, RegexMatch, strToBool,
    GenerateWireguardPublicKey, get_backup_paths,
    ResponseObject, ValidateCPSFormat, NormalizeCPSFormat
)


from .Jobs import PeerJobLogger, PeerJob, PeerJobs
from .Locale.Locale import Locale

from .Share.ShareLink import PeerShareLinks
from .Share.ShareLink import PeerShareLink
from .DataBase import (
    ConfigurationDatabase, check_and_migrate_sqlite_databases
)
from .Security import (
    execute_wg_command, execute_wg_quick_command, 
    execute_awg_command, execute_awg_quick_command,
    execute_ip_command, 
)


from .Share.ShareLink import AllPeerShareLinks
from .Jobs import AllPeerJobs


class Configuration:
    class InvalidConfigurationFileException(Exception):
        def __init__(self, m):
            self.message = m

        def __str__(self):
            return self.message

    def __init__(self, name: str = None, data: dict = None, backup: dict = None, startup: bool = False):
        self.__parser: configparser.ConfigParser = configparser.ConfigParser(strict=False)
        self.__parser.optionxform = str
        self.__configFileModifiedTime = None

        self.Status: bool = False
        self.Name: str = ""
        self.PrivateKey: str = ""
        self.PublicKey: str = ""
        self.ListenPort: str = ""
        self.Address: str = ""
        self.DNS: str = ""
        self.Table: str = ""
        self.Jc: str = ""
        self.Jmin: str = ""
        self.Jmax: str = ""
        self.S1: str = ""
        self.S2: str = ""
        self.H1: str = ""
        self.H2: str = ""
        self.H3: str = ""
        self.H4: str = ""
        self.I1: str = ""
        self.I2: str = ""
        self.I3: str = ""
        self.I4: str = ""
        self.I5: str = ""
        self.MTU: str = ""
        self.PreUp: str = ""
        self.PostUp: str = ""
        self.PreDown: str = ""
        self.PostDown: str = ""
        self.SaveConfig: bool = True
        self.Name = name
        self.Protocol = self.get_iface_proto()

        self.configPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf')

        backupPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')
        if not os.path.exists(backupPath):
            os.mkdir(backupPath)

        # Initialize database manager
        self.db = ConfigurationDatabase(self.Name)
        
        # Initialize CPS pattern adaptation (lightweight ML auto-adaptation)
        try:
            from .AwgCPS.CPSPatternAdaptation import CPSPatternAdaptation
            self.cps_adaptation = CPSPatternAdaptation(self.Name, self.db)
        except Exception as e:
            logger.warning(f"Failed to initialize CPS pattern adaptation: {e}")
            self.cps_adaptation = None

        if name is not None:
            # NOTE: Database operations and file parsing are now handled in create_async()
            # This __init__ method is kept for backward compatibility but should not be used
            # for new code. Use Configuration.create_async() instead.
            # 
            # For sync initialization (legacy code), we still parse the config file
            # but database operations run through async helpers
            self.__parseConfigurationFileSync()
            asyncio.run(self.__initPeersList())

        else:
            self.Name = data["ConfigurationName"]
            self.configPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf')

            for i in dir(self):
                if str(i) in data.keys():
                    if isinstance(getattr(self, i), bool):
                        setattr(self, i, StringToBoolean(data[i]))
                    else:
                        setattr(self, i, str(data[i]))
            
            # Normalize I1-I5 CPS parameters (convert raw hex 0x... to <b 0x...> format)
            if hasattr(self, 'I1') and self.I1:
                self.I1 = NormalizeCPSFormat(self.I1)
            if hasattr(self, 'I2') and self.I2:
                self.I2 = NormalizeCPSFormat(self.I2)
            if hasattr(self, 'I3') and self.I3:
                self.I3 = NormalizeCPSFormat(self.I3)
            if hasattr(self, 'I4') and self.I4:
                self.I4 = NormalizeCPSFormat(self.I4)
            if hasattr(self, 'I5') and self.I5:
                self.I5 = NormalizeCPSFormat(self.I5)

            self.__parser["Interface"] = {
                "PrivateKey": self.PrivateKey,
                "Address": self.Address,
                "ListenPort": self.ListenPort,
                "PreUp": self.PreUp,
                "PreDown": self.PreDown,
                "PostUp": self.PostUp,
                "PostDown": self.PostDown,
            }

            # Only add values if they are not empty or null
            if self.Jc:
                self.__parser["Interface"]["Jc"] = self.Jc
            if self.Jmin:
                self.__parser["Interface"]["Jmin"] = self.Jmin
            if self.Jmax:
                self.__parser["Interface"]["Jmax"] = self.Jmax
            if self.S1:
                self.__parser["Interface"]["S1"] = self.S1
            if self.S2:
                self.__parser["Interface"]["S2"] = self.S2
            if self.H1:
                self.__parser["Interface"]["H1"] = self.H1
            if self.H2:
                self.__parser["Interface"]["H2"] = self.H2
            if self.H3:
                self.__parser["Interface"]["H3"] = self.H3
            if self.H4:
                self.__parser["Interface"]["H4"] = self.H4
            # Scramble I1-I5 for interface config to ensure it doesn't match peer configs
            # Each configuration gets its own scrambled patterns that differ from peers
            if self.I1 and self.I1.strip():
                # Use configuration name as seed for interface scrambling
                interface_seed = f"{self.Name}_interface"
                scrambled_i1 = self._scramble_cps_pattern(self.I1, interface_seed + "_I1")
                self.__parser["Interface"]["I1"] = scrambled_i1
            if self.I2 and self.I2.strip():
                interface_seed = f"{self.Name}_interface"
                scrambled_i2 = self._scramble_cps_pattern(self.I2, interface_seed + "_I2")
                self.__parser["Interface"]["I2"] = scrambled_i2
            if self.I3 and self.I3.strip():
                interface_seed = f"{self.Name}_interface"
                scrambled_i3 = self._scramble_cps_pattern(self.I3, interface_seed + "_I3")
                self.__parser["Interface"]["I3"] = scrambled_i3
            if self.I4 and self.I4.strip():
                interface_seed = f"{self.Name}_interface"
                scrambled_i4 = self._scramble_cps_pattern(self.I4, interface_seed + "_I4")
                self.__parser["Interface"]["I4"] = scrambled_i4
            if self.I5 and self.I5.strip():
                interface_seed = f"{self.Name}_interface"
                scrambled_i5 = self._scramble_cps_pattern(self.I5, interface_seed + "_I5")
                self.__parser["Interface"]["I5"] = scrambled_i5

            # Add SaveConfig at the end, it seems like it's always True
            self.__parser["Interface"]["SaveConfig"] = "true"

            if "Backup" not in data.keys():
                self.db.create_database()
                # Ensure migration happens here too
                self.db.migrate_database()
                with open(self.configPath, "w+") as configFile:
                    self.__parser.write(configFile)
                self.__initPeersList()

        logger.info(f"Initialized Configuration: {name}")
        if self.getAutostartStatus() and not self.getStatus() and startup:
            self.toggleConfiguration()
            logger.info(f"Autostart Configuration: {name}")


    async def __initPeersList(self):
        self.Peers: list[Peer] = []
        await self.getPeersList()
        await self.getRestrictedPeersList()

    def getRawConfigurationFile(self):
        return open(self.configPath, 'r').read()

    async def updateRawConfigurationFile(self, newRawConfiguration):
        backupStatus, backup = self.backupConfigurationFile()
        if not backupStatus:
            # Extract error message if available
            error_msg = backup.get('error', 'Cannot create backup') if isinstance(backup, dict) else 'Cannot create backup'
            logger.error(f"Failed to create backup before raw config update: {error_msg}")
            return False, error_msg

        if self.Status:
            self.toggleConfiguration()

        with open(self.configPath, 'w') as f:
            f.write(newRawConfiguration)

        status, err = self.toggleConfiguration()
        if not status:
            restoreStatus = await self.restoreBackup(backup['filename'])
            logger.debug(f"Restore status: {restoreStatus}")
            self.toggleConfiguration()
            return False, err
        return True, None

    def get_script_path(self, script_path):
        """
        Resolve script path relative to WireGuard config directory
        """
        if not script_path:
            return None

        # Get WireGuard config directory
        wg_dir = DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
        # Normalize the config directory path to remove any trailing slashes
        wg_dir = os.path.normpath(wg_dir)

        if script_path.startswith('/'):
            # Absolute path
            return script_path
        else:
            # Remove any leading './' from both wg_dir and script_path
            clean_wg_dir = wg_dir.strip('./')
            clean_script_path = script_path.strip('./')

            # Combine and normalize the path to remove any duplicates
            full_path = os.path.normpath(os.path.join(clean_wg_dir, clean_script_path))

            # If the original path was relative (started with ./), preserve that
            if script_path.startswith('./') or wg_dir.startswith('./'):
                full_path = './' + full_path

            return full_path

    def getPostUp(self):
        """Extract and resolve PostUp script path"""
        if not self.PostUp:
            return []

        # Split multiple commands if any
        commands = self.PostUp.split(';')
        script_paths = []

        for cmd in commands:
            cmd = cmd.strip()
            if cmd.endswith('.sh') or cmd.endswith('.bash'):
                # If the command is just a script path
                script_paths.append(cmd)
            else:
                # Look for script paths in command parts
                parts = cmd.split()
                for part in parts:
                    if part.endswith('.sh') or part.endswith('.bash'):
                        script_paths.append(part)

        return [p for p in script_paths if p is not None]

    def getPreUp(self):
        """Extract and resolve PreUp script path"""
        if not self.PreUp:
            return []

        commands = self.PreUp.split(';')
        script_paths = []

        for cmd in commands:
            cmd = cmd.strip()
            if cmd.endswith('.sh') or cmd.endswith('.bash'):
                script_paths.append(cmd)
            else:
                parts = cmd.split()
                for part in parts:
                    if part.endswith('.sh') or part.endswith('.bash'):
                        script_paths.append(part)

        return [p for p in script_paths if p is not None]

    def getPreDown(self):
        """Extract and resolve PreDown script path"""
        if not self.PreDown:
            return []

        commands = self.PreDown.split(';')
        script_paths = []

        for cmd in commands:
            cmd = cmd.strip()
            if cmd.endswith('.sh') or cmd.endswith('.bash'):
                script_paths.append(cmd)
            else:
                parts = cmd.split()
                for part in parts:
                    if part.endswith('.sh') or part.endswith('.bash'):
                        script_paths.append(part)

        return [p for p in script_paths if p is not None]

    def getPostDown(self):
        """Extract and resolve PostDown script path"""
        if not self.PostDown:
            return []

        commands = self.PostDown.split(';')
        script_paths = []

        for cmd in commands:
            cmd = cmd.strip()
            if cmd.endswith('.sh') or cmd.endswith('.bash'):
                script_paths.append(cmd)
            else:
                parts = cmd.split()
                for part in parts:
                    if part.endswith('.sh') or part.endswith('.bash'):
                        script_paths.append(part)

        return [p for p in script_paths if p is not None]

    def __parseConfigurationFileSync(self):
        """Synchronous version of configuration file parsing for use in constructor"""
        with open(self.configPath, 'r') as f:
            content = f.read()
            original = [l.rstrip("\n") for l in content.splitlines()]
            try:
                start = original.index("[Interface]")

                # Clean
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], maxsplit=1)
                    if len(split) == 2:
                        key = split[0]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, False)
                            else:
                                setattr(self, key, "")

                # Set
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], maxsplit=1)
                    if len(split) == 2:
                        key = split[0]
                        value = split[1]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, value.lower() in ['true', '1', 'yes', 'on'])
                            elif isinstance(getattr(self, key), int):
                                try:
                                    setattr(self, key, int(value))
                                except ValueError:
                                    pass
                            else:
                                setattr(self, key, value)

            except ValueError:
                pass

    async def __parseConfigurationFile(self):
        async with aiofiles.open(self.configPath, 'r') as f:
            content = await f.read()
            original = [l.rstrip("\n") for l in content.splitlines()]
            try:
                start = original.index("[Interface]")

                # Clean
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], maxsplit=1)
                    if len(split) == 2:
                        key = split[0]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, False)
                            else:
                                setattr(self, key, "")

                # Set
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], maxsplit=1)
                    if len(split) == 2:
                        key = split[0]
                        value = split[1]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, StringToBoolean(value))
                            else:
                                if len(getattr(self, key)) > 0:
                                    setattr(self, key, f"{getattr(self, key)}, {value}")
                                else:
                                    setattr(self, key, value)
            except ValueError as e:
                raise self.InvalidConfigurationFileException(
                    "[Interface] section not found in " + self.configPath)
            logger.debug(f"Configuration {self.Name} parsed. PrivateKey length: {len(self.PrivateKey) if self.PrivateKey else 0}")
            if self.PrivateKey:
                self.PublicKey = self.__getPublicKey()
                logger.debug(f"Configuration {self.Name} PublicKey length: {len(self.PublicKey) if self.PublicKey else 0}")
            else:
                logger.warning(f"Configuration {self.Name} has no PrivateKey, skipping public key generation")
            self.Status = self.getStatus()

    async def __dropDatabase(self):
        """Drop database - now handled by ConfigurationDatabase"""
        await self.db.drop_database()

    async def __createDatabase(self, dbName=None):
        """Create database - now handled by ConfigurationDatabase"""
        await self.db.create_database(dbName)

    async def __migrateDatabase(self):
        """Migrate database - now handled by ConfigurationDatabase"""
        await self.db.migrate_database()

    def __dumpDatabase(self):
        """Dump database - now handled by ConfigurationDatabase"""
        return self.db.dump_database()

    async def __importDatabase(self, sqlFilePath) -> bool:
        """Import database - now handled by ConfigurationDatabase"""
        return await self.db.import_database(sqlFilePath)

    def __getPublicKey(self) -> str:
        logger.debug(f"Generating public key for configuration {self.Name}, PrivateKey length: {len(self.PrivateKey) if self.PrivateKey else 0}")
        success, public_key = GenerateWireguardPublicKey(self.PrivateKey)
        if success and public_key:
            logger.debug(f"Successfully generated public key for {self.Name}: {public_key[:10]}...")
            return public_key
        else:
            logger.error(f"Failed to generate public key for configuration {self.Name}. Success: {success}, PublicKey: {public_key}")
            return ""

    def getStatus(self) -> bool:
        self.Status = self.Name in psutil.net_if_addrs().keys()
        return self.Status

    def getAutostartStatus(self):
        s, d = DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        return self.Name in d

    async def __getRestrictedPeers(self):
        """Load restricted peers from the database"""
        self.RestrictedPeers = []
        restricted = await self.db.get_restricted_peers()
        if restricted is not None:
            for i in restricted:
                self.RestrictedPeers.append(Peer(i, self))

    def configurationFileChanged(self):
        mt = os.path.getmtime(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'))
        changed = self.__configFileModifiedTime is None or self.__configFileModifiedTime != mt
        self.__configFileModifiedTime = mt
        return changed

    async def __getPeers(self):
        """Load peers from the database/config"""
        if self.configurationFileChanged():
            self.Peers = []
            
            with open(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'),
                      'r') as configFile:
                p = []
                pCounter = -1
                content = configFile.read().split('\n')
                try:
                    peerStarts = content.index("[Peer]")
                    content = content[peerStarts:]
                    for i in content:
                        # Handle #Name# comments first, before skipping other comments
                        if RegexMatch("#Name# = (.*)", i):
                            split = re.split(r'\s*=\s*', i, maxsplit=1)
                            if len(split) == 2:
                                # Only set name if we have a valid peer object
                                if pCounter >= 0 and pCounter < len(p):
                                    p[pCounter]["name"] = split[1]
                                    logger.debug(f"Found name comment: {split[1]} for peer {pCounter}")
                                else:
                                    logger.warning(f"Found name comment but no valid peer object exists: {split[1]}")
                        elif not RegexMatch("#(.*)", i) and not RegexMatch(";(.*)", i):
                            if i == "[Peer]":
                                pCounter += 1
                                p.append({})
                                p[pCounter]["name"] = ""
                            else:
                                if len(i) > 0:
                                    split = re.split(r'\s*=\s*', i, maxsplit=1)
                                    if len(split) == 2:
                                        p[pCounter][split[0]] = split[1]

                    for i in p:
                        if "PublicKey" in i.keys():
                            checkIfExist = await self.db.search_peer(i['PublicKey'])
                            if checkIfExist is None:
                                allowed_ips = i.get("AllowedIPs", "N/A").split(',')
                                addr_v4 = []
                                addr_v6 = []
                                for addr in allowed_ips:
                                    addr = addr.strip()
                                    if ':' in addr:  # IPv6
                                        addr_v6.append(addr)
                                    else:  # IPv4
                                        addr_v4.append(addr)

                                newPeer = {
                                    "id": i['PublicKey'],
                                    "private_key": "",
                                    "DNS": DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1],
                                    "endpoint_allowed_ip": DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1],
                                    "name": i.get("name"),
                                    "total_receive": 0,
                                    "total_sent": 0,
                                    "total_data": 0,
                                    "endpoint": "N/A",
                                    "status": "stopped",
                                    "latest_handshake": "N/A",
                                    "allowed_ip": i.get("AllowedIPs", "N/A"),
                                    "cumu_receive": 0,
                                    "cumu_sent": 0,
                                    "cumu_data": 0,
                                    "traffic": [],
                                    "mtu": int(DashboardConfig.GetConfig("Peers", "peer_mtu")[1]),
                                    "keepalive": int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1]),
                                    "remote_endpoint": DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                                    "preshared_key": i["PresharedKey"] if "PresharedKey" in i.keys() else "",
                                    "address_v4": ','.join(addr_v4) if addr_v4 else None,
                                    "address_v6": ','.join(addr_v6) if addr_v6 else None,
                                    "upload_rate_limit": 0,
                                    "download_rate_limit": 0,
                                    "scheduler_type": "htb"
                                }
                                logger.debug(f"Inserting peer with name '{newPeer['name']}' and IP '{newPeer['allowed_ip']}'")
                                await self.db.insert_peer(newPeer)
                                self.Peers.append(Peer(newPeer, self))
                            else:
                                # Update both allowed_ip and name if they exist in the config file
                                update_data = {"allowed_ip": i.get("AllowedIPs", "N/A")}
                                if i.get("name"):
                                    update_data["name"] = i.get("name")
                                    logger.debug(f"Updating peer {i['PublicKey'][:8]}... with name '{i.get('name')}'")
                                await self.db.update_peer(i['PublicKey'], update_data)
                                self.Peers.append(Peer(checkIfExist, self))
                except Exception as e:
                    if __name__ == '__main__':
                        logger.error(f"{self.Name} Error: {str(e)}")
        else:
            self.Peers.clear()
            checkIfExist = await self.db.get_peers()
            if checkIfExist is not None:
                for i in checkIfExist:
                    self.Peers.append(Peer(i, self))

    async def addPeersAsync(self, peers: list):
        """Async version of addPeers with bulk database operations for better performance"""
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()
        try:
            # Validate peer names for uniqueness within this configuration
            existing_peer_names = {peer.name for peer in self.Peers}
            for peer in peers:
                if peer.get('name') and peer['name'] in existing_peer_names:
                    raise ValueError(f"A peer with the name '{peer['name']}' already exists in this configuration")
                existing_peer_names.add(peer.get('name', ''))
            
            # Prepare all peer data for bulk database insertion
            peers_data = []
            for i in peers:
                # Split addresses into v4 and v6
                addr_v4 = []
                addr_v6 = []
                if 'allowed_ip' in i:
                    for addr in i['allowed_ip'].split(','):
                        addr = addr.strip()
                        if ':' in addr:  # IPv6
                            addr_v6.append(addr)
                        else:  # IPv4
                            addr_v4.append(addr)

                newPeer = {
                    "id": i['id'],
                    "private_key": i['private_key'],
                    "DNS": i['DNS'],
                    "endpoint_allowed_ip": i['endpoint_allowed_ip'],
                    "name": i['name'],
                    "total_receive": 0,
                    "total_sent": 0,
                    "total_data": 0,
                    "endpoint": "N/A",
                    "status": "stopped",
                    "latest_handshake": "N/A",
                    "allowed_ip": i.get("allowed_ip", "N/A"),
                    "cumu_receive": 0,
                    "cumu_sent": 0,
                    "cumu_data": 0,
                    "traffic": [],
                    "mtu": i['mtu'],
                    "keepalive": i['keepalive'],
                    "remote_endpoint": DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                    "preshared_key": i["preshared_key"],
                    "address_v4": ','.join(addr_v4) if addr_v4 else None,
                    "address_v6": ','.join(addr_v6) if addr_v6 else None,
                    "upload_rate_limit": 0,
                    "download_rate_limit": 0,
                    "scheduler_type": "htb"  # Add default scheduler type
                }
                peers_data.append(newPeer)

            # Bulk insert all peers into database
            if hasattr(self.db, 'bulk_insert_peers'):
                await self.db.bulk_insert_peers(peers_data)
            else:
                # Fallback to individual inserts
                for peer_data in peers_data:
                    await self.db.insert_peer(peer_data)

            # Handle wg commands and config file updates (these still need to be sequential)
            config_path = f"/etc/wireguard/{self.Name}.conf"
            for i, p in enumerate(peers):
                logger.debug(f"Adding peer {i+1}/{len(peers)}: {p['id'][:8]}...")
                presharedKeyExist = len(p['preshared_key']) > 0
                # Use cryptographically secure random for UUID generation
                uid = str(uuid.uuid4())

                # Handle wg command securely
                if presharedKeyExist:
                    with open(uid, "w+") as f:
                        f.write(p['preshared_key'])
                
                try:
                    # Use secure command execution
                    if cmd_prefix == "awg":
                        result = execute_awg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=p['id'],
                            allowed_ips=p['allowed_ip'].replace(' ', ''),
                            preshared_key=p['preshared_key'] if presharedKeyExist else None
                        )
                    else:
                        result = execute_wg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=p['id'],
                            allowed_ips=p['allowed_ip'].replace(' ', ''),
                            preshared_key=p['preshared_key'] if presharedKeyExist else None
                        )
                    
                    logger.debug(f"Peer {i+1} result: success={result['success']}, error={result.get('error', 'None')}")
                    if not result['success']:
                        raise Exception(f"Failed to set peer {i+1}: {result.get('error', result.get('stderr', 'Unknown error'))}")
                finally:
                    # Always clean up the temporary file
                    if presharedKeyExist and os.path.exists(uid):
                        try:
                            os.remove(uid)
                        except OSError as e:
                            logger.warning(f"Failed to remove temporary file {uid}: {e}")
                        except Exception as e:
                            logger.warning(f"Unexpected error removing temporary file {uid}: {e}")

                # Add name comment to config file
                if 'name_comment' in p and p['name_comment']:
                    with open(config_path, 'r') as f:
                        config_lines = f.readlines()

                    # Find the [Peer] section for this peer
                    peer_index = -1
                    for idx, line in enumerate(config_lines):
                        if line.strip() == '[Peer]':
                            next_lines = config_lines[idx:idx + 5]  # Look at next few lines
                            for next_line in next_lines:
                                if f"PublicKey = {p['id']}" in next_line:
                                    peer_index = idx
                                    break

                    # Insert name comment if we found the peer section
                    if peer_index != -1:
                        config_lines.insert(peer_index + 1, p['name_comment'] + '\n')
                        with open(config_path, 'w') as f:
                            f.writelines(config_lines)

            # Save and patch
            if cmd_prefix == "awg":
                result = execute_awg_quick_command('save', self.Name)
            else:
                result = execute_wg_quick_command('save', self.Name)
            if not result['success']:
                raise Exception(f"Failed to save configuration: {result.get('error', result.get('stderr', 'Unknown error'))}")
            try_patch = self.patch_iface_address(interface_address)
            if try_patch:
                return try_patch

            await self.getPeersList()
            return True
        except Exception as e:
            logger.error(f"Error in addPeersAsync: {str(e)}")
            return False

    def searchPeer(self, publicKey):
        # Check main peers first
        for i in self.Peers:
            if i.id == publicKey:
                return True, i
        
        # Check restricted peers if not found in main
        for i in self.RestrictedPeers:
            if i.id == publicKey:
                return True, i
                
        return False, None

    async def allowAccessPeersAsync(self, listOfPublicKeys):
        """Async version of allowAccessPeers with bulk database operations for better performance"""
        try:
            if not self.getStatus():
                self.toggleConfiguration()
            interface_address = self.get_iface_address()
            cmd_prefix = self.get_iface_proto()
            
            # Use bulk operation to move peers from restricted table
            if hasattr(self.db, 'bulk_move_peers_from_restricted'):
                await self.db.bulk_move_peers_from_restricted(listOfPublicKeys)
            else:
                # Fallback to individual moves
                for i in listOfPublicKeys:
                    if not await self.db.move_peer_from_restricted(i):
                        return ResponseObject(False, f"Failed to move peer {i} from restricted table")
            
            # Get all peer data for wg commands
            restricted_peers = await self.db.get_restricted_peers()
            peers_to_process = []
            if restricted_peers is not None:
                for peer in restricted_peers:
                    if peer.get('id') in listOfPublicKeys:
                        peers_to_process.append(peer)
            
            # Process wg commands for each peer
            for p in peers_to_process:
                presharedKeyExist = len(p.get('preshared_key', '')) > 0
                uid = None
                
                try:
                    if presharedKeyExist:
                        # Use cryptographically secure random for UUID generation
                        uid = str(uuid.uuid4())
                        with open(uid, "w+") as f:
                            f.write(p['preshared_key'])

                    # Use secure command execution with protocol check
                    if cmd_prefix == "awg":
                        result = execute_awg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=p['id'],
                            allowed_ips=p['allowed_ip'].replace(' ', ''),
                            preshared_key=p['preshared_key'] if presharedKeyExist else None
                        )
                    else:
                        result = execute_wg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=p['id'],
                            allowed_ips=p['allowed_ip'].replace(' ', ''),
                            preshared_key=p['preshared_key'] if presharedKeyExist else None
                        )
                    
                    if not result['success']:
                        logger.error(f"Failed to set peer {p['id']}: {result.get('error', result.get('stderr', 'Unknown error'))}")
                        return ResponseObject(False, f"Failed to set peer {p['id']}: {result.get('error', result.get('stderr', 'Unknown error'))}")
                        
                finally:
                    # Always clean up the temporary file
                    if presharedKeyExist and uid and os.path.exists(uid):
                        try:
                            os.remove(uid)
                        except:
                            pass

            # Save and patch
            if cmd_prefix == "awg":
                result = execute_awg_quick_command('save', self.Name)
            else:
                result = execute_wg_quick_command('save', self.Name)
            if not result['success']:
                return ResponseObject(False, f"Failed to save configuration: {result.get('error', result.get('stderr', 'Unknown error'))}")
            
            try_patch = self.patch_iface_address(interface_address)
            if try_patch:
                return try_patch

            await self.__getPeers()
            return ResponseObject(True, "All peers have been allowed access successfully")
        except Exception as e:
            logger.error(f"Error in allowAccessPeersAsync: {str(e)}")
            return ResponseObject(False, f"Error allowing access to peers: {str(e)}")

    async def restrictPeersAsync(self, listOfPublicKeys):
        """Async version of restrictPeers"""
        numOfRestrictedPeers = 0
        numOfFailedToRestrictPeers = 0
        if not self.getStatus():
            self.toggleConfiguration()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()
        for p in listOfPublicKeys:
            found, pf = self.searchPeer(p)
            if found:
                try:
                    if cmd_prefix == "awg":
                        result = execute_awg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=pf.id,
                            remove=True
                        )
                    else:
                        result = execute_wg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=pf.id,
                            remove=True
                        )
                    if not result['success']:
                        raise Exception(f"Failed to remove peer: {result.get('error', result.get('stderr', 'Unknown error'))}")

                    await self.db.move_peer_to_restricted(pf.id)
                    # Update status to stopped
                    await self.db.update_peer(pf.id, {"status": "stopped"})
                    numOfRestrictedPeers += 1
                except Exception as e:
                    numOfFailedToRestrictPeers += 1

        if not self.__wgSave():
            return ResponseObject(False, "Failed to save configuration through WireGuard")

        try_patch = self.patch_iface_address(interface_address)
        if try_patch:
            return try_patch

        await self.__getPeers()

        if numOfRestrictedPeers == len(listOfPublicKeys):
            return ResponseObject(True, f"Restricted {numOfRestrictedPeers} peer(s)")
        return ResponseObject(False,
                              f"Restricted {numOfRestrictedPeers} peer(s) successfully. Failed to restrict {numOfFailedToRestrictPeers} peer(s)")

    async def deletePeersAsync(self, listOfPublicKeys):
        """Async version of deletePeers"""
        # Reload peers list first to ensure we have the latest state
        # (important after restrict/allow operations that move peers between tables)
        await self.__getPeers()
        await self.getRestrictedPeersList()
        
        numOfDeletedPeers = 0
        numOfFailedToDeletePeers = 0
        if not self.getStatus():
            self.toggleConfiguration()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()
        for p in listOfPublicKeys:
            found, pf = self.searchPeer(p)
            if found:
                try:
                    # Build cmd string based off of interface protocol
                    if cmd_prefix == "awg":
                        result = execute_awg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=pf.id,
                            remove=True
                        )
                    else:
                        result = execute_wg_command(
                            action='set',
                            interface=self.Name,
                            peer_key=pf.id,
                            remove=True
                        )
                    if not result['success']:
                        raise Exception(f"Failed to remove peer: {result.get('error', result.get('stderr', 'Unknown error'))}")

                    await self.db.delete_peer(pf.id)
                    numOfDeletedPeers += 1
                except Exception as e:
                    numOfFailedToDeletePeers += 1

        if not self.__wgSave():
            return ResponseObject(False, "Failed to save configuration through WireGuard")

        try_patch = self.patch_iface_address(interface_address)
        if try_patch:
            return try_patch

        await self.__getPeers()

        if numOfDeletedPeers == len(listOfPublicKeys):
            return ResponseObject(True, f"Deleted {numOfDeletedPeers} peer(s)")
        return ResponseObject(False,
                              f"Deleted {numOfDeletedPeers} peer(s) successfully. Failed to delete {numOfFailedToDeletePeers} peer(s)")

    def get_iface_proto(self):
        try:
            # Get the path to the WireGuard configuration file
            config_path = os.path.join(
                DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                f"{self.Name}.conf"
            )

            with open(config_path, "r") as conf_file:
                lines = conf_file.readlines()

            # Parse the [Interface] section
            interface_section = False
            awg_params = {"Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"}
            found_awg_params = set()

            for line in lines:
                line = line.strip()

                if line.startswith("[Interface]"):
                    interface_section = True
                    continue

                # Stop parsing if another section starts
                if interface_section and line.startswith("["):
                    break

                if interface_section:
                    # Split the line to extract the key and value
                    if "=" in line:
                        key, _ = line.split("=", 1)
                        key = key.strip()
                        # Check if the key is in AmneziaWG parameters
                        if key in awg_params:
                            found_awg_params.add(key)

            # Determine if the file contains awg parameters
            if found_awg_params:
                return "awg"
            else:
                return "wg"

        except Exception as e:
            logger.error(f"Error while parsing interface config: {e}")
            return None

    def get_iface_address(self):
        try:
            # Fetch both inet (IPv4) and inet6 (IPv6) addresses
            ip_result = execute_ip_command('addr_show', self.Name)
            if not ip_result['success']:
                return None, None
            
            # Parse IPv4 addresses from output
            ipv4_address = ""
            ipv6_addresses = []
            for line in ip_result['stdout'].splitlines():
                if 'inet ' in line and not 'inet6' in line:
                    # Extract IP address from line like "inet 192.168.1.1/24 dev wg0"
                    parts = line.split()
                    if len(parts) >= 2:
                        ipv4_address = parts[1]
                elif 'inet6 ' in line:
                    # Extract IPv6 address from line like "inet6 2001:db8::1/64 dev wg0"
                    parts = line.split()
                    if len(parts) >= 2:
                        ipv6_addresses.append(parts[1])

            # Filter out potential duplicates and retain unique IPv6 addresses
            unique_ipv6_addresses = set(ipv6_addresses)
            ipv6_address = ", ".join(unique_ipv6_addresses)

            # Combine into the required format if addresses are available
            address = ipv4_address if ipv4_address else ""
            if ipv6_address:
                if address:
                    address += ", "  # Add a separator if both addresses are present
                address += ipv6_address

            return address if address else None  # Return combined address or None if no address found

        except subprocess.CalledProcessError:
            return None  # Handle errors if the command fails

    def patch_iface_address(self, interface_address):
        try:
            # Fix link-local IPv6 addresses before writing to config
            fixed_address = self._fix_link_local_ipv6(interface_address)
            
            config_path = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f"{self.Name}.conf")
            with open(config_path, "r") as conf_file:
                lines = conf_file.readlines()

            # Locate the [Interface] section and the Address line
            interface_index = next((i for i, line in enumerate(lines) if line.strip() == "[Interface]"), None)
            address_line_index = next((i for i, line in enumerate(lines) if line.strip().startswith("Address")), None)

            # Create the new Address line with fixed addresses
            address_line = f"Address = {fixed_address}\n"

            # Check if the Address line exists, update it or insert after the [Interface] section
            if address_line_index is not None:
                lines[address_line_index] = address_line
            elif interface_index is not None:
                lines.insert(interface_index + 1, address_line)

            # Remove any additional Address lines (IPv4 or IPv6) to prevent duplicates
            lines = [line for i, line in enumerate(lines)
                     if not (line.strip().startswith("Address") and i != address_line_index)]

            # Write back the modified configuration to the file
            with open(config_path, "w") as conf_file:
                conf_file.writelines(lines)
            
            # If we fixed link-local addresses, also fix the live interface
            if fixed_address != interface_address and self.getStatus():
                logger.debug(f" Link-local detected, fixing live interface {self.Name}")
                self._apply_ipv6_fix_to_live_interface(fixed_address)

        except IOError:
            return ResponseObject(False, "Failed to write the interface address to the config file")

    def _fix_link_local_ipv6(self, interface_address):
        """Replace link-local IPv6 addresses with ULA addresses"""
        import ipaddress
        
        addresses = [addr.strip() for addr in interface_address.split(',')]
        fixed_addresses = []
        
        for addr in addresses:
            try:
                ip_net = ipaddress.ip_network(addr, strict=False)
                
                # If it's a link-local IPv6 (fe80::/10), replace with ULA
                if ip_net.version == 6 and str(ip_net.network_address).startswith('fe80:'):
                    # Generate consistent ULA based on config name
                    config_hash = abs(hash(self.Name)) % 65536  # Get a consistent hash
                    ula_addr = f"fd42:{config_hash:04x}:42::1/{ip_net.prefixlen}"
                    logger.debug(f" Replacing link-local {addr} with ULA {ula_addr}")
                    fixed_addresses.append(ula_addr)
                else:
                    fixed_addresses.append(addr)
            except Exception as e:
                # Keep non-IP addresses as-is
                logger.debug(f" Keeping address as-is: {addr} (error: {e})")
                fixed_addresses.append(addr)
        
        result = ', '.join(fixed_addresses)
        if result != interface_address:
            logger.debug(f" Fixed interface address: {interface_address} -> {result}")
        
        return result

    def _apply_ipv6_fix_to_live_interface(self, fixed_address):
        """Apply IPv6 fixes directly to the live interface"""
        try:
            import subprocess
            
            # Extract IPv6 addresses from the fixed address string
            ipv4_addr = None
            ipv6_addr = None
            
            for addr in fixed_address.split(','):
                addr = addr.strip()
                if ':' in addr and not addr.startswith('fe80:'):
                    ipv6_addr = addr
                elif '.' in addr:
                    ipv4_addr = addr
            
            if ipv6_addr:
                logger.debug(f" Applying IPv6 fix to live interface {self.Name}")
                
                # Remove all existing IPv6 addresses (including link-local)
                result = execute_ip_command('addr_flush', self.Name)
                if result['success']:
                    logger.debug(f" Flushed IPv6 addresses from {self.Name}")
                else:
                    logger.warning(f"Failed to flush IPv6: {result['stderr']}")
                
                # Add the proper ULA IPv6 address
                result = execute_ip_command('addr_add', self.Name, address=ipv6_addr)
                if result['success']:
                    logger.debug(f" Added ULA address {ipv6_addr} to {self.Name}")
                else:
                    logger.error(f"Failed to add ULA address: {result.stderr}")
                
                # Ensure IPv4 address is still present (in case it was affected)
                if ipv4_addr:
                    # Check if IPv4 is still there
                    check_result = execute_ip_command('addr_show', self.Name)
                    if check_result['success']:
                        # Check if IPv4 address is in the output
                        ipv4_found = False
                        for line in check_result['stdout'].splitlines():
                            if f"inet {ipv4_addr.split('/')[0]}" in line:
                                ipv4_found = True
                                break
                        
                        if not ipv4_found:
                            # Re-add IPv4 if missing
                            result = execute_ip_command('addr_add', self.Name, address=ipv4_addr)
                            if result['success']:
                                logger.debug(f" Re-added IPv4 address {ipv4_addr} to {self.Name}")
                
        except Exception as e:
            logger.error(f"Failed to fix live interface IPv6: {e}")

    def __wgSave(self) -> tuple[bool, str] | tuple[bool, None]:
        cmd_prefix = self.get_iface_proto()
        try:
            # Build cmd string based off of interface protocol
            if cmd_prefix == "awg":
                result = execute_awg_quick_command('save', self.Name)
            else:
                result = execute_wg_quick_command('save', self.Name)
            if not result['success']:
                return False, result.get('error', result.get('stderr', 'Unknown error'))

            return True, None
        except subprocess.CalledProcessError as e:
            return False, str(e)

    async def getPeersLatestHandshakeAsync(self):
        """Async version of getPeersLatestHandshake"""
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            if cmd_prefix == "awg":
                result = execute_awg_command('show', self.Name, subcommand='latest-handshakes')
            else:
                result = execute_wg_command('show', self.Name, subcommand='latest-handshakes')
            if not result['success']:
                return "stopped"
            latestHandshake = result['stdout'].split()

        except Exception:
            return "stopped"
        count = 0
        now = datetime.now()
        time_delta = timedelta(minutes=2)
        for _ in range(int(len(latestHandshake) / 2)):
            minus = now - datetime.fromtimestamp(int(latestHandshake[count + 1]))
            if minus < time_delta:
                status = "running"
            else:
                status = "stopped"
            if int(latestHandshake[count + 1]) > 0:
                await self.db.update_peer_handshake(latestHandshake[count], str(minus).split(".", maxsplit=1)[0], status)
            else:
                await self.db.update_peer_handshake(latestHandshake[count], 'No Handshake', status)
            count += 2

    async def getPeersTransferAsync(self):
        """Async version of getPeersTransfer"""
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            if cmd_prefix == "awg":
                result = execute_awg_command('show', self.Name, subcommand='transfer')
            else:
                result = execute_wg_command('show', self.Name, subcommand='transfer')
            if not result['success']:
                return
            data_usage = result['stdout'].split("\n")
            data_usage = [p.split("\t") for p in data_usage]
            for i in range(len(data_usage)):
                if len(data_usage[i]) == 3:
                    cur_i = await self.db.search_peer(data_usage[i][0])
                    if cur_i is not None:
                        # Get correctly parsed values from WireGuard (now parsing is fixed)
                        cur_total_sent = float(data_usage[i][1]) / (1024 ** 3)
                        cur_total_receive = float(data_usage[i][2]) / (1024 ** 3)
                        
                        # Get old values from database (may be swapped from previous parsing bug)
                        old_total_sent = cur_i['total_sent']
                        old_total_receive = cur_i['total_receive']
                        old_cumu_sent = cur_i['cumu_sent']
                        old_cumu_receive = cur_i['cumu_receive']
                        
                        # Detect if old values are likely swapped by comparing with current WireGuard values
                        # If old total_sent matches current total_receive better than current total_sent, they're swapped
                        sent_matches_current = abs(old_total_sent - cur_total_sent) < abs(old_total_sent - cur_total_receive)
                        recv_matches_current = abs(old_total_receive - cur_total_receive) < abs(old_total_receive - cur_total_sent)
                        
                        # If both don't match their current counterparts, likely swapped
                        if not sent_matches_current and not recv_matches_current:
                            # Old values were swapped - correct them
                            corrected_total_sent = old_total_receive
                            corrected_total_receive = old_total_sent
                            corrected_cumu_sent = old_cumu_receive
                            corrected_cumu_receive = old_cumu_sent
                        else:
                            # Old values appear correct
                            corrected_total_sent = old_total_sent
                            corrected_total_receive = old_total_receive
                            corrected_cumu_sent = old_cumu_sent
                            corrected_cumu_receive = old_cumu_receive
                        
                        # Calculate new totals and cumulative values with corrected old values
                        if corrected_total_sent <= cur_total_sent and corrected_total_receive <= cur_total_receive:
                            # Normal increment - add difference to cumulative
                            total_sent = cur_total_sent
                            total_receive = cur_total_receive
                            cumulative_sent = corrected_cumu_sent + (cur_total_sent - corrected_total_sent)
                            cumulative_receive = corrected_cumu_receive + (cur_total_receive - corrected_total_receive)
                        else:
                            # Counter reset (WireGuard restarted) - add old total to cumulative
                            cumulative_sent = corrected_cumu_sent + corrected_total_sent
                            cumulative_receive = corrected_cumu_receive + corrected_total_receive
                            await self.db.update_peer(data_usage[i][0], {
                                'cumu_receive': cumulative_receive,
                                'cumu_sent': cumulative_sent,
                                'cumu_data': cumulative_sent + cumulative_receive
                            })
                            total_sent = 0
                            total_receive = 0
                        
                        # Update database with correct values (will overwrite any swapped values)
                        found, p = self.searchPeer(data_usage[i][0])
                        if found and p and hasattr(p, 'total_receive') and hasattr(p, 'total_sent') and (p.total_receive != total_receive or p.total_sent != total_sent):
                            await self.db.update_peer_transfer(data_usage[i][0], total_receive, total_sent, total_receive + total_sent)
        except Exception as e:
            logger.error(f"{self.Name} Error: {str(e)} {str(e.__traceback__)}")

    async def getPeersEndpointAsync(self):
        """Async version of getPeersEndpoint"""
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            if cmd_prefix == "awg":
                result = execute_awg_command('show', self.Name, subcommand='endpoints')
            else:
                result = execute_wg_command('show', self.Name, subcommand='endpoints')
            if not result['success']:
                return "stopped"
            data_usage = result['stdout'].split()

        except Exception:
            return "stopped"
        count = 0
        for _ in range(int(len(data_usage) / 2)):
            await self.db.update_peer_endpoint(data_usage[count], data_usage[count + 1])
            count += 2

    def toggleConfiguration(self) -> tuple[bool, str]:
        self.getStatus()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()

        config_file_path = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f"{self.Name}.conf")

        # Initialize connection_start_time for CPS adaptation tracking (only for AWG with CPS enabled)
        connection_start_time = None

        if self.Status:
            try:
                if cmd_prefix == "awg":
                    result = execute_awg_quick_command('down', self.Name)
                else:
                    result = execute_wg_quick_command('down', self.Name)
                if not result['success']:
                    return False, result.get('error', result.get('stderr', 'Unknown error'))
            except Exception as exc:
                return False, str(exc)

            # Write the interface address after bringing it down
            try_patch = self.patch_iface_address(interface_address)
            if try_patch:
                return try_patch
        else:
            # Check if config file exists before trying to bring interface up
            if not os.path.exists(config_file_path):
                return False, f"Configuration file does not exist: {config_file_path}"
            
            # Record connection attempt for CPS adaptation (only for AWG with CPS enabled)
            if self.get_iface_proto() == "awg" and (self.I1 or self.I2 or self.I3 or self.I4 or self.I5):
                connection_start_time = time.time()
            try:
                # Extract IPv6 address from the WireGuard configuration file
                with open(config_file_path, 'r') as f:
                    config_data = f.read()

                # Extract the IPv6 address from the Address line
                ipv6_address = None
                for line in config_data.splitlines():
                    if line.strip().startswith("Address"):
                        parts = line.split("=")[1].strip().split(", ")
                        for part in parts:
                            if ":" in part:  # Check if the part looks like an IPv6 address
                                ipv6_address = part.strip()
                                break
                        if ipv6_address:
                            break

                # Modify the logic to continue without IPv6 if not found
                if ipv6_address:
                    # Bring the interface up
                    if cmd_prefix == "awg":
                        result = execute_awg_quick_command('up', self.Name)
                    else:
                        result = execute_wg_quick_command('up', self.Name)
                    if not result['success']:
                        return False, result.get('error', result.get('stderr', 'Unknown error'))

                    try:
                        # Remove any existing IPv6 addresses for the interface
                        result = execute_ip_command('addr_flush', self.Name)
                        if not result['success']:
                            return False, result.get('error', result.get('stderr', 'Unknown error'))

                        # Add the new IPv6 address with the desired parameters
                        result = execute_ip_command('addr_add', self.Name, address=ipv6_address)
                        if not result['success']:
                            return False, result.get('error', result.get('stderr', 'Unknown error'))
                    except subprocess.CalledProcessError as exc:
                        return False, str(exc.output.strip().decode("utf-8"))
                else:
                    # No IPv6 address found, just bring the interface up without modifying IPv6
                    if cmd_prefix == "awg":
                        result = execute_awg_quick_command('up', self.Name)
                    else:
                        result = execute_wg_quick_command('up', self.Name)
                    if not result['success']:
                        return False, result.get('error', result.get('stderr', 'Unknown error'))
            except subprocess.CalledProcessError as exc:
                # Record failed connection attempt for CPS adaptation (safely access method)
                if connection_start_time:
                    record_method = getattr(type(self), '_record_cps_connection_attempt', None)
                    if record_method:
                        try:
                            record_method(self, success=False)
                        except Exception:
                            pass
                return False, str(exc.output.strip().decode("utf-8"))
        
        # Record successful connection attempt for CPS adaptation
        if connection_start_time:
            latency_ms = (time.time() - connection_start_time) * 1000
            # Get throughput from traffic monitor if available (safely access method)
            throughput_method = getattr(type(self), '_get_current_throughput', None)
            if throughput_method:
                try:
                    throughput_mbps = throughput_method(self)
                except Exception:
                    throughput_mbps = 0.0
            else:
                throughput_mbps = 0.0
            # Record successful connection attempt (safely access method)
            record_method = getattr(type(self), '_record_cps_connection_attempt', None)
            if record_method:
                try:
                    record_method(self, success=True, latency_ms=latency_ms, throughput_mbps=throughput_mbps)
                except Exception:
                    pass
            
            # Real-time adaptation check (safely access methods)
            init_method = getattr(type(self), '_ensure_cps_adaptation_initialized', None)
            adapted_patterns = None
            if init_method:
                try:
                    init_method(self)
                    if hasattr(self, 'cps_adaptation') and self.cps_adaptation:
                        adapt_method = getattr(self.cps_adaptation, 'adapt_pattern_real_time', None)
                        if adapt_method:
                            adapted_patterns = adapt_method(
                                self.I1, self.I2, self.I3, self.I4, self.I5
                            )
                except Exception:
                    pass
            
            # Apply adapted patterns if they differ
            if adapted_patterns and (adapted_patterns.get('i1') != self.I1 or 
                                     adapted_patterns.get('i2') != self.I2 or
                                     adapted_patterns.get('i3') != self.I3 or
                                     adapted_patterns.get('i4') != self.I4 or
                                     adapted_patterns.get('i5') != self.I5):
                apply_method = getattr(type(self), '_apply_cps_patterns', None)
                if apply_method:
                    try:
                        logger.info(f"Adapting CPS patterns for {self.Name} based on performance")
                        apply_method(self, adapted_patterns)
                    except Exception:
                        pass
        
        self.__parseConfigurationFileSync()
        self.getStatus()
        return True, None

    async def getPeersList(self):
        await self.__getPeers()
        return self.Peers

    async def getRestrictedPeersList(self) -> list:
        """Return restricted peers list"""
        await self.__getRestrictedPeers()
        return self.RestrictedPeers

    def toJson(self):
        self.Status = self.getStatus()
        # Force refresh public key if it's empty but we have a private key
        if not self.PublicKey and self.PrivateKey:
            logger.debug(f"Refreshing empty public key for configuration {self.Name}")
            self.PublicKey = self.__getPublicKey()
        
        # Detect Tor configuration in iptables scripts
        has_tor = False
        tor_keywords = ['proxy', 'tor', 'transport', 'dnsport', '9050', '9040']
        iptables_scripts = [self.PreUp, self.PostUp, self.PreDown, self.PostDown]
        
        for script in iptables_scripts:
            if script and any(keyword in script.lower() for keyword in tor_keywords):
                has_tor = True
                break
        
        return {
            "Status": self.Status,
            "Name": self.Name,
            "PrivateKey": self.PrivateKey,
            "PublicKey": self.PublicKey,
            "Address": self.Address,
            "ListenPort": self.ListenPort,
            "PreUp": self.PreUp,
            "PreDown": self.PreDown,
            "PostUp": self.PostUp,
            "PostDown": self.PostDown,
            "SaveConfig": self.SaveConfig,
            "DataUsage": {
                "Total": sum(list(map(lambda x: x.cumu_data + x.total_data, self.Peers))),
                "Sent": sum(list(map(lambda x: x.cumu_sent + x.total_sent, self.Peers))),
                "Receive": sum(list(map(lambda x: x.cumu_receive + x.total_receive, self.Peers)))
            },
            "ConnectedPeers": len(list(filter(lambda x: x.status == "running", self.Peers))),
            "TotalPeers": len(self.Peers),
            "Protocol": self.Protocol,
            "HasTor": has_tor,
            # AmneziaWG parameters
            "Jc": self.Jc,
            "Jmin": self.Jmin,
            "Jmax": self.Jmax,
            "S1": self.S1,
            "S2": self.S2,
            "H1": self.H1,
            "H2": self.H2,
            "H3": self.H3,
            "H4": self.H4,
            # AmneziaWG 1.5 CPS packets
            "I1": self.I1,
            "I2": self.I2,
            "I3": self.I3,
            "I4": self.I4,
            "I5": self.I5,
            # CPS Pattern Adaptation stats (if available) - safely get using getattr from class
            "CPSAdaptation": self._get_cps_stats_via_class(),
        }
    
    def _get_cps_stats_via_class(self) -> dict[str, Any]:
        """Get CPS stats via class lookup - works even if method not bound to instance"""
        try:
            # Try to get the safe method directly from class
            safe_method = getattr(type(self), '_get_cps_adaptation_stats_safe', None)
            if safe_method:
                try:
                    return safe_method(self)
                except Exception:
                    pass
            
            # Fallback: try initialization method from class
            init_method = getattr(type(self), '_ensure_cps_adaptation_initialized', None)
            if init_method:
                try:
                    init_method(self)
                    cps_adaptation = getattr(self, 'cps_adaptation', None)
                    if cps_adaptation:
                        stats_method = getattr(cps_adaptation, 'get_adaptation_stats', None)
                        if callable(stats_method):
                            return stats_method()
                except Exception:
                    pass
            
            # Last resort: direct initialization
            try:
                if not hasattr(self, 'cps_adaptation') or not getattr(self, 'cps_adaptation', None):
                    from .AwgCPS.CPSPatternAdaptation import CPSPatternAdaptation
                    if hasattr(self, 'Name') and hasattr(self, 'db'):
                        self.cps_adaptation = CPSPatternAdaptation(self.Name, self.db)
                        if self.cps_adaptation:
                            stats_method = getattr(self.cps_adaptation, 'get_adaptation_stats', None)
                            if callable(stats_method):
                                return stats_method()
            except Exception:
                pass
        except Exception:
            pass
        return {}
    
    def _get_cps_adaptation_stats_for_json_safe(self) -> dict[str, Any]:
        """Get CPS stats for JSON - completely safe, works with existing instances"""
        try:
            # Try to get stats via class method lookup (works even if instance doesn't have it bound)
            safe_method = getattr(type(self), '_get_cps_adaptation_stats_safe', None)
            if safe_method:
                try:
                    return safe_method(self)
                except Exception as e:
                    logger.debug(f"Failed to get CPS stats via safe method: {e}")
                    pass
            
            # Try initialization via class method
            init_method = getattr(type(self), '_ensure_cps_adaptation_initialized', None)
            if init_method:
                try:
                    init_method(self)
                    cps_adaptation = getattr(self, 'cps_adaptation', None)
                    if cps_adaptation:
                        stats_method = getattr(cps_adaptation, 'get_adaptation_stats', None)
                        if callable(stats_method):
                            return stats_method()
                except Exception as e:
                    logger.debug(f"Failed to initialize CPS adaptation via class method: {e}")
                    pass
            
            # Direct initialization as last resort
            try:
                if not hasattr(self, 'cps_adaptation') or not getattr(self, 'cps_adaptation', None):
                    from .AwgCPS.CPSPatternAdaptation import CPSPatternAdaptation
                    if hasattr(self, 'Name') and hasattr(self, 'db'):
                        self.cps_adaptation = CPSPatternAdaptation(self.Name, self.db)
                        if self.cps_adaptation:
                            stats_method = getattr(self.cps_adaptation, 'get_adaptation_stats', None)
                            if callable(stats_method):
                                return stats_method()
            except Exception as e:
                logger.debug(f"Failed to initialize CPS adaptation directly: {e}")
                pass
            
            return {}
        except Exception:
            return {}

    def backupConfigurationFile(self):
        """Enhanced backup method that includes all iptables scripts with organized directory structure"""
        try:
            # Generate timestamp for backup files
            time_str = datetime.now().strftime("%Y%m%d%H%M%S")

            # Get organized backup paths
            try:
                backup_paths = get_backup_paths(self.Name, time_str)
            except OSError as e:
                error_msg = f"Failed to create backup directory: {str(e)}"
                logger.error(error_msg)
                return False, {"error": error_msg}

            # Backup main configuration file
            try:
                shutil.copy(self.configPath, backup_paths['conf_file'])
            except (OSError, IOError) as e:
                error_msg = f"Failed to copy configuration file to backup: {str(e)}"
                logger.error(error_msg)
                return False, {"error": error_msg}

            # Backup database
            try:
                # __dumpDatabase() returns an async generator, so we need to handle it properly
                # Since this is a sync method, we'll use asyncio to run the async generator
                import asyncio
                
                async def collect_database_lines():
                    """Collect all lines from the async generator"""
                    lines = []
                    async_gen = self.db.dump_database()
                    async for line in async_gen:
                        lines.append(line)
                    return lines
                
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Collect all database lines
                if loop.is_running():
                    # We're in an async context, need to handle differently
                    # Create a task and wait for it
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(collect_database_lines())
                        )
                        lines = future.result()
                else:
                    lines = loop.run_until_complete(collect_database_lines())
                
                # Write all lines to backup file
                with open(backup_paths['redis_file'], 'w+') as f:
                    for l in lines:
                        f.write(l + "\n")
            except (OSError, IOError) as e:
                error_msg = f"Failed to write database backup file: {str(e)}"
                logger.error(error_msg)
                return False, {"error": error_msg}
            except Exception as e:
                error_msg = f"Failed to dump database: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, {"error": error_msg}

            # Backup all iptables scripts if they exist
            scripts_backup = {}
            script_types = {
                'preup': ('preup', self.PreUp),
                'postup': ('postup', self.PostUp),
                'predown': ('predown', self.PreDown),
                'postdown': ('postdown', self.PostDown)
            }

            for script_key, (script_name, script_path) in script_types.items():
                if script_path:
                    # script_path contains the actual file path from PostUp/PreUp/etc attributes
                    logger.debug(f"Processing {script_key}: script_path='{script_path}'")
                    iptables_dir = DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
                    
                    if os.path.isabs(script_path):
                        # Absolute path - use as is
                        script_file = script_path
                    else:
                        # Relative path - try multiple locations
                        # First try the exact path from PostUp attribute
                        if script_path.startswith('./iptable-rules/'):
                            # PostUp contains full path relative to iptables_dir, extract the relative path
                            clean_path = script_path[2:]  # Remove './' prefix
                            # Remove 'iptable-rules/' prefix since iptables_dir already contains it
                            if clean_path.startswith('iptable-rules/'):
                                clean_path = clean_path[14:]  # Remove 'iptable-rules/' (14 characters)
                            script_file = os.path.join(iptables_dir, clean_path)
                        else:
                            # PostUp contains just the script name, construct the path
                            script_file = os.path.join(iptables_dir, script_path.lstrip('./'))
                        
                        # If not found, try the subdirectory structure for new configs
                        if not os.path.exists(script_file):
                            script_file = os.path.join(iptables_dir, self.Name, f"{script_name}.sh")
                        
                        # If still not found, try the old naming convention as fallback
                        if not os.path.exists(script_file):
                            script_file = os.path.join(iptables_dir, f"{self.Name}-{script_name}.sh")
                    
                    logger.debug(f"Final resolved path: {script_file}")
                    logger.debug(f"Checking for script: {script_file}")
                    if os.path.exists(script_file):
                        logger.debug(f"Found script: {script_file}")
                        with open(script_file, 'r') as f:
                            scripts_backup[f"{script_key}_script"] = f.read()
                    else:
                        logger.debug(f"Script not found: {script_file}")

            # Save iptables scripts content if any exist
            if scripts_backup:
                try:
                    with open(backup_paths['iptables_file'], 'w') as f:
                        json.dump(scripts_backup, f, indent=2)
                except (OSError, IOError) as e:
                    error_msg = f"Failed to write iptables backup file: {str(e)}"
                    logger.warning(error_msg)
                    # Don't fail the entire backup if iptables backup fails

            # Return success and backup details
            return True, {
                'filename': os.path.basename(backup_paths['conf_file']),
                'database': backup_paths['redis_file'],
                'iptables': backup_paths['iptables_file'] if scripts_backup else None
            }
        except Exception as e:
            error_msg = f"Unexpected backup error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, {"error": error_msg}

    def getBackups(self, databaseContent: bool = False) -> list[dict[str, str]]:
        """Enhanced getBackups method with organized directory structure"""
        backups = []

        # Get backup paths
        backup_paths = get_backup_paths(self.Name)

        if not os.path.exists(backup_paths['config_dir']):
            return backups

        # Get all files in the config backup directory
        files = [(file, os.path.getctime(os.path.join(backup_paths['config_dir'], file)))
                 for file in os.listdir(backup_paths['config_dir'])
                 if os.path.isfile(os.path.join(backup_paths['config_dir'], file))]

        files.sort(key=lambda x: x[1], reverse=True)

        for f, ct in files:
            if RegexMatch(f"^({self.Name})_(.*)\\.(conf)$", f):
                s = re.search(f"^({self.Name})_(.*)\\.(conf)$", f)
                date = s.group(2)
                d = {
                    "filename": f,
                    "backupDate": date,
                    "content": open(os.path.join(backup_paths['config_dir'], f), 'r').read()
                }

                # Add database info if exists
                redis_file = f.replace(".conf", ".redis")
                if os.path.exists(os.path.join(backup_paths['config_dir'], redis_file)):
                    d['database'] = True
                    if databaseContent:
                        d['databaseContent'] = open(os.path.join(backup_paths['config_dir'], redis_file), 'r').read()

                # Add iptables scripts info if exists
                iptables_file = f.replace(".conf", "_iptables.json")
                if os.path.exists(os.path.join(backup_paths['config_dir'], iptables_file)):
                    d['iptables_scripts'] = True
                    if databaseContent:
                        d['iptablesContent'] = open(os.path.join(backup_paths['config_dir'], iptables_file), 'r').read()

                backups.append(d)

        return backups

    async def restoreBackup(self, backupFileName: str) -> bool:
        """Enhanced restore method with pre/post up/down scripts"""
        backups = list(map(lambda x: x['filename'], self.getBackups()))
        if backupFileName not in backups:
            return False

        # Backup current state before restore
        # Note: backupConfigurationFile() is sync but uses async operations internally
        # It handles the async operations itself, so we can call it directly
        try:
            backup_success, _ = self.backupConfigurationFile()
            if not backup_success:
                logger.warning(f"Failed to create backup before restore, continuing anyway")
        except Exception as e:
            logger.warning(f"Error creating backup before restore: {e}, continuing anyway")
        
        if self.Status:
            self.toggleConfiguration()

        # Get timestamp from backup filename
        # Filename format: {config_name}_{timestamp}.conf
        # Extract timestamp (14 digits before .conf, after the last underscore)
        import re
        timestamp_match = re.search(r'_(\d{14})\.conf$', backupFileName)
        if not timestamp_match:
            logger.error(f"Invalid backup filename format: {backupFileName}")
            return False
        timestamp = timestamp_match.group(1)
        backup_paths = get_backup_paths(self.Name, timestamp)
        if not os.path.exists(backup_paths['conf_file']):
            return False

        # Restore configuration file
        try:
            with open(backup_paths['conf_file'], 'r') as f:
                targetContent = f.read()
            with open(self.configPath, 'w') as f:
                f.write(targetContent)
        except Exception:
            return False

        # Parse and restore database
        self.__parseConfigurationFileSync()
        await self.__dropDatabase()
        await self.__importDatabase(backup_paths['redis_file'])
        
        # Force refresh of peers from database after import
        await self.__initPeersList()

        # Restore iptables scripts if they exist
        if os.path.exists(backup_paths['iptables_file']):
            try:
                with open(backup_paths['iptables_file'], 'r') as f:
                    scripts = json.load(f)

                # Direct mapping of script keys to filenames
                script_files = {
                    'preup_script': 'preup',
                    'postup_script': 'postup',
                    'predown_script': 'predown',
                    'postdown_script': 'postdown'
                }

                # Use configured iptables rules path instead of hardcoded path
                rules_dir = DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
                os.makedirs(rules_dir, exist_ok=True)

                # Process each script
                for script_key, script_type in script_files.items():
                    if script_key in scripts and scripts[script_key]:  # Check if script exists and is not empty
                        # Determine the correct directory structure based on config name
                        if self.Name in ['ADMINS', 'MEMBERS', 'GUESTS', 'LANP2P']:
                            # Use the special directory structure for pregenerated configs
                            if self.Name == 'ADMINS':
                                script_subdir = 'Admins'
                            elif self.Name == 'MEMBERS':
                                script_subdir = 'Members'
                            elif self.Name == 'GUESTS':
                                script_subdir = 'Guest'
                            elif self.Name == 'LANP2P':
                                script_subdir = 'LAN-only-users'
                            
                            script_dir = os.path.join(rules_dir, script_subdir)
                            os.makedirs(script_dir, exist_ok=True)
                            script_path = os.path.join(script_dir, f"{script_type}.sh")
                        else:
                            # Use subdirectory structure for all custom configs
                            script_dir = os.path.join(rules_dir, self.Name)
                            os.makedirs(script_dir, exist_ok=True)
                            script_path = os.path.join(script_dir, f"{script_type}.sh")
                        
                        logger.debug(f"Restoring {script_key} to {script_path}")

                        with open(script_path, 'w') as f:
                            f.write(scripts[script_key])
                        os.chmod(script_path, 0o755)

            except Exception as e:
                logger.warning(f"Failed to restore iptables scripts: {e}")
                # Continue execution even if script restoration fails
                pass
        return True


    def deleteBackup(self, backupFileName: str) -> bool:
        """Enhanced delete method with organized directory structure that handles uploaded backups"""
        backups = list(map(lambda x: x['filename'], self.getBackups()))
        if backupFileName not in backups:
            return False

        try:
            # Get timestamp from backup filename
            timestamp = backupFileName.split('_')[1].split('.')[0]
            backup_paths = get_backup_paths(self.Name, timestamp)

            files_to_delete = [
                # Regular backup files
                backup_paths['conf_file'],
                backup_paths['redis_file'],
                backup_paths['iptables_file'],

                # Handle potential uploaded backup files
                os.path.join(backup_paths['config_dir'], backupFileName),
                os.path.join(backup_paths['config_dir'], backupFileName.replace('.conf', '.redis')),
                os.path.join(backup_paths['config_dir'], backupFileName.replace('.conf', '_iptables.json'))
            ]

            # Delete all existing files
            for file_path in files_to_delete:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted backup file: {file_path}")

            # Clean up empty config directory
            try:
                if os.path.exists(backup_paths['config_dir']):
                    if not os.listdir(backup_paths['config_dir']):
                        os.rmdir(backup_paths['config_dir'])
                        logger.debug(f"Removed empty backup directory: {backup_paths['config_dir']}")
            except OSError as e:
                # Directory not empty or other OS error, log but continue
                logger.debug(f"Note: Could not remove backup directory: {str(e)}")
                pass

        except Exception as e:
            logger.error(f"Error deleting backup files: {str(e)}")
            return False

        return True

    def updateConfigurationSettings(self, newData: dict) -> tuple[bool, str]:
        # Store original status to restore it later
        was_running = self.Status
        if was_running:
            self.toggleConfiguration()
        original = []
        dataChanged = False
        with open(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'), 'r') as f:
            original = f.readlines()
            original = [l.rstrip("\n") for l in original]
            allowEdit = ["Address", "PreUp", "PostUp", "PreDown", "PostDown", "ListenPort", "PrivateKey",
                         "I1", "I2", "I3", "I4", "I5"]

            start = original.index("[Interface]")
            interface_end = len(original)
            
            # Find where the Interface section ends
            for i in range(start + 1, len(original)):
                if original[i] == "[Peer]":
                    interface_end = i
                    break
            
            # Track which fields exist in the config
            existing_fields = set()
            
            # First pass: update existing fields and handle deletions
            lines_to_remove = []
            for line in range(start + 1, interface_end):
                split = re.split(r'\s*=\s*', original[line], 1)
                if len(split) == 2:
                    key = split[0]
                    value = split[1]
                    existing_fields.add(key)
                    if key in allowEdit and key in newData.keys():
                        # If value is empty/None, mark for removal (for I1-I5)
                        if key in ["I1", "I2", "I3", "I4", "I5"] and (not newData[key] or newData[key].strip() == ""):
                            lines_to_remove.append(line)
                            setattr(self, key, "")
                            dataChanged = True
                        elif value != newData[key]:
                            # For I1-I5, scramble the value before writing to interface config
                            if key in ["I1", "I2", "I3", "I4", "I5"]:
                                interface_seed = f"{self.Name}_interface"
                                scrambled_value = self._scramble_cps_pattern(newData[key], interface_seed + f"_{key}")
                                split[1] = scrambled_value
                                original[line] = " = ".join(split)
                                # Store the base (unscrambled) value in the object
                                setattr(self, key, str(newData[key]))
                            else:
                                split[1] = newData[key]
                                original[line] = " = ".join(split)
                                if isinstance(getattr(self, key), bool):
                                    setattr(self, key, strToBool(newData[key]))
                                else:
                                    setattr(self, key, str(newData[key]))
                            dataChanged = True
                    logger.debug(f"Original line: {original[line]}")
            
            # Remove lines marked for deletion (iterate backwards to preserve indices)
            for line_num in sorted(lines_to_remove, reverse=True):
                del original[line_num]
                # Adjust interface_end if we removed lines before it
                if line_num < interface_end:
                    interface_end -= 1
            
            # Second pass: add new I1-I5 fields if they don't exist and are provided
            i_fields = ["I1", "I2", "I3", "I4", "I5"]
            new_lines = []
            for field in i_fields:
                if field in newData and newData[field] and newData[field].strip() and field not in existing_fields:
                    # Scramble I1-I5 values before writing to interface config
                    interface_seed = f"{self.Name}_interface"
                    scrambled_value = self._scramble_cps_pattern(newData[field], interface_seed + f"_{field}")
                    new_lines.append(f"{field} = {scrambled_value}")
                    # Store the base (unscrambled) value in the object
                    setattr(self, field, str(newData[field]))
                    dataChanged = True
            
            # Insert new I fields before [Peer] section if any
            if new_lines:
                # Find the best insertion point (after H4 or last AmneziaWG param if present)
                insert_index = interface_end - 1
                for i in range(interface_end - 1, start, -1):
                    if any(original[i].startswith(f"{p} =") for p in ["H4", "H3", "H2", "H1", "S2", "S1", "Jmax", "Jmin", "Jc"]):
                        insert_index = i + 1
                        break
                
                # Insert the new lines
                for idx, new_line in enumerate(new_lines):
                    original.insert(insert_index + idx, new_line)
        if dataChanged:

            if not os.path.exists(
                    os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')):
                os.mkdir(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup'))
            shutil.copy(
                os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'),
                os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup',
                             f'{self.Name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.conf')
            )
            with open(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'),
                      'w') as f:
                f.write("\n".join(original))

        # Restore the interface to its original state (up if it was running, down if it wasn't)
        # This will apply the new configuration if bringing it up
        if was_running:
            status, msg = self.toggleConfiguration()
            if not status:
                return False, msg
        
        return True, ""

    @classmethod
    async def create_async(cls, name: str, data: dict = None, backup: dict = None, startup: bool = False):
        """Async factory method for Configuration with async file parsing"""
        instance = cls.__new__(cls)
        instance.__parser: configparser.ConfigParser = configparser.ConfigParser(strict=False)
        instance.__parser.optionxform = str
        instance.__configFileModifiedTime = None

        instance.Status: bool = False
        instance.Name: str = ""
        instance.PrivateKey: str = ""
        instance.PublicKey: str = ""
        instance.ListenPort: str = ""
        instance.Address: str = ""
        instance.DNS: str = ""
        instance.Table: str = ""
        instance.Jc: str = ""
        instance.Jmin: str = ""
        instance.Jmax: str = ""
        instance.S1: str = ""
        instance.S2: str = ""
        instance.H1: str = ""
        instance.H2: str = ""
        instance.H3: str = ""
        instance.H4: str = ""
        instance.I1: str = ""
        instance.I2: str = ""
        instance.I3: str = ""
        instance.I4: str = ""
        instance.I5: str = ""
        instance.MTU: str = ""
        instance.PreUp: str = ""
        instance.PostUp: str = ""
        instance.PreDown: str = ""
        instance.PostDown: str = ""
        instance.SaveConfig: bool = True
        instance.Protocol: str = "wg"  # Default to wg, will be set from data or detected
        instance.Name = name
        
        logger.debug(f"[Core] create_async called for configuration: {name}")
        logger.debug(f"[Core] Data received in create_async: {json.dumps({k: v for k, v in (data or {}).items() if k != 'PrivateKey'}, indent=2)}")
        
        # Set Protocol from data if provided, otherwise try to detect from existing config file
        if data and "Protocol" in data:
            logger.debug(f"[Core] Setting Protocol from data: {data['Protocol']}")
            instance.Protocol = data["Protocol"]
        else:
            detected_proto = instance.get_iface_proto()
            logger.debug(f"[Core] Protocol not in data, attempting to detect from existing file: {detected_proto}")
            instance.Protocol = detected_proto or "wg"
        
        logger.debug(f"[Core] Final Protocol value set to: {instance.Protocol}")

        instance.configPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{instance.Name}.conf')

        backupPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')
        if not os.path.exists(backupPath):
            os.mkdir(backupPath)

        # Initialize database manager
        instance.db = ConfigurationDatabase(instance.Name)

        if name is not None:
            if data is not None and "Backup" in data.keys():
                await instance.db.import_database(
                    os.path.join(
                        DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                        'WGDashboard_Backup',
                        data["Backup"].replace(".conf", ".redis")))
            else:
                await instance.db.create_database()
                # Ensure migration happens right after database creation
                await instance.db.migrate_database()

            # Mark as async initialized and use async parsing
            instance._async_initialized = True
            
            # Check if this is a new configuration (data provided but file doesn't exist)
            is_new_config = data is not None and "Backup" not in data.keys() and not os.path.exists(instance.configPath)
            
            if is_new_config:
                # This is a new configuration - skip parsing and go to file creation
                logger.debug(f"[Core] New configuration detected, skipping file parse: {instance.Name}")
                # Initialize empty peer lists for new configs
                if not hasattr(instance, 'Peers') or instance.Peers is None:
                    instance.Peers = []
                if not hasattr(instance, 'RestrictedPeers') or instance.RestrictedPeers is None:
                    instance.RestrictedPeers = []
            else:
                # Existing config or backup restore - parse the file
                if os.path.exists(instance.configPath):
                    await instance.__parseConfigurationFile()
                elif data is not None and "Backup" in data.keys():
                    # Backup restore case - file should exist after restore, parse it
                    await instance.__parseConfigurationFile()
            
            # For existing configs, normalize I1-I5 CPS parameters and load peers
            if not is_new_config:
                # Normalize I1-I5 CPS parameters (convert raw hex 0x... to <b 0x...> format)
                if hasattr(instance, 'I1') and instance.I1:
                    instance.I1 = NormalizeCPSFormat(instance.I1)
                if hasattr(instance, 'I2') and instance.I2:
                    instance.I2 = NormalizeCPSFormat(instance.I2)
                if hasattr(instance, 'I3') and instance.I3:
                    instance.I3 = NormalizeCPSFormat(instance.I3)
                if hasattr(instance, 'I4') and instance.I4:
                    instance.I4 = NormalizeCPSFormat(instance.I4)
                if hasattr(instance, 'I5') and instance.I5:
                    instance.I5 = NormalizeCPSFormat(instance.I5)
                
                await instance.__getPeers()
                # Use async version for restricted peers
                await instance.getRestrictedPeersList()
            
            # Handle autostart if needed
            if startup and instance.getAutostartStatus() and not instance.getStatus():
                instance.toggleConfiguration()
                logger.info(f"Autostart Configuration: {instance.Name}")
            
            logger.info(f"✓ Successfully initialized Configuration: {instance.Name}")
        else:
                # For new configs, initialize empty peer lists (file will be created below)
                if not hasattr(instance, 'Peers') or instance.Peers is None:
                    instance.Peers = []
                if not hasattr(instance, 'RestrictedPeers') or instance.RestrictedPeers is None:
                    instance.RestrictedPeers = []

        # Handle new configuration creation (when name is None or when it's a new config)
        if name is None or (name is not None and data is not None and "Backup" not in data.keys() and not os.path.exists(instance.configPath)):
            instance.Name = data["ConfigurationName"]
            instance.configPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{instance.Name}.conf')
            
            logger.debug(f"[Core] Creating new configuration (not from file): {instance.Name}")
            logger.debug(f"[Core] Protocol before setting attributes: {instance.Protocol}")
            logger.debug(f"[Core] I1-I5 values in data: I1={bool(data.get('I1'))}, I2={bool(data.get('I2'))}, I3={bool(data.get('I3'))}, I4={bool(data.get('I4'))}, I5={bool(data.get('I5'))}")
            logger.debug(f"[Core] PrivateKey in data: present={bool(data.get('PrivateKey'))}, length={len(data.get('PrivateKey', '')) if data.get('PrivateKey') else 0}")

            for i in dir(instance):
                if str(i) in data.keys():
                    old_value = getattr(instance, i, None)
                    if isinstance(getattr(instance, i), bool):
                        setattr(instance, i, StringToBoolean(data[i]))
                    else:
                        setattr(instance, i, str(data[i]))
                    # Log important attribute changes
                    if i in ['Protocol', 'I1', 'I2', 'I3', 'I4', 'I5', 'PrivateKey']:
                        if i == 'PrivateKey':
                            logger.debug(f"[Core] Set {i}: length={len(getattr(instance, i)) if getattr(instance, i) else 0}")
                        else:
                            logger.debug(f"[Core] Set {i}: '{old_value}' -> '{getattr(instance, i)}'")
            
            logger.debug(f"[Core] Protocol after setting attributes: {instance.Protocol}")
            logger.debug(f"[Core] PrivateKey after setting attributes: length={len(instance.PrivateKey) if instance.PrivateKey else 0}")

            instance.__parser["Interface"] = {
                "PrivateKey": instance.PrivateKey,
                "Address": instance.Address,
                "ListenPort": instance.ListenPort,
                "PreUp": instance.PreUp,
                "PreDown": instance.PreDown,
                "PostUp": instance.PostUp,
                "PostDown": instance.PostDown,
            }

            # Only add values if they are not empty or null
            if instance.Jc:
                instance.__parser["Interface"]["Jc"] = instance.Jc
            if instance.Jmin:
                instance.__parser["Interface"]["Jmin"] = instance.Jmin
            if instance.Jmax:
                instance.__parser["Interface"]["Jmax"] = instance.Jmax
            if instance.S1:
                instance.__parser["Interface"]["S1"] = instance.S1
            if instance.S2:
                instance.__parser["Interface"]["S2"] = instance.S2
            if instance.H1:
                instance.__parser["Interface"]["H1"] = instance.H1
            if instance.H2:
                instance.__parser["Interface"]["H2"] = instance.H2
            if instance.H3:
                instance.__parser["Interface"]["H3"] = instance.H3
            if instance.H4:
                instance.__parser["Interface"]["H4"] = instance.H4

            # Add SaveConfig at the end, it seems like it's always True
            instance.__parser["Interface"]["SaveConfig"] = "true"

            # Write the configuration file
            logger.debug(f"[Core] Writing configuration file to: {instance.configPath}")
            logger.debug(f"[Core] Protocol value when writing file: {instance.Protocol}")
            logger.debug(f"[Core] I1-I5 values when writing file: I1={instance.I1[:50] if instance.I1 else 'empty'}..., I2={instance.I2[:50] if instance.I2 else 'empty'}..., I3={instance.I3[:50] if instance.I3 else 'empty'}..., I4={instance.I4[:50] if instance.I4 else 'empty'}..., I5={instance.I5[:50] if instance.I5 else 'empty'}...")
            
            import io
            config_buffer = io.StringIO()
            instance.__parser.write(config_buffer)
            async with aiofiles.open(instance.configPath, "w+") as configFile:
                await configFile.write(config_buffer.getvalue())
            
            logger.debug(f"[Core] Configuration file written successfully: {instance.configPath}")

            instance.Status = instance.getStatus()
            
            # For new configs, log success after file creation
            if is_new_config:
                logger.info(f"✓ Successfully created new Configuration: {instance.Name}")

        return instance

    async def deleteConfiguration(self):
        if self.getStatus():
            self.toggleConfiguration()
        os.remove(self.configPath)
        await self.__dropDatabase()
        return True

    async def renameConfigurationAsync(self, newConfigurationName) -> tuple[bool, str]:
        """Async version of renameConfiguration"""
        if newConfigurationName in Configurations.keys():
            return False, "Configuration name already exist"
        try:
            if self.getStatus():
                self.toggleConfiguration()
            await self.db.create_database(newConfigurationName)
            await self.db.copy_database_to(newConfigurationName)
            # AllPeerJobs.updateJobConfigurationName is async
            await AllPeerJobs.updateJobConfigurationName(self.Name, newConfigurationName)
            shutil.copy(
                self.configPath,
                os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{newConfigurationName}.conf')
            )
            await self.deleteConfiguration()
        except Exception as e:
            return False, str(e)
        return True, None

    async def getAvailableIP(self, all: bool = False) -> tuple[bool, list[str]] | tuple[bool, None]:
        if len(self.Address) < 0:
            return False, None
        
        logger.debug(f" getAvailableIP for {self.Name} (all={all})")
        address = self.Address.split(',')
        logger.debug(f" Interface addresses: {address}")
        
        existedAddress = []
        availableAddress = []
        
        # Collect existing peer addresses
        for p in self.Peers:
            if len(p.allowed_ip) > 0:
                add = p.allowed_ip.split(',')
                for i in add:
                    a, c = i.split('/')
                    try:
                        ip = ipaddress.ip_address(a.replace(" ", ""))
                        existedAddress.append(ip)
                        logger.debug(f" Added peer {p.name} ({p.id[:8]}...) IP: {ip} (v{ip.version})")
                    except ValueError as error:
                        logger.error(f"{self.Name} peer {p.id} have invalid ip")
        
        # Collect restricted peer addresses
        for p in await self.getRestrictedPeersList():
            if len(p.allowed_ip) > 0:
                add = p.allowed_ip.split(',')
                for i in add:
                    a, c = i.split('/')
                    ip = ipaddress.ip_address(a.replace(" ", ""))
                    existedAddress.append(ip)
                    logger.debug(f" Added restricted peer {p.id[:8]}... IP: {ip} (v{ip.version})")
        
        # Add interface addresses to excluded list
        for i in address:
            addressSplit, cidr = i.split('/')
            ip = ipaddress.ip_address(addressSplit.replace(" ", ""))
            existedAddress.append(ip)
            logger.debug(f"Added interface IP: {ip} (v{ip.version})")
        
        # Find available addresses in each network
        for i in address:
            network = ipaddress.ip_network(i.replace(" ", ""), False)
            logger.debug(f"Processing network: {network} (v{network.version})")
            
            count = 0
            ipv6_count = 0
            
            for h in network.hosts():
                if h not in existedAddress:
                    availableAddress.append(ipaddress.ip_network(h).compressed)
                    count += 1
                    
                    # Log IPv6 addresses specifically
                    if h.version == 6:
                        ipv6_count += 1
                        if ipv6_count <= 5 or ipv6_count % 50 == 0:  # Log first 5 and then every 50th
                            logger.debug(f"Available IPv6: {h} (#{ipv6_count})")
                    
                    if not all:
                        if network.version == 6 and count > 255:
                            logger.debug(f"Reached IPv6 limit (255) for network {network}")
                            break
            
            logger.debug(f"Found {count} available IPs in network {network}")
            if network.version == 6:
                logger.debug(f"Found {ipv6_count} available IPv6 addresses")
        
        # Debug the final results by IP version
        ipv4_addresses = []
        ipv6_addresses = []
        
        for addr in availableAddress:
            # Remove CIDR notation if present
            if '/' in addr:
                addr = addr.split('/')[0]
            
            try:
                ip = ipaddress.ip_address(addr)
                if ip.version == 4:
                    ipv4_addresses.append(addr)
                else:
                    ipv6_addresses.append(addr)
            except ValueError:
                logger.debug(f"Invalid IP address in results: {addr}")
        
        logger.debug(f"Total available addresses: {len(availableAddress)}")
        logger.debug(f"IPv4 addresses: {len(ipv4_addresses)}")
        logger.debug(f"IPv6 addresses: {len(ipv6_addresses)}")
            
        return True, availableAddress

    def getRealtimeTrafficUsage(self):
        """Get real-time traffic usage using native WireGuard/AmneziaWG statistics"""
        # Use the native WireGuard/AmneziaWG method
        return self.getRealtimeTraffic()

    def getRealtimeTraffic(self):
        """Get real-time traffic data using native WireGuard/AmneziaWG statistics"""
        if not self.getStatus():
            return {"sent": 0, "recv": 0}
        
        try:
            # Get interface protocol (wg or awg)
            protocol = self.get_iface_proto()
            
            # Use the global traffic monitor with native WireGuard/AmneziaWG commands
            result = TRAFFIC_MONITOR.calculate_rate(self.Name, protocol)
            
            # Add logging
            logger.debug(f"Interface {self.Name} (native {protocol}) traffic: in={result['recv']}MB/s, out={result['sent']}MB/s, period={result['sample_period']}s")
            
            return {
                "sent": result["sent"],
                "recv": result["recv"]
            }
        except Exception as e:
            logger.error(f"Failed to get real-time traffic from {protocol}: {str(e)}")
            return {"sent": 0, "recv": 0}

    def getRealtimeTrafficFromPeers(self):
        """Get real-time traffic data using native WireGuard/AmneziaWG statistics (legacy method name kept for compatibility)"""
        return self.getRealtimeTraffic()

    def _scramble_cps_pattern(self, pattern: str, seed: str) -> str:
        """
        Scramble a CPS pattern to create variation for interface/peer obfuscation.
        Uses seed for deterministic but different scrambling.
        
        Args:
            pattern: Original CPS pattern (e.g., "<b 0x474554><c><r 16>")
            seed: Seed for deterministic randomization
        
        Returns:
            Scrambled CPS pattern with modified lengths and optional tags
        """
        if not pattern or not pattern.strip():
            return pattern
        
        # Generate deterministic random values based on seed
        seed_hash = hashlib.sha256(seed.encode()).digest()
        seed_int = int.from_bytes(seed_hash[:8], 'big')
        
        # Use seed for random operations
        import random
        rng = random.Random(seed_int)
        
        try:
            # Parse existing tags
            tags = re.findall(r'<(b\s+0x[0-9a-fA-F]+|c|t|r\s+\d+|rc\s+\d+|rd\s+\d+)>', pattern)
            
            if not tags:
                return pattern
            
            scrambled_tags = []
            for tag in tags:
                tag_content = tag.strip()
                
                # Handle <b 0x...> - modify hex value to ensure uniqueness
                if tag_content.startswith('b 0x'):
                    hex_val = tag_content[4:]
                    if len(hex_val) >= 2:
                        # Always modify hex value based on seed to ensure different patterns
                        # For large hex blobs, modify multiple bytes at random positions
                        hex_bytes = [hex_val[i:i+2] for i in range(0, len(hex_val), 2)]
                        
                        # Determine how many bytes to modify (10-30% of bytes, min 1, max 10)
                        num_bytes_to_modify = max(1, min(10, max(1, len(hex_bytes) // 10)))
                        if num_bytes_to_modify == 0:
                            num_bytes_to_modify = 1
                        
                        # Get random positions to modify (deterministic based on seed)
                        positions_to_modify = set()
                        while len(positions_to_modify) < num_bytes_to_modify and len(positions_to_modify) < len(hex_bytes):
                            pos = rng.randint(0, len(hex_bytes) - 1)
                            positions_to_modify.add(pos)
                        
                        # Modify bytes at selected positions
                        for pos in positions_to_modify:
                            # Modify byte to a random value (deterministic based on seed)
                            new_byte = format(rng.randint(0, 255), '02x')
                            hex_bytes[pos] = new_byte
                        
                        new_hex = ''.join(hex_bytes)
                        scrambled_tags.append(f'<b 0x{new_hex}>')
                    else:
                        scrambled_tags.append(f'<{tag_content}>')
                
                # Handle <c> and <t> - keep them
                elif tag_content in ['c', 't']:
                    scrambled_tags.append(f'<{tag_content}>')
                
                # Handle <r N>, <rc N>, <rd N> - modify length ±25%
                elif tag_content.startswith('r ') or tag_content.startswith('rc ') or tag_content.startswith('rd '):
                    parts = tag_content.split()
                    if len(parts) == 2:
                        try:
                            length = int(parts[1])
                            # Modify length by ±25% (min 1, max 1000)
                            variation = int(length * 0.25)
                            new_length = max(1, min(1000, length + rng.randint(-variation, variation)))
                            scrambled_tags.append(f'<{parts[0]} {new_length}>')
                        except ValueError:
                            scrambled_tags.append(f'<{tag_content}>')
                    else:
                        scrambled_tags.append(f'<{tag_content}>')
                else:
                    scrambled_tags.append(f'<{tag_content}>')
            
            # 30% chance to add an extra random tag at the end
            if rng.random() < 0.3:
                extra_tag_type = rng.choice(['r', 'rc', 'rd'])
                extra_length = rng.randint(8, 32)
                scrambled_tags.append(f'<{extra_tag_type} {extra_length}>')
            
            return ''.join(scrambled_tags)
        
        except Exception as e:
            logger.debug(f"Failed to scramble CPS pattern, using original: {e}")
            return pattern


class Peer:
    def __init__(self, tableData, configuration: Configuration):
        self.configuration = configuration
        self.id = tableData.get("id", "")
        self.private_key = tableData.get("private_key", "")
        self.DNS = tableData.get("DNS", "")
        self.endpoint_allowed_ip = tableData.get("endpoint_allowed_ip", "")
        self.name = tableData.get("name", "")
        self.total_receive = tableData.get("total_receive", 0)
        self.total_sent = tableData.get("total_sent", 0)
        self.total_data = tableData.get("total_data", 0)
        self.endpoint = tableData.get("endpoint", "N/A")
        self.status = tableData.get("status", "stopped")
        self.latest_handshake = tableData.get("latest_handshake", "N/A")
        self.allowed_ip = tableData.get("allowed_ip", "N/A")
        self.cumu_receive = tableData.get("cumu_receive", 0)
        self.cumu_sent = tableData.get("cumu_sent", 0)
        self.cumu_data = tableData.get("cumu_data", 0)
        self.traffic = tableData.get("traffic", [])
        self.mtu = tableData.get("mtu", 1420)
        self.keepalive = tableData.get("keepalive", 21)
        self.remote_endpoint = tableData.get("remote_endpoint", "N/A")
        self.preshared_key = tableData.get("preshared_key", "")
        self.upload_rate_limit = tableData.get("upload_rate_limit", 0)
        self.download_rate_limit = tableData.get("download_rate_limit", 0)
        self.scheduler_type = tableData.get("scheduler_type", "htb")
        # Peer-specific I1-I5 CPS parameters (override config defaults if set)
        # Normalize raw hex values (0x...) to CPS tag format (<b 0x...>)
        self.I1 = NormalizeCPSFormat(tableData.get("I1", ""))
        self.I2 = NormalizeCPSFormat(tableData.get("I2", ""))
        self.I3 = NormalizeCPSFormat(tableData.get("I3", ""))
        self.I4 = NormalizeCPSFormat(tableData.get("I4", ""))
        self.I5 = NormalizeCPSFormat(tableData.get("I5", ""))
    
    def _scramble_cps_pattern(self, pattern: str, seed: str) -> str:
        """
        Scramble a CPS pattern to create variation for peer obfuscation.
        Uses peer ID as seed for deterministic but different scrambling per peer.
        
        Args:
            pattern: Original CPS pattern (e.g., "<b 0x474554><c><r 16>")
            seed: Seed for deterministic randomization (e.g., peer ID)
        
        Returns:
            Scrambled CPS pattern with modified lengths and optional tags
        """
        if not pattern or not pattern.strip():
            return pattern
        
        # Generate deterministic random values based on seed
        seed_hash = hashlib.sha256(seed.encode()).digest()
        seed_int = int.from_bytes(seed_hash[:8], 'big')
        
        # Use seed for random operations
        import random
        rng = random.Random(seed_int)
        
        try:
            # Parse existing tags
            tags = re.findall(r'<(b\s+0x[0-9a-fA-F]+|c|t|r\s+\d+|rc\s+\d+|rd\s+\d+)>', pattern)
            
            if not tags:
                return pattern
            
            scrambled_tags = []
            for tag in tags:
                tag_content = tag.strip()
                
                # Handle <b 0x...> - modify hex value to ensure uniqueness
                if tag_content.startswith('b 0x'):
                    hex_val = tag_content[4:]
                    if len(hex_val) >= 2:
                        # Always modify hex value based on seed to ensure different patterns
                        # For large hex blobs, modify multiple bytes at random positions
                        hex_bytes = [hex_val[i:i+2] for i in range(0, len(hex_val), 2)]
                        
                        # Determine how many bytes to modify (10-30% of bytes, min 1, max 10)
                        num_bytes_to_modify = max(1, min(10, max(1, len(hex_bytes) // 10)))
                        if num_bytes_to_modify == 0:
                            num_bytes_to_modify = 1
                        
                        # Get random positions to modify (deterministic based on seed)
                        positions_to_modify = set()
                        while len(positions_to_modify) < num_bytes_to_modify and len(positions_to_modify) < len(hex_bytes):
                            pos = rng.randint(0, len(hex_bytes) - 1)
                            positions_to_modify.add(pos)
                        
                        # Modify bytes at selected positions
                        for pos in positions_to_modify:
                            # Modify byte to a random value (deterministic based on seed)
                            new_byte = format(rng.randint(0, 255), '02x')
                            hex_bytes[pos] = new_byte
                        
                        new_hex = ''.join(hex_bytes)
                        scrambled_tags.append(f'<b 0x{new_hex}>')
                    else:
                        scrambled_tags.append(f'<{tag_content}>')
                
                # Handle <c> and <t> - keep them
                elif tag_content in ['c', 't']:
                    scrambled_tags.append(f'<{tag_content}>')
                
                # Handle <r N>, <rc N>, <rd N> - modify length ±25%
                elif tag_content.startswith('r ') or tag_content.startswith('rc ') or tag_content.startswith('rd '):
                    parts = tag_content.split()
                    if len(parts) == 2:
                        try:
                            length = int(parts[1])
                            # Modify length by ±25% (min 1, max 1000)
                            variation = int(length * 0.25)
                            new_length = max(1, min(1000, length + rng.randint(-variation, variation)))
                            scrambled_tags.append(f'<{parts[0]} {new_length}>')
                        except ValueError:
                            scrambled_tags.append(f'<{tag_content}>')
                    else:
                        scrambled_tags.append(f'<{tag_content}>')
                else:
                    scrambled_tags.append(f'<{tag_content}>')
            
            # 30% chance to add an extra random tag at the end
            if rng.random() < 0.3:
                extra_tag_type = rng.choice(['r', 'rc', 'rd'])
                extra_length = rng.randint(8, 32)
                scrambled_tags.append(f'<{extra_tag_type} {extra_length}>')
            
            return ''.join(scrambled_tags)
        
        except Exception as e:
            logger.debug(f"Failed to scramble CPS pattern, using original: {e}")
            return pattern
        

    def toJson(self):
        self.getJobs(force_refresh=True)
        # Note: getShareLink should be called before toJson() in async contexts
        # If ShareLink is not set, it will be None in the JSON output
        # Create a copy of __dict__ without the configuration reference to avoid circular serialization
        peer_dict = self.__dict__.copy()
        peer_dict.pop('configuration', None)  # Remove circular reference
        
        # Convert jobs to serializable format
        if 'jobs' in peer_dict and peer_dict['jobs']:
            peer_dict['jobs'] = [job.toJson() for job in peer_dict['jobs']]
        
        return peer_dict

    def __repr__(self):
        return str(self.toJson())

    async def updatePeerAsync(self, name: str, private_key: str,
                   preshared_key: str,
                   dns_addresses: str, allowed_ip: str, endpoint_allowed_ip: str, mtu: int,
                   keepalive: int, i1: str = None, i2: str = None, i3: str = None, 
                   i4: str = None, i5: str = None) -> ResponseObject:
        """Async version of updatePeer"""
        if not self.configuration.getStatus():
            self.configuration.toggleConfiguration()
        cmd_prefix = self.configuration.get_iface_proto()
        peers_list = await self.configuration.getPeersList()
        existingAllowedIps = [item for row in list(
            map(lambda x: [q.strip() for q in x.split(',')],
                map(lambda y: y.allowed_ip,
                    list(filter(lambda k: k.id != self.id, peers_list))))) for item in row]

        if allowed_ip in existingAllowedIps:
            return ResponseObject(False, "Allowed IP already taken by another peer")
        if not ValidateIPAddressesWithRange(endpoint_allowed_ip):
            return ResponseObject(False, f"Endpoint Allowed IPs format is incorrect")
        if len(dns_addresses) > 0 and not ValidateDNSAddress(dns_addresses):
            return ResponseObject(False, f"DNS format is incorrect")
        if mtu < 0 or mtu > 1460:
            return ResponseObject(False, "MTU format is not correct")
        if keepalive < 0:
            return ResponseObject(False, "Persistent Keepalive format is not correct")
        
        # Validate I1-I5 CPS format if provided (only for AWG protocol)
        if cmd_prefix == "awg":
            i_params = [("I1", i1), ("I2", i2), ("I3", i3), ("I4", i4), ("I5", i5)]
            for param_name, param_value in i_params:
                if param_value is not None and param_value.strip():
                    is_valid, error_msg = ValidateCPSFormat(param_value.strip())
                    if not is_valid:
                        return ResponseObject(False, f"{param_name}: {error_msg}")
        
        if len(private_key) > 0:
            pubKey = GenerateWireguardPublicKey(private_key)
            if not pubKey[0] or pubKey[1] != self.id:
                return ResponseObject(False, "Private key does not match with the public key")
        try:
            # Use cryptographically secure random for UUID generation
            uid = str(uuid.uuid4())
            pskExist = len(preshared_key) > 0

            if pskExist:
                with open(uid, "w+") as f:
                    f.write(preshared_key)
            newAllowedIPs = allowed_ip.replace(" ", "")

            try:
                if cmd_prefix == "awg":
                    result = execute_awg_command(
                        action='set',
                        interface=self.configuration.Name,
                        peer_key=self.id,
                        allowed_ips=newAllowedIPs,
                        preshared_key=preshared_key if pskExist else None
                    )
                else:
                    result = execute_wg_command(
                        action='set',
                        interface=self.configuration.Name,
                        peer_key=self.id,
                        allowed_ips=newAllowedIPs,
                        preshared_key=preshared_key if pskExist else None
                    )
                if not result['success']:
                    return ResponseObject(False, f"Failed to update allowed IPs: {result.get('error', result.get('stderr', 'Unknown error'))}")
            finally:
                # Always clean up the temporary file
                if pskExist and os.path.exists(uid):
                    try:
                        os.remove(uid)
                    except OSError as e:
                        logger.warning(f"Failed to remove temporary file {uid}: {e}")
                    except Exception as e:
                        logger.warning(f"Unexpected error removing temporary file {uid}: {e}")

            if result['stderr'] and len(result['stderr'].strip()) != 0:
                return ResponseObject(False,
                                      "Update peer failed when updating Allowed IPs")
            
            if cmd_prefix == "awg":
                result = execute_awg_quick_command('save', self.configuration.Name)
            else:
                result = execute_wg_quick_command('save', self.configuration.Name)
            if not result['success']:
                return ResponseObject(False, f"Failed to save configuration: {result.get('error', result.get('stderr', 'Unknown error'))}")

            # Build update dict with peer fields
            update_data = {
                'name': name,
                'private_key': private_key,
                'DNS': dns_addresses,
                'endpoint_allowed_ip': endpoint_allowed_ip,
                'mtu': mtu,
                'keepalive': keepalive,
                'preshared_key': preshared_key
            }
            
            # Add I1-I5 if provided (only for AWG protocol)
            # Normalize raw hex values (0x...) to CPS tag format (<b 0x...>)
            if self.configuration.get_iface_proto() == "awg":
                if i1 is not None:
                    update_data['I1'] = NormalizeCPSFormat(i1.strip() if i1 else "")
                if i2 is not None:
                    update_data['I2'] = NormalizeCPSFormat(i2.strip() if i2 else "")
                if i3 is not None:
                    update_data['I3'] = NormalizeCPSFormat(i3.strip() if i3 else "")
                if i4 is not None:
                    update_data['I4'] = NormalizeCPSFormat(i4.strip() if i4 else "")
                if i5 is not None:
                    update_data['I5'] = NormalizeCPSFormat(i5.strip() if i5 else "")
            
            await self.configuration.db.update_peer(self.id, update_data)
            
            # Update local attributes (normalize raw hex to CPS format)
            if i1 is not None:
                self.I1 = NormalizeCPSFormat(i1.strip() if i1 else "")
            if i2 is not None:
                self.I2 = NormalizeCPSFormat(i2.strip() if i2 else "")
            if i3 is not None:
                self.I3 = NormalizeCPSFormat(i3.strip() if i3 else "")
            if i4 is not None:
                self.I4 = NormalizeCPSFormat(i4.strip() if i4 else "")
            if i5 is not None:
                self.I5 = NormalizeCPSFormat(i5.strip() if i5 else "")
            return ResponseObject()
        except subprocess.CalledProcessError as exc:
            return ResponseObject(False, exc.output.decode("UTF-8").strip())

    def downloadPeer(self) -> dict[str, str]:
        filename = self.name
        if len(filename) == 0:
            filename = "UntitledPeer"
        filename = "".join(filename.split(' '))
        filename = f"{filename}_{self.configuration.Name}"
        illegal_filename = [".", ",", "/", "?", "<", ">", "\\", ":", "*", '|' '\"', "com1", "com2", "com3",
                            "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
                            "lpt5", "lpt6", "lpt7", "lpt8", "lpt9", "con", "nul", "prn"]
        for i in illegal_filename:
            filename = filename.replace(i, "")

        peerConfiguration = f'''[Interface]
PrivateKey = {self.private_key}
Address = {self.allowed_ip}
MTU = {str(self.mtu)}
'''
        if len(self.DNS) > 0:
            peerConfiguration += f"DNS = {self.DNS}\n"

        if self.configuration.get_iface_proto() == "awg":
            peerConfiguration += f'''
Jc = {self.configuration.Jc}
Jmin = {self.configuration.Jmin}
Jmax = {self.configuration.Jmax}
S1 = {self.configuration.S1}
S2 = {self.configuration.S2}
H1 = {self.configuration.H1}
H2 = {self.configuration.H2}
H3 = {self.configuration.H3}
H4 = {self.configuration.H4}
'''
            # Add I1-I5 if present (AmneziaWG 1.5)
            # Note: I1-I5 are one-way decoy packets sent before handshake initiation.
            # They do NOT need to match between peers/configs - each side configures
            # independently for its own outbound traffic. The receiver silently drops
            # these packets (expected behavior).
            # Use peer-specific I1-I5 if set, otherwise scramble from config base values
            seed = f"{self.configuration.Name}_{self.id}"
            
            # I1: Use peer-specific if set, otherwise scramble from config
            if self.I1 and self.I1.strip():
                peerConfiguration += f'I1 = {self.I1}\n'
            elif self.configuration.I1 and self.configuration.I1.strip():
                scrambled_i1 = self._scramble_cps_pattern(self.configuration.I1, seed + "_I1")
                peerConfiguration += f'I1 = {scrambled_i1}\n'
            
            # I2: Use peer-specific if set, otherwise scramble from config
            if self.I2 and self.I2.strip():
                peerConfiguration += f'I2 = {self.I2}\n'
            elif self.configuration.I2 and self.configuration.I2.strip():
                scrambled_i2 = self._scramble_cps_pattern(self.configuration.I2, seed + "_I2")
                peerConfiguration += f'I2 = {scrambled_i2}\n'
            
            # I3: Use peer-specific if set, otherwise scramble from config
            if self.I3 and self.I3.strip():
                peerConfiguration += f'I3 = {self.I3}\n'
            elif self.configuration.I3 and self.configuration.I3.strip():
                scrambled_i3 = self._scramble_cps_pattern(self.configuration.I3, seed + "_I3")
                peerConfiguration += f'I3 = {scrambled_i3}\n'
            
            # I4: Use peer-specific if set, otherwise scramble from config
            if self.I4 and self.I4.strip():
                peerConfiguration += f'I4 = {self.I4}\n'
            elif self.configuration.I4 and self.configuration.I4.strip():
                scrambled_i4 = self._scramble_cps_pattern(self.configuration.I4, seed + "_I4")
                peerConfiguration += f'I4 = {scrambled_i4}\n'
            
            # I5: Use peer-specific if set, otherwise scramble from config
            if self.I5 and self.I5.strip():
                peerConfiguration += f'I5 = {self.I5}\n'
            elif self.configuration.I5 and self.configuration.I5.strip():
                scrambled_i5 = self._scramble_cps_pattern(self.configuration.I5, seed + "_I5")
                peerConfiguration += f'I5 = {scrambled_i5}\n'

        peerConfiguration += f'''
[Peer]
PublicKey = {self.configuration.PublicKey}
AllowedIPs = {self.endpoint_allowed_ip}
Endpoint = {DashboardConfig.GetConfig("Peers", "remote_endpoint")[1]}:{self.configuration.ListenPort}
PersistentKeepalive = {str(self.keepalive)}
'''
        if len(self.preshared_key) > 0:
            peerConfiguration += f"PresharedKey = {self.preshared_key}\n"
        return {
            "fileName": filename,
            "file": peerConfiguration
        }

    def getJobs(self, force_refresh=False):
        logger.debug(f" getJobs called for peer {self.id} in config {self.configuration.Name}")
        # Only reload if jobs list is empty or we need to refresh
        if not hasattr(self, 'jobs') or not self.jobs or force_refresh:
            self.jobs = AllPeerJobs.searchJob(self.configuration.Name, self.id)
            logger.debug(f" Found {len(self.jobs)} jobs for peer {self.id}")
            for i, job in enumerate(self.jobs):
                logger.debug(f"   Job {i+1}: {job.toJson()}")
        else:
            logger.debug(f" Using cached jobs for peer {self.id}: {len(self.jobs)} jobs")
    
    def refreshJobs(self):
        """Force refresh jobs from Redis"""
        self.getJobs(force_refresh=True)

    async def getShareLink(self):
        self.ShareLink = await AllPeerShareLinks.getLink(self.configuration.Name, self.id)

    def resetDataUsage(self, type):
        try:
            return self.configuration.db.reset_peer_data_usage(self.id, type)
        except Exception as e:
            return False




async def cleanup_orphaned_configurations(existing_config_files: set):
    """
    Clean up database entries for configurations that no longer have corresponding .conf files.
    This handles the edge case where Redis data persists but config files don't (e.g., during development).
    """
    from .DataBase import get_redis_manager
    
    try:
        redis_manager = await get_redis_manager()
        
        # Get all configuration names from Redis database
        all_config_keys = redis_manager.get_all_keys()
        
        # Extract configuration names from Redis keys
        db_config_names = set()
        for key in all_config_keys:
            # Keys are in format: wiregate:{config_name}:{peer_id}
            # or wiregate:{config_name}_restrict_access:{peer_id}
            if key.startswith('wiregate:'):
                parts = key.split(':')
                if len(parts) >= 2:
                    config_name = parts[1]
                    # Remove _restrict_access suffix if present
                    if config_name.endswith('_restrict_access'):
                        config_name = config_name.replace('_restrict_access', '')
                    db_config_names.add(config_name)
        
        # Find orphaned configurations (exist in DB but not in files)
        orphaned_configs = db_config_names - existing_config_files
        
        if orphaned_configs:
            logger.info(f"Found {len(orphaned_configs)} orphaned configuration(s) in database: {list(orphaned_configs)}")
            logger.info("Cleaning up orphaned database entries...")
            
            for config_name in orphaned_configs:
                try:
                    # Delete all keys for this configuration
                    keys_to_delete = []
                    for key in all_config_keys:
                        if key.startswith(f'wiregate:{config_name}:') or key.startswith(f'wiregate:{config_name}_restrict_access:'):
                            keys_to_delete.append(key)
                    
                    if keys_to_delete:
                        redis_manager.delete_keys(keys_to_delete)
                        logger.info(f"Cleaned up {len(keys_to_delete)} database entries for orphaned config: {config_name}")
                
                except Exception as e:
                    logger.error(f"Error cleaning up orphaned config {config_name}: {e}")
            
            logger.info("Orphaned configuration cleanup completed.")
        else:
            logger.info("No orphaned configurations found in database.")
            
    except Exception as e:
        logger.error(f"Error during orphaned configuration cleanup: {e}")

async def InitWireguardConfigurationsList(startup: bool = False):
    # Database migrations are now handled in the main application startup
    # This function focuses on configuration initialization
    
    wg_conf_path = DashboardConfig.GetConfig("Server", "wg_conf_path")[1]
    logger.info(f"Loading WireGuard configurations from: {wg_conf_path}")
    
    try:
        confs = os.listdir(wg_conf_path)
    except Exception as e:
        logger.error(f"Failed to list directory {wg_conf_path}: {e}")
        return
    
    confs.sort()
    
    # Get list of existing configuration files (without .conf extension)
    existing_config_files = set()
    for i in confs:
        if RegexMatch("^(.{1,}).(conf)$", i):
            existing_config_files.add(i.replace('.conf', ''))
    
    logger.info(f"Found {len(existing_config_files)} configuration file(s)")
    
    # Clean up database entries for configurations that no longer have files
    if startup:
        await cleanup_orphaned_configurations(existing_config_files)
    
    # Load configurations from existing files using async factory
    loaded_count = 0
    failed_count = 0
    for i in confs:
        if RegexMatch("^(.{1,}).(conf)$", i):
            config_name = i.replace('.conf', '')
            try:
                if config_name in Configurations.keys():
                    if Configurations[config_name].configurationFileChanged():
                        logger.info(f"Reloading configuration: {config_name}")
                        Configurations[config_name] = await Configuration.create_async(config_name)
                        loaded_count += 1
                else:
                    logger.info(f"Loading configuration: {config_name}")
                    Configurations[config_name] = await Configuration.create_async(config_name, startup=startup)
                    loaded_count += 1
                    logger.info(f"✓ Successfully loaded configuration: {config_name}")
            except Configuration.InvalidConfigurationFileException as e:
                logger.error(f"{config_name} has an invalid configuration file: {e}")
                failed_count += 1
            except Exception as e:
                logger.error(f"Failed to load configuration {config_name}: {e}", exc_info=True)
                failed_count += 1
    
    logger.info(f"Configuration loading complete: {loaded_count} loaded, {failed_count} failed")

def refresh_all_public_keys():
    """Force refresh public keys for all configurations"""
    logger.info("Refreshing public keys for all configurations...")
    refreshed_count = 0
    for config_name, config in Configurations.items():
        if config.PrivateKey and not config.PublicKey:
            logger.info(f"Refreshing public key for configuration: {config_name}")
            config.PublicKey = config.__getPublicKey()
            refreshed_count += 1
        elif config.PrivateKey and config.PublicKey:
            # Test if the existing public key is valid by regenerating it
            success, new_public_key = GenerateWireguardPublicKey(config.PrivateKey)
            if success and new_public_key and new_public_key != config.PublicKey:
                logger.warning(f"Public key mismatch for {config_name}, updating...")
                config.PublicKey = new_public_key
                refreshed_count += 1
    
    logger.info(f"Refreshed public keys for {refreshed_count} configurations")
    return refreshed_count

async def InitRateLimits():
    """Reapply rate limits for all peers across all interfaces"""
    logger = logging.getLogger('wiregate')
    try:
        for config_name, config in Configurations.items():
            logger.debug(f"Processing rate limits for configuration: {config_name}")
            try:
                # Get all peers with rate limits
                all_peers = await config.db.get_peers()
                rate_limited_peers = [
                    peer for peer in all_peers 
                    if (peer.get('upload_rate_limit', 0) > 0 or peer.get('download_rate_limit', 0) > 0)
                ]
                
                logger.debug(f"Found {len(rate_limited_peers)} rate-limited peers for {config_name}")
                
                for peer in rate_limited_peers:
                    try:
                        # Skip if missing required data
                        if not peer.get('id') or not peer.get('allowed_ip'):
                            logger.warning(f"Skipping peer {peer.get('id')} - missing required data")
                            continue
                            
                        # Execute traffic-weir command to reapply limits
                        cmd = [
                            './traffic-weir',
                            '-interface', config.Name,
                            '-peer', peer['id'],
                            '-upload-rate', str(peer.get('upload_rate_limit', 0)),
                            '-download-rate', str(peer.get('download_rate_limit', 0)),
                            '-protocol', config.Protocol,
                            '-scheduler', peer.get('scheduler_type', 'htb'),
                            '-allowed-ips', peer['allowed_ip']
                        ]
                        
                        logger.debug(f"Executing command: {' '.join(cmd)}")
                        process = await asyncio.create_subprocess_exec(
                            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            logger.error(f"Failed to reapply rate limits for peer {peer['id']} on {config.Name}: {stderr.decode()}")
                        else:
                            logger.debug(f"Successfully applied rate limits for peer {peer['id']} on {config.Name}")
                            
                    except Exception as e:
                        logger.error(f"Error reapplying rate limits for peer {peer['id']} on {config.Name}: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error processing rate limits for configuration {config_name}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error initializing rate limits: {str(e)}")


Configurations: dict[str, Configuration] = {}



# Add this at the module level (outside any class)
class WireGuardTrafficMonitor:
    """Accurate traffic monitor using native WireGuard/AmneziaWG statistics with per-peer granularity"""
    
    def __init__(self):
        # Track per-peer statistics: {interface_name: {peer_public_key: {'recv': bytes, 'sent': bytes, 'timestamp': time}}}
        self.last_measurement = {}
    
    def get_transfer_data(self, interface_name, protocol='wg'):
        """Get cumulative transfer data from wg/awg show transfer command"""
        try:
            # Use appropriate command based on protocol
            cmd_func = execute_awg_command if protocol == 'awg' else execute_wg_command
            result = cmd_func('show', interface_name, subcommand='transfer')
            
            if not result['success']:
                logger.debug(f"Failed to get transfer data for {interface_name}: {result.get('error', 'Unknown error')}")
                return None
                
            # Parse output: peer_key\tsent\treceived
            lines = result['stdout'].strip().split('\n')
            peer_data = {}
            total_recv = 0
            total_sent = 0
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) == 3:
                    peer_key = parts[0]
                    sent_bytes = int(parts[1])
                    recv_bytes = int(parts[2])
                    
                    peer_data[peer_key] = {
                        'recv': recv_bytes,
                        'sent': sent_bytes,
                        'timestamp': time.time()
                    }
                    
                    total_recv += recv_bytes
                    total_sent += sent_bytes
            
            # Return both per-peer data and interface totals
            return {
                'peer_data': peer_data,
                'total_recv': total_recv,
                'total_sent': total_sent,
                'timestamp': time.time()
            }
                
        except Exception as e:
            logger.debug(f"Could not get transfer data for {interface_name}: {str(e)}")
            return None
    
    def calculate_rate(self, interface_name, protocol='wg'):
        """Calculate real-time transfer rate in Mbps using per-peer aggregation"""
        current_data = self.get_transfer_data(interface_name, protocol)
        
        if not current_data:
            return {"sent": 0, "recv": 0, "sample_period": 0}
        
        # Check if we have previous measurements
        if interface_name in self.last_measurement:
            last_data = self.last_measurement[interface_name]
            time_diff = current_data['timestamp'] - last_data['timestamp']
            
            if time_diff > 0:
                # Calculate deltas for total interface traffic
                recv_diff = current_data['total_recv'] - last_data['total_recv']
                sent_diff = current_data['total_sent'] - last_data['total_sent']
                
                # Handle counter resets (interface restart)
                if recv_diff < 0:
                    recv_diff = current_data['total_recv']
                if sent_diff < 0:
                    sent_diff = current_data['total_sent']
                
                # Convert to Mbps
                recv_rate_mbps = (recv_diff * 8) / (time_diff * 1_000_000)
                sent_rate_mbps = (sent_diff * 8) / (time_diff * 1_000_000)
                
                # Store current measurement for next calculation
                self.last_measurement[interface_name] = current_data
                
                return {
                    "sent": round(sent_rate_mbps, 3),
                    "recv": round(recv_rate_mbps, 3),
                    "sample_period": round(time_diff, 3)
                }
        
        # First measurement, store and return 0
        self.last_measurement[interface_name] = current_data
        return {"sent": 0, "recv": 0, "sample_period": 0}
    
    def _record_cps_connection_attempt(self, success: bool, latency_ms: float = 0.0, throughput_mbps: float = 0.0):
        """Record a connection attempt for CPS pattern adaptation"""
        if self.get_iface_proto() != "awg":
            return
        
        self._ensure_cps_adaptation_initialized()
        if not self.cps_adaptation:
            return
        
        try:
            self.cps_adaptation.metrics.record_connection_attempt(
                self.I1 or '', self.I2 or '', self.I3 or '', self.I4 or '', self.I5 or '',
                success, latency_ms, throughput_mbps
            )
        except Exception as e:
            logger.error(f"Failed to record CPS connection attempt: {e}")
    
    def _get_current_throughput(self) -> float:
        """Get current throughput in Mbps for CPS adaptation"""
        try:
            if hasattr(self, '_traffic_monitor'):
                rates = self._traffic_monitor.get_peer_rates(self.Name, self.get_iface_proto())
                if rates:
                    # Return average throughput across all peers
                    total_throughput = sum(r.get('sent', 0) + r.get('recv', 0) for r in rates.values())
                    return total_throughput / len(rates) if rates else 0.0
        except Exception as e:
            logger.debug(f"Failed to get current throughput: {e}")
        return 0.0
    
    def _apply_cps_patterns(self, patterns: dict[str, str]):
        """Apply adapted CPS patterns to configuration"""
        try:
            # Normalize raw hex values (0x...) to CPS tag format (<b 0x...>)
            if patterns.get('i1') is not None:
                self.I1 = NormalizeCPSFormat(patterns['i1'])
            if patterns.get('i2') is not None:
                self.I2 = NormalizeCPSFormat(patterns['i2'])
            if patterns.get('i3') is not None:
                self.I3 = NormalizeCPSFormat(patterns['i3'])
            if patterns.get('i4') is not None:
                self.I4 = NormalizeCPSFormat(patterns['i4'])
            if patterns.get('i5') is not None:
                self.I5 = NormalizeCPSFormat(patterns['i5'])
            
            # Update configuration file
            self.updateConfigurationSettings({
                'I1': self.I1,
                'I2': self.I2,
                'I3': self.I3,
                'I4': self.I4,
                'I5': self.I5
            })
        except Exception as e:
            logger.error(f"Failed to apply CPS patterns: {e}")
    
    def _ensure_cps_adaptation_initialized(self):
        """Ensure CPS adaptation is initialized (lazy initialization)"""
        if not hasattr(self, 'cps_adaptation') or self.cps_adaptation is None:
            try:
                from .AwgCPS.CPSPatternAdaptation import CPSPatternAdaptation
                self.cps_adaptation = CPSPatternAdaptation(self.Name, self.db)
                logger.debug(f"Lazy initialized CPS adaptation for {self.Name}")
            except Exception as e:
                logger.warning(f"Failed to initialize CPS adaptation for {self.Name}: {e}")
                self.cps_adaptation = None
    
    def _get_cps_adaptation_stats_safe(self) -> dict[str, Any]:
        """Safely get CPS pattern adaptation statistics (handles missing attributes)"""
        try:
            self._ensure_cps_adaptation_initialized()
            if not self.cps_adaptation:
                return {}
            return self.cps_adaptation.get_adaptation_stats()
        except Exception as e:
            logger.debug(f"Failed to get CPS adaptation stats for {self.Name}: {e}")
            return {}
    
    def _get_cps_adaptation_stats_for_json(self) -> dict[str, Any]:
        """Safe wrapper for toJson - handles missing methods and initialization"""
        try:
            # Try to get the safe method using getattr
            safe_method = getattr(self, '_get_cps_adaptation_stats_safe', None)
            if safe_method and callable(safe_method):
                return safe_method()
            
            # Fallback: try direct initialization if methods don't exist
            init_method = getattr(self, '_ensure_cps_adaptation_initialized', None)
            if init_method and callable(init_method):
                try:
                    init_method()
                    if hasattr(self, 'cps_adaptation') and self.cps_adaptation:
                        stats_method = getattr(self.cps_adaptation, 'get_adaptation_stats', None)
                    if stats_method and callable(stats_method):
                        return stats_method()
                except Exception as e:
                    logger.debug(f"Failed to get CPS adaptation stats: {e}")
                    pass
            return {}
        except Exception as e:
            logger.debug(f"Failed to get CPS adaptation stats for JSON: {e}")
            return {}
    
    def get_cps_adaptation_stats(self) -> dict[str, Any]:
        """Get CPS pattern adaptation statistics"""
        self._ensure_cps_adaptation_initialized()
        if not self.cps_adaptation:
            return {}
        return self.cps_adaptation.get_adaptation_stats()
    
    def periodic_cps_adaptation(self) -> Optional[dict[str, str]]:
        """Perform periodic CPS pattern adaptation (call daily/weekly)"""
        if self.get_iface_proto() != "awg":
            return None
        
        self._ensure_cps_adaptation_initialized()
        if not self.cps_adaptation:
            return None
        
        try:
            adapted_patterns = self.cps_adaptation.periodic_adaptation_check()
            if adapted_patterns:
                self._apply_cps_patterns(adapted_patterns)
                return adapted_patterns
        except Exception as e:
            logger.error(f"Failed periodic CPS adaptation: {e}")
        return None
    
    def get_peer_rates(self, interface_name, protocol='wg'):
        """Get per-peer transfer rates for detailed analysis"""
        current_data = self.get_transfer_data(interface_name, protocol)
        
        if not current_data or interface_name not in self.last_measurement:
            return {}
        
        last_data = self.last_measurement[interface_name]
        time_diff = current_data['timestamp'] - last_data['timestamp']
        
        if time_diff <= 0:
            return {}
        
        peer_rates = {}
        
        # Calculate rate for each peer
        for peer_key, current_peer in current_data['peer_data'].items():
            if peer_key in last_data['peer_data']:
                last_peer = last_data['peer_data'][peer_key]
                
                recv_diff = current_peer['recv'] - last_peer['recv']
                sent_diff = current_peer['sent'] - last_peer['sent']
                
                # Handle counter resets
                if recv_diff < 0:
                    recv_diff = current_peer['recv']
                if sent_diff < 0:
                    sent_diff = current_peer['sent']
                
                recv_rate_mbps = (recv_diff * 8) / (time_diff * 1_000_000)
                sent_rate_mbps = (sent_diff * 8) / (time_diff * 1_000_000)
                
                peer_rates[peer_key] = {
                    "sent": round(sent_rate_mbps, 3),
                    "recv": round(recv_rate_mbps, 3)
                }
        
        return peer_rates

# Create a single instance at module level
TRAFFIC_MONITOR = WireGuardTrafficMonitor()
