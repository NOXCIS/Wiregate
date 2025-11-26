"""
Lightweight ML Auto-Adaptation for I1-I5 CPS Patterns
Uses simple statistical learning to adapt CPS packet patterns and avoid DPI fingerprinting
"""
import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

logger = logging.getLogger('wiregate')


class CPSPatternMetrics:
    """
    Tracks performance metrics for CPS pattern combinations
    
    Now supports library-based pattern tracking:
    - Stores library pattern IDs (base patterns before randomization)
    - Tracks which library patterns perform well per protocol
    - Enables ML adaptation to suggest better library patterns
    """
    
    def __init__(self, config_name: str, db_manager):
        self.config_name = config_name
        self.db = db_manager
        self._init_metrics_table()
        
    def _init_metrics_table(self):
        """Initialize database table for CPS pattern metrics"""
        try:
            # Create table if it doesn't exist
            table_name = f"{self.config_name}_cps_metrics"
            
            # Check if table exists
            if not self.db.manager.table_exists(table_name):
                schema = {
                    'pattern_hash': 'VARCHAR PRIMARY KEY',
                    'i1': 'TEXT',
                    'i2': 'TEXT',
                    'i3': 'TEXT',
                    'i4': 'TEXT',
                    'i5': 'TEXT',
                    'i1_library_id': 'VARCHAR',
                    'i2_library_id': 'VARCHAR',
                    'i3_library_id': 'VARCHAR',
                    'i4_library_id': 'VARCHAR',
                    'i5_library_id': 'VARCHAR',
                    'connection_attempts': 'INTEGER DEFAULT 0',
                    'connection_successes': 'INTEGER DEFAULT 0',
                    'connection_failures': 'INTEGER DEFAULT 0',
                    'avg_latency_ms': 'REAL DEFAULT 0.0',
                    'avg_throughput_mbps': 'REAL DEFAULT 0.0',
                    'last_used': 'TIMESTAMP',
                    'last_updated': 'TIMESTAMP',
                    'performance_score': 'REAL DEFAULT 0.0'
                }
                
                self.db.manager.create_table(table_name, schema)
                logger.debug(f"Initialized CPS metrics table for {self.config_name}")
        except Exception as e:
            logger.error(f"Failed to initialize CPS metrics table: {e}")
    
    def _hash_pattern(self, i1: str, i2: str, i3: str, i4: str, i5: str) -> str:
        """Generate hash for pattern combination"""
        pattern_str = f"{i1}|{i2}|{i3}|{i4}|{i5}"
        return hashlib.sha256(pattern_str.encode()).hexdigest()[:16]
    
    def record_connection_attempt(self, i1: str, i2: str, i3: str, i4: str, i5: str, 
                                 success: bool, latency_ms: float = 0.0, throughput_mbps: float = 0.0,
                                 i1_lib_id: Optional[str] = None, i2_lib_id: Optional[str] = None,
                                 i3_lib_id: Optional[str] = None, i4_lib_id: Optional[str] = None,
                                 i5_lib_id: Optional[str] = None):
        """
        Record a connection attempt with the given CPS pattern
        
        Args:
            i1-i5: The randomized CPS patterns used
            success: Whether connection succeeded
            latency_ms: Connection latency in milliseconds
            throughput_mbps: Throughput in Mbps
            i1_lib_id - i5_lib_id: Optional library pattern IDs (base patterns before randomization)
        """
        try:
            pattern_hash = self._hash_pattern(i1, i2, i3, i4, i5)
            table_name = f"{self.config_name}_cps_metrics"
            
            # Get existing metrics or create new
            existing = self.db.manager.get_record(table_name, pattern_hash)
            
            now = datetime.now()
            
            if existing:
                # Update existing metrics
                attempts = existing.get('connection_attempts', 0) + 1
                successes = existing.get('connection_successes', 0) + (1 if success else 0)
                failures = existing.get('connection_failures', 0) + (0 if success else 1)
                
                # Update latency (exponential moving average)
                old_avg_latency = existing.get('avg_latency_ms', 0.0) or 0.0
                alpha = 0.3  # Smoothing factor
                new_avg_latency = (alpha * latency_ms) + ((1 - alpha) * old_avg_latency) if latency_ms > 0 else old_avg_latency
                
                # Update throughput (exponential moving average)
                old_avg_throughput = existing.get('avg_throughput_mbps', 0.0) or 0.0
                new_avg_throughput = (alpha * throughput_mbps) + ((1 - alpha) * old_avg_throughput) if throughput_mbps > 0 else old_avg_throughput
                
                # Calculate performance score
                success_rate = successes / attempts if attempts > 0 else 0.0
                performance_score = self._calculate_performance_score(
                    success_rate, new_avg_latency, new_avg_throughput
                )
                
                self.db.manager.update_record(
                    table_name,
                    pattern_hash,
                    {
                        'connection_attempts': attempts,
                        'connection_successes': successes,
                        'connection_failures': failures,
                        'avg_latency_ms': new_avg_latency,
                        'avg_throughput_mbps': new_avg_throughput,
                        'last_used': now,
                        'last_updated': now,
                        'performance_score': performance_score
                    }
                )
            else:
                # Create new metrics entry
                performance_score = self._calculate_performance_score(
                    1.0 if success else 0.0, latency_ms, throughput_mbps
                )
                
                insert_data = {
                    'pattern_hash': pattern_hash,
                    'i1': i1 or '',
                    'i2': i2 or '',
                    'i3': i3 or '',
                    'i4': i4 or '',
                    'i5': i5 or '',
                    'i1_library_id': i1_lib_id or '',
                    'i2_library_id': i2_lib_id or '',
                    'i3_library_id': i3_lib_id or '',
                    'i4_library_id': i4_lib_id or '',
                    'i5_library_id': i5_lib_id or '',
                    'connection_attempts': 1,
                    'connection_successes': 1 if success else 0,
                    'connection_failures': 0 if success else 1,
                    'avg_latency_ms': latency_ms,
                    'avg_throughput_mbps': throughput_mbps,
                    'last_used': now,
                    'last_updated': now,
                    'performance_score': performance_score
                }
                self.db.manager.insert_record(table_name, pattern_hash, insert_data)
                
            logger.debug(f"Recorded connection attempt for pattern {pattern_hash[:8]}... (success: {success})")
        except Exception as e:
            logger.error(f"Failed to record connection attempt: {e}")
    
    def _calculate_performance_score(self, success_rate: float, latency_ms: float, throughput_mbps: float) -> float:
        """Calculate performance score (0.0 to 1.0)"""
        # Weighted scoring: success rate is most important
        # Lower latency is better, higher throughput is better
        success_weight = 0.6
        latency_weight = 0.2
        throughput_weight = 0.2
        
        # Normalize latency (assume < 500ms is good, > 2000ms is bad)
        latency_score = max(0.0, min(1.0, 1.0 - (latency_ms / 2000.0))) if latency_ms > 0 else 0.5
        
        # Normalize throughput (assume > 10 Mbps is good)
        throughput_score = min(1.0, throughput_mbps / 10.0) if throughput_mbps > 0 else 0.0
        
        score = (success_weight * success_rate) + (latency_weight * latency_score) + (throughput_weight * throughput_score)
        return round(score, 4)
    
    def get_pattern_performance(self, i1: str, i2: str, i3: str, i4: str, i5: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific pattern"""
        try:
            pattern_hash = self._hash_pattern(i1, i2, i3, i4, i5)
            table_name = f"{self.config_name}_cps_metrics"
            
            result = self.db.manager.get_record(table_name, pattern_hash)
            
            return result if result else None
        except Exception as e:
            logger.error(f"Failed to get pattern performance: {e}")
            return None
    
    def get_best_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing patterns by performance score"""
        try:
            table_name = f"{self.config_name}_cps_metrics"
            
            # Get patterns with minimum attempts threshold (at least 3 attempts)
            query = f"""
                SELECT * FROM "{table_name}"
                WHERE connection_attempts >= 3
                ORDER BY performance_score DESC, connection_attempts DESC
                LIMIT {limit}
            """
            
            results = self.db.manager.execute_query(query)
            return results if results else []
        except Exception as e:
            logger.error(f"Failed to get best patterns: {e}")
            return []
    
    def get_poor_patterns(self, threshold: float = 0.3, min_attempts: int = 5) -> List[Dict[str, Any]]:
        """Get patterns performing below threshold"""
        try:
            table_name = f"{self.config_name}_cps_metrics"
            
            query = f"""
                SELECT * FROM "{table_name}"
                WHERE performance_score < {threshold}
                AND connection_attempts >= {min_attempts}
                ORDER BY performance_score ASC
            """
            
            results = self.db.manager.execute_query(query)
            return results if results else []
        except Exception as e:
            logger.error(f"Failed to get poor patterns: {e}")
            return []


class CPSPatternAdaptation:
    """
    Lightweight statistical learning system for CPS pattern adaptation
    
    Updated for library-based pattern generation:
    - Tracks library pattern IDs alongside randomized patterns
    - Suggests improvements by selecting better-performing library patterns
    - Frontend handles randomization of suggested library patterns
    """
    
    def __init__(self, config_name: str, db_manager):
        self.config_name = config_name
        self.metrics = CPSPatternMetrics(config_name, db_manager)
        self.adaptation_threshold = 0.4  # Adapt if performance score < 0.4
        self.min_attempts_for_adaptation = 5  # Need at least 5 attempts before adapting
        
    def should_adapt_pattern(self, i1: str, i2: str, i3: str, i4: str, i5: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if pattern should be adapted based on performance"""
        try:
            perf = self.metrics.get_pattern_performance(i1, i2, i3, i4, i5)
            
            if not perf:
                # New pattern, no adaptation needed yet
                return False, None
            
            attempts = perf.get('connection_attempts', 0)
            score = perf.get('performance_score', 0.0) or 0.0
            
            if attempts >= self.min_attempts_for_adaptation and score < self.adaptation_threshold:
                return True, perf
            
            return False, perf
        except Exception as e:
            logger.error(f"Failed to check adaptation need: {e}")
            return False, None
    
    def suggest_improved_pattern(self, current_i1: str, current_i2: str, current_i3: str, 
                                 current_i4: str, current_i5: str) -> Dict[str, str]:
        """
        Suggest improved pattern based on best performing library patterns
        
        Strategy: Find best performing library pattern IDs, then fetch new patterns
        from library and randomize them (frontend will handle randomization)
        """
        try:
            from .CPSPatternLibrary import CPSPatternLibrary
            
            # Get best performing patterns
            best_patterns = self.metrics.get_best_patterns(limit=5)
            
            library = CPSPatternLibrary()
            
            # Map I1-I5 to protocol types
            protocol_map = {
                'i1': 'quic',
                'i2': 'http_get',
                'i3': 'dns',
                'i4': 'json',
                'i5': 'http_response'
            }
            
            suggested = {}
            
            # For each I parameter, try to find a better library pattern
            current_patterns = {
                'i1': current_i1,
                'i2': current_i2,
                'i3': current_i3,
                'i4': current_i4,
                'i5': current_i5
            }
            
            for param, protocol in protocol_map.items():
                current_pattern = current_patterns[param]
                
                # Try to get best performing library IDs for this protocol
                best_lib_ids = self.metrics.get_best_library_ids_by_protocol(protocol)
                
                # If we have best library IDs, prefer them
                if best_lib_ids:
                    try:
                        all_patterns = library.load_patterns(protocol)
                        # Try to get a pattern from the best performing library IDs
                        for lib_id in best_lib_ids:
                            for p in all_patterns:
                                if p.get('id') == lib_id:
                                    # Return the base pattern - frontend will randomize it
                                    suggested[param] = p.get('cps_pattern', current_pattern) or current_pattern
                                    break
                            if param in suggested:
                                break
                    except Exception as e:
                        logger.debug(f"Could not fetch best library patterns for {protocol}: {e}")
                
                # If we didn't find a best pattern, get a random one from library
                if param not in suggested:
                    library_pattern = library.select_random_pattern(protocol)
                    if library_pattern:
                        suggested[param] = library_pattern
                    else:
                        # Fallback to current if library unavailable
                        suggested[param] = current_pattern
            
            return {
                'i1': suggested.get('i1', current_i1) or current_i1,
                'i2': suggested.get('i2', current_i2) or current_i2,
                'i3': suggested.get('i3', current_i3) or current_i3,
                'i4': suggested.get('i4', current_i4) or current_i4,
                'i5': suggested.get('i5', current_i5) or current_i5
            }
        except Exception as e:
            logger.error(f"Failed to suggest improved pattern: {e}")
            # Return current pattern on error
            return {
                'i1': current_i1,
                'i2': current_i2,
                'i3': current_i3,
                'i4': current_i4,
                'i5': current_i5
            }
    
    def adapt_pattern_real_time(self, current_i1: str, current_i2: str, current_i3: str,
                                current_i4: str, current_i5: str) -> Dict[str, str]:
        """Real-time pattern adaptation check"""
        should_adapt, perf = self.should_adapt_pattern(current_i1, current_i2, current_i3, current_i4, current_i5)
        
        if should_adapt:
            logger.info(f"Adapting CPS pattern for {self.config_name} due to poor performance (score: {perf.get('performance_score', 0):.2f})")
            return self.suggest_improved_pattern(current_i1, current_i2, current_i3, current_i4, current_i5)
        
        # Return current pattern if no adaptation needed
        return {
            'i1': current_i1,
            'i2': current_i2,
            'i3': current_i3,
            'i4': current_i4,
            'i5': current_i5
        }
    
    def periodic_adaptation_check(self) -> Optional[Dict[str, str]]:
        """
        Periodic batch adaptation check (called daily/weekly)
        
        Uses library-based pattern selection: finds best performing library pattern IDs
        per protocol and returns base patterns (frontend will randomize them)
        """
        try:
            from .CPSPatternLibrary import CPSPatternLibrary
            
            # Get all poor performing patterns
            poor_patterns = self.metrics.get_poor_patterns(threshold=self.adaptation_threshold)
            
            if not poor_patterns:
                return None
            
            library = CPSPatternLibrary()
            
            # Map I1-I5 to protocol types
            protocol_map = {
                'i1': 'quic',
                'i2': 'http_get',
                'i3': 'dns',
                'i4': 'json',
                'i5': 'http_response'
            }
            
            suggested = {}
            
            # For each protocol, get best performing library pattern
            for param, protocol in protocol_map.items():
                # Get best library IDs for this protocol
                best_lib_ids = self.metrics.get_best_library_ids_by_protocol(protocol)
                
                if best_lib_ids:
                    try:
                        all_patterns = library.load_patterns(protocol)
                        # Get the top performing library pattern
                        for lib_id in best_lib_ids[:1]:  # Just use the best one
                            for p in all_patterns:
                                if p.get('id') == lib_id:
                                    suggested[param] = p.get('cps_pattern', '') or ''
                                    break
                            if param in suggested:
                                break
                    except Exception as e:
                        logger.debug(f"Could not fetch library pattern for {protocol}: {e}")
                
                # Fallback to random library pattern if no best ID found
                if param not in suggested:
                    library_pattern = library.select_random_pattern(protocol)
                    suggested[param] = library_pattern or ''
            
            logger.info(f"Periodic adaptation: Found {len(poor_patterns)} poor patterns, recommending library-based patterns")
            
            return {
                'i1': suggested.get('i1', '') or '',
                'i2': suggested.get('i2', '') or '',
                'i3': suggested.get('i3', '') or '',
                'i4': suggested.get('i4', '') or '',
                'i5': suggested.get('i5', '') or ''
            }
        except Exception as e:
            logger.error(f"Failed periodic adaptation check: {e}")
            return None
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about pattern adaptation"""
        try:
            best_patterns = self.metrics.get_best_patterns(limit=5)
            poor_patterns = self.metrics.get_poor_patterns()
            
            return {
                'total_tracked_patterns': len(best_patterns) + len(poor_patterns),
                'top_performing': len(best_patterns),
                'poor_performing': len(poor_patterns),
                'adaptation_threshold': self.adaptation_threshold,
                'best_pattern_score': best_patterns[0].get('performance_score', 0.0) if best_patterns else 0.0
            }
        except Exception as e:
            logger.error(f"Failed to get adaptation stats: {e}")
            return {}

