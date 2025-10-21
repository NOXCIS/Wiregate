<script>
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

export default {
	name: "changelogModal",
	components: {LocaleText},
	setup() {
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {dashboardConfigurationStore}
	},
	data() {
		return {
			activeTab: 'current',
			currentVersionChangelog: [],
			allVersionsChangelog: {},
			changelogLoading: false,
			updateInfo: {
				available: false,
				message: "Checking for update...",
				url: "",
				latestVersion: "",
				loading: false
			}
		}
	},
	mounted() {
		this.loadChangelogData();
		this.checkForUpdates();
	},
	methods: {
		closeModal() {
			this.$emit('close');
		},
		async loadChangelogData() {
			this.changelogLoading = true;
			
			try {
				// Load current version changelog
				await this.loadCurrentVersionChangelog();
				
				// Load all versions changelog
				await this.loadAllVersionsChangelog();
			} catch (error) {
				console.error("Failed to load changelog data:", error);
			} finally {
				this.changelogLoading = false;
			}
		},
		async loadCurrentVersionChangelog() {
			const currentVersion = this.dashboardConfigurationStore.Configuration.Server.version;
			console.log("=== LOADING CURRENT VERSION CHANGELOG ===");
			console.log("Current version from store:", currentVersion);
			console.log("Dashboard config store:", this.dashboardConfigurationStore.Configuration.Server);
			
			try {
				console.log("Making API call to /api/getCurrentVersionChangelog with version:", currentVersion);
				const response = await new Promise((resolve, reject) => {
					fetchGet("/api/getCurrentVersionChangelog", {version: currentVersion}, (res) => {
						console.log("API callback received response:", res);
						resolve(res);
					}).catch(reject);
				});
				
				console.log("Full API response:", response);
				console.log("Response status:", response ? response.status : "undefined");
				console.log("Response data:", response ? response.data : "undefined");
				
				if (response && response.status) {
					this.currentVersionChangelog = response.data.changelog || [];
					console.log("Successfully loaded changelog items:", this.currentVersionChangelog);
					console.log("Number of changelog items:", this.currentVersionChangelog.length);
				} else {
					console.warn("API call failed - response status:", response ? response.status : "undefined");
					console.warn("API response message:", response ? response.message : "undefined");
					console.log("Trying fallback to 'latest' version...");
					
					// Try to get latest version changelog as fallback
					try {
						const latestResponse = await new Promise((resolve, reject) => {
							fetchGet("/api/getCurrentVersionChangelog", {version: "latest"}, (res) => {
								console.log("Latest version API callback received response:", res);
								resolve(res);
							}).catch(reject);
						});
						
						console.log("Latest version API response:", latestResponse);
						if (latestResponse && latestResponse.status) {
							this.currentVersionChangelog = latestResponse.data.changelog || [];
							console.log("Fallback successful - loaded latest changelog items:", this.currentVersionChangelog);
						} else {
							console.error("Fallback also failed");
							this.currentVersionChangelog = [];
						}
					} catch (fallbackError) {
						console.error("Fallback error:", fallbackError);
						this.currentVersionChangelog = [];
					}
				}
			} catch (error) {
				console.error("Error loading current version changelog:", error);
				this.currentVersionChangelog = [];
			}
			
			console.log("Final currentVersionChangelog:", this.currentVersionChangelog);
			console.log("=== END LOADING CURRENT VERSION CHANGELOG ===");
		},
		async loadAllVersionsChangelog() {
			try {
				// Fetch the changelog file directly from GitHub
				const response = await fetch('https://raw.githubusercontent.com/NOXCIS/Wiregate/refs/heads/main/Docs/CHANGELOG.md');
				const text = await response.text();
				this.allVersionsChangelog = this.parseAllVersionsChangelog(text);
			} catch (error) {
				console.error("Error loading all versions changelog:", error);
				this.allVersionsChangelog = {};
			}
		},
		parseAllVersionsChangelog(text) {
			const changelogMap = {};
			const content = text.trim().split('\n');
			let currentVersion = null;
			
			for (const line of content) {
				const trimmedLine = line.trim();
				if (!trimmedLine) continue;
				
				// Check if this line defines a version (ends with : and doesn't start with - or space)
				if (trimmedLine.endsWith(':') && !trimmedLine.startsWith('-') && !trimmedLine.startsWith(' ')) {
					currentVersion = trimmedLine.replace(':', '').trim();
					changelogMap[currentVersion] = [];
				} else if (trimmedLine.startsWith('-') && currentVersion) {
					const item = trimmedLine.replace('-', '', 1).trim();
					changelogMap[currentVersion].push(item);
				}
			}
			
			return changelogMap;
		},
		async checkForUpdates() {
			this.updateInfo.loading = true;
			
			try {
				const response = await new Promise((resolve, reject) => {
					fetchGet("/api/getDashboardUpdate", {}, (res) => {
						resolve(res);
					}).catch(reject);
				});
				
				if (response && response.status && response.data) {
					this.updateInfo.available = true;
					this.updateInfo.message = response.message;
					this.updateInfo.url = response.data.url || "";
					this.updateInfo.latestVersion = response.data.version || "";
				} else {
					this.updateInfo.available = false;
					this.updateInfo.message = (response && response.message) || GetLocale("Failed to check available update");
				}
			} catch (error) {
				console.error("Update check failed:", error);
				this.updateInfo.available = false;
				this.updateInfo.message = GetLocale("Update check failed");
			} finally {
				this.updateInfo.loading = false;
			}
		},
		async refreshUpdateCheck() {
			await this.checkForUpdates();
		},
		setActiveTab(tab) {
			this.activeTab = tab;
		},
		getVersionKeys() {
			return Object.keys(this.allVersionsChangelog).sort((a, b) => {
				// Sort versions in descending order (latest first)
				return b.localeCompare(a, undefined, {numeric: true});
			});
		}
	}
}
</script>

<template>
	<div class="modal fade show d-block" tabindex="-1" role="dialog" style="background-color: rgba(0,0,0,0.5);">
		<div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
			<div class="modal-content" :data-bs-theme="dashboardConfigurationStore.Configuration.Server.dashboard_theme">
				<div class="modal-header">
					<h5 class="modal-title">
						<i class="bi bi-journal-text me-2"></i>
						<LocaleText t="Changelog"></LocaleText>
					</h5>
					<button type="button" class="btn-close" @click="closeModal" aria-label="Close"></button>
				</div>
				
				<div class="modal-body">
					<!-- Update Check Section -->
					<div class="update-check-section mb-4 p-3 border rounded">
						<div class="d-flex align-items-center justify-content-between mb-3">
							<h6 class="mb-0">
								<i class="bi bi-arrow-up-circle me-2"></i>
								<LocaleText t="Update Check"></LocaleText>
							</h6>
							<button class="btn btn-sm btn-outline-primary" 
							        @click="refreshUpdateCheck" 
							        :disabled="updateInfo.loading">
								<i class="bi bi-arrow-clockwise" :class="{'spinning': updateInfo.loading}"></i>
								<LocaleText t="Check for Updates"></LocaleText>
							</button>
						</div>
						
						<div class="row">
							<div class="col-md-6">
								<small class="text-muted">
									<LocaleText t="Current Version:"></LocaleText>
								</small>
								<div class="fw-bold">{{ dashboardConfigurationStore.Configuration.Server.version }}</div>
							</div>
							<div class="col-md-6" v-if="updateInfo.latestVersion">
								<small class="text-muted">
									<LocaleText t="Latest Version:"></LocaleText>
								</small>
								<div class="fw-bold">{{ updateInfo.latestVersion }}</div>
							</div>
						</div>
						
						<div class="mt-2">
							<div v-if="updateInfo.available" class="alert alert-success mb-0">
								<i class="bi bi-check-circle me-2"></i>
								<LocaleText :t="updateInfo.message"></LocaleText>
								<a v-if="updateInfo.url" :href="updateInfo.url" target="_blank" class="btn btn-sm btn-brand ms-2">
									<i class="bi bi-box-arrow-up-right me-1"></i>
									<LocaleText t="View on Docker Hub"></LocaleText>
								</a>
							</div>
							<div v-else class="alert alert-info mb-0">
								<i class="bi bi-info-circle me-2"></i>
								<LocaleText :t="updateInfo.message"></LocaleText>
							</div>
						</div>
					</div>
					
					<!-- Tabs Navigation -->
					<ul class="nav nav-tabs mb-3" role="tablist">
						<li class="nav-item" role="presentation">
							<button class="nav-link" 
							        :class="{active: activeTab === 'current'}" 
							        @click="setActiveTab('current')" 
							        type="button">
								<i class="bi bi-file-text me-2"></i>
								<LocaleText t="Current Version"></LocaleText>
							</button>
						</li>
						<li class="nav-item" role="presentation">
							<button class="nav-link" 
							        :class="{active: activeTab === 'all'}" 
							        @click="setActiveTab('all')" 
							        type="button">
								<i class="bi bi-list-ul me-2"></i>
								<LocaleText t="All Versions"></LocaleText>
							</button>
						</li>
					</ul>
					
					<!-- Tab Content -->
					<div class="tab-content">
						<!-- Current Version Tab -->
						<div v-if="activeTab === 'current'" class="tab-pane active">
							<div v-if="changelogLoading" class="text-center py-4">
								<div class="spinner-border text-primary" role="status">
									<span class="visually-hidden"><LocaleText t="Loading..."></LocaleText></span>
								</div>
								<div class="mt-2">
									<LocaleText t="Loading changelog..."></LocaleText>
								</div>
							</div>
							
							<div v-else-if="currentVersionChangelog.length > 0">
								<h6 class="mb-3">
									<i class="bi bi-info-circle me-2"></i>
									<LocaleText t="Changelog for version:"></LocaleText> 
									{{ dashboardConfigurationStore.Configuration.Server.version }}
								</h6>
								<ul class="changelog-list">
									<li v-for="(item, index) in currentVersionChangelog" :key="index" class="mb-2">
										{{ item }}
									</li>
								</ul>
							</div>
							
							<div v-else class="text-center py-4 text-muted">
								<i class="bi bi-exclamation-circle me-2"></i>
								<LocaleText t="NO CHANGE LOG AVAILABLE"></LocaleText>
							</div>
						</div>
						
						<!-- All Versions Tab -->
						<div v-if="activeTab === 'all'" class="tab-pane active">
							<div v-if="changelogLoading" class="text-center py-4">
								<div class="spinner-border text-primary" role="status">
									<span class="visually-hidden"><LocaleText t="Loading..."></LocaleText></span>
								</div>
								<div class="mt-2">
									<LocaleText t="Loading changelog..."></LocaleText>
								</div>
							</div>
							
							<div v-else-if="Object.keys(allVersionsChangelog).length > 0">
								<div v-for="version in getVersionKeys()" :key="version" class="version-section mb-4">
									<div class="version-header p-3 rounded">
										<h6 class="mb-0">
											<i class="bi bi-tag me-2"></i>
											{{ version }}
										</h6>
									</div>
									<div class="version-content p-3">
										<ul v-if="allVersionsChangelog[version].length > 0" class="changelog-list mb-0">
											<li v-for="(item, index) in allVersionsChangelog[version]" :key="index" class="mb-2">
												{{ item }}
											</li>
										</ul>
										<div v-else class="text-muted">
											<LocaleText t="NO CHANGE LOG AVAILABLE"></LocaleText>
										</div>
									</div>
								</div>
							</div>
							
							<div v-else class="text-center py-4 text-muted">
								<i class="bi bi-exclamation-circle me-2"></i>
								<LocaleText t="NO CHANGE LOG AVAILABLE"></LocaleText>
							</div>
						</div>
					</div>
				</div>
				
				<div class="modal-footer">
					<button type="button" class="btn btn-brand" @click="closeModal">
						<LocaleText t="Close"></LocaleText>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
/* Modal styling - consistent with app theme */
.modal-content {
	border-radius: 0.5rem;
	box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

/* Dark theme styles */
[data-bs-theme="dark"] .modal-content {
	background-color: #000000;
	color: #ffffff;
}

[data-bs-theme="dark"] .modal-header {
	background-color: #000000;
	border-bottom: 1px solid #444444;
	color: #ffffff;
}

[data-bs-theme="dark"] .modal-footer {
	background-color: #000000;
	border-top: 1px solid #444444;
	color: #ffffff;
}

[data-bs-theme="dark"] .modal-body {
	background-color: #000000;
	color: #ffffff;
}

/* Light theme styles */
[data-bs-theme="light"] .modal-content {
	background-color: #ffffff;
	color: #000000;
}

[data-bs-theme="light"] .modal-header {
	background-color: #ffffff;
	border-bottom: 1px solid #dee2e6;
	color: #000000;
}

[data-bs-theme="light"] .modal-footer {
	background-color: #ffffff;
	border-top: 1px solid #dee2e6;
	color: #000000;
}

[data-bs-theme="light"] .modal-body {
	background-color: #ffffff;
	color: #000000;
}

/* Update check section */
.update-check-section {
	border-radius: 0.375rem;
}

[data-bs-theme="dark"] .update-check-section {
	background-color: #0d0d0d;
	border-color: #444444 !important;
	color: #ffffff;
}

[data-bs-theme="light"] .update-check-section {
	background-color: #f8f9fa;
	border-color: #dee2e6 !important;
	color: #000000;
}

/* Changelog list styling */
.changelog-list {
	padding-left: 1.5rem;
	margin-bottom: 0;
}

.changelog-list li {
	font-size: 0.9rem;
	line-height: 1.5;
}

/* Version section styling */
.version-section {
	border-radius: 0.375rem;
	overflow: hidden;
}

[data-bs-theme="dark"] .version-section {
	border: 1px solid #444444;
}

[data-bs-theme="light"] .version-section {
	border: 1px solid #dee2e6;
}

.version-header {
	border-radius: 0.375rem 0.375rem 0 0;
}

[data-bs-theme="dark"] .version-header {
	background-color: #0d0d0d;
	border-bottom: 1px solid #444444;
	color: #ffffff;
}

[data-bs-theme="light"] .version-header {
	background-color: #f8f9fa;
	border-bottom: 1px solid #dee2e6;
	color: #000000;
}

.version-content {
	border-radius: 0 0 0.375rem 0.375rem;
}

[data-bs-theme="dark"] .version-content {
	background-color: #000000;
	color: #ffffff;
}

[data-bs-theme="light"] .version-content {
	background-color: #ffffff;
	color: #000000;
}

/* Tab styling */
.nav-tabs .nav-link {
	border-radius: 0.375rem 0.375rem 0 0;
	border: 1px solid transparent;
}

[data-bs-theme="dark"] .nav-tabs .nav-link {
	color: #ffffff;
}

[data-bs-theme="dark"] .nav-tabs .nav-link:hover {
	border-color: #444444;
	color: var(--brandColor3);
}

[data-bs-theme="dark"] .nav-tabs .nav-link.active {
	background-color: var(--brandColor4);
	color: white;
	border-color: var(--brandColor4);
}

[data-bs-theme="light"] .nav-tabs .nav-link {
	color: #000000;
}

[data-bs-theme="light"] .nav-tabs .nav-link:hover {
	border-color: #dee2e6;
	color: #000000;
}

[data-bs-theme="light"] .nav-tabs .nav-link.active {
	background-color: var(--brandColor4);
	color: white;
	border-color: var(--brandColor4);
}

/* Alert styling */
.alert {
	border-radius: 0.375rem;
}

[data-bs-theme="dark"] .alert-success {
	background-color: #1a4d1a;
	border-color: #28a745;
	color: #ffffff;
}

[data-bs-theme="dark"] .alert-info {
	background-color: #1a3a4d;
	border-color: #17a2b8;
	color: #ffffff;
}

[data-bs-theme="light"] .alert-success {
	background-color: #d1e7dd;
	border-color: #28a745;
	color: #0f5132;
}

[data-bs-theme="light"] .alert-info {
	background-color: #cff4fc;
	border-color: #17a2b8;
	color: #055160;
}

/* Spinning animation */
.spinning {
	animation: spin 1s linear infinite;
}

@keyframes spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

/* Responsive adjustments */
@media (max-width: 768px) {
	.modal-dialog {
		margin: 0.5rem;
	}
	
	.update-check-section .row {
		flex-direction: column;
	}
	
	.update-check-section .col-md-6 {
		margin-bottom: 0.5rem;
	}
	
	.changelog-list {
		padding-left: 1rem;
	}
	
	.changelog-list li {
		font-size: 0.85rem;
	}
}
</style>
