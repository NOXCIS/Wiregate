<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {v4} from "uuid";
import {fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	components: {LocaleText},
	props:{
		targetData: String,
		title: String,
		description: {
			type: String,
			default: ""
		}
	},
	setup(){
		const store = DashboardConfigurationStore();
		const uuid = `switch_${v4()}`;
		return {store, uuid};
	},
	data(){
		return{
			value: false,
			isValid: false,
			timeout: undefined,
			changed: false,
			updating: false,
		}
	},
	mounted() {
		const configValue = this.store.Configuration.Peers[this.targetData];
		this.value = configValue === "true" || configValue === true;
	},
	methods:{
		async toggleValue(){
			this.value = !this.value;
			this.changed = true;
			await this.saveValue();
		},
		async saveValue(){
			if(this.changed){
				this.updating = true;
				await fetchPost("/api/updateDashboardConfigurationItem", {
					section: "Peers",
					key: this.targetData,
					value: this.value ? "true" : "false"
				}, (res) => {
					if (res.status){
						this.isValid = true;
						this.store.Configuration.Peers[this.targetData] = this.value ? "true" : "false";
						clearTimeout(this.timeout);
						this.timeout = setTimeout(() => this.isValid = false, 3000);
					}
					this.changed = false;
					this.updating = false;
				})
			}
		}
	}
}
</script>

<template>
	<div class="form-group mb-2">
		<div class="form-check form-switch d-flex align-items-center">
			<input class="form-check-input" type="checkbox" role="switch"
			       :id="this.uuid"
			       :checked="this.value"
			       @change="toggleValue()"
			       :disabled="this.updating"
			>
			<label class="form-check-label ms-2" :for="this.uuid">
				<strong><small>
					<LocaleText :t="this.title"></LocaleText>
				</small></strong>
				<i v-if="isValid" class="bi bi-check-circle-fill text-success ms-2"></i>
			</label>
		</div>
		<small v-if="description" class="text-muted d-block mt-1">
			<LocaleText :t="description"></LocaleText>
		</small>
	</div>
</template>

<style scoped>
.form-check-input {
	cursor: pointer;
}
.form-check-input:disabled {
	cursor: not-allowed;
}
</style>

