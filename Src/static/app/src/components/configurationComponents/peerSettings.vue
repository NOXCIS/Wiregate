<script>
import {fetchPost, getUrl} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";
import {validateCPSFormat} from "@/utilities/validation.js";

export default {
	name: "peerSettings",
	components: {LocaleText},
	props: {
		selectedPeer: Object,
		configurationInfo: Object
	},
	data(){
		return {
			data: undefined,
			dataChanged: false,
			showKey: false,
			saving: false
		}
	},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {dashboardConfigurationStore}
	},
	methods: {
		reset(){
			if (this.selectedPeer){
				this.data = JSON.parse(JSON.stringify(this.selectedPeer))
				// Initialize I1-I5 if not present
				if (!this.data.I1) this.data.I1 = "";
				if (!this.data.I2) this.data.I2 = "";
				if (!this.data.I3) this.data.I3 = "";
				if (!this.data.I4) this.data.I4 = "";
				if (!this.data.I5) this.data.I5 = "";
				// Initialize TLS piping (udptlspipe) fields if not present
				if (this.data.udptlspipe_enabled === undefined) this.data.udptlspipe_enabled = false;
				if (!this.data.udptlspipe_password) this.data.udptlspipe_password = "";
				if (!this.data.udptlspipe_port) this.data.udptlspipe_port = "443";
				if (!this.data.udptlspipe_tls_server_name) this.data.udptlspipe_tls_server_name = "";
				if (this.data.udptlspipe_secure === undefined) this.data.udptlspipe_secure = false;
				if (!this.data.udptlspipe_proxy) this.data.udptlspipe_proxy = "";
				if (!this.data.udptlspipe_fingerprint_profile) this.data.udptlspipe_fingerprint_profile = "okhttp";
				this.dataChanged = false;
			}
		},
		validateCPSFormat(value) {
			return validateCPSFormat(value);
		},
		async generateSingleCPS(key) {
			// Generate cryptographically secure random CPS patterns
			// Enhanced with pattern library support (70% library, 30% current generation)
			const randomHexByte = () => {
				const bytes = new Uint8Array(1);
				window.crypto.getRandomValues(bytes);
				return bytes[0].toString(16).padStart(2, '0');
			};
			
			const randomHexBytes = (count) => {
				const bytes = new Uint8Array(count);
				window.crypto.getRandomValues(bytes);
				return Array.from(bytes)
					.map(b => b.toString(16).padStart(2, '0'))
					.join('');
			};
			
			const secureRandomInt = (min, max) => {
				const range = max - min + 1;
				const bytesNeeded = Math.ceil(Math.log2(range) / 8);
				let randomValue;
				do {
					const randomBytes = new Uint8Array(bytesNeeded);
					window.crypto.getRandomValues(randomBytes);
					randomValue = 0;
					for (let i = 0; i < bytesNeeded; i++) {
						randomValue = (randomValue << 8) + randomBytes[i];
					}
					const maxValue = Math.pow(2, bytesNeeded * 8) - 1;
					const threshold = maxValue - (maxValue % range);
					if (randomValue < threshold) {
						break;
					}
				} while (true);
				return min + (randomValue % range);
			};
			
			// Map I1-I5 to protocol types for pattern library
			const protocolMap = {
				'I1': 'quic',
				'I2': 'http_get',
				'I3': 'dns',
				'I4': 'json',
				'I5': 'http_response'
			};
			
			// Always try library first (100% chance), only use synthetic as fallback
			const protocol = protocolMap[key];
			let libraryPattern = null;
			if (protocol) {
				try {
					const url = getUrl(`/api/cps-patterns/${protocol}`);
					const res = await fetch(url, {
						method: 'GET',
						headers: {
							'Content-Type': 'application/json',
						},
						credentials: 'include'
					});
					if (res.ok) {
						const jsonData = await res.json();
						if (jsonData.status && jsonData.data && jsonData.data.cps_pattern) {
							libraryPattern = jsonData.data.cps_pattern;
							console.debug(`✓ Retrieved ${protocol} pattern from library for peer`);
						} else {
							console.debug(`✗ Library returned no pattern for ${protocol}`);
						}
					} else {
						console.debug(`✗ Library fetch failed for ${protocol}: ${res.status}`);
					}
				} catch (e) {
					// Fallback to generation if library fetch fails
					console.debug(`Pattern library not available for ${protocol}, using generation:`, e);
				}
			}
			
			// Helper to randomize pattern (applies to both library and synthetic patterns)
			const randomizePattern = (pattern) => {
				if (!pattern) return pattern;
				
				// Check if pattern is a full hexstream (single <b 0x...> tag)
				const fullHexMatch = pattern.trim().match(/^<b\s+0x([0-9a-fA-F]+)>$/);
				if (fullHexMatch) {
					// For full hexstreams, randomly modify 5-15% of the hex characters
					// This maintains the overall structure while adding variation
					const hexString = fullHexMatch[1];
					const hexArray = hexString.split('');
					const numChanges = Math.max(1, Math.floor(hexArray.length * secureRandomInt(5, 15) / 100));
					
					// Randomly select positions to modify
					const positions = new Set();
					while (positions.size < numChanges) {
						positions.add(secureRandomInt(0, hexArray.length - 1));
					}
					
					// Modify selected hex characters
					positions.forEach(pos => {
						// Generate random hex character (0-9, a-f)
						const newChar = secureRandomInt(0, 15).toString(16);
						hexArray[pos] = newChar;
					});
					
					return `<b 0x${hexArray.join('')}>`;
				}
				
				// For tag-based patterns, randomize length tags
				return pattern
					.replace(/<r\s+(\d+)>/g, (match, len) => {
						const originalLen = parseInt(len);
						const variation = secureRandomInt(Math.max(1, Math.floor(originalLen * 0.75)), Math.min(1000, Math.floor(originalLen * 1.25)));
						return `<r ${variation}>`;
					})
					.replace(/<rc\s+(\d+)>/g, (match, len) => {
						const originalLen = parseInt(len);
						const variation = secureRandomInt(Math.max(1, Math.floor(originalLen * 0.75)), Math.min(1000, Math.floor(originalLen * 1.25)));
						return `<rc ${variation}>`;
					})
					.replace(/<rd\s+(\d+)>/g, (match, len) => {
						const originalLen = parseInt(len);
						const variation = secureRandomInt(Math.max(1, Math.floor(originalLen * 0.75)), Math.min(1000, Math.floor(originalLen * 1.25)));
						return `<rd ${variation}>`;
					});
			};
			
			// If we have a library pattern, randomize it and use it
			// If no library pattern available, leave empty (user can enter manually)
			if (libraryPattern) {
				this.data[key] = randomizePattern(libraryPattern);
				this.dataChanged = true;
			} else {
				this.data[key] = "";
				this.dataChanged = true;
			}
		},
		savePeer(){
			this.saving = true;
			fetchPost(`/api/updatePeerSettings/${this.$route.params.id}`, this.data, (res) => {
				this.saving = false;
				if (res.status){
					this.dashboardConfigurationStore.newMessage("Server", "Peer saved", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
				this.$emit("refresh")
			})
		},
		resetPeerData(type){
			this.saving = true
			fetchPost(`/api/resetPeerData/${this.$route.params.id}`, {
				id: this.data.id,
				type: type
			}, (res) => {
				this.saving = false;
				if (res.status){
					this.dashboardConfigurationStore.newMessage("Server", "Peer data usage reset successfully", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
				this.$emit("refresh")
			})
		}
	},
	beforeMount() {
		this.reset();
	},
	mounted() {
		this.$el.querySelectorAll("input").forEach(x => {
			x.addEventListener("change", () => {
				this.dataChanged = true;
			});
		})
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
						<h4 class="mb-0">
							<LocaleText t="Peer Settings"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4 pb-4" v-if="this.data">
						<div class="d-flex flex-column gap-2 mb-4">
							<div class="d-flex align-items-center">
								<small class="text-muted">
									<LocaleText t="Public Key"></LocaleText>
								</small>
								<small class="ms-auto"><samp>{{this.data.id}}</samp></small>
							</div>
							<div>
								<label for="peer_name_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Name"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.name"
								       id="peer_name_textbox" placeholder="">
							</div>
							<div>
								<div class="d-flex position-relative">
									<label for="peer_private_key_textbox" class="form-label">
										<small class="text-muted"><LocaleText t="Private Key"></LocaleText> 
											<code>
												<LocaleText t="(Required for QR Code and Download)"></LocaleText>
											</code></small>
									</label>
									<a role="button" class="ms-auto text-decoration-none toggleShowKey"
									   @click="this.showKey = !this.showKey"
									>
										<i class="bi" :class="[this.showKey ? 'bi-eye-slash-fill':'bi-eye-fill']"></i>
									</a>
								</div>
								<input :type="[this.showKey ? 'text':'password']" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.private_key"
								       id="peer_private_key_textbox"
								       style="padding-right: 40px">
							</div>
							<div>
								<label for="peer_allowed_ip_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.allowed_ip"
								       id="peer_allowed_ip_textbox">
							</div>

							<div>
								<label for="peer_endpoint_allowed_ips" class="form-label">
									<small class="text-muted">
										<LocaleText t="Endpoint Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.endpoint_allowed_ip"
								       id="peer_endpoint_allowed_ips">
							</div>
							<div>
								<label for="peer_DNS_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="DNS"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.DNS"
								       id="peer_DNS_textbox">
							</div>
							<div class="accordion mt-3" id="peerSettingsAccordion">
								<div class="accordion-item">
									<h2 class="accordion-header">
										<button class="accordion-button rounded-3 collapsed" type="button"
										        data-bs-toggle="collapse" data-bs-target="#peerSettingsAccordionOptional">
											<LocaleText t="Optional Settings"></LocaleText>
										</button>
									</h2>
									<div id="peerSettingsAccordionOptional" class="accordion-collapse collapse"
									     data-bs-parent="#peerSettingsAccordion">
										<div class="accordion-body d-flex flex-column gap-2 mb-2">
											<div>
												<label for="peer_preshared_key_textbox" class="form-label">
													<small class="text-muted">
														<LocaleText t="Pre-Shared Key"></LocaleText></small>
												</label>
												<input type="text" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.preshared_key"
												       id="peer_preshared_key_textbox">
											</div>
											<div>
												<label for="peer_mtu" class="form-label"><small class="text-muted">
													<LocaleText t="MTU"></LocaleText>
												</small></label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.mtu"
												       id="peer_mtu">
											</div>
											<div>
												<label for="peer_keep_alive" class="form-label">
													<small class="text-muted">
														<LocaleText t="Persistent Keepalive"></LocaleText>
													</small>
												</label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.keepalive"
												       id="peer_keep_alive">
											</div>
											<div v-if="this.data.advanced_security">
												<label for="peer_advance_security" class="form-label d-block">
													<small class="text-muted">
														<LocaleText t="Advanced Security"></LocaleText>
													</small>
												</label>
												<div class="btn-group" role="group">
													<input type="radio" class="btn-check"
													       v-model="this.data.advanced_security"
													       value="on"
													       name="advanced_security_radio" id="advanced_security_on" autocomplete="off">
													<label class="btn btn-outline-primary  btn-sm" for="advanced_security_on">
														<LocaleText t="On"></LocaleText>
													</label>

													<input type="radio"
													       v-model="this.data.advanced_security"
													       value="off"
													       class="btn-check" name="advanced_security_radio" id="advanced_security_off" autocomplete="off">
													<label class="btn btn-outline-primary btn-sm" for="advanced_security_off">
														<LocaleText t="Off"></LocaleText>
													</label>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							<!-- I1-I5 CPS Parameters (AmneziaWG 1.5 only) -->
							<div v-if="configurationInfo && configurationInfo.Protocol === 'awg'" class="mt-3">
								<div class="accordion" id="peerCPSAccordion">
									<div class="accordion-item">
										<h2 class="accordion-header">
											<button class="accordion-button rounded-3 collapsed" type="button"
											        data-bs-toggle="collapse" data-bs-target="#peerCPSAccordionCollapse">
												<LocaleText t="I1-I5 CPS Parameters (AmneziaWG 1.5)"></LocaleText>
											</button>
										</h2>
										<div id="peerCPSAccordionCollapse" class="accordion-collapse collapse"
										     data-bs-parent="#peerCPSAccordion">
											<div class="accordion-body d-flex flex-column gap-2 mb-2">
												<div v-for="key in ['I1', 'I2', 'I3', 'I4', 'I5']" :key="key">
													<label :for="'peer_' + key" class="form-label">
														<small class="text-muted">
															<LocaleText :t="key"></LocaleText>
														</small>
													</label>
													<div class="form-text text-muted mb-1">
														<small v-if="key === 'I1'">Primary CPS packet. Tags: &lt;b 0xHEX&gt; (binary), &lt;c&gt; (counter), &lt;t&gt; (timestamp), &lt;r N&gt; (random), &lt;rc N&gt; (ASCII), &lt;rd N&gt; (digits)</small>
														<small v-else>{{ key }} CPS packet. Available tags: &lt;b 0xHEX&gt;, &lt;c&gt;, &lt;t&gt;, &lt;r N&gt;, &lt;rc N&gt;, &lt;rd N&gt;</small>
													</div>
													<div class="input-group">
														<input 
															type="text" 
															class="form-control form-control-sm rounded-3"
															:class="{'is-invalid': this.data[key] && !this.validateCPSFormat(this.data[key])}"
															:disabled="this.saving"
															v-model="this.data[key]"
															:id="'peer_' + key"
															:placeholder="key === 'I1' ? '<b 0xLARGE_HEX_BLOB>' : ''"
														>
														<button
															v-if="!this.data[key]"
															class="btn btn-sm bg-primary-subtle border-primary-subtle text-primary-emphasis"
															@click="async () => { await this.generateSingleCPS(key); }"
															type="button"
															:disabled="this.saving"
														>
															<i class="bi bi-magic"></i> Auto
														</button>
													</div>
													<div class="invalid-feedback" v-if="this.data[key] && !this.validateCPSFormat(this.data[key])">
														Invalid CPS format. Use tags: &lt;b 0xHEX&gt;, &lt;c&gt;, &lt;t&gt;, &lt;r N&gt;, &lt;rc N&gt;, &lt;rd N&gt;
													</div>
													<small class="text-muted d-block mt-1">
														Leave empty to use auto-scrambled values from configuration
													</small>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							<!-- TLS Piping (udptlspipe) Configuration -->
							<div class="mt-3">
								<div class="accordion" id="peerTlsPipeAccordion">
									<div class="accordion-item">
										<h2 class="accordion-header">
											<button class="accordion-button rounded-3 collapsed" type="button"
											        data-bs-toggle="collapse" data-bs-target="#peerTlsPipeAccordionCollapse">
												<LocaleText t="TLS Piping Configuration"></LocaleText>
											</button>
										</h2>
										<div id="peerTlsPipeAccordionCollapse" class="accordion-collapse collapse"
										     data-bs-parent="#peerTlsPipeAccordion">
											<div class="accordion-body d-flex flex-column gap-2 mb-2">
												<div class="form-text text-muted mb-2">
													<small>
														<i class="bi bi-shield-lock me-1"></i>
														TLS piping wraps WireGuard UDP traffic in TLS, useful when UDP is blocked or unreliable. 
														Requires udptlspipe server running on the tunnel server.
													</small>
												</div>
												<!-- Enable TLS Piping -->
												<div class="form-check form-switch">
													<input class="form-check-input" type="checkbox" role="switch" 
													       id="peer_udptlspipe_enabled"
													       v-model="this.data.udptlspipe_enabled"
													       :disabled="this.saving">
													<label class="form-check-label" for="peer_udptlspipe_enabled">
														<small class="text-muted">
															<LocaleText t="Enable TLS Piping"></LocaleText>
														</small>
													</label>
												</div>
												<!-- Password -->
												<div v-if="this.data.udptlspipe_enabled">
													<label for="peer_udptlspipe_password" class="form-label">
														<small class="text-muted">
															<LocaleText t="Password"></LocaleText>
															<code class="ms-1">
																<LocaleText t="(Required)"></LocaleText>
															</code>
														</small>
													</label>
													<input type="password" class="form-control form-control-sm rounded-3"
													       :disabled="this.saving"
													       v-model="this.data.udptlspipe_password"
													       id="peer_udptlspipe_password"
													       placeholder="Server authentication password">
												</div>
												<!-- TLS Pipe Server Port -->
												<div v-if="this.data.udptlspipe_enabled">
													<label for="peer_udptlspipe_port" class="form-label">
														<small class="text-muted">
															<LocaleText t="TLS Server Port"></LocaleText>
														</small>
													</label>
													<input type="text" class="form-control form-control-sm rounded-3"
													       :disabled="this.saving"
													       v-model="this.data.udptlspipe_port"
													       id="peer_udptlspipe_port"
													       placeholder="443">
													<small class="text-muted d-block mt-1">
														Port where the udptlspipe server is listening (default: 443)
													</small>
												</div>
												<!-- TLS Server Name -->
												<div v-if="this.data.udptlspipe_enabled">
													<label for="peer_udptlspipe_tls_server_name" class="form-label">
														<small class="text-muted">
															<LocaleText t="TLS Server Name (SNI)"></LocaleText>
														</small>
													</label>
													<input type="text" class="form-control form-control-sm rounded-3"
													       :disabled="this.saving"
													       v-model="this.data.udptlspipe_tls_server_name"
													       id="peer_udptlspipe_tls_server_name"
													       placeholder="Optional: example.com">
													<small class="text-muted d-block mt-1">
														Leave empty to use endpoint hostname
													</small>
												</div>
												<!-- Secure Mode -->
												<div class="form-check form-switch" v-if="this.data.udptlspipe_enabled">
													<input class="form-check-input" type="checkbox" role="switch" 
													       id="peer_udptlspipe_secure"
													       v-model="this.data.udptlspipe_secure"
													       :disabled="this.saving">
													<label class="form-check-label" for="peer_udptlspipe_secure">
														<small class="text-muted">
															<LocaleText t="Verify Server Certificate"></LocaleText>
														</small>
													</label>
												</div>
												<!-- Proxy URL -->
												<div v-if="this.data.udptlspipe_enabled">
													<label for="peer_udptlspipe_proxy" class="form-label">
														<small class="text-muted">
															<LocaleText t="Proxy URL"></LocaleText>
														</small>
													</label>
													<input type="text" class="form-control form-control-sm rounded-3"
													       :disabled="this.saving"
													       v-model="this.data.udptlspipe_proxy"
													       id="peer_udptlspipe_proxy"
													       placeholder="Optional: socks5://user:pass@host:port">
													<small class="text-muted d-block mt-1">
														Optional proxy for connecting to the TLS pipe server
													</small>
												</div>
												<!-- TLS Fingerprint Profile -->
												<div v-if="this.data.udptlspipe_enabled">
													<label for="peer_udptlspipe_fingerprint_profile" class="form-label">
														<small class="text-muted">
															<LocaleText t="TLS Fingerprint Profile"></LocaleText>
														</small>
													</label>
													<select class="form-select form-select-sm rounded-3"
													        :disabled="this.saving"
													        v-model="this.data.udptlspipe_fingerprint_profile"
													        id="peer_udptlspipe_fingerprint_profile">
														<option value="okhttp">okhttp (Android)</option>
														<option value="chrome">Chrome</option>
														<option value="firefox">Firefox</option>
														<option value="safari">Safari</option>
														<option value="edge">Edge</option>
														<option value="ios">iOS App</option>
														<option value="randomized">Randomized</option>
													</select>
													<small class="text-muted d-block mt-1">
														Mimic TLS fingerprint to evade detection (JA3/JA4)
													</small>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							<hr>
							<div class="d-flex gap-2 align-items-center">
								<strong>
									<LocaleText t="Reset Data Usage"></LocaleText>
								</strong>
								<div class="d-flex gap-2 ms-auto">
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
										@click="this.resetPeerData('total')"
									>
										<i class="bi bi-arrow-down-up me-2"></i>
										<LocaleText t="Total"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('receive')"
									>
										<i class="bi bi-arrow-down me-2"></i>
										<LocaleText t="Received"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3  flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('sent')"
									>
										<i class="bi bi-arrow-up me-2"></i>
										<LocaleText t="Sent"></LocaleText>
									</button>
								</div>
								
							</div>
						</div>
						<div class="d-flex align-items-center gap-2">
							<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto px-3 py-2"
							        @click="this.reset()"
							        :disabled="!this.dataChanged || this.saving">
								 <i class="bi bi-arrow-clockwise"></i>
							</button>

							<button class="btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 px-3 py-2 shadow"
							        :disabled="!this.dataChanged || this.saving"
							        @click="this.savePeer()"
							>
								<i class="bi bi-save-fill"></i></button>
						</div>
					</div>
				</div>
			</div>
			
		</div>

	</div>
</template>

<style scoped>
.toggleShowKey{
	position: absolute;
	top: 35px;
	right: 12px;
}
</style>