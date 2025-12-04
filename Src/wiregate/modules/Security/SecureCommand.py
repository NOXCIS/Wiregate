"""
Secure command execution module to prevent command injection
"""
import subprocess
import os
import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger('wiregate')

class SecureCommandExecutor:
    """Secure command execution with input validation and sanitization"""
    
    # Allowed commands and their expected arguments
    ALLOWED_COMMANDS = {
        'wg': {
            'allowed_args': ['show', 'set', 'add', 'del', 'genkey', 'genpsk', 'pubkey', 'dump', 'latest-handshakes', 'transfer', 'endpoints'],
            'max_args': 20
        },
        'awg': {
            'allowed_args': ['show', 'set', 'add', 'del', 'genkey', 'genpsk', 'pubkey', 'dump', 'latest-handshakes', 'transfer', 'endpoints'],
            'max_args': 20
        },
        'wg-quick': {
            'allowed_args': ['up', 'down', 'save', 'strip'],
            'max_args': 10
        },
        'awg-quick': {
            'allowed_args': ['up', 'down', 'save', 'strip'],
            'max_args': 10
        },
        'ip': {
            'allowed_args': ['link', 'addr', 'route', 'rule'],
            'max_args': 15
        },
        'iptables': {
            'allowed_args': ['-A', '-D', '-I', '-F', '-L', '-N', '-X', '-P'],
            'max_args': 25
        },
        'tc': {
            'allowed_args': ['qdisc', 'class', 'filter', 'show'],
            'max_args': 20
        },
        'tail': {
            'allowed_args': ['-n', '-f'],
            'max_args': 5
        },
        'head': {
            'allowed_args': ['-n'],
            'max_args': 5
        },
        'grep': {
            'allowed_args': ['-i', '-v', '-E', '-F'],
            'max_args': 10
        },
        'awk': {
            'allowed_args': ['-F', '-v'],
            'max_args': 10
        },
        'sed': {
            'allowed_args': ['-i', '-n', '-e'],
            'max_args': 10
        },
        'chmod': {
            'allowed_args': ['+x', '-x', '755', '644', '600'],
            'max_args': 5
        },
        'chown': {
            'allowed_args': ['root:root', 'nobody:nogroup'],
            'max_args': 5
        },
        'mkdir': {
            'allowed_args': ['-p', '-m'],
            'max_args': 5
        },
        'rm': {
            'allowed_args': ['-f', '-r'],
            'max_args': 5
        },
        'cp': {
            'allowed_args': ['-r', '-p'],
            'max_args': 5
        },
        'mv': {
            'allowed_args': [],
            'max_args': 5
        },
        'ls': {
            'allowed_args': ['-la', '-l', '-a'],
            'max_args': 5
        },
        'cat': {
            'allowed_args': [],
            'max_args': 3
        },
        'echo': {
            'allowed_args': ['-n', '-e'],
            'max_args': 5
        },
        'ps': {
            'allowed_args': ['aux', '-ef'],
            'max_args': 5
        },
        'netstat': {
            'allowed_args': ['-tulpn', '-an'],
            'max_args': 5
        },
        'curl': {
            'allowed_args': ['-s', '-o', '-w', '-H', '-X'],
            'max_args': 15
        },
        'wget': {
            'allowed_args': ['-q', '-O', '-T'],
            'max_args': 10
        },
        'traffic-weir': {
            'allowed_args': ['-interface', '-peer', '-upload-rate', '-download-rate', '-protocol', '-scheduler', '-allowed-ips', '-remove', '-nuke', '--interface', '--peer', '--upload-rate', '--download-rate', '--protocol', '--scheduler', '--allowed-ips', '--remove', '--nuke'],
            'max_args': 15
        },
        'torflux': {
            'allowed_args': ['-config', '-action', '--help', '-h'],
            'max_args': 5
        },
        'udptlspipe': {
            'allowed_args': ['--server', '-s', '-l', '--listen', '-d', '--destination', '-p', '--password', '-x', '--proxy', '--secure', '--tls-servername', '--tls-certfile', '--tls-keyfile', '--probe-reverseproxyurl', '-v', '--verbose', '--help', '-h'],
            'max_args': 20
        }
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        ';', '&&', '||', '|', '`', '$', '$(', '${', '>', '<', '>>', '<<',
        '&', '(', ')', '{', '}', '[', ']', '~', '!', '@', '#', '%', '^',
        '\\', '?', '*', '+', '=', '"', "'", '\n', '\r', '\t'
    ]
    
    def __init__(self):
        self.timeout = 30  # Default timeout in seconds
    
    def validate_command(self, command: str, args: List[str]) -> Tuple[bool, str]:
        """Validate command and arguments for security"""
        if not command or not isinstance(command, str):
            return False, "Invalid command"
        
        # Extract command name from full path for validation
        command_name = os.path.basename(command)
        
        # Check if command is allowed
        if command_name not in self.ALLOWED_COMMANDS:
            return False, f"Command '{command_name}' is not allowed"
        
        # Check argument count
        max_args = self.ALLOWED_COMMANDS[command_name]['max_args']
        if len(args) > max_args:
            return False, f"Too many arguments for command '{command_name}' (max: {max_args})"
        
        # Validate arguments based on command type
        if command_name in ['wg', 'awg']:
            # For wg/awg commands, validate the first argument (subcommand) and allow others
            if args and args[0] not in self.ALLOWED_COMMANDS[command_name]['allowed_args']:
                # Check if it's a valid interface name instead of subcommand
                if not self._is_valid_interface_name(args[0]):
                    return False, f"Invalid subcommand '{args[0]}' for command '{command_name}'"
        elif command_name == 'traffic-weir':
            # For traffic-weir, validate argument names and allow values
            i = 0
            while i < len(args):
                arg = args[i]
                if arg.startswith('-'):
                    # This is an argument name, validate it
                    if arg not in self.ALLOWED_COMMANDS[command_name]['allowed_args']:
                        return False, f"Invalid argument '{arg}' for command '{command_name}'"
                    # Skip the next argument (value) if it exists and it's not another flag
                    if i + 1 < len(args) and not args[i + 1].startswith('-'):
                        i += 1
                else:
                    # This is a value, validate it as safe
                    if not self._is_safe_string(arg):
                        return False, f"Invalid value '{arg}' for command '{command_name}'"
                i += 1
        else:
            # For other commands, validate all arguments
            allowed_args = self.ALLOWED_COMMANDS[command_name]['allowed_args']
            for arg in args:
                if not self._validate_argument(arg, allowed_args):
                    return False, f"Invalid argument '{arg}' for command '{command_name}'"
        
        return True, ""
    
    def _validate_argument(self, arg: str, allowed_args: List[str]) -> bool:
        """Validate individual argument"""
        if not arg or not isinstance(arg, str):
            return False
        
        # Length check
        if len(arg) > 1000:  # Reasonable limit
            return False
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in arg:
                return False
        
        # Check for command injection patterns
        injection_patterns = [
            'rm -rf', 'dd if=', 'mkfs', 'fdisk', 'format', 'del /q', 'shutdown', 'reboot',
            'nc -', 'netcat', 'telnet', 'ssh', 'scp', 'rsync', 'wget', 'curl -X POST',
            'python -c', 'perl -e', 'ruby -e', 'node -e', 'php -r'
        ]
        
        arg_lower = arg.lower()
        for pattern in injection_patterns:
            if pattern in arg_lower:
                return False
        
        # If no specific allowed args, allow basic alphanumeric and common chars
        if not allowed_args:
            return self._is_safe_string(arg)
        
        # Check if argument matches allowed patterns
        for allowed_arg in allowed_args:
            if arg.startswith(allowed_arg) or arg == allowed_arg:
                return True
        
        # Allow file paths and basic values for specific commands
        return self._is_safe_string(arg)
    
    def _is_safe_string(self, s: str) -> bool:
        """Check if string contains only safe characters"""
        if not s:
            return False
        
        # Allow alphanumeric, dots, dashes, underscores, slashes, colons, and spaces
        # Also allow common network characters for IP addresses and ports
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_/:, ')
        
        for char in s:
            if char not in safe_chars:
                return False
        
        # Additional validation for specific patterns
        # Check if it looks like a valid IP address, CIDR, or interface name
        if self._is_valid_network_string(s) or self._is_valid_interface_name(s) or self._is_valid_file_path(s):
            return True
        
        # For other strings, be more restrictive
        return self._is_basic_safe_string(s)
    
    def _is_valid_network_string(self, s: str) -> bool:
        """Check if string looks like valid network configuration"""
        import ipaddress
        try:
            # Try to parse as IP address or network
            ipaddress.ip_address(s)
            return True
        except ValueError:
            try:
                ipaddress.ip_network(s, strict=False)
                return True
            except ValueError:
                pass
        
        # Check for valid hostname format
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$', s):
            return True
        
        return False
    
    def _is_valid_interface_name(self, s: str) -> bool:
        """Check if string looks like valid interface name"""
        # WireGuard and network interface naming conventions
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9]$', s) and len(s) <= 15:
            return True
        return False
    
    def _is_valid_file_path(self, s: str) -> bool:
        """Check if string looks like valid file path"""
        # Basic file path validation
        if re.match(r'^[a-zA-Z0-9._/-]+$', s) and not s.startswith('/etc/passwd') and not s.startswith('/etc/shadow'):
            return True
        return False
    
    def _is_basic_safe_string(self, s: str) -> bool:
        """Basic string safety check"""
        # Only alphanumeric, dots, dashes, underscores
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_')
        return all(char in safe_chars for char in s)
    
    def execute_command(self, command: str, args: List[str] = None, 
                       timeout: int = None, cwd: str = None, stdin_input: str = None) -> Dict[str, Any]:
        """Execute command securely with validation"""
        if args is None:
            args = []
        
        timeout = timeout or self.timeout
        
        # Validate command and arguments
        is_valid, error_msg = self.validate_command(command, args)
        if not is_valid:
            logger.error(f"Command validation failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'returncode': -1,
                'stdout': '',
                'stderr': error_msg
            }
        
        # Build command list
        cmd_list = [command] + args
        
        try:
            # Use restricted shell wrapper for additional security
            # For relative paths, ensure we're in the correct directory
            if command.startswith('./'):
                restricted_cmd = ['/WireGate/restricted_shell.sh'] + cmd_list
                cwd = '/WireGate'  # Set working directory for relative paths
            else:
                restricted_cmd = ['/WireGate/restricted_shell.sh'] + cmd_list
                cwd = cwd  # Use provided cwd or None
            
            if stdin_input:
                result = subprocess.run(
                    restricted_cmd,
                    input=stdin_input,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd,
                    shell=False  # Never use shell=True
                )
            else:
                result = subprocess.run(
                    restricted_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd,
                    shell=False  # Never use shell=True
                )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd_list)
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd_list)}")
            return {
                'success': False,
                'error': 'Command timed out',
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out',
                'command': ' '.join(cmd_list)
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(cmd_list)
            }
    
    def execute_wg_command(self, action: str, interface: str = None, 
                          peer_key: str = None, **kwargs) -> Dict[str, Any]:
        """Execute WireGuard commands safely"""
        args = [action]  # Include the action (e.g., 'show') as the first argument
        
        if action == 'show':
            if interface:
                args.append(interface)
            else:
                args.append('all')
            
            # Add sub-commands for show
            if 'subcommand' in kwargs:
                subcommand = kwargs['subcommand']
                if subcommand in ['latest-handshakes', 'transfer', 'endpoints']:
                    args.append(subcommand)
        
        elif action == 'set':
            if not interface:
                return {'success': False, 'error': 'Interface required for set action'}
            
            args.append(interface)
            
            # Add peer configuration
            if peer_key:
                args.extend(['peer', peer_key])
                
                # Add allowed IPs
                if 'allowed_ips' in kwargs:
                    args.extend(['allowed-ips', kwargs['allowed_ips']])
                
                # Add preshared key if provided
                temp_file = None
                if 'preshared_key' in kwargs and kwargs['preshared_key']:
                    # Write preshared key to temporary file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                        f.write(kwargs['preshared_key'])
                        temp_file = f.name
                    
                    args.extend(['preshared-key', temp_file])
                
                # Add remove command
                if 'remove' in kwargs and kwargs['remove']:
                    args.append('remove')
        
        elif action == 'add':
            if not interface:
                return {'success': False, 'error': 'Interface required for add action'}
            
            args.append(interface)
            args.append('peer')
            
            if peer_key:
                args.append(peer_key)
        
        elif action == 'del':
            if not interface:
                return {'success': False, 'error': 'Interface required for del action'}
            
            args.append(interface)
            args.append('peer')
            
            if peer_key:
                args.append(peer_key)
        
        elif action in ['genkey', 'genpsk', 'pubkey']:
            # These don't need additional args
            pass
        
        else:
            return {'success': False, 'error': f'Unknown WireGuard action: {action}'}
        
        # Execute the command and clean up temp file if needed
        result = self.execute_command('wg', args)
        
        # Clean up temporary file if it was created
        if 'temp_file' in locals() and temp_file:
            try:
                os.unlink(temp_file)
            except OSError as e:
                logger.warning(f"Failed to remove temporary file {temp_file}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error removing temporary file {temp_file}: {e}")
        
        return result
    
    def execute_wg_quick_command(self, action: str, interface: str, **kwargs) -> Dict[str, Any]:
        """Execute wg-quick commands safely"""
        if not interface:
            return {'success': False, 'error': 'Interface required for wg-quick action'}
        
        args = [action, interface]
        
        # Validate action
        if action not in ['up', 'down', 'save', 'strip']:
            return {'success': False, 'error': f'Invalid wg-quick action: {action}'}
        
        return self.execute_command('wg-quick', args)
    
    def execute_ip_command(self, subcommand: str, interface: str = None, **kwargs) -> Dict[str, Any]:
        """Execute ip commands safely"""
        args = []
        
        if subcommand == 'addr_show':
            args.extend(['addr', 'show'])
            if interface:
                args.append(interface)
        
        elif subcommand == 'addr_add':
            if not interface or 'address' not in kwargs:
                return {'success': False, 'error': 'Interface and address required for addr_add'}
            address = kwargs['address']
            # Check if it's an IPv6 address and add -6 flag
            if ':' in address:
                args.extend(['-6', 'addr', 'add', address, 'dev', interface])
            else:
                args.extend(['addr', 'add', address, 'dev', interface])
        
        elif subcommand == 'addr_flush':
            if not interface:
                return {'success': False, 'error': 'Interface required for addr_flush'}
            # Use -6 flag for IPv6 address flushing
            args.extend(['-6', 'addr', 'flush', 'dev', interface])
        
        elif subcommand == 'link_show':
            args.extend(['link', 'show'])
            if interface:
                args.append(interface)
        
        elif subcommand == 'link_stats':
            if not interface:
                return {'success': False, 'error': 'Interface required for link_stats'}
            args.extend(['-s', 'link', 'show', interface])
        
        else:
            return {'success': False, 'error': f'Unknown ip subcommand: {subcommand}'}
        
        return self.execute_command('ip', args)
    
    def execute_awk_command(self, script: str, input_data: str = None) -> Dict[str, Any]:
        """Execute awk commands safely"""
        # Validate awk script for dangerous patterns
        dangerous_patterns = ['system', 'exec', 'getline', 'print', 'printf']
        for pattern in dangerous_patterns:
            if pattern in script.lower():
                return {'success': False, 'error': f'Dangerous awk pattern detected: {pattern}'}
        
        args = [script]
        
        if input_data:
            # Use echo to pipe data to awk
            echo_result = self.execute_command('echo', [input_data])
            if not echo_result['success']:
                return echo_result
            
            # For now, return the echo result as we can't easily pipe in this context
            return echo_result
        
        return self.execute_command('awk', args)
    
    def execute_grep_command(self, pattern: str, file_path: str = None, **kwargs) -> Dict[str, Any]:
        """Execute grep commands safely"""
        args = []
        
        # Add flags
        if kwargs.get('quiet', False):
            args.append('-q')
        
        # Add pattern
        args.append(pattern)
        
        # Add file if provided
        if file_path:
            args.append(file_path)
        
        return self.execute_command('grep', args)
    
    def execute_file_operation(self, operation: str, source: str, 
                             destination: str = None) -> Dict[str, Any]:
        """Execute file operations safely"""
        if operation == 'read':
            return self.execute_command('cat', [source])
        
        elif operation == 'write':
            if not destination:
                return {'success': False, 'error': 'Destination required for write operation'}
            return self.execute_command('cp', [source, destination])
        
        elif operation == 'delete':
            return self.execute_command('rm', ['-f', source])
        
        elif operation == 'chmod':
            if not destination:
                return {'success': False, 'error': 'Mode required for chmod operation'}
            return self.execute_command('chmod', [destination, source])
        
        elif operation == 'mkdir':
            return self.execute_command('mkdir', ['-p', source])
        
        else:
            return {'success': False, 'error': f'Unknown file operation: {operation}'}
    
    def execute_network_command(self, command: str, interface: str = None, 
                               **kwargs) -> Dict[str, Any]:
        """Execute network-related commands safely"""
        args = []
        
        if command == 'ip_link':
            args.extend(['link', 'show'])
            if interface:
                args.append(interface)
        
        elif command == 'ip_addr':
            args.extend(['addr', 'show'])
            if interface:
                args.append(interface)
        
        elif command == 'netstat':
            args.append('-tulpn')
        
        elif command == 'ps':
            args.append('aux')
        
        else:
            return {'success': False, 'error': f'Unknown network command: {command}'}
        
        return self.execute_command('ip' if command.startswith('ip_') else command, args)

# Global secure command executor instance
secure_executor = SecureCommandExecutor()

def execute_secure_command(command: str, args: List[str] = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for secure command execution"""
    return secure_executor.execute_command(command, args, **kwargs)

def execute_wg_command(action: str, interface: str = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for WireGuard command execution"""
    return secure_executor.execute_wg_command(action, interface, **kwargs)

def execute_awg_command(action: str, interface: str = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for AmneziaWG command execution"""
    # Use the same logic as WG commands but with 'awg' command
    args = [action]  # Include the action (e.g., 'show') as the first argument
    
    if action == 'show':
        if interface:
            args.append(interface)
        else:
            args.append('all')
        
        # Add sub-commands for show
        if 'subcommand' in kwargs:
            subcommand = kwargs['subcommand']
            if subcommand in ['transfer', 'latest-handshakes', 'endpoints']:
                args.append(subcommand)
    
    elif action == 'set':
        if not interface:
            return {'success': False, 'error': 'Interface required for awg set'}
        
        args.append(interface)
        
        # Add peer key
        if 'peer_key' in kwargs:
            args.extend(['peer', kwargs['peer_key']])
        
        # Add allowed IPs
        if 'allowed_ips' in kwargs:
            args.extend(['allowed-ips', kwargs['allowed_ips']])
        
        # Add preshared key
        temp_file = None
        if 'preshared_key' in kwargs and kwargs['preshared_key']:
            # Write preshared key to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(kwargs['preshared_key'])
                temp_file = f.name
            
            args.extend(['preshared-key', temp_file])
        
        # Handle remove operation
        if kwargs.get('remove', False):
            args.append('remove')
    
    else:
        return {'success': False, 'error': f'Unknown AmneziaWG action: {action}'}
    
    # Execute the command and clean up temp file if needed
    result = secure_executor.execute_command('awg', args)
    
    # Clean up temporary file if it was created
    if 'temp_file' in locals() and temp_file:
        try:
            os.unlink(temp_file)
        except:
            pass
    
    return result

def execute_file_operation(operation: str, source: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for file operation execution"""
    return secure_executor.execute_file_operation(operation, source, **kwargs)

def execute_wg_quick_command(action: str, interface: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for wg-quick command execution"""
    return secure_executor.execute_wg_quick_command(action, interface, **kwargs)

def execute_awg_quick_command(action: str, interface: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for awg-quick command execution"""
    if not interface:
        return {'success': False, 'error': 'Interface required for awg-quick action'}
    
    args = [action, interface]
    
    # Validate action
    if action not in ['up', 'down', 'save', 'strip']:
        return {'success': False, 'error': f'Invalid awg-quick action: {action}'}
    
    return secure_executor.execute_command('awg-quick', args)

def execute_ip_command(subcommand: str, interface: str = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for ip command execution"""
    return secure_executor.execute_ip_command(subcommand, interface, **kwargs)

def execute_awk_command(script: str, input_data: str = None) -> Dict[str, Any]:
    """Convenience function for awk command execution"""
    return secure_executor.execute_awk_command(script, input_data)

def execute_grep_command(pattern: str, file_path: str = None, **kwargs) -> Dict[str, Any]:
    """Convenience function for grep command execution"""
    return secure_executor.execute_grep_command(pattern, file_path, **kwargs)

