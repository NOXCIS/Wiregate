import {defineStore} from "pinia";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import isCidr from "is-cidr";
import {GetLocale} from "@/utilities/locale.js";

export const WireguardConfigurationsStore = defineStore('WireguardConfigurationsStore', {
	state: () => ({
		Configurations: undefined,
		searchString: "",
		ConfigurationListInterval: undefined,
		PeerScheduleJobs: {
			dropdowns: {
				Field: [
					{
						display: GetLocale("Total Received"),
						value: "total_receive",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Total Sent"),
						value: "total_sent",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Total Usage"),
						value: "total_data",
						unit: "GB",
						type: 'number'
					},
					{
						display: GetLocale("Date"),
						value: "date",
						type: 'date'
					},
					{
						display: GetLocale("Weekly Schedule"),
						value: "weekly",
						type: 'multiDayTime',
						options: [
							{ label: GetLocale("Monday"), value: "0" },
							{ label: GetLocale("Tuesday"), value: "1" },
							{ label: GetLocale("Wednesday"), value: "2" },
							{ label: GetLocale("Thursday"), value: "3" },
							{ label: GetLocale("Friday"), value: "4" },
							{ label: GetLocale("Saturday"), value: "5" },
							{ label: GetLocale("Sunday"), value: "6" }
						]
					}
				],
				Operator: [
					{
						display: GetLocale("equal to"),
						value: "eq"
					},
					{
						display: GetLocale("not equal to"),
						value: "neq"
					},
					{
						display: GetLocale("larger than"),
						value: "lgt"
					},
					{
						display: GetLocale("less than"),
						value: "lst"
					}
				],
				Action: [
					{
						display: GetLocale("Allow Peer"),
						value: "allow"
					},
					{
						display: GetLocale("Restrict Peer"),
						value: "restrict"
					},
					{
						display: GetLocale("Delete Peer"),
						value: "delete"
					},
					{
						display: GetLocale("Set Rate Limit"),
						value: "rate_limit",
						defaultRates: {
							upload_rate: 1000,
							download_rate: 1000
						}
					}
				]
			}
		},
		eventSource: null,
		peerRateLimits: {},
		fetchingRateLimit: false,
		rateLimitError: null,
	}),
	actions: {
		async getConfigurations(){
			await fetchGet("/api/getConfigurations", {}, (res) => {
				if (res.status)  this.Configurations = res.data
				// this.Configurations = []
			});
		},
		regexCheckIP(ip){
			let regex = /((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))/;
			return regex.test(ip)
		},
		checkCIDR(ip){
			return isCidr(ip) !== 0
		},
		checkWGKeyLength(key){
			console.log(key)
			const reg = /^[A-Za-z0-9+/]{43}=?=?$/;
			return reg.test(key)
		},
		initConfigStatusStream() {
			this.eventSource = new EventSource('/api/config-status-stream')
			this.eventSource.onmessage = (event) => {
				this.Configurations = JSON.parse(event.data)
			}
		},
		cleanup() {
			if (this.eventSource) {
				this.eventSource.close()
			}
		},
		async fetchPeerRateLimit(interfaceName, peerKey) {
			this.fetchingRateLimit = true;
			this.rateLimitError = null;
			
			try {
				await fetchGet("/api/get_peer_rate_limit", {
					interface: interfaceName,
					peer_key: peerKey
				}, (response) => {
					if (!response?.status) {
						throw new Error(response?.message || 'Failed to fetch rate limits');
					}
					
					this.peerRateLimits[peerKey] = {
						upload_rate: response.data?.upload_rate ?? 0,
						download_rate: response.data?.download_rate ?? 0
					};
				});
			} catch (error) {
				console.error('Fetch error:', error);
				this.rateLimitError = error.message || 'Failed to fetch rate limits';
				this.peerRateLimits[peerKey] = { upload_rate: 0, download_rate: 0 };
			} finally {
				this.fetchingRateLimit = false;
			}
		},
		async setPeerRateLimit(interfaceName, peerKey, uploadRate, downloadRate) {
			try {
				await fetchPost("/api/set_peer_rate_limit", {
					interface: interfaceName,
					peer_key: peerKey,
					upload_rate: uploadRate,
					download_rate: downloadRate
				}, (response) => {
					if (response?.status) {
						this.peerRateLimits[peerKey] = {
							upload_rate: uploadRate,
							download_rate: downloadRate
						};
						return true;
					}
					throw new Error(response?.message || 'Failed to set rate limits');
				});
			} catch (error) {
				console.error('Request error:', error);
				throw error;
			}
		},
		async removePeerRateLimit(interfaceName, peerKey) {
			try {
				await fetchPost("/api/remove_peer_rate_limit", {
					interface: interfaceName,
					peer_key: peerKey
				}, (response) => {
					if (response?.status) {
						this.peerRateLimits[peerKey] = { upload_rate: 0, download_rate: 0 };
						return true;
					}
					throw new Error(response?.message || 'Failed to remove rate limit');
				});
			} catch (error) {
				console.error('Request error:', error);
				throw error;
			}
		}
	}
});