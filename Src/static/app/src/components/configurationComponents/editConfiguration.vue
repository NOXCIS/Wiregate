<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {onMounted, reactive, ref, useTemplateRef, watch} from "vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {fetchPost, fetchGet, getUrl} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import UpdateConfigurationName
	from "@/components/configurationComponents/editConfigurationComponents/updateConfigurationName.vue";
import CodeEditor from "@/utilities/simple-code-editor/CodeEditor.vue";
const props = defineProps({
	configurationInfo: Object
})

// Add these reactive refs for script contents
const scriptContents = reactive({
    PreUp: null,
    PostUp: null,
    PreDown: null,
    PostDown: null
})

const loadScriptContents = (type) => {

    fetchPost(`/api/getConfigTables${type}`, {
        configurationName: props.configurationInfo.Name
    }, (res) => {
        if (res.status) {
            scriptContents[type] = res.data
        } else {
            store.newMessage("Server", res.message || "Failed to load script", "warning")
            console.error(`Failed to load ${type} scripts:`, res.message)
        }
    })
}
const updateScript = (type, content) => {
    fetchPost(`/api/updateConfigTables${type}`, {
        configurationName: props.configurationInfo.Name,
        content: content
    }, (res) => {
        if (res.status) {
            store.newMessage("Server", `${type} script updated successfully`, "success")
            // Reload script contents
            loadScriptContents(type)
        } else {
            store.newMessage("Server", res.message || `Failed to update ${type} script`, "danger")
        }
    })
}

const editMode = reactive({})
const editedContent = reactive({})

// Code editor state
const codeEditor = reactive({
	show: false,
	scriptType: '',
	scriptPath: '',
	content: '',
	saving: false
})


const enableEditMode = (path, content) => {
    // Initialize edited content with current content when entering edit mode
    editedContent[path] = content
    editMode[path] = true
}

const saveScript = (type, path, content) => {
    fetchPost(`/api/updateConfigTables${type}`, {
        configurationName: props.configurationInfo.Name,
        content: content
    }, (res) => {
        if (res.status) {
            store.newMessage("Server", `${type} script updated successfully`, "success")
            // Reload script contents
            loadScriptContents(type)
            // Exit edit mode
            editMode[path] = false
            delete editedContent[path]
        } else {
            store.newMessage("Server", res.message || `Failed to update ${type} script`, "danger")
        }
    })
}

const cancelEdit = (path) => {
    editMode[path] = false
    delete editedContent[path]
}

// Code editor methods
const openCodeEditor = (scriptType, scriptPath, content) => {
    codeEditor.show = true
    codeEditor.scriptType = scriptType
    codeEditor.scriptPath = scriptPath
    codeEditor.content = content
    codeEditor.saving = false
}

const closeCodeEditor = () => {
    codeEditor.show = false
    codeEditor.scriptType = ''
    codeEditor.scriptPath = ''
    codeEditor.content = ''
    codeEditor.saving = false
}

const saveCodeEditorContent = () => {
    if (codeEditor.scriptType && codeEditor.scriptPath) {
        codeEditor.saving = true
        fetchPost(`/api/updateConfigTables${codeEditor.scriptType}`, {
            configurationName: props.configurationInfo.Name,
            content: codeEditor.content
        }, (res) => {
            codeEditor.saving = false
            if (res.status) {
                store.newMessage("Server", `${codeEditor.scriptType} script updated successfully`, "success")
                // Reload script contents
                loadScriptContents(codeEditor.scriptType)
                closeCodeEditor()
            } else {
                store.newMessage("Server", res.message || `Failed to update ${codeEditor.scriptType} script`, "danger")
            }
        })
    }
}

// Add click handler for script viewing
const viewScript = (type) => {
    if (!scriptContents[type]) {
        loadScriptContents(type)
    }
    // Toggle visibility of script content
    scriptContents[type] = scriptContents[type] ? null : {}
}

const wgStore = WireguardConfigurationsStore()
const store = DashboardConfigurationStore()
const saving = ref(false)
const data = reactive({
	...JSON.parse(JSON.stringify(props.configurationInfo)),
	// Initialize I1-I5 if not present
	I1: props.configurationInfo.I1 || "",
	I2: props.configurationInfo.I2 || "",
	I3: props.configurationInfo.I3 || "",
	I4: props.configurationInfo.I4 || "",
	I5: props.configurationInfo.I5 || ""
})
const editPrivateKey = ref(false)
const dataChanged = ref(false)
const confirmChanges = ref(false)
const reqField = reactive({
	PrivateKey: true,
	IPAddress: true,
	ListenPort: true
})
const editConfigurationContainer = useTemplateRef("editConfigurationContainer")
const genKey = () => {
	if (wgStore.checkWGKeyLength(data.PrivateKey)){
		reqField.PrivateKey = true;
		data.PublicKey = window.wireguard.generatePublicKey(data.PrivateKey)
	}else{
		reqField.PrivateKey = false;
	}
}
const validateCPSFormat = (value) => {
	if (!value || value === "") return true;
	
	// Pattern for individual tags
	const hexTag = /<b\s+0x[0-9a-fA-F]+>/g;
	const counterTag = /<c>/g;
	const timestampTag = /<t>/g;
	const randomTag = /<r\s+(\d+)>/g;
	const randomAsciiTag = /<rc\s+(\d+)>/g;  // Random ASCII characters (a-z, A-Z)
	const randomDigitTag = /<rd\s+(\d+)>/g;  // Random digits (0-9)
	
	// Check if the string only contains valid tags
	let testString = value;
	testString = testString.replace(hexTag, '');
	testString = testString.replace(counterTag, '');
	testString = testString.replace(timestampTag, '');
	testString = testString.replace(randomTag, '');
	testString = testString.replace(randomAsciiTag, '');
	testString = testString.replace(randomDigitTag, '');
	
	// If there's anything left, it's invalid
	if (testString.trim() !== '') return false;
	
	// Validate random length constraints for all variable-length tags
	const allLengthTags = [
		...value.matchAll(/<r\s+(\d+)>/g),
		...value.matchAll(/<rc\s+(\d+)>/g),
		...value.matchAll(/<rd\s+(\d+)>/g)
	];
	
	for (const match of allLengthTags) {
		const length = parseInt(match[1]);
		if (length <= 0 || length > 1000) return false;
	}
	
	return true;
}

const generateSingleCPS = async (key) => {
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
		} while (true); // Retry if biased
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
		// Use fetch directly for async/await
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
				console.debug(`[${protocol}] API response:`, {
					status: jsonData?.status,
					hasData: !!jsonData?.data,
					dataKeys: jsonData?.data ? Object.keys(jsonData.data) : [],
					hasPattern: !!jsonData?.data?.cps_pattern,
					patternLength: jsonData?.data?.cps_pattern?.length || 0,
					message: jsonData?.message
				});
				
				if (jsonData.status && jsonData.data && jsonData.data.cps_pattern) {
					libraryPattern = jsonData.data.cps_pattern;
					console.debug(`✓ Retrieved ${protocol} pattern from library (ID: ${jsonData.data.pattern_id || 'unknown'}, ${libraryPattern.length} chars)`);
				} else {
					console.debug(`✗ Library returned no pattern for ${protocol}:`, {
						status: jsonData?.status,
						hasData: !!jsonData?.data,
						hasPattern: !!jsonData?.data?.cps_pattern,
						message: jsonData?.message
					});
				}
			} else {
				const errorText = await res.text().catch(() => '');
				console.debug(`✗ Library fetch failed for ${protocol}: ${res.status}`, errorText);
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
	// If no library pattern available, return empty (user can enter manually)
	if (libraryPattern) {
		return randomizePattern(libraryPattern);
	}
	return "";
}

const resetForm = () => {
	dataChanged.value = false;
	Object.assign(data, {
		...JSON.parse(JSON.stringify(props.configurationInfo)),
		I1: props.configurationInfo.I1 || "",
		I2: props.configurationInfo.I2 || "",
		I3: props.configurationInfo.I3 || "",
		I4: props.configurationInfo.I4 || "",
		I5: props.configurationInfo.I5 || ""
	})
}
const emit = defineEmits(["changed", "close", "backupRestore", "deleteConfiguration", "editRaw"])
const saveForm = ()  => {
	saving.value = true
	fetchPost("/api/updateConfiguration", data, (res) => {
		saving.value = false
		if (res.status){
			store.newMessage("Server", "Configuration saved", "success")
			dataChanged.value = false
			emit("dataChanged", res.data)
			
		}else{
			store.newMessage("Server", res.message, "danger")
		}
	})
}
const updateConfigurationName = ref(false)

watch(data, () => {
	dataChanged.value = JSON.stringify(data) !== JSON.stringify(props.configurationInfo);
}, {
	deep: true
})
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll" ref="editConfigurationContainer">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 700px">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Configuration Settings"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="$emit('close')"></button>
					</div>
					<div class="card-body px-4 pb-4">
						<div class="d-flex gap-2 flex-column">
							<div class="d-flex align-items-center gap-3" v-if="!updateConfigurationName">
								<small class="text-muted">
									<LocaleText t="Name"></LocaleText>
								</small>
								<small>{{data.Name}}</small>
								<button 
									@click="updateConfigurationName = true"
									class="btn btn-sm bg-danger-subtle border-danger-subtle text-danger-emphasis rounded-3 ms-auto">
									Update Name
								</button>
							</div>
							<UpdateConfigurationName
								@close="updateConfigurationName = false"
								:configuration-name="data.Name"
								v-if="updateConfigurationName"></UpdateConfigurationName>
							
							<template v-else>
								<hr>
								<div class="d-flex align-items-center gap-3">
									<small class="text-muted" style="word-break: keep-all">
										<LocaleText t="Public Key"></LocaleText>
									</small>
									<small class="ms-auto"  style="word-break: break-all">
										{{data.PublicKey}}
									</small>
								</div>
								<hr>
								<div>
									<div class="d-flex">
										<label for="configuration_private_key" class="form-label">
											<small class="text-muted d-block">
												<LocaleText t="Private Key"></LocaleText>
											</small>
										</label>
										<div class="form-check form-switch ms-auto">
											<input class="form-check-input"
											       type="checkbox" role="switch" id="editPrivateKeySwitch"
											       v-model="editPrivateKey"
											>
											<label class="form-check-label" for="editPrivateKeySwitch">
												<small>Edit</small>
											</label>
										</div>
									</div>
									<input type="text" class="form-control form-control-sm rounded-3"
									       :disabled="saving || !editPrivateKey"
									       :class="{'is-invalid': !reqField.PrivateKey}"
									       @keyup="genKey()"
									       v-model="data.PrivateKey"
									       id="configuration_private_key">
								</div>
								<div>
									<label for="configuration_ipaddress_cidr" class="form-label">
										<small class="text-muted">
											<LocaleText t="IP Address/CIDR"></LocaleText>
										</small>
									</label>
									<input type="text" class="form-control form-control-sm rounded-3"
									       :disabled="saving"
									       v-model="data.Address"
									       id="configuration_ipaddress_cidr">
								</div>
								<div>
									<label for="configuration_listen_port" class="form-label">
										<small class="text-muted">
											<LocaleText t="Listen Port"></LocaleText>
										</small>
									</label>
									<input type="number" class="form-control form-control-sm rounded-3"
									       :disabled="saving"
									       v-model="data.ListenPort"
									       id="configuration_listen_port">

								</div>
								<div v-for="key in ['PreUp', 'PreDown', 'PostUp', 'PostDown']" :key="key">
									<label :for="'configuration_' + key" class="form-label">
									<small class="text-muted">
										<LocaleText :t="key"></LocaleText>
									</small>
									</label>
									<div class="d-flex gap-2 align-items-center">
									<input 
										type="text" 
										class="form-control form-control-sm rounded-3"
										:disabled="saving"
										v-model="data[key]"
										:id="'configuration_' + key"
									>
									<button
										:class="scriptContents[key] ? 'btn-warning' : 'bg-primary-subtle border-primary-subtle btn-outline-secondary'"
										class="btn btn-sm text-primary-subtle"
										@click="viewScript(key)"
										v-if="data[key]"
									>
										<i class="bi" :class="scriptContents[key] ? 'bi-x-lg' : 'bi-file-text'"></i>
									</button>
									</div>
									<!-- Script content viewer/editor -->
									<div v-if="scriptContents[key]" class="mt-2 border rounded p-2">
									<div v-for="(content, path) in scriptContents[key].contents" :key="path">
										<div class="d-flex justify-content-between align-items-center">
										<small class="text-muted">{{ path }}</small>
										<div class="btn-group">
											<button
											v-if="!editMode[path]"
											class="bg-primary-subtle border-primary-subtle btn btn-sm btn-outline-secondary text-primary-subtle"
											@click="openCodeEditor(key, path, content)"
											>
											<i class="bi bi-pencil"></i>
											</button>
											<button
											v-else
											class="btn btn-sm btn-outline-primary"
											@click="saveScript(key, path, editedContent[path])"
											>
											<i class="bi bi-save"></i>
											</button>
											<button
											v-if="editMode[path]"
											class="btn btn-sm btn-outline-secondary"
											@click="cancelEdit(path)"
											>
											<i class="bi bi-x-lg"></i>
											</button>
										</div>
										</div>
										<div class="script-box mt-1">
										<textarea
											v-if="editMode[path]"
											class="script-box-active form-control form-control-sm font-monospace resizable-textarea"
											v-model="editedContent[path]"
											rows="10"
										></textarea>
										<pre v-else class="mb-0 resizable-preview"><code>{{ content }}</code></pre>
										</div>
									</div>
									</div>
								</div>

								<!-- AmneziaWG 1.5 CPS Packets Section -->
								<div v-if="data.Protocol === 'awg' || data.Jc || data.H1" class="mt-4">
									<h6 class="mb-3">
										<LocaleText t="AmneziaWG 1.5 CPS Packets (Optional)"></LocaleText>
									</h6>
									<div class="alert alert-info py-2 px-3">
										<small>
											<i class="bi bi-info-circle me-2"></i>
											<LocaleText t="Add CPS support to upgrade to AmneziaWG 1.5. Leave empty to use AmneziaWG 1.0."></LocaleText>
										</small>
									</div>
									
									<div v-for="key in ['I1', 'I2', 'I3', 'I4', 'I5']" :key="key" class="mb-3">
										<label :for="'edit_' + key" class="form-label">
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
												:class="{'is-invalid': data[key] && !validateCPSFormat(data[key])}"
												:disabled="saving"
												v-model="data[key]"
												:id="'edit_' + key"
												:placeholder="key === 'I1' ? '<b 0xLARGE_HEX_BLOB>' : ''"
											>
											<button
												v-if="!data[key]"
												class="btn btn-sm bg-primary-subtle border-primary-subtle text-primary-emphasis"
												@click="async () => { data[key] = await generateSingleCPS(key); dataChanged = true; }"
												type="button"
												:disabled="saving"
											>
												<i class="bi bi-magic"></i> Auto
											</button>
										</div>
										<div class="invalid-feedback" v-if="data[key] && !validateCPSFormat(data[key])">
											<LocaleText t="Invalid CPS format"></LocaleText>
										</div>
									</div>
								</div>

								<div class="d-flex align-items-center gap-2 mt-4">
									<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto"
									        @click="resetForm()"
									        :disabled="!dataChanged || saving">
										<i class="bi bi-arrow-clockwise me-2"></i>
										<LocaleText t="Reset"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 shadow"
									        :disabled="!dataChanged || saving"
									        @click="saveForm()"
									>
										<i class="bi bi-save-fill me-2"></i>
										<LocaleText t="Save"></LocaleText>
									</button>
								</div>
								<hr>
								<h5 class="mb-3">Danger Zone</h5>
								<div class="d-flex gap-2 flex-column">
									<button
										@click="emit('backupRestore')"
										class="btn bg-warning-subtle border-warning-subtle text-warning-emphasis rounded-3 text-start d-flex">
										<i class="bi bi-copy me-auto"></i>
										<LocaleText t="Backup & Restore"></LocaleText>
									</button>
									<button
										@click="emit('editRaw')"
										class="btn bg-warning-subtle border-warning-subtle text-warning-emphasis rounded-3 d-flex">
										<i class="bi bi-pen me-auto"></i>
										<LocaleText t="Edit Raw Configuration File"></LocaleText>
									</button>
									
									<button
										@click="emit('deleteConfiguration')"
										class="btn bg-danger-subtle border-danger-subtle text-danger-emphasis rounded-3 d-flex mt-4">
										<i class="bi bi-trash-fill me-auto"></i>
										<LocaleText t="Delete Configuration"></LocaleText>
									</button>
								</div>
								
							</template>
						</div>
					</div>
				</div>
			</div>
		</div>
		
		<!-- Code Editor Modal -->
		<div v-if="codeEditor.show" class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
			<div class="container d-flex h-100 w-100">
				<div class="m-auto modal-dialog-centered dashboardModal" style="width: 1000px">
					<div class="card rounded-3 shadow flex-grow-1">
						<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
							<h5 class="mb-0">
								<LocaleText t="Edit Script"></LocaleText> - {{ codeEditor.scriptPath }}
							</h5>
							<button type="button" class="btn-close ms-auto" @click="closeCodeEditor"></button>
						</div>
						<div class="card-body px-4 d-flex flex-column gap-3">
							<CodeEditor
								:readOnly="codeEditor.saving"
								v-model="codeEditor.content"
								:theme="store.Configuration.Server.dashboard_theme === 'dark' ? 'github-dark' : 'github'"
								:languages="[['bash', codeEditor.scriptPath]]"
								width="100%" 
								height="600px"
							/>
							<div class="d-flex gap-2">
								<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto px-3 py-2"
								        :disabled="codeEditor.saving"
								        @click="closeCodeEditor">
									<LocaleText t="Cancel"></LocaleText>
								</button>
								<button 
									@click="saveCodeEditorContent"
									:disabled="codeEditor.saving"
									class="btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 px-3 py-2 shadow"
								>
									<i class="bi bi-save-fill me-2"></i>
									<LocaleText t="Save" v-if="!codeEditor.saving"></LocaleText>
									<LocaleText t="Saving..." v-else></LocaleText>
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.script-box {
  position: relative;
  min-height: 100px;
}

.resizable-textarea {
  resize: vertical;
  overflow: scroll;
  min-height: 500px;
  max-height: 1000px;
  width: 100%;
}

.resizable-preview {
  resize: vertical;
  overflow: scroll;
  min-height: 150px;
  max-height: 200px;
  width: 100%;
  background-color: #212529;
  padding: 0.5rem;
  border: 1px solid #dee2e646;
  border-radius: 0.25rem;
}

/* Ensures the resize handle is visible */
.resizable-textarea::-webkit-resizer,
.resizable-preview::-webkit-resizer {
  border-width: 8px;
  border-style: solid;
  border-color: transparent #6c757d #6c757d transparent;
}

/* Scrollbar styling for better visibility */
.resizable-textarea::-webkit-scrollbar,
.resizable-preview::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.resizable-textarea::-webkit-scrollbar-track,
.resizable-preview::-webkit-scrollbar-track {
  background: #5c5c5c;
}

.resizable-textarea::-webkit-scrollbar-thumb,
.resizable-preview::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.resizable-textarea::-webkit-scrollbar-thumb:hover,
.resizable-preview::-webkit-scrollbar-thumb:hover {
  background: #555;
}

</style>