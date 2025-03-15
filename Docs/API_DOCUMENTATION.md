# WireGate API Documentation

This document provides detailed information about all available API endpoints in the WireGate application.

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
Returns a list of available IP addresses for new peers.

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

### Set Peer Rate Limit
```
POST /api/set_peer_rate_limit
```
Sets traffic rate limits for a WireGuard peer.

**Request Body:**
```json
{
    "interface": "string",
    "peer_key": "string",
    "upload_rate": "number",
    "download_rate": "number",
    "scheduler_type": "string"  // "htb" or "hfsc"
}
```

### Get Peer Rate Limit
```
GET /api/get_peer_rate_limit?interface=string&peer_key=string
```
Gets the current rate limits for a peer.

**Response:**
```json
{
    "status": true,
    "data": {
        "upload_rate": "number",
        "download_rate": "number",
        "scheduler_type": "string"
    }
}
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

### Get Interface Scheduler
```
GET /api/get_interface_scheduler
```
Gets the scheduler type for an interface if any peer has it set.

**Response:**
```json
{
    "status": true,
    "data": {
        "scheduler_type": "string",
        "locked": "boolean"
    }
}
```

### Nuke Interface
```
POST /api/nuke_interface
```
Removes all traffic control qdiscs from an interface.

**Request Body:**
```json
{
    "interface": "string"
}
```

## Network Utilities

### Execute Ping
```
GET /api/ping/execute?ipAddress=string&count=number
```
Performs a ping test to the specified IP address.

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
        "geo": "object"  // Optional geolocation data
    }
}
```

### Execute Traceroute
```
GET /api/traceroute/execute?ipAddress=string
```
Performs a traceroute to the specified IP address.

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
            "geo": "object"  // Optional geolocation data
        }
    ]
}
```

### Get All Peer IP Addresses
```
GET /api/ping/getAllPeersIpAddress
```
Returns all peer IP addresses organized by configuration.

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

### Get Dashboard Update
```
GET /api/getDashboardUpdate
```
Checks for available dashboard updates.

**Response:**
```json
{
    "status": true,
    "data": {
        "current_version": "string",
        "latest_version": "string",
        "update_available": "boolean",
        "changelog": "string"
    }
}
```

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

### Get Configuration Realtime Traffic
```
GET /api/getConfigurationRealtimeTraffic?configurationName=string
```
Returns realtime traffic usage data for a configuration.

**Response:**
```json
{
    "status": true,
    "data": {
        "upload": "number",
        "download": "number",
        "total": "number"
    }
}
```

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

### Handshake
```
GET /api/handshake
```
Performs authentication handshake.

**Response:**
```json
{
    "status": true,
    "data": {
        "token": "string"
    }
}
``` 
