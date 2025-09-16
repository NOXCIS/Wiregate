"""
Distributed Rate Limiting Configuration
Provides configuration management for distributed rate limiting features
"""
import os
from typing import Dict, Any

class DistributedRateLimitConfig:
    """Configuration for distributed rate limiting"""
    
    def __init__(self):
        # Default configuration
        self.config = {
            'enabled': os.getenv('DISTRIBUTED_RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            'redis_cluster_enabled': os.getenv('REDIS_CLUSTER_ENABLED', 'false').lower() == 'true',
            'redis_cluster_nodes': os.getenv('REDIS_CLUSTER_NODES', '').split(',') if os.getenv('REDIS_CLUSTER_NODES') else [],
            'default_limits': {
                'api_requests': int(os.getenv('API_RATE_LIMIT', '100')),
                'auth_requests': int(os.getenv('AUTH_RATE_LIMIT', '5')),
                'burst_requests': int(os.getenv('BURST_RATE_LIMIT', '25')),
                'window_seconds': int(os.getenv('RATE_LIMIT_WINDOW', '60')),
                'burst_window_seconds': int(os.getenv('BURST_WINDOW', '60'))
            },
            'advanced_features': {
                'sliding_window_enabled': os.getenv('SLIDING_WINDOW_ENABLED', 'true').lower() == 'true',
                'burst_protection_enabled': os.getenv('BURST_PROTECTION_ENABLED', 'true').lower() == 'true',
                'adaptive_limits_enabled': os.getenv('ADAPTIVE_LIMITS_ENABLED', 'false').lower() == 'true',
                'geo_distributed_enabled': os.getenv('GEO_DISTRIBUTED_ENABLED', 'false').lower() == 'true'
            },
            'monitoring': {
                'metrics_enabled': os.getenv('RATE_LIMIT_METRICS_ENABLED', 'true').lower() == 'true',
                'alert_threshold': float(os.getenv('RATE_LIMIT_ALERT_THRESHOLD', '0.8')),
                'cleanup_interval': int(os.getenv('RATE_LIMIT_CLEANUP_INTERVAL', '300'))
            }
        }
    
    def get_config(self, section: str = None, key: str = None) -> Any:
        """Get configuration value"""
        if section is None:
            return self.config
        
        if key is None:
            return self.config.get(section, {})
        
        return self.config.get(section, {}).get(key)
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """Update configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return True
        except Exception:
            return False
    
    def get_rate_limits_for_endpoint(self, endpoint: str) -> Dict[str, int]:
        """Get rate limits for a specific endpoint"""
        endpoint_limits = {
            '/authenticate': {
                'limit': self.get_config('default_limits', 'auth_requests'),
                'window': self.get_config('default_limits', 'window_seconds'),
                'burst_limit': self.get_config('default_limits', 'burst_requests')
            },
            '/api/': {
                'limit': self.get_config('default_limits', 'api_requests'),
                'window': self.get_config('default_limits', 'window_seconds'),
                'burst_limit': self.get_config('default_limits', 'burst_requests')
            },
            'default': {
                'limit': self.get_config('default_limits', 'api_requests'),
                'window': self.get_config('default_limits', 'window_seconds'),
                'burst_limit': self.get_config('default_limits', 'burst_requests')
            }
        }
        
        # Find matching endpoint configuration
        for pattern, limits in endpoint_limits.items():
            if endpoint.startswith(pattern):
                return limits
        
        return endpoint_limits['default']
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get_config('advanced_features', feature) or False
    
    def get_redis_cluster_config(self) -> Dict[str, Any]:
        """Get Redis cluster configuration"""
        return {
            'enabled': self.get_config('redis_cluster_enabled'),
            'nodes': self.get_config('redis_cluster_nodes'),
            'password': os.getenv('REDIS_PASSWORD'),
            'timeout': int(os.getenv('REDIS_TIMEOUT', '5')),
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '100'))
        }

# Global configuration instance
distributed_rate_limit_config = DistributedRateLimitConfig()
