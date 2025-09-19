from flask import Blueprint, request
import logging
import json

logger = logging.getLogger('wiregate')

from ..modules.App import ResponseObject
from ..modules.DataBase.DataBaseManager import DatabaseAPI

database_blueprint = Blueprint('database', __name__)

@database_blueprint.route('/database/config', methods=['GET'])
def get_database_config():
    """Get current database configuration"""
    try:
        # Get database configuration from DatabaseAPI
        config = DatabaseAPI.get_config()
        return ResponseObject(True, data=config)
    except Exception as e:
        logger.error(f"Failed to get database config: {e}")
        return ResponseObject(False, f"Failed to get database configuration: {str(e)}")

@database_blueprint.route('/database/config', methods=['POST'])
def update_database_config():
    """Update database configuration"""
    try:
        data = request.get_json()
        if not data:
            return ResponseObject(False, "No configuration data provided")
        
        # Update database configuration
        result = DatabaseAPI.update_config(data)
        if result:
            return ResponseObject(True, "Database configuration updated successfully")
        else:
            return ResponseObject(False, "Failed to update database configuration")
    except Exception as e:
        logger.error(f"Failed to update database config: {e}")
        return ResponseObject(False, f"Failed to update database configuration: {str(e)}")

@database_blueprint.route('/database/stats', methods=['GET'])
def get_database_stats():
    """Get database statistics"""
    try:
        stats = DatabaseAPI.get_stats()
        return ResponseObject(True, data=stats)
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return ResponseObject(False, f"Failed to get database statistics: {str(e)}")

@database_blueprint.route('/database/test', methods=['POST'])
def test_database_connections():
    """Test database connections"""
    try:
        data = request.get_json()
        if not data:
            return ResponseObject(False, "No configuration data provided")
        
        # Test database connections
        result = DatabaseAPI.test_connections(data)
        if result['success']:
            return ResponseObject(True, data=result['data'])
        else:
            return ResponseObject(False, result['message'])
    except Exception as e:
        logger.error(f"Failed to test database connections: {e}")
        return ResponseObject(False, f"Failed to test database connections: {str(e)}")

@database_blueprint.route('/database/migrate', methods=['POST'])
def migrate_database():
    """Migrate database between architectures"""
    try:
        data = request.get_json()
        if not data or 'type' not in data:
            return ResponseObject(False, "Migration type not specified")
        
        migration_type = data['type']
        result = DatabaseAPI.migrate(migration_type)
        
        if result['success']:
            return ResponseObject(True, data=result['data'], message=result['message'])
        else:
            return ResponseObject(False, result['message'])
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        return ResponseObject(False, f"Failed to migrate database: {str(e)}")

@database_blueprint.route('/database/clear-cache', methods=['POST'])
def clear_database_cache():
    """Clear database cache"""
    try:
        result = DatabaseAPI.clear_cache()
        if result['success']:
            return ResponseObject(True, message=result['message'])
        else:
            return ResponseObject(False, result['message'])
    except Exception as e:
        logger.error(f"Failed to clear database cache: {e}")
        return ResponseObject(False, f"Failed to clear database cache: {str(e)}")
