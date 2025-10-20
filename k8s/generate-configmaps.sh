#!/bin/bash

# Script to generate Kubernetes ConfigMaps and Secrets from .env file
# Usage: ./generate-configmaps.sh [path-to-env-file]

set -e

ENV_FILE="${1:-../.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE_PATH="$(realpath "$ENV_FILE")"

if [[ ! -f "$ENV_FILE_PATH" ]]; then
    echo "Error: Environment file not found at $ENV_FILE_PATH"
    exit 1
fi

echo "Generating ConfigMaps from $ENV_FILE_PATH"

# Create temporary files
TEMP_ENV=$(mktemp)
TEMP_SECRETS=$(mktemp)

# Read .env file and separate sensitive vs non-sensitive variables
while IFS='=' read -r key value || [[ -n "$key" ]]; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Remove quotes from value and strip inline comments
    value=$(echo "$value" | sed 's/^"//;s/"$//' | sed 's/[[:space:]]*#.*$//')
    
    # Check if this is a sensitive variable
    if [[ "$key" =~ ^(WGD_USER|WGD_PASS|POSTGRES_PASSWORD|POSTGRES_USER|REDIS_PASSWORD|REDIS_USER)$ ]]; then
        echo "  $key: \"$value\"" >> "$TEMP_SECRETS"
    else
        echo "  $key: \"$value\"" >> "$TEMP_ENV"
    fi
done < "$ENV_FILE_PATH"

# Generate ConfigMap
cat > "$SCRIPT_DIR/configmaps/env-configmap.yaml" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: wiregate-env
  namespace: wiregate
data:
$(cat "$TEMP_ENV")
EOF

# Generate Secret
cat > "$SCRIPT_DIR/secrets/wiregate-secrets.yaml" << EOF
apiVersion: v1
kind: Secret
metadata:
  name: wiregate-secrets
  namespace: wiregate
type: Opaque
stringData:
$(cat "$TEMP_SECRETS")
EOF

# Clean up
rm "$TEMP_ENV" "$TEMP_SECRETS"

echo "✅ Generated configmaps/env-configmap.yaml"
echo "✅ Generated secrets/wiregate-secrets.yaml"
echo ""
echo "To apply the changes:"
echo "kubectl apply -f configmaps/env-configmap.yaml"
echo "kubectl apply -f secrets/wiregate-secrets.yaml"
