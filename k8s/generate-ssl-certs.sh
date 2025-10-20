#!/bin/bash
# Generate SSL certificates for WireGate Kubernetes deployment

set -e

NAMESPACE="wiregate"
CERT_DIR="./ssl-certs"
CONFIGMAP_NAME="wiregate-ssl-certs"

echo "🔐 Generating SSL certificates for WireGate Kubernetes deployment..."

# Create SSL directory
mkdir -p "$CERT_DIR"

# Generate self-signed certificate
echo "📜 Generating self-signed SSL certificate..."
openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 365 -nodes \
    -subj "/C=US/ST=Production/L=WireGate/O=Kubernetes/OU=Security/CN=wiregate.local" \
    -addext "subjectAltName=DNS:wiregate.local,DNS:localhost,DNS:wiregate,IP:127.0.0.1,IP:10.0.0.1" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth,clientAuth" \
    -addext "basicConstraints=CA:FALSE" 2>/dev/null

# Set proper permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "✅ SSL certificates generated successfully!"
echo "📁 Certificate files:"
echo "   - Certificate: $CERT_DIR/cert.pem"
echo "   - Private Key: $CERT_DIR/key.pem"

# Create ConfigMap from SSL certificates
echo "📦 Creating Kubernetes ConfigMap from SSL certificates..."

# Delete existing ConfigMap if it exists
kubectl delete configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" --ignore-not-found=true

# Create ConfigMap with SSL certificates
kubectl create configmap "$CONFIGMAP_NAME" \
    --from-file=cert.pem="$CERT_DIR/cert.pem" \
    --from-file=key.pem="$CERT_DIR/key.pem" \
    -n "$NAMESPACE"

echo "✅ SSL certificates ConfigMap created successfully!"
echo "📋 ConfigMap name: $CONFIGMAP_NAME"
echo "📋 Namespace: $NAMESPACE"

# Show ConfigMap details
echo "🔍 ConfigMap details:"
kubectl describe configmap "$CONFIGMAP_NAME" -n "$NAMESPACE"

echo ""
echo "⚠️  WARNING: This is a self-signed certificate for development/testing."
echo "   For production, consider using Let's Encrypt or a proper CA certificate."
echo ""
echo "🚀 SSL certificates are ready for Kubernetes deployment!"
