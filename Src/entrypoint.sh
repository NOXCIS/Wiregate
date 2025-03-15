#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Trap the SIGTERM signal and call the stop_service function
trap 'stop_service' SIGTERM


dashes='------------------------------------------------------------'
equals='============================================================'
dnscrypt_conf=./dnscrypt/dnscrypt-proxy.toml




stop_service() {
  printf "%s\n" "$equals"  
  echo "[WIREGATE] Stopping WireGuard Dashboard and Tor."
  ./wiregate.sh stop
  pkill tor
  printf "[WIREGATE] Tor EXITED.\n"
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






