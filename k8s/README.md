# Wiregate Kubernetes Deployment

This directory contains Kubernetes manifests for deploying Wiregate, a VPN gateway solution, to a Kubernetes cluster.

## Overview

Wiregate is deployed as a multi-service application consisting of:
- **Redis**: Database for storing configuration and session data
- **Wiregate**: Main VPN gateway application with WireGuard support

## Prerequisites

- Kubernetes cluster (v1.19+)
- `kubectl` configured to access your cluster
- `kustomize` installed (for deployment)
- Cluster with support for:
  - Privileged containers (for WireGuard)
  - Host networking (for VPN functionality)
  - LoadBalancer services (or NodePort for external access)

## Quick Start

1. **Deploy using the provided script:**
   ```bash
   ./deploy.sh
   ```

2. **Or deploy manually:**
   ```bash
   kustomize build . | kubectl apply -f -
   ```

3. **Check deployment status:**
   ```bash
   kubectl get pods -n wiregate
   kubectl get services -n wiregate
   ```

## Configuration

### Environment Variables

The Wiregate configuration can be modified in `wiregate-configmap.yaml`:

- `WGD_TOR_PROXY`: Enable Tor proxy (true/false)
- `WGD_TOR_EXIT_NODES`: Tor exit node countries (e.g., "{ch}")
- `WGD_USER`/`WGD_PASS`: Dashboard credentials
- `WGD_REMOTE_ENDPOINT`: External endpoint IP
- `WGD_DNS`: DNS servers to use

### Secrets

Update `wiregate-secret.yaml` and `redis-secret.yaml` with your actual passwords:

```bash
# Generate base64 encoded password
echo -n "your_password" | base64

# Update the secret files with the encoded value
```

### SSL Certificates

Add your SSL certificates to `ssl-configmap.yaml` or create a separate secret:

```bash
kubectl create secret tls wiregate-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  -n wiregate
```

## Services

### Wiregate Service
- **HTTP Dashboard**: Port 80 (LoadBalancer/NodePort)
- **WireGuard Main**: Port 44333/UDP
- **WireGuard Zones**: Ports 4430-4433/UDP

### Redis Service
- **Database**: Port 6379 (ClusterIP, internal only)

## Network Policies

The deployment includes NetworkPolicies that:
- Restrict Redis access to only Wiregate pods
- Allow necessary external traffic for Wiregate
- Block unnecessary ingress/egress

## Security Considerations

⚠️ **Important Security Notes:**

1. **Privileged Containers**: Wiregate requires privileged access for WireGuard functionality
2. **Host Networking**: Uses host networking for VPN traffic routing
3. **Secrets Management**: Store sensitive data in Kubernetes Secrets, not ConfigMaps
4. **Network Policies**: Review and adjust NetworkPolicies based on your security requirements
5. **RBAC**: The ServiceAccount has minimal required permissions

## Troubleshooting

### Check Pod Logs
```bash
kubectl logs -n wiregate deployment/wiregate
kubectl logs -n wiregate deployment/redis
```

### Check Service Status
```bash
kubectl describe service -n wiregate
kubectl get endpoints -n wiregate
```

### Port Forward for Testing
```bash
# Access dashboard locally
kubectl port-forward -n wiregate service/wiregate 8000:80

# Access Redis locally
kubectl port-forward -n wiregate service/redis 6379:6379
```

### Common Issues

1. **Pod stuck in Pending**: Check if the cluster supports privileged containers
2. **WireGuard not working**: Ensure host networking is enabled and ports are accessible
3. **Redis connection failed**: Check if Redis pod is running and NetworkPolicy allows communication

## Customization

### Using Custom Images
Update the image in `wiregate-deployment.yaml`:
```yaml
spec:
  template:
    spec:
      containers:
      - name: wiregate
        image: your-registry/wiregate:your-tag
```

### Resource Limits
Adjust CPU/memory limits in the deployment files based on your cluster capacity.

### Storage
For persistent storage, replace `emptyDir` volumes with PersistentVolumeClaims.

## Cleanup

To remove the deployment:
```bash
kubectl delete namespace wiregate
```

## Support

For issues specific to Wiregate functionality, refer to the main Wiregate documentation.
For Kubernetes deployment issues, check the troubleshooting section above.
