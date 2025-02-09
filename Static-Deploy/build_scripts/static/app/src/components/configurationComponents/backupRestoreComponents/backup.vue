<script setup>
import dayjs from "dayjs";
import {computed, ref} from "vue";
import {fetchPost} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps(["b", "delay"])
const deleteConfirmation = ref(false)
const restoreConfirmation = ref(false)
const route = useRoute()
const emit = defineEmits(["refresh", "refreshPeersList"])
const store = DashboardConfigurationStore()
const loading = ref(false);
const fileInput = ref(null);

const deleteBackup = () => {
    loading.value = true;
    fetchPost("/api/deleteConfigurationBackup", {
        configurationName: route.params.id,
        backupFileName: props.b.filename
    }, (res) => {
        loading.value = false;
        if (res.status){
            emit("refresh")
            store.newMessage("Server", "Backup deleted", "success")
        }else{
            store.newMessage("Server", "Backup failed to delete", "danger")
        }
    })
}

const restoreBackup = () => {
    loading.value = true;
    fetchPost("/api/restoreConfigurationBackup", {
        configurationName: route.params.id,
        backupFileName: props.b.filename
    }, (res) => {
        loading.value = false;
        restoreConfirmation.value = false;
        if (res.status){
            emit("refresh")
            store.newMessage("Server", "Backup restored with " + props.b.filename, "success")
        }else{
            store.newMessage("Server", "Backup failed to restore", "danger")
        }
    })
}

const downloadBackup = async () => {
  try {
    const response = await fetch(
      `/api/downloadConfigurationBackup?configurationName=${route.params.id}&backupFileName=${props.b.filename}`
    );

    if (!response.ok) {
      throw new Error('Download failed');
    }

    // Parse the response as a Blob for the zip file
    const blob = await response.blob();

    // Generate a download URL for the file
    const url = window.URL.createObjectURL(blob);

    // Create a hidden link element to trigger the download
    const a = document.createElement('a');
    a.href = url;
    a.download = props.b.filename.replace('.conf', '_complete.7z'); // Set the file name for download
    document.body.appendChild(a);
    a.click(); // Trigger the download
    window.URL.revokeObjectURL(url); // Clean up the URL
    document.body.removeChild(a); // Remove the link element
  } catch (error) {
    console.error(error); // Log detailed error
    store.newMessage("Server", "Failed to download backup", "danger"); // Notify user about the failure
  }
};



const delaySeconds = computed(() => {
    return props.delay + 's'
})

const showContent = ref(false);
</script>
 
<template>
    <div class="card my-0 rounded-3">
        <div class="card-body position-relative">
            <Transition name="zoomReversed">
                <div 
                    v-if="deleteConfirmation"
                    class="position-absolute w-100 h-100 confirmationContainer start-0 top-0 rounded-3 d-flex p-2">
                    <div class="m-auto">
                        <h5>
                            <LocaleText t="Are you sure to delete this backup?"></LocaleText>
                        </h5>
                        <div class="d-flex gap-2 align-items-center justify-content-center">
                            <button class="btn btn-danger rounded-3" 
                                    :disabled="loading"
                                    @click='deleteBackup()'>
                                <LocaleText t="Yes"></LocaleText>
                            </button>
                            <button
                                @click="deleteConfirmation = false"
                                :disabled="loading"
                                class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
                                <LocaleText t="No"></LocaleText>
                            </button>
                        </div>
                    </div>
                </div>
            </Transition>
            <Transition name="zoomReversed">
                <div
                    v-if="restoreConfirmation"
                    class="position-absolute w-100 h-100 confirmationContainer start-0 top-0 rounded-3 d-flex p-2">
                    <div class="m-auto">
                        <h5>
                            <LocaleText t="Are you sure to restore this backup?"></LocaleText>
                        </h5>
                        <div class="d-flex gap-2 align-items-center justify-content-center">
                            <button
                                :disabled="loading"
                                @click="restoreBackup()"
                                class="btn btn-success rounded-3">
                                <LocaleText t="Yes"></LocaleText>
                            </button>
                            <button
                                @click="restoreConfirmation = false"
                                :disabled="loading"
                                class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
                                <LocaleText t="No"></LocaleText>
                            </button>
                        </div>
                    </div>
                </div>
            </Transition>
            <div class="d-flex gap-3">
                <div class="d-flex flex-column">
                    <small class="text-muted">
                        <LocaleText t="Backup"></LocaleText>
                    </small>
                    <samp>{{b.filename}}</samp>
                </div>
                <div class="d-flex flex-column">
                    <small class="text-muted">
                        <LocaleText t="Backup Date"></LocaleText>
                    </small>
                    {{dayjs(b.backupDate, "YYYYMMDDHHmmss").format("YYYY-MM-DD HH:mm:ss")}}
                </div>
                <div class="d-flex gap-2 align-items-center ms-auto">
                    <!-- Download button -->
                    <button 
                        @click="downloadBackup"
                        class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 btn-sm">
                        <i class="bi bi-download"></i>
                    </button>
                    <!-- Restore button -->
                    <button 
                        @click="restoreConfirmation = true"
                        class="btn bg-warning-subtle text-warning-emphasis border-warning-subtle rounded-3 btn-sm">
                        <i class="bi bi-clock-history"></i>
                    </button>
                    <!-- Delete button -->
                    <button 
                        @click="deleteConfirmation = true"
                        class="btn bg-danger-subtle text-danger-emphasis border-danger-subtle rounded-3 btn-sm">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                </div>
            </div>
            <hr>
            <div class="card rounded-3">
                <div class="card-header d-flex align-items-center justify-content-between">
                    <a role="button" class="text-decoration-none d-flex align-items-center flex-grow-1" 
                       :class="{'border-bottom-0': !showContent}"
                       style="cursor: pointer" @click="showContent = !showContent">
                        <small>.conf <LocaleText t="File"></LocaleText></small>
                        <i class="bi bi-chevron-down ms-auto"></i>
                    </a>
                </div>
                <div class="card-body" v-if="showContent">
                    <textarea class="form-control rounded-3" :value="b.content"
                              disabled
                              style="height: 300px; font-family: var(--bs-font-monospace),sans-serif !important;"></textarea>
                </div>
            </div>
            <hr>
            <div class="d-flex">
                <span>
                    <i class="bi bi-database me-1"></i>
                    <LocaleText t="Database File"></LocaleText>
                </span>
                <i class="bi ms-auto"
                    :class="[b.database ? 'text-success bi-check-circle-fill' : 'text-danger bi-x-circle-fill']"
                ></i>
            </div>
        </div>
    </div>
</template>

<style scoped>
.confirmationContainer{
    background-color: rgba(0, 0, 0, 0.53);
    z-index: 9999;
    backdrop-filter: blur(1px);
    -webkit-backdrop-filter: blur(1px);
}

.list1-enter-active{
    transition-delay: v-bind(delaySeconds) !important;
}
</style>