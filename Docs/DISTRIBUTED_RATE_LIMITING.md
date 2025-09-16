# Distributed Rate Limiting for Wiregate

## Overview

This implementation provides enterprise-grade distributed rate limiting for Wiregate, enabling horizontal scaling across multiple application instances while maintaining consistent rate limiting policies.

## Features

### 🚀 **Core Features**
- **Distributed Rate Limiting**: Shared state across multiple instances via Redis
- **Multi-Strategy Limiting**: Standard, burst, and sliding window algorithms
- **Redis Cluster Support**: High availability with Redis cluster
- **Real-time Metrics**: Comprehensive monitoring and alerting
- **Configurable Limits**: Per-endpoint rate limiting configuration
- **Admin Controls**: Reset limits and manage policies

### 🛡️ **Security Features**
- **Burst Protection**: Prevents rapid-fire attacks
- **Sliding Window**: More precise rate limiting
- **Identifier-based**: IP and user-based limiting
- **Graceful Degradation**: Continues working if Redis fails

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Instance 1    │    │   Instance 2    │    │   Instance N    │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │Rate Limit │  │    │  │Rate Limit │  │    │  │Rate Limit │  │
│  │Decorator  │  │    │  │Decorator  │  │    │  │Decorator  │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
│        │        │    │        │        │    │        │        │
└────────┼────────┘    └────────┼────────┘    └────────┼────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │      Redis Cluster    │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  Rate Limiting  │  │
                    │  │     Data        │  │
                    │  └─────────────────┘  │
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │    Metrics      │  │
                    │  │    Storage      │  │
                    │  └─────────────────┘  │
                    └───────────────────────┘
```

## Configuration

### Environment Variables

```bash
# Enable distributed rate limiting
DISTRIBUTED_RATE_LIMIT_ENABLED=true

# Redis cluster configuration
REDIS_CLUSTER_ENABLED=true
REDIS_CLUSTER_NODES=redis1:6379,redis2:6379,redis3:6379

# Rate limiting limits
API_RATE_LIMIT=100
AUTH_RATE_LIMIT=5
BURST_RATE_LIMIT=25
RATE_LIMIT_WINDOW=60
BURST_WINDOW=60

# Advanced features
SLIDING_WINDOW_ENABLED=true
BURST_PROTECTION_ENABLED=true
ADAPTIVE_LIMITS_ENABLED=false
GEO_DISTRIBUTED_ENABLED=false

# Monitoring
RATE_LIMIT_METRICS_ENABLED=true
RATE_LIMIT_ALERT_THRESHOLD=0.8
RATE_LIMIT_CLEANUP_INTERVAL=300
```

### Per-Endpoint Configuration

```python
# Different limits for different endpoints
@rate_limit(limit=5, window=300, use_distributed=True)  # 5 requests per 5 minutes
@auth_blueprint.post('/authenticate')

@rate_limit(limit=100, window=60, use_distributed=True)  # 100 requests per minute
@api_blueprint.get('/api/data')
```

## Usage

### Basic Rate Limiting

```python
from ..modules.Security import rate_limit

@rate_limit(limit=10, window=60, use_distributed=True)
def my_endpoint():
    return ResponseObject(True, "Success")
```

### Advanced Rate Limiting

```python
# With burst protection
@rate_limit(limit=100, window=60, use_distributed=True)
def api_endpoint():
    # This will use distributed rate limiting with burst protection
    pass
```

### Manual Rate Limiting

```python
from ..modules.Security import security_manager

# Check if rate limited
is_limited, info = security_manager.is_distributed_rate_limited(
    identifier="192.168.1.1",
    limit=10,
    window=60,
    burst_limit=5
)

if is_limited:
    return ResponseObject(False, "Rate limited")
```

## API Endpoints

### Rate Limiting Status
- `GET /rate-limit-status` - Get current rate limit status
- `GET /distributed-rate-limit-test` - Test distributed rate limiting

### Administration
- `POST /reset-rate-limit` - Reset rate limit for identifier
- `GET /rate-limit-metrics` - Get rate limiting metrics
- `GET /rate-limit-health` - Get system health status
- `GET /top-limited-identifiers` - Get top limited identifiers
- `POST /cleanup-rate-limit-metrics` - Clean up old metrics

## Monitoring

### Metrics Collected
- **Request Count**: Total requests per time window
- **Limited Requests**: Number of rate-limited requests
- **Limit Rate**: Percentage of requests that were limited
- **Response Times**: Average response times
- **Endpoint Statistics**: Requests per endpoint
- **Limit Type Statistics**: Distribution of limit types

### Health Monitoring
- **Redis Connection**: Connection status to Redis
- **Metrics Collection**: Status of metrics collection
- **Alert Thresholds**: Automatic alerting when thresholds exceeded

### Example Metrics Response
```json
{
  "status": "active",
  "time_window": 3600,
  "total_requests": 1500,
  "limited_requests": 45,
  "limit_rate_percent": 3.0,
  "average_response_time": 0.125,
  "endpoint_stats": {
    "/authenticate": 50,
    "/api/data": 1200,
    "/api/config": 250
  },
  "limit_type_stats": {
    "rate": 30,
    "burst": 10,
    "sliding": 5
  },
  "is_alert_threshold_exceeded": false
}
```

## Performance Characteristics

### Scalability
- **Horizontal Scaling**: Supports unlimited application instances
- **Redis Cluster**: High availability and performance
- **Memory Efficient**: Uses Redis sorted sets for efficient storage
- **Low Latency**: Sub-millisecond rate limit checks

### Throughput
- **High Throughput**: Handles thousands of requests per second
- **Burst Handling**: Protects against rapid-fire attacks
- **Graceful Degradation**: Continues working if Redis is unavailable

## Security Considerations

### Protection Mechanisms
- **Burst Protection**: Prevents rapid-fire attacks
- **Sliding Window**: More precise than fixed windows
- **Identifier-based**: IP and user-based limiting
- **Admin Controls**: Secure reset and management functions

### Attack Mitigation
- **DDoS Protection**: Rate limiting prevents overwhelming
- **Brute Force Protection**: Integrated with authentication
- **Resource Protection**: Prevents resource exhaustion

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis server status
   - Verify connection parameters
   - Check network connectivity

2. **Rate Limiting Not Working**
   - Verify `DISTRIBUTED_RATE_LIMIT_ENABLED=true`
   - Check Redis cluster configuration
   - Review endpoint decorators

3. **High Memory Usage**
   - Run cleanup endpoint: `POST /cleanup-rate-limit-metrics`
   - Adjust cleanup interval
   - Monitor Redis memory usage

### Debug Commands

```bash
# Check Redis connection
redis-cli ping

# View rate limiting keys
redis-cli keys "rate_limit:*"

# Check metrics
redis-cli keys "rate_limit_metrics:*"

# Monitor Redis performance
redis-cli monitor
```

## Migration Guide

### From Basic Rate Limiting

1. **Update Environment Variables**
   ```bash
   DISTRIBUTED_RATE_LIMIT_ENABLED=true
   REDIS_CLUSTER_ENABLED=true
   ```

2. **Update Decorators**
   ```python
   # Old
   @rate_limit(limit=10, window=60)
   
   # New
   @rate_limit(limit=10, window=60, use_distributed=True)
   ```

3. **Deploy and Test**
   - Deploy to multiple instances
   - Test rate limiting across instances
   - Monitor metrics and health

## Best Practices

### Configuration
- Set appropriate limits for each endpoint type
- Use burst protection for authentication endpoints
- Monitor metrics regularly
- Set up alerting for threshold breaches

### Monitoring
- Regular health checks
- Metrics analysis
- Performance monitoring
- Capacity planning

### Security
- Regular security reviews
- Limit admin access
- Monitor for abuse
- Keep Redis secure

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review metrics and health endpoints
3. Check Redis logs
4. Contact the development team

---

**Note**: This distributed rate limiting system is designed for production use and provides enterprise-grade scalability and monitoring capabilities.
