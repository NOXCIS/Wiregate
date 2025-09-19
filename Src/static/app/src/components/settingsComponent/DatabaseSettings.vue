<template>
	<form data-form-type="other" autocomplete="off">
		<div class="d-flex flex-column gap-3">

		<!-- Redis Configuration -->
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<LocaleText t="Redis Configuration"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<div class="row g-3">
					<div class="col-md-6">
						<label for="redisHost" class="form-label">
							<LocaleText t="Redis Host"></LocaleText>
						</label>
						<input 
							type="text" 
							class="form-control" 
							id="redisHost"
							name="redisHost"
							v-model="databaseConfig.redis.host"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="redisPort" class="form-label">
							<LocaleText t="Redis Port"></LocaleText>
						</label>
						<input 
							type="number" 
							class="form-control" 
							id="redisPort"
							name="redisPort"
							v-model="databaseConfig.redis.port"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="redisPassword" class="form-label">
							<LocaleText t="Redis Password"></LocaleText>
						</label>
						<input 
							type="password" 
							class="form-control" 
							id="redisPassword"
							name="redisPassword"
							v-model="databaseConfig.redis.password"
							@change="updateDatabaseConfig"
							autocomplete="off"
						>
					</div>
					<div class="col-md-6">
						<label for="redisDb" class="form-label">
							<LocaleText t="Redis Database"></LocaleText>
						</label>
						<input 
							type="number" 
							class="form-control" 
							id="redisDb"
							name="redisDb"
							v-model="databaseConfig.redis.db"
							@change="updateDatabaseConfig"
						>
					</div>
				</div>
			</div>
		</div>

		<!-- PostgreSQL Configuration -->
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<LocaleText t="PostgreSQL Configuration"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<div class="row g-3">
					<div class="col-md-6">
						<label for="postgresHost" class="form-label">
							<LocaleText t="PostgreSQL Host"></LocaleText>
						</label>
						<input 
							type="text" 
							class="form-control" 
							id="postgresHost"
							name="postgresHost"
							v-model="databaseConfig.postgres.host"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="postgresPort" class="form-label">
							<LocaleText t="PostgreSQL Port"></LocaleText>
						</label>
						<input 
							type="number" 
							class="form-control" 
							id="postgresPort"
							name="postgresPort"
							v-model="databaseConfig.postgres.port"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="postgresDb" class="form-label">
							<LocaleText t="Database Name"></LocaleText>
						</label>
						<input 
							type="text" 
							class="form-control" 
							id="postgresDb"
							name="postgresDb"
							v-model="databaseConfig.postgres.db"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="postgresUser" class="form-label">
							<LocaleText t="Username"></LocaleText>
						</label>
						<input 
							type="text" 
							class="form-control" 
							id="postgresUser"
							name="postgresUser"
							v-model="databaseConfig.postgres.user"
							@change="updateDatabaseConfig"
						>
					</div>
					<div class="col-md-6">
						<label for="postgresPassword" class="form-label">
							<LocaleText t="Password"></LocaleText>
						</label>
						<input 
							type="password" 
							class="form-control" 
							id="postgresPassword"
							name="postgresPassword"
							v-model="databaseConfig.postgres.password"
							@change="updateDatabaseConfig"
							autocomplete="off"
						>
					</div>
					<div class="col-md-6">
						<label for="postgresSslMode" class="form-label">
							<LocaleText t="SSL Mode"></LocaleText>
						</label>
						<select 
							class="form-select" 
							id="postgresSslMode"
							name="postgresSslMode"
							v-model="databaseConfig.postgres.ssl_mode"
							@change="updateDatabaseConfig"
						>
							<option value="disable">Disable</option>
							<option value="allow">Allow</option>
							<option value="prefer">Prefer</option>
							<option value="require">Require</option>
							<option value="verify-ca">Verify CA</option>
							<option value="verify-full">Verify Full</option>
						</select>
					</div>
				</div>
			</div>
		</div>

		<!-- Cache Configuration -->
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<LocaleText t="Cache Configuration"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<div class="row g-3">
					<div class="col-md-6">
						<div class="form-check form-switch">
							<input 
								class="form-check-input" 
								type="checkbox" 
								id="cacheEnabled"
								name="cacheEnabled"
								v-model="databaseConfig.cache.enabled"
								@change="updateDatabaseConfig"
							>
							<label class="form-check-label" for="cacheEnabled">
								<LocaleText t="Enable Caching"></LocaleText>
							</label>
						</div>
					</div>
					<div class="col-md-6">
						<label for="cacheTtl" class="form-label">
							<LocaleText t="Cache TTL (seconds)"></LocaleText>
						</label>
						<input 
							type="number" 
							class="form-control" 
							id="cacheTtl"
							name="cacheTtl"
							v-model="databaseConfig.cache.ttl"
							@change="updateDatabaseConfig"
							:disabled="!databaseConfig.cache.enabled"
						>
					</div>
				</div>
			</div>
		</div>

		<!-- Database Statistics -->
		<div class="card rounded-3">
			<div class="card-header d-flex justify-content-between align-items-center">
				<h6 class="my-2">
					<LocaleText t="Database Statistics"></LocaleText>
				</h6>
				<button 
					id="refreshStatsBtn"
					class="btn btn-outline-primary btn-sm" 
					@click="refreshStats"
					:disabled="loading"
					aria-label="Refresh database statistics"
				>
					<i class="bi bi-arrow-clockwise" :class="{'spinning': loading}"></i>
					<LocaleText t="Refresh"></LocaleText>
				</button>
			</div>
			<div class="card-body">
				<div v-if="loading" class="text-center">
					<div class="spinner-border text-primary" role="status">
						<span class="visually-hidden">Loading...</span>
					</div>
				</div>
				<div v-else-if="databaseStats" class="row g-3">
					<div class="col-md-3">
						<div class="card bg-light">
							<div class="card-body text-center">
								<h5 class="card-title">{{ databaseStats.total_peers || 0 }}</h5>
								<p class="card-text small">Total Peers</p>
							</div>
						</div>
					</div>
					<div class="col-md-3">
						<div class="card bg-light">
							<div class="card-body text-center">
								<h5 class="card-title">{{ databaseStats.total_configurations || 0 }}</h5>
								<p class="card-text small">Configurations</p>
							</div>
						</div>
					</div>
					<div class="col-md-3">
						<div class="card bg-light">
							<div class="card-body text-center">
								<h5 class="card-title">
									<i class="bi" :class="databaseStats.redis_connected ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'"></i>
								</h5>
								<p class="card-text small">Redis Status</p>
							</div>
						</div>
					</div>
					<div class="col-md-3">
						<div class="card bg-light">
							<div class="card-body text-center">
								<h5 class="card-title">
									<i class="bi" :class="databaseStats.postgres_connected ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'"></i>
								</h5>
								<p class="card-text small">PostgreSQL Status</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Database Actions -->
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<LocaleText t="Database Actions"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<div class="row g-3">
					<div class="col-md-6">
						<button 
							id="testConnectionsBtn"
							class="btn btn-outline-primary w-100" 
							@click="testConnections"
							:disabled="testing"
							aria-label="Test database connections"
						>
							<i class="bi bi-wifi" :class="{'spinning': testing}"></i>
							<LocaleText t="Test Connections"></LocaleText>
						</button>
					</div>
					<div class="col-md-6">
						<button 
							id="clearCacheBtn"
							class="btn btn-outline-danger w-100" 
							@click="clearCache"
							:disabled="clearing"
							aria-label="Clear database cache"
						>
							<i class="bi bi-trash" :class="{'spinning': clearing}"></i>
							<LocaleText t="Clear Cache"></LocaleText>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
	</form>

	<!-- Clear Cache Confirmation Modal -->
	<Transition name="zoomReversed">
		<div v-if="showClearCacheConfirmation"
			 class="position-fixed w-100 h-100 top-0 start-0 d-flex align-items-center justify-content-center confirmationContainer"
			 style="z-index: 1050;">
			<div class="card rounded-3 shadow" style="max-width: 400px; width: 90%;">
				<div class="card-body text-center">
					<h5 class="mb-3">
						<LocaleText t="Clear Database Cache"></LocaleText>
					</h5>
					<p class="text-muted mb-4">
						<LocaleText t="This will clear all cached data. Are you sure?"></LocaleText>
					</p>
					<div class="d-flex gap-2 justify-content-center">
						<button class="btn btn-danger rounded-3"
								:disabled="clearing"
								@click="confirmClearCache()">
							<i class="bi bi-trash me-2" :class="{'spinning': clearing}"></i>
							<LocaleText t="Yes, Clear Cache"></LocaleText>
						</button>
						<button @click="showClearCacheConfirmation = false"
								:disabled="clearing"
								class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
							<LocaleText t="Cancel"></LocaleText>
						</button>
					</div>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script>
import LocaleText from "@/components/text/localeText.vue";
import { ref, onMounted, onUnmounted } from 'vue';

export default {
	name: "DatabaseSettings",
	components: {
		LocaleText
	},
	setup() {
		const loading = ref(false);
		const testing = ref(false);
		const clearing = ref(false);
		const showClearCacheConfirmation = ref(false);
		
		const databaseConfig = ref({
			redis: {
				host: 'redis',
				port: 6379,
				password: 'wiregate_redis_password',
				db: 0
			},
			postgres: {
				host: 'postgres',
				port: 5432,
				db: 'wiregate',
				user: 'wiregate_user',
				password: 'wiregate_postgres_password',
				ssl_mode: 'disable'
			},
			cache: {
				enabled: true,
				ttl: 300
			}
		});

		const databaseStats = ref(null);

		const loadDatabaseConfig = async () => {
			console.log('Loading database configuration...');
			try {
				const response = await fetch('/api/database/config');
				console.log('Config response status:', response.status);
				
				if (response.ok) {
					const config = await response.json();
					console.log('Config response data:', config);
					
					if (config.status) {
						// Preserve default passwords if API returns empty or masked passwords
						const apiData = config.data;
						
						// Ensure numeric values are properly converted
						const processNumericValue = (value, defaultValue) => {
							if (typeof value === 'number') return value;
							if (typeof value === 'string' && !isNaN(value)) return parseInt(value, 10);
							return defaultValue;
						};
						
						databaseConfig.value = { 
							...databaseConfig.value, 
							...apiData,
							redis: {
								...databaseConfig.value.redis,
								...apiData.redis,
								port: processNumericValue(apiData.redis?.port, databaseConfig.value.redis.port),
								db: processNumericValue(apiData.redis?.db, databaseConfig.value.redis.db),
								password: apiData.redis?.password && apiData.redis.password !== '***' && apiData.redis.password.length > 3 
									? apiData.redis.password 
									: databaseConfig.value.redis.password
							},
							postgres: {
								...databaseConfig.value.postgres,
								...apiData.postgres,
								port: processNumericValue(apiData.postgres?.port, databaseConfig.value.postgres.port),
								password: apiData.postgres?.password && apiData.postgres.password !== '***' && apiData.postgres.password.length > 3 
									? apiData.postgres.password 
									: databaseConfig.value.postgres.password
							},
							cache: {
								...databaseConfig.value.cache,
								...apiData.cache,
								ttl: processNumericValue(apiData.cache?.ttl, databaseConfig.value.cache.ttl)
							}
						};
						console.log('Updated database config:', databaseConfig.value);
					}
				} else {
					console.error('Failed to load config - HTTP error:', response.status, response.statusText);
				}
			} catch (error) {
				console.error('Failed to load database config:', error);
			}
		};

		const updateDatabaseConfig = async () => {
			try {
				const response = await fetch('/api/database/config', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(databaseConfig.value)
				});
				
				if (response.ok) {
					const result = await response.json();
					if (result.status) {
						// Show success message
						console.log('Database configuration updated successfully');
					}
				}
			} catch (error) {
				console.error('Failed to update database config:', error);
			}
		};

		const refreshStats = async () => {
			loading.value = true;
			console.log('Refreshing database statistics...');
			try {
				const response = await fetch('/api/database/stats');
				console.log('Stats response status:', response.status);
				
				if (response.ok) {
					const stats = await response.json();
					console.log('Stats response data:', stats);
					
					if (stats.status) {
						databaseStats.value = stats.data;
						console.log('Updated database stats:', databaseStats.value);
					}
				} else {
					console.error('Failed to load stats - HTTP error:', response.status, response.statusText);
				}
			} catch (error) {
				console.error('Failed to load database stats:', error);
			} finally {
				loading.value = false;
			}
		};

		const testConnections = async () => {
			testing.value = true;
			console.log('Testing database connections with config:', databaseConfig.value);
			
			// Create a copy of the config and ensure passwords are set correctly
			const configToSend = {
				...databaseConfig.value,
				redis: {
					...databaseConfig.value.redis,
					password: databaseConfig.value.redis.password || 'wiregate_redis_password'
				},
				postgres: {
					...databaseConfig.value.postgres,
					password: databaseConfig.value.postgres.password || 'wiregate_postgres_password'
				}
			};
			
			console.log('Config being sent:', JSON.stringify(configToSend, null, 2));
			console.log('Redis password length:', configToSend.redis.password.length);
			console.log('Postgres password length:', configToSend.postgres.password.length);
			
			try {
				const response = await fetch('/api/database/test', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(configToSend)
				});
				
				console.log('Database test response status:', response.status);
				console.log('Database test response ok:', response.ok);
				
				if (response.ok) {
					const result = await response.json();
					console.log('Database test result:', result);
					
					if (result.status) {
						console.log('Database connections successful:', result.data);
						// Use message system instead of alert
						const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
						const store = DashboardConfigurationStore();
						store.newMessage('Database', 'Database connections tested successfully!', 'success');
					} else {
						console.error('Database test failed:', result.message);
						const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
						const store = DashboardConfigurationStore();
						store.newMessage('Database', `Connection test failed: ${result.message}`, 'danger');
					}
				} else {
					console.error('Database test HTTP error:', response.status, response.statusText);
					const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
					const store = DashboardConfigurationStore();
					store.newMessage('Database', `HTTP Error ${response.status}: ${response.statusText}`, 'danger');
				}
			} catch (error) {
				console.error('Failed to test database connections:', error);
				const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
				const store = DashboardConfigurationStore();
				store.newMessage('Database', `Connection test failed: ${error.message}`, 'danger');
			} finally {
				testing.value = false;
			}
		};


		const clearCache = async () => {
			console.log('Clearing database cache...');
			
			showClearCacheConfirmation.value = true;
		};

		const confirmClearCache = async () => {
			showClearCacheConfirmation.value = false;
			clearing.value = true;
		try {
			const response = await fetch('/api/database/clear-cache', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({})
			});
				
				console.log('Clear cache response status:', response.status);
				
				if (response.ok) {
					const result = await response.json();
					console.log('Clear cache result:', result);
					
					const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
					const store = DashboardConfigurationStore();
					
					if (result.status) {
						store.newMessage('Database', 'Cache cleared successfully!', 'success');
					} else {
						store.newMessage('Database', `Failed to clear cache: ${result.message}`, 'danger');
					}
				} else {
					console.error('Clear cache HTTP error:', response.status, response.statusText);
					const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
					const store = DashboardConfigurationStore();
					store.newMessage('Database', `Clear cache HTTP Error ${response.status}: ${response.statusText}`, 'danger');
				}
			} catch (error) {
				console.error('Failed to clear cache:', error);
				const { DashboardConfigurationStore } = await import('@/stores/DashboardConfigurationStore.js');
				const store = DashboardConfigurationStore();
				store.newMessage('Database', `Failed to clear cache: ${error.message}`, 'danger');
			} finally {
				clearing.value = false;
			}
		};

		onMounted(() => {
			loadDatabaseConfig();
			refreshStats();
			
			// Set up automatic stats refresh every 10 seconds
			const statsInterval = setInterval(() => {
				refreshStats();
			}, 10000);
			
			// Clean up interval when component is unmounted
			onUnmounted(() => {
				clearInterval(statsInterval);
			});
		});

		return {
			loading,
			testing,
			clearing,
			showClearCacheConfirmation,
			databaseConfig,
			databaseStats,
			updateDatabaseConfig,
			refreshStats,
			testConnections,
			clearCache,
			confirmClearCache
		};
	}
};
</script>

<style scoped>
.spinning {
	animation: spin 1s linear infinite;
}

@keyframes spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

.card {
	transition: all 0.3s ease;
}

.card:hover {
	box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.form-check-input:checked {
	background-color: #0d6efd;
	border-color: #0d6efd;
}

.btn {
	transition: all 0.3s ease;
}

.btn:hover {
	transform: translateY(-1px);
}

.confirmationContainer {
	background-color: rgba(0, 0, 0, 0.53);
	backdrop-filter: blur(1px);
	-webkit-backdrop-filter: blur(1px);
}
</style>
