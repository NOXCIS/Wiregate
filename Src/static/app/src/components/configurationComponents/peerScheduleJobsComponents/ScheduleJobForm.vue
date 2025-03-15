<script setup>
import { ref, computed, watch } from 'vue'
import ScheduleDropdown from './scheduleDropdown.vue'
import VueDatePicker from '@vuepic/vue-datepicker'
import WeeklySchedule from './weeklySchedule.vue'
import PeerRateLimitSettings from '../peerRateLimitSettings.vue'
import LocaleText from '@/components/text/localeText.vue'

const props = defineProps({
  job: {
    type: Object,
    required: true
  },
  dropdowns: {
    type: Array,
    required: true
  },
  edit: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['update:job'])

const thresholdValue = ref(0)

const isDataField = computed(() => {
  return ['total_receive', 'total_sent', 'total_data'].includes(props.job.Field)
})

// ... rest of the form logic
</script>

<template>
  <div class="d-flex gap-2 align-items-center mb-2">
    <samp><LocaleText t="if" /></samp>
    <ScheduleDropdown
      :edit="edit"
      :options="dropdowns.Field"
      :data="job.Field"
      @update="$emit('update:job', { ...job, Field: $event })"
    />
    <!-- ... rest of the form template -->
  </div>
</template> 