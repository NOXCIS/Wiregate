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
import logging
from typing import Dict, List, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta

# Set up logger
logger = logging.getLogger(__name__)
try:
    import redis
except ImportError:
    redis = None
from ..Config import (
    redis_host, redis_port, redis_db, redis_password,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, BRUTE_FORCE_MAX_ATTEMPTS,
    BRUTE_FORCE_LOCKOUT_TIME, SESSION_TIMEOUT, SECURE_SESSION,
    DASHBOARD_MODE, ALLOWED_ORIGINS
)
from ..DataBase.DataBaseManager import get_redis_manager
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
        
        # Initialize PostgreSQL database manager for brute force protection
        try:
            self.db_manager = get_redis_manager()
            # Create brute force table if it doesn't exist using existing create_table method
            brute_force_schema = {
                'id': 'SERIAL PRIMARY KEY',
                'identifier': 'VARCHAR(255) NOT NULL',
                'attempts': 'INTEGER NOT NULL DEFAULT 0',
                'first_attempt': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
                'last_attempt': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
                'locked_until': 'TIMESTAMP WITH TIME ZONE NULL',
                'created_at': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP'
            }
            self.db_manager.create_table('brute_force_attempts', brute_force_schema)
            logger.info("PostgreSQL brute force protection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL for brute force protection: {e}")
            self.db_manager = None
        
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
            logger.error(f"Rate limiting error: {e}")
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
            logger.error(f"Distributed rate limiting error: {e}")
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
            logger.error(f"Rate limit status error: {e}")
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
            logger.error(f"Rate limit reset error: {e}")
            return False
    
    def check_brute_force(self, identifier: str) -> Tuple[bool, Dict]:
        """Check if identifier is locked due to brute force attempts"""
        if self.db_manager is None:
            return False, {'attempts': 0, 'locked_until': None}
        
        try:
            data = self.db_manager.get_brute_force_attempts(identifier)
            attempts = data.get('attempts', 0)
            locked_until = data.get('locked_until')
            
            if attempts >= BRUTE_FORCE_MAX_ATTEMPTS and locked_until:
                # Check if lockout period has expired
                from datetime import datetime
                now = datetime.now(locked_until.tzinfo) if locked_until.tzinfo else datetime.now()
                
                if now < locked_until:
                    remaining_time = int((locked_until - now).total_seconds())
                    return True, {
                        'attempts': attempts,
                        'locked_until': int(locked_until.timestamp()),
                        'remaining_time': remaining_time
                    }
                else:
                    # Lockout expired, clear attempts
                    self.db_manager.clear_brute_force_attempts(identifier)
                    return False, {'attempts': 0, 'locked_until': None}
            
            return False, {'attempts': attempts, 'locked_until': None}
            
        except Exception as e:
            logger.error(f"Brute force check error: {e}")
            return False, {'attempts': 0, 'locked_until': None}
    
    def record_session_expiration(self, identifier: str) -> None:
        """Record session expiration time for grace period in rate limiting"""
        if self.redis_client is None:
            return
        try:
            key = f"session_expiration:{identifier}"
            current_time = int(time.time())
            # Store expiration timestamp, expire after 2 minutes (grace period window)
            self.redis_client.setex(key, 120, current_time)
        except Exception as e:
            logger.error(f"Error recording session expiration: {e}")
    
    def has_recent_session_expiration(self, identifier: str, grace_period: int = 120) -> bool:
        """Check if there was a recent session expiration (within grace period)"""
        if self.redis_client is None:
            return False
        try:
            key = f"session_expiration:{identifier}"
            expiration_time = self.redis_client.get(key)
            if expiration_time:
                expiration_ts = int(expiration_time)
                current_time = int(time.time())
                return (current_time - expiration_ts) <= grace_period
        except Exception as e:
            logger.error(f"Error checking session expiration: {e}")
        return False
    
    def record_failed_attempt(self, identifier: str) -> None:
        """Record a failed authentication attempt"""
        if self.db_manager is None:
            return
        
        try:
            self.db_manager.record_brute_force_attempt(
                identifier, 
                BRUTE_FORCE_MAX_ATTEMPTS, 
                BRUTE_FORCE_LOCKOUT_TIME
            )
        except Exception as e:
            logger.error(f"Failed to record brute force attempt: {e}")
    
    def clear_failed_attempts(self, identifier: str) -> None:
        """Clear failed attempts for successful authentication"""
        if self.db_manager is None:
            return
        
        try:
            self.db_manager.clear_brute_force_attempts(identifier)
        except Exception as e:
            logger.error(f"Failed to clear brute force attempts: {e}")
    
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
        """Sanitize user input - removes dangerous characters including CRLF sequences"""
        if not input_str:
            return ""
        
        # Limit length
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        # CRLF injection prevention - remove CRLF sequences first
        input_str = input_str.replace('\r\n', '').replace('\r', '').replace('\n', '')
        
        # Remove null bytes and control characters (except tab which may be needed for some inputs)
        input_str = ''.join(char for char in input_str if ord(char) >= 32 or char == '\t')
        
        return input_str.strip()
    
    def sanitize_for_header(self, value: str) -> str:
        """Sanitize value for use in HTTP headers to prevent CRLF injection"""
        if not value:
            return ""
        
        # Remove CRLF sequences and other dangerous characters for headers
        sanitized = value.replace('\r\n', '').replace('\r', '').replace('\n', '')
        # Remove any remaining control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        return sanitized.strip()
    
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
    
    def validate_password_policy(self, password: str) -> Tuple[bool, str]:
        """Validate password against security policy"""
        if not password:
            return False, "Password cannot be empty"
        
        # Minimum length requirement
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Check for common weak passwords
        common_passwords = [
            'password', 'password123', 'admin', 'admin123', '12345678',
            'qwerty', 'letmein', 'welcome', 'monkey', '1234567890',
            'password1', '123456', 'admin1234', 'root', 'toor'
        ]
        if password.lower() in common_passwords:
            return False, "Password is too common. Please choose a stronger password"
        
        # Check for complexity (at least one letter and one number)
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            return False, "Password must contain at least one letter and one number"
        
        return True, ""
    
    def validate_redirect_url(self, redirect_url: str, allowed_domains: list = None) -> Tuple[bool, str]:
        """Validate redirect URL to prevent open redirect attacks"""
        if not redirect_url:
            return False, "Redirect URL cannot be empty"
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(redirect_url)
            
            # Relative URLs are safe
            if not parsed.netloc:
                # Check for path traversal attempts
                if '../' in redirect_url or '..\\' in redirect_url:
                    return False, "Invalid redirect URL: path traversal detected"
                return True, ""
            
            # Absolute URLs need domain validation
            if allowed_domains:
                domain = parsed.netloc.lower()
                # Remove port if present
                if ':' in domain:
                    domain = domain.split(':')[0]
                
                # Check if domain is in allowed list
                if not any(domain == allowed.lower() or domain.endswith('.' + allowed.lower()) 
                          for allowed in allowed_domains):
                    return False, f"Redirect URL domain not allowed: {domain}"
            
            # Prevent javascript: and data: schemes
            if parsed.scheme in ['javascript', 'data', 'vbscript']:
                return False, f"Invalid redirect URL scheme: {parsed.scheme}"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error validating redirect URL: {e}")
            return False, "Invalid redirect URL format"

# Global security manager instance
security_manager = SecurityManager()
