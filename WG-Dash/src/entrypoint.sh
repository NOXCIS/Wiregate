#!/bin/bash


run_wireguard_up() {
    config_files=$(find /etc/wireguard -type f -name "*.conf")

    if [ ! -f "/etc/wireguard/ADMINS.conf" ]; then
    /home/app/wgd.sh newconfig
    

    chmod u+x /home/app/wgd.sh

    for file in $(find /home/app/Iptables -type f -name "*.sh"); do
        chmod u+x "$file"
    done

    for file in $config_files; do
        config_name=$(basename "$file" ".conf")
        chmod 600 "/etc/wireguard/$config_name.conf"
    done
    
    wg-quick up ADMINS
    fi
}

config_nginx () {
    rm /etc/nginx/http.d/default.conf
    cat <<EOF > "/etc/nginx/http.d/default.conf"

server {
    listen 80;

    location / {
        include uwsgi_params;
        uwsgi_pass 127.0.0.1:10086;  # uWSGI service address and port
    }

    # Set the location of the uWSGI static folder
    location /static/ {
        alias /home/app/static/;
    }

    # Set security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Disable server version information
    server_tokens off;

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

}
EOF
nginx 
}




run_wireguard_up #>/dev/null 2>&1 && 

config_nginx &&

/home/app/wgd.sh start

