<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {onMounted, ref, computed} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";

const store = DashboardConfigurationStore()

// Initialize Email configuration if it doesn't exist
if (!store.Configuration?.Email) {
	store.Configuration = {
		...store.Configuration,
		Email: {
			provider: 'smtp',
			server: '',
			port: '',
			encryption: 'STARTTLS',
			username: '',
			email_password: '',
			send_from: '',
			email_template: '',
			// New OAuth fields
			ms_client_id: '',
			ms_client_secret: '',
			ms_tenant_id: '',
			cf_api_token: '',
			cf_account_id: ''
		}
	}
}

const showAdvancedSettings = computed(() => store.Configuration.Email.provider === 'smtp')
const showOAuthSettings = computed(() => ['gmail', 'outlook'].includes(store.Configuration.Email.provider))
const showCloudflareSettings = computed(() => store.Configuration.Email.provider === 'cloudflare')

// Watch for provider changes to set default values
const handleProviderChange = () => {
	const provider = store.Configuration.Email.provider;
	if (provider === 'gmail') {
		store.Configuration.Email.server = 'smtp.gmail.com';
		store.Configuration.Email.port = '587';
		store.Configuration.Email.encryption = 'STARTTLS';
	} else if (provider === 'outlook') {
		store.Configuration.Email.server = 'smtp.office365.com';
		store.Configuration.Email.port = '587';
		store.Configuration.Email.encryption = 'STARTTLS';
	} else if (provider === 'cloudflare') {
		store.Configuration.Email.server = 'smtp.cloudflare.email';
		store.Configuration.Email.port = '587';
		store.Configuration.Email.encryption = 'STARTTLS';
	}
}

const startOAuthFlow = async (provider) => {
	await fetchGet(`/api/email/oauth/${provider}/start`, {}, (res) => {
		if (res.status && res.data?.authUrl) {
			window.location.href = res.data.authUrl;
		} else {
			store.newMessage("Server", res.message || "Failed to start OAuth flow", "danger");
		}
	});
}

onMounted(() => {
	checkEmailReady()
	document.querySelectorAll("#emailAccount input, #emailAccount select, #email_template").forEach(x => {
		if (x.id === 'provider') {
			handleProviderChange();
		}
		let id = x.attributes.getNamedItem('id').value;
		x.addEventListener("change", async () => {
			await fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Email",
				key: id,
				value: x.value
			}, (res) => {
				if (res.status){
					x.classList.remove('is-invalid')
					x.classList.add('is-valid')
				}else{
					x.classList.remove('is-valid')
					x.classList.add('is-invalid')
				}
				checkEmailReady()
			})
		})
	})
})

const emailIsReady = ref(false)
const testEmailReceiver = ref("")
const testing = ref(false)

const checkEmailReady = async () => {
	await fetchGet("/api/email/ready", {}, (res) => {
		emailIsReady.value = res.status
	})
}

const sendTestEmail = async () => {
	testing.value = true
	await fetchPost("/api/email/send", {
		Receiver: testEmailReceiver.value,
		Subject: "WGDashboard Testing Email",
		Body: "Test 1, 2, 3! Hello World :)"
	}, (res) => {
		if (res.status){
			store.newMessage("Server", "Test email sent successfully!", "success")
		}else{
			store.newMessage("Server", `Test email sent failed! Reason: ${res.message}`, "danger")
		}
		testing.value = false
	})
}
</script>

<template>
	<div class="card">
		<div class="card-header">
			<h6 class="my-2 d-flex">
				<LocaleText t="Email Account"></LocaleText>
				<span class="text-success ms-auto" v-if="emailIsReady">
					<i class="bi bi-check-circle-fill me-2"></i>
					<LocaleText t="Ready"></LocaleText>
				</span>
			</h6>
		</div>
		<div class="card-body d-flex flex-column gap-3">
			<form @submit="(e) => e.preventDefault(e)" id="emailAccount">
				<div class="row gx-2 gy-2">
					<div class="col-12">
						<div class="form-group">
							<label for="provider" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Email Provider"></LocaleText>
								</small></strong>
							</label>
							<select class="form-select"
									v-model="store.Configuration.Email.provider"
									id="provider">
								<option value="smtp">SMTP</option>
								<option value="gmail">Gmail (OAuth)</option>
								<option value="outlook">Microsoft Outlook (OAuth)</option>
								<option value="cloudflare">Cloudflare Email</option>
							</select>
						</div>
					</div>
					<template v-if="showAdvancedSettings">
						<div class="col-12 col-lg-4">
							<div class="form-group">
								<label for="server" class="text-muted mb-1">
									<strong><small>
										<LocaleText t="Server"></LocaleText>
									</small></strong>
								</label>
								<input id="server" 
									   v-model="store.Configuration.Email.server"
									   :readonly="store.Configuration.Email.provider !== 'smtp'"
									   type="text" class="form-control">
							</div>
						</div>
						<div class="col-12 col-lg-4">
							<div class="form-group">
								<label for="port" class="text-muted mb-1">
									<strong><small>
										<LocaleText t="Port"></LocaleText>
									</small></strong>
								</label>
								<input id="port"
									   v-model="store.Configuration.Email.port"
									   :readonly="store.Configuration.Email.provider !== 'smtp'"
									   type="text" class="form-control">
							</div>
						</div>
						<div class="col-12 col-lg-4">
							<div class="form-group">
								<label for="encryption" class="text-muted mb-1">
									<strong><small>
										<LocaleText t="Encryption"></LocaleText>
									</small></strong>
								</label>
								<select class="form-select"
										v-model="store.Configuration.Email.encryption"
										:disabled="store.Configuration.Email.provider !== 'smtp'"
										id="encryption">
									<option value="STARTTLS">STARTTLS</option>
									<option value="SSL/TLS">SSL/TLS</option>
									<option value="NOTLS">
										<LocaleText t="No Encryption"></LocaleText>
									</option>
								</select>
							</div>
						</div>
					</template>
					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="username" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Username"></LocaleText>
								</small></strong>
							</label>
							<input id="username"
								   v-model="store.Configuration.Email.username"
								   type="text" class="form-control">
						</div>
					</div>
					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="email_password" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Password/API Key"></LocaleText>
								</small></strong>
							</label>
							<input id="email_password"
								   v-model="store.Configuration.Email.email_password"
								   type="password" class="form-control">
						</div>
					</div>
					<template v-if="showOAuthSettings">
						<div class="col-12">
							<div class="alert alert-info">
								<i class="bi bi-info-circle me-2"></i>
								<LocaleText t="Configure OAuth authentication for secure email access"></LocaleText>
							</div>
							<button @click="startOAuthFlow(store.Configuration.Email.provider)"
									class="btn btn-primary">
								<i class="bi bi-shield-lock me-2"></i>
								<LocaleText t="Configure OAuth"></LocaleText>
							</button>
						</div>
					</template>
					<template v-if="showCloudflareSettings">
						<div class="col-12 col-lg-6">
							<div class="form-group">
								<label for="cf_api_token" class="text-muted mb-1">
									<strong><small><LocaleText t="API Token"></LocaleText></small></strong>
								</label>
								<input id="cf_api_token"
									   v-model="store.Configuration.Email.cf_api_token"
									   type="password" class="form-control">
							</div>
						</div>
						<div class="col-12 col-lg-6">
							<div class="form-group">
								<label for="cf_account_id" class="text-muted mb-1">
									<strong><small><LocaleText t="Account ID"></LocaleText></small></strong>
								</label>
								<input id="cf_account_id"
									   v-model="store.Configuration.Email.cf_account_id"
									   type="text" class="form-control">
							</div>
						</div>
					</template>
					<div class="col-12">
						<div class="form-group">
							<label for="send_from" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Send From"></LocaleText>
								</small></strong>
							</label>
							<input id="send_from"
								   v-model="store.Configuration.Email.send_from"
								   type="text" class="form-control">
						</div>
					</div>
				</div>
			</form>
			<hr v-if="emailIsReady">
			<div v-if="emailIsReady">
				<label class="text-muted mb-1" for="test_email">
					<small class="fw-bold">
						<LocaleText t="Send Test Email"></LocaleText>
					</small>
				</label>
				<form @submit="(e) => {e.preventDefault(); sendTestEmail()}"
					  class="input-group">
					<input type="email" class="form-control rounded-start-3"
						   id="test_email"
						   placeholder="john@example.com"
						   v-model="testEmailReceiver"
						   :disabled="testing">
					<button class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-end-3"
							type="submit"
							:disabled="testEmailReceiver.length === 0 || testing"
							id="button-addon2">
						<i class="bi bi-send me-2" v-if="!testing"></i>
						<span class="spinner-border spinner-border-sm me-2" v-else>
							<span class="visually-hidden">Loading...</span>
						</span>
						<LocaleText :t="!testing ? 'Send':'Sending...'"></LocaleText>
					</button>
				</form>
			</div>
			<hr>
			<div>
				<label class="text-muted mb-1" for="email_template">
					<small class="fw-bold">
						<LocaleText t="Email Body Template"></LocaleText>
					</small>
				</label>
				<textarea class="form-control rounded-3 font-monospace"
						  v-model="store.Configuration.Email.email_template"
						  id="email_template"
						  style="min-height: 400px"></textarea>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>