#!/bin/bash

# wgd.sh - Copyright(C) 2021 Donald Zou [https://github.com/donaldzou]
# Under Apache-2.0 License
app_name="dashboard.py"
app_official_name="WGDashboard"
environment=$(if [[ $ENVIRONMENT ]]; then echo $ENVIRONMENT; else echo 'develop'; fi)
if [[ $CONFIGURATION_PATH ]]; then
  cb_work_dir=$CONFIGURATION_PATH/letsencrypt/work-dir
  cb_config_dir=$CONFIGURATION_PATH/letsencrypt/config-dir
else
  cb_work_dir=/etc/letsencrypt
  cb_config_dir=/var/lib/letsencrypt
fi

dashes='------------------------------------------------------------'
equals='============================================================'
help () {
  printf "=================================================================================\n"
  printf "+          <WGDashboard> by Donald Zou - https://github.com/donaldzou           +\n"
  printf "=================================================================================\n"
  printf "| Usage: ./wgd.sh <option>                                                      |\n"
  printf "|                                                                               |\n"
  printf "| Available options:                                                            |\n"
  printf "|    start: To start WGDashboard.                                               |\n"
  printf "|    stop: To stop WGDashboard.                                                 |\n"
  printf "|    debug: To start WGDashboard in debug mode (i.e run in foreground).         |\n"
  printf "|    update: To update WGDashboard to the newest version from GitHub.           |\n"
  printf "|    install: To install WGDashboard.                                           |\n"
  printf "| Thank you for using! Your support is my motivation ;)                         |\n"
  printf "=================================================================================\n"
}

_check_and_set_venv(){
    # This function will not be using in v3.0
    # deb/ubuntu users: might need a 'apt install python3.8-venv'
    # set up the local environment
    APP_ROOT=`pwd`
    VIRTUAL_ENV="${APP_ROOT%/*}/venv"
    if [ ! -d $VIRTUAL_ENV ]; then
        python3 -m venv $VIRTUAL_ENV
    fi
    . ${VIRTUAL_ENV}/bin/activate
}

install_wgd(){
    printf "| Starting to install WGDashboard                          |\n"
    if [ ! -d "db" ]
      then mkdir "db"
    fi
    if [ ! -d "log" ]
      then mkdir "log"
    fi
    printf "| Upgrading pip                                            |\n"
    pip3 install --upgrade pip > /dev/null 2>&1
    printf "| Installing latest Python dependencies                    |\n"
    pip3 install -r requirements.txt 
    printf "| WGDashboard installed successfully!                      |\n"
    printf "| Enter ./wgd.sh start to start the dashboard              |\n"
}

start_wgd () {
    uwsgi -i wgd-uwsgi-conf.ini
}



newconf_wgd() {
  local num_configs=$CONFIG_CT
  local listen_port=51820
  local address_prefix="10.0."

  for ((i = 0; i < num_configs; i++)); do
    local listen_port_str="ListenPort = $listen_port"
    local address_str="Address = ${address_prefix}$((i + 1)).1/32"
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    local file_number=$((i))
    if [[ $file_number -eq 0 ]]; then
      file_number="0"
    fi

    cat <<EOF >"/etc/wireguard/wg$file_number.conf"
[Interface]
PrivateKey = $private_key
$listen_port_str
$address_str
SaveConfig = true
PostUp = iptables -t nat -I POSTROUTING -o eth0 -j MASQUERADE
PreDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

    echo "Generated wg$file_number.conf"
    ((listen_port++))
  done
}

check_wgd_status(){
  if test -f "$PID_FILE"; then
    if ps aux | grep -v grep | grep $(cat ./gunicorn.pid)  > /dev/null; then
    return 0
    else
      return 1
    fi
  else
    if ps aux | grep -v grep | grep '[p]ython3 '$app_name > /dev/null; then
      return 0
    else
      return 1
    fi
  fi
}

start_wgd_debug() {
  printf "%s\n" "$dashes"
  printf "| Starting WGDashboard in the foreground.                  |\n"
  python3 "$app_name"
  printf "%s\n" "$dashes"
}

update_wgd() {
  new_ver=$(python3 -c "import json; import urllib.request; data = urllib.request.urlopen('https://api.github.com/repos/donaldzou/WGDashboard/releases/latest').read(); output = json.loads(data);print(output['tag_name'])")
  printf "%s\n" "$dashes"
  printf "| Are you sure you want to update to the %s? (Y/N): " "$new_ver"
  read up
  if [ "$up" = "Y" ]; then
    printf "| Shutting down WGDashboard...                             |\n"
    if check_wgd_status; then
      stop_wgd
    fi
    mv wgd.sh wgd.sh.old
    printf "| Downloading %s from GitHub...                            |\n" "$new_ver"
    git stash > /dev/null 2>&1
    git pull https://github.com/donaldzou/WGDashboard.git $new_ver --force >  /dev/null 2>&1
    printf "| Upgrading pip                                            |\n"
    python3 -m pip install -U pip > /dev/null 2>&1
    printf "| Installing latest Python dependencies                    |\n"
    python3 -m pip install -U -r requirements.txt > /dev/null 2>&1
    printf "| Update Successfully!                                     |\n"
    printf "%s\n" "$dashes"
    rm wgd.sh.old
  else
    printf "%s\n" "$dashes"
    printf "| Update Canceled.                                         |\n"
    printf "%s\n" "$dashes"
  fi
}


if [ "$#" != 1 ];
  then
    help
  else
    if [ "$1" = "start" ]; then
        if check_wgd_status; then
          printf "%s\n" "$dashes"
          printf "| WGDashboard is already running.                          |\n"
          printf "%s\n" "$dashes"
          else
            start_wgd
        fi
      elif [ "$1" = "stop" ]; then
        if check_wgd_status; then
            printf "%s\n" "$dashes"
            stop_wgd
            printf "| WGDashboard is stopped.                                  |\n"
            printf "%s\n" "$dashes"
            else
              printf "%s\n" "$dashes"
              printf "| WGDashboard is not running.                              |\n"
              printf "%s\n" "$dashes"
        fi
      elif [ "$1" = "update" ]; then
        update_wgd
      elif [ "$1" = "install" ]; then
        printf "%s\n" "$dashes"
        install_wgd
        printf "%s\n" "$dashes"
      elif [ "$1" = "restart" ]; then
         if check_wgd_status; then
           printf "%s\n" "$dashes"
           stop_wgd
           printf "| WGDashboard is stopped.                                  |\n"
           sleep 4
           start_wgd
        else
          start_wgd
        fi
      elif [ "$1" = "debug" ]; then
        if check_wgd_status; then
          printf "| WGDashboard is already running.                          |\n"
          else
            start_wgd_debug
        fi
      elif [ "$1" = "newconfig" ]; then
        newconf_wgd 
      else
        help
    fi
fi
