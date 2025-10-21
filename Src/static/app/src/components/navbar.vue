<script>
import {WiregateDashboardStore} from "@/stores/WiregateDashboardStore.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";
import ProtocolBadge from "@/components/protocolBadge.vue";
import ChangelogModal from "@/components/changelogModal.vue";

export default {
	name: "navbar",
	components: {LocaleText, ProtocolBadge, ChangelogModal},
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
			showChangelogModal: false,
			configurationsCollapsed: false,
			toolsCollapsed: true,
			showProtocolBadges: true,
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
		
		// Initialize matrix rain effect
		this.initMatrixRain();
	},
	beforeUnmount() {
		// Clean up event listener
		if (this.updateCheckHandler) {
			window.removeEventListener('triggerUpdateCheck', this.updateCheckHandler);
		}
		
		// Clean up matrix rain
		if (this.matrixInterval) {
			clearInterval(this.matrixInterval);
		}
		if (this.handleResize) {
			window.removeEventListener('resize', this.handleResize);
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
							console.log("Update URL:", this.updateUrl);
						} else {
							this.updateUrl = res.data
							console.log("No changelog data in response, using simple URL");
						}
						console.log("Update URL:", this.updateUrl);
					} else {
						// No update available
						this.updateAvailable = false
						console.log("No update available");
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
			this.checkForUpdates();
		},
		openChangelogModal() {
			this.showChangelogModal = true;
		},
		closeChangelogModal() {
			this.showChangelogModal = false;
		},
		toggleConfigurations() {
			this.configurationsCollapsed = !this.configurationsCollapsed;
		},
		toggleTools() {
			this.toolsCollapsed = !this.toolsCollapsed;
		},
		toggleProtocolBadges() {
			this.showProtocolBadges = !this.showProtocolBadges;
		},
		initMatrixRain() {
			// Wait for next tick to ensure DOM is ready
			this.$nextTick(() => {
				const navBrand = document.querySelector('.nav-brand.matrix-rain-bg');
				const navBrandMobile = document.querySelector('.nav-brand-mobile.matrix-rain-bg');
				
				if (navBrand) {
					this.createMatrixCanvas(navBrand);
				}
				if (navBrandMobile) {
					this.createMatrixCanvas(navBrandMobile);
				}
			});
		},
		createMatrixCanvas(container) {
			// Create canvas element
			const canvas = document.createElement('canvas');
			canvas.className = 'matrix-canvas';
			canvas.style.position = 'absolute';
			canvas.style.top = '0';
			canvas.style.left = '0';
			canvas.style.width = '100%';
			canvas.style.height = '100%';
			canvas.style.pointerEvents = 'none';
			canvas.style.zIndex = '1';
			canvas.style.opacity = '0.3';
			
			// Insert canvas as first child
			container.insertBefore(canvas, container.firstChild);
			
			// Make container relative positioned
			container.style.position = 'relative';
			container.style.overflow = 'hidden';
			
			// Ensure content stays above canvas
			const content = container.querySelector('.position-relative, .d-flex');
			if (content) {
				content.style.position = 'relative';
				content.style.zIndex = '2';
			}
			
			// Initialize matrix animation
			this.startMatrixAnimation(canvas);
		},
		startMatrixAnimation(canvas) {
			const ctx = canvas.getContext('2d');
			
			// Enable crisp text rendering
			ctx.imageSmoothingEnabled = false;
			ctx.textRendering = 'geometricPrecision';
			
			// Configuration
			const config = {
				delay: 0,
				fadeFactor: 0.15,
				interval: 120,
				colors: {
					primary: '#4cd964',    // Green
					secondary: '#33ff33',  // Bright green
					purple: {
						head: '#b31fff',     // Bright purple head
						tail: '#7a0cc4'      // Original purple tail
					},
					orange: {
						head: '#ff7b00',     // Bright orange head
						tail: '#e38e41'      // Original orange tail
					},
					cyan: '#00ffff'        // Cyan for easter eggs
				}
			};
			
			const fontSize = 12;
			const tileSize = fontSize + 2;
			const fontFamily = 'Consolas, monospace';
			let columns = [];
			
			const getRandomStackHeight = () => {
				const maxStackHeight = Math.ceil(canvas.height / tileSize);
				return Math.floor(Math.random() * (maxStackHeight - 5 + 1)) + 5;
			};
			
			const getRandomText = () => {
				const easterEggs = ['weir', 'noxis', 'james', 'wireguard', 'amnezia', 'WireGate'];
				const showEasterEgg = Math.random() < 0.002;
				
				if (showEasterEgg) {
					return {
						word: easterEggs[Math.floor(Math.random() * easterEggs.length)],
						isEasterEgg: true,
						charIndex: 0
					};
				}
				return {
					char: String.fromCharCode(Math.floor(Math.random() * (126 - 33 + 1)) + 33),
					isEasterEgg: false
				};
			};
			
			const getRandomColor = () => {
				const rand = Math.random();
				if (rand < 0.7) {
					return {
						color: config.colors.primary,
						glow: '#00ff2d',
						type: 'green'
					};
				} else if (rand < 0.85) {
					return {
						color: config.colors.secondary,
						glow: '#33ff33',
						type: 'green'
					};
				} else if (rand < 0.95) {
					return {
						color: config.colors.purple,
						glow: '#b31fff',
						type: 'purple'
					};
				} else {
					return {
						color: config.colors.orange,
						glow: '#ff7b00',
						type: 'orange'
					};
				}
			};
			
			const initColumns = () => {
				columns = [];
				const columnCount = Math.floor(canvas.width / tileSize);
				for (let i = 0; i < columnCount; i++) {
					const colorInfo = getRandomColor();
					columns.push({
						x: i * tileSize,
						stackCounter: Math.floor(Math.random() * 30),
						stackHeight: getRandomStackHeight(),
						colorInfo: colorInfo,
						intensity: 0.6 + Math.random() * 0.3,
						headPos: 0,
						easterEgg: null
					});
				}
			};
			
			const resizeCanvas = () => {
				const dpr = window.devicePixelRatio || 1;
				const rect = canvas.getBoundingClientRect();
				
				if (rect.width === 0 || rect.height === 0) {
					return;
				}
				
				canvas.width = rect.width * dpr;
				canvas.height = rect.height * dpr;
				canvas.style.width = `${rect.width}px`;
				canvas.style.height = `${rect.height}px`;
				
				ctx.scale(dpr, dpr);
			};
			
			const draw = () => {
				if (canvas.width === 0 || canvas.height === 0) {
					return;
				}
				
				ctx.font = `bold ${fontSize}px ${fontFamily}`;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				
				ctx.fillStyle = `rgba(0, 0, 0, ${config.fadeFactor})`;
				ctx.fillRect(0, 0, canvas.width, canvas.height);
				
				columns.forEach(column => {
					ctx.shadowBlur = 0;
					
					const stackProgress = column.stackCounter / column.stackHeight;
					let opacity = column.intensity * (1 - stackProgress * 0.2);
					
					let text;
					if (column.easterEgg) {
						text = {
							char: column.easterEgg.word[column.easterEgg.charIndex],
							isEasterEgg: true
						};
						
						column.easterEgg.charIndex++;
						
						if (column.easterEgg.charIndex >= column.easterEgg.word.length) {
							column.easterEgg = null;
						}
					} else {
						text = getRandomText();
						if (text.isEasterEgg) {
							column.easterEgg = {
								word: text.word,
								charIndex: 1
							};
							text.char = text.word[0];
						}
					}
					
					if (text.isEasterEgg) {
						ctx.shadowBlur = 1;
						ctx.shadowColor = config.colors.cyan;
						ctx.fillStyle = `${config.colors.cyan}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}`;
					} else if (column.colorInfo.type === 'purple' || column.colorInfo.type === 'orange') {
						column.intensity = 0.7 + Math.sin(Date.now() * 0.003) * 0.2;
						
						const colorType = column.colorInfo.type;
						const headColor = config.colors[colorType].head;
						const tailColor = config.colors[colorType].tail;
						
						const r = parseInt(headColor.slice(1, 3), 16);
						const g = parseInt(headColor.slice(3, 5), 16);
						const b = parseInt(headColor.slice(5, 7), 16);
						
						ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity * 0.8})`;
					} else {
						opacity *= 0.7;
						ctx.fillStyle = column.colorInfo.color.startsWith('#') ? 
							`${column.colorInfo.color}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}` : 
							column.colorInfo.color;
					}
					
					ctx.fillText(
						text.char,
						Math.round(column.x + tileSize/2),
						Math.round(column.stackCounter * tileSize + tileSize/2)
					);
					
					column.stackCounter++;
					if (column.stackCounter >= column.stackHeight) {
						column.stackCounter = 0;
						column.stackHeight = getRandomStackHeight();
						const newColorInfo = getRandomColor();
						column.colorInfo = newColorInfo;
						column.intensity = column.colorInfo.type === 'green' ? 
							0.6 + Math.random() * 0.3 : 
							0.7 + Math.random() * 0.2;
					}
				});
			};
			
			// Initialize
			resizeCanvas();
			initColumns();
			
			// Start animation
			this.matrixInterval = setInterval(draw, config.interval);
			
			// Handle resize
			let resizeTimeout;
			const handleResize = () => {
				clearTimeout(resizeTimeout);
				resizeTimeout = setTimeout(() => {
					clearInterval(this.matrixInterval);
					resizeCanvas();
					initColumns();
					this.matrixInterval = setInterval(draw, config.interval);
				}, 100);
			};
			
			window.addEventListener('resize', handleResize);
			this.handleResize = handleResize;
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
				<div class="text-white m-0 py-3 mb-3 nav-brand d-flex flex-wrap align-items-center justify-content-between d-none d-md-flex matrix-rain-bg">
				<div class="position-relative d-flex align-items-center">
					
					<div class="responsive-title-container d-flex">
						<div class="logo-column me-2">
							<img src="/img/logo.png" alt="WireGate Logo" class="logo-image">
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
				<div class="text-white m-0 py-2 mb-2 nav-brand-mobile d-flex align-items-center d-none matrix-rain-bg">
					<img src="/img/logo.png" alt="WireGate Logo" class="mobile-logo me-2">
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
				<div class="sidebar-section">
					<div class="sidebar-heading px-3 mt-4 mb-3 text-muted d-flex align-items-center justify-content-between" 
					     @click="toggleConfigurations" role="button">
						<div class="d-flex align-items-center">
							<i class="bi bi-body-text me-2"></i>
							<LocaleText t="Configurations"></LocaleText>
						</div>
						<div class="d-flex align-items-center">
							<button class="btn btn-sm btn-outline-secondary protocol-toggle me-2" 
							        @click.stop="toggleProtocolBadges" 
							        :title="showProtocolBadges ? 'Hide Protocol Badges' : 'Show Protocol Badges'">
								<i class="bi" :class="showProtocolBadges ? 'bi-eye' : 'bi-eye-slash'"></i>
							</button>
							<i class="bi" :class="configurationsCollapsed ? 'bi-chevron-right' : 'bi-chevron-down'"></i>
						</div>
					</div>
					<div class="collapse" :class="{show: !configurationsCollapsed}">
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
									<div class="d-flex align-items-center">
										<span class="configuration-name">{{c.Name}}</span>
										<ProtocolBadge v-if="showProtocolBadges" :protocol="c.Protocol" :mini="true" class="protocol-badge-small ms-2"></ProtocolBadge>
									</div>
								</RouterLink>
							</li>
						</ul>
					</div>
				</div>
				<hr class="text-body">
				<div class="sidebar-section">
					<div class="sidebar-heading px-3 mt-4 mb-3 text-muted d-flex align-items-center justify-content-between" 
					     @click="toggleTools" role="button">
						<div class="d-flex align-items-center">
							<i class="bi bi-tools me-2"></i>
							<LocaleText t="Tools"></LocaleText>
						</div>
						<i class="bi" :class="toolsCollapsed ? 'bi-chevron-right' : 'bi-chevron-down'"></i>
					</div>
					<div class="collapse" :class="{show: !toolsCollapsed}">
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
									<i class="bi bi-broadcast me-2 icon-broadcast"></i>
									<LocaleText t="Ping"></LocaleText>
								</RouterLink>
							</li>
							<li class="nav-item mb-2">
								<RouterLink to="/traceroute" class="nav-link rounded-3" active-class="active">
									<i class="bi bi-diagram-2 me-2 icon-diagram"></i>
									<LocaleText t="Traceroute"></LocaleText>
								</RouterLink>
							</li>
							<li class="nav-item mb-2">
								<RouterLink to="/restore_configuration" class="nav-link rounded-3" active-class="active">
									<i class="bi bi-cloud-upload me-2 icon-cloud-upload"></i>
									<LocaleText t="Upload & Restore"></LocaleText>
								</RouterLink>
							</li>
							<li class="nav-item mb-2">
								<a class="nav-link rounded-3" @click="openChangelogModal" role="button">
									<i class="bi bi-journal-text me-2"></i>
									<LocaleText t="Changelog"></LocaleText>
								</a>
							</li>
						</ul>
					</div>
				</div>
				<hr class="text-body">
				<ul class="nav flex-column px-2 mb-3">
					<li class="nav-item">
						<a class="nav-link text-danger rounded-3 sign-out-link" 
					                        @click="this.dashboardConfigurationStore.signOut()" 
					                        role="button">
							<i class="bi bi-box-arrow-left me-2"></i>
							<LocaleText t="Sign Out"></LocaleText>	
						</a>
					</li>
					<li class="nav-item mt-4">
						<div class="d-flex align-items-center justify-content-center">
							<div class="d-flex flex-column">
								<small class="version-link" @click="openChangelogModal" title="View Changelog">
									<strong>{{ dashboardConfigurationStore.Configuration.Server.version }}</strong>
								</small>
							</div>
						</div>
					</li>
				</ul>
			</div>
		</nav>
		
		<!-- Changelog Modal -->
		<ChangelogModal v-if="showChangelogModal" @close="closeChangelogModal" />
	</div>
</template>

<style scoped>
.nav-link.active {
	background-color: #000000 !important;
	border: 1px solid #ffffff !important;
	color: white !important;
	font-weight: 500;
}

/* Light theme styles for navbar */
[data-bs-theme="light"] .nav-link.active {
	background-color: #ffffff !important;
	border: 1px solid #000000 !important;
	color: #000000 !important;
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
	color: #ffc107 !important;
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

.logo-image {
	width: 32px;
	height: 32px;
}

.mobile-logo {
	width: 32px;
	height: 32px;
}

.sidebar-heading {
	font-size: 0.7rem;
	font-weight: 100;
}

.icon-broadcast {
	font-size: 1.3em;
}

.icon-diagram {
	font-size: 1.4em;
}

.icon-cloud-upload {
	font-size: 1.3em;
}

.sign-out-link {
	font-weight: bold;
}

.changelog-version {
	font-size: 0.75rem;
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

/* Configuration list styling */
.nav-conf-link {
	padding: 0.75rem !important;
}

.configuration-name {
	font-weight: 500;
	font-size: 0.9rem;
	line-height: 1.2;
	flex: 1;
}

.nav-conf-link .d-flex {
	align-items: center;
}

.nav-conf-link {
	display: flex;
	align-items: center;
}

.nav-conf-link .dot {
	margin-left: 0 !important;
	margin-right: 0.5rem !important;
	flex-shrink: 0;
}

.nav-conf-link .badge {
	font-size: 0.65rem;
	padding: 0.25rem 0.5rem;
	line-height: 1;
}

/* Small protocol badge styling */
.protocol-badge-small {
	font-size: 0.5rem !important;
	padding: 0.15rem 0.3rem !important;
	line-height: 1;
	flex-shrink: 0;
}

.protocol-badge-small .badge {
	font-size: 0.5rem !important;
	padding: 0.15rem 0.3rem !important;
	line-height: 1;
}

/* Responsive adjustments for configuration badges */
@media screen and (max-width: 768px) {
	.nav-conf-link {
		padding: 0.5rem !important;
	}
	
	.configuration-name {
		font-size: 0.85rem;
	}
	
	.protocol-badge-small {
		font-size: 0.45rem !important;
		padding: 0.1rem 0.25rem !important;
		margin-left: 0.25rem !important;
	}
	
	.protocol-badge-small .badge {
		font-size: 0.45rem !important;
		padding: 0.1rem 0.25rem !important;
	}
}

@media screen and (min-width: 769px) and (max-width: 991px) {
	.nav-conf-link {
		padding: 0.6rem 0.75rem !important;
	}
	
	.configuration-name {
		font-size: 0.85rem;
	}
	
	.protocol-badge-small {
		font-size: 0.5rem !important;
		padding: 0.12rem 0.3rem !important;
		margin-left: 0.25rem !important;
	}
	
	.protocol-badge-small .badge {
		font-size: 0.5rem !important;
		padding: 0.12rem 0.3rem !important;
	}
}

/* Matrix Rain Background Effect */
.matrix-rain-bg {
	position: relative;
	overflow: hidden;
	background: linear-gradient(234deg, #150044 0%, #002e00 100%) !important;
	animation: matrixGradient 8s ease-in-out infinite;
}

@keyframes matrixGradient {
	0% {
		background: linear-gradient(234deg, #150044 0%, #002e00 100%) !important;
	}
	100% {
		background: linear-gradient(594deg, #150044 0%, #002e00 100%) !important;
	}
}

.matrix-canvas {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
	z-index: 1;
	opacity: 0.3;
}

/* Ensure content stays above the matrix effect */
.matrix-rain-bg > * {
	position: relative;
	z-index: 2;
}

/* Matrix rain for mobile navbar */
.nav-brand-mobile.matrix-rain-bg {
	background: linear-gradient(234deg, #150044 0%, #002e00 100%) !important;
	animation: matrixGradient 8s ease-in-out infinite;
}

/* Version clickable styling */
.version-link {
	cursor: pointer;
	transition: color 0.2s ease-in-out;
	color: #4a4a4a;
}

.version-link:hover {
	color: white !important;
}

/* Collapsible sidebar sections */
.sidebar-section {
	margin-bottom: 0.5rem;
}

.sidebar-section .sidebar-heading {
	cursor: pointer;
	transition: all 0.2s ease-in-out;
	border-radius: 0.375rem;
	margin-bottom: 0.5rem !important;
	padding: 0.5rem 0.75rem !important;
}

.sidebar-section .sidebar-heading:hover {
	background-color: rgba(255, 255, 255, 0.1);
}

[data-bs-theme="light"] .sidebar-section .sidebar-heading:hover {
	background-color: rgba(0, 0, 0, 0.1);
}

.sidebar-section .collapse {
	transition: all 0.3s ease-in-out;
}

.sidebar-section .collapse.show {
	display: block;
}

.sidebar-section .bi-chevron-right,
.sidebar-section .bi-chevron-down {
	transition: transform 0.2s ease-in-out;
	font-size: 0.8rem;
}

/* Protocol toggle button styling */
.protocol-toggle {
	padding: 0.2rem 0.4rem !important;
	font-size: 0.7rem !important;
	border: 1px solid rgba(255, 255, 255, 0.3) !important;
	background-color: transparent !important;
	color: rgba(255, 255, 255, 0.7) !important;
	transition: all 0.2s ease-in-out;
}

.protocol-toggle:hover {
	background-color: rgba(255, 255, 255, 0.1) !important;
	border-color: rgba(255, 255, 255, 0.5) !important;
	color: white !important;
}

[data-bs-theme="light"] .protocol-toggle {
	border: 1px solid rgba(0, 0, 0, 0.3) !important;
	color: rgba(0, 0, 0, 0.7) !important;
}

[data-bs-theme="light"] .protocol-toggle:hover {
	background-color: rgba(0, 0, 0, 0.1) !important;
	border-color: rgba(0, 0, 0, 0.5) !important;
	color: #000000 !important;
}
</style>