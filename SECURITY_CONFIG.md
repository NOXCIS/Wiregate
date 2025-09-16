# Wiregate Security Configuration Guide

## Overview
This document provides security configuration recommendations for deploying Wiregate in production environments.

## Environment Variables for Production

### Required Security Settings
```bash
# Set to production mode
DASHBOARD_MODE=production

# Restrict CORS to specific domains (comma-separated)
ALLOWED_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# Request size limits (in bytes)
MAX_REQUEST_SIZE=16777216  # 16MB

# Rate limiting
RATE_LIMIT_REQUESTS=100    # requests per minute
RATE_LIMIT_WINDOW=60       # time window in seconds

# Brute force protection
BRUTE_FORCE_MAX_ATTEMPTS=5      # max failed attempts
BRUTE_FORCE_LOCKOUT_TIME=900    # lockout time in seconds (15 minutes)

# Session security
SESSION_TIMEOUT=3600       # session timeout in seconds (1 hour)
SECURE_SESSION=true        # use secure cookies

# Redis security
REDIS_PASSWORD=your_strong_redis_password
```

### Optional Security Settings
```bash
# Custom paths
CONFIGURATION_PATH=/etc/wiregate
WG_CONF_PATH=/etc/wireguard

# Authentication
WGD_AUTH_REQ=true
WGD_USER=admin
WGD_PASS=your_strong_password

# Network settings
WGD_REMOTE_ENDPOINT=your.server.ip
WGD_REMOTE_ENDPOINT_PORT=443
```

## Docker Security Configuration

### Production Docker Compose
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: wiregate-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - wiregate_network
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp

  wiregate:
    build: .
    container_name: wiregate
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    cap_drop:
      - ALL
    devices:
      - /dev/net/tun:/dev/net/tun
    volumes:
      - /lib/modules:/lib/modules:ro
      - ./configs:/WireGate/configs:ro
      - ./logs:/WireGate/logs
    environment:
      - DASHBOARD_MODE=production
      - ALLOWED_ORIGINS=https://yourdomain.com
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - WGD_AUTH_REQ=true
      - WGD_USER=${ADMIN_USER}
      - WGD_PASS=${ADMIN_PASSWORD}
      - SECURE_SESSION=true
      - SESSION_TIMEOUT=3600
      - RATE_LIMIT_REQUESTS=100
      - BRUTE_FORCE_MAX_ATTEMPTS=5
    networks:
      - wiregate_network
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /WireGate/db
    depends_on:
      - redis

networks:
  wiregate_network:
    driver: bridge
    internal: false

volumes:
  redis_data:
```

## Security Headers

The application now includes the following security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'` (production only)

## API Security Features

### Rate Limiting
- **Authentication endpoints**: 5 attempts per 5 minutes
- **General API endpoints**: 100 requests per minute
- **File upload endpoints**: 10 requests per minute

### Brute Force Protection
- **Max failed attempts**: 5 (configurable)
- **Lockout duration**: 15 minutes (configurable)
- **Tracking**: Per IP address

### Input Validation
- **Request size limit**: 16MB (configurable)
- **Input sanitization**: All user inputs are sanitized
- **File upload validation**: Only allowed file types and sizes

### Session Security
- **Secure cookies**: Enabled in production
- **HttpOnly cookies**: Always enabled
- **Session timeout**: 1 hour (configurable)
- **Session invalidation**: Proper logout clears all session data

## File Upload Security

### Allowed File Types
- **Backup files**: `.7z` only
- **Configuration files**: `.conf`, `.ini` only
- **Script files**: `.sh` only (with execution permissions)

### File Validation
- **Path traversal protection**: Prevents `../` attacks
- **Filename validation**: Blocks dangerous characters
- **File size limits**: Configurable per endpoint
- **Content scanning**: Basic file type validation

## Command Execution Security

### Secure Command Execution
- **No shell execution**: All commands use parameterized execution
- **Command whitelist**: Only allowed commands can be executed
- **Argument validation**: All arguments are validated
- **Timeout protection**: Commands have execution timeouts

### Allowed Commands
- `wg` - WireGuard management
- `ip` - Network interface management
- `iptables` - Firewall rules
- `tc` - Traffic control
- `tail`, `head`, `grep`, `awk`, `sed` - Log processing
- `chmod`, `chown`, `mkdir`, `rm`, `cp`, `mv` - File operations
- `curl`, `wget` - Network requests

## Database Security

### Redis Configuration
- **Authentication**: Password required
- **Network isolation**: Internal network only
- **Data encryption**: Use TLS in production
- **Access control**: Restrict to application only

### Data Protection
- **Sensitive data**: Passwords and keys are hashed
- **Session data**: Stored securely in Redis
- **Log data**: Sanitized before storage

## Network Security

### CORS Configuration
- **Development**: Wildcard allowed (for testing)
- **Production**: Specific domains only
- **Credentials**: Supported for authenticated requests

### Firewall Rules
- **WireGuard ports**: UDP 4430-4433
- **Web interface**: HTTPS only (port 443)
- **API endpoints**: Rate limited and authenticated

## Monitoring and Logging

### Security Logging
- **Authentication attempts**: Success and failure
- **API access**: All requests logged
- **Command execution**: All commands logged
- **File operations**: Upload and download activities

### Log Security
- **Sensitive data**: Not logged in plain text
- **Log rotation**: Implement log rotation
- **Log monitoring**: Monitor for suspicious activities

## Deployment Checklist

### Pre-deployment
- [ ] Set `DASHBOARD_MODE=production`
- [ ] Configure `ALLOWED_ORIGINS` with your domains
- [ ] Set strong `REDIS_PASSWORD`
- [ ] Configure `WGD_USER` and `WGD_PASS`
- [ ] Set `SECURE_SESSION=true`
- [ ] Configure rate limiting parameters
- [ ] Set up SSL/TLS certificates

### Post-deployment
- [ ] Test authentication and session management
- [ ] Verify rate limiting is working
- [ ] Test file upload restrictions
- [ ] Verify CORS configuration
- [ ] Check security headers
- [ ] Monitor logs for security events
- [ ] Test brute force protection

## Security Best Practices

1. **Regular Updates**: Keep all dependencies updated
2. **Monitoring**: Implement security monitoring
3. **Backups**: Regular secure backups
4. **Access Control**: Limit administrative access
5. **Network Security**: Use VPN or private networks
6. **SSL/TLS**: Always use HTTPS in production
7. **Log Analysis**: Regular log analysis for threats
8. **Incident Response**: Have a security incident response plan

## Troubleshooting

### Common Issues
- **CORS errors**: Check `ALLOWED_ORIGINS` configuration
- **Rate limiting**: Adjust `RATE_LIMIT_REQUESTS` if needed
- **Session timeouts**: Adjust `SESSION_TIMEOUT` if needed
- **File upload failures**: Check file size and type restrictions

### Security Alerts
- Monitor logs for repeated failed authentication attempts
- Watch for unusual API usage patterns
- Check for command execution errors
- Monitor file upload activities

## Support

For security-related issues or questions:
1. Check the logs for error messages
2. Verify environment variable configuration
3. Test with minimal configuration
4. Review this security guide
5. Contact the development team for assistance
