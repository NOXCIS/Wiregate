<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { fetchGet, fetchPost } from '@/utilities/fetch.js'
import { DashboardConfigurationStore } from '@/stores/DashboardConfigurationStore.js'
import LocaleText from '@/components/text/localeText.vue'

const props = defineProps({
	configurationInfo: Object
})

const emit = defineEmits(['close', 'refresh'])

const dashboardStore = DashboardConfigurationStore()
const loading = ref(false)
const saving = ref(false)

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

// Current config settings
const configEnabled = ref(false)
const configSettings = ref({
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
	configSettings.value.password = result
}

// Fetch server status
const fetchStatus = async () => {
	loading.value = true
	await fetchGet('/api/udptlspipe/shared/status', {}, (res) => {
		if (res.status && res.data) {
			serverStatus.value = {
				running: res.data.running || false,
				pid: res.data.pid || null,
				listen_port: res.data.listen_port || 443,
				route_count: res.data.route_count || 0,
				routes: res.data.routes || []
			}
			// Check if current config is enabled
			configEnabled.value = serverStatus.value.routes.includes(props.configurationInfo?.Name)
		}
		loading.value = false
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

// Enable TLS pipe for current config
const enableTlsPipe = async () => {
	if (!configSettings.value.password) {
		dashboardStore.newMessage('TLS Pipe', 'Password is required', 'danger')
		return
	}
	
	saving.value = true
	await fetchPost(`/api/udptlspipe/shared/enable/${props.configurationInfo.Name}`, {
		password: configSettings.value.password,
		tls_server_name: configSettings.value.tls_server_name,
		secure: configSettings.value.secure
	}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TLS Pipe', `Enabled for ${props.configurationInfo.Name}`, 'success')
			configEnabled.value = true
			fetchStatus()
			fetchRoutes()
			emit('refresh')
		} else {
			dashboardStore.newMessage('TLS Pipe', res.message || 'Failed to enable', 'danger')
		}
		saving.value = false
	})
}

// Disable TLS pipe for current config
const disableTlsPipe = async () => {
	saving.value = true
	await fetchPost(`/api/udptlspipe/shared/disable/${props.configurationInfo.Name}`, {}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TLS Pipe', `Disabled for ${props.configurationInfo.Name}`, 'success')
			configEnabled.value = false
			fetchStatus()
			fetchRoutes()
			emit('refresh')
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

// Initialize
onMounted(async () => {
	await fetchStatus()
	await fetchRoutes()
	
	// Find current route to get settings
	const currentRoute = routes.value.find(r => r.config_name === props.configurationInfo?.Name)
	if (currentRoute) {
		configSettings.value.password = currentRoute.password || ''
	} else {
		// Generate a default password for new configs
		generatePassword()
	}
})

// Computed: is current config using the pipe
const isCurrentConfigActive = computed(() => {
	return serverStatus.value.routes.includes(props.configurationInfo?.Name)
})
</script>

<template>
<div class="modal fade show d-block" tabindex="-1" style="backdrop-filter: blur(3px); background-color: rgba(0,0,0,0.5);">
	<div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
		<div class="modal-content rounded-4 shadow-lg border-0">
			<!-- Header -->
			<div class="modal-header border-0 pb-0">
				<div class="d-flex align-items-center gap-2">
					<div class="rounded-circle bg-primary-subtle d-flex align-items-center justify-content-center" 
					     style="width: 42px; height: 42px;">
						<i class="bi bi-shield-lock-fill text-primary fs-5"></i>
					</div>
					<div>
						<h5 class="modal-title mb-0">
							<LocaleText t="Shared TLS Pipe Server"></LocaleText>
						</h5>
						<small class="text-muted">Port 443 • Censorship Resistant Tunnel</small>
					</div>
				</div>
				<button type="button" class="btn-close" @click="emit('close')"></button>
			</div>
			
			<div class="modal-body">
				<!-- Loading State -->
				<div v-if="loading" class="text-center py-5">
					<div class="spinner-border text-primary" role="status">
						<span class="visually-hidden">Loading...</span>
					</div>
				</div>
				
				<template v-else>
					<!-- Server Status Card -->
					<div class="card border-0 bg-body-tertiary rounded-3 mb-4">
						<div class="card-body">
							<div class="d-flex align-items-center justify-content-between mb-3">
								<h6 class="mb-0 d-flex align-items-center gap-2">
									<i class="bi bi-hdd-network-fill"></i>
									<LocaleText t="Server Status"></LocaleText>
								</h6>
								<span v-if="serverStatus.running" 
								      class="badge bg-success-subtle text-success-emphasis d-flex align-items-center gap-1">
									<span class="pulse-dot bg-success"></span>
									Running
								</span>
								<span v-else class="badge bg-secondary-subtle text-secondary-emphasis">
									Stopped
								</span>
							</div>
							
							<div class="row g-3">
								<div class="col-6 col-md-3">
									<div class="text-muted small">Port</div>
									<div class="fw-semibold">
										<i class="bi bi-ethernet me-1"></i>
										{{ serverStatus.listen_port }}
									</div>
								</div>
								<div class="col-6 col-md-3">
									<div class="text-muted small">Protocol</div>
									<div class="fw-semibold">
										<i class="bi bi-lock-fill me-1 text-success"></i>
										TLS/WSS
									</div>
								</div>
								<div class="col-6 col-md-3">
									<div class="text-muted small">Active Routes</div>
									<div class="fw-semibold">
										<i class="bi bi-signpost-split me-1"></i>
										{{ serverStatus.route_count }}
									</div>
								</div>
								<div class="col-6 col-md-3" v-if="serverStatus.pid">
									<div class="text-muted small">Process ID</div>
									<div class="fw-semibold font-monospace">
										{{ serverStatus.pid }}
									</div>
								</div>
							</div>
						</div>
					</div>
					
					<!-- Current Configuration Card -->
					<div class="card border-0 rounded-3 mb-4"
					     :class="isCurrentConfigActive ? 'bg-success-subtle' : 'bg-body-tertiary'">
						<div class="card-body">
							<div class="d-flex align-items-center justify-content-between mb-3">
								<h6 class="mb-0 d-flex align-items-center gap-2">
									<i class="bi bi-router-fill"></i>
									{{ configurationInfo.Name }}
								</h6>
								<span v-if="isCurrentConfigActive" 
								      class="badge bg-success d-flex align-items-center gap-1">
									<i class="bi bi-check-circle-fill"></i>
									Active
								</span>
								<span v-else class="badge bg-secondary">
									Not Configured
								</span>
							</div>
							
							<!-- Settings Form -->
							<div class="mb-3">
								<label class="form-label small text-muted">
									<i class="bi bi-key-fill me-1"></i>
									TLS Pipe Password
									<span class="text-danger">*</span>
								</label>
								<div class="input-group">
									<input type="text" 
									       class="form-control font-monospace" 
									       v-model="configSettings.password"
									       :disabled="isCurrentConfigActive"
									       placeholder="Enter password for this configuration">
									<button class="btn btn-outline-secondary" 
									        type="button"
									        @click="copyPassword(configSettings.password)"
									        title="Copy password">
										<i class="bi bi-clipboard"></i>
									</button>
									<button class="btn btn-outline-primary" 
									        type="button"
									        @click="generatePassword"
									        :disabled="isCurrentConfigActive"
									        title="Generate random password">
										<i class="bi bi-shuffle"></i>
									</button>
								</div>
								<div class="form-text">
									Clients connecting to this config must use this password
								</div>
							</div>
							
							<div class="row g-3 mb-3">
								<div class="col-md-8">
									<label class="form-label small text-muted">
										<i class="bi bi-globe me-1"></i>
										TLS Server Name (SNI)
									</label>
									<input type="text" 
									       class="form-control" 
									       v-model="configSettings.tls_server_name"
									       :disabled="isCurrentConfigActive"
									       placeholder="e.g., www.google.com">
									<div class="form-text">
										Fake hostname for TLS SNI (helps evade censorship)
									</div>
								</div>
								<div class="col-md-4">
									<label class="form-label small text-muted">
										<i class="bi bi-shield-check me-1"></i>
										Certificate Verification
									</label>
									<div class="form-check form-switch mt-2">
										<input class="form-check-input" 
										       type="checkbox" 
										       v-model="configSettings.secure"
										       :disabled="isCurrentConfigActive"
										       id="tlsSecureSwitch">
										<label class="form-check-label" for="tlsSecureSwitch">
											{{ configSettings.secure ? 'Enabled' : 'Disabled' }}
										</label>
									</div>
								</div>
							</div>
							
							<!-- Action Buttons -->
							<div class="d-flex gap-2">
								<button v-if="!isCurrentConfigActive"
								        class="btn btn-primary flex-grow-1"
								        @click="enableTlsPipe"
								        :disabled="saving || !configSettings.password">
									<span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
									<i v-else class="bi bi-power me-2"></i>
									<LocaleText t="Enable TLS Pipe"></LocaleText>
								</button>
								<button v-else
								        class="btn btn-danger flex-grow-1"
								        @click="disableTlsPipe"
								        :disabled="saving">
									<span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
									<i v-else class="bi bi-stop-circle me-2"></i>
									<LocaleText t="Disable TLS Pipe"></LocaleText>
								</button>
							</div>
						</div>
					</div>
					
					<!-- All Routes Card -->
					<div class="card border-0 bg-body-tertiary rounded-3" v-if="routes.length > 0">
						<div class="card-body">
							<h6 class="mb-3 d-flex align-items-center gap-2">
								<i class="bi bi-diagram-3-fill"></i>
								<LocaleText t="All Configured Routes"></LocaleText>
								<span class="badge bg-primary-subtle text-primary-emphasis ms-auto">
									{{ routes.length }}
								</span>
							</h6>
							
							<div class="table-responsive">
								<table class="table table-sm table-hover mb-0">
									<thead class="table-light">
										<tr>
											<th class="border-0">Configuration</th>
											<th class="border-0">WireGuard Port</th>
											<th class="border-0">Password</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="route in routes" :key="route.config_name"
										    :class="{'table-success': route.config_name === configurationInfo.Name}">
											<td class="align-middle">
												<div class="d-flex align-items-center gap-2">
													<i class="bi bi-hdd-network text-muted"></i>
													<span class="fw-semibold">{{ route.config_name }}</span>
													<span v-if="route.config_name === configurationInfo.Name" 
													      class="badge bg-success-subtle text-success-emphasis" 
													      style="font-size: 0.65rem;">
														Current
													</span>
												</div>
											</td>
											<td class="align-middle font-monospace text-muted">
												{{ route.destination }}
											</td>
											<td class="align-middle">
												<div class="d-flex align-items-center gap-1">
													<code class="bg-body-secondary px-2 py-1 rounded small">
														{{ route.password.substring(0, 8) }}...
													</code>
													<button class="btn btn-sm btn-link p-0" 
													        @click="copyPassword(route.password)"
													        title="Copy full password">
														<i class="bi bi-clipboard text-muted"></i>
													</button>
												</div>
											</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
					
					<!-- Info Box -->
					<div class="alert alert-info border-0 rounded-3 mt-4 mb-0 d-flex align-items-start gap-2">
						<i class="bi bi-info-circle-fill mt-1"></i>
						<div class="small">
							<strong>How it works:</strong> The shared TLS pipe server runs on port 443 and routes 
							traffic to different WireGuard configurations based on the password. Clients connect 
							to the same port but use different passwords to reach their respective VPN configs.
							This makes the traffic look like regular HTTPS, making it very hard to block.
						</div>
					</div>
				</template>
			</div>
			
			<!-- Footer -->
			<div class="modal-footer border-0 pt-0">
				<button type="button" class="btn btn-secondary" @click="emit('close')">
					<i class="bi bi-x-lg me-1"></i>
					<LocaleText t="Close"></LocaleText>
				</button>
				<button type="button" class="btn btn-outline-primary" @click="fetchStatus(); fetchRoutes()">
					<i class="bi bi-arrow-clockwise me-1"></i>
					<LocaleText t="Refresh"></LocaleText>
				</button>
			</div>
		</div>
	</div>
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
</style>

