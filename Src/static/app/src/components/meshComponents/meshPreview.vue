<script setup>
import { computed } from 'vue';
import LocaleText from '@/components/text/localeText.vue';
import MeshNetworkVisualizer from '@/components/meshComponents/meshNetworkVisualizer.vue';

const props = defineProps({
  preview: {
    type: Object,
    default: null
  }
});

const hasWarnings = computed(() => {
  return props.preview?.warnings?.length > 0;
});

const groupedPeerEntries = computed(() => {
  if (!props.preview?.peer_entries) return {};
  
  const grouped = {};
  props.preview.peer_entries.forEach(entry => {
    if (!grouped[entry.config]) {
      grouped[entry.config] = [];
    }
    grouped[entry.config].push(entry);
  });
  
  return grouped;
});

const totalPeerEntries = computed(() => {
  return props.preview?.peer_entries?.length || 0;
});

const configCount = computed(() => {
  return Object.keys(groupedPeerEntries.value).length;
});
</script>

<template>
  <div class="preview-container">
    <!-- Summary Card -->
    <div class="card rounded-3 shadow mb-4">
      <div class="card-header">
        <i class="bi bi-clipboard-data me-2"></i>
        <LocaleText t="Mesh Preview Summary"></LocaleText>
      </div>
      <div class="card-body">
        <div class="row g-4">
          <div class="col-sm-4">
            <div class="summary-stat">
              <div class="stat-icon bg-primary-subtle text-primary">
                <i class="bi bi-hdd-network"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ preview?.nodes?.length || 0 }}</div>
                <div class="stat-label"><LocaleText t="Nodes"></LocaleText></div>
              </div>
            </div>
          </div>
          <div class="col-sm-4">
            <div class="summary-stat">
              <div class="stat-icon bg-success-subtle text-success">
                <i class="bi bi-link-45deg"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ preview?.connections?.length || 0 }}</div>
                <div class="stat-label"><LocaleText t="Connections"></LocaleText></div>
              </div>
            </div>
          </div>
          <div class="col-sm-4">
            <div class="summary-stat">
              <div class="stat-icon bg-info-subtle text-info">
                <i class="bi bi-person-plus"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ totalPeerEntries }}</div>
                <div class="stat-label"><LocaleText t="Peer Entries"></LocaleText></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Warnings -->
    <div v-if="hasWarnings" class="card rounded-3 shadow mb-4 border-warning">
      <div class="card-header bg-warning-subtle text-warning-emphasis">
        <i class="bi bi-exclamation-triangle me-2"></i>
        <LocaleText t="Warnings"></LocaleText>
        <span class="badge bg-warning text-dark ms-2">{{ preview.warnings.length }}</span>
      </div>
      <div class="card-body">
        <div 
          v-for="(warning, index) in preview.warnings" 
          :key="index"
          class="warning-item"
        >
          <div v-if="warning.type === 'ip_collision'" class="d-flex align-items-start gap-2">
            <i class="bi bi-hdd-network text-warning mt-1"></i>
            <div>
              <strong>IP Collision Detected</strong>
              <p class="mb-0 text-muted small">
                {{ warning.details.node_a || warning.details.node }} 
                <template v-if="warning.details.node_b">
                  and {{ warning.details.node_b }}
                </template>
                - {{ warning.details.address_a || warning.details.address }}
                <template v-if="warning.details.address_b">
                  / {{ warning.details.address_b }}
                </template>
              </p>
            </div>
          </div>
          <div v-else class="d-flex align-items-start gap-2">
            <i class="bi bi-info-circle text-warning mt-1"></i>
            <span>{{ warning.details || JSON.stringify(warning) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Peer Entries by Configuration -->
    <div class="card rounded-3 shadow">
      <div class="card-header d-flex align-items-center justify-content-between">
        <div>
          <i class="bi bi-diagram-3 me-2"></i>
          <LocaleText t="Peer Entries to Add"></LocaleText>
        </div>
        <span class="badge bg-secondary">{{ configCount }} configurations</span>
      </div>
      <div class="card-body p-0">
        <div class="accordion" id="peerEntriesAccordion">
          <div 
            v-for="(entries, configName, index) in groupedPeerEntries" 
            :key="configName"
            class="accordion-item"
          >
            <h2 class="accordion-header">
              <button 
                class="accordion-button"
                :class="{ collapsed: index !== 0 }"
                type="button" 
                data-bs-toggle="collapse" 
                :data-bs-target="'#config-' + index"
              >
                <div class="d-flex align-items-center gap-2 w-100">
                  <i class="bi bi-file-earmark-code"></i>
                  <strong>{{ configName }}</strong>
                  <span class="badge bg-primary ms-auto me-3">
                    +{{ entries.length }} peer{{ entries.length !== 1 ? 's' : '' }}
                  </span>
                </div>
              </button>
            </h2>
            <div 
              :id="'config-' + index" 
              class="accordion-collapse collapse"
              :class="{ show: index === 0 }"
            >
              <div class="accordion-body p-0">
                <div class="table-responsive">
                  <table class="table table-hover mb-0">
                    <thead class="table-light">
                      <tr>
                        <th><LocaleText t="Peer Name"></LocaleText></th>
                        <th><LocaleText t="Public Key"></LocaleText></th>
                        <th><LocaleText t="Allowed IPs"></LocaleText></th>
                        <th><LocaleText t="Endpoint"></LocaleText></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(entry, entryIndex) in entries" :key="entryIndex">
                        <td>
                          <code>{{ entry.peer_name }}</code>
                        </td>
                        <td>
                          <code class="text-truncate d-inline-block" style="max-width: 150px;" :title="entry.public_key">
                            {{ entry.public_key.substring(0, 20) }}...
                          </code>
                        </td>
                        <td>
                          <span class="badge bg-secondary">{{ entry.allowed_ips }}</span>
                        </td>
                        <td>
                          <span v-if="entry.endpoint" class="text-muted small">
                            {{ entry.endpoint }}
                          </span>
                          <span v-else class="text-muted small fst-italic">
                            (dynamic)
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Empty State -->
        <div v-if="totalPeerEntries === 0" class="text-center py-5">
          <i class="bi bi-inbox fs-1 text-muted"></i>
          <p class="mt-2 text-muted mb-0">
            <LocaleText t="No peer entries to add. Create some connections first."></LocaleText>
          </p>
        </div>
      </div>
    </div>
    
    <!-- Network Topology Visualization -->
    <div class="mt-4">
      <MeshNetworkVisualizer
        :preview="preview"
        :interactive="true"
        height="600px"
      />
    </div>
    
    <!-- Connections List (Legacy View) -->
    <div class="card rounded-3 shadow mt-4">
      <div class="card-header">
        <i class="bi bi-share me-2"></i>
        <LocaleText t="Connection List"></LocaleText>
      </div>
      <div class="card-body">
        <div class="connection-map">
          <div 
            v-for="(conn, index) in preview?.connections" 
            :key="index"
            class="connection-item"
          >
            <div class="connection-node">
              <i class="bi bi-hdd"></i>
              <span>{{ conn.from }}</span>
            </div>
            <div class="connection-arrow">
              <i class="bi bi-arrow-left-right"></i>
            </div>
            <div class="connection-node">
              <i class="bi bi-hdd"></i>
              <span>{{ conn.to }}</span>
            </div>
            <span 
              class="connection-status"
              :class="conn.enabled ? 'text-success' : 'text-muted'"
            >
              <i :class="conn.enabled ? 'bi-check-circle-fill' : 'bi-x-circle'"></i>
            </span>
          </div>
          
          <div v-if="!preview?.connections?.length" class="text-center text-muted">
            <LocaleText t="No connections defined"></LocaleText>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary-stat {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.75rem;
  background: var(--bs-secondary-bg);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--bs-secondary-color);
  margin-top: 0.25rem;
}

.warning-item {
  padding: 0.75rem;
  background: var(--bs-warning-bg-subtle);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}

.warning-item:last-child {
  margin-bottom: 0;
}

.connection-map {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--bs-secondary-bg);
  border-radius: 0.5rem;
}

.connection-node {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.connection-node i {
  color: var(--bs-primary);
}

.connection-arrow {
  color: var(--bs-secondary-color);
}

.connection-status {
  margin-left: auto;
}

.accordion-button:not(.collapsed) {
  background-color: var(--bs-primary-bg-subtle);
}
</style>

