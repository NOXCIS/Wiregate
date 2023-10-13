#!/bin/bash


chmod u+x /home/app/wgd.sh

if [ ! -f "/etc/wireguard/wg0.conf" ]; then
    /home/app/wgd.sh newconfig

fi

run_wireguard_up() {
  config_files=$(find /etc/wireguard -type f -name "*.conf")
  
  for file in $config_files; do
    config_name=$(basename "$file" ".conf")
    # Show the current permissions
    file_permissions=$(stat -c %a "$file")
    echo "Current permissions for $file: $file_permissions"
    wg-quick up "$config_name"
  done
}

chmod_wg_conf_files() {
  local conf_dir="/etc/wireguard/"
  local files=()

  # Check if the directory exists
  if [ -d "$conf_dir" ]; then
    # Find all .conf files in the directory
    files=("$conf_dir"*.conf)

    # Loop through the files and set their permissions to 600
    for file in "${files[@]}"; do
      if [ -f "$file" ]; then
        chmod -f 600 "$file"
        echo "Set permissions to 600 for $file"
      fi
    done
  else
    echo "Directory $conf_dir does not exist."
  fi
}

# Call the function to apply permissions
chmod_wg_conf_files



run_wireguard_up 





/home/app/wgd.sh debug
