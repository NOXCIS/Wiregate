import {defineStore} from "pinia";
import {fetchGet} from "@/utilities/fetch.js";


export const WiregateDashboardStore = defineStore('WiregateDashboardStore', {
	state: () => ({
		WireguardConfigurations: undefined,
		DashboardConfiguration: undefined
	}),
	actions: {
		async getDashboardConfiguration(){
			await fetchGet("/api/getDashboardConfiguration", {}, (res) => {
				console.log(res.status)
				if (res.status)  this.DashboardConfiguration = res.data
			})
		}
	}
});


