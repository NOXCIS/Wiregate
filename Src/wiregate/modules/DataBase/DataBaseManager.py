import redis
import json
import os
import re
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
from ..ConfigEnv import redis_host, redis_port, redis_db, redis_password

# Configure logging
logger = logging.getLogger('wiregate')

class DatabaseManager:
    """Redis-based database manager for WireGate"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get_key(self, table_name: str, record_id: str = None) -> str:
        """Generate Redis key for table or record"""
        if record_id:
            return f"wiregate:{table_name}:{record_id}"
        return f"wiregate:{table_name}"
    
    def get_all_keys(self) -> List[str]:
        """Get all keys in the database"""
        try:
            return self.redis_client.keys("wiregate:*")
        except redis.exceptions.ResponseError as e:
            if "unknown command 'KEYS'" in str(e):
                # Fallback: use SCAN if KEYS is disabled
                keys = []
                cursor = 0
                while True:
                    cursor, batch_keys = self.redis_client.scan(cursor, match="wiregate:*", count=100)
                    keys.extend(batch_keys)
                    if cursor == 0:
                        break
                return keys
            else:
                raise
    
    def delete_keys(self, keys: List[str]) -> int:
        """Delete multiple keys from Redis"""
        if not keys:
            return 0
        try:
            return self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Error deleting keys: {e}")
            return 0
    
    def get_table_keys(self, table_name: str) -> List[str]:
        """Get all keys for a table"""
        pattern = f"wiregate:{table_name}:*"
        try:
            return self.redis_client.keys(pattern)
        except redis.exceptions.ResponseError as e:
            if "unknown command 'KEYS'" in str(e):
                # Fallback: use SCAN if KEYS is disabled
                keys = []
                cursor = 0
                while True:
                    cursor, partial_keys = self.redis_client.scan(cursor, match=pattern, count=100)
                    keys.extend(partial_keys)
                    if cursor == 0:
                        break
                return keys
            else:
                raise
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """Create a table (Redis doesn't have tables, but we can store schema)"""
        try:
            schema_key = f"wiregate:schemas:{table_name}"
            self.redis_client.hset(schema_key, mapping=schema)
            logger.info(f"Created table schema for {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        schema_key = f"wiregate:schemas:{table_name}"
        return self.redis_client.exists(schema_key) > 0
    
    def drop_table(self, table_name: str) -> bool:
        """Drop a table (delete all records and schema)"""
        try:
            # Delete all records
            keys = self.get_table_keys(table_name)
            if keys:
                self.redis_client.delete(*keys)
            
            # Delete schema
            schema_key = f"wiregate:schemas:{table_name}"
            self.redis_client.delete(schema_key)
            
            logger.info(f"Dropped table {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            return False
    
    def insert_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Insert a record"""
        try:
            key = self.get_key(table_name, record_id)
            # Convert all values to strings for Redis
            redis_data = {k: str(v) if v is not None else '' for k, v in data.items()}
            self.redis_client.hset(key, mapping=redis_data)
            logger.debug(f"Inserted record {record_id} into {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert record {record_id} into {table_name}: {e}")
            return False
    
    def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record"""
        try:
            key = self.get_key(table_name, record_id)
            if not self.redis_client.exists(key):
                return False
            
            # Convert all values to strings for Redis
            redis_data = {k: str(v) if v is not None else '' for k, v in data.items()}
            self.redis_client.hset(key, mapping=redis_data)
            logger.debug(f"Updated record {record_id} in {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update record {record_id} in {table_name}: {e}")
            return False
    
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """Delete a record"""
        try:
            key = self.get_key(table_name, record_id)
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted record {record_id} from {table_name}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete record {record_id} from {table_name}: {e}")
            return False
    
    def get_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record"""
        try:
            key = self.get_key(table_name, record_id)
            data = self.redis_client.hgetall(key)
            if not data:
                return None
            
            # Convert string values back to appropriate types
            return self._convert_record_types(data)
        except Exception as e:
            logger.error(f"Failed to get record {record_id} from {table_name}: {e}")
            return None
    
    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table"""
        try:
            keys = self.get_table_keys(table_name)
            records = []
            
            for key in keys:
                data = self.redis_client.hgetall(key)
                if data:
                    records.append(self._convert_record_types(data))
            
            logger.debug(f"Retrieved {len(records)} records from {table_name}")
            return records
        except Exception as e:
            logger.error(f"Failed to get all records from {table_name}: {e}")
            # Return empty list instead of raising exception to prevent startup failures
            return []
    
    def search_records(self, table_name: str, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search records based on conditions"""
        try:
            all_records = self.get_all_records(table_name)
            matching_records = []
            
            for record in all_records:
                match = True
                for field, value in conditions.items():
                    if field not in record or str(record[field]) != str(value):
                        match = False
                        break
                
                if match:
                    matching_records.append(record)
            
            logger.debug(f"Found {len(matching_records)} matching records in {table_name}")
            return matching_records
        except Exception as e:
            logger.error(f"Failed to search records in {table_name}: {e}")
            return []
    
    def _convert_record_types(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Convert Redis string values back to appropriate Python types"""
        converted = {}
        
        for key, value in data.items():
            if value == '' or value is None:
                converted[key] = None
            elif value.lower() in ['true', 'false']:
                converted[key] = value.lower() == 'true'
            elif value.isdigit():
                converted[key] = int(value)
            elif self._is_float(value):
                converted[key] = float(value)
            else:
                converted[key] = value
        
        return converted
    
    def _is_float(self, value: str) -> bool:
        """Check if string can be converted to float"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def set_migration_flag(self, migration_type: str, source_path: str = None) -> bool:
        """Set migration flag to track completed migrations"""
        try:
            migration_key = f"wiregate:migration:{migration_type}"
            migration_data = {
                'completed': True,
                'timestamp': str(datetime.now()),
                'source_path': source_path or '',
                'version': '1.0'
            }
            self.redis_client.hset(migration_key, mapping=migration_data)
            logger.info(f"Set migration flag for {migration_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to set migration flag for {migration_type}: {e}")
            return False
    
    def is_migration_completed(self, migration_type: str) -> bool:
        """Check if migration has been completed"""
        try:
            migration_key = f"wiregate:migration:{migration_type}"
            return self.redis_client.exists(migration_key) > 0
        except Exception as e:
            logger.error(f"Failed to check migration status for {migration_type}: {e}")
            return False
    
    def get_migration_info(self, migration_type: str) -> Optional[Dict[str, Any]]:
        """Get migration information"""
        try:
            migration_key = f"wiregate:migration:{migration_type}"
            data = self.redis_client.hgetall(migration_key)
            if data:
                return self._convert_record_types(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get migration info for {migration_type}: {e}")
            return None
    
    def reset_migration_flag(self, migration_type: str) -> bool:
        """Reset migration flag to allow re-migration"""
        try:
            migration_key = f"wiregate:migration:{migration_type}"
            result = self.redis_client.delete(migration_key)
            if result > 0:
                logger.info(f"Reset migration flag for {migration_type}")
                return True
            else:
                logger.warning(f"Migration flag for {migration_type} was not found")
                return False
        except Exception as e:
            logger.error(f"Failed to reset migration flag for {migration_type}: {e}")
            return False
    
    def list_migration_flags(self) -> List[str]:
        """List all migration flags"""
        try:
            pattern = "wiregate:migration:*"
            keys = self.redis_client.keys(pattern)
            return [key.replace("wiregate:migration:", "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to list migration flags: {e}")
            return []
    
    def dump_table(self, table_name: str) -> List[str]:
        """Dump table data as SQL INSERT statements (for compatibility)"""
        try:
            records = self.get_all_records(table_name)
            sql_statements = []
            
            for record in records:
                # Convert record to SQL INSERT statement
                columns = list(record.keys())
                values = [f"'{record[col]}'" if record[col] is not None else 'NULL' for col in columns]
                
                sql = f"INSERT INTO \"{table_name}\" ({', '.join(columns)}) VALUES ({', '.join(values)});"
                sql_statements.append(sql)
            
            return sql_statements
        except Exception as e:
            logger.error(f"Failed to dump table {table_name}: {e}")
            return []
    
    def import_sql_statements(self, sql_statements: List[str]) -> bool:
        """Import SQL statements (for migration from SQLite)"""
        try:
            for sql in sql_statements:
                if sql.strip().startswith('INSERT INTO'):
                    # Parse INSERT statement
                    self._parse_and_insert_sql(sql)
            
            logger.info(f"Imported {len(sql_statements)} SQL statements")
            return True
        except Exception as e:
            logger.error(f"Failed to import SQL statements: {e}")
            return False
    
    def _parse_and_insert_sql(self, sql: str):
        """Parse SQL INSERT statement and insert into Redis"""
        try:
            import re
            
            # Extract table name
            table_match = re.search(r'INSERT INTO "?(\w+)"?', sql)
            if not table_match:
                return
            
            table_name = table_match.group(1)
            
            # Extract column names
            columns_match = re.search(r'INSERT INTO "?\w+"?\s*\(([^)]+)\)', sql)
            if not columns_match:
                return
            
            columns_str = columns_match.group(1)
            columns = [col.strip().strip('"') for col in columns_str.split(',')]
            
            # Extract VALUES clause
            values_match = re.search(r'VALUES\s*\((.*)\)', sql, re.IGNORECASE)
            if not values_match:
                return
            
            values_str = values_match.group(1)
            
            # Parse values (handle quoted strings properly)
            values = []
            current_value = ""
            in_quotes = False
            quote_char = None
            paren_count = 0
            
            for char in values_str:
                if char in ["'", '"'] and not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and in_quotes:
                    in_quotes = False
                    quote_char = None
                elif char == '(' and not in_quotes:
                    paren_count += 1
                elif char == ')' and not in_quotes:
                    paren_count -= 1
                elif char == ',' and not in_quotes and paren_count == 0:
                    values.append(current_value.strip().strip("'").strip('"'))
                    current_value = ""
                    continue
                
                current_value += char
            
            if current_value.strip():
                values.append(current_value.strip().strip("'").strip('"'))
            
            # Map columns to values
            if values and len(values) == len(columns):
                record_data = {}
                for i, column in enumerate(columns):
                    value = values[i]
                    # Handle NULL values
                    if value.upper() == 'NULL':
                        record_data[column] = None
                    else:
                        record_data[column] = value
                
                # Use the first column as the record ID (assuming it's the primary key)
                record_id = record_data.get('id')
                if record_id:
                    self.insert_record(table_name, record_id, record_data)
                    logger.debug(f"Imported record {record_id} into {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to parse SQL statement: {e}")


# Global Redis instance
_redis_manager = None

def get_redis_manager() -> DatabaseManager:
    """Get or create global Redis manager instance"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = DatabaseManager(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
    return _redis_manager

# Compatibility functions for existing code
def sqlSelect(query: str, params: tuple = None) -> 'RedisCursor':
    """SQL SELECT compatibility function"""
    return RedisCursor(query, params)

def sqlUpdate(query: str, params: tuple = None) -> bool:
    """SQL UPDATE/INSERT/DELETE compatibility function"""
    manager = get_redis_manager()
    
    try:
        # Parse query type
        query_upper = query.upper().strip()
        
        if query_upper.startswith('SELECT'):
            # SELECT queries are handled by RedisCursor
            return True
        
        elif query_upper.startswith('INSERT'):
            return _handle_insert(query, params, manager)
        
        elif query_upper.startswith('UPDATE'):
            return _handle_update(query, params, manager)
        
        elif query_upper.startswith('DELETE'):
            return _handle_delete(query, params, manager)
        
        elif query_upper.startswith('CREATE TABLE'):
            return _handle_create_table(query, manager)
        
        elif query_upper.startswith('DROP TABLE'):
            return _handle_drop_table(query, manager)
        
        elif query_upper.startswith('ALTER TABLE'):
            return _handle_alter_table(query, manager)
        
        else:
            logger.warning(f"Unsupported query type: {query}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to execute query: {query}, Error: {e}")
        return False

def _handle_insert(query: str, params: tuple, manager: DatabaseManager) -> bool:
    """Handle INSERT queries"""
    import re
    
    # Extract table name
    table_match = re.search(r'INSERT INTO [\'"]?(\w+)[\'"]?', query, re.IGNORECASE)
    if not table_match:
        return False
    
    table_name = table_match.group(1)
    
    # Extract column names and values
    if 'VALUES' in query.upper():
        values_match = re.search(r'VALUES\s*\((.*)\)', query, re.IGNORECASE)
        if values_match and params:
            # Map parameters to column names (simplified)
            columns = ['id', 'private_key', 'DNS', 'endpoint_allowed_ip', 'name', 
                      'total_receive', 'total_sent', 'total_data', 'endpoint', 
                      'status', 'latest_handshake', 'allowed_ip', 'cumu_receive', 
                      'cumu_sent', 'cumu_data', 'mtu', 'keepalive', 'remote_endpoint', 
                      'preshared_key', 'address_v4', 'address_v6', 'upload_rate_limit', 
                      'download_rate_limit', 'scheduler_type']
            
            record_data = {}
            for i, value in enumerate(params):
                if i < len(columns):
                    record_data[columns[i]] = value
            
            record_id = record_data.get('id', str(len(manager.get_all_records(table_name)) + 1))
            return manager.insert_record(table_name, record_id, record_data)
    
    return False

def _handle_update(query: str, params: tuple, manager: DatabaseManager) -> bool:
    """Handle UPDATE queries"""
    import re
    
    # Extract table name
    table_match = re.search(r'UPDATE [\'"]?(\w+)[\'"]?', query, re.IGNORECASE)
    if not table_match:
        return False
    
    table_name = table_match.group(1)
    
    # Extract WHERE clause
    where_match = re.search(r'WHERE\s+(\w+)\s*=\s*\?', query, re.IGNORECASE)
    if where_match and params:
        field_name = where_match.group(1)
        record_id = params[-1]  # Assuming the last parameter is the ID
        
        # Extract SET clause
        set_match = re.search(r'SET\s+(.*?)\s+WHERE', query, re.IGNORECASE | re.DOTALL)
        if set_match:
            set_clause = set_match.group(1)
            # Parse SET clause to get field-value pairs
            updates = {}
            set_parts = set_clause.split(',')
            
            for i, part in enumerate(set_parts):
                if '= ?' in part:
                    field = part.split('=')[0].strip()
                    if i < len(params) - 1:  # Exclude the WHERE parameter
                        updates[field] = params[i]
            
            return manager.update_record(table_name, record_id, updates)
    
    return False

def _handle_delete(query: str, params: tuple, manager: DatabaseManager) -> bool:
    """Handle DELETE queries"""
    import re
    
    # Extract table name
    table_match = re.search(r'DELETE FROM [\'"]?(\w+)[\'"]?', query, re.IGNORECASE)
    if not table_match:
        return False
    
    table_name = table_match.group(1)
    
    # Extract WHERE clause
    where_match = re.search(r'WHERE\s+(\w+)\s*=\s*\?', query, re.IGNORECASE)
    if where_match and params:
        record_id = params[0]
        return manager.delete_record(table_name, record_id)
    
    return False

def _handle_create_table(query: str, manager: DatabaseManager) -> bool:
    """Handle CREATE TABLE queries"""
    import re
    
    # Extract table name
    table_match = re.search(r'CREATE TABLE [\'"]?(\w+)[\'"]?', query, re.IGNORECASE)
    if not table_match:
        return False
    
    table_name = table_match.group(1)
    
    # For Redis, we just need to create a schema entry
    # This is a simplified implementation
    schema = {
        'created_at': str(datetime.now()),
        'type': 'table'
    }
    
    return manager.create_table(table_name, schema)

def _handle_drop_table(query: str, manager: DatabaseManager) -> bool:
    """Handle DROP TABLE queries"""
    import re
    
    # Extract table name
    table_match = re.search(r'DROP TABLE [\'"]?(\w+)[\'"]?', query, re.IGNORECASE)
    if not table_match:
        return False
    
    table_name = table_match.group(1)
    return manager.drop_table(table_name)

def _handle_alter_table(query: str, manager: DatabaseManager) -> bool:
    """Handle ALTER TABLE queries for Redis compatibility"""
    try:
        # Parse ALTER TABLE query
        query_upper = query.upper().strip()
        
        # Extract table name
        if 'ALTER TABLE' in query_upper:
            parts = query.split()
            table_index = parts.index('TABLE') + 1
            if table_index < len(parts):
                table_name = parts[table_index].strip('`"\'')
            else:
                logger.error(f"Could not extract table name from ALTER TABLE query: {query}")
                return False
        
        # Handle ADD COLUMN
        if 'ADD COLUMN' in query_upper:
            # Extract column name and type
            add_column_match = re.search(r'ADD\s+COLUMN\s+(\w+)\s+(\w+)', query_upper)
            if add_column_match:
                column_name = add_column_match.group(1)
                column_type = add_column_match.group(2)
                
                logger.info(f"Adding column {column_name} to table {table_name}")
                # For Redis, we don't need to alter the schema as fields are added dynamically
                # The migration function will handle adding default values to existing records
                return True
            else:
                logger.warning(f"Could not parse ADD COLUMN from query: {query}")
                return False
        
        # Handle other ALTER TABLE operations
        else:
            logger.info(f"ALTER TABLE operation not supported in Redis: {query}")
            return True  # Return True to avoid errors, but log the unsupported operation
            
    except Exception as e:
        logger.error(f"Error handling ALTER TABLE query: {query}, Error: {e}")
        return False

class RedisCursor:
    """Cursor-like object for Redis queries to maintain compatibility"""
    
    def __init__(self, query: str, params: tuple = None):
        self.query = query
        self.params = params or ()
        self.results = []
        self.current_index = 0
        self._execute_query()
    
    def _execute_query(self):
        """Execute the query and store results"""
        manager = get_redis_manager()
        
        try:
            query_upper = self.query.upper().strip()
            
            if 'SELECT' in query_upper:
                if 'FROM' in query_upper:
                    # Extract table name
                    import re
                    table_match = re.search(r'FROM [\'"]?(\w+)[\'"]?', self.query, re.IGNORECASE)
                    if table_match:
                        table_name = table_match.group(1)
                        
                        # Handle WHERE clause
                        where_match = re.search(r'WHERE\s+(\w+)\s*=\s*\?', self.query, re.IGNORECASE)
                        if where_match and self.params:
                            field_name = where_match.group(1)
                            field_value = self.params[0]
                            self.results = manager.search_records(table_name, {field_name: field_value})
                        else:
                            self.results = manager.get_all_records(table_name)
            
            # Convert results to dict-like objects for compatibility
            converted_results = []
            for result in self.results:
                # Create a dict-like object that supports both attribute and key access
                class DictLikeRecord:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                    
                    def __getitem__(self, key):
                        return getattr(self, key)
                    
                    def __contains__(self, key):
                        return hasattr(self, key)
                    
                    def keys(self):
                        return [attr for attr in dir(self) if not attr.startswith('_')]
                    
                    def get(self, key, default=None):
                        return getattr(self, key, default)
                
                record = DictLikeRecord(result)
                converted_results.append(record)
            self.results = converted_results
            
        except Exception as e:
            logger.error(f"Failed to execute query: {self.query}, Error: {e}")
            self.results = []
    
    def fetchone(self):
        """Fetch one result"""
        if self.current_index < len(self.results):
            result = self.results[self.current_index]
            self.current_index += 1
            return result
        return None
    
    def fetchall(self):
        """Fetch all results"""
        results = self.results[self.current_index:]
        self.current_index = len(self.results)
        return results
    
    def __iter__(self):
        """Make cursor iterable"""
        return iter(self.results)

# Legacy compatibility - maintain the old sqldb reference
class LegacySqldb:
    """Legacy SQLite database compatibility"""
    
    def iterdump(self):
        """Iterate over SQL dump statements"""
        manager = get_redis_manager()
        
        try:
            # Get all table names
            pattern = "wiregate:*"
            keys = manager.redis_client.keys(pattern)
            tables = set()
            
            for key in keys:
                if ':schemas:' not in key:
                    table_name = key.split(':')[1]
                    tables.add(table_name)
            
            # Generate SQL dump statements
            for table_name in tables:
                sql_statements = manager.dump_table(table_name)
                for statement in sql_statements:
                    yield statement
        except Exception as e:
            logger.error(f"Failed to generate SQL dump: {e}")
            # Return empty generator to prevent startup failures
            return

# Configuration-specific database methods (moved from Core.py)
class ConfigurationDatabase:
    """Database methods specific to Configuration class"""
    
    def __init__(self, configuration_name: str):
        self.configuration_name = configuration_name
        self.manager = get_redis_manager()
    
    def drop_database(self):
        """Drop all tables for this configuration"""
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_transfer",
            f"{self.configuration_name}_deleted"
        ]
        
        for table in tables:
            self.manager.drop_table(table)
    
    def create_database(self, db_name=None):
        """Create database tables for this configuration"""
        if db_name is None:
            db_name = self.configuration_name
        
        # Define table schemas
        main_table_schema = {
            'id': 'VARCHAR NOT NULL',
            'private_key': 'VARCHAR NULL',
            'DNS': 'VARCHAR NULL',
            'endpoint_allowed_ip': 'VARCHAR NULL',
            'name': 'VARCHAR NULL',
            'total_receive': 'FLOAT NULL',
            'total_sent': 'FLOAT NULL',
            'total_data': 'FLOAT NULL',
            'endpoint': 'VARCHAR NULL',
            'status': 'VARCHAR NULL',
            'latest_handshake': 'VARCHAR NULL',
            'allowed_ip': 'VARCHAR NULL',
            'cumu_receive': 'FLOAT NULL',
            'cumu_sent': 'FLOAT NULL',
            'cumu_data': 'FLOAT NULL',
            'mtu': 'INT NULL',
            'keepalive': 'INT NULL',
            'remote_endpoint': 'VARCHAR NULL',
            'preshared_key': 'VARCHAR NULL',
            'address_v4': 'VARCHAR NULL',
            'address_v6': 'VARCHAR NULL',
            'upload_rate_limit': 'INTEGER DEFAULT 0',
            'download_rate_limit': 'INTEGER DEFAULT 0',
            'scheduler_type': 'TEXT'
        }
        
        # Create main table
        self.manager.create_table(db_name, main_table_schema)
        
        # Create restrict_access table
        self.manager.create_table(f"{db_name}_restrict_access", main_table_schema)
        
        # Create transfer table
        transfer_schema = {
            'id': 'VARCHAR NOT NULL',
            'total_receive': 'FLOAT NULL',
            'total_sent': 'FLOAT NULL',
            'total_data': 'FLOAT NULL',
            'cumu_receive': 'FLOAT NULL',
            'cumu_sent': 'FLOAT NULL',
            'cumu_data': 'FLOAT NULL',
            'time': 'DATETIME'
        }
        self.manager.create_table(f"{db_name}_transfer", transfer_schema)
        
        # Create deleted table
        self.manager.create_table(f"{db_name}_deleted", main_table_schema)
    
    def migrate_database(self):
        """Add missing columns to existing tables and update existing records with default values"""
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_deleted"
        ]
        
        # Define new fields with their default values
        new_fields = {
            'address_v4': None,
            'address_v6': None,
            'upload_rate_limit': 0,
            'download_rate_limit': 0,
            'scheduler_type': 'htb'
        }
        
        for table in tables:
            if not self.manager.table_exists(table):
                logger.info(f"Table {table} does not exist, skipping migration")
                continue
            
            logger.info(f"Migrating table {table}...")
            
            # Get all existing records in this table
            try:
                records = self.manager.get_all_records(table)
                updated_count = 0
                
                for record_data in records:
                    record_id = record_data.get('id')
                    if not record_id:
                        continue
                    # Check if record needs migration
                    needs_update = False
                    update_data = {}
                    
                    for field, default_value in new_fields.items():
                        if field not in record_data or record_data[field] is None:
                            update_data[field] = default_value
                            needs_update = True
                    
                    # Update record if needed
                    if needs_update:
                        self.manager.update_record(table, record_id, update_data)
                        updated_count += 1
                
                logger.info(f"Migration completed for table {table}: {updated_count} records updated")
                
            except Exception as e:
                logger.error(f"Error migrating table {table}: {e}")
                # Continue with other tables even if one fails
    
    def dump_database(self):
        """Dump database data as SQL statements"""
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_transfer",
            f"{self.configuration_name}_deleted"
        ]
        
        for table in tables:
            try:
                sql_statements = self.manager.dump_table(table)
                for statement in sql_statements:
                    yield statement
            except Exception as e:
                logger.error(f"Failed to dump table {table}: {e}")
                # Continue with other tables even if one fails
                continue
    
    def import_database(self, sql_file_path: str) -> bool:
        """Import database from SQL file"""
        try:
            import os
            if not os.path.exists(sql_file_path):
                return False
            
            # Drop existing tables
            self.drop_database()
            
            # Create new tables
            self.create_database()
            self.migrate_database()
            
            # Read and import SQL statements
            with open(sql_file_path, 'r') as f:
                sql_statements = []
                for line in f.readlines():
                    line = line.rstrip("\n")
                    if len(line) > 0:
                        sql_statements.append(line)
                
                return self.manager.import_sql_statements(sql_statements)
                
        except Exception as e:
            logger.error(f"Failed to import database: {e}")
            return False
    
    def get_restricted_peers(self):
        """Get restricted peers"""
        return self.manager.get_all_records(f"{self.configuration_name}_restrict_access")
    
    def get_peers(self):
        """Get all peers"""
        return self.manager.get_all_records(self.configuration_name)
    
    def search_peer(self, peer_id: str):
        """Search for a specific peer"""
        return self.manager.get_record(self.configuration_name, peer_id)
    
    def insert_peer(self, peer_data: dict):
        """Insert a new peer"""
        peer_id = peer_data.get('id')
        if peer_id:
            return self.manager.insert_record(self.configuration_name, peer_id, peer_data)
        return False
    
    def update_peer(self, peer_id: str, peer_data: dict):
        """Update a peer"""
        return self.manager.update_record(self.configuration_name, peer_id, peer_data)
    
    def delete_peer(self, peer_id: str):
        """Delete a peer"""
        return self.manager.delete_record(self.configuration_name, peer_id)
    
    def move_peer_to_restricted(self, peer_id: str):
        """Move peer to restricted access table"""
        peer_data = self.manager.get_record(self.configuration_name, peer_id)
        if peer_data:
            # Insert into restricted table
            self.manager.insert_record(f"{self.configuration_name}_restrict_access", peer_id, peer_data)
            # Delete from main table
            self.manager.delete_record(self.configuration_name, peer_id)
            return True
        return False
    
    def move_peer_from_restricted(self, peer_id: str):
        """Move peer from restricted access table back to main table"""
        peer_data = self.manager.get_record(f"{self.configuration_name}_restrict_access", peer_id)
        if peer_data:
            # Insert into main table
            self.manager.insert_record(self.configuration_name, peer_id, peer_data)
            # Delete from restricted table
            self.manager.delete_record(f"{self.configuration_name}_restrict_access", peer_id)
            return True
        return False
    
    def update_peer_handshake(self, peer_id: str, handshake_time: str, status: str):
        """Update peer handshake information"""
        updates = {
            'latest_handshake': handshake_time,
            'status': status
        }
        return self.manager.update_record(self.configuration_name, peer_id, updates)
    
    def update_peer_transfer(self, peer_id: str, total_receive: float, total_sent: float, total_data: float):
        """Update peer transfer data"""
        updates = {
            'total_receive': total_receive,
            'total_sent': total_sent,
            'total_data': total_data
        }
        return self.manager.update_record(self.configuration_name, peer_id, updates)
    
    def update_peer_endpoint(self, peer_id: str, endpoint: str):
        """Update peer endpoint"""
        updates = {'endpoint': endpoint}
        return self.manager.update_record(self.configuration_name, peer_id, updates)
    
    def reset_peer_data_usage(self, peer_id: str, reset_type: str):
        """Reset peer data usage"""
        if reset_type == "total":
            updates = {
                'total_data': 0,
                'cumu_data': 0,
                'total_receive': 0,
                'cumu_receive': 0,
                'total_sent': 0,
                'cumu_sent': 0
            }
        elif reset_type == "receive":
            updates = {
                'total_receive': 0,
                'cumu_receive': 0
            }
        elif reset_type == "sent":
            updates = {
                'total_sent': 0,
                'cumu_sent': 0
            }
        else:
            return False
        
        return self.manager.update_record(self.configuration_name, peer_id, updates)
    
    def copy_database_to(self, new_configuration_name: str):
        """Copy database to new configuration name"""
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_deleted",
            f"{self.configuration_name}_transfer"
        ]
        
        for table in tables:
            new_table = table.replace(self.configuration_name, new_configuration_name)
            
            # Get all records from source table
            records = self.manager.get_all_records(table)
            
            # Insert records into new table
            for record in records:
                record_id = record.get('id')
                if record_id:
                    self.manager.insert_record(new_table, record_id, record)
        
        return True

# Global sqldb instance for compatibility
sqldb = LegacySqldb()

# Initialize Redis connection on module import
try:
    get_redis_manager()
    logger.info("Redis database manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Redis database manager: {e}")
    # Fallback to a no-op implementation
    class NoOpManager:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    _redis_manager = NoOpManager()

# SQLite to Redis Migration Functions
def migrate_sqlite_to_redis():
    """Migrate any existing SQLite databases to Redis"""
    logger.info("Checking for SQLite databases to migrate...")
    
    # Get Redis manager to check migration status
    try:
        redis_manager = get_redis_manager()
        
        # Check if migration has already been completed
        if redis_manager.is_migration_completed('sqlite_to_redis'):
            migration_info = redis_manager.get_migration_info('sqlite_to_redis')
            logger.info(f"SQLite to Redis migration already completed at {migration_info.get('timestamp', 'unknown time')}")
            return 0
            
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        # Continue with migration if we can't check status
    
    # Common SQLite database file patterns
    sqlite_patterns = [
        "wgdashboard.db",
        "wgdashboard_job.db", 
        "wgdashboard_log.db"
    ]
    
    # Check for SQLite files in common locations
    db_locations = [
        "./db/",
        "./Src/db/",
        "/etc/wireguard/",
        os.path.expanduser("~/.wiregate/")
    ]
    
    migrated_count = 0
    found_databases = []
    
    # First, collect all found databases
    for location in db_locations:
        if not os.path.exists(location):
            continue
            
        for pattern in sqlite_patterns:
            sqlite_path = os.path.join(location, pattern)
            if os.path.exists(sqlite_path):
                found_databases.append(sqlite_path)
    
    if not found_databases:
        logger.info("No SQLite databases found to migrate")
        return 0
    
    logger.info(f"Found {len(found_databases)} SQLite databases to migrate")
    
    # Migrate each database
    for sqlite_path in found_databases:
        try:
            logger.info(f"Migrating SQLite database: {sqlite_path}")
            if migrate_sqlite_file_to_redis(sqlite_path):
                migrated_count += 1
                logger.info(f"Successfully migrated {sqlite_path}")
            else:
                logger.warning(f"Failed to migrate {sqlite_path}")
        except Exception as e:
            logger.error(f"Error migrating {sqlite_path}: {e}")
    
    # Set migration flag if any databases were migrated
    if migrated_count > 0:
        try:
            redis_manager = get_redis_manager()
            redis_manager.set_migration_flag('sqlite_to_redis', f"{migrated_count} databases")
            logger.info(f"Migration completed: {migrated_count} SQLite databases migrated to Redis")
        except Exception as e:
            logger.error(f"Failed to set migration flag: {e}")
    else:
        logger.info("No SQLite databases were migrated")
    
    return migrated_count

def migrate_sqlite_file_to_redis(sqlite_path: str) -> bool:
    """Migrate a specific SQLite file to Redis"""
    try:
        # Get Redis manager to check if this specific file has been migrated
        redis_manager = get_redis_manager()
        
        # Create a unique migration key for this specific file
        file_basename = os.path.basename(sqlite_path)
        migration_key = f"sqlite_file_{file_basename}"
        
        # Check if this specific file has already been migrated
        if redis_manager.is_migration_completed(migration_key):
            migration_info = redis_manager.get_migration_info(migration_key)
            logger.info(f"SQLite file {sqlite_path} already migrated at {migration_info.get('timestamp', 'unknown time')}")
            return True
        
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Get all table names
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        if not tables:
            logger.warning(f"No tables found in {sqlite_path}")
            sqlite_conn.close()
            return False
        
        migrated_tables = 0
        total_records = 0
        
        for table_name in tables:
            try:
                # Get table schema
                sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
                columns = sqlite_cursor.fetchall()
                
                # Create schema for Redis
                schema = {}
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_nullable = not col[3]  # NOT NULL is 0, NULL is 1
                    
                    # Convert SQLite types to Redis-compatible types
                    if 'INT' in col_type.upper():
                        schema[col_name] = 'INTEGER'
                    elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper():
                        schema[col_name] = 'FLOAT'
                    else:
                        schema[col_name] = 'VARCHAR'
                
                # Create table in Redis if it doesn't exist
                if not redis_manager.table_exists(table_name):
                    redis_manager.create_table(table_name, schema)
                
                # Migrate data
                sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                rows = sqlite_cursor.fetchall()
                
                for row in rows:
                    # Create record data
                    record_data = {}
                    for i, col in enumerate(columns):
                        col_name = col[1]
                        value = row[i]
                        
                        # Convert None to appropriate default
                        if value is None:
                            if 'INT' in col[2].upper():
                                record_data[col_name] = 0
                            elif 'REAL' in col[2].upper() or 'FLOAT' in col[2].upper():
                                record_data[col_name] = 0.0
                            else:
                                record_data[col_name] = ""
                        else:
                            record_data[col_name] = value
                    
                    # Use first column as ID (assuming it's the primary key)
                    record_id = str(record_data[columns[0][1]])
                    
                    # Insert into Redis
                    redis_manager.insert_record(table_name, record_id, record_data)
                
                migrated_tables += 1
                total_records += len(rows)
                logger.info(f"Migrated table {table_name}: {len(rows)} records")
                
            except Exception as e:
                logger.error(f"Error migrating table {table_name}: {e}")
                continue
        
        sqlite_conn.close()
        
        if migrated_tables > 0:
            # Set migration flag for this specific file
            try:
                redis_manager.set_migration_flag(migration_key, sqlite_path)
                logger.info(f"Set migration flag for {sqlite_path}")
            except Exception as e:
                logger.warning(f"Failed to set migration flag for {sqlite_path}: {e}")
            
            # Create backup of original SQLite file
            backup_path = f"{sqlite_path}.migrated_backup"
            try:
                import shutil
                shutil.copy2(sqlite_path, backup_path)
                logger.info(f"Created backup of original SQLite file: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
            
            logger.info(f"Successfully migrated {sqlite_path}: {migrated_tables} tables, {total_records} records")
            return True
        else:
            logger.warning(f"No tables were migrated from {sqlite_path}")
            return False
        
    except Exception as e:
        logger.error(f"Error migrating SQLite file {sqlite_path}: {e}")
        return False

def check_and_migrate_sqlite_databases():
    """Check for and migrate SQLite databases during startup"""
    try:
        # Only run migration if Redis is available
        redis_manager = get_redis_manager()
        if redis_manager is None:
            logger.warning("Redis not available, skipping SQLite migration")
            return False
        
        # Test Redis connection
        redis_manager.redis_client.ping()
        
        # Check if migration has already been completed
        if redis_manager.is_migration_completed('sqlite_to_redis'):
            migration_info = redis_manager.get_migration_info('sqlite_to_redis')
            logger.info(f"SQLite to Redis migration already completed at {migration_info.get('timestamp', 'unknown time')}")
            return True
        
        # Check for development mode - skip migration if in development
        from ..ConfigEnv import DASHBOARD_MODE
        if DASHBOARD_MODE == 'development':
            logger.info("Development mode detected, skipping SQLite migration")
            return False
        
        # Run migration
        migrated_count = migrate_sqlite_to_redis()
        return migrated_count > 0
        
    except Exception as e:
        logger.error(f"Error during SQLite migration check: {e}")
        return False

def reset_sqlite_migration_flags():
    """Reset all SQLite migration flags to allow re-migration"""
    try:
        redis_manager = get_redis_manager()
        if redis_manager is None:
            logger.warning("Redis not available, cannot reset migration flags")
            return False
        
        # Get all migration flags
        migration_flags = redis_manager.list_migration_flags()
        reset_count = 0
        
        for flag in migration_flags:
            if flag.startswith('sqlite') or flag == 'sqlite_to_redis':
                if redis_manager.reset_migration_flag(flag):
                    reset_count += 1
        
        logger.info(f"Reset {reset_count} SQLite migration flags")
        return reset_count > 0
        
    except Exception as e:
        logger.error(f"Error resetting migration flags: {e}")
        return False

def get_migration_status():
    """Get current migration status"""
    try:
        redis_manager = get_redis_manager()
        if redis_manager is None:
            return {"error": "Redis not available"}
        
        migration_flags = redis_manager.list_migration_flags()
        status = {}
        
        for flag in migration_flags:
            info = redis_manager.get_migration_info(flag)
            if info:
                status[flag] = {
                    'completed': info.get('completed', False),
                    'timestamp': info.get('timestamp', 'unknown'),
                    'source_path': info.get('source_path', ''),
                    'version': info.get('version', 'unknown')
                }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting migration status: {e}")
        return {"error": str(e)}
