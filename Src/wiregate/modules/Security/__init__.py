"""
Security module package for Wiregate
Contains security-related modules for rate limiting, command execution, and security utilities
"""

from .Security import (
    SecurityManager,
    security_manager
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

# FastAPI components
try:
    from .fastapi_middleware import (
        HTTPSRedirectMiddleware,
        BotProtectionMiddleware,
        CSRFProtectionMiddleware,
        SecurityHeadersMiddleware,
        RequestLoggingMiddleware,
        RateLimitMiddleware,
        SessionMiddleware,
        configure_cors
    )
    from .fastapi_dependencies import (
        get_security_manager,
        verify_api_key_dependency,
        get_current_user,
        require_authentication as fastapi_require_auth,
        get_optional_user,
        check_brute_force,
        validate_csrf_token
    )
    FASTAPI_AVAILABLE = True
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"FastAPI components not available: {e}")
    FASTAPI_AVAILABLE = False

__all__ = [
    # Security module exports
    'SecurityManager',
    'security_manager',
    
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
    'execute_grep_command',
]

# Add FastAPI exports if available
if FASTAPI_AVAILABLE:
    __all__.extend([
        # FastAPI middleware
        'HTTPSRedirectMiddleware',
        'BotProtectionMiddleware',
        'CSRFProtectionMiddleware',
        'SecurityHeadersMiddleware',
        'RequestLoggingMiddleware',
        'RateLimitMiddleware',
        'SessionMiddleware',
        'configure_cors',
        
        # FastAPI dependencies
        'get_security_manager',
        'verify_api_key_dependency',
        'get_current_user',
        'fastapi_require_auth',
        'get_optional_user',
        'check_brute_force',
        'validate_csrf_token',
    ])
