#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

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
  pkill -f tor 2>/dev/null || true
  
  # Kill any remaining wiregate processes
  pkill -f wiregate 2>/dev/null || true
  
  # Kill any remaining vanguards processes
  pkill -f vanguards 2>/dev/null || true
  
  # Kill any remaining torflux processes
  pkill -f torflux 2>/dev/null || true
  
  printf "[WIREGATE] All processes stopped.\n"
  printf "%s\n" "$equals"
  exit 0
}


if [[ "$WGD_TOR_DNSCRYPT" == "true" ]]; then
        sed -i "s/^#\(proxy = 'socks5:\/\/wiregate:9053'\)/\1/" "$dnscrypt_conf"
        else
            sed -i "s/^\(proxy = 'socks5:\/\/wiregate:9053'\)/#\1/" "$dnscrypt_conf"
    fi

if [ ! -d "log" ]
	  then 
		printf "[WIREGATE] Creating WireGate Logs folder\n"
		mkdir "log"
	fi
    if [ ! -d "db" ] 
		then 
			mkdir "db"
    fi
    if [ ! -d "SSL_CERT" ] 
		then 
			mkdir "SSL_CERT"
    fi

#MAIN
################################




chmod u+x wiregate.sh





./wiregate.sh install

./wiregate.sh start 






