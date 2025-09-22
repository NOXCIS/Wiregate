import { createRouter, createWebHashHistory } from 'vue-router'
import {cookie} from "../utilities/cookie.js";
import {fetchGet} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

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
					name: "Tor Configuration",
					path: '/tor-configuration',
					component: () => import('@/views/TorConfiguration.vue'),
					meta: {
						title: "Tor Configuration"
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
					name: "System Status",
					path: '/system_status',
					component: () => import("@/views/systemStatus.vue"),
					meta: {
						title: "System Status"
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
						}
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
		},
		{
			path: '/404',
			name: 'NotFound',
			component: () => import('@/views/404.vue'),
			meta: {
				title: "Page Not Found",
				hideTopNav: false
			}
		},
		{
			path: '/401',
			name: 'Unauthorized',
			component: () => import('@/views/401.vue'),
			meta: {
				title: "Unauthorized",
				hideTopNav: false
			}
		},
		{
			path: '/403',
			name: 'Forbidden',
			component: () => import('@/views/403.vue'),
			meta: {
				title: "Access Forbidden",
				hideTopNav: false
			}
		},
		{
			path: '/429',
			name: 'TooManyRequests',
			component: () => import('@/views/429.vue'),
			meta: {
				title: "Too Many Requests",
				hideTopNav: false
			}
		},
		{
			path: '/:pathMatch(.*)*',
			name: 'CatchAll',
			component: () => import('@/views/404.vue'),
			meta: {
				title: "Page Not Found",
				hideTopNav: false
			}
		}
	]
});

router.beforeEach(async (to, from, next) => {
	const wireguardConfigurationsStore = WireguardConfigurationsStore();
	const dashboardConfigurationStore = DashboardConfigurationStore();

	if (to.meta.title){
		if (to.params.id){
			document.title = to.params.id + " | WireGate";
		}else{
			document.title = to.meta.title + " | WireGate";
		}
	}else{
		document.title = "WireGate"
	}
	dashboardConfigurationStore.ShowNavBar = false;
	dashboardConfigurationStore.loading.overall = true;
	const loadingBar = document.querySelector(".loadingBar");
	if (loadingBar) {
		loadingBar.classList.remove("loadingDone");
		loadingBar.classList.add("loading");
	}
	console.log(to.path)
	if (to.meta.requiresAuth){
		if (!dashboardConfigurationStore.getActiveCrossServer()){
			if (await checkAuth()){
				await dashboardConfigurationStore.getConfiguration()
				if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
					await wireguardConfigurationsStore.getConfigurations();
				}
				dashboardConfigurationStore.Redirect = undefined;
				next()
				
			}else{
				dashboardConfigurationStore.Redirect = to;
				next("/signin")
				dashboardConfigurationStore.newMessage("WireGate", "Sign in session ended, please sign in again", "warning")
			}
		}else{
			await dashboardConfigurationStore.getConfiguration()
			if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
				await wireguardConfigurationsStore.getConfigurations();
			}
			next()
		}
	}else {
		if (to.path === "/signin" && await checkAuth()){
			next("/")
		}else{
			next()
		}
	}
});

router.afterEach(async (to) => {
	// Wait for configuration loading to complete
	const dashboardConfigurationStore = DashboardConfigurationStore();
	
	while (dashboardConfigurationStore.loading.configuration) {
		await new Promise(resolve => setTimeout(resolve, 50));
	}
	
	dashboardConfigurationStore.loading.overall = false;
	
	// For routes that don't have configuration list, complete loading bar after a short delay
	if (to.name !== 'Configuration List' && to.name !== 'Index') {
		setTimeout(() => {
			const loadingBar = document.querySelector(".loadingBar");
			if (loadingBar) {
				loadingBar.classList.remove("loading");
				loadingBar.classList.add("loadingDone");
			}
		}, 300);
	}
	
	// Note: Loading bar completion for Configuration List is handled by the component itself
})
export default router