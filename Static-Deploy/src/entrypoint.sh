#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Trap the SIGTERM signal and call the stop_service function
trap 'stop_service' SIGTERM

TORRC_PATH="/etc/tor/torrc"
DNS_TORRC_PATH="/etc/tor/dnstorrc"
INET_ADDR="$(hostname -i | awk '{print $1}')"
dashes='------------------------------------------------------------'
equals='============================================================'
log_dir="./log"
dnscrypt_conf=./dnscrypt/dnscrypt-proxy.toml


stop_service() {
  printf "%s\n" "$equals"  
  echo "[WIREGATE] Stopping WireGuard Dashboard and Tor."
  ./wiregate.sh stop
  pkill tor
  printf "[WIREGATE] Tor EXITED.\n"
  exit 0
}

ensure_blocking() {
  sleep 1s
  err_log=$(find ./log -name "error_*.log" | head -n 1)
  acc_log=$(find ./log -name "access_*.log" | head -n 1)
  if [ -n "$err_log" ] || [ -n "$acc_log" ]; then
    tail -f $err_log $acc_log &
  fi
  wait
}


#MAIN
################################




chmod u+x wiregate.sh





./wiregate.sh install

./wiregate.sh start 


ensure_blocking




