<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {v4} from "uuid";
import {fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "accountSettingsMFA",
	components: {LocaleText},
	setup(){
		const store = DashboardConfigurationStore();
		const uuid = `input_${v4()}`;
		return {store, uuid};
	},
	data(){
		return {
			status: false
		}
	},
	mounted() {
		this.status = this.store.Configuration.Account["enable_totp"]
	},
	methods: {
		async resetMFA(){
			// Use dedicated Reset_MFA endpoint to clear pending key and reset MFA state
			// This ensures a fresh TOTP key is generated for security
			await fetchPost("/api/Reset_MFA", {}, (res) => {
				if (res.status){
					this.$router.push("/2FASetup")
				}
			})
		}
	}
}
</script>

<template>
<div>
	
	<div class="d-flex align-items-center">

		<div class="form-check form-switch">
			<input class="form-check-input" type="checkbox"
			       v-model="this.status"
			       role="switch" id="allowMFAKeysSwitch">
			<label for="allowMFAKeysSwitch">
					<LocaleText t="Enabled" v-if="this.status"></LocaleText>
					<LocaleText t="Disabled" v-else></LocaleText>
				</label>
		</div>
		<button id="mfaToggleBtn" class="btn bg-warning-subtle text-warning-emphasis border-1 border-warning-subtle ms-auto rounded-3 shadow-sm" 
		        v-if="this.status" @click="this.resetMFA()"
		        aria-label="Reset or setup MFA">
			<i class="bi bi-shield-lock-fill me-2"></i>
			<LocaleText t="Reset" v-if='this.store.Configuration.Account["totp_verified"]'></LocaleText>
			<LocaleText t="Setup" v-else></LocaleText>
			MFA
		</button>
	</div>
</div>
</template>

<style scoped>

</style>