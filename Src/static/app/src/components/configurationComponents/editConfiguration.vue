<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {onMounted, reactive, ref, useTemplateRef, watch} from "vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {fetchPost, fetchGet} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import UpdateConfigurationName
	from "@/components/configurationComponents/editConfigurationComponents/updateConfigurationName.vue";
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
const data = reactive(JSON.parse(JSON.stringify(props.configurationInfo)))
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
const resetForm = () => {
	dataChanged.value = false;
	Object.assign(data, JSON.parse(JSON.stringify(props.configurationInfo)))
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
											@click="enableEditMode(path, content)"
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