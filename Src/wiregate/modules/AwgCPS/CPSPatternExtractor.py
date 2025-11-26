"""
CPS Pattern Extractor
Extracts protocol patterns from captured packets and converts them to CPS tag format
"""
import logging
import re
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger('wiregate')

try:
    import dpkt
    DPKT_AVAILABLE = True
except ImportError:
    DPKT_AVAILABLE = False
    logger.warning("dpkt not available. Packet extraction will be limited.")


class CPSPatternExtractor:
    """Extract and convert protocol patterns to CPS format"""
    
    def __init__(self):
        self.protocol_handlers = {
            'http_get': self.extract_http_get_pattern,
            'http_response': self.extract_http_response_pattern,
            'dns': self.extract_dns_query_pattern,
            'quic': self.extract_quic_pattern,
            'json': self.extract_json_pattern,
        }
    
    def identify_protocol(self, packet_data: bytes) -> Optional[str]:
        """Identify protocol type from packet data"""
        if not packet_data:
            return None
        
        # Check for HTTP GET
        if packet_data.startswith(b'GET ') or packet_data.startswith(b'POST ') or \
           packet_data.startswith(b'PUT ') or packet_data.startswith(b'DELETE '):
            return 'http_get'
        
        # Check for HTTP Response
        if packet_data.startswith(b'HTTP/'):
            return 'http_response'
        
        # Check for QUIC (starts with specific flags)
        if len(packet_data) >= 1 and (packet_data[0] & 0xC0) == 0xC0:
            return 'quic'
        
        # Check for DNS (UDP port 53, specific structure)
        if len(packet_data) >= 12:
            # DNS header: ID (2 bytes) + Flags (2 bytes) + Questions (2 bytes)
            # Standard query flags: 0x0100
            if len(packet_data) >= 4 and packet_data[2:4] == b'\x01\x00':
                return 'dns'
        
        # Check for JSON in HTTP responses
        if b'\r\n\r\n' in packet_data:
            headers, body = packet_data.split(b'\r\n\r\n', 1)
            if body and (body.startswith(b'{') or body.startswith(b'[')):
                return 'json'
        
        return None
    
    def extract_http_get_pattern(self, packet_data: bytes) -> Optional[str]:
        """Extract HTTP GET request pattern"""
        try:
            # Find HTTP request line
            lines = packet_data.split(b'\r\n')
            if not lines:
                return None
            
            request_line = lines[0].decode('utf-8', errors='ignore')
            if not request_line.startswith('GET '):
                return None
            
            # Parse: GET /path HTTP/1.1
            parts = request_line.split(' ', 2)
            if len(parts) < 3:
                return None
            
            method = parts[0]
            path = parts[1]
            version = parts[2]
            
            # Build CPS pattern
            cps_parts = []
            
            # Method + space
            cps_parts.append(f'<b 0x{method.encode().hex()}>')
            cps_parts.append('<b 0x20>')  # Space
            
            # Path (variable length)
            path_len = len(path.encode())
            cps_parts.append(f'<rc {path_len}>')
            
            # Space + HTTP version
            version_bytes = (' ' + version).encode()
            cps_parts.append(f'<b 0x{version_bytes.hex()}>')
            cps_parts.append('<b 0x0d0a>')  # \r\n
            
            # Headers
            header_started = False
            for line in lines[1:]:
                if not line:
                    break
                line_str = line.decode('utf-8', errors='ignore')
                if ':' in line_str:
                    header_started = True
                    key, value = line_str.split(':', 1)
                    # Header key + colon + space
                    header_prefix = (key + ': ').encode()
                    cps_parts.append(f'<b 0x{header_prefix.hex()}>')
                    # Value (variable length)
                    value_len = len(value.strip().encode())
                    if value_len > 0:
                        cps_parts.append(f'<rc {value_len}>')
                    cps_parts.append('<b 0x0d0a>')  # \r\n
            
            if header_started:
                cps_parts.append('<b 0x0d0a>')  # Final \r\n
            
            return ''.join(cps_parts)
            
        except Exception as e:
            logger.error(f"Error extracting HTTP GET pattern: {e}")
            return None
    
    def extract_http_response_pattern(self, packet_data: bytes) -> Optional[str]:
        """Extract HTTP response pattern"""
        try:
            lines = packet_data.split(b'\r\n')
            if not lines:
                return None
            
            status_line = lines[0].decode('utf-8', errors='ignore')
            if not status_line.startswith('HTTP/'):
                return None
            
            # Build CPS pattern
            cps_parts = []
            
            # Status line (HTTP/1.1 200 OK\r\n)
            status_bytes = status_line.encode()
            cps_parts.append(f'<b 0x{status_bytes.hex()}>')
            cps_parts.append('<b 0x0d0a>')  # \r\n
            
            # Headers
            for line in lines[1:]:
                if not line:
                    break
                line_str = line.decode('utf-8', errors='ignore')
                if ':' in line_str:
                    key, value = line_str.split(':', 1)
                    # Header key + colon + space
                    header_prefix = (key + ': ').encode()
                    cps_parts.append(f'<b 0x{header_prefix.hex()}>')
                    # Value (variable length)
                    value_len = len(value.strip().encode())
                    if value_len > 0:
                        cps_parts.append(f'<rc {value_len}>')
                    cps_parts.append('<b 0x0d0a>')  # \r\n
            
            cps_parts.append('<b 0x0d0a>')  # Final \r\n
            
            return ''.join(cps_parts)
            
        except Exception as e:
            logger.error(f"Error extracting HTTP response pattern: {e}")
            return None
    
    def extract_dns_query_pattern(self, packet_data: bytes) -> Optional[str]:
        """Extract DNS query pattern"""
        try:
            if len(packet_data) < 12:
                return None
            
            # DNS header: ID (2) + Flags (2) + Questions (2) + Answers (2) + Authority (2) + Additional (2)
            cps_parts = []
            
            # ID (use counter tag)
            cps_parts.append('<c>')
            
            # Flags + Questions + Answers + Authority + Additional
            header_bytes = packet_data[2:12]
            cps_parts.append(f'<b 0x{header_bytes.hex()}>')
            
            # Question section: Name (variable length, length-prefixed labels)
            offset = 12
            name_parts = []
            while offset < len(packet_data) and packet_data[offset] != 0:
                label_len = packet_data[offset]
                if label_len == 0 or offset + label_len > len(packet_data):
                    break
                offset += 1
                label = packet_data[offset:offset + label_len]
                name_parts.append((label_len, label))
                offset += label_len
            
            # Build name pattern
            for label_len, label in name_parts:
                cps_parts.append(f'<b 0x{label_len:02x}>')  # Length byte
                cps_parts.append(f'<rc {label_len}>')  # Label content
            
            # Null terminator
            if offset < len(packet_data) and packet_data[offset] == 0:
                cps_parts.append('<b 0x00>')
                offset += 1
            
            # Type (2 bytes) + Class (2 bytes)
            if offset + 4 <= len(packet_data):
                type_class = packet_data[offset:offset + 4]
                cps_parts.append(f'<b 0x{type_class.hex()}>')
            
            return ''.join(cps_parts)
            
        except Exception as e:
            logger.error(f"Error extracting DNS pattern: {e}")
            return None
    
    def extract_quic_pattern(self, packet_data: bytes) -> Optional[str]:
        """Extract QUIC initial packet pattern"""
        try:
            if len(packet_data) < 5:
                return None
            
            cps_parts = []
            
            # Header flags (1 byte)
            flags = packet_data[0]
            cps_parts.append(f'<b 0x{flags:02x}>')
            
            # Version (4 bytes)
            if len(packet_data) >= 5:
                version = packet_data[1:5]
                cps_parts.append(f'<b 0x{version.hex()}>')
            
            offset = 5
            
            # Destination Connection ID length
            if offset < len(packet_data):
                dcid_len = packet_data[offset]
                cps_parts.append(f'<b 0x{dcid_len:02x}>')
                offset += 1
                
                # Destination Connection ID
                if offset + dcid_len <= len(packet_data):
                    cps_parts.append(f'<r {dcid_len}>')
                    offset += dcid_len
            
            # Source Connection ID length
            if offset < len(packet_data):
                scid_len = packet_data[offset]
                cps_parts.append(f'<b 0x{scid_len:02x}>')
                offset += 1
                
                # Source Connection ID
                if offset + scid_len <= len(packet_data):
                    cps_parts.append(f'<r {scid_len}>')
                    offset += scid_len
            
            # Token length (variable length encoding)
            if offset < len(packet_data):
                token_len = packet_data[offset]
                cps_parts.append(f'<b 0x{token_len:02x}>')
                offset += 1
                
                # Token
                if offset + token_len <= len(packet_data):
                    cps_parts.append(f'<r {token_len}>')
                    offset += token_len
            
            # Payload (remaining data)
            if offset < len(packet_data):
                payload_len = len(packet_data) - offset
                cps_parts.append(f'<r {payload_len}>')
            
            return ''.join(cps_parts)
            
        except Exception as e:
            logger.error(f"Error extracting QUIC pattern: {e}")
            return None
    
    def extract_json_pattern(self, packet_data: bytes) -> Optional[str]:
        """Extract JSON pattern from HTTP response body"""
        try:
            # Find JSON in response body
            if b'\r\n\r\n' not in packet_data:
                return None
            
            headers, body = packet_data.split(b'\r\n\r\n', 1)
            if not body:
                return None
            
            # Try to parse JSON
            try:
                json_data = json.loads(body.decode('utf-8', errors='ignore'))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON from HTTP response body: {e}")
                return None
            
            # Convert JSON structure to CPS pattern
            cps_parts = []
            cps_parts.append('<b 0x7b>')  # {
            
            # Simple pattern: {"key":"value"}
            if isinstance(json_data, dict):
                first_key = True
                for key, value in list(json_data.items())[:2]:  # Limit to 2 items
                    if not first_key:
                        cps_parts.append('<b 0x2c>')  # ,
                    
                    # Key
                    key_bytes = json.dumps(key).encode()
                    cps_parts.append(f'<b 0x{key_bytes.hex()}>')
                    cps_parts.append('<b 0x3a>')  # :
                    
                    # Value
                    if isinstance(value, str):
                        value_bytes = json.dumps(value).encode()
                        cps_parts.append(f'<b 0x{value_bytes.hex()}>')
                    elif isinstance(value, (int, float)):
                        value_str = str(value)
                        cps_parts.append(f'<rd {len(value_str)}>')
                    elif isinstance(value, bool):
                        cps_parts.append(f'<b 0x{json.dumps(value).encode().hex()}>')
                    
                    first_key = False
                
                cps_parts.append('<b 0x7d>')  # }
            
            return ''.join(cps_parts)
            
        except Exception as e:
            logger.error(f"Error extracting JSON pattern: {e}")
            return None
    
    def convert_to_cps_format(self, packet_data: bytes, protocol: Optional[str] = None) -> Optional[str]:
        """Convert packet data to CPS format"""
        if protocol is None:
            protocol = self.identify_protocol(packet_data)
        
        if protocol is None:
            return None
        
        handler = self.protocol_handlers.get(protocol)
        if handler:
            return handler(packet_data)
        
        return None
    
    def process_captured_packets(self, capture_dir: str) -> List[Dict[str, Any]]:
        """Process all captured packets from a capture directory"""
        patterns = []
        
        if not os.path.exists(capture_dir):
            logger.error(f"Capture directory not found: {capture_dir}")
            return patterns
        
        # Process JSON files from capture
        for filename in os.listdir(capture_dir):
            if not filename.endswith('.json') or filename == 'summary.json':
                continue
            
            filepath = os.path.join(capture_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                if 'packets' not in data:
                    continue
                
                # Determine protocol from filename
                protocol = None
                if 'http_get' in filename:
                    protocol = 'http_get'
                elif 'http_response' in filename:
                    protocol = 'http_response'
                elif 'dns' in filename:
                    protocol = 'dns'
                elif 'quic' in filename:
                    protocol = 'quic'
                elif 'json' in filename:
                    protocol = 'json'
                
                # Process each packet
                for packet in data.get('packets', []):
                    hex_data = packet.get('hex_data', '')
                    if not hex_data:
                        continue
                    
                    # Convert hex string to bytes
                    try:
                        packet_bytes = bytes.fromhex(hex_data)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to convert hex string to bytes: {e}")
                        continue
                    
                    # Extract pattern
                    cps_pattern = self.convert_to_cps_format(packet_bytes, protocol)
                    if cps_pattern:
                        patterns.append({
                            'protocol': protocol or 'unknown',
                            'cps_pattern': cps_pattern,
                            'original_length': len(packet_bytes),
                            'source': 'captured',
                            'capture_date': datetime.now().isoformat(),
                            'metadata': {
                                'packet_number': packet.get('packet_number'),
                                'timestamp': packet.get('timestamp')
                            }
                        })
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                continue
        
        return patterns

