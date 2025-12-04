"""
UdpTlsPipe Server Manager

Manages udptlspipe server processes for TLS piping support.
The server wraps WireGuard UDP traffic in TLS for use in networks where UDP is blocked.
"""

import subprocess
import os
import signal
import logging
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger('wiregate')


@dataclass
class UdpTlsPipeServerConfig:
    """Configuration for a udptlspipe server instance"""
    config_name: str
    listen_port: int
    destination: str  # WireGuard endpoint (e.g., "127.0.0.1:51820")
    password: str
    tls_server_name: Optional[str] = None
    tls_cert_file: Optional[str] = None
    tls_key_file: Optional[str] = None
    probe_reverse_proxy_url: Optional[str] = None


class UdpTlsPipeServer:
    """Represents a running udptlspipe server instance"""
    
    def __init__(self, config: UdpTlsPipeServerConfig):
        self.config = config
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
        """Start the udptlspipe server"""
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return {
                    'success': False,
                    'error': 'Server is already running',
                    'pid': self.process.pid
                }
            
            try:
                # Build command arguments
                cmd = self._build_command()
                
                logger.info(f"Starting udptlspipe server for {self.config.config_name}: listening on port {self.config.listen_port}")
                logger.debug(f"Command: {' '.join(cmd)}")
                
                # Start the process
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True  # Detach from parent process group
                )
                
                logger.info(f"udptlspipe server started with PID {self.process.pid}")
                
                return {
                    'success': True,
                    'pid': self.process.pid,
                    'config_name': self.config.config_name,
                    'listen_port': self.config.listen_port
                }
                
            except FileNotFoundError:
                error_msg = "udptlspipe binary not found. Please ensure it's installed."
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
            except Exception as e:
                error_msg = f"Failed to start udptlspipe server: {str(e)}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the udptlspipe server"""
        with self._lock:
            if self.process is None:
                return {'success': True, 'message': 'Server is not running'}
            
            if self.process.poll() is not None:
                self.process = None
                return {'success': True, 'message': 'Server has already stopped'}
            
            try:
                pid = self.process.pid
                logger.info(f"Stopping udptlspipe server (PID {pid}) for {self.config.config_name}")
                
                # Try graceful termination first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning(f"udptlspipe server (PID {pid}) did not terminate gracefully, forcing kill")
                    self.process.kill()
                    self.process.wait(timeout=2)
                
                self.process = None
                logger.info(f"udptlspipe server stopped successfully")
                
                return {'success': True, 'pid': pid}
                
            except Exception as e:
                error_msg = f"Failed to stop udptlspipe server: {str(e)}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
    
    def restart(self) -> Dict[str, Any]:
        """Restart the udptlspipe server"""
        stop_result = self.stop()
        if not stop_result.get('success', False):
            return stop_result
        return self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the udptlspipe server"""
        with self._lock:
            if self.process is None:
                return {
                    'running': False,
                    'config_name': self.config.config_name,
                    'listen_port': self.config.listen_port
                }
            
            poll_result = self.process.poll()
            if poll_result is not None:
                # Process has exited
                return {
                    'running': False,
                    'exit_code': poll_result,
                    'config_name': self.config.config_name,
                    'listen_port': self.config.listen_port
                }
            
            return {
                'running': True,
                'pid': self.process.pid,
                'config_name': self.config.config_name,
                'listen_port': self.config.listen_port
            }
    
    def _build_command(self) -> list:
        """Build the command line arguments for udptlspipe"""
        # Try to find udptlspipe binary
        binary_paths = [
            '/WireGate/udptlspipe',  # Primary location in container
            '/usr/local/bin/udptlspipe',
            '/usr/bin/udptlspipe',
            'udptlspipe'
        ]
        
        binary_path = None
        for path in binary_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                binary_path = path
                break
        
        if binary_path is None:
            # Default to PATH lookup
            binary_path = 'udptlspipe'
        
        cmd = [
            binary_path,
            '--server',
            '-l', f'0.0.0.0:{self.config.listen_port}',
            '-d', self.config.destination,
        ]
        
        # Add password if specified
        if self.config.password:
            cmd.extend(['-p', self.config.password])
        
        # Add TLS server name if specified
        if self.config.tls_server_name:
            cmd.extend(['--tls-servername', self.config.tls_server_name])
        
        # Add TLS certificate files if specified
        if self.config.tls_cert_file:
            cmd.extend(['--tls-certfile', self.config.tls_cert_file])
        if self.config.tls_key_file:
            cmd.extend(['--tls-keyfile', self.config.tls_key_file])
        
        # Add probe reverse proxy URL if specified (for anti-probing)
        if self.config.probe_reverse_proxy_url:
            cmd.extend(['--probe-reverseproxyurl', self.config.probe_reverse_proxy_url])
        
        return cmd


class UdpTlsPipeManager:
    """
    Manages multiple udptlspipe server instances.
    
    Each WireGuard configuration can have its own TLS pipe server.
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
        self._servers: Dict[str, UdpTlsPipeServer] = {}
        self._config_lock = threading.Lock()
        self._initialized = True
        logger.info("UdpTlsPipeManager initialized")
    
    def start_server(self, config: UdpTlsPipeServerConfig) -> Dict[str, Any]:
        """Start a udptlspipe server for a configuration"""
        with self._config_lock:
            config_name = config.config_name
            
            # Check if a server is already running for this config
            if config_name in self._servers:
                existing_server = self._servers[config_name]
                if existing_server.is_running:
                    # Update config and restart if needed
                    if self._config_changed(existing_server.config, config):
                        logger.info(f"Configuration changed for {config_name}, restarting server")
                        existing_server.stop()
                    else:
                        return {
                            'success': True,
                            'message': 'Server already running with same configuration',
                            'pid': existing_server.process.pid if existing_server.process else None
                        }
            
            # Create and start new server
            server = UdpTlsPipeServer(config)
            result = server.start()
            
            if result.get('success'):
                self._servers[config_name] = server
            
            return result
    
    def stop_server(self, config_name: str) -> Dict[str, Any]:
        """Stop the udptlspipe server for a configuration"""
        with self._config_lock:
            if config_name not in self._servers:
                return {'success': True, 'message': 'No server found for this configuration'}
            
            server = self._servers[config_name]
            result = server.stop()
            
            if result.get('success'):
                del self._servers[config_name]
            
            return result
    
    def restart_server(self, config: UdpTlsPipeServerConfig) -> Dict[str, Any]:
        """Restart the udptlspipe server for a configuration"""
        self.stop_server(config.config_name)
        return self.start_server(config)
    
    def get_server_status(self, config_name: str) -> Dict[str, Any]:
        """Get the status of a udptlspipe server"""
        with self._config_lock:
            if config_name not in self._servers:
                return {'running': False, 'config_name': config_name}
            
            return self._servers[config_name].get_status()
    
    def get_all_servers_status(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all udptlspipe servers"""
        with self._config_lock:
            return {
                name: server.get_status()
                for name, server in self._servers.items()
            }
    
    def stop_all_servers(self) -> Dict[str, Any]:
        """Stop all running udptlspipe servers"""
        with self._config_lock:
            results = {}
            for config_name in list(self._servers.keys()):
                results[config_name] = self._servers[config_name].stop()
                del self._servers[config_name]
            return results
    
    def _config_changed(self, old_config: UdpTlsPipeServerConfig, new_config: UdpTlsPipeServerConfig) -> bool:
        """Check if configuration has changed"""
        return (
            old_config.listen_port != new_config.listen_port or
            old_config.destination != new_config.destination or
            old_config.password != new_config.password or
            old_config.tls_server_name != new_config.tls_server_name or
            old_config.tls_cert_file != new_config.tls_cert_file or
            old_config.tls_key_file != new_config.tls_key_file
        )


# Global instance
_manager: Optional[UdpTlsPipeManager] = None


def get_udptlspipe_manager() -> UdpTlsPipeManager:
    """Get the global UdpTlsPipeManager instance"""
    global _manager
    if _manager is None:
        _manager = UdpTlsPipeManager()
    return _manager


def start_udptlspipe_for_config(
    config_name: str,
    listen_port: int,
    wireguard_port: int,
    password: str,
    tls_server_name: Optional[str] = None,
    tls_cert_file: Optional[str] = None,
    tls_key_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to start a udptlspipe server for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
        listen_port: The port for the TLS pipe server to listen on (e.g., 443)
        wireguard_port: The WireGuard listen port to forward to
        password: Authentication password for clients
        tls_server_name: Optional TLS server name for the certificate
        tls_cert_file: Optional path to TLS certificate file
        tls_key_file: Optional path to TLS key file
    
    Returns:
        Result dict with success status and details
    """
    config = UdpTlsPipeServerConfig(
        config_name=config_name,
        listen_port=listen_port,
        destination=f"127.0.0.1:{wireguard_port}",
        password=password,
        tls_server_name=tls_server_name,
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file
    )
    
    manager = get_udptlspipe_manager()
    return manager.start_server(config)


def stop_udptlspipe_for_config(config_name: str) -> Dict[str, Any]:
    """
    Convenience function to stop a udptlspipe server for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
    
    Returns:
        Result dict with success status and details
    """
    manager = get_udptlspipe_manager()
    return manager.stop_server(config_name)


def get_udptlspipe_status(config_name: str) -> Dict[str, Any]:
    """
    Get the status of a udptlspipe server for a WireGuard configuration.
    
    Args:
        config_name: The WireGuard configuration name
    
    Returns:
        Status dict with running state and details
    """
    manager = get_udptlspipe_manager()
    return manager.get_server_status(config_name)

