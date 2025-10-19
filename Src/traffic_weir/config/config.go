package config

const (
	TCPath    = "/sbin/tc"
	IFBFormat = "ifb-%s" // Will be formatted with interface name
	LogFile   = "traffic-weir.log"
	// Maximum rates in Kb/s
	MaxRate32 = 4194303 // 32-bit max: ~4.2 Gb/s
	MaxRate64 = 4194303 // 64-bit max: ~18.4 Pb/s
)

// PeerInfo represents information about a WireGuard/AmneziaWG peer
type PeerInfo struct {
	PublicKey  string
	AllowedIPs []string
}

// SystemCapabilities represents the system's traffic control capabilities
type SystemCapabilities struct {
	Supports64BitRates bool   `json:"supports_64bit_rates"`
	MaximumRate        int64  `json:"maximum_rate_kbps"`
	SchedulerType      string `json:"scheduler_type"`
}

// Global configuration variables
var (
	SchedulerType string
	Supports64Bit bool
	WGPath        string // Dynamic path for wg
	AWGPath       string // Dynamic path for awg
)
