"""
DataBase module package for Wiregate
Contains database management, Redis operations, and SQL compatibility
"""

from .DataBaseManager import (
    DatabaseManager,
    SQLiteDatabaseManager,
    get_redis_manager,
    sqlSelect,
    sqlUpdate,
    PostgreSQLCursor,
    LegacySqldb,
    ConfigurationDatabase,
    migrate_sqlite_to_postgres,
    migrate_sqlite_file_to_postgres,
    check_and_migrate_sqlite_databases,
    reset_sqlite_migration_flags,
    get_migration_status
)

__all__ = [
    'DatabaseManager',
    'SQLiteDatabaseManager',
    'get_redis_manager',
    'sqlSelect',
    'sqlUpdate',
    'PostgreSQLCursor',
    'LegacySqldb',
    'ConfigurationDatabase',
    'migrate_sqlite_to_postgres',
    'migrate_sqlite_file_to_postgres',
    'check_and_migrate_sqlite_databases',
    'reset_sqlite_migration_flags',
    'get_migration_status'
]
