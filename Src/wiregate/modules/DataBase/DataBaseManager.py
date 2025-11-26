import redis
import json
import os
import re
import aiosqlite
import sqlite3  # Still needed for migration functions
import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
import asyncio
from ..Config import (
    redis_host, redis_port, redis_db, redis_password,
    postgres_host, postgres_port, postgres_db, postgres_user, postgres_password, postgres_ssl_mode,
    DASHBOARD_TYPE
)

# Configure logging
logger = logging.getLogger('wiregate')

class SQLiteDatabaseManager:
    """
    Async SQLite database manager for simple deployments
    Uses aiosqlite for thread-safe async operations
    
    All methods are async to ensure thread-safe access when used from async contexts.
    See Docs/ARCHITECTURE.md for database architecture documentation.
    """
    
    def __init__(self, db_path=None):
        """Initialize SQLite connection (async initialization required)"""
        if db_path is None:
            # Default SQLite database path
            db_path = os.path.join(os.getcwd(), 'db', 'wgdashboard.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self._init_event = None
        # Note: Connection will be initialized asynchronously via _init_sqlite()
        
    async def _init_sqlite(self):
        """Initialize async SQLite connection"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row  # Enable dict-like access
            logger.info(f"Successfully connected to async SQLite database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to async SQLite database: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure database connection is initialized (for sync compatibility)"""
        if self.conn is None:
            # Try to initialize synchronously if not already done
            if self._init_event is None:
                self._init_event = asyncio.Event()
                try:
                    # Try to get running event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, we need to wait for async init
                        # This is a fallback - ideally all code should use async methods
                        logger.warning("SQLiteDatabaseManager used synchronously - connection may not be initialized")
                    else:
                        # No running loop, can initialize directly
                        loop.run_until_complete(self._init_sqlite())
                except RuntimeError:
                    # No event loop, create one
                    asyncio.run(self._init_sqlite())
    
    @property
    def redis_client(self):
        """Mock Redis client for compatibility - returns None in simple mode"""
        return None
    
    def _serialize_data_for_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data for database storage (convert lists to JSON strings)"""
        serialized_data = data.copy()
        if 'traffic' in serialized_data and isinstance(serialized_data['traffic'], list):
            serialized_data['traffic'] = json.dumps(serialized_data['traffic'])
        return serialized_data
    
    def _deserialize_data_from_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize data from database (convert JSON strings back to lists)"""
        deserialized_data = data.copy()
        if 'traffic' in deserialized_data and isinstance(deserialized_data['traffic'], str):
            try:
                deserialized_data['traffic'] = json.loads(deserialized_data['traffic'])
            except (json.JSONDecodeError, TypeError):
                deserialized_data['traffic'] = []
        return deserialized_data
    
    async def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """Create a table with the given schema"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            columns = []
            for column_name, column_type in schema.items():
                columns.append(f"{column_name} {column_type}")
            
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
            
            await self.conn.execute(create_sql)
            await self.conn.commit()
            logger.debug(f"Created table {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    async def insert_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Insert a record into the table"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            # Ensure the record_id is in the data
            data['id'] = record_id
            
            # Serialize data for database storage
            serialized_data = self._serialize_data_for_db(data)
            
            columns = list(serialized_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(serialized_data.values())
            
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            await self.conn.execute(insert_sql, values)
            await self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert record into {table_name}: {e}")
            return False
    
    async def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record in the table"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            # Serialize data for database storage
            serialized_data = self._serialize_data_for_db(data)
            
            set_clauses = [f"{key} = ?" for key in serialized_data.keys()]
            values = list(serialized_data.values()) + [record_id]
            
            update_sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor = await self.conn.execute(update_sql, values)
            await self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update record in {table_name}: {e}")
            return False
    
    async def get_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            select_sql = f"SELECT * FROM {table_name} WHERE id = ?"
            cursor = await self.conn.execute(select_sql, (record_id,))
            row = await cursor.fetchone()
            
            if row:
                data = dict(row)
                return self._deserialize_data_from_db(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get record from {table_name}: {e}")
            return None
    
    async def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            select_sql = f"SELECT * FROM {table_name}"
            cursor = await self.conn.execute(select_sql)
            rows = await cursor.fetchall()
            
            return [self._deserialize_data_from_db(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get records from {table_name}: {e}")
            return []
    
    async def delete_record(self, table_name: str, record_id: str) -> bool:
        """Delete a record from the table"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            delete_sql = f"DELETE FROM {table_name} WHERE id = ?"
            
            cursor = await self.conn.execute(delete_sql, (record_id,))
            await self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete record from {table_name}: {e}")
            return False
    
    async def drop_table(self, table_name: str) -> bool:
        """Drop a table"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            drop_sql = f"DROP TABLE IF EXISTS {table_name}"
            
            await self.conn.execute(drop_sql)
            await self.conn.commit()
            logger.debug(f"Dropped table {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            return False
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists in SQLite"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            cursor = await self.conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            result = await cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check if table {table_name} exists: {e}")
            return False
    
    async def get_all_keys(self) -> List[str]:
        """Get all table names from SQLite"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            cursor = await self.conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'wiregate_%'
            """)
            rows = await cursor.fetchall()
            tables = [row[0] for row in rows]
            return tables
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def _invalidate_cache(self, table_name: str, record_id: str = None) -> bool:
        """No-op cache invalidation for SQLite (no cache)"""
        # SQLite doesn't use Redis cache, so this is a no-op
        return True
    
    async def dump_table(self, table_name: str) -> List[str]:
        """Dump table data as SQL INSERT statements (for compatibility)"""
        try:
            records = await self.get_all_records(table_name)
            sql_statements = []
            
            for record in records:
                # Convert record to SQL INSERT statement
                columns = list(record.keys())
                values = []
                for col in columns:
                    if record[col] is None:
                        values.append('NULL')
                    elif isinstance(record[col], str):
                        # Escape single quotes in strings
                        escaped_value = record[col].replace("'", "''")
                        values.append(f"'{escaped_value}'")
                    else:
                        values.append(f"'{record[col]}'")
                
                sql = f"INSERT INTO \"{table_name}\" ({', '.join([f'\"{col}\"' for col in columns])}) VALUES ({', '.join(values)});"
                sql_statements.append(sql)
            
            return sql_statements
        except Exception as e:
            logger.error(f"Failed to dump table {table_name}: {e}")
            return []
    
    async def import_sql_statements(self, sql_statements: List[str]) -> bool:
        """Import SQL statements into SQLite"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            for sql in sql_statements:
                if sql.strip().startswith('INSERT INTO'):
                    try:
                        await self.conn.execute(sql)
                    except Exception as e:
                        logger.warning(f"Failed to execute SQL statement: {sql[:100]}... Error: {e}")
                        continue
            
            await self.conn.commit()
            logger.debug(f"Imported {len(sql_statements)} SQL statements")
            return True
        except Exception as e:
            logger.error(f"Failed to import SQL statements: {e}")
            return False
    
    async def create_jobs_table(self) -> bool:
        """Create jobs table in SQLite"""
        try:
            schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'JobID': 'VARCHAR UNIQUE NOT NULL',
                'Configuration': 'TEXT NOT NULL',
                'Peer': 'TEXT NOT NULL',
                'Field': 'TEXT',
                'Operator': 'TEXT',
                'Value': 'TEXT',
                'CreationDate': 'TIMESTAMP',
                'ExpireDate': 'TIMESTAMP',
                'Action': 'TEXT',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            return await self.create_table('PeerJobs', schema)
        except Exception as e:
            logger.error(f"Failed to create jobs table: {e}")
            return False
    
    async def create_logs_table(self) -> bool:
        """Create logs table in SQLite"""
        try:
            schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'LogID': 'VARCHAR UNIQUE NOT NULL',
                'JobID': 'VARCHAR NOT NULL',
                'LogDate': 'TIMESTAMP',
                'Status': 'BOOLEAN',
                'Message': 'TEXT',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            return await self.create_table('PeerJobLogs', schema)
        except Exception as e:
            logger.error(f"Failed to create logs table: {e}")
            return False
    
    async def _ensure_brute_force_table(self) -> bool:
        """Ensure brute_force_attempts table exists"""
        try:
            schema = {
                'identifier': 'VARCHAR PRIMARY KEY',
                'attempts': 'INTEGER DEFAULT 0',
                'locked_until': 'TIMESTAMP',
                'last_attempt': 'TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            return await self.create_table('brute_force_attempts', schema)
        except Exception as e:
            logger.error(f"Failed to create brute force table: {e}")
            return False
    
    async def get_brute_force_attempts(self, identifier: str) -> Dict[str, Any]:
        """Get brute force attempts for an identifier from SQLite"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            await self._ensure_brute_force_table()
            cursor = await self.conn.execute("""
                SELECT attempts, locked_until, last_attempt 
                FROM brute_force_attempts 
                WHERE identifier = ?
            """, (identifier,))
            result = await cursor.fetchone()
            
            if result:
                return {
                    'attempts': result['attempts'],
                    'locked_until': result['locked_until'],
                    'last_attempt': result['last_attempt']
                }
            return {'attempts': 0, 'locked_until': None, 'last_attempt': None}
        except Exception as e:
            logger.error(f"Failed to get brute force attempts: {e}")
            return {'attempts': 0, 'locked_until': None, 'last_attempt': None}
    
    async def record_brute_force_attempt(self, identifier: str, max_attempts: int, lockout_time: int) -> bool:
        """Record a brute force attempt in SQLite"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            await self._ensure_brute_force_table()
            
            # Check if record exists
            cursor = await self.conn.execute("SELECT attempts FROM brute_force_attempts WHERE identifier = ?", (identifier,))
            result = await cursor.fetchone()
            
            if result:
                # Update existing record
                attempts = result[0] + 1
                await self.conn.execute("""
                    UPDATE brute_force_attempts 
                    SET attempts = ?, last_attempt = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE identifier = ?
                """, (attempts, identifier))
            else:
                # Insert new record
                attempts = 1
                await self.conn.execute("""
                    INSERT INTO brute_force_attempts (identifier, attempts, last_attempt)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (identifier, attempts))
            
            # If max attempts reached, set lockout
            if attempts >= max_attempts:
                await self.conn.execute("""
                    UPDATE brute_force_attempts 
                    SET locked_until = datetime('now', '+' || ? || ' seconds')
                    WHERE identifier = ?
                """, (lockout_time, identifier))
            
            await self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record brute force attempt: {e}")
            return False
    
    async def clear_brute_force_attempts(self, identifier: str) -> bool:
        """Clear brute force attempts for successful authentication"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            await self._ensure_brute_force_table()
            await self.conn.execute("DELETE FROM brute_force_attempts WHERE identifier = ?", (identifier,))
            await self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear brute force attempts: {e}")
            return False
    
    async def cleanup_expired_brute_force(self) -> int:
        """Clean up expired brute force records"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            await self._ensure_brute_force_table()
            cursor = await self.conn.execute("""
                DELETE FROM brute_force_attempts 
                WHERE locked_until IS NOT NULL AND locked_until < CURRENT_TIMESTAMP
            """)
            await self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup expired brute force records: {e}")
            return 0
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a custom query"""
        try:
            if self.conn is None:
                await self._init_sqlite()
            
            cursor = await self.conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []
    
    async def close(self):
        """Close the database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Async SQLite database connection closed")

class DatabaseManager:
    """PostgreSQL primary database with Redis cache layer for WireGate"""
    
    def __init__(self, postgres_config=None, redis_config=None):
        """Initialize PostgreSQL and Redis connections"""
        # Use provided config or fallback to environment variables
        # Avoid circular import by not importing DashboardConfig here
        self.postgres_config = postgres_config or {
            'host': postgres_host,
            'port': postgres_port,
            'database': postgres_db,
            'user': postgres_user,
            'password': postgres_password,
            'sslmode': postgres_ssl_mode
        }
        self.redis_config = redis_config or {
            'host': redis_host,
            'port': redis_port,
            'db': redis_db,
            'password': redis_password
        }
        
        # Initialize connections
        self._init_postgres()
        self._init_redis()
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes default TTL
        self.cache_enabled = True
        
    def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            self.postgres_conn = psycopg2.connect(**self.postgres_config)
            self.postgres_conn.autocommit = True
            logger.info("Successfully connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                db=self.redis_config['db'],
                password=self.redis_config['password'],
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Continue without Redis if it fails
            self.redis_client = None
            self.cache_enabled = False
    
    def get_cache_key(self, table_name: str, record_id: str = None) -> str:
        """Generate Redis cache key for table or record"""
        if record_id:
            return f"wiregate:cache:{table_name}:{record_id}"
        return f"wiregate:cache:{table_name}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache"""
        if not self.cache_enabled or not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.debug(f"Cache read error for key {cache_key}: {e}")
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """Set data in Redis cache"""
        if not self.cache_enabled or not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.cache_ttl
            self.redis_client.setex(cache_key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.debug(f"Cache write error for key {cache_key}: {e}")
            return False
    
    def _invalidate_cache(self, table_name: str, record_id: str = None) -> bool:
        """Invalidate cache entries for a table or specific record"""
        if not self.cache_enabled or not self.redis_client:
            return False
        
        try:
            if record_id:
                # Invalidate specific record
                cache_key = self.get_cache_key(table_name, record_id)
                self.redis_client.delete(cache_key)
            else:
                # Invalidate all records for table
                pattern = f"wiregate:cache:{table_name}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.debug(f"Cache invalidation error for {table_name}:{record_id}: {e}")
            return False
    
    def _serialize_data_for_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data for database storage (convert lists to JSON strings)"""
        serialized_data = data.copy()
        if 'traffic' in serialized_data and isinstance(serialized_data['traffic'], list):
            serialized_data['traffic'] = json.dumps(serialized_data['traffic'])
        return serialized_data
    
    def _deserialize_data_from_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize data from database (convert JSON strings back to lists)"""
        deserialized_data = data.copy()
        if 'traffic' in deserialized_data and isinstance(deserialized_data['traffic'], str):
            try:
                deserialized_data['traffic'] = json.loads(deserialized_data['traffic'])
            except (json.JSONDecodeError, TypeError):
                deserialized_data['traffic'] = []
        return deserialized_data
    
    def get_all_keys(self) -> List[str]:
        """Get all table names from PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'wiregate_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                return tables
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def delete_keys(self, keys: List[str]) -> int:
        """Delete multiple tables from PostgreSQL"""
        if not keys:
            return 0
        try:
            deleted_count = 0
            with self.postgres_conn.cursor() as cursor:
                for table_name in keys:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    deleted_count += 1
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting tables: {e}")
            return 0
    
    def get_table_keys(self, table_name: str) -> List[str]:
        """Get all record IDs for a table"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(f"SELECT id FROM {table_name}")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get table keys for {table_name}: {e}")
            return []
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """Create a table in PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Build CREATE TABLE statement
                columns = []
                for col_name, col_type in schema.items():
                    if col_name == 'id':
                        columns.append(f'"{col_name}" VARCHAR PRIMARY KEY')
                    else:
                        # Convert Redis types to PostgreSQL types
                        if 'INT' in col_type.upper():
                            pg_type = 'INTEGER'
                        elif 'FLOAT' in col_type.upper() or 'REAL' in col_type.upper():
                            pg_type = 'REAL'
                        elif 'DATETIME' in col_type.upper():
                            pg_type = 'TIMESTAMP'
                        else:
                            pg_type = 'TEXT'
                        
                        columns.append(f'"{col_name}" {pg_type}')
                
                create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
                cursor.execute(create_sql)
                
                # Invalidate cache for this table
                self._invalidate_cache(table_name)
                
                logger.debug(f"Created table {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    
    def get_brute_force_attempts(self, identifier: str) -> Dict[str, Any]:
        """Get brute force attempts for an identifier"""
        try:
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT attempts, locked_until, last_attempt 
                    FROM brute_force_attempts 
                    WHERE identifier = %s
                """, (identifier,))
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return {'attempts': 0, 'locked_until': None, 'last_attempt': None}
        except Exception as e:
            logger.error(f"Failed to get brute force attempts: {e}")
            return {'attempts': 0, 'locked_until': None, 'last_attempt': None}
    
    def record_brute_force_attempt(self, identifier: str, max_attempts: int, lockout_time: int) -> bool:
        """Record a brute force attempt"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Check if record exists
                cursor.execute("SELECT attempts FROM brute_force_attempts WHERE identifier = %s", (identifier,))
                result = cursor.fetchone()
                
                if result:
                    # Update existing record
                    attempts = result[0] + 1
                    cursor.execute("""
                        UPDATE brute_force_attempts 
                        SET attempts = %s, last_attempt = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE identifier = %s
                    """, (attempts, identifier))
                else:
                    # Insert new record
                    attempts = 1
                    cursor.execute("""
                        INSERT INTO brute_force_attempts (identifier, attempts, last_attempt)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """, (identifier, attempts))
                
                # If max attempts reached, set lockout
                if attempts >= max_attempts:
                    cursor.execute("""
                        UPDATE brute_force_attempts 
                        SET locked_until = CURRENT_TIMESTAMP + INTERVAL '%s seconds'
                        WHERE identifier = %s
                    """, (lockout_time, identifier))
                
                return True
        except Exception as e:
            logger.error(f"Failed to record brute force attempt: {e}")
            return False
    
    def clear_brute_force_attempts(self, identifier: str) -> bool:
        """Clear brute force attempts for successful authentication"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("DELETE FROM brute_force_attempts WHERE identifier = %s", (identifier,))
                return True
        except Exception as e:
            logger.error(f"Failed to clear brute force attempts: {e}")
            return False
    
    def cleanup_expired_brute_force(self) -> int:
        """Clean up expired brute force records"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM brute_force_attempts 
                    WHERE locked_until IS NOT NULL AND locked_until < CURRENT_TIMESTAMP
                """)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup expired brute force records: {e}")
            return 0
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table_name,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to check if table {table_name} exists: {e}")
            return False
    
    def drop_table(self, table_name: str) -> bool:
        """Drop a table from PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                
                # Invalidate cache for this table
                self._invalidate_cache(table_name)
                
                logger.debug(f"Dropped table {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            return False
    
    def insert_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Insert a record into PostgreSQL and cache in Redis"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Serialize data for database storage
                serialized_data = self._serialize_data_for_db(data)
                
                # Prepare data for PostgreSQL
                columns = list(serialized_data.keys())
                values = list(serialized_data.values())
                placeholders = ['%s'] * len(values)
                
                # Insert into PostgreSQL
                insert_sql = f'''
                    INSERT INTO "{table_name}" ({", ".join([f'"{col}"' for col in columns])})
                    VALUES ({", ".join(placeholders)})
                    ON CONFLICT (id) DO UPDATE SET
                    {", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'id'])}
                '''
                cursor.execute(insert_sql, values)
                
                # Cache in Redis (use original data, not serialized)
                cache_key = self.get_cache_key(table_name, record_id)
                self._set_cache(cache_key, data)
                
                return True
        except Exception as e:
            logger.error(f"Failed to insert record {record_id} into {table_name}: {e}")
            return False
    
    def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record in PostgreSQL and cache in Redis"""
        try:
            with self.postgres_conn.cursor() as cursor:
                # Serialize data for database storage
                serialized_data = self._serialize_data_for_db(data)
                
                # Build UPDATE statement
                set_clauses = []
                values = []
                for field, value in serialized_data.items():
                    set_clauses.append(f'"{field}" = %s')
                    values.append(value)
                
                values.append(record_id)  # Add record_id for WHERE clause
                
                update_sql = f'''
                    UPDATE "{table_name}" 
                    SET {", ".join(set_clauses)}
                    WHERE "id" = %s
                '''
                cursor.execute(update_sql, values)
                
                # Invalidate cache for this record
                self._invalidate_cache(table_name, record_id)
                
                return True
        except Exception as e:
            logger.error(f"Failed to update record {record_id} in {table_name}: {e}")
            return False
    
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """Delete a record from PostgreSQL and invalidate cache"""
        try:
            with self.postgres_conn.cursor() as cursor:
                delete_sql = f'DELETE FROM "{table_name}" WHERE "id" = %s'
                cursor.execute(delete_sql, (record_id,))
                
                # Invalidate cache for this record
                self._invalidate_cache(table_name, record_id)
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete record {record_id} from {table_name}: {e}")
            return False
    
    def get_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record from cache first, then PostgreSQL"""
        try:
            # Try cache first
            cache_key = self.get_cache_key(table_name, record_id)
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
            
            # If not in cache, get from PostgreSQL
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(f'SELECT * FROM "{table_name}" WHERE "id" = %s', (record_id,))
                row = cursor.fetchone()
                
                if row:
                    # Convert to dict, deserialize, and cache
                    data = dict(row)
                    deserialized_data = self._deserialize_data_from_db(data)
                    self._set_cache(cache_key, deserialized_data)
                    return deserialized_data
                
                return None
        except Exception as e:
            logger.error(f"Failed to get record {record_id} from {table_name}: {e}")
            return None
    
    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table (PostgreSQL with optional caching)"""
        try:
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(f'SELECT * FROM "{table_name}"')
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    data = dict(row)
                    deserialized_data = self._deserialize_data_from_db(data)
                    records.append(deserialized_data)
                    
                    # Cache individual records
                    record_id = deserialized_data.get('id')
                    if record_id:
                        cache_key = self.get_cache_key(table_name, record_id)
                        self._set_cache(cache_key, deserialized_data)
                
                return records
        except Exception as e:
            logger.error(f"Failed to get all records from {table_name}: {e}")
            return []
    
    def search_records(self, table_name: str, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search records based on conditions using PostgreSQL"""
        try:
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Build WHERE clause
                where_clauses = []
                values = []
                for field, value in conditions.items():
                    where_clauses.append(f'"{field}" = %s')
                    values.append(value)
                
                where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
                search_sql = f'SELECT * FROM "{table_name}" WHERE {where_sql}'
                
                cursor.execute(search_sql, values)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    data = dict(row)
                    deserialized_data = self._deserialize_data_from_db(data)
                    records.append(deserialized_data)
                    
                    # Cache individual records
                    record_id = deserialized_data.get('id')
                    if record_id:
                        cache_key = self.get_cache_key(table_name, record_id)
                        self._set_cache(cache_key, deserialized_data)
                
                return records
        except Exception as e:
            logger.error(f"Failed to search records in {table_name}: {e}")
            return []
    
    def close_connections(self):
        """Close database connections"""
        try:
            if hasattr(self, 'postgres_conn'):
                self.postgres_conn.close()
            if hasattr(self, 'redis_client') and self.redis_client:
                self.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
    
    def __del__(self):
        """Cleanup connections on object destruction"""
        self.close_connections()
    
    def _ensure_migrations_table(self):
        """Ensure migrations tracking table exists"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS wiregate_migrations (
                        migration_type VARCHAR PRIMARY KEY,
                        completed BOOLEAN NOT NULL DEFAULT FALSE,
                        timestamp TIMESTAMP NOT NULL,
                        source_path TEXT,
                        version VARCHAR NOT NULL DEFAULT '1.0'
                    )
                """)
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise
    
    def set_migration_flag(self, migration_type: str, source_path: str = None) -> bool:
        """Set migration flag to track completed migrations in PostgreSQL"""
        try:
            # Ensure migrations table exists
            self._ensure_migrations_table()
            
            with self.postgres_conn.cursor() as cursor:
                migration_data = {
                    'migration_type': migration_type,
                    'completed': True,
                    'timestamp': datetime.now(),
                    'source_path': source_path or '',
                    'version': '1.0'
                }
                
                cursor.execute("""
                    INSERT INTO wiregate_migrations (migration_type, completed, timestamp, source_path, version)
                    VALUES (%(migration_type)s, %(completed)s, %(timestamp)s, %(source_path)s, %(version)s)
                    ON CONFLICT (migration_type) DO UPDATE SET
                    completed = EXCLUDED.completed,
                    timestamp = EXCLUDED.timestamp,
                    source_path = EXCLUDED.source_path,
                    version = EXCLUDED.version
                """, migration_data)
                
                logger.debug(f"Set migration flag for {migration_type}")
                return True
        except Exception as e:
            logger.error(f"Failed to set migration flag for {migration_type}: {e}")
            return False
    
    def is_migration_completed(self, migration_type: str) -> bool:
        """Check if migration has been completed in PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT completed FROM wiregate_migrations 
                    WHERE migration_type = %s
                """, (migration_type,))
                result = cursor.fetchone()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Failed to check migration status for {migration_type}: {e}")
            return False
    
    def get_migration_info(self, migration_type: str) -> Optional[Dict[str, Any]]:
        """Get migration information from PostgreSQL"""
        try:
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM wiregate_migrations 
                    WHERE migration_type = %s
                """, (migration_type,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get migration info for {migration_type}: {e}")
            return None
    
    def reset_migration_flag(self, migration_type: str) -> bool:
        """Reset migration flag to allow re-migration in PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM wiregate_migrations 
                    WHERE migration_type = %s
                """, (migration_type,))
                
                if cursor.rowcount > 0:
                    logger.debug(f"Reset migration flag for {migration_type}")
                    return True
                else:
                    logger.warning(f"Migration flag for {migration_type} was not found")
                    return False
        except Exception as e:
            logger.error(f"Failed to reset migration flag for {migration_type}: {e}")
            return False
    
    def list_migration_flags(self) -> List[str]:
        """List all migration flags from PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT migration_type FROM wiregate_migrations
                """)
                return [row[0] for row in cursor.fetchall()]
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
                values = []
                for col in columns:
                    if record[col] is None:
                        values.append('NULL')
                    elif isinstance(record[col], str):
                        # Escape single quotes in strings
                        escaped_value = record[col].replace("'", "''")
                        values.append(f"'{escaped_value}'")
                    else:
                        values.append(f"'{record[col]}'")
                
                sql = f"INSERT INTO \"{table_name}\" ({', '.join([f'\"{col}\"' for col in columns])}) VALUES ({', '.join(values)});"
                sql_statements.append(sql)
            
            return sql_statements
        except Exception as e:
            logger.error(f"Failed to dump table {table_name}: {e}")
            return []
    
    def import_sql_statements(self, sql_statements: List[str]) -> bool:
        """Import SQL statements into PostgreSQL"""
        try:
            with self.postgres_conn.cursor() as cursor:
                for sql in sql_statements:
                    if sql.strip().startswith('INSERT INTO'):
                        try:
                            cursor.execute(sql)
                        except Exception as e:
                            logger.warning(f"Failed to execute SQL statement: {sql[:100]}... Error: {e}")
                            continue
            
            logger.debug(f"Imported {len(sql_statements)} SQL statements")
            return True
        except Exception as e:
            logger.error(f"Failed to import SQL statements: {e}")
            return False
    
    def create_jobs_table(self) -> bool:
        """Create jobs table in PostgreSQL"""
        try:
            schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'JobID': 'VARCHAR UNIQUE NOT NULL',
                'Configuration': 'TEXT NOT NULL',
                'Peer': 'TEXT NOT NULL',
                'Field': 'TEXT',
                'Operator': 'TEXT',
                'Value': 'TEXT',
                'CreationDate': 'TIMESTAMP',
                'ExpireDate': 'TIMESTAMP',
                'Action': 'TEXT',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            return self.create_table('PeerJobs', schema)
        except Exception as e:
            logger.error(f"Failed to create jobs table: {e}")
            return False
    
    def create_logs_table(self) -> bool:
        """Create logs table in PostgreSQL"""
        try:
            schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'LogID': 'VARCHAR UNIQUE NOT NULL',
                'JobID': 'VARCHAR NOT NULL',
                'LogDate': 'TIMESTAMP',
                'Status': 'BOOLEAN',
                'Message': 'TEXT',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            return self.create_table('PeerJobLogs', schema)
        except Exception as e:
            logger.error(f"Failed to create logs table: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a custom query"""
        try:
            with self.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                # Convert RealDictRow objects to regular dicts
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []
    
    def close(self):
        """Close the database connection"""
        if self.postgres_conn:
            self.postgres_conn.close()
            logger.info("PostgreSQL database connection closed")
        if hasattr(self, 'redis_client') and self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

# Global database manager instance
_db_manager = None
_db_manager_init_lock = asyncio.Lock()

async def get_redis_manager():
    """Get or create global database manager instance based on DASHBOARD_TYPE (async)"""
    global _db_manager
    if _db_manager is None:
        async with _db_manager_init_lock:
            if _db_manager is None:  # Double-check after acquiring lock
                if DASHBOARD_TYPE.lower() == 'simple':
                    logger.info("Using async SQLite database manager (simple mode)")
                    _db_manager = SQLiteDatabaseManager()
                    await _db_manager._init_sqlite()
                else:
                    logger.info("Using PostgreSQL + Redis database manager (scale mode)")
                    _db_manager = DatabaseManager()
    return _db_manager

def get_redis_manager_sync():
    """Safely get redis manager synchronously, handling both running and non-running event loops"""
    import asyncio
    import threading
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a new event loop in a thread
            result = None
            exception = None
            
            def run_in_thread():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(get_redis_manager())
                    new_loop.close()
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if exception:
                raise exception
            return result
        else:
            return loop.run_until_complete(get_redis_manager())
    except RuntimeError:
        # No event loop exists, create a new one
        return get_redis_manager_sync()

# Compatibility functions for existing code
async def sqlSelect(query: str, params: tuple = None):
    """SQL SELECT compatibility function (async)"""
    manager = await get_redis_manager()
    if isinstance(manager, SQLiteDatabaseManager):
        # For SQLite, return a cursor-like object for compatibility
        return await SQLiteCursor.create_async(query, params)
    else:
        # For PostgreSQL, return cursor
        return PostgreSQLCursor(query, params)

async def sqlUpdate(query: str, params: tuple = None) -> bool:
    """SQL UPDATE/INSERT/DELETE compatibility function (async)"""
    manager = await get_redis_manager()
    
    if isinstance(manager, SQLiteDatabaseManager):
        # For SQLite, convert PostgreSQL-style %s placeholders to ? placeholders
        try:
            sqlite_query = query.replace('%s', '?')
            if manager.conn is None:
                await manager._init_sqlite()
            await manager.conn.execute(sqlite_query, params or ())
            await manager.conn.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite query execution failed: {e}")
            return False
    else:
        # For PostgreSQL, use existing logic
        # Note: PostgreSQL connection has autocommit=True, so commit is automatic
        try:
            with manager.postgres_conn.cursor() as cursor:
                # Ensure params is a tuple or list, and handle None values properly
                if params is None:
                    params = ()
                elif not isinstance(params, (tuple, list)):
                    params = (params,)
                cursor.execute(query, params)
                # Commit is not needed with autocommit=True, but explicit commit ensures consistency
                if not manager.postgres_conn.autocommit:
                    manager.postgres_conn.commit()
                return True
        except Exception as e:
            logger.error(f"PostgreSQL query execution failed: {e}")
            if not manager.postgres_conn.autocommit:
                manager.postgres_conn.rollback()
            return False


class SQLiteCursor:
    """Cursor-like object for SQLite queries to maintain compatibility"""
    
    def __init__(self, query: str, params: tuple = None, results: list = None):
        self.query = query
        self.params = params or ()
        self.results = results or []
        self.current_index = 0
    
    @classmethod
    async def create_async(cls, query: str, params: tuple = None):
        """Async factory method to create and initialize cursor"""
        instance = cls(query, params)
        await instance._execute_query()
        return instance
    
    async def _execute_query(self):
        """Execute the query and store results"""
        manager = await get_redis_manager()
        
        try:
            # Execute query using SQLite manager (async method)
            raw_results = await manager.execute_query(self.query, self.params)
            
            # Convert results to dict-like objects for compatibility
            converted_results = []
            for row in raw_results:
                # Ensure row is a dict with string keys
                if not isinstance(row, dict):
                    # Convert Row or tuple to dict
                    if hasattr(row, 'keys'):
                        row = {str(k): row[k] for k in row.keys()}
                    else:
                        # Tuple - convert to dict using column names
                        # This shouldn't happen with aiosqlite.Row, but handle it
                        row = dict(row)
                
                # Create a dict-like object that supports both attribute and key access
                class DictLikeRecord:
                    def __init__(self, data):
                        # Ensure all keys are strings
                        for key, value in data.items():
                            setattr(self, str(key), value)
                    
                    def __getitem__(self, key):
                        return getattr(self, key)
                    
                    def __contains__(self, key):
                        return hasattr(self, key)
                    
                    def keys(self):
                        return [attr for attr in dir(self) if not attr.startswith('_')]
                    
                    def get(self, key, default=None):
                        return getattr(self, key, default)
                
                record = DictLikeRecord(row)
                converted_results.append(record)
            
            self.results = converted_results
            
        except Exception as e:
            logger.error(f"Failed to execute SQLite query: {self.query}, Error: {e}")
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

class PostgreSQLCursor:
    """Cursor-like object for PostgreSQL queries to maintain compatibility"""
    
    def __init__(self, query: str, params: tuple = None, results: list = None):
        self.query = query
        self.params = params or ()
        self.results = results or []
        self.current_index = 0
        # PostgreSQL queries are sync, so we can execute immediately
        self._execute_query()
    
    def _execute_query(self):
        """Execute the query and store results"""
        # For PostgreSQL, we still need to get the manager synchronously
        # This is a limitation - PostgreSQL operations are sync in this codebase
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new event loop in a thread
                import threading
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(get_redis_manager())
                        new_loop.close()
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                manager = result
            else:
                manager = loop.run_until_complete(get_redis_manager())
        except RuntimeError:
            manager = get_redis_manager_sync()
        
        try:
            with manager.postgres_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(self.query, self.params)
                rows = cursor.fetchall()
                
                # Convert results to dict-like objects for compatibility
                converted_results = []
                for row in rows:
                    # Ensure row is a dict with string keys
                    if not isinstance(row, dict):
                        # Convert Row or tuple to dict
                        if hasattr(row, 'keys'):
                            row = {str(k): row[k] for k in row.keys()}
                        else:
                            # Tuple - convert to dict using column names
                            row = dict(row)
                    
                    # Create a dict-like object that supports both attribute and key access
                    class DictLikeRecord:
                        def __init__(self, data):
                            # Ensure all keys are strings
                            for key, value in data.items():
                                setattr(self, str(key), value)
                        
                        def __getitem__(self, key):
                            return getattr(self, key)
                        
                        def __contains__(self, key):
                            return hasattr(self, key)
                        
                        def keys(self):
                            return [attr for attr in dir(self) if not attr.startswith('_')]
                        
                        def get(self, key, default=None):
                            return getattr(self, key, default)
                    
                    record = DictLikeRecord(dict(row))
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

# Configuration-specific database methods (moved from Core.py)
class ConfigurationDatabase:
    """Database methods specific to Configuration class - now async"""
    
    def __init__(self, configuration_name: str):
        self.configuration_name = configuration_name
        self.manager = None  # Will be initialized asynchronously
        self._init_done = False
    
    async def _ensure_initialized(self):
        """Ensure database manager is initialized"""
        if not self._init_done:
            self.manager = await get_redis_manager()
            
            # Ensure global job and log tables exist
            try:
                if isinstance(self.manager, SQLiteDatabaseManager):
                    if not await self.manager.table_exists('PeerJobs'):
                        await self.manager.create_jobs_table()
                    if not await self.manager.table_exists('PeerJobLogs'):
                        await self.manager.create_logs_table()
                else:
                    # PostgreSQL
                    if not self.manager.table_exists('PeerJobs'):
                        self.manager.create_jobs_table()
                    if not self.manager.table_exists('PeerJobLogs'):
                        self.manager.create_logs_table()
            except Exception as e:
                logger.warning(f"Could not create job/log tables: {e}")
            
            self._init_done = True
    
    async def drop_database(self):
        """Drop all tables for this configuration"""
        await self._ensure_initialized()
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_transfer",
            f"{self.configuration_name}_deleted"
        ]
        
        for table in tables:
            if isinstance(self.manager, SQLiteDatabaseManager):
                await self.manager.drop_table(table)
            else:
                self.manager.drop_table(table)
            # Invalidate cache for this table
            self.manager._invalidate_cache(table)
    
    async def create_database(self, db_name=None):
        """Create database tables for this configuration"""
        await self._ensure_initialized()
        if db_name is None:
            db_name = self.configuration_name
        
        # Define table schemas
        main_table_schema = {
            'id': 'VARCHAR PRIMARY KEY',
            'private_key': 'TEXT',
            'DNS': 'TEXT',
            'endpoint_allowed_ip': 'TEXT',
            'name': 'TEXT',
            'total_receive': 'REAL',
            'total_sent': 'REAL',
            'total_data': 'REAL',
            'endpoint': 'TEXT',
            'status': 'TEXT',
            'latest_handshake': 'TEXT',
            'allowed_ip': 'TEXT',
            'cumu_receive': 'REAL',
            'cumu_sent': 'REAL',
            'cumu_data': 'REAL',
            'traffic': 'TEXT',
            'mtu': 'INTEGER',
            'keepalive': 'INTEGER',
            'remote_endpoint': 'TEXT',
            'preshared_key': 'TEXT',
            'address_v4': 'TEXT',
            'address_v6': 'TEXT',
            'upload_rate_limit': 'INTEGER DEFAULT 0',
            'download_rate_limit': 'INTEGER DEFAULT 0',
            'scheduler_type': 'TEXT DEFAULT \'htb\''
        }
        
        # Create main table
        if isinstance(self.manager, SQLiteDatabaseManager):
            await self.manager.create_table(db_name, main_table_schema)
            await self.manager.create_table(f"{db_name}_restrict_access", main_table_schema)
            transfer_schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'total_receive': 'REAL',
                'total_sent': 'REAL',
                'total_data': 'REAL',
                'cumu_receive': 'REAL',
                'cumu_sent': 'REAL',
                'cumu_data': 'REAL',
                'time': 'TIMESTAMP'
            }
            await self.manager.create_table(f"{db_name}_transfer", transfer_schema)
            await self.manager.create_table(f"{db_name}_deleted", main_table_schema)
        else:
            self.manager.create_table(db_name, main_table_schema)
            self.manager.create_table(f"{db_name}_restrict_access", main_table_schema)
            transfer_schema = {
                'id': 'VARCHAR PRIMARY KEY',
                'total_receive': 'REAL',
                'total_sent': 'REAL',
                'total_data': 'REAL',
                'cumu_receive': 'REAL',
                'cumu_sent': 'REAL',
                'cumu_data': 'REAL',
                'time': 'TIMESTAMP'
            }
            self.manager.create_table(f"{db_name}_transfer", transfer_schema)
            self.manager.create_table(f"{db_name}_deleted", main_table_schema)
    
    async def migrate_database(self):
        """Add missing columns to existing tables and update existing records with default values"""
        await self._ensure_initialized()
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_deleted"
        ]
        
        # Define new fields with their default values and SQL types
        new_fields = {
            'traffic': {'default': '[]', 'type': 'TEXT'},
            'address_v4': {'default': None, 'type': 'TEXT'},
            'address_v6': {'default': None, 'type': 'TEXT'},
            'upload_rate_limit': {'default': 0, 'type': 'INTEGER DEFAULT 0'},
            'download_rate_limit': {'default': 0, 'type': 'INTEGER DEFAULT 0'},
            'scheduler_type': {'default': 'htb', 'type': 'TEXT DEFAULT \'htb\''}
        }
        
        for table in tables:
            if isinstance(self.manager, SQLiteDatabaseManager):
                table_exists = await self.manager.table_exists(table)
            else:
                table_exists = self.manager.table_exists(table)
            
            if not table_exists:
                logger.debug(f"Table {table} does not exist, skipping migration")
                continue
            
            logger.debug(f"Migrating table {table}...")
            
            try:
                # Get appropriate cursor based on database type
                if isinstance(self.manager, SQLiteDatabaseManager):
                    # SQLite - async operations
                    updated_count = 0
                    
                    # Add missing columns
                    for field, field_info in new_fields.items():
                        try:
                            # Check if column exists by trying to select it
                            try:
                                await self.manager.execute_query(f'SELECT "{field}" FROM "{table}" LIMIT 1')
                            except Exception:
                                # Column doesn't exist, add it
                                await self.manager.conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{field}" {field_info["type"]}')
                                await self.manager.conn.commit()
                                logger.debug(f"Added column {field} to table {table}")
                        except Exception as e:
                            # Column might already exist, which is fine
                            logger.debug(f"Column {field} might already exist in table {table}: {e}")
                    
                    # Update existing records with default values
                    for field, field_info in new_fields.items():
                        if field_info['default'] is not None:
                            cursor = await self.manager.conn.execute(f'''
                                UPDATE "{table}" 
                                SET "{field}" = ? 
                                WHERE "{field}" IS NULL
                            ''', (field_info['default'],))
                            updated_count += cursor.rowcount
                            await self.manager.conn.commit()
                    
                else:
                    # PostgreSQL - use connection context manager
                    with self.manager.postgres_conn.cursor() as cursor:
                        updated_count = 0
                        
                        # Add missing columns
                        for field, field_info in new_fields.items():
                            try:
                                cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{field}" {field_info["type"]}')
                                logger.debug(f"Added column {field} to table {table}")
                            except Exception as e:
                                logger.warning(f"Could not add column {field} to table {table}: {e}")
                        
                        # Update existing records with default values
                        for field, field_info in new_fields.items():
                            if field_info['default'] is not None:
                                cursor.execute(f'''
                                    UPDATE "{table}" 
                                    SET "{field}" = %s 
                                    WHERE "{field}" IS NULL
                                ''', (field_info['default'],))
                                updated_count += cursor.rowcount
                        
                        # Invalidate cache for this table
                        self.manager._invalidate_cache(table)
                
                logger.debug(f"Migration completed for table {table}: {updated_count} records updated")
                
            except Exception as e:
                logger.error(f"Error migrating table {table}: {e}")
                # Continue with other tables even if one fails
    
    async def dump_database(self):
        """Dump database data as SQL statements (async generator)"""
        await self._ensure_initialized()
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_transfer",
            f"{self.configuration_name}_deleted"
        ]
        
        for table in tables:
            try:
                if isinstance(self.manager, SQLiteDatabaseManager):
                    sql_statements = await self.manager.dump_table(table)
                else:
                    sql_statements = self.manager.dump_table(table)
                for statement in sql_statements:
                    yield statement
            except Exception as e:
                logger.error(f"Failed to dump table {table}: {e}")
                # Continue with other tables even if one fails
                continue
    
    async def import_database(self, sql_file_path: str) -> bool:
        """Import database from SQL file"""
        await self._ensure_initialized()
        try:
            import os
            if not os.path.exists(sql_file_path):
                return False
            
            # Drop existing tables
            await self.drop_database()
            
            # Create new tables
            await self.create_database()
            await self.migrate_database()
            
            # Read and import SQL statements
            with open(sql_file_path, 'r') as f:
                sql_statements = []
                for line in f.readlines():
                    line = line.rstrip("\n")
                    if len(line) > 0:
                        sql_statements.append(line)
                
                if isinstance(self.manager, SQLiteDatabaseManager):
                    return await self.manager.import_sql_statements(sql_statements)
                else:
                    return self.manager.import_sql_statements(sql_statements)
                
        except Exception as e:
            logger.error(f"Failed to import database: {e}")
            return False
    
    async def get_restricted_peers(self):
        """Get restricted peers"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            return await self.manager.get_all_records(f"{self.configuration_name}_restrict_access")
        else:
            return self.manager.get_all_records(f"{self.configuration_name}_restrict_access")
    
    async def get_peers(self):
        """Get all peers"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            return await self.manager.get_all_records(self.configuration_name)
        else:
            return self.manager.get_all_records(self.configuration_name)
    
    async def search_peer(self, peer_id: str):
        """Search for a specific peer"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            return await self.manager.get_record(self.configuration_name, peer_id)
        else:
            return self.manager.get_record(self.configuration_name, peer_id)
    
    async def insert_peer(self, peer_data: dict):
        """Insert a new peer"""
        await self._ensure_initialized()
        peer_id = peer_data.get('id')
        if peer_id:
            if isinstance(self.manager, SQLiteDatabaseManager):
                result = await self.manager.insert_record(self.configuration_name, peer_id, peer_data)
            else:
                result = self.manager.insert_record(self.configuration_name, peer_id, peer_data)
            # Invalidate cache for this peer
            self.manager._invalidate_cache(self.configuration_name, peer_id)
            return result
        return False
    
    async def update_peer(self, peer_id: str, peer_data: dict):
        """Update a peer"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.update_record(self.configuration_name, peer_id, peer_data)
        else:
            result = self.manager.update_record(self.configuration_name, peer_id, peer_data)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def delete_peer(self, peer_id: str):
        """Delete a peer"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.delete_record(self.configuration_name, peer_id)
        else:
            result = self.manager.delete_record(self.configuration_name, peer_id)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def move_peer_to_restricted(self, peer_id: str):
        """Move peer to restricted access table"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            peer_data = await self.manager.get_record(self.configuration_name, peer_id)
        else:
            peer_data = self.manager.get_record(self.configuration_name, peer_id)
        
        if peer_data:
            # Insert into restricted table
            if isinstance(self.manager, SQLiteDatabaseManager):
                await self.manager.insert_record(f"{self.configuration_name}_restrict_access", peer_id, peer_data)
                await self.manager.delete_record(self.configuration_name, peer_id)
            else:
                self.manager.insert_record(f"{self.configuration_name}_restrict_access", peer_id, peer_data)
                self.manager.delete_record(self.configuration_name, peer_id)
            # Invalidate cache for both tables
            self.manager._invalidate_cache(self.configuration_name, peer_id)
            self.manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            return True
        return False
    
    async def move_peer_from_restricted(self, peer_id: str):
        """Move peer from restricted access table back to main table"""
        await self._ensure_initialized()
        if isinstance(self.manager, SQLiteDatabaseManager):
            peer_data = await self.manager.get_record(f"{self.configuration_name}_restrict_access", peer_id)
        else:
            peer_data = self.manager.get_record(f"{self.configuration_name}_restrict_access", peer_id)
        
        if peer_data:
            # Insert into main table
            if isinstance(self.manager, SQLiteDatabaseManager):
                await self.manager.insert_record(self.configuration_name, peer_id, peer_data)
                await self.manager.delete_record(f"{self.configuration_name}_restrict_access", peer_id)
            else:
                self.manager.insert_record(self.configuration_name, peer_id, peer_data)
                self.manager.delete_record(f"{self.configuration_name}_restrict_access", peer_id)
            # Invalidate cache for both tables
            self.manager._invalidate_cache(self.configuration_name, peer_id)
            self.manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            return True
        return False
    
    async def update_peer_handshake(self, peer_id: str, handshake_time: str, status: str):
        """Update peer handshake information"""
        await self._ensure_initialized()
        updates = {
            'latest_handshake': handshake_time,
            'status': status
        }
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.update_record(self.configuration_name, peer_id, updates)
        else:
            result = self.manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def update_peer_transfer(self, peer_id: str, total_receive: float, total_sent: float, total_data: float):
        """Update peer transfer data"""
        await self._ensure_initialized()
        updates = {
            'total_receive': total_receive,
            'total_sent': total_sent,
            'total_data': total_data
        }
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.update_record(self.configuration_name, peer_id, updates)
        else:
            result = self.manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def update_peer_endpoint(self, peer_id: str, endpoint: str):
        """Update peer endpoint"""
        await self._ensure_initialized()
        updates = {'endpoint': endpoint}
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.update_record(self.configuration_name, peer_id, updates)
        else:
            result = self.manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def reset_peer_data_usage(self, peer_id: str, reset_type: str):
        """Reset peer data usage"""
        await self._ensure_initialized()
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
        
        if isinstance(self.manager, SQLiteDatabaseManager):
            result = await self.manager.update_record(self.configuration_name, peer_id, updates)
        else:
            result = self.manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        self.manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def copy_database_to(self, new_configuration_name: str):
        """Copy database to new configuration name"""
        await self._ensure_initialized()
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_deleted",
            f"{self.configuration_name}_transfer"
        ]
        
        for table in tables:
            new_table = table.replace(self.configuration_name, new_configuration_name)
            
            # Get all records from source table
            if isinstance(self.manager, SQLiteDatabaseManager):
                records = await self.manager.get_all_records(table)
            else:
                records = self.manager.get_all_records(table)
            
            # Insert records into new table
            for record in records:
                record_id = record.get('id')
                if record_id:
                    if isinstance(self.manager, SQLiteDatabaseManager):
                        await self.manager.insert_record(new_table, record_id, record)
                    else:
                        self.manager.insert_record(new_table, record_id, record)
            
            # Invalidate cache for the new table
            self.manager._invalidate_cache(new_table)
        
        return True
    
    async def bulk_insert_peers(self, peers_data: list[dict]):
        """Bulk insert multiple peers into the database"""
        await self._ensure_initialized()
        for peer_data in peers_data:
            peer_id = peer_data.get('id')
            if peer_id:
                if isinstance(self.manager, SQLiteDatabaseManager):
                    await self.manager.insert_record(self.configuration_name, peer_id, peer_data)
                else:
                    self.manager.insert_record(self.configuration_name, peer_id, peer_data)
                # Invalidate cache for this peer
                self.manager._invalidate_cache(self.configuration_name, peer_id)
    
    async def bulk_move_peers_from_restricted(self, peer_ids: list[str]):
        """Bulk move peers from restricted access table back to main table"""
        await self._ensure_initialized()
        for peer_id in peer_ids:
            await self.move_peer_from_restricted(peer_id)

# Static methods for API compatibility
class DatabaseAPI:
    """Static methods for database configuration and management"""
    
    @staticmethod
    def get_config():
        """Get current database configuration"""
        try:
            from ..DashboardConfig import DashboardConfig
            
            # Get configuration from DashboardConfig
            db_config = DashboardConfig.GetConfig("Database", "redis_host")[1]
            if not db_config:
                # Fallback to environment variables if not in config
                from ..Config import (
                    redis_host, redis_port, redis_db, redis_password,
                    postgres_host, postgres_port, postgres_db, postgres_user, postgres_password, postgres_ssl_mode
                )
                
                return {
                    'mode': DASHBOARD_TYPE,
                    'redis': {
                        'host': redis_host,
                        'port': redis_port,
                        'db': redis_db,
                        'password': redis_password if redis_password else '***'
                    },
                    'postgres': {
                        'host': postgres_host,
                        'port': postgres_port,
                        'db': postgres_db,
                        'user': postgres_user,
                        'password': postgres_password if postgres_password else '***',
                        'ssl_mode': postgres_ssl_mode
                    },
                    'cache': {
                        'enabled': True,
                        'ttl': 300
                    }
                }
            
            # Get from DashboardConfig
            # Use masked=False for passwords to get actual values needed for database connections
            redis_host = DashboardConfig.GetConfig("Database", "redis_host")[1]
            redis_port = DashboardConfig.GetConfig("Database", "redis_port")[1]
            redis_db = DashboardConfig.GetConfig("Database", "redis_db")[1]
            redis_password = DashboardConfig.GetConfig("Database", "redis_password", masked=False)[1]
            
            postgres_host = DashboardConfig.GetConfig("Database", "postgres_host")[1]
            postgres_port = DashboardConfig.GetConfig("Database", "postgres_port")[1]
            postgres_db = DashboardConfig.GetConfig("Database", "postgres_db")[1]
            postgres_user = DashboardConfig.GetConfig("Database", "postgres_user")[1]
            postgres_password = DashboardConfig.GetConfig("Database", "postgres_password", masked=False)[1]
            postgres_ssl_mode = DashboardConfig.GetConfig("Database", "postgres_ssl_mode")[1]
            
            cache_enabled = DashboardConfig.GetConfig("Database", "cache_enabled")[1]
            cache_ttl = DashboardConfig.GetConfig("Database", "cache_ttl")[1]
            
            return {
                'mode': DASHBOARD_TYPE,
                'redis': {
                    'host': redis_host,
                    'port': redis_port,
                    'db': redis_db,
                    'password': redis_password  # Actual password for internal use
                },
                'postgres': {
                    'host': postgres_host,
                    'port': postgres_port,
                    'db': postgres_db,
                    'user': postgres_user,
                    'password': postgres_password,  # Actual password for internal use
                    'ssl_mode': postgres_ssl_mode
                },
                'cache': {
                    'enabled': cache_enabled,
                    'ttl': cache_ttl
                }
            }
        except Exception as e:
            logger.error(f"Failed to get database config: {e}")
            return None
    
    @staticmethod
    def update_config(config_data):
        """Update database configuration"""
        try:
            from ..DashboardConfig import DashboardConfig
            
            # Update Redis configuration
            if 'redis' in config_data:
                redis_config = config_data['redis']
                for key, value in redis_config.items():
                    if key == 'password' and value != '***':
                        # Only update password if it's not masked
                        success, error = DashboardConfig.SetConfig("Database", f"redis_{key}", value)
                        if not success:
                            logger.error(f"Failed to update redis_{key}: {error}")
                            return False
                    elif key != 'password':
                        # Update non-password fields
                        success, error = DashboardConfig.SetConfig("Database", f"redis_{key}", value)
                        if not success:
                            logger.error(f"Failed to update redis_{key}: {error}")
                            return False
            
            # Update PostgreSQL configuration
            if 'postgres' in config_data:
                postgres_config = config_data['postgres']
                for key, value in postgres_config.items():
                    if key == 'password' and value != '***':
                        # Only update password if it's not masked
                        success, error = DashboardConfig.SetConfig("Database", f"postgres_{key}", value)
                        if not success:
                            logger.error(f"Failed to update postgres_{key}: {error}")
                            return False
                    elif key != 'password':
                        # Update non-password fields
                        success, error = DashboardConfig.SetConfig("Database", f"postgres_{key}", value)
                        if not success:
                            logger.error(f"Failed to update postgres_{key}: {error}")
                            return False
            
            # Update cache configuration
            if 'cache' in config_data:
                cache_config = config_data['cache']
                for key, value in cache_config.items():
                    success, error = DashboardConfig.SetConfig("Database", f"cache_{key}", value)
                    if not success:
                        logger.error(f"Failed to update cache_{key}: {error}")
                        return False
            
            logger.info("Database configuration updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update database config: {e}")
            return False
    
    @staticmethod
    async def get_stats():
        """Get database statistics"""
        try:
            manager = await get_redis_manager()
            
            # Get basic stats
            stats = {
                'total_peers': 0,
                'total_configurations': 0,
                'redis_connected': False,
                'postgres_connected': False
            }
            
            # Check Redis connection
            try:
                if manager.redis_client:
                    manager.redis_client.ping()
                    stats['redis_connected'] = True
            except Exception as e:
                logger.debug(f"Redis connection check failed: {e}")
                stats['redis_connected'] = False
            
            # Check PostgreSQL connection
            try:
                with manager.postgres_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    stats['postgres_connected'] = True
            except Exception as e:
                logger.debug(f"PostgreSQL connection check failed: {e}")
                stats['postgres_connected'] = False
            
            # Get configuration count and total peers
            try:
                with manager.postgres_conn.cursor() as cursor:
                    # Get configuration tables by finding tables that have auxiliary tables
                    # (tables with _restrict_access, _transfer, _deleted suffixes indicate main config tables)
                    cursor.execute("""
                        WITH config_names AS (
                            SELECT DISTINCT 
                                CASE 
                                    WHEN table_name LIKE '%_restrict_access' THEN REPLACE(table_name, '_restrict_access', '')
                                    WHEN table_name LIKE '%_transfer' THEN REPLACE(table_name, '_transfer', '')
                                    WHEN table_name LIKE '%_deleted' THEN REPLACE(table_name, '_deleted', '')
                                END as config_name
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND (table_name LIKE '%_restrict_access' 
                                 OR table_name LIKE '%_transfer' 
                                 OR table_name LIKE '%_deleted')
                        )
                        SELECT config_name FROM config_names 
                        WHERE config_name IS NOT NULL
                        ORDER BY config_name
                    """)
                    config_tables = [row[0] for row in cursor.fetchall()]
                    stats['total_configurations'] = len(config_tables)
                    
                    # Count total peers across all configuration tables
                    total_peers = 0
                    for table_name in config_tables:
                        try:
                            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                            peer_count = cursor.fetchone()[0] or 0
                            total_peers += peer_count
                        except Exception as e:
                            logger.debug(f"Error counting peers in table {table_name}: {e}")
                            continue
                    
                    stats['total_peers'] = total_peers
                    
            except Exception as e:
                logger.debug(f"Error getting database stats: {e}")
                pass
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return None
    
    @staticmethod
    def test_connections(config_data):
        """Test database connections with given configuration"""
        try:
            results = {
                'success': True,
                'data': {},
                'message': 'All connections successful'
            }
            
            # Test Redis connection
            try:
                import redis
                redis_client = redis.Redis(
                    host=config_data['redis']['host'],
                    port=config_data['redis']['port'],
                    db=config_data['redis']['db'],
                    password=config_data['redis']['password'],
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                redis_client.ping()
                results['data']['redis'] = {'connected': True, 'message': 'Redis connection successful'}
            except Exception as e:
                results['data']['redis'] = {'connected': False, 'message': f'Redis connection failed: {str(e)}'}
                results['success'] = False
            
            # Test PostgreSQL connection
            try:
                import psycopg2
                postgres_conn = psycopg2.connect(
                    host=config_data['postgres']['host'],
                    port=config_data['postgres']['port'],
                    database=config_data['postgres']['db'],
                    user=config_data['postgres']['user'],
                    password=config_data['postgres']['password'],
                    sslmode=config_data['postgres']['ssl_mode']
                )
                with postgres_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                postgres_conn.close()
                results['data']['postgres'] = {'connected': True, 'message': 'PostgreSQL connection successful'}
            except Exception as e:
                results['data']['postgres'] = {'connected': False, 'message': f'PostgreSQL connection failed: {str(e)}'}
                results['success'] = False
            
            if not results['success']:
                results['message'] = 'One or more connections failed'
            
            return results
        except Exception as e:
            logger.error(f"Failed to test database connections: {e}")
            return {
                'success': False,
                'data': {},
                'message': f'Connection test failed: {str(e)}'
            }
    
    
    @staticmethod
    async def clear_cache():
        """Clear database cache"""
        try:
            manager = await get_redis_manager()
            
            if manager.redis_client:
                # Clear all cache keys
                keys = manager.redis_client.keys("wiregate:cache:*")
                if keys:
                    manager.redis_client.delete(*keys)
                
                return {
                    'success': True,
                    'message': f'Cleared {len(keys)} cache entries'
                }
            else:
                return {
                    'success': False,
                    'message': 'Redis not available'
                }
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return {
                'success': False,
                'message': f'Failed to clear cache: {str(e)}'
            }

# Initialize database manager on module import
try:
    manager = get_redis_manager_sync()
    if isinstance(manager, SQLiteDatabaseManager):
        logger.info("SQLite database manager initialized successfully")
    else:
        logger.info("PostgreSQL + Redis database manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database manager: {e}")
    # Fallback to a no-op implementation
    class NoOpManager:
        def __getattr__(self, name):
            # Return appropriate defaults for common methods
            if name in ['get_restricted_peers', 'get_peers', 'get_all_records']:
                return lambda *args, **kwargs: []
            elif name in ['search_peer', 'get_peer']:
                return lambda *args, **kwargs: None
            elif name in ['insert_peer', 'update_peer', 'delete_peer', 'create_database', 'drop_database', 'migrate_database']:
                return lambda *args, **kwargs: True
            else:
                return lambda *args, **kwargs: None
    
    _db_manager = NoOpManager()

# SQLite to PostgreSQL Migration Functions
def migrate_sqlite_to_postgres():
    """Migrate any existing SQLite databases to PostgreSQL"""
    logger.info("Checking for SQLite databases to migrate...")
    
    # Get database manager to check migration status
    try:
        db_manager = get_redis_manager_sync()
        
        # Check if migration has already been completed
        if db_manager.is_migration_completed('sqlite_to_postgres'):
            migration_info = db_manager.get_migration_info('sqlite_to_postgres')
            logger.info(f"SQLite to PostgreSQL migration already completed at {migration_info.get('timestamp', 'unknown time')}")
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
            if migrate_sqlite_file_to_postgres(sqlite_path):
                migrated_count += 1
                logger.info(f"Successfully migrated {sqlite_path}")
            else:
                logger.warning(f"Failed to migrate {sqlite_path}")
        except Exception as e:
            logger.error(f"Error migrating {sqlite_path}: {e}")
    
    # Set migration flag if any databases were migrated
    if migrated_count > 0:
        try:
            db_manager = get_redis_manager_sync()
            db_manager.set_migration_flag('sqlite_to_postgres', f"{migrated_count} databases")
            logger.info(f"Migration completed: {migrated_count} SQLite databases migrated to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to set migration flag: {e}")
    else:
        logger.info("No SQLite databases were migrated")
    
    return migrated_count

def migrate_sqlite_file_to_postgres(sqlite_path: str) -> bool:
    """Migrate a specific SQLite file to PostgreSQL"""
    try:
        # Get database manager to check if this specific file has been migrated
        db_manager = get_redis_manager_sync()
        
        # Create a unique migration key for this specific file
        file_basename = os.path.basename(sqlite_path)
        migration_key = f"sqlite_file_{file_basename}"
        
        # Check if this specific file has already been migrated
        if db_manager.is_migration_completed(migration_key):
            migration_info = db_manager.get_migration_info(migration_key)
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
                
                # Create table in PostgreSQL if it doesn't exist
                if not db_manager.table_exists(table_name):
                    db_manager.create_table(table_name, schema)
                
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
                    
                    # Insert into PostgreSQL
                    db_manager.insert_record(table_name, record_id, record_data)
                
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
                db_manager.set_migration_flag(migration_key, sqlite_path)
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
        # Check dashboard type - only run migration in scale mode
        if DASHBOARD_TYPE.lower() == 'simple':
            logger.info("Simple mode detected, using SQLite database directly")
            return False
        
        # Only run migration if PostgreSQL is available (scale mode)
        db_manager = get_redis_manager_sync()
        if db_manager is None:
            logger.warning("Database manager not available, skipping SQLite migration")
            return False
        
        # Test PostgreSQL connection
        db_manager.postgres_conn.cursor().execute("SELECT 1")
        
        # Check if migration has already been completed
        if db_manager.is_migration_completed('sqlite_to_postgres'):
            migration_info = db_manager.get_migration_info('sqlite_to_postgres')
            logger.info(f"SQLite to PostgreSQL migration already completed at {migration_info.get('timestamp', 'unknown time')}")
            return True
        
        # Run migration
        migrated_count = migrate_sqlite_to_postgres()
        return migrated_count > 0
        
    except Exception as e:
        logger.error(f"Error during SQLite migration check: {e}")
        return False

def reset_sqlite_migration_flags():
    """Reset all SQLite migration flags to allow re-migration"""
    try:
        db_manager = get_redis_manager_sync()
        if db_manager is None:
            logger.warning("Database manager not available, cannot reset migration flags")
            return False
        
        # Get all migration flags
        migration_flags = db_manager.list_migration_flags()
        reset_count = 0
        
        for flag in migration_flags:
            if flag.startswith('sqlite') or flag == 'sqlite_to_postgres':
                if db_manager.reset_migration_flag(flag):
                    reset_count += 1
        
        logger.info(f"Reset {reset_count} SQLite migration flags")
        return reset_count > 0
        
    except Exception as e:
        logger.error(f"Error resetting migration flags: {e}")
        return False

def get_migration_status():
    """Get current migration status"""
    try:
        db_manager = get_redis_manager_sync()
        if db_manager is None:
            return {"error": "Database manager not available"}
        
        migration_flags = db_manager.list_migration_flags()
        status = {}
        
        for flag in migration_flags:
            info = db_manager.get_migration_info(flag)
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
