<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import PeersDefaultSettingsInput from "@/components/settingsComponent/peersDefaultSettingsInput.vue";
import {ipV46RegexCheck} from "@/utilities/ipCheck.js";
import AccountSettingsInputUsername from "@/components/settingsComponent/accountSettingsInputUsername.vue";
import AccountSettingsInputPassword from "@/components/settingsComponent/accountSettingsInputPassword.vue";
import DashboardSettingsInputWireguardConfigurationPath
	from "@/components/settingsComponent/dashboardSettingsInputWireguardConfigurationPath.vue";
import DashboardTheme from "@/components/settingsComponent/dashboardTheme.vue";
import DashboardSettingsInputIPAddressAndPort
	from "@/components/settingsComponent/dashboardSettingsInputIPAddressAndPort.vue";
import DashboardAPIKeys from "@/components/settingsComponent/dashboardAPIKeys.vue";
import AccountSettingsMFA from "@/components/settingsComponent/accountSettingsMFA.vue";
import LocaleText from "@/components/text/localeText.vue";
import DashboardLanguage from "@/components/settingsComponent/dashboardLanguage.vue";
import DashboardIPPortInput from "@/components/settingsComponent/dashboardIPPortInput.vue";

export default {
	name: "settings",
	methods: {ipV46RegexCheck},
	components: {
		DashboardIPPortInput,
		DashboardLanguage,
		LocaleText,
		AccountSettingsMFA,
		DashboardAPIKeys,
		DashboardSettingsInputIPAddressAndPort,
		DashboardTheme,
		DashboardSettingsInputWireguardConfigurationPath,
		AccountSettingsInputPassword, AccountSettingsInputUsername, PeersDefaultSettingsInput},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore()
		return {dashboardConfigurationStore}
	},
}
</script>

<template>
	<div class="mt-md-5 mt-3">
		<div class="container-md">
			<h3 class="mb-3 text-body">
				<LocaleText t="Settings"></LocaleText>
			</h3>
			
			<div class="card mb-4 shadow rounded-3">
				<p class="card-header">
					<LocaleText t="Peers Default Settings"></LocaleText>
				</p>
				<div class="card-body">
					<PeersDefaultSettingsInput 
						targetData="peer_global_dns" title="DNS"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput 
						targetData="peer_endpoint_allowed_ip" title="Endpoint Allowed IPs"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput 
						targetData="peer_mtu" title="MTU"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput 
						targetData="peer_keep_alive" title="Persistent Keepalive"></PeersDefaultSettingsInput>
					<PeersDefaultSettingsInput 
						targetData="remote_endpoint" title="Peer Remote Endpoint"
					                           :warning="true" warningText="This will be changed globally, and will be apply to all peer's QR code and configuration file."
					></PeersDefaultSettingsInput>
				</div>
			</div>
			<div class="card mb-4 shadow rounded-3">
				<p class="card-header">
					<LocaleText t="WireGuard Configurations Settings"></LocaleText>
				</p>
				<div class="card-body">
					<DashboardSettingsInputWireguardConfigurationPath
						targetData="wg_conf_path"
						title="Configurations Directory"
						:warning="true"
						warning-text="Remember to remove / at the end of your path. e.g /etc/wireguard"
					>
					</DashboardSettingsInputWireguardConfigurationPath>
				</div>
			</div>
			<hr class="mb-4">
			<div class="row gx-4">
				<div class="col-sm">
					<DashboardTheme></DashboardTheme>
				</div>
				<div class="col-sm">
					<DashboardLanguage></DashboardLanguage>
				</div>

			</div>
			<DashboardIPPortInput></DashboardIPPortInput>
			
			
			<div class="card mb-4 shadow rounded-3">
				<p class="card-header">
					<LocaleText t="WGDashboard Account Settings"></LocaleText>
				</p>
				<div class="card-body d-flex gap-4 flex-column">
					<AccountSettingsInputUsername targetData="username"
					                              title="Username"
					></AccountSettingsInputUsername>
					<hr class="m-0">
					<AccountSettingsInputPassword
						targetData="password">
					</AccountSettingsInputPassword>
					<hr class="m-0" v-if="!this.dashboardConfigurationStore.getActiveCrossServer()">
					<AccountSettingsMFA v-if="!this.dashboardConfigurationStore.getActiveCrossServer()"></AccountSettingsMFA>
				</div>
			</div>
			<DashboardAPIKeys></DashboardAPIKeys>
		</div>
	</div>
</template>

<style scoped>

</style>