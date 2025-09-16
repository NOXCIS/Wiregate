import random, shutil, configparser, psutil
import os, subprocess, uuid, datetime, time
import ipaddress, json, re
import logging

from datetime import datetime, timedelta

logger = logging.getLogger('wiregate')
 
from .DashboardConfig import DashboardConfig
from .Utilities import (
    StringToBoolean, ValidateIPAddressesWithRange,
    ValidateDNSAddress, RegexMatch, strToBool,
    GenerateWireguardPublicKey, get_backup_paths
)
from .App import (
    ResponseObject
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

        if name is not None:
            if data is not None and "Backup" in data.keys():
                db = self.db.import_database(
                    os.path.join(
                        DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                        'WGDashboard_Backup',
                        data["Backup"].replace(".conf", ".redis")))
            else:
                self.db.create_database()
                # Ensure migration happens right after database creation
                self.db.migrate_database()

            self.__parseConfigurationFile()
            self.__initPeersList()

        else:
            self.Name = data["ConfigurationName"]
            self.configPath = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf')

            for i in dir(self):
                if str(i) in data.keys():
                    if isinstance(getattr(self, i), bool):
                        setattr(self, i, StringToBoolean(data[i]))
                    else:
                        setattr(self, i, str(data[i]))

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


    def __initPeersList(self):
        self.Peers: list[Peer] = []
        self.getPeersList()
        self.getRestrictedPeersList()

    def getRawConfigurationFile(self):
        return open(self.configPath, 'r').read()

    def updateRawConfigurationFile(self, newRawConfiguration):
        backupStatus, backup = self.backupConfigurationFile()
        if not backupStatus:
            return False, "Cannot create backup"

        if self.Status:
            self.toggleConfiguration()

        with open(self.configPath, 'w') as f:
            f.write(newRawConfiguration)

        status, err = self.toggleConfiguration()
        if not status:
            restoreStatus = self.restoreBackup(backup['filename'])
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

    def __parseConfigurationFile(self):
        with open(self.configPath, 'r') as f:
            original = [l.rstrip("\n") for l in f.readlines()]
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
            if self.PrivateKey:
                self.PublicKey = self.__getPublicKey()
            self.Status = self.getStatus()

    def __dropDatabase(self):
        """Drop database - now handled by ConfigurationDatabase"""
        self.db.drop_database()

    def __createDatabase(self, dbName=None):
        """Create database - now handled by ConfigurationDatabase"""
        self.db.create_database(dbName)

    def __migrateDatabase(self):
        """Migrate database - now handled by ConfigurationDatabase"""
        self.db.migrate_database()

    def __dumpDatabase(self):
        """Dump database - now handled by ConfigurationDatabase"""
        return self.db.dump_database()

    def __importDatabase(self, sqlFilePath) -> bool:
        """Import database - now handled by ConfigurationDatabase"""
        return self.db.import_database(sqlFilePath)

    def __getPublicKey(self) -> str:
        return GenerateWireguardPublicKey(self.PrivateKey)[1]

    def getStatus(self) -> bool:
        self.Status = self.Name in psutil.net_if_addrs().keys()
        return self.Status

    def getAutostartStatus(self):
        s, d = DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        return self.Name in d

    def __getRestrictedPeers(self):
        self.RestrictedPeers = []
        restricted = self.db.get_restricted_peers()
        for i in restricted:
            self.RestrictedPeers.append(Peer(i, self))

    def configurationFileChanged(self):
        mt = os.path.getmtime(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'))
        changed = self.__configFileModifiedTime is None or self.__configFileModifiedTime != mt
        self.__configFileModifiedTime = mt
        return changed

    def __cleanup_master_keys_in_dev_mode(self):
        """Clean up master key entries from database in development mode"""
        from .ConfigEnv import DASHBOARD_MODE
        if DASHBOARD_MODE == 'development':
            try:
                # Get all peers from database
                all_peers = self.db.get_peers()
                for peer in all_peers:
                    # Check if this is a master key peer (has IP 10.0.0.254/32)
                    if peer.get('allowed_ip') == '10.0.0.254/32' or '10.0.0.254/32' in str(peer.get('allowed_ip', '')):
                        logger.info(f"Removing old master key peer from database: {peer.get('id', 'unknown')[:8]}...")
                        self.db.delete_peer(peer.get('id'))
            except Exception as e:
                logger.error(f"Error cleaning up master keys in development mode: {e}")

    def __getPeers(self):
        if self.configurationFileChanged():
            self.Peers = []
            
            # Clean up master keys in development mode before processing config file
            self.__cleanup_master_keys_in_dev_mode()
            
            with open(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'),
                      'r') as configFile:
                p = []
                pCounter = -1
                content = configFile.read().split('\n')
                try:
                    peerStarts = content.index("[Peer]")
                    content = content[peerStarts:]
                    for i in content:
                        if not RegexMatch("#(.*)", i) and not RegexMatch(";(.*)", i):
                            if i == "[Peer]":
                                pCounter += 1
                                p.append({})
                                p[pCounter]["name"] = ""
                            else:
                                if len(i) > 0:
                                    split = re.split(r'\s*=\s*', i, maxsplit=1)
                                    if len(split) == 2:
                                        p[pCounter][split[0]] = split[1]

                        if RegexMatch("#Name# = (.*)", i):
                            split = re.split(r'\s*=\s*', i, maxsplit=1)
                            if len(split) == 2:
                                p[pCounter]["name"] = split[1]

                    for i in p:
                        if "PublicKey" in i.keys():
                            checkIfExist = self.db.search_peer(i['PublicKey'])
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
                                    "mtu": DashboardConfig.GetConfig("Peers", "peer_mtu")[1],
                                    "keepalive": DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1],
                                    "remote_endpoint": DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                                    "preshared_key": i["PresharedKey"] if "PresharedKey" in i.keys() else "",
                                    "address_v4": ','.join(addr_v4) if addr_v4 else None,
                                    "address_v6": ','.join(addr_v6) if addr_v6 else None,
                                    "upload_rate_limit": 0,
                                    "download_rate_limit": 0,
                                    "scheduler_type": "htb"
                                }
                                self.db.insert_peer(newPeer)
                                self.Peers.append(Peer(newPeer, self))
                            else:
                                # Update both allowed_ip and name if they exist in the config file
                                update_data = {"allowed_ip": i.get("AllowedIPs", "N/A")}
                                if i.get("name"):
                                    update_data["name"] = i.get("name")
                                self.db.update_peer(i['PublicKey'], update_data)
                                self.Peers.append(Peer(checkIfExist, self))
                except Exception as e:
                    if __name__ == '__main__':
                        logger.error(f"{self.Name} Error: {str(e)}")
        else:
            self.Peers.clear()
            checkIfExist = self.db.get_peers()
            for i in checkIfExist:
                self.Peers.append(Peer(i, self))

    def addPeers(self, peers: list):
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()
        try:
            # First, handle database updates and wg commands
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

                self.db.insert_peer(newPeer)

            # Handle wg commands and config file updates
            config_path = f"/etc/wireguard/{self.Name}.conf"
            for i, p in enumerate(peers):
                logger.debug(f"Adding peer {i+1}/{len(peers)}: {p['id'][:8]}...")
                presharedKeyExist = len(p['preshared_key']) > 0
                rd = random.Random()
                uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))

                # Handle wg command securely
                if presharedKeyExist:
                    with open(uid, "w+") as f:
                        f.write(p['preshared_key'])
                
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
                
                if presharedKeyExist:
                    os.remove(uid)

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

            self.getPeersList()
            return True
        except Exception as e:
            logger.error(f"Error in addPeers: {str(e)}")
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

    def allowAccessPeers(self, listOfPublicKeys):
        try:
            if not self.getStatus():
                self.toggleConfiguration()
            interface_address = self.get_iface_address()
            cmd_prefix = self.get_iface_proto()
            
            for i in listOfPublicKeys:
                # Search in restricted table
                restricted_peers = self.db.get_restricted_peers()
                p = None
                for peer in restricted_peers:
                    if peer.get('id') == i:
                        p = peer
                        break
                
                if p is not None:
                    # Move peer from restricted table
                    if not self.db.move_peer_from_restricted(i):
                        return ResponseObject(False, f"Failed to move peer {i} from restricted table")

                    presharedKeyExist = len(p.get('preshared_key', '')) > 0
                    uid = None
                    
                    try:
                        if presharedKeyExist:
                            rd = random.Random()
                            uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
                            with open(uid, "w+") as f:
                                f.write(p['preshared_key'])

                        # Use secure command execution with fallback
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
                            return ResponseObject(False, f"Failed to execute WireGuard command: {result.get('error', result.get('stderr', 'Unknown error'))}")

                    except subprocess.CalledProcessError as e:
                        return ResponseObject(False, f"Failed to execute WireGuard command: {str(e)}")
                    except Exception as e:
                        return ResponseObject(False, f"Error processing peer {i}: {str(e)}")
                    finally:
                        # Clean up temporary file
                        if presharedKeyExist and uid and os.path.exists(uid):
                            try:
                                os.remove(uid)
                            except Exception as e:
                                logger.warning(f"Failed to remove temporary file {uid}: {e}")
                else:
                    return ResponseObject(False, "Failed to allow access of peer " + i)
                    
            if not self.__wgSave():
                return ResponseObject(False, "Failed to save configuration through WireGuard")

            try_patch = self.patch_iface_address(interface_address)
            if try_patch:
                return try_patch

            self.__getPeers()
            return ResponseObject(True, "Allow access successfully")
            
        except Exception as e:
            logger.error(f"Error in allowAccessPeers: {str(e)}")
            return ResponseObject(False, f"Internal error: {str(e)}")

    def restrictPeers(self, listOfPublicKeys):
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

                    self.db.move_peer_to_restricted(pf.id)
                    # Update status to stopped
                    self.db.update_peer(pf.id, {"status": "stopped"})
                    numOfRestrictedPeers += 1
                except Exception as e:
                    numOfFailedToRestrictPeers += 1

        if not self.__wgSave():
            return ResponseObject(False, "Failed to save configuration through WireGuard")

        try_patch = self.patch_iface_address(interface_address)
        if try_patch:
            return try_patch

        self.__getPeers()

        if numOfRestrictedPeers == len(listOfPublicKeys):
            return ResponseObject(True, f"Restricted {numOfRestrictedPeers} peer(s)")
        return ResponseObject(False,
                              f"Restricted {numOfRestrictedPeers} peer(s) successfully. Failed to restrict {numOfFailedToRestrictPeers} peer(s)")
        pass

    def deletePeers(self, listOfPublicKeys):
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

                    self.db.delete_peer(pf.id)
                    numOfDeletedPeers += 1
                except Exception as e:
                    numOfFailedToDeletePeers += 1

        if not self.__wgSave():
            return ResponseObject(False, "Failed to save configuration through WireGuard")

        try_patch = self.patch_iface_address(interface_address)
        if try_patch:
            return try_patch

        self.__getPeers()

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

    def getPeersLatestHandshake(self):
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
                self.db.update_peer_handshake(latestHandshake[count], str(minus).split(".", maxsplit=1)[0], status)
            else:
                self.db.update_peer_handshake(latestHandshake[count], 'No Handshake', status)
            count += 2

    def getPeersTransfer(self):
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
                    cur_i = self.db.search_peer(data_usage[i][0])
                    if cur_i is not None:
                        total_sent = cur_i['total_sent']
                        total_receive = cur_i['total_receive']
                        cur_total_sent = float(data_usage[i][2]) / (1024 ** 3)
                        cur_total_receive = float(data_usage[i][1]) / (1024 ** 3)
                        cumulative_receive = cur_i['cumu_receive'] + total_receive
                        cumulative_sent = cur_i['cumu_sent'] + total_sent
                        if total_sent <= cur_total_sent and total_receive <= cur_total_receive:
                            total_sent = cur_total_sent
                            total_receive = cur_total_receive
                        else:
                            self.db.update_peer(data_usage[i][0], {
                                'cumu_receive': cumulative_receive,
                                'cumu_sent': cumulative_sent,
                                'cumu_data': cumulative_sent + cumulative_receive
                            })
                            total_sent = 0
                            total_receive = 0
                        _, p = self.searchPeer(data_usage[i][0])
                        if p.total_receive != total_receive or p.total_sent != total_sent:
                            self.db.update_peer_transfer(data_usage[i][0], total_receive, total_sent, total_receive + total_sent)
        except Exception as e:
            logger.error(f"{self.Name} Error: {str(e)} {str(e.__traceback__)}")

    def getPeersEndpoint(self):
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
            self.db.update_peer_endpoint(data_usage[count], data_usage[count + 1])
            count += 2

    def toggleConfiguration(self) -> tuple[bool, str]:
        self.getStatus()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()

        config_file_path = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f"{self.Name}.conf")

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
                return False, str(exc.output.strip().decode("utf-8"))
        self.__parseConfigurationFile()
        self.getStatus()
        return True, None

    def getPeersList(self):
        self.__getPeers()
        return self.Peers

    def getRestrictedPeersList(self) -> list:
        self.__getRestrictedPeers()
        return self.RestrictedPeers

    def toJson(self):
        self.Status = self.getStatus()
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
        }

    def backupConfigurationFile(self):
        """Enhanced backup method that includes all iptables scripts with organized directory structure"""
        try:
            # Generate timestamp for backup files
            time_str = datetime.now().strftime("%Y%m%d%H%M%S")

            # Get organized backup paths
            backup_paths = get_backup_paths(self.Name, time_str)

            # Backup main configuration file
            shutil.copy(self.configPath, backup_paths['conf_file'])

            # Backup database
            with open(backup_paths['redis_file'], 'w+') as f:
                for l in self.__dumpDatabase():
                    f.write(l + "\n")

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
                with open(backup_paths['iptables_file'], 'w') as f:
                    json.dump(scripts_backup, f, indent=2)

            # Return success and backup details
            return True, {
                'filename': backup_paths['conf_file'],
                'database': backup_paths['redis_file'],
                'iptables': backup_paths['iptables_file'] if scripts_backup else None
            }
        except Exception as e:
            logger.error(f"Backup Error: {str(e)}")
            return False, None

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

    def restoreBackup(self, backupFileName: str) -> bool:
        """Enhanced restore method with pre/post up/down scripts"""
        backups = list(map(lambda x: x['filename'], self.getBackups()))
        if backupFileName not in backups:
            return False

        # Backup current state before restore
        self.backupConfigurationFile()
        if self.Status:
            self.toggleConfiguration()

        # Get timestamp from backup filename
        timestamp = backupFileName.split('_')[1].split('.')[0]
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
        self.__parseConfigurationFile()
        self.__dropDatabase()
        self.__importDatabase(backup_paths['redis_file'])
        
        # Force refresh of peers from database after import
        self.__initPeersList()

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
        if self.Status:
            self.toggleConfiguration()
        original = []
        dataChanged = False
        with open(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'), 'r') as f:
            original = f.readlines()
            original = [l.rstrip("\n") for l in original]
            allowEdit = ["Address", "PreUp", "PostUp", "PreDown", "PostDown", "ListenPost", "PrivateKey"]

            start = original.index("[Interface]")
            for line in range(start + 1, len(original)):
                if original[line] == "[Peer]":
                    break
                split = re.split(r'\s*=\s*', original[line], 1)
                if len(split) == 2:
                    key = split[0]
                    value = split[1]
                    if key in allowEdit and key in newData.keys() and value != newData[key]:
                        split[1] = newData[key]
                        original[line] = " = ".join(split)
                        if isinstance(getattr(self, key), bool):
                            setattr(self, key, strToBool(newData[key]))
                        else:
                            setattr(self, key, str(newData[key]))
                        dataChanged = True
                    logger.debug(f"Original line: {original[line]}")
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

        status, msg = self.toggleConfiguration()
        if not status:
            return False, msg
        return True, ""

    def deleteConfiguration(self):
        if self.getStatus():
            self.toggleConfiguration()
        os.remove(self.configPath)
        self.__dropDatabase()
        return True

    def renameConfiguration(self, newConfigurationName) -> tuple[bool, str]:
        if newConfigurationName in Configurations.keys():
            return False, "Configuration name already exist"
        try:
            if self.getStatus():
                self.toggleConfiguration()
            self.db.create_database(newConfigurationName)
            self.db.copy_database_to(newConfigurationName)
            AllPeerJobs.updateJobConfigurationName(self.Name, newConfigurationName)
            shutil.copy(
                self.configPath,
                os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{newConfigurationName}.conf')
            )
            self.deleteConfiguration()
        except Exception as e:
            return False, str(e)
        return True, None

    def getAvailableIP(self, all: bool = False) -> tuple[bool, list[str]] | tuple[bool, None]:
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
        for p in self.getRestrictedPeersList():
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
        """Get real-time traffic usage using ip command only"""
        # Simply use the IP-based method directly
        return self.getRealtimeTrafficFromIp()

    def getRealtimeTrafficFromIp(self):
        """Get real-time traffic data using ip command only"""
        if not self.getStatus():
            return {"sent": 0, "recv": 0}
        
        try:
            # Use the global traffic monitor with no protocol command
            result = TRAFFIC_MONITOR.calculate_rate(self.Name)
            
            # Apply compensation factor to both directions
            if result:
                result["sent"] = round(result["sent"] * 0.591, 3)
                result["recv"] = round(result["recv"] * 1.261, 3)  # Fixed typo in original (01.261)
            
            # Add logging
            logger.debug(f" Interface {self.Name} (from ip) traffic: in={result['recv']}MB/s, out={result['sent']}MB/s, period={result['sample_period']}s")
            
            return {
                "sent": result["recv"],
                "recv": result["sent"]
            }
        except Exception as e:
            logger.error(f"Failed to get real-time traffic from ip: {str(e)}")
            return {"sent": 0, "recv": 0}

    def getRealtimeTrafficFromPeers(self):
        """Get real-time traffic data using ip command only (legacy method name kept for compatibility)"""
        return self.getRealtimeTrafficFromIp()


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
        self.mtu = tableData.get("mtu", 1420)
        self.keepalive = tableData.get("keepalive", 21)
        self.remote_endpoint = tableData.get("remote_endpoint", "N/A")
        self.preshared_key = tableData.get("preshared_key", "")
        self.upload_rate_limit = tableData.get("upload_rate_limit", 0)
        self.download_rate_limit = tableData.get("download_rate_limit", 0)
        self.scheduler_type = tableData.get("scheduler_type", "htb")
        self.jobs: list[PeerJob] = []
        self.ShareLink: list[PeerShareLink] = []
        self.getJobs()
        self.getShareLink()
        

    def toJson(self):
        self.getJobs()
        self.getShareLink()
        return self.__dict__

    def __repr__(self):
        return str(self.toJson())

    def updatePeer(self, name: str, private_key: str,
                   preshared_key: str,
                   dns_addresses: str, allowed_ip: str, endpoint_allowed_ip: str, mtu: int,
                   keepalive: int) -> ResponseObject:
        if not self.configuration.getStatus():
            self.configuration.toggleConfiguration()
        cmd_prefix = self.configuration.get_iface_proto()
        existingAllowedIps = [item for row in list(
            map(lambda x: [q.strip() for q in x.split(',')],
                map(lambda y: y.allowed_ip,
                    list(filter(lambda k: k.id != self.id, self.configuration.getPeersList()))))) for item in row]

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
        if len(private_key) > 0:
            pubKey = GenerateWireguardPublicKey(private_key)
            if not pubKey[0] or pubKey[1] != self.id:
                return ResponseObject(False, "Private key does not match with the public key")
        try:
            rd = random.Random()
            uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
            pskExist = len(preshared_key) > 0

            if pskExist:
                with open(uid, "w+") as f:
                    f.write(preshared_key)
            newAllowedIPs = allowed_ip.replace(" ", "")

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

            if pskExist: os.remove(uid)

            if result['stderr'] and len(result['stderr'].strip()) != 0:
                return ResponseObject(False,
                                      "Update peer failed when updating Allowed IPs")
            
            if cmd_prefix == "awg":
                result = execute_awg_quick_command('save', self.configuration.Name)
            else:
                result = execute_wg_quick_command('save', self.configuration.Name)
            if not result['success']:
                return ResponseObject(False, f"Failed to save configuration: {result.get('error', result.get('stderr', 'Unknown error'))}")

            if f"{cmd_prefix} showconf {self.configuration.Name}" not in result['stdout'].strip():
                return ResponseObject(False,
                                      "Update peer failed when saving the configuration")
            self.configuration.db.update_peer(self.id, {
                'name': name,
                'private_key': private_key,
                'DNS': dns_addresses,
                'endpoint_allowed_ip': endpoint_allowed_ip,
                'mtu': mtu,
                'keepalive': keepalive,
                'preshared_key': preshared_key
            })
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

    def getShareLink(self):
        self.ShareLink = AllPeerShareLinks.getLink(self.configuration.Name, self.id)

    def resetDataUsage(self, type):
        try:
            return self.configuration.db.reset_peer_data_usage(self.id, type)
        except Exception as e:
            return False




_, APP_PREFIX = DashboardConfig.GetConfig("Server", "app_prefix")

def cleanup_orphaned_configurations(existing_config_files: set):
    """
    Clean up database entries for configurations that no longer have corresponding .conf files.
    This handles the edge case where Redis data persists but config files don't (e.g., during development).
    """
    from .DataBase import get_redis_manager
    
    try:
        redis_manager = get_redis_manager()
        
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

def InitWireguardConfigurationsList(startup: bool = False):
    # Check for and migrate SQLite databases on startup
    if startup:
        logger.info("Checking for SQLite databases to migrate...")
        if check_and_migrate_sqlite_databases():
            logger.info("✓ SQLite databases migrated to Redis")
        else:
            logger.info("✓ No SQLite databases found to migrate")
    
    confs = os.listdir(DashboardConfig.GetConfig("Server", "wg_conf_path")[1])
    confs.sort()
    
    # Get list of existing configuration files (without .conf extension)
    existing_config_files = set()
    for i in confs:
        if RegexMatch("^(.{1,}).(conf)$", i):
            existing_config_files.add(i.replace('.conf', ''))
    
    # Clean up database entries for configurations that no longer have files
    if startup:
        cleanup_orphaned_configurations(existing_config_files)
    
    # Load configurations from existing files
    for i in confs:
        if RegexMatch("^(.{1,}).(conf)$", i):
            i = i.replace('.conf', '')
            try:
                if i in Configurations.keys():
                    if Configurations[i].configurationFileChanged():
                        Configurations[i] = Configuration(i)
                        # Don't try to call the private method directly
                else:
                    Configurations[i] = Configuration(i, startup=startup)
                    # Don't try to call the private method directly
            except Configuration.InvalidConfigurationFileException as e:
                logger.error(f"{i} have an invalid configuration file.")

def InitRateLimits():
    """Reapply rate limits for all peers across all interfaces"""
    logger = logging.getLogger('wiregate')
    try:
        for config_name, config in Configurations.items():
            logger.debug(f"Processing rate limits for configuration: {config_name}")
            try:
                # Get all peers with rate limits
                all_peers = config.db.get_peers()
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
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            logger.error(f"Failed to reapply rate limits for peer {peer['id']} on {config.Name}: {result.stderr}")
                        else:
                            logger.debug(f"Successfully applied rate limits for peer {peer['id']} on {config.Name}")
                            
                    except Exception as e:
                        logger.error(f"Error reapplying rate limits for peer {peer['id']} on {config.Name}: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error processing rate limits for configuration {config_name}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error initializing rate limits: {str(e)}")


Configurations: dict[str, Configuration] = {}

def is_kernel_module_loaded(module_name):
    """Check if a specific kernel module is loaded"""
    try:
        result = subprocess.run(['lsmod'], stdout=subprocess.PIPE, text=True)
        return module_name in result.stdout
    except Exception:
        # Fallback to checking /proc/modules
        try:
            with open('/proc/modules', 'r') as f:
                return module_name in f.read()
        except Exception:
            return False

# Add this at the module level (outside any class)
class TrafficMonitor:
    """Traffic rate monitor using raw calculations without statistical smoothing"""
    
    def __init__(self, window_size=3, min_samples=1):
        self.window_size = window_size
        self.min_samples = min_samples
        self.last_measurement = {}  # {interface_name: {'recv': bytes, 'sent': bytes, 'timestamp': time}}
    
    def get_transfer_data(self, interface_name):
        """Get raw transfer data using ip command only"""
        try:
            # Use ip -s link show to get interface statistics directly
            result = execute_ip_command('link_stats', interface_name)
            if not result['success']:
                return None
            output = result['stdout'].encode()
            
            # Parse the output to extract RX/TX bytes
            lines = output.decode("UTF-8").splitlines()
            
            # Find RX and TX statistics sections
            rx_bytes = None
            tx_bytes = None
            
            for i, line in enumerate(lines):
                if "RX:" in line and i+1 < len(lines):
                    # RX bytes is typically the first value on the next line
                    rx_stats = lines[i+1].strip().split()
                    if len(rx_stats) >= 1:
                        try:
                            rx_bytes = int(rx_stats[0])
                        except (ValueError, IndexError):
                            pass
                
                if "TX:" in line and i+1 < len(lines):
                    # TX bytes is typically the first value on the next line
                    tx_stats = lines[i+1].strip().split()
                    if len(tx_stats) >= 1:
                        try:
                            tx_bytes = int(tx_stats[0])
                        except (ValueError, IndexError):
                            pass
            
            # If we successfully parsed both values, return them
            if rx_bytes is not None and tx_bytes is not None:
                return {
                    'recv': rx_bytes, 
                    'sent': tx_bytes,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            # Log the error
            logger.debug(f" Could not get interface stats via ip command: {str(e)}")
        
        # Return empty result if ip command failed
        return {}
    
    def calculate_rate(self, interface_name):
        """Calculate transfer rate using precise time differentials"""
        current_data = self.get_transfer_data(interface_name)
        result = {"sent": 0, "recv": 0, "sample_period": 0}
        
        if interface_name in self.last_measurement and current_data:
            last_data = self.last_measurement[interface_name]
            
            current_time = current_data.get('timestamp', time.time())
            last_time = last_data.get('timestamp', 0)
            time_diff = current_time - last_time
            
            if time_diff > 0:
                recv_diff = current_data['recv'] - last_data['recv']
                sent_diff = current_data['sent'] - last_data['sent']
                
                if recv_diff < 0:
                    recv_diff = current_data['recv']
                if sent_diff < 0:
                    sent_diff = current_data['sent']
                
                bytes_in_per_sec = recv_diff / time_diff
                bytes_out_per_sec = sent_diff / time_diff
                
                result = {
                    "sent": round((bytes_out_per_sec * 8) / 1_000_000, 3),  # Mbps
                    "recv": round((bytes_in_per_sec * 8) / 1_000_000, 3),   # Mbps
                    "sample_period": round(time_diff, 3)
                }
        
        self.last_measurement[interface_name] = current_data
        return result
    
# Create a single instance at module level with larger window for better statistics
TRAFFIC_MONITOR = TrafficMonitor(window_size=15, min_samples=3)
