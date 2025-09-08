# Redis Database Migration

This document describes the migration from SQLite to Redis database for WireGate.

## Overview

WireGate has been migrated from SQLite to Redis to provide better performance, scalability, and reliability. The migration maintains full compatibility with existing functionality while providing the following benefits:

- **Better Performance**: Redis is an in-memory database that provides faster read/write operations
- **Scalability**: Redis can handle more concurrent connections and larger datasets
- **Persistence**: Data is persisted to disk using Redis AOF (Append Only File) persistence
- **High Availability**: Redis supports clustering and replication for high availability setups

## Architecture Changes

### Database Layer
- **Old**: Direct SQLite operations in `Core.py`
- **New**: Centralized `DataBaseManager.py` with Redis backend

### Key Components

1. **DatabaseManager**: Core Redis operations (CRUD, search, etc.)
2. **ConfigurationDatabase**: Configuration-specific database operations
3. **Compatibility Layer**: SQL-like functions for backward compatibility

## Configuration

### Environment Variables

The following environment variables control Redis connection:

```bash
REDIS_HOST=redis          # Redis server hostname
REDIS_PORT=6379          # Redis server port
REDIS_DB=0               # Redis database number
REDIS_PASSWORD=wiregate_redis_password  # Redis password
```

### Docker Compose

Redis is included in the Docker Compose setup:

```yaml
redis:
  image: redis:7-alpine
  container_name: wiregate-redis
  hostname: redis
  restart: unless-stopped
  command: redis-server --appendonly yes --requirepass wiregate_redis_password
  volumes:
    - redis_data:/data
  networks:
    private_network:
      ipv4_address: 10.2.0.4
      ipv6_address: 2001:db8:abc::4
```

## Data Structure

### Redis Key Format
```
wiregate:{table_name}:{record_id}
```

### Table Schemas
- `{config_name}`: Main peers table
- `{config_name}_restrict_access`: Restricted peers
- `{config_name}_transfer`: Transfer data
- `{config_name}_deleted`: Deleted peers

### Data Types
All data is stored as Redis hashes with automatic type conversion:
- Strings remain strings
- Numbers are converted to appropriate Python types
- Booleans are converted from string representations

## Migration Process

### Automatic Migration
The system automatically handles migration from SQLite to Redis:

1. **Database Creation**: New configurations create Redis tables
2. **Data Import**: Existing SQLite data can be imported via backup/restore
3. **Schema Migration**: Automatic schema updates for new fields

### Manual Migration
To migrate existing data:

1. Create a backup of your current configuration
2. The system will automatically import SQLite data when restoring from backup
3. All new data will be stored in Redis

## API Compatibility

The migration maintains full API compatibility:

### SQL-like Functions
- `sqlSelect()`: Query data (returns cursor-like object)
- `sqlUpdate()`: Insert/Update/Delete data
- `sqldb.iterdump()`: Export data as SQL statements

### Configuration Methods
All existing configuration methods work unchanged:
- `__createDatabase()`
- `__dropDatabase()`
- `__migrateDatabase()`
- `__dumpDatabase()`
- `__importDatabase()`

## Performance Benefits

### Read Operations
- **SQLite**: Disk-based reads
- **Redis**: In-memory reads (10-100x faster)

### Write Operations
- **SQLite**: Disk-based writes with locking
- **Redis**: In-memory writes with optional persistence

### Concurrent Access
- **SQLite**: Limited concurrent writes
- **Redis**: High concurrent read/write performance

## Monitoring and Maintenance

### Redis Monitoring
```bash
# Connect to Redis CLI
docker exec -it wiregate-redis redis-cli

# Monitor Redis operations
docker exec -it wiregate-redis redis-cli monitor

# Check memory usage
docker exec -it wiregate-redis redis-cli info memory
```

### Backup and Restore
```bash
# Create backup
docker exec wiregate-redis redis-cli BGSAVE

# Restore from backup
docker cp backup.rdb wiregate-redis:/data/
```

## Troubleshooting

### Connection Issues
1. Check Redis container is running: `docker ps | grep redis`
2. Verify network connectivity between containers
3. Check Redis logs: `docker logs wiregate-redis`

### Data Issues
1. Check Redis persistence: `docker exec wiregate-redis redis-cli config get save`
2. Verify data exists: `docker exec wiregate-redis redis-cli keys "wiregate:*"`
3. Check memory usage: `docker exec wiregate-redis redis-cli info memory`

### Performance Issues
1. Monitor Redis performance: `docker exec wiregate-redis redis-cli info stats`
2. Check slow queries: `docker exec wiregate-redis redis-cli slowlog get 10`
3. Monitor memory usage and consider increasing Redis memory limits

## Security Considerations

### Authentication
- Redis password is set via `REDIS_PASSWORD` environment variable
- Default password: `wiregate_redis_password` (change in production)

### Network Security
- Redis is only accessible within the Docker network
- No external ports are exposed for Redis

### Data Encryption
- Consider enabling Redis AUTH and TLS for production deployments
- Data is stored in plain text (consider Redis encryption at rest)

## Future Enhancements

### Planned Features
1. **Redis Clustering**: Support for Redis cluster mode
2. **Data Compression**: Compress stored data to reduce memory usage
3. **Advanced Caching**: Implement intelligent caching strategies
4. **Metrics**: Detailed performance and usage metrics

### Migration Tools
1. **Data Migration Scripts**: Automated migration from SQLite
2. **Backup Tools**: Enhanced backup and restore utilities
3. **Monitoring Dashboard**: Redis performance monitoring

## Support

For issues related to the Redis migration:

1. Check the logs: `docker logs wiregate`
2. Verify Redis connectivity: `docker exec wiregate-redis redis-cli ping`
3. Review this documentation
4. Check GitHub issues for known problems

## Conclusion

The migration to Redis provides significant performance improvements while maintaining full compatibility with existing WireGate functionality. The new architecture is more scalable and provides a solid foundation for future enhancements.
