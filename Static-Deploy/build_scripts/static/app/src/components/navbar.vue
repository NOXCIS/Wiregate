<script>
import {wgdashboardStore} from "@/stores/wgdashboardStore.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";
import HelpModal from "@/components/navbarComponents/helpModal.vue";

export default {
	name: "navbar",
	components: {HelpModal, LocaleText},
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
			openHelpModal: false,
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
		fetchGet("/api/getDashboardUpdate", {}, (res) => {
			if (res.status){
				if (res.data){
					this.updateAvailable = true
					this.updateUrl = res.data
				}
				this.updateMessage = res.message
			}else{
				this.updateMessage = GetLocale("Failed to check available update")
				console.log(`Failed to get update: ${res.message}`)
			}
		})
	}
}
</script>

<template>
	<div class="col-md-3 col-lg-2 d-md-block p-2 navbar-container"
	     :class="{active: this.dashboardConfigurationStore.ShowNavBar}"
	     :data-bs-theme="dashboardConfigurationStore.Configuration.Server.dashboard_theme"
	>
		<nav id="sidebarMenu" class=" bg-body-tertiary sidebar border h-100 rounded-3 shadow overflow-y-scroll" >
			<div class="sidebar-sticky ">
				<div class="text-white m-0 py-3 mb-3 nav-brand d-flex flex-wrap align-items-center justify-content-between">
				<div class="position-relative">
					<h5 class="dashboardNavBarLogo m-0">
					WireGate
					</h5>
					<div class="text-xs opacity-75 mb-1" style="padding-left: 70px;">Dashboard</div>
				</div>
				<small class="d-inline-flex align-items-center" v-if="getActiveCrossServer !== undefined">
					<i class="bi bi-hdd-rack-fill me-2"></i>
					<span class="text-truncate">{{getActiveCrossServer.host}}</span>
				</small>
				</div>
				<ul class="nav flex-column px-2">
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
					<li class="nav-item">
						<a class="nav-link rounded-3" role="button" @click="openHelpModal = true">
							<i class="bi bi-question-circle me-2"></i>
							<LocaleText t="Help"></LocaleText>
						</a>
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
						   class="nav-link text-success rounded-3 d-flex align-items-center" 
						   target="_blank">
							<i class="bi bi-arrow-up-circle me-2"></i>
							<div class="d-flex flex-column">
								<small><LocaleText :t="this.updateMessage"></LocaleText></small>
								<small class="text-muted">
									<LocaleText t="Current Version:"></LocaleText> 
									{{ dashboardConfigurationStore.Configuration.Server.version }}
								</small>
							</div>
						</a>
						<div v-else class="nav-link text-muted rounded-3 d-flex align-items-center">
							<i class="bi bi-check-circle me-2"></i>
							<div class="d-flex flex-column">
								<small><LocaleText :t="this.updateMessage"></LocaleText></small>
								<small>{{ dashboardConfigurationStore.Configuration.Server.version }}</small>
							</div>
						</div>
					</li>
				</ul>
			</div>
		</nav>
		<Transition name="zoom">
			<HelpModal v-if="this.openHelpModal" @close="openHelpModal = false;"></HelpModal>
		</Transition>
	</div>
</template>

<style scoped>



.nav-link.active {
	background: linear-gradient(234deg, var(--brandColor4) 0%, var(--brandColor6) 100%);
	color: white !important;
	font-weight: 500;
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
</style>