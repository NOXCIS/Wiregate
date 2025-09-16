"""
Security module package for Wiregate
Contains security-related modules for rate limiting, command execution, and security utilities
"""

from .Security import (
    SecurityManager,
    security_manager,
    rate_limit,
    brute_force_protection,
    validate_input,
    secure_file_upload,
    require_authentication,
    secure_headers
)

from .SecureCommand import (
    SecureCommandExecutor,
    secure_executor,
    execute_secure_command,
    execute_wg_command,
    execute_awg_command,
    execute_file_operation,
    execute_wg_quick_command,
    execute_awg_quick_command,
    execute_ip_command,
    execute_awk_command,
    execute_grep_command
)

__all__ = [
    # Security module exports
    'SecurityManager',
    'security_manager',
    'rate_limit',
    'brute_force_protection',
    'validate_input',
    'secure_file_upload',
    'require_authentication',
    'secure_headers',
    
    # SecureCommand module exports
    'SecureCommandExecutor',
    'secure_executor',
    'execute_secure_command',
    'execute_wg_command',
    'execute_awg_command',
    'execute_file_operation',
    'execute_wg_quick_command',
    'execute_awg_quick_command',
    'execute_ip_command',
    'execute_awk_command',
    'execute_grep_command'
]
