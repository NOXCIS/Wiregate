<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {onMounted, ref} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import BackupGroup from "@/components/restoreConfigurationComponents/backupGroup.vue";
import ConfirmBackup from "@/components/restoreConfigurationComponents/confirmBackup.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const backups = ref({
    ExistingConfigurations: {},
    NonExistingConfigurations: {}
});
const selectedFile = ref(null);
const isUploading = ref(false);
const dashboardStore = DashboardConfigurationStore();
const confirm = ref(false);
const selectedConfigurationBackup = ref(undefined);
const selectedConfiguration = ref("");
const isDragging = ref(false);

onMounted(() => {
    fetchGet("/api/getAllConfigurationBackup", {}, (res) => {
        if (res.status) {
            backups.value = res.data;
        } else {
            dashboardStore.newMessage(
                "WireGate",
                res.message || "Failed to load backups",
                "danger"
            );
        }
    });
});



const handleFileSelect = (event) => {
    selectedFile.value = event.target.files[0];
};

const handleUpload = async () => {
    if (!selectedFile.value) {
        dashboardStore.newMessage(
            "WireGate",
            "Please select a file to upload",
            "warning"
        );
        return;
    }
    
    isUploading.value = true;
    try {
        const formData = new FormData();
        formData.append('files', selectedFile.value);

        const response = await fetch('/api/uploadConfigurationBackup', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();
        
        if (result.status) {
            // Clear file selection
            selectedFile.value = null;
            const fileInput = document.querySelector('input[type="file"]');
            if (fileInput) fileInput.value = '';

            // Show success message
            dashboardStore.newMessage(
                "WireGate",
                result.message || "Files uploaded successfully",
                "success"
            );

            // Immediately refresh backups list
            try {
                const backupResponse = await fetch("/api/getAllConfigurationBackup");
                const backupResult = await backupResponse.json();
                
                if (backupResult.status) {
                    backups.value = backupResult.data;
                } else {
                    throw new Error(backupResult.message || "Failed to refresh backup list");
                }
            } catch (refreshError) {
                dashboardStore.newMessage(
                    "WireGate",
                    "Upload successful, but failed to refresh backup list. Please reload the page.",
                    "warning"
                );
            }
        } else {
            throw new Error(result.message || "Upload failed");
        }
    } catch (error) {
        dashboardStore.newMessage(
            "WireGate",
            error.message || "Upload failed",
            "danger"
        );
    } finally {
        isUploading.value = false;
    }
};

const refreshBackups = async () => {
    try {
        console.log('Refreshing backups...');
        const backupResponse = await fetch("/api/getAllConfigurationBackup");
        const backupResult = await backupResponse.json();
        console.log('Backup response:', backupResult);
        
        if (backupResult.status) {
            console.log('Setting backups data:', backupResult.data);
            backups.value = backupResult.data;
        } else {
            console.error('Failed to refresh backups:', backupResult.message);
            throw new Error(backupResult.message || "Failed to refresh backup list");
        }
    } catch (refreshError) {
        console.error('Error refreshing backups:', refreshError);
        dashboardStore.newMessage(
            "WireGate",
            refreshError.message || "Failed to refresh backup list",
            "danger"
        );
    }
};

const deleteBackup = (configurationName, backup) => {
    console.log('Deleting backup:', {
        configurationName: configurationName,
        backupFileName: backup.filename
    });
    
    fetchPost("/api/deleteConfigurationBackup", {
        configurationName: configurationName,
        backupFileName: backup.filename
    }, (res) => {
        console.log('Delete backup response:', res);
        if (res.status) {
            console.log('Refreshing backups after delete');
            refreshBackups();
            dashboardStore.newMessage("Server", "Backup deleted", "success")
        } else {
            console.error('Failed to delete backup:', res);
            dashboardStore.newMessage("Server", "Backup failed to delete", "danger")
        }
    })
}

const handleDragEnter = (e) => {
    e.preventDefault();
    isDragging.value = true;
};

const handleDragLeave = (e) => {
    e.preventDefault();
    isDragging.value = false;
};

const handleDragOver = (e) => {
    e.preventDefault();
    isDragging.value = true;
};

const handleDrop = (e) => {
    e.preventDefault();
    isDragging.value = false;
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        selectedFile.value = files[0];
    }
};
</script>

<template>
    <div class="mt-md-5 mt-3 text-body">
        <div class="container mb-4">
            <!-- Header section -->
            <div class="mb-5 d-flex align-items-center gap-4">
                <RouterLink to="/"
                           class="btn btn-dark btn-brand p-2 shadow" style="border-radius: 100%">
                    <h2 class="mb-0" style="line-height: 0">
                        <i class="bi bi-arrow-left-circle"></i>
                    </h2>
                </RouterLink>
                <h2 class="mb-0">
                    <LocaleText t="Restore Configuration"></LocaleText>
                </h2>
            </div>
            
            <!-- File Upload Section -->
            <div class="mb-4">
                <h4><LocaleText t="Upload Backup"></LocaleText></h4>
                <div 
                    class="card rounded-3" 
                    @dragover="handleDragOver"
                    @drop="handleDrop"
                    @dragenter="handleDragEnter"
                    @dragleave="handleDragLeave"
                >
                    <div class="card-body">
                        <div 
                            class="upload-zone p-4 border-2 border-dashed rounded-3"
                            :class="{ 'border-primary': isDragging }"
                        >
                            <div class="text-center mb-3">
                                <i class="bi bi-cloud-upload fs-1"></i>
                                <p class="mb-0">
                                    <LocaleText t="Drag and drop your backup file here"></LocaleText>
                                </p>
                                <p class="text-muted">
                                    <small><LocaleText t="or"></LocaleText></small>
                                </p>
                            </div>

                            <div class="row align-items-end">
                                <div class="col">
                                    <div class="mb-0">
                                        <label class="form-label">
                                            <LocaleText t="Select backup file"></LocaleText>
                                        </label>
                                        <div class="input-group">
                                            <input 
                                                type="file" 
                                                class="form-control" 
                                                @change="handleFileSelect"
                                                accept=".7z"
                                            >
                                            <div v-if="selectedFile" 
                                                 class="input-group-text text-truncate" 
                                                 style="max-width: 200px;" 
                                                 :title="selectedFile.name">
                                                {{ selectedFile.name }}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-auto">
                                    <button 
                                        class="ms-md-auto py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle" 
                                        @click="handleUpload"
                                        :disabled="!selectedFile || isUploading"
                                    >
                                        <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
                                        <i v-else class="bi bi-cloud-upload me-2"></i>
                                        <LocaleText t="Upload"></LocaleText>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <Transition name="fade" appear>
                <div v-if="backups">
                    <!-- Step 1 Section -->
                    <div class="d-flex mb-5 align-items-center steps" role="button"
                         :class="{active: !confirm}"
                         @click="confirm = false" key="step1">
                        <div class="d-flex text-decoration-none text-body flex-grow-1 align-items-center gap-3">
                            <h1 class="mb-0" style="line-height: 0">
                                <i class="bi bi-1-circle-fill"></i>
                            </h1>
                            <div>
                                <h4 class="mb-0">
                                    <LocaleText t="Step 1"></LocaleText>
                                </h4>
                                <small class="text-muted">
                                    <LocaleText t="Select a backup you want to restore" v-if="!confirm"></LocaleText>
                                    <LocaleText t="Click to change a backup" v-else></LocaleText>
                                </small>
                            </div>
                        </div>
                        <Transition name="zoomReversed">
                            <div class="ms-sm-auto" v-if="confirm">
                                <small class="text-muted">
                                    <LocaleText t="Selected Backup"></LocaleText>
                                </small>
                                <h6>
                                    <samp>{{selectedConfigurationBackup?.filename}}</samp>
                                </h6>
                            </div>
                        </Transition>
                    </div>

                    <div id="step1Detail" v-if="!confirm">
                        <!-- Existing Configurations -->
                        <div class="mb-4" v-if="Object.keys(backups.ExistingConfigurations).length > 0">
                            <h5 class="mb-3 d-flex align-items-center gap-2">
                                <i class="bi bi-check-circle-fill text-success"></i>
                                <LocaleText t="Existing Configurations"></LocaleText>
                            </h5>
                            <div class="d-flex gap-3 flex-column">
                                <BackupGroup
                                    v-for="(backupsList, configName) in backups.ExistingConfigurations"
                                    :key="configName"
                                    @delete="(b) => deleteBackup(configName, b)"
                                    :selectedConfigurationBackup="selectedConfigurationBackup"
                                    :open="selectedConfiguration === configName"
                                    :configuration-name="configName"
                                    :backups="backupsList"
                                    :isExisting="true"
                                />
                            </div>
                        </div>

                        <!-- Non-Existing Configurations -->
                        <div class="mb-4">
                            <h5 class="mb-3 d-flex align-items-center gap-2">
                                <i class="bi bi-dash-circle-fill text-secondary"></i>
                                <LocaleText t="Non-Existing Configurations"></LocaleText>
                            </h5>
                            <div class="d-flex gap-3 flex-column">
                                <BackupGroup
                                    v-for="(backupsList, configName) in backups.NonExistingConfigurations"
                                    :key="configName"
                                    @select="(b) => {
                                        selectedConfigurationBackup = b;
                                        selectedConfiguration = configName;
                                        confirm = true;
                                    }"
                                    @delete="(b) => deleteBackup(configName, b)"
                                    :selectedConfigurationBackup="selectedConfigurationBackup"
                                    :open="selectedConfiguration === configName"
                                    :configuration-name="configName"
                                    :backups="backupsList"
                                    :isExisting="false"
                                />
                                <div v-if="Object.keys(backups.NonExistingConfigurations).length === 0"
                                     class="card rounded-3">
                                    <div class="card-body">
                                        <p class="mb-0 text-muted">
                                            <LocaleText t="No non-existing configuration backups available"></LocaleText>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 2 Section -->
                    <div class="my-5" key="step2" id="step2">
                        <div class="steps d-flex text-decoration-none text-body flex-grow-1 align-items-center gap-3"
                             :class="{active: confirm}">
                            <h1 class="mb-0" style="line-height: 0">
                                <i class="bi bi-2-circle-fill"></i>
                            </h1>
                            <div>
                                <h4 class="mb-0">Step 2</h4>
                                <small class="text-muted">
                                    <LocaleText t="Backup not selected" v-if="!confirm"></LocaleText>
                                    <LocaleText t="Confirm & edit restore information" v-else></LocaleText>
                                </small>
                            </div>
                        </div>
                    </div>

                    <ConfirmBackup 
                        :selectedConfigurationBackup="selectedConfigurationBackup" 
                        v-if="confirm" 
                        @cancel="confirm = false"
                        key="confirm">
                    </ConfirmBackup>
                </div>
            </Transition>
        </div>
    </div>
</template>

<style scoped>
.steps {
    transition: all 0.3s ease-in-out;
    opacity: 0.3;
    
    &.active {
        opacity: 1;
    }
}
</style>