<script setup>
import { ref } from 'vue';
import { fetchPost, getUrl } from '@/utilities/fetch.js';
import { DashboardConfigurationStore } from '@/stores/DashboardConfigurationStore.js';
import LocaleText from '@/components/text/localeText.vue';

const props = defineProps({
  meshId: {
    type: String,
    default: null
  }
});

const emit = defineEmits(['close', 'upload-complete']);

const dashboardStore = DashboardConfigurationStore();

const selectedFile = ref(null);
const isUploading = ref(false);
const isDragging = ref(false);
const parsedConfig = ref(null);
const uploadError = ref('');

const handleFileSelect = (event) => {
  const file = event.target.files[0];
  if (file) {
    validateAndPreview(file);
  }
};

const handleDrop = (event) => {
  event.preventDefault();
  isDragging.value = false;
  
  const file = event.dataTransfer.files[0];
  if (file) {
    validateAndPreview(file);
  }
};

const handleDragOver = (event) => {
  event.preventDefault();
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const validateAndPreview = async (file) => {
  uploadError.value = '';
  parsedConfig.value = null;
  
  if (!file.name.endsWith('.conf')) {
    uploadError.value = 'Only .conf files are allowed';
    return;
  }
  
  selectedFile.value = file;
  
  // Preview the file content
  try {
    const content = await file.text();
    const preview = parseConfigPreview(content);
    parsedConfig.value = preview;
  } catch (error) {
    uploadError.value = 'Failed to read file';
  }
};

const parseConfigPreview = (content) => {
  const lines = content.split('\n');
  const data = {
    protocol: 'wg',
    address: '',
    listenPort: '',
    hasPrivateKey: false,
    hasPublicKey: false,
    peerCount: 0,
    isAmneziaWG: false
  };
  
  const amneziaParams = ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4', 'I1', 'I2', 'I3', 'I4', 'I5'];
  let inInterface = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    
    if (trimmed === '[Interface]') {
      inInterface = true;
      continue;
    }
    if (trimmed === '[Peer]') {
      inInterface = false;
      data.peerCount++;
      continue;
    }
    
    if (inInterface && trimmed.includes('=')) {
      const [key, value] = trimmed.split('=').map(s => s.trim());
      
      if (key === 'Address') data.address = value;
      if (key === 'ListenPort') data.listenPort = value;
      if (key === 'PrivateKey') data.hasPrivateKey = true;
      if (key === 'PublicKey') data.hasPublicKey = true;
      
      if (amneziaParams.includes(key)) {
        data.isAmneziaWG = true;
        data.protocol = 'awg';
      }
    }
  }
  
  return data;
};

const uploadConfig = async () => {
  if (!selectedFile.value) return;
  
  isUploading.value = true;
  uploadError.value = '';
  
  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    
    const endpoint = props.meshId 
      ? `/api/mesh/${props.meshId}/upload`
      : '/api/mesh/upload';
    
    const response = await fetch(getUrl(endpoint), {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });
    
    const result = await response.json();
    
    if (result.status) {
      dashboardStore.newMessage('WireGate', result.message || 'Config uploaded successfully', 'success');
      emit('upload-complete', result.data);
    } else {
      uploadError.value = result.message || 'Upload failed';
    }
  } catch (error) {
    uploadError.value = 'Network error during upload';
    console.error('Upload error:', error);
  } finally {
    isUploading.value = false;
  }
};

const clearSelection = () => {
  selectedFile.value = null;
  parsedConfig.value = null;
  uploadError.value = '';
};
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop fade show" @click="$emit('close')"></div>
    <div class="modal fade show d-block" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content rounded-4 shadow">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title d-flex align-items-center gap-2">
              <i class="bi bi-upload text-primary"></i>
              <LocaleText t="Upload External Configuration"></LocaleText>
            </h5>
            <button type="button" class="btn-close" @click="$emit('close')"></button>
          </div>
          
          <div class="modal-body">
            <!-- Upload Zone -->
            <div 
              class="upload-zone"
              :class="{ 'drag-over': isDragging, 'has-file': selectedFile }"
              @drop="handleDrop"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
            >
              <div v-if="!selectedFile" class="upload-prompt">
                <i class="bi bi-cloud-arrow-up"></i>
                <p class="mb-2">
                  <LocaleText t="Drag and drop your WireGuard config here"></LocaleText>
                </p>
                <p class="text-muted small mb-3">
                  <LocaleText t="Supports .conf files (WireGuard and AmneziaWG)"></LocaleText>
                </p>
                <label class="btn btn-primary">
                  <i class="bi bi-folder2-open me-2"></i>
                  <LocaleText t="Browse Files"></LocaleText>
                  <input 
                    type="file" 
                    class="d-none" 
                    accept=".conf"
                    @change="handleFileSelect"
                  />
                </label>
              </div>
              
              <div v-else class="file-preview">
                <div class="d-flex align-items-center gap-3">
                  <div class="file-icon">
                    <i class="bi bi-file-earmark-code"></i>
                  </div>
                  <div class="file-info flex-grow-1">
                    <h6 class="mb-0">{{ selectedFile.name }}</h6>
                    <small class="text-muted">
                      {{ (selectedFile.size / 1024).toFixed(1) }} KB
                    </small>
                  </div>
                  <button class="btn btn-outline-danger btn-sm" @click="clearSelection">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Error Message -->
            <div v-if="uploadError" class="alert alert-danger mt-3 d-flex align-items-center">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              {{ uploadError }}
            </div>
            
            <!-- Parsed Config Preview -->
            <div v-if="parsedConfig" class="config-preview mt-4">
              <h6 class="d-flex align-items-center gap-2 mb-3">
                <i class="bi bi-eye"></i>
                <LocaleText t="Configuration Preview"></LocaleText>
              </h6>
              
              <div class="preview-grid">
                <div class="preview-item">
                  <span class="preview-label"><LocaleText t="Protocol"></LocaleText></span>
                  <span class="preview-value">
                    <span 
                      class="badge"
                      :class="parsedConfig.isAmneziaWG ? 'bg-purple' : 'bg-success'"
                    >
                      {{ parsedConfig.isAmneziaWG ? 'AmneziaWG' : 'WireGuard' }}
                    </span>
                  </span>
                </div>
                
                <div class="preview-item">
                  <span class="preview-label"><LocaleText t="Address"></LocaleText></span>
                  <span class="preview-value">
                    <code>{{ parsedConfig.address || 'Not specified' }}</code>
                  </span>
                </div>
                
                <div class="preview-item">
                  <span class="preview-label"><LocaleText t="Listen Port"></LocaleText></span>
                  <span class="preview-value">
                    {{ parsedConfig.listenPort || 'Not specified' }}
                  </span>
                </div>
                
                <div class="preview-item">
                  <span class="preview-label"><LocaleText t="Private Key"></LocaleText></span>
                  <span class="preview-value">
                    <i 
                      class="bi"
                      :class="parsedConfig.hasPrivateKey ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'"
                    ></i>
                    {{ parsedConfig.hasPrivateKey ? 'Present' : 'Missing' }}
                  </span>
                </div>
                
                <div class="preview-item">
                  <span class="preview-label"><LocaleText t="Existing Peers"></LocaleText></span>
                  <span class="preview-value">
                    {{ parsedConfig.peerCount }}
                  </span>
                </div>
              </div>
              
              <!-- Validation Messages -->
              <div v-if="!parsedConfig.hasPrivateKey" class="alert alert-warning mt-3 mb-0">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <LocaleText t="Configuration is missing a private key. A public key must be available for mesh connections."></LocaleText>
              </div>
            </div>
          </div>
          
          <div class="modal-footer border-0 pt-0">
            <button type="button" class="btn btn-outline-secondary" @click="$emit('close')">
              <LocaleText t="Cancel"></LocaleText>
            </button>
            <button 
              type="button" 
              class="btn btn-primary"
              :disabled="!selectedFile || isUploading || !!uploadError"
              @click="uploadConfig"
            >
              <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
              <i v-else class="bi bi-upload me-2"></i>
              <LocaleText t="Upload & Add to Mesh"></LocaleText>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal {
  background-color: rgba(0, 0, 0, 0.5);
}

.upload-zone {
  border: 2px dashed var(--bs-border-color);
  border-radius: 1rem;
  padding: 3rem 2rem;
  text-align: center;
  transition: all 0.3s ease;
  background: var(--bs-secondary-bg);
}

.upload-zone.drag-over {
  border-color: var(--bs-primary);
  background: var(--bs-primary-bg-subtle);
}

.upload-zone.has-file {
  border-style: solid;
  padding: 1.5rem;
  text-align: left;
}

.upload-prompt i {
  font-size: 3rem;
  color: var(--bs-secondary-color);
  margin-bottom: 1rem;
}

.file-icon {
  width: 48px;
  height: 48px;
  border-radius: 0.5rem;
  background: var(--bs-primary-bg-subtle);
  color: var(--bs-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.config-preview {
  background: var(--bs-secondary-bg);
  border-radius: 0.75rem;
  padding: 1.25rem;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.preview-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--bs-secondary-color);
}

.preview-value {
  font-weight: 500;
}

.bg-purple {
  background-color: #7b1fa2 !important;
}
</style>

