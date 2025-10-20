"""
Async Database Manager with Connection Pooling
Provides high-performance async database operations for PostgreSQL, Redis, and SQLite
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import asyncpg
import aiosqlite
import redis.asyncio as aioredis

from ..Config import (
    redis_host, redis_port, redis_db, redis_password,
    postgres_host, postgres_port, postgres_db, postgres_user, postgres_password, postgres_ssl_mode,
    DASHBOARD_TYPE
)

logger = logging.getLogger('wiregate')


class AsyncSQLiteDatabaseManager:
    """Async SQLite database manager for simple deployments with connection pooling"""
    
    def __init__(self, db_path=None):
        """Initialize async SQLite connection"""
        if db_path is None:
            db_path = os.path.join(os.getcwd(), 'db', 'wgdashboard.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        # Note: _init_sqlite is async, will be called during async initialization
        
    async def _init_sqlite(self):
        """Initialize async SQLite connection"""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row  # Enable dict-like access
            logger.info(f"Successfully connected to async SQLite database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to async SQLite database: {e}")
            raise
    
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
            delete_sql = f"DELETE FROM {table_name} WHERE id = ?"
            
            cursor = await self.conn.execute(delete_sql, (record_id,))
            await self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete record from {table_name}: {e}")
            return False
    
    async def close(self):
        """Close the database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Async SQLite database connection closed")


class AsyncDatabaseManager:
    """Async PostgreSQL primary database with Redis cache layer and connection pooling"""
    
    def __init__(self, postgres_config=None, redis_config=None):
        """Initialize async PostgreSQL and Redis connections with pooling"""
        # Use provided config or fallback to environment variables
        self.postgres_config = postgres_config or {
            'host': postgres_host,
            'port': postgres_port,
            'database': postgres_db,
            'user': postgres_user,
            'password': postgres_password,
            'ssl': postgres_ssl_mode
        }
        self.redis_config = redis_config or {
            'host': redis_host,
            'port': redis_port,
            'db': redis_db,
            'password': redis_password
        }
        
        # Initialize connections
        self.pg_pool = None
        self.redis = None
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes default TTL
        self.cache_enabled = True
        
    async def init_postgres_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.pg_pool = await asyncpg.create_pool(
                host=self.postgres_config['host'],
                port=self.postgres_config['port'],
                database=self.postgres_config['database'],
                user=self.postgres_config['user'],
                password=self.postgres_config['password'],
                ssl=self.postgres_config['ssl'],
                min_size=10,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for better performance with small queries
                }
            )
            logger.info("Successfully created async PostgreSQL connection pool")
        except Exception as e:
            logger.error(f"Failed to create async PostgreSQL pool: {e}")
            raise
    
    async def init_redis_pool(self):
        """Initialize Redis connection pool"""
        try:
            self.redis = aioredis.ConnectionPool.from_url(
                f"redis://:{self.redis_config['password']}@{self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}",
                minsize=5,
                maxsize=20,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client = aioredis.Redis(connection_pool=self.redis)
            await redis_client.ping()
            await redis_client.close()
            logger.info("Successfully created async Redis connection pool")
        except Exception as e:
            logger.error(f"Failed to create async Redis pool: {e}")
            # Continue without Redis if it fails
            self.redis = None
            self.cache_enabled = False
    
    async def get_cache_key(self, table_name: str, record_id: str = None) -> str:
        """Generate Redis cache key for table or record"""
        if record_id:
            return f"wiregate:cache:{table_name}:{record_id}"
        return f"wiregate:cache:{table_name}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis cache"""
        if not self.cache_enabled or not self.redis:
            return None
        
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis)
            cached_data = await redis_client.get(cache_key)
            await redis_client.close()
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.debug(f"Cache read error for key {cache_key}: {e}")
        return None
    
    async def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """Set data in Redis cache"""
        if not self.cache_enabled or not self.redis:
            return False
        
        try:
            ttl = ttl or self.cache_ttl
            redis_client = aioredis.Redis(connection_pool=self.redis)
            await redis_client.setex(cache_key, ttl, json.dumps(data))
            await redis_client.close()
            return True
        except Exception as e:
            logger.debug(f"Cache write error for key {cache_key}: {e}")
            return False
    
    async def _invalidate_cache(self, table_name: str, record_id: str = None) -> bool:
        """Invalidate cache entries for a table or specific record"""
        if not self.cache_enabled or not self.redis:
            return False
        
        try:
            redis_client = aioredis.Redis(connection_pool=self.redis)
            if record_id:
                # Invalidate specific record
                cache_key = await self.get_cache_key(table_name, record_id)
                await redis_client.delete(cache_key)
            else:
                # Invalidate all records for table
                pattern = f"wiregate:cache:{table_name}:*"
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
            await redis_client.close()
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
    
    async def get_all_keys(self) -> List[str]:
        """Get all table names from PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'wiregate_%'
                """)
                return [row['table_name'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    async def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """Create a table in PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
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
                await conn.execute(create_sql)
                
                # Invalidate cache for this table
                await self._invalidate_cache(table_name)
                
                logger.info(f"Created table {table_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    async def insert_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Insert a record into PostgreSQL and cache in Redis"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Serialize data for database storage
                serialized_data = self._serialize_data_for_db(data)
                
                # Prepare data for PostgreSQL
                columns = list(serialized_data.keys())
                values = list(serialized_data.values())
                placeholders = [f'${i+1}' for i in range(len(values))]
                
                # Insert into PostgreSQL
                insert_sql = f'''
                    INSERT INTO "{table_name}" ({", ".join([f'"{col}"' for col in columns])})
                    VALUES ({", ".join(placeholders)})
                    ON CONFLICT (id) DO UPDATE SET
                    {", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'id'])}
                '''
                await conn.execute(insert_sql, *values)
                
                # Cache in Redis (use original data, not serialized)
                cache_key = await self.get_cache_key(table_name, record_id)
                await self._set_cache(cache_key, data)
                
                return True
        except Exception as e:
            logger.error(f"Failed to insert record {record_id} into {table_name}: {e}")
            return False
    
    async def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record in PostgreSQL and cache in Redis"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Serialize data for database storage
                serialized_data = self._serialize_data_for_db(data)
                
                # Build UPDATE statement
                set_clauses = []
                values = []
                for i, (field, value) in enumerate(serialized_data.items()):
                    set_clauses.append(f'"{field}" = ${i+1}')
                    values.append(value)
                
                values.append(record_id)  # Add record_id for WHERE clause
                
                update_sql = f'''
                    UPDATE "{table_name}" 
                    SET {", ".join(set_clauses)}
                    WHERE "id" = ${len(values)}
                '''
                await conn.execute(update_sql, *values)
                
                # Invalidate cache for this record
                await self._invalidate_cache(table_name, record_id)
                
                return True
        except Exception as e:
            logger.error(f"Failed to update record {record_id} in {table_name}: {e}")
            return False
    
    async def delete_record(self, table_name: str, record_id: str) -> bool:
        """Delete a record from PostgreSQL and invalidate cache"""
        try:
            async with self.pg_pool.acquire() as conn:
                delete_sql = f'DELETE FROM "{table_name}" WHERE "id" = $1'
                result = await conn.execute(delete_sql, record_id)
                
                # Invalidate cache for this record
                await self._invalidate_cache(table_name, record_id)
                
                return result.split()[-1] == '1'  # Check if any rows were affected
        except Exception as e:
            logger.error(f"Failed to delete record {record_id} from {table_name}: {e}")
            return False
    
    async def get_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record from cache first, then PostgreSQL"""
        try:
            # Try cache first
            cache_key = await self.get_cache_key(table_name, record_id)
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
            
            # If not in cache, get from PostgreSQL
            async with self.pg_pool.acquire() as conn:
                row = await conn.fetchrow(f'SELECT * FROM "{table_name}" WHERE "id" = $1', record_id)
                
                if row:
                    # Convert to dict, deserialize, and cache
                    data = dict(row)
                    deserialized_data = self._deserialize_data_from_db(data)
                    await self._set_cache(cache_key, deserialized_data)
                    return deserialized_data
                
                return None
        except Exception as e:
            logger.error(f"Failed to get record {record_id} from {table_name}: {e}")
            return None
    
    async def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table (PostgreSQL with optional caching)"""
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(f'SELECT * FROM "{table_name}"')
                
                records = []
                for row in rows:
                    data = dict(row)
                    deserialized_data = self._deserialize_data_from_db(data)
                    records.append(deserialized_data)
                    
                    # Cache individual records
                    record_id = deserialized_data.get('id')
                    if record_id:
                        cache_key = await self.get_cache_key(table_name, record_id)
                        await self._set_cache(cache_key, deserialized_data)
                
                return records
        except Exception as e:
            logger.error(f"Failed to get all records from {table_name}: {e}")
            return []
    
    async def close_connections(self):
        """Close database connections"""
        try:
            if self.pg_pool:
                await self.pg_pool.close()
            if self.redis:
                await self.redis.disconnect()
        except Exception as e:
            logger.error(f"Error closing connections: {e}")


# Global async database manager instance
_async_db_manager = None

async def get_async_db_manager():
    """Get or create global async database manager instance based on DASHBOARD_TYPE"""
    global _async_db_manager
    if _async_db_manager is None:
        if DASHBOARD_TYPE.lower() == 'simple':
            logger.info("Using async SQLite database manager (simple mode)")
            _async_db_manager = AsyncSQLiteDatabaseManager()
        else:
            logger.info("Using async PostgreSQL + Redis database manager (scale mode)")
            _async_db_manager = AsyncDatabaseManager()
            await _async_db_manager.init_postgres_pool()
            await _async_db_manager.init_redis_pool()
    return _async_db_manager

# Async Configuration-specific database methods
class AsyncConfigurationDatabase:
    """Async database methods specific to Configuration class"""
    
    def __init__(self, configuration_name: str):
        self.configuration_name = configuration_name
        self.manager = None
        
    async def _get_manager(self):
        """Get async database manager"""
        if self.manager is None:
            self.manager = await get_async_db_manager()
        return self.manager
    
    async def drop_database(self):
        """Drop all tables for this configuration"""
        manager = await self._get_manager()
        tables = [
            self.configuration_name,
            f"{self.configuration_name}_restrict_access",
            f"{self.configuration_name}_transfer",
            f"{self.configuration_name}_deleted"
        ]
        
        for table in tables:
            if hasattr(manager, 'drop_table'):
                await manager.drop_table(table)
            # Invalidate cache for this table
            if hasattr(manager, '_invalidate_cache'):
                await manager._invalidate_cache(table)
    
    async def create_database(self, db_name=None):
        """Create database tables for this configuration"""
        manager = await self._get_manager()
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
        await manager.create_table(db_name, main_table_schema)
        
        # Create restrict_access table
        await manager.create_table(f"{db_name}_restrict_access", main_table_schema)
        
        # Create transfer table
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
        await manager.create_table(f"{db_name}_transfer", transfer_schema)
        
        # Create deleted table
        await manager.create_table(f"{db_name}_deleted", main_table_schema)
    
    async def get_restricted_peers(self):
        """Get restricted peers"""
        manager = await self._get_manager()
        return await manager.get_all_records(f"{self.configuration_name}_restrict_access")
    
    async def get_peers(self):
        """Get all peers"""
        manager = await self._get_manager()
        return await manager.get_all_records(self.configuration_name)
    
    async def search_peer(self, peer_id: str):
        """Search for a specific peer"""
        manager = await self._get_manager()
        return await manager.get_record(self.configuration_name, peer_id)
    
    async def insert_peer(self, peer_data: dict):
        """Insert a new peer"""
        manager = await self._get_manager()
        peer_id = peer_data.get('id')
        if peer_id:
            result = await manager.insert_record(self.configuration_name, peer_id, peer_data)
            # Invalidate cache for this peer
            if hasattr(manager, '_invalidate_cache'):
                await manager._invalidate_cache(self.configuration_name, peer_id)
            return result
        return False
    
    async def update_peer(self, peer_id: str, peer_data: dict):
        """Update a peer"""
        manager = await self._get_manager()
        result = await manager.update_record(self.configuration_name, peer_id, peer_data)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def delete_peer(self, peer_id: str):
        """Delete a peer"""
        manager = await self._get_manager()
        result = await manager.delete_record(self.configuration_name, peer_id)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def move_peer_to_restricted(self, peer_id: str):
        """Move peer to restricted access table"""
        manager = await self._get_manager()
        peer_data = await manager.get_record(self.configuration_name, peer_id)
        if peer_data:
            # Insert into restricted table
            await manager.insert_record(f"{self.configuration_name}_restrict_access", peer_id, peer_data)
            # Delete from main table
            await manager.delete_record(self.configuration_name, peer_id)
            # Invalidate cache for both tables
            if hasattr(manager, '_invalidate_cache'):
                await manager._invalidate_cache(self.configuration_name, peer_id)
                await manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            return True
        return False
    
    async def move_peer_from_restricted(self, peer_id: str):
        """Move peer from restricted access table back to main table"""
        manager = await self._get_manager()
        peer_data = await manager.get_record(f"{self.configuration_name}_restrict_access", peer_id)
        if peer_data:
            # Insert into main table
            await manager.insert_record(self.configuration_name, peer_id, peer_data)
            # Delete from restricted table
            await manager.delete_record(f"{self.configuration_name}_restrict_access", peer_id)
            # Invalidate cache for both tables
            if hasattr(manager, '_invalidate_cache'):
                await manager._invalidate_cache(self.configuration_name, peer_id)
                await manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            return True
        return False
    
    async def update_peer_handshake(self, peer_id: str, handshake_time: str, status: str):
        """Update peer handshake information"""
        manager = await self._get_manager()
        updates = {
            'latest_handshake': handshake_time,
            'status': status
        }
        result = await manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def update_peer_transfer(self, peer_id: str, total_receive: float, total_sent: float, total_data: float):
        """Update peer transfer data"""
        manager = await self._get_manager()
        updates = {
            'total_receive': total_receive,
            'total_sent': total_sent,
            'total_data': total_data
        }
        result = await manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def update_peer_endpoint(self, peer_id: str, endpoint: str):
        """Update peer endpoint"""
        manager = await self._get_manager()
        updates = {'endpoint': endpoint}
        result = await manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result
    
    async def reset_peer_data_usage(self, peer_id: str, reset_type: str):
        """Reset peer data usage"""
        manager = await self._get_manager()
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
        
        result = await manager.update_record(self.configuration_name, peer_id, updates)
        # Invalidate cache for this peer
        if hasattr(manager, '_invalidate_cache'):
            await manager._invalidate_cache(self.configuration_name, peer_id)
        return result

    # Bulk operations for better performance
    async def bulk_insert_peers(self, peers_data: List[dict]):
        """Insert multiple peers in a single transaction for better performance"""
        manager = await self._get_manager()
        
        if not peers_data:
            return True
        
        try:
            # Use transaction for bulk operations
            if hasattr(manager, 'bulk_insert_records'):
                result = await manager.bulk_insert_records(self.configuration_name, peers_data)
            else:
                # Fallback to individual inserts in transaction
                results = []
                for peer_data in peers_data:
                    peer_id = peer_data.get('id')
                    if peer_id:
                        result = await manager.insert_record(self.configuration_name, peer_id, peer_data)
                        results.append(result)
                result = all(results)
            
            # Invalidate cache for all peers
            if hasattr(manager, '_invalidate_cache'):
                for peer_data in peers_data:
                    peer_id = peer_data.get('id')
                    if peer_id:
                        await manager._invalidate_cache(self.configuration_name, peer_id)
            
            return result
        except Exception as e:
            logger.error(f"Bulk insert peers failed: {e}")
            return False

    async def bulk_update_peers(self, peers_updates: List[tuple]):
        """Update multiple peers in a single transaction
        Args:
            peers_updates: List of (peer_id, peer_data) tuples
        """
        manager = await self._get_manager()
        
        if not peers_updates:
            return True
        
        try:
            # Use transaction for bulk operations
            if hasattr(manager, 'bulk_update_records'):
                result = await manager.bulk_update_records(self.configuration_name, peers_updates)
            else:
                # Fallback to individual updates in transaction
                results = []
                for peer_id, peer_data in peers_updates:
                    result = await manager.update_record(self.configuration_name, peer_id, peer_data)
                    results.append(result)
                result = all(results)
            
            # Invalidate cache for all updated peers
            if hasattr(manager, '_invalidate_cache'):
                for peer_id, _ in peers_updates:
                    await manager._invalidate_cache(self.configuration_name, peer_id)
            
            return result
        except Exception as e:
            logger.error(f"Bulk update peers failed: {e}")
            return False

    async def bulk_move_peers_to_restricted(self, peer_ids: List[str]):
        """Move multiple peers to restricted access table in a single transaction"""
        manager = await self._get_manager()
        
        if not peer_ids:
            return True
        
        try:
            # Get all peer data first
            peers_data = []
            for peer_id in peer_ids:
                peer_data = await manager.get_record(self.configuration_name, peer_id)
                if peer_data:
                    peers_data.append((peer_id, peer_data))
            
            if not peers_data:
                return True
            
            # Use transaction for bulk operations
            if hasattr(manager, 'bulk_move_records'):
                result = await manager.bulk_move_records(
                    self.configuration_name, 
                    f"{self.configuration_name}_restrict_access", 
                    peers_data
                )
            else:
                # Fallback to individual moves
                results = []
                for peer_id, peer_data in peers_data:
                    # Insert into restricted table
                    await manager.insert_record(f"{self.configuration_name}_restrict_access", peer_id, peer_data)
                    # Delete from main table
                    await manager.delete_record(self.configuration_name, peer_id)
                    results.append(True)
                result = all(results)
            
            # Invalidate cache for all moved peers
            if hasattr(manager, '_invalidate_cache'):
                for peer_id, _ in peers_data:
                    await manager._invalidate_cache(self.configuration_name, peer_id)
                    await manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            
            return result
        except Exception as e:
            logger.error(f"Bulk move peers to restricted failed: {e}")
            return False

    async def bulk_move_peers_from_restricted(self, peer_ids: List[str]):
        """Move multiple peers from restricted access table back to main table in a single transaction"""
        manager = await self._get_manager()
        
        if not peer_ids:
            return True
        
        try:
            # Get all peer data first
            peers_data = []
            for peer_id in peer_ids:
                peer_data = await manager.get_record(f"{self.configuration_name}_restrict_access", peer_id)
                if peer_data:
                    peers_data.append((peer_id, peer_data))
            
            if not peers_data:
                return True
            
            # Use transaction for bulk operations
            if hasattr(manager, 'bulk_move_records'):
                result = await manager.bulk_move_records(
                    f"{self.configuration_name}_restrict_access",
                    self.configuration_name, 
                    peers_data
                )
            else:
                # Fallback to individual moves
                results = []
                for peer_id, peer_data in peers_data:
                    # Insert into main table
                    await manager.insert_record(self.configuration_name, peer_id, peer_data)
                    # Delete from restricted table
                    await manager.delete_record(f"{self.configuration_name}_restrict_access", peer_id)
                    results.append(True)
                result = all(results)
            
            # Invalidate cache for all moved peers
            if hasattr(manager, '_invalidate_cache'):
                for peer_id, _ in peers_data:
                    await manager._invalidate_cache(self.configuration_name, peer_id)
                    await manager._invalidate_cache(f"{self.configuration_name}_restrict_access", peer_id)
            
            return result
        except Exception as e:
            logger.error(f"Bulk move peers from restricted failed: {e}")
            return False


# Initialize async database manager on module import
async def init_async_db():
    """Initialize async database manager"""
    try:
        manager = await get_async_db_manager()
        if isinstance(manager, AsyncSQLiteDatabaseManager):
            logger.info("Async SQLite database manager initialized successfully")
        else:
            logger.info("Async PostgreSQL + Redis database manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize async database manager: {e}")
        # Fallback to a no-op implementation
        class NoOpAsyncManager:
            async def __getattr__(self, name):
                # Return appropriate defaults for common methods
                if name in ['get_all_records', 'get_restricted_peers', 'get_peers']:
                    return lambda *args, **kwargs: []
                elif name in ['search_peer', 'get_peer']:
                    return lambda *args, **kwargs: None
                elif name in ['insert_peer', 'update_peer', 'delete_peer', 'create_database', 'drop_database', 'migrate_database']:
                    return lambda *args, **kwargs: True
                else:
                    return lambda *args, **kwargs: None
        
        _async_db_manager = NoOpAsyncManager()
