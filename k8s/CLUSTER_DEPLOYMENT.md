# WireGate Kubernetes Cluster Deployment

This guide explains how to deploy WireGate in a clustered configuration with shared PostgreSQL and distributed Redis caching.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WireGate-1    │    │   WireGate-2    │    │   WireGate-N    │
│   + Redis-1     │    │   + Redis-2     │    │   + Redis-N     │
│   (Local Cache) │    │   (Local Cache) │    │   (Local Cache) │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     Shared PostgreSQL     │
                    │   (Primary Database)      │
                    └───────────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     Nginx Load Balancer   │
                    │   (Traffic Distribution)  │
                    └───────────────────────────┘
```

## Key Benefits

- **Shared PostgreSQL**: Single source of truth for all data
- **Distributed Redis**: Each WireGate instance has its own Redis cache
- **Load Balancing**: Nginx distributes traffic across WireGate instances
- **High Availability**: Multiple WireGate instances for redundancy
- **Scalability**: Easy to scale WireGate instances up/down

## Quick Start

### Deploy Clustered WireGate

```bash
# Run the deployment script and choose option 2
./deploy.sh

# Or deploy directly
kustomize build -f kustomization-cluster.yaml | kubectl apply -f -
```

### Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n wiregate

# Check services
kubectl get services -n wiregate

# Check PostgreSQL connection
kubectl exec -n wiregate deployment/postgres -- psql -U wiregate_user -d wiregate -c "SELECT version();"

# Check Redis cluster
kubectl exec -n wiregate redis-cluster-0 -- redis-cli -a $(kubectl get secret redis-secret -o jsonpath='{.data.password}' | base64 -d) ping
```

## Configuration

### Scaling WireGate Instances

```bash
# Scale WireGate cluster
kubectl scale deployment wiregate-cluster --replicas=5 -n wiregate

# Scale Redis cluster (must match WireGate instances)
kubectl scale statefulset redis-cluster --replicas=5 -n wiregate
```

### Database Configuration

The cluster uses shared PostgreSQL with these settings:
- **Host**: `postgres.wiregate.svc.cluster.local`
- **Database**: `wiregate`
- **User**: `wiregate_user`
- **SSL**: Disabled (can be enabled for production)

### Redis Configuration

Each WireGate instance connects to its own Redis:
- **Instance 1**: `redis-cluster-0.redis-cluster-headless.wiregate.svc.cluster.local`
- **Instance 2**: `redis-cluster-1.redis-cluster-headless.wiregate.svc.cluster.local`
- **Instance N**: `redis-cluster-N.redis-cluster-headless.wiregate.svc.cluster.local`

## Load Balancing

Nginx load balancer distributes traffic using:
- **Algorithm**: Least connections
- **Health Checks**: Automatic failover
- **Sticky Sessions**: Not required (stateless design)

### Access Points

- **HTTP Dashboard**: LoadBalancer external IP
- **WireGuard Main**: Port 44333/UDP
- **WireGuard Zones**: Ports 4430-4433/UDP

## Monitoring

### Check Cluster Health

```bash
# WireGate instances
kubectl get pods -l app=wiregate-cluster -n wiregate

# Redis instances
kubectl get pods -l app=redis-cluster -n wiregate

# PostgreSQL
kubectl get pods -l app=postgres -n wiregate

# Load balancer
kubectl get pods -l app=nginx-loadbalancer -n wiregate
```

### View Logs

```bash
# WireGate logs
kubectl logs -l app=wiregate-cluster -n wiregate --tail=100

# Redis logs
kubectl logs -l app=redis-cluster -n wiregate --tail=100

# PostgreSQL logs
kubectl logs -l app=postgres -n wiregate --tail=100
```

## Performance Tuning

### PostgreSQL Tuning

Update `postgres-configmap.yaml` for your workload:
- `max_connections`: Increase for more concurrent users
- `shared_buffers`: Adjust based on available memory
- `work_mem`: Increase for complex queries

### Redis Tuning

Update `redis-configmap.yaml`:
- `maxmemory`: Set based on available memory
- `maxmemory-policy`: Choose eviction policy
- `save`: Configure persistence settings

### WireGate Tuning

Update resource limits in `wiregate-cluster-deployment.yaml`:
- `requests`: Minimum resources needed
- `limits`: Maximum resources allowed

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   ```bash
   kubectl logs -l app=wiregate-cluster -n wiregate | grep -i postgres
   kubectl exec -n wiregate deployment/postgres -- pg_isready -U wiregate_user -d wiregate
   ```

2. **Redis Connection Failed**
   ```bash
   kubectl logs -l app=wiregate-cluster -n wiregate | grep -i redis
   kubectl exec -n wiregate redis-cluster-0 -- redis-cli ping
   ```

3. **Load Balancer Not Working**
   ```bash
   kubectl logs -l app=nginx-loadbalancer -n wiregate
   kubectl get endpoints -n wiregate
   ```

### Debug Commands

```bash
# Port forward for testing
kubectl port-forward -n wiregate service/nginx-loadbalancer 8000:80

# Access PostgreSQL directly
kubectl port-forward -n wiregate service/postgres 5432:5432

# Access Redis directly
kubectl port-forward -n wiregate redis-cluster-0 6379:6379
```

## Production Considerations

### Security
- Enable PostgreSQL SSL
- Use Kubernetes Secrets for all passwords
- Implement proper RBAC
- Use Network Policies for traffic isolation

### Backup
- Set up PostgreSQL backups
- Configure Redis persistence
- Backup Kubernetes configurations

### Monitoring
- Set up Prometheus/Grafana
- Configure alerting
- Monitor resource usage
- Track performance metrics

## Cleanup

```bash
# Remove clustered deployment
kubectl delete -f kustomization-cluster.yaml

# Or remove namespace (removes everything)
kubectl delete namespace wiregate
```
