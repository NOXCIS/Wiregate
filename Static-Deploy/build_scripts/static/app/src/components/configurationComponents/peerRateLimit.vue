
<script>
  import { ref } from 'vue'
  import LocaleText from "@/components/text/localeText.vue"
  import { fetchPost } from '@/utilities/fetch'
  
  export default {
    name: 'PeerRateLimit',
    components: { LocaleText },
    props: {
      peer: {
        type: Object,
        required: true
      },
      interface: {
        type: String,
        required: true
      }
    },
    setup(props, { emit }) {
      const rateLimit = ref(0)
      const isLoading = ref(false)
  
      const applyRateLimit = async () => {
        isLoading.value = true
        try {
          const response = await fetchPost('/api/set_peer_rate_limit', {
            interface: props.interface,
            peer_key: props.peer.id,
            rate: parseInt(rateLimit.value)
          })
          
          if (response.status) {
            emit('success', 'Rate limit applied successfully')
          } else {
            emit('error', response.message)
          }
        } catch (error) {
          emit('error', 'Failed to apply rate limit')
        } finally {
          isLoading.value = false
        }
      }
  
      return {
        rateLimit,
        isLoading,
        applyRateLimit
      }
    }
  }
</script>  

<template>
    <div class="rate-limit-settings">
      <div class="mb-3">
        <label class="form-label">
          <LocaleText t="Rate Limit (Kb/s)"></LocaleText>
        </label>
        <input 
          type="number" 
          class="form-control"
          v-model="rateLimit"
          min="0"
          :placeholder="$t('Enter rate limit in Kb/s')"
        />
      </div>
      <div class="d-flex justify-content-end">
        <button 
          class="btn btn-primary"
          @click="applyRateLimit"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
          <LocaleText t="Apply Rate Limit"></LocaleText>
        </button>
      </div>
    </div>
  </template>
    