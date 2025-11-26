import re, ipaddress
import subprocess
from .Security import execute_wg_command, execute_secure_command


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
    Raises:
        OSError: If directory creation fails
    """
    import os
    import logging

    logger = logging.getLogger('wiregate')

    from ..modules.DashboardConfig import (
        DashboardConfig
    )
    # Get base backup directory
    backup_dir = os.path.join(DashboardConfig.GetConfig("Server", "wg_conf_path")[1], 'WGDashboard_Backup')

    # Create base backup directory if it doesn't exist
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create base backup directory {backup_dir}: {e}")
        raise

    # Create config-specific directory
    config_backup_dir = os.path.join(backup_dir, config_name)
    try:
        os.makedirs(config_backup_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create config backup directory {config_backup_dir}: {e}")
        raise

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

def NormalizeCPSFormat(cps_value: str) -> str:
    """
    Normalize CPS (Custom Protocol Signature) format for I1-I5 fields.
    Converts raw hex values (0x...) to proper CPS tag format (<b 0x...>).
    
    @param cps_value: CPS string to normalize
    @return: Normalized CPS string
    """
    if not cps_value or not cps_value.strip():
        return cps_value
    
    cps_value = cps_value.strip()
    
    # If it's already in CPS tag format (contains <b, <c, <t, <r, etc.), return as-is
    if '<' in cps_value and '>' in cps_value:
        return cps_value
    
    # Check if it's a raw hex value (starts with 0x)
    if cps_value.startswith('0x'):
        # Remove the 0x prefix and wrap in <b 0x...> tag
        hex_content = cps_value[2:]
        # Validate hex content
        if all(c in '0123456789abcdefABCDEF' for c in hex_content):
            return f'<b 0x{hex_content}>'
    
    # If it doesn't match any known format, return as-is
    return cps_value

def ValidateCPSFormat(cps_value: str) -> tuple[bool, str]:
    """
    Validate CPS (Custom Protocol Signature) format for I1-I5 fields
    @param cps_value: CPS string to validate
    @return: Tuple of (is_valid, error_message)
    """
    if not cps_value or cps_value.strip() == "":
        return (True, None)
    
    # Normalize first to handle raw hex values
    normalized = NormalizeCPSFormat(cps_value)
    if normalized != cps_value:
        # If normalization changed the value, it means it was raw hex
        # We'll validate the normalized version
        cps_value = normalized
    
    # Pattern for individual tags
    hex_tag = r'<b\s+0x[0-9a-fA-F]+>'
    counter_tag = r'<c>'
    timestamp_tag = r'<t>'
    random_tag = r'<r\s+(\d+)>'
    random_ascii_tag = r'<rc\s+(\d+)>'  # Random ASCII characters (a-z, A-Z)
    random_digit_tag = r'<rd\s+(\d+)>'  # Random digits (0-9)
    
    # Combined pattern - matches one or more valid tags
    pattern = f'^({hex_tag}|{counter_tag}|{timestamp_tag}|{random_tag}|{random_ascii_tag}|{random_digit_tag})+$'
    
    if not re.match(pattern, cps_value):
        return (False, 'Invalid CPS format. Expected tags like <b 0xHEX>, <c>, <t>, <r LENGTH>, <rc LENGTH>, <rd LENGTH>')
    
    # Validate random length constraints for all variable-length tags
    all_length_tags = re.findall(r'<(?:r|rc|rd)\s+(\d+)>', cps_value)
    for length_str in all_length_tags:
        try:
            length = int(length_str)
            if length <= 0 or length > 1000:
                return (False, f'Random length {length} must be between 1 and 1000')
        except ValueError:
            return (False, f'Invalid length value: {length_str}')
    
    return (True, None)

def ResponseObject(status=True, message=None, data=None):
    """
    FastAPI-compatible response object
    Returns a dict that can be used with StandardResponse model
    """
    return {
        "status": status,
        "message": message,
        "data": data
    }

def convert_response_object_to_dict(response_obj):
    """Convert response object to dict for FastAPI"""
    if isinstance(response_obj, dict):
        return response_obj
    else:
        # Fallback for any other format
        return {"status": False, "message": "Unknown response format", "data": None}
    

