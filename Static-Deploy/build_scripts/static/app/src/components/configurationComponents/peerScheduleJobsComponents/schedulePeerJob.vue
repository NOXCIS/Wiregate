<script>
import ScheduleDropdown from "@/components/configurationComponents/peerScheduleJobsComponents/scheduleDropdown.vue";
import {ref, computed} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import VueDatePicker from "@vuepic/vue-datepicker";
import dayjs from "dayjs";
import LocaleText from "@/components/text/localeText.vue";
import WeeklySchedule from "@/components/configurationComponents/peerScheduleJobsComponents/weeklySchedule.vue";

export default {
	name: "schedulePeerJob",
	components: {LocaleText, VueDatePicker, ScheduleDropdown, WeeklySchedule},
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
			timeIntervals: {}
		}
	},
	watch:{
		pjob: {
			deep: true,
			immediate: true,
			handler(newValue){
				if (!this.edit){
					this.job = JSON.parse(JSON.stringify(newValue))
				}
			}
		}	
	},
	methods: {
		save(){
			if (!this.job.Field || !this.job.Action || !this.job.Value || 
				(this.job.Field !== 'weekly' && !this.job.Operator)) {
				this.alert();
				return;
			}

			if (!this.job.Peer && this.pjob?.Peer) {
				this.job.Peer = this.pjob.Peer;
			}

			if (this.job.Field === 'weekly' && !this.job.Value) {
				this.alert();
				return;
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
			console.log('Parsing existing job value:', {
				jobValue: this.job.Value,
				jobField: this.job.Field
			});

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
			}
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
		}
	},
	computed: {
		currentFieldType() {
			return this.dropdowns.Field.find(x => x.value === this.job.Field)?.type || 'text';
		},
		weeklyOptions() {
			return this.dropdowns.Field.find(x => x.value === 'weekly')?.options || [];
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
				<div class="d-flex gap-2 align-items-center mb-2">
					<samp><LocaleText t="if"></LocaleText></samp>
					<ScheduleDropdown
						:edit="edit"
						:options="this.dropdowns.Field"
						:data="this.job.Field"
						@update="(value) => {this.job.Field = value}"
					></ScheduleDropdown>
					<samp><LocaleText t="is"></LocaleText></samp>
					
					<!-- Hide operator for weekly schedule -->
					<template v-if="this.job.Field !== 'weekly'">
						<ScheduleDropdown
							:edit="edit"
							:options="this.dropdowns.Operator"
							:data="this.job.Operator"
							@update="(value) => this.job.Operator = value"
						></ScheduleDropdown>
					</template>

					<!-- Date Picker -->
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
					
					<!-- Regular input for non-weekly/date fields -->
					<input v-if="this.job.Field !== 'weekly' && this.job.Field !== 'date'"
						class="form-control form-control-sm form-control-dark rounded-3 flex-grow-1" 
						:disabled="!edit"
						v-model="this.job.Value"
						style="width: auto">
						
					<samp>{{this.dropdowns.Field.find(x => x.value === this.job.Field)?.unit}} {</samp>
				</div>
				<div class="card card-body shadow-sm rounded-3 mb-2">
		<!-- Weekly Schedule Component (outside main card) -->
		<WeeklySchedule
			v-if="this.job.Field === 'weekly'"
			:edit="edit"
			:weekly-options="weeklyOptions"
			:selected-days="selectedDays"
			:time-intervals="timeIntervals"
			@update:time-interval="updateTimeInterval"
				@update:toggle-day="toggleDay"
			/>
		</div>
	</div>
				<!-- Action section -->
				<div class="px-5 d-flex gap-2 align-items-center">
					<samp><LocaleText t="then"></LocaleText></samp>
					<ScheduleDropdown
						:edit="edit"
						:options="this.dropdowns.Action"
						:data="this.job.Action"
						@update="(value) => this.job.Action = value"
					></ScheduleDropdown>
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
</style>