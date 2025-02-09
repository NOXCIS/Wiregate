<script>
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import "animate.css"
import PeerSettingsDropdown from "@/components/configurationComponents/peerSettingsDropdown.vue";
import LocaleText from "@/components/text/localeText.vue";
import PeerRateLimitSettings from '@/components/configurationComponents/peerRateLimitSettings.vue'
import { WireguardConfigurationsStore } from "@/stores/WireguardConfigurationsStore.js"


export default {
	name: "peer",
	components: {LocaleText, PeerSettingsDropdown, PeerRateLimitSettings},
	emits: [
		'share',
		'refresh',
		'jobs',
		'setting',
		'rateLimit',
		'qrcode',
		'configurationFile',
		'showToast'
	],
	props: {
		Peer: Object,
		configurationName: String
	},
	data(){
		return {
			showRateLimitSettings: false,
			rateUnit: 'Mb'
		}
	},
	setup(){
		const target = ref(null);
		const subMenuOpened = ref(false)
		const wireguardStore = WireguardConfigurationsStore()
		onClickOutside(target, event => {
			subMenuOpened.value = false;
		});
		return {target, subMenuOpened, wireguardStore}
	},
	computed: {
		getLatestHandshake(){
			if (this.Peer.latest_handshake.includes(",")){
				return this.Peer.latest_handshake.split(",")[0]
			}
			return this.Peer.latest_handshake;
		},
		peerRateLimit() {
			const limits = this.wireguardStore.peerRateLimits[this.Peer.id] || { upload_rate: 0, download_rate: 0 };
			return {
				upload: this.convertFromKb(limits.upload_rate),
				download: this.convertFromKb(limits.download_rate)
			};
		}
	},
	methods: {
		handleRateLimitSuccess(message) {
			this.showRateLimitSettings = false
			this.$emit('showToast', {
				type: 'success',
				message
			})
		},
		handleRateLimitError(message) {
			this.$emit('showToast', {
				type: 'error',
				message
			})
		},
		toggleRateUnit() {
			const units = ['Kb', 'Mb', 'Gb'];
			const currentIndex = units.indexOf(this.rateUnit);
			this.rateUnit = units[(currentIndex + 1) % units.length];
		},
		convertFromKb(rateInKb) {
			if (!rateInKb) return '∞';
			
			switch (this.rateUnit) {
				case 'Gb':
					return `${(rateInKb / (1024 * 1024)).toFixed(2)}Gb/s`;
				case 'Mb':
					return `${(rateInKb / 1024).toFixed(2)}Mb/s`;
				default:
					return `${rateInKb}Kb/s`;
			}
		}
	}
}
</script>

<template>
	<div class="card shadow-sm rounded-3 peerCard bg-transparent"
		:class="{'border-warning': Peer.restricted}">
		<div>
			<div v-if="!Peer.restricted" class="card-header bg-transparent d-flex align-items-center gap-2 border-0">
				<div class="dot ms-0" :class="{active: Peer.status === 'running'}"></div>
				<div style="font-size: 0.8rem" class="ms-auto d-flex gap-2">
					<span class="text-primary">
						<i class="bi bi-arrow-down"></i><strong>
						{{(Peer.cumu_receive + Peer.total_receive).toFixed(4)}}</strong> GB
						<small class="text-muted ms-1">
							({{ peerRateLimit.download }}&nbsp;<i 
							class="bi bi-arrow-repeat" 
							role="button" 
							@click="toggleRateUnit"></i>)
						</small>
					</span>
					<span class="text-success">
						<i class="bi bi-arrow-up"></i><strong>
						{{(Peer.cumu_sent + Peer.total_sent).toFixed(4)}}</strong> GB
						<small class="text-muted ms-1">
							({{ peerRateLimit.upload }}&nbsp;<i 
							class="bi bi-arrow-repeat" 
							role="button" 
							@click="toggleRateUnit"></i>)
						</small>
					</span>
					<span class="text-secondary" v-if="Peer.latest_handshake !== 'No Handshake'">
						<i class="bi bi-arrows-angle-contract"></i>
						{{getLatestHandshake}} ago
					</span>
				</div>
			</div>
			<div v-else class="border-0 card-header bg-transparent text-warning fw-bold" 
			     style="font-size: 0.8rem">
				<i class="bi-lock-fill me-2"></i>
				<LocaleText t="Access Restricted"></LocaleText>
			</div>
		</div>
		<div class="card-body pt-1" style="font-size: 0.9rem">
			<h6>
				{{Peer.name ? Peer.name : 'Untitled Peer'}}
			</h6>
			<div class="mb-1">
				<small class="text-muted">
					<LocaleText t="Public Key"></LocaleText>
				</small>
				<small class="d-block">
					<samp>{{Peer.id}}</samp>
				</small>
			</div>
			<div>
				<small class="text-muted">
					<LocaleText t="Allowed IPs"></LocaleText>
				</small>
				<small class="d-block">
					<samp>{{Peer.allowed_ip}}</samp>
				</small>
			</div>
			<div v-if="Peer.advanced_security">
				<small class="text-muted">
					<LocaleText t="Advanced Security"></LocaleText>
				</small>
				<small class="d-block">
					<samp>{{Peer.advanced_security}}</samp>
				</small>
			</div>
			<div class="d-flex align-items-end">
				
				<div class="ms-auto px-2 rounded-3 subMenuBtn"
				     :class="{active: this.subMenuOpened}"
				>
					<a role="button" class="text-body"
					   @click="this.subMenuOpened = true">
						<h5 class="mb-0"><i class="bi bi-three-dots"></i></h5>
					</a>
					<Transition name="slide-fade">
						<PeerSettingsDropdown 
							@qrcode="(file) => this.$emit('qrcode', file)"
							@configurationFile="(file) => this.$emit('configurationFile', file)"
							@setting="this.$emit('setting')"
							@jobs="this.$emit('jobs')"
							@refresh="this.$emit('refresh')"
							@share="this.$emit('share')"
							@rateLimit="this.$emit('rateLimit')"
							:Peer="Peer"
							v-if="this.subMenuOpened"
							ref="target"
						></PeerSettingsDropdown>
					</Transition>
				</div>
			</div>
		</div>
	</div>
	<div v-if="showRateLimitSettings" 
		 class="modal fade show" 
		 style="display: block"
		 tabindex="-1">
		<div class="modal-dialog">
			<div class="modal-content">
				<div class="modal-header">
					<h5 class="modal-title">
						<LocaleText t="Set Rate Limit"></LocaleText>
					</h5>
					<button type="button" 
							class="btn-close" 
							@click="showRateLimitSettings = false">
					</button>
				</div>
				<div class="modal-body">
					<PeerRateLimitSettings 
						:selectedPeer="Peer"
						:configurationInfo="{Name: configurationName}"
						@close="showRateLimitSettings = false"
						@refresh="$emit('refresh')"
					></PeerRateLimitSettings>
				</div>
			</div>
		</div>
		<div class="modal-backdrop fade show"></div>
	</div>
</template>

<style scoped>
.slide-fade-leave-active, .slide-fade-enter-active{
	transition: all 0.2s cubic-bezier(0.82, 0.58, 0.17, 1.3);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
	transform: translateY(20px);
	opacity: 0;
	filter: blur(3px);
}

.subMenuBtn.active{
	background-color: #ffffff20;
}

.peerCard{
	transition: box-shadow 0.1s cubic-bezier(0.82, 0.58, 0.17, 0.9);
}

.peerCard:hover{
	box-shadow: var(--bs-box-shadow) !important;
}

.modal {
	background-color: rgba(0, 0, 0, 0.5);
}

.bi-arrow-repeat {
	cursor: pointer;
	transition: transform 0.2s ease;
}
.bi-arrow-repeat:hover {
	transform: rotate(180deg);
}
</style>