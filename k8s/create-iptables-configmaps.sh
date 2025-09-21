#!/bin/bash
# Script to create iptables ConfigMaps from source files

set -e

NAMESPACE="wiregate"
SOURCE_DIR="../Src/iptable-rules"

echo "Creating iptables ConfigMaps for namespace: $NAMESPACE"

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for Admins
echo "Creating iptables-admins ConfigMap..."
kubectl create configmap iptables-admins \
  --from-file="$SOURCE_DIR/Admins/" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for Guest
echo "Creating iptables-guest ConfigMap..."
kubectl create configmap iptables-guest \
  --from-file="$SOURCE_DIR/Guest/" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for Members
echo "Creating iptables-members ConfigMap..."
kubectl create configmap iptables-members \
  --from-file="$SOURCE_DIR/Members/" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Create ConfigMap for LAN-only-users
echo "Creating iptables-lan ConfigMap..."
kubectl create configmap iptables-lan \
  --from-file="$SOURCE_DIR/LAN-only-users/" \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

echo "All iptables ConfigMaps created successfully!"
echo "ConfigMaps created:"
kubectl get configmaps -n $NAMESPACE | grep iptables
