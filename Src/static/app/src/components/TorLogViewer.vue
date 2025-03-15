<script>
import { ref, watch, onMounted } from 'vue'
import { fetchGet, fetchPost } from '@/utilities/fetch.js'
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"

export default {
  name: 'TorLogViewer',
  props: {
    configType: {
      type: String,
      default: 'main',
      validator: (value) => ['main', 'dns'].includes(value)
    }
  },
  setup(props) {
    const dashboardStore = DashboardConfigurationStore()
    const logContent = ref('')
    const loading = ref(false)
    const autoRefresh = ref(false)
    const refreshInterval = ref(null)
    const logLines = ref(100) // Default number of lines to fetch
    const availableLogFiles = ref([])
    const selectedLogFile = ref('')

    const fetchLogFiles = async () => {
      try {
        loading.value = true
        await fetchGet('/api/tor/logs/files', {
          configType: props.configType
        }, (response) => {
          if (response?.status) {
            availableLogFiles.value = response.data.files || []
            if (availableLogFiles.value.length > 0 && !selectedLogFile.value) {
              selectedLogFile.value = availableLogFiles.value[0]
            }
          } else {
            throw new Error(response?.message || 'Failed to fetch log files')
          }
        })
      } catch (error) {
        console.error('Error fetching log files:', error)
        dashboardStore.newMessage('Error', error.message || 'Failed to fetch log files', 'error')
      } finally {
        loading.value = false
      }
    }

    const fetchLogs = async () => {
      try {
        loading.value = true
        await fetchGet('/api/tor/logs', {
          configType: props.configType,
          lines: logLines.value,
          file: selectedLogFile.value
        }, (response) => {
          if (response?.status) {
            logContent.value = response.data.content || 'No logs available'
          } else {
            throw new Error(response?.message || 'Failed to fetch logs')
          }
        })
      } catch (error) {
        console.error('Error fetching logs:', error)
        dashboardStore.newMessage('Error', error.message || 'Failed to fetch logs', 'error')
        logContent.value = 'Error loading logs'
      } finally {
        loading.value = false
      }
    }

    const toggleAutoRefresh = () => {
      autoRefresh.value = !autoRefresh.value
      if (autoRefresh.value) {
        refreshInterval.value = setInterval(fetchLogs, 5000) // Refresh every 5 seconds
      } else {
        clearInterval(refreshInterval.value)
        refreshInterval.value = null
      }
    }

    const clearLogs = async () => {
      try {
        if (!confirm('Are you sure you want to clear this log file?')) return
        
        loading.value = true
        await fetchPost('/api/tor/logs/clear', {
          configType: props.configType,
          file: selectedLogFile.value
        }, (response) => {
          if (response?.status) {
            logContent.value = ''
            dashboardStore.newMessage('Server', 'Logs cleared successfully', 'success')
          } else {
            throw new Error(response?.message || 'Failed to clear logs')
          }
        })
      } catch (error) {
        console.error('Error clearing logs:', error)
        dashboardStore.newMessage('Error', error.message || 'Failed to clear logs', 'error')
      } finally {
        loading.value = false
      }
    }

    // Watch for changes in config type or selected log file
    watch(() => props.configType, () => {
      fetchLogFiles()
    })

    watch(selectedLogFile, () => {
      fetchLogs()
    })

    onMounted(() => {
      fetchLogFiles()
    })

    // Clean up interval on component unmount
    const onBeforeUnmount = () => {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value)
      }
    }

    return {
      logContent,
      loading,
      autoRefresh,
      logLines,
      availableLogFiles,
      selectedLogFile,
      fetchLogs,
      toggleAutoRefresh,
      clearLogs,
      onBeforeUnmount
    }
  }
}
</script>

<template>
  <div class="tor-log-viewer">
    <div class="card shadow-sm">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">{{ configType === 'main' ? 'Main' : 'DNS' }} Tor Logs</h5>
        <div class="d-flex align-items-center gap-2">
          <select 
            v-model="logLines" 
            class="form-select form-select-sm" 
            style="width: auto;"
            :disabled="loading"
          >
            <option value="50">Last 50 lines</option>
            <option value="100">Last 100 lines</option>
            <option value="500">Last 500 lines</option>
            <option value="1000">Last 1000 lines</option>
          </select>
          
          <select 
            v-model="selectedLogFile" 
            class="form-select form-select-sm" 
            style="width: auto;"
            :disabled="loading || availableLogFiles.length === 0"
          >
            <option v-for="file in availableLogFiles" :key="file" :value="file">
              {{ file }}
            </option>
          </select>
          
          <button 
            class="btn btn-sm btn-outline-primary" 
            @click="fetchLogs" 
            :disabled="loading"
          >
            <i class="bi" :class="loading ? 'bi-hourglass-split' : 'bi-arrow-clockwise'"></i>
            Refresh
          </button>
          
          <button 
            class="btn btn-sm" 
            :class="autoRefresh ? 'btn-success' : 'btn-outline-secondary'" 
            @click="toggleAutoRefresh"
            :disabled="loading"
          >
            <i class="bi" :class="autoRefresh ? 'bi-play-fill' : 'bi-pause-fill'"></i>
            {{ autoRefresh ? 'Auto-refresh On' : 'Auto-refresh Off' }}
          </button>
          
          <button 
            class="btn btn-sm btn-outline-danger" 
            @click="clearLogs" 
            :disabled="loading || !selectedLogFile"
          >
            <i class="bi bi-trash"></i>
            Clear
          </button>
        </div>
      </div>
      
      <div class="card-body p-0">
        <div class="log-container">
          <pre 
            class="log-content" 
            :class="{ 'loading': loading }"
          >{{ logContent || 'No logs available' }}</pre>
          
          <div v-if="loading" class="log-overlay">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-container {
  position: relative;
  min-height: 300px;
  max-height: 500px;
}

.log-content {
  width: 100%;
  height: 100%;
  min-height: 300px;
  max-height: 500px;
  overflow-y: auto;
  background-color: #1e1e1e;
  color: #f8f8f8;
  padding: 1rem;
  margin: 0;
  font-family: monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-content.loading {
  opacity: 0.6;
}

.log-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.2);
}
</style>
