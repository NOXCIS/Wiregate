#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Use restricted shell for secure command execution
secure_exec() {
    /WireGate/restricted_shell.sh "$@"
}

# Trap signals and call the stop_service function
trap 'stop_service' SIGTERM SIGINT SIGQUIT


dashes='------------------------------------------------------------'
equals='============================================================'
dnscrypt_conf=./dnscrypt/dnscrypt-proxy.toml




stop_service() {
  printf "%s\n" "$equals"  
  echo "[WIREGATE] Received stop signal. Stopping WireGuard Dashboard and Tor."
  echo "[WIREGATE] DEBUG: Signal received at $(date)"
  
  # Set a timeout for graceful shutdown (10 seconds)
  timeout=10
  start_time=$(date +%s)
  
  # Stop the main wiregate process
  echo "[WIREGATE] DEBUG: Starting wiregate.sh stop process"
  ./wiregate.sh stop &
  local stop_pid=$!
  echo "[WIREGATE] DEBUG: Stop process PID: $stop_pid"
  
  # Wait for graceful shutdown with timeout
  while kill -0 "$stop_pid" 2>/dev/null; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [ $elapsed -ge $timeout ]; then
      echo "[WIREGATE] Graceful shutdown timeout reached after ${elapsed}s. Force killing processes..."
      kill -KILL "$stop_pid" 2>/dev/null || true
      break
    fi
    sleep 0.1
  done
  
  # Force kill any remaining processes immediately
  # Since we don't have ps/pgrep, we'll rely on the main stop process
  # to handle cleanup through the wiregate.sh script
  # Additional cleanup will be handled by the main process
  
  printf "[WIREGATE] All processes stopped.\n"
  printf "%s\n" "$equals"
  exit 0
}


if [[ "$WGD_TOR_DNSCRYPT" == "true" ]]; then
        secure_exec sed -i "s/^#\(proxy = 'socks5:\/\/wiregate:9053'\)/\1/" "$dnscrypt_conf"
        else
            secure_exec sed -i "s/^\(proxy = 'socks5:\/\/wiregate:9053'\)/#\1/" "$dnscrypt_conf"
    fi

if [ ! -d "log" ]
	  then 
		printf "[WIREGATE] Creating WireGate Logs folder\n"
		secure_exec mkdir "log"
	fi
    if [ ! -d "db" ] 
		then 
			secure_exec mkdir "db"
    fi
    if [ ! -d "SSL_CERT" ] 
		then 
			secure_exec mkdir "SSL_CERT"
    fi

#MAIN
################################




secure_exec chmod u+x wiregate.sh

# Initialize Cloudflare Warp if enabled
if [[ "$WGD_WARP_ENABLED" == "true" ]]; then
    printf "%s\n" "$dashes"
    echo "[WARP] Cloudflare Warp is enabled. Initializing..."
    printf "%s\n" "$dashes"
    if /WireGate/warp-manager.sh setup; then
        printf "%s\n" "$dashes"
        echo "[WARP] ✓ Cloudflare Warp initialized successfully"
        printf "%s\n" "$dashes"
    else
        printf "%s\n" "$dashes"
        echo "[WARP] WARNING: Failed to initialize Cloudflare Warp"
        echo "[WARP] Traffic will use default routing"
        printf "%s\n" "$dashes"
    fi
else
    echo "[WARP] Cloudflare Warp is disabled. Skipping initialization."
fi

./wiregate.sh install

./wiregate.sh start &

# Keep the script running to handle signals
while true; do
    sleep 1
done 






