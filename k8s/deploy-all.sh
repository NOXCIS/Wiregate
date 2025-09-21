#!/bin/bash
# Complete WireGate Kubernetes deployment script

set -e

NAMESPACE="wiregate"

echo "🚀 Starting WireGate Kubernetes deployment..."

# Create namespace
echo "📁 Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

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
kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "LoadBalancer IP pending..."
echo "   HTTP Dashboard: http://$(kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'LOADBALANCER_IP'):8000"
echo "   WireGuard VPN: $(kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'LOADBALANCER_IP'):44333"
