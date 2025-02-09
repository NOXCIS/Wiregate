<script setup>
import {onMounted, ref} from "vue";
import dayjs from "dayjs";
import LocaleText from "@/components/text/localeText.vue";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const props = defineProps({
	configurationName: String,
	backups: Array,
	open: false,
	selectedConfigurationBackup: Object,
	isExisting: Boolean
})

const emit = defineEmits(["select", "refresh", "delete"])
const showBackups = ref(props.open)
const deleteConfirmation = ref(false)
const selectedBackup = ref(null)
const loading = ref(false)
const store = DashboardConfigurationStore()

onMounted(() => {
	if (props.selectedConfigurationBackup) {
		document.querySelector(`#${props.selectedConfigurationBackup.filename.replace('.conf', '')}`).scrollIntoView({
			behavior: "smooth"
		})
	}
})

const deleteBackup = () => {
	loading.value = true;
	emit('delete', selectedBackup.value);
	deleteConfirmation.value = false;
	loading.value = false;
}
</script>

<template>
	<div class="card rounded-3 shadow-sm">
		<a role="button" class="card-body d-flex align-items-center text-decoration-none" @click="showBackups = !showBackups">
			<div class="d-flex gap-3 align-items-center">
				<h6 class="mb-0">
					<samp>
						{{configurationName}}
					</samp>
				</h6>
				<small class="text-muted">
					<LocaleText :t="backups.length + (backups.length > 1 ? ' Backups':' Backup')"></LocaleText>
				</small>
			</div>
			<h5 class="ms-auto mb-0 dropdownIcon text-muted" :class="{active: showBackups}">
				<i class="bi bi-chevron-down"></i>
			</h5>
		</a>
		<div class="card-footer p-3 d-flex flex-column gap-2" v-if="showBackups">
			<!-- Delete Confirmation Modal -->
			<Transition name="zoomReversed">
				<div v-if="deleteConfirmation && selectedBackup"
					 class="position-fixed w-100 h-100 top-0 start-0 d-flex confirmationContainer"
					 style="z-index: 1050;">
					<div class="card m-auto rounded-3 shadow">
						<div class="card-body">
							<h5>
								<LocaleText t="Are you sure to delete this backup?"></LocaleText>
							</h5>
							<div class="d-flex gap-2 align-items-center justify-content-center">
								<button class="btn btn-danger rounded-3"
										:disabled="loading"
										@click="deleteBackup()">
									<LocaleText t="Yes"></LocaleText>
								</button>
								<button @click="deleteConfirmation = false"
										:disabled="loading"
										class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
									<LocaleText t="No"></LocaleText>
								</button>
							</div>
						</div>
					</div>
				</div>
			</Transition>

			<div class="card rounded-3 shadow-sm animate__animated"
				 :key="b.filename"
				 :id="b.filename.replace('.conf', '')"
				 role="button" v-for="b in backups">
				<div class="card-body d-flex p-3 gap-3 align-items-center">
					<div class="d-flex gap-3 align-items-center flex-grow-1" 
						 @click="!isExisting && emit('select', b)"
						 :class="{'cursor-not-allowed': isExisting}">
						<small>
							<i class="bi bi-file-earmark me-2"></i>
							<samp>{{b.filename}}</samp>
						</small>
						<small>
							<i class="bi bi-clock-history me-2"></i>
							<samp>{{dayjs(b.backupDate).format("YYYY-MM-DD HH:mm:ss")}}</samp>
						</small>
						<small>
							<i class="bi bi-database me-2"></i>
							<LocaleText t="Yes" v-if="b.database"></LocaleText>
							<LocaleText t="No" v-else></LocaleText>
						</small>
					</div>
					<div class="d-flex gap-2">
						<button @click="() => {
							selectedBackup = b;
							deleteConfirmation = true;
						}"
								class="btn bg-danger-subtle text-danger-emphasis border-danger-subtle rounded-3 btn-sm">
							<i class="bi bi-trash-fill"></i>
						</button>
						<small class="text-muted" v-if="!isExisting" @click="() => {emit('select', b)}">
							<i class="bi bi-chevron-right"></i>
						</small>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
	.dropdownIcon{
		transition: all 0.2s ease-in-out;
	}
	.dropdownIcon.active{
		transform: rotate(180deg);
	}
	.confirmationContainer {
		background-color: rgba(0, 0, 0, 0.53);
		backdrop-filter: blur(1px);
		-webkit-backdrop-filter: blur(1px);
	}
	.cursor-not-allowed {
		cursor: not-allowed;
		opacity: 0.7;
	}
</style>