<script>
import { ref, watch, onMounted } from 'vue'
import { fetchGet, fetchPost } from '@/utilities/fetch.js'
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"
import ProcessWidget from '@/components/ProcessWidget.vue'
import TorLogViewer from '@/components/TorLogViewer.vue'

export default {
    name: 'TorConfiguration',
    components: {
        ProcessWidget,
        TorLogViewer
    },
    setup() {
        const dashboardStore = DashboardConfigurationStore()
        const selectedConfig = ref('main')
        const configContent = ref('')
        const loading = ref(false)
        const refreshLoading = ref(false)
        const reloadLoading = ref(false)
        const currentPlugin = ref('obfs4')
        const availablePlugins = ref(['obfs4', 'webtunnel', 'snowflake'])
        const useBridges = ref(true)
        const torStatus = ref({
            main: false,
            dns: false
        })
        const configPlugins = ref({
            main: 'obfs4',
            dns: 'obfs4'
        })
        const processLoading = ref(false)

        const generatePluginConfig = (plugin) => {
            let config = ''
            switch(plugin) {
                case 'snowflake':
                    config = `UseBridges 1
ClientTransportPlugin snowflake exec /usr/local/bin/snowflake
Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn
Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478 utls-imitate=hellorandomizedalpn`
                    break
                case 'obfs4':
                case 'webtunnel':
                    config = `UseBridges 1
ClientTransportPlugin ${plugin} exec /usr/local/bin/${plugin}`
                    break
                default:
                    config = `ClientTransportPlugin ${plugin} exec /usr/local/bin/${plugin}`
            }
            return config
        }

        const refreshBridges = async () => {
            try {
                refreshLoading.value = true
                console.log('Refreshing bridges for plugin:', currentPlugin.value)
                
                await fetchPost('/api/tor/bridges/refresh', {
                    plugin: currentPlugin.value,
                    configType: selectedConfig.value
                }, (res) => {
                    if (res.status) {
                        // Update config content with new bridges
                        configContent.value = res.data.config
                        dashboardStore.newMessage('Server', 'Bridges refreshed successfully', 'success')
                    } else {
                        throw new Error(res.message || 'Failed to refresh bridges')
                    }
                })
            } catch (error) {
                console.error('Bridge refresh error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to refresh bridges', 'error')
            } finally {
                refreshLoading.value = false
            }
        }

        const setPlugin = async (plugin) => {
            try {
                loading.value = true
                console.log('Setting plugin to:', plugin)
                
                await fetchPost('/api/tor/plugin/update', {
                    plugin: plugin,
                    configType: selectedConfig.value,
                    useBridges: useBridges.value
                }, async (res) => {
                    if (res.status) {
                        currentPlugin.value = plugin
                        configPlugins.value[selectedConfig.value] = plugin
                        configContent.value = res.data.config
                        
                        // Automatically refresh bridges for obfs4 and webtunnel
                        if (['obfs4', 'webtunnel'].includes(plugin) && useBridges.value) {
                            await refreshBridges()
                        }
                        
                        dashboardStore.newMessage('Server', `Switched to ${plugin} plugin`, 'success')
                    } else {
                        throw new Error(res.message || 'Failed to switch plugin')
                    }
                })
            } catch (error) {
                console.error('Plugin switch error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to switch plugin', 'error')
            } finally {
                loading.value = false
            }
        }

        const toggleBridges = async () => {
            try {
                useBridges.value = !useBridges.value
                
                // Update config with new bridge state
                await fetchPost('/api/tor/plugin/update', {
                    plugin: currentPlugin.value,
                    configType: selectedConfig.value,
                    useBridges: useBridges.value
                }, async (res) => {
                    if (res.status) {
                        configContent.value = res.data.config
                        if (useBridges.value && ['obfs4', 'webtunnel'].includes(currentPlugin.value)) {
                            await refreshBridges()
                        }
                        dashboardStore.newMessage('Server', `Bridges ${useBridges.value ? 'enabled' : 'disabled'}`, 'success')
                    } else {
                        throw new Error(res.message || 'Failed to toggle bridges')
                    }
                })
            } catch (error) {
                console.error('Bridge toggle error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to toggle bridges', 'error')
                useBridges.value = !useBridges.value // Revert on error
            }
        }

        const saveConfig = async () => {
            try {
                loading.value = true
                console.log('Saving config:', configContent.value)
                
                await fetchPost('/api/tor/config/update', {
                    type: selectedConfig.value,
                    content: configContent.value,
                    plugin: currentPlugin.value
                }, (response) => {
                    if (response?.status) {
                        dashboardStore.newMessage('Server', 'Configuration saved successfully', 'success')
                    } else {
                        throw new Error(response?.message || 'Failed to save configuration')
                    }
                })
            } catch (error) {
                console.error('Save config error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to save configuration', 'error')
                throw error
            } finally {
                loading.value = false
            }
        }

        const toggleTorProcess = async () => {
            try {
                processLoading.value = true
                const isRunning = torStatus.value[selectedConfig.value]
                const action = isRunning ? 'stop' : 'start'
                
                console.log(`${action} Tor process for ${selectedConfig.value} configuration`)
                
                await fetchPost('/api/tor/process/control', {
                    action: action,
                    configType: selectedConfig.value
                }, (res) => {
                    if (res.status) {
                        // Update status
                        torStatus.value[selectedConfig.value] = !isRunning
                        dashboardStore.newMessage('Server', `Tor ${selectedConfig.value} process ${action}ed successfully`, 'success')
                    } else {
                        throw new Error(res.message || `Failed to ${action} Tor process`)
                    }
                })
            } catch (error) {
                console.error('Process control error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to control Tor process', 'error')
            } finally {
                processLoading.value = false
            }
        }

        const getTorStatus = async () => {
            try {
                await fetchGet('/api/tor/process/status', {}, (response) => {
                    if (response?.status) {
                        torStatus.value = response.data
                        console.log('Tor status:', torStatus.value)
                    } else {
                        throw new Error(response?.message || 'Failed to get Tor status')
                    }
                })
            } catch (error) {
                console.error('Get status error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to get Tor status', 'error')
            }
        }

        // Watch for config type changes to reload content
        watch(selectedConfig, () => {
            loadConfig()
        })

        const loadConfig = async () => {
            try {
                reloadLoading.value = true
                console.log('Loading config for type:', selectedConfig.value)
                await fetchGet('/api/tor/config', {}, (response) => {
                    console.log('Full config response:', response)
                    if (response?.status) {
                        // Update config content based on selected type
                        configContent.value = response.data?.configs?.[selectedConfig.value] || ''
                        console.log('Updated config content:', configContent.value)
                        
                        // Update plugins for both configs if available
                        if (response.data?.plugins) {
                            // Update configPlugins for both main and dns
                            if (response.data.plugins.main) {
                                configPlugins.value.main = response.data.plugins.main
                            }
                            if (response.data.plugins.dns) {
                                configPlugins.value.dns = response.data.plugins.dns
                            }
                            // Set current plugin based on selected config
                            currentPlugin.value = response.data.plugins[selectedConfig.value] || configPlugins.value[selectedConfig.value] || 'obfs4'
                        } else {
                            // Fallback: try to detect from config content or use stored/default value
                            currentPlugin.value = configPlugins.value[selectedConfig.value] || 'obfs4'
                        }
                        console.log('Current plugin set to:', currentPlugin.value)
                        console.log('All plugins:', configPlugins.value)
                    } else {
                        throw new Error(response?.message || 'Failed to load configuration')
                    }
                })
            } catch (error) {
                console.error('Load config error:', error)
                dashboardStore.newMessage('Error', error.message || 'Failed to load configuration', 'error')
                configContent.value = '' // Reset content on error
            } finally {
                reloadLoading.value = false
            }
        }

        onMounted(async () => {
            await loadConfig()  // Load the configuration
            await getTorStatus() // Get Tor process status
        })

        return {
            selectedConfig,
            configContent,
            loading,
            refreshLoading,
            reloadLoading,
            currentPlugin,
            availablePlugins,
            setPlugin,
            saveConfig,
            loadConfig,
            refreshBridges,
            useBridges,
            toggleBridges,
            torStatus,
            toggleTorProcess,
            processLoading
        }
    }
}
</script>

<template>
    <div class="container-fluid py-3">
        <div class="row">
            <div class="col-12 mb-3">
                <ProcessWidget />
            </div>
            
            <div class="col-12">
                <div class="card shadow-sm">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Tor Configuration Manager</h5>
                        <div class="d-flex align-items-center gap-3">
                            <span>
                                <span class="text-warning">Current:</span> <span class="text-danger">{{ selectedConfig === 'main' ? 'Main Torrc' : 'DNS Torrc' }}</span>
                            </span>
                            
                            <div class="btn-group">
                                <button 
                                    class="btn" 
                                    :class="selectedConfig === 'main' ? 'tor-config-btn-active' : 'tor-config-btn-inactive'"
                                    @click="selectedConfig = 'main'"
                                    :disabled="loading"
                                >
                                    Main Torrc
                                </button>
                                <button 
                                    class="btn" 
                                    :class="selectedConfig === 'dns' ? 'tor-config-btn-active' : 'tor-config-btn-inactive'"
                                    @click="selectedConfig = 'dns'"
                                    :disabled="loading"
                                >
                                    DNS Torrc
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card-body">
                        <!-- Process Control -->
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="form-label mb-0" role="heading" aria-level="2">Tor Process Control</span>
                                <div class="d-flex align-items-center">
                                    <span class="me-2">Status:</span>
                                    <span 
                                        class="badge" 
                                        :class="torStatus[selectedConfig] ? 'bg-success' : 'bg-danger'"
                                    >
                                        {{ torStatus[selectedConfig] ? 'Running' : 'Stopped' }}
                                    </span>
                                </div>
                            </div>
                            <button 
                                class="btn w-100"
                                :class="torStatus[selectedConfig] ? 'btn-danger' : 'btn-success'"
                                @click="toggleTorProcess"
                                :disabled="processLoading"
                            >
                                <i class="bi" :class="processLoading ? 'bi-hourglass-split' : (torStatus[selectedConfig] ? 'bi-stop-fill' : 'bi-play-fill')"></i>
                                {{ processLoading ? 'Processing...' : (torStatus[selectedConfig] ? `Stop ${selectedConfig === 'main' ? 'Main' : 'DNS'} Tor` : `Start ${selectedConfig === 'main' ? 'Main' : 'DNS'} Tor`) }}
                            </button>
                        </div>
                        
                        <!-- Plugin Selection -->
                        <div class="mb-3">
                            <div class="mb-3 d-flex gap-2 align-items-center">
                                <button 
                                    class="btn"
                                    :class="useBridges ? 'tor-bridge-btn-active' : 'tor-bridge-btn-inactive'"
                                    @click="toggleBridges"
                                    :disabled="loading"
                                >
                                    <i class="bi" :class="useBridges ? 'bi-shield-check' : 'bi-shield-x'"></i>
                                    {{ useBridges ? 'Bridges Enabled' : 'Bridges Disabled' }}
                                </button>
                                
                                <button 
                                    v-if="['obfs4', 'webtunnel'].includes(currentPlugin) && useBridges"
                                    class="btn tor-refresh-btn-inactive btn-reload"
                                    @click="refreshBridges"
                                    :disabled="refreshLoading"
                                    :class="{ 'is-loading': refreshLoading }"
                                >
                                    <i class="bi bi-arrow-repeat me-1"></i>
                                    Refresh Bridges
                                </button>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="form-label mb-0" role="heading" aria-level="2">Tor Plugin</span>
                            </div>
                            <div class="btn-group w-100">
                                <button 
                                    v-for="plugin in availablePlugins" 
                                    :key="plugin"
                                    class="btn" 
                                    :class="currentPlugin === plugin ? 'tor-plugin-btn-active' : 'tor-plugin-btn-inactive'"
                                    @click="setPlugin(plugin)"
                                    :disabled="loading"
                                >
                                    {{ plugin }}
                                </button>
                            </div>
                        </div>

                        <!-- Configuration Editor -->
                        <div class="form-group">
                            <label for="torConfigEditor" class="form-label">Configuration</label>
                            <textarea 
                                id="torConfigEditor"
                                name="torConfig"
                                v-model="configContent"
                                class="form-control font-monospace"
                                rows="30"
                                style="resize: vertical;"
                                :disabled="loading"
                            ></textarea>
                        </div>
                    </div>

                    <div class="card-footer">
                        <div class="d-flex justify-content-between">
                            <button 
                                class="btn tor-footer-btn-inactive" 
                                @click="loadConfig"
                                :disabled="reloadLoading"
                                :class="{ 'is-loading': reloadLoading }"
                            >
                                <i class="bi bi-arrow-clockwise me-1"></i>
                                Refresh Tor Config File
                            </button>
                            <button 
                                class="btn tor-footer-btn-inactive" 
                                @click="saveConfig"
                                :disabled="loading"
                                :class="{ 'is-loading': loading }"
                            >
                                <i class="bi me-1" :class="loading ? 'bi-hourglass-split' : 'bi-save'"></i>
                                {{ loading ? 'Saving...' : 'Save & Reload Tor' }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Add the log viewer component -->
            <div class="col-12 mt-3">
                <TorLogViewer :configType="selectedConfig" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.bi-arrow-repeat,
.bi-arrow-clockwise,
.bi-hourglass-split {
    display: inline-block;
    transition: transform 0.4s ease;
}

/* Only apply animation to the button that is loading */
.btn-reload.is-loading .bi-arrow-repeat,
.btn-outline-primary.is-loading .bi-arrow-clockwise,
.tor-footer-btn-inactive.is-loading .bi-hourglass-split {
    animation: spin 1s linear infinite;
}

.btn

/* Style the button when disabled/loading */
.btn-reload.is-loading,
.btn-outline-primary.is-loading {
    opacity: 1 !important;
    background-color: var(--brandColor8) !important;
    color: white !important;
    border-color: var(--brandColor4) !important;
    --bs-primary-bg-subtle: var(--brandColor8) !important;
    position: relative;
    overflow: hidden;
}

.tor-footer-btn-inactive.is-loading {
    opacity: 1 !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    border-color: #000000 !important;
    position: relative;
    overflow: hidden;
}

.btn-reload.is-loading::before,
.btn-outline-primary.is-loading::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        var(--brandColor4),
        transparent
    );
    animation: loading 1.5s infinite;
}

.btn-reload.is-loading::after,
.btn-outline-primary.is-loading::after {
    content: '';
    position: absolute;
    top: 0;
    right: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgb(0, 255, 106),
        transparent
    );
    animation: loading 1.5s infinite;
    animation-delay: 0.75s;
}

.tor-footer-btn-inactive.is-loading::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(0, 0, 0, 0.3),
        transparent
    );
    animation: loading 1.5s infinite;
}

.tor-footer-btn-inactive.is-loading::after {
    content: '';
    position: absolute;
    top: 0;
    right: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.3),
        transparent
    );
    animation: loading 1.5s infinite;
    animation-delay: 0.75s;
}

@keyframes loading {
    100% {
        transform: translateX(200%);
    }
}

@keyframes spin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

/* Tor Configuration Button Styling - Inverted Theme */
.tor-config-btn-inactive {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
    transition: all 0.2s ease-in-out;
}

.tor-config-btn-inactive:hover {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-config-btn-active {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-bridge-btn-inactive {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
    transition: all 0.2s ease-in-out;
}

.tor-bridge-btn-inactive:hover {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-bridge-btn-active {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-plugin-btn-inactive {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
    transition: all 0.2s ease-in-out;
}

.tor-plugin-btn-inactive:hover {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-plugin-btn-active {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-refresh-btn-inactive {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
    transition: all 0.2s ease-in-out;
}

.tor-refresh-btn-inactive:hover {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

.tor-footer-btn-inactive {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
    transition: all 0.2s ease-in-out;
}

.tor-footer-btn-inactive:hover {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

/* Light theme styles */
[data-bs-theme="light"] .tor-config-btn-inactive {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

[data-bs-theme="light"] .tor-config-btn-inactive:hover {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-config-btn-active {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-bridge-btn-inactive {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

[data-bs-theme="light"] .tor-bridge-btn-inactive:hover {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-bridge-btn-active {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-plugin-btn-inactive {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

[data-bs-theme="light"] .tor-plugin-btn-inactive:hover {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-plugin-btn-active {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-refresh-btn-inactive {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

[data-bs-theme="light"] .tor-refresh-btn-inactive:hover {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}

[data-bs-theme="light"] .tor-footer-btn-inactive {
    background-color: #ffffff !important;
    border: 1px solid #000000 !important;
    color: #000000 !important;
}

[data-bs-theme="light"] .tor-footer-btn-inactive:hover {
    background-color: #000000 !important;
    border: 1px solid #ffffff !important;
    color: #ffffff !important;
}
</style>