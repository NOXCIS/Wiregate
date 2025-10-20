#!/bin/bash
# Import custom SSL certificates for WireGate Kubernetes deployment

set -e

NAMESPACE="wiregate"
CONFIGMAP_NAME="wiregate-ssl-certs"
CERT_DIR="./ssl-certs"

echo "🔐 Importing custom SSL certificates for WireGate Kubernetes deployment..."

# Check if custom certificates exist
if [ ! -f "$CERT_DIR/cert.pem" ] || [ ! -f "$CERT_DIR/key.pem" ]; then
    echo "❌ Custom SSL certificates not found!"
    echo "📁 Expected files:"
    echo "   - $CERT_DIR/cert.pem (certificate file)"
    echo "   - $CERT_DIR/key.pem (private key file)"
    echo ""
    echo "💡 To use this script:"
    echo "   1. Create directory: mkdir -p $CERT_DIR"
    echo "   2. Copy your certificate: cp your-cert.pem $CERT_DIR/cert.pem"
    echo "   3. Copy your private key: cp your-key.pem $CERT_DIR/key.pem"
    echo "   4. Run this script again"
    echo ""
    echo "📁 Note: This script looks for certificates in: $CERT_DIR/"
    exit 1
fi

# Validate certificate files
echo "🔍 Validating custom SSL certificates..."

# Check certificate file
if ! openssl x509 -in "$CERT_DIR/cert.pem" -text -noout >/dev/null 2>&1; then
    echo "❌ Invalid certificate file: $CERT_DIR/cert.pem"
    exit 1
fi

# Check private key file
if ! openssl rsa -in "$CERT_DIR/key.pem" -check -noout >/dev/null 2>&1; then
    echo "❌ Invalid private key file: $CERT_DIR/key.pem"
    exit 1
fi

# Verify certificate and key match
CERT_MD5=$(openssl x509 -noout -modulus -in "$CERT_DIR/cert.pem" | openssl md5)
KEY_MD5=$(openssl rsa -noout -modulus -in "$CERT_DIR/key.pem" | openssl md5)

if [ "$CERT_MD5" != "$KEY_MD5" ]; then
    echo "❌ Certificate and private key do not match!"
    exit 1
fi

echo "✅ Custom SSL certificates are valid and match!"

# Display certificate information
echo "📋 Certificate details:"
openssl x509 -in "$CERT_DIR/cert.pem" -text -noout | grep -E "(Subject:|Not Before|Not After|DNS:|IP Address:)" | head -10

# Set proper permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "✅ Custom SSL certificates validated successfully!"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    echo "❌ Namespace '$NAMESPACE' does not exist. Please run deploy-all.sh first."
    exit 1
fi

# Create ConfigMap from custom SSL certificates
echo "📦 Creating Kubernetes ConfigMap from custom SSL certificates..."

# Delete existing ConfigMap if it exists
kubectl delete configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" --ignore-not-found=true

# Create ConfigMap with custom SSL certificates
kubectl create configmap "$CONFIGMAP_NAME" \
    --from-file=cert.pem="$CERT_DIR/cert.pem" \
    --from-file=key.pem="$CERT_DIR/key.pem" \
    -n "$NAMESPACE"

echo "✅ Custom SSL certificates ConfigMap created successfully!"
echo "📋 ConfigMap name: $CONFIGMAP_NAME"
echo "📋 Namespace: $NAMESPACE"

# Restart WireGate deployment to pick up new certificates
echo "🔄 Restarting WireGate deployment to apply custom certificates..."
kubectl rollout restart deployment/wiregate -n "$NAMESPACE"

echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/wiregate -n "$NAMESPACE" --timeout=120s

echo "✅ Custom SSL certificates imported and deployment restarted successfully!"
echo "🌐 WireGate is now accessible with your custom SSL certificates at:"
kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "LoadBalancer IP pending..."
echo "   HTTPS Dashboard: https://$(kubectl get svc -n $NAMESPACE wiregate -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo 'LOADBALANCER_IP'):8443"
echo ""
echo "💡 To access via localhost, run:"
echo "   kubectl port-forward -n wiregate svc/wiregate 8443:8443"
echo "   Then visit: https://localhost:8443"
