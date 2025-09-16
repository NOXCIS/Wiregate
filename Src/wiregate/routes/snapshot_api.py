import os
import re
import shutil
import json
import logging

logger = logging.getLogger('wiregate')

from flask import request, make_response, Blueprint 


from ..modules.App import (
    ResponseObject
)

from ..modules.Core import (
    Configurations, Configuration
)

from ..modules.DashboardConfig import (
    DashboardConfig
)

# Import Security modules with fallbacks
try:
    from ..modules.Security import security_manager, secure_file_upload, validate_input
except ImportError:
    # Fallback if Security module is not available
    class MockSecurityManager:
        def validate_filename(self, filename):
            return True, filename
        def validate_path(self, file_path, base_path=None):
            return True, file_path
        def sanitize_input(self, data):
            return data
    
    security_manager = MockSecurityManager()
    
    def secure_file_upload(f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    
    def validate_input(required_fields=None):
        def decorator(f):
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapper
        return decorator

# Import Archive module with fallback
try:
    from ..modules.Archive.SnapShot import ArchiveUtils
except ImportError:
    # Fallback if Archive module is not available
    class ArchiveUtils:
        @staticmethod
        def create_archive(data, filename):
            return {"success": False, "message": "Archive module not available"}
        
        @staticmethod
        def extract_archive(file_path, extract_to):
            return {"success": False, "message": "Archive module not available"}

from ..modules.Utilities import (
    RegexMatch, get_backup_paths
)


snapshot_api_blueprint = Blueprint('snapshot_api', __name__)





@snapshot_api_blueprint.get('/getConfigurationBackup')
def API_getConfigurationBackup():
    """Get backups for a specific configuration with organized structure"""
    configurationName = request.args.get('configurationName')
    if configurationName is None or configurationName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    return ResponseObject(data=Configurations[configurationName].getBackups())


@snapshot_api_blueprint.get('/getAllConfigurationBackup')
def API_getAllConfigurationBackup():
    """Get all configuration backups with organized structure"""
    data = {
        "ExistingConfigurations": {},
        "NonExistingConfigurations": {}
    }

    # Get base backup directory
    backup_dir = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')

    # Handle existing configurations
    existingConfiguration = Configurations.keys()
    for config_name in existingConfiguration:
        backups = Configurations[config_name].getBackups(True)
        if backups:
            data['ExistingConfigurations'][config_name] = backups

    # Handle non-existing configurations
    if os.path.exists(backup_dir):
        # Look for backup directories that don't match existing configurations
        for dir_name in os.listdir(backup_dir):
            dir_path = os.path.join(backup_dir, dir_name)
            if os.path.isdir(dir_path) and dir_name not in existingConfiguration:
                backups = []
                files = [(f, os.path.getctime(os.path.join(dir_path, f)))
                         for f in os.listdir(dir_path)
                         if os.path.isfile(os.path.join(dir_path, f))]
                files.sort(key=lambda x: x[1], reverse=True)

                for f, _ in files:
                    if RegexMatch(r"^(.*)_(.*)\.(conf)$", f):
                        s = re.search(r"^(.*)_(.*)\.(conf)$", f)
                        date = s.group(2)
                        backup_info = {
                            "filename": f,
                            "backupDate": date,
                            "content": open(os.path.join(dir_path, f), 'r').read()
                        }

                        # Check for associated backup files
                        redis_file = f.replace(".conf", ".redis")
                        if os.path.exists(os.path.join(dir_path, redis_file)):
                            backup_info['database'] = True
                            backup_info['databaseContent'] = open(os.path.join(dir_path, redis_file), 'r').read()

                        iptables_file = f.replace(".conf", "_iptables.json")
                        if os.path.exists(os.path.join(dir_path, iptables_file)):
                            backup_info['iptables_scripts'] = True
                            with open(os.path.join(dir_path, iptables_file), 'r') as iptables_f:
                                backup_info['iptablesContent'] = iptables_f.read()

                        backups.append(backup_info)

                if backups:
                    data['NonExistingConfigurations'][dir_name] = backups

    return ResponseObject(data=data)


@snapshot_api_blueprint.get('/createConfigurationBackup')
def API_createConfigurationBackup():
    """Create a backup for a specific configuration using organized structure"""
    configurationName = request.args.get('configurationName')
    if configurationName is None or configurationName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")

    success = Configurations[configurationName].backupConfigurationFile()
    return ResponseObject(
        status=success,
        data=Configurations[configurationName].getBackups() if success else None
    )


@snapshot_api_blueprint.post('/deleteConfigurationBackup')
def API_DeleteConfigurationBackup():
    try:
        data = request.get_json()
        if 'configurationName' not in data or 'backupFileName' not in data:
            return ResponseObject(False, "Missing required parameters")

        config_name = data['configurationName']
        backup_file = data['backupFileName']

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
        if len(os.listdir(backup_paths['config_dir'])) == 0:
            os.rmdir(backup_paths['config_dir'])

        return ResponseObject(True, "Backup deleted successfully")

    except Exception as e:
        logging.error(f"Error deleting backup: {str(e)}")
        return ResponseObject(False, f"Failed to delete backup: {str(e)}")


@snapshot_api_blueprint.post('/restoreConfigurationBackup')
def API_restoreConfigurationBackup():
    """Restore a backup using organized structure"""
    try:
        if request.is_json:
            data = request.get_json()
            configuration_name = data.get("configurationName")
            backup_file_name = data.get("backupFileName")
            backup_file = None

            if not configuration_name or not backup_file_name:
                return ResponseObject(False, "Configuration name and backup file name are required")

        else:
            backup_file = request.files.get("backupFile")
            if not backup_file:
                return ResponseObject(False, "No backup file uploaded")

            # Extract configuration name from backup filename
            backup_filename = backup_file.filename
            match = re.search(r"^(.+?)_\d{14}_complete\.7z$", backup_filename)
            if not match:
                return ResponseObject(False, f"Invalid backup filename format: {backup_filename}")

            configuration_name = match.group(1)
            backup_file_name = None

        # Create temp directory for processing
        temp_dir = os.path.join(
            DashboardConfig.GetConfig("Server", "wg_conf_path")[1],
            'WGDashboard_Backup',
            'temp'
        )
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            if backup_file:
                # Handle uploaded 7z file
                if not backup_file.filename.endswith('.7z'):
                    return ResponseObject(False, "Uploaded file must be a .7z archive")

                # Validate filename and path
                is_valid, error_msg = security_manager.validate_filename(backup_file.filename)
                if not is_valid:
                    return ResponseObject(False, f"Invalid filename: {error_msg}")
                
                # Validate path to prevent traversal
                is_valid, safe_path = security_manager.validate_path(backup_file.filename, temp_dir)
                if not is_valid:
                    return ResponseObject(False, f"Invalid file path: {error_msg}")
                
                # Save uploaded file
                file_path = os.path.join(temp_dir, safe_path)
                backup_file.save(file_path)

                # Verify and extract the archive
                is_valid, error_msg, extracted_files = ArchiveUtils.verify_archive(
                    open(file_path, 'rb').read()
                )

                if not is_valid:
                    return ResponseObject(False, f"Invalid backup archive: {error_msg}")

                # Create configuration if it doesn't exist
                if configuration_name not in Configurations.keys():
                    Configurations[configuration_name] = Configuration(configuration_name)

                # Get backup paths for the configuration
                backup_paths = get_backup_paths(configuration_name)

                # Save extracted files to appropriate locations
                for filename, content in extracted_files.items():
                    if filename.startswith('iptable-rules/'):
                        # Handle iptables rules - preserve directory structure
                        rules_dir = os.path.join(
                            DashboardConfig.GetConfig("Server", "iptable_rules_path")[1]
                        )
                        # Remove 'iptable-rules/' prefix and use the rest as the path
                        relative_path = filename[14:]  # Remove 'iptable-rules/' (14 characters)
                        file_path = os.path.join(rules_dir, relative_path)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    else:
                        # Handle regular backup files
                        file_path = os.path.join(backup_paths['config_dir'], filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    with open(file_path, 'wb') as f:
                        f.write(content)

                    if filename.endswith('.sh'):
                        os.chmod(file_path, 0o755)

            else:
                # Handle native backup restore
                if configuration_name not in Configurations.keys():
                    return ResponseObject(False, "Configuration does not exist")

                success = Configurations[configuration_name].restoreBackup(backup_file_name)
                if not success:
                    return ResponseObject(False, "Failed to restore backup")

                # Force refresh of peers list to ensure latest data
                Configurations[configuration_name].getPeersList()
                
                # Return updated configuration data for frontend refresh
                return ResponseObject(True, "Backup restored successfully", {
                    "configuration": Configurations[configuration_name].toJson(),
                    "peers": [peer.toJson() for peer in Configurations[configuration_name].getPeersList()]
                })

        except Exception as e:
            return ResponseObject(False, f"Error processing uploaded file: {str(e)}")
        finally:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    except Exception as e:
        return ResponseObject(False, f"Error restoring backup: {str(e)}")


@snapshot_api_blueprint.get('/downloadConfigurationBackup')
def API_downloadConfigurationBackup():
    """Download a backup with enhanced script handling"""
    try:
        config_name = request.args.get('configurationName')
        backup_name = request.args.get('backupFileName')
        logger.debug(f"Download requested for config: {config_name}, backup: {backup_name}")

        if not config_name or not backup_name:
            return ResponseObject(False, "Configuration name and backup filename are required")

        # Get timestamp from backup filename
        timestamp = backup_name.split('_')[1].split('.')[0]
        backup_paths = get_backup_paths(config_name, timestamp)

        if not os.path.exists(backup_paths['conf_file']):
            return ResponseObject(False, "Backup file not found")

        try:
            # Collect all backup files
            files_dict = {}

            # Add main configuration file
            with open(backup_paths['conf_file'], 'rb') as f:
                files_dict[os.path.basename(backup_paths['conf_file'])] = f.read()

            # Add Redis backup if it exists
            if os.path.exists(backup_paths['redis_file']):
                with open(backup_paths['redis_file'], 'rb') as f:
                    files_dict[os.path.basename(backup_paths['redis_file'])] = f.read()

            # Add iptables backup if it exists
            if os.path.exists(backup_paths['iptables_file']):
                # First add the iptables.json file itself
                with open(backup_paths['iptables_file'], 'rb') as f:
                    files_dict[os.path.basename(backup_paths['iptables_file'])] = f.read()

                # Then process the scripts stored in iptables.json
                with open(backup_paths['iptables_file'], 'r') as f:
                    scripts = json.load(f)
                # Include all script files if they exist
                script_types = ['preup', 'postup', 'predown', 'postdown']
                for script_type in script_types:
                    script_key = f"{script_type}_script"
                    if script_key in scripts and scripts[script_key]:
                        # Determine the correct directory structure based on config name
                        if config_name in ['ADMINS', 'MEMBERS', 'GUESTS', 'LANP2P']:
                            # Use the special directory structure for pregenerated configs
                            if config_name == 'ADMINS':
                                script_dir = 'iptable-rules/Admins'
                            elif config_name == 'MEMBERS':
                                script_dir = 'iptable-rules/Members'
                            elif config_name == 'GUESTS':
                                script_dir = 'iptable-rules/Guest'
                            elif config_name == 'LANP2P':
                                script_dir = 'iptable-rules/LAN-only-users'
                            script_name = f"{script_type}.sh"
                        else:
                            # Use subdirectory structure for all custom configs
                            script_dir = f'iptable-rules/{config_name}'
                            script_name = f"{script_type}.sh"
                        
                        # The script content is already in the JSON, no need to read from filesystem
                        files_dict[f"{script_dir}/{script_name}"] = scripts[script_key].encode('utf-8')

            # Create archive with integrity checks
            archive_data, _, combined_checksum = ArchiveUtils.create_archive(files_dict)

            # Create response
            response = make_response(archive_data)
            response.headers['Content-Type'] = 'application/x-7z-compressed'
            response.headers['Content-Disposition'] = \
                f'attachment; filename="{config_name}_{timestamp}_complete.7z"'
            response.headers['Content-Length'] = len(archive_data)
            response.headers['X-Archive-Checksum'] = combined_checksum

            return response

        except Exception as e:
            return ResponseObject(False, f"Error creating backup archive: {str(e)}")

    except Exception as e:
        return ResponseObject(False, f"Error processing download request: {str(e)}")


@snapshot_api_blueprint.post('/uploadConfigurationBackup')
@secure_file_upload(allowed_extensions=['.7z'], max_size=50*1024*1024)  # 50MB max
def API_uploadConfigurationBackup():
    """Upload and process a backup using organized structure"""
    try:
        if 'files' not in request.files:
            return ResponseObject(False, "No file part in request")

        files = request.files.getlist('files')
        if not files or len(files) != 1:
            return ResponseObject(False, "Please upload exactly one backup archive")

        file = files[0]
        if file.filename == '':
            return ResponseObject(False, "File name is empty")

        if not file.filename.endswith('.7z'):
            return ResponseObject(False, "Only .7z backup archives are allowed")

        # Extract configuration name from filename
        match = re.search(r"^(.+?)_\d{14}_complete\.7z$", file.filename)
        if not match:
            return ResponseObject(False, f"Invalid backup filename format: {file.filename}")

        config_name = match.group(1)
        backup_paths = get_backup_paths(config_name)

        # Read and verify the archive
        archive_data = file.read()
        is_valid, error_msg, extracted_files = ArchiveUtils.verify_archive(archive_data)

        if not is_valid:
            return ResponseObject(False, f"Invalid backup archive: {error_msg}")

        # Save verified files to appropriate locations
        saved_files = []
        for filename, content in extracted_files.items():
            # Skip iptables rules files as they're handled by restoreConfig
            if filename.startswith('iptable-rules/'):
                continue

            # Handle regular backup files
            file_path = os.path.join(backup_paths['config_dir'], filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(content)
            saved_files.append(filename)

            if filename.endswith('.sh'):
                os.chmod(file_path, 0o755)

        return ResponseObject(
            True,
            "Backup archive verified and extracted successfully",
            {"saved_files": saved_files}
        )

    except Exception as e:
        return ResponseObject(False, f"Error processing backup: {str(e)}")
