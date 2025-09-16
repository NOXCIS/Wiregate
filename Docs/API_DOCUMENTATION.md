# WireGate API Documentation

This document provides comprehensive information about all available API endpoints in the WireGate application. WireGate is a powerful WireGuard management dashboard that provides both web-based and programmatic access to WireGuard configuration management, traffic monitoring, and advanced features.

## Overview

WireGate offers a RESTful API that allows you to:
- Manage WireGuard configurations and peers
- Monitor real-time traffic and system status
- Configure traffic shaping and rate limiting
- Set up automated peer management jobs
- Integrate with external systems via API keys
- Manage backups and snapshots
- Configure authentication and security settings

## Base URL

All API endpoints are prefixed with `/api/`. For example:
```
http://localhost:8080/api/getConfigurations
```

## Authentication

Most API endpoints require authentication. WireGate supports multiple authentication methods:

1. **Session-based Authentication**: Use cookies for web-based access
2. **API Key Authentication**: Use `wg-dashboard-apikey` header for programmatic access
3. **LDAP Integration**: Enterprise authentication via LDAP/Active Directory

### API Key Usage
```bash
curl -X GET http://localhost:8080/api/getConfigurations \
  -H "wg-dashboard-apikey: your-api-key-here"
```

### Session Authentication
```bash
curl -X GET http://localhost:8080/api/getConfigurations \
  -H "Cookie: authToken=your-session-token"
```

## Response Format

All API responses follow a consistent format:

```json
{
    "status": "boolean",    // true for success, false for error
    "message": "string",    // Optional message describing the result
    "data": "any"          // Response data (varies by endpoint)
}
```

## Error Handling

When an error occurs, the API returns:
```json
{
    "status": false,
    "message": "Error description",
    "data": null
}
```

Common HTTP status codes:
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or failed
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to prevent abuse. If you exceed the rate limit, you'll receive a `429 Too Many Requests` response. Implement appropriate retry logic with exponential backoff.

## Getting Started

1. **Check Authentication Requirements**:
   ```bash
   curl -X GET http://localhost:8080/api/requireAuthentication
   ```

2. **Authenticate** (if required):
   ```bash
   curl -X POST http://localhost:8080/api/authenticate \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "password"}'
   ```

3. **Get Available Configurations**:
   ```bash
   curl -X GET http://localhost:8080/api/getConfigurations
   ```

## API Categories

The WireGate API is organized into the following categories:

## Table of Contents
- [Configuration Management](#configuration-management)
- [Peer Management](#peer-management)
- [Dashboard Configuration](#dashboard-configuration)
- [System Status](#system-status)
- [Authentication & Security](#authentication--security)
- [Share Management](#share-management)
- [Raw Configuration Management](#raw-configuration-management)
- [IPTables Management](#iptables-management)
- [Dashboard API Keys](#dashboard-api-keys)
- [Peer Data Management](#peer-data-management)
- [LDAP Integration](#ldap-integration)
- [Locale Management](#locale-management)
- [Email Integration](#email-integration)
- [Tor Integration](#tor-integration)
- [Traffic Weir API](#traffic-weir-api)
- [Network Utilities](#network-utilities)
- [Peer Jobs API](#peer-jobs-api)
- [Data Charts API](#data-charts-api)
- [Snapshot API](#snapshot-api)
- [Authentication API](#authentication-api)
- [Thread Pool API](#thread-pool-api)
- [Process Pool API](#process-pool-api)

## Configuration Management

### Get Configuration Status Stream
```
GET /api/config-status-stream
```
Provides a Server-Sent Events (SSE) stream of configuration status updates.

**Response:**
Server-Sent Events stream with the following event format:
```json
{
    "status": true,
    "data": {
        "configurationName": "string",
        "status": "string",
        "timestamp": "string"
    }
}
```

**Example Usage:**
```bash
curl -N http://localhost:8080/api/config-status-stream \
  -H "Content-Type: text/event-stream"
```

### Get All Configurations
```
GET /api/getConfigurations
```
Returns a list of all WireGuard configurations.

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "Name": "string",
            "Address": "string",
            "ListenPort": "integer",
            "PrivateKey": "string",
            "Status": "boolean"
            // ... other configuration properties
        }
    ]
}
```

### Cleanup Orphaned Configurations
```
POST /api/cleanupOrphanedConfigurations
```
Manually triggers cleanup of orphaned database configurations that no longer have corresponding configuration files.

**Response:**
```json
{
    "status": true,
    "message": "Orphaned configurations cleaned up successfully",
    "data": {
        "cleaned_count": "number",
        "removed_configurations": ["string"]
    }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/cleanupOrphanedConfigurations \
  -H "Content-Type: application/json"
```

### Add Configuration
```
POST /api/addConfiguration
```
Creates a new WireGuard configuration.

**Request Body:**
```json
{
    "ConfigurationName": "string",
    "Address": "string",
    "ListenPort": "integer",
    "PrivateKey": "string",
    "Protocol": "string",  // Optional, "wg" or "awg"
    "PreUp": "string",     // Optional
    "PostUp": "string",    // Optional
    "PreDown": "string",   // Optional
    "PostDown": "string"   // Optional
}
```

**Response:**
```json
{
    "status": true,
    "message": "string",
    "data": null
}
```

### Toggle Configuration
```
GET /api/toggleConfiguration?configurationName=string
```
Enables or disables a WireGuard configuration.

**Query Parameters:**
- `configurationName`: Name of the configuration to toggle

**Response:**
```json
{
    "status": true,
    "message": "string",
    "data": "boolean"  // Current status after toggle
}
```

### Update Configuration
```
POST /api/updateConfiguration
```
Updates an existing WireGuard configuration.

**Request Body:**
```json
{
    "Name": "string",
    "Address": "string",     // Optional
    "ListenPort": "integer", // Optional
    "PrivateKey": "string",  // Optional
    "DNS": "string",         // Optional
    "MTU": "integer",        // Optional
    "KeepAlive": "integer"   // Optional
}
```

### Delete Configuration
```
POST /api/deleteConfiguration
```
Deletes a WireGuard configuration.

**Request Body:**
```json
{
    "Name": "string"
}
```

### Rename Configuration
```
POST /api/renameConfiguration
```
Renames an existing WireGuard configuration.

**Request Body:**
```json
{
    "Name": "string",
    "NewConfigurationName": "string"
}
```

## Peer Management

### Add Peers
```
POST /api/addPeers/<configName>
```
Adds one or more peers to a configuration.

**Request Body:**
```json
{
    "bulkAdd": "boolean",           // Optional, for adding multiple peers
    "bulkAddAmount": "integer",     // Required if bulkAdd is true
    "preshared_key_bulkAdd": "boolean", // Optional
    "public_key": "string",         // Required if not bulkAdd
    "allowed_ips": ["string"],      // Required if not bulkAdd
    "endpoint_allowed_ip": "string", // Optional
    "DNS": "string",                // Optional
    "mtu": "integer",               // Optional
    "keepalive": "integer",         // Optional
    "name": "string",               // Optional
    "private_key": "string",        // Optional
    "preshared_key": "string"       // Optional
}
```

### Delete Peers
```
POST /api/deletePeers/<configName>
```
Deletes specified peers from a configuration.

**Request Body:**
```json
{
    "peers": ["string"]  // Array of peer IDs
}
```

### Update Peer Settings
```
POST /api/updatePeerSettings/<configName>
```
Updates settings for a specific peer.

**Request Body:**
```json
{
    "id": "string",
    "name": "string",
    "private_key": "string",
    "DNS": "string",
    "allowed_ip": "string",
    "endpoint_allowed_ip": "string",
    "preshared_key": "string",
    "mtu": "integer",
    "keepalive": "integer"
}
```

### Download Peer Configuration
```
GET /api/downloadPeer/<configName>?id=string
```
Downloads the configuration file for a specific peer.

### Download All Peer Configurations
```
GET /api/downloadAllPeers/<configName>
```
Downloads configuration files for all peers in a configuration.

### Get Available IPs
```
GET /api/getAvailableIPs/<configName>
```
Returns a list of available IP addresses for new peers in a specific configuration.

**Path Parameters:**
- `configName`: Name of the configuration

**Response:**
```json
{
    "status": true,
    "data": {
        "available_ips": ["string"],
        "total_available": "number",
        "configuration_name": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/getAvailableIPs/my-config" \
  -H "Content-Type: application/json"
```

### Get Wireguard Configuration Info
```
GET /api/getWireguardConfigurationInfo?configurationName=string
```
Returns detailed information about a WireGuard configuration including peers and their scheduled jobs.

**Query Parameters:**
- `configurationName`: Name of the configuration

**Response:**
```json
{
    "status": true,
    "data": {
        "configurationInfo": "object",
        "configurationPeers": [
            {
                "id": "string",
                "name": "string",
                "public_key": "string",
                "allowed_ip": "string",
                "endpoint": "string",
                "jobs": [
                    {
                        "JobID": "string",
                        "Field": "string",
                        "Action": "string",
                        "Value": "string",
                        "CreationDate": "string",
                        "ExpireDate": "string"
                    }
                ]
            }
        ],
        "configurationRestrictedPeers": ["object"]
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/getWireguardConfigurationInfo?configurationName=my-config" \
  -H "Content-Type: application/json"
```

### Restrict Peers
```
POST /api/restrictPeers/<configName>
```
Restricts access for specified peers in a configuration.

**Request Body:**
```json
{
    "peers": ["string"]  // Array of peer IDs
}
```

### Allow Access to Peers
```
POST /api/allowAccessPeers/<configName>
```
Allows access for previously restricted peers in a configuration.

**Request Body:**
```json
{
    "peers": ["string"]  // Array of peer IDs
}
```

## IPTables Management

### Get PreUp Scripts
```
POST /api/getConfigTablesPreUp
```
Retrieves the PreUp IPTables scripts for a configuration.

**Request Body:**
```json
{
    "configurationName": "string"
}
```

**Response:**
```json
{
    "status": true,
    "data": {
        "paths": ["string"],
        "contents": {"path": "content"},
        "raw_preup": "string"
    }
}
```

### Get PostUp Scripts
```
POST /api/getConfigTablesPostUp
```
Retrieves the PostUp IPTables scripts for a configuration.

### Get PostDown Scripts
```
POST /api/getConfigTablesPostDown
```
Retrieves the PostDown IPTables scripts for a configuration.

### Get PreDown Scripts
```
POST /api/getConfigTablesPreDown
```
Retrieves the PreDown IPTables scripts for a configuration.

### Update IPTables Scripts
```
POST /api/updateConfigTablesPreUp
POST /api/updateConfigTablesPostUp
POST /api/updateConfigTablesPreDown
POST /api/updateConfigTablesPostDown
```
Updates the respective IPTables scripts for a configuration.

**Request Body:**
```json
{
    "configurationName": "string",
    "content": "string"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Script updated successfully"
}
```

## Dashboard Configuration

### Get Dashboard Configuration
```
GET /api/getDashboardConfiguration
```
Returns the current dashboard configuration settings.

### Update Dashboard Configuration Item
```
POST /api/updateDashboardConfigurationItem
```
Updates a specific dashboard configuration setting.

**Request Body:**
```json
{
    "section": "string",
    "key": "string",
    "value": "any"
}
```

### Get Dashboard Theme
```
GET /api/getDashboardTheme
```
Returns the current dashboard theme setting.

### Get Dashboard Version
```
GET /api/getDashboardVersion
```
Returns the current version of the dashboard.

### Get Dashboard Protocol
```
GET /api/getDashboardProto
```
Returns the current protocol setting.

**Response:**
```json
{
    "status": true,
    "data": "string"  // Protocol setting (e.g., "http" or "https")
}
```

### Get Dashboard Theme
```
GET /api/getDashboardTheme
```
Returns the current dashboard theme setting.

**Response:**
```json
{
    "status": true,
    "data": "string"  // Theme name (e.g., "dark", "light")
}
```

### Get Dashboard Version
```
GET /api/getDashboardVersion
```
Returns the current version of the dashboard.

**Response:**
```json
{
    "status": true,
    "data": "string"  // Version string (e.g., "acid-rain-beta-v0.4")
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/getDashboardVersion \
  -H "Content-Type: application/json"
```

## System Status

### Get System Status
```
GET /api/systemStatus
```
Returns comprehensive system status information including CPU, memory, disk, and network usage.

**Response:**
```json
{
    "status": true,
    "data": {
        "cpu": {
            "cpu_percent": "number",
            "cpu_percent_per_cpu": ["number"]
        },
        "memory": {
            "virtual_memory": {
                "total": "number",
                "available": "number",
                "percent": "number"
            },
            "swap_memory": {
                "total": "number",
                "used": "number",
                "percent": "number"
            }
        },
        "disk": {
            "mountpoint": {
                "total": "number",
                "used": "number",
                "free": "number",
                "percent": "number"
            }
        },
        "network": {
            "interface": {
                "byte_sent": "number",
                "byte_recv": "number"
            }
        },
        "process": {
            "cpu_top_10": ["object"],
            "memory_top_10": ["object"]
        }
    }
}
```

## Authentication & Security

### Check TOTP Status
```
GET /api/isTotpEnabled
```
Checks if Two-Factor Authentication (TOTP) is enabled.

### Get TOTP Setup Link
```
GET /api/Welcome_GetTotpLink
```
Generates a new TOTP setup link for initial configuration.

### Verify TOTP Setup
```
POST /api/Welcome_VerifyTotpLink
```
Verifies the TOTP setup.

**Request Body:**
```json
{
    "totp": "string"
}
```

### Complete Initial Setup
```
POST /api/Welcome_Finish
```
Completes the initial dashboard setup.

**Request Body:**
```json
{
    "username": "string",
    "newPassword": "string",
    "repeatNewPassword": "string"
}
```

### Validate Authentication
```
GET /api/validateAuthentication
```
Validates the current authentication status.

**Response:**
```json
{
    "status": true,
    "data": "boolean"
}
```

### Require Authentication
```
GET /api/requireAuthentication
```
Checks if authentication is required.

**Response:**
```json
{
    "status": true,
    "data": "boolean"
}
```

### Authenticate
```
POST /api/authenticate
```
Authenticates a user.

**Request Body:**
```json
{
    "username": "string",
    "password": "string",
    "totp": "string"  // Optional
}
```

### Sign Out
```
GET /api/signout
```
Signs out the current user.

## Share Management

### Create Share Link
```
POST /api/sharePeer/create
```
Creates a share link for a peer configuration.

**Request Body:**
```json
{
    "Configuration": "string",
    "Peer": "string",
    "ExpireDate": "string"  // Optional
}
```

### Update Share Link
```
POST /api/sharePeer/update
```
Updates an existing share link.

**Request Body:**
```json
{
    "ShareID": "string",
    "ExpireDate": "string"
}
```

### Get Shared Configuration
```
GET /api/sharePeer/get?ShareID=string
```
Retrieves a shared peer configuration.

## Raw Configuration Management

### Get Raw Configuration File
```
GET /api/getConfigurationRawFile?configurationName=string
```
Returns the raw configuration file content for a WireGuard configuration.

**Response:**
```json
{
    "status": true,
    "data": {
        "path": "string",
        "content": "string"
    }
}
```

### Update Raw Configuration File
```
POST /api/updateConfigurationRawFile
```
Updates the raw configuration file content.

**Request Body:**
```json
{
    "configurationName": "string",
    "rawConfiguration": "string"
}
```

## Dashboard API Keys

### Get API Keys
```
GET /api/getDashboardAPIKeys
```
Returns all dashboard API keys.

### Create New API Key
```
POST /api/newDashboardAPIKey
```
Creates a new dashboard API key.

**Request Body:**
```json
{
    "neverExpire": "boolean",
    "ExpiredAt": "string"  // Required if neverExpire is false, format: "YYYY-MM-DD HH:MM:SS"
}
```

### Delete API Key
```
POST /api/deleteDashboardAPIKey
```
Deletes a dashboard API key.

**Request Body:**
```json
{
    "Key": "string"
}
```

## Peer Data Management

### Reset Peer Data
```
POST /api/resetPeerData/<configName>
```
Resets data usage statistics for a peer.

**Request Body:**
```json
{
    "id": "string",
    "type": "string"
}
```

### Get Configuration Info
```
GET /api/getWireguardConfigurationInfo?configurationName=string
```
Returns detailed information about a WireGuard configuration including peers.

**Response:**
```json
{
    "status": true,
    "data": {
        "configurationInfo": "object",
        "configurationPeers": ["object"],
        "configurationRestrictedPeers": ["object"]
    }
}
```

## LDAP Integration

### Get LDAP Settings
```
GET /api/getLDAPSettings
```
Returns the current LDAP configuration settings.

### Save LDAP Settings
```
POST /api/saveLDAPSettings
```
Updates the LDAP configuration settings.

**Request Body:**
```json
{
    "enabled": "boolean",
    "server": "string",
    "port": "integer",
    "use_ssl": "boolean",
    "domain": "string",
    "bind_dn": "string",
    "bind_password": "string",
    "search_base": "string",
    "search_filter": "string",
    "attr_username": "string",
    "require_group": "boolean",
    "group_dn": "string"
}
```

### Test LDAP Connection
```
POST /api/testLDAPConnection
```
Tests the LDAP connection with the current settings.

**Response:**
```json
{
    "status": true,
    "message": "string",
    "data": "boolean"
}
```

## Locale Management

### Get Current Language
```
GET /api/locale
```
Returns the current language setting.

**Response:**
```json
{
    "status": true,
    "data": "string" // Language code
}
```

### Get Available Languages
```
GET /api/locale/available
```
Returns a list of available language options.

**Response:**
```json
{
    "status": true,
    "data": ["string"] // Array of language codes
}
```

### Update Language
```
POST /api/locale/update
```
Updates the current language setting.

**Request Body:**
```json
{
    "lang_id": "string"
}
```

**Response:**
```json
{
    "status": true,
    "data": "string" // Updated language code
}
```

## Email Integration

### Check Email Ready
```
GET /api/email/ready
```
Checks if the email configuration is ready to use.

**Response:**
```json
{
    "status": true,
    "data": "boolean"
}
```

### Send Email
```
POST /api/email/send
```
Sends an email, optionally with peer configuration attachment.

**Request Body:**
```json
{
    "Receiver": "string",
    "Subject": "string",
    "Body": "string",
    "ConfigurationName": "string",  // Optional, required if sending peer config
    "Peer": "string",              // Optional, required if sending peer config
    "IncludeAttachment": "boolean" // Optional
}
```

### Preview Email Body
```
POST /api/email/previewBody
```
Previews the email body with template variables replaced.

**Request Body:**
```json
{
    "Body": "string",
    "ConfigurationName": "string",
    "Peer": "string"
}
```

## Tor Integration

### Get Tor Configuration
```
GET /api/tor/config
```
Gets the current Tor configuration.

**Response:**
```json
{
    "status": true,
    "data": {
        "config": "object"
    }
}
```

### Get Tor Plugins
```
GET /api/tor/plugins
```
Gets available Tor plugins.

**Response:**
```json
{
    "status": true,
    "data": {
        "plugins": ["array of plugins"]
    }
}
```

### Update Tor Configuration
```
POST /api/tor/config/update
```
Updates the Tor configuration.

**Request Body:**
```json
{
    "config": "object"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Configuration updated successfully"
}
```

### Update Tor Plugin
```
POST /api/tor/plugin/update
```
Updates a Tor plugin configuration.

**Request Body:**
```json
{
    "plugin": "string",
    "config": "object"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Plugin updated successfully"
}
```

### Refresh Tor Bridges
```
POST /api/tor/bridges/refresh
```
Refreshes the Tor bridges list.

**Response:**
```json
{
    "status": true,
    "message": "Bridges refreshed successfully"
}
```

### Control Tor Process
```
POST /api/tor/process/control
```
Controls the Tor process (start/stop/restart).

**Request Body:**
```json
{
    "action": "string" // "start", "stop", or "restart"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Process action completed successfully"
}
```

### Get Tor Process Status
```
GET /api/tor/process/status
```
Gets the current status of the Tor process.

**Response:**
```json
{
    "status": true,
    "data": {
        "running": "boolean",
        "pid": "number"
    }
}
```

### Get Tor Log Files
```
GET /api/tor/logs/files
```
Gets a list of available Tor log files.

**Response:**
```json
{
    "status": true,
    "data": {
        "files": ["array of log files"]
    }
}
```

### Get Tor Logs
```
GET /api/tor/logs
```
Gets the contents of Tor logs.

**Response:**
```json
{
    "status": true,
    "data": {
        "logs": "string"
    }
}
```

### Clear Tor Logs
```
POST /api/tor/logs/clear
```
Clears the Tor logs.

**Response:**
```json
{
    "status": true,
    "message": "Logs cleared successfully"
}
```

## Traffic Weir API

The Traffic Weir API provides comprehensive traffic shaping and rate limiting capabilities for WireGuard peers using Linux traffic control (tc) with multiple scheduler types.

### Set Peer Rate Limit
```
POST /api/set_peer_rate_limit
```
Sets traffic rate limits for a WireGuard peer using configurable schedulers.

**Request Body:**
```json
{
    "interface": "string",
    "peer_key": "string",
    "upload_rate": "number",
    "download_rate": "number",
    "scheduler_type": "string"  // "htb", "hfsc", or "cake"
}
```

**Parameters:**
- `interface`: Name of the WireGuard interface
- `peer_key`: Public key of the peer
- `upload_rate`: Upload rate limit in kbps
- `download_rate`: Download rate limit in kbps
- `scheduler_type`: Traffic scheduler type ("htb", "hfsc", or "cake")

**Response:**
```json
{
    "status": true,
    "message": "Successfully configured rate limiting for peer peer_id on interface interface_name"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "wg0",
    "peer_key": "ABC123...",
    "upload_rate": 1000,
    "download_rate": 2000,
    "scheduler_type": "htb"
  }'
```

### Get Peer Rate Limit
```
GET /api/get_peer_rate_limit?interface=string&peer_key=string
```
Gets the current rate limits for a peer.

**Query Parameters:**
- `interface`: Name of the WireGuard interface
- `peer_key`: Public key of the peer (URL encoded)

**Response:**
```json
{
    "status": true,
    "message": "Rate limits retrieved successfully",
    "data": {
        "upload_rate": "number",
        "download_rate": "number",
        "scheduler_type": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/get_peer_rate_limit?interface=wg0&peer_key=ABC123..." \
  -H "Content-Type: application/json"
```

### Remove Peer Rate Limit
```
POST /api/remove_peer_rate_limit
```
Removes rate limits from a peer.

**Request Body:**
```json
{
    "interface": "string",
    "peer_key": "string"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Rate limits removed successfully for peer peer_id on interface interface_name"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/remove_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "wg0",
    "peer_key": "ABC123..."
  }'
```

### Get Interface Scheduler
```
GET /api/get_interface_scheduler?interface=string
```
Gets the scheduler type for an interface if any peer has rate limits set.

**Query Parameters:**
- `interface`: Name of the WireGuard interface

**Response:**
```json
{
    "status": true,
    "message": "Interface scheduler type retrieved successfully",
    "data": {
        "scheduler_type": "string",
        "locked": "boolean"
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/get_interface_scheduler?interface=wg0" \
  -H "Content-Type: application/json"
```

### Nuke Interface
```
POST /api/nuke_interface
```
Removes all traffic control qdiscs from an interface. This is useful for resetting all traffic shaping rules.

**Request Body:**
```json
{
    "interface": "string"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Successfully nuked all traffic control on interface interface_name"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/nuke_interface \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "wg0"
  }'
```

**Scheduler Types:**
- **HTB (Hierarchical Token Bucket)**: Default scheduler, good for general traffic shaping
- **HFSC (Hierarchical Fair Service Curve)**: More advanced scheduler with better fairness
- **CAKE (Common Applications Kept Enhanced)**: Modern scheduler with automatic flow classification

## Network Utilities

The Network Utilities API provides comprehensive network diagnostic and monitoring tools for WireGuard configurations.

### Execute Ping
```
GET /api/ping/execute?ipAddress=string&count=number
```
Performs a ping test to the specified IP address with configurable packet count.

**Query Parameters:**
- `ipAddress`: IP address to ping (IPv4 or IPv6)
- `count`: Number of ping packets to send

**Response:**
```json
{
    "status": true,
    "data": {
        "address": "string",
        "is_alive": "boolean",
        "min_rtt": "number",
        "avg_rtt": "number",
        "max_rtt": "number",
        "package_sent": "number",
        "package_received": "number",
        "package_loss": "number",
        "geo": {
            "city": "string",
            "country": "string",
            "lat": "number",
            "lon": "number"
        }
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/ping/execute?ipAddress=8.8.8.8&count=5" \
  -H "Content-Type: application/json"
```

### Execute Traceroute
```
GET /api/traceroute/execute?ipAddress=string
```
Performs a traceroute to the specified IP address to show the network path.

**Query Parameters:**
- `ipAddress`: IP address to trace route to

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "hop": "number",
            "ip": "string",
            "avg_rtt": "number",
            "min_rtt": "number",
            "max_rtt": "number",
            "geo": {
                "city": "string",
                "country": "string",
                "lat": "number",
                "lon": "number"
            }
        }
    ]
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/traceroute/execute?ipAddress=8.8.8.8" \
  -H "Content-Type: application/json"
```

### Get All Peer IP Addresses
```
GET /api/ping/getAllPeersIpAddress
```
Returns all peer IP addresses organized by configuration with endpoint information.

**Response:**
```json
{
    "status": true,
    "data": {
        "configName": {
            "peerName - peerId": {
                "allowed_ips": ["string"],
                "endpoint": "string"
            }
        }
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/ping/getAllPeersIpAddress \
  -H "Content-Type: application/json"
```

### Get Dashboard Update
```
GET /api/getDashboardUpdate
```
Checks for available dashboard updates by querying Docker Hub for the latest version.

**Response:**
```json
{
    "status": true,
    "message": "string",
    "data": {
        "url": "string",
        "changelog": ["string"],
        "message": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/getDashboardUpdate \
  -H "Content-Type: application/json"
```

**Features:**
- Automatic version checking from Docker Hub
- Changelog retrieval from GitHub
- Background update checking to prevent UI blocking
- Cached results for performance

**Use Cases:**
- Network connectivity testing
- Troubleshooting peer connections
- Geographic location analysis
- Update notifications
- Network path analysis

## Peer Jobs API

### Save Peer Schedule Job
```
POST /api/savePeerScheduleJob
```
Creates or updates a scheduled job for a peer.

**Request Body:**
```json
{
    "Job": {
        "JobID": "string",
        "Configuration": "string",
        "Peer": "string",
        "Field": "string",         // "weekly" or "total_receive" or "total_sent" or "total_data"
        "Operator": "string",
        "Value": "string",         // For weekly: "day:HH:MM-HH:MM,..." format
        "CreationDate": "string",
        "ExpireDate": "string",
        "Action": "string"         // "restrict", "delete", or "rate_limit"
    }
}
```

For rate limit actions, the Value field should be a JSON string containing:
```json
{
    "upload_rate": "number",
    "download_rate": "number"
}
```

### Delete Peer Schedule Job
```
POST /api/deletePeerScheduleJob
```
Deletes a scheduled job for a peer.

**Request Body:**
```json
{
    "Job": {
        "JobID": "string",
        "Configuration": "string",
        "Peer": "string",
        "Field": "string",
        "Operator": "string",
        "Value": "string",
        "CreationDate": "string",
        "ExpireDate": "string",
        "Action": "string"
    }
}
```

### Get Peer Schedule Job Logs
```
GET /api/getPeerScheduleJobLogs/<configName>?requestAll=boolean
```
Retrieves logs for scheduled jobs of a configuration.

**Query Parameters:**
- `requestAll`: Whether to get all logs or just recent ones
- `configName`: Name of the configuration

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "JobID": "string",
            "Status": "boolean",
            "Message": "string",
            "Timestamp": "string"
        }
    ]
}
```

## Data Charts API

The Data Charts API provides real-time traffic monitoring and analytics for WireGuard configurations.

### Get Configuration Realtime Traffic
```
GET /api/getConfigurationRealtimeTraffic?configurationName=string
```
Returns realtime traffic usage data for a specific configuration.

**Query Parameters:**
- `configurationName`: Name of the configuration to get traffic data for

**Response:**
```json
{
    "status": true,
    "data": {
        "upload": "number",      // Upload traffic in bytes
        "download": "number",    // Download traffic in bytes
        "total": "number"        // Total traffic in bytes
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/getConfigurationRealtimeTraffic?configurationName=wg0" \
  -H "Content-Type: application/json"
```

**Use Cases:**
- Real-time monitoring dashboards
- Traffic usage alerts
- Bandwidth consumption tracking
- Network performance analysis

## Snapshot API

### Get Configuration Backup
```
GET /api/getConfigurationBackup?configurationName=string
```
Gets backups for a specific configuration.

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "filename": "string",
            "backupDate": "string",
            "content": "string",
            "database": "boolean",
            "databaseContent": "string",
            "iptables_scripts": "boolean",
            "iptablesContent": "string"
        }
    ]
}
```

### Get All Configuration Backups
```
GET /api/getAllConfigurationBackup
```
Gets all configuration backups with organized structure.

**Response:**
```json
{
    "status": true,
    "data": {
        "ExistingConfigurations": {
            "configName": [
                {
                    "filename": "string",
                    "backupDate": "string",
                    "content": "string",
                    "database": "boolean",
                    "databaseContent": "string",
                    "iptables_scripts": "boolean",
                    "iptablesContent": "string"
                }
            ]
        },
        "NonExistingConfigurations": {
            "configName": [
                // Same structure as above
            ]
        }
    }
}
```

### Create Configuration Backup
```
GET /api/createConfigurationBackup?configurationName=string
```
Creates a backup for a specific configuration.

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "filename": "string",
            "backupDate": "string",
            "content": "string",
            "database": "boolean",
            "databaseContent": "string",
            "iptables_scripts": "boolean",
            "iptablesContent": "string"
        }
    ]
}
```

### Download Configuration Backup
```
GET /api/downloadConfigurationBackup?configurationName=string&backupFileName=string
```
Downloads a backup file as a 7z archive.

**Response:**
Binary file download with Content-Type: application/x-7z-compressed

### Delete Configuration Backup
```
POST /api/deleteConfigurationBackup
```
Deletes a configuration backup.

**Request Body:**
```json
{
    "configurationName": "string",
    "backupFileName": "string"
}
```

### Restore Configuration Backup
```
POST /api/restoreConfigurationBackup
```
Restores a configuration from a backup.

**Request Body:**
```json
{
    "configurationName": "string",
    "backupFileName": "string"
}
```

### Upload Configuration Backup
```
POST /api/uploadConfigurationBackup
```
Uploads a configuration backup file.

**Request Body:**
Multipart form data with the backup file.

---

### Common Response Format
All API endpoints return responses in the following format:
```json
{
    "status": "boolean",
    "message": "string",  // Optional
    "data": "any"        // Optional
}
```

### Error Handling
In case of errors, the response will include:
- `status`: false
- `message`: Description of the error
- `data`: null or additional error details

### Authentication
Most endpoints require authentication. Ensure you include appropriate authentication headers with your requests.

### Rate Limiting
The API may include rate limiting. Please handle 429 (Too Many Requests) responses appropriately.

## Authentication API

The Authentication API provides comprehensive authentication and session management capabilities including local authentication, LDAP integration, API key management, and advanced security features.

### Handshake
```
GET /api/handshake
```
Performs authentication handshake to establish a session.

**Response:**
```json
{
    "status": true,
    "data": {
        "token": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/handshake \
  -H "Content-Type: application/json"
```

### Security Check
```
GET /api/security-check
```
Performs security startup checks to ensure the system is properly configured.

**Response:**
```json
{
    "status": true,
    "message": "Security checks completed successfully"
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/security-check \
  -H "Content-Type: application/json"
```

### Get CSRF Token
```
GET /api/csrf-token
```
Gets a CSRF token for form submissions.

**Response:**
```json
{
    "status": true,
    "data": {
        "csrf_token": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/csrf-token \
  -H "Content-Type: application/json" \
  -b "authToken=your_auth_token"
```

### Validate CSRF Token
```
POST /api/validate-csrf
```
Validates a CSRF token for security.

**Request Body:**
```json
{
    "csrf_token": "string"
}
```

**Response:**
```json
{
    "status": true,
    "message": "CSRF token is valid"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/validate-csrf \
  -H "Content-Type: application/json" \
  -b "authToken=your_auth_token" \
  -d '{"csrf_token": "your_csrf_token"}'
```

### Get Rate Limit Status
```
GET /api/rate-limit-status
```
Gets the current rate limit status for the requesting IP address.

**Response:**
```json
{
    "status": true,
    "data": {
        "identifier": "string",
        "is_limited": "boolean",
        "remaining_requests": "number",
        "reset_time": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/rate-limit-status \
  -H "Content-Type: application/json"
```

### Reset Rate Limit
```
POST /api/reset-rate-limit
```
Resets rate limit for a specific identifier (admin function).

**Request Body:**
```json
{
    "identifier": "string"
}
```

**Response:**
```json
{
    "status": true,
    "message": "Rate limit reset for identifier"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/reset-rate-limit \
  -H "Content-Type: application/json" \
  -H "wg-dashboard-apikey: your-api-key" \
  -d '{"identifier": "192.168.1.100"}'
```

### Test Distributed Rate Limit
```
GET /api/distributed-rate-limit-test
```
Tests the distributed rate limiting system.

**Response:**
```json
{
    "status": true,
    "data": {
        "is_limited": "boolean",
        "info": "object",
        "identifier": "string"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/distributed-rate-limit-test \
  -H "Content-Type: application/json"
```

### Get Rate Limit Metrics
```
GET /api/rate-limit-metrics
```
Gets rate limiting metrics and statistics (admin function).

**Query Parameters:**
- `window`: Time window in seconds (default: 3600)

**Response:**
```json
{
    "status": true,
    "data": {
        "total_requests": "number",
        "blocked_requests": "number",
        "unique_identifiers": "number",
        "top_identifiers": ["object"]
    }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/rate-limit-metrics?window=3600" \
  -H "Content-Type: application/json" \
  -H "wg-dashboard-apikey: your-api-key"
```

### Get Rate Limit Health
```
GET /api/rate-limit-health
```
Gets the health status of the rate limiting system.

**Response:**
```json
{
    "status": true,
    "data": {
        "system_healthy": "boolean",
        "redis_connected": "boolean",
        "metrics_available": "boolean"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/rate-limit-health \
  -H "Content-Type: application/json"
```

### Get Top Limited Identifiers
```
GET /api/top-limited-identifiers
```
Gets the top identifiers that are being rate limited (admin function).

**Query Parameters:**
- `limit`: Number of identifiers to return (default: 10)

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "identifier": "string",
            "request_count": "number",
            "blocked_count": "number",
            "last_seen": "string"
        }
    ]
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8080/api/top-limited-identifiers?limit=10" \
  -H "Content-Type: application/json" \
  -H "wg-dashboard-apikey: your-api-key"
```

### Cleanup Rate Limit Metrics
```
POST /api/cleanup-rate-limit-metrics
```
Cleans up old rate limiting metrics data (admin function).

**Response:**
```json
{
    "status": true,
    "message": "Cleaned up X old metrics entries"
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/cleanup-rate-limit-metrics \
  -H "Content-Type: application/json" \
  -H "wg-dashboard-apikey: your-api-key"
```

### Validate Authentication
```
GET /api/validateAuthentication
```
Validates the current authentication status and session.

**Response:**
```json
{
    "status": true,
    "data": "boolean"  // true if authenticated, false otherwise
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/validateAuthentication \
  -H "Content-Type: application/json" \
  -b "authToken=your_auth_token"
```

### Require Authentication
```
GET /api/requireAuthentication
```
Checks if authentication is required for the dashboard.

**Response:**
```json
{
    "status": true,
    "data": "boolean"  // true if authentication is required
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/requireAuthentication \
  -H "Content-Type: application/json"
```

### Authenticate
```
POST /api/authenticate
```
Authenticates a user with username/password and optional TOTP.

**Request Body:**
```json
{
    "username": "string",
    "password": "string",
    "totp": "string"  // Optional, required if TOTP is enabled
}
```

**Response:**
```json
{
    "status": true,
    "message": "string",  // Welcome message
    "data": "string"      // Authentication token
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password123",
    "totp": "123456"
  }'
```

### Sign Out
```
GET /api/signout
```
Signs out the current user and clears the session.

**Response:**
```json
{
    "status": true,
    "message": "",
    "data": null
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/signout \
  -H "Content-Type: application/json" \
  -b "authToken=your_auth_token"
```

**Authentication Methods:**
- **Local Authentication**: Username/password stored in dashboard configuration
- **LDAP Authentication**: Integration with LDAP/Active Directory servers
- **TOTP (Two-Factor Authentication)**: Time-based one-time passwords
- **API Key Authentication**: Programmatic access using API keys

**Security Features:**
- Constant-time comparison to prevent timing attacks
- Secure session management with HTTP-only cookies
- Comprehensive logging of authentication attempts
- Support for multiple authentication backends

## Thread Pool API

The Thread Pool API provides high-performance parallel processing capabilities for bulk operations using Python's ThreadPoolExecutor.

### Get Thread Pool Status
```
GET /api/threadPool/status
```
Returns the current status and statistics of the thread pool.

**Response:**
```json
{
    "status": true,
    "data": {
        "active": "boolean",
        "max_workers": "number",
        "current_workers": "number",
        "queue_size": "number"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/threadPool/status \
  -H "Content-Type: application/json"
```

### Bulk Peer Status Check
```
POST /api/threadPool/bulkPeerStatus
```
Checks the status of multiple peers in parallel using the thread pool.

**Request Body:**
```json
{
    "peer_ids": ["string"],
    "configuration_name": "string"
}
```

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "peer_id": "string",
            "is_online": "boolean",
            "last_seen": "string",
            "response_time": "number"
        }
    ]
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8080/api/threadPool/bulkPeerStatus \
  -H "Content-Type: application/json" \
  -d '{
    "peer_ids": ["peer1", "peer2", "peer3"],
    "configuration_name": "my-vpn"
  }'
```

### Bulk Redis Operations
```
POST /api/threadPool/bulkRedisOps
```
Executes multiple Redis operations in parallel using the thread pool.

**Request Body:**
```json
{
    "operations": [
        {
            "operation": "string",
            "key": "string",
            "value": "any"
        }
    ]
}
```

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "operation": "string",
            "success": "boolean",
            "result": "any",
            "error": "string"
        }
    ]
}
```

### Bulk File Operations
```
POST /api/threadPool/bulkFileOps
```
Executes multiple file operations in parallel using the thread pool.

**Request Body:**
```json
{
    "operations": [
        {
            "operation": "string",
            "file_path": "string",
            "data": "any"
        }
    ]
}
```

### Bulk WireGuard Commands
```
POST /api/threadPool/bulkWgCommands
```
Executes multiple WireGuard commands in parallel using the thread pool.

**Request Body:**
```json
{
    "commands": [
        {
            "command": "string",
            "args": ["string"],
            "timeout": "number"
        }
    ]
}
```

## Process Pool API

The Process Pool API provides CPU-intensive parallel processing capabilities using Python's ProcessPoolExecutor for tasks that benefit from true parallelism.

### Get Process Pool Status
```
GET /api/processPool/status
```
Returns the current status and statistics of the process pool.

**Response:**
```json
{
    "status": true,
    "data": {
        "active": "boolean",
        "max_workers": "number",
        "current_workers": "number",
        "queue_size": "number"
    }
}
```

**Example Usage:**
```bash
curl -X GET http://localhost:8080/api/processPool/status \
  -H "Content-Type: application/json"
```

### Bulk Peer Processing
```
POST /api/processPool/bulkPeerProcessing
```
Processes multiple peers in parallel using the process pool.

**Request Body:**
```json
{
    "peers_data": [
        {
            "peer_id": "string",
            "configuration_name": "string",
            "operation": "string"
        }
    ]
}
```

**Response:**
```json
{
    "status": true,
    "data": [
        {
            "peer_id": "string",
            "success": "boolean",
            "result": "any",
            "processing_time": "number"
        }
    ]
}
```

### Bulk Peer Validation
```
POST /api/processPool/bulkPeerValidation
```
Validates multiple peers in parallel using the process pool.

**Request Body:**
```json
{
    "peers_data": [
        {
            "peer_id": "string",
            "public_key": "string",
            "allowed_ips": "string"
        }
    ]
}
```

### Bulk Peer Encryption
```
POST /api/processPool/bulkPeerEncryption
```
Encrypts multiple peers in parallel using the process pool.

**Request Body:**
```json
{
    "peers_data": [
        {
            "peer_id": "string",
            "private_key": "string",
            "public_key": "string"
        }
    ]
}
```

### Bulk Usage Analysis
```
POST /api/processPool/bulkUsageAnalysis
```
Analyzes usage patterns for multiple peers in parallel using the process pool.

**Request Body:**
```json
{
    "usage_data_list": [
        {
            "peer_id": "string",
            "traffic_data": "object",
            "time_range": "string"
        }
    ]
}
```

### Bulk QR Code Generation
```
POST /api/processPool/bulkQrGeneration
```
Generates QR codes for multiple peers in parallel using the process pool.

**Request Body:**
```json
{
    "peer_data_list": [
        {
            "peer_id": "string",
            "configuration_data": "string",
            "qr_size": "number"
        }
    ]
}
```

### Process Pool Performance Test
```
POST /api/processPool/performanceTest
```
Tests process pool performance with CPU-intensive tasks.

**Request Body:**
```json
{
    "task_count": "number",
    "task_duration": "number"
}
```

**Response:**
```json
{
    "status": true,
    "data": {
        "total_time": "number",
        "average_time_per_task": "number",
        "tasks_completed": "number",
        "throughput": "number"
    }
}
```

**Use Cases:**
- High-performance bulk operations
- CPU-intensive data processing
- Parallel peer management
- Performance testing and benchmarking
- Resource-intensive cryptographic operations

---

## Complete API Examples

This section provides comprehensive examples for common use cases with the WireGate API.

### Example 1: Complete Configuration Management Workflow

```bash
#!/bin/bash
# Complete workflow for managing a WireGuard configuration

# 1. Check if authentication is required
AUTH_REQUIRED=$(curl -s http://localhost:8080/api/requireAuthentication | jq -r '.data')

if [ "$AUTH_REQUIRED" = "true" ]; then
    # 2. Authenticate
    AUTH_RESPONSE=$(curl -s -X POST http://localhost:8080/api/authenticate \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "password123"}')
    
    # Extract auth token
    AUTH_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.data')
    COOKIE_HEADER="Cookie: authToken=$AUTH_TOKEN"
else
    COOKIE_HEADER=""
fi

# 3. Create a new configuration
curl -s -X POST http://localhost:8080/api/addConfiguration \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "ConfigurationName": "my-vpn",
        "Address": "10.0.0.1/24",
        "ListenPort": 51820,
        "PrivateKey": "generated_private_key_here"
    }'

# 4. Add a peer to the configuration
curl -s -X POST http://localhost:8080/api/addPeers/my-vpn \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "public_key": "peer_public_key_here",
        "allowed_ips": "10.0.0.2/32",
        "name": "client-1"
    }'

# 5. Get configuration info
curl -s -X GET "http://localhost:8080/api/getWireguardConfigurationInfo?configurationName=my-vpn" \
    -H "$COOKIE_HEADER"

# 6. Set up rate limiting for the peer
curl -s -X POST http://localhost:8080/api/set_peer_rate_limit \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "interface": "my-vpn",
        "peer_key": "peer_public_key_here",
        "upload_rate": 1000,
        "download_rate": 2000,
        "scheduler_type": "htb"
    }'
```

### Example 2: Automated Peer Management with Scheduled Jobs

```bash
#!/bin/bash
# Set up automated peer management with scheduled jobs

# Create a weekly schedule job to restrict access during business hours
curl -s -X POST http://localhost:8080/api/savePeerScheduleJob \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "Job": {
            "JobID": "weekly-restrict-1",
            "Configuration": "my-vpn",
            "Peer": "peer_public_key_here",
            "Field": "weekly",
            "Value": "1:09:00-17:00,2:09:00-17:00,3:09:00-17:00,4:09:00-17:00,5:09:00-17:00",
            "CreationDate": "2024-01-01 00:00:00",
            "ExpireDate": "2024-12-31 23:59:59",
            "Action": "restrict"
        }
    }'

# Create a data usage job to restrict peers who exceed 1GB
curl -s -X POST http://localhost:8080/api/savePeerScheduleJob \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "Job": {
            "JobID": "data-limit-1",
            "Configuration": "my-vpn",
            "Peer": "peer_public_key_here",
            "Field": "total_data",
            "Operator": "lgt",
            "Value": "1073741824",
            "CreationDate": "2024-01-01 00:00:00",
            "ExpireDate": "2024-12-31 23:59:59",
            "Action": "restrict"
        }
    }'
```

### Example 3: Monitoring and Analytics

```bash
#!/bin/bash
# Comprehensive monitoring and analytics example

# 1. Get system status
echo "=== System Status ==="
curl -s -X GET http://localhost:8080/api/systemStatus \
    -H "$COOKIE_HEADER" | jq '.'

# 2. Get real-time traffic for all configurations
echo "=== Real-time Traffic ==="
for config in $(curl -s -X GET http://localhost:8080/api/getConfigurations \
    -H "$COOKIE_HEADER" | jq -r '.data[].Name'); do
    echo "Configuration: $config"
    curl -s -X GET "http://localhost:8080/api/getConfigurationRealtimeTraffic?configurationName=$config" \
        -H "$COOKIE_HEADER" | jq '.'
done

# 3. Test network connectivity
echo "=== Network Tests ==="
curl -s -X GET "http://localhost:8080/api/ping/execute?ipAddress=8.8.8.8&count=3" \
    -H "$COOKIE_HEADER" | jq '.'

# 4. Get all peer IP addresses
echo "=== All Peer IPs ==="
curl -s -X GET http://localhost:8080/api/ping/getAllPeersIpAddress \
    -H "$COOKIE_HEADER" | jq '.'
```

### Example 4: Backup and Restore Operations

```bash
#!/bin/bash
# Complete backup and restore workflow

# 1. Create a backup of a configuration
echo "Creating backup..."
BACKUP_RESPONSE=$(curl -s -X GET "http://localhost:8080/api/createConfigurationBackup?configurationName=my-vpn" \
    -H "$COOKIE_HEADER")

echo $BACKUP_RESPONSE | jq '.'

# 2. List all available backups
echo "Available backups:"
curl -s -X GET http://localhost:8080/api/getAllConfigurationBackup \
    -H "$COOKIE_HEADER" | jq '.'

# 3. Download a specific backup
BACKUP_FILE="my-vpn_20240101120000.conf"
curl -s -X GET "http://localhost:8080/api/downloadConfigurationBackup?configurationName=my-vpn&backupFileName=$BACKUP_FILE" \
    -H "$COOKIE_HEADER" \
    -o "backup_$BACKUP_FILE.7z"

# 4. Restore from backup
curl -s -X POST http://localhost:8080/api/restoreConfigurationBackup \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d "{
        \"configurationName\": \"my-vpn\",
        \"backupFileName\": \"$BACKUP_FILE\"
    }"
```

### Example 5: Traffic Shaping and Rate Limiting

```bash
#!/bin/bash
# Advanced traffic shaping example

# 1. Set up rate limiting for multiple peers
PEERS=("peer1_key" "peer2_key" "peer3_key")
RATES=("1000:2000" "500:1000" "2000:4000")

for i in "${!PEERS[@]}"; do
    IFS=':' read -r upload download <<< "${RATES[$i]}"
    
    echo "Setting rate limit for peer ${PEERS[$i]}: ${upload}kbps up, ${download}kbps down"
    
    curl -s -X POST http://localhost:8080/api/set_peer_rate_limit \
        -H "Content-Type: application/json" \
        -H "$COOKIE_HEADER" \
        -d "{
            \"interface\": \"my-vpn\",
            \"peer_key\": \"${PEERS[$i]}\",
            \"upload_rate\": $upload,
            \"download_rate\": $download,
            \"scheduler_type\": \"htb\"
        }"
done

# 2. Check current rate limits
echo "Current rate limits:"
for peer in "${PEERS[@]}"; do
    echo "Peer: $peer"
    curl -s -X GET "http://localhost:8080/api/get_peer_rate_limit?interface=my-vpn&peer_key=$peer" \
        -H "$COOKIE_HEADER" | jq '.data'
done

# 3. Get interface scheduler status
echo "Interface scheduler status:"
curl -s -X GET "http://localhost:8080/api/get_interface_scheduler?interface=my-vpn" \
    -H "$COOKIE_HEADER" | jq '.'
```

### Example 6: Email Integration

```bash
#!/bin/bash
# Email integration example

# 1. Check if email is ready
EMAIL_READY=$(curl -s -X GET http://localhost:8080/api/email/ready \
    -H "$COOKIE_HEADER" | jq -r '.data')

if [ "$EMAIL_READY" = "true" ]; then
    # 2. Send peer configuration via email
    curl -s -X POST http://localhost:8080/api/email/send \
        -H "Content-Type: application/json" \
        -H "$COOKIE_HEADER" \
        -d '{
            "Receiver": "user@example.com",
            "Subject": "Your VPN Configuration",
            "Body": "Please find your VPN configuration attached.",
            "ConfigurationName": "my-vpn",
            "Peer": "peer_public_key_here",
            "IncludeAttachment": true
        }'
    
    # 3. Preview email body with template variables
    curl -s -X POST http://localhost:8080/api/email/previewBody \
        -H "Content-Type: application/json" \
        -H "$COOKIE_HEADER" \
        -d '{
            "Body": "Hello {{ peer.name }}, your VPN config is ready!",
            "ConfigurationName": "my-vpn",
            "Peer": "peer_public_key_here"
        }' | jq -r '.data'
fi
```

### Example 7: LDAP Integration

```bash
#!/bin/bash
# LDAP configuration example

# 1. Get current LDAP settings
echo "Current LDAP settings:"
curl -s -X GET http://localhost:8080/api/getLDAPSettings \
    -H "$COOKIE_HEADER" | jq '.'

# 2. Configure LDAP settings
curl -s -X POST http://localhost:8080/api/saveLDAPSettings \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "enabled": true,
        "server": "ldap.example.com",
        "port": 389,
        "use_ssl": false,
        "domain": "example.com",
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "admin_password",
        "search_base": "ou=users,dc=example,dc=com",
        "search_filter": "(uid=%s)",
        "attr_username": "uid",
        "require_group": true,
        "group_dn": "cn=vpn-users,ou=groups,dc=example,dc=com"
    }'

# 3. Test LDAP connection
curl -s -X POST http://localhost:8080/api/testLDAPConnection \
    -H "Content-Type: application/json" \
    -H "$COOKIE_HEADER" \
    -d '{
        "server": "ldap.example.com",
        "port": 389,
        "use_ssl": false,
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "admin_password",
        "search_base": "ou=users,dc=example,dc=com"
    }' | jq '.'
```

## Best Practices

1. **Error Handling**: Always check the `status` field in responses and implement proper error handling
2. **Rate Limiting**: Implement exponential backoff for retry logic
3. **Authentication**: Store API keys securely and rotate them regularly
4. **Monitoring**: Use the system status and traffic monitoring endpoints for health checks
5. **Backups**: Regularly create backups of your configurations
6. **Logging**: Monitor the dashboard logs for security and operational insights
7. **Testing**: Use the network utilities to test connectivity and troubleshoot issues

## Troubleshooting

### Common Issues

1. **Authentication Failures**: Check credentials and ensure TOTP is configured correctly
2. **Rate Limiting**: Implement proper retry logic with exponential backoff
3. **Configuration Errors**: Validate all required parameters before making requests
4. **Network Issues**: Use the ping and traceroute utilities to diagnose connectivity problems
5. **Permission Errors**: Ensure the dashboard has proper permissions for WireGuard operations

### Debug Mode

Enable debug logging by checking the dashboard configuration and monitoring the logs for detailed error information.

---

*This documentation covers all available API endpoints in WireGate. For additional support or feature requests, please refer to the project repository.*
