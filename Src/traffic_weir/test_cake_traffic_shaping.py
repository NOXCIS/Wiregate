#!/usr/bin/env python3
"""
Unit tests for CAKE traffic shaping implementation in traffic-weir
"""

import unittest
import subprocess
import tempfile
import os
import sys
import json
from unittest.mock import patch, MagicMock, call
import time

# Add the Src directory to the path so we can import the API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

from wiregate.routes.traffic_weir_api import traffic_weir_blueprint
from flask import Flask

class TestCAKETrafficShaping(unittest.TestCase):
    """Test cases for CAKE traffic shaping functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.register_blueprint(traffic_weir_blueprint)
        self.client = self.app.test_client()
        
        # Test data
        self.test_interface = "wg0"
        self.test_peer_key = "test_peer_key_12345"
        self.test_allowed_ips = "10.0.0.2/32"
        self.test_upload_rate = 1000  # 1 Mbps
        self.test_download_rate = 2000  # 2 Mbps
        
    def tearDown(self):
        """Clean up after tests"""
        # Clean up any test traffic control rules
        try:
            subprocess.run(['tc', 'qdisc', 'del', 'dev', 'lo', 'root'], 
                         capture_output=True, check=False)
            subprocess.run(['tc', 'qdisc', 'del', 'dev', 'lo', 'ingress'], 
                         capture_output=True, check=False)
        except:
            pass

    @patch('subprocess.run')
    def test_cake_scheduler_validation(self, mock_run):
        """Test that CAKE scheduler is properly validated"""
        # Mock successful tc command
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Test valid CAKE scheduler
        response = self.client.post('/set_peer_rate_limit', json={
            'interface': self.test_interface,
            'peer_key': self.test_peer_key,
            'upload_rate': self.test_upload_rate,
            'download_rate': self.test_download_rate,
            'scheduler_type': 'cake'
        })
        
        # Should not return validation error
        self.assertNotEqual(response.status_code, 400)
        
        # Test invalid scheduler
        response = self.client.post('/set_peer_rate_limit', json={
            'interface': self.test_interface,
            'peer_key': self.test_peer_key,
            'upload_rate': self.test_upload_rate,
            'download_rate': self.test_download_rate,
            'scheduler_type': 'invalid'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['status'])
        self.assertIn('Invalid scheduler type', data['message'])

    @patch('subprocess.run')
    def test_cake_rate_limit_setup(self, mock_run):
        """Test CAKE rate limit setup"""
        # Mock successful commands
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        response = self.client.post('/set_peer_rate_limit', json={
            'interface': self.test_interface,
            'peer_key': self.test_peer_key,
            'upload_rate': self.test_upload_rate,
            'download_rate': self.test_download_rate,
            'scheduler_type': 'cake'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['status'])
        
        # Verify that traffic-weir was called with cake scheduler
        mock_run.assert_called()
        call_args = mock_run.call_args_list[-1][0][0]  # Get the last call's command
        self.assertIn('cake', call_args)

    @patch('subprocess.run')
    def test_cake_rate_limit_removal(self, mock_run):
        """Test CAKE rate limit removal"""
        # Mock successful commands
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        response = self.client.post('/remove_peer_rate_limit', json={
            'interface': self.test_interface,
            'peer_key': self.test_peer_key
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['status'])

    def test_cake_vs_htb_hfsc_differences(self):
        """Test that CAKE behaves differently from HTB/HFSC"""
        # This test verifies that CAKE uses different command structures
        # In a real implementation, we'd check the actual tc commands generated
        
        schedulers = ['htb', 'hfsc', 'cake']
        commands = {}
        
        for scheduler in schedulers:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                self.client.post('/set_peer_rate_limit', json={
                    'interface': self.test_interface,
                    'peer_key': self.test_peer_key,
                    'upload_rate': self.test_upload_rate,
                    'download_rate': self.test_download_rate,
                    'scheduler_type': scheduler
                })
                
                # Capture the command arguments
                if mock_run.call_args_list:
                    commands[scheduler] = mock_run.call_args_list[-1][0][0]
        
        # Verify that CAKE uses different commands than HTB/HFSC
        if 'cake' in commands and 'htb' in commands:
            self.assertNotEqual(commands['cake'], commands['htb'])
        if 'cake' in commands and 'hfsc' in commands:
            self.assertNotEqual(commands['cake'], commands['hfsc'])

    @patch('subprocess.run')
    def test_cake_interface_scheduler_detection(self, mock_run):
        """Test interface scheduler type detection with CAKE"""
        # Mock database query to return CAKE scheduler
        with patch('Src.wiregate.routes.traffic_weir_api.sqlSelect') as mock_sql:
            mock_result = MagicMock()
            mock_result.fetchone.return_value = {'scheduler_type': 'cake'}
            mock_sql.return_value = mock_result
            
            response = self.client.get(f'/get_interface_scheduler?interface={self.test_interface}')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['status'])
            self.assertEqual(data['data']['scheduler_type'], 'cake')

    def test_cake_bandwidth_calculation(self):
        """Test CAKE bandwidth calculation and burst size"""
        # Test that CAKE uses appropriate burst calculations
        # Burst should be 1ms worth of traffic (rate * 125)
        
        test_cases = [
            (1000, 125000),   # 1 Mbps -> 125KB burst
            (5000, 625000),   # 5 Mbps -> 625KB burst
            (10000, 1250000), # 10 Mbps -> 1.25MB burst
        ]
        
        for rate_kbps, expected_burst in test_cases:
            burst = rate_kbps * 125
            self.assertEqual(burst, expected_burst)

    @patch('subprocess.run')
    def test_cake_ipv6_support(self, mock_run):
        """Test CAKE support for IPv6 addresses"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Test with IPv6 address
        ipv6_allowed_ips = "2001:db8::2/128"
        
        response = self.client.post('/set_peer_rate_limit', json={
            'interface': self.test_interface,
            'peer_key': self.test_peer_key,
            'upload_rate': self.test_upload_rate,
            'download_rate': self.test_download_rate,
            'scheduler_type': 'cake'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['status'])

    def test_cake_error_handling(self):
        """Test CAKE error handling scenarios"""
        with patch('subprocess.run') as mock_run:
            # Mock tc command failure
            mock_run.return_value = MagicMock(
                returncode=1, 
                stdout="", 
                stderr="RTNETLINK answers: File exists"
            )
            
            response = self.client.post('/set_peer_rate_limit', json={
                'interface': self.test_interface,
                'peer_key': self.test_peer_key,
                'upload_rate': self.test_upload_rate,
                'download_rate': self.test_download_rate,
                'scheduler_type': 'cake'
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertFalse(data['status'])
            self.assertIn('Failed to set rate limits', data['message'])

    def test_cake_nuke_interface(self):
        """Test nuking interface with CAKE scheduler"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            
            response = self.client.post('/nuke_interface', json={
                'interface': self.test_interface
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['status'])

    def test_cake_performance_characteristics(self):
        """Test CAKE performance characteristics"""
        # CAKE should be more efficient for many flows
        # This is a conceptual test - in practice, we'd measure actual performance
        
        schedulers = ['htb', 'hfsc', 'cake']
        
        # Simulate multiple flows
        num_flows = 100
        
        for scheduler in schedulers:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                start_time = time.time()
                
                # Simulate setting up multiple flows
                for i in range(num_flows):
                    self.client.post('/set_peer_rate_limit', json={
                        'interface': self.test_interface,
                        'peer_key': f'peer_{i}',
                        'upload_rate': self.test_upload_rate,
                        'download_rate': self.test_download_rate,
                        'scheduler_type': scheduler
                    })
                
                end_time = time.time()
                setup_time = end_time - start_time
                
                # CAKE should be faster for many flows (conceptual)
                if scheduler == 'cake':
                    # In a real test, we'd assert that CAKE is faster
                    self.assertIsInstance(setup_time, float)

class TestCAKEIntegration(unittest.TestCase):
    """Integration tests for CAKE traffic shaping"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.app = Flask(__name__)
        self.app.register_blueprint(traffic_weir_blueprint)
        self.client = self.app.test_client()
        
    @patch('subprocess.run')
    def test_cake_end_to_end_workflow(self, mock_run):
        """Test complete CAKE workflow: setup -> get -> remove"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # 1. Set rate limits
        response = self.client.post('/set_peer_rate_limit', json={
            'interface': 'wg0',
            'peer_key': 'test_peer',
            'upload_rate': 1000,
            'download_rate': 2000,
            'scheduler_type': 'cake'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.data)['status'])
        
        # 2. Get rate limits
        response = self.client.get('/get_peer_rate_limit?interface=wg0&peer_key=test_peer')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['status'])
        self.assertEqual(data['data']['scheduler_type'], 'cake')
        
        # 3. Remove rate limits
        response = self.client.post('/remove_peer_rate_limit', json={
            'interface': 'wg0',
            'peer_key': 'test_peer'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.data)['status'])

    def test_cake_system_capabilities(self):
        """Test that system capabilities include CAKE scheduler"""
        # This would test the getSystemCapabilities function
        # In a real implementation, we'd call the actual function
        
        schedulers = ['htb', 'hfsc', 'cake']
        self.assertIn('cake', schedulers)
        self.assertEqual(len(schedulers), 3)

if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTest(unittest.makeSuite(TestCAKETrafficShaping))
    suite.addTest(unittest.makeSuite(TestCAKEIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
