<script>
import {WiregateDashboardStore} from "@/stores/WiregateDashboardStore.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";

export default {
	name: "navbar",
	components: {LocaleText},
	setup(){
		const wireguardConfigurationsStore = WireguardConfigurationsStore();
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {wireguardConfigurationsStore, dashboardConfigurationStore}
	},
	data(){
		return {
			updateAvailable: false,
			updateMessage: "Checking for update...",
			updateUrl: "",
			changelogItems: [],
			showChangelog: false,
			changelogLoading: false,
			changelogVersion: null,
		}
	},
	computed: {
		getActiveCrossServer(){
			if (this.dashboardConfigurationStore.ActiveServerConfiguration){
				return new URL(this.dashboardConfigurationStore.CrossServerConfiguration.ServerList
					[this.dashboardConfigurationStore.ActiveServerConfiguration].host)
			}
			return undefined
		}
	},
	mounted() {
		// Don't run update check on mount to prevent blocking
		// The update check will be triggered after configurations are loaded
		this.updateMessage = "Update check will run after configurations load";
		
		// Listen for the custom event to trigger update check
		this.updateCheckHandler = () => {
			this.checkForUpdates();
		};
		window.addEventListener('triggerUpdateCheck', this.updateCheckHandler);
		
		// Always fetch changelog for current version on mount
		// Use a longer delay to ensure the store is fully loaded
		setTimeout(() => {
			this.fetchCurrentVersionChangelog();
		}, 2000);
	},
	beforeUnmount() {
		// Clean up event listener
		if (this.updateCheckHandler) {
			window.removeEventListener('triggerUpdateCheck', this.updateCheckHandler);
		}
	},
	methods: {
		checkForUpdates() {
			// Make this completely non-blocking by not awaiting anything
			// Add a timeout to prevent hanging
			const timeoutId = setTimeout(() => {
				this.updateMessage = "Update check timed out";
			}, 10000); // Increased timeout to 10 seconds
			
			fetchGet("/api/getDashboardUpdate", {}, (res) => {
				clearTimeout(timeoutId);
				console.log("Update check response:", res);
				if (res.status){
					if (res.data){
						this.updateAvailable = true
						if (typeof res.data === 'object' && res.data.url) {
							this.updateUrl = res.data.url
							this.changelogItems = res.data.changelog || []
							console.log("Changelog items received:", this.changelogItems);
							console.log("Changelog items count:", this.changelogItems.length);
							console.log("Changelog items type:", typeof this.changelogItems);
						} else {
							this.updateUrl = res.data
							console.log("No changelog data in response, using simple URL");
						}
						console.log("Update URL:", this.updateUrl);
					} else {
						// No update available, preserve existing changelog data
						this.updateAvailable = false
						console.log("No update available, preserving existing changelog data");
						// Don't clear changelog items here - keep what we have
					}
					this.updateMessage = res.message
					console.log("Update message:", this.updateMessage);
				}else{
					this.updateMessage = res.message || GetLocale("Failed to check available update")
					console.log(`Update check failed: ${res.message}`)
					
					// If update check was started, retry after a delay
					if (res.message && res.message.includes("Update check started")) {
						setTimeout(() => {
							this.checkForUpdates();
						}, 3000); // Retry after 3 seconds
					}
				}
			}).catch(error => {
				clearTimeout(timeoutId);
				console.warn("Update check failed:", error);
				this.updateMessage = GetLocale("Update check failed");
			});
		},
		refreshUpdateCheck() {
			this.updateMessage = "Checking for updates...";
			// Store current changelog items before update check
			const currentChangelogItems = [...this.changelogItems];
			const currentChangelogVersion = this.changelogVersion;
			this.checkForUpdates();
			// Restore changelog items if update check doesn't provide new ones
			setTimeout(() => {
				if (this.changelogItems.length === 0 && currentChangelogItems.length > 0) {
					this.changelogItems = currentChangelogItems;
					this.changelogVersion = currentChangelogVersion;
					console.log("Restored changelog data after update check");
				}
			}, 2000);
		},
		toggleChangelog() {
			console.log("Toggling changelog. Current state:", this.showChangelog);
			console.log("Current changelog items:", this.changelogItems);
			console.log("Changelog items length:", this.changelogItems.length);
			console.log("Changelog items type:", typeof this.changelogItems);
			this.showChangelog = !this.showChangelog;
		},
		fetchCurrentVersionChangelog() {
			// Fetch changelog for latest version using the existing API
			console.log("Fetching changelog for latest version using API");
			this.changelogLoading = true;
			
			// Add a small delay to ensure the store is fully loaded
			setTimeout(() => {
				// Use the existing update API which already determines the latest Docker tag
				this.fetchLatestVersionChangelogFromAPI();
			}, 1000);
		},
		fetchLatestVersionChangelogFromAPI() {
			// Use the existing update API to get the latest version's changelog
			console.log("Fetching latest version changelog from update API");
			this.changelogLoading = true;
			
			fetchGet("/api/getDashboardUpdate", {}, (res) => {
				console.log("Update API response for changelog:", res);
				this.changelogLoading = false;
				
				if (res.status && res.data) {
					// If there's an update available, use that changelog
					if (typeof res.data === 'object' && res.data.changelog && res.data.changelog.length > 0) {
						this.changelogItems = res.data.changelog || [];
						this.changelogVersion = res.data.version || "latest";
						console.log("Loaded latest changelog from update API:", this.changelogItems.length, "items");
					} else {
						// No changelog data from API, fall back to parsing the changelog file
						console.log("No changelog data from API, falling back to GitHub parsing");
						this.loadLatestVersionChangelog();
					}
				} else {
					// API failed, fall back to parsing the changelog file
					console.log("API failed, falling back to GitHub parsing");
					this.loadLatestVersionChangelog();
				}
			}).catch(error => {
				console.warn("Update API failed, falling back to changelog parsing:", error);
				this.changelogLoading = false;
				this.loadLatestVersionChangelog();
			});
		},
		loadLatestVersionChangelog() {
			// Fallback: Fetch the latest version's changelog from GitHub directly
			console.log("Loading latest version changelog from GitHub (fallback)");
			this.changelogLoading = true;
			
			// Try to fetch directly from GitHub
			fetch('https://raw.githubusercontent.com/NOXCIS/Wiregate/refs/heads/main/Docs/CHANGELOG.md')
				.then(response => response.text())
				.then(text => {
					const { changelogItems, version } = this.parseLatestChangelogFromText(text);
					this.changelogItems = changelogItems;
					this.changelogVersion = version;
					this.changelogLoading = false;
					console.log("Loaded latest changelog from GitHub:", changelogItems.length, "items for version", version);
				})
				.catch(error => {
					console.warn("Failed to fetch changelog from GitHub:", error);
					this.changelogItems = [];
					this.changelogLoading = false;
				});
		},
		loadLocalChangelogForCurrentVersion() {
			// Fallback: Try to fetch from GitHub directly if API fails
			const currentVersion = this.dashboardConfigurationStore.Configuration.Server.version;
			console.log("Loading changelog from GitHub for version:", currentVersion);
			this.changelogLoading = true;
			
			// Try to fetch directly from GitHub as fallback
			fetch('https://raw.githubusercontent.com/NOXCIS/Wiregate/refs/heads/main/Docs/CHANGELOG.md')
				.then(response => response.text())
				.then(text => {
					const changelogItems = this.parseChangelogFromText(text, currentVersion);
					this.changelogItems = changelogItems;
					this.changelogLoading = false;
					console.log("Loaded changelog from GitHub:", changelogItems.length, "items");
				})
				.catch(error => {
					console.warn("Failed to fetch changelog from GitHub:", error);
					this.changelogItems = [];
					this.changelogLoading = false;
				});
		},
		parseChangelogFromText(text, version) {
			// Parse changelog text to extract items for specific version
			const changelogMap = {};
			const content = text.trim().split('\n');
			let currentVersion = null;
			
			for (const line of content) {
				const trimmedLine = line.trim();
				if (!trimmedLine) continue;
				
				// Check if this line defines a version (starts with ## or ends with :)
				if (trimmedLine.startsWith('## ')) {
					currentVersion = trimmedLine.replace('## ', '').trim();
					changelogMap[currentVersion] = [];
				} else if (trimmedLine.endsWith(':')) {
					currentVersion = trimmedLine.replace(':', '').trim();
					changelogMap[currentVersion] = [];
				} else if (trimmedLine.startsWith('-') && currentVersion) {
					const item = trimmedLine.replace('-', '', 1).trim();
					changelogMap[currentVersion].push(item);
				}
			}
			
			// If exact version not found, try to find the latest version
			if (changelogMap[version] && changelogMap[version].length > 0) {
				return changelogMap[version];
			}
			
			// Fallback: return the latest available version's changelog
			const versions = Object.keys(changelogMap);
			if (versions.length > 0) {
				const latestVersion = versions[0]; // Assuming first version is latest
				console.log(`Version ${version} not found, showing latest available: ${latestVersion}`);
				this.changelogVersion = latestVersion;
				return changelogMap[latestVersion] || [];
			}
			
			return [];
		},
		parseLatestChangelogFromText(text) {
			// Parse changelog text to extract the latest version's changelog
			const changelogMap = {};
			const content = text.trim().split('\n');
			let currentVersion = null;
			
			for (const line of content) {
				const trimmedLine = line.trim();
				if (!trimmedLine) continue;
				
				// Check if this line defines a version (starts with ## or ends with :)
				if (trimmedLine.startsWith('## ')) {
					currentVersion = trimmedLine.replace('## ', '').trim();
					changelogMap[currentVersion] = [];
				} else if (trimmedLine.endsWith(':')) {
					currentVersion = trimmedLine.replace(':', '').trim();
					changelogMap[currentVersion] = [];
				} else if (trimmedLine.startsWith('-') && currentVersion) {
					const item = trimmedLine.replace('-', '', 1).trim();
					changelogMap[currentVersion].push(item);
				}
			}
			
			// Return the first (latest) version's changelog
			const versions = Object.keys(changelogMap);
			if (versions.length > 0) {
				const latestVersion = versions[0]; // First version is latest
				const changelogItems = changelogMap[latestVersion] || [];
				console.log(`Found latest version: ${latestVersion} with ${changelogItems.length} items`);
				return { changelogItems, version: latestVersion };
			}
			
			return { changelogItems: [], version: null };
		}
	}
}
</script>

<template>
	<div class="col-12 col-lg-2 d-md-block p-2 navbar-container"
	     :class="{active: this.dashboardConfigurationStore.ShowNavBar}"
	     :data-bs-theme="dashboardConfigurationStore.Configuration.Server.dashboard_theme"
	>
		<nav id="sidebarMenu" class=" bg-body-tertiary sidebar border h-100 rounded-3 shadow overflow-y-scroll" >
			<div class="sidebar-sticky ">
				<!-- Desktop/Tablet Logo and Title -->
				<div class="text-white m-0 py-3 mb-3 nav-brand d-flex flex-wrap align-items-center justify-content-between d-none d-md-flex">
				<div class="position-relative d-flex align-items-center">
					
					<div class="responsive-title-container d-flex">
						<div class="logo-column me-2">
							<img src="/img/logo.png" alt="WireGate Logo" style="width: 32px; height: 32px;">
						</div>
						<div class="title-column">
							<div class="responsive-title">WireGate</div>
							<div class="responsive-subtitle">Dashboard</div>
						</div>
					</div>
				</div>
				<small class="d-inline-flex align-items-center" v-if="getActiveCrossServer !== undefined">
					<i class="bi bi-hdd-rack-fill me-2"></i>
					<span class="text-truncate">{{getActiveCrossServer.host}}</span>
				</small>
				</div>
				
				<!-- Mobile Logo and Title - Hidden, shown in top navbar instead -->
				<div class="text-white m-0 py-2 mb-2 nav-brand-mobile d-flex align-items-center d-none">
					<img src="/img/logo.png" alt="WireGate Logo" class="mobile-logo me-2" style="width: 32px; height: 32px;">
					<div class="d-flex flex-column">
						<span class="mobile-title">WireGate</span>
						<span class="mobile-subtitle">Dashboard</span>
					</div>
				</div>
				<ul class="nav flex-column px-2 mt-2">
					<li class="nav-item">
						<RouterLink class="nav-link rounded-3"
						            to="/" exact-active-class="active">
							<i class="bi bi-house me-2"></i>
							<LocaleText t="Home"></LocaleText>	
						</RouterLink></li>
					<li class="nav-item">
						<RouterLink class="nav-link rounded-3" to="/settings" 
						            exact-active-class="active">
							<i class="bi bi-gear me-2"></i>
							<LocaleText t="Settings"></LocaleText>	
						</RouterLink>
					</li>
				</ul>
				<hr class="text-body">
				<h6 class="sidebar-heading px-3 mt-4 mb-3 text-muted" style="font-size: 0.7rem; font-weight: 100;">
					<i class="bi bi-body-text me-2"></i>
					<LocaleText t="Configurations"></LocaleText>
				</h6>
				<ul class="nav flex-column px-2">
					<li class="nav-item mb-2">
						<RouterLink to="/new_configuration" class="nav-link rounded-3" active-class="active">
							<i class="bi bi-plus-circle me-2"></i>
							<LocaleText t="New Configuration"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item" v-for="c in this.wireguardConfigurationsStore.Configurations">
						<RouterLink :to="'/configuration/'+c.Name + '/peers'" 
						            class="nav-link nav-conf-link rounded-3"
						            active-class="active">
							<span class="dot me-2" :class="{active: c.Status}"></span>
							{{c.Name}}
						</RouterLink>
					</li>
				</ul>
				<hr class="text-body">
				<h6 class="sidebar-heading px-3 mt-4 mb-3 text-muted" style="font-size: 0.7rem; font-weight: 100;">
					<i class="bi bi-tools me-2"></i>
					<LocaleText t="Tools"></LocaleText>
				</h6>
				<ul class="nav flex-column px-2">
					<li class="nav-item mb-2">
						<RouterLink to="/system_status" class="nav-link rounded-3" active-class="active">
							<i class="bi bi-pc-display me-2"></i>
							<LocaleText t="System Status"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item mb-2">
						<RouterLink to="/tor-configuration" class="nav-link rounded-3" active-class="active">
							<i class="bi tor-logo me-2"></i>
							<LocaleText t="Tor Configuration"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item mb-2">
						<RouterLink to="/ping" class="nav-link rounded-3" active-class="active">
							<i class="bi bi-broadcast me-2" style="font-size: 1.3em"></i>
							<LocaleText t="Ping"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item mb-2">
						<RouterLink to="/traceroute" class="nav-link rounded-3" active-class="active">
							<i class="bi bi-diagram-2 me-2" style="font-size: 1.4em"></i>
							<LocaleText t="Traceroute"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item mb-2">
						<RouterLink to="/restore_configuration" class="nav-link rounded-3" active-class="active">
							<i class="bi bi-cloud-upload me-2" style="font-size: 1.3em"></i>
							<LocaleText t="Upload & Restore"></LocaleText>
						</RouterLink>
					</li>
				</ul>
				<hr class="text-body">
				<ul class="nav flex-column px-2 mb-3">
					<li class="nav-item">
						<a class="nav-link text-danger rounded-3" 
					                        @click="this.dashboardConfigurationStore.signOut()" 
					                        role="button" style="font-weight: bold">
							<i class="bi bi-box-arrow-left me-2"></i>
							<LocaleText t="Sign Out"></LocaleText>	
						</a>
					</li>
					<li class="nav-item">
						<a :href="this.updateUrl" 
						   v-if="this.updateAvailable" 
						   class="nav-link text-success rounded-3" 
						   target="_blank">
							<div class="d-flex align-items-center">
								<i class="bi bi-arrow-up-circle me-2"></i>
								<div class="d-flex flex-column flex-grow-1">
									<small><LocaleText :t="this.updateMessage"></LocaleText></small>
									<small class="text-muted">
										<LocaleText t="Current Version:"></LocaleText> 
										{{ dashboardConfigurationStore.Configuration.Server.version }}
									</small>
									<small v-if="changelogItems.length > 0" 
										   class="changelog-toggle text-secondary" 
										   @click.stop.prevent="toggleChangelog">
										<i class="bi" :class="showChangelog ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
										<LocaleText t="View changelog"></LocaleText>
									</small>
									<div v-if="showChangelog" class="changelog-container mt-2">
										<ul class="changelog-list">
											<li v-for="(item, index) in changelogItems" :key="index">
												{{ item }}
											</li>
										</ul>
									</div>
								</div>
								<button class="btn btn-sm btn-outline-light ms-2" 
								        @click.stop.prevent="refreshUpdateCheck"
								        title="Refresh update check">
									<i class="bi bi-arrow-clockwise"></i>
								</button>
							</div>
						</a>
						<div v-else class="nav-link text-muted rounded-3 d-flex align-items-center">
							<i class="bi bi-check-circle me-2"></i>
							<div class="d-flex flex-column flex-grow-1">
								<small><LocaleText :t="this.updateMessage"></LocaleText></small>
								<small>{{ dashboardConfigurationStore.Configuration.Server.version }}</small>
								<small class="changelog-toggle text-secondary" 
									   @click.stop.prevent="toggleChangelog"
									   style="cursor: pointer;">
									<i class="bi" :class="showChangelog ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
									<LocaleText t="View changelog"></LocaleText>
								</small>
								<div v-if="showChangelog" class="changelog-container mt-2">
									<div v-if="changelogLoading" class="text-center py-2">
										<small class="text-muted">
											<i class="bi bi-hourglass-split me-1"></i>
											<LocaleText t="Loading changelog..."></LocaleText>
										</small>
									</div>
									<div v-else-if="changelogItems.length > 0">
										<div class="text-info mb-2" style="font-size: 0.75rem;">
											<i class="bi bi-info-circle me-1"></i>
											<LocaleText t="Latest version changelog:"></LocaleText> {{ changelogVersion }}
										</div>
										<ul class="changelog-list">
											<li v-for="(item, index) in changelogItems" :key="index">
												{{ item }}
											</li>
										</ul>
									</div>
									<div v-else class="text-muted text-center py-2">
										<small><LocaleText t="No changelog available for this version"></LocaleText></small>
									</div>
								</div>
							</div>
							<button class="btn btn-sm btn-outline-light ms-2" 
							        @click.stop.prevent="refreshUpdateCheck"
							        title="Refresh update check">
								<i class="bi bi-arrow-clockwise"></i>
							</button>
						</div>
					</li>
				</ul>
			</div>
		</nav>
	</div>
</template>

<style scoped>
.nav-link.active {
	background: linear-gradient(234deg, var(--brandColor4) 0%, var(--brandColor6) 100%);
	color: white !important;
	font-weight: 500;
}

/* Update check refresh button styles */
.btn-outline-light {
	border-color: rgba(255, 255, 255, 0.3);
	color: rgba(255, 255, 255, 0.7);
	font-size: 0.75rem;
	padding: 0.25rem 0.5rem;
	min-width: 2rem;
}

.btn-outline-light:hover {
	background-color: rgba(255, 255, 255, 0.1);
	border-color: rgba(255, 255, 255, 0.5);
	color: white;
}

.btn-outline-light:focus {
	box-shadow: 0 0 0 0.2rem rgba(255, 255, 255, 0.25);
}

/* Ensure proper spacing for update section */
.nav-item .d-flex {
	align-items: center;
}

.flex-grow-1 {
	flex-grow: 1;
}

/* Tablet responsive adjustments */
@media screen and (min-width: 768px) and (max-width: 991px) {
	.navbar-container {
		flex: 0 0 25%;
		max-width: 25%;
		padding: 0.5rem;
	}
	
	.sidebar {
		height: calc(100vh - 1rem);
		max-height: calc(100vh - 1rem);
		overflow-y: auto;
		overflow-x: hidden;
	}
	
	.sidebar-sticky {
		padding-bottom: 1rem;
	}
	
	.nav-brand {
		padding: 0.75rem 0.5rem !important;
		margin-bottom: 0.75rem !important;
	}
	
	.responsive-title {
		font-size: 1.3rem;
	}
	
	.responsive-subtitle {
		font-size: 0.7rem;
		padding-left: 0px !important;
		line-height: 1.3;
		margin-bottom: 0.25rem;
	}
	
	.nav-link {
		padding: 0.5rem 0.75rem;
		font-size: 0.9rem;
	}
	
	.sidebar-heading {
		font-size: 0.65rem;
		margin-top: 0.75rem !important;
		margin-bottom: 0.5rem !important;
	}
}

/* Large screens - let Bootstrap handle the width */
@media screen and (min-width: 992px) {
	.sidebar {
		height: calc(100vh - 1rem);
		max-height: calc(100vh - 1rem);
		overflow-y: auto;
		overflow-x: hidden;
	}
	
	.sidebar-sticky {
		padding-bottom: 1rem;
	}
}

@media screen and (max-width: 768px) {
	.navbar-container{
		position: absolute;
		z-index: 1000;
		
		animation-duration: 0.4s;
		animation-fill-mode: both;
		display: none;
		animation-timing-function: cubic-bezier(0.82, 0.58, 0.17, 0.9);
	}
	.navbar-container.active{
		animation-direction: normal;
		display: block !important;
		animation-name: zoomInFade
	}
}

@supports (height: 100dvh) {
	@media screen and (max-width: 768px){
		.navbar-container{
			height: calc(100dvh - 50px);
		}	
	}
}

@keyframes zoomInFade {
	0%{
		opacity: 0;
		transform: translateY(60px);
		filter: blur(3px);
	}
	100%{
		opacity: 1;
		transform: translateY(0px);
		filter: blur(0px);
	}
}

.changelog-toggle {
	cursor: pointer;
	color: var(--bs-primary);
	margin-top: 5px;
}

.changelog-container {
	background: rgba(0, 0, 0, 0.05);
	border-radius: 8px;
	padding: 8px;
	max-height: 150px;
	overflow-y: auto;
}

.changelog-list {
	padding-left: 20px;
	margin-bottom: 0;
}

.changelog-list li {
	font-size: 0.8rem;
	margin-bottom: 4px;
}

/* Responsive title and subtitle styles */
.responsive-title-container {
	display: flex;
	align-items: center;
}

.logo-column {
	display: flex;
	align-items: center;
}

.title-column {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
}

.responsive-title {
	font-size: clamp(0.8rem, 3vw, 1.2rem);
	font-weight: 600;
	line-height: 1.2;
	word-wrap: break-word;
	overflow-wrap: break-word;
	hyphens: auto;
	margin: 0;
}

.responsive-subtitle {
	font-size: clamp(0.6rem, 2.5vw, 0.8rem);
	line-height: 1.3;
	word-wrap: break-word;
	overflow-wrap: break-word;
	white-space: nowrap;
	overflow: visible;
	text-overflow: unset;
	margin: 0;
	opacity: 0.75;
}

/* Nav brand container adjustments */
.nav-brand {
	min-height: auto;
	padding: 0.75rem 0.5rem !important;
	display: flex;
	align-items: flex-start;
}

.nav-brand .position-relative {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	max-width: 100%;
	overflow: visible;
}

/* Very small screens (phones in portrait) */
@media screen and (max-width: 480px) {
	.responsive-title {
		font-size: 0.8rem;
		line-height: 1.1;
	}
	
	.responsive-subtitle {
		font-size: 0.6rem;
		max-width: calc(100vw - 100px);
	}
	
	.nav-brand {
		padding: 0.5rem 0.25rem !important;
	}
}

/* Small screens (mobile landscape) */
@media screen and (min-width: 481px) and (max-width: 576px) {
	.responsive-title {
		font-size: 0.9rem;
	}
	
	.responsive-subtitle {
		font-size: 0.65rem;
		max-width: calc(100vw - 120px);
	}
}

/* Medium screens (tablets) */
@media screen and (min-width: 577px) and (max-width: 768px) {
	.responsive-title {
		font-size: 1.1rem;
	}
	
	.responsive-subtitle {
		font-size: 0.7rem;
	}
}

/* Large screens (desktop) */
@media screen and (min-width: 769px) and (max-width: 1199px) {
	.responsive-title {
		font-size: 1.2rem;
	}
	
	.responsive-subtitle {
		font-size: 0.75rem;
	}
}

/* Extra large screens */
@media screen and (min-width: 1200px) {
	.responsive-title {
		font-size: 1.4rem;
	}
	
	.responsive-subtitle {
		font-size: 0.8rem;
	}
}

/* Ultra-wide screens */
@media screen and (min-width: 1920px) {
	.responsive-title {
		font-size: 1.6rem;
	}
	
	.responsive-subtitle {
		font-size: 0.9rem;
	}
}

/* Very narrow screens (unusual aspect ratios) */
@media screen and (max-width: 320px) {
	.responsive-title {
		font-size: 0.9rem;
		line-height: 1;
	}
	
	.responsive-subtitle {
		font-size: 0.55rem;
		max-width: calc(100vw - 80px);
	}
	
	.nav-brand {
		padding: 0.25rem 0.1rem !important;
	}
}

/* Mobile logo and title styles */
.nav-brand-mobile {
	padding: 0.5rem 1rem !important;
	border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.mobile-logo {
	width: 32px !important;
	height: 32px !important;
	flex-shrink: 0;
}

.mobile-title {
	font-size: 1rem;
	font-weight: 600;
	line-height: 1.2;
	color: white;
}

.mobile-subtitle {
	font-size: 0.7rem;
	line-height: 1;
	color: rgba(255, 255, 255, 0.75);
}

/* Additional responsive improvements for better spacing */
@media screen and (min-width: 769px) {
	.changelog-container {
		max-height: 120px;
	}
	
	.nav-item .d-flex {
		flex-wrap: wrap;
	}
	
	.nav-item .btn-outline-light {
		font-size: 0.7rem;
		padding: 0.2rem 0.4rem;
		min-width: 1.8rem;
	}
}

/* Landscape orientation adjustments */
@media screen and (max-height: 500px) and (orientation: landscape) {
	.nav-brand {
		padding: 0.25rem 0.5rem !important;
	}
	
	.nav-brand-mobile {
		padding: 0.25rem 0.5rem !important;
	}
	
	.responsive-title {
		font-size: clamp(0.8rem, 3vw, 1.2rem);
	}
	
	.responsive-subtitle {
		font-size: clamp(0.5rem, 2vw, 0.7rem);
	}
	
	.mobile-title {
		font-size: 0.9rem;
	}
	
	.mobile-subtitle {
		font-size: 0.65rem;
	}
	
	.sidebar {
		height: calc(100vh - 0.5rem);
		max-height: calc(100vh - 0.5rem);
	}
	
	.changelog-container {
		max-height: 80px;
	}
}

/* Very short screens (height-based) */
@media screen and (max-height: 600px) {
	.nav-brand {
		padding: 0.5rem 0.75rem !important;
		margin-bottom: 0.5rem !important;
	}
	
	.sidebar-heading {
		margin-top: 0.5rem !important;
		margin-bottom: 0.25rem !important;
	}
	
	.nav-link {
		padding: 0.4rem 0.75rem;
	}
	
	.changelog-container {
		max-height: 100px;
	}
}
</style>