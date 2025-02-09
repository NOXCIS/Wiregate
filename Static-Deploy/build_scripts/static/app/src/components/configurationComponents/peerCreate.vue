<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import NameInput from "@/components/configurationComponents/newPeersComponents/nameInput.vue";
import PrivatePublicKeyInput from "@/components/configurationComponents/newPeersComponents/privatePublicKeyInput.vue";
import AllowedIPsInput from "@/components/configurationComponents/newPeersComponents/allowedIPsInput.vue";
import DnsInput from "@/components/configurationComponents/newPeersComponents/dnsInput.vue";
import EndpointAllowedIps from "@/components/configurationComponents/newPeersComponents/endpointAllowedIps.vue";
import PresharedKeyInput from "@/components/configurationComponents/newPeersComponents/presharedKeyInput.vue";
import MtuInput from "@/components/configurationComponents/newPeersComponents/mtuInput.vue";
import PersistentKeepAliveInput
	from "@/components/configurationComponents/newPeersComponents/persistentKeepAliveInput.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import BulkAdd from "@/components/configurationComponents/newPeersComponents/bulkAdd.vue";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "peerCreate",
	components: {
		LocaleText,
		BulkAdd,
		PersistentKeepAliveInput,
		MtuInput,
		PresharedKeyInput, EndpointAllowedIps, DnsInput, AllowedIPsInput, PrivatePublicKeyInput, NameInput},
	data(){
		return{
			data: {
				bulkAdd: false,
				bulkAddAmount: 0,
				name: "",
				allowed_ips: [],
				private_key: "",
				public_key: "",
				DNS: this.dashboardStore.Configuration.Peers.peer_global_dns,
				endpoint_allowed_ip: this.dashboardStore.Configuration.Peers.peer_endpoint_allowed_ip,
				keepalive: parseInt(this.dashboardStore.Configuration.Peers.peer_keep_alive),
				mtu: parseInt(this.dashboardStore.Configuration.Peers.peer_mtu),
				preshared_key: "",
				preshared_key_bulkAdd: false,
				advanced_security: "off",
			},
			availableIp: undefined,
			availableIpSearchString: "",
			saving: false,
			allowedIpDropdown: undefined
		}
	},
	mounted() {
		fetchGet("/api/getAvailableIPs/" + this.$route.params.id, {}, (res) => {
			if (res.status){
				this.availableIp = res.data;
			}
		})
	},
	setup(){
		const store = WireguardConfigurationsStore();
		const dashboardStore = DashboardConfigurationStore();
		return {store, dashboardStore}
	}, 
	methods: {
		peerCreate(){
			this.saving = true
			fetchPost("/api/addPeers/" + this.$route.params.id, this.data, (res) => {
				if (res.status){
					this.$router.push(`/configuration/${this.$route.params.id}/peers`)
					this.dashboardStore.newMessage("Server", "Peer created successfully", "success")
				}else{
					this.dashboardStore.newMessage("Server", res.message, "danger")
				}
				this.saving = false;
			})
		}	
	},
	computed:{
		allRequireFieldsFilled(){
			let status = true;
			if (this.data.bulkAdd){
				if(this.data.bulkAddAmount.length === 0 || this.data.bulkAddAmount > this.availableIp.length){
					status = false;
				}
			}else{
				let requireFields =
					["allowed_ips", "private_key", "public_key", "endpoint_allowed_ip", "keepalive", "mtu"]
				requireFields.forEach(x => {
					if (this.data[x].length === 0) status = false;
				});
			}
			return status;
		},
		getProtocol(){
			return this.store.Configurations.find(x => x.Name === this.$route.params.id).Protocol;
		}
	},
	watch: {
		bulkAdd(newVal){
			if(!newVal){
				this.data.bulkAddAmount = "";
			}
		},
		'data.bulkAddAmount'(){
			if (this.data.bulkAddAmount > this.availableIp.length){
				this.data.bulkAddAmount = this.availableIp.length;
			}
		}
	}
}
</script>

<template>
	<div class="modal-overlay position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center">
		<div class="modal-backdrop position-fixed top-0 start-0 w-100 h-100" 
			 style="background: rgba(0,0,0,0.3); backdrop-filter: blur(2px);"
			 @click="$router.push('/peers')">
		</div>
		
		<div class="modal-content bg-dark bg-opacity-50 rounded-3 shadow p-4" 
			 style="width: 100%; max-width: 800px; z-index: 1050;">
			<div class="mb-4 d-flex align-items-center gap-4">
				<RouterLink to="peers"
						  class="btn btn-dark btn-brand p-2 shadow" 
						  style="border-radius: 100%">
					<h2 class="mb-0" style="line-height: 0">
						<i class="bi bi-arrow-left-circle"></i>
					</h2>
				</RouterLink>
				<h2 class="mb-0">
					<LocaleText t="Add Peers"></LocaleText>
				</h2>
			</div>

			<div class="d-flex flex-column gap-2">
				<BulkAdd :saving="saving" :data="data" :availableIp="availableIp"></BulkAdd>
				<hr class="mb-0 mt-2">
				<NameInput :saving="saving" :data="data" v-if="!data.bulkAdd"></NameInput>
				<PrivatePublicKeyInput :saving="saving" :data="data" v-if="!data.bulkAdd"></PrivatePublicKeyInput>
				<AllowedIPsInput :availableIp="availableIp" :saving="saving" :data="data" v-if="!data.bulkAdd"></AllowedIPsInput>
				<EndpointAllowedIps :saving="saving" :data="data"></EndpointAllowedIps>
				<DnsInput :saving="saving" :data="data"></DnsInput>

				<hr class="mb-0 mt-2">
				<div class="row gy-3">
					<div class="col-sm" v-if="!data.bulkAdd">
						<PresharedKeyInput :saving="saving" :data="data"></PresharedKeyInput>
					</div>
					
					<div class="col-sm">
						<MtuInput :saving="saving" :data="data"></MtuInput>
					</div>
					<div class="col-sm">
						<PersistentKeepAliveInput :saving="saving" :data="data"></PersistentKeepAliveInput>
					</div>
				</div>
				<hr>
				
				<div class="d-flex mt-2">
					<button class="ms-auto btn btn-dark btn-brand rounded-3 px-3 py-2 shadow"
							:disabled="!allRequireFieldsFilled || saving"
							@click="peerCreate()">
						<span v-if="!saving">
							<i class="bi bi-plus-circle-fill me-2"></i>
							<LocaleText t="Add"></LocaleText>
						</span>
						<span v-else>
							<span class="spinner-border spinner-border-sm me-2"></span>
							<LocaleText t="Adding..."></LocaleText>
						</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.modal-overlay {
	z-index: 1040;
}

.modal-content {
	border: 1px solid rgba(255, 255, 255, 0.1);
	backdrop-filter: blur(2px);
}

div {
	transition: 0.2s ease-in-out;
}

.inactiveField {
	opacity: 0.4;
}
</style>