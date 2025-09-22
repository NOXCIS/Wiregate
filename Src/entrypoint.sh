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
  
  # Stop the main wiregate process
  ./wiregate.sh stop
  
  # Kill any remaining tor processes
  secure_exec pkill -f tor 2>/dev/null || true
  
  # Kill any remaining wiregate processes
  secure_exec pkill -f wiregate 2>/dev/null || true
  
  # Kill any remaining vanguards processes
  secure_exec pkill -f vanguards 2>/dev/null || true
  
  # Kill any remaining torflux processes
  secure_exec pkill -f torflux 2>/dev/null || true
  
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





./wiregate.sh install

./wiregate.sh start 






