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
from ..ConfigEnv import (
    redis_host, redis_port, redis_db, redis_password,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, BRUTE_FORCE_MAX_ATTEMPTS,
    BRUTE_FORCE_LOCKOUT_TIME, SESSION_TIMEOUT, SECURE_SESSION,
    DASHBOARD_MODE, ALLOWED_ORIGINS
)
from ..RateLimitMetrics import rate_limit_metrics

class SecurityManager:
    """Centralized security management for Wiregate"""
    
    def __init__(self):
        if redis is not None:
            try:
                # Try Redis cluster first, fallback to single instance
                if hasattr(redis, 'RedisCluster'):
                    try:
                        self.redis_client = redis.RedisCluster(
                            startup_nodes=[{"host": redis_host, "port": redis_port}],
                            password=redis_password,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5,
                            skip_full_coverage_check=True
                        )
                        # Test cluster connection
                        self.redis_client.ping()
                        self.is_cluster = True
                    except Exception:
                        # Fallback to single Redis instance
                        self.redis_client = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            password=redis_password,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5
                        )
                        self.is_cluster = False
                else:
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                    self.is_cluster = False
            except Exception:
                self.redis_client = None
                self.is_cluster = False
        else:
            self.redis_client = None
            self.is_cluster = False
        
        # Initialize metrics
        rate_limit_metrics.redis_client = self.redis_client
        
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
        """Check if request is rate limited with distributed support"""
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
            
            # Add current request with microsecond precision for better distribution
            pipe.zadd(key, {f"{current_time}.{int(time.time() * 1000000) % 1000000}": current_time})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            is_limited = current_requests >= limit
            
            return is_limited, {
                'current_requests': current_requests,
                'limit': limit,
                'window': window,
                'reset_time': current_time + window,
                'remaining_requests': max(0, limit - current_requests)
            }
            
        except Exception as e:
            # If Redis fails, allow the request but log the error
            print(f"Rate limiting error: {e}")
            return False, {}
    
    def is_distributed_rate_limited(self, identifier: str, limit: int = None, window: int = None, 
                                   burst_limit: int = None) -> Tuple[bool, Dict]:
        """Advanced distributed rate limiting with burst protection"""
        if self.redis_client is None:
            return False, {}
            
        limit = limit or RATE_LIMIT_REQUESTS
        window = window or RATE_LIMIT_WINDOW
        burst_limit = burst_limit or (limit // 4)  # 25% of normal limit for burst
        
        current_time = int(time.time())
        window_start = current_time - window
        burst_window = 60  # 1 minute burst window
        
        # Keys for different rate limiting strategies
        rate_key = f"rate_limit:{identifier}"
        burst_key = f"burst_limit:{identifier}"
        sliding_key = f"sliding_limit:{identifier}"
        
        try:
            pipe = self.redis_client.pipeline()
            
            # 1. Standard rate limiting
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zcard(rate_key)
            pipe.zadd(rate_key, {f"{current_time}.{int(time.time() * 1000000) % 1000000}": current_time})
            pipe.expire(rate_key, window)
            
            # 2. Burst protection (short window)
            burst_start = current_time - burst_window
            pipe.zremrangebyscore(burst_key, 0, burst_start)
            pipe.zcard(burst_key)
            pipe.zadd(burst_key, {f"{current_time}.{int(time.time() * 1000000) % 1000000}": current_time})
            pipe.expire(burst_key, burst_window)
            
            # 3. Sliding window (more precise)
            pipe.zremrangebyscore(sliding_key, 0, window_start)
            pipe.zcard(sliding_key)
            pipe.zadd(sliding_key, {f"{current_time}.{int(time.time() * 1000000) % 1000000}": current_time})
            pipe.expire(sliding_key, window)
            
            results = pipe.execute()
            
            # Extract results
            current_requests = results[1]
            burst_requests = results[6]
            sliding_requests = results[11]
            
            # Check all limits
            is_rate_limited = current_requests >= limit
            is_burst_limited = burst_requests >= burst_limit
            is_sliding_limited = sliding_requests >= limit
            
            # Overall limiting decision
            is_limited = is_rate_limited or is_burst_limited or is_sliding_limited
            
            # Record metrics
            limit_type = None
            if is_burst_limited:
                limit_type = 'burst'
            elif is_sliding_limited:
                limit_type = 'sliding'
            elif is_rate_limited:
                limit_type = 'rate'
            
            # Record request metrics (async, don't wait for completion)
            try:
                rate_limit_metrics.record_request(
                    identifier=identifier,
                    endpoint=getattr(request, 'path', 'unknown'),
                    is_limited=is_limited,
                    limit_type=limit_type
                )
            except Exception:
                pass  # Don't fail rate limiting if metrics fail
            
            return is_limited, {
                'current_requests': current_requests,
                'burst_requests': burst_requests,
                'sliding_requests': sliding_requests,
                'limit': limit,
                'burst_limit': burst_limit,
                'window': window,
                'reset_time': current_time + window,
                'remaining_requests': max(0, limit - current_requests),
                'is_rate_limited': is_rate_limited,
                'is_burst_limited': is_burst_limited,
                'is_sliding_limited': is_sliding_limited
            }
            
        except Exception as e:
            print(f"Distributed rate limiting error: {e}")
            return False, {}
    
    def get_rate_limit_status(self, identifier: str) -> Dict:
        """Get current rate limit status for an identifier"""
        if self.redis_client is None:
            return {'status': 'disabled'}
            
        current_time = int(time.time())
        window = RATE_LIMIT_WINDOW
        window_start = current_time - window
        
        try:
            rate_key = f"rate_limit:{identifier}"
            burst_key = f"burst_limit:{identifier}"
            
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zcard(rate_key)
            pipe.zcard(burst_key)
            pipe.ttl(rate_key)
            
            results = pipe.execute()
            
            return {
                'status': 'active',
                'current_requests': results[1],
                'burst_requests': results[2],
                'ttl': results[3],
                'window_remaining': max(0, window - (current_time - window_start))
            }
            
        except Exception as e:
            print(f"Rate limit status error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit for an identifier (admin function)"""
        if self.redis_client is None:
            return False
            
        try:
            keys = [
                f"rate_limit:{identifier}",
                f"burst_limit:{identifier}",
                f"sliding_limit:{identifier}"
            ]
            self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Rate limit reset error: {e}")
            return False
    
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

def rate_limit(limit: int = None, window: int = None, per: str = 'ip', use_distributed: bool = True):
    """Decorator for rate limiting endpoints with distributed support"""
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
            
            # Check rate limit using distributed method if enabled
            if use_distributed:
                is_limited, info = security_manager.is_distributed_rate_limited(identifier, limit, window)
            else:
                is_limited, info = security_manager.is_rate_limited(identifier, limit, window)
            
            if is_limited:
                # Determine which type of limit was exceeded
                limit_type = "rate"
                if info.get('is_burst_limited', False):
                    limit_type = "burst"
                elif info.get('is_sliding_limited', False):
                    limit_type = "sliding"
                
                return jsonify({
                    'status': False,
                    'message': f'Rate limit exceeded ({limit_type})',
                    'data': {
                        'retry_after': info.get('reset_time', 0) - int(time.time()),
                        'limit': info.get('limit', 0),
                        'current_requests': info.get('current_requests', 0),
                        'remaining_requests': info.get('remaining_requests', 0),
                        'limit_type': limit_type,
                        'burst_requests': info.get('burst_requests', 0),
                        'sliding_requests': info.get('sliding_requests', 0)
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
