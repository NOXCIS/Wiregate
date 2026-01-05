"""
WgTcpTunnel Server Manager

Manages wg-tcp-tunnel server processes for UDP-over-TCP tunneling support.
The server wraps WireGuard UDP traffic in TCP for use in networks where UDP is blocked.

This is a simpler alternative to UdpTlsPipe that doesn't require TLS certificates.
It uses the wg-tcp-tunnel binary which implements the same protocol as the client.

Binary usage:
  wg-tcp-tunnel --src-tcp=0.0.0.0:PORT --dst-udp=127.0.0.1:51820
"""

import subprocess
import os
import logging
import threading
import tempfile
import ipaddress
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger('wiregate')

# Directory to store auto-generated certificates
CERTS_DIR = Path('/var/lib/wiregate/certs/wgtcptunnel')


def generate_self_signed_cert(config_name: str) -> Tuple[str, str]:
    """
    Generate a self-signed certificate and key for the given config.
    Returns tuple of (cert_path, key_path).
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        logger.error("cryptography library not installed. Run: pip install cryptography")
        raise ImportError("cryptography library required for self-signed certificate generation")
    
    # Ensure certs directory exists
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    
    cert_path = CERTS_DIR / f"{config_name}.crt"
    key_path = CERTS_DIR / f"{config_name}.key"
    
    # Check if certs already exist and are still valid
    if cert_path.exists() and key_path.exists():
        try:
            with open(cert_path, 'rb') as f:
                existing_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            # Check if cert expires in more than 30 days
            if existing_cert.not_valid_after_utc > datetime.utcnow() + timedelta(days=30):
                logger.info(f"Using existing self-signed certificate for {config_name}")
                return str(cert_path), str(key_path)
        except Exception as e:
            logger.warning(f"Existing certificate invalid, regenerating: {e}")
    
    logger.info(f"Generating self-signed certificate for {config_name}")
    
    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WireGate"),
        x509.NameAttribute(NameOID.COMMON_NAME, f"wgtcptunnel-{config_name}"),
    ])
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.local"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    
    # Write key to file
    with open(key_path, 'wb') as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    os.chmod(key_path, 0o600)  # Secure the private key
    
    # Write certificate to file
    with open(cert_path, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    logger.info(f"Generated self-signed certificate: {cert_path}")
    return str(cert_path), str(key_path)


@dataclass
class WgTcpTunnelRoute:
    """A route mapping a TCP port to a WireGuard UDP port"""
    config_name: str
    tcp_port: int
    wireguard_port: int
    
    @property
    def destination(self) -> str:
        return f"127.0.0.1:{self.wireguard_port}"


class WgTcpTunnelServer:
    """
    Manages a wg-tcp-tunnel server process that forwards TCP traffic to a WireGuard UDP port.
    
    Environment variables supported:
        MAX_CONNECTIONS: Maximum concurrent TCP connections per UDP source (default: 100)
        MAX_QUEUE_SIZE: Maximum queue size per connection (default: 1000)
    """
    
    # Default configuration values
    DEFAULT_MAX_CONNECTIONS = 100
    DEFAULT_MAX_QUEUE_SIZE = 1000
    
    def __init__(self, tcp_port: int, wireguard_port: int = 51820,
                 max_connections: Optional[int] = None, max_queue_size: Optional[int] = None,
                 use_websocket: bool = False,
                 use_tls: bool = False, tls_cert_path: Optional[str] = None,
                 tls_key_path: Optional[str] = None, tls_ca_path: Optional[str] = None,
                 config_name: Optional[str] = None):
        self.tcp_port = tcp_port
        self.wireguard_port = wireguard_port
        self.max_connections = max_connections
        self.max_queue_size = max_queue_size
        self.use_websocket = use_websocket
        self.config_name = config_name or f"port_{tcp_port}"
        # TLS configuration
        self.use_tls = use_tls
        self.tls_cert_path = tls_cert_path
        self.tls_key_path = tls_key_path
        self.tls_ca_path = tls_ca_path
        self._auto_generated_cert = False  # Track if we auto-generated certs
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        """Check if the server process is running"""
        with self._lock:
            if self.process is None:
                return False
            return self.process.poll() is None
    
    def start(self) -> Dict[str, Any]:
        """Start the wg-tcp-tunnel server"""
        with self._lock:
            return self._start_internal()
    
    def stop(self) -> Dict[str, Any]:
        """Stop the wg-tcp-tunnel server"""
        with self._lock:
            return self._stop_internal()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the server"""
        with self._lock:
            running = self.process is not None and self.process.poll() is None
            return {
                'running': running,
                'tcp_port': self.tcp_port,
                'wireguard_port': self.wireguard_port,
                'max_connections': self.max_connections or self.DEFAULT_MAX_CONNECTIONS,
                'max_queue_size': self.max_queue_size or self.DEFAULT_MAX_QUEUE_SIZE,
                'use_websocket': self.use_websocket,
                'use_tls': self.use_tls,
                'tls_cert_path': self.tls_cert_path,
                'tls_key_path': self.tls_key_path,
                'tls_ca_path': self.tls_ca_path,
                'pid': self.process.pid if running else None
            }
    
    def _start_internal(self) -> Dict[str, Any]:
        """Internal start method (must be called with lock held)"""
        if self.process is not None and self.process.poll() is None:
            return {'success': False, 'error': 'Server is already running'}
        
        try:
            # Find binary
            binary_path = self._find_binary()
            
            # Build command
            # wg-tcp-tunnel uses -T for src-tcp and -u for dst-udp
            cmd = [
                binary_path,
                '-T', f'0.0.0.0:{self.tcp_port}',
                '-u', f'127.0.0.1:{self.wireguard_port}'
            ]
            
            # Add WebSocket transport mode flag if enabled
            if self.use_websocket:
                cmd.append('--web-socket')
            
            # Add TLS flags if enabled
            if self.use_tls:
                cmd.append('--tls')
                
                # Auto-generate self-signed certificate if none provided
                if not self.tls_cert_path or not self.tls_key_path:
                    logger.info(f"No TLS certificate provided for {self.config_name}, generating self-signed certificate...")
                    try:
                        self.tls_cert_path, self.tls_key_path = generate_self_signed_cert(self.config_name)
                        self._auto_generated_cert = True
                        logger.info(f"Using auto-generated self-signed certificate: {self.tls_cert_path}")
                    except Exception as e:
                        error_msg = f"Failed to generate self-signed certificate: {e}"
                        logger.error(error_msg)
                        return {'success': False, 'error': error_msg}
                
                cmd.extend(['--tls-cert', self.tls_cert_path])
                cmd.extend(['--tls-key', self.tls_key_path])
                if self.tls_ca_path:
                    cmd.extend(['--tls-ca', self.tls_ca_path])
            
            # Build environment with connection management settings
            # wg-tcp-tunnel reads MAX_CONNECTIONS and MAX_QUEUE_SIZE from environment
            env = os.environ.copy()
            
            max_conn = self.max_connections or self.DEFAULT_MAX_CONNECTIONS
            max_queue = self.max_queue_size or self.DEFAULT_MAX_QUEUE_SIZE
            
            env['MAX_CONNECTIONS'] = str(max_conn)
            env['MAX_QUEUE_SIZE'] = str(max_queue)
            
            logger.info(f"Starting wg-tcp-tunnel server: TCP port {self.tcp_port} -> UDP port {self.wireguard_port} (websocket: {self.use_websocket}, tls: {self.use_tls})")
            logger.info(f"Connection limits: max_connections={max_conn}, max_queue_size={max_queue}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Start process with environment variables
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=env,
                start_new_session=True
            )
            
            logger.info(f"wg-tcp-tunnel server started with PID {self.process.pid}")
            
            return {
                'success': True,
                'pid': self.process.pid,
                'tcp_port': self.tcp_port,
                'wireguard_port': self.wireguard_port,
                'max_connections': max_conn,
                'max_queue_size': max_queue
            }
            
        except FileNotFoundError:
            error_msg = "wg-tcp-tunnel binary not found"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Failed to start wg-tcp-tunnel server: {str(e)}"
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
            logger.info(f"Stopping wg-tcp-tunnel server (PID {pid})")
            
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Server did not terminate gracefully, forcing kill")
                self.process.kill()
                self.process.wait(timeout=2)
            
            self.process = None
            
            logger.info("wg-tcp-tunnel server stopped")
            return {'success': True, 'pid': pid}
            
        except Exception as e:
            error_msg = f"Failed to stop server: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _find_binary(self) -> str:
        """Find the wg-tcp-tunnel binary"""
        binary_paths = [
            '/WireGate/wg-tcp-tunnel',
            '/usr/local/bin/wg-tcp-tunnel',
            '/usr/bin/wg-tcp-tunnel',
            'wg-tcp-tunnel'
        ]
        
        for path in binary_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return 'wg-tcp-tunnel'


class WgTcpTunnelManager:
    """
    Singleton manager for wg-tcp-tunnel servers.
    Manages one server per WireGuard configuration.
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
        self._servers: Dict[str, WgTcpTunnelServer] = {}  # config_name -> server
        self._routes: Dict[str, WgTcpTunnelRoute] = {}  # config_name -> route
        self._db = None
        self._initialized = True
        logger.info("WgTcpTunnelManager initialized")
        
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
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def _load_routes_from_db(self):
        """Load persisted routes from database on startup"""
        try:
            db = self._get_db()
            if db is None:
                logger.debug("Database not available, skipping route loading")
                return
            
            routes = None
            if hasattr(db, 'get_all_wgtcptunnel_routes'):
                method = db.get_all_wgtcptunnel_routes
                import inspect
                if inspect.iscoroutinefunction(method):
                    routes = self._run_async(method())
                else:
                    routes = method()
            
            if routes:
                logger.info(f"Loading {len(routes)} wg-tcp-tunnel routes from database")
                
                for route_data in routes:
                    config_name = route_data['config_name']
                    tcp_port = route_data['tcp_port']
                    wireguard_port = route_data['wireguard_port']
                    # Load additional settings from database
                    use_websocket = bool(route_data.get('use_websocket', 0))
                    max_connections = route_data.get('max_connections')
                    max_queue_size = route_data.get('max_queue_size')
                    # Load TLS settings from database
                    use_tls = bool(route_data.get('use_tls', 0))
                    tls_cert_path = route_data.get('tls_cert_path')
                    tls_key_path = route_data.get('tls_key_path')
                    tls_ca_path = route_data.get('tls_ca_path')
                    
                    # Create route and server with all settings
                    route = WgTcpTunnelRoute(
                        config_name=config_name,
                        tcp_port=tcp_port,
                        wireguard_port=wireguard_port
                    )
                    self._routes[config_name] = route
                    
                    server = WgTcpTunnelServer(
                        tcp_port, wireguard_port,
                        max_connections=max_connections,
                        max_queue_size=max_queue_size,
                        use_websocket=use_websocket,
                        use_tls=use_tls,
                        tls_cert_path=tls_cert_path,
                        tls_key_path=tls_key_path,
                        tls_ca_path=tls_ca_path,
                        config_name=config_name
                    )
                    self._servers[config_name] = server
                    start_result = server.start()
                    
                    # If server started successfully and TLS is enabled, save any auto-generated certificate paths
                    if start_result.get('success') and use_tls:
                        # Check if certificates were auto-generated (paths changed from None to actual paths)
                        if server.tls_cert_path and server.tls_key_path and (not tls_cert_path or not tls_key_path):
                            # Auto-generated certificates were created, save them to database
                            self._save_route_to_db(
                                config_name, tcp_port, wireguard_port,
                                use_websocket, max_connections, max_queue_size,
                                use_tls, server.tls_cert_path, server.tls_key_path, server.tls_ca_path
                            )
                            logger.info(f"Saved auto-generated certificate paths to database for {config_name}")
                    
                    logger.info(f"Loaded route {config_name}: TCP {tcp_port} -> WG {wireguard_port} (websocket={use_websocket}, tls={use_tls})")
                    
                logger.info(f"Started {len(self._servers)} wg-tcp-tunnel servers")
        except Exception as e:
            logger.error(f"Failed to load wg-tcp-tunnel routes from database: {e}")
    
    def _save_route_to_db(self, config_name: str, tcp_port: int, wireguard_port: int,
                          use_websocket: bool = False, max_connections: int = None, 
                          max_queue_size: int = None,
                          use_tls: bool = False, tls_cert_path: str = None,
                          tls_key_path: str = None, tls_ca_path: str = None) -> bool:
        """Save a route to the database with all settings"""
        try:
            db = self._get_db()
            if db is None:
                logger.warning("Database not available, route will not persist")
                return False
            
            if hasattr(db, 'save_wgtcptunnel_route'):
                method = db.save_wgtcptunnel_route
                import inspect
                if inspect.iscoroutinefunction(method):
                    return self._run_async(method(
                        config_name, tcp_port, wireguard_port, 
                        use_websocket, max_connections, max_queue_size,
                        use_tls, tls_cert_path, tls_key_path, tls_ca_path
                    ))
                else:
                    return method(
                        config_name, tcp_port, wireguard_port,
                        use_websocket, max_connections, max_queue_size,
                        use_tls, tls_cert_path, tls_key_path, tls_ca_path
                    )
            return False
        except Exception as e:
            logger.error(f"Failed to save wg-tcp-tunnel route to database: {e}")
            return False
    
    def _delete_route_from_db(self, config_name: str) -> bool:
        """Delete a route from the database"""
        try:
            db = self._get_db()
            if db is None:
                return False
            
            if hasattr(db, 'delete_wgtcptunnel_route'):
                method = db.delete_wgtcptunnel_route
                import inspect
                if inspect.iscoroutinefunction(method):
                    return self._run_async(method(config_name))
                else:
                    return method(config_name)
            return False
        except Exception as e:
            logger.error(f"Failed to delete wg-tcp-tunnel route from database: {e}")
            return False
    
    def enable(self, config_name: str, tcp_port: int, wireguard_port: int = 51820,
                max_connections: Optional[int] = None, max_queue_size: Optional[int] = None,
                use_websocket: bool = False,
                use_tls: bool = False, tls_cert_path: Optional[str] = None,
                tls_key_path: Optional[str] = None, tls_ca_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Enable wg-tcp-tunnel for a WireGuard configuration.
        
        Args:
            config_name: The WireGuard configuration name
            tcp_port: The TCP port to listen on
            wireguard_port: The WireGuard UDP port to forward to (default: 51820)
            max_connections: Maximum concurrent TCP connections per UDP source (default: 100)
            max_queue_size: Maximum queue size per connection (default: 1000)
            use_websocket: Enable WebSocket transport mode (default: False)
            use_tls: Enable TLS encryption (default: False)
            tls_cert_path: Path to TLS certificate file (optional, auto-generated if not provided)
            tls_key_path: Path to TLS private key file (optional, auto-generated if not provided)
            tls_ca_path: Path to CA certificate file for client verification (optional)
        
        Returns:
            Result dict with success status and details
        """
        # Validate TLS configuration - only check if paths are provided
        if use_tls:
            # If cert/key paths are provided, verify they exist
            if tls_cert_path and not os.path.isfile(tls_cert_path):
                return {'success': False, 'error': f'TLS certificate file not found: {tls_cert_path}'}
            if tls_key_path and not os.path.isfile(tls_key_path):
                return {'success': False, 'error': f'TLS key file not found: {tls_key_path}'}
            if tls_ca_path and not os.path.isfile(tls_ca_path):
                return {'success': False, 'error': f'TLS CA file not found: {tls_ca_path}'}
            # Note: If no cert/key paths provided, server will auto-generate self-signed certificate
        
        with self._lock:
            # Stop existing server if any
            if config_name in self._servers:
                self._servers[config_name].stop()
            
            # Create new route and server
            route = WgTcpTunnelRoute(
                config_name=config_name,
                tcp_port=tcp_port,
                wireguard_port=wireguard_port
            )
            self._routes[config_name] = route
            
            server = WgTcpTunnelServer(
                tcp_port, wireguard_port,
                max_connections=max_connections,
                max_queue_size=max_queue_size,
                use_websocket=use_websocket,
                use_tls=use_tls,
                tls_cert_path=tls_cert_path,
                tls_key_path=tls_key_path,
                tls_ca_path=tls_ca_path,
                config_name=config_name
            )
            self._servers[config_name] = server
            
            result = server.start()
            
            if result.get('success'):
                # Save route with all settings to database for persistence
                # Use the server's actual paths (which may have been auto-generated)
                actual_cert_path = server.tls_cert_path
                actual_key_path = server.tls_key_path
                actual_ca_path = server.tls_ca_path
                
                self._save_route_to_db(
                    config_name, tcp_port, wireguard_port,
                    use_websocket, max_connections, max_queue_size,
                    use_tls, actual_cert_path, actual_key_path, actual_ca_path
                )
                logger.info(f"Saved TCP tunnel route to database: {config_name} (TLS: {use_tls}, cert: {actual_cert_path})")
            
            return result
    
    def disable(self, config_name: str) -> Dict[str, Any]:
        """
        Disable wg-tcp-tunnel for a WireGuard configuration.
        
        Args:
            config_name: The WireGuard configuration name
        
        Returns:
            Result dict with success status and details
        """
        with self._lock:
            if config_name not in self._servers:
                self._delete_route_from_db(config_name)
                return {'success': True, 'message': 'No server configured'}
            
            server = self._servers.pop(config_name)
            self._routes.pop(config_name, None)
            
            result = server.stop()
            self._delete_route_from_db(config_name)
            
            return result
    
    def get_status(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of wg-tcp-tunnel server(s).
        
        Args:
            config_name: Optional config name. If None, returns all statuses.
        
        Returns:
            Status dict
        """
        with self._lock:
            if config_name:
                if config_name not in self._servers:
                    return {'running': False, 'message': 'No server configured'}
                return self._servers[config_name].get_status()
            
            running_count = sum(1 for server in self._servers.values() if server.is_running)
            return {
                'servers': {
                    name: server.get_status()
                    for name, server in self._servers.items()
                },
                'count': len(self._servers),
                'route_count': len(self._routes),
                'running_count': running_count
            }
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all configured routes"""
        with self._lock:
            return [
                {
                    'config_name': route.config_name,
                    'tcp_port': route.tcp_port,
                    'wireguard_port': route.wireguard_port,
                    'running': self._servers[route.config_name].is_running if route.config_name in self._servers else False
                }
                for route in self._routes.values()
            ]
    
    def get_route(self, config_name: str) -> Optional[WgTcpTunnelRoute]:
        """Get the route for a specific configuration"""
        with self._lock:
            return self._routes.get(config_name)
    
    def get_server(self, config_name: str) -> Optional[WgTcpTunnelServer]:
        """Get the server for a specific configuration"""
        with self._lock:
            return self._servers.get(config_name)
    
    def stop_all(self) -> Dict[str, Any]:
        """Stop all wg-tcp-tunnel servers"""
        with self._lock:
            results = {}
            for name, server in self._servers.items():
                results[name] = server.stop()
            return results


# Global manager instance
_manager: Optional[WgTcpTunnelManager] = None


def get_wgtcptunnel_manager() -> WgTcpTunnelManager:
    """Get the global WgTcpTunnelManager instance"""
    global _manager
    if _manager is None:
        _manager = WgTcpTunnelManager()
    return _manager


# ============================================================================
# Convenience Functions
# ============================================================================

def enable_wgtcptunnel(
    config_name: str,
    tcp_port: int,
    wireguard_port: int = 51820,
    max_connections: Optional[int] = None,
    max_queue_size: Optional[int] = None,
    use_websocket: bool = False,
    use_tls: bool = False,
    tls_cert_path: Optional[str] = None,
    tls_key_path: Optional[str] = None,
    tls_ca_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enable wg-tcp-tunnel for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
        tcp_port: The TCP port to listen on
        wireguard_port: The WireGuard UDP port to forward to (default: 51820)
        max_connections: Maximum concurrent TCP connections per UDP source (default: 100)
        max_queue_size: Maximum queue size per connection (default: 1000)
        use_websocket: Enable WebSocket transport mode (default: False)
        use_tls: Enable TLS encryption (default: False)
        tls_cert_path: Path to TLS certificate file (required if use_tls is True)
        tls_key_path: Path to TLS private key file (required if use_tls is True)
        tls_ca_path: Path to CA certificate file for client verification (optional)
    
    Returns:
        Result dict with success status and details
    """
    manager = get_wgtcptunnel_manager()
    return manager.enable(
        config_name, tcp_port, wireguard_port, 
        max_connections, max_queue_size, use_websocket,
        use_tls, tls_cert_path, tls_key_path, tls_ca_path
    )


def disable_wgtcptunnel(config_name: str) -> Dict[str, Any]:
    """
    Disable wg-tcp-tunnel for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
    
    Returns:
        Result dict with success status and details
    """
    manager = get_wgtcptunnel_manager()
    return manager.disable(config_name)


def get_wgtcptunnel_status(config_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the status of wg-tcp-tunnel server(s).
    
    Args:
        config_name: Optional config name. If None, returns all statuses.
    
    Returns:
        Status dict
    """
    manager = get_wgtcptunnel_manager()
    return manager.get_status(config_name)


def get_wgtcptunnel_routes() -> List[Dict[str, Any]]:
    """
    Get all configured wg-tcp-tunnel routes.
    
    Returns:
        List of route configurations
    """
    manager = get_wgtcptunnel_manager()
    return manager.get_routes()

