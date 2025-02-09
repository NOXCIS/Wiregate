<script>
import {fetchGet, fetchPost} from "../utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import Message from "@/components/messageCentreComponent/message.vue";
import RemoteServerList from "@/components/signInComponents/RemoteServerList.vue";
import {GetLocale} from "@/utilities/locale.js";
import LocaleText from "@/components/text/localeText.vue";
import SignInInput from "@/components/signIn/signInInput.vue";
import SignInTOTP from "@/components/signIn/signInTOTP.vue";

export default {
	name: "signin",
	components: {SignInTOTP, SignInInput, LocaleText, RemoteServerList, Message},
	async setup(){
		const store = DashboardConfigurationStore()
		let theme = "dark"
		let totpEnabled = false;
		let version = undefined;
		if (!store.IsElectronApp){
			await Promise.all([
				fetchGet("/api/getDashboardTheme", {}, (res) => {
					theme = res.data
				}),
				fetchGet("/api/isTotpEnabled", {}, (res) => {
					totpEnabled = res.data
				}),
				fetchGet("/api/getDashboardVersion", {}, (res) => {
					version = res.data
				})
			]);
		}
		store.removeActiveCrossServer();
		return {store, theme, totpEnabled, version}
	},
	data(){
		return {
			data: {
				username: "",
				password: "",
				totp: "",
			},
			showUsername: false,
			showPassword: false,
			loginError: false,
			loginErrorMessage: "",
			loading: false
		}
	},
	computed: {
		getMessages(){
			return this.store.Messages.filter(x => x.show)
		},
		applyLocale(key){
			return GetLocale(key)
		},
		formValid(){
			return this.data.username && this.data.password && ((this.totpEnabled && this.data.totp) || !this.totpEnabled)
		}
	},
	methods: {
		GetLocale,
		resetValidation(event) {
			event.target.classList.remove('is-invalid', 'is-valid');
			this.loginError = false;
			this.loginErrorMessage = "";
		},
		async auth(){
			if (this.formValid){
				this.loading = true
				await fetchPost("/api/authenticate", this.data, (response) => {
					if (response.status){
						this.loginError = false;
						this.$refs["signInBtn"].classList.add("signedIn")
						if (response.message){
							this.$router.push('/welcome')
						}else{
							if (this.store.Redirect !== undefined){
								this.$router.push(this.store.Redirect)
							}else{
								this.$router.push('/')
							}
						}
					}else{
						this.store.newMessage("Server", response.message, "danger")
						document.querySelectorAll("input[required]").forEach(x => {
							x.classList.remove("is-valid")
							x.classList.add("is-invalid")
						});
						this.loading = false
					}
					
				})
			}else{
				document.querySelectorAll("input[required]").forEach(x => {
					if (x.value.length === 0){
						x.classList.remove("is-valid")
						x.classList.add("is-invalid")
					}else{
						x.classList.remove("is-invalid")
						x.classList.add("is-valid")
					}
				});
			}
		},
		initMatrixRain() {
			const canvas = document.getElementById('matrix-rain');
			const ctx = canvas.getContext('2d');

			// Enable crisp text rendering
			ctx.imageSmoothingEnabled = false;
			ctx.textRendering = 'geometricPrecision';

			// Configuration
			const config = {
				delay: 0,
				fadeFactor: 0.05,
				interval: 95,
				colors: {
					primary: '#4cd964',    // Green
					secondary: '#33ff33',  // Bright green
					purple: {
						head: '#b31fff',     // Bright purple head
						tail: '#7a0cc4'      // Original purple tail
					},
					orange: {
						head: '#ff7b00',     // Bright orange head
						tail: '#e38e41'      // Original orange tail
					},
					cyan: '#00ffff'        // Cyan for easter eggs
				}
			};

			const fontSize = 14;
			const tileSize = fontSize + 2;
			const fontFamily = 'Consolas, monospace'; // Changed to Consolas for sharper rendering
			let columns = [];

			const getRandomStackHeight = () => {
				const maxStackHeight = Math.ceil(canvas.height / tileSize);
				return Math.floor(Math.random() * (maxStackHeight - 10 + 1)) + 10;
			};

			const getRandomText = () => {
				// Easter egg words with low probability
				const easterEggs = ['weir', 'noxis', 'james', 'wireguard', 'amnezia'];
				const showEasterEgg = Math.random() < 0.0011; // 1% chance for easter egg

				if (showEasterEgg) {
					return {
						word: easterEggs[Math.floor(Math.random() * easterEggs.length)],
						isEasterEgg: true,
						charIndex: 0
					};
				}
				return {
					char: String.fromCharCode(Math.floor(Math.random() * (126 - 33 + 1)) + 33),
					isEasterEgg: false
				};
			};

			const getRandomColor = () => {
				// Distribution: 65% primary green, 15% secondary green, 10% purple, 10% orange
				const rand = Math.random();
				if (rand < 0.65) {
					return {
						color: config.colors.primary,
						glow: '#00ff2d',
						type: 'green'
					};
				} else if (rand < 0.80) {
					return {
						color: config.colors.secondary,
						glow: '#33ff33',
						type: 'green'
					};
				} else if (rand < 0.90) {
					return {
						color: config.colors.purple,
						glow: '#b31fff',
						type: 'purple'
					};
				} else {
					return {
						color: config.colors.orange,
						glow: '#ff7b00',
						type: 'orange'
					};
				}
			};

			const initColumns = () => {
				columns = [];
				for (let i = 0; i < canvas.width / tileSize; i++) {
					const colorInfo = getRandomColor();
					columns.push({
						x: i * tileSize,
						stackCounter: Math.floor(Math.random() * 50),
						stackHeight: getRandomStackHeight(),
						colorInfo: colorInfo,
						intensity: 0.8 + Math.random() * 0.2,
						headPos: 0,
						easterEgg: null
					});
				}
			};

			const draw = () => {
				ctx.font = `bold ${fontSize}px ${fontFamily}`;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				
				ctx.fillStyle = `rgba(0, 0, 0, ${config.fadeFactor})`;
				ctx.fillRect(0, 0, canvas.width, canvas.height);

				columns.forEach(column => {
					ctx.shadowBlur = 0;
					
					const stackProgress = column.stackCounter / column.stackHeight;
					let opacity = column.intensity * (1 - stackProgress * 0.3);
					
					let text;
					if (column.easterEgg) {
						// Continue displaying current easter egg word
						text = {
							char: column.easterEgg.word[column.easterEgg.charIndex],
							isEasterEgg: true
						};
						
						// Move to next character for next frame
						column.easterEgg.charIndex++;
						
						// Reset easter egg when word is complete
						if (column.easterEgg.charIndex >= column.easterEgg.word.length) {
							column.easterEgg = null;
						}
					} else {
						text = getRandomText();
						if (text.isEasterEgg) {
							// Start new easter egg word
							column.easterEgg = {
								word: text.word,
								charIndex: 1  // Start at 1 since we're using first char now
							};
							text.char = text.word[0];  // Use first character immediately
						}
					}
					
					if (text.isEasterEgg) {
						// Use cyan color for easter egg characters
						ctx.shadowBlur = 2;
						ctx.shadowColor = config.colors.cyan;
						ctx.fillStyle = `${config.colors.cyan}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}`;
					} else if (column.colorInfo.type === 'purple' || column.colorInfo.type === 'orange') {
						column.intensity = 0.85 + Math.sin(Date.now() * 0.005) * 0.15;
						
						column.headPos = column.stackCounter * tileSize;
						const gradientLength = 8;
						const distanceFromHead = Math.abs(column.headPos - (column.stackCounter * tileSize));
						const headIntensity = Math.max(0, 1 - (distanceFromHead / (gradientLength * tileSize)));
						
						const colorType = column.colorInfo.type;
						const headColor = config.colors[colorType].head;
						const tailColor = config.colors[colorType].tail;
						
						const r = parseInt(headColor.slice(1, 3), 16) * headIntensity + parseInt(tailColor.slice(1, 3), 16) * (1 - headIntensity);
						const g = parseInt(headColor.slice(3, 5), 16) * headIntensity + parseInt(tailColor.slice(3, 5), 16) * (1 - headIntensity);
						const b = parseInt(headColor.slice(5, 7), 16) * headIntensity + parseInt(tailColor.slice(5, 7), 16) * (1 - headIntensity);
						
						const specialOpacity = opacity * (0.9 + headIntensity * 0.3);
						
						// Add minimal shadow only for head characters
						if (headIntensity > 0.7) {
							ctx.shadowBlur = 1;
							ctx.shadowColor = column.colorInfo.type === 'purple' ? '#b31fff' : '#ff7b00';
						}
						
						ctx.fillStyle = `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${specialOpacity})`;
					} else {
						opacity *= 0.8;
						ctx.fillStyle = column.colorInfo.color.startsWith('#') ? 
							`${column.colorInfo.color}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}` : 
							column.colorInfo.color;
					}

					// Draw characters with pixel-perfect positioning
					ctx.fillText(
						text.char,
						Math.round(column.x + tileSize/2),
						Math.round(column.stackCounter * tileSize + tileSize/2)
					);

					column.stackCounter++;
					if (column.stackCounter >= column.stackHeight) {
						column.stackCounter = 0;
						column.stackHeight = getRandomStackHeight();
						const newColorInfo = getRandomColor();
						column.colorInfo = newColorInfo;
						column.intensity = column.colorInfo.type === 'green' ? 
							0.8 + Math.random() * 0.2 : 
							0.9 + Math.random() * 0.1;
					}
				});
			};

			// Adjust canvas for pixel-perfect rendering
			const dpr = window.devicePixelRatio || 1;
			const rect = canvas.getBoundingClientRect();
			
			canvas.width = rect.width * dpr;
			canvas.height = rect.height * dpr;
			canvas.style.width = `${rect.width}px`;
			canvas.style.height = `${rect.height}px`;
			
			ctx.scale(dpr, dpr);

			// Initialize
			initColumns();

			// Start animation
			this.matrixInterval = setInterval(draw, config.interval);

			// Handle window resize
			window.addEventListener('resize', () => {
				clearInterval(this.matrixInterval);
				resizeCanvas();
				initColumns();
				this.matrixInterval = setInterval(draw, config.interval);
			});
		},
		beforeUnmount() {
			if (this.matrixInterval) {
				clearInterval(this.matrixInterval);
			}
			window.removeEventListener('resize', this.handleResize);
		}
	},
	mounted() {
		this.initMatrixRain();
	},
	beforeUnmount() {
		// Clean up any intervals when component is destroyed
		clearInterval(this.matrixInterval);
	}
}
</script>

<template>
	<div class="container-fluid login-container-fluid d-flex main flex-column py-4 text-body h-100" 
	     style="overflow-y: scroll"
	     :data-bs-theme="this.theme">
		<canvas id="matrix-rain" class="matrix-background"></canvas>
		<div class="login-box m-auto" >
			<div class="m-auto" style="width: 700px;">
			
				<span class="dashboardLogo display-3"><strong>WireGate</strong></span>
				<div class="alert alert-danger mt-2 mb-0" role="alert" v-if="loginError">
					<LocaleText :t="this.loginErrorMessage"></LocaleText>
				</div>
				<form @submit="(e) => {e.preventDefault(); this.auth();}"
				      class="mt-3"
				      v-if="!this.store.CrossServerConfiguration.Enable">
					<div class="form-floating mb-2">
						<input type="username"
						       required
						       :disabled="loading"
						       v-model="this.data.username"
						       name="username"
						       autocomplete="username"
						       autofocus
						       @focus="resetValidation"
						       class="form-control rounded-3" id="username" placeholder="Username">
						<label for="username" class="login-badges d-flex">
							<i class="bi bi-person-circle me-2"></i>
							<LocaleText t="Username"></LocaleText>	
						</label>
					</div>
					<div class="form-floating mb-2 position-relative">
						<input :type="showPassword ? 'text' : 'password'"
						       required
						       :disabled="loading"
						       autocomplete="current-password"
						       v-model="this.data.password"
						       class="form-control rounded-3" 
						       id="password" 
						       placeholder="Password"
						       ref="passwordInput"
						       @focus="resetValidation($event)">
						<label for="password" class="login-badges d-flex">
							<i class="bi bi-key-fill me-2"></i>
							<LocaleText t="Password"></LocaleText>	
						</label>
						<button type="button"
						        v-show="!loginError && !$refs.passwordInput?.classList.contains('is-invalid')"
						        class="btn btn-link position-absolute top-50 end-0 translate-middle-y text-body-secondary pe-3 border-0"
						        style="z-index: 5;"
						        @click="showPassword = !showPassword"
						        :aria-label="showPassword ? 'Hide password' : 'Show password'"
						        :title="showPassword ? 'Hide password' : 'Show password'">
							<i class="bi" :class="showPassword ? 'bi-eye-slash-fill' : 'bi-eye-fill'"></i>
						</button>
					</div>
					<div class="form-floating mb-2" v-if="this.totpEnabled">
						<input type="text"
						       id="totp"
						       required
						       :disabled="loading"
						       placeholder="totp"
						       v-model="this.data.totp"
						       @focus="resetValidation"
						       class="form-control rounded-3" 
						       maxlength="6" 
						       inputmode="numeric" 
						       autocomplete="one-time-code">
						<label for="floatingInput" class="login-badges d-flex">
							<i class="bi bi-lock-fill me-2"></i>
							<LocaleText t="OTP from your authenticator"></LocaleText>
						</label>
					</div>
					<button class="btn btn-lg btn-dark ms-auto mt-5 w-100 d-flex btn-brand signInBtn rounded-3" 
					        :disabled="this.loading || !this.formValid"
					        ref="signInBtn">
							<span v-if="!this.loading" class="d-flex w-100">
								<LocaleText t="Sign In"></LocaleText>
								<i class="ms-auto bi bi-chevron-right"></i>
							</span>
							<span v-else class="d-flex w-100 align-items-center">
								<LocaleText t="Signing In..."></LocaleText>
								<span class="spinner-border ms-auto spinner-border-sm" role="status"></span>
							</span>
					</button>
				</form>
				<RemoteServerList v-else></RemoteServerList>

				<div class="d-flex mt-3" v-if="!this.store.IsElectronApp">
					<div class="form-check form-switch ms-auto">
						<input
							v-model="this.store.CrossServerConfiguration.Enable"
							class="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckChecked">
						<label class="form-check-label" for="flexSwitchCheckChecked">
							<LocaleText t="Access Remote Server"></LocaleText>
						</label>
					</div>
				</div>
			</div>
		</div>
		<small class="text-muted pb-3 d-block w-100 text-center mt-3">
			<a href="https://github.com/NOXCIS/Wiregate" target="_blank" style="color: #4a4a4a;">
				<strong>WireGate</strong>
			</a> 
			Build: <strong>{{ this.version }}</strong> | UI Based On 
			<a href="https://github.com/donaldzou/WGDashboard" target="_blank" style="color: #4a4a4a;">
				<strong>WGDashboard</strong>
			</a>
		</small>
		<div class="messageCentre text-body position-absolute end-0 m-3">
			<TransitionGroup name="message" tag="div" class="position-relative">
				<Message v-for="m in getMessages.slice().reverse()"
				         :message="m" :key="m.id"></Message>
			</TransitionGroup>
		</div>
	</div>
</template>

<style scoped>
@media screen and (max-width: 768px) {
	.login-box{
		width: 100% !important;
	}

	.login-box div{
		width: auto !important;
	}
}

.matrix-background {
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	z-index: 0;
	opacity: 0.50;
	pointer-events: none;
}

.login-box {
	position: relative;
	z-index: 1;
}

.messageCentre {
	z-index: 2;
}
</style>