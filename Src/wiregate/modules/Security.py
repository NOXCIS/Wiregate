"""
Security module for Wiregate
Implements rate limiting, brute force protection, input validation, and security utilities
"""
import time
import hashlib
import hmac
import secrets
import re
import os
from typing import Dict, List, Optional, Tuple
from functools import wraps
from flask import request, jsonify, session, g
from datetime import datetime, timedelta
try:
    import redis
except ImportError:
    redis = None
from ..modules.ConfigEnv import (
    redis_host, redis_port, redis_db, redis_password,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, BRUTE_FORCE_MAX_ATTEMPTS,
    BRUTE_FORCE_LOCKOUT_TIME, SESSION_TIMEOUT, SECURE_SESSION,
    DASHBOARD_MODE, ALLOWED_ORIGINS
)

class SecurityManager:
    """Centralized security management for Wiregate"""
    
    def __init__(self):
        if redis is not None:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            except Exception:
                self.redis_client = None
        else:
            self.redis_client = None
        
        # Security patterns
        self.path_traversal_patterns = [
            r'\.\./', r'\.\.\\', r'\.\.%2f', r'\.\.%5c',
            r'%2e%2e%2f', r'%2e%2e%5c', r'\.\.%252f', r'\.\.%255c'
        ]
        
        self.dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.pl', '.sh'
        ]
    
    def constant_time_compare(self, val1: str, val2: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks"""
        if len(val1) != len(val2):
            return False
        result = 0
        for x, y in zip(val1.encode(), val2.encode()):
            result |= x ^ y
        return result == 0
    
    def verify_api_key(self, provided_key: str, valid_keys: List[str]) -> bool:
        """Verify API key using constant time comparison"""
        if not provided_key or not valid_keys:
            return False
        
        # Use constant time comparison for each key
        for valid_key in valid_keys:
            if self.constant_time_compare(provided_key, valid_key):
                return True
        return False
    
    def is_rate_limited(self, identifier: str, limit: int = None, window: int = None) -> Tuple[bool, Dict]:
        """Check if request is rate limited"""
        if self.redis_client is None:
            return False, {}
            
        limit = limit or RATE_LIMIT_REQUESTS
        window = window or RATE_LIMIT_WINDOW
        
        current_time = int(time.time())
        window_start = current_time - window
        key = f"rate_limit:{identifier}"
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            is_limited = current_requests >= limit
            
            return is_limited, {
                'current_requests': current_requests,
                'limit': limit,
                'window': window,
                'reset_time': current_time + window
            }
            
        except Exception as e:
            # If Redis fails, allow the request but log the error
            print(f"Rate limiting error: {e}")
            return False, {}
    
    def check_brute_force(self, identifier: str) -> Tuple[bool, Dict]:
        """Check if identifier is locked due to brute force attempts"""
        if self.redis_client is None:
            return False, {'attempts': 0, 'locked_until': None}
            
        key = f"brute_force:{identifier}"
        
        try:
            attempts = self.redis_client.get(key)
            if attempts is None:
                return False, {'attempts': 0, 'locked_until': None}
            
            attempts = int(attempts)
            if attempts >= BRUTE_FORCE_MAX_ATTEMPTS:
                # Check if lockout period has expired
                lockout_key = f"brute_force_lockout:{identifier}"
                lockout_until = self.redis_client.get(lockout_key)
                
                if lockout_until:
                    lockout_until = int(lockout_until)
                    if time.time() < lockout_until:
                        return True, {
                            'attempts': attempts,
                            'locked_until': lockout_until,
                            'remaining_time': lockout_until - int(time.time())
                        }
                    else:
                        # Lockout expired, reset attempts
                        self.redis_client.delete(key, lockout_key)
                        return False, {'attempts': 0, 'locked_until': None}
            
            return False, {'attempts': attempts, 'locked_until': None}
            
        except Exception as e:
            print(f"Brute force check error: {e}")
            return False, {'attempts': 0, 'locked_until': None}
    
    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed authentication attempt"""
        if self.redis_client is None:
            return
            
        key = f"brute_force:{identifier}"
        
        try:
            # Increment attempts
            attempts = self.redis_client.incr(key)
            
            # Set expiration
            self.redis_client.expire(key, BRUTE_FORCE_LOCKOUT_TIME)
            
            # If max attempts reached, set lockout
            if attempts >= BRUTE_FORCE_MAX_ATTEMPTS:
                lockout_until = int(time.time()) + BRUTE_FORCE_LOCKOUT_TIME
                lockout_key = f"brute_force_lockout:{identifier}"
                self.redis_client.set(lockout_key, lockout_until, ex=BRUTE_FORCE_LOCKOUT_TIME)
                
        except Exception as e:
            print(f"Failed to record brute force attempt: {e}")
    
    def clear_failed_attempts(self, identifier: str) -> None:
        """Clear failed attempts for successful authentication"""
        if self.redis_client is None:
            return
            
        try:
            self.redis_client.delete(f"brute_force:{identifier}", f"brute_force_lockout:{identifier}")
        except Exception as e:
            print(f"Failed to clear brute force attempts: {e}")
    
    def validate_path(self, file_path: str, base_path: str = None) -> Tuple[bool, str]:
        """Validate file path to prevent path traversal attacks"""
        if not file_path:
            return False, "Empty file path"
        
        # Normalize path
        normalized_path = os.path.normpath(file_path)
        
        # Check for path traversal patterns
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return False, f"Path traversal detected: {pattern}"
        
        # If base_path is provided, ensure the file is within it
        if base_path:
            base_path = os.path.normpath(base_path)
            try:
                # Resolve relative paths
                full_path = os.path.abspath(os.path.join(base_path, normalized_path))
                if not full_path.startswith(os.path.abspath(base_path)):
                    return False, "Path outside allowed directory"
            except (OSError, ValueError):
                return False, "Invalid path"
        
        return True, normalized_path
    
    def validate_filename(self, filename: str) -> Tuple[bool, str]:
        """Validate filename for security"""
        if not filename:
            return False, "Empty filename"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            if char in filename:
                return False, f"Dangerous character in filename: {char}"
        
        # Check for dangerous extensions
        filename_lower = filename.lower()
        for ext in self.dangerous_extensions:
            if filename_lower.endswith(ext):
                return False, f"Dangerous file extension: {ext}"
        
        # Check length
        if len(filename) > 255:
            return False, "Filename too long"
        
        return True, filename
    
    def sanitize_input(self, input_str: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        if not input_str:
            return ""
        
        # Limit length
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        # Remove null bytes and control characters
        input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
        
        return input_str.strip()
    
    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_port(self, port: str) -> bool:
        """Validate port number"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str) -> str:
        """Hash password using secure method"""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

# Global security manager instance
security_manager = SecurityManager()

def rate_limit(limit: int = None, window: int = None, per: str = 'ip'):
    """Decorator for rate limiting endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier (IP address or user ID)
            if per == 'ip':
                identifier = request.remote_addr
            elif per == 'user' and 'username' in session:
                identifier = session['username']
            else:
                identifier = request.remote_addr
            
            # Check rate limit
            is_limited, info = security_manager.is_rate_limited(identifier, limit, window)
            
            if is_limited:
                return jsonify({
                    'status': False,
                    'message': 'Rate limit exceeded',
                    'data': {
                        'retry_after': info.get('reset_time', 0) - int(time.time()),
                        'limit': info.get('limit', 0),
                        'current_requests': info.get('current_requests', 0)
                    }
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def brute_force_protection(identifier_func=None):
    """Decorator for brute force protection on authentication endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier for brute force tracking
            if identifier_func:
                identifier = identifier_func()
            else:
                identifier = request.remote_addr
            
            # Check if locked due to brute force
            is_locked, info = security_manager.check_brute_force(identifier)
            
            if is_locked:
                remaining_time = info.get('remaining_time', 0)
                return jsonify({
                    'status': False,
                    'message': f'Account temporarily locked due to too many failed attempts. Try again in {remaining_time} seconds.',
                    'data': {
                        'locked_until': info.get('locked_until', 0),
                        'remaining_time': remaining_time
                    }
                }), 423
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # If authentication failed, record the attempt
            if hasattr(result, 'get_json'):
                response_data = result.get_json()
                if not response_data.get('status', False):
                    security_manager.record_failed_attempt(identifier)
            elif isinstance(result, tuple) and len(result) > 0:
                # Check if it's an error response
                if isinstance(result[0], str) and 'error' in result[0].lower():
                    security_manager.record_failed_attempt(identifier)
            
            return result
        return decorated_function
    return decorator

def validate_input(required_fields: List[str] = None, max_length: int = 1000):
    """Decorator for input validation"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get request data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'status': False,
                        'message': f'Missing required fields: {", ".join(missing_fields)}',
                        'data': {'missing_fields': missing_fields}
                    }), 400
            
            # Sanitize all string inputs
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = security_manager.sanitize_input(value, max_length)
            
            # Store sanitized data in g for use in the function
            g.sanitized_data = data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def secure_file_upload(allowed_extensions: List[str] = None, max_size: int = None):
    """Decorator for secure file upload validation"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'file' not in request.files:
                return jsonify({
                    'status': False,
                    'message': 'No file provided'
                }), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    'status': False,
                    'message': 'No file selected'
                }), 400
            
            # Validate filename
            is_valid, error_msg = security_manager.validate_filename(file.filename)
            if not is_valid:
                return jsonify({
                    'status': False,
                    'message': f'Invalid filename: {error_msg}'
                }), 400
            
            # Check file extension
            if allowed_extensions:
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    return jsonify({
                        'status': False,
                        'message': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
                    }), 400
            
            # Check file size
            if max_size:
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > max_size:
                    return jsonify({
                        'status': False,
                        'message': f'File too large. Maximum size: {max_size} bytes'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_authentication(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({
                'status': False,
                'message': 'Authentication required'
            }), 401
        
        # Check session timeout
        if 'last_activity' in session:
            last_activity = session['last_activity']
            if time.time() - last_activity > SESSION_TIMEOUT:
                session.clear()
                return jsonify({
                    'status': False,
                    'message': 'Session expired'
                }), 401
        
        # Update last activity
        session['last_activity'] = time.time()
        
        return f(*args, **kwargs)
    return decorated_function

def secure_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    if DASHBOARD_MODE == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    return response
