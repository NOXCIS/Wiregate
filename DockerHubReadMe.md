# WireGate Docker Configuration Guide

A comprehensive guide for configuring and deploying WireGate with Docker Compose, including WireGuard, AmneziaWG, Tor integration, and dashboard management.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
  - [Tor Settings](#tor-settings)
  - [WGDashboard Settings](#wgdashboard-settings)
  - [DNS Settings](#dns-settings)
  - [Database Settings](#database-settings)
  - [Security Settings](#security-settings)
- [Volume Mounts](#volume-mounts)
- [Docker Compose Configuration](#docker-compose-configuration)
- [Configuration Files](#configuration-files)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

Before deploying WireGate, ensure your system meets the following requirements:

### System Requirements
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **Docker**: 20.10.0+
- **Docker Compose**: 2.0.0+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 10GB free space
- **Network**: Root access for network configuration

### Required Capabilities
- `NET_ADMIN` capability for network management
- `SYS_MODULE` capability for kernel module loading
- Access to `/dev/net/tun` device
- IPv4/IPv6 forwarding enabled

### Firewall Configuration
```bash
# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.conf
sysctl -p

# Allow required ports
ufw allow 44333/udp
ufw allow 4430:4433/udp
ufw allow 8000/tcp
```

---

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/wiregate.git
   cd wiregate
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy the stack**:
   ```bash
   docker compose up -d
   ```

4. **Access the dashboard**:
   - Local: `http://localhost:8000`
   - Remote: `http://your-server-ip:8000`

---

## Environment Variables

### Tor Settings

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `WGD_TOR_PROXY` | Enable Tor proxy for WireGuard connections | `true` | `true`, `false` |
| `WGD_TOR_EXIT_NODES` | Tor exit node country codes | `{ch}` | `{us}`, `{gb}`, `{de}`, etc. |
| `WGD_TOR_DNS_EXIT_NODES` | DNS exit node country codes | `{gb}` | `{us}`, `{ch}`, `{de}`, etc. |
| `WGD_TOR_PLUGIN` | Tor obfuscation plugin | `obfs4` | `webtunnel`, `obfs4`, `snowflake` |
| `WGD_TOR_BRIDGES` | Enable Tor bridges for censorship bypass | `true` | `true`, `false` |
| `WGD_TOR_DNSCRYPT` | Enable Dnscrypt with Tor Socks Proxy | `false` | `true`, `false` |

### WGDashboard Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WGD_WELCOME_SESSION` | Enable welcome session | `false` | `true`, `false` |
| `WGD_AUTH_REQ` | Require authentication | `false` | `true`, `false` |
| `WGD_USER` | Dashboard username | `admin` | Any username |
| `WGD_PASS` | Dashboard password | `admin` | Strong password |
| `WGD_REMOTE_ENDPOINT` | Remote endpoint IP | `0.0.0.0` | `192.168.1.100` |
| `WGD_REMOTE_ENDPOINT_PORT` | Remote endpoint port | `80` | `443`, `8080` |
| `WGD_PEER_ENDPOINT_ALLOWED_IP` | Allowed IP range | `0.0.0.0/0` | `192.168.0.0/16` |
| `WGD_KEEP_ALIVE` | Keep-alive interval (seconds) | `21` | `15`, `30` |
| `WGD_MTU` | Maximum Transmission Unit | `1420` | `1280`, `1500` |
| `WGD_PORT_RANGE_STARTPORT` | Starting port for WireGuard | `4430` | `51820`, `4430` |

### DNS Settings

> **Important**: DNS variables must match each other for proper functionality.

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WGD_DNS` | DNS server IPs for WireGuard | `1.1.1.1` | `8.8.8.8`, `1.0.0.1` |
| `WGD_IPTABLES_DNS` | DNS server IP for iptables | `1.1.1.1` | `8.8.8.8`, `1.0.0.1` |

### Database Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `postgres` | `localhost`, `db.example.com` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | `5432` |
| `POSTGRES_DB` | Database name | `wiregate` | `wiregate_prod` |
| `POSTGRES_USER` | Database user | `wiregate_user` | `wg_admin` |
| `POSTGRES_PASSWORD` | Database password | `wiregate_postgres_password` | Strong password |
| `REDIS_HOST` | Redis host | `redis` | `localhost` |
| `REDIS_PORT` | Redis port | `6379` | `6379` |
| `REDIS_PASSWORD` | Redis password | `wiregate_redis_password` | Strong password |

### Security Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DASHBOARD_MODE` | Dashboard mode | `development` | `production` |
| `ALLOWED_ORIGINS` | Allowed CORS origins | `*` | `https://yourdomain.com` |
| `RATE_LIMIT_REQUESTS` | Rate limit (requests/minute) | `100` | `50`, `200` |
| `BRUTE_FORCE_MAX_ATTEMPTS` | Max failed login attempts | `5` | `3`, `10` |
| `SESSION_TIMEOUT` | Session timeout (seconds) | `3600` | `1800`, `7200` |
| `SECURE_SESSION` | Enable secure sessions | `true` | `true`, `false` |

---

## Volume Mounts

| Mount | Purpose | Required |
|-------|---------|----------|
| `/lib/modules:/lib/modules:ro` | AmneziaWG kernel modules | Yes |
| `pf_conf:/WireGate/iptable-rules/` | iptables firewall scripts | Yes |
| `conf:/etc/wireguard` | WireGuard & AmneziaWG configs | Yes |
| `db:/WireGate/db` | Database, dashboard & WSGI files | Yes |
| `./configs/ssl:/WireGate/SSL_CERT` | SSL certificates | Optional |
| `./configs/dnscrypt:/WireGate/dnscrypt` | Dnscrypt configuration | Optional |
| `./configs/tor:/etc/tor/` | Tor configuration files | Optional |
| `./configs/logs:/WireGate/log/` | Log files | Optional |
| `./configs/master-key:/WireGate/master-key` | WireGate master config | Optional |

---

## Docker Compose Configuration

```yaml
# WireGate Docker Compose Configuration
# Configure for your environment and run:
# docker compose up -d

networks:
  private_network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "true"
    attachable: true
    internal: false
    enable_ipv6: true
    ipam:
      config:
        - subnet: 10.2.0.0/24
        - subnet: 2001:db8:abc::/64
          gateway: 2001:db8:abc::1

services:
  redis:
    image: redis:7-alpine
    container_name: wiregate-redis
    hostname: redis
    restart: unless-stopped
    command: redis-server /usr/local/etc/redis/redis.conf
    env_file:
      - ./.env
    volumes:
      - redis_data:/data
      - ./configs/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    networks:
      private_network:
        ipv4_address: 10.2.0.4
        ipv6_address: 2001:db8:abc::4
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "wiregate_redis_password", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  postgres:
    image: postgres:15-alpine
    container_name: wiregate-postgres
    hostname: postgres
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./configs/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./configs/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      private_network:
        ipv4_address: 10.2.0.5
        ipv6_address: 2001:db8:abc::5
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wiregate_user -d wiregate"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf

  wiregate:
    image: noxcis/wiregate:sol-beta-v2.1.0
    container_name: wiregate
    hostname: wiregate
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    devices:
      - /dev/net/tun:/dev/net/tun  
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - /lib/modules:/lib/modules:ro 
      - pf_conf:/WireGate/iptable-rules/
      - conf:/etc/wireguard 
      - db:/WireGate/db
      - ./configs/ssl:/WireGate/SSL_CERT
      - ./configs/dnscrypt:/WireGate/dnscrypt
      - ./configs/tor:/etc/tor/
      - ./configs/logs:/WireGate/log/
      - ./configs/master-key:/WireGate/master-key
    env_file:
      - ./.env
    ports:
      - 44333:44333/udp
      - "4430-4433:4430-4433/udp"  # UDP Interface Listen Ports For Zones
      - 8000:80/tcp  # Comment out for full network lockdown
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
      - net.ipv6.conf.all.forwarding=1
      - net.ipv6.conf.default.forwarding=1
    networks:
      private_network:
        ipv4_address: 10.2.0.3
        ipv6_address: 2001:db8:abc::3

volumes:
  db:
  conf:
  pf_conf:
  redis_data:
  postgres_data:
```

---

## Configuration Files

### Environment File (.env)

```ini
# Dashboard Security Settings
##########################################################
DASHBOARD_MODE=production
ALLOWED_ORIGINS=https://yourdomain.com
MAX_REQUEST_SIZE=16777216     # 16MB default
RATE_LIMIT_REQUESTS=100       # requests per minute
RATE_LIMIT_WINDOW=60          # seconds
BRUTE_FORCE_MAX_ATTEMPTS=5    # max failed attempts
BRUTE_FORCE_LOCKOUT_TIME=900  # 15 minutes
SESSION_TIMEOUT=3600          # 1 hour
SECURE_SESSION=true

# Redis Database Settings
##########################################################
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=wiregate_redis_password

# PostgreSQL Database Settings
##########################################################
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=wiregate
POSTGRES_USER=wiregate_user
POSTGRES_PASSWORD=wiregate_postgres_password
POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C"
POSTGRES_SSL_MODE=disable

# Tor Settings
##########################################################
WGD_TOR_PROXY=true          # Enable Tor
WGD_TOR_EXIT_NODES={ch}     # Ex. {gb},{fr}
WGD_TOR_DNS_EXIT_NODES={us}
WGD_TOR_BRIDGES=false        # Enable Tor Bridges
WGD_TOR_PLUGIN=snowflake    # OPTIONS: webtunnel, obfs4, snowflake
WGD_TOR_DNSCRYPT=false

# WGDashboard Global Settings
##########################################################
WGDCONF_PATH=/etc/wireguard
AMNEZIA_WG=true
TZ=America/New_York

WGD_WELCOME_SESSION=false
WGD_AUTH_REQ=true
WGD_USER=admin
WGD_PASS=your_secure_password_here
WGD_REMOTE_ENDPOINT=192.168.0.4
WGD_REMOTE_ENDPOINT_PORT=80
WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0, ::/0
WGD_KEEP_ALIVE=21
WGD_MTU=1420
WGD_PORT_RANGE_STARTPORT=4430

# DNS Settings (Must match each other)
##########################################################
WGD_DNS=1.1.1.1
WGD_IPTABLES_DNS=1.1.1.1
```

### PostgreSQL Initialization (init.sql)

```sql
-- PostgreSQL initialization script for WireGate
-- This script runs when the PostgreSQL container is first created

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
```

### PostgreSQL Configuration (postgresql.conf)

```ini
# PostgreSQL configuration for WireGate
# This file contains PostgreSQL server configuration

# Connection Settings
listen_addresses = '*'
port = 5432
max_connections = 100
superuser_reserved_connections = 3

# Memory Settings
shared_buffers = 128MB
effective_cache_size = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
checkpoint_timeout = 5min
max_wal_size = 1GB
min_wal_size = 80MB

# Query Tuning
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 10MB
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# Locale and Formatting
datestyle = 'iso, mdy'
timezone = 'UTC'
lc_messages = 'en_US.utf8'
lc_monetary = 'en_US.utf8'
lc_numeric = 'en_US.utf8'
lc_time = 'en_US.utf8'
default_text_search_config = 'pg_catalog.english'

# Security
ssl = off
password_encryption = scram-sha-256

# Performance
shared_preload_libraries = ''
dynamic_shared_memory_type = posix

# Autovacuum
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
autovacuum_freeze_max_age = 200000000
autovacuum_multixact_freeze_max_age = 400000000
autovacuum_vacuum_cost_delay = 20ms
autovacuum_vacuum_cost_limit = 200

# Client Connection Defaults
default_transaction_isolation = 'read committed'
default_transaction_read_only = off
default_transaction_deferrable = off
session_replication_role = 'origin'
statement_timeout = 0
lock_timeout = 0
idle_in_transaction_session_timeout = 0
vacuum_freeze_min_age = 50000000
vacuum_freeze_table_age = 150000000
vacuum_multixact_freeze_min_age = 5000000
vacuum_multixact_freeze_table_age = 150000000
```

### Redis Configuration (redis.conf)

```ini
# Redis configuration for WireGate
# This file contains Redis server configuration

# Network
bind 0.0.0.0
port 6379
protected-mode yes

# Authentication
requirepass wiregate_redis_password

# Persistence
save 900 1
save 300 10
save 60 10000

# Append Only File
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Logging
loglevel notice
logfile ""

# Performance
tcp-keepalive 300
timeout 0

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
# Note: KEYS command is needed for WireGate database operations
# rename-command KEYS ""
rename-command CONFIG ""

# Client output buffer limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Latency monitoring
latency-monitor-threshold 100
```

---

## Security Considerations

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Enable authentication (`WGD_AUTH_REQ=true`)
- [ ] Set `DASHBOARD_MODE=production`
- [ ] Configure proper `ALLOWED_ORIGINS`
- [ ] Use strong passwords (minimum 16 characters)
- [ ] Enable SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption

### Network Security

```bash
# Example iptables rules for additional security
iptables -A INPUT -p tcp --dport 8000 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
iptables -A INPUT -p udp --dport 44333 -j ACCEPT
iptables -A INPUT -p udp --dport 4430:4433 -j ACCEPT
```

### SSL/TLS Configuration

For production deployments, configure SSL certificates:

```yaml
# Add to wiregate service volumes
- ./configs/ssl/cert.pem:/WireGate/SSL_CERT/cert.pem:ro
- ./configs/ssl/key.pem:/WireGate/SSL_CERT/key.pem:ro
```

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

**Symptoms**: Container exits immediately or fails to start

**Solutions**:
```bash
# Check container logs
docker logs wiregate

# Verify capabilities
docker run --rm --cap-add=NET_ADMIN --cap-add=SYS_MODULE noxcis/wiregate:sol-beta-v2.1.0

# Check kernel modules
lsmod | grep wireguard
```

#### 2. Network Connectivity Issues

**Symptoms**: Can't access dashboard or VPN connections fail

**Solutions**:
```bash
# Check IP forwarding
sysctl net.ipv4.ip_forward
sysctl net.ipv6.conf.all.forwarding

# Verify port binding
netstat -tulpn | grep :8000
netstat -tulpn | grep :44333

# Check firewall
ufw status
iptables -L
```

#### 3. Database Connection Issues

**Symptoms**: Database connection errors in logs

**Solutions**:
```bash
# Check database health
docker exec wiregate-postgres pg_isready -U wiregate_user -d wiregate

# Verify Redis connection
docker exec wiregate-redis redis-cli -a wiregate_redis_password ping

# Check network connectivity
docker exec wiregate ping postgres
docker exec wiregate ping redis
```

#### 4. Tor Connection Issues

**Symptoms**: Tor proxy not working or slow connections

**Solutions**:
```bash
# Check Tor status
docker exec wiregate ps aux | grep tor

# Verify Tor configuration
docker exec wiregate cat /etc/tor/torrc

# Test Tor connectivity
docker exec wiregate curl --socks5 127.0.0.1:9050 https://check.torproject.org
```

### Log Analysis

```bash
# View all container logs
docker compose logs

# View specific service logs
docker compose logs wiregate
docker compose logs postgres
docker compose logs redis

# Follow logs in real-time
docker compose logs -f wiregate
```

### Performance Monitoring

```bash
# Check resource usage
docker stats

# Monitor network traffic
docker exec wiregate iftop

# Check disk usage
docker system df
```

---

## Performance Tuning

### Database Optimization

#### PostgreSQL Tuning
```ini
# For high-traffic deployments
shared_buffers = 256MB
effective_cache_size = 512MB
work_mem = 8MB
maintenance_work_mem = 128MB
max_connections = 200
```

#### Redis Tuning
```ini
# For high-memory usage
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Network Optimization

```yaml
# Add to docker-compose.yml for better performance
services:
  wiregate:
    sysctls:
      - net.core.rmem_max=134217728
      - net.core.wmem_max=134217728
      - net.ipv4.udp_rmem_min=8192
      - net.ipv4.udp_wmem_min=8192
```

### Resource Limits

```yaml
# Add resource limits to prevent resource exhaustion
services:
  wiregate:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

---

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker exec wiregate-postgres pg_dump -U wiregate_user wiregate > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup Redis
docker exec wiregate-redis redis-cli -a wiregate_redis_password --rdb /data/backup_$(date +%Y%m%d_%H%M%S).rdb
```

### Configuration Backup

```bash
# Backup all configurations
tar -czf wiregate_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  configs/ \
  .env \
  docker-compose.yml
```

### Automated Backup Script

```bash
#!/bin/bash
# backup_wiregate.sh

BACKUP_DIR="/backups/wiregate"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup databases
docker exec wiregate-postgres pg_dump -U wiregate_user wiregate > $BACKUP_DIR/postgres_$DATE.sql
docker exec wiregate-redis redis-cli -a wiregate_redis_password --rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup configurations
tar -czf $BACKUP_DIR/config_$DATE.tar.gz configs/ .env docker-compose.yml

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Recovery Process

```bash
# Restore PostgreSQL
docker exec -i wiregate-postgres psql -U wiregate_user -d wiregate < backup_20240101_120000.sql

# Restore Redis
docker cp backup_20240101_120000.rdb wiregate-redis:/data/dump.rdb
docker restart wiregate-redis

# Restore configurations
tar -xzf config_20240101_120000.tar.gz
docker compose restart
```

---

## Monitoring and Alerting

### Health Checks

The Docker Compose configuration includes built-in health checks for all services. Monitor these using:

```bash
# Check service health
docker compose ps

# View health check status
docker inspect wiregate | jq '.[0].State.Health'
```

### Log Monitoring

Set up log monitoring with tools like:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Prometheus + Grafana**
- **Fluentd**
- **Splunk**

### Alerting

Configure alerts for:
- Service down
- High CPU/Memory usage
- Database connection failures
- Failed authentication attempts
- Network connectivity issues

---

## Support and Contributing

### Getting Help

- **Documentation**: Check this guide and inline comments
- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join our Discord/Telegram for community support

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Changelog

### Version 2.1.0
- Added comprehensive documentation
- Improved security configurations
- Enhanced troubleshooting guide
- Added performance tuning recommendations
- Included backup and recovery procedures

---

*Last updated: January 2024*