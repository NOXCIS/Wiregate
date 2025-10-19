"""
FastAPI Main API Router
Migrated from api.py Flask blueprint
Handles core CRUD operations for configurations, peers, and system status
"""
import os
import pyotp
import psutil
import logging
import json
import shutil
import subprocess
from datetime import datetime
import time
from typing import Dict, Any, List
from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio

from ..models.responses import StandardResponse, SystemStatusResponse
from ..models.requests import (
    ConfigurationCreate, PeerCreate, PeerUpdate, PeerBulkAction,
    DashboardConfigUpdate, APIKeyCreate
)
from ..modules.Core import (
    DashboardConfig, Configuration, Configurations,
    InitWireguardConfigurationsList
)
from ..modules.DataBase import sqlUpdate
from ..modules.ConfigEnv import wgd_config_path
from ..modules.Utilities import (
    GenerateWireguardPublicKey, GenerateWireguardPrivateKey,
    get_backup_paths, RegexMatch
)
from ..modules.Share.ShareLink import AllPeerShareLinks
from ..modules.Security import (
    execute_secure_command, execute_wg_command,
    execute_awg_command, execute_wg_quick_command
)
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db
from ..modules.App import convert_response_object_to_dict
from ..modules.Async import (
    thread_pool, bulk_peer_status_check, redis_bulk_operations,
    file_operations, wg_command_operations, process_pool,
    bulk_peer_processing, bulk_peer_validation,
    bulk_peer_encryption, bulk_usage_analysis, bulk_qr_generation
)

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


def _is_safe_sql_statement(sql: str) -> bool:
    """Validate that SQL statement is safe for execution"""
    sql_upper = sql.upper().strip()
    
    allowed_operations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']
    if not any(sql_upper.startswith(op) for op in allowed_operations):
        return False
    
    dangerous_patterns = [
        'DROP TABLE', 'DROP DATABASE', 'TRUNCATE', 'ALTER TABLE',
        'EXEC', 'EXECUTE', 'UNION', '--', '/*', '*/', ';',
        'INFORMATION_SCHEMA', 'SYS.', 'MYSQL.', 'PG_'
    ]
    
    for pattern in dangerous_patterns:
        if pattern in sql_upper:
            return False
    
    return True


# ============================================================================
# Configuration Management Endpoints
# ============================================================================

@router.get('/getConfigurations', response_model=StandardResponse)
async def get_configurations(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get all WireGuard configurations"""
    InitWireguardConfigurationsList()
    configs = [wc.toJson() for wc in Configurations.values()]
    return StandardResponse(status=True, data=configs)


@router.post('/cleanupOrphanedConfigurations', response_model=StandardResponse)
async def cleanup_orphaned_configurations(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Manually trigger cleanup of orphaned database configurations"""
    try:
        from ..modules.Core import cleanup_orphaned_configurations
        
        conf_path = DashboardConfig.GetConfig("Server", "wg_conf_path")[1]
        confs = os.listdir(conf_path)
        existing_config_files = set()
        
        for i in confs:
            if RegexMatch("^(.{1,}).(conf)$", i):
                existing_config_files.add(i.replace('.conf', ''))
        
        cleanup_orphaned_configurations(existing_config_files)
        
        return StandardResponse(
            status=True,
            message="Orphaned configuration cleanup completed successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Error during cleanup: {str(e)}"
        )


@router.post('/addConfiguration', response_model=StandardResponse)
async def add_configuration(
    config_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Add a new WireGuard configuration"""
    required_keys = ["ConfigurationName", "Address", "ListenPort", "PrivateKey"]
    for key in required_keys:
        if key not in config_data:
            return StandardResponse(
                status=False,
                message="Please provide all required parameters."
            )
    
    # Check duplicates
    for i in Configurations.values():
        if i.Name == config_data['ConfigurationName']:
            return StandardResponse(
                status=False,
                message=f"Already have a configuration with the name \"{config_data['ConfigurationName']}\"",
                data="ConfigurationName"
            )
        if str(i.ListenPort) == str(config_data["ListenPort"]):
            return StandardResponse(
                status=False,
                message=f"Already have a configuration with the port \"{config_data['ListenPort']}\"",
                data="ListenPort"
            )
        if i.Address == config_data["Address"]:
            return StandardResponse(
                status=False,
                message=f"Already have a configuration with the address \"{config_data['Address']}\"",
                data="Address"
            )
    
    # Create iptables directory
    iptables_dir = DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
    if not os.path.exists(iptables_dir):
        try:
            os.makedirs(iptables_dir)
        except Exception as e:
            return StandardResponse(
                status=False,
                message=f"Failed to create iptables directory: {str(e)}"
            )
    
    backup_mode = "Backup" in config_data
    
    if backup_mode:
        # Existing backup mode handling
        config_name = config_data["Backup"].split("_")[0]
        backup_paths = get_backup_paths(config_name)
        backup_file = os.path.join(backup_paths['config_dir'], config_data["Backup"])
        backup_redis = os.path.join(backup_paths['config_dir'], config_data["Backup"].replace('.conf', '.redis'))
        backup_iptables = os.path.join(backup_paths['config_dir'], config_data["Backup"].replace('.conf', '_iptables.json'))
        
        if not os.path.exists(backup_file):
            return StandardResponse(
                status=False,
                message="Backup configuration file does not exist"
            )
        
        # Copy configuration file
        try:
            wg_conf_path = os.path.join(
                DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
                f'{config_data["ConfigurationName"]}.conf'
            )
            shutil.copy(backup_file, wg_conf_path)
        except Exception as e:
            return StandardResponse(
                status=False,
                message=f"Failed to copy configuration file: {str(e)}"
            )
        
        # Create and initialize configuration
        try:
            Configurations[config_data['ConfigurationName']] = Configuration(
                name=config_data['ConfigurationName']
            )
        except Exception as e:
            if os.path.exists(wg_conf_path):
                os.remove(wg_conf_path)
            return StandardResponse(
                status=False,
                message=f"Failed to initialize configuration: {str(e)}"
            )
        
        # Restore database if it exists
        if os.path.exists(backup_redis):
            try:
                with open(backup_redis, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            if not _is_safe_sql_statement(line):
                                logger.warning(f"Skipping potentially unsafe SQL statement: {line}")
                                continue
                            
                            line = line.replace(
                                f'"{config_data["Backup"].split("_")[0]}"',
                                f'"{config_data["ConfigurationName"]}"'
                            )
                            sqlUpdate(line)
            except Exception as e:
                Configurations[config_data['ConfigurationName']].deleteConfiguration()
                Configurations.pop(config_data['ConfigurationName'])
                return StandardResponse(
                    status=False,
                    message=f"Failed to restore database: {str(e)}"
                )
        
        # Restore iptables scripts if they exist
        if os.path.exists(backup_iptables):
            try:
                with open(backup_iptables, 'r') as f:
                    scripts = json.load(f)
                
                script_mapping = {
                    'preup_script': ('PreUp', '-preup.sh'),
                    'postup_script': ('PostUp', '-postup.sh'),
                    'predown_script': ('PreDown', '-predown.sh'),
                    'postdown_script': ('PostDown', '-postdown.sh')
                }
                
                for script_key, (config_attr, suffix) in script_mapping.items():
                    if script_key in scripts:
                        script_path = os.path.join(iptables_dir, f"{config_data['ConfigurationName']}{suffix}")
                        with open(script_path, 'w') as f:
                            f.write(scripts[script_key])
                        os.chmod(script_path, 0o755)
                        
                        setattr(
                            Configurations[config_data['ConfigurationName']],
                            config_attr,
                            script_path
                        )
            except Exception as e:
                Configurations[config_data['ConfigurationName']].deleteConfiguration()
                Configurations.pop(config_data['ConfigurationName'])
                return StandardResponse(
                    status=False,
                    message=f"Failed to restore iptables scripts: {str(e)}"
                )
    else:
        # Handle new configuration creation
        try:
            config_name = config_data['ConfigurationName']
            
            script_types = {
                'PreUp': 'preup',
                'PostUp': 'postup',
                'PreDown': 'predown',
                'PostDown': 'postdown'
            }
            
            config_script_dir = os.path.join(iptables_dir, config_name)
            os.makedirs(config_script_dir, exist_ok=True)
            
            script_paths = {}
            for script_type, script_name in script_types.items():
                if script_type in config_data and config_data.get(script_type):
                    script_path = os.path.join(config_script_dir, f"{script_name}.sh")
                    with open(script_path, 'w') as f:
                        f.write("#!/bin/bash\n\n")
                        f.write(f"# IPTables {script_type} Rules for {config_name}\n")
                        f.write(config_data.get(script_type, ''))
                    os.chmod(script_path, 0o755)
                    script_paths[script_type] = script_path
            
            for script_type, path in script_paths.items():
                config_data[script_type] = path
            
            Configurations[config_name] = Configuration(data=config_data)
            
        except Exception as e:
            for script_path in script_paths.values():
                if os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                    except:
                        pass
            return StandardResponse(
                status=False,
                message=f"Failed to create configuration: {str(e)}"
            )
    
    # Handle AmneziaWG symlink
    if config_data.get("Protocol") == "awg":
        try:
            conf_file_path = os.path.join(wgd_config_path, f'{config_data["ConfigurationName"]}.conf')
            symlink_path = os.path.join("/etc/amnezia/amneziawg", f'{config_data["ConfigurationName"]}.conf')
            
            if not os.path.islink(symlink_path):
                os.symlink(conf_file_path, symlink_path)
                logger.debug(f"Created symbolic link: {symlink_path} -> {conf_file_path}")
        except Exception as e:
            logger.warning(f"Failed to create AmneziaWG symlink: {str(e)}")
    
    return StandardResponse(status=True)


@router.get('/toggleConfiguration/', response_model=StandardResponse)
async def toggle_configuration(
    configurationName: str = Query(..., description="Configuration name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Toggle configuration on/off"""
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    toggleStatus, msg = Configurations[configurationName].toggleConfiguration()
    return StandardResponse(
        status=toggleStatus,
        message=msg,
        data=Configurations[configurationName].Status
    )


@router.post('/updateConfiguration', response_model=StandardResponse)
async def update_configuration(
    update_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update configuration settings"""
    if "Name" not in update_data:
        return StandardResponse(
            status=False,
            message="Please provide Name field"
        )
    
    name = update_data.get("Name")
    if name not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    status, msg = Configurations[name].updateConfigurationSettings(update_data)
    
    return StandardResponse(
        status=status,
        message=msg,
        data=Configurations[name].toJson()
    )


@router.get('/getConfigurationRawFile', response_model=StandardResponse)
async def get_configuration_raw_file(
    configurationName: str = Query(..., description="Configuration name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get raw configuration file content"""
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    return StandardResponse(
        status=True,
        data={
            "path": Configurations[configurationName].configPath,
            "content": Configurations[configurationName].getRawConfigurationFile()
        }
    )


@router.post('/updateConfigurationRawFile', response_model=StandardResponse)
async def update_configuration_raw_file(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update raw configuration file"""
    configurationName = update_data.get('configurationName')
    rawConfiguration = update_data.get('rawConfiguration')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    if not rawConfiguration:
        return StandardResponse(
            status=False,
            message="Please provide content"
        )
    
    status, err = Configurations[configurationName].updateRawConfigurationFile(rawConfiguration)
    
    return StandardResponse(status=status, message=err)


@router.post('/deleteConfiguration', response_model=StandardResponse)
async def delete_configuration(
    delete_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Delete a WireGuard configuration"""
    if "Name" not in delete_data or delete_data.get("Name") not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide the configuration name you want to delete"
        )
    
    config_name = delete_data.get("Name")
    
    # Delete iptables script files
    script_types = ['preup', 'postup', 'predown', 'postdown']
    iptables_dir = DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
    
    config_script_dir = os.path.join(iptables_dir, config_name)
    if os.path.exists(config_script_dir):
        for script_type in script_types:
            script_path = os.path.join(config_script_dir, f"{script_type}.sh")
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
                    logger.debug(f"Deleted iptables script: {script_path}")
            except Exception as e:
                logger.warning(f"Failed to delete iptables script {script_path}: {str(e)}")
        
        try:
            if not os.listdir(config_script_dir):
                os.rmdir(config_script_dir)
                logger.debug(f"Removed empty config directory: {config_script_dir}")
        except Exception as e:
            logger.warning(f"Failed to remove config directory {config_script_dir}: {str(e)}")
    else:
        # Fallback to old format
        for script_type in script_types:
            script_path = os.path.join(iptables_dir, f"{config_name}-{script_type}.sh")
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except Exception as e:
                logger.warning(f"Failed to delete iptables script {script_path}: {str(e)}")
    
    # Delete the configuration
    status = Configurations[config_name].deleteConfiguration()
    
    if status:
        Configurations.pop(config_name)
    
    return StandardResponse(status=status)


@router.post('/renameConfiguration', response_model=StandardResponse)
async def rename_configuration(
    rename_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Rename a WireGuard configuration"""
    keys = ["Name", "NewConfigurationName"]
    for k in keys:
        if (k not in rename_data or not rename_data.get(k) or
            (k == "Name" and rename_data.get(k) not in Configurations.keys())):
            return StandardResponse(
                status=False,
                message="Please provide the configuration name you want to rename"
            )
    
    status, message = Configurations[rename_data.get("Name")].renameConfiguration(
        rename_data.get("NewConfigurationName")
    )
    if status:
        Configurations.pop(rename_data.get("Name"))
        Configurations[rename_data.get("NewConfigurationName")] = Configuration(
            rename_data.get("NewConfigurationName")
        )
    
    return StandardResponse(status=status, message=message)


@router.get('/getWireguardConfigurationInfo', response_model=StandardResponse)
async def get_wireguard_configuration_info(
    configurationName: str = Query(..., description="Configuration name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get detailed information about a WireGuard configuration"""
    logger.debug(f"getWireguardConfigurationInfo called for: {configurationName}")
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide configuration name"
        )
    
    # Refresh peer jobs
    from ..modules.Jobs import AllPeerJobs
    logger.debug(f"Refreshing AllPeerJobs data...")
    AllPeerJobs._PeerJobs__getJobs()
    logger.debug(f"AllPeerJobs now has {len(AllPeerJobs.Jobs)} total jobs")
    
    # Get configuration and peers
    config = Configurations[configurationName]
    peers = config.getPeersList()
    restricted_peers = config.getRestrictedPeersList()
    
    logger.debug(f"Found {len(peers)} peers for configuration {configurationName}")
    
    # Convert peers to JSON
    peers_json = []
    for i, peer in enumerate(peers):
        logger.debug(f"Processing peer {i+1}: {peer.id}")
        peer_json = peer.toJson()
        logger.debug(f"Peer {peer.id} jobs: {len(peer_json.get('jobs', []))}")
        peers_json.append(peer_json)
    
    restricted_peers_json = [peer.toJson() for peer in restricted_peers]
    
    logger.debug(f"Returning {len(peers_json)} peers with jobs data")
    
    return StandardResponse(
        status=True,
        data={
            "configurationInfo": config.toJson(),
            "configurationPeers": peers_json,
            "configurationRestrictedPeers": restricted_peers_json
        }
    )


# ============================================================================
# Peer Management Endpoints
# ============================================================================

@router.post('/addPeers/{configName}', response_model=StandardResponse)
async def add_peers(
    configName: str,
    peer_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Add peers to a configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    try:
        bulkAdd: bool = peer_data.get("bulkAdd", False)
        bulkAddAmount: int = peer_data.get('bulkAddAmount', 0)
        preshared_key_bulkAdd: bool = peer_data.get('preshared_key_bulkAdd', False)
        
        public_key: str = peer_data.get('public_key', "")
        allowed_ips: list = peer_data.get('allowed_ips', "")
        
        endpoint_allowed_ip: str = peer_data.get(
            'endpoint_allowed_ip',
            DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1]
        )
        dns_addresses: str = peer_data.get(
            'DNS',
            DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1]
        )
        mtu: int = peer_data.get('mtu', int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1]))
        keep_alive: int = peer_data.get('keepalive', int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1]))
        preshared_key: str = peer_data.get('preshared_key', "")
        
        if type(mtu) is not int or mtu < 0 or mtu > 1460:
            mtu = int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1])
        if type(keep_alive) is not int or keep_alive < 0:
            keep_alive = int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1])
        if len(dns_addresses) == 0:
            dns_addresses = DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1]
        if len(endpoint_allowed_ip) == 0:
            endpoint_allowed_ip = DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1]
        
        config = Configurations.get(configName)
        if not bulkAdd and (len(public_key) == 0 or len(allowed_ips) == 0):
            return StandardResponse(
                status=False,
                message="Please provide at least public_key and allowed_ips"
            )
        
        if not config.getStatus():
            config.toggleConfiguration()
        
        availableIps = config.getAvailableIP()
        
        if bulkAdd:
            if type(preshared_key_bulkAdd) is not bool:
                preshared_key_bulkAdd = False
            
            if type(bulkAddAmount) is not int or bulkAddAmount < 1:
                return StandardResponse(
                    status=False,
                    message="Please specify amount of peers you want to add"
                )
            if not availableIps[0]:
                return StandardResponse(
                    status=False,
                    message="No more available IP can assign"
                )
            if bulkAddAmount > len(availableIps[1]):
                return StandardResponse(
                    status=False,
                    message=f"The maximum number of peers can add is {len(availableIps[1])}"
                )
            
            keyPairs = []
            for i in range(bulkAddAmount):
                newPrivateKey = GenerateWireguardPrivateKey()[1]
                keyPairs.append({
                    "private_key": newPrivateKey,
                    "id": GenerateWireguardPublicKey(newPrivateKey)[1],
                    "preshared_key": (GenerateWireguardPrivateKey()[1] if preshared_key_bulkAdd else ""),
                    "allowed_ip": availableIps[1][i],
                    "name": f"BulkPeer #{(i + 1)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "DNS": dns_addresses,
                    "endpoint_allowed_ip": endpoint_allowed_ip,
                    "mtu": mtu,
                    "keepalive": keep_alive
                })
            
            if len(keyPairs) == 0:
                return StandardResponse(
                    status=False,
                    message="Generating key pairs by bulk failed"
                )
            
            logger.debug(f"API: Calling addPeers with {len(keyPairs)} bulk peers")
            result = config.addPeers(keyPairs)
            logger.debug(f"API: addPeers result: {result}")
            return StandardResponse(status=True)
        else:
            if config.searchPeer(public_key)[0] is True:
                return StandardResponse(
                    status=False,
                    message=f"This peer already exist"
                )
            
            name = peer_data.get("name", "")
            private_key = peer_data.get("private_key", "")
            
            # Validate peer name uniqueness
            if name:
                existing_peers = config.getPeersList()
                for existing_peer in existing_peers:
                    if existing_peer.name == name:
                        return StandardResponse(
                            status=False,
                            message=f"A peer with the name '{name}' already exists in this configuration"
                        )
            
            for i in allowed_ips:
                if i not in availableIps[1]:
                    return StandardResponse(
                        status=False,
                        message=f"This IP is not available: {i}"
                    )
            
            logger.debug(f"API: Calling addPeers with single peer: {public_key[:8]}...")
            status = config.addPeers([{
                "name": name,
                "id": public_key,
                "private_key": private_key,
                "allowed_ip": ','.join(allowed_ips),
                "preshared_key": preshared_key,
                "endpoint_allowed_ip": endpoint_allowed_ip,
                "DNS": dns_addresses,
                "mtu": mtu,
                "keepalive": keep_alive
            }])
            return StandardResponse(status=status)
    except Exception as e:
        logger.error(f"Add peers failed: {e}")
        return StandardResponse(
            status=False,
            message="Add peers failed. Please see data for specific issue"
        )


@router.post('/updatePeerSettings/{configName}', response_model=StandardResponse)
async def update_peer_settings(
    configName: str,
    peer_update: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update peer settings"""
    peer_id = peer_update.get('id')
    
    if not peer_id or configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration/Peer does not exist"
        )
    
    wireguardConfig = Configurations[configName]
    foundPeer, peer = wireguardConfig.searchPeer(peer_id)
    
    if foundPeer:
        result = peer.updatePeer(
            peer_update.get('name'),
            peer_update.get('private_key'),
            peer_update.get('preshared_key'),
            peer_update.get('DNS'),
            peer_update.get('allowed_ip'),
            peer_update.get('endpoint_allowed_ip'),
            peer_update.get('mtu'),
            peer_update.get('keepalive')
        )
        result_dict = convert_response_object_to_dict(result)
        return StandardResponse(**result_dict)
    
    return StandardResponse(status=False, message="Peer does not exist")


@router.post('/resetPeerData/{configName}', response_model=StandardResponse)
async def reset_peer_data(
    configName: str,
    reset_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Reset peer data usage"""
    peer_id = reset_data.get('id')
    reset_type = reset_data.get('type')
    
    if not peer_id or configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration/Peer does not exist"
        )
    
    wgc = Configurations.get(configName)
    foundPeer, peer = wgc.searchPeer(peer_id)
    
    if not foundPeer:
        return StandardResponse(
            status=False,
            message="Configuration/Peer does not exist"
        )
    
    return StandardResponse(status=peer.resetDataUsage(reset_type))


@router.post('/deletePeers/{configName}', response_model=StandardResponse)
async def delete_peers(
    configName: str,
    delete_data: PeerBulkAction,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Delete multiple peers from a configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    if len(delete_data.peers) == 0:
        return StandardResponse(
            status=False,
            message="Please specify one or more peers"
        )
    
    configuration = Configurations.get(configName)
    result = configuration.deletePeers(delete_data.peers)
    result_dict = convert_response_object_to_dict(result)
    return StandardResponse(**result_dict)


@router.post('/restrictPeers/{configName}', response_model=StandardResponse)
async def restrict_peers(
    configName: str,
    restrict_data: PeerBulkAction,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Restrict multiple peers"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    if len(restrict_data.peers) == 0:
        return StandardResponse(
            status=False,
            message="Please specify one or more peers"
        )
    
    configuration = Configurations.get(configName)
    result = configuration.restrictPeers(restrict_data.peers)
    result_dict = convert_response_object_to_dict(result)
    return StandardResponse(**result_dict)


@router.post('/allowAccessPeers/{configName}', response_model=StandardResponse)
async def allow_access_peers(
    configName: str,
    allow_data: PeerBulkAction,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Allow access to restricted peers"""
    try:
        if configName not in Configurations.keys():
            return StandardResponse(
                status=False,
                message="Configuration does not exist"
            )
        
        if len(allow_data.peers) == 0:
            return StandardResponse(
                status=False,
                message="Please specify one or more peers"
            )
        
        configuration = Configurations.get(configName)
        result = configuration.allowAccessPeers(allow_data.peers)
        result_dict = convert_response_object_to_dict(result)
        return StandardResponse(**result_dict)
        
    except Exception as e:
        logger.error(f"allowAccessPeers: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Internal server error: {str(e)}"
        )


@router.get("/downloadPeer/{configName}", response_model=StandardResponse)
async def download_peer(
    configName: str,
    id: str = Query(..., description="Peer ID"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Download peer configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    configuration = Configurations[configName]
    peerFound, peer = configuration.searchPeer(id)
    
    if not id or not peerFound:
        return StandardResponse(
            status=False,
            message="Peer does not exist"
        )
    
    return StandardResponse(
        status=True,
        data=peer.downloadPeer()
    )


@router.get("/downloadAllPeers/{configName}", response_model=StandardResponse)
async def download_all_peers(
    configName: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Download all peers configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    configuration = Configurations[configName]
    peerData = []
    untitledPeer = 0
    
    for i in configuration.Peers:
        file = i.downloadPeer()
        if file["fileName"] == "UntitledPeer_" + configName:
            file["fileName"] = str(untitledPeer) + "_" + file["fileName"]
            untitledPeer += 1
        peerData.append(file)
    
    return StandardResponse(status=True, data=peerData)


@router.get("/getAvailableIPs/{configName}", response_model=StandardResponse)
async def get_available_ips(
    configName: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get available IPs for a configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    status, ips = Configurations.get(configName).getAvailableIP()
    return StandardResponse(status=status, data=ips)


# ============================================================================
# Share Link Management
# ============================================================================

@router.post('/sharePeer/create', response_model=StandardResponse)
async def share_peer_create(
    share_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Create a peer share link"""
    Configuration = share_data.get('Configuration')
    Peer = share_data.get('Peer')
    ExpireDate = share_data.get('ExpireDate')
    
    if Configuration is None or Peer is None:
        return StandardResponse(
            status=False,
            message="Please specify configuration and peers"
        )
    
    activeLink = AllPeerShareLinks.getLink(Configuration, Peer)
    if len(activeLink) > 0:
        return StandardResponse(
            status=True,
            message="This peer is already sharing. Please view data for shared link.",
            data=activeLink[0].toJson()
        )
    
    status, message = AllPeerShareLinks.addLink(Configuration, Peer, ExpireDate)
    if not status:
        return StandardResponse(status=status, message=message)
    
    links = AllPeerShareLinks.getLinkByID(message)
    return StandardResponse(status=True, data=[link.toJson() for link in links])


@router.post('/sharePeer/update', response_model=StandardResponse)
async def share_peer_update(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update a peer share link"""
    ShareID: str = update_data.get("ShareID")
    ExpireDate: str = update_data.get("ExpireDate")
    
    if ShareID is None:
        return StandardResponse(
            status=False,
            message="Please specify ShareID"
        )
    
    if len(AllPeerShareLinks.getLinkByID(ShareID)) == 0:
        return StandardResponse(
            status=False,
            message="ShareID does not exist"
        )
    
    status, message = AllPeerShareLinks.updateLinkExpireDate(ShareID, ExpireDate)
    if not status:
        return StandardResponse(status=status, message=message)
    
    links = AllPeerShareLinks.getLinkByID(ShareID)
    return StandardResponse(status=True, data=[link.toJson() for link in links])


@router.get('/sharePeer/get', response_model=StandardResponse)
async def share_peer_get(
    ShareID: str = Query(..., description="Share ID")
):
    """Get shared peer configuration (public endpoint)"""
    if not ShareID:
        return StandardResponse(
            status=False,
            message="Please provide ShareID"
        )
    
    link = AllPeerShareLinks.getLinkByID(ShareID)
    if len(link) == 0:
        return StandardResponse(
            status=False,
            message="This link is either expired or invalid"
        )
    
    l = link[0]
    if l.Configuration not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="The peer you're looking for does not exist"
        )
    
    c = Configurations.get(l.Configuration)
    fp, p = c.searchPeer(l.Peer)
    
    if not fp:
        return StandardResponse(
            status=False,
            message="The peer you're looking for does not exist"
        )
    
    return StandardResponse(status=True, data=p.downloadPeer())


# ============================================================================
# Dashboard Configuration
# ============================================================================

@router.get('/getDashboardConfiguration', response_model=StandardResponse)
async def get_dashboard_configuration(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get dashboard configuration"""
    return StandardResponse(status=True, data=DashboardConfig.toJson())


@router.post('/updateDashboardConfigurationItem', response_model=StandardResponse)
async def update_dashboard_configuration_item(
    update_data: DashboardConfigUpdate,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update a dashboard configuration item"""
    valid, msg = DashboardConfig.SetConfig(
        update_data.section,
        update_data.key,
        update_data.value
    )
    
    if not valid:
        return StandardResponse(status=False, message=msg)
    
    if update_data.section == "Server":
        if update_data.key == 'wg_conf_path':
            Configurations.clear()
            InitWireguardConfigurationsList()
    
    return StandardResponse(
        status=True,
        data=DashboardConfig.GetConfig(update_data.section, update_data.key)[1]
    )


@router.get('/getDashboardAPIKeys', response_model=StandardResponse)
async def get_dashboard_api_keys(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get dashboard API keys"""
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key')[1]:
        return StandardResponse(
            status=True,
            data=[key.toJson() for key in DashboardConfig.DashboardAPIKeys]
        )
    return StandardResponse(
        status=False,
        message="WGDashboard API Keys function is disabled"
    )


@router.post('/newDashboardAPIKey', response_model=StandardResponse)
async def new_dashboard_api_key(
    key_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Create a new dashboard API key"""
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key')[1]:
        try:
            if key_data.get('neverExpire'):
                expiredAt = None
            else:
                expiredAt = datetime.strptime(key_data['ExpiredAt'], '%Y-%m-%d %H:%M:%S')
            
            DashboardConfig.createAPIKeys(expiredAt)
            return StandardResponse(
                status=True,
                data=[key.toJson() for key in DashboardConfig.DashboardAPIKeys]
            )
        except Exception as e:
            return StandardResponse(status=False, message=str(e))
    
    return StandardResponse(
        status=False,
        message="Dashboard API Keys function is disabled"
    )


@router.post('/deleteDashboardAPIKey', response_model=StandardResponse)
async def delete_dashboard_api_key(
    key_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Delete a dashboard API key"""
    if DashboardConfig.GetConfig('Server', 'dashboard_api_key')[1]:
        key = key_data.get('Key')
        if key and any(x.Key == key for x in DashboardConfig.DashboardAPIKeys):
            DashboardConfig.deleteAPIKey(key)
            return StandardResponse(
                status=True,
                data=[key.toJson() for key in DashboardConfig.DashboardAPIKeys]
            )
    
    return StandardResponse(
        status=False,
        message="Dashboard API Keys function is disabled"
    )


@router.get('/getDashboardTheme', response_model=StandardResponse)
async def get_dashboard_theme():
    """Get dashboard theme (public endpoint)"""
    theme = DashboardConfig.GetConfig("Server", "dashboard_theme")[1]
    return StandardResponse(status=True, data=theme)


@router.get('/getDashboardVersion', response_model=StandardResponse)
async def get_dashboard_version():
    """Get dashboard version (public endpoint)"""
    version = DashboardConfig.GetConfig("Server", "version")[1]
    return StandardResponse(status=True, data=version)


# ============================================================================
# IPTables Script Management
# ============================================================================

@router.post('/getConfigTablesPreUp', response_model=StandardResponse)
async def get_config_tables_preup(
    script_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get PreUp iptables script"""
    configurationName = script_data.get('configurationName')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    script_paths = Configurations[configurationName].getPreUp()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PreUp scripts found"
        )
    
    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"
    
    return StandardResponse(
        status=True,
        data={
            "paths": script_paths,
            "contents": script_contents,
            "raw_preup": Configurations[configurationName].PreUp
        }
    )


@router.post('/getConfigTablesPostUp', response_model=StandardResponse)
async def get_config_tables_postup(
    script_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get PostUp iptables script"""
    configurationName = script_data.get('configurationName')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    script_paths = Configurations[configurationName].getPostUp()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PostUp scripts found"
        )
    
    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"
    
    return StandardResponse(
        status=True,
        data={
            "paths": script_paths,
            "contents": script_contents,
            "raw_postup": Configurations[configurationName].PostUp
        }
    )


@router.post('/getConfigTablesPostDown', response_model=StandardResponse)
async def get_config_tables_postdown(
    script_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get PostDown iptables script"""
    configurationName = script_data.get('configurationName')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    script_paths = Configurations[configurationName].getPostDown()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PostDown scripts found"
        )
    
    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"
    
    return StandardResponse(
        status=True,
        data={
            "paths": script_paths,
            "contents": script_contents,
            "raw_postdown": Configurations[configurationName].PostDown
        }
    )


@router.post('/getConfigTablesPreDown', response_model=StandardResponse)
async def get_config_tables_predown(
    script_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get PreDown iptables script"""
    configurationName = script_data.get('configurationName')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    script_paths = Configurations[configurationName].getPreDown()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PreDown scripts found"
        )
    
    script_contents = {}
    for path in script_paths:
        try:
            with open(path, 'r') as f:
                script_contents[path] = f.read()
        except (IOError, OSError) as e:
            script_contents[path] = f"Error reading file: {str(e)}"
    
    return StandardResponse(
        status=True,
        data={
            "paths": script_paths,
            "contents": script_contents,
            "raw_predown": Configurations[configurationName].PreDown
        }
    )


@router.post('/updateConfigTablesPreUp', response_model=StandardResponse)
async def update_config_tables_preup(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update PreUp iptables script"""
    configurationName = update_data.get('configurationName')
    script_content = update_data.get('content')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    if script_content is None:
        return StandardResponse(
            status=False,
            message="Please provide script content"
        )
    
    config = Configurations[configurationName]
    script_paths = config.getPreUp()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PreUp script path found"
        )
    
    try:
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            os.chmod(path, 0o755)
        
        return StandardResponse(
            status=True,
            message="PreUp script updated successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update script: {str(e)}"
        )


@router.post('/updateConfigTablesPostUp', response_model=StandardResponse)
async def update_config_tables_postup(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update PostUp iptables script"""
    configurationName = update_data.get('configurationName')
    script_content = update_data.get('content')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    if script_content is None:
        return StandardResponse(
            status=False,
            message="Please provide script content"
        )
    
    config = Configurations[configurationName]
    script_paths = config.getPostUp()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PostUp script path found"
        )
    
    try:
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            os.chmod(path, 0o755)
        
        return StandardResponse(
            status=True,
            message="PostUp script updated successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update script: {str(e)}"
        )


@router.post('/updateConfigTablesPreDown', response_model=StandardResponse)
async def update_config_tables_predown(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update PreDown iptables script"""
    configurationName = update_data.get('configurationName')
    script_content = update_data.get('content')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    if script_content is None:
        return StandardResponse(
            status=False,
            message="Please provide script content"
        )
    
    config = Configurations[configurationName]
    script_paths = config.getPreDown()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PreDown script path found"
        )
    
    try:
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            os.chmod(path, 0o755)
        
        return StandardResponse(
            status=True,
            message="PreDown script updated successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update script: {str(e)}"
        )


@router.post('/updateConfigTablesPostDown', response_model=StandardResponse)
async def update_config_tables_postdown(
    update_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update PostDown iptables script"""
    configurationName = update_data.get('configurationName')
    script_content = update_data.get('content')
    
    if not configurationName or configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Please provide a valid configuration name"
        )
    
    if script_content is None:
        return StandardResponse(
            status=False,
            message="Please provide script content"
        )
    
    config = Configurations[configurationName]
    script_paths = config.getPostDown()
    
    if not script_paths:
        return StandardResponse(
            status=False,
            message="No PostDown script path found"
        )
    
    try:
        for path in script_paths:
            with open(path, 'w') as f:
                f.write(script_content)
            os.chmod(path, 0o755)
        
        return StandardResponse(
            status=True,
            message="PostDown script updated successfully"
        )
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Failed to update script: {str(e)}"
        )


# ============================================================================
# System Status
# ============================================================================

@router.get('/systemStatus', response_model=StandardResponse)
async def get_system_status(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get system status (CPU, memory, disk, network, processes)"""
    try:
        # CPU Information
        try:
            cpu_percpu = psutil.cpu_percent(interval=0.5, percpu=True)
            cpu = psutil.cpu_percent(interval=0.5)
        except Exception as e:
            cpu_percpu = []
            cpu = None
            logger.warning(f"Could not retrieve CPU information: {e}")
        
        # Memory Information
        try:
            memory = psutil.virtual_memory()
            try:
                swap_memory = psutil.swap_memory()
            except AttributeError:
                swap_memory = None
        except Exception as e:
            memory = None
            swap_memory = None
            logger.warning(f"Could not retrieve memory information: {e}")
        
        # Disk Information
        try:
            disks = psutil.disk_partitions(all=False)
            disk_status = {}
            for d in disks:
                if d.fstype in ('squashfs', 'devfs', 'fdescfs', 'devtmpfs'):
                    continue
                try:
                    detail = psutil.disk_usage(d.mountpoint)
                    disk_status[d.mountpoint] = {
                        "total": detail.total,
                        "used": detail.used,
                        "free": detail.free,
                        "percent": detail.percent
                    }
                except (OSError, PermissionError) as disk_e:
                    logger.warning(f"Could not retrieve disk information for {d.mountpoint}: {disk_e}")
        except Exception as e:
            disk_status = {}
            logger.warning(f"Could not retrieve disk partitions: {e}")
        
        # Network Information
        try:
            is_awg_kernel_loaded = False
            try:
                result = subprocess.run(['lsmod'], stdout=subprocess.PIPE, text=True)
                is_awg_kernel_loaded = 'amneziawg' in result.stdout
            except Exception:
                try:
                    with open('/proc/modules', 'r') as f:
                        is_awg_kernel_loaded = 'amneziawg' in f.read()
                except Exception:
                    pass
            
            network = psutil.net_io_counters(pernic=True, nowrap=True)
            network_status = {}
            
            for interface, stats in network.items():
                if interface in ('lo', 'lo0'):
                    continue
                network_status[interface] = {
                    "byte_sent": stats.bytes_sent,
                    "byte_recv": stats.bytes_recv
                }
            
            # Handle amneziawg interfaces
            if is_awg_kernel_loaded:
                for name, config in Configurations.items():
                    if config.get_iface_proto() == "awg" and config.getStatus():
                        if name in network_status:
                            logger.info(f"Enhancing network stats for amneziawg interface: {name}")
                            try:
                                result = execute_awg_command('show', name, subcommand='transfer')
                                if result['success']:
                                    data_usage = result['stdout'].split("\n")
                                    total_recv = 0
                                    total_sent = 0
                                    
                                    for line in data_usage:
                                        if line.strip():
                                            parts = line.split('\t')
                                            if len(parts) >= 3:
                                                total_recv += int(parts[1])
                                                total_sent += int(parts[2])
                                    
                                    network_status[name]["byte_sent"] = max(
                                        network_status[name]["byte_sent"], total_sent
                                    )
                                    network_status[name]["byte_recv"] = max(
                                        network_status[name]["byte_recv"], total_recv
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to get enhanced stats for {name}: {e}")
        except Exception as e:
            network_status = {}
            logger.warning(f"Could not retrieve network information: {e}")
        
        # Process Information
        try:
            processes = []
            for proc in psutil.process_iter():
                try:
                    with proc.oneshot():
                        name = proc.name()
                        try:
                            cmdline = ' '.join(proc.cmdline())
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            cmdline = name
                        
                        cpu_percent = proc.cpu_percent(interval=None)
                        mem_percent = proc.memory_percent()
                        
                        processes.append({
                            "name": name,
                            "command": cmdline,
                            "pid": proc.pid,
                            "cpu_percent": cpu_percent,
                            "memory_percent": mem_percent
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as proc_e:
                    logger.warning(f"Error getting process info: {proc_e}")
                    continue
            
            cpu_top_10 = sorted(
                [p for p in processes if p['cpu_percent'] is not None],
                key=lambda x: x['cpu_percent'],
                reverse=True
            )[:10]
            
            memory_top_10 = sorted(
                [p for p in processes if p['memory_percent'] is not None],
                key=lambda x: x['memory_percent'],
                reverse=True
            )[:10]
        except Exception as e:
            cpu_top_10 = []
            memory_top_10 = []
            logger.warning(f"Could not retrieve process information: {e}")
        
        # Construct status dictionary
        status_data = {
            "cpu": {
                "cpu_percent": cpu,
                "cpu_percent_per_cpu": cpu_percpu,
            },
            "memory": {
                "virtual_memory": {
                    "total": getattr(memory, 'total', None),
                    "available": getattr(memory, 'available', None),
                    "percent": getattr(memory, 'percent', None)
                },
                "swap_memory": {
                    "total": getattr(swap_memory, 'total', None) if swap_memory else None,
                    "used": getattr(swap_memory, 'used', None) if swap_memory else None,
                    "percent": getattr(swap_memory, 'percent', None) if swap_memory else None
                } if swap_memory else None
            },
            "disk": disk_status,
            "network": network_status,
            "process": {
                "cpu_top_10": cpu_top_10,
                "memory_top_10": memory_top_10
            }
        }
        
        return StandardResponse(status=True, data=status_data)
        
    except Exception as global_e:
        logger.error(f"Unexpected error in system status API: {global_e}")
        return StandardResponse(
            status=False,
            message=f"Failed to retrieve system status: {str(global_e)}"
        )


# ============================================================================
# Server-Sent Events (SSE) for Config Status Stream
# ============================================================================

@router.get('/config-status-stream')
async def stream_config_status(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Stream configuration status updates via Server-Sent Events"""
    async def event_generator():
        while True:
            # Get all configuration statuses
            configs = {name: config.getStatus() for name, config in Configurations.items()}
            yield f"data: {json.dumps(configs)}\n\n"
            await asyncio.sleep(0.1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ============================================================================
# Thread Pool API Endpoints
# ============================================================================

@router.get('/threadPool/status', response_model=StandardResponse)
async def thread_pool_status(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get thread pool status and statistics"""
    try:
        status = {
            'active': thread_pool.executor is not None,
            'max_workers': thread_pool.max_workers,
            'thread_count': len(thread_pool.executor._threads) if thread_pool.executor else 0
        }
        return StandardResponse(status=True, data=status)
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/threadPool/bulkPeerStatus', response_model=StandardResponse)
async def bulk_peer_status(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Check status of multiple peers in parallel using thread pool"""
    try:
        peer_ids = bulk_data.get('peer_ids', [])
        config_name = bulk_data.get('config_name')
        
        if not peer_ids:
            return StandardResponse(status=False, message="No peer IDs provided")
        
        results = bulk_peer_status_check(peer_ids, config_name)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_checked': len(results),
                'successful': len([r for r in results if r.get('status') == 'connected'])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/threadPool/bulkRedisOps', response_model=StandardResponse)
async def bulk_redis_ops(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Execute multiple Redis operations in parallel using thread pool"""
    try:
        operations = bulk_data.get('operations', [])
        
        if not operations:
            return StandardResponse(status=False, message="No operations provided")
        
        results = redis_bulk_operations(operations)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_operations': len(results),
                'successful': len([r for r in results if r is not None and 'error' not in str(r)])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/threadPool/bulkFileOps', response_model=StandardResponse)
async def bulk_file_ops(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Execute multiple file operations in parallel using thread pool"""
    try:
        operations = bulk_data.get('operations', [])
        
        if not operations:
            return StandardResponse(status=False, message="No operations provided")
        
        results = file_operations(operations)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_operations': len(results),
                'successful': len([r for r in results if r is not None and 'error' not in str(r)])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/threadPool/bulkWgCommands', response_model=StandardResponse)
async def bulk_wg_commands(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Execute multiple WireGuard commands in parallel using thread pool"""
    try:
        commands = bulk_data.get('commands', [])
        
        if not commands:
            return StandardResponse(status=False, message="No commands provided")
        
        results = wg_command_operations(commands)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_commands': len(results),
                'successful': len([r for r in results if r.get('success', False)])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


# ============================================================================
# Process Pool API Endpoints
# ============================================================================

@router.get('/processPool/status', response_model=StandardResponse)
async def process_pool_status(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get process pool status and statistics"""
    try:
        status = {
            'active': process_pool.pool is not None,
            'max_workers': process_pool.max_workers,
            'process_count': len(process_pool.pool._pool) if process_pool.pool else 0
        }
        return StandardResponse(status=True, data=status)
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/bulkPeerProcessing', response_model=StandardResponse)
async def bulk_peer_processing_api(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Process multiple peers in parallel using process pool"""
    try:
        peers_data = bulk_data.get('peers_data', [])
        
        if not peers_data:
            return StandardResponse(status=False, message="No peer data provided")
        
        results = bulk_peer_processing(peers_data)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_processed': len(results),
                'successful': len([r for r in results if r is not None])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/bulkPeerValidation', response_model=StandardResponse)
async def bulk_peer_validation_api(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Validate multiple peers in parallel using process pool"""
    try:
        peers_data = bulk_data.get('peers_data', [])
        
        if not peers_data:
            return StandardResponse(status=False, message="No peer data provided")
        
        results = bulk_peer_validation(peers_data)
        valid_count = len([r for r in results if r.get('valid', False)])
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_validated': len(results),
                'valid_count': valid_count,
                'invalid_count': len(results) - valid_count
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/bulkPeerEncryption', response_model=StandardResponse)
async def bulk_peer_encryption_api(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Encrypt multiple peers in parallel using process pool"""
    try:
        peers_data = bulk_data.get('peers_data', [])
        
        if not peers_data:
            return StandardResponse(status=False, message="No peer data provided")
        
        results = bulk_peer_encryption(peers_data)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_encrypted': len(results),
                'successful': len([r for r in results if r is not None])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/bulkUsageAnalysis', response_model=StandardResponse)
async def bulk_usage_analysis_api(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Analyze usage patterns for multiple peers in parallel using process pool"""
    try:
        usage_data_list = bulk_data.get('usage_data_list', [])
        
        if not usage_data_list:
            return StandardResponse(status=False, message="No usage data provided")
        
        results = bulk_usage_analysis(usage_data_list)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_analyzed': len(results),
                'successful': len([r for r in results if r is not None])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/bulkQrGeneration', response_model=StandardResponse)
async def bulk_qr_generation_api(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Generate QR codes for multiple peers in parallel using process pool"""
    try:
        peer_data_list = bulk_data.get('peer_data_list', [])
        
        if not peer_data_list:
            return StandardResponse(status=False, message="No peer data provided")
        
        results = bulk_qr_generation(peer_data_list)
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'total_generated': len(results),
                'successful': len([r for r in results if r is not None])
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))


@router.post('/processPool/performanceTest', response_model=StandardResponse)
async def process_pool_performance_test(
    bulk_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Test process pool performance with CPU-intensive tasks"""
    try:
        task_count = bulk_data.get('task_count', 10)
        
        # Generate test data
        test_peers = []
        for i in range(task_count):
            test_peers.append({
                'id': f'test_peer_{i}',
                'name': f'Test Peer {i}',
                'public_key': 'A' * 44 + '=',
                'allowed_ips': f'10.0.0.{i}/32',
                'endpoint': f'example.com:{51820 + i}'
            })
        
        start_time = time.time()
        results = bulk_peer_processing(test_peers)
        end_time = time.time()
        duration = end_time - start_time
        
        return StandardResponse(
            status=True,
            data={
                'results': results,
                'task_count': task_count,
                'duration': duration,
                'tasks_per_second': task_count / duration if duration > 0 else 0,
                'avg_time_per_task': duration / task_count if task_count > 0 else 0
            }
        )
    except Exception as e:
        return StandardResponse(status=False, message=str(e))

