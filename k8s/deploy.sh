#!/bin/bash

# Wiregate Kubernetes Deployment Script
# This script deploys Wiregate to a Kubernetes cluster

set -e

echo "🚀 Deploying Wiregate to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "❌ kustomize is not installed or not in PATH"
    echo "Install kustomize: https://kustomize.io/"
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    echo "Please ensure your kubeconfig is properly configured"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Deploy using kustomize
echo "📦 Deploying Wiregate resources..."
echo "Choose deployment type:"
echo "1) Single instance (default)"
echo "2) Clustered deployment (shared PostgreSQL + distributed Redis)"
echo "3) Environment-based deployment (uses k8.env file)"
echo "4) Environment-based clustered deployment (uses k8.env file + clustering)"
read -p "Enter choice [1-4]: " choice

case $choice in
    2)
        echo "🚀 Deploying clustered Wiregate..."
        kustomize build -f kustomization-cluster.yaml | kubectl apply -f -
        ;;
    3)
        echo "🚀 Deploying environment-based Wiregate..."
        if [ -f "k8.env" ]; then
            echo "📄 Found k8.env file, converting to Kubernetes resources..."
            chmod +x env-to-k8s.sh
            ./env-to-k8s.sh k8.env wiregate
            echo "🚀 Deploying with k8.env configuration..."
            kubectl apply -f wiregate-env-deployment.yaml
        else
            echo "❌ k8.env file not found. Please create one first."
            echo "You can copy from k8.env.example and customize it."
            exit 1
        fi
        ;;
    4)
        echo "🚀 Deploying environment-based clustered Wiregate..."
        if [ -f "k8.env" ]; then
            echo "📄 Found k8.env file, converting to Kubernetes resources..."
            chmod +x env-to-k8s.sh
            ./env-to-k8s.sh k8.env wiregate
            echo "🚀 Deploying Redis cluster..."
            kubectl apply -f redis-cluster-statefulset.yaml
            echo "🚀 Deploying PostgreSQL..."
            kubectl apply -f postgres-deployment.yaml
            kubectl apply -f postgres-configmap.yaml
            kubectl apply -f postgres-secret.yaml
            echo "🚀 Deploying clustered Wiregate with k8.env configuration..."
            kubectl apply -f wiregate-env-cluster-deployment.yaml
        else
            echo "❌ k8.env file not found. Please create one first."
            echo "You can copy from k8.env.example and customize it."
            exit 1
        fi
        ;;
    *)
        echo "🚀 Deploying single instance Wiregate..."
        kustomize build . | kubectl apply -f -
        ;;
esac

echo "⏳ Waiting for deployments to be ready..."

# Wait for Redis to be ready
echo "🔄 Waiting for Redis to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/redis -n wiregate

# Wait for Wiregate to be ready
echo "🔄 Waiting for Wiregate to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/wiregate -n wiregate

echo "✅ Deployment completed successfully!"

# Display service information
echo ""
echo "📋 Service Information:"
echo "======================"
kubectl get services -n wiregate

echo ""
echo "📊 Pod Status:"
echo "============="
kubectl get pods -n wiregate

echo ""
echo "🌐 Access Information:"
echo "====================="
echo "Wiregate Dashboard: Check the LoadBalancer external IP or use port-forward:"
echo "kubectl port-forward -n wiregate service/wiregate 8000:80"
echo ""
echo "WireGuard Ports: 44333 (main), 4430-4433 (zones)"
echo ""

# Optional: Show logs
read -p "Would you like to view Wiregate logs? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl logs -n wiregate deployment/wiregate --tail=50 -f
fi
