<script>
import QRCode from "qrcode";
import LocaleText from "@/components/text/localeText.vue";
import {fetchGet} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {nextTick} from "vue";

export default {
	name: "peerQRCode",
	components: {LocaleText},
	props: {
		selectedPeer: Object
	},
	setup(){
		const dashboardStore = DashboardConfigurationStore();
		return {dashboardStore}
	},
	data(){
		return{
			loading: true,
			error: null,
			configFile: null,
			fileName: ''
		}
	},
	computed: {
		downloadUrl() {
			if (!this.configFile) return '';
			const blob = new Blob([this.configFile], { type: 'text/plain' });
			return URL.createObjectURL(blob);
		}
	},
	mounted() {
		fetchGet("/api/downloadPeer/"+this.$route.params.id, {
			id: this.selectedPeer.id
		}, (res) => {
			this.loading = false;
			if (res.status){
				this.configFile = res.data.file;
				this.fileName = res.data.fileName || this.selectedPeer.name || 'peer';
				
				// Use nextTick to ensure DOM is updated after loading state change
				nextTick(() => {
					const canvas = this.$refs.qrcode;
					if (canvas && res.data.file) {
						// Use lowest error correction (L) and no margin for max data capacity
						const options = {
							errorCorrectionLevel: 'L',
							margin: 1,
							width: 280
						};
						
						QRCode.toCanvas(canvas, res.data.file, options, (error) => {
							if (error) {
								// If data is too large even with lowest error correction
								if (error.message && error.message.includes('too big')) {
									this.error = 'too_large';
								} else {
									this.error = 'failed';
									console.error(error);
								}
							}
						})
					}
				});
			}else{
				this.dashboardStore.newMessage("Server", res.message, "danger")
			}
		})
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal justify-content-center">
				<div class="card rounded-3 shadow">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h4 class="mb-0">
							<LocaleText t="QR Code"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body p-4">
						<div class="qr-container d-flex justify-content-center align-items-center flex-column" style="min-width: 300px; min-height: 300px;">
							<canvas id="qrcode" ref="qrcode" class="rounded-3 shadow animate__animated animate__fadeIn animate__faster" :class="{'d-none': loading || error}"></canvas>
							<div class="spinner-border m-auto" role="status" v-if="loading">
								<span class="visually-hidden">Loading...</span>
							</div>
							<div v-if="error === 'too_large'" class="text-center p-3 animate__animated animate__fadeIn">
								<i class="bi bi-qr-code text-warning" style="font-size: 3rem;"></i>
								<p class="mt-3 mb-2 text-muted">
									<LocaleText t="Configuration is too large for QR code."></LocaleText>
								</p>
								<p class="text-muted small mb-3">
									<LocaleText t="Please download the config file instead."></LocaleText>
								</p>
								<a 
									v-if="configFile"
									:href="downloadUrl" 
									:download="fileName + '.conf'"
									class="btn btn-primary">
									<i class="bi bi-download me-2"></i>
									<LocaleText t="Download Config"></LocaleText>
								</a>
							</div>
							<div v-else-if="error === 'failed'" class="text-center p-3 animate__animated animate__fadeIn">
								<i class="bi bi-exclamation-triangle text-danger" style="font-size: 3rem;"></i>
								<p class="mt-3 mb-0 text-muted">
									<LocaleText t="Failed to generate QR code."></LocaleText>
								</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.qr-container {
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 10px;
}

#qrcode {
	max-width: 100%;
	height: auto;
}
</style>