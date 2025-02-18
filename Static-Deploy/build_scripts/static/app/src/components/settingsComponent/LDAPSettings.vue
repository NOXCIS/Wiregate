<template>
	<div class="ldap-settings">
		<div class="form-check form-switch mb-3">
			<input class="form-check-input" type="checkbox" v-model="settings.enabled" id="ldapEnabled">
			<label class="form-check-label" for="ldapEnabled">
				<LocaleText t="Enable LDAP Authentication"></LocaleText>
			</label>
		</div>

		<div v-if="settings.enabled" class="ldap-config">
			<div class="row g-3">
				<div class="col-md-8">
					<label class="form-label">
						<LocaleText t="LDAP Server"></LocaleText>
					</label>
					<input type="text" class="form-control" v-model="settings.server" placeholder="ldap.example.com">
				</div>

				<div class="col-md-4">
					<label class="form-label">
						<LocaleText t="Port"></LocaleText>
					</label>
					<input type="number" class="form-control" v-model="settings.port" placeholder="389">
				</div>

				<div class="col-12">
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox" v-model="settings.use_ssl" id="useSSL">
						<label class="form-check-label" for="useSSL">
							<LocaleText t="Use SSL/LDAPS"></LocaleText>
						</label>
					</div>
				</div>

				<div class="col-12">
					<label class="form-label">
						<LocaleText t="Domain"></LocaleText>
					</label>
					<input type="text" class="form-control" v-model="settings.domain" placeholder="example.com">
				</div>

				<div class="col-12">
					<label class="form-label">
						<LocaleText t="Bind DN"></LocaleText>
					</label>
					<input type="text" class="form-control" v-model="settings.bind_dn" 
						   placeholder="CN=Service Account,OU=Users,DC=example,DC=com">
				</div>

				<div class="col-12">
					<label class="form-label">
						<LocaleText t="Bind Password"></LocaleText>
					</label>
					<input type="password" class="form-control" v-model="settings.bind_password">
				</div>

				<div class="col-12">
					<label class="form-label">
						<LocaleText t="Search Base"></LocaleText>
					</label>
					<input type="text" class="form-control" v-model="settings.search_base" 
						   placeholder="DC=example,DC=com">
				</div>

				<div class="col-12">
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox" v-model="settings.require_group" id="requireGroup">
						<label class="form-check-label" for="requireGroup">
							<LocaleText t="Require Group Membership"></LocaleText>
						</label>
					</div>
				</div>

				<div class="col-12" v-if="settings.require_group">
					<label class="form-label">
						<LocaleText t="Group DN"></LocaleText>
					</label>
					<input type="text" class="form-control" v-model="settings.group_dn" 
						   placeholder="CN=WireGate Users,OU=Groups,DC=example,DC=com">
				</div>

				<div class="col-12 d-flex gap-2">
					<button class="btn btn-secondary" @click="testConnection" :disabled="testing">
						{{ testing ? 'Testing...' : 'Test Connection' }}
					</button>
					<button class="btn btn-primary" @click="saveSettings" :disabled="saving">
						{{ saving ? 'Saving...' : 'Save Settings' }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: 'LDAPSettings',
	components: {
		LocaleText
	},
	data() {
		return {
			settings: {
				enabled: false,
				server: '',
				port: '389',
				use_ssl: false,
				domain: '',
				bind_dn: '',
				bind_password: '',
				search_base: '',
				search_filter: '(sAMAccountName=%s)',
				require_group: false,
				group_dn: ''
			},
			testing: false,
			saving: false
		}
	},
	async mounted() {
		try {
			const response = await fetchGet('/api/getLDAPSettings')
			if (response.status) {
				this.settings = { ...this.settings, ...response.data }
			}
		} catch (error) {
			console.error('Failed to load LDAP settings:', error)
		}
	},
	methods: {
		async testConnection() {
			this.testing = true
			try {
				const response = await fetchPost('/api/testLDAPConnection', this.settings)
				if (response.status) {
					this.$root.$emit('showMessage', 'LDAP Connection Test', 'Connection successful!', 'success')
				} else {
					this.$root.$emit('showMessage', 'LDAP Connection Test', `Connection failed: ${response.message}`, 'error')
				}
			} finally {
				this.testing = false
			}
		},
		async saveSettings() {
			this.saving = true
			try {
				const response = await fetchPost('/api/saveLDAPSettings', this.settings)
				if (response.status) {
					this.$root.$emit('showMessage', 'LDAP Settings', 'Settings saved successfully!', 'success')
				} else {
					this.$root.$emit('showMessage', 'LDAP Settings', `Failed to save settings: ${response.message}`, 'error')
				}
			} finally {
				this.saving = false
			}
		}
	}
}
</script> 