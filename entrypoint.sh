#!/bin/sh
set -e

# Replace environment variables in nginx configuration
envsubst '${PORTAINER_HOST} ${WIREDASH_HOST} ${PIHOLE_HOST}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx
nginx -g 'daemon off;'
