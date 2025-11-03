"""
FastAPI Snapshot Router
Migrated from snapshot_api.py Flask blueprint
Handles configuration backups and restoration
"""
import os
import re
import shutil
import json
import logging
import aiofiles
from fastapi import APIRouter, Query, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
from io import BytesIO

from ..models.responses import StandardResponse
from ..modules.Core import Configurations, Configuration
from ..modules.DashboardConfig import DashboardConfig
from ..modules.Archive.SnapShot import ArchiveUtils
from ..modules.Utilities import RegexMatch, get_backup_paths
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db
from ..modules.Security import security_manager

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.get('/getConfigurationBackup', response_model=StandardResponse)
async def get_configuration_backup(
    configurationName: str = Query(..., description="Configuration name"),
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Get backups for a specific configuration"""
    if configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    backups = Configurations[configurationName].getBackups()
    return StandardResponse(status=True, data=backups)


@router.get('/getAllConfigurationBackup', response_model=StandardResponse)
async def get_all_configuration_backup(
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Get all configuration backups"""
    data = {
        "ExistingConfigurations": {},
        "NonExistingConfigurations": {}
    }
    
    # Get base backup directory
    backup_dir = os.path.join(
        DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
        'WGDashboard_Backup'
    )
    
    # Handle existing configurations
    existingConfiguration = Configurations.keys()
    for config_name in existingConfiguration:
        backups = Configurations[config_name].getBackups(True)
        if backups:
            data['ExistingConfigurations'][config_name] = backups
    
    # Handle non-existing configurations
    if os.path.exists(backup_dir):
        for dir_name in os.listdir(backup_dir):
            dir_path = os.path.join(backup_dir, dir_name)
            if os.path.isdir(dir_path) and dir_name not in existingConfiguration:
                backups = []
                files = [
                    (f, os.path.getctime(os.path.join(dir_path, f)))
                    for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                files.sort(key=lambda x: x[1], reverse=True)
                
                for f, _ in files:
                    if RegexMatch(r"^(.*)_(.*)\.(conf)$", f):
                        s = re.search(r"^(.*)_(.*)\.(conf)$", f)
                        date = s.group(2)
                        async with aiofiles.open(os.path.join(dir_path, f), 'r') as cf:
                            content = await cf.read()
                        backup_info = {
                            "filename": f,
                            "backupDate": date,
                            "content": content
                        }
                        
                        # Check for associated backup files
                        redis_file = f.replace(".conf", ".redis")
                        if os.path.exists(os.path.join(dir_path, redis_file)):
                            backup_info['database'] = True
                            async with aiofiles.open(os.path.join(dir_path, redis_file), 'r') as rf:
                                backup_info['databaseContent'] = await rf.read()
                        
                        iptables_file = f.replace(".conf", "_iptables.json")
                        if os.path.exists(os.path.join(dir_path, iptables_file)):
                            backup_info['iptables_scripts'] = True
                            async with aiofiles.open(os.path.join(dir_path, iptables_file), 'r') as iptables_f:
                                backup_info['iptablesContent'] = await iptables_f.read()
                        
                        backups.append(backup_info)
                
                if backups:
                    data['NonExistingConfigurations'][dir_name] = backups
    
    return StandardResponse(status=True, data=data)


@router.get('/createConfigurationBackup', response_model=StandardResponse)
async def create_configuration_backup(
    configurationName: str = Query(..., description="Configuration name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Create a backup for a specific configuration"""
    if configurationName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    success, backup_info = Configurations[configurationName].backupConfigurationFile()
    
    if success:
        backups = Configurations[configurationName].getBackups()
        return StandardResponse(status=True, data=backups)
    else:
        return StandardResponse(status=False, message="Failed to create backup")


@router.post('/deleteConfigurationBackup', response_model=StandardResponse)
async def delete_configuration_backup(
    delete_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Delete a configuration backup"""
    try:
        if 'configurationName' not in delete_data or 'backupFileName' not in delete_data:
            return StandardResponse(
                status=False,
                message="Missing required parameters"
            )
        
        config_name = delete_data['configurationName']
        backup_file = delete_data['backupFileName']
        
        # Get backup paths
        backup_timestamp = backup_file.replace(f'{config_name}_', '').replace('.conf', '')
        backup_paths = get_backup_paths(config_name, backup_timestamp)
        
        # Delete backup files if they exist
        files_to_delete = [
            backup_paths['conf_file'],
            backup_paths['redis_file'],
            backup_paths['iptables_file']
        ]
        
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Check if config backup directory is empty and remove it if so
        if os.path.exists(backup_paths['config_dir']):
            if len(os.listdir(backup_paths['config_dir'])) == 0:
                os.rmdir(backup_paths['config_dir'])
        
        return StandardResponse(
            status=True,
            message="Backup deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Failed to delete backup: {str(e)}"
        )


@router.post('/restoreConfigurationBackup', response_model=StandardResponse)
async def restore_configuration_backup(
    restore_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Restore a configuration backup"""
    try:
        configuration_name = restore_data.get("configurationName")
        backup_file_name = restore_data.get("backupFileName")
        
        if not configuration_name or not backup_file_name:
            return StandardResponse(
                status=False,
                message="Configuration name and backup file name are required"
            )
        
        if configuration_name not in Configurations.keys():
            return StandardResponse(
                status=False,
                message="Configuration does not exist"
            )
        
        success = Configurations[configuration_name].restoreBackup(backup_file_name)
        if not success:
            return StandardResponse(
                status=False,
                message="Failed to restore backup"
            )
        
        # Force refresh of peers list
        Configurations[configuration_name].getPeersList()
        
        return StandardResponse(
            status=True,
            message="Backup restored successfully",
            data={
                "configuration": Configurations[configuration_name].toJson(),
                "peers": [peer.toJson() for peer in Configurations[configuration_name].getPeersList()]
            }
        )
        
    except Exception as e:
        return StandardResponse(
            status=False,
            message=f"Error restoring backup: {str(e)}"
        )


@router.get('/downloadConfigurationBackup')
async def download_configuration_backup(
    configurationName: str = Query(..., description="Configuration name"),
    backupFileName: str = Query(..., description="Backup file name"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Download a backup as 7z archive"""
    try:
        logger.debug(f"Download requested for config: {configurationName}, backup: {backupFileName}")
        
        if not configurationName or not backupFileName:
            return StandardResponse(
                status=False,
                message="Configuration name and backup filename are required"
            )
        
        # Get timestamp from backup filename
        timestamp = backupFileName.split('_')[1].split('.')[0]
        backup_paths = get_backup_paths(configurationName, timestamp)
        
        if not os.path.exists(backup_paths['conf_file']):
            return StandardResponse(
                status=False,
                message="Backup file not found"
            )
        
        # Collect all backup files
        files_dict = {}
        
        # Add main configuration file
        async with aiofiles.open(backup_paths['conf_file'], 'rb') as f:
            files_dict[os.path.basename(backup_paths['conf_file'])] = await f.read()
        
        # Add Redis backup if it exists
        if os.path.exists(backup_paths['redis_file']):
            async with aiofiles.open(backup_paths['redis_file'], 'rb') as f:
                files_dict[os.path.basename(backup_paths['redis_file'])] = await f.read()
        
        # Add iptables backup if it exists
        if os.path.exists(backup_paths['iptables_file']):
            async with aiofiles.open(backup_paths['iptables_file'], 'rb') as f:
                files_dict[os.path.basename(backup_paths['iptables_file'])] = await f.read()
            
            # Process the scripts stored in iptables.json
            async with aiofiles.open(backup_paths['iptables_file'], 'r') as f:
                content = await f.read()
                scripts = json.loads(content)
            
            script_types = ['preup', 'postup', 'predown', 'postdown']
            for script_type in script_types:
                script_key = f"{script_type}_script"
                if script_key in scripts and scripts[script_key]:
                    # Determine directory structure
                    if configurationName in ['ADMINS', 'MEMBERS', 'GUESTS', 'LANP2P']:
                        if configurationName == 'ADMINS':
                            script_dir = 'iptable-rules/Admins'
                        elif configurationName == 'MEMBERS':
                            script_dir = 'iptable-rules/Members'
                        elif configurationName == 'GUESTS':
                            script_dir = 'iptable-rules/Guest'
                        elif configurationName == 'LANP2P':
                            script_dir = 'iptable-rules/LAN-only-users'
                        script_name = f"{script_type}.sh"
                    else:
                        script_dir = f'iptable-rules/{configurationName}'
                        script_name = f"{script_type}.sh"
                    
                    files_dict[f"{script_dir}/{script_name}"] = scripts[script_key].encode('utf-8')
        
        # Create archive with integrity checks
        archive_data, _, combined_checksum = ArchiveUtils.create_archive(files_dict)
        
        # Return as streaming response
        return StreamingResponse(
            BytesIO(archive_data),
            media_type='application/x-7z-compressed',
            headers={
                'Content-Disposition': f'attachment; filename="{configurationName}_{timestamp}_complete.7z"',
                'X-Archive-Checksum': combined_checksum
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating backup archive: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Error creating backup archive: {str(e)}"
        )


@router.post('/uploadConfigurationBackup', response_model=StandardResponse)
async def upload_configuration_backup(
    files: List[UploadFile] = File(...),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Upload and process a backup archive"""
    try:
        if not files or len(files) != 1:
            return StandardResponse(
                status=False,
                message="Please upload exactly one backup archive"
            )
        
        file = files[0]
        if not file.filename.endswith('.7z'):
            return StandardResponse(
                status=False,
                message="Only .7z backup archives are allowed"
            )
        
        # Validate filename
        is_valid, error_msg = security_manager.validate_filename(file.filename)
        if not is_valid:
            return StandardResponse(
                status=False,
                message=f"Invalid filename: {error_msg}"
            )
        
        # Extract configuration name from filename
        match = re.search(r"^(.+?)_\d{14}_complete\.7z$", file.filename)
        if not match:
            return StandardResponse(
                status=False,
                message=f"Invalid backup filename format: {file.filename}"
            )
        
        config_name = match.group(1)
        backup_paths = get_backup_paths(config_name)
        
        # Read and verify the archive
        archive_data = await file.read()
        is_valid, error_msg, extracted_files = ArchiveUtils.verify_archive(archive_data)
        
        if not is_valid:
            return StandardResponse(
                status=False,
                message=f"Invalid backup archive: {error_msg}"
            )
        
        # Save verified files to appropriate locations
        saved_files = []
        for filename, content in extracted_files.items():
            # Skip iptables rules files as they're handled by restoreConfig
            if filename.startswith('iptable-rules/'):
                continue
            
            # Validate filename to prevent path traversal
            is_valid, error_msg = security_manager.validate_filename(filename)
            if not is_valid:
                logger.warning(f"Invalid filename in backup archive: {filename} - {error_msg}")
                continue
            
            # Validate path to prevent directory traversal
            normalized_filename = os.path.normpath(filename).lstrip(os.sep)
            if '..' in normalized_filename or normalized_filename.startswith('/'):
                logger.warning(f"Path traversal attempt detected in backup: {filename}")
                continue
            
            # Handle regular backup files - ensure path is within allowed directory
            base_path = os.path.normpath(backup_paths['config_dir'])
            file_path = os.path.join(base_path, normalized_filename)
            
            # Additional security check: ensure resolved path is within base_path
            resolved_path = os.path.abspath(file_path)
            resolved_base = os.path.abspath(base_path)
            if not resolved_path.startswith(resolved_base):
                logger.warning(f"Path outside allowed directory: {filename}")
                continue
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            saved_files.append(filename)
            
            if filename.endswith('.sh'):
                os.chmod(file_path, 0o755)
        
        return StandardResponse(
            status=True,
            message="Backup archive verified and extracted successfully",
            data={"saved_files": saved_files}
        )
        
    except Exception as e:
        logger.error(f"Error processing backup: {str(e)}")
        return StandardResponse(
            status=False,
            message=f"Error processing backup: {str(e)}"
        )

