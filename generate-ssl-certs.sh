#!/bin/bash
# Generate SSL certificates for WireGate Docker deployment

echo "Generating SSL certificates for WireGate..."

# Create SSL directory if it doesn't exist
mkdir -p ./configs/ssl

# Generate self-signed certificate in configs/ssl directory
openssl req -x509 -newkey rsa:4096 -keyout ./configs/ssl/key.pem -out ./configs/ssl/cert.pem -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=WireGate/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:wiregate,IP:127.0.0.1,IP:10.2.0.3"

# Set proper permissions
chmod 600 ./configs/ssl/key.pem
chmod 644 ./configs/ssl/cert.pem

echo "SSL certificates generated successfully!"
echo "Certificate: ./configs/ssl/cert.pem"
echo "Private Key: ./configs/ssl/key.pem"
echo ""
echo "To use with Docker:"
echo "1. Run: docker compose up -d"
echo "2. Access via: https://localhost:8443"
echo ""
echo "Note: You'll need to accept the self-signed certificate warning in your browser."
