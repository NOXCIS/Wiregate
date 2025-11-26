"""
CPS Pattern Library Manager
Manages storage and retrieval of CPS patterns from captured packets
"""
import logging
import json
import os
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger('wiregate')

# Import DashboardConfig only when needed
try:
    from ..DashboardConfig import DashboardConfig
    DASHBOARD_CONFIG_AVAILABLE = True
except (ImportError, AttributeError):
    DASHBOARD_CONFIG_AVAILABLE = False
    DashboardConfig = None


class CPSPatternLibrary:
    """Manage CPS pattern library storage and retrieval"""
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize pattern library
        
        Args:
            library_path: Path to pattern library directory. If None, uses default.
        """
        if library_path is None:
            # Priority order:
            # 1. Check container path first (most reliable in Docker)
            # 2. Try DashboardConfig path calculation
            # 3. Fallback to relative path from module location
            
            container_path = "/WireGate/configs/cps_patterns"
            if os.path.exists(container_path):
                library_path = container_path
                logger.debug(f"Using container path: {library_path}")
            elif DASHBOARD_CONFIG_AVAILABLE and DashboardConfig:
                try:
                    base_path = DashboardConfig.GetConfig("Server", "wg_conf_path")[1]
                    # In container, wg_conf_path is /etc/wireguard
                    # Project root is /WireGate, so check if /WireGate/configs/cps_patterns exists
                    wiregate_path = "/WireGate/configs/cps_patterns"
                    if os.path.exists(wiregate_path):
                        library_path = wiregate_path
                        logger.debug(f"Using WireGate path from DashboardConfig: {library_path}")
                    else:
                        # Calculate relative to wg_conf_path
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(base_path))))
                        library_path = os.path.join(project_root, "configs", "cps_patterns")
                        logger.debug(f"Calculated library path from DashboardConfig: {library_path}")
                except Exception as e:
                    logger.debug(f"DashboardConfig path calculation failed: {e}")
                    # Fallback to relative path from module location
                    library_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "cps_patterns")
                    logger.debug(f"Using relative path fallback: {library_path}")
            else:
                # Fallback to relative path from module location
                library_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "cps_patterns")
                logger.debug(f"Using relative path fallback: {library_path}")
        
        self.library_path = library_path
        self.patterns_file = os.path.join(library_path, "patterns.json")
        self._ensure_library_exists()
    
    def _ensure_library_exists(self):
        """Create library directory and initialize patterns.json if needed"""
        os.makedirs(self.library_path, exist_ok=True)
        
        # Create protocol subdirectories
        for protocol in ['http_get', 'http_response', 'dns', 'quic', 'json']:
            os.makedirs(os.path.join(self.library_path, protocol), exist_ok=True)
        
        # Initialize patterns.json if it doesn't exist
        if not os.path.exists(self.patterns_file):
            self._save_patterns_file({
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'patterns': [],
                'statistics': {
                    'total_patterns': 0,
                    'by_protocol': {
                        'http_get': 0,
                        'http_response': 0,
                        'dns': 0,
                        'quic': 0,
                        'json': 0
                    }
                }
            })
    
    def _load_patterns_file(self) -> Dict[str, Any]:
        """Load patterns.json file"""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading patterns file: {e}")
        
        # Return default structure
        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'patterns': [],
            'statistics': {
                'total_patterns': 0,
                'by_protocol': {
                    'http_get': 0,
                    'http_response': 0,
                    'dns': 0,
                    'quic': 0,
                    'json': 0
                }
            }
        }
    
    def _save_patterns_file(self, data: Dict[str, Any]):
        """Save patterns.json file"""
        try:
            with open(self.patterns_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving patterns file: {e}")
            raise
    
    def _generate_pattern_id(self, protocol: str, cps_pattern: str) -> str:
        """Generate unique pattern ID"""
        pattern_hash = hashlib.md5(cps_pattern.encode()).hexdigest()[:8]
        return f"{protocol}_{pattern_hash}"
    
    def load_patterns(self, protocol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load patterns from library
        
        Args:
            protocol: Filter by protocol type. If None, returns all patterns.
        
        Returns:
            List of pattern dictionaries
        """
        try:
            data = self._load_patterns_file()
            patterns = data.get('patterns', [])
            
            logger.debug(f"Loaded {len(patterns)} total patterns from {self.patterns_file}")
            
            if protocol:
                filtered = [p for p in patterns if p.get('protocol') == protocol]
                logger.debug(f"Filtered to {len(filtered)} patterns for protocol {protocol}")
                return filtered
            
            return patterns
        except Exception as e:
            logger.error(f"Error loading patterns from {self.patterns_file}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def save_pattern(self, pattern: Dict[str, Any]) -> bool:
        """
        Save pattern to library
        
        Args:
            pattern: Pattern dictionary with keys:
                - protocol: Protocol type (http_get, http_response, dns, quic, json)
                - cps_pattern: CPS pattern string
                - metadata: Optional metadata dict
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate required fields
            if 'protocol' not in pattern or 'cps_pattern' not in pattern:
                logger.error("Pattern missing required fields: protocol or cps_pattern")
                return False
            
            # Generate pattern ID if not provided
            if 'id' not in pattern:
                pattern['id'] = self._generate_pattern_id(pattern['protocol'], pattern['cps_pattern'])
            
            # Add timestamp if not present
            if 'metadata' not in pattern:
                pattern['metadata'] = {}
            
            if 'capture_date' not in pattern['metadata']:
                pattern['metadata']['capture_date'] = datetime.now().isoformat()
            
            if 'source' not in pattern['metadata']:
                pattern['metadata']['source'] = 'captured'
            
            # Load existing patterns
            data = self._load_patterns_file()
            patterns = data.get('patterns', [])
            
            # Check for duplicates (same pattern ID or same CPS pattern)
            existing_ids = [p.get('id') for p in patterns]
            existing_patterns = [p.get('cps_pattern') for p in patterns]
            
            # Skip if same ID or same CPS pattern already exists
            if pattern['id'] in existing_ids:
                logger.debug(f"Pattern {pattern['id']} already exists (same ID), skipping")
                return True  # Not an error, just skip duplicate
            if pattern['cps_pattern'] in existing_patterns:
                logger.debug(f"Pattern already exists (same CPS pattern), skipping")
                return True  # Not an error, just skip duplicate
            
            # Add new pattern
            patterns.append(pattern)
            data['patterns'] = patterns
            
            # Update statistics
            stats = data.get('statistics', {})
            stats['total_patterns'] = len(patterns)
            protocol_stats = stats.get('by_protocol', {})
            protocol = pattern['protocol']
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
            stats['by_protocol'] = protocol_stats
            data['statistics'] = stats
            
            # Save to file
            self._save_patterns_file(data)
            
            # Also save individual pattern file
            protocol_dir = os.path.join(self.library_path, protocol)
            pattern_file = os.path.join(protocol_dir, f"{pattern['id']}.json")
            with open(pattern_file, 'w') as f:
                json.dump(pattern, f, indent=2)
            
            logger.debug(f"Saved pattern {pattern['id']} to library")
            return True
            
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
            return False
    
    def select_random_pattern(self, protocol: str) -> Optional[str]:
        """
        Select random pattern from library for given protocol
        
        Args:
            protocol: Protocol type
        
        Returns:
            CPS pattern string or None if no patterns found
        """
        patterns = self.load_patterns(protocol)
        if not patterns:
            return None
        
        selected = random.choice(patterns)
        return selected.get('cps_pattern')
    
    def mix_patterns(self, base_pattern: str, variations: List[str]) -> str:
        """
        Mix multiple patterns for enhanced randomization
        
        Args:
            base_pattern: Base CPS pattern
            variations: List of variation patterns
        
        Returns:
            Mixed pattern string
        """
        if not variations:
            return base_pattern
        
        # Simple mixing: randomly choose between base and variations
        if random.random() < 0.3:  # 30% chance to use variation
            return random.choice(variations)
        
        return base_pattern
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        data = self._load_patterns_file()
        return data.get('statistics', {})
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete pattern from library
        
        Args:
            pattern_id: Pattern ID to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            data = self._load_patterns_file()
            patterns = data.get('patterns', [])
            
            # Find and remove pattern
            original_count = len(patterns)
            patterns = [p for p in patterns if p.get('id') != pattern_id]
            
            if len(patterns) == original_count:
                logger.warning(f"Pattern {pattern_id} not found")
                return False
            
            # Update statistics
            stats = data.get('statistics', {})
            stats['total_patterns'] = len(patterns)
            
            # Find protocol of deleted pattern
            deleted_pattern = next((p for p in data.get('patterns', []) if p.get('id') == pattern_id), None)
            if deleted_pattern:
                protocol = deleted_pattern.get('protocol')
                protocol_stats = stats.get('by_protocol', {})
                protocol_stats[protocol] = max(0, protocol_stats.get(protocol, 0) - 1)
                stats['by_protocol'] = protocol_stats
            
            data['patterns'] = patterns
            data['statistics'] = stats
            
            # Save to file
            self._save_patterns_file(data)
            
            # Delete individual pattern file
            if deleted_pattern:
                protocol = deleted_pattern.get('protocol')
                pattern_file = os.path.join(self.library_path, protocol, f"{pattern_id}.json")
                if os.path.exists(pattern_file):
                    os.remove(pattern_file)
            
            logger.debug(f"Deleted pattern {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")
            return False
    
    def validate_pattern(self, pattern: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CPS pattern format
        
        Args:
            pattern: CPS pattern string
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from ..Utilities import ValidateCPSFormat
        is_valid, error_msg = ValidateCPSFormat(pattern)
        return is_valid, error_msg
    
    def bulk_save_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Save multiple patterns at once
        
        Args:
            patterns: List of pattern dictionaries
        
        Returns:
            Dictionary with success and failure counts
        """
        results = {'success': 0, 'failed': 0, 'duplicates': 0}
        
        for pattern in patterns:
            # Check if pattern already exists (by ID or CPS pattern)
            existing_patterns = self.load_patterns(pattern.get('protocol'))
            pattern_id = self._generate_pattern_id(pattern.get('protocol', ''), pattern.get('cps_pattern', ''))
            cps_pattern = pattern.get('cps_pattern', '')
            
            # Check for duplicates
            is_duplicate = False
            for existing in existing_patterns:
                if existing.get('id') == pattern_id or existing.get('cps_pattern') == cps_pattern:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                results['duplicates'] += 1
                continue
            
            if self.save_pattern(pattern):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results

