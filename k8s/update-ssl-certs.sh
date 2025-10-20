#!/bin/bash
# Update SSL certificates for existing WireGate Kubernetes deployment

set -e

NAMESPACE="wiregate"
CONFIGMAP_NAME="wiregate-ssl-certs"
CERT_DIR="./ssl-certs"

echo "🔄 Updating SSL certificates for WireGate Kubernetes deployment..."

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    echo "❌ Namespace '$NAMESPACE' does not exist. Please run deploy-all.sh first."
    exit 1
fi

# Check if ConfigMap exists
if ! kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
    echo "❌ ConfigMap '$CONFIGMAP_NAME' does not exist. Please run deploy-all.sh first."
    exit 1
fi

# Generate new SSL certificates
echo "📜 Generating new SSL certificates..."
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 365 -nodes \
    -subj "/C=US/ST=Production/L=WireGate/O=Kubernetes/OU=Security/CN=wiregate.local" \
    -addext "subjectAltName=DNS:wiregate.local,DNS:localhost,DNS:wiregate,IP:127.0.0.1,IP:10.0.0.1" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth,clientAuth" \
    -addext "basicConstraints=CA:FALSE" 2>/dev/null

# Set proper permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "✅ New SSL certificates generated successfully!"

# Update ConfigMap with new certificates
echo "📦 Updating Kubernetes ConfigMap with new SSL certificates..."

kubectl create configmap "$CONFIGMAP_NAME" \
    --from-file=cert.pem="$CERT_DIR/cert.pem" \
    --from-file=key.pem="$CERT_DIR/key.pem" \
    -n "$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ SSL certificates ConfigMap updated successfully!"

# Restart WireGate deployment to pick up new certificates
echo "🔄 Restarting WireGate deployment to apply new certificates..."
kubectl rollout restart deployment/wiregate -n "$NAMESPACE"

echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/wiregate -n "$NAMESPACE" --timeout=120s

echo "✅ SSL certificates updated and deployment restarted successfully!"
echo "🌐 WireGate is now accessible with new SSL certificates at:"
kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "LoadBalancer IP pending..."
echo "   HTTPS Dashboard: https://$(kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'LOADBALANCER_IP'):8443"
