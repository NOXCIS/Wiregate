import {defineStore} from "pinia";
import {fetchGet} from "@/utilities/fetch.js";
import isCidr from "is-cidr";

export const WireguardConfigurationsStore = defineStore('WireguardConfigurationsStore', {
	state: () => ({
		Configurations: undefined,
		searchString: "",
		PeerScheduleJobs: {
			dropdowns: {
				Field: [
					{
						display: "Total Received",
						value: "total_receive",
						unit: "GB",
						type: 'number'
					},
					{
						display: "Total Sent",
						value: "total_sent",
						unit: "GB",
						type: 'number'
					},
					{
						display: "Total Data",
						value: "total_data",
						unit: "GB",
						type: 'number'
					},
					{
						display: "Date",
						value: "date",
						type: 'date'
					}
				],
				Operator: [
					{
						display: "equal",
						value: "eq"
					},
					{
						display: "not equal",
						value: "neq"
					},
					{
						display: "larger than",
						value: "lgt"
					},
					{
						display: "less than",
						value: "lst"
					},
				],
				Action: [
					{
						display: "Restrict Peer",
						value: "restrict"
					},
					{
						display: "Delete Peer",
						value: "delete"
					}
				]
			}
		}
	}),
	actions: {
		async getConfigurations(){
			await fetchGet("/api/getWireguardConfigurations", {}, (res) => {
				if (res.status)  this.Configurations = res.data
			});
		},
		regexCheckIP(ip){
			let regex = /((^\s*((([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\s*$)|(^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$))/;
			return regex.test(ip)
		},
		checkCIDR(ip){
			return isCidr(ip) !== 0
		},
		
	}
});