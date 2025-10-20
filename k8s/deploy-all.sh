#!/bin/bash
# Complete WireGate Kubernetes deployment script

set -e

NAMESPACE="wiregate"

echo "🚀 Starting WireGate Kubernetes deployment..."

# Create namespace
echo "📁 Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Generate ConfigMaps and Secrets from .env file
echo "🔧 Generating ConfigMaps and Secrets from .env file..."
./generate-configmaps.sh

# Create iptables ConfigMaps
echo "🔧 Creating iptables ConfigMaps..."
./create-iptables-configmaps.sh

# Apply all configurations
echo "⚙️  Applying configurations..."
kubectl apply -f configmaps/
kubectl apply -f secrets/
kubectl apply -f persistentvolumes/
kubectl apply -f services/
kubectl apply -f network-policies/

# Deploy applications
echo "🚀 Deploying applications..."
kubectl apply -f deployments/

# Check for custom SSL certificates after deployment
SSL_CERTS_DIR="./ssl-certs"
if [ -f "$SSL_CERTS_DIR/cert.pem" ] && [ -f "$SSL_CERTS_DIR/key.pem" ]; then
    echo "🔐 Custom SSL certificates found in $SSL_CERTS_DIR/, importing them..."
    ./import-custom-ssl-certs.sh
else
    echo "🔐 No custom SSL certificates found, generating self-signed certificates..."
    ./generate-ssl-certs.sh
fi

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --namespace=$NAMESPACE --for=condition=ready pod -l app=postgres --timeout=60s
kubectl wait --namespace=$NAMESPACE --for=condition=ready pod -l app=redis --timeout=60s
kubectl wait --namespace=$NAMESPACE --for=condition=ready pod -l app=wiregate --timeout=120s

# Show final status
echo "✅ Deployment complete! Status:"
kubectl get all -n $NAMESPACE

echo ""
echo "🌐 WireGate is accessible at:"
LOADBALANCER_IP=$(kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "LOADBALANCER_IP")
echo "   HTTP Dashboard: http://$LOADBALANCER_IP:8000"
echo "   HTTPS Dashboard: https://$LOADBALANCER_IP:8443"
echo "   WireGuard VPN Ports:"
kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{range .spec.ports[?(@.protocol=="UDP")]}{.name}: {.port}{"\n"}{end}' | while read -r line; do
    if [ -n "$line" ]; then
        port_name=$(echo "$line" | cut -d: -f1 | tr -d ' ')
        port_num=$(echo "$line" | cut -d: -f2 | tr -d ' ')
        echo "     - $port_name: $LOADBALANCER_IP:$port_num"
    fi
done
