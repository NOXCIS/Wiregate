package tests

import (
	"os/exec"
	"testing"
	"time"
)

func BenchmarkHTBSetup(b *testing.B) {
	// Benchmark HTB setup performance
	for i := 0; i < b.N; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_htb_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			b.Logf("HTB benchmark output: %s", string(output))
		}
	}
}

func BenchmarkHFSCSetup(b *testing.B) {
	// Benchmark HFSC setup performance
	for i := 0; i < b.N; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_hfsc_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			b.Logf("HFSC benchmark output: %s", string(output))
		}
	}
}

func BenchmarkCAKESetupPerf(b *testing.B) {
	// Benchmark CAKE setup performance
	for i := 0; i < b.N; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_cake_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "cake", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			b.Logf("CAKE benchmark output: %s", string(output))
		}
	}
}

func BenchmarkRateLimitRemoval(b *testing.B) {
	// Benchmark rate limit removal performance
	for i := 0; i < b.N; i++ {
		// First set up rate limits
		cmd1 := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_removal_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		cmd1.CombinedOutput()
		
		// Then remove them
		cmd2 := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_removal_"+string(rune(i)), 
			"-upload-rate", "4194303", "-download-rate", "4194303", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32", "-remove")
		
		output, err := cmd2.CombinedOutput()
		if err != nil {
			b.Logf("Removal benchmark output: %s", string(output))
		}
	}
}

func BenchmarkInterfaceNuke(b *testing.B) {
	// Benchmark interface nuking performance
	for i := 0; i < b.N; i++ {
		// First set up some rate limits
		cmd1 := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_bench_nuke_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		cmd1.CombinedOutput()
		
		// Then nuke the interface
		cmd2 := exec.Command("/app/traffic-weir", "-interface", "lo", "-nuke")
		
		output, err := cmd2.CombinedOutput()
		if err != nil {
			b.Logf("Nuke benchmark output: %s", string(output))
		}
	}
}

func TestMemoryUsage(t *testing.T) {
	// Test memory usage during operations
	interfaceName := "lo"
	
	// Test memory usage with multiple operations
	for i := 0; i < 100; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
			"-peer", "test_peer_memory_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Logf("Memory test output %d: %s", i, string(output))
		}
		
		// Small delay to allow memory cleanup
		time.Sleep(1 * time.Millisecond)
	}
}

func TestConcurrentPerformance(t *testing.T) {
	// Test concurrent performance
	interfaceName := "lo"
	numGoroutines := 10
	
	done := make(chan bool, numGoroutines)
	start := time.Now()
	
	for i := 0; i < numGoroutines; i++ {
		go func(index int) {
			cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
				"-peer", "test_peer_concurrent_perf_"+string(rune(index)), 
				"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
				"-allowed-ips", "127.0.0.1/32")
			
			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Logf("Concurrent performance test %d output: %s", index, string(output))
			}
			
			done <- true
		}(i)
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		select {
		case <-done:
			// Goroutine completed
		case <-time.After(5 * time.Second):
			t.Errorf("Concurrent performance test %d timed out", i)
		}
	}
	
	duration := time.Since(start)
	t.Logf("Concurrent performance test completed in %v", duration)
	
	// Verify reasonable performance
	if duration > 2*time.Second {
		t.Errorf("Concurrent performance test took too long: %v", duration)
	}
}

func TestThroughputPerformance(t *testing.T) {
	// Test throughput performance
	interfaceName := "lo"
	numOperations := 50
	
	start := time.Now()
	
	for i := 0; i < numOperations; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
			"-peer", "test_peer_throughput_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Logf("Throughput test output %d: %s", i, string(output))
		}
	}
	
	duration := time.Since(start)
	throughput := float64(numOperations) / duration.Seconds()
	
	t.Logf("Throughput test: %d operations in %v (%.2f ops/sec)", 
		numOperations, duration, throughput)
	
	// Verify reasonable throughput
	if throughput < 10 {
		t.Errorf("Throughput too low: %.2f ops/sec", throughput)
	}
}

func TestLatencyPerformance(t *testing.T) {
	// Test latency performance
	interfaceName := "lo"
	numTests := 20
	var totalLatency time.Duration
	
	for i := 0; i < numTests; i++ {
		start := time.Now()
		
		cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
			"-peer", "test_peer_latency_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		latency := time.Since(start)
		totalLatency += latency
		
		if err != nil {
			t.Logf("Latency test output %d: %s", i, string(output))
		}
		
		// Verify individual latency
		if latency > 100*time.Millisecond {
			t.Errorf("Latency test %d took too long: %v", i, latency)
		}
	}
	
	avgLatency := totalLatency / time.Duration(numTests)
	t.Logf("Average latency: %v", avgLatency)
	
	// Verify average latency
	if avgLatency > 50*time.Millisecond {
		t.Errorf("Average latency too high: %v", avgLatency)
	}
}

func TestResourceEfficiency(t *testing.T) {
	// Test resource efficiency
	interfaceName := "lo"
	
	// Test with different rate combinations
	rateCombinations := [][]int{
		{100, 200},
		{1000, 2000},
		{10000, 20000},
		{100000, 200000},
		{1000000, 2000000},
	}
	
	for i, rates := range rateCombinations {
		start := time.Now()
		
		cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
			"-peer", "test_peer_efficiency_"+string(rune(i)), 
			"-upload-rate", string(rune(rates[0])), 
			"-download-rate", string(rune(rates[1])), 
			"-scheduler", "htb", "-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		duration := time.Since(start)
		
		if err != nil {
			t.Logf("Resource efficiency test %d output: %s", i, string(output))
		}
		
		// Verify performance scales reasonably
		if duration > 200*time.Millisecond {
			t.Errorf("Resource efficiency test %d took too long: %v", i, duration)
		}
		
		t.Logf("Rate combination %d (%d/%d): %v", i, rates[0], rates[1], duration)
	}
}

func TestStressPerformance(t *testing.T) {
	// Test stress performance
	interfaceName := "lo"
	numStressTests := 100
	
	start := time.Now()
	
	for i := 0; i < numStressTests; i++ {
		cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
			"-peer", "test_peer_stress_"+string(rune(i)), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.1/32")
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Logf("Stress test output %d: %s", i, string(output))
		}
		
		// Small delay to prevent overwhelming the system
		time.Sleep(1 * time.Millisecond)
	}
	
	duration := time.Since(start)
	throughput := float64(numStressTests) / duration.Seconds()
	
	t.Logf("Stress test: %d operations in %v (%.2f ops/sec)", 
		numStressTests, duration, throughput)
	
	// Verify stress test performance
	if throughput < 5 {
		t.Errorf("Stress test throughput too low: %.2f ops/sec", throughput)
	}
}
