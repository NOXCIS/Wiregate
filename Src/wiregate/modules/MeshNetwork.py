"""
Mesh Network Module
Manages mesh topology, peer relationships, IP allocation, and key generation
for creating partial mesh networks from WireGuard/AmneziaWG configurations
"""
import logging
import ipaddress
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

logger = logging.getLogger('wiregate')


@dataclass
class MeshNode:
    """Represents a node in the mesh network"""
    id: str
    name: str
    public_key: str
    private_key: str = ""
    address: str = ""
    endpoint: str = ""
    listen_port: int = 0
    protocol: str = "wg"  # wg or awg
    is_external: bool = False  # True if uploaded from external config
    # AmneziaWG specific fields
    awg_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "public_key": self.public_key,
            "private_key": self.private_key if not self.is_external else "",
            "address": self.address,
            "endpoint": self.endpoint,
            "listen_port": self.listen_port,
            "protocol": self.protocol,
            "is_external": self.is_external,
            "awg_params": self.awg_params
        }


@dataclass
class MeshConnection:
    """Represents a connection between two mesh nodes"""
    node_a_id: str
    node_b_id: str
    preshared_key: str = ""
    allowed_ips_a_to_b: str = ""  # What A allows from B
    allowed_ips_b_to_a: str = ""  # What B allows from A
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_a_id": self.node_a_id,
            "node_b_id": self.node_b_id,
            "preshared_key": self.preshared_key,
            "allowed_ips_a_to_b": self.allowed_ips_a_to_b,
            "allowed_ips_b_to_a": self.allowed_ips_b_to_a,
            "enabled": self.enabled
        }


class MeshNetwork:
    """
    Manages mesh network topology and peer relationships.
    Supports partial mesh where users can select which peers connect.
    """
    
    def __init__(self, name: str = ""):
        self.id = str(uuid.uuid4())
        self.name = name or f"mesh_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.nodes: Dict[str, MeshNode] = {}
        self.connections: List[MeshConnection] = []
        self.created_at = datetime.now()
        
    def add_node(self, node: MeshNode) -> bool:
        """Add a node to the mesh network"""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists in mesh")
            return False
        self.nodes[node.id] = node
        logger.info(f"Added node {node.name} to mesh {self.name}")
        return True
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its connections"""
        if node_id not in self.nodes:
            return False
        
        # Remove all connections involving this node
        self.connections = [
            conn for conn in self.connections
            if conn.node_a_id != node_id and conn.node_b_id != node_id
        ]
        
        del self.nodes[node_id]
        logger.info(f"Removed node {node_id} from mesh {self.name}")
        return True
    
    def add_connection(self, node_a_id: str, node_b_id: str, 
                      preshared_key: str = "") -> Optional[MeshConnection]:
        """Add a connection between two nodes"""
        if node_a_id not in self.nodes or node_b_id not in self.nodes:
            logger.error(f"Cannot connect nodes: one or both nodes not found")
            return None
        
        if node_a_id == node_b_id:
            logger.error("Cannot connect a node to itself")
            return None
        
        # Check if connection already exists
        for conn in self.connections:
            if (conn.node_a_id == node_a_id and conn.node_b_id == node_b_id) or \
               (conn.node_a_id == node_b_id and conn.node_b_id == node_a_id):
                logger.warning(f"Connection between {node_a_id} and {node_b_id} already exists")
                return None
        
        # Calculate allowed IPs based on node addresses
        node_a = self.nodes[node_a_id]
        node_b = self.nodes[node_b_id]
        
        # Extract IP from address (e.g., "10.0.0.1/24" -> "10.0.0.1/32")
        allowed_ips_a = self._get_peer_allowed_ip(node_a.address)
        allowed_ips_b = self._get_peer_allowed_ip(node_b.address)
        
        connection = MeshConnection(
            node_a_id=node_a_id,
            node_b_id=node_b_id,
            preshared_key=preshared_key,
            allowed_ips_a_to_b=allowed_ips_b,  # A allows traffic from B's IP
            allowed_ips_b_to_a=allowed_ips_a   # B allows traffic from A's IP
        )
        
        self.connections.append(connection)
        logger.info(f"Added connection between {node_a.name} and {node_b.name}")
        return connection
    
    def remove_connection(self, node_a_id: str, node_b_id: str) -> bool:
        """Remove a connection between two nodes"""
        for i, conn in enumerate(self.connections):
            if (conn.node_a_id == node_a_id and conn.node_b_id == node_b_id) or \
               (conn.node_a_id == node_b_id and conn.node_b_id == node_a_id):
                self.connections.pop(i)
                logger.info(f"Removed connection between {node_a_id} and {node_b_id}")
                return True
        return False
    
    def get_node_connections(self, node_id: str) -> List[MeshConnection]:
        """Get all connections for a specific node"""
        return [
            conn for conn in self.connections
            if conn.node_a_id == node_id or conn.node_b_id == node_id
        ]
    
    def get_node_peers(self, node_id: str) -> List[MeshNode]:
        """Get all peers (connected nodes) for a specific node"""
        peer_ids = set()
        for conn in self.get_node_connections(node_id):
            if conn.node_a_id == node_id:
                peer_ids.add(conn.node_b_id)
            else:
                peer_ids.add(conn.node_a_id)
        
        return [self.nodes[pid] for pid in peer_ids if pid in self.nodes]
    
    @staticmethod
    def _get_peer_allowed_ip(address: str) -> str:
        """Convert node address to peer allowed IP (single host)"""
        if not address:
            return ""
        try:
            # Parse the address and get just the IP (as /32 for point-to-point)
            network = ipaddress.ip_interface(address)
            return f"{network.ip}/32"
        except ValueError:
            return address
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize mesh network to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "connections": [conn.to_dict() for conn in self.connections]
        }


class MeshNetworkManager:
    """
    Manages mesh network operations including:
    - Creating mesh networks from existing configurations
    - Parsing and adding external configs
    - Generating peer configurations for mesh connections
    - IP allocation and collision detection
    """
    
    def __init__(self):
        self.mesh_networks: Dict[str, MeshNetwork] = {}
    
    def create_mesh_from_configs(self, config_names: List[str], 
                                  mesh_name: str = "") -> Optional[MeshNetwork]:
        """
        Create a new mesh network from existing WireGuard configurations
        """
        from .Core import Configurations
        
        # Validate input
        if not config_names or not isinstance(config_names, list):
            logger.error("Invalid config_names: must be a non-empty list")
            return None
        
        if len(config_names) < 2:
            logger.error("Need at least 2 configurations to create a mesh")
            return None
        
        # Validate all configs exist before creating mesh
        missing_configs = []
        for config_name in config_names:
            if not isinstance(config_name, str):
                logger.error(f"Invalid config name type: {type(config_name)}")
                return None
            if config_name not in Configurations:
                missing_configs.append(config_name)
        
        if missing_configs:
            logger.error(f"Configurations not found: {', '.join(missing_configs)}")
            return None
        
        mesh = MeshNetwork(name=mesh_name)
        
        for config_name in config_names:
            config = Configurations[config_name]
            
            # Create mesh node from configuration
            node = MeshNode(
                id=config.Name,
                name=config.Name,
                public_key=config.PublicKey,
                private_key=config.PrivateKey,
                address=config.Address,
                endpoint=f"{config.Name}",  # Will be resolved
                listen_port=int(config.ListenPort) if config.ListenPort else 51820,
                protocol=config.get_iface_proto()
            )
            
            # Add AmneziaWG params if applicable
            if config.get_iface_proto() == "awg":
                node.awg_params = {
                    "Jc": config.Jc,
                    "Jmin": config.Jmin,
                    "Jmax": config.Jmax,
                    "S1": config.S1,
                    "S2": config.S2,
                    "H1": config.H1,
                    "H2": config.H2,
                    "H3": config.H3,
                    "H4": config.H4,
                    "I1": config.I1,
                    "I2": config.I2,
                    "I3": config.I3,
                    "I4": config.I4,
                    "I5": config.I5
                }
            
            mesh.add_node(node)
        
        # Final validation - should never happen if validation above worked, but double-check
        if len(mesh.nodes) < 2:
            logger.error("Need at least 2 configurations to create a mesh")
            return None
        
        self.mesh_networks[mesh.id] = mesh
        logger.info(f"Created mesh network '{mesh.name}' with {len(mesh.nodes)} nodes")
        return mesh
    
    def parse_external_config(self, config_content: str, 
                             config_name: str = "") -> Optional[MeshNode]:
        """
        Parse an external WireGuard/AmneziaWG config file and create a mesh node
        """
        lines = config_content.strip().split('\n')
        interface_data = {}
        in_interface = False
        
        # AmneziaWG parameters
        awg_params = ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4']
        cps_params = ['I1', 'I2', 'I3', 'I4', 'I5']
        
        for line in lines:
            line = line.strip()
            
            if line == "[Interface]":
                in_interface = True
                continue
            elif line.startswith("[") and line != "[Interface]":
                in_interface = False
                continue
            
            if in_interface and "=" in line:
                # Use first = as delimiter
                eq_idx = line.index("=")
                key = line[:eq_idx].strip()
                value = line[eq_idx + 1:].strip()
                interface_data[key] = value
        
        if not interface_data.get("PrivateKey"):
            logger.error("External config missing PrivateKey")
            return None
        
        # Generate public key from private key
        public_key = interface_data.get("PublicKey", "")
        private_key = interface_data.get("PrivateKey", "")
        
        # Try to derive public key if not provided
        if not public_key and private_key:
            try:
                from .Security.SecureCommand import execute_wg_command
                result = execute_wg_command(action='pubkey', private_key=private_key)
                if result.get('success') and result.get('stdout'):
                    public_key = result['stdout'].strip()
            except Exception as e:
                logger.warning(f"Could not derive public key: {e}")
        
        # Detect protocol
        protocol = "wg"
        awg_data = {}
        for param in awg_params + cps_params:
            if param in interface_data:
                protocol = "awg"
                awg_data[param] = interface_data[param]
        
        node_name = config_name or f"external_{uuid.uuid4().hex[:8]}"
        
        node = MeshNode(
            id=str(uuid.uuid4()),
            name=node_name,
            public_key=public_key,
            private_key=private_key,
            address=interface_data.get("Address", ""),
            endpoint=interface_data.get("Endpoint", ""),
            listen_port=int(interface_data.get("ListenPort", 51820)),
            protocol=protocol,
            is_external=True,
            awg_params=awg_data
        )
        
        logger.info(f"Parsed external config as node: {node.name}")
        return node
    
    def add_external_node_to_mesh(self, mesh_id: str, 
                                  config_content: str,
                                  config_name: str = "") -> Optional[MeshNode]:
        """Add an external config to an existing mesh network"""
        if mesh_id not in self.mesh_networks:
            logger.error(f"Mesh network {mesh_id} not found")
            return None
        
        node = self.parse_external_config(config_content, config_name)
        if not node:
            return None
        
        mesh = self.mesh_networks[mesh_id]
        if mesh.add_node(node):
            return node
        return None
    
    def check_ip_collisions(self, mesh: MeshNetwork) -> List[Dict[str, Any]]:
        """
        Check for IP address collisions between mesh nodes
        Returns list of collision details
        """
        collisions = []
        addresses = []
        
        for node in mesh.nodes.values():
            if not node.address:
                continue
            
            try:
                net = ipaddress.ip_interface(node.address)
                network = net.network
                
                # Check against existing addresses
                for existing in addresses:
                    if network.overlaps(existing['network']):
                        collisions.append({
                            "type": "overlap",
                            "node_a": node.name,
                            "node_b": existing['node_name'],
                            "address_a": node.address,
                            "address_b": existing['address']
                        })
                
                addresses.append({
                    "node_name": node.name,
                    "address": node.address,
                    "network": network
                })
                
            except ValueError as e:
                collisions.append({
                    "type": "invalid",
                    "node": node.name,
                    "address": node.address,
                    "error": str(e)
                })
        
        return collisions
    
    def suggest_non_conflicting_ip(self, mesh: MeshNetwork, 
                                   preferred_subnet: str = "10.0.0.0/8") -> str:
        """
        Suggest a non-conflicting IP address for a new node
        """
        used_ips: Set[ipaddress.IPv4Address] = set()
        
        for node in mesh.nodes.values():
            if node.address:
                try:
                    net = ipaddress.ip_interface(node.address)
                    used_ips.add(net.ip)
                except ValueError:
                    pass
        
        try:
            base_network = ipaddress.ip_network(preferred_subnet, strict=False)
            
            # Find first available /24 subnet
            for subnet in base_network.subnets(new_prefix=24):
                # Check if any IP in this subnet is used
                subnet_used = False
                for used_ip in used_ips:
                    if used_ip in subnet:
                        subnet_used = True
                        break
                
                if not subnet_used:
                    # Return first usable host in this subnet
                    hosts = list(subnet.hosts())
                    if hosts:
                        return f"{hosts[0]}/24"
            
        except ValueError as e:
            logger.error(f"Invalid subnet: {e}")
        
        # Fallback
        return "10.100.0.1/24"
    
    def generate_mesh_preview(self, mesh: MeshNetwork) -> Dict[str, Any]:
        """
        Generate a preview of what changes would be made to apply the mesh
        """
        preview = {
            "mesh_id": mesh.id,
            "mesh_name": mesh.name,
            "nodes": [],
            "connections": [],
            "peer_entries": [],
            "warnings": []
        }
        
        # Add node info
        for node in mesh.nodes.values():
            preview["nodes"].append(node.to_dict())
        
        # Add connection info
        for conn in mesh.connections:
            node_a = mesh.nodes.get(conn.node_a_id)
            node_b = mesh.nodes.get(conn.node_b_id)
            
            if node_a and node_b:
                preview["connections"].append({
                    "from": node_a.name,
                    "to": node_b.name,
                    "enabled": conn.enabled
                })
                
                # Generate peer entry previews
                # Entry for node_a to add node_b as peer
                preview["peer_entries"].append({
                    "config": node_a.name,
                    "peer_name": f"mesh_{node_b.name}",
                    "public_key": node_b.public_key,
                    "allowed_ips": conn.allowed_ips_a_to_b,
                    "endpoint": f"{node_b.endpoint}:{node_b.listen_port}" if node_b.endpoint else ""
                })
                
                # Entry for node_b to add node_a as peer
                preview["peer_entries"].append({
                    "config": node_b.name,
                    "peer_name": f"mesh_{node_a.name}",
                    "public_key": node_a.public_key,
                    "allowed_ips": conn.allowed_ips_b_to_a,
                    "endpoint": f"{node_a.endpoint}:{node_a.listen_port}" if node_a.endpoint else ""
                })
        
        # Check for collisions
        collisions = self.check_ip_collisions(mesh)
        for collision in collisions:
            preview["warnings"].append({
                "type": "ip_collision",
                "details": collision
            })
        
        return preview
    
    def generate_preshared_key(self) -> str:
        """Generate a new WireGuard preshared key"""
        try:
            from .Security.SecureCommand import execute_wg_command
            result = execute_wg_command(action='genpsk')
            if result.get('success') and result.get('stdout'):
                return result['stdout'].strip()
        except Exception as e:
            logger.error(f"Failed to generate preshared key: {e}")
        
        # Fallback: generate using secrets
        import secrets
        import base64
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    def apply_mesh(self, mesh: MeshNetwork, 
                   create_new: bool = True,
                   new_config_suffix: str = "_mesh") -> Dict[str, Any]:
        """
        Apply mesh configuration to the WireGuard configurations
        
        Args:
            mesh: The mesh network to apply
            create_new: If True, create new configurations. If False, modify existing.
            new_config_suffix: Suffix for new configuration names
        
        Returns:
            Result dictionary with status and details
        """
        from .Core import Configurations, Configuration
        from .DashboardConfig import DashboardConfig
        
        result = {
            "success": True,
            "message": "",
            "created_configs": [],
            "modified_configs": [],
            "errors": []
        }
        
        if len(mesh.connections) == 0:
            result["success"] = False
            result["message"] = "No connections defined in mesh"
            return result
        
        try:
            for conn in mesh.connections:
                if not conn.enabled:
                    continue
                
                node_a = mesh.nodes.get(conn.node_a_id)
                node_b = mesh.nodes.get(conn.node_b_id)
                
                if not node_a or not node_b:
                    continue
                
                # Skip external nodes for now (they can't be modified)
                # Add peer entries to non-external nodes
                
                if not node_a.is_external and node_a.id in Configurations:
                    try:
                        config = Configurations[node_a.id]
                        # Add node_b as peer to node_a's configuration
                        peer_data = {
                            "public_key": node_b.public_key,
                            "allowed_ips": [conn.allowed_ips_a_to_b],
                            "preshared_key": conn.preshared_key,
                            "DNS": DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1],
                            "endpoint_allowed_ip": conn.allowed_ips_a_to_b,
                            "mtu": int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1]),
                            "keepalive": int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1])
                        }
                        
                        # This would add the peer - for preview, just record it
                        result["modified_configs"].append({
                            "config": node_a.id,
                            "action": "add_peer",
                            "peer": node_b.name,
                            "peer_data": peer_data
                        })
                        
                    except Exception as e:
                        result["errors"].append(f"Error adding peer to {node_a.id}: {str(e)}")
                
                if not node_b.is_external and node_b.id in Configurations:
                    try:
                        config = Configurations[node_b.id]
                        # Add node_a as peer to node_b's configuration
                        peer_data = {
                            "public_key": node_a.public_key,
                            "allowed_ips": [conn.allowed_ips_b_to_a],
                            "preshared_key": conn.preshared_key,
                            "DNS": DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1],
                            "endpoint_allowed_ip": conn.allowed_ips_b_to_a,
                            "mtu": int(DashboardConfig.GetConfig("Peers", "peer_MTU")[1]),
                            "keepalive": int(DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1])
                        }
                        
                        result["modified_configs"].append({
                            "config": node_b.id,
                            "action": "add_peer",
                            "peer": node_a.name,
                            "peer_data": peer_data
                        })
                        
                    except Exception as e:
                        result["errors"].append(f"Error adding peer to {node_b.id}: {str(e)}")
            
            if result["errors"]:
                result["success"] = False
                result["message"] = f"Completed with {len(result['errors'])} errors"
            else:
                result["message"] = f"Mesh applied successfully: {len(result['modified_configs'])} peer entries"
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"Failed to apply mesh: {str(e)}"
            logger.error(f"Error applying mesh: {e}", exc_info=True)
        
        return result
    
    def get_mesh(self, mesh_id: str) -> Optional[MeshNetwork]:
        """Get a mesh network by ID"""
        if not mesh_id:
            return None
        # Ensure exact string match
        return self.mesh_networks.get(str(mesh_id))
    
    def list_meshes(self) -> List[Dict[str, Any]]:
        """List all mesh networks"""
        return [
            {
                "id": mesh.id,
                "name": mesh.name,
                "node_count": len(mesh.nodes),
                "connection_count": len(mesh.connections),
                "created_at": mesh.created_at.isoformat()
            }
            for mesh in self.mesh_networks.values()
        ]
    
    def delete_mesh(self, mesh_id: str) -> bool:
        """Delete a mesh network"""
        if not mesh_id:
            logger.warning("Attempted to delete mesh with empty ID")
            return False
        
        mesh_id = str(mesh_id)  # Ensure it's a string
        
        if mesh_id in self.mesh_networks:
            # Store reference for logging
            mesh_name = self.mesh_networks[mesh_id].name if self.mesh_networks[mesh_id] else "unknown"
            del self.mesh_networks[mesh_id]
            # Verify deletion
            if mesh_id not in self.mesh_networks:
                logger.info(f"Successfully deleted mesh network: {mesh_id} ({mesh_name})")
                return True
            else:
                logger.error(f"Failed to delete mesh network: {mesh_id} still exists after deletion")
                return False
        else:
            logger.warning(f"Mesh network not found for deletion: {mesh_id}")
            return False


# Global mesh network manager instance
mesh_manager = MeshNetworkManager()

