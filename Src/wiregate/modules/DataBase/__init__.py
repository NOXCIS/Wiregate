"""
DataBase module package for Wiregate
Contains database management, Redis operations, and SQL compatibility
"""

from .DataBaseManager import (
    DatabaseManager,
    get_redis_manager,
    sqlSelect,
    sqlUpdate,
    RedisCursor,
    LegacySqldb,
    ConfigurationDatabase,
    migrate_sqlite_to_redis,
    migrate_sqlite_file_to_redis,
    check_and_migrate_sqlite_databases,
    reset_sqlite_migration_flags,
    get_migration_status
)

__all__ = [
    'DatabaseManager',
    'get_redis_manager',
    'sqlSelect',
    'sqlUpdate',
    'RedisCursor',
    'LegacySqldb',
    'ConfigurationDatabase',
    'migrate_sqlite_to_redis',
    'migrate_sqlite_file_to_redis',
    'check_and_migrate_sqlite_databases',
    'reset_sqlite_migration_flags',
    'get_migration_status'
]
