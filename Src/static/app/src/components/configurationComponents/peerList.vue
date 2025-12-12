<script setup async>
import {computed, defineAsyncComponent, onBeforeUnmount, ref, watch} from "vue";
import {useRoute} from "vue-router";
import {fetchGet} from "@/utilities/fetch.js";
import ProtocolBadge from "@/components/protocolBadge.vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import PeerDataUsageCharts from "@/components/configurationComponents/peerListComponents/peerDataUsageCharts.vue";
import PeerSearch from "@/components/configurationComponents/peerSearch.vue";
import Peer from "@/components/configurationComponents/peer.vue";
import PeerListModals from "@/components/configurationComponents/peerListComponents/peerListModals.vue";
import PeerIntersectionObserver from "@/components/configurationComponents/peerIntersectionObserver.vue";


// Async Components
const DeleteConfiguration = defineAsyncComponent(() => import("@/components/configurationComponents/deleteConfiguration.vue"))
const ConfigurationBackupRestore = defineAsyncComponent(() => import("@/components/configurationComponents/configurationBackupRestore.vue"))
const EditRawConfigurationFile = defineAsyncComponent(() => import("@/components/configurationComponents/editConfigurationComponents/editRawConfigurationFile.vue"))
const PeerSearchBar = defineAsyncComponent(() => import("@/components/configurationComponents/peerSearchBar.vue"))
const PeerJobsAllModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerJobsAllModal.vue"))
const PeerJobsLogsModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerJobsLogsModal.vue"))
const EditConfigurationModal = defineAsyncComponent(() => import("@/components/configurationComponents/editConfiguration.vue"))
const SelectPeersModal = defineAsyncComponent(() => import("@/components/configurationComponents/selectPeers.vue"))
const PeerAddModal = defineAsyncComponent(() => import("@/components/configurationComponents/peerAddModal.vue"))
const TlsPipeManager = defineAsyncComponent(() => import("@/components/configurationComponents/tlsPipeManager.vue"))

const dashboardStore = DashboardConfigurationStore()
const wireguardConfigurationStore = WireguardConfigurationsStore()
const route = useRoute()
const configurationInfo = ref({})
const configurationPeers = ref([])
const configurationToggling = ref(false)

// TLS Pipe Server Status (Shared)
const tlsPipeStatus = ref({
	running: false,
	loading: false,
	port: 443,
	routeCount: 0,
	configEnabled: false,
	shared: true
})
const configurationModalSelectedPeer = ref({})
const configurationModals = ref({
	peerNew: {
		modalOpen: false	
	},
	peerSetting: {
		modalOpen: false,
	},
	peerScheduleJobs:{
		modalOpen: false,
	},
	peerQRCode: {
		modalOpen: false,
	},
	peerConfigurationFile: {
		modalOpen: false,
	},
	peerCreate: {
		modalOpen: false
	},
	peerScheduleJobsAll: {
		modalOpen: false
	},
	peerScheduleJobsLogs: {
		modalOpen: false
	},
	peerShare:{
		modalOpen: false,
	},
	editConfiguration: {
		modalOpen: false
	},
	selectPeers: {
		modalOpen: false
	},
	backupRestore: {
		modalOpen: false
	},
	deleteConfiguration: {
		modalOpen: false
	},
	editRawConfigurationFile: {
		modalOpen: false
	},
	peerRateLimit: {
		modalOpen: false
	},
	tlsPipeManager: {
		modalOpen: false
	}
})
const peerSearchBar = ref(false)

// Fetch TLS Pipe Status (Shared Server) =====================================
const fetchTlsPipeStatus = async () => {
	tlsPipeStatus.value.loading = true
	// Fetch shared TLS pipe status
	await fetchGet('/api/udptlspipe/shared/status', {}, (res) => {
		if (res.status && res.data) {
			const isConfigEnabled = res.data.routes?.includes(route.params.id)
			tlsPipeStatus.value = {
				running: res.data.running || false,
				loading: false,
				port: res.data.listen_port || 443,
				pid: res.data.pid || null,
				routeCount: res.data.route_count || 0,
				configEnabled: isConfigEnabled,
				shared: true
			}
		} else {
			tlsPipeStatus.value = {
				running: false,
				loading: false,
				port: 443,
				routeCount: 0,
				configEnabled: false,
				shared: true
			}
		}
	})
}

// Count peers with TLS Piping enabled =====================================
const tlsPipePeersCount = computed(() => {
	return configurationPeers.value.filter(p => p.udptlspipe_enabled).length
})

// Fetch Peer =====================================
const fetchPeerList = async () => {
	console.log(`[DEBUG] fetchPeerList called for configuration: ${route.params.id}`);
	await fetchGet("/api/getWireguardConfigurationInfo", {
		configurationName: route.params.id
	}, async (res) => {
		console.log(`[DEBUG] fetchPeerList response:`, res);
		if (res.status){
			configurationInfo.value = res.data.configurationInfo;
			configurationPeers.value = res.data.configurationPeers;
			
			console.log(`[DEBUG] Received ${configurationPeers.value.length} peers`);
			configurationPeers.value.forEach((p, index) => {
				console.log(`[DEBUG] Peer ${index + 1}: ${p.id}, jobs: ${p.jobs ? p.jobs.length : 0}`);
				if (p.jobs && p.jobs.length > 0) {
					p.jobs.forEach((job, jobIndex) => {
						console.log(`[DEBUG]   Job ${jobIndex + 1}:`, job);
					});
				}
				p.restricted = false
			})
			res.data.configurationRestrictedPeers.forEach(x => {
				x.restricted = true;
				configurationPeers.value.push(x)
			})

			// Fetch rate limits for all peers (ignore errors for missing peers)
			for (const peer of configurationPeers.value) {
				try {
					await wireguardConfigurationStore.fetchPeerRateLimit(
						configurationInfo.value.Name,
						peer.id
					);
				} catch (error) {
					// Silently handle missing peers - this is expected when peers are deleted
					if (!error.message?.includes('not found')) {
						console.warn('Failed to fetch rate limit for peer:', peer.id, error);
					}
				}
			}
		}
	})
}
await fetchPeerList()
await fetchTlsPipeStatus()

// Fetch Peer Interval =====================================
const fetchPeerListInterval = ref(undefined)
const setFetchPeerListInterval = () => {
	// Unregister old interval if it exists
	if (fetchPeerListInterval.value) {
		dashboardStore.unregisterInterval(fetchPeerListInterval.value);
		clearInterval(fetchPeerListInterval.value);
	}
	fetchPeerListInterval.value = setInterval(async () => {
		await fetchPeerList()
		await fetchTlsPipeStatus()
	},  parseInt(dashboardStore.Configuration.Server.dashboard_refresh_interval))
	// Register the new interval with the global tracker
	if (fetchPeerListInterval.value) {
		dashboardStore.registerInterval(fetchPeerListInterval.value);
	}
}
setFetchPeerListInterval()
onBeforeUnmount(() => {
	if (fetchPeerListInterval.value) {
		dashboardStore.unregisterInterval(fetchPeerListInterval.value);
		clearInterval(fetchPeerListInterval.value);
		fetchPeerListInterval.value = undefined;
	}
})

watch(() => {
	return dashboardStore.Configuration.Server.dashboard_refresh_interval
}, () => {
	setFetchPeerListInterval()
})

// Toggle Configuration Method =====================================
const toggleConfiguration = async () => {
	configurationToggling.value = true;
	await fetchGet("/api/toggleConfiguration/", {
		configurationName: configurationInfo.value.Name
	}, (res) => {
		if (res.status){
			dashboardStore.newMessage("Server", 
				`${configurationInfo.value.Name} ${res.data ? 'is on':'is off'}`, "success")
		}else{
			dashboardStore.newMessage("Server", res.message, 'danger')
		}
		wireguardConfigurationStore.Configurations
			.find(x => x.Name === configurationInfo.value.Name).Status = res.data
		configurationInfo.value.Status = res.data
		configurationToggling.value = false;
	})
}

// Configuration Summary =====================================
const configurationSummary = computed(() => {
	return {
		connectedPeers: configurationPeers.value.filter(x => x.status === "running").length,
		totalUsage: configurationPeers.value.length > 0 ?
			configurationPeers.value.filter(x => !x.restricted)
				.map(x => x.total_data + x.cumu_data).reduce((a, b) => a + b, 0).toFixed(4) : 0,
		totalReceive: configurationPeers.value.length > 0 ?
			configurationPeers.value.filter(x => !x.restricted)
				.map(x => x.total_receive + x.cumu_receive).reduce((a, b) => a + b, 0).toFixed(4) : 0,
		totalSent: configurationPeers.value.length > 0 ?
			configurationPeers.value.filter(x => !x.restricted)
				.map(x => x.total_sent + x.cumu_sent).reduce((a, b) => a + b, 0).toFixed(4) : 0
	}
})

const showPeersCount = ref(10)
const showPeersThreshold = 20;
const searchPeers = computed(() => {
	const result = wireguardConfigurationStore.searchString ?
		configurationPeers.value.filter(x => {
			return x.name.includes(wireguardConfigurationStore.searchString) ||
				x.id.includes(wireguardConfigurationStore.searchString) ||
				x.allowed_ip.includes(wireguardConfigurationStore.searchString)
		}) : configurationPeers.value;

	if (dashboardStore.Configuration.Server.dashboard_sort === "restricted"){
		return result.sort((a, b) => {
			if ( a[dashboardStore.Configuration.Server.dashboard_sort]
				< b[dashboardStore.Configuration.Server.dashboard_sort] ){
				return 1;
			}
			if ( a[dashboardStore.Configuration.Server.dashboard_sort]
				> b[dashboardStore.Configuration.Server.dashboard_sort]){
				return -1;
			}
			return 0;
		}).slice(0, showPeersCount.value);
	}

	return result.sort((a, b) => {
		if ( a[dashboardStore.Configuration.Server.dashboard_sort]
			< b[dashboardStore.Configuration.Server.dashboard_sort] ){
			return -1;
		}
		if ( a[dashboardStore.Configuration.Server.dashboard_sort]
			> b[dashboardStore.Configuration.Server.dashboard_sort]){
			return 1;
		}
		return 0;
	}).slice(0, showPeersCount.value)
})

// Add watch for peers to update rate limits when peers change
watch(() => configurationPeers.value, async (newPeers) => {
	if (configurationInfo.value?.Name && newPeers?.length) {
		// Fetch rate limits for all peers (ignore errors for missing peers)
		for (const peer of newPeers) {
			try {
				await wireguardConfigurationStore.fetchPeerRateLimit(
					configurationInfo.value.Name,
					peer.id
				);
			} catch (error) {
				// Silently handle missing peers - this is expected when peers are deleted
				if (!error.message?.includes('not found')) {
					console.warn('Failed to fetch rate limit for peer:', peer.id, error);
				}
			}
		}
	}
})
</script>

<template>
<div class="container-fluid" >
	<div class="d-flex align-items-sm-center flex-column flex-sm-row gap-3">
		<div>
			<div class="d-flex align-items-center gap-3">
				<h1 class="mb-0 display-4"><samp>{{configurationInfo.Name}}</samp></h1>
			</div>
			<br></br>
			<div class="text-muted d-flex align-items-center gap-2">
			<h5 class="mb-0">
				<ProtocolBadge :protocol="configurationInfo.Protocol" :hasTor="configurationInfo.HasTor"></ProtocolBadge>
			</h5>
			</div>
			
		</div>
		<div class="ms-sm-auto d-flex gap-2 flex-column">
			<div class="card rounded-3 bg-transparent ">
				<div class="card-body py-2 d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Status"></LocaleText>
					</small>
					<div class="dot ms-2" :class="{active: configurationInfo.Status}"></div>
					<div class="form-check form-switch mb-0 ms-auto pe-0 me-0">
						<label class="form-check-label" style="cursor: pointer" :for="'switch' + configurationInfo.id">
							<LocaleText t="On" v-if="configurationInfo.Status && !configurationToggling"></LocaleText>
							<LocaleText t="Off" v-else-if="!configurationInfo.Status && !configurationToggling"></LocaleText>
							<span v-if="configurationToggling"
							      class="spinner-border spinner-border-sm ms-2" aria-hidden="true">
							</span>
						</label>
						<input class="form-check-input"
						       style="cursor: pointer"
						       :disabled="configurationToggling"
						       type="checkbox" role="switch" :id="'switch' + configurationInfo.id"
						       @change="toggleConfiguration()"
						       v-model="configurationInfo.Status">
					</div>

				</div>
			</div>
			<!-- Shared TLS Pipe Server Status (Clickable) -->
			<div class="card rounded-3 bg-transparent tls-pipe-card" 
			     role="button"
			     @click="configurationModals.tlsPipeManager.modalOpen = true"
			     title="Click to manage TLS Pipe">
				<div class="card-body py-2 d-flex align-items-center gap-2">
					<small class="text-muted d-flex align-items-center gap-1">
						<i class="bi bi-shield-lock-fill"></i>
						<LocaleText t="TLS Pipe"></LocaleText>
						<span class="badge bg-secondary-subtle text-secondary-emphasis ms-1" 
						      style="font-size: 0.6rem;" 
						      title="Single shared server on port 443">
							Shared
						</span>
					</small>
					<div class="dot ms-2" :class="{active: tlsPipeStatus.running}"></div>
					<small v-if="tlsPipeStatus.loading" class="text-muted">
						<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
					</small>
					<small v-else-if="tlsPipeStatus.running" class="text-success">
						:{{ tlsPipeStatus.port }}
						<span class="text-muted ms-1" v-if="tlsPipeStatus.routeCount > 1">
							({{ tlsPipeStatus.routeCount }} configs)
						</span>
					</small>
					<small v-else class="text-muted">
						<LocaleText t="Off"></LocaleText>
					</small>
					<span v-if="tlsPipePeersCount > 0" 
					      class="badge bg-info-subtle text-info-emphasis ms-auto"
					      style="font-size: 0.7rem;">
						{{ tlsPipePeersCount }} <LocaleText t="peer"></LocaleText><span v-if="tlsPipePeersCount > 1">s</span>
					</span>
					<i class="bi bi-gear-fill text-muted ms-2" style="font-size: 0.8rem;"></i>
				</div>
			</div>
			<div class="d-flex gap-2 flex-wrap">
				<a
					role="button"
					@click="configurationModals.peerNew.modalOpen = true"
					class="titleBtn py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle ">
					<i class="bi bi-plus-circle me-2"></i>
					<LocaleText t="Peer"></LocaleText>
				</a>
				<button class="titleBtn py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle "
				        @click="configurationModals.editConfiguration.modalOpen = true"
				        type="button" aria-expanded="false">
					<i class="bi bi-gear-fill me-2"></i>
					<LocaleText t="Configuration Settings"></LocaleText>
				</button>
				<button class="titleBtn py-2 text-decoration-none btn text-success-emphasis bg-success-subtle rounded-3 border-1 border-success-subtle"
				        @click="configurationModals.tlsPipeManager.modalOpen = true"
				        type="button"
				        title="Manage TLS Pipe for censorship-resistant tunneling">
					<i class="bi bi-shield-lock-fill me-2"></i>
					<LocaleText t="TLS Pipe"></LocaleText>
				</button>
			</div>
		</div>
	</div>
	<hr>
	<div class="row mt-3 gy-2 gx-2 mb-2">
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent  h-100">
				<div class="card-body py-2 d-flex flex-column justify-content-center">
					<p class="mb-0 text-muted"><small>
						<LocaleText t="Address"></LocaleText>
					</small></p>
					{{configurationInfo.Address}}
				</div>
			</div>
		</div>
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent h-100">
				<div class="card-body py-2 d-flex flex-column justify-content-center">
					<p class="mb-0 text-muted"><small>
						<LocaleText t="Listen Port"></LocaleText>
					</small></p>
					{{configurationInfo.ListenPort}}
				</div>
			</div>
		</div>
		<div style="word-break: break-all" class="col-12 col-lg-6">
			<div class="card rounded-3 bg-transparent h-100">
				<div class="card-body py-2 d-flex flex-column justify-content-center">
					<p class="mb-0 text-muted"><small>
						<LocaleText t="Public Key"></LocaleText>
					</small></p>
					<samp>{{configurationInfo.PublicKey}}</samp>
				</div>
			</div>
		</div>
	</div>
	<div class="row gx-2 gy-2 mb-2">
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent  h-100">
				<div class="card-body d-flex">
					<div>
						<p class="mb-0 text-muted"><small>
							<LocaleText t="Connected Peers"></LocaleText>
						</small></p>
						<strong class="h4">
							{{configurationSummary.connectedPeers}} / {{configurationPeers.length}}
						</strong>
					</div>
					<i class="bi bi-ethernet ms-auto h2 text-muted"></i>
				</div>
			</div>
		</div>
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent  h-100">
				<div class="card-body d-flex">
					<div>
						<p class="mb-0 text-muted"><small>
							<LocaleText t="Total Usage"></LocaleText>
						</small></p>
						<strong class="h4">{{configurationSummary.totalUsage}} GB</strong>
					</div>
					<i class="bi bi-arrow-down-up ms-auto h2 text-muted"></i>
				</div>
			</div>
		</div>
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent  h-100">
				<div class="card-body d-flex">
					<div>
						<p class="mb-0 text-muted"><small>
							<LocaleText t="Total Received"></LocaleText>
						</small></p>
						<strong class="h4 text-primary">{{configurationSummary.totalReceive}} GB</strong>
					</div>
					<i class="bi bi-arrow-down ms-auto h2 text-muted"></i>
				</div>
			</div>
		</div>
		<div class="col-12 col-lg-3">
			<div class="card rounded-3 bg-transparent  h-100">
				<div class="card-body d-flex">
					<div>
						<p class="mb-0 text-muted"><small>
							<LocaleText t="Total Sent"></LocaleText>
						</small></p>
						<strong class="h4 text-success">{{configurationSummary.totalSent}} GB</strong>
					</div>
					<i class="bi bi-arrow-up ms-auto h2 text-muted"></i>
				</div>
			</div>
		</div>
	</div>
	<PeerDataUsageCharts
		:configurationPeers="configurationPeers"
		:configurationInfo="configurationInfo"
	></PeerDataUsageCharts>
	<hr>
	<div style="margin-bottom: 80px">
		<PeerSearch
			v-if="configurationPeers.length > 0"
			@search="peerSearchBar = true"
			@jobsAll="configurationModals.peerScheduleJobsAll.modalOpen = true"
			@jobLogs="configurationModals.peerScheduleJobsLogs.modalOpen = true"
			@editConfiguration="configurationModals.editConfiguration.modalOpen = true"
			@selectPeers="configurationModals.selectPeers.modalOpen = true"
			@backupRestore="configurationModals.backupRestore.modalOpen = true"
			@deleteConfiguration="configurationModals.deleteConfiguration.modalOpen = true"
			:configuration="configurationInfo">
		</PeerSearch>
		<TransitionGroup name="peerList" tag="div" class="row gx-2 gy-2 z-0 position-relative">
			<div class="col-12 col-lg-6 col-xl-4"
			     :key="peer.id"
			     v-for="peer in searchPeers">
				<Peer :Peer="peer"
				      @share="configurationModals.peerShare.modalOpen = true; configurationModalSelectedPeer = peer"
				      @refresh="fetchPeerList()"
				      @jobs="configurationModals.peerScheduleJobs.modalOpen = true; configurationModalSelectedPeer = peer"
				      @setting="configurationModals.peerSetting.modalOpen = true; configurationModalSelectedPeer = peer"
				      @rateLimit="configurationModals.peerRateLimit.modalOpen = true; configurationModalSelectedPeer = peer"
				      @qrcode="configurationModals.peerQRCode.modalOpen = true; configurationModalSelectedPeer = peer"
				      @configurationFile="configurationModals.peerConfigurationFile.modalOpen = true; configurationModalSelectedPeer = peer">
				</Peer>
			</div>
		</TransitionGroup>
		
	</div>
	<Transition name="slideUp">
		<PeerSearchBar @close="peerSearchBar = false" v-if="peerSearchBar"></PeerSearchBar>
	</Transition>
	<PeerListModals 
		:configurationModals="configurationModals"
		:configurationModalSelectedPeer="configurationModalSelectedPeer"
		:configurationInfo="configurationInfo"
		@refresh="fetchPeerList()"
	></PeerListModals>
	<TransitionGroup name="zoom">
		<Suspense key="PeerAddModal">
			<PeerAddModal
				v-if="configurationModals.peerNew.modalOpen"
				@close="configurationModals.peerNew.modalOpen = false"
				@addedPeers="configurationModals.peerNew.modalOpen = false; fetchPeerList()"
			></PeerAddModal>
		</Suspense>
		<PeerJobsAllModal
			key="PeerJobsAllModal"
			v-if="configurationModals.peerScheduleJobsAll.modalOpen"
			@refresh="fetchPeerList()"
			@allLogs="configurationModals.peerScheduleJobsLogs.modalOpen = true"
			@close="configurationModals.peerScheduleJobsAll.modalOpen = false"
			:configurationPeers="configurationPeers"
		>
		</PeerJobsAllModal>
		<PeerJobsLogsModal
			key="PeerJobsLogsModal"
			v-if="configurationModals.peerScheduleJobsLogs.modalOpen" 
			@close="configurationModals.peerScheduleJobsLogs.modalOpen = false"
			:configurationInfo="configurationInfo">
		</PeerJobsLogsModal>
		<EditConfigurationModal
			@editRaw="configurationModals.editRawConfigurationFile.modalOpen = true"
			@backupRestore="configurationModals.backupRestore.modalOpen = true"
			@deleteConfiguration="configurationModals.deleteConfiguration.modalOpen = true"
			@close="configurationModals.editConfiguration.modalOpen = false"
			@dataChanged="(d) => configurationInfo = d"
			:configurationInfo="configurationInfo"
			v-if="configurationModals.editConfiguration.modalOpen"
		></EditConfigurationModal>
		<SelectPeersModal
			@refresh="fetchPeerList()"
			v-if="configurationModals.selectPeers.modalOpen"
			:configurationPeers="configurationPeers"
			@close="configurationModals.selectPeers.modalOpen = false"
		></SelectPeersModal>
		<DeleteConfiguration
			v-if="configurationModals.deleteConfiguration.modalOpen"
			@backup="configurationModals.backupRestore.modalOpen = true"
			@close="configurationModals.deleteConfiguration.modalOpen = false"
		></DeleteConfiguration>
		<EditRawConfigurationFile
			v-if="configurationModals.editRawConfigurationFile.modalOpen"
			@close="configurationModals.editRawConfigurationFile.modalOpen = false"
		></EditRawConfigurationFile>
		<ConfigurationBackupRestore
			v-if="configurationModals.backupRestore.modalOpen"
			@close="configurationModals.backupRestore.modalOpen = false"
			@refreshPeersList="fetchPeerList()"
		></ConfigurationBackupRestore>
		<TlsPipeManager
			key="TlsPipeManager"
			v-if="configurationModals.tlsPipeManager.modalOpen"
			@close="configurationModals.tlsPipeManager.modalOpen = false"
			@refresh="fetchPeerList(); fetchTlsPipeStatus()"
			:configurationInfo="configurationInfo"
		></TlsPipeManager>
	</TransitionGroup>
	<PeerIntersectionObserver
		:showPeersCount="showPeersCount"
		:peerListLength="searchPeers.length"
		@loadMore="showPeersCount += showPeersThreshold"></PeerIntersectionObserver>
</div>
</template>

<style scoped>
.peerNav .nav-link{
	&.active{
		background-color: #efefef;
	}
}

th, td{
	background-color: transparent !important;
}

@media screen and (max-width: 576px) {
	.titleBtn{
		flex-basis: 100%;
	}
}

.tls-pipe-card {
	cursor: pointer;
	transition: all 0.2s ease;
}

.tls-pipe-card:hover {
	background-color: rgba(var(--bs-success-rgb), 0.1) !important;
	border-color: var(--bs-success) !important;
}
</style>