<script setup>
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	protocol: String,
	hasTor: Boolean,
	mini: false
})
</script>

<template>
<div class="d-flex gap-1 align-items-center">
	<span class="badge wireguardBg rounded-3 shadow" v-if="protocol === 'wg'">
		WireGuard <LocaleText t="Configuration" v-if="!mini"></LocaleText>
	</span>
	<span class="badge amneziawgBg rounded-3 shadow" v-else-if="protocol === 'awg'">
		AmneziaWG <LocaleText t="Configuration" v-if="!mini"></LocaleText>
	</span>
	<span class="badge torBg rounded-3 shadow" v-if="hasTor">
		Tor <LocaleText t="Proxy" v-if="!mini"></LocaleText>
	</span>
</div>
</template>

<style scoped>

</style>