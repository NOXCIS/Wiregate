<script>
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import ConfigurationCard from "@/components/configurationListComponents/configurationCard.vue";
import LocaleText from "@/components/text/localeText.vue";
import SystemStatus from "@/components/systemStatusComponents/systemStatusWidget.vue";
import {GetLocale} from "@/utilities/locale.js";

export default {
	name: "configurationList",
	components: {SystemStatus, LocaleText, ConfigurationCard},
	setup(){
		const wireguardConfigurationsStore = WireguardConfigurationsStore();
		return {wireguardConfigurationsStore}
	},
	data(){
		return {
			configurationLoaded: false,
			showProtocolBadges: true,
			sort: {
				Name: GetLocale("Name"),
				Status: GetLocale("Status"),
				'DataUsage.Total': GetLocale("Total Usage")
			},
			currentSort: {
				key: "Name",
				order: "asc"
			},
			searchKey: "",
			protocolFilter: null
		}
	},
	async mounted() {
		if (!window.localStorage.getItem('ConfigurationListSort')){
			window.localStorage.setItem('ConfigurationListSort', JSON.stringify(this.currentSort))
		}else{
			this.currentSort = JSON.parse(window.localStorage.getItem('ConfigurationListSort'))
		}
		
		// Load protocol badge visibility preference
		if (window.localStorage.getItem('ConfigurationListShowProtocolBadges') !== null){
			this.showProtocolBadges = JSON.parse(window.localStorage.getItem('ConfigurationListShowProtocolBadges'))
		}
		
		await this.wireguardConfigurationsStore.getConfigurations();
		this.configurationLoaded = true;
		
		// Complete the loading bar when configuration list is loaded
		this.completeLoadingBar();
		
		// Trigger update check after configurations are loaded
		this.triggerUpdateCheck();
		
		const dashboardStore = DashboardConfigurationStore();
		this.wireguardConfigurationsStore.ConfigurationListInterval = setInterval(() => {
			this.wireguardConfigurationsStore.getConfigurations()
		}, 10000)
		// Register interval with global tracker
		if (this.wireguardConfigurationsStore.ConfigurationListInterval) {
			dashboardStore.registerInterval(this.wireguardConfigurationsStore.ConfigurationListInterval);
		}
	},
	beforeUnmount() {
		const dashboardStore = DashboardConfigurationStore();
		if (this.wireguardConfigurationsStore.ConfigurationListInterval) {
			dashboardStore.unregisterInterval(this.wireguardConfigurationsStore.ConfigurationListInterval);
			clearInterval(this.wireguardConfigurationsStore.ConfigurationListInterval);
		}
	},
	computed: {
		configurations(){
			let filteredConfigurations = [...this.wireguardConfigurationsStore.Configurations]
				.filter(x => x.Name.includes(this.searchKey) || x.PublicKey.includes(this.searchKey) || !this.searchKey);
			
			// Apply protocol filter
			if (this.protocolFilter) {
				if (this.protocolFilter === 'tor') {
					filteredConfigurations = filteredConfigurations.filter(configuration => configuration.HasTor);
				} else {
					filteredConfigurations = filteredConfigurations.filter(configuration => configuration.Protocol === this.protocolFilter);
				}
			}
			
			return filteredConfigurations.sort((a, b) => {
				if (this.currentSort.order === 'desc') {
					return this.dotNotation(a, this.currentSort.key) < this.dotNotation(b, this.currentSort.key) ? 
						1 : this.dotNotation(a, this.currentSort.key) > this.dotNotation(b, this.currentSort.key) ? -1 : 0;
				} else {
					return this.dotNotation(a, this.currentSort.key) > this.dotNotation(b, this.currentSort.key) ? 
						1 : this.dotNotation(a, this.currentSort.key) < this.dotNotation(b, this.currentSort.key) ? -1 : 0;
				}
			})
		}
	},
	methods: {
		dotNotation(object, dotNotation){
			return dotNotation.split('.').reduce((o, key) => o && o[key], object)
		},
		updateSort(key){
			if (this.currentSort.key === key){
				if (this.currentSort.order === 'asc') this.currentSort.order = 'desc'
				else this.currentSort.order = 'asc'
			}else{
				this.currentSort.key = key
			}
			window.localStorage.setItem('ConfigurationListSort', JSON.stringify(this.currentSort))
		},
		completeLoadingBar() {
			// Small delay to ensure smooth transition
			setTimeout(() => {
				const loadingBar = document.querySelector(".loadingBar");
				if (loadingBar) {
					loadingBar.classList.remove("loading");
					loadingBar.classList.add("loadingDone");
				}
			}, 100);
		},
		triggerUpdateCheck() {
			// Trigger update check after configurations are loaded
			// This ensures the update check doesn't interfere with critical loading
			setTimeout(() => {
				// Dispatch a custom event to trigger update check
				window.dispatchEvent(new CustomEvent('triggerUpdateCheck'));
			}, 2000); // Wait 2 seconds after configurations are loaded
		},
		toggleProtocolBadges() {
			this.showProtocolBadges = !this.showProtocolBadges;
			window.localStorage.setItem('ConfigurationListShowProtocolBadges', JSON.stringify(this.showProtocolBadges));
		},
		filterByProtocol(protocol) {
			if (this.protocolFilter === protocol) {
				// If clicking the same filter, clear it
				this.protocolFilter = null;
			} else {
				this.protocolFilter = protocol;
			}
		}
	}
}
</script>

<template>
	<div class="mt-md-5 mt-3">
		<div class="container-md">
			<SystemStatus></SystemStatus>
			<div class="d-flex mb-4 configurationListTitle align-items-md-center gap-3 flex-column flex-md-row">
				<h2 class="text-body d-flex mb-0">
					<LocaleText t="Configurations"></LocaleText>
				</h2>
				<RouterLink to="/new_configuration"
				            class="ms-md-auto py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle">
					<i class="bi bi-plus-circle me-2"></i><LocaleText t="Configuration"></LocaleText>
				</RouterLink>
				<RouterLink to="/restore_configuration"
				            class="py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle">
					<i class="bi bi-clock-history me-2"></i><LocaleText t="Restore"></LocaleText>
				</RouterLink>
				
			</div>
			<div class="text-body filter mb-3 d-flex gap-2 flex-column flex-md-row" v-if="this.configurationLoaded">
				<div class="d-flex align-items-center gap-2 gap-md-3 flex-wrap">
					<small class="text-muted flex-shrink-0">
						<LocaleText t="Sort By"></LocaleText>
					</small>
					<a role="button" 
					   @click="updateSort(sv)"
					   :class="{'sort-btn-active': this.currentSort.key === sv, 'sort-btn-inactive': this.currentSort.key !== sv}"
					   class="px-2 py-1 rounded-3" v-for="(s, sv) in this.sort">
						<small>
							<i class="bi me-2" 
							   :class="[this.currentSort.order === 'asc' ? 'bi-sort-up' : 'bi-sort-down']" 
							   v-if="this.currentSort.key === sv"></i>{{s}}
						</small>
					</a>
					<a role="button" 
					   @click="toggleProtocolBadges"
					   :class="{'visibility-btn-active': showProtocolBadges, 'visibility-btn-inactive': !showProtocolBadges}"
					   class="px-2 py-1 rounded-3"
					   :title="showProtocolBadges ? 'Hide Protocol Badges' : 'Show Protocol Badges'">
						<small>
							<i class="bi" :class="showProtocolBadges ? 'bi-eye' : 'bi-eye-slash'"></i>
						</small>
					</a>
					<a role="button" 
					   @click="filterByProtocol('wg')"
					   :class="{'protocol-btn-active': protocolFilter === 'wg', 'protocol-btn-inactive': protocolFilter !== 'wg'}"
					   class="px-2 py-1 rounded-3">
						<small>WG</small>
					</a>
					<a role="button" 
					   @click="filterByProtocol('awg')"
					   :class="{'protocol-btn-active': protocolFilter === 'awg', 'protocol-btn-inactive': protocolFilter !== 'awg'}"
					   class="px-2 py-1 rounded-3">
						<small>AWG</small>
					</a>
					<a role="button" 
					   @click="filterByProtocol('tor')"
					   :class="{'protocol-btn-active': protocolFilter === 'tor', 'protocol-btn-inactive': protocolFilter !== 'tor'}"
					   class="px-2 py-1 rounded-3">
						<small>Tor</small>
					</a>
					<div class="d-flex align-items-center flex-grow-1 flex-md-grow-0">
						<label for="configurationSearch" class="text-muted">
							<i class="bi bi-search me-2"></i>
						</label>
						<input class="form-control form-control-sm rounded-3" 
						       v-model="this.searchKey"
						       id="configurationSearch"
						       style="min-width: 150px;">
					</div>
				</div>
			</div>
			
			<TransitionGroup name="list" tag="div" class="d-flex flex-column gap-3 mb-4">
				<!-- Loading skeleton -->
				<div v-if="!this.configurationLoaded" class="d-flex flex-column gap-3">
					<div v-for="n in 3" :key="'skeleton-' + n" class="card skeleton-card">
						<div class="card-body">
							<div class="d-flex justify-content-between align-items-start mb-3">
								<div class="skeleton-line" style="width: 200px; height: 24px;"></div>
								<div class="skeleton-line" style="width: 80px; height: 32px;"></div>
							</div>
							<div class="skeleton-line mb-2" style="width: 100%; height: 16px;"></div>
							<div class="skeleton-line mb-2" style="width: 80%; height: 16px;"></div>
							<div class="d-flex gap-2">
								<div class="skeleton-line" style="width: 100px; height: 20px;"></div>
								<div class="skeleton-line" style="width: 100px; height: 20px;"></div>
								<div class="skeleton-line" style="width: 100px; height: 20px;"></div>
							</div>
						</div>
					</div>
				</div>
				
				<p class="text-muted" 
				   key="noConfiguration"
				   v-else-if="this.configurationLoaded && this.wireguardConfigurationsStore.Configurations.length === 0">
					<LocaleText t="You don't have any Configurations yet. Please check the configuration folder or change it in Settings. By default the folder is /etc/wireguard."></LocaleText>
				</p>
				<ConfigurationCard v-for="(c, index) in configurations"
				                   v-else-if="this.configurationLoaded"
				                   :key="c.Name" :c="c" :showProtocolBadges="showProtocolBadges"></ConfigurationCard>
			</TransitionGroup>
			
		</div>
	</div>
	
</template>

<style scoped>
.filter a{
	text-decoration: none;
	flex-shrink: 0; /* Prevent buttons from shrinking */
	white-space: nowrap; /* Keep button text on one line */
}

.filter {
	overflow-x: auto;
	-webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
}

.filter::-webkit-scrollbar {
	height: 4px;
}

.filter::-webkit-scrollbar-track {
	background: transparent;
}

.filter::-webkit-scrollbar-thumb {
	background: rgba(255, 255, 255, 0.3);
	border-radius: 2px;
}

.filter::-webkit-scrollbar-thumb:hover {
	background: rgba(255, 255, 255, 0.5);
}

/* Ensure the sort/filter bar doesn't overflow on mobile */
@media (max-width: 767.98px) {
	.filter > div {
		min-width: min-content; /* Allow horizontal scroll if content is too wide */
	}
}

.skeleton-card {
	background: rgba(255, 255, 255, 0.1);
	border: 1px solid rgba(255, 255, 255, 0.1);
	animation: skeleton-pulse 2s ease-in-out infinite;
}

.skeleton-line {
	background: rgba(255, 255, 255, 0.1);
	border-radius: 4px;
	animation: skeleton-pulse 2s ease-in-out infinite;
}

@keyframes skeleton-pulse {
	0%, 100% {
		opacity: 0.4;
	}
	50% {
		opacity: 0.8;
	}
}

[data-bs-theme="dark"] .skeleton-card {
	background: rgba(255, 255, 255, 0.05);
	border: 1px solid rgba(255, 255, 255, 0.05);
}

[data-bs-theme="dark"] .skeleton-line {
	background: rgba(255, 255, 255, 0.05);
}

/* Sort button styling - inverted theme like settings */
.sort-btn-inactive {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
	transition: all 0.2s ease-in-out;
}

.sort-btn-inactive:hover {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

.sort-btn-active {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

/* Light theme styles */
[data-bs-theme="light"] .sort-btn-inactive {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

[data-bs-theme="light"] .sort-btn-inactive:hover {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}

[data-bs-theme="light"] .sort-btn-active {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}

/* Protocol filter button styling - same inverted theme as sort buttons */
.protocol-btn-inactive {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
	transition: all 0.2s ease-in-out;
}

.protocol-btn-inactive:hover {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

.protocol-btn-active {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

/* Light theme styles for protocol buttons */
[data-bs-theme="light"] .protocol-btn-inactive {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

[data-bs-theme="light"] .protocol-btn-inactive:hover {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}

[data-bs-theme="light"] .protocol-btn-active {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}

/* Visibility toggle button styling - same inverted theme as other buttons */
.visibility-btn-inactive {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
	transition: all 0.2s ease-in-out;
}

.visibility-btn-inactive:hover {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

.visibility-btn-active {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

/* Light theme styles for visibility button */
[data-bs-theme="light"] .visibility-btn-inactive {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
}

[data-bs-theme="light"] .visibility-btn-inactive:hover {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}

[data-bs-theme="light"] .visibility-btn-active {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: #ffffff !important;
}
</style>