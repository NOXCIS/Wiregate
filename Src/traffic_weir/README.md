# Traffic-Weir - Modular Architecture

This is the modularized version of the traffic-weir tool, split into logical modules for better maintainability and organization.

## Module Structure

### `/config` - Configuration and Types
- **Purpose**: Centralized configuration constants, types, and global variables
- **Key Components**:
  - Constants for paths, file names, and rate limits
  - `PeerInfo` struct for peer information
  - `SystemCapabilities` struct for system capabilities
  - Global variables for scheduler type, 64-bit support, and executable paths

### `/logger` - Logging System
- **Purpose**: Centralized logging functionality
- **Key Components**:
  - Logger initialization with file and console output
  - Global logger instance accessible throughout the application

### `/peer` - Peer Management
- **Purpose**: WireGuard/AmneziaWG peer discovery and information retrieval
- **Key Components**:
  - Executable discovery for `wg` and `awg` commands
  - Peer information parsing from command output
  - Support for both WireGuard and AmneziaWG protocols

### `/qdisc` - Queue Discipline Management
- **Purpose**: Traffic control qdisc setup, management, and cleanup
- **Key Components**:
  - Smart qdisc detection and preservation logic
  - Scheduler type conflict resolution
  - Interface nuking functionality
  - Root qdisc setup for different scheduler types

### `/scheduler` - Traffic Schedulers
- **Purpose**: Implementation of different traffic scheduling algorithms
- **Key Components**:
  - **`scheduler.go`**: Core scheduler functionality (HTB, HFSC)
  - **`cake.go`**: CAKE scheduler implementation
  - **`filters.go`**: Traffic filtering and classification
  - **`removal.go`**: Rate limit removal and cleanup
  - Rate validation and system capability detection

### `/ifb` - IFB Device Management
- **Purpose**: Intermediate Functional Block device setup and management
- **Key Components**:
  - IFB device creation and configuration
  - Ingress traffic redirection
  - Basic traffic shaping fallback
  - IFB support detection

### `/main.go` - Application Entry Point
- **Purpose**: CLI interface and orchestration
- **Key Components**:
  - Command-line argument parsing
  - Application flow orchestration
  - Error handling and cleanup
  - Integration of all modules

## Key Features

### Smart Scheduler Management
- **Preservation Logic**: Automatically preserves existing qdiscs when other peers have active rate limits
- **Smart Swapping**: Swaps scheduler types when no active peers exist
- **Conflict Resolution**: Warns users about scheduler conflicts and provides guidance

### Multi-Protocol Support
- **WireGuard**: Native support for WireGuard VPN
- **AmneziaWG**: Support for AmneziaWG protocol
- **Dynamic Discovery**: Automatically finds executable paths

### Robust Error Handling
- **Graceful Degradation**: Falls back to basic traffic shaping when IFB is not supported
- **Comprehensive Cleanup**: Emergency cleanup on errors
- **Detailed Logging**: Extensive logging for debugging and monitoring

## Usage

The modular structure maintains the same CLI interface as the original:

```bash
# Set rate limits
./traffic-weir -interface wg0 -peer <peer-key> -upload-rate 1000 -download-rate 2000 -scheduler htb

# Remove rate limits
./traffic-weir -interface wg0 -peer <peer-key> -remove

# Nuke interface (remove all traffic control)
./traffic-weir -interface wg0 -nuke

# Use different scheduler
./traffic-weir -interface wg0 -peer <peer-key> -scheduler hfsc -upload-rate 1000
```

## Benefits of Modular Architecture

1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Individual modules can be unit tested
3. **Reusability**: Modules can be imported by other projects
4. **Clarity**: Clear separation of concerns
5. **Extensibility**: Easy to add new schedulers or features

## Module Dependencies

```
main.go
├── config (no dependencies)
├── logger (depends on config)
├── peer (depends on logger, config)
├── qdisc (depends on logger, config)
├── scheduler (depends on logger, config)
└── ifb (depends on logger, config, qdisc)
```

This modular structure makes the codebase much more maintainable and easier to understand while preserving all the original functionality.
