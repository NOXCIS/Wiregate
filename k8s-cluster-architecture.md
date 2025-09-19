# WireGate Kubernetes Cluster Architecture

## Cluster Overview

The WireGate Kubernetes cluster is designed for high availability and scalability, featuring:

- **3x WireGate Application Pods** (scalable to 5)
- **3x Redis Cluster Pods** (StatefulSet for distributed caching)
- **1x PostgreSQL Database** (shared data store)
- **2x Nginx Load Balancer Pods** (high availability)
- **Network Policies** for security isolation
- **ConfigMaps and Secrets** for configuration management

## Architecture Diagram

```mermaid
graph TB
    subgraph "External Traffic"
        Internet[Internet Traffic]
        Users[WireGuard Users]
    end

    subgraph "Kubernetes Cluster - wiregate namespace"
        subgraph "Load Balancer Layer"
            LB1[Nginx LB Pod 1<br/>Port: 80, 443]
            LB2[Nginx LB Pod 2<br/>Port: 80, 443]
            LB_SVC[nginx-loadbalancer<br/>Service: LoadBalancer]
        end

        subgraph "WireGate Application Layer"
            WG1[WireGate Pod 1<br/>Ports: 80, 44333, 4430-4433<br/>Host Network: true]
            WG2[WireGate Pod 2<br/>Ports: 80, 44333, 4430-4433<br/>Host Network: true]
            WG3[WireGate Pod 3<br/>Ports: 80, 44333, 4430-4433<br/>Host Network: true]
            WG_SVC[wiregate-cluster<br/>Service: LoadBalancer]
        end

        subgraph "Data Layer"
            subgraph "Redis Cluster (StatefulSet)"
                R1[Redis Pod 1<br/>redis-cluster-0<br/>Port: 6379]
                R2[Redis Pod 2<br/>redis-cluster-1<br/>Port: 6379]
                R3[Redis Pod 3<br/>redis-cluster-2<br/>Port: 6379]
                R_SVC[redis-cluster<br/>Service: Headless]
            end

            subgraph "PostgreSQL Database"
                PG[PostgreSQL Pod<br/>Port: 5432<br/>PVC: 10Gi]
                PG_SVC[postgres<br/>Service: ClusterIP]
            end
        end

        subgraph "Configuration & Security"
            CM[ConfigMaps<br/>- wiregate-config<br/>- postgres-config<br/>- redis-config<br/>- nginx-config<br/>- dnscrypt-config<br/>- tor-config<br/>- ssl-certs]
            SEC[Secrets<br/>- postgres-secret<br/>- redis-secret<br/>- wiregate-secret]
            NP[Network Policies<br/>- wiregate-network-policy<br/>- redis-network-policy]
            SA[Service Account<br/>- wiregate]
        end
    end

    subgraph "Storage"
        PVC1[PostgreSQL PVC<br/>10Gi RWO]
        PVC2[Redis PVCs<br/>1Gi each RWO]
    end

    %% External connections
    Internet --> LB_SVC
    Users --> WG_SVC

    %% Load balancer connections
    LB_SVC --> LB1
    LB_SVC --> LB2
    LB1 --> WG1
    LB1 --> WG2
    LB1 --> WG3
    LB2 --> WG1
    LB2 --> WG2
    LB2 --> WG3

    %% Application to data layer
    WG1 --> R_SVC
    WG2 --> R_SVC
    WG3 --> R_SVC
    WG1 --> PG_SVC
    WG2 --> PG_SVC
    WG3 --> PG_SVC

    %% Redis cluster connections
    R_SVC --> R1
    R_SVC --> R2
    R_SVC --> R3

    %% PostgreSQL connections
    PG_SVC --> PG

    %% Storage connections
    PG --> PVC1
    R1 --> PVC2
    R2 --> PVC2
    R3 --> PVC2

    %% Configuration connections
    WG1 -.-> CM
    WG2 -.-> CM
    WG3 -.-> CM
    WG1 -.-> SEC
    WG2 -.-> SEC
    WG3 -.-> SEC
    PG -.-> CM
    PG -.-> SEC
    R1 -.-> CM
    R2 -.-> CM
    R3 -.-> CM
    R1 -.-> SEC
    R2 -.-> SEC
    R3 -.-> SEC

    %% Security
    NP -.-> WG1
    NP -.-> WG2
    NP -.-> WG3
    NP -.-> R1
    NP -.-> R2
    NP -.-> R3

    %% Service account
    SA -.-> WG1
    SA -.-> WG2
    SA -.-> WG3

    classDef loadBalancer fill:#e1f5fe
    classDef application fill:#f3e5f5
    classDef database fill:#e8f5e8
    classDef config fill:#fff3e0
    classDef storage fill:#fce4ec

    class LB1,LB2,LB_SVC loadBalancer
    class WG1,WG2,WG3,WG_SVC application
    class R1,R2,R3,R_SVC,PG,PG_SVC database
    class CM,SEC,NP,SA config
    class PVC1,PVC2 storage
```

## Key Features

### High Availability
- **3x WireGate Pods**: Each with host networking for WireGuard VPN functionality
- **2x Nginx Load Balancers**: Distribute HTTP traffic across WireGate pods
- **3x Redis Cluster**: Distributed caching with StatefulSet for ordered deployment

### Scalability
- WireGate pods can be scaled from 3 to 5 replicas
- Redis cluster automatically scales with WireGate cluster size
- Load balancer can be scaled independently

### Security
- **Network Policies**: Restrict traffic between components
- **Secrets Management**: Encrypted storage for passwords and keys
- **Service Accounts**: Least privilege access for pods
- **Host Networking**: Required for WireGuard VPN functionality

### Data Persistence
- **PostgreSQL**: Shared database with 10Gi persistent volume
- **Redis**: Individual persistent volumes for each Redis pod (1Gi each)

### Port Configuration
- **HTTP**: Port 80 (load balanced)
- **HTTPS**: Port 443 (load balanced)
- **WireGuard Main**: Port 44333 (UDP)
- **WireGuard Zones**: Ports 4430-4433 (UDP)
- **PostgreSQL**: Port 5432 (internal)
- **Redis**: Port 6379 (internal)

### Configuration Management
- **ConfigMaps**: Non-sensitive configuration data
- **Secrets**: Sensitive data like passwords and certificates
- **Environment Variables**: Pod-specific configuration (e.g., Redis host per pod)

## Deployment Commands

```bash
# Deploy the cluster
kubectl apply -k k8s/

# Scale WireGate pods
kubectl scale deployment wiregate-cluster --replicas=5 -n wiregate

# Check pod status
kubectl get pods -n wiregate

# Check services
kubectl get svc -n wiregate

# Check persistent volumes
kubectl get pvc -n wiregate
```

## Monitoring and Logs

```bash
# View logs from all WireGate pods
kubectl logs -l app=wiregate-cluster -n wiregate

# View Redis cluster logs
kubectl logs -l app=redis-cluster -n wiregate

# Check resource usage
kubectl top pods -n wiregate
```
