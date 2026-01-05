<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { fetchGet, fetchPost } from '@/utilities/fetch.js'
import { DashboardConfigurationStore } from '@/stores/DashboardConfigurationStore.js'
import { WireguardConfigurationsStore } from '@/stores/WireguardConfigurationsStore.js'
import LocaleText from '@/components/text/localeText.vue'

const dashboardStore = DashboardConfigurationStore()
const wireguardStore = WireguardConfigurationsStore()
const loading = ref(true)
const saving = ref(false)
const refreshInterval = ref(null)

// Server status
const serverStatus = ref({
	count: 0,
	route_count: 0,
	running_count: 0,
	servers: {}
})

// Routes (configs using TCP tunnel)
const routes = ref([])

// New config to add
const newConfig = ref({
	configName: '',
	tcp_port: 443,
	wireguard_port: 51820,
	max_connections: 100,
	max_queue_size: 1000,
	use_websocket: false
})

// Available configs (not yet using TCP tunnel)
const availableConfigs = computed(() => {
	const usedConfigs = routes.value.map(r => r.config_name)
	return wireguardStore.Configurations?.filter(c => !usedConfigs.includes(c.Name)) || []
})

// Fetch server status
const fetchStatus = async () => {
	await fetchGet('/api/wgtcptunnel/status', {}, (res) => {
		if (res.status && res.data) {
			serverStatus.value = {
				count: res.data.count || 0,
				route_count: res.data.route_count || 0,
				running_count: res.data.running_count || 0,
				servers: res.data.servers || {}
			}
		}
	})
}

// Fetch all routes with details
const fetchRoutes = async () => {
	await fetchGet('/api/wgtcptunnel/routes', {}, (res) => {
		if (res.status && res.data) {
			routes.value = res.data
		}
	})
}

// Load all data
const loadData = async () => {
	loading.value = true
	await Promise.all([fetchStatus(), fetchRoutes()])
	loading.value = false
}

// Enable TCP tunnel for a config
const enableTcpTunnel = async () => {
	if (!newConfig.value.configName) {
		dashboardStore.newMessage('TCP Tunnel', 'Please select a configuration', 'warning')
		return
	}
	if (!newConfig.value.tcp_port || newConfig.value.tcp_port < 1 || newConfig.value.tcp_port > 65535) {
		dashboardStore.newMessage('TCP Tunnel', 'Please enter a valid TCP port (1-65535)', 'danger')
		return
	}
	
	saving.value = true
	await fetchPost(`/api/wgtcptunnel/enable/${newConfig.value.configName}`, {
		tcp_port: newConfig.value.tcp_port,
		wireguard_port: newConfig.value.wireguard_port,
		max_connections: newConfig.value.max_connections,
		max_queue_size: newConfig.value.max_queue_size,
		use_websocket: newConfig.value.use_websocket
	}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TCP Tunnel', `Enabled for ${newConfig.value.configName}`, 'success')
			// Reset form
			newConfig.value = {
				configName: '',
				tcp_port: 443,
				wireguard_port: 51820,
				max_connections: 100,
				max_queue_size: 1000,
				use_websocket: false
			}
			loadData()
		} else {
			dashboardStore.newMessage('TCP Tunnel', res.message || 'Failed to enable', 'danger')
		}
		saving.value = false
	})
}

// Disable TCP tunnel for a config
const disableTcpTunnel = async (configName) => {
	if (!confirm(`Disable TCP tunneling for ${configName}?`)) return
	
	saving.value = true
	await fetchPost(`/api/wgtcptunnel/disable/${configName}`, {}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TCP Tunnel', `Disabled for ${configName}`, 'success')
			loadData()
		} else {
			dashboardStore.newMessage('TCP Tunnel', res.message || 'Failed to disable', 'danger')
		}
		saving.value = false
	})
}

// Initialize
onMounted(async () => {
	await loadData()
	
	// Set up refresh interval
	refreshInterval.value = setInterval(loadData, 10000)
	dashboardStore.registerInterval(refreshInterval.value)
})

onBeforeUnmount(() => {
	if (refreshInterval.value) {
		dashboardStore.unregisterInterval(refreshInterval.value)
		clearInterval(refreshInterval.value)
	}
})
</script>

<template>
<div class="container-fluid">
	<!-- Header -->
	<div class="d-flex align-items-center gap-3 mb-4">
		<div class="rounded-circle bg-primary-subtle d-flex align-items-center justify-content-center" 
		     style="width: 56px; height: 56px;">
			<i class="bi bi-ethernet text-primary fs-3"></i>
		</div>
		<div>
			<h1 class="mb-0 display-5">
				<LocaleText t="TCP Tunnel Server"></LocaleText>
			</h1>
			<p class="text-muted mb-0">
				<LocaleText t="UDP over TCP tunneling for restricted networks"></LocaleText>
			</p>
		</div>
	</div>

	<!-- Loading State -->
	<div v-if="loading" class="text-center py-5">
		<div class="spinner-border text-primary" role="status">
			<span class="visually-hidden">Loading...</span>
		</div>
	</div>

	<template v-else>
		<!-- Server Status Card -->
		<div class="row g-4 mb-4">
			<div class="col-12 col-lg-8">
				<div class="card border-0 shadow-sm rounded-4">
					<div class="card-body p-4">
						<div class="d-flex align-items-center justify-content-between mb-4">
							<h5 class="mb-0 d-flex align-items-center gap-2">
								<i class="bi bi-hdd-network-fill"></i>
								<LocaleText t="Server Status"></LocaleText>
							</h5>
							<div class="d-flex align-items-center gap-2">
								<span v-if="serverStatus.running_count > 0" 
								      class="badge bg-success d-flex align-items-center gap-2 px-3 py-2">
									<span class="pulse-dot bg-white"></span>
									{{ serverStatus.running_count }} <LocaleText t="Running"></LocaleText>
								</span>
								<span v-else class="badge bg-secondary px-3 py-2">
									<LocaleText t="No Active Tunnels"></LocaleText>
								</span>
								<button class="btn btn-sm btn-outline-secondary" @click="loadData" :disabled="loading">
									<i class="bi bi-arrow-clockwise"></i>
								</button>
							</div>
						</div>
						
						<div class="row g-4">
							<div class="col-6 col-md-4">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Configured Routes"></LocaleText>
									</div>
									<div class="h4 mb-0 font-monospace text-primary">
										{{ serverStatus.route_count }}
									</div>
								</div>
							</div>
							<div class="col-6 col-md-4">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Active Servers"></LocaleText>
									</div>
									<div class="h4 mb-0 font-monospace text-success">
										{{ serverStatus.running_count }}
									</div>
								</div>
							</div>
							<div class="col-6 col-md-4">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Total Servers"></LocaleText>
									</div>
									<div class="h4 mb-0 font-monospace">
										{{ serverStatus.count }}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			
			<!-- Info Card -->
			<div class="col-12 col-lg-4">
				<div class="card border-0 shadow-sm rounded-4 h-100 bg-primary-subtle">
					<div class="card-body p-4">
						<h6 class="mb-3 d-flex align-items-center gap-2">
							<i class="bi bi-info-circle-fill text-primary"></i>
							<LocaleText t="How it Works"></LocaleText>
						</h6>
						<ul class="list-unstyled small text-muted mb-0">
							<li class="mb-2">
								<i class="bi bi-check-circle text-success me-1"></i>
								<LocaleText t="Wraps WireGuard UDP in TCP"></LocaleText>
							</li>
							<li class="mb-2">
								<i class="bi bi-check-circle text-success me-1"></i>
								<LocaleText t="Works on any TCP port"></LocaleText>
							</li>
							<li class="mb-2">
								<i class="bi bi-check-circle text-success me-1"></i>
								<LocaleText t="Simple and lightweight"></LocaleText>
							</li>
							<li class="mb-2">
								<i class="bi bi-check-circle text-success me-1"></i>
								<LocaleText t="Client auto-reconnects"></LocaleText>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>

		<!-- Routes Table -->
		<div class="card border-0 shadow-sm rounded-4">
			<div class="card-header bg-transparent border-0 p-4 pb-0">
				<div class="d-flex align-items-center justify-content-between">
				<h5 class="mb-0 d-flex align-items-center gap-2">
						<i class="bi bi-list-ul"></i>
						<LocaleText t="Configured Tunnels"></LocaleText>
				</h5>
				</div>
			</div>
			<div class="card-body p-4">
				<!-- Routes List -->
				<div v-if="routes.length > 0" class="table-responsive">
					<table class="table table-hover align-middle mb-0">
						<thead class="table-light">
							<tr>
								<th><LocaleText t="Configuration"></LocaleText></th>
								<th><LocaleText t="TCP Port"></LocaleText></th>
								<th><LocaleText t="WireGuard Port"></LocaleText></th>
								<th><LocaleText t="Status"></LocaleText></th>
								<th class="text-end"><LocaleText t="Actions"></LocaleText></th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="route in routes" :key="route.config_name">
								<td>
									<span class="fw-medium">{{ route.config_name }}</span>
								</td>
								<td>
									<code class="bg-body-tertiary px-2 py-1 rounded">{{ route.tcp_port }}</code>
									<span v-if="route.use_websocket" class="badge bg-info-subtle text-info-emphasis ms-1" title="WebSocket transport enabled">
										<i class="bi bi-globe"></i>
									</span>
								</td>
								<td>
									<code class="bg-body-tertiary px-2 py-1 rounded">{{ route.wireguard_port }}</code>
								</td>
								<td>
									<span v-if="route.running" class="badge bg-success">
										<i class="bi bi-check-circle me-1"></i>
										<LocaleText t="Running"></LocaleText>
									</span>
									<span v-else class="badge bg-secondary">
										<LocaleText t="Stopped"></LocaleText>
									</span>
								</td>
								<td class="text-end">
										<button class="btn btn-sm btn-outline-danger" 
									        @click="disableTcpTunnel(route.config_name)"
									        :disabled="saving">
											<i class="bi bi-trash"></i>
										</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				
				<!-- Empty State -->
				<div v-else class="text-center py-5 text-muted">
					<i class="bi bi-inbox fs-1 mb-3 d-block opacity-50"></i>
					<p class="mb-0"><LocaleText t="No TCP tunnels configured"></LocaleText></p>
					<p class="small"><LocaleText t="Add a configuration below to get started"></LocaleText></p>
				</div>
			</div>
		</div>

		<!-- Add New Route Card -->
		<div class="card border-0 shadow-sm rounded-4 mt-4">
			<div class="card-header bg-transparent border-0 p-4 pb-0">
				<h5 class="mb-0 d-flex align-items-center gap-2">
					<i class="bi bi-plus-circle"></i>
					<LocaleText t="Add New TCP Tunnel"></LocaleText>
				</h5>
			</div>
			<div class="card-body p-4">
				<div class="row g-3">
					<div class="col-12 col-md-3">
						<label class="form-label small text-muted">
							<LocaleText t="Configuration"></LocaleText>
						</label>
						<select class="form-select" v-model="newConfig.configName" :disabled="saving">
							<option value="">Select a configuration...</option>
							<option v-for="config in availableConfigs" :key="config.Name" :value="config.Name">
								{{ config.Name }}
							</option>
						</select>
					</div>
					<div class="col-12 col-md-2">
						<label class="form-label small text-muted">
							<LocaleText t="TCP Port"></LocaleText>
						</label>
						<input type="number" 
						       class="form-control font-monospace" 
						       v-model.number="newConfig.tcp_port"
						       min="1" max="65535"
						       placeholder="443"
						       :disabled="saving">
						<div class="form-text small">Port clients connect to</div>
					</div>
					<div class="col-12 col-md-2">
						<label class="form-label small text-muted">
							<LocaleText t="WireGuard Port"></LocaleText>
						</label>
						<input type="number" 
						       class="form-control font-monospace" 
						       v-model.number="newConfig.wireguard_port"
						       min="1" max="65535"
						       placeholder="51820"
						       :disabled="saving">
						<div class="form-text small">WireGuard listen port</div>
					</div>
					<div class="col-12 col-md-2">
						<label class="form-label small text-muted">
							<LocaleText t="Max Connections"></LocaleText>
						</label>
						<input type="number" 
						       class="form-control font-monospace" 
						       v-model.number="newConfig.max_connections"
						       min="1" max="10000"
						       placeholder="100"
						       :disabled="saving">
						<div class="form-text small">Max concurrent connections</div>
					</div>
					<div class="col-12 col-md-2">
						<label class="form-label small text-muted">
							<LocaleText t="Max Queue Size"></LocaleText>
						</label>
						<input type="number" 
						       class="form-control font-monospace" 
						       v-model.number="newConfig.max_queue_size"
						       min="1" max="10000"
						       placeholder="1000"
						       :disabled="saving">
						<div class="form-text small">Max queued packets</div>
					</div>
				</div>
				<div class="row g-3 mt-2">
					<div class="col-12 col-md-auto">
						<div class="form-check form-switch">
							<input class="form-check-input" 
							       type="checkbox" 
							       role="switch" 
							       id="newConfigUseWebSocket"
							       v-model="newConfig.use_websocket"
							       :disabled="saving">
							<label class="form-check-label small" for="newConfigUseWebSocket">
								<i class="bi bi-globe me-1"></i>
								<LocaleText t="WebSocket Transport"></LocaleText>
							</label>
						</div>
					</div>
					<div class="col-12 col-md-auto ms-md-auto">
						<button class="btn btn-primary" 
						        @click="enableTcpTunnel" 
						        :disabled="saving || !newConfig.configName">
							<i class="bi bi-plus-lg me-1"></i>
							<LocaleText t="Enable TCP Tunnel"></LocaleText>
						</button>
					</div>
				</div>
			</div>
		</div>
	</template>
</div>
</template>

<style scoped>
.pulse-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.5; }
}
</style>
