import random, shutil, configparser, psutil
import os, subprocess, uuid, datetime, time
import ipaddress, json, re, sqlite3
import logging

from datetime import datetime, timedelta
 
from .DashboardConfig import DashboardConfig
from .Utilities import (
    StringToBoolean, ValidateIPAddressesWithRange,
    ValidateDNSAddress, RegexMatch, strToBool,
    GenerateWireguardPublicKey, get_backup_paths
)
from .App import (
    ResponseObject
)


from .Jobs.PeerJobLogger import PeerJobLogger
from .Jobs.PeerJob import PeerJob
from .Jobs.PeerJobs import PeerJobs
from .Locale.Locale import Locale

from .Share.ShareLink import PeerShareLinks
from .Share.ShareLink import PeerShareLink
from .DataBase.DataBaseManager import (
    DatabaseManager, sqlSelect, sqlUpdate, sqldb
)


from .Share.ShareLink import AllPeerShareLinks
from .Jobs.PeerJobs import AllPeerJobs




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

        if name is not None:
            if data is not None and "Backup" in data.keys():
                db = self.__importDatabase(
                    os.path.join(
                        DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                        'WGDashboard_Backup',
                        data["Backup"].replace(".conf", ".sql")))
            else:
                self.__createDatabase()
                # Ensure migration happens right after database creation
                self.__migrateDatabase()

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
                self.__createDatabase()
                # Ensure migration happens here too
                self.__migrateDatabase()
                with open(self.configPath, "w+") as configFile:
                    self.__parser.write(configFile)
                self.__initPeersList()

        print(f"[WireGate] Initialized Configuration: {name}")
        if self.getAutostartStatus() and not self.getStatus() and startup:
            self.toggleConfiguration()
            print(f"[WireGate] Autostart Configuration: {name}")

        #if startup:
        #    self.reapply_rate_limits()

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
            print(f"Restore status: {restoreStatus}")
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
        existingTables = sqlSelect(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{self.Name}%'").fetchall()
        for t in existingTables:
            sqlUpdate("DROP TABLE '%s'" % t['name'])

        existingTables = sqlSelect(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{self.Name}%'").fetchall()

    def __createDatabase(self, dbName=None):
        if dbName is None:
            dbName = self.Name

        existingTables = sqlSelect("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        existingTables = [t['name'] for t in existingTables]
        if dbName not in existingTables:
            sqlUpdate(
                """
                CREATE TABLE IF NOT EXISTS '%s'(
                    id VARCHAR NOT NULL, 
                    private_key VARCHAR NULL, 
                    DNS VARCHAR NULL, 
                    endpoint_allowed_ip VARCHAR NULL, 
                    name VARCHAR NULL, 
                    total_receive FLOAT NULL, 
                    total_sent FLOAT NULL, 
                    total_data FLOAT NULL, 
                    endpoint VARCHAR NULL, 
                    status VARCHAR NULL, 
                    latest_handshake VARCHAR NULL, 
                    allowed_ip VARCHAR NULL,  
                    cumu_receive FLOAT NULL, 
                    cumu_sent FLOAT NULL, 
                    cumu_data FLOAT NULL, 
                    mtu INT NULL, 
                    keepalive INT NULL, 
                    remote_endpoint VARCHAR NULL, 
                    preshared_key VARCHAR NULL,
                    address_v4 VARCHAR NULL,  
                    address_v6 VARCHAR NULL,
                    upload_rate_limit INTEGER DEFAULT 0,
                    download_rate_limit INTEGER DEFAULT 0,
                    scheduler_type TEXT CHECK(scheduler_type IN ('htb', 'hfsc') OR scheduler_type IS NULL),
                    PRIMARY KEY (id)
                )
                """ % dbName
            )

        # Create other tables with similar updates...

        if f'{dbName}_restrict_access' not in existingTables:
            sqlUpdate(
                """
                CREATE TABLE '%s_restrict_access' (
                    id VARCHAR NOT NULL, private_key VARCHAR NULL, DNS VARCHAR NULL, 
                    endpoint_allowed_ip VARCHAR NULL, name VARCHAR NULL, total_receive FLOAT NULL, 
                    total_sent FLOAT NULL, total_data FLOAT NULL, endpoint VARCHAR NULL, 
                    status VARCHAR NULL, latest_handshake VARCHAR NULL, allowed_ip VARCHAR NULL, 
                    cumu_receive FLOAT NULL, cumu_sent FLOAT NULL, cumu_data FLOAT NULL, mtu INT NULL, 
                    keepalive INT NULL, remote_endpoint VARCHAR NULL, preshared_key VARCHAR NULL,
                    address_v4 VARCHAR NULL,  
                    address_v6 VARCHAR NULL,
                    upload_rate_limit INTEGER DEFAULT 0,
                    download_rate_limit INTEGER DEFAULT 0,
                    scheduler_type TEXT CHECK(scheduler_type IN ('htb', 'hfsc') OR scheduler_type IS NULL),
                    PRIMARY KEY (id)
                )
                """ % dbName
            )
        if f'{dbName}_transfer' not in existingTables:
            sqlUpdate(
                """
                CREATE TABLE '%s_transfer' (
                    id VARCHAR NOT NULL, total_receive FLOAT NULL,
                    total_sent FLOAT NULL, total_data FLOAT NULL,
                    cumu_receive FLOAT NULL, cumu_sent FLOAT NULL, cumu_data FLOAT NULL, time DATETIME
                )
                """ % dbName
            )
        if f'{dbName}_deleted' not in existingTables:
            sqlUpdate(
                """
                CREATE TABLE '%s_deleted' (
                    id VARCHAR NOT NULL, private_key VARCHAR NULL, DNS VARCHAR NULL, 
                    endpoint_allowed_ip VARCHAR NULL, name VARCHAR NULL, total_receive FLOAT NULL, 
                    total_sent FLOAT NULL, total_data FLOAT NULL, endpoint VARCHAR NULL, 
                    status VARCHAR NULL, latest_handshake VARCHAR NULL, allowed_ip VARCHAR NULL, 
                    cumu_receive FLOAT NULL, cumu_sent FLOAT NULL, cumu_data FLOAT NULL, mtu INT NULL, 
                    keepalive INT NULL, remote_endpoint VARCHAR NULL, preshared_key VARCHAR NULL,
                    address_v4 VARCHAR NULL,  
                    address_v6 VARCHAR NULL,
                    upload_rate_limit INTEGER DEFAULT 0,
                    download_rate_limit INTEGER DEFAULT 0,
                    scheduler_type TEXT CHECK(scheduler_type IN ('htb', 'hfsc') OR scheduler_type IS NULL),
                    PRIMARY KEY (id)
                )
                """ % dbName
            )

    def __migrateDatabase(self):
        """Add missing columns to existing tables if they don't exist"""
        tables = [self.Name, f"{self.Name}_restrict_access", f"{self.Name}_deleted"]
        columns = {
            'address_v4': 'VARCHAR NULL',
            'address_v6': 'VARCHAR NULL', 
            'upload_rate_limit': 'INTEGER DEFAULT 0',
            'download_rate_limit': 'INTEGER DEFAULT 0',
            'scheduler_type': "TEXT CHECK(scheduler_type IN ('htb', 'hfsc') OR scheduler_type IS NULL)"
        }

        for table in tables:
            # Check if table exists first
            table_exists = sqlSelect(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
            if not table_exists:
                print(f"[WireGate] Table {table} does not exist, skipping migration")
                continue
                
            # Get current columns for the table
            try:
                cursor = sqlSelect(f"PRAGMA table_info('{table}')")
                existing_columns = [row['name'] for row in cursor.fetchall()]
                
                for column, type_def in columns.items():
                    if column not in existing_columns:
                        try:
                            # Add missing column
                            sqlUpdate(f"ALTER TABLE '{table}' ADD COLUMN {column} {type_def}")
                            print(f"[WireGate] Added {column} to {table}")
                        except sqlite3.OperationalError as e:
                            print(f"[WireGate] Error adding {column} to {table}: {e}")
            except sqlite3.OperationalError as e:
                print(f"[WireGate] Error checking columns for table {table}: {e}")

    def __dumpDatabase(self):
        for line in sqldb.iterdump():
            if (line.startswith(f"INSERT INTO \"{self.Name}\"")
                    or line.startswith(f'INSERT INTO "{self.Name}_restrict_access"')
                    or line.startswith(f'INSERT INTO "{self.Name}_transfer"')
                    or line.startswith(f'INSERT INTO "{self.Name}_deleted"')
            ):
                yield line

    def __importDatabase(self, sqlFilePath) -> bool:
        self.__dropDatabase()
        self.__createDatabase()
        self.__migrateDatabase()  # Add this line to ensure columns exist
        if not os.path.exists(sqlFilePath):
            return False

        with open(sqlFilePath, 'r') as f:
            for l in f.readlines():
                l = l.rstrip("\n")
                if len(l) > 0:
                    # Split addresses into v4 and v6 parts before insert
                    if "INSERT INTO" in l:
                        try:
                            # Parse out address values
                            addresses = re.search(r"Address\s*=\s*'([^']*)'", l)
                            if addresses:
                                addr_parts = addresses.group(1).split(',')
                                addr_v4 = []
                                addr_v6 = []
                                for addr in addr_parts:
                                    addr = addr.strip()
                                    if ':' in addr:  # IPv6
                                        addr_v6.append(addr)
                                    else:  # IPv4
                                        addr_v4.append(addr)

                                # Replace original address with split version
                                l = l.replace(
                                    f"Address = '{addresses.group(1)}'",
                                    f"address_v4 = '{','.join(addr_v4)}', address_v6 = '{','.join(addr_v6)}'"
                                )
                        except Exception as e:
                            print(f"Error parsing addresses: {e}")

                    sqlUpdate(l)
        return True

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
        restricted = sqlSelect("SELECT * FROM '%s_restrict_access'" % self.Name).fetchall()
        for i in restricted:
            self.RestrictedPeers.append(Peer(i, self))

    def configurationFileChanged(self):
        mt = os.path.getmtime(os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f'{self.Name}.conf'))
        changed = self.__configFileModifiedTime is None or self.__configFileModifiedTime != mt
        self.__configFileModifiedTime = mt
        return changed

    def __getPeers(self):
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
                            checkIfExist = sqlSelect("SELECT * FROM '%s' WHERE id = ?" % self.Name,
                                                     ((i['PublicKey']),)).fetchone()
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
                                sqlUpdate(
                                    """
                                    INSERT INTO '%s'
                                        VALUES (:id, :private_key, :DNS, :endpoint_allowed_ip, :name, :total_receive, :total_sent, 
                                        :total_data, :endpoint, :status, :latest_handshake, :allowed_ip, :cumu_receive, :cumu_sent, 
                                        :cumu_data, :mtu, :keepalive, :remote_endpoint, :preshared_key, :address_v4, :address_v6, 
                                        :upload_rate_limit, :download_rate_limit, :scheduler_type);
                                    """ % self.Name, newPeer)
                                self.Peers.append(Peer(newPeer, self))
                            else:
                                sqlUpdate("UPDATE '%s' SET allowed_ip = ? WHERE id = ?" % self.Name,
                                          (i.get("AllowedIPs", "N/A"), i['PublicKey'],))
                                self.Peers.append(Peer(checkIfExist, self))
                except Exception as e:
                    if __name__ == '__main__':
                        print(f"[WireGate] {self.Name} Error: {str(e)}")
        else:
            self.Peers.clear()
            checkIfExist = sqlSelect("SELECT * FROM '%s'" % self.Name).fetchall()
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

                sqlUpdate(
                    """
                    INSERT INTO '%s'
                    VALUES (:id, :private_key, :DNS, :endpoint_allowed_ip, :name, :total_receive, :total_sent,
                    :total_data, :endpoint, :status, :latest_handshake, :allowed_ip, :cumu_receive, :cumu_sent,
                    :cumu_data, :mtu, :keepalive, :remote_endpoint, :preshared_key, :address_v4, :address_v6, 
                    :upload_rate_limit, :download_rate_limit, :scheduler_type);
                    """ % self.Name, newPeer)

            # Handle wg commands and config file updates
            config_path = f"/etc/wireguard/{self.Name}.conf"
            for p in peers:
                presharedKeyExist = len(p['preshared_key']) > 0
                rd = random.Random()
                uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))

                # Handle wg command
                if presharedKeyExist:
                    with open(uid, "w+") as f:
                        f.write(p['preshared_key'])
                cmd = (
                    f"{cmd_prefix} set {self.Name} peer {p['id']} allowed-ips {p['allowed_ip'].replace(' ', '')}{f' preshared-key {uid}' if presharedKeyExist else ''}")
                subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
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
            cmd = (f"{cmd_prefix}-quick save {self.Name}")
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            try_patch = self.patch_iface_address(interface_address)
            if try_patch:
                return try_patch

            self.getPeersList()
            return True
        except Exception as e:
            print(str(e))
            return False

    def searchPeer(self, publicKey):
        for i in self.Peers:
            if i.id == publicKey:
                return True, i
        return False, None

    def allowAccessPeers(self, listOfPublicKeys):
        if not self.getStatus():
            self.toggleConfiguration()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()
        for i in listOfPublicKeys:
            p = sqlSelect("SELECT * FROM '%s_restrict_access' WHERE id = ?" % self.Name, (i,)).fetchone()
            if p is not None:
                sqlUpdate("INSERT INTO '%s' SELECT * FROM %s_restrict_access WHERE id = ?"
                          % (self.Name, self.Name,), (p['id'],))
                sqlUpdate("DELETE FROM '%s_restrict_access' WHERE id = ?"
                          % self.Name, (p['id'],))

                presharedKeyExist = len(p['preshared_key']) > 0
                rd = random.Random()
                uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
                if presharedKeyExist:
                    with open(uid, "w+") as f:
                        f.write(p['preshared_key'])

                cmd = (
                    f"{cmd_prefix} set {self.Name} peer {p['id']} allowed-ips {p['allowed_ip'].replace(' ', '')}{f' preshared-key {uid}' if presharedKeyExist else ''}")
                subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

                if presharedKeyExist: os.remove(uid)
            else:
                return ResponseObject(False, "Failed to allow access of peer " + i)
        if not self.__wgSave():
            return ResponseObject(False, "Failed to save configuration through WireGuard")

        try_patch = self.patch_iface_address(interface_address)
        if try_patch:
            return try_patch

        self.__getPeers()
        return ResponseObject(True, "Allow access successfully")

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

                    cmd = (f"{cmd_prefix} set {self.Name} peer {pf.id} remove")
                    subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

                    sqlUpdate("INSERT INTO '%s_restrict_access' SELECT * FROM %s WHERE id = ?" %
                              (self.Name, self.Name,), (pf.id,))
                    sqlUpdate("UPDATE '%s_restrict_access' SET status = 'stopped' WHERE id = ?" %
                              (self.Name,), (pf.id,))
                    sqlUpdate("DELETE FROM '%s' WHERE id = ?" % self.Name, (pf.id,))
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
                    cmd = (f"{cmd_prefix} set {self.Name} peer {pf.id} remove")
                    subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

                    sqlUpdate("DELETE FROM '%s' WHERE id = ?" % self.Name, (pf.id,))
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
            print(f"Error while parsing interface config: {e}")
            return None

    def get_iface_address(self):
        try:
            # Fetch both inet (IPv4) and inet6 (IPv6) addresses
            ipv4_address = subprocess.check_output(
                f"ip addr show {self.Name} | awk '/inet /{{print $2}}'", shell=True
            ).decode().strip()

            # Capture all IPv6 addresses (link-local and global)
            ipv6_addresses = subprocess.check_output(
                f"ip addr show {self.Name} | awk '/inet6 /{{print $2}}'", shell=True
            ).decode().splitlines()

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
            config_path = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f"{self.Name}.conf")
            with open(config_path, "r") as conf_file:
                lines = conf_file.readlines()

            # Locate the [Interface] section and the Address line
            interface_index = next((i for i, line in enumerate(lines) if line.strip() == "[Interface]"), None)
            address_line_index = next((i for i, line in enumerate(lines) if line.strip().startswith("Address")), None)

            # Create the new Address line with both IPv4 and IPv6 addresses
            address_line = f"Address = {interface_address}\n"

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

        except IOError:
            return ResponseObject(False, "Failed to write the interface address to the config file")

    def __wgSave(self) -> tuple[bool, str] | tuple[bool, None]:
        cmd_prefix = self.get_iface_proto()
        try:
            # Build cmd string based off of interface protocol
            cmd = (f"{cmd_prefix}-quick save {self.Name}")
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

            return True, None
        except subprocess.CalledProcessError as e:
            return False, str(e)

    def getPeersLatestHandshake(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            cmd = (f"{cmd_prefix} show {self.Name} latest-handshakes")
            latestHandshake = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError:
            return "stopped"
        latestHandshake = latestHandshake.decode("UTF-8").split()
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
                sqlUpdate("UPDATE '%s' SET latest_handshake = ?, status = ? WHERE id= ?" % self.Name
                          , (str(minus).split(".", maxsplit=1)[0], status, latestHandshake[count],))
            else:
                sqlUpdate("UPDATE '%s' SET latest_handshake = 'No Handshake', status = ? WHERE id= ?" % self.Name
                          , (status, latestHandshake[count],))
            count += 2

    def getPeersTransfer(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            cmd = (f"{cmd_prefix} show {self.Name} transfer")
            data_usage = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

            data_usage = data_usage.decode("UTF-8").split("\n")
            data_usage = [p.split("\t") for p in data_usage]
            for i in range(len(data_usage)):
                if len(data_usage[i]) == 3:
                    cur_i = sqlSelect(
                        "SELECT total_receive, total_sent, cumu_receive, cumu_sent, status FROM '%s' WHERE id= ? "
                        % self.Name, (data_usage[i][0],)).fetchone()
                    if cur_i is not None:
                        cur_i = dict(cur_i)
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
                            sqlUpdate(
                                "UPDATE '%s' SET cumu_receive = ?, cumu_sent = ?, cumu_data = ? WHERE id = ?" %
                                self.Name, (cumulative_receive, cumulative_sent,
                                            cumulative_sent + cumulative_receive,
                                            data_usage[i][0],))
                            total_sent = 0
                            total_receive = 0
                        _, p = self.searchPeer(data_usage[i][0])
                        if p.total_receive != total_receive or p.total_sent != total_sent:
                            sqlUpdate(
                                "UPDATE '%s' SET total_receive = ?, total_sent = ?, total_data = ? WHERE id = ?"
                                % self.Name, (total_receive, total_sent,
                                              total_receive + total_sent, data_usage[i][0],))
        except Exception as e:
            print(f"[WireGate] {self.Name} Error: {str(e)} {str(e.__traceback__)}")

    def getPeersEndpoint(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            # Build cmd string based off of interface protocol
            cmd_prefix = self.get_iface_proto()
            cmd = (f"{cmd_prefix} show {self.Name} endpoints")
            data_usage = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError:
            return "stopped"
        data_usage = data_usage.decode("UTF-8").split()
        count = 0
        for _ in range(int(len(data_usage) / 2)):
            sqlUpdate("UPDATE '%s' SET endpoint = ? WHERE id = ?" % self.Name
                      , (data_usage[count + 1], data_usage[count],))
            count += 2

    def toggleConfiguration(self) -> tuple[bool, str]:
        self.getStatus()
        interface_address = self.get_iface_address()
        cmd_prefix = self.get_iface_proto()

        config_file_path = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], f"{self.Name}.conf")

        if self.Status:
            try:

                cmd = (f"{cmd_prefix}-quick down {self.Name}")
                check = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                # check = subprocess.check_output(f"wg-quick down {self.Name}",
                #                                shell=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as exc:
                return False, str(exc.output.strip().decode("utf-8"))

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
                    # Bring the WireGuard interface up
                    cmd = (f"{cmd_prefix}-quick up {self.Name}")
                    check = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                    # check = subprocess.check_output(f"wg-quick up {self.Name}",
                    #                                shell=True, stderr=subprocess.STDOUT)

                    try:
                        # Remove any existing IPv6 addresses for the interface
                        remove_ipv6_cmd = f"ip -6 addr flush dev {self.Name}"
                        subprocess.check_output(remove_ipv6_cmd, shell=True, stderr=subprocess.STDOUT)

                        # Add the new IPv6 address with the desired parameters
                        add_ipv6_cmd = f"ip -6 addr add {ipv6_address} dev {self.Name}"
                        subprocess.check_output(add_ipv6_cmd, shell=True, stderr=subprocess.STDOUT)
                    except subprocess.CalledProcessError as exc:
                        return False, str(exc.output.strip().decode("utf-8"))
                else:
                    # No IPv6 address found, just bring the interface up without modifying IPv6
                    cmd = (f"{cmd_prefix}-quick up {self.Name}")
                    check = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                    # check = subprocess.check_output(f"wg-quick up {self.Name}",
                    #                                shell=True, stderr=subprocess.STDOUT)
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
            with open(backup_paths['sql_file'], 'w+') as f:
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
                    script_file = os.path.join("./iptable-rules", f"{self.Name}-{script_name}.sh")
                    if os.path.exists(script_file):
                        with open(script_file, 'r') as f:
                            scripts_backup[f"{script_key}_script"] = f.read()

            # Save iptables scripts content if any exist
            if scripts_backup:
                with open(backup_paths['iptables_file'], 'w') as f:
                    json.dump(scripts_backup, f, indent=2)

            # Return success and backup details
            return True, {
                'filename': backup_paths['conf_file'],
                'database': backup_paths['sql_file'],
                'iptables': backup_paths['iptables_file'] if scripts_backup else None
            }
        except Exception as e:
            print(f"[WireGate] Backup Error: {str(e)}")
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
                sql_file = f.replace(".conf", ".sql")
                if os.path.exists(os.path.join(backup_paths['config_dir'], sql_file)):
                    d['database'] = True
                    if databaseContent:
                        d['databaseContent'] = open(os.path.join(backup_paths['config_dir'], sql_file), 'r').read()

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
        self.__importDatabase(backup_paths['sql_file'])
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

                rules_dir = "./iptable-rules"
                os.makedirs(rules_dir, exist_ok=True)

                # Process each script
                for script_key, script_type in script_files.items():
                    if script_key in scripts and scripts[script_key]:  # Check if script exists and is not empty
                        script_path = os.path.join(rules_dir, f"{self.Name}-{script_type}.sh")
                        print(f"Restoring {script_key} to {script_path}")  # Debug log

                        with open(script_path, 'w') as f:
                            f.write(scripts[script_key])
                        os.chmod(script_path, 0o755)

            except Exception as e:
                print(f"Warning: Failed to restore iptables scripts: {e}")
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
                backup_paths['sql_file'],
                backup_paths['iptables_file'],

                # Handle potential uploaded backup files
                os.path.join(backup_paths['config_dir'], backupFileName),
                os.path.join(backup_paths['config_dir'], backupFileName.replace('.conf', '.sql')),
                os.path.join(backup_paths['config_dir'], backupFileName.replace('.conf', '_iptables.json'))
            ]

            # Delete all existing files
            for file_path in files_to_delete:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[WireGate] Deleted backup file: {file_path}")

            # Clean up empty config directory
            try:
                if os.path.exists(backup_paths['config_dir']):
                    if not os.listdir(backup_paths['config_dir']):
                        os.rmdir(backup_paths['config_dir'])
                        print(f"[WireGate] Removed empty backup directory: {backup_paths['config_dir']}")
            except OSError as e:
                # Directory not empty or other OS error, log but continue
                print(f"[WireGate] Note: Could not remove backup directory: {str(e)}")
                pass

        except Exception as e:
            print(f"[WireGate] Error deleting backup files: {str(e)}")
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
                    print(original[line])
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
            self.__createDatabase(newConfigurationName)
            sqlUpdate(f'INSERT INTO "{newConfigurationName}" SELECT * FROM "{self.Name}"')
            sqlUpdate(
                f'INSERT INTO "{newConfigurationName}_restrict_access" SELECT * FROM "{self.Name}_restrict_access"')
            sqlUpdate(f'INSERT INTO "{newConfigurationName}_deleted" SELECT * FROM "{self.Name}_deleted"')
            sqlUpdate(f'INSERT INTO "{newConfigurationName}_transfer" SELECT * FROM "{self.Name}_transfer"')
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
        
        print(f"[DEBUG] getAvailableIP for {self.Name} (all={all})")
        address = self.Address.split(',')
        print(f"[DEBUG] Interface addresses: {address}")
        
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
                        print(f"[DEBUG] Added peer {p.name} ({p.id[:8]}...) IP: {ip} (v{ip.version})")
                    except ValueError as error:
                        print(f"[WireGate] Error: {self.Name} peer {p.id} have invalid ip")
        
        # Collect restricted peer addresses
        for p in self.getRestrictedPeersList():
            if len(p.allowed_ip) > 0:
                add = p.allowed_ip.split(',')
                for i in add:
                    a, c = i.split('/')
                    ip = ipaddress.ip_address(a.replace(" ", ""))
                    existedAddress.append(ip)
                    print(f"[DEBUG] Added restricted peer {p.id[:8]}... IP: {ip} (v{ip.version})")
        
        # Add interface addresses to excluded list
        for i in address:
            addressSplit, cidr = i.split('/')
            ip = ipaddress.ip_address(addressSplit.replace(" ", ""))
            existedAddress.append(ip)
            print(f"[DEBUG] Added interface IP: {ip} (v{ip.version})")
        
        # Find available addresses in each network
        for i in address:
            network = ipaddress.ip_network(i.replace(" ", ""), False)
            print(f"[DEBUG] Processing network: {network} (v{network.version})")
            
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
                            print(f"[DEBUG] Available IPv6: {h} (#{ipv6_count})")
                    
                    if not all:
                        if network.version == 6 and count > 255:
                            print(f"[DEBUG] Reached IPv6 limit (255) for network {network}")
                            break
            
            print(f"[DEBUG] Found {count} available IPs in network {network}")
            if network.version == 6:
                print(f"[DEBUG] Found {ipv6_count} available IPv6 addresses")
        
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
                print(f"[DEBUG] Invalid IP address in results: {addr}")
        
        print(f"[DEBUG] Total available addresses: {len(availableAddress)}")
        print(f"[DEBUG] IPv4 addresses: {len(ipv4_addresses)}")
        print(f"[DEBUG] IPv6 addresses: {len(ipv6_addresses)}")
        
        # Print sample of returned addresses
        if ipv4_addresses:
            print(f"[DEBUG] Sample IPv4 addresses: {ipv4_addresses[:5]}")
        if ipv6_addresses:
            print(f"[DEBUG] Sample IPv6 addresses: {ipv6_addresses[:5]}")
            
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
            print(f"[DEBUG] Interface {self.Name} (from ip) traffic: in={result['recv']}MB/s, out={result['sent']}MB/s, period={result['sample_period']}s")
            
            return {
                "sent": result["recv"],
                "recv": result["sent"]
            }
        except Exception as e:
            print(f"[ERROR] Failed to get real-time traffic from ip: {str(e)}")
            return {"sent": 0, "recv": 0}

    def getRealtimeTrafficFromPeers(self):
        """Get real-time traffic data using ip command only (legacy method name kept for compatibility)"""
        return self.getRealtimeTrafficFromIp()


class Peer:
    def __init__(self, tableData, configuration: Configuration):
        self.configuration = configuration
        self.id = tableData["id"]
        self.private_key = tableData["private_key"]
        self.DNS = tableData["DNS"]
        self.endpoint_allowed_ip = tableData["endpoint_allowed_ip"]
        self.name = tableData["name"]
        self.total_receive = tableData["total_receive"]
        self.total_sent = tableData["total_sent"]
        self.total_data = tableData["total_data"]
        self.endpoint = tableData["endpoint"]
        self.status = tableData["status"]
        self.latest_handshake = tableData["latest_handshake"]
        self.allowed_ip = tableData["allowed_ip"]
        self.cumu_receive = tableData["cumu_receive"]
        self.cumu_sent = tableData["cumu_sent"]
        self.cumu_data = tableData["cumu_data"]
        self.mtu = tableData["mtu"]
        self.keepalive = tableData["keepalive"]
        self.remote_endpoint = tableData["remote_endpoint"]
        self.preshared_key = tableData["preshared_key"]
        self.upload_rate_limit = tableData["upload_rate_limit"]
        self.download_rate_limit = tableData["download_rate_limit"]
        self.scheduler_type = tableData["scheduler_type"]
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

            cmd = (
                    f"{cmd_prefix} set {self.configuration.Name} peer {self.id} allowed-ips {newAllowedIPs} {f' preshared-key {uid}' if pskExist else 'preshared-key /dev/null'}")
            updateAllowedIp = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

            if pskExist: os.remove(uid)

            if len(updateAllowedIp.decode().strip("\n")) != 0:
                return ResponseObject(False,
                                      "Update peer failed when updating Allowed IPs")
            
            cmd = (
                    f"{cmd_prefix}-quick save {self.configuration.Name}")
            saveConfig = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

            if f"{cmd_prefix} showconf {self.configuration.Name}" not in saveConfig.decode().strip('\n'):
                return ResponseObject(False,
                                      "Update peer failed when saving the configuration")
            sqlUpdate(
                '''UPDATE '%s' SET name = ?, private_key = ?, DNS = ?, endpoint_allowed_ip = ?, mtu = ?, 
                keepalive = ?, preshared_key = ? WHERE id = ?''' % self.configuration.Name,
                (name, private_key, dns_addresses, endpoint_allowed_ip, mtu,
                 keepalive, preshared_key, self.id,)
            )
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

    def getJobs(self):
        self.jobs = AllPeerJobs.searchJob(self.configuration.Name, self.id)

    def getShareLink(self):
        self.ShareLink = AllPeerShareLinks.getLink(self.configuration.Name, self.id)

    def resetDataUsage(self, type):
        try:
            if type == "total":
                sqlUpdate(
                    "UPDATE '%s' SET total_data = 0, cumu_data = 0, total_receive = 0, cumu_receive = 0, total_sent = 0, cumu_sent = 0  WHERE id = ?" % self.configuration.Name,
                    (self.id,))
            elif type == "receive":
                sqlUpdate("UPDATE '%s' SET total_receive = 0, cumu_receive = 0 WHERE id = ?" % self.configuration.Name,
                          (self.id,))
            elif type == "sent":
                sqlUpdate("UPDATE '%s' SET total_sent = 0, cumu_sent = 0 WHERE id = ?" % self.configuration.Name,
                          (self.id,))
            else:
                return False
        except Exception as e:
            return False
        return True




_, APP_PREFIX = DashboardConfig.GetConfig("Server", "app_prefix")

def InitWireguardConfigurationsList(startup: bool = False):
    confs = os.listdir(DashboardConfig.GetConfig("Server", "wg_conf_path")[1])
    confs.sort()
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
                print(f"{i} have an invalid configuration file.")

def InitRateLimits():
    """Reapply rate limits for all peers across all interfaces"""
    logger = logging.getLogger('wiregate')
    try:
        for config_name, config in Configurations.items():
            logger.debug(f"Processing rate limits for configuration: {config_name}")
            try:
                # Get all peers with rate limits
                rate_limited_peers = sqlSelect(
                    "SELECT id, upload_rate_limit, download_rate_limit, scheduler_type, allowed_ip FROM '%s' WHERE upload_rate_limit > 0 OR download_rate_limit > 0" % config.Name
                ).fetchall()
                
                logger.debug(f"Found {len(rate_limited_peers)} rate-limited peers for {config_name}")
                
                for peer in rate_limited_peers:
                    try:
                        # Skip if missing required data
                        if not peer['id'] or not peer['allowed_ip']:
                            logger.warning(f"Skipping peer {peer['id']} - missing required data")
                            continue
                            
                        # Execute traffic-weir command to reapply limits
                        cmd = [
                            './traffic-weir',
                            '-interface', config.Name,
                            '-peer', peer['id'],
                            '-upload-rate', str(peer['upload_rate_limit'] or 0),
                            '-download-rate', str(peer['download_rate_limit'] or 0),
                            '-protocol', config.Protocol,
                            '-scheduler', peer['scheduler_type'] or 'htb',
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
            cmd = f"ip -s link show {interface_name}"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=2)
            
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
            print(f"[DEBUG] Could not get interface stats via ip command: {str(e)}")
        
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
