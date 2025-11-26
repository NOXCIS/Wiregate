<script>
import dayjs from "dayjs";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import VueDatePicker from "@vuepic/vue-datepicker";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "newDashboardAPIKey",
	components: {LocaleText, VueDatePicker},
	data(){
		return{
			newKeyData:{
				ExpiredAt: dayjs().add(7, 'd').format("YYYY-MM-DD HH:mm:ss"),
				neverExpire: false
			},
			submitting: false,
			createdKey: null,
			keyCopied: false
		}
	},
	setup(){
		const store = DashboardConfigurationStore();
		return {store};
	},
	mounted() {
		console.log(this.newKeyData.ExpiredAt)
	},
	
	methods: {
		submitNewAPIKey(){
			console.log('[newDashboardAPIKey] Submitting new API key request:', this.newKeyData);
			this.submitting = true;
			fetchPost('/api/newDashboardAPIKey', this.newKeyData, (res) => {
				console.log('[newDashboardAPIKey] Response received:', res);
				if (res.status){
					// Store the newly created key from the message field
					this.createdKey = res.message || (res.data && res.data.find(k => k._isNew)?.Key);
					this.keyCopied = false;
					console.log('[newDashboardAPIKey] Success! Created key stored for one-time display');
					// Don't close yet - show the key first
				}else{
					console.error('[newDashboardAPIKey] Error:', res.message);
					this.store.newMessage("Server", res.message, "danger");
					this.submitting = false;
				}
			})
		},
		copyKeyToClipboard(){
			if (this.createdKey){
				navigator.clipboard.writeText(this.createdKey).then(() => {
					this.keyCopied = true;
					this.store.newMessage("Server", "API Key copied to clipboard", "success");
					// After copy, mask the key and close
					setTimeout(() => {
						this.createdKey = null;
						this.keyCopied = false;
						// Refresh the keys list (will show masked keys)
						this.$emit('created', null); // Trigger refresh
						this.$emit('close');
					}, 1000);
				}).catch(err => {
					console.error('[newDashboardAPIKey] Failed to copy:', err);
					this.store.newMessage("Server", "Failed to copy API key", "danger");
				});
			}
		},
		skipKeyDisplay(){
			// User chose to skip viewing the key
			this.createdKey = null;
			this.keyCopied = false;
			this.$emit('created', null); // Trigger refresh
			this.$emit('close');
		},
		fixDate(date){
			console.log(dayjs(date).format("YYYY-MM-DDTHH:mm:ss"))
			return dayjs(date).format("YYYY-MM-DDTHH:mm:ss")
		},
		parseTime(modelData){
			if(modelData){
				this.newKeyData.ExpiredAt = dayjs(modelData).format("YYYY-MM-DD HH:mm:ss");
			}else{
				this.newKeyData.ExpiredAt = undefined
			}
		}
	}
}
</script>

<template>
	<div class="position-absolute w-100 h-100 top-0 start-0 rounded-bottom-3 p-3 d-flex"
	     style="background-color: #00000060; backdrop-filter: blur(3px)">
		<div class="card m-auto rounded-3 mt-5" style="max-width: 600px;">
			<!-- Key Display View (shown after creation) -->
			<template v-if="this.createdKey">
				<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
					<h6 class="mb-0">
						<LocaleText t="API Key Created"></LocaleText>
					</h6>
					<button type="button" class="btn-close ms-auto" @click="this.skipKeyDisplay()"></button>
				</div>
				<div class="card-body d-flex gap-3 p-4 flex-column">
					<div class="alert alert-warning d-flex align-items-center gap-2" role="alert">
						<i class="bi bi-exclamation-triangle-fill"></i>
						<small>
							<LocaleText t="This is the only time you will see this API key. Copy it now and store it securely."></LocaleText>
						</small>
					</div>
					<div class="d-flex flex-column gap-2">
						<label class="text-muted small">
							<LocaleText t="Your API Key"></LocaleText>
						</label>
						<div class="input-group">
							<input type="text" 
							       class="form-control font-monospace" 
							       :value="this.createdKey" 
							       readonly
							       id="apiKeyInput"
							       style="font-size: 0.9rem;">
							<button class="btn btn-outline-primary" 
							        type="button" 
							        @click="this.copyKeyToClipboard()"
							        :disabled="this.keyCopied">
								<i class="bi bi-clipboard-check-fill me-2" v-if="this.keyCopied"></i>
								<i class="bi bi-clipboard me-2" v-else></i>
								<LocaleText t="Copied!" v-if="this.keyCopied"></LocaleText>
								<LocaleText t="Copy" v-else></LocaleText>
							</button>
						</div>
					</div>
					<div class="d-flex gap-2 justify-content-end mt-2">
						<button class="btn btn-secondary" @click="this.skipKeyDisplay()">
							<LocaleText t="I've Copied It"></LocaleText>
						</button>
					</div>
				</div>
			</template>
			
			<!-- Creation Form View (shown initially) -->
			<template v-else>
				<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
					<h6 class="mb-0">
						<LocaleText t="Create API Key"></LocaleText>
					</h6>
					<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
				</div>
				<div class="card-body d-flex gap-2 p-4 flex-column">
					<small class="text-muted">
						<LocaleText t="When should this API Key expire?"></LocaleText>
					</small>
					<div class="d-flex align-items-center gap-2">
						<VueDatePicker
							:is24="true"
							:min-date="new Date()"
							:model-value="this.newKeyData.ExpiredAt"
							@update:model-value="this.parseTime" time-picker-inline
							format="yyyy-MM-dd HH:mm:ss"
							preview-format="yyyy-MM-dd HH:mm:ss"
							:clearable="false"
							:disabled="this.newKeyData.neverExpire || this.submitting"
							:dark="this.store.Configuration.Server.dashboard_theme === 'dark'"
						/>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="checkbox"
						       v-model="this.newKeyData.neverExpire" id="neverExpire" :disabled="this.submitting">
						<label class="form-check-label" for="neverExpire">
							<LocaleText t="Never Expire"></LocaleText> (<i class="bi bi-emoji-grimace-fill me-2"></i> 
							<LocaleText t="Don't think that's a good idea"></LocaleText>)
						</label>
					</div>
					<button class="ms-auto btn bg-success-subtle text-success-emphasis border-1 border-success-subtle rounded-3 shadow-sm"
						:class="{disabled: this.submitting}"
					        @click="this.submitNewAPIKey()"
					>
						<i class="bi bi-check-lg me-2" v-if="!this.submitting"></i>
						<LocaleText t="Creating..." v-if="this.submitting"></LocaleText>
						<LocaleText t="Create" v-else></LocaleText>
					</button>
				</div>
			</template>
		</div>
	</div>
</template>

<style scoped>

</style>