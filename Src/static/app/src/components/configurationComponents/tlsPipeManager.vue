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
	count: 0,
	route_count: 0,
	running_count: 0,
	servers: {}
})

// Routes (configs using TCP tunnel)
const routes = ref([])

// Current config settings
const configEnabled = ref(false)
const configSettings = ref({
	tcp_port: 443,
	wireguard_port: 51820,
	max_connections: 100,
	max_queue_size: 1000,
	use_websocket: false,
	use_tls: false,
	tls_cert_path: '',
	tls_key_path: '',
	tls_ca_path: ''
})

// Fetch server status
const fetchStatus = async () => {
	loading.value = true
	await fetchGet('/api/wgtcptunnel/status', {}, (res) => {
		if (res.status && res.data) {
			serverStatus.value = {
				count: res.data.count || 0,
				route_count: res.data.route_count || 0,
				running_count: res.data.running_count || 0,
				servers: res.data.servers || {}
			}
		}
		loading.value = false
	})
}

// Fetch all routes with details
const fetchRoutes = async () => {
	await fetchGet('/api/wgtcptunnel/routes', {}, (res) => {
		if (res.status && res.data) {
			routes.value = res.data
			// Check if current config is enabled
			configEnabled.value = routes.value.some(r => r.config_name === props.configurationInfo?.Name)
		}
	})
}

// Enable TCP tunnel for current config
const enableTcpTunnel = async () => {
	if (!configSettings.value.tcp_port || configSettings.value.tcp_port < 1 || configSettings.value.tcp_port > 65535) {
		dashboardStore.newMessage('TCP Tunnel', 'Please enter a valid TCP port (1-65535)', 'danger')
		return
	}
	
	// Note: TLS certificates are optional - server will auto-generate self-signed if not provided
	
	saving.value = true
	await fetchPost(`/api/wgtcptunnel/enable/${props.configurationInfo.Name}`, {
		tcp_port: configSettings.value.tcp_port,
		wireguard_port: configSettings.value.wireguard_port || props.configurationInfo.ListenPort,
		max_connections: configSettings.value.max_connections,
		max_queue_size: configSettings.value.max_queue_size,
		use_websocket: configSettings.value.use_websocket,
		use_tls: configSettings.value.use_tls,
		tls_cert_path: configSettings.value.tls_cert_path || null,
		tls_key_path: configSettings.value.tls_key_path || null,
		tls_ca_path: configSettings.value.tls_ca_path || null
	}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TCP Tunnel', `Enabled for ${props.configurationInfo.Name}`, 'success')
			configEnabled.value = true
			fetchStatus()
			fetchRoutes()
			emit('refresh')
		} else {
			dashboardStore.newMessage('TCP Tunnel', res.message || 'Failed to enable', 'danger')
		}
		saving.value = false
	})
}

// Disable TCP tunnel for current config
const disableTcpTunnel = async () => {
	saving.value = true
	await fetchPost(`/api/wgtcptunnel/disable/${props.configurationInfo.Name}`, {}, (res) => {
		if (res.status) {
			dashboardStore.newMessage('TCP Tunnel', `Disabled for ${props.configurationInfo.Name}`, 'success')
			configEnabled.value = false
			fetchStatus()
			fetchRoutes()
			emit('refresh')
		} else {
			dashboardStore.newMessage('TCP Tunnel', res.message || 'Failed to disable', 'danger')
		}
		saving.value = false
	})
}

// Initialize
onMounted(async () => {
	await fetchStatus()
	await fetchRoutes()
	
	// Find current route to get settings
	const currentRoute = routes.value.find(r => r.config_name === props.configurationInfo?.Name)
	if (currentRoute) {
		configSettings.value.tcp_port = currentRoute.tcp_port || 443
		configSettings.value.wireguard_port = currentRoute.wireguard_port || props.configurationInfo?.ListenPort || 51820
		configSettings.value.max_connections = currentRoute.max_connections || 100
		configSettings.value.max_queue_size = currentRoute.max_queue_size || 1000
		configSettings.value.use_websocket = currentRoute.use_websocket || false
		configSettings.value.use_tls = currentRoute.use_tls || false
		configSettings.value.tls_cert_path = currentRoute.tls_cert_path || ''
		configSettings.value.tls_key_path = currentRoute.tls_key_path || ''
		configSettings.value.tls_ca_path = currentRoute.tls_ca_path || ''
	} else {
		// Use config's listen port for WireGuard port
		configSettings.value.wireguard_port = props.configurationInfo?.ListenPort || 51820
		configSettings.value.max_connections = 100
		configSettings.value.max_queue_size = 1000
	}
})

// Computed: is current config using the tunnel
const isCurrentConfigActive = computed(() => {
	return routes.value.some(r => r.config_name === props.configurationInfo?.Name)
})

// Get current route info
const currentRoute = computed(() => {
	return routes.value.find(r => r.config_name === props.configurationInfo?.Name)
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
						<i class="bi bi-ethernet text-primary fs-5"></i>
					</div>
					<div>
						<h5 class="modal-title mb-0">
							<LocaleText t="TCP Tunnel Server"></LocaleText>
						</h5>
						<small class="text-muted">UDP over TCP • Works on Restricted Networks</small>
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
								<span v-if="serverStatus.running_count > 0" 
								      class="badge bg-success-subtle text-success-emphasis d-flex align-items-center gap-1">
									<span class="pulse-dot bg-success"></span>
									{{ serverStatus.running_count }} Running
								</span>
								<span v-else class="badge bg-secondary-subtle text-secondary-emphasis">
									No Active Tunnels
								</span>
							</div>
							
							<div class="row g-3">
								<div class="col-6 col-md-4">
									<div class="text-muted small">Routes</div>
									<div class="fw-semibold">
										<i class="bi bi-signpost-split me-1"></i>
										{{ serverStatus.route_count }}
									</div>
								</div>
								<div class="col-6 col-md-4">
									<div class="text-muted small">Running</div>
									<div class="fw-semibold">
										<i class="bi bi-play-circle me-1 text-success"></i>
										{{ serverStatus.running_count }}
									</div>
								</div>
								<div class="col-6 col-md-4">
									<div class="text-muted small">Protocol</div>
									<div class="fw-semibold">
										<i class="bi bi-arrow-left-right me-1"></i>
										TCP → UDP
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
							
							<!-- Current Route Info -->
							<div v-if="currentRoute" class="alert alert-success border-0 mb-3">
								<div class="small">
									<strong>Listening on TCP port {{ currentRoute.tcp_port }}</strong>
									→ forwarding to WireGuard UDP port {{ currentRoute.wireguard_port }}
									<span v-if="currentRoute.use_tls" class="badge bg-warning-subtle text-warning-emphasis ms-2">
										<i class="bi bi-shield-lock me-1"></i>TLS
									</span>
									<span v-if="currentRoute.use_websocket" class="badge bg-info-subtle text-info-emphasis ms-2">
										<i class="bi bi-globe me-1"></i>WebSocket
									</span>
									<span v-if="currentRoute.use_tls && currentRoute.use_websocket" class="badge bg-success-subtle text-success-emphasis ms-2">
										<i class="bi bi-shield-check me-1"></i>WSS
									</span>
								</div>
								<div class="small text-muted mt-1" v-if="currentRoute.running">
									<i class="bi bi-check-circle me-1"></i> Server is running
								</div>
							</div>
							
							<!-- Settings Form (only show when not active) -->
							<div v-if="!isCurrentConfigActive">
							<div class="row g-3 mb-3">
									<div class="col-md-6">
									<label class="form-label small text-muted">
											<i class="bi bi-ethernet me-1"></i>
											TCP Port (clients connect to)
									</label>
										<input type="number" 
										       class="form-control font-monospace" 
										       v-model.number="configSettings.tcp_port"
										       min="1" max="65535"
										       placeholder="443">
									<div class="form-text">
											Port clients will connect to over TCP
										</div>
									</div>
									<div class="col-md-6">
									<label class="form-label small text-muted">
											<i class="bi bi-hdd-network me-1"></i>
											WireGuard Port
										</label>
										<input type="number" 
										       class="form-control font-monospace" 
										       v-model.number="configSettings.wireguard_port"
										       min="1" max="65535"
										       :placeholder="configurationInfo.ListenPort || 51820">
										<div class="form-text">
											WireGuard's UDP listen port
										</div>
									</div>
								</div>
								<div class="row g-3 mb-3">
									<div class="col-md-6">
										<label class="form-label small text-muted">
											<i class="bi bi-diagram-3 me-1"></i>
											Max Connections
										</label>
										<input type="number" 
										       class="form-control font-monospace" 
										       v-model.number="configSettings.max_connections"
										       min="1" max="10000"
										       placeholder="100">
										<div class="form-text">
											Max concurrent TCP connections per UDP source (default: 100)
										</div>
									</div>
									<div class="col-md-6">
										<label class="form-label small text-muted">
											<i class="bi bi-stack me-1"></i>
											Max Queue Size
										</label>
										<input type="number" 
										       class="form-control font-monospace" 
										       v-model.number="configSettings.max_queue_size"
										       min="1" max="10000"
										       placeholder="1000">
										<div class="form-text">
											Max queued packets per connection (default: 1000)
										</div>
									</div>
								</div>
								
								<!-- WebSocket Toggle -->
								<div class="row g-3 mb-3">
									<div class="col-12">
										<div class="form-check form-switch">
											<input class="form-check-input" 
											       type="checkbox" 
											       role="switch" 
											       id="useWebSocket"
											       v-model="configSettings.use_websocket">
											<label class="form-check-label" for="useWebSocket">
												<i class="bi bi-globe me-1"></i>
												Enable WebSocket Transport
											</label>
										</div>
										<div class="form-text">
											Wrap traffic in WebSocket frames for better firewall/proxy compatibility
										</div>
									</div>
								</div>
								
								<!-- TLS Settings -->
								<div class="card bg-body-secondary border-0 rounded-3 p-3 mb-3">
									<div class="row g-3">
										<div class="col-12">
											<div class="form-check form-switch">
												<input class="form-check-input" 
												       type="checkbox" 
												       role="switch" 
												       id="useTls"
												       v-model="configSettings.use_tls">
												<label class="form-check-label" for="useTls">
													<i class="bi bi-shield-lock me-1"></i>
													Enable TLS Encryption
												</label>
											</div>
											<div class="form-text">
												Encrypt traffic using TLS/SSL. Auto-generates self-signed certificate if none provided. When combined with WebSocket, creates WSS.
											</div>
										</div>
									</div>
									
									<!-- TLS Certificate Settings (shown when TLS is enabled) -->
									<div v-if="configSettings.use_tls" class="mt-3">
										<div class="row g-3">
											<div class="col-md-6">
												<label class="form-label small text-muted">
													<i class="bi bi-file-earmark-lock me-1"></i>
													Certificate Path <span class="text-muted">(optional)</span>
												</label>
												<input type="text" 
												       class="form-control font-monospace" 
												       v-model="configSettings.tls_cert_path"
												       placeholder="Auto-generated if empty">
												<div class="form-text">
													Path to TLS certificate (PEM). Leave empty to auto-generate self-signed.
												</div>
											</div>
											<div class="col-md-6">
												<label class="form-label small text-muted">
													<i class="bi bi-key me-1"></i>
													Private Key Path <span class="text-muted">(optional)</span>
												</label>
												<input type="text" 
												       class="form-control font-monospace" 
												       v-model="configSettings.tls_key_path"
												       placeholder="Auto-generated if empty">
												<div class="form-text">
													Path to TLS private key (PEM). Leave empty to auto-generate self-signed.
												</div>
											</div>
										</div>
										<div class="row g-3 mt-1">
											<div class="col-12">
												<label class="form-label small text-muted">
													<i class="bi bi-file-earmark-check me-1"></i>
													CA Certificate Path (Optional)
												</label>
												<input type="text" 
												       class="form-control font-monospace" 
												       v-model="configSettings.tls_ca_path"
												       placeholder="/etc/ssl/certs/ca.crt">
												<div class="form-text">
													Path to CA certificate for client verification (optional, for mutual TLS)
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							
							<!-- Action Buttons -->
							<div class="d-flex gap-2">
								<button v-if="!isCurrentConfigActive"
								        class="btn btn-primary flex-grow-1"
								        @click="enableTcpTunnel"
								        :disabled="saving">
									<span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
									<i v-else class="bi bi-power me-2"></i>
									<LocaleText t="Enable TCP Tunnel"></LocaleText>
								</button>
								<button v-else
								        class="btn btn-danger flex-grow-1"
								        @click="disableTcpTunnel"
								        :disabled="saving">
									<span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
									<i v-else class="bi bi-stop-circle me-2"></i>
									<LocaleText t="Disable TCP Tunnel"></LocaleText>
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
											<th class="border-0">TCP Port</th>
											<th class="border-0">WG Port</th>
											<th class="border-0">Transport</th>
											<th class="border-0">Status</th>
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
												{{ route.tcp_port }}
											</td>
											<td class="align-middle font-monospace text-muted">
												{{ route.wireguard_port }}
											</td>
											<td class="align-middle">
												<div class="d-flex flex-wrap gap-1">
													<span v-if="route.use_tls && route.use_websocket" 
													      class="badge bg-success-subtle text-success-emphasis">
														WSS
													</span>
													<span v-else-if="route.use_tls" 
													      class="badge bg-warning-subtle text-warning-emphasis">
														TLS
													</span>
													<span v-else-if="route.use_websocket" 
													      class="badge bg-info-subtle text-info-emphasis">
														WS
													</span>
													<span v-else 
													      class="badge bg-secondary-subtle text-secondary-emphasis">
														TCP
													</span>
												</div>
											</td>
											<td class="align-middle">
												<span v-if="route.running" class="badge bg-success-subtle text-success-emphasis">
													<i class="bi bi-check-circle me-1"></i> Running
												</span>
												<span v-else class="badge bg-secondary-subtle text-secondary-emphasis">
													Stopped
												</span>
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
							<strong>How it works:</strong> The TCP tunnel server wraps WireGuard's UDP traffic 
							in TCP, allowing it to work on networks that block UDP. Each configuration has its 
							own TCP port. Clients connect to the TCP port, and the server forwards traffic to 
							the corresponding WireGuard UDP port.<br><br>
							<strong>Transport Options:</strong><br>
							• <strong>TCP</strong> — Raw TCP transport<br>
							• <strong>TLS</strong> — Encrypted TCP with TLS/SSL<br>
							• <strong>WS</strong> — WebSocket for firewall/proxy compatibility<br>
							• <strong>WSS</strong> — WebSocket over TLS (most compatible and secure)
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
