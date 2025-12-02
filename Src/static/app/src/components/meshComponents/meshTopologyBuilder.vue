<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
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
  }
});

const emit = defineEmits(['update:connections', 'upload']);

const canvasRef = ref(null);
const containerRef = ref(null);
const nodePositions = ref({});
const isDragging = ref(false);
const draggedNode = ref(null);
const dragOffset = ref({ x: 0, y: 0 });
const selectedNodes = ref([]);
const hoveredNode = ref(null);
const connectionMode = ref(false);
const connectionStart = ref(null);
const tempConnectionEnd = ref({ x: 0, y: 0 });

// Computed
const nodes = computed(() => {
  if (!props.mesh?.nodes) return [];
  return Object.values(props.mesh.nodes);
});

const isConnected = (nodeA, nodeB) => {
  return props.connections.some(c => 
    (c.source === nodeA && c.target === nodeB) ||
    (c.source === nodeB && c.target === nodeA)
  );
};

// Initialize node positions in a circular layout
const initializePositions = () => {
  if (!containerRef.value || nodes.value.length === 0) return;
  
  const rect = containerRef.value.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = 200;
  const radius = Math.min(rect.width, 400) * 0.35;
  
  nodes.value.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / nodes.value.length - Math.PI / 2;
    nodePositions.value[node.id] = {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  });
};

// Create full mesh (connect all nodes)
const createFullMesh = () => {
  const newConnections = [];
  const nodeList = nodes.value;
  
  for (let i = 0; i < nodeList.length; i++) {
    for (let j = i + 1; j < nodeList.length; j++) {
      newConnections.push({
        source: nodeList[i].id,
        target: nodeList[j].id
      });
    }
  }
  
  emit('update:connections', newConnections);
};

// Clear all connections
const clearConnections = () => {
  emit('update:connections', []);
};

// Toggle connection between two nodes
const toggleConnection = (nodeA, nodeB) => {
  const newConnections = [...props.connections];
  const existingIndex = newConnections.findIndex(c => 
    (c.source === nodeA && c.target === nodeB) ||
    (c.source === nodeB && c.target === nodeA)
  );
  
  if (existingIndex > -1) {
    newConnections.splice(existingIndex, 1);
  } else {
    newConnections.push({ source: nodeA, target: nodeB });
  }
  
  emit('update:connections', newConnections);
};

// Mouse event handlers for dragging
const handleMouseDown = (event, node) => {
  if (connectionMode.value) {
    connectionStart.value = node.id;
    tempConnectionEnd.value = { x: event.offsetX, y: event.offsetY };
    return;
  }
  
  isDragging.value = true;
  draggedNode.value = node.id;
  const pos = nodePositions.value[node.id];
  dragOffset.value = {
    x: event.offsetX - pos.x,
    y: event.offsetY - pos.y
  };
};

const handleMouseMove = (event) => {
  if (connectionMode.value && connectionStart.value) {
    tempConnectionEnd.value = { x: event.offsetX, y: event.offsetY };
    return;
  }
  
  if (!isDragging.value || !draggedNode.value) return;
  
  nodePositions.value[draggedNode.value] = {
    x: event.offsetX - dragOffset.value.x,
    y: event.offsetY - dragOffset.value.y
  };
};

const handleMouseUp = (event, targetNode = null) => {
  if (connectionMode.value && connectionStart.value) {
    if (targetNode && targetNode.id !== connectionStart.value) {
      toggleConnection(connectionStart.value, targetNode.id);
    }
    connectionStart.value = null;
  }
  
  isDragging.value = false;
  draggedNode.value = null;
};

const handleNodeClick = (node) => {
  if (connectionMode.value) return;
  
  const index = selectedNodes.value.indexOf(node.id);
  if (index > -1) {
    selectedNodes.value.splice(index, 1);
  } else {
    if (selectedNodes.value.length < 2) {
      selectedNodes.value.push(node.id);
    }
    
    if (selectedNodes.value.length === 2) {
      toggleConnection(selectedNodes.value[0], selectedNodes.value[1]);
      selectedNodes.value = [];
    }
  }
};

// Watch for mesh changes
watch(() => props.mesh, () => {
  initializePositions();
}, { deep: true });

// Lifecycle
onMounted(() => {
  initializePositions();
  window.addEventListener('resize', initializePositions);
});

onUnmounted(() => {
  window.removeEventListener('resize', initializePositions);
});
</script>

<template>
  <div class="card rounded-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-between flex-wrap gap-2">
      <div>
        <LocaleText t="Mesh Topology"></LocaleText>
        <span class="badge bg-secondary ms-2">{{ nodes.length }} nodes</span>
        <span class="badge bg-info ms-1">{{ connections.length }} connections</span>
      </div>
      <div class="d-flex gap-2 flex-wrap">
        <button 
          class="btn btn-sm"
          :class="connectionMode ? 'btn-primary' : 'btn-outline-primary'"
          @click="connectionMode = !connectionMode"
        >
          <i class="bi bi-link-45deg me-1"></i>
          {{ connectionMode ? 'Exit Connection Mode' : 'Connection Mode' }}
        </button>
        <button class="btn btn-sm btn-outline-success" @click="createFullMesh">
          <i class="bi bi-diagram-3 me-1"></i>
          <LocaleText t="Full Mesh"></LocaleText>
        </button>
        <button class="btn btn-sm btn-outline-danger" @click="clearConnections">
          <i class="bi bi-x-circle me-1"></i>
          <LocaleText t="Clear"></LocaleText>
        </button>
        <button class="btn btn-sm btn-outline-secondary" @click="$emit('upload')">
          <i class="bi bi-upload me-1"></i>
          <LocaleText t="Add External"></LocaleText>
        </button>
      </div>
    </div>
    
    <div class="card-body p-0">
      <!-- Instructions -->
      <div class="topology-instructions p-3 border-bottom">
        <div class="d-flex align-items-center gap-3 flex-wrap">
          <div class="instruction-item">
            <i class="bi bi-cursor-fill text-primary"></i>
            <span><LocaleText t="Drag nodes to reposition"></LocaleText></span>
          </div>
          <div class="instruction-item">
            <i class="bi bi-link-45deg text-success"></i>
            <span><LocaleText t="Click two nodes to toggle connection"></LocaleText></span>
          </div>
          <div class="instruction-item">
            <i class="bi bi-arrows-move text-info"></i>
            <span><LocaleText t="Use connection mode for drawing"></LocaleText></span>
          </div>
        </div>
      </div>
      
      <!-- Canvas -->
      <div 
        ref="containerRef"
        class="topology-canvas-container"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp()"
        @mouseleave="handleMouseUp()"
      >
        <svg class="topology-canvas" width="100%" height="400">
          <!-- Grid Pattern -->
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--bs-border-color)" stroke-width="0.5" opacity="0.3"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          
          <!-- Connections -->
          <g class="connections">
            <line
              v-for="(conn, index) in connections"
              :key="'conn-' + index"
              :x1="nodePositions[conn.source]?.x || 0"
              :y1="nodePositions[conn.source]?.y || 0"
              :x2="nodePositions[conn.target]?.x || 0"
              :y2="nodePositions[conn.target]?.y || 0"
              class="connection-line"
              @click="toggleConnection(conn.source, conn.target)"
            />
          </g>
          
          <!-- Temporary connection while drawing -->
          <line
            v-if="connectionMode && connectionStart"
            :x1="nodePositions[connectionStart]?.x || 0"
            :y1="nodePositions[connectionStart]?.y || 0"
            :x2="tempConnectionEnd.x"
            :y2="tempConnectionEnd.y"
            class="temp-connection-line"
          />
          
          <!-- Nodes -->
          <g 
            v-for="node in nodes" 
            :key="node.id"
            class="node-group"
            :class="{ 
              selected: selectedNodes.includes(node.id),
              external: node.is_external,
              hovered: hoveredNode === node.id
            }"
            :transform="`translate(${nodePositions[node.id]?.x || 0}, ${nodePositions[node.id]?.y || 0})`"
            @mousedown="handleMouseDown($event, node)"
            @mouseup="handleMouseUp($event, node)"
            @mouseenter="hoveredNode = node.id"
            @mouseleave="hoveredNode = null"
            @click="handleNodeClick(node)"
          >
            <!-- Node circle -->
            <circle 
              r="35" 
              class="node-circle"
              :class="{ awg: node.protocol === 'awg' }"
            />
            
            <!-- Connection count indicator -->
            <circle
              r="12"
              cx="25"
              cy="-25"
              class="connection-count-circle"
            />
            <text
              x="25"
              y="-21"
              class="connection-count-text"
            >{{ connections.filter(c => c.source === node.id || c.target === node.id).length }}</text>
            
            <!-- Node icon -->
            <text y="-5" class="node-icon">
              <tspan v-if="node.is_external">📁</tspan>
              <tspan v-else>🖥️</tspan>
            </text>
            
            <!-- Node name -->
            <text y="50" class="node-name">{{ node.name }}</text>
            
            <!-- Node address -->
            <text y="65" class="node-address">{{ node.address || 'No IP' }}</text>
          </g>
        </svg>
      </div>
    </div>
    
    <!-- Connection Matrix -->
    <div class="card-footer" v-if="nodes.length > 0">
      <details class="connection-matrix">
        <summary class="mb-2 cursor-pointer">
          <i class="bi bi-grid-3x3 me-2"></i>
          <LocaleText t="Connection Matrix"></LocaleText>
        </summary>
        <div class="table-responsive">
          <table class="table table-sm table-bordered mb-0">
            <thead>
              <tr>
                <th></th>
                <th v-for="node in nodes" :key="'h-' + node.id" class="text-center">
                  {{ node.name.substring(0, 6) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="nodeA in nodes" :key="'r-' + nodeA.id">
                <th>{{ nodeA.name.substring(0, 6) }}</th>
                <td 
                  v-for="nodeB in nodes" 
                  :key="'c-' + nodeB.id"
                  class="text-center matrix-cell"
                  :class="{ 
                    connected: isConnected(nodeA.id, nodeB.id),
                    disabled: nodeA.id === nodeB.id
                  }"
                  @click="nodeA.id !== nodeB.id && toggleConnection(nodeA.id, nodeB.id)"
                >
                  <i v-if="nodeA.id === nodeB.id" class="bi bi-dash text-muted"></i>
                  <i v-else-if="isConnected(nodeA.id, nodeB.id)" class="bi bi-check-lg text-success"></i>
                  <i v-else class="bi bi-x text-muted"></i>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </div>
  </div>
</template>

<style scoped>
.topology-canvas-container {
  position: relative;
  min-height: 400px;
  background: var(--bs-body-bg);
  cursor: crosshair;
}

.topology-canvas {
  display: block;
}

.topology-instructions {
  background: var(--bs-secondary-bg);
}

.instruction-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--bs-secondary-color);
}

.instruction-item i {
  font-size: 1rem;
}

.connection-line {
  stroke: var(--bs-primary);
  stroke-width: 3;
  stroke-linecap: round;
  cursor: pointer;
  transition: stroke-width 0.2s ease;
}

.connection-line:hover {
  stroke-width: 5;
  stroke: var(--bs-danger);
}

.temp-connection-line {
  stroke: var(--bs-primary);
  stroke-width: 2;
  stroke-dasharray: 8, 4;
  opacity: 0.6;
}

.node-group {
  cursor: grab;
  transition: transform 0.1s ease;
}

.node-group:active {
  cursor: grabbing;
}

.node-circle {
  fill: var(--bs-body-bg);
  stroke: var(--bs-primary);
  stroke-width: 3;
  transition: all 0.2s ease;
}

.node-circle.awg {
  stroke: #7b1fa2;
}

.node-group.selected .node-circle {
  stroke-width: 5;
  filter: drop-shadow(0 0 8px var(--bs-primary));
}

.node-group.hovered .node-circle {
  stroke-width: 4;
}

.node-group.external .node-circle {
  stroke-dasharray: 8, 4;
}

.connection-count-circle {
  fill: var(--bs-secondary);
}

.connection-count-text {
  fill: white;
  font-size: 12px;
  font-weight: bold;
  text-anchor: middle;
  dominant-baseline: middle;
}

.node-icon {
  font-size: 24px;
  text-anchor: middle;
  dominant-baseline: middle;
}

.node-name {
  font-size: 12px;
  font-weight: 600;
  text-anchor: middle;
  fill: var(--bs-body-color);
}

.node-address {
  font-size: 10px;
  text-anchor: middle;
  fill: var(--bs-secondary-color);
}

.connection-matrix summary {
  font-weight: 500;
}

.matrix-cell {
  cursor: pointer;
  transition: background-color 0.2s ease;
  width: 40px;
  height: 40px;
}

.matrix-cell:hover:not(.disabled) {
  background-color: var(--bs-primary-bg-subtle);
}

.matrix-cell.connected {
  background-color: var(--bs-success-bg-subtle);
}

.matrix-cell.disabled {
  background-color: var(--bs-secondary-bg);
  cursor: not-allowed;
}

.cursor-pointer {
  cursor: pointer;
}
</style>

