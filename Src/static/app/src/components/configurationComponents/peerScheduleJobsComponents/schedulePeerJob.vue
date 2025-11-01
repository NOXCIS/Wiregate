<script>
import ScheduleDropdown from "@/components/configurationComponents/peerScheduleJobsComponents/scheduleDropdown.vue";
import {ref, computed, defineAsyncComponent} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import VueDatePicker from "@vuepic/vue-datepicker";
import dayjs from "dayjs";
import LocaleText from "@/components/text/localeText.vue";
import WeeklySchedule from "@/components/configurationComponents/peerScheduleJobsComponents/weeklySchedule.vue";
import DataUsageSchedule from "@/components/configurationComponents/peerScheduleJobsComponents/dataUsageSchedule.vue";

const PeerRateLimitSettings = defineAsyncComponent(() => import('@/components/configurationComponents/peerRateLimitSettings.vue'))

export default {
	name: "schedulePeerJob",
	components: {LocaleText, VueDatePicker, ScheduleDropdown, WeeklySchedule, PeerRateLimitSettings, DataUsageSchedule},
	props: {
		dropdowns: Array[Object],
		pjob: Object,
		viewOnly: false
	},
	setup(props){
		const job = ref({})
		const edit = ref(false)
		const newJob = ref(false)
		job.value = JSON.parse(JSON.stringify(props.pjob))
		if (!job.value.CreationDate){
			edit.value = true
			newJob.value = true
		}
		const store = DashboardConfigurationStore()
		return {job, edit, newJob, store}
	},
	data(){
		return {
			inputType: undefined,
			selectedDays: [],
			timeIntervals: {},
			thresholdValue: 0
		}
	},
	watch:{
		pjob: {
			deep: true,
			immediate: true,
			handler(newValue){
				if (!this.edit){
					this.job = JSON.parse(JSON.stringify(newValue))
					// Parse the existing job value to populate thresholdValue for data fields
					this.parseExistingJobValue()
				}
			}
		},
		'job.Value': {
			immediate: true,
			handler(newValue) {
				if (this.isDataField) {
					try {
						const value = JSON.parse(newValue)
						if (value.threshold) {
							this.thresholdValue = value.threshold
						}
					} catch (e) {
						this.thresholdValue = parseFloat(newValue) || 0
					}
				}
			}
		},
		thresholdValue(newValue) {
			console.log('thresholdValue changed to:', newValue, 'isDataField:', this.isDataField);
			if (this.isDataField) {
				if (this.job.Action === 'rate_limit') {
					// Preserve rate limits when updating threshold
					try {
						const currentValue = JSON.parse(this.job.Value || '{}')
						this.job.Value = JSON.stringify({
							...currentValue,
							threshold: Number(newValue)
						})
					} catch (e) {
						this.job.Value = JSON.stringify({
							threshold: Number(newValue)
						})
					}
				} else {
					this.job.Value = String(newValue)
				}
				console.log('Updated job.Value to:', this.job.Value);
			}
		}
	},
	methods: {
		save(){
			// Comprehensive validation
			if (!this.job.Field || !this.job.Action || !this.job.Value) {
				this.alert();
				return;
			}

			// Validate operator for non-weekly fields
			if (this.job.Field !== 'weekly' && !this.job.Operator) {
				this.alert();
				return;
			}

			// Validate weekly schedule format
			if (this.job.Field === 'weekly' && !this.job.Value) {
				this.alert();
				return;
			}

			// Validate data fields have numeric values
			if (this.isDataField() && this.job.Field !== 'weekly') {
				try {
					const value = JSON.parse(this.job.Value);
					if (this.job.Action === 'rate_limit') {
						if (typeof value.threshold !== 'number' || value.threshold < 0) {
							this.alert();
							return;
						}
					} else {
						const numValue = parseFloat(this.job.Value);
						if (isNaN(numValue) || numValue < 0) {
							this.alert();
							return;
						}
					}
				} catch (e) {
					const numValue = parseFloat(this.job.Value);
					if (isNaN(numValue) || numValue < 0) {
						this.alert();
						return;
					}
				}
			}

			// Validate date format for date fields
			if (this.job.Field === 'date') {
				const dateRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
				if (!dateRegex.test(this.job.Value)) {
					this.alert();
					return;
				}
			}

			if (!this.job.Peer && this.pjob?.Peer) {
				this.job.Peer = this.pjob.Peer;
			}

			fetchPost(`/api/savePeerScheduleJob/`, {
				Job: this.job
			}, (res) => {
				if (res.status){
					this.edit = false;
					this.store.newMessage("Server", "Peer job saved", "success")
					this.$emit("refresh", res.data[0])
					this.newJob = false;
				} else {
					this.store.newMessage("Server", res.message, "danger")
				}
			})
		},
		alert(){
			let animation = "animate__flash";
			let dropdowns = this.$el.querySelectorAll(".scheduleDropdown");
			let inputs = this.$el.querySelectorAll("input");
			dropdowns.forEach(x => x.classList.add("animate__animated", animation))
			inputs.forEach(x => x.classList.add("animate__animated", animation))
			setTimeout(() => {
				dropdowns.forEach(x => x.classList.remove("animate__animated", animation))
				inputs.forEach(x => x.classList.remove("animate__animated", animation))
			}, 2000)
		},
		reset(){
			if(this.job.CreationDate){
				this.job = JSON.parse(JSON.stringify(this.pjob));
				this.edit = false;
			}else{
				this.$emit('delete')
			}
		},
		delete(){
			if(this.job.CreationDate){
				fetchPost(`/api/deletePeerScheduleJob/`, {
					Job: this.job
				}, (res) => {
					if (!res.status){
						this.store.newMessage("Server", res.message, "danger")
						this.$emit('delete')
					}else{
						this.store.newMessage("Server", "Peer job deleted", "success")
					}
					
				})
			}
			this.$emit('delete')
		},
		parseTime(modelData){
			if(modelData){
				this.job.Value = dayjs(modelData).format("YYYY-MM-DD HH:mm:ss");
			}
		},
		handleWeeklySelection(value) {
			this.job.Value = value;
		},
		toggleDay(day) {
			const index = this.selectedDays.indexOf(day);
			if (index === -1) {
				this.selectedDays.push(day);
				this.timeIntervals[day] = { start: '00:00', end: '23:59' };
			} else {
				this.selectedDays.splice(index, 1);
				delete this.timeIntervals[day];
			}
			this.updateJobValue();
		},
		updateTimeInterval({ day, type, value }) {
			if (this.timeIntervals[day]) {
				this.timeIntervals[day][type] = value;
				this.updateJobValue();
			}
		},
		updateJobValue() {
			const formattedValue = this.selectedDays
				.map(day => {
					const interval = this.timeIntervals[day];
					const start = interval.start.padStart(5, '0');
					const end = interval.end.padStart(5, '0');
					return `${day}:${start}-${end}`;
				})
				.join(',');
			this.job.Value = formattedValue;
		},
		parseExistingJobValue() {
			console.log('=== parseExistingJobValue called ===');
			console.log('Job object:', this.job);
			console.log('Job Value:', this.job.Value);
			console.log('Job Field:', this.job.Field);
			console.log('isDataField result:', this.isDataField());
			console.log('thresholdValue before:', this.thresholdValue);

			if (this.job.Value && this.job.Field === 'weekly') {
				// Clear existing arrays before parsing
				this.selectedDays = [];
				this.timeIntervals = {};
				
				const schedules = this.job.Value.split(',');
				console.log('Parsed schedules:', schedules);

				schedules.forEach(schedule => {
					// First split to get the day
					const [day, ...timeparts] = schedule.split(':');
					// Rejoin the time parts and split on the hyphen
					const timeStr = timeparts.join(':');  // Handles cases like "05:29-18:11"
					const [start, end] = timeStr.split('-');
					
					console.log('Processing schedule entry:', {
						day,
						start,
						end
					});

					this.selectedDays.push(day);
					this.timeIntervals[day] = { start, end };
				});
			} else if (this.job.Value && this.isDataField()) {
				// Handle data fields (total_receive, total_sent, total_data)
				console.log('Parsing data field value:', this.job.Value, 'Field:', this.job.Field, 'isDataField:', this.isDataField);
				try {
					const value = JSON.parse(this.job.Value);
					console.log('Parsed JSON value:', value);
					if (value.threshold !== undefined) {
						this.thresholdValue = value.threshold;
						console.log('Set thresholdValue from JSON:', this.thresholdValue);
					} else {
						console.log('No threshold property in JSON, using direct value');
						this.thresholdValue = parseFloat(this.job.Value) || 0;
					}
				} catch (e) {
					// If not JSON, treat as simple number
					console.log('Not JSON, parsing as number:', this.job.Value);
					this.thresholdValue = parseFloat(this.job.Value) || 0;
					console.log('Set thresholdValue from string:', this.thresholdValue);
				}
			} else {
				console.log('Not parsing - job.Value:', this.job.Value, 'isDataField:', this.isDataField);
			}
			console.log('thresholdValue after parsing:', this.thresholdValue);
			console.log('=== parseExistingJobValue completed ===');
		},
		formatTime(time) {
			const [hours, minutes] = time.split(':').map(Number);
			return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
		},
		timeToMinutes(time) {
			const [hours, minutes] = time.split(':').map(Number);
			return hours * 60 + minutes;
		},
		minutesToTime(minutes) {
			const hours = Math.floor(minutes / 60);
			const mins = minutes % 60;
			return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
		},
		updateTimeFromSlider(day, type, value) {
			const timeString = this.minutesToTime(value);
			this.updateTimeInterval(day, type, timeString);
		},
		getPeerObject() {
			return {
				id: this.job.Peer
			}
		},
		getConfigInfo() {
			return {
				Name: this.job.Configuration
			}
		},
		updateRateLimits(rates) {
			try {
				const currentValue = JSON.parse(this.job.Value || '{}')
				this.job.Value = JSON.stringify({
					threshold: Number(this.thresholdValue),
					upload_rate: Number(rates.upload) || 0,
					download_rate: Number(rates.download) || 0
				})
			} catch (e) {
				console.error('Error updating rate limits:', e)
			}
		},
		updateField(value) {
			this.job.Field = value
			if (this.isDataField && !this.job.Value) {
				this.job.Value = '0'
			}
		},
		updateAction(value) {
			this.job.Action = value
			if (value === 'rate_limit') {
				// Initialize rate limit value structure
				this.job.Value = JSON.stringify({
					threshold: Number(this.thresholdValue) || 0,
					upload_rate: 0,
					download_rate: 0
				})
			} else if (this.isDataField()) {
				// Reset to simple threshold value for non-rate-limit actions
				this.job.Value = String(this.thresholdValue || 0)
			}
		},
		isDataField() {
			return ['total_receive', 'total_sent', 'total_data'].includes(this.job.Field)
		}
	},
	computed: {
		currentFieldType() {
			return this.dropdowns.Field.find(x => x.value === this.job.Field)?.type || 'text';
		},
		weeklyOptions() {
			return this.dropdowns.Field.find(x => x.value === 'weekly')?.options || [];
		},
		formattedValue: {
			get() {
				if (this.isDataField && this.job.Value) {
					try {
						const obj = JSON.parse(this.job.Value);
						return JSON.stringify(obj, null, 2);
					} catch (e) {
						return this.job.Value;
					}
				}
				return this.job.Value;
			},
			set(value) {
				try {
					// Try to parse and re-stringify to remove formatting
					const parsed = JSON.parse(value);
					this.job.Value = JSON.stringify(parsed);
				} catch (e) {
					// If parsing fails, store the raw value
					this.job.Value = value;
				}
			}
		},
		shouldShowJsonInput() {
			return this.job.Field !== 'weekly' && 
				   this.job.Field !== 'date' && 
				   !(this.isDataField && ['restrict', 'allow'].includes(this.job.Action));
		}
	},
	mounted() {
		this.parseExistingJobValue();
	}
}
</script>

<template>
	<div>
		<!-- Main Schedule Job Card -->
		<div class="card shadow-sm rounded-3 mb-2" :class="{'border-warning-subtle': this.newJob}">
			<div class="card-header bg-transparent text-muted border-0">
				<small class="d-flex" v-if="!this.newJob">
					<strong class="me-auto">
						<LocaleText t="Job ID"></LocaleText>
					</strong>
					<samp>{{this.job.JobID}}</samp>
				</small>
				<small v-else><span class="badge text-bg-warning">
					<LocaleText t="Unsaved Job"></LocaleText>
				</span></small>
			</div>
			<div class="card-body pt-1" style="font-family: var(--bs-font-monospace)">
				<!-- Top row with job type and comparator -->
				<div class="d-flex gap-2 align-items-center mb-2">
					<samp><LocaleText t="if"></LocaleText></samp>
					<ScheduleDropdown
						:edit="edit"
						:options="this.dropdowns.Field"
						:data="this.job.Field"
						@update="updateField"
					></ScheduleDropdown>

					<!-- Show operator for non-weekly fields -->
					<template v-if="this.job.Field !== 'weekly'">
						<samp><LocaleText t="is"></LocaleText></samp>
						<ScheduleDropdown
							:edit="edit"
							:options="this.dropdowns.Operator"
							:data="this.job.Operator"
							@update="job.Operator = $event"
						></ScheduleDropdown>
					</template>

					<!-- Data unit input - only show for data fields -->
					<div v-if="this.isDataField && this.job.Field !== 'weekly' && this.job.Field !== 'date'" class="input-group" style="width: auto">
						<!-- Debug info -->
						<small class="text-muted" style="font-size: 0.7em;">
							DEBUG: thresholdValue={{ thresholdValue }}, job.Value={{ job.Value }}
						</small>
						<input
							type="number"
							class="form-control form-control-sm"
							:disabled="!edit"
							v-model="thresholdValue"
							placeholder="Enter threshold"
							style="max-width: 120px"
						/>
						<span class="input-group-text">GB</span>
					</div>

					<!-- Date Picker - show for date fields -->
					<VueDatePicker v-if="this.job.Field === 'date'"
						:is24="true"
						:min-date="new Date()"
						:model-value="this.job.Value"
						@update:model-value="this.parseTime"
						time-picker-inline
						format="yyyy-MM-dd HH:mm:ss"
						preview-format="yyyy-MM-dd HH:mm:ss"
						:clearable="false"
						:disabled="!edit"
						:dark="this.store.Configuration.Server.dashboard_theme === 'dark'"
					/>
				</div>

				<!-- Action section moved up -->
				<div class="px-5 d-flex gap-2 align-items-center mb-2">
					<samp><LocaleText t="then"></LocaleText></samp>
					<ScheduleDropdown
						:edit="edit"
						:options="this.dropdowns.Action"
						:data="this.job.Action"
						@update="updateAction"
					></ScheduleDropdown>
				</div>

				<!-- Value input row -->
				<div class="d-flex gap-2 align-items-center mb-2">
					<!-- Data usage schedule -->
					<DataUsageSchedule
						v-if="isDataField"
						:edit="edit"
						:job="job"
						:dropdowns="dropdowns"
						@update:value="job.Value = $event"
					/>
				</div>

				<!-- Weekly Schedule Component -->
				<div v-if="this.job.Field === 'weekly'" class="card card-body shadow-sm rounded-3 mb-2">
					<WeeklySchedule
						:edit="edit"
						:weekly-options="weeklyOptions"
						:selected-days="selectedDays"
						:time-intervals="timeIntervals"
						@update:time-interval="updateTimeInterval"
						@update:toggle-day="toggleDay"
					/>
				</div>

				<!-- Footer section -->
				<div class="d-flex gap-3">
					<samp>}</samp>
					<div class="ms-auto d-flex gap-3" v-if="!this.edit">
						<a role="button"
						   class="ms-auto text-decoration-none"
						   @click="this.edit = true">[E] <LocaleText t="Edit"></LocaleText></a>
						<a role="button"
						   @click="this.delete()"
						   class=" text-danger text-decoration-none">[D] <LocaleText t="Delete"></LocaleText></a>
					</div>
					<div class="ms-auto d-flex gap-3" v-else>
						<a role="button"
						   class="text-secondary text-decoration-none"
						   @click="this.reset()">[C] <LocaleText t="Cancel"></LocaleText></a>
						<a role="button"
						   class="text-primary ms-auto text-decoration-none"
						   @click="this.save()">[S] <LocaleText t="Save"></LocaleText></a>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
* {
	font-size: 0.875rem;
}

input {
	padding: 0.1rem 0.4rem;
}

input:disabled {
	border-color: transparent;
	background-color: rgba(13, 110, 253, 0.09);
	color: #0d6efd;
}

.dp__main {
	width: auto;
	flex-grow: 1;
	--dp-input-padding: 2.5px 30px 2.5px 12px;
	--dp-border-radius: 0.5rem;
}

select {
	padding: 0.1rem 0.4rem;
}

select:disabled {
	border-color: transparent;
	background-color: rgba(13, 110, 253, 0.09);
	color: #0d6efd;
}

/* Add responsive styles */
@media screen and (max-width: 768px) {
	.card-body {
		padding: 0.75rem;
	}

	.d-flex {
		flex-wrap: wrap;
	}

	.gap-2 {
		gap: 0.5rem !important;
	}

	/* Make inputs and selects full width on mobile */
	input, select, .dp__main {
		width: 100% !important;
		flex: 0 0 100%;
	}

	/* Adjust spacing for mobile */
	.px-5 {
		padding-left: 1rem !important;
		padding-right: 1rem !important;
	}
}

@media screen and (max-width: 576px) {
	.card-header {
		padding: 0.5rem;
	}

	.card-body {
		padding: 0.5rem;
	}
}

/* Add these styles to match the input field appearance */
.input-group .form-control-sm {
	padding: 0.1rem 0.4rem;
}

.input-group .input-group-text {
	padding: 0.1rem 0.4rem;
	font-size: 0.875rem;
}

.input-group {
	flex-wrap: nowrap;
}

.multi-line-input {
	resize: none;
	line-height: 1.2;
	overflow-y: auto;
	white-space: pre;
	word-wrap: break-word;
	word-break: break-all;
	font-family: var(--bs-font-monospace);
}
</style>