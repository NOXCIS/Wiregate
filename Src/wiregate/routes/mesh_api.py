"""
FastAPI Mesh Network Router
Handles mesh network creation, management, and configuration merging
"""
import logging
from fastapi import APIRouter, Query, Depends, UploadFile, File
from typing import Dict, Any, List, Optional

from ..models.responses import StandardResponse
from ..modules.Core import Configurations
from ..modules.MeshNetwork import mesh_manager, MeshNetwork, MeshNode, MeshConnection
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.get('/mesh/list', response_model=StandardResponse)
async def list_mesh_networks(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """List all mesh networks"""
    try:
        meshes = mesh_manager.list_meshes()
        return StandardResponse(
            status=True,
            data=meshes
        )
    except Exception as e:
        logger.error(f"Error listing mesh networks: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to list mesh networks: {str(e)}"
        )


@router.get('/mesh/configurations', response_model=StandardResponse)
async def get_available_configurations(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get list of available configurations for meshing"""
    try:
        configs = []
        for name, config in Configurations.items():
            configs.append({
                "name": name,
                "public_key": config.PublicKey,
                "address": config.Address,
                "listen_port": config.ListenPort,
                "protocol": config.get_iface_proto(),
                "status": config.getStatus(),
                "peer_count": len(config.Peers) if hasattr(config, 'Peers') else 0
            })
        
        return StandardResponse(
            status=True,
            data=configs
        )
    except Exception as e:
        logger.error(f"Error getting configurations: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get configurations: {str(e)}"
        )


@router.post('/mesh/create', response_model=StandardResponse)
async def create_mesh_network(
    mesh_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Create a new mesh network from selected configurations"""
    try:
        logger.debug(f"Received mesh create request: {mesh_data}")
        config_names = mesh_data.get('configurations', [])
        mesh_name = mesh_data.get('name', '')
        
        logger.debug(f"Config names: {config_names}, type: {type(config_names)}, length: {len(config_names) if isinstance(config_names, list) else 'N/A'}")
        
        # Validate input types - must be done before any processing
        if not isinstance(config_names, list):
            logger.warning(f"Invalid configurations type: {type(config_names)}")
            return StandardResponse(
                status=False,
                message="Configurations must be a list"
            )
        
        # Validate minimum configurations - this is the critical check
        config_count = len(config_names)
        if config_count < 2:
            logger.warning(f"Insufficient configurations: {config_count} provided, need at least 2")
            # Create response with explicit status=False
            response = StandardResponse(
                status=False,
                message="At least 2 configurations are required to create a mesh",
                data=None
            )
            # Double-check the status before returning
            logger.info(f"Returning validation failure: status={response.status}, message={response.message}, data={response.data}")
            # Use model_dump to ensure proper serialization
            logger.debug(f"Response model_dump: {response.model_dump()}")
            return response
        
        # Validate all config names are strings
        if not all(isinstance(name, str) and name for name in config_names):
            return StandardResponse(
                status=False,
                message="All configuration names must be non-empty strings"
            )
        
        mesh = mesh_manager.create_mesh_from_configs(config_names, mesh_name)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Failed to create mesh network"
            )
        
        return StandardResponse(
            status=True,
            message=f"Mesh network '{mesh.name}' created with {len(mesh.nodes)} nodes",
            data=mesh.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error creating mesh network: {e}", exc_info=True)
        return StandardResponse(
            status=False,
            message=f"Failed to create mesh network: {str(e)}"
        )


@router.get('/mesh/{mesh_id}', response_model=StandardResponse)
async def get_mesh_network(
    mesh_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get details of a specific mesh network"""
    try:
        if not mesh_id or not isinstance(mesh_id, str):
            return StandardResponse(
                status=False,
                message="Invalid mesh ID"
            )
        
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if mesh is None:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        return StandardResponse(
            status=True,
            data=mesh.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error getting mesh network: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get mesh network: {str(e)}"
        )


@router.delete('/mesh/{mesh_id}', response_model=StandardResponse)
async def delete_mesh_network(
    mesh_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Delete a mesh network"""
    try:
        if not mesh_id or not isinstance(mesh_id, str):
            return StandardResponse(
                status=False,
                message="Invalid mesh ID"
            )
        
        # Check if mesh exists before deletion
        mesh = mesh_manager.get_mesh(mesh_id)
        if mesh is None:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        # Delete the mesh
        deleted = mesh_manager.delete_mesh(mesh_id)
        
        if deleted:
            # Verify deletion
            verify_mesh = mesh_manager.get_mesh(mesh_id)
            if verify_mesh is not None:
                logger.warning(f"Mesh {mesh_id} still exists after deletion attempt")
                return StandardResponse(
                    status=False,
                    message="Failed to delete mesh network"
                )
            
            return StandardResponse(
                status=True,
                message="Mesh network deleted"
            )
        
        return StandardResponse(
            status=False,
            message="Mesh network not found"
        )
        
    except Exception as e:
        logger.error(f"Error deleting mesh network: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to delete mesh network: {str(e)}"
        )


@router.post('/mesh/{mesh_id}/connection', response_model=StandardResponse)
async def add_mesh_connection(
    mesh_id: str,
    connection_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Add a connection between two nodes in a mesh"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        node_a_id = connection_data.get('node_a_id')
        node_b_id = connection_data.get('node_b_id')
        generate_psk = connection_data.get('generate_preshared_key', False)
        
        if not node_a_id or not node_b_id:
            return StandardResponse(
                status=False,
                message="Both node_a_id and node_b_id are required"
            )
        
        preshared_key = ""
        if generate_psk:
            preshared_key = mesh_manager.generate_preshared_key()
        
        connection = mesh.add_connection(node_a_id, node_b_id, preshared_key)
        
        if not connection:
            return StandardResponse(
                status=False,
                message="Failed to add connection (nodes may not exist or connection already exists)"
            )
        
        return StandardResponse(
            status=True,
            message="Connection added",
            data=connection.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error adding connection: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to add connection: {str(e)}"
        )


@router.delete('/mesh/{mesh_id}/connection', response_model=StandardResponse)
async def remove_mesh_connection(
    mesh_id: str,
    node_a_id: str = Query(..., description="First node ID"),
    node_b_id: str = Query(..., description="Second node ID"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Remove a connection between two nodes"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        if mesh.remove_connection(node_a_id, node_b_id):
            return StandardResponse(
                status=True,
                message="Connection removed"
            )
        
        return StandardResponse(
            status=False,
            message="Connection not found"
        )
        
    except Exception as e:
        logger.error(f"Error removing connection: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to remove connection: {str(e)}"
        )


@router.post('/mesh/{mesh_id}/connections/bulk', response_model=StandardResponse)
async def update_mesh_connections_bulk(
    mesh_id: str,
    connections_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update all connections in a mesh at once"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        connections = connections_data.get('connections', [])
        generate_psk = connections_data.get('generate_preshared_keys', False)
        
        # Clear existing connections
        mesh.connections = []
        
        # Add new connections
        added = 0
        for conn in connections:
            node_a_id = conn.get('node_a_id')
            node_b_id = conn.get('node_b_id')
            
            if node_a_id and node_b_id:
                preshared_key = ""
                if generate_psk:
                    preshared_key = mesh_manager.generate_preshared_key()
                
                if mesh.add_connection(node_a_id, node_b_id, preshared_key):
                    added += 1
        
        return StandardResponse(
            status=True,
            message=f"Updated connections: {added} added",
            data=mesh.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error updating connections: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to update connections: {str(e)}"
        )


@router.post('/mesh/upload', response_model=StandardResponse)
async def upload_external_config(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Upload and parse an external WireGuard/AmneziaWG config file"""
    try:
        if not file.filename.endswith('.conf'):
            return StandardResponse(
                status=False,
                message="Only .conf files are allowed"
            )
        
        content = await file.read()
        config_content = content.decode('utf-8')
        config_name = file.filename.replace('.conf', '')
        
        node = mesh_manager.parse_external_config(config_content, config_name)
        
        if not node:
            return StandardResponse(
                status=False,
                message="Failed to parse configuration file"
            )
        
        return StandardResponse(
            status=True,
            message=f"Successfully parsed external config: {node.name}",
            data=node.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error uploading config: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to upload config: {str(e)}"
        )


@router.post('/mesh/{mesh_id}/upload', response_model=StandardResponse)
async def add_external_config_to_mesh(
    mesh_id: str,
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Upload an external config and add it to an existing mesh"""
    try:
        if not file.filename.endswith('.conf'):
            return StandardResponse(
                status=False,
                message="Only .conf files are allowed"
            )
        
        content = await file.read()
        config_content = content.decode('utf-8')
        config_name = file.filename.replace('.conf', '')
        
        node = mesh_manager.add_external_node_to_mesh(mesh_id, config_content, config_name)
        
        if not node:
            return StandardResponse(
                status=False,
                message="Failed to add external config to mesh"
            )
        
        mesh = mesh_manager.get_mesh(mesh_id)
        
        return StandardResponse(
            status=True,
            message=f"Added external node: {node.name}",
            data=mesh.to_dict() if mesh else None
        )
        
    except Exception as e:
        logger.error(f"Error adding external config to mesh: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to add external config: {str(e)}"
        )


@router.post('/mesh/{mesh_id}/node', response_model=StandardResponse)
async def add_node_to_mesh(
    mesh_id: str,
    node_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Add an existing configuration as a node to mesh"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        config_name = node_data.get('configuration')
        
        if not config_name or config_name not in Configurations:
            return StandardResponse(
                status=False,
                message="Configuration not found"
            )
        
        config = Configurations[config_name]
        
        node = MeshNode(
            id=config.Name,
            name=config.Name,
            public_key=config.PublicKey,
            private_key=config.PrivateKey,
            address=config.Address,
            endpoint=config.Name,
            listen_port=int(config.ListenPort) if config.ListenPort else 51820,
            protocol=config.get_iface_proto()
        )
        
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
                "H4": config.H4
            }
        
        if mesh.add_node(node):
            return StandardResponse(
                status=True,
                message=f"Node {config_name} added to mesh",
                data=mesh.to_dict()
            )
        
        return StandardResponse(
            status=False,
            message="Node already exists in mesh"
        )
        
    except Exception as e:
        logger.error(f"Error adding node to mesh: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to add node: {str(e)}"
        )


@router.delete('/mesh/{mesh_id}/node/{node_id}', response_model=StandardResponse)
async def remove_node_from_mesh(
    mesh_id: str,
    node_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Remove a node from mesh"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        if mesh.remove_node(node_id):
            return StandardResponse(
                status=True,
                message="Node removed from mesh",
                data=mesh.to_dict()
            )
        
        return StandardResponse(
            status=False,
            message="Node not found in mesh"
        )
        
    except Exception as e:
        logger.error(f"Error removing node from mesh: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to remove node: {str(e)}"
        )


@router.get('/mesh/{mesh_id}/preview', response_model=StandardResponse)
async def preview_mesh_changes(
    mesh_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Preview the changes that would be made when applying the mesh"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        preview = mesh_manager.generate_mesh_preview(mesh)
        
        return StandardResponse(
            status=True,
            data=preview
        )
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to generate preview: {str(e)}"
        )


@router.post('/mesh/{mesh_id}/apply', response_model=StandardResponse)
async def apply_mesh_configuration(
    mesh_id: str,
    apply_options: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Apply mesh configuration to WireGuard configurations"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        create_new = apply_options.get('create_new', False)
        
        result = mesh_manager.apply_mesh(mesh, create_new=create_new)
        
        return StandardResponse(
            status=result['success'],
            message=result['message'],
            data={
                "created_configs": result.get('created_configs', []),
                "modified_configs": result.get('modified_configs', []),
                "errors": result.get('errors', [])
            }
        )
        
    except Exception as e:
        logger.error(f"Error applying mesh: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to apply mesh: {str(e)}"
        )


@router.get('/mesh/{mesh_id}/check-collisions', response_model=StandardResponse)
async def check_ip_collisions(
    mesh_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Check for IP address collisions in the mesh"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        collisions = mesh_manager.check_ip_collisions(mesh)
        
        return StandardResponse(
            status=True,
            data={
                "has_collisions": len(collisions) > 0,
                "collisions": collisions
            }
        )
        
    except Exception as e:
        logger.error(f"Error checking collisions: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to check collisions: {str(e)}"
        )


@router.get('/mesh/{mesh_id}/suggest-ip', response_model=StandardResponse)
async def suggest_ip_address(
    mesh_id: str,
    subnet: str = Query(default="10.0.0.0/8", description="Preferred subnet"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Suggest a non-conflicting IP address for a new node"""
    try:
        mesh = mesh_manager.get_mesh(mesh_id)
        
        if not mesh:
            return StandardResponse(
                status=False,
                message="Mesh network not found"
            )
        
        suggested_ip = mesh_manager.suggest_non_conflicting_ip(mesh, subnet)
        
        return StandardResponse(
            status=True,
            data={"suggested_ip": suggested_ip}
        )
        
    except Exception as e:
        logger.error(f"Error suggesting IP: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to suggest IP: {str(e)}"
        )

