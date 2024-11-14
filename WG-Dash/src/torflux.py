# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License


import os
import time
from stem import Signal
from stem.control import Controller

# Define log directory and log file
log_dir = "./log"  # Change this to your log directory path
log_file = os.path.join(log_dir, "tor_circuit_refresh_log.txt")

# Ensure the log directory exists
os.makedirs(log_dir, exist_ok=True)

# Function to log messages
def log(message, add_newlines=False, to_console=False):
    # Get the current timestamp in the desired format
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the log message with the timestamp
    log_message = f"[{timestamp}] {message}"
    
    # Print the log message to the console only if to_console is True
    if to_console:
        print(log_message)
    
    # Write the log message to the log file
    with open(log_file, "a") as log_f:
        log_f.write(log_message + "\n")
        if add_newlines:
            log_f.write("\n" * 5)  # Add 5 empty lines after successful refresh

# Function to send NEWNYM signal to the Tor control port
def send_signal(port, password=None):
    log(f"[TOR] Sending NEWNYM signal to Control port {port}...", add_newlines=False, to_console=False)

    try:
        with Controller.from_port(port=port) as controller:
            # Authenticate with password if provided
            if password:
                controller.authenticate(password)
            else:
                controller.authenticate()

            # Send NEWNYM signal
            controller.signal(Signal.NEWNYM)
            log(f"[TOR] New Tor Circuits Requested Successfully on Control port {port}.", add_newlines=False, to_console=False)

            # Get circuit status (but don't print it to console)
            circuit_status = controller.get_info("circuit-status")
            with open(log_file, "a") as log_f:
                log_f.write(f"\n[TOR] Circuit status after NEWNYM signal:\n{circuit_status}\n")

            return circuit_status

    except Exception as e:
        log(f"[TOR] Failed to request new Tor circuit on Control port {port}: {e}", add_newlines=False, to_console=False)
        return None

# Function to check if the circuits are different
def circuits_are_different(old_status, new_status):
    # Simple comparison of the status strings (more advanced diff logic can be added)
    return old_status != new_status

# Ensure the control port password (VANGUARD) is set
VANGUARD = os.getenv("VANGUARD")
if not VANGUARD:
    log("Error: Tor control port password (VANGUARD) is not set.", add_newlines=False, to_console=False)
    exit(1)

# Main process to request a new Tor circuit if needed
log("Starting Tor circuit refresh...", add_newlines=False, to_console=False)

# Get initial circuit status for both control ports
old_circuit_status_9051 = send_signal(9051, VANGUARD)
if not old_circuit_status_9051:
    exit(1)

old_circuit_status_9054 = send_signal(9054, VANGUARD)
if not old_circuit_status_9054:
    exit(1)

# Compare the old circuit status with new status after sending NEWNYM signal
new_circuit_status_9051 = send_signal(9051, VANGUARD)
if not new_circuit_status_9051:
    exit(1)

new_circuit_status_9054 = send_signal(9054, VANGUARD)
if not new_circuit_status_9054:
    exit(1)

# Check if the circuit status has changed for both ports
if circuits_are_different(old_circuit_status_9051, new_circuit_status_9051) or \
   circuits_are_different(old_circuit_status_9054, new_circuit_status_9054):
    log("Tor circuits have been successfully refreshed.", add_newlines=True, to_console=True)
else:
    log("Tor circuits did not change. Retrying...", add_newlines=False, to_console=False)

    # Retry the circuit refresh until circuits change
    while old_circuit_status_9051 == new_circuit_status_9051 and \
          old_circuit_status_9054 == new_circuit_status_9054:
        log("Old circuits match new circuits. Requesting a new set of circuits.", add_newlines=False, to_console=False)
        
        new_circuit_status_9051 = send_signal(9051, VANGUARD)
        if not new_circuit_status_9051:
            exit(1)

        new_circuit_status_9054 = send_signal(9054, VANGUARD)
        if not new_circuit_status_9054:
            exit(1)

    log("Tor circuits have been successfully refreshed after retrying.", add_newlines=True, to_console=True)

log("Tor circuit refresh completed.", add_newlines=True, to_console=True)
