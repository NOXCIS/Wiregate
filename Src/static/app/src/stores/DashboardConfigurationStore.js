import {defineStore} from "pinia";
import {fetchGet, fetchPost, clearCsrfToken} from "@/utilities/fetch.js";
import {v4} from "uuid";
import {GetLocale} from "@/utilities/locale.js";

export const DashboardConfigurationStore = defineStore('DashboardConfigurationStore', {
	state: () => ({
		Redirect: undefined,
		Configuration: undefined,
		Messages: [],
		Peers: {
			Selecting: false,
			RefreshInterval: undefined
		},
		CrossServerConfiguration:{
			Enable: false,
			ServerList: {}
		},
		SystemStatus: undefined,
		ActiveServerConfiguration: undefined,
		IsElectronApp: false,
		ShowNavBar: false,
		Locale: undefined,
		loading: {
			configuration: false,
			configurations: false,
			overall: false
		},
		// Global interval tracker to stop all polling on session expiration
		registeredIntervals: new Set(),
		// Flag to prevent API calls after session expiration
		sessionExpired: false
	}),
	actions: {
		initCrossServerConfiguration(){
			const currentConfiguration = localStorage.getItem('CrossServerConfiguration');
			if (localStorage.getItem("ActiveCrossServerConfiguration") !== null){
				this.ActiveServerConfiguration = localStorage.getItem("ActiveCrossServerConfiguration");
			}
			if (currentConfiguration === null){
				window.localStorage.setItem('CrossServerConfiguration', JSON.stringify(this.CrossServerConfiguration))
			}else{
				this.CrossServerConfiguration = JSON.parse(currentConfiguration)
			}
		},
		syncCrossServerConfiguration(){
			window.localStorage.setItem('CrossServerConfiguration', JSON.stringify(this.CrossServerConfiguration))
		},
		addCrossServerConfiguration(){
			this.CrossServerConfiguration.ServerList[v4().toString()] = {host: "", apiKey: "", active: false}
		},
		deleteCrossServerConfiguration(key){
			delete this.CrossServerConfiguration.ServerList[key];
		},
		getActiveCrossServer(){
			const key = localStorage.getItem('ActiveCrossServerConfiguration');
			if (key !== null){
				return this.CrossServerConfiguration.ServerList[key]
			}
			return undefined
		},
		setActiveCrossServer(key){
			this.ActiveServerConfiguration = key;
			localStorage.setItem('ActiveCrossServerConfiguration', key)
		},
		removeActiveCrossServer(){
			this.ActiveServerConfiguration = undefined;
			localStorage.removeItem('ActiveCrossServerConfiguration')
		},
		async getConfiguration(){
			this.loading.configuration = true;
			await fetchGet("/api/getDashboardConfiguration", {}, (res) => {
				if (res.status) this.Configuration = res.data
			});
			this.loading.configuration = false;
		},
		async signOut(){
			await fetchGet("/api/signout", {}, () => {
				// Clear CSRF token on logout
				clearCsrfToken();
				// Stop all registered intervals
				this.stopAllIntervals();
				this.removeActiveCrossServer();
				document.cookie = '';
				this.$router.go('/signin')
			});
		},
		// Register an interval so it can be stopped globally on session expiration
		registerInterval(intervalId) {
			if (intervalId) {
				this.registeredIntervals.add(intervalId);
			}
		},
		// Unregister an interval (e.g., when component unmounts)
		unregisterInterval(intervalId) {
			if (intervalId) {
				this.registeredIntervals.delete(intervalId);
			}
		},
		// Stop all registered intervals (called on session expiration)
		stopAllIntervals() {
			this.registeredIntervals.forEach(intervalId => {
				if (intervalId) {
					clearInterval(intervalId);
				}
			});
			this.registeredIntervals.clear();
			// Also clear intervals stored in other stores
			if (this.Peers.RefreshInterval) {
				clearInterval(this.Peers.RefreshInterval);
				this.Peers.RefreshInterval = undefined;
			}
			// Also clear intervals in WireguardConfigurationsStore
			// Use dynamic import to avoid circular dependency issues
			import("@/stores/WireguardConfigurationsStore.js").then(({ WireguardConfigurationsStore }) => {
				const wireguardStore = WireguardConfigurationsStore();
				if (wireguardStore.ConfigurationListInterval) {
					clearInterval(wireguardStore.ConfigurationListInterval);
					wireguardStore.ConfigurationListInterval = undefined;
				}
			}).catch(() => {
				// Ignore errors if store not available
			});
		},
		// Handle session expiration - stop intervals and set flag
		handleSessionExpiration() {
			if (!this.sessionExpired) {
				this.sessionExpired = true;
				this.stopAllIntervals();
			}
		},
		// Reset session expired flag (called on successful login)
		resetSessionExpired() {
			this.sessionExpired = false;
		},
		newMessage(from, content, type){
			this.Messages.push({
				id: v4(),
				from: GetLocale(from),
				content: GetLocale(content),
				type: type,
				show: true
			})
		},
		applyLocale(key){
			if (this.Locale === null) 
				return key
			const reg = Object.keys(this.Locale)
			const match = reg.filter(x => {
				return key.match(new RegExp('^' + x + '$', 'g')) !== null
			})
			console.log(match)
			if (match.length === 0 || match.length > 1){
				return key
			}
			return this.Locale[match[0]]
		}
	}
});