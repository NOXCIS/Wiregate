import re, ipaddress
import subprocess
from .SecureCommand import execute_wg_command, execute_secure_command


def strToBool(value: str) -> bool:
        return value.lower() in ("yes", "true", "t", "1", 1)



def get_backup_paths(config_name: str, backup_timestamp: str = None) -> dict:
    """
    Get organized backup file paths for a configuration
    Args:
        config_name: Name of the WireGuard configuration
        backup_timestamp: Optional timestamp for specific backup
    Returns:
        Dictionary containing backup paths
    """
    import os

    from ..modules.DashboardConfig import (
        DashboardConfig
    )
    # Get base backup directory
    backup_dir = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')

    # Create config-specific directory
    config_backup_dir = os.path.join(backup_dir, config_name)
    os.makedirs(config_backup_dir, exist_ok=True)

    if backup_timestamp:
        return {
            'base_dir': backup_dir,
            'config_dir': config_backup_dir,
            'conf_file': os.path.join(config_backup_dir, f'{config_name}_{backup_timestamp}.conf'),
            'redis_file': os.path.join(config_backup_dir, f'{config_name}_{backup_timestamp}.redis'),
            'iptables_file': os.path.join(config_backup_dir, f'{config_name}_{backup_timestamp}_iptables.json')
        }
    return {
        'base_dir': backup_dir,
        'config_dir': config_backup_dir
    }


def RegexMatch(regex, text) -> bool:
    """
    Regex Match
    @param regex: Regex patter
    @param text: Text to match
    @return: Boolean indicate if the text match the regex pattern
    """
    pattern = re.compile(regex)
    return pattern.search(text) is not None

def GetRemoteEndpoint() -> str:
    """
    Using socket to determine default interface IP address. Thanks, @NOXICS
    @return: 
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("1.1.1.1", 80))  # Connecting to a public IP
        wgd_remote_endpoint = s.getsockname()[0]
        return str(wgd_remote_endpoint)


def StringToBoolean(value: str):
    """
    Convert string boolean to boolean
    @param value: Boolean value in string came from Configuration file
    @return: Boolean value
    """
    return (value.strip().replace(" ", "").lower() in 
            ("yes", "true", "t", "1", 1))

def ValidateIPAddressesWithRange(ips: str) -> bool:
    s = ips.replace(" ", "").split(",")
    for ip in s:
        try:
            ipaddress.ip_network(ip)
        except ValueError as e:
            return False
    return True

def ValidateIPAddresses(ips) -> bool:
    s = ips.replace(" ", "").split(",")
    for ip in s:
        try:
            ipaddress.ip_address(ip)
        except ValueError as e:
            return False
    return True

def ValidateDNSAddress(addresses) -> tuple[bool, str]:
    s = addresses.replace(" ", "").split(",")
    for address in s:
        if not ValidateIPAddresses(address) and not RegexMatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z]{0,61}[a-z]", address):
            return False, f"{address} does not appear to be an valid DNS address"
    return True, ""

def GenerateWireguardPublicKey(privateKey: str) -> tuple[bool, str] | tuple[bool, None]:
    try:
        # Use secure command execution with stdin input
        result = execute_secure_command('wg', ['pubkey'], stdin_input=privateKey)
        if result['success']:
            return True, result['stdout'].strip('\n')
        else:
            return False, None
    except Exception:
        return False, None
    
def GenerateWireguardPrivateKey() -> tuple[bool, str] | tuple[bool, None]:
    try:
        result = execute_wg_command('genkey')
        if result['success']:
            return True, result['stdout'].strip('\n')
        else:
            return False, None
    except Exception:
        return False, None
    

