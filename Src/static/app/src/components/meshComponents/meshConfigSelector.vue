<script setup>
import { computed } from 'vue';
import LocaleText from '@/components/text/localeText.vue';
import ProtocolBadge from '@/components/protocolBadge.vue';

const props = defineProps({
  configurations: {
    type: Array,
    default: () => []
  },
  selected: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:selected']);

const isSelected = (configName) => {
  return props.selected.includes(configName);
};

const toggleSelection = (configName) => {
  const newSelected = [...props.selected];
  const index = newSelected.indexOf(configName);
  
  if (index > -1) {
    newSelected.splice(index, 1);
  } else {
    newSelected.push(configName);
  }
  
  emit('update:selected', newSelected);
};

const selectAll = () => {
  emit('update:selected', props.configurations.map(c => c.name));
};

const deselectAll = () => {
  emit('update:selected', []);
};

const sortedConfigurations = computed(() => {
  return [...props.configurations].sort((a, b) => a.name.localeCompare(b.name));
});
</script>

<template>
  <div class="card rounded-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-between">
      <div>
        <LocaleText t="Select Configurations"></LocaleText>
        <span class="badge bg-primary ms-2">{{ selected.length }} selected</span>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-primary" @click="selectAll" :disabled="loading">
          <i class="bi bi-check-all me-1"></i>
          <LocaleText t="Select All"></LocaleText>
        </button>
        <button class="btn btn-sm btn-outline-secondary" @click="deselectAll" :disabled="loading">
          <i class="bi bi-x-lg me-1"></i>
          <LocaleText t="Clear"></LocaleText>
        </button>
      </div>
    </div>
    <div class="card-body">
      <!-- Loading State -->
      <div v-if="loading" class="text-center py-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2 text-muted mb-0">
          <LocaleText t="Loading configurations..."></LocaleText>
        </p>
      </div>
      
      <!-- Empty State -->
      <div v-else-if="configurations.length === 0" class="text-center py-4">
        <i class="bi bi-inbox fs-1 text-muted"></i>
        <p class="mt-2 text-muted mb-0">
          <LocaleText t="No configurations available"></LocaleText>
        </p>
      </div>
      
      <!-- Configuration List -->
      <div v-else class="config-grid">
        <div 
          v-for="config in sortedConfigurations" 
          :key="config.name"
          class="config-card"
          :class="{ selected: isSelected(config.name) }"
          @click="toggleSelection(config.name)"
        >
          <div class="config-card-inner">
            <div class="d-flex align-items-start justify-content-between">
              <div class="d-flex align-items-center gap-2">
                <div class="form-check mb-0">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    :checked="isSelected(config.name)"
                    @click.stop
                    @change="toggleSelection(config.name)"
                  />
                </div>
                <div>
                  <h6 class="mb-0 config-name">{{ config.name }}</h6>
                  <small class="text-muted">{{ config.address }}</small>
                </div>
              </div>
              <ProtocolBadge :protocol="config.protocol" :mini="true" />
            </div>
            
            <div class="config-details mt-3">
              <div class="detail-item">
                <i class="bi bi-diagram-3"></i>
                <span>{{ config.peer_count || 0 }} peers</span>
              </div>
              <div class="detail-item">
                <i class="bi bi-broadcast"></i>
                <span>Port {{ config.listen_port || 'N/A' }}</span>
              </div>
              <div class="detail-item">
                <span 
                  class="status-dot" 
                  :class="{ active: config.status }"
                ></span>
                <span>{{ config.status ? 'Active' : 'Inactive' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Minimum Selection Warning -->
      <div v-if="selected.length === 1" class="alert alert-info mt-3 mb-0 d-flex align-items-center">
        <i class="bi bi-info-circle me-2"></i>
        <LocaleText t="Select at least 2 configurations to create a mesh network"></LocaleText>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.config-card {
  border: 2px solid var(--bs-border-color);
  border-radius: 0.75rem;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--bs-body-bg);
}

.config-card:hover {
  border-color: var(--bs-primary);
  background: var(--bs-primary-bg-subtle);
}

.config-card.selected {
  border-color: var(--bs-primary);
  background: var(--bs-primary-bg-subtle);
  box-shadow: 0 0 0 3px rgba(var(--bs-primary-rgb), 0.15);
}

.config-card-inner {
  display: flex;
  flex-direction: column;
}

.config-name {
  font-weight: 600;
  color: var(--bs-body-color);
}

.config-details {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: var(--bs-secondary-color);
}

.detail-item i {
  font-size: 0.9rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--bs-secondary);
}

.status-dot.active {
  background-color: var(--bs-success);
  box-shadow: 0 0 6px var(--bs-success);
}

@media (max-width: 576px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>

