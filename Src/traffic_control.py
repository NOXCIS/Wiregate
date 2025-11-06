"""
Traffic Control Module for Wiregate
Provides Python wrapper for Linux tc (traffic control) commands
Supports CAKE (Common Applications Kept Enhanced) qdisc configuration
"""

import subprocess
import logging
import json
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TrafficControlError(Exception):
    """Custom exception for traffic control operations"""
    pass


class CAKEQdisc:
    """
    CAKE (Common Applications Kept Enhanced) qdisc manager

    CAKE is a comprehensive queue management system that aims to replace
    traditional traffic shapers like HTB + fq_codel with better performance
    and less configuration complexity.

    Key Features:
    - Automatic burst handling (no token bucket issues)
    - Triple-isolate mode for fair queuing through NAT
    - Built-in ACK filtering and GSO packet splitting
    - Automatic rate adaptation for ingress traffic
    """

    # Valid CAKE options
    VALID_OPTIONS = [
        'besteffort', 'precedence', 'diffserv8', 'diffserv4', 'diffserv3',
        'nat', 'nonat', 'wash', 'nowash', 'split-gso', 'no-split-gso',
        'ack-filter', 'ack-filter-aggressive', 'no-ack-filter',
        'memlimit', 'ptm', 'atm', 'noatm', 'raw', 'conservative',
        'rtt-scaling', 'no-rtt-scaling', 'dual-srchost', 'dual-dsthost',
        'triple-isolate', 'flows', 'autorate-ingress', 'ingress',
        'ethernet', 'docsis', 'pppoe-ptm', 'pppoe-vcmux', 'bridged-ptm'
    ]

    # Default CAKE configuration
    DEFAULT_CONFIG = {
        'bandwidth': '1gbit',
        'overhead': 0,
        'mpu': 0,
        'memlimit': '32m',
        'options': ['besteffort', 'triple-isolate', 'nat', 'nowash', 'split-gso']
    }

    @staticmethod
    def is_available() -> bool:
        """
        Check if CAKE qdisc is available in the kernel

        Returns:
            bool: True if CAKE is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['tc', 'qdisc', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Check if tc command works
            if result.returncode != 0:
                logger.warning("tc command not available")
                return False

            # Try to get CAKE help (will succeed if module is loaded)
            result = subprocess.run(
                ['tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'cake', 'help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # CAKE help returns non-zero but outputs help text if available
            return 'cake' in result.stderr.lower() or 'cake' in result.stdout.lower()
        except Exception as e:
            logger.warning(f"Error checking CAKE availability: {e}")
            return False

    @staticmethod
    def validate_bandwidth(bandwidth: str) -> bool:
        """
        Validate bandwidth parameter format

        Args:
            bandwidth: Bandwidth string (e.g., '100mbit', '1gbit', '50000kbit')

        Returns:
            bool: True if valid format
        """
        # Pattern: number followed by bit/kbit/mbit/gbit (case insensitive)
        pattern = r'^\d+(\.\d+)?(bit|kbit|mbit|gbit)$'
        return bool(re.match(pattern, bandwidth.lower()))

    @staticmethod
    def validate_options(options: List[str]) -> Tuple[bool, str]:
        """
        Validate CAKE options

        Args:
            options: List of CAKE option strings

        Returns:
            Tuple of (is_valid, error_message)
        """
        for option in options:
            base_option = option.split()[0]  # Handle options with values like 'memlimit 32m'
            if base_option not in CAKEQdisc.VALID_OPTIONS:
                return False, f"Invalid CAKE option: {base_option}"
        return True, ""

    @staticmethod
    def apply(interface: str, bandwidth: str = '1gbit',
              overhead: int = 0, mpu: int = 0,
              options: Optional[List[str]] = None,
              memlimit: str = '32m') -> bool:
        """
        Apply CAKE qdisc to a network interface

        Args:
            interface: Network interface name (e.g., 'MEMBERS', 'eth0')
            bandwidth: Bandwidth limit (e.g., '100mbit', '1gbit')
            overhead: Bytes to add to each packet (default: 0)
            mpu: Minimum packet unit (default: 0)
            options: List of CAKE options (default: besteffort, triple-isolate, nat, nowash, split-gso)
            memlimit: Memory limit for queues (default: '32m')

        Returns:
            bool: True if successful

        Raises:
            TrafficControlError: If operation fails
        """
        # Validate inputs
        if not CAKEQdisc.validate_bandwidth(bandwidth):
            raise TrafficControlError(f"Invalid bandwidth format: {bandwidth}")

        if overhead < -64 or overhead > 256:
            raise TrafficControlError(f"Overhead must be between -64 and 256, got {overhead}")

        if mpu < 0 or mpu > 256:
            raise TrafficControlError(f"MPU must be between 0 and 256, got {mpu}")

        # Use default options if none provided
        if options is None:
            options = CAKEQdisc.DEFAULT_CONFIG['options']

        # Validate options
        valid, error = CAKEQdisc.validate_options(options)
        if not valid:
            raise TrafficControlError(error)

        # Remove any existing qdisc first (ignore errors)
        try:
            CAKEQdisc.remove(interface)
        except TrafficControlError:
            pass  # Interface may not have qdisc yet

        # Build tc command
        cmd = [
            'tc', 'qdisc', 'add', 'dev', interface, 'root', 'cake',
            'bandwidth', bandwidth,
            'overhead', str(overhead),
            'mpu', str(mpu),
            'memlimit', memlimit
        ]

        # Add additional options
        cmd.extend(options)

        logger.info(f"Applying CAKE qdisc to {interface}: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            logger.info(f"CAKE qdisc applied successfully to {interface}")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to apply CAKE qdisc to {interface}: {e.stderr}"
            logger.error(error_msg)
            raise TrafficControlError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout applying CAKE qdisc to {interface}"
            logger.error(error_msg)
            raise TrafficControlError(error_msg)

    @staticmethod
    def remove(interface: str) -> bool:
        """
        Remove qdisc from network interface

        Args:
            interface: Network interface name

        Returns:
            bool: True if successful

        Raises:
            TrafficControlError: If operation fails
        """
        cmd = ['tc', 'qdisc', 'del', 'dev', interface, 'root']

        logger.info(f"Removing qdisc from {interface}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            logger.info(f"Qdisc removed successfully from {interface}")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to remove qdisc from {interface}: {e.stderr}"
            logger.error(error_msg)
            raise TrafficControlError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout removing qdisc from {interface}"
            logger.error(error_msg)
            raise TrafficControlError(error_msg)

    @staticmethod
    def get_stats(interface: str) -> Optional[Dict]:
        """
        Get CAKE qdisc statistics for an interface

        Args:
            interface: Network interface name

        Returns:
            Dictionary with statistics, or None if not found
        """
        cmd = ['tc', '-s', 'qdisc', 'show', 'dev', interface]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )

            output = result.stdout

            # Parse tc output to extract CAKE stats
            if 'cake' not in output.lower():
                return None

            stats = {
                'interface': interface,
                'raw_output': output,
                'qdisc_type': 'cake',
                'parsed': {}
            }

            # Extract key metrics using regex
            # Example line: "Sent 12345 bytes 100 pkt (dropped 5, overlimits 10 requeues 0)"
            sent_match = re.search(r'Sent (\d+) bytes (\d+) pkt', output)
            if sent_match:
                stats['parsed']['bytes_sent'] = int(sent_match.group(1))
                stats['parsed']['packets_sent'] = int(sent_match.group(2))

            dropped_match = re.search(r'dropped (\d+)', output)
            if dropped_match:
                stats['parsed']['dropped'] = int(dropped_match.group(1))

            overlimits_match = re.search(r'overlimits (\d+)', output)
            if overlimits_match:
                stats['parsed']['overlimits'] = int(overlimits_match.group(1))

            # Extract bandwidth
            bandwidth_match = re.search(r'bandwidth (\S+)', output)
            if bandwidth_match:
                stats['parsed']['bandwidth'] = bandwidth_match.group(1)

            return stats
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get stats for {interface}: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Error getting stats for {interface}: {e}")
            return None

    @staticmethod
    def get_status(interface: str) -> str:
        """
        Get qdisc status for an interface

        Args:
            interface: Network interface name

        Returns:
            Status string: 'cake', 'other', or 'none'
        """
        cmd = ['tc', 'qdisc', 'show', 'dev', interface]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )

            output = result.stdout.lower()

            if 'cake' in output:
                return 'cake'
            elif 'qdisc' in output and output.strip():
                return 'other'
            else:
                return 'none'
        except subprocess.CalledProcessError:
            return 'error'
        except Exception as e:
            logger.error(f"Error getting status for {interface}: {e}")
            return 'error'


class TrafficControl:
    """
    High-level traffic control manager for Wiregate
    Integrates CAKE qdisc with WireGuard configurations
    """

    # Zone-specific default bandwidth limits
    ZONE_DEFAULTS = {
        'ADMINS': '1gbit',
        'MEMBERS': '100mbit',
        'GUESTS': '50mbit',
        'LANP2P': '100mbit'
    }

    @staticmethod
    def apply_zone_shaping(zone_name: str, bandwidth: Optional[str] = None,
                          custom_options: Optional[List[str]] = None) -> bool:
        """
        Apply traffic shaping to a WireGuard zone

        Args:
            zone_name: WireGuard zone/interface name (e.g., 'ADMINS', 'MEMBERS')
            bandwidth: Bandwidth limit (defaults to zone-specific value)
            custom_options: Custom CAKE options (defaults to standard options)

        Returns:
            bool: True if successful
        """
        # Use zone default if bandwidth not specified
        if bandwidth is None:
            bandwidth = TrafficControl.ZONE_DEFAULTS.get(zone_name, '100mbit')

        logger.info(f"Applying traffic shaping to zone {zone_name} with bandwidth {bandwidth}")

        try:
            return CAKEQdisc.apply(
                interface=zone_name,
                bandwidth=bandwidth,
                options=custom_options
            )
        except TrafficControlError as e:
            logger.error(f"Failed to apply shaping to {zone_name}: {e}")
            return False

    @staticmethod
    def remove_zone_shaping(zone_name: str) -> bool:
        """
        Remove traffic shaping from a WireGuard zone

        Args:
            zone_name: WireGuard zone/interface name

        Returns:
            bool: True if successful
        """
        logger.info(f"Removing traffic shaping from zone {zone_name}")

        try:
            return CAKEQdisc.remove(zone_name)
        except TrafficControlError as e:
            logger.error(f"Failed to remove shaping from {zone_name}: {e}")
            return False

    @staticmethod
    def get_zone_stats(zone_name: str) -> Optional[Dict]:
        """
        Get traffic shaping statistics for a zone

        Args:
            zone_name: WireGuard zone/interface name

        Returns:
            Dictionary with statistics, or None if not found
        """
        return CAKEQdisc.get_stats(zone_name)

    @staticmethod
    def is_zone_shaped(zone_name: str) -> bool:
        """
        Check if a zone has CAKE traffic shaping enabled

        Args:
            zone_name: WireGuard zone/interface name

        Returns:
            bool: True if CAKE is active on the interface
        """
        status = CAKEQdisc.get_status(zone_name)
        return status == 'cake'


# Module-level convenience functions
def check_cake_available() -> bool:
    """Check if CAKE qdisc is available in the system"""
    return CAKEQdisc.is_available()


def apply_cake(interface: str, bandwidth: str, **kwargs) -> bool:
    """
    Apply CAKE qdisc to an interface (convenience function)

    Args:
        interface: Network interface name
        bandwidth: Bandwidth limit
        **kwargs: Additional CAKE parameters

    Returns:
        bool: True if successful
    """
    try:
        return CAKEQdisc.apply(interface, bandwidth, **kwargs)
    except TrafficControlError:
        return False


def remove_cake(interface: str) -> bool:
    """
    Remove CAKE qdisc from an interface (convenience function)

    Args:
        interface: Network interface name

    Returns:
        bool: True if successful
    """
    try:
        return CAKEQdisc.remove(interface)
    except TrafficControlError:
        return False


if __name__ == '__main__':
    # Self-test
    logging.basicConfig(level=logging.INFO)

    print("CAKE Traffic Control Module - Self Test")
    print("=" * 50)

    print(f"CAKE available: {check_cake_available()}")
    print(f"Validate '100mbit': {CAKEQdisc.validate_bandwidth('100mbit')}")
    print(f"Validate '1gbit': {CAKEQdisc.validate_bandwidth('1gbit')}")
    print(f"Validate 'invalid': {CAKEQdisc.validate_bandwidth('invalid')}")

    print("\nDefault zone bandwidths:")
    for zone, bw in TrafficControl.ZONE_DEFAULTS.items():
        print(f"  {zone}: {bw}")
