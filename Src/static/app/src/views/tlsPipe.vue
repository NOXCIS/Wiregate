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
	running: false,
	pid: null,
	listen_port: 443,
	route_count: 0,
	routes: []
})

// Routes (configs using the shared pipe)
const routes = ref([])

// New config to add
const newConfig = ref({
	configName: '',
	password: '',
	tls_server_name: '',
	secure: false
})

// Generate random password
const generatePassword = () => {
	const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
	let result = ''
	for (let i = 0; i < 24; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length))
	}
	newConfig.value.password = result
}

// Available configs (not yet using TLS pipe)
const availableConfigs = computed(() => {
	const usedConfigs = routes.value.map(r => r.config_name)
	return wireguardStore.Configurations?.filter(c => !usedConfigs.includes(c.Name)) || []
})

// Fetch server status
const fetchStatus = async () => {
	await fetchGet('/api/udptlspipe/shared/status', {}, (res) => {
		if (res.status && res.data) {
			serverStatus.value = {
				running: res.data.running || false,
				pid: res.data.pid || null,
				listen_port: res.data.listen_port || 443,
				route_count: res.data.route_count || 0,
				routes: res.data.routes || []
			}
		}
	})
}

// Fetch all routes with details
const fetchRoutes = async () => {
	await fetchGet('/api/udptlspipe/shared/routes', {}, (res) => {
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

// Enable TLS pipe for a config
const enableTlsPipe = async () => {
	if (!newConfig.value.configName) {
		dashboardStore.newMessage('TLS Pipe', 'Please select a configuration', 'warning')
		return
	}
	if (!newConfig.value.password) {
		dashboardStore.newMessage('TLS Pipe', 'Password is required', 'danger')
		return
	}
	
	saving.value = true
	await fetchPost(`/api/udptlspipe/shared/enable/${newConfig.value.configName}`, {
		password: newConfig.value.password,
		tls_server_name: newConfig.value.tls_server_name,
		secure: newConfig.value.secure
	}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TLS Pipe', `Enabled for ${newConfig.value.configName}`, 'success')
			// Reset form
			newConfig.value = {
				configName: '',
				password: '',
				tls_server_name: '',
				secure: false
			}
			loadData()
		} else {
			dashboardStore.newMessage('TLS Pipe', res.message || 'Failed to enable', 'danger')
		}
		saving.value = false
	})
}

// Disable TLS pipe for a config
const disableTlsPipe = async (configName) => {
	if (!confirm(`Disable TLS piping for ${configName}?`)) return
	
	saving.value = true
	await fetchPost(`/api/udptlspipe/shared/disable/${configName}`, {}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TLS Pipe', `Disabled for ${configName}`, 'success')
			loadData()
		} else {
			dashboardStore.newMessage('TLS Pipe', res.message || 'Failed to disable', 'danger')
		}
		saving.value = false
	})
}

// Copy password to clipboard
const copyPassword = async (password) => {
	try {
		await navigator.clipboard.writeText(password)
		dashboardStore.newMessage('TLS Pipe', 'Password copied to clipboard', 'success')
	} catch (err) {
		dashboardStore.newMessage('TLS Pipe', 'Failed to copy password', 'danger')
	}
}

// Copy full connection string
const copyConnectionString = async (route) => {
	const connStr = `wss://${serverStatus.value.listen_port === 443 ? '' : ':' + serverStatus.value.listen_port}/?password=${route.password}`
	try {
		await navigator.clipboard.writeText(connStr)
		dashboardStore.newMessage('TLS Pipe', 'Connection string copied', 'success')
	} catch (err) {
		dashboardStore.newMessage('TLS Pipe', 'Failed to copy', 'danger')
	}
}

// Initialize
onMounted(async () => {
	await loadData()
	// Generate default password
	generatePassword()
	
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
		<div class="rounded-circle bg-success-subtle d-flex align-items-center justify-content-center" 
		     style="width: 56px; height: 56px;">
			<i class="bi bi-shield-lock-fill text-success fs-3"></i>
		</div>
		<div>
			<h1 class="mb-0 display-5">
				<LocaleText t="TLS Pipe Server"></LocaleText>
			</h1>
			<p class="text-muted mb-0">
				<LocaleText t="Censorship-resistant tunneling on port 443"></LocaleText>
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
								<span v-if="serverStatus.running" 
								      class="badge bg-success d-flex align-items-center gap-2 px-3 py-2">
									<span class="pulse-dot bg-white"></span>
									<LocaleText t="Running"></LocaleText>
								</span>
								<span v-else class="badge bg-secondary px-3 py-2">
									<LocaleText t="Stopped"></LocaleText>
								</span>
								<button class="btn btn-sm btn-outline-secondary" @click="loadData" :disabled="loading">
									<i class="bi bi-arrow-clockwise"></i>
								</button>
							</div>
						</div>
						
						<div class="row g-4">
							<div class="col-6 col-md-3">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Listen Port"></LocaleText>
									</div>
									<div class="h4 mb-0 font-monospace text-primary">
										{{ serverStatus.listen_port }}
									</div>
								</div>
							</div>
							<div class="col-6 col-md-3">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Protocol"></LocaleText>
									</div>
									<div class="h5 mb-0">
										<i class="bi bi-lock-fill text-success me-1"></i>
										TLS/WSS
									</div>
								</div>
							</div>
							<div class="col-6 col-md-3">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Active Routes"></LocaleText>
									</div>
									<div class="h4 mb-0 text-info">
										{{ serverStatus.route_count }}
									</div>
								</div>
							</div>
							<div class="col-6 col-md-3">
								<div class="p-3 bg-body-tertiary rounded-3 text-center">
									<div class="text-muted small mb-1">
										<LocaleText t="Process ID"></LocaleText>
									</div>
									<div class="h5 mb-0 font-monospace">
										{{ serverStatus.pid || '—' }}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			
			<!-- Quick Info Card -->
			<div class="col-12 col-lg-4">
				<div class="card border-0 shadow-sm rounded-4 h-100 bg-gradient-info">
					<div class="card-body p-4 text-white">
						<h5 class="mb-3 d-flex align-items-center gap-2">
							<i class="bi bi-info-circle-fill"></i>
							<LocaleText t="How It Works"></LocaleText>
						</h5>
						<ul class="list-unstyled mb-0 small">
							<li class="mb-2 d-flex gap-2">
								<i class="bi bi-check-circle-fill text-success"></i>
								<span>Single port 443 for all configs</span>
							</li>
							<li class="mb-2 d-flex gap-2">
								<i class="bi bi-check-circle-fill text-success"></i>
								<span>Password-based routing</span>
							</li>
							<li class="mb-2 d-flex gap-2">
								<i class="bi bi-check-circle-fill text-success"></i>
								<span>Looks like regular HTTPS</span>
							</li>
							<li class="mb-2 d-flex gap-2">
								<i class="bi bi-check-circle-fill text-success"></i>
								<span>Very hard to block/censor</span>
							</li>
							<li class="d-flex gap-2">
								<i class="bi bi-check-circle-fill text-success"></i>
								<span>TLS fingerprint mimicking</span>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>

		<!-- Add New Route Card -->
		<div class="card border-0 shadow-sm rounded-4 mb-4">
			<div class="card-header bg-transparent border-0 py-3">
				<h5 class="mb-0 d-flex align-items-center gap-2">
					<i class="bi bi-plus-circle-fill text-success"></i>
					<LocaleText t="Add Configuration"></LocaleText>
				</h5>
			</div>
			<div class="card-body">
				<div class="row g-3 align-items-end">
					<div class="col-12 col-md-3">
						<label class="form-label small text-muted">
							<i class="bi bi-hdd-network me-1"></i>
							<LocaleText t="Configuration"></LocaleText>
						</label>
						<select class="form-select" v-model="newConfig.configName" :disabled="saving || availableConfigs.length === 0">
							<option value="">Select configuration...</option>
							<option v-for="config in availableConfigs" :key="config.Name" :value="config.Name">
								{{ config.Name }}
							</option>
						</select>
					</div>
					<div class="col-12 col-md-3">
						<label class="form-label small text-muted">
							<i class="bi bi-key-fill me-1"></i>
							<LocaleText t="Password"></LocaleText>
							<span class="text-danger">*</span>
						</label>
						<div class="input-group">
							<input type="text" 
							       class="form-control font-monospace" 
							       v-model="newConfig.password"
							       :disabled="saving"
							       placeholder="TLS pipe password">
							<button class="btn btn-outline-primary" 
							        type="button"
							        @click="generatePassword"
							        :disabled="saving"
							        title="Generate random password">
								<i class="bi bi-shuffle"></i>
							</button>
						</div>
					</div>
					<div class="col-12 col-md-3">
						<label class="form-label small text-muted">
							<i class="bi bi-globe me-1"></i>
							<LocaleText t="TLS Server Name (SNI)"></LocaleText>
						</label>
						<input type="text" 
						       class="form-control" 
						       v-model="newConfig.tls_server_name"
						       :disabled="saving"
						       placeholder="e.g., www.google.com">
					</div>
					<div class="col-12 col-md-3">
						<button class="btn btn-success w-100"
						        @click="enableTlsPipe"
						        :disabled="saving || !newConfig.configName || !newConfig.password">
							<span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
							<i v-else class="bi bi-plus-lg me-2"></i>
							<LocaleText t="Enable TLS Pipe"></LocaleText>
						</button>
					</div>
				</div>
				<div v-if="availableConfigs.length === 0" class="alert alert-info mt-3 mb-0 d-flex align-items-center gap-2">
					<i class="bi bi-info-circle-fill"></i>
					<span>All configurations are already using TLS piping.</span>
				</div>
			</div>
		</div>

		<!-- Routes Table -->
		<div class="card border-0 shadow-sm rounded-4">
			<div class="card-header bg-transparent border-0 py-3 d-flex align-items-center justify-content-between">
				<h5 class="mb-0 d-flex align-items-center gap-2">
					<i class="bi bi-diagram-3-fill text-primary"></i>
					<LocaleText t="Configured Routes"></LocaleText>
				</h5>
				<span class="badge bg-primary-subtle text-primary-emphasis px-3 py-2">
					{{ routes.length }} <LocaleText t="route"></LocaleText><span v-if="routes.length !== 1">s</span>
				</span>
			</div>
			<div class="card-body p-0">
				<div v-if="routes.length === 0" class="text-center py-5 text-muted">
					<i class="bi bi-inbox display-4 d-block mb-3"></i>
					<p class="mb-0">No configurations are using TLS piping yet.</p>
					<p class="small">Add a configuration above to get started.</p>
				</div>
				<div v-else class="table-responsive">
					<table class="table table-hover align-middle mb-0">
						<thead class="table-light">
							<tr>
								<th class="ps-4 border-0">Configuration</th>
								<th class="border-0">WireGuard Destination</th>
								<th class="border-0">Password</th>
								<th class="border-0 text-center">Status</th>
								<th class="border-0 text-end pe-4">Actions</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="route in routes" :key="route.config_name">
								<td class="ps-4">
									<div class="d-flex align-items-center gap-2">
										<div class="rounded-circle bg-primary-subtle d-flex align-items-center justify-content-center" 
										     style="width: 36px; height: 36px;">
											<i class="bi bi-hdd-network text-primary"></i>
										</div>
										<div>
											<div class="fw-semibold">{{ route.config_name }}</div>
											<div class="text-muted small">
												<RouterLink :to="'/configuration/' + route.config_name + '/peers'" class="text-decoration-none">
													View peers →
												</RouterLink>
											</div>
										</div>
									</div>
								</td>
								<td>
									<code class="bg-body-tertiary px-2 py-1 rounded">
										{{ route.destination }}
									</code>
								</td>
								<td>
									<div class="d-flex align-items-center gap-2">
										<code class="bg-body-tertiary px-2 py-1 rounded text-truncate" style="max-width: 120px;">
											{{ route.password }}
										</code>
										<button class="btn btn-sm btn-outline-secondary" 
										        @click="copyPassword(route.password)"
										        title="Copy password">
											<i class="bi bi-clipboard"></i>
										</button>
									</div>
								</td>
								<td class="text-center">
									<span v-if="serverStatus.running" class="badge bg-success-subtle text-success-emphasis">
										<i class="bi bi-check-circle-fill me-1"></i>
										Active
									</span>
									<span v-else class="badge bg-secondary-subtle text-secondary-emphasis">
										Inactive
									</span>
								</td>
								<td class="text-end pe-4">
									<div class="btn-group">
										<button class="btn btn-sm btn-outline-secondary" 
										        @click="copyConnectionString(route)"
										        title="Copy connection string">
											<i class="bi bi-link-45deg"></i>
										</button>
										<button class="btn btn-sm btn-outline-danger" 
										        @click="disableTlsPipe(route.config_name)"
										        :disabled="saving"
										        title="Remove from TLS pipe">
											<i class="bi bi-trash"></i>
										</button>
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>

		<!-- Info Section -->
		<div class="row g-4 mt-2">
			<div class="col-12 col-md-6">
				<div class="card border-0 bg-body-tertiary rounded-4">
					<div class="card-body">
						<h6 class="d-flex align-items-center gap-2 mb-3">
							<i class="bi bi-shield-check text-success"></i>
							<LocaleText t="Censorship Resistance"></LocaleText>
						</h6>
						<p class="small text-muted mb-0">
							The TLS pipe wraps WireGuard UDP traffic in TLS WebSocket connections on port 443. 
							This makes the traffic indistinguishable from regular HTTPS, making it extremely 
							difficult for censors to detect or block.
						</p>
					</div>
				</div>
			</div>
			<div class="col-12 col-md-6">
				<div class="card border-0 bg-body-tertiary rounded-4">
					<div class="card-body">
						<h6 class="d-flex align-items-center gap-2 mb-3">
							<i class="bi bi-signpost-split text-primary"></i>
							<LocaleText t="Password-Based Routing"></LocaleText>
						</h6>
						<p class="small text-muted mb-0">
							Each configuration gets a unique password. When clients connect, the server uses 
							the password to route traffic to the correct WireGuard instance. All configs 
							share one port 443 entry point.
						</p>
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
	animation: pulse 2s infinite;
}

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.5; }
}

.font-monospace {
	font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', 'Droid Sans Mono', monospace;
}

.bg-gradient-info {
	background: linear-gradient(135deg, #0d6efd 0%, #6610f2 100%);
}

.rounded-4 {
	border-radius: 1rem !important;
}

.table th {
	font-weight: 500;
	font-size: 0.85rem;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--bs-secondary);
}

.table td {
	padding-top: 1rem;
	padding-bottom: 1rem;
}
</style>

