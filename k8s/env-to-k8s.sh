#!/bin/bash

# Convert .env file to Kubernetes ConfigMap and Secrets
# Usage: ./env-to-k8s.sh <env-file> <namespace>

set -e

ENV_FILE=${1:-"k8.env"}
NAMESPACE=${2:-"wiregate"}

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file $ENV_FILE not found"
    exit 1
fi

echo "🔄 Converting $ENV_FILE to Kubernetes resources..."

# Create temporary files
CONFIGMAP_FILE="/tmp/wiregate-configmap-env.yaml"
SECRET_FILE="/tmp/wiregate-secret-env.yaml"

# Initialize files
cat > "$CONFIGMAP_FILE" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: wiregate-config-env
  namespace: $NAMESPACE
data:
EOF

cat > "$SECRET_FILE" << EOF
apiVersion: v1
kind: Secret
metadata:
  name: wiregate-secret-env
  namespace: $NAMESPACE
type: Opaque
data:
EOF

# Process the .env file
while IFS='=' read -r key value || [ -n "$key" ]; do
    # Skip empty lines and comments
    if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # Remove quotes if present
    value=$(echo "$value" | sed 's/^"//;s/"$//')
    
    # Check if it's a sensitive value (password, secret, key, etc.)
    if [[ "$key" =~ (PASSWORD|SECRET|KEY|TOKEN|AUTH) ]]; then
        # Add to secret (base64 encode)
        encoded_value=$(echo -n "$value" | base64)
        echo "  $key: $encoded_value" >> "$SECRET_FILE"
    else
        # Add to configmap
        echo "  $key: \"$value\"" >> "$CONFIGMAP_FILE"
    fi
done < "$ENV_FILE"

echo "✅ Generated Kubernetes resources:"
echo "   ConfigMap: $CONFIGMAP_FILE"
echo "   Secret: $SECRET_FILE"

# Apply the resources
echo "🚀 Applying to Kubernetes..."
kubectl apply -f "$CONFIGMAP_FILE"
kubectl apply -f "$SECRET_FILE"

echo "✅ Environment variables applied to namespace: $NAMESPACE"

# Clean up temporary files
rm -f "$CONFIGMAP_FILE" "$SECRET_FILE"

echo "🎉 Done! Your environment variables are now available in Kubernetes."
