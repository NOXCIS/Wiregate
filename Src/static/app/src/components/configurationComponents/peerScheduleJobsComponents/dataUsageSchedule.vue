<script>
import { defineAsyncComponent } from 'vue'

const PeerRateLimitSettings = defineAsyncComponent(() => import('@/components/configurationComponents/peerRateLimitSettings.vue'))

export default {
    name: "dataUsageSchedule",
    components: { PeerRateLimitSettings },
    props: {
        edit: {
            type: Boolean,
            default: false
        },
        job: {
            type: Object,
            required: true
        },
        dropdowns: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            thresholdValue: 0,
            rateLimits: {
                upload: 0,
                download: 0
            }
        }
    },
    watch: {
        'job.Value': {
            immediate: true,
            handler(newValue) {
                try {
                    const value = JSON.parse(newValue)
                    if (value.threshold) {
                        this.thresholdValue = value.threshold
                    }
                    if (value.upload_rate !== undefined) {
                        this.rateLimits.upload = value.upload_rate
                    }
                    if (value.download_rate !== undefined) {
                        this.rateLimits.download = value.download_rate
                    }
                } catch (e) {
                    this.thresholdValue = parseFloat(newValue) || 0
                }
            }
        },
        thresholdValue(newValue) {
            if (this.job.Action === 'rate_limit') {
                try {
                    const currentValue = JSON.parse(this.job.Value || '{}')
                    this.$emit('update:value', JSON.stringify({
                        ...currentValue,
                        threshold: Number(newValue) || 0
                    }))
                } catch (e) {
                    this.$emit('update:value', JSON.stringify({
                        threshold: Number(newValue) || 0
                    }))
                }
            } else {
                this.$emit('update:value', String(newValue || 0))
            }
        }
    },
    methods: {
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
            this.rateLimits = rates
            try {
                this.$emit('update:value', JSON.stringify({
                    threshold: Number(this.thresholdValue),
                    upload_rate: Number(rates.upload) || 0,
                    download_rate: Number(rates.download) || 0
                }))
            } catch (e) {
                console.error('Error updating rate limits:', e)
            }
        },
        isDataField() {
            return ['total_receive', 'total_sent', 'total_data'].includes(this.job.Field)
        }
    }
}
</script>

<template>
    <div class="d-flex gap-2 align-items-center">
        <!-- Threshold input for data usage -->
        <div v-if="this.isDataField" class="input-group" style="width: auto">
                        <input
                            type="number"
                            class="form-control"
                            :disabled="!edit"
                            v-model="thresholdValue"
                            placeholder="Enter threshold"
                        />
                        <span class="input-group-text">GB</span>
                    </div>

                    <!-- Add rate limit settings component -->
                    <div v-if="this.job.Action === 'rate_limit' && this.isDataField" class="flex-grow-1">
                        <PeerRateLimitSettings
                            :selectedPeer="getPeerObject()"
                            :configurationInfo="getConfigInfo()"
                            :embedded="true"
                            @update:rates="updateRateLimits"
                        />
                    </div>

        <!-- Rate limit settings -->
        <div v-if="job.Action === 'rate_limit'" class="flex-grow-1">
            <PeerRateLimitSettings
                :selectedPeer="getPeerObject()"
                :configurationInfo="getConfigInfo()"
                :embedded="true"
                :edit="edit"
                :rates="rateLimits"
                @update:rates="updateRateLimits"
            />
        </div>
    </div>
</template>

<style scoped>
input {
    padding: 0.1rem 0.4rem;
}

input:disabled {
    border-color: transparent;
    background-color: rgba(13, 110, 253, 0.09);
    color: #0d6efd;
}
</style> 