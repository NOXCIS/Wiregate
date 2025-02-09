<script setup async>
import {computed, onMounted, ref, watch} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import LocaleText from "@/components/text/localeText.vue";
import EndpointAllowedIps from "@/components/configurationComponents/newPeersComponents/endpointAllowedIps.vue";
import AllowedIPsInput from "@/components/configurationComponents/newPeersComponents/allowedIPsInput.vue";
import DnsInput from "@/components/configurationComponents/newPeersComponents/dnsInput.vue";
import NameInput from "@/components/configurationComponents/newPeersComponents/nameInput.vue";
import PrivatePublicKeyInput from "@/components/configurationComponents/newPeersComponents/privatePublicKeyInput.vue";
import BulkAdd from "@/components/configurationComponents/newPeersComponents/bulkAdd.vue";
import PresharedKeyInput from "@/components/configurationComponents/newPeersComponents/presharedKeyInput.vue";
import MtuInput from "@/components/configurationComponents/newPeersComponents/mtuInput.vue";
import PersistentKeepAliveInput
	from "@/components/configurationComponents/newPeersComponents/persistentKeepAliveInput.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";

const dashboardStore = DashboardConfigurationStore()
const wireguardStore = WireguardConfigurationsStore()

const autoSelectFirstAvailableIPs = (ips) => {
	const ipv4Address = ips.find(ip => ip.includes('.')) // Find first IPv4
	const ipv6Address = ips.find(ip => ip.includes(':')) // Find first IPv6
	
	if (ipv4Address) {
		peerData.value.allowed_ips.push(`${ipv4Address}/32`)
	}
	
	if (ipv6Address) {
		peerData.value.allowed_ips.push(`${ipv6Address}/128`)
	}
}

const peerData = ref({
	bulkAdd: false,
	bulkAddAmount: 0,
	name: "",
	allowed_ips: [],
	private_key: "",
	public_key: "",
	DNS: dashboardStore.Configuration.Peers.peer_global_dns,
	endpoint_allowed_ip: dashboardStore.Configuration.Peers.peer_endpoint_allowed_ip,
	keepalive: parseInt(dashboardStore.Configuration.Peers.peer_keep_alive),
	mtu: parseInt(dashboardStore.Configuration.Peers.peer_mtu),
	preshared_key: "",
	preshared_key_bulkAdd: false,
	advanced_security: "off",
	override_allowed_ips: false,
})

const availableIp = ref([])
const saving = ref(false)

const route = useRoute()
await fetchGet("/api/getAvailableIPs/" + route.params.id, {}, (res) => {
	if (res.status) {
		availableIp.value = res.data
		if (!peerData.value.bulkAdd) {
			autoSelectFirstAvailableIPs(availableIp.value)
		}
	}
})

const emits = defineEmits(['close'])

const getProtocol = computed(() => {
	return wireguardStore.Configurations.find(x => x.Name === route.params.id).Protocol;
})

const allRequireFieldsFilled = computed(() => {
	let status = true;
	if (peerData.value.bulkAdd){
		if(peerData.value.bulkAddAmount.length === 0 || peerData.value.bulkAddAmount > availableIp.value.length){
			status = false;
		}
	}else{
		let requireFields =
			["allowed_ips", "private_key", "public_key", "endpoint_allowed_ip", "keepalive", "mtu"]
		requireFields.forEach(x => {
			if (peerData.value[x].length === 0) status = false;
		});
	}
	return status;
})

const peerCreate = () => {
	saving.value = true
	fetchPost("/api/addPeers/" + route.params.id, peerData.value, (res) => {
		if (res.status){
			dashboardStore.newMessage("Server", "Peer created successfully", "success")
			emits('addedPeers')
		}else{
			dashboardStore.newMessage("Server", res.message, "danger")
		}
		saving.value = false;
	})
}

watch(() => {
	return peerData.value.bulkAddAmount
}, () => {
	if (peerData.value.bulkAddAmount > availableIp.value.length){
		peerData.value.bulkAddAmount = availableIp.value.length
	}
})

watch(() => peerData.value.bulkAdd, (newVal) => {
	peerData.value.allowed_ips = []
	if (!newVal) {
		autoSelectFirstAvailableIPs(availableIp.value)
	}
})
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll" ref="editConfigurationContainer">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 1000px">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Add Peers"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
					</div>
					<div class="card-body px-4 pb-4">
						<div class="d-flex flex-column gap-2">
							<BulkAdd :saving="saving" :data="peerData" :availableIp="availableIp"></BulkAdd>
							<hr class="mb-0 mt-2">
							<NameInput :saving="saving" :data="peerData" v-if="!peerData.bulkAdd"></NameInput>
							<PrivatePublicKeyInput :saving="saving" :data="peerData" v-if="!peerData.bulkAdd"></PrivatePublicKeyInput>
							<AllowedIPsInput :availableIp="availableIp" :saving="saving" :data="peerData" v-if="!peerData.bulkAdd"></AllowedIPsInput>
							<EndpointAllowedIps :saving="saving" :data="peerData"></EndpointAllowedIps>
							<DnsInput :saving="saving" :data="peerData"></DnsInput>
						</div>
						<hr>
						<div class="row gy-3">
							<div class="col-sm" v-if="!peerData.bulkAdd">
								<PresharedKeyInput :saving="saving" :data="peerData" :bulk="peerData.bulkAdd"></PresharedKeyInput>
							</div>

							<div class="col-sm">
								<MtuInput :saving="saving" :data="peerData"></MtuInput>
							</div>
							<div class="col-sm">
								<PersistentKeepAliveInput :saving="saving" :data="peerData"></PersistentKeepAliveInput>
							</div>
							<div class="col-12" v-if="peerData.bulkAdd">
								<div class="form-check form-switch">
									<input class="form-check-input" type="checkbox" role="switch"
									       v-model="peerData.preshared_key_bulkAdd"
									       id="bullAdd_PresharedKey_Switch" checked>
									<label class="form-check-label" for="bullAdd_PresharedKey_Switch">
										<small class="fw-bold">
											<LocaleText t="Pre-Shared Key"></LocaleText> <LocaleText t="Enabled" v-if="peerData.preshared_key_bulkAdd"></LocaleText><LocaleText t="Disabled" v-else></LocaleText>
										</small>
									</label>
								</div>
							</div>
						</div>
						<hr>
						<div class="d-flex mt-2">
							<button class="ms-auto btn btn-dark btn-brand rounded-3 px-3 py-2 shadow"
							        :disabled="!allRequireFieldsFilled || saving"
							        @click="peerCreate()"
							>
								<i class="bi bi-plus-circle-fill me-2" v-if="!saving"></i>
								<LocaleText t="Adding..." v-if="saving"></LocaleText>
								<LocaleText t="Add" v-else></LocaleText>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>