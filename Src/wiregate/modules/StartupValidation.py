"""
Startup Configuration Validation
Validates critical configuration at application startup
"""
import os
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

from .Config import (
    DASHBOARD_TYPE, DASHBOARD_MODE,
    redis_host, redis_port, redis_db, redis_password,
    postgres_host, postgres_port, postgres_db, postgres_user, postgres_password,
    CONFIGURATION_PATH, DB_PATH
)

logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a validation issue"""
    def __init__(self, severity: str, component: str, message: str, fix_hint: str = None):
        self.severity = severity  # 'critical', 'warning', 'info'
        self.component = component
        self.message = message
        self.fix_hint = fix_hint
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity,
            'component': self.component,
            'message': self.message,
            'fix_hint': self.fix_hint
        }


class StartupValidation:
    """Validates startup configuration"""
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.critical_issues: List[ValidationIssue] = []
        self.warnings: List[ValidationIssue] = []
    
    def add_issue(self, severity: str, component: str, message: str, fix_hint: str = None):
        """Add a validation issue"""
        issue = ValidationIssue(severity, component, message, fix_hint)
        self.issues.append(issue)
        
        if severity == 'critical':
            self.critical_issues.append(issue)
        elif severity == 'warning':
            self.warnings.append(issue)
    
    async def validate_database_connectivity(self) -> bool:
        """Validate database connectivity"""
        try:
            from .DataBase import get_redis_manager
            manager = await get_redis_manager()
            
            if DASHBOARD_TYPE.lower() == 'simple':
                # SQLite - check if we can execute a query
                try:
                    if hasattr(manager, 'execute_query'):
                        result = await manager.execute_query("SELECT 1")
                        if result:
                            logger.info("✓ SQLite database connectivity validated")
                            return True
                        else:
                            self.add_issue(
                                'critical',
                                'database',
                                'SQLite database query returned no results',
                                'Check SQLite database file integrity'
                            )
                            return False
                    else:
                        self.add_issue(
                            'critical',
                            'database',
                            'SQLite database manager does not have execute_query method',
                            'Check database manager initialization'
                        )
                        return False
                except Exception as e:
                    self.add_issue(
                        'critical',
                        'database',
                        f'SQLite database connection failed: {str(e)}',
                        'Check database file permissions and path'
                    )
                    return False
            else:
                # PostgreSQL - check connection
                try:
                    if hasattr(manager, 'postgres_conn'):
                        import asyncio
                        def _check_postgres():
                            with manager.postgres_conn.cursor() as cursor:
                                cursor.execute("SELECT 1")
                                cursor.fetchone()
                                return True
                        
                        await asyncio.to_thread(_check_postgres)
                        logger.info("✓ PostgreSQL database connectivity validated")
                        return True
                    else:
                        self.add_issue(
                            'critical',
                            'database',
                            'PostgreSQL connection not available',
                            'Check PostgreSQL connection configuration'
                        )
                        return False
                except Exception as e:
                    self.add_issue(
                        'critical',
                        'database',
                        f'PostgreSQL connection failed: {str(e)}',
                        'Check PostgreSQL host, port, credentials, and network connectivity'
                    )
                    return False
        except Exception as e:
            self.add_issue(
                'critical',
                'database',
                f'Database validation error: {str(e)}',
                'Check database configuration and dependencies'
            )
            return False
    
    async def validate_redis_connectivity(self) -> bool:
        """Validate Redis connectivity (only in scale mode)"""
        if DASHBOARD_TYPE.lower() != 'scale':
            logger.debug("Redis validation skipped (simple mode)")
            return True
        
        try:
            import redis
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            redis_client.ping()
            logger.info("✓ Redis connectivity validated")
            return True
        except ImportError:
            self.add_issue(
                'critical',
                'redis',
                'Redis Python library not installed',
                'Install redis package: pip install redis'
            )
            return False
        except Exception as e:
            self.add_issue(
                'critical',
                'redis',
                f'Redis connection failed: {str(e)}',
                'Check Redis host, port, password, and network connectivity'
            )
            return False
    
    def validate_file_paths(self) -> bool:
        """Validate critical file paths exist and are writable"""
        all_valid = True
        
        # Check configuration path
        if not os.path.exists(CONFIGURATION_PATH):
            try:
                os.makedirs(CONFIGURATION_PATH, exist_ok=True)
                logger.info(f"✓ Created configuration path: {CONFIGURATION_PATH}")
            except Exception as e:
                self.add_issue(
                    'critical',
                    'file_paths',
                    f'Configuration path does not exist and cannot be created: {CONFIGURATION_PATH}',
                    f'Create directory manually or fix permissions: {str(e)}'
                )
                all_valid = False
        else:
            if not os.access(CONFIGURATION_PATH, os.W_OK):
                self.add_issue(
                    'critical',
                    'file_paths',
                    f'Configuration path is not writable: {CONFIGURATION_PATH}',
                    'Fix directory permissions'
                )
                all_valid = False
        
        # Check database path
        if not os.path.exists(DB_PATH):
            try:
                os.makedirs(DB_PATH, exist_ok=True)
                logger.info(f"✓ Created database path: {DB_PATH}")
            except Exception as e:
                self.add_issue(
                    'critical',
                    'file_paths',
                    f'Database path does not exist and cannot be created: {DB_PATH}',
                    f'Create directory manually or fix permissions: {str(e)}'
                )
                all_valid = False
        else:
            if not os.access(DB_PATH, os.W_OK):
                self.add_issue(
                    'critical',
                    'file_paths',
                    f'Database path is not writable: {DB_PATH}',
                    'Fix directory permissions'
                )
                all_valid = False
        
        # Check WireGuard config path
        try:
            from .DashboardConfig import DashboardConfig
            wg_conf_path = DashboardConfig.GetConfig("Server", "wg_conf_path")[1]
            if wg_conf_path:
                if not os.path.exists(wg_conf_path):
                    try:
                        os.makedirs(wg_conf_path, exist_ok=True)
                        logger.info(f"✓ Created WireGuard config path: {wg_conf_path}")
                    except Exception as e:
                        self.add_issue(
                            'warning',
                            'file_paths',
                            f'WireGuard config path does not exist: {wg_conf_path}',
                            f'Create directory manually: {str(e)}'
                        )
                elif not os.access(wg_conf_path, os.W_OK):
                    self.add_issue(
                        'warning',
                        'file_paths',
                        f'WireGuard config path is not writable: {wg_conf_path}',
                        'Fix directory permissions'
                    )
        except Exception as e:
            self.add_issue(
                'warning',
                'file_paths',
                f'Could not validate WireGuard config path: {str(e)}',
                'Check DashboardConfig initialization'
            )
        
        if all_valid:
            logger.info("✓ File paths validated")
        
        return all_valid
    
    def validate_environment_variables(self) -> bool:
        """Validate required environment variables are set"""
        all_valid = True
        
        # Required variables (with defaults, so these are warnings)
        optional_vars = {
            'DASHBOARD_TYPE': DASHBOARD_TYPE,
            'DASHBOARD_MODE': DASHBOARD_MODE,
        }
        
        for var_name, value in optional_vars.items():
            if not value or value == '':
                self.add_issue(
                    'warning',
                    'environment',
                    f'Environment variable {var_name} is not set, using default',
                    f'Set {var_name} environment variable for explicit configuration'
                )
        
        # Scale mode specific variables
        if DASHBOARD_TYPE.lower() == 'scale':
            scale_vars = {
                'POSTGRES_HOST': postgres_host,
                'POSTGRES_PORT': postgres_port,
                'POSTGRES_DB': postgres_db,
                'POSTGRES_USER': postgres_user,
                'POSTGRES_PASSWORD': postgres_password,
                'REDIS_HOST': redis_host,
                'REDIS_PORT': redis_port,
            }
            
            for var_name, value in scale_vars.items():
                if not value or value == '':
                    self.add_issue(
                        'critical',
                        'environment',
                        f'Required environment variable {var_name} is not set for scale mode',
                        f'Set {var_name} environment variable'
                    )
                    all_valid = False
        
        if all_valid:
            logger.info("✓ Environment variables validated")
        
        return all_valid
    
    def validate_configuration_file(self) -> bool:
        """Validate configuration file integrity"""
        try:
            from .DashboardConfig import DashboardConfig
            
            # Try to read a basic config value
            try:
                version = DashboardConfig.GetConfig("Server", "version")[1]
                if version:
                    logger.info("✓ Configuration file validated")
                    return True
                else:
                    self.add_issue(
                        'warning',
                        'configuration',
                        'Configuration file exists but appears empty',
                        'Check configuration file content'
                    )
                    return False
            except Exception as e:
                self.add_issue(
                    'warning',
                    'configuration',
                    f'Could not read configuration file: {str(e)}',
                    'Check configuration file format and permissions'
                )
                return False
        except Exception as e:
            self.add_issue(
                'warning',
                'configuration',
                f'Configuration validation error: {str(e)}',
                'Check DashboardConfig initialization'
            )
            return False
    
    async def validate_all(self) -> Tuple[bool, Dict[str, Any]]:
        """Run all validation checks"""
        logger.info("Starting startup configuration validation...")
        
        # Run all validations
        db_valid = await self.validate_database_connectivity()
        redis_valid = await self.validate_redis_connectivity()
        paths_valid = self.validate_file_paths()
        env_valid = self.validate_environment_variables()
        config_valid = self.validate_configuration_file()
        
        # Determine overall status
        has_critical_issues = len(self.critical_issues) > 0
        overall_valid = db_valid and redis_valid and paths_valid and env_valid and not has_critical_issues
        
        # Build validation report
        report = {
            'valid': overall_valid,
            'has_critical_issues': has_critical_issues,
            'has_warnings': len(self.warnings) > 0,
            'total_issues': len(self.issues),
            'critical_count': len(self.critical_issues),
            'warning_count': len(self.warnings),
            'issues': [issue.to_dict() for issue in self.issues],
            'checks': {
                'database': db_valid,
                'redis': redis_valid,
                'file_paths': paths_valid,
                'environment': env_valid,
                'configuration': config_valid
            }
        }
        
        if overall_valid:
            logger.info("✓ Startup validation passed")
        else:
            logger.error("✗ Startup validation failed - critical issues found")
            for issue in self.critical_issues:
                logger.error(f"  CRITICAL: {issue.component} - {issue.message}")
        
        if self.warnings:
            logger.warning(f"⚠ Startup validation completed with {len(self.warnings)} warnings")
            for issue in self.warnings:
                logger.warning(f"  WARNING: {issue.component} - {issue.message}")
        
        return overall_valid, report


# Global validation instance
_startup_validator = StartupValidation()


async def validate_startup_config() -> Tuple[bool, Dict[str, Any]]:
    """
    Validate startup configuration
    Returns: (is_valid, validation_report)
    """
    return await _startup_validator.validate_all()

