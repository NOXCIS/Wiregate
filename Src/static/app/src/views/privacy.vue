<template>
	<div class="container py-4">
		<div class="row justify-content-center">
			<div class="col-lg-10 col-xl-8">
				<div class="card shadow-sm">
					<div class="card-header">
						<h1 class="h3 mb-0">Privacy Policy</h1>
						<p class="text-muted mb-0">Last Updated: November 2, 2025</p>
					</div>
					<div class="card-body">
						<section class="mb-4">
							<h2>1. Introduction</h2>
							<p>
								WireGate is a self-hosted VPN dashboard that you run on your own server. This Privacy Policy explains how WireGate handles your data when you use the dashboard.
							</p>
							<p>
								<strong>Important:</strong> WireGate is designed to be completely self-hosted. All your data remains on your server and is never transmitted to external servers. The only external communication is a one-way fetch from GitHub to check for available updates (no data is sent).
							</p>
						</section>

						<section class="mb-4">
							<h2>2. Data Collection</h2>
							<p>
								<strong>WireGate does not collect or transmit user data to external servers.</strong> All information remains on your server:
							</p>
							<ul>
								<li><strong>Configuration Data:</strong> WireGuard configurations, peer information, and network settings are stored locally on your server</li>
								<li><strong>Account Information:</strong> Username and password for dashboard access are stored only on your server</li>
								<li><strong>Usage Data:</strong> Network traffic statistics and connection logs remain on your server</li>
								<li><strong>Session Information:</strong> Authentication tokens and session data are stored locally</li>
							</ul>
							<p>
								WireGate does not use analytics, tracking pixels, or any data collection mechanisms that send information to third parties.
							</p>
						</section>

						<section class="mb-4">
							<h2>3. External Communications</h2>
							<h3>3.1 Update Status Checks</h3>
							<p>
								WireGate automatically checks for software updates by fetching version information from GitHub. This check:
							</p>
							<ul>
								<li><strong>Fetches version information from GitHub</strong> - WireGate downloads a public list of available versions</li>
								<li><strong>Compares locally</strong> - The comparison between your current version and available versions happens on your server</li>
								<li><strong>No data transmitted</strong> - Your version number, configuration data, or any other information is never sent to external servers</li>
							</ul>
							<p>
								This is a one-way fetch operation - WireGate downloads public information but never uploads any data about your installation.
							</p>

							<h3>3.2 Third-Party Service Integrations</h3>
							<p>
								WireGate may optionally integrate with external services (such as OpenStreetMap for network mapping) 
								only if you explicitly configure such integrations. These services have their own privacy policies, 
								and any data sent to them is done so at your discretion.
							</p>
						</section>

						<section class="mb-4">
							<h2>4. Data Storage and Security</h2>
							<p>
								All your data is stored locally on your server. You have complete control over:
							</p>
							<ul>
								<li>Where data is stored (database location and configuration)</li>
								<li>How data is backed up</li>
								<li>Data retention policies</li>
								<li>Access controls and authentication settings</li>
							</ul>

							<h3>Security Features</h3>
							<p>WireGate includes security features to protect your self-hosted installation:</p>
							<ul>
								<li>Encrypted authentication tokens and secure session management</li>
								<li>Rate limiting and brute force protection</li>
								<li>CSRF protection for state-changing operations</li>
								<li>Security headers and policies</li>
								<li>Optional two-factor authentication (TOTP)</li>
							</ul>
						</section>

						<section class="mb-4">
							<h2>5. Your Control</h2>
							<p>
								Since WireGate is self-hosted, you have complete control over your data:
							</p>
							<ul>
								<li><strong>Full Access:</strong> You can view, modify, or delete any data stored by WireGate</li>
								<li><strong>Export:</strong> You can export your configuration data at any time</li>
								<li><strong>Backup:</strong> You control backup and retention policies</li>
								<li><strong>Deletion:</strong> You can delete all data by removing the installation or database</li>
								<li><strong>Privacy:</strong> No data leaves your server unless you explicitly configure it</li>
							</ul>
						</section>

						<section class="mb-4">
							<h2>6. Cookies and Local Storage</h2>
							<p>
								WireGate uses essential session cookies and authentication tokens to maintain your login session. 
								These are stored locally in your browser and on your server. WireGate does not use:
							</p>
							<ul>
								<li>Third-party analytics cookies</li>
								<li>Advertising or tracking pixels</li>
								<li>Cross-site tracking mechanisms</li>
								<li>Persistent cookies beyond session management</li>
							</ul>
						</section>

						<section class="mb-4">
							<h2>7. No Data Sharing</h2>
							<p>
								WireGate does not share, sell, trade, or transmit your data to any external parties. 
								Since the application runs on your server, all data remains under your control.
							</p>
						</section>

						<section class="mb-4">
							<h2>8. Open Source and Transparency</h2>
							<p>
								WireGate is open source software. You can review the source code to verify:
							</p>
							<ul>
								<li>What data is stored locally</li>
								<li>What external communications (if any) are made</li>
								<li>How security features are implemented</li>
								<li>That no hidden data collection occurs</li>
							</ul>
						</section>

						<section class="mb-4">
							<h2>9. Contact and Support</h2>
							<p>
								If you have questions about WireGate's privacy practices or how it handles data, 
								please refer to the project documentation or GitHub repository. Since WireGate is self-hosted, 
								your system administrator is responsible for your specific installation.
							</p>
						</section>

						<section class="mb-4">
							<h2>10. Changes to This Privacy Policy</h2>
							<p>
								This Privacy Policy may be updated from time to time to reflect changes in WireGate functionality. 
								The "Last Updated" date at the top indicates when changes were made. Since WireGate is self-hosted, 
								you control when and if you update to newer versions.
							</p>
						</section>

						<div class="mt-4 pt-4 border-top">
							<RouterLink to="/signin" class="btn btn-outline-secondary">
								<i class="bi bi-arrow-left me-2"></i>Back to Sign In
							</RouterLink>
							<RouterLink to="/" v-if="isAuthenticated" class="btn btn-outline-primary ms-2">
								<i class="bi bi-house me-2"></i>Go to Dashboard
							</RouterLink>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js";

export default {
	name: "Privacy",
	setup() {
		const dashboardStore = DashboardConfigurationStore();
		return { dashboardStore };
	},
	computed: {
		isAuthenticated() {
			// Check if user is authenticated (basic check)
			return this.dashboardStore.Configuration !== undefined;
		}
	}
};
</script>

<style scoped>
.card {
	border: 1px solid rgba(255, 255, 255, 0.1);
}

.card-header {
	background-color: rgba(0, 0, 0, 0.05);
	border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.card-body {
	line-height: 1.8;
}

section h2 {
	color: inherit;
	font-size: 1.5rem;
	margin-top: 2rem;
	margin-bottom: 1rem;
}

section h3 {
	color: inherit;
	font-size: 1.2rem;
	margin-top: 1.5rem;
	margin-bottom: 0.75rem;
}

section ul {
	padding-left: 1.5rem;
}

section ul li {
	margin-bottom: 0.5rem;
}

section p {
	margin-bottom: 1rem;
}

[data-bs-theme="light"] .card {
	border-color: rgba(0, 0, 0, 0.1);
}

[data-bs-theme="light"] .card-header {
	background-color: rgba(0, 0, 0, 0.02);
	border-bottom-color: rgba(0, 0, 0, 0.1);
}
</style>

