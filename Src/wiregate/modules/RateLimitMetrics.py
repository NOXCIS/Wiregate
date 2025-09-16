"""
Rate Limiting Metrics and Monitoring
Provides metrics collection and monitoring for distributed rate limiting
"""
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..modules.DistributedRateLimitConfig import distributed_rate_limit_config

class RateLimitMetrics:
    """Metrics collection for rate limiting"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.metrics_enabled = distributed_rate_limit_config.is_feature_enabled('metrics_enabled')
        self.alert_threshold = distributed_rate_limit_config.get_config('monitoring', 'alert_threshold')
        
    def record_request(self, identifier: str, endpoint: str, is_limited: bool, 
                      limit_type: str = None, response_time: float = None) -> None:
        """Record a request for metrics"""
        if not self.metrics_enabled or not self.redis_client:
            return
            
        try:
            timestamp = int(time.time())
            metrics_key = f"rate_limit_metrics:{timestamp // 60}"  # 1-minute buckets
            
            data = {
                'identifier': identifier,
                'endpoint': endpoint,
                'is_limited': is_limited,
                'limit_type': limit_type or 'none',
                'response_time': response_time or 0,
                'timestamp': timestamp
            }
            
            # Store in Redis sorted set
            self.redis_client.zadd(metrics_key, {json.dumps(data): timestamp})
            self.redis_client.expire(metrics_key, 3600)  # Keep for 1 hour
            
        except Exception as e:
            print(f"Metrics recording error: {e}")
    
    def get_metrics_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get metrics summary for the specified time window"""
        if not self.metrics_enabled or not self.redis_client:
            return {'status': 'disabled'}
            
        try:
            current_time = int(time.time())
            start_time = current_time - time_window
            
            # Get all metrics keys in the time window
            pattern = "rate_limit_metrics:*"
            keys = self.redis_client.keys(pattern)
            
            total_requests = 0
            limited_requests = 0
            endpoint_stats = {}
            limit_type_stats = {}
            response_times = []
            
            for key in keys:
                # Get metrics from this time bucket
                metrics = self.redis_client.zrangebyscore(key, start_time, current_time)
                
                for metric_str in metrics:
                    try:
                        metric = json.loads(metric_str)
                        total_requests += 1
                        
                        if metric.get('is_limited', False):
                            limited_requests += 1
                        
                        # Endpoint statistics
                        endpoint = metric.get('endpoint', 'unknown')
                        endpoint_stats[endpoint] = endpoint_stats.get(endpoint, 0) + 1
                        
                        # Limit type statistics
                        limit_type = metric.get('limit_type', 'none')
                        limit_type_stats[limit_type] = limit_type_stats.get(limit_type, 0) + 1
                        
                        # Response time statistics
                        response_time = metric.get('response_time', 0)
                        if response_time > 0:
                            response_times.append(response_time)
                            
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Calculate statistics
            limit_rate = (limited_requests / total_requests * 100) if total_requests > 0 else 0
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'status': 'active',
                'time_window': time_window,
                'total_requests': total_requests,
                'limited_requests': limited_requests,
                'limit_rate_percent': round(limit_rate, 2),
                'average_response_time': round(avg_response_time, 3),
                'endpoint_stats': endpoint_stats,
                'limit_type_stats': limit_type_stats,
                'is_alert_threshold_exceeded': limit_rate > (self.alert_threshold * 100)
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_top_limited_identifiers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top identifiers that are being rate limited"""
        if not self.metrics_enabled or not self.redis_client:
            return []
            
        try:
            current_time = int(time.time())
            time_window = 3600  # 1 hour
            start_time = current_time - time_window
            
            # Count limited requests per identifier
            identifier_counts = {}
            pattern = "rate_limit_metrics:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                metrics = self.redis_client.zrangebyscore(key, start_time, current_time)
                
                for metric_str in metrics:
                    try:
                        metric = json.loads(metric_str)
                        if metric.get('is_limited', False):
                            identifier = metric.get('identifier', 'unknown')
                            identifier_counts[identifier] = identifier_counts.get(identifier, 0) + 1
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Sort by count and return top N
            sorted_identifiers = sorted(identifier_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {'identifier': identifier, 'limited_count': count}
                for identifier, count in sorted_identifiers[:limit]
            ]
            
        except Exception as e:
            print(f"Top limited identifiers error: {e}")
            return []
    
    def cleanup_old_metrics(self) -> int:
        """Clean up old metrics data"""
        if not self.redis_client:
            return 0
            
        try:
            current_time = int(time.time())
            cleanup_interval = distributed_rate_limit_config.get_config('monitoring', 'cleanup_interval')
            cutoff_time = current_time - cleanup_interval
            
            pattern = "rate_limit_metrics:*"
            keys = self.redis_client.keys(pattern)
            cleaned_count = 0
            
            for key in keys:
                # Remove old entries
                removed = self.redis_client.zremrangebyscore(key, 0, cutoff_time)
                cleaned_count += removed
                
                # If key is empty, delete it
                if self.redis_client.zcard(key) == 0:
                    self.redis_client.delete(key)
            
            return cleaned_count
            
        except Exception as e:
            print(f"Metrics cleanup error: {e}")
            return 0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of rate limiting system"""
        try:
            if not self.redis_client:
                return {'status': 'unhealthy', 'reason': 'Redis not available'}
            
            # Test Redis connection
            self.redis_client.ping()
            
            # Get recent metrics
            metrics = self.get_metrics_summary(300)  # Last 5 minutes
            
            if metrics.get('status') == 'error':
                return {'status': 'degraded', 'reason': 'Metrics collection error'}
            
            # Check if alert threshold is exceeded
            if metrics.get('is_alert_threshold_exceeded', False):
                return {
                    'status': 'warning',
                    'reason': 'Rate limit threshold exceeded',
                    'limit_rate': metrics.get('limit_rate_percent', 0)
                }
            
            return {
                'status': 'healthy',
                'total_requests': metrics.get('total_requests', 0),
                'limit_rate': metrics.get('limit_rate_percent', 0)
            }
            
        except Exception as e:
            return {'status': 'unhealthy', 'reason': str(e)}

# Global metrics instance
rate_limit_metrics = RateLimitMetrics()
