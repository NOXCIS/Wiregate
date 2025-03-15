import os, re, sqlite3

from ..ConfigEnv import (
    CONFIGURATION_PATH,
    DB_PATH
)

# Create DB directory if it doesn't exist
if not os.path.isdir(DB_PATH):
    os.mkdir(DB_PATH)

# Database connection
sqldb = sqlite3.connect(os.path.join(CONFIGURATION_PATH, 'db', 'wgdashboard.db'), check_same_thread=False)
sqldb.row_factory = sqlite3.Row
cursor = sqldb.cursor()

def sqlSelect(statement: str, paramters: tuple = ()) -> sqlite3.Cursor:
    with sqldb:
        try:
            cursor = sqldb.cursor()
            return cursor.execute(statement, paramters)

        except sqlite3.OperationalError as error:
            print("[WGDashboard] SQLite Error:" + str(error) + " | Statement: " + statement)
            return []


def sqlUpdate(statement: str, paramters: tuple = ()) -> sqlite3.Cursor:
    with sqldb:
        cursor = sqldb.cursor()
        try:
            statement = statement.rstrip(';')
            s = f'BEGIN TRANSACTION;{statement};END TRANSACTION;'
            cursor.execute(statement, paramters)
            sqldb.commit()
        except sqlite3.OperationalError as error:
            print("[WGDashboard] SQLite Error:" + str(error) + " | Statement: " + statement)




class DatabaseManager:
    def __init__(self, config_name: str):
        self.config_name = config_name

    def __drop_database(self):
        """Drop all tables related to this configuration"""
        existing_tables = sqlSelect(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{self.config_name}%'").fetchall()
        for t in existing_tables:
            sqlUpdate("DROP TABLE '%s'" % t['name'])

    def __create_database(self, db_name=None):
        """Create all necessary tables for this configuration"""
        if db_name is None:
            db_name = self.config_name

        existing_tables = sqlSelect("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        existing_tables = [t['name'] for t in existing_tables]
        
        # Create main peers table
        if db_name not in existing_tables:
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
                """ % db_name
            )

        # Create other tables
        if f'{db_name}_restrict_access' not in existing_tables:
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
                """ % db_name
            )
        
        # ... create other tables similarly ...

    def __migrate_database(self):
        """Add missing columns to existing tables"""
        tables = [self.config_name, f"{self.config_name}_restrict_access", f"{self.config_name}_deleted"]
        columns = {
            'address_v4': 'VARCHAR NULL',
            'address_v6': 'VARCHAR NULL', 
            'upload_rate_limit': 'INTEGER DEFAULT 0',
            'download_rate_limit': 'INTEGER DEFAULT 0',
            'scheduler_type': "TEXT CHECK(scheduler_type IN ('htb', 'hfsc') OR scheduler_type IS NULL)"
        }

        for table in tables:
            try:
                cursor = sqlSelect(f"PRAGMA table_info('{table}')")
                existing_columns = [row['name'] for row in cursor.fetchall()]
                
                for column, type_def in columns.items():
                    if column not in existing_columns:
                        try:
                            sqlUpdate(f"ALTER TABLE '{table}' ADD COLUMN {column} {type_def}")
                        except sqlite3.OperationalError as e:
                            print(f"Error adding {column} to {table}: {e}")
            except sqlite3.OperationalError as e:
                print(f"Error checking columns for table {table}: {e}")

    def __dump_database(self):
        """Dump database content for backup"""
        for line in sqldb.iterdump():
            if (line.startswith(f"INSERT INTO \"{self.config_name}\"") or
                line.startswith(f'INSERT INTO "{self.config_name}_restrict_access"') or
                line.startswith(f'INSERT INTO "{self.config_name}_transfer"') or
                line.startswith(f'INSERT INTO "{self.config_name}_deleted"')
            ):
                yield line

    def __import_database(self, sql_file_path) -> bool:
        """Import database from SQL file"""
        self.__drop_database()
        self.__create_database()
        self.__migrate_database()

        if not os.path.exists(sql_file_path):
            return False

        with open(sql_file_path, 'r') as f:
            for l in f.readlines():
                l = l.rstrip("\n")
                if len(l) > 0:
                    if "INSERT INTO" in l:
                        try:
                            # Parse addresses
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

                                l = l.replace(
                                    f"Address = '{addresses.group(1)}'",
                                    f"address_v4 = '{','.join(addr_v4)}', address_v6 = '{','.join(addr_v6)}'"
                                )
                        except Exception as e:
                            print(f"Error parsing addresses: {e}")

                    sqlUpdate(l)
        return True
