<template>
  <div :class="{'modal fade show': !embedded}" :style="!embedded ? 'display: block' : ''">
    <div :class="{'modal-dialog': !embedded}">
      <div :class="{'modal-content': !embedded}">
        <!-- Only show header and close button if not embedded -->
        <div v-if="!embedded" class="modal-header">
          <h5 class="modal-title">
            <LocaleText t="Rate Limit Settings"></LocaleText>
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>

        <div :class="{'modal-body': !embedded}">
          <div v-if="error" class="alert alert-danger mb-3 error-message">
            <span class="message-text">{{ error }}</span>
          </div>
          
          <!-- Upload Rate -->
          <div class="mb-3">
            <label class="form-label">
              <LocaleText t="Upload Rate Limit"></LocaleText>
            </label>
            <div v-if="fetchingRate" class="text-center py-3">
              <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>
            </div>
            <div v-else class="input-group">
              <input 
                type="number" 
                class="form-control"
                v-model="uploadRateValue"
                min="0"
                :placeholder="'Enter upload rate limit'"
              />
              <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                {{ uploadRateUnit }}/s
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" @click="updateUnit('upload', 'Kb')">Kb/s</a></li>
                <li><a class="dropdown-item" @click="updateUnit('upload', 'Mb')">Mb/s</a></li>
                <li><a class="dropdown-item" @click="updateUnit('upload', 'Gb')">Gb/s</a></li>
              </ul>
            </div>
          </div>

          <!-- Download Rate -->
          <div class="mb-3">
            <label class="form-label">
              <LocaleText t="Download Rate Limit"></LocaleText>
            </label>
            <div v-if="fetchingRate" class="text-center py-3">
              <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>
            </div>
            <div v-else class="input-group">
              <input 
                type="number" 
                class="form-control"
                v-model="downloadRateValue"
                min="0"
                :placeholder="'Enter download rate limit'"
              />
              <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                {{ downloadRateUnit }}/s
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" @click="updateUnit('download', 'Kb')">Kb/s</a></li>
                <li><a class="dropdown-item" @click="updateUnit('download', 'Mb')">Mb/s</a></li>
                <li><a class="dropdown-item" @click="updateUnit('download', 'Gb')">Gb/s</a></li>
              </ul>
            </div>
          </div>

          <small class="text-muted d-block mt-1">
            <LocaleText t="Enter 0 to remove rate limit"></LocaleText>
          </small>
        </div>

        <!-- Only show footer buttons if not embedded -->
        <div v-if="!embedded" class="modal-footer">
          <button 
            class="btn btn-secondary"
            @click="removeRateLimit"
            :disabled="loading"
          >
            <span v-if="loading && isRemoving" class="spinner-border spinner-border-sm me-2"></span>
            <LocaleText t="Remove Limit"></LocaleText>
          </button>
          <button 
            class="btn btn-primary"
            @click="applyRateLimit"
            :disabled="loading || !isValidRate"
          >
            <span v-if="loading && !isRemoving" class="spinner-border spinner-border-sm me-2"></span>
            <LocaleText t="Apply"></LocaleText>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import LocaleText from "@/components/text/localeText.vue";
import { WireguardConfigurationsStore } from "@/stores/WireguardConfigurationsStore.js"
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"

export default {
  name: "PeerRateLimitSettings",
  components: {
    LocaleText
  },
  props: {
    selectedPeer: {
      type: Object,
      required: true
    },
    configurationInfo: {
      type: Object,
      required: true
    },
    embedded: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const wireguardStore = WireguardConfigurationsStore()
    const dashboardStore = DashboardConfigurationStore()
    return { wireguardStore, dashboardStore }
  },
  data() {
    return {
      uploadRateValue: 0,
      uploadRateUnit: 'Mb',
      downloadRateValue: 0,
      downloadRateUnit: 'Mb',
      loading: false,
      error: null,
      isRemoving: false,
      fetchingRate: false,
    }
  },
  async created() {
    await this.fetchExistingRateLimit();
  },
  computed: {
    isValidRate() {
      const uploadRate = parseFloat(this.uploadRateValue);
      const downloadRate = parseFloat(this.downloadRateValue);
      return !isNaN(uploadRate) && !isNaN(downloadRate) && uploadRate >= 0 && downloadRate >= 0;
    }
  },
  watch: {
    uploadRateValue(val) {
      this.emitRateUpdate();
    },
    downloadRateValue(val) {
      this.emitRateUpdate();
    },
    uploadRateUnit() {
      this.emitRateUpdate();
    },
    downloadRateUnit() {
      this.emitRateUpdate(); 
    }
  },
  methods: {
    formatToKb(value, unit) {
      const val = parseFloat(value);
      if (isNaN(val)) return '0';
      
      switch (unit.toUpperCase()) {
        case 'GB':
        case 'Gb':
          return (val * 1024 * 1024).toLocaleString();
        case 'MB':
        case 'Mb':
          return (val * 1024).toLocaleString();
        default:
          return val.toLocaleString();
      }
    },
    
    convertToKb(value, unit) {
      const val = parseFloat(value);
      if (isNaN(val)) return 0;
      
      switch (unit.toUpperCase()) {
        case 'GB':
        case 'Gb':
          return val * 1000000; // Gb to Kb (1000 * 1000)
        case 'MB':
        case 'Mb':
          return val * 1000; // Mb to Kb (1000)
        default:
          return val; // Already in Kb
      }
    },
    
    async fetchExistingRateLimit() {
      try {
        await this.wireguardStore.fetchPeerRateLimit(
          this.configurationInfo.Name,
          this.selectedPeer.id
        );
        
        const rateData = this.wireguardStore.peerRateLimits[this.selectedPeer.id];
        [this.uploadRateValue, this.uploadRateUnit] = this.convertFromKb(rateData.upload_rate);
        [this.downloadRateValue, this.downloadRateUnit] = this.convertFromKb(rateData.download_rate);
      } catch (error) {
        this.dashboardStore.newMessage("Error", error.message, "danger");
        this.error = error.message;
      }
    },
    
    async applyRateLimit() {
      if (!this.isValidRate) return;
      
      this.loading = true;
      this.isRemoving = false;
      
      try {
        await this.wireguardStore.setPeerRateLimit(
          this.configurationInfo.Name,
          this.selectedPeer.id,
          this.convertToKb(this.uploadRateValue, this.uploadRateUnit),
          this.convertToKb(this.downloadRateValue, this.downloadRateUnit)
        );
        this.dashboardStore.newMessage("Server", "Rate limits updated successfully", "success");
      } catch (error) {
        this.dashboardStore.newMessage("Error", error.message, "danger");
      } finally {
        this.loading = false;
      }
    },
    
    async removeRateLimit() {
      this.loading = true;
      this.isRemoving = true;
      
      try {
        await this.wireguardStore.removePeerRateLimit(
          this.configurationInfo.Name,
          this.selectedPeer.id
        );
        this.dashboardStore.newMessage("Server", "Rate limits removed successfully", "success");
      } catch (error) {
        this.dashboardStore.newMessage("Error", error.message, "danger");
      } finally {
        this.loading = false;
        this.isRemoving = false;
      }
    },
    
    convertFromKb(rateInKb) {
      if (!rateInKb) return [0, 'Mb'];
      
      const kbValue = parseFloat(rateInKb);
      if (kbValue >= 1000000) {
        return [(kbValue / 1000000).toFixed(2), 'Gb'];
      } else if (kbValue >= 1000) {
        return [(kbValue / 1000).toFixed(2), 'Mb'];
      }
      return [kbValue.toFixed(2), 'Kb'];
    },
    
    updateUnit(direction, newUnit) {
      const oldUnit = direction === 'upload' ? this.uploadRateUnit : this.downloadRateUnit;
      const currentValue = direction === 'upload' ? this.uploadRateValue : this.downloadRateValue;

      // Convert to Kb using precise math
      let valueInKb = this.convertToKb(currentValue, oldUnit);

      // Convert to new unit using precise math
      let newValue;
      switch (newUnit) {
        case 'Gb':
          newValue = (valueInKb / Math.pow(1024, 2)).toFixed(3);
          break;
        case 'Mb':
          newValue = (valueInKb / 1024).toFixed(2);
          break;
        default: // Kb
          newValue = valueInKb.toString();
          break;
      }

      // Update state
      if (direction === 'upload') {
        this.uploadRateUnit = newUnit;
        this.uploadRateValue = newValue;
      } else {
        this.downloadRateUnit = newUnit;
        this.downloadRateValue = newValue;
      }
    },
    emitRateUpdate() {
      if (this.embedded) {
        this.$emit('update:rates', {
          upload: this.convertToKb(this.uploadRateValue, this.uploadRateUnit),
          download: this.convertToKb(this.downloadRateValue, this.downloadRateUnit)
        });
      }
    },
  }
}
</script>

<style scoped>
.modal {
  background: rgba(0, 0, 0, 0.5);
}
.form-select {
  flex: 0 0 auto;
}
.error-message {
  word-wrap: break-word;
  word-break: break-word;
  white-space: pre-wrap;
  max-width: 100%;
  overflow-wrap: break-word;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  padding: 0.75rem 1.25rem;
  margin: 1rem 0;
  border-radius: 0.25rem;
}
.message-text {
  display: inline-block;
  word-break: break-all;
  white-space: normal;
  width: 100%;
}
/* Add embedded specific styles */
.embedded-rate-limit {
  padding: 0;
  margin: 0;
}
</style> 