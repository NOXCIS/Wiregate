# Environment-Based Kubernetes Deployment

This guide explains how to use the `k8.env` file for Kubernetes deployments with WireGate.

## Overview

The `k8.env` file allows you to manage all your WireGate configuration in one place and automatically convert it to Kubernetes ConfigMaps and Secrets.

## Quick Start

### 1. Edit Your Environment File

```bash
# Edit the k8.env file with your settings
nano k8.env
```

### 2. Deploy Using Environment File

```bash
# Run the deployment script and choose option 3 or 4
./deploy.sh

# Option 3: Single instance with k8.env
# Option 4: Clustered deployment with k8.env
```

### 3. Manual Deployment

```bash
# Convert environment file to Kubernetes resources
./env-to-k8s.sh k8.env wiregate

# Deploy single instance
kubectl apply -f wiregate-env-deployment.yaml

# Or deploy clustered version
kubectl apply -f wiregate-env-cluster-deployment.yaml
```

## Environment File Structure

Your `k8.env` file should contain:

```bash
# Redis Database Settings
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=wiregate_redis_password

# PostgreSQL Database Settings
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=wiregate
POSTGRES_USER=wiregate_user
POSTGRES_PASSWORD=wiregate_postgres_password
POSTGRES_SSL_MODE=disable

# Tor Settings
WGD_TOR_PROXY=true
WGD_TOR_EXIT_NODES={ch}
WGD_TOR_DNS_EXIT_NODES={us}
WGD_TOR_BRIDGES=false
WGD_TOR_PLUGIN=snowflake
WGD_TOR_DNSCRYPT=false

# WireGate Settings
DASHBOARD_MODE=production
WGD_WELCOME_SESSION=false
WGD_AUTH_REQ=false
WGD_USER=admin
WGD_PASS=admin
WGD_REMOTE_ENDPOINT=192.168.0.4
WGD_REMOTE_ENDPOINT_PORT=80
WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0, ::/0
WGD_KEEP_ALIVE=21
WGD_MTU=1420
WGD_PORT_RANGE_STARTPORT=4430

# DNS Settings
WGD_DNS=1.1.1.1
WGD_IPTABLES_DNS=1.1.1.1
```

## How It Works

### Automatic Conversion

The `env-to-k8s.sh` script automatically:

1. **Reads** your `k8.env` file
2. **Separates** sensitive data (passwords, secrets) from regular config
3. **Creates** two Kubernetes resources:
   - `ConfigMap` for non-sensitive configuration
   - `Secret` for sensitive data (base64 encoded)

### Sensitive Data Detection

The script automatically detects sensitive variables by keywords:
- `PASSWORD`
- `SECRET`
- `KEY`
- `TOKEN`
- `AUTH`

These are stored in Kubernetes Secrets, everything else goes to ConfigMaps.

## Deployment Options

### Option 1: Single Instance
```bash
./deploy.sh
# Choose option 3
```

Uses your `k8.env` file for a single WireGate instance.

### Option 2: Clustered Deployment
```bash
./deploy.sh
# Choose option 4
```

Uses your `k8.env` file with:
- Shared PostgreSQL database
- Distributed Redis caching
- Multiple WireGate instances
- Load balancing

## Customization

### Adding New Environment Variables

1. **Add to `k8.env`**:
   ```bash
   MY_CUSTOM_SETTING=value
   MY_CUSTOM_PASSWORD=secret123
   ```

2. **Redeploy**:
   ```bash
   ./env-to-k8s.sh k8.env wiregate
   kubectl apply -f wiregate-env-deployment.yaml
   ```

### Modifying Existing Settings

1. **Edit `k8.env`**
2. **Redeploy**:
   ```bash
   ./env-to-k8s.sh k8.env wiregate
   kubectl rollout restart deployment/wiregate-env
   ```

## Verification

### Check Generated Resources

```bash
# View ConfigMap
kubectl get configmap wiregate-config-env -o yaml

# View Secret
kubectl get secret wiregate-secret-env -o yaml

# Decode secret values
kubectl get secret wiregate-secret-env -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d
```

### Check Pod Environment

```bash
# View environment variables in pod
kubectl exec -n wiregate deployment/wiregate-env -- env | grep -E "(REDIS|POSTGRES|WGD_)"
```

## Troubleshooting

### Common Issues

1. **Environment file not found**:
   ```bash
   # Make sure k8.env exists in the k8s directory
   ls -la k8.env
   ```

2. **Permission denied**:
   ```bash
   # Make script executable
   chmod +x env-to-k8s.sh
   ```

3. **Kubernetes connection failed**:
   ```bash
   # Check kubectl configuration
   kubectl cluster-info
   ```

### Debug Commands

```bash
# Check if resources were created
kubectl get configmaps,secrets -n wiregate

# View pod logs
kubectl logs -n wiregate deployment/wiregate-env

# Check pod environment
kubectl describe pod -n wiregate -l app=wiregate-env
```

## Best Practices

### Security
- Never commit `k8.env` with real passwords to version control
- Use strong, unique passwords
- Consider using Kubernetes external secret management

### Configuration Management
- Keep `k8.env` in sync with your deployment
- Document any custom environment variables
- Use descriptive variable names

### Backup
- Backup your `k8.env` file
- Export Kubernetes resources for backup:
  ```bash
  kubectl get configmap wiregate-config-env -o yaml > configmap-backup.yaml
  kubectl get secret wiregate-secret-env -o yaml > secret-backup.yaml
  ```

## Advanced Usage

### Custom Environment Files

```bash
# Use different environment file
./env-to-k8s.sh production.env wiregate

# Use different namespace
./env-to-k8s.sh k8.env my-namespace
```

### Integration with CI/CD

```bash
# In your CI/CD pipeline
./env-to-k8s.sh $ENVIRONMENT_FILE $NAMESPACE
kubectl apply -f wiregate-env-deployment.yaml
kubectl rollout status deployment/wiregate-env
```

This approach gives you the flexibility to manage your WireGate configuration through environment variables while maintaining the benefits of Kubernetes ConfigMaps and Secrets!
