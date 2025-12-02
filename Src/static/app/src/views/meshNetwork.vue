<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { fetchGet, fetchPost } from '@/utilities/fetch.js';
import { DashboardConfigurationStore } from '@/stores/DashboardConfigurationStore.js';
import LocaleText from '@/components/text/localeText.vue';
import MeshConfigSelector from '@/components/meshComponents/meshConfigSelector.vue';
import MeshTopologyBuilder from '@/components/meshComponents/meshTopologyBuilder.vue';
import MeshPreview from '@/components/meshComponents/meshPreview.vue';
import MeshUploadModal from '@/components/meshComponents/meshUploadModal.vue';
import MeshNetworkVisualizer from '@/components/meshComponents/meshNetworkVisualizer.vue';

const dashboardStore = DashboardConfigurationStore();

// State
const currentStep = ref(1);
const meshName = ref('');
const selectedConfigs = ref([]);
const availableConfigs = ref([]);
const currentMesh = ref(null);
const meshConnections = ref([]);
const meshPreview = ref(null);
const showUploadModal = ref(false);
const applyMode = ref('preview'); // 'preview' or 'modify'
const isLoading = ref(false);
const isCreatingMesh = ref(false);
const isApplying = ref(false);
const generatePresharedKeys = ref(true);

// Computed
const canProceedStep1 = computed(() => {
  return selectedConfigs.value.length >= 2 && meshName.value.trim().length > 0;
});

const canProceedStep2 = computed(() => {
  return currentMesh.value && meshConnections.value.length > 0;
});

const canApply = computed(() => {
  return meshPreview.value && meshPreview.value.peer_entries?.length > 0;
});

// Methods
const loadConfigurations = async () => {
  isLoading.value = true;
  try {
    await fetchGet('/api/mesh/configurations', {}, (res) => {
      console.log('Mesh configurations response:', res);
      if (res.status) {
        availableConfigs.value = res.data;
      } else {
        dashboardStore.newMessage('WireGate', res.message || 'Failed to load configurations', 'danger');
      }
    });
  } catch (error) {
    console.error('Error loading configurations:', error);
    dashboardStore.newMessage('WireGate', 'Error loading configurations', 'danger');
  } finally {
    isLoading.value = false;
  }
};

const createMesh = async () => {
  console.log('createMesh called', {
    canProceedStep1: canProceedStep1.value,
    selectedConfigs: selectedConfigs.value,
    meshName: meshName.value
  });
  
  if (!canProceedStep1.value) {
    console.log('Cannot proceed - validation failed');
    return;
  }
  
  isCreatingMesh.value = true;
  try {
    console.log('Creating mesh with:', {
      configurations: selectedConfigs.value,
      name: meshName.value
    });
    
    await fetchPost('/api/mesh/create', {
      configurations: selectedConfigs.value,
      name: meshName.value
    }, (res) => {
      console.log('Create mesh response:', res);
      if (res.status) {
        currentMesh.value = res.data;
        meshConnections.value = [];
        currentStep.value = 2;
        dashboardStore.newMessage('WireGate', `Mesh "${meshName.value}" created`, 'success');
      } else {
        dashboardStore.newMessage('WireGate', res.message || 'Failed to create mesh', 'danger');
      }
    });
  } catch (error) {
    console.error('Error creating mesh:', error);
    dashboardStore.newMessage('WireGate', 'Error creating mesh', 'danger');
  } finally {
    isCreatingMesh.value = false;
  }
};

const updateConnections = async (connections) => {
  meshConnections.value = connections;
  
  if (!currentMesh.value) return;
  
  try {
    await fetchPost(`/api/mesh/${currentMesh.value.id}/connections/bulk`, {
      connections: connections.map(c => ({
        node_a_id: c.source,
        node_b_id: c.target
      })),
      generate_preshared_keys: generatePresharedKeys.value
    }, (res) => {
      if (res.status) {
        currentMesh.value = res.data;
      }
    });
  } catch (error) {
    console.error('Error updating connections:', error);
  }
};

const loadPreview = async () => {
  if (!currentMesh.value) return;
  
  isLoading.value = true;
  try {
    await fetchGet(`/api/mesh/${currentMesh.value.id}/preview`, {}, (res) => {
      if (res.status) {
        meshPreview.value = res.data;
        currentStep.value = 3;
      } else {
        dashboardStore.newMessage('WireGate', res.message || 'Failed to load preview', 'danger');
      }
    });
  } catch (error) {
    dashboardStore.newMessage('WireGate', 'Error loading preview', 'danger');
  } finally {
    isLoading.value = false;
  }
};

const applyMesh = async () => {
  if (!currentMesh.value || !canApply.value) return;
  
  isApplying.value = true;
  try {
    await fetchPost(`/api/mesh/${currentMesh.value.id}/apply`, {
      create_new: applyMode.value === 'create'
    }, (res) => {
      if (res.status) {
        dashboardStore.newMessage('WireGate', res.message || 'Mesh applied successfully', 'success');
        // Reset to initial state
        resetMesh();
      } else {
        dashboardStore.newMessage('WireGate', res.message || 'Failed to apply mesh', 'danger');
      }
    });
  } catch (error) {
    dashboardStore.newMessage('WireGate', 'Error applying mesh', 'danger');
  } finally {
    isApplying.value = false;
  }
};

const handleUploadComplete = async (node) => {
  if (!currentMesh.value) return;
  
  // Add external node to mesh
  currentMesh.value.nodes[node.id] = node;
  showUploadModal.value = false;
  dashboardStore.newMessage('WireGate', `Added external config: ${node.name}`, 'success');
};

const handleNodeClick = (node) => {
  console.log('Node clicked:', node);
};

const handleEdgeClick = (edge) => {
  console.log('Edge clicked:', edge);
};

const goToStep = (step) => {
  if (step < currentStep.value) {
    currentStep.value = step;
  } else if (step === 2 && canProceedStep1.value && currentMesh.value) {
    currentStep.value = 2;
  } else if (step === 3 && canProceedStep2.value) {
    loadPreview();
  }
};

const resetMesh = () => {
  currentStep.value = 1;
  meshName.value = '';
  selectedConfigs.value = [];
  currentMesh.value = null;
  meshConnections.value = [];
  meshPreview.value = null;
  applyMode.value = 'preview';
};

// Lifecycle
onMounted(() => {
  loadConfigurations();
});
</script>

<template>
  <div class="mt-md-5 mt-3 text-body">
    <div class="container-fluid px-lg-4">
      <!-- Header -->
      <div class="mb-4 d-flex align-items-center gap-4">
        <RouterLink to="/" class="btn btn-dark btn-brand p-2 shadow" style="border-radius: 100%">
          <h2 class="mb-0" style="line-height: 0">
            <i class="bi bi-arrow-left-circle"></i>
          </h2>
        </RouterLink>
        <div>
          <h2 class="mb-0">
            <LocaleText t="Mesh Network Builder"></LocaleText>
          </h2>
          <small class="text-muted">
            <LocaleText t="Combine configurations into mesh networks"></LocaleText>
          </small>
        </div>
      </div>

      <!-- Progress Steps -->
      <div class="card rounded-3 shadow mb-4">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center mesh-steps">
            <!-- Step 1 -->
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 1, current: currentStep === 1 }"
              @click="goToStep(1)"
              role="button"
            >
              <div class="step-circle">
                <i v-if="currentStep > 1" class="bi bi-check-lg"></i>
                <span v-else>1</span>
              </div>
              <div class="step-label">
                <LocaleText t="Select Configurations"></LocaleText>
              </div>
            </div>
            
            <div class="step-line" :class="{ active: currentStep > 1 }"></div>
            
            <!-- Step 2 -->
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 2, current: currentStep === 2 }"
              @click="goToStep(2)"
              role="button"
            >
              <div class="step-circle">
                <i v-if="currentStep > 2" class="bi bi-check-lg"></i>
                <span v-else>2</span>
              </div>
              <div class="step-label">
                <LocaleText t="Build Topology"></LocaleText>
              </div>
            </div>
            
            <div class="step-line" :class="{ active: currentStep > 2 }"></div>
            
            <!-- Step 3 -->
            <div 
              class="step-item" 
              :class="{ active: currentStep >= 3, current: currentStep === 3 }"
              @click="goToStep(3)"
              role="button"
            >
              <div class="step-circle">
                <span>3</span>
              </div>
              <div class="step-label">
                <LocaleText t="Preview & Apply"></LocaleText>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 1: Select Configurations -->
      <Transition name="fade" mode="out-in">
        <div v-if="currentStep === 1" key="step1">
          <div class="row g-4">
            <!-- Mesh Name -->
            <div class="col-12">
              <div class="card rounded-3 shadow">
                <div class="card-header">
                  <LocaleText t="Mesh Network Name"></LocaleText>
                </div>
                <div class="card-body">
                  <input 
                    type="text" 
                    class="form-control" 
                    v-model="meshName"
                    placeholder="Enter mesh network name..."
                    :disabled="isLoading"
                  />
                </div>
              </div>
            </div>
            
            <!-- Configuration Selector -->
            <div class="col-12">
              <MeshConfigSelector
                :configurations="availableConfigs"
                :selected="selectedConfigs"
                :loading="isLoading"
                @update:selected="selectedConfigs = $event"
              />
            </div>
            
            <!-- Validation Status -->
            <div class="col-12" v-if="!canProceedStep1">
              <div class="alert alert-warning d-flex align-items-center mb-0">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <div>
                  <span v-if="meshName.trim().length === 0">
                    <LocaleText t="Please enter a mesh network name"></LocaleText>
                  </span>
                  <span v-else-if="selectedConfigs.length < 2">
                    <LocaleText t="Please select at least 2 configurations to create a mesh"></LocaleText>
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="col-12 d-flex justify-content-end gap-2">
              <button 
                class="btn btn-dark btn-brand rounded-3 px-4 py-2"
                :disabled="!canProceedStep1 || isCreatingMesh"
                @click="createMesh"
              >
                <span v-if="isCreatingMesh" class="spinner-border spinner-border-sm me-2"></span>
                <i v-else class="bi bi-arrow-right-circle me-2"></i>
                <LocaleText t="Create Mesh & Continue"></LocaleText>
              </button>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Step 2: Build Topology -->
      <Transition name="fade" mode="out-in">
        <div v-if="currentStep === 2" key="step2">
          <div class="row g-4">
            <!-- Network Visualizer -->
            <div class="col-12">
              <MeshNetworkVisualizer
                :mesh="currentMesh"
                :connections="meshConnections"
                :interactive="true"
                height="500px"
                @node-click="handleNodeClick"
                @edge-click="handleEdgeClick"
              />
            </div>
            
            <!-- Topology Builder -->
            <div class="col-12">
              <MeshTopologyBuilder
                :mesh="currentMesh"
                :connections="meshConnections"
                @update:connections="updateConnections"
                @upload="showUploadModal = true"
              />
            </div>
            
            <!-- Options -->
            <div class="col-12">
              <div class="card rounded-3 shadow">
                <div class="card-header">
                  <LocaleText t="Connection Options"></LocaleText>
                </div>
                <div class="card-body">
                  <div class="form-check form-switch">
                    <input 
                      class="form-check-input" 
                      type="checkbox" 
                      id="generatePSK"
                      v-model="generatePresharedKeys"
                    />
                    <label class="form-check-label" for="generatePSK">
                      <LocaleText t="Generate preshared keys for each connection"></LocaleText>
                    </label>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="col-12 d-flex justify-content-between">
              <button 
                class="btn btn-outline-secondary rounded-3 px-4 py-2"
                @click="currentStep = 1"
              >
                <i class="bi bi-arrow-left me-2"></i>
                <LocaleText t="Back"></LocaleText>
              </button>
              <button 
                class="btn btn-dark btn-brand rounded-3 px-4 py-2"
                :disabled="!canProceedStep2 || isLoading"
                @click="loadPreview"
              >
                <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
                <i v-else class="bi bi-eye me-2"></i>
                <LocaleText t="Preview Changes"></LocaleText>
              </button>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Step 3: Preview & Apply -->
      <Transition name="fade" mode="out-in">
        <div v-if="currentStep === 3" key="step3">
          <div class="row g-4">
            <!-- Preview -->
            <div class="col-12">
              <MeshPreview :preview="meshPreview" />
            </div>
            
            <!-- Apply Mode -->
            <div class="col-12">
              <div class="card rounded-3 shadow">
                <div class="card-header">
                  <LocaleText t="Apply Mode"></LocaleText>
                </div>
                <div class="card-body">
                  <div class="d-flex gap-3">
                    <div class="form-check">
                      <input 
                        class="form-check-input" 
                        type="radio" 
                        name="applyMode" 
                        id="modeModify"
                        value="modify"
                        v-model="applyMode"
                      />
                      <label class="form-check-label" for="modeModify">
                        <strong><LocaleText t="Modify Existing"></LocaleText></strong>
                        <br/>
                        <small class="text-muted">
                          <LocaleText t="Add peer entries directly to existing configurations"></LocaleText>
                        </small>
                      </label>
                    </div>
                    <div class="form-check">
                      <input 
                        class="form-check-input" 
                        type="radio" 
                        name="applyMode" 
                        id="modeCreate"
                        value="create"
                        v-model="applyMode"
                      />
                      <label class="form-check-label" for="modeCreate">
                        <strong><LocaleText t="Create New"></LocaleText></strong>
                        <br/>
                        <small class="text-muted">
                          <LocaleText t="Create new configurations with mesh settings"></LocaleText>
                        </small>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="col-12 d-flex justify-content-between">
              <button 
                class="btn btn-outline-secondary rounded-3 px-4 py-2"
                @click="currentStep = 2"
              >
                <i class="bi bi-arrow-left me-2"></i>
                <LocaleText t="Back"></LocaleText>
              </button>
              <div class="d-flex gap-2">
                <button 
                  class="btn btn-outline-danger rounded-3 px-4 py-2"
                  @click="resetMesh"
                >
                  <i class="bi bi-x-circle me-2"></i>
                  <LocaleText t="Cancel"></LocaleText>
                </button>
                <button 
                  class="btn btn-success rounded-3 px-4 py-2"
                  :disabled="!canApply || isApplying"
                  @click="applyMesh"
                >
                  <span v-if="isApplying" class="spinner-border spinner-border-sm me-2"></span>
                  <i v-else class="bi bi-check-circle me-2"></i>
                  <LocaleText t="Apply Mesh"></LocaleText>
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Upload Modal -->
      <MeshUploadModal
        v-if="showUploadModal"
        :mesh-id="currentMesh?.id"
        @close="showUploadModal = false"
        @upload-complete="handleUploadComplete"
      />
    </div>
  </div>
</template>

<style scoped>
.mesh-steps {
  padding: 1rem 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}

.step-item.active {
  opacity: 1;
}

.step-item.current .step-circle {
  background-color: var(--bs-primary);
  color: white;
  box-shadow: 0 0 0 4px rgba(var(--bs-primary-rgb), 0.25);
}

.step-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: var(--bs-secondary-bg);
  border: 2px solid var(--bs-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 1.1rem;
  transition: all 0.3s ease;
}

.step-item.active .step-circle {
  border-color: var(--bs-primary);
  background-color: var(--bs-primary-bg-subtle);
}

.step-label {
  font-size: 0.85rem;
  font-weight: 500;
  text-align: center;
}

.step-line {
  flex: 1;
  height: 2px;
  background-color: var(--bs-border-color);
  margin: 0 1rem;
  margin-bottom: 2rem;
  transition: background-color 0.3s ease;
}

.step-line.active {
  background-color: var(--bs-primary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

@media (max-width: 768px) {
  .step-label {
    font-size: 0.75rem;
  }
  
  .step-circle {
    width: 36px;
    height: 36px;
    font-size: 0.9rem;
  }
  
  .step-line {
    margin: 0 0.5rem;
  }
}
</style>

