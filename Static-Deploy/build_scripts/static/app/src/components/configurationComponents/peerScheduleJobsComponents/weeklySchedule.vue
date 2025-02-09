<script>
export default {
  name: 'WeeklySchedule',
  props: {
    edit: {
      type: Boolean,
      default: false
    },
    weeklyOptions: {
      type: Array,
      required: true
    },
    selectedDays: {
      type: Array,
      required: true
    },
    timeIntervals: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      collapsedStates: {}
    }
  },
  created() {
    // Initialize collapse states for all days
    this.selectedDays.forEach(day => {
      this.collapsedStates[day] = false;
    });
  },
  watch: {
    selectedDays: {
      handler(newDays) {
        // Initialize collapse state for new days
        newDays.forEach(day => {
          if (!(day in this.collapsedStates)) {
            this.collapsedStates[day] = false;
          }
        });
      },
      immediate: true
    }
  },
  methods: {
    toggleDay(day) {
      if (!this.edit) return;
      this.$emit('update:toggle-day', day);
    },
    updateTimeInterval(day, type, value) {
      // Validate time format
      const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
      if (!timeRegex.test(value)) {
        console.warn('Invalid time format:', value);
        return;
      }

      if (this.timeIntervals[day]) {
        this.timeIntervals[day][type] = value;
        this.$emit('update:time-interval', day, type, value);
      }
    },
    updateTimeFromSlider(day, type, value) {
      const timeString = this.minutesToTime(parseInt(value));
      this.timeIntervals[day][type] = timeString;
      this.$emit('update:time-interval', { day, type, value: timeString });
    },
    timeToMinutes(time) {
      if (!time) return 0;
      try {
        const [hours, minutes] = time.split(':').map(Number);
        // Ensure hours don't exceed 23
        const validHours = Math.min(hours, 23);
        return validHours * 60 + minutes;
      } catch (e) {
        console.warn('Invalid time format:', time);
        return 0;
      }
    },
    minutesToTime(minutes) {
      // Ensure we don't exceed 23:59
      minutes = Math.min(minutes, 23 * 60 + 59);
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    },
    getTimeValue(day, type) {
      return this.timeIntervals[day]?.[type] || '00:00';
    },
    formatTimeMarker(minutes) {
      const hours = Math.floor(minutes / 60);
      const period = hours >= 12 ? 'PM' : 'AM';
      const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
      return `${displayHours}${period}`;
    },
    generateTimeMarkers() {
      const markers = [];
      // Generate markers for every 3 hours (180 minutes)
      for (let i = 0; i <= 1440; i += 180) {
        markers.push({
          position: (i / 1440) * 100,
          label: this.formatTimeMarker(i)
        });
      }
      return markers;
    },
    toggleCollapse(day) {
      this.collapsedStates[day] = !this.collapsedStates[day];
    }
  }
}
</script>

<template>
  <div class="d-flex flex-column flex-md-row mb-3 gap-2">
    <!-- Days Column - Updated with radio checkboxes -->
    <div class="days-selection">
      <div v-for="option in weeklyOptions" 
           :key="option.value"
           class="day-option">
        <input type="checkbox"
               :id="option.value"
               :checked="selectedDays.includes(option.value)"
               :disabled="!edit"
               class="btn-check bi-circle"
               @change="toggleDay(option.value)">
        <label :for="option.value" 
               class="btn btn-outline-primary w-100 d-flex align-items-center">
          <i class="bi me-2"></i>
          {{ option.label }}
        </label>
      </div>
    </div>

    <!-- Time Settings Column - Made collapsible -->
    <div class="time-settings">
      <div v-for="day in selectedDays" 
           :key="day" 
           class="mb-3 card conf_card bg-dark">
        <div class="card-header p-2 cursor-pointer"
             @click="toggleCollapse(day)">
          <div class="d-flex justify-content-between align-items-center">
            <span>{{ weeklyOptions.find(opt => opt.value === day).label }}</span>
            <i class="bi" 
               :class="collapsedStates[day] ? 'bi-chevron-down' : 'bi-chevron-up'">
            </i>
          </div>
        </div>
        <div class="card-body" v-show="!collapsedStates[day]">
          <div class="time-controls">
            <div class="d-flex flex-wrap gap-3">
              <div class="d-flex align-items-center">
                <span class="me-2">Start:</span>
                <input 
                  type="time" 
                  :value="getTimeValue(day, 'start')"
                  @input="e => updateTimeInterval(day, 'start', e.target.value)"
                  :disabled="!edit"
                  max="23:59"
                  class="time-input">
              </div>
              <div class="d-flex align-items-center">
                <span class="me-2">End:</span>
                <input 
                  type="time" 
                  :value="getTimeValue(day, 'end')"
                  @input="e => updateTimeInterval(day, 'end', e.target.value)"
                  :disabled="!edit"
                  max="23:59"
                  class="time-input">
              </div>
            </div>
            
            <!-- Time Slider -->
            <div class="slider-container mt-3">
              <div class="time-markers">
                <div v-for="marker in generateTimeMarkers()" 
                     :key="marker.position"
                     class="time-marker"
                     :style="{ left: `${marker.position}%` }">
                  <span class="marker-label">{{ marker.label }}</span>
                </div>
              </div>
              <div class="slider-wrapper">
                <input 
                  type="range" 
                  class="time-slider start-handle" 
                  :min="0" 
                  :max="1440" 
                  step="15"
                  :value="timeToMinutes(getTimeValue(day, 'start'))"
                  @input="e => updateTimeFromSlider(day, 'start', e.target.value)"
                  :disabled="!edit">
                <input 
                  type="range" 
                  class="time-slider end-handle" 
                  :min="0" 
                  :max="1440" 
                  step="15"
                  :value="timeToMinutes(getTimeValue(day, 'end'))"
                  @input="e => updateTimeFromSlider(day, 'end', e.target.value)"
                  :disabled="!edit">
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.weekly-schedule-container {
  padding: 1rem;
  background: var(--bs-dark);
  border-radius: 0.5rem;
  width: 100%;
}

.schedule-layout {
  display: flex;
  gap: 2rem;
  width: 100%;
  min-width: 0;
}

.days-selection {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 120px;
  flex-shrink: 0;
}

.days-selection .btn {
  text-align: center;
  transition: all 0.2s ease;
  width: 100%;
}

.time-settings {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.time-controls {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Add responsive styles */
@media screen and (max-width: 768px) {
  .d-flex {
    flex-wrap: wrap;
  }

  .time-controls {
    width: 100%;
  }

  .time-input {
    width: 100%;
    margin: 0.25rem 0;
  }

  .slider-wrapper {
    margin-top: 1rem;
  }

  /* Stack time inputs vertically on mobile */
  .time-controls .d-flex {
    flex-direction: column;
  }

  .time-controls .d-flex .d-flex {
    width: 100%;
    margin-bottom: 0.5rem;
  }

  /* Adjust time markers for better mobile visibility */
  .marker-label {
    font-size: 0.6rem;
  }

  .time-marker {
    display: none;
  }

  .time-marker:nth-child(4n+1) {
    display: flex;
  }
}

@media screen and (max-width: 576px) {
  .weekly-schedule-container {
    padding: 0.5rem;
  }

  .schedule-layout {
    gap: 1rem;
  }

  .days-selection {
    min-width: 100px;
  }

  /* Make time inputs more touch-friendly */
  input[type="time"] {
    min-height: 38px;
  }

  /* Improve slider touch targets */
  .time-slider::-webkit-slider-thumb {
    width: 24px;
    height: 24px;
  }
}

.slider-container {
  position: relative;
  padding-top: 20px;
  margin-top: 1rem;
}

.time-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
}

.time-marker {
  position: absolute;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.marker-label {
  font-size: 0.7rem;
  color: var(--bs-secondary);
}

.slider-wrapper {
  position: relative;
  height: 40px;
  margin-top: 10px;
}

.time-slider {
  position: absolute;
  width: 100%;
  height: 4px;
  background: var(--bs-primary);
  opacity: 0.5;
  border-radius: 2px;
  -webkit-appearance: none;
  appearance: none;
  pointer-events: none;
}

.time-slider::-webkit-slider-thumb {
  pointer-events: auto;
}

.time-slider::-moz-range-thumb {
  pointer-events: auto;
}

.time-slider:disabled {
  opacity: 0.5;
}

/* Mobile responsive additions for slider */
@media screen and (max-width: 768px) {
  .slider-container {
    padding-top: 15px;
  }

  .time-slider::-webkit-slider-thumb {
    width: 20px;
    height: 20px;
  }

  .time-slider::-moz-range-thumb {
    width: 20px;
    height: 20px;
  }

  /* Show fewer time markers on mobile */
  .time-marker {
    display: none;
  }

  .time-marker:nth-child(4n+1) {
    display: flex;
  }

  .marker-label {
    font-size: 0.6rem;
  }
}

@media screen and (max-width: 576px) {
  .slider-wrapper {
    height: 50px; /* Increase touch target area */
  }

  .time-slider {
    height: 6px; /* Slightly thicker slider bar */
  }

  .time-slider::-webkit-slider-thumb {
    width: 24px;
    height: 24px;
  }

  .time-slider::-moz-range-thumb {
    width: 24px;
    height: 24px;
  }
}

.time-slider::-webkit-slider-runnable-track {
  -webkit-appearance: none;
  background: repeating-linear-gradient(
    to right,
    #373b3e,
    #373b3e 2px,
    transparent 2px,
    transparent calc((100% / 96))
  );
  height: 8px;
  border-radius: 4px;
}

.time-slider::-moz-range-track {
  background: repeating-linear-gradient(
    to right,
    #373b3e,
    #373b3e 2px,
    transparent 2px,
    transparent calc((100% / 96))
  );
  height: 8px;
  border-radius: 4px;
}

.time-slider.start-handle {
  z-index: 2;
}

.time-slider.end-handle {
  z-index: 1;
}

.time-slider::-webkit-slider-thumb {
  z-index: 3;
  margin-top: -4px; /* Adjust thumb vertical position */
}

/* Add step attribute to inputs in template */

/* New styles for radio checkboxes and collapsible sections */
.day-option {
  position: relative;
  margin-bottom: 0.5rem;
}

.cursor-pointer {
  cursor: pointer;
}

.card-header:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.btn-check {
  position: absolute;
  clip: rect(0,0,0,0);
  pointer-events: none;
}

.btn-check:checked + .btn {
  background-color: var(--bs-primary);
  color: white;
}

.btn-check:disabled + .btn {
  opacity: 0.65;
  pointer-events: none;
}
</style>