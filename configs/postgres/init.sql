-- PostgreSQL initialization script for WireGate
-- This script runs when the PostgreSQL container is first created

-- Create the wiregate database if it doesn't exist
-- (This is handled by the POSTGRES_DB environment variable)

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create a migrations table to track database migrations
CREATE TABLE IF NOT EXISTS wiregate_migrations (
    migration_type VARCHAR PRIMARY KEY,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_path TEXT,
    version VARCHAR NOT NULL DEFAULT '1.0'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_wiregate_migrations_timestamp ON wiregate_migrations(timestamp);
CREATE INDEX IF NOT EXISTS idx_wiregate_migrations_completed ON wiregate_migrations(completed);

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE wiregate TO wiregate_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wiregate_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO wiregate_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO wiregate_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO wiregate_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO wiregate_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO wiregate_user;

-- Log the initialization
INSERT INTO wiregate_migrations (migration_type, completed, source_path, version) 
VALUES ('database_initialization', TRUE, 'init.sql', '1.0')
ON CONFLICT (migration_type) DO NOTHING;
