#!/usr/bin/env python3
# Metrics Collection and Reporting
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

"""
Metrics collection and reporting for stress tests.

Features:
- Collect metrics: throughput, latency, packet loss, connection count
- Separate metrics for raw TCP and WebSocket
- Export to JSON/CSV for analysis
- Generate HTML report
"""

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    mode: str  # tcp or websocket
    timestamp: str
    duration_seconds: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    loss_rate_percent: float = 0.0
    throughput_pps: float = 0.0
    throughput_mbps: float = 0.0
    latency_avg_ms: float = 0.0
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    errors: int = 0
    passed: bool = True
    details: Dict = field(default_factory=dict)


@dataclass
class TestSummary:
    """Summary of all tests."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    tcp_tests: int = 0
    websocket_tests: int = 0
    total_duration_seconds: float = 0.0
    total_packets_sent: int = 0
    total_packets_received: int = 0
    avg_loss_rate_percent: float = 0.0
    avg_latency_ms: float = 0.0


class MetricsCollector:
    """Collects and aggregates test metrics."""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.results: List[TestResult] = []
        self.summary = TestSummary()
    
    def collect_from_json(self, filepath: Path) -> Optional[TestResult]:
        """Parse a JSON result file and extract metrics."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Determine mode
            mode = data.get('mode', 'tcp')
            if 'websocket' in filepath.name.lower() or 'ws_' in filepath.name.lower():
                mode = 'websocket'
            
            # Extract test name from filename
            test_name = filepath.stem
            
            # Get timestamp
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            result = TestResult(
                test_name=test_name,
                mode=mode,
                timestamp=timestamp,
            )
            
            # Handle different result formats
            if 'packets_sent' in data:
                # UDP stress test format
                result.packets_sent = data.get('packets_sent', 0)
                result.packets_received = data.get('packets_received', 0)
                result.packets_lost = data.get('packets_lost', 0)
                result.loss_rate_percent = data.get('loss_rate_percent', 0)
                result.duration_seconds = data.get('duration_seconds', 0)
                result.throughput_pps = data.get('packets_per_second', 0)
                result.throughput_mbps = data.get('throughput_mbps', 0)
                result.errors = data.get('errors', 0)
                
                latency = data.get('latency_ms', {})
                result.latency_avg_ms = latency.get('avg', 0)
                result.latency_min_ms = latency.get('min', 0)
                result.latency_max_ms = latency.get('max', 0)
                result.latency_p50_ms = latency.get('p50', 0)
                result.latency_p95_ms = latency.get('p95', 0)
                result.latency_p99_ms = latency.get('p99', 0)
                
                result.passed = result.loss_rate_percent < 5
                
            elif 'handshake_success' in data:
                # WebSocket test format
                result.packets_sent = data.get('frames_sent', 0)
                result.packets_received = data.get('frames_received', 0)
                result.duration_seconds = data.get('duration_seconds', 0)
                result.latency_avg_ms = data.get('avg_latency_ms', 0)
                result.errors = len(data.get('errors', []))
                
                success = data.get('handshake_success', 0)
                failure = data.get('handshake_failure', 0)
                result.loss_rate_percent = (failure / (success + failure) * 100) if (success + failure) > 0 else 0
                result.passed = failure == 0
                
            elif 'tests' in data:
                # Aggregate result file
                for test in data.get('tests', []):
                    sub_result = TestResult(
                        test_name=test.get('test_name', test.get('name', 'unknown')),
                        mode=mode,
                        timestamp=timestamp,
                        packets_sent=test.get('packets_sent', 0),
                        packets_received=test.get('packets_received', 0),
                        packets_lost=test.get('packets_lost', 0),
                        loss_rate_percent=test.get('loss_rate_percent', 0),
                        duration_seconds=test.get('duration_seconds', 0),
                        throughput_pps=test.get('packets_per_second', 0),
                        latency_avg_ms=test.get('latency_ms', {}).get('avg', 0) if isinstance(test.get('latency_ms'), dict) else 0,
                        details=test,
                    )
                    sub_result.passed = sub_result.loss_rate_percent < 5
                    self.results.append(sub_result)
                return None
            
            result.details = data
            return result
            
        except Exception as e:
            print(f"Error parsing {filepath}: {e}", file=sys.stderr)
            return None
    
    def collect_all(self):
        """Collect metrics from all JSON files in results directory."""
        if not self.results_dir.exists():
            print(f"Results directory not found: {self.results_dir}")
            return
        
        for filepath in self.results_dir.glob('*.json'):
            result = self.collect_from_json(filepath)
            if result:
                self.results.append(result)
        
        self._calculate_summary()
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        if not self.results:
            return
        
        self.summary.total_tests = len(self.results)
        self.summary.passed_tests = sum(1 for r in self.results if r.passed)
        self.summary.failed_tests = sum(1 for r in self.results if not r.passed)
        self.summary.tcp_tests = sum(1 for r in self.results if r.mode == 'tcp')
        self.summary.websocket_tests = sum(1 for r in self.results if r.mode == 'websocket')
        self.summary.total_duration_seconds = sum(r.duration_seconds for r in self.results)
        self.summary.total_packets_sent = sum(r.packets_sent for r in self.results)
        self.summary.total_packets_received = sum(r.packets_received for r in self.results)
        
        loss_rates = [r.loss_rate_percent for r in self.results if r.loss_rate_percent > 0]
        self.summary.avg_loss_rate_percent = sum(loss_rates) / len(loss_rates) if loss_rates else 0
        
        latencies = [r.latency_avg_ms for r in self.results if r.latency_avg_ms > 0]
        self.summary.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
    
    def export_csv(self, filepath: str):
        """Export results to CSV."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'test_name', 'mode', 'timestamp', 'duration_seconds',
                'packets_sent', 'packets_received', 'packets_lost',
                'loss_rate_percent', 'throughput_pps', 'throughput_mbps',
                'latency_avg_ms', 'latency_p50_ms', 'latency_p95_ms', 'latency_p99_ms',
                'errors', 'passed'
            ])
            
            for r in self.results:
                writer.writerow([
                    r.test_name, r.mode, r.timestamp, r.duration_seconds,
                    r.packets_sent, r.packets_received, r.packets_lost,
                    r.loss_rate_percent, r.throughput_pps, r.throughput_mbps,
                    r.latency_avg_ms, r.latency_p50_ms, r.latency_p95_ms, r.latency_p99_ms,
                    r.errors, r.passed
                ])
        
        print(f"CSV exported to {filepath}")
    
    def export_json(self, filepath: str):
        """Export results to JSON."""
        data = {
            'summary': {
                'total_tests': self.summary.total_tests,
                'passed_tests': self.summary.passed_tests,
                'failed_tests': self.summary.failed_tests,
                'tcp_tests': self.summary.tcp_tests,
                'websocket_tests': self.summary.websocket_tests,
                'total_duration_seconds': round(self.summary.total_duration_seconds, 2),
                'total_packets_sent': self.summary.total_packets_sent,
                'total_packets_received': self.summary.total_packets_received,
                'avg_loss_rate_percent': round(self.summary.avg_loss_rate_percent, 2),
                'avg_latency_ms': round(self.summary.avg_latency_ms, 2),
            },
            'results': [
                {
                    'test_name': r.test_name,
                    'mode': r.mode,
                    'timestamp': r.timestamp,
                    'duration_seconds': r.duration_seconds,
                    'packets_sent': r.packets_sent,
                    'packets_received': r.packets_received,
                    'packets_lost': r.packets_lost,
                    'loss_rate_percent': r.loss_rate_percent,
                    'throughput_pps': r.throughput_pps,
                    'throughput_mbps': r.throughput_mbps,
                    'latency_avg_ms': r.latency_avg_ms,
                    'latency_p50_ms': r.latency_p50_ms,
                    'latency_p95_ms': r.latency_p95_ms,
                    'latency_p99_ms': r.latency_p99_ms,
                    'errors': r.errors,
                    'passed': r.passed,
                }
                for r in self.results
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"JSON exported to {filepath}")
    
    def generate_html_report(self, filepath: str):
        """Generate an HTML report."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>wg-tcp-tunnel Stress Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #eee; padding: 2rem; }}
        h1 {{ color: #00d4ff; margin-bottom: 1rem; }}
        h2 {{ color: #00ff88; margin: 2rem 0 1rem; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .card {{ background: #16213e; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .card h3 {{ color: #00d4ff; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 0.5rem; }}
        .card .value {{ font-size: 2rem; font-weight: bold; color: #fff; }}
        .card .unit {{ font-size: 0.8rem; color: #888; }}
        .passed {{ color: #00ff88; }}
        .failed {{ color: #ff4757; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #16213e; color: #00d4ff; }}
        tr:hover {{ background: #16213e; }}
        .tag {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }}
        .tag-tcp {{ background: #3498db; color: #fff; }}
        .tag-websocket {{ background: #9b59b6; color: #fff; }}
        .status-passed {{ background: #00ff88; color: #000; }}
        .status-failed {{ background: #ff4757; color: #fff; }}
    </style>
</head>
<body>
    <h1>wg-tcp-tunnel Stress Test Report</h1>
    <p style="color: #888; margin-bottom: 2rem;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary</h2>
    <div class="summary">
        <div class="card">
            <h3>Total Tests</h3>
            <div class="value">{self.summary.total_tests}</div>
        </div>
        <div class="card">
            <h3>Passed</h3>
            <div class="value passed">{self.summary.passed_tests}</div>
        </div>
        <div class="card">
            <h3>Failed</h3>
            <div class="value failed">{self.summary.failed_tests}</div>
        </div>
        <div class="card">
            <h3>TCP Tests</h3>
            <div class="value">{self.summary.tcp_tests}</div>
        </div>
        <div class="card">
            <h3>WebSocket Tests</h3>
            <div class="value">{self.summary.websocket_tests}</div>
        </div>
        <div class="card">
            <h3>Total Duration</h3>
            <div class="value">{self.summary.total_duration_seconds:.0f}</div>
            <div class="unit">seconds</div>
        </div>
        <div class="card">
            <h3>Packets Sent</h3>
            <div class="value">{self.summary.total_packets_sent:,}</div>
        </div>
        <div class="card">
            <h3>Avg Loss Rate</h3>
            <div class="value {'passed' if self.summary.avg_loss_rate_percent < 1 else 'failed'}">{self.summary.avg_loss_rate_percent:.2f}%</div>
        </div>
        <div class="card">
            <h3>Avg Latency</h3>
            <div class="value">{self.summary.avg_latency_ms:.2f}</div>
            <div class="unit">ms</div>
        </div>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Mode</th>
                <th>Duration</th>
                <th>Packets Sent</th>
                <th>Loss Rate</th>
                <th>Throughput</th>
                <th>Avg Latency</th>
                <th>P99 Latency</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for r in self.results:
            mode_class = 'tag-tcp' if r.mode == 'tcp' else 'tag-websocket'
            status_class = 'status-passed' if r.passed else 'status-failed'
            status_text = 'PASSED' if r.passed else 'FAILED'
            
            html += f"""
            <tr>
                <td>{r.test_name}</td>
                <td><span class="tag {mode_class}">{r.mode}</span></td>
                <td>{r.duration_seconds:.1f}s</td>
                <td>{r.packets_sent:,}</td>
                <td class="{'passed' if r.loss_rate_percent < 1 else 'failed'}">{r.loss_rate_percent:.2f}%</td>
                <td>{r.throughput_pps:.0f} pps</td>
                <td>{r.latency_avg_ms:.2f} ms</td>
                <td>{r.latency_p99_ms:.2f} ms</td>
                <td><span class="tag {status_class}">{status_text}</span></td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
</body>
</html>
"""
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        print(f"HTML report generated: {filepath}")
    
    def print_summary(self):
        """Print summary to console."""
        print("\n" + "=" * 60)
        print(" STRESS TEST METRICS SUMMARY")
        print("=" * 60)
        print(f"Total Tests:        {self.summary.total_tests}")
        print(f"Passed:             {self.summary.passed_tests}")
        print(f"Failed:             {self.summary.failed_tests}")
        print(f"TCP Tests:          {self.summary.tcp_tests}")
        print(f"WebSocket Tests:    {self.summary.websocket_tests}")
        print(f"Total Duration:     {self.summary.total_duration_seconds:.1f}s")
        print(f"Total Packets Sent: {self.summary.total_packets_sent:,}")
        print(f"Avg Loss Rate:      {self.summary.avg_loss_rate_percent:.2f}%")
        print(f"Avg Latency:        {self.summary.avg_latency_ms:.2f} ms")
        print("=" * 60 + "\n")
        
        if self.summary.failed_tests > 0:
            print("Failed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.test_name} ({r.mode}): loss={r.loss_rate_percent:.2f}%")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Metrics Collection and Reporting for Stress Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default="./stress-results",
        help="Directory containing test results (default: ./stress-results)"
    )
    parser.add_argument("--csv", type=str, help="Export to CSV file")
    parser.add_argument("--json", type=str, help="Export to JSON file")
    parser.add_argument("--html", type=str, help="Generate HTML report")
    parser.add_argument("--all", action="store_true", help="Export all formats")
    
    args = parser.parse_args()
    
    collector = MetricsCollector(args.results_dir)
    collector.collect_all()
    
    collector.print_summary()
    
    if args.all or args.csv:
        csv_path = args.csv or os.path.join(args.results_dir, "stress_results.csv")
        collector.export_csv(csv_path)
    
    if args.all or args.json:
        json_path = args.json or os.path.join(args.results_dir, "stress_results.json")
        collector.export_json(json_path)
    
    if args.all or args.html:
        html_path = args.html or os.path.join(args.results_dir, "stress_report.html")
        collector.generate_html_report(html_path)
    
    # Exit with error if any tests failed
    if collector.summary.failed_tests > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

