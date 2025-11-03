# WireGate Database System Architecture

This document provides a comprehensive overview of the WireGate database system architecture, including the hybrid PostgreSQL + Redis setup, migration system, and data flow patterns.

## Overview

WireGate uses a sophisticated **hybrid database architecture** that combines PostgreSQL as the primary database with Redis as a high-performance cache layer. This design provides optimal performance, scalability, and reliability while maintaining backward compatibility with legacy SQLite systems.

## Architecture Components

### 1. Application Layer

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vue.js Frontend│    │   Flask API     │    │  Core Modules   │    │  Configuration  │
│                 │    │   Routes        │    │                 │    │  Management     │
│ • DatabaseSettings│◄──►│ • /api/database│◄──►│ • DataBaseManager│◄──►│ • DashboardConfig│
│ • LDAPSettings   │    │ • /api/ldap    │    │ • Core.py       │    │ • ConfigEnv.py  │
│ • EmailSettings  │    │ • /api/email   │    │ • ShareLink.py  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. Database Layer - Hybrid Architecture

#### PostgreSQL (Primary Database)
- **Purpose**: Persistent data storage and primary data source
- **Connection**: `postgres:5432`
- **Database**: `wiregate`
- **User**: `wiregate_user`
- **Features**:
  - ACID compliance
  - Complex queries and transactions
  - Data integrity and constraints
  - Connection pooling

#### Redis (Cache Layer)
- **Purpose**: High-performance caching and session storage
- **Connection**: `redis:6379`
- **Database**: `0`
- **Password**: `wiregate_redis_password`
- **Features**:
  - In-memory storage
  - TTL-based expiration
  - Cache invalidation strategies
  - AOF persistence

### 3. Data Structure

#### PostgreSQL Tables
```sql
-- Main peers table for each configuration
{config_name}:
  - id (VARCHAR PRIMARY KEY)
  - private_key (TEXT)
  - DNS (TEXT)
  - endpoint_allowed_ip (TEXT)
  - name (TEXT)
  - total_receive (REAL)
  - total_sent (REAL)
  - total_data (REAL)
  - endpoint (TEXT)
  - status (TEXT)
  - latest_handshake (TEXT)
  - allowed_ip (TEXT)
  - cumu_receive (REAL)
  - cumu_sent (REAL)
  - cumu_data (REAL)
  - traffic (TEXT)
  - mtu (INTEGER)
  - keepalive (INTEGER)
  - remote_endpoint (TEXT)
  - preshared_key (TEXT)
  - address_v4 (TEXT)
  - address_v6 (TEXT)
  - upload_rate_limit (INTEGER DEFAULT 0)
  - download_rate_limit (INTEGER DEFAULT 0)
  - scheduler_type (TEXT DEFAULT 'htb')

-- Additional tables per configuration
{config_name}_restrict_access  -- Restricted peers
{config_name}_transfer         -- Transfer logs
{config_name}_deleted          -- Deleted peers

-- System tables
DashboardAPIKeys               -- API key management
Migration tracking             -- Migration status and timestamps
```

#### Redis Cache Keys
```
wiregate:cache:{table_name}:{record_id}  -- Individual record cache
wiregate:cache:{table_name}              -- Table-level cache
```

## Data Flow Patterns

### Read Operations
```
Frontend Request → API Route → DataBaseManager → Redis Cache Check
                                                      │
                                                      ▼
                                              Cache Hit? ──Yes──► Return Cached Data
                                                      │
                                                      No
                                                      ▼
                                              PostgreSQL Query ──► Return Data
                                                      │
                                                      ▼
                                              Update Redis Cache
```

### Write Operations
```
Frontend Request → API Route → DataBaseManager → PostgreSQL Write
                                                      │
                                                      ▼
                                              Invalidate Redis Cache
                                                      │
                                                      ▼
                                              Update Redis Cache (Optional)
```

## Migration System

### SQLite to PostgreSQL Migration
The system includes automatic migration from legacy SQLite databases to PostgreSQL:

#### Migration Process
1. **Detection**: Auto-detect SQLite files in common locations
2. **Schema Mapping**: Convert SQLite schemas to PostgreSQL equivalents
3. **Data Transfer**: Migrate data with type conversion
4. **Validation**: Verify data integrity post-migration
5. **Tracking**: Record migration status and timestamps

#### Supported SQLite Files
- `wgdashboard.db` - Main dashboard data
- `wgdashboard_job.db` - Job queue data
- `wgdashboard_log.db` - Logging data

#### Migration Locations
- `./db/`
- `./Src/db/`
- `/etc/wireguard/`
- `~/.wiregate/`

### Migration Types
- **Auto Migration**: Detect current state and migrate accordingly
- **Redis to Hybrid**: Migrate from Redis-only to hybrid architecture
- **Hybrid to PostgreSQL**: Migrate from hybrid to PostgreSQL-only
- **PostgreSQL to Hybrid**: Migrate from PostgreSQL-only to hybrid

## Configuration

### Environment Variables

#### PostgreSQL Configuration
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=wiregate
POSTGRES_USER=wiregate_user
POSTGRES_PASSWORD=wiregate_postgres_password
POSTGRES_SSL_MODE=disable
```

#### Redis Configuration
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=wiregate_redis_password
```

#### Application Configuration
```bash
DASHBOARD_MODE=production
MIGRATION_MODE=auto
```

### Docker Configuration

#### PostgreSQL Container
```yaml
postgres:
  image: postgres:15-alpine
  container_name: wiregate-postgres
  hostname: postgres
  restart: unless-stopped
  environment:
    POSTGRES_DB: wiregate
    POSTGRES_USER: wiregate_user
    POSTGRES_PASSWORD: wiregate_postgres_password
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./configs/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    - ./configs/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U wiregate_user -d wiregate"]
    interval: 10s
    timeout: 5s
    retries: 3
```

#### Redis Container
```yaml
redis:
  image: redis:7-alpine
  container_name: wiregate-redis
  hostname: redis
  restart: unless-stopped
  command: redis-server /usr/local/etc/redis/redis.conf
  volumes:
    - ./configs/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "wiregate_redis_password", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
```

## API Endpoints

### Database Management
- `GET /api/database/config` - Get database configuration
- `POST /api/database/config` - Update database configuration
- `GET /api/database/stats` - Get database statistics
- `POST /api/database/test` - Test database connections

### Migration Management
- `POST /api/database/migrate` - Perform database migration
- `POST /api/database/clear-cache` - Clear database cache

### Health Monitoring
- `GET /api/health` - System health status

## Performance Features

### Caching Strategy
- **Cache-First**: Check Redis before PostgreSQL
- **TTL Management**: Configurable cache expiration (default: 300 seconds)
- **Cache Invalidation**: Automatic cache clearing on data updates
- **Selective Caching**: Cache frequently accessed data only

### Connection Management
- **Connection Pooling**: Reuse database connections
- **Auto-commit**: Enable for better performance
- **Health Checks**: Monitor connection status
- **Graceful Degradation**: Continue operation if cache fails

### Query Optimization
- **Indexed Queries**: Optimized database indexes
- **Batch Operations**: Efficient bulk data operations
- **Query Caching**: Cache query results in Redis
- **Connection Reuse**: Minimize connection overhead

## Monitoring and Maintenance

### Health Checks
- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command
- **Interval**: 10 seconds
- **Timeout**: 5 seconds
- **Retries**: 3 attempts

### Logging
- **Database Operations**: All database operations logged
- **Migration Events**: Migration progress and status
- **Error Handling**: Comprehensive error logging
- **Performance Metrics**: Query execution times

### Backup Strategy
- **PostgreSQL**: Automated database backups
- **Redis**: AOF persistence and RDB snapshots
- **Configuration**: Version-controlled config files
- **Migration State**: Preserved migration history

## Security Considerations

### Authentication
- **Database Users**: Dedicated users with minimal privileges
- **Password Security**: Strong, unique passwords
- **Connection Encryption**: SSL/TLS support (configurable)

### Access Control
- **Network Isolation**: Private Docker networks
- **Port Restrictions**: Limited external access
- **User Permissions**: Principle of least privilege

### Data Protection
- **Encryption at Rest**: Database-level encryption
- **Encryption in Transit**: SSL/TLS connections
- **Sensitive Data**: Secure handling of passwords and keys

## Troubleshooting

### Common Issues
1. **Connection Failures**: Check network connectivity and credentials
2. **Migration Errors**: Verify SQLite file integrity and permissions
3. **Cache Issues**: Clear Redis cache or restart Redis container
4. **Performance Problems**: Check query optimization and cache hit rates

### Diagnostic Commands
```bash
# Test PostgreSQL connection
pg_isready -h postgres -p 5432 -U wiregate_user -d wiregate

# Test Redis connection
redis-cli -h redis -p 6379 -a wiregate_redis_password ping

# Check migration status
curl http://localhost:10086/api/database/stats

# Clear cache
curl -X POST http://localhost:10086/api/database/clear-cache
```

## Future Enhancements

### Planned Features
- **Redis Clustering**: High availability setup
- **Read Replicas**: PostgreSQL read replicas for scaling
- **Advanced Caching**: More sophisticated cache strategies
- **Monitoring Integration**: Prometheus/Grafana integration
- **Backup Automation**: Automated backup scheduling

### Performance Improvements
- **Query Optimization**: Advanced query tuning
- **Index Optimization**: Better indexing strategies
- **Connection Pooling**: Enhanced connection management
- **Cache Warming**: Proactive cache population

---

*This document is maintained as part of the WireGate project. For updates or questions, please refer to the project repository.*
