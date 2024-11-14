import { createRouter, createWebHashHistory } from 'vue-router'
import {cookie} from "../utilities/cookie.js";
// import Index from "@/views/index.vue"
// import Signin from "@/views/signin.vue";
// import ConfigurationList from "@/components/configurationList.vue";
import {fetchGet} from "@/utilities/fetch.js";
// import Settings from "@/views/settings.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
// import Setup from "@/views/setup.vue";
// import NewConfiguration from "@/views/newConfiguration.vue";
// import Configuration from "@/views/configuration.vue";
// import PeerList from "@/components/configurationComponents/peerList.vue";
// import PeerCreate from "@/components/configurationComponents/peerCreate.vue";
// import Ping from "@/views/ping.vue";
// import Traceroute from "@/views/traceroute.vue";
// import Totp from "@/components/setupComponent/totp.vue";
// import Share from "@/views/share.vue";
// import RestoreConfiguration from "@/views/restoreConfiguration.vue";

const checkAuth = async () => {
	let result = false
	await fetchGet("/api/validateAuthentication", {}, (res) => {
		result = res.status
	});
	return result;
}

const router = createRouter({
	history: createWebHashHistory(),
	scrollBehavior(){
		if (document.querySelector("main") !== null){
			document.querySelector("main").scrollTo({
				top: 0
			})
		}
	},
	routes: [
		{
			name: "Index",
			path: '/',
			component: () => import('@/views/index.vue'),
			meta: {
				requiresAuth: true,
			},
			children: [
				{
					name: "Configuration List",
					path: '',
					component: () => import('@/components/configurationList.vue'),
					meta: {
						title: "WireGuard Configurations"
					}
				},
				{
					name: "Settings",
					path: '/settings',
					component: () => import('@/views/settings.vue'),
					meta: {
						title: "Settings"
					}
				},
				{
					path: '/ping',
					name: "Ping",
					component: () => import('@/views/ping.vue'),
				},
				{
					path: '/traceroute',
					name: "Traceroute",
					component: () => import('@/views/traceroute.vue'),
				},
				{
					name: "New Configuration",
					path: '/new_configuration',
					component: () => import('@/views/newConfiguration.vue'),
					meta: {
						title: "New Configuration"
					}
				},
				{
					name: "Restore Configuration",
					path: '/restore_configuration',
					component: () => import('@/views/restoreConfiguration.vue'),
					meta: {
						title: "Restore Configuration"
					}
				},
				{
					name: "Configuration",
					path: '/configuration/:id',
					component: () => import('@/views/configuration.vue'),
					meta: {
						title: "Configuration"
					},
					children: [
						{
							name: "Peers List",
							path: 'peers',
							component: () => import('@/components/configurationComponents/peerList.vue')
						},
						{
							name: "Peers Create",
							path: 'create',
							component: () => import('@/components/configurationComponents/peerCreate.vue')
						},
					]
				},

			]
		},
		{
			path: '/signin', 
			component: () => import('@/views/signin.vue'),
			meta: {
				title: "Sign In",
				hideTopNav: true
			}
		},
		{
			path: '/welcome', 
			component: () => import("@/views/setup.vue"),
			meta: {
				requiresAuth: true,
				title: "Welcome to WGDashboard",
				hideTopNav: true
			},
		},
		{
			path: '/2FASetup', 
			component: () => import("@/components/setupComponent/totp.vue"),
			meta: {
				requiresAuth: true,
				title: "Multi-Factor Authentication Setup",
				hideTopNav: true
			},
		},
		{
			path: '/share', 
			component: () => import("@/views/share.vue"),
			meta: {
				title: "Share",
				hideTopNav: true
			}
		}
	]
});

router.beforeEach(async (to, from, next) => {
	const wireguardConfigurationsStore = WireguardConfigurationsStore();
	const dashboardConfigurationStore = DashboardConfigurationStore();

	if (to.meta.title){
		if (to.params.id){
			document.title = to.params.id + " | WGDashboard";
		}else{
			document.title = to.meta.title + " | WGDashboard";
		}
	}else{
		document.title = "WGDashboard"
	}
	dashboardConfigurationStore.ShowNavBar = false;
	document.querySelector(".loadingBar").classList.remove("loadingDone")
	document.querySelector(".loadingBar").classList.add("loading")
	if (to.meta.requiresAuth){
		if (!dashboardConfigurationStore.getActiveCrossServer()){
			if (cookie.getCookie("authToken") && await checkAuth()){
				await dashboardConfigurationStore.getConfiguration()
				if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
					await wireguardConfigurationsStore.getConfigurations();
				}
				dashboardConfigurationStore.Redirect = undefined;
				next()
			}else{
				dashboardConfigurationStore.Redirect = to;
				next("/signin")
				dashboardConfigurationStore.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
			}
		}else{
			await dashboardConfigurationStore.getConfiguration()
			if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
				await wireguardConfigurationsStore.getConfigurations();
			}
			next()
		}
	}else {
		next();
	}
});

router.afterEach(() => {
	document.querySelector(".loadingBar").classList.remove("loading")
	document.querySelector(".loadingBar").classList.add("loadingDone")
})
export default router