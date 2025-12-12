"""
UdpTlsPipe Server Manager

Manages udptlspipe server processes for TLS piping support.
The server wraps WireGuard UDP traffic in TLS for use in networks where UDP is blocked.

Supports two modes:
1. Per-config mode: Each WireGuard config has its own TLS pipe server on a different port
2. Shared mode: Single TLS pipe server on port 443 with password-based routing

Password storage:
- Passwords are encrypted using Fernet (AES-128-CBC) before storage in the database
- The encryption key is derived from the server's secret key
- Passwords are decrypted only when needed (to pass to udptlspipe process)
"""

import subprocess
import os
import signal
import logging
import threading
import yaml
import tempfile
import base64
import hashlib
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field

# Cryptography for password encryption (Argon2id + ChaCha20-Poly1305)
try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
    
    # Try to import argon2 (preferred) or fall back to PBKDF2
    try:
        import argon2
        from argon2.low_level import hash_secret_raw, Type
        ARGON2_AVAILABLE = True
    except ImportError:
        ARGON2_AVAILABLE = False
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        
except ImportError:
    CRYPTO_AVAILABLE = False
    ARGON2_AVAILABLE = False

logger = logging.getLogger('wiregate')


# ============================================================================
# Password Encryption Helper (Argon2id + ChaCha20-Poly1305)
# ============================================================================

class PasswordEncryption:
    """
    Handles encryption/decryption of TLS pipe passwords using industry-best cryptography.
    
    Security stack (same primitives as WireGuard and Signal):
    - Key Derivation: Argon2id (memory-hard, GPU/ASIC resistant)
      - Falls back to PBKDF2-SHA256 (600k iterations) if argon2 not available
    - Encryption: ChaCha20-Poly1305 (same cipher WireGuard uses)
      - 256-bit key, 96-bit nonce
      - Built-in authentication (AEAD)
      - Constant-time, no timing attacks
      - Faster than AES on devices without AES-NI
    
    Argon2id parameters (OWASP 2023 recommendations):
    - Memory: 64 MiB (65536 KiB)
    - Iterations: 3
    - Parallelism: 4
    
    Format: base64(version[1] + salt[16] + nonce[12] + ciphertext + tag[16])
    - version 0x01 = Argon2id + ChaCha20-Poly1305
    - version 0x02 = PBKDF2 + ChaCha20-Poly1305 (fallback)
    """
    
    _instance = None
    _master_key: Optional[bytes] = None
    
    # Argon2id parameters (OWASP 2023 - "first recommended option")
    ARGON2_TIME_COST = 3          # iterations
    ARGON2_MEMORY_COST = 65536    # 64 MiB in KiB
    ARGON2_PARALLELISM = 4        # threads
    
    # PBKDF2 fallback (if argon2 not available)
    PBKDF2_ITERATIONS = 600_000
    
    # Common parameters
    SALT_SIZE = 16   # 128 bits
    NONCE_SIZE = 12  # 96 bits (ChaCha20-Poly1305 standard)
    KEY_SIZE = 32    # 256 bits
    
    # Version bytes for format identification
    VERSION_ARGON2 = b'\x01'
    VERSION_PBKDF2 = b'\x02'
    
    @classmethod
    def get_instance(cls) -> 'PasswordEncryption':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if not CRYPTO_AVAILABLE:
            logger.warning("cryptography module not available - passwords will be stored in plain text")
            return
        
        # Get or generate master key
        self._master_key = self._get_or_create_master_key()
        if self._master_key:
            kdf_name = "Argon2id" if ARGON2_AVAILABLE else "PBKDF2-SHA256"
            logger.info(f"Password encryption initialized: {kdf_name} + ChaCha20-Poly1305")
    
    def _get_or_create_master_key(self) -> Optional[bytes]:
        """Get master key from environment or derive from server secret"""
        try:
            # Try to get from environment (for advanced deployments)
            env_key = os.environ.get('TLSPIPE_ENCRYPTION_KEY')
            if env_key:
                key_bytes = base64.urlsafe_b64decode(env_key)
                if len(key_bytes) >= 32:
                    return key_bytes[:32]
                logger.warning("TLSPIPE_ENCRYPTION_KEY too short, deriving from secret")
            
            # Get secret key from WG dashboard
            secret_key = os.environ.get('WG_SECRET_KEY', '')
            if not secret_key:
                try:
                    from .DashboardConfig import DashboardConfig
                    secret_key = DashboardConfig.GetConfig("Server", "app_secret")[1]
                except Exception:
                    pass
            
            if not secret_key:
                # Generate a random key if no secret available
                secret_key = os.urandom(32).hex()
                logger.warning("No secret key found, using random key (routes won't persist across restarts)")
            
            # Use the secret as the master key material
            return hashlib.sha256(secret_key.encode()).digest()
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption master key: {e}")
            return None
    
    def _derive_key_argon2(self, salt: bytes) -> bytes:
        """Derive 256-bit key using Argon2id (memory-hard, GPU-resistant)"""
        return hash_secret_raw(
            secret=self._master_key,
            salt=salt,
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=self.KEY_SIZE,
            type=Type.ID  # Argon2id - hybrid of Argon2i and Argon2d
        )
    
    def _derive_key_pbkdf2(self, salt: bytes) -> bytes:
        """Derive 256-bit key using PBKDF2-SHA256 (fallback)"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(self._master_key)
    
    def _derive_key(self, salt: bytes, use_argon2: bool = True) -> bytes:
        """Derive encryption key using best available KDF"""
        if use_argon2 and ARGON2_AVAILABLE:
            return self._derive_key_argon2(salt)
        else:
            return self._derive_key_pbkdf2(salt)
    
    def encrypt(self, password: str) -> str:
        """
        Encrypt a password using ChaCha20-Poly1305 with Argon2id key derivation.
        
        Returns: base64-encoded string containing version + salt + nonce + ciphertext + tag
        """
        if not self._master_key or not CRYPTO_AVAILABLE:
            return password
        
        try:
            # Generate random salt and nonce
            salt = os.urandom(self.SALT_SIZE)
            nonce = os.urandom(self.NONCE_SIZE)
            
            # Derive encryption key
            use_argon2 = ARGON2_AVAILABLE
            key = self._derive_key(salt, use_argon2)
            version = self.VERSION_ARGON2 if use_argon2 else self.VERSION_PBKDF2
            
            # Encrypt with ChaCha20-Poly1305
            chacha = ChaCha20Poly1305(key)
            ciphertext = chacha.encrypt(nonce, password.encode('utf-8'), None)
            
            # Combine: version + salt + nonce + ciphertext (includes 16-byte auth tag)
            encrypted_data = version + salt + nonce + ciphertext
            
            return base64.urlsafe_b64encode(encrypted_data).decode('ascii')
            
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            return password
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a password from base64-encoded ChaCha20-Poly1305 ciphertext.
        
        Format: base64(version[1] + salt[16] + nonce[12] + ciphertext + tag[16])
        """
        if not self._master_key or not CRYPTO_AVAILABLE:
            return encrypted
        
        try:
            # Decode base64
            encrypted_data = base64.urlsafe_b64decode(encrypted.encode('ascii'))
            
            # Check minimum length (version + salt + nonce + at least 1 byte + tag)
            min_length = 1 + self.SALT_SIZE + self.NONCE_SIZE + 1 + 16
            if len(encrypted_data) < min_length:
                logger.debug("Encrypted data too short, assuming plain password")
                return encrypted
            
            # Extract version
            version = encrypted_data[0:1]
            
            # Determine which KDF was used
            if version == self.VERSION_ARGON2:
                use_argon2 = True
            elif version == self.VERSION_PBKDF2:
                use_argon2 = False
            else:
                # Unknown version, try legacy formats
                return self._try_legacy_decrypt(encrypted)
            
            # Extract components (skip version byte)
            salt = encrypted_data[1:1 + self.SALT_SIZE]
            nonce = encrypted_data[1 + self.SALT_SIZE:1 + self.SALT_SIZE + self.NONCE_SIZE]
            ciphertext = encrypted_data[1 + self.SALT_SIZE + self.NONCE_SIZE:]
            
            # Derive decryption key
            key = self._derive_key(salt, use_argon2)
            
            # Decrypt with ChaCha20-Poly1305
            chacha = ChaCha20Poly1305(key)
            plaintext = chacha.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.debug(f"ChaCha20-Poly1305 decryption failed, trying legacy: {e}")
            return self._try_legacy_decrypt(encrypted)
    
    def _try_legacy_decrypt(self, encrypted: str) -> str:
        """Try to decrypt using legacy formats (AES-GCM, Fernet) for migration"""
        # Try AES-256-GCM (previous version)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            encrypted_data = base64.urlsafe_b64decode(encrypted.encode('ascii'))
            # Old format: salt[16] + nonce[12] + ciphertext (no version byte)
            if len(encrypted_data) >= 16 + 12 + 1 + 16:
                salt = encrypted_data[:16]
                nonce = encrypted_data[16:28]
                ciphertext = encrypted_data[28:]
                
                key = self._derive_key_pbkdf2(salt)
                aesgcm = AESGCM(key)
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
                logger.info("Decrypted legacy AES-GCM password, will upgrade on next save")
                return plaintext.decode('utf-8')
        except Exception:
            pass
        
        # Try Fernet (oldest version)
        try:
            from cryptography.fernet import Fernet
            
            if self._master_key:
                fernet_key = base64.urlsafe_b64encode(self._master_key)
                fernet = Fernet(fernet_key)
                encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
                decrypted = fernet.decrypt(encrypted_bytes)
                logger.info("Decrypted legacy Fernet password, will upgrade on next save")
                return decrypted.decode()
        except Exception:
            pass
        
        # Assume plain password
        return encrypted


def get_password_encryption() -> PasswordEncryption:
    """Get the global password encryption instance"""
    return PasswordEncryption.get_instance()


@dataclass
class TlsPipeRoute:
    """A route mapping a password to a WireGuard destination"""
    config_name: str
    password: str
    wireguard_port: int
    
    @property
    def destination(self) -> str:
        return f"127.0.0.1:{self.wireguard_port}"


class SharedUdpTlsPipeServer:
    """
    A shared TLS pipe server that routes to multiple WireGuard configurations
    based on password. This enables using a single port (443) for all TLS piping.
    """
    
    def __init__(self, listen_port: int = 443, tls_server_name: Optional[str] = None,
                 tls_cert_file: Optional[str] = None, tls_key_file: Optional[str] = None):
        self.listen_port = listen_port
        self.tls_server_name = tls_server_name
        self.tls_cert_file = tls_cert_file
        self.tls_key_file = tls_key_file
        self.routes: Dict[str, TlsPipeRoute] = {}  # config_name -> route
        self.process: Optional[subprocess.Popen] = None
        self.config_file_path: Optional[str] = None
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        """Check if the server process is running"""
        with self._lock:
            if self.process is None:
                return False
            return self.process.poll() is None
    
    def add_route(self, config_name: str, password: str, wireguard_port: int) -> Dict[str, Any]:
        """Add a route for a WireGuard configuration"""
        with self._lock:
            route = TlsPipeRoute(
                config_name=config_name,
                password=password,
                wireguard_port=wireguard_port
            )
            self.routes[config_name] = route
            logger.info(f"Added TLS pipe route: {config_name} -> port {wireguard_port}")
            
            # If server is running, restart to apply new config
            if self.process is not None and self.process.poll() is None:
                return self._restart_internal()
            elif len(self.routes) == 1:
                # First route added, start the server
                return self._start_internal()
            
            return {'success': True, 'message': f'Route added for {config_name}'}
    
    def remove_route(self, config_name: str) -> Dict[str, Any]:
        """Remove a route for a WireGuard configuration"""
        with self._lock:
            if config_name not in self.routes:
                return {'success': True, 'message': 'Route not found'}
            
            del self.routes[config_name]
            logger.info(f"Removed TLS pipe route: {config_name}")
            
            if len(self.routes) == 0:
                # No more routes, stop the server
                return self._stop_internal()
            elif self.process is not None and self.process.poll() is None:
                # Restart to apply new config
                return self._restart_internal()
            
            return {'success': True, 'message': f'Route removed for {config_name}'}
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all configured routes"""
        with self._lock:
            return [
                {
                    'config_name': route.config_name,
                    'password': route.password,
                    'wireguard_port': route.wireguard_port,
                    'destination': route.destination
                }
                for route in self.routes.values()
            ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the shared TLS pipe server"""
        with self._lock:
            running = self.process is not None and self.process.poll() is None
            return {
                'running': running,
                'listen_port': self.listen_port,
                'route_count': len(self.routes),
                'routes': [r.config_name for r in self.routes.values()],
                'pid': self.process.pid if running else None
            }
    
    def start(self) -> Dict[str, Any]:
        """Start the shared TLS pipe server"""
        with self._lock:
            return self._start_internal()
    
    def stop(self) -> Dict[str, Any]:
        """Stop the shared TLS pipe server"""
        with self._lock:
            return self._stop_internal()
    
    def _start_internal(self) -> Dict[str, Any]:
        """Internal start method (must be called with lock held)"""
        if self.process is not None and self.process.poll() is None:
            return {'success': False, 'error': 'Server is already running'}
        
        if len(self.routes) == 0:
            return {'success': False, 'error': 'No routes configured'}
        
        try:
            # Generate config file
            self._write_config_file()
            
            # Find binary
            binary_path = self._find_binary()
            
            # Build command
            cmd = [binary_path, '-c', self.config_file_path]
            
            logger.info(f"Starting shared udptlspipe server on port {self.listen_port} with {len(self.routes)} routes")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
            
            logger.info(f"Shared udptlspipe server started with PID {self.process.pid}")
            
            return {
                'success': True,
                'pid': self.process.pid,
                'listen_port': self.listen_port,
                'route_count': len(self.routes)
            }
            
        except FileNotFoundError:
            error_msg = "udptlspipe binary not found"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Failed to start shared udptlspipe server: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _stop_internal(self) -> Dict[str, Any]:
        """Internal stop method (must be called with lock held)"""
        if self.process is None:
            return {'success': True, 'message': 'Server is not running'}
        
        if self.process.poll() is not None:
            self.process = None
            return {'success': True, 'message': 'Server has already stopped'}
        
        try:
            pid = self.process.pid
            logger.info(f"Stopping shared udptlspipe server (PID {pid})")
            
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Server did not terminate gracefully, forcing kill")
                self.process.kill()
                self.process.wait(timeout=2)
            
            self.process = None
            
            # Clean up config file
            if self.config_file_path and os.path.exists(self.config_file_path):
                os.remove(self.config_file_path)
                self.config_file_path = None
            
            logger.info("Shared udptlspipe server stopped")
            return {'success': True, 'pid': pid}
            
        except Exception as e:
            error_msg = f"Failed to stop server: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _restart_internal(self) -> Dict[str, Any]:
        """Internal restart method (must be called with lock held)"""
        self._stop_internal()
        return self._start_internal()
    
    def _write_config_file(self):
        """Write the configuration file for udptlspipe"""
        config = {
            'listen': f'0.0.0.0:{self.listen_port}',
            'routes': [
                {
                    'password': route.password,
                    'destination': route.destination
                }
                for route in self.routes.values()
            ]
        }
        
        if self.tls_server_name:
            config['tls_servername'] = self.tls_server_name
        if self.tls_cert_file:
            config['tls_certfile'] = self.tls_cert_file
        if self.tls_key_file:
            config['tls_keyfile'] = self.tls_key_file
        
        # Write to temp file
        if self.config_file_path is None:
            fd, self.config_file_path = tempfile.mkstemp(suffix='.yaml', prefix='udptlspipe_')
            os.close(fd)
        
        with open(self.config_file_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.debug(f"Wrote config to {self.config_file_path}")
    
    def _find_binary(self) -> str:
        """Find the udptlspipe binary"""
        binary_paths = [
            '/WireGate/udptlspipe',
            '/usr/local/bin/udptlspipe',
            '/usr/bin/udptlspipe',
            'udptlspipe'
        ]
        
        for path in binary_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return 'udptlspipe'


class SharedUdpTlsPipeManager:
    """
    Singleton manager for the shared TLS pipe server.
    Provides a single TLS pipe server on port 443 for all WireGuard configurations.
    
    Routes are persisted to the database with encrypted passwords.
    On initialization, routes are loaded from the database and the server is started
    if there are any enabled routes.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._server: Optional[SharedUdpTlsPipeServer] = None
        self._db = None
        self._initialized = True
        self._encryption = get_password_encryption()
        logger.info("SharedUdpTlsPipeManager initialized")
        
        # Load routes from database on init
        self._load_routes_from_db()
    
    def _get_db(self):
        """Get database manager (lazy initialization)"""
        if self._db is None:
            try:
                from .DataBase.DataBaseManager import get_db_manager_sync
                self._db = get_db_manager_sync()
            except ImportError:
                logger.warning("Could not import database manager")
        return self._db
    
    def _run_async(self, coro):
        """Run an async coroutine synchronously"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new thread to run the coroutine
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)
    
    def _load_routes_from_db(self):
        """Load persisted routes from database on startup"""
        try:
            db = self._get_db()
            if db is None:
                logger.debug("Database not available, skipping route loading")
                return
            
            # Handle async SQLite vs sync PostgreSQL
            routes = None
            if hasattr(db, 'get_all_tlspipe_routes'):
                method = db.get_all_tlspipe_routes
                # Check if it's a coroutine function (async)
                import inspect
                if inspect.iscoroutinefunction(method):
                    routes = self._run_async(method())
                else:
                    routes = method()
            
            if routes:
                logger.info(f"Loading {len(routes)} TLS pipe routes from database")
                server = self.get_or_create_server()
                
                for route_data in routes:
                    config_name = route_data['config_name']
                    password_encrypted = route_data['password_encrypted']
                    wireguard_port = route_data['wireguard_port']
                    
                    # Decrypt password
                    password = self._encryption.decrypt(password_encrypted)
                    
                    # Add to server (internal, doesn't re-save to DB)
                    with server._lock:
                        route = TlsPipeRoute(
                            config_name=config_name,
                            password=password,
                            wireguard_port=wireguard_port
                        )
                        server.routes[config_name] = route
                
                # Start server if we have routes
                if server.routes:
                    server.start()
                    logger.info(f"Started shared TLS pipe server with {len(server.routes)} routes")
        except Exception as e:
            logger.error(f"Failed to load TLS pipe routes from database: {e}")
    
    def _save_route_to_db(self, config_name: str, password: str, wireguard_port: int,
                          tls_server_name: str = None) -> bool:
        """Save a route to the database with encrypted password"""
        try:
            db = self._get_db()
            if db is None:
                logger.warning("Database not available, route will not persist")
                return False
            
            # Encrypt password
            password_encrypted = self._encryption.encrypt(password)
            
            if hasattr(db, 'save_tlspipe_route'):
                method = db.save_tlspipe_route
                import inspect
                if inspect.iscoroutinefunction(method):
                    return self._run_async(method(config_name, password_encrypted, wireguard_port, tls_server_name))
                else:
                    return method(config_name, password_encrypted, wireguard_port, tls_server_name)
            return False
        except Exception as e:
            logger.error(f"Failed to save TLS pipe route to database: {e}")
            return False
    
    def _delete_route_from_db(self, config_name: str) -> bool:
        """Delete a route from the database"""
        try:
            db = self._get_db()
            if db is None:
                return False
            
            if hasattr(db, 'delete_tlspipe_route'):
                method = db.delete_tlspipe_route
                import inspect
                if inspect.iscoroutinefunction(method):
                    return self._run_async(method(config_name))
                else:
                    return method(config_name)
            return False
        except Exception as e:
            logger.error(f"Failed to delete TLS pipe route from database: {e}")
            return False
    
    def get_or_create_server(self, listen_port: int = 443, 
                             tls_server_name: Optional[str] = None,
                             tls_cert_file: Optional[str] = None,
                             tls_key_file: Optional[str] = None) -> SharedUdpTlsPipeServer:
        """Get or create the shared TLS pipe server"""
        if self._server is None:
            self._server = SharedUdpTlsPipeServer(
                listen_port=listen_port,
                tls_server_name=tls_server_name,
                tls_cert_file=tls_cert_file,
                tls_key_file=tls_key_file
            )
        return self._server
    
    def add_route(self, config_name: str, password: str, wireguard_port: int,
                  listen_port: int = 443, tls_server_name: str = None) -> Dict[str, Any]:
        """Add a route to the shared TLS pipe server and persist to database"""
        server = self.get_or_create_server(listen_port=listen_port)
        result = server.add_route(config_name, password, wireguard_port)
        
        if result.get('success'):
            # Persist to database
            self._save_route_to_db(config_name, password, wireguard_port, tls_server_name)
        
        return result
    
    def remove_route(self, config_name: str) -> Dict[str, Any]:
        """Remove a route from the shared TLS pipe server and database"""
        if self._server is None:
            # Still try to remove from database
            self._delete_route_from_db(config_name)
            return {'success': True, 'message': 'No server configured'}
        
        result = self._server.remove_route(config_name)
        
        # Remove from database
        self._delete_route_from_db(config_name)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the shared TLS pipe server"""
        if self._server is None:
            return {'running': False, 'message': 'No server configured'}
        return self._server.get_status()
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all configured routes"""
        if self._server is None:
            return []
        return self._server.get_routes()
    
    def stop(self) -> Dict[str, Any]:
        """Stop the shared TLS pipe server"""
        if self._server is None:
            return {'success': True, 'message': 'No server configured'}
        return self._server.stop()


# Global shared manager instance
_shared_manager: Optional[SharedUdpTlsPipeManager] = None


def get_shared_udptlspipe_manager() -> SharedUdpTlsPipeManager:
    """Get the global SharedUdpTlsPipeManager instance"""
    global _shared_manager
    if _shared_manager is None:
        _shared_manager = SharedUdpTlsPipeManager()
    return _shared_manager


# ============================================================================
# Shared TLS Pipe Server Functions (Single port 443 for all configs)
# ============================================================================

def enable_shared_tlspipe(
    config_name: str,
    password: str,
    wireguard_port: int,
    listen_port: int = 443
) -> Dict[str, Any]:
    """
    Enable TLS piping for a WireGuard configuration using the shared server.
    
    All configurations share a single TLS pipe server on port 443, with
    password-based routing to the appropriate WireGuard interface.
    
    Args:
        config_name: The WireGuard configuration name
        password: Unique password for this configuration (used for routing)
        wireguard_port: The WireGuard listen port to forward to
        listen_port: The TLS pipe listen port (default: 443)
    
    Returns:
        Result dict with success status and details
    """
    manager = get_shared_udptlspipe_manager()
    return manager.add_route(config_name, password, wireguard_port, listen_port)


def disable_shared_tlspipe(config_name: str) -> Dict[str, Any]:
    """
    Disable TLS piping for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
    
    Returns:
        Result dict with success status and details
    """
    manager = get_shared_udptlspipe_manager()
    return manager.remove_route(config_name)


def get_shared_tlspipe_status() -> Dict[str, Any]:
    """
    Get the status of the shared TLS pipe server.
    
    Returns:
        Status dict with running state, port, and configured routes
    """
    manager = get_shared_udptlspipe_manager()
    return manager.get_status()


def get_shared_tlspipe_routes() -> List[Dict[str, Any]]:
    """
    Get all routes configured on the shared TLS pipe server.
    
    Returns:
        List of route configurations
    """
    manager = get_shared_udptlspipe_manager()
    return manager.get_routes()

