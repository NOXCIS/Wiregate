<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Network } from 'vis-network';
import LocaleText from '@/components/text/localeText.vue';
import ProtocolBadge from '@/components/protocolBadge.vue';

const props = defineProps({
  mesh: {
    type: Object,
    default: null
  },
  connections: {
    type: Array,
    default: () => []
  },
  preview: {
    type: Object,
    default: null
  },
  interactive: {
    type: Boolean,
    default: true
  },
  height: {
    type: String,
    default: '600px'
  }
});

const emit = defineEmits(['node-click', 'edge-click', 'node-select', 'layout-change']);

const networkContainer = ref(null);
const networkInstance = ref(null);
const selectedNodeId = ref(null);
const selectedEdgeId = ref(null);
const layoutType = ref('hierarchical'); // hierarchical, circular, force
const showLabels = ref(true);
const showDetails = ref(false);

// Computed properties for network data
const nodes = computed(() => {
  const nodeList = [];
  
  // Get nodes from mesh or preview
  const meshNodes = props.mesh?.nodes ? Object.values(props.mesh.nodes) : [];
  const previewNodes = props.preview?.nodes || [];
  const allNodes = meshNodes.length > 0 ? meshNodes : previewNodes;
  
  allNodes.forEach((node, index) => {
    const nodeConnections = getNodeConnectionCount(node.id);
    const nodeColor = getNodeColor(node);
    
    nodeList.push({
      id: node.id,
      label: showLabels.value ? node.name : '',
      title: getNodeTooltip(node),
      color: {
        background: nodeColor.background,
        border: nodeColor.border,
        highlight: {
          background: nodeColor.highlight,
          border: nodeColor.border
        }
      },
      shape: node.is_external ? 'diamond' : 'dot',
      size: 25 + (nodeConnections * 3),
      font: {
        size: 14,
        color: '#333',
        face: 'Arial'
      },
      borderWidth: node.is_external ? 3 : 2,
      borderWidthSelected: 4,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.2)',
        size: 5,
        x: 2,
        y: 2
      },
      // Custom data
      data: {
        name: node.name,
        address: node.address,
        protocol: node.protocol,
        is_external: node.is_external,
        public_key: node.public_key,
        listen_port: node.listen_port,
        endpoint: node.endpoint,
        connection_count: nodeConnections
      }
    });
  });
  
  return nodeList;
});

const edges = computed(() => {
  const edgeList = [];
  
  // Get connections from props or preview
  const connections = props.connections || props.preview?.connections || [];
  
  connections.forEach((conn, index) => {
    const sourceId = conn.source || conn.from || conn.node_a_id;
    const targetId = conn.target || conn.to || conn.node_b_id;
    
    if (!sourceId || !targetId) return;
    
    edgeList.push({
      id: `edge-${index}`,
      from: sourceId,
      to: targetId,
      label: '',
      color: {
        color: '#4A90E2',
        highlight: '#1E88E5',
        hover: '#1976D2'
      },
      width: 3,
      smooth: {
        type: 'continuous',
        roundness: 0.5
      },
      arrows: {
        to: {
          enabled: false
        },
        middle: {
          enabled: false
        },
        from: {
          enabled: false
        }
      },
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.1)',
        size: 3
      },
      // Custom data
      data: {
        enabled: conn.enabled !== false,
        preshared_key: conn.preshared_key || '',
        allowed_ips_a_to_b: conn.allowed_ips_a_to_b || '',
        allowed_ips_b_to_a: conn.allowed_ips_b_to_a || ''
      }
    });
  });
  
  return edgeList;
});

const networkData = computed(() => ({
  nodes: nodes.value,
  edges: edges.value
}));

const networkOptions = computed(() => {
  const baseOptions = {
    nodes: {
      font: {
        size: 14,
        face: 'Arial'
      },
      shadow: true
    },
    edges: {
      shadow: true,
      smooth: {
        type: 'continuous',
        roundness: 0.5
      }
    },
    physics: {
      enabled: true,
      stabilization: {
        enabled: true,
        iterations: 200
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      zoomView: true,
      dragView: true
    }
  };
  
  // Layout-specific options
  if (layoutType.value === 'hierarchical') {
    baseOptions.layout = {
      hierarchical: {
        enabled: true,
        direction: 'UD', // Up-Down
        sortMethod: 'directed',
        levelSeparation: 150,
        nodeSpacing: 200,
        treeSpacing: 200,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true
      }
    };
    baseOptions.physics = {
      enabled: false
    };
  } else if (layoutType.value === 'circular') {
    baseOptions.layout = {
      randomSeed: 2
    };
    baseOptions.physics = {
      enabled: false
    };
  } else if (layoutType.value === 'force') {
    baseOptions.physics = {
      enabled: true,
      stabilization: {
        enabled: true,
        iterations: 200
      },
      barnesHut: {
        gravitationalConstant: -2000,
        centralGravity: 0.3,
        springLength: 200,
        springConstant: 0.04,
        damping: 0.09
      }
    };
  }
  
  return baseOptions;
});

// Helper functions
function getNodeConnectionCount(nodeId) {
  const connections = props.connections || props.preview?.connections || [];
  return connections.filter(conn => {
    const sourceId = conn.source || conn.from || conn.node_a_id;
    const targetId = conn.target || conn.to || conn.node_b_id;
    return sourceId === nodeId || targetId === nodeId;
  }).length;
}

function getNodeColor(node) {
  if (node.is_external) {
    return {
      background: '#FFF3E0',
      border: '#FF9800',
      highlight: '#FFE0B2'
    };
  }
  
  if (node.protocol === 'awg') {
    return {
      background: '#F3E5F5',
      border: '#7B1FA2',
      highlight: '#E1BEE7'
    };
  }
  
  return {
    background: '#E3F2FD',
    border: '#2196F3',
    highlight: '#BBDEFB'
  };
}

function getNodeTooltip(node) {
  let tooltip = `<strong>${node.name}</strong><br/>`;
  tooltip += `Protocol: ${node.protocol.toUpperCase()}<br/>`;
  if (node.address) tooltip += `Address: ${node.address}<br/>`;
  if (node.endpoint) tooltip += `Endpoint: ${node.endpoint}<br/>`;
  if (node.listen_port) tooltip += `Port: ${node.listen_port}<br/>`;
  tooltip += `Connections: ${getNodeConnectionCount(node.id)}<br/>`;
  if (node.is_external) tooltip += `<em>External Node</em>`;
  return tooltip;
}

// Network event handlers
function setupNetworkEvents() {
  if (!networkInstance.value) return;
  
  networkInstance.value.on('click', (params) => {
    if (params.nodes.length > 0) {
      selectedNodeId.value = params.nodes[0];
      selectedEdgeId.value = null;
      const node = nodes.value.find(n => n.id === params.nodes[0]);
      if (node) {
        emit('node-click', node);
        emit('node-select', node);
      }
    } else if (params.edges.length > 0) {
      selectedEdgeId.value = params.edges[0];
      selectedNodeId.value = null;
      const edge = edges.value.find(e => e.id === params.edges[0]);
      if (edge) {
        emit('edge-click', edge);
      }
    } else {
      selectedNodeId.value = null;
      selectedEdgeId.value = null;
    }
  });
  
  networkInstance.value.on('hoverNode', (params) => {
    networkContainer.value.style.cursor = 'pointer';
  });
  
  networkInstance.value.on('blurNode', () => {
    networkContainer.value.style.cursor = 'default';
  });
  
  networkInstance.value.on('stabilizationEnd', () => {
    // Network has stabilized
  });
}

// Layout functions
function applyLayout(type) {
  layoutType.value = type;
  nextTick(() => {
    if (networkInstance.value) {
      networkInstance.value.setOptions(networkOptions.value);
    }
  });
  emit('layout-change', type);
}

function fitNetwork() {
  if (networkInstance.value) {
    networkInstance.value.fit({
      animation: {
        duration: 500,
        easingFunction: 'easeInOutQuad'
      }
    });
  }
}

function centerNetwork() {
  if (networkInstance.value) {
    networkInstance.value.moveTo({
      position: { x: 0, y: 0 },
      scale: 1,
      animation: {
        duration: 500,
        easingFunction: 'easeInOutQuad'
      }
    });
  }
}

// Watch for data changes
watch(networkData, (newData) => {
  if (networkInstance.value) {
    networkInstance.value.setData(newData);
    nextTick(() => {
      fitNetwork();
    });
  }
}, { deep: true });

watch(layoutType, () => {
  if (networkInstance.value) {
    networkInstance.value.setOptions(networkOptions.value);
    nextTick(() => {
      fitNetwork();
    });
  }
});

// Lifecycle
onMounted(() => {
  nextTick(() => {
    if (networkContainer.value && networkData.value.nodes.length > 0) {
      networkInstance.value = new Network(
        networkContainer.value,
        networkData.value,
        networkOptions.value
      );
      
      setupNetworkEvents();
      
      // Fit network after a short delay to ensure rendering
      setTimeout(() => {
        fitNetwork();
      }, 100);
    }
  });
});

onBeforeUnmount(() => {
  if (networkInstance.value) {
    networkInstance.value.destroy();
    networkInstance.value = null;
  }
});
</script>

<template>
  <div class="mesh-network-visualizer">
    <div class="card rounded-3 shadow">
      <div class="card-header d-flex align-items-center justify-content-between flex-wrap gap-2">
        <div>
          <i class="bi bi-diagram-3 me-2"></i>
          <LocaleText t="Network Topology Visualization"></LocaleText>
          <span class="badge bg-secondary ms-2">{{ nodes.length }} nodes</span>
          <span class="badge bg-info ms-1">{{ edges.length }} connections</span>
        </div>
        <div class="d-flex gap-2 flex-wrap">
          <!-- Layout Controls -->
          <div class="btn-group" role="group">
            <button
              type="button"
              class="btn btn-sm"
              :class="layoutType === 'hierarchical' ? 'btn-primary' : 'btn-outline-primary'"
              @click="applyLayout('hierarchical')"
              title="Hierarchical Layout"
            >
              <i class="bi bi-diagram-3"></i>
            </button>
            <button
              type="button"
              class="btn btn-sm"
              :class="layoutType === 'circular' ? 'btn-primary' : 'btn-outline-primary'"
              @click="applyLayout('circular')"
              title="Circular Layout"
            >
              <i class="bi bi-circle"></i>
            </button>
            <button
              type="button"
              class="btn btn-sm"
              :class="layoutType === 'force' ? 'btn-primary' : 'btn-outline-primary'"
              @click="applyLayout('force')"
              title="Force-Directed Layout"
            >
              <i class="bi bi-shuffle"></i>
            </button>
          </div>
          
          <!-- View Controls -->
          <div class="btn-group" role="group">
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="fitNetwork"
              title="Fit to Screen"
            >
              <i class="bi bi-arrows-angle-contract"></i>
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="centerNetwork"
              title="Center View"
            >
              <i class="bi bi-compass"></i>
            </button>
          </div>
          
          <!-- Toggle Controls -->
          <div class="btn-group" role="group">
            <button
              type="button"
              class="btn btn-sm"
              :class="showLabels ? 'btn-success' : 'btn-outline-success'"
              @click="showLabels = !showLabels"
              title="Toggle Labels"
            >
              <i class="bi bi-tag"></i>
            </button>
            <button
              type="button"
              class="btn btn-sm"
              :class="showDetails ? 'btn-info' : 'btn-outline-info'"
              @click="showDetails = !showDetails"
              title="Toggle Details"
            >
              <i class="bi bi-info-circle"></i>
            </button>
          </div>
        </div>
      </div>
      
      <div class="card-body p-0">
        <!-- Network Canvas -->
        <div
          ref="networkContainer"
          class="network-container"
          :style="{ height: height }"
        ></div>
        
        <!-- Legend -->
        <div class="network-legend p-3 border-top">
          <div class="d-flex align-items-center gap-4 flex-wrap">
            <div class="legend-item">
              <div class="legend-icon" style="background: #E3F2FD; border-color: #2196F3;"></div>
              <span><LocaleText t="WireGuard Node"></LocaleText></span>
            </div>
            <div class="legend-item">
              <div class="legend-icon" style="background: #F3E5F5; border-color: #7B1FA2;"></div>
              <span><LocaleText t="AmneziaWG Node"></LocaleText></span>
            </div>
            <div class="legend-item">
              <div class="legend-icon legend-diamond" style="background: #FFF3E0; border-color: #FF9800;"></div>
              <span><LocaleText t="External Node"></LocaleText></span>
            </div>
            <div class="legend-item">
              <div class="legend-line"></div>
              <span><LocaleText t="Connection"></LocaleText></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Node Details Panel -->
      <div v-if="showDetails && selectedNodeId" class="card-footer">
        <div class="node-details">
          <div
            v-for="node in nodes.filter(n => n.id === selectedNodeId)"
            :key="node.id"
          >
            <h6 class="mb-3">
              <i class="bi bi-hdd-network me-2"></i>
              {{ node.data.name }}
            </h6>
            <div class="row g-2">
              <div class="col-md-6">
                <strong><LocaleText t="Protocol"></LocaleText>:</strong>
                <ProtocolBadge :protocol="node.data.protocol" />
              </div>
              <div class="col-md-6">
                <strong><LocaleText t="Address"></LocaleText>:</strong>
                <code>{{ node.data.address || 'N/A' }}</code>
              </div>
              <div class="col-md-6">
                <strong><LocaleText t="Endpoint"></LocaleText>:</strong>
                <span>{{ node.data.endpoint || 'N/A' }}</span>
              </div>
              <div class="col-md-6">
                <strong><LocaleText t="Listen Port"></LocaleText>:</strong>
                <span>{{ node.data.listen_port || 'N/A' }}</span>
              </div>
              <div class="col-md-6">
                <strong><LocaleText t="Connections"></LocaleText>:</strong>
                <span class="badge bg-info">{{ node.data.connection_count }}</span>
              </div>
              <div class="col-md-6">
                <strong><LocaleText t="Type"></LocaleText>:</strong>
                <span class="badge" :class="node.data.is_external ? 'bg-warning' : 'bg-success'">
                  {{ node.data.is_external ? 'External' : 'Internal' }}
                </span>
              </div>
              <div class="col-12" v-if="node.data.public_key">
                <strong><LocaleText t="Public Key"></LocaleText>:</strong>
                <code class="d-block text-truncate" style="max-width: 100%;" :title="node.data.public_key">
                  {{ node.data.public_key }}
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mesh-network-visualizer {
  width: 100%;
}

.network-container {
  width: 100%;
  background: var(--bs-body-bg);
  border: 1px solid var(--bs-border-color);
  position: relative;
  overflow: hidden;
}

.network-legend {
  background: var(--bs-secondary-bg);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.legend-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid;
  display: inline-block;
}

.legend-icon.legend-diamond {
  border-radius: 0;
  transform: rotate(45deg);
  width: 14px;
  height: 14px;
  margin: 0 3px;
}

.legend-line {
  width: 30px;
  height: 3px;
  background: #4A90E2;
  display: inline-block;
}

.node-details {
  font-size: 0.9rem;
}

.node-details code {
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
  background: var(--bs-secondary-bg);
  border-radius: 0.25rem;
}

/* Network canvas styling */
.network-container :deep(.vis-network) {
  outline: none;
}

.network-container :deep(.vis-tooltip) {
  background-color: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .network-container {
    height: 400px !important;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start !important;
  }
  
  .btn-group {
    width: 100%;
    margin-top: 0.5rem;
  }
}
</style>

