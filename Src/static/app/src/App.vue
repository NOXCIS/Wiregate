<script setup async>
import {RouterView, useRoute} from 'vue-router'
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {computed, watch} from "vue";
const store = DashboardConfigurationStore();
import "@/utilities/wireguard.js"
store.initCrossServerConfiguration();
if (window.IS_WIREGATE_DESKTOP){
	store.IsElectronApp = true;
	store.CrossServerConfiguration.Enable = true;
}
watch(store.CrossServerConfiguration, () => {
	store.syncCrossServerConfiguration()
}, {
	deep: true
});
const route = useRoute()

</script>

<template>
	<div class="loading-bar-top position-absolute loadingBar top-0 start-0"></div>
	<nav class="navbar bg-dark sticky-top" data-bs-theme="dark" v-if="!route.meta.hideTopNav">
		<div class="container-fluid d-flex text-body align-items-center">
			<RouterLink to="/" class="navbar-brand mb-0 h1 d-flex align-items-center">
				<img src="/img/logo.png" alt="WireGate Logo" class="navbar-logo me-2">
				<div class="d-flex flex-column">
					<span class="navbar-title">WireGate</span>
					<small class="navbar-subtitle">Dashboard</small>
				</div>
			</RouterLink>
			<a role="button" class="navbarBtn text-body navbar-toggle-btn"
			   @click="store.ShowNavBar = !store.ShowNavBar">
				<Transition name="fade2" mode="out-in">
					<i class="bi bi-list" v-if="!store.ShowNavBar"></i>
					<i class="bi bi-x-lg" v-else></i>
				</Transition>
			</a>
		</div>
	</nav>
	<RouterView v-slot="{ Component }">
		<Transition name="app" mode="out-in" type="transition" appear>
			<Component :is="Component"></Component>
		</Transition>
	</RouterView>
</template>

<style scoped>
.app-enter-active,
.app-leave-active {
	transition: all 0.7s cubic-bezier(0.82, 0.58, 0.17, 1);
}
.app-enter-from,
.app-leave-to{
	opacity: 0;
	transform: scale(1.1);
}
/* Navbar title and subtitle styles */
.navbar-title {
	font-size: 1.2rem;
	font-weight: 600;
	color: white;
	line-height: 1.2;
}

.navbar-subtitle {
	font-size: 0.7rem;
	color: rgba(255, 255, 255, 0.75);
	line-height: 1;
}

.loading-bar-top {
	z-index: 9999;
	height: 4px;
}

.navbar-logo {
	width: 32px;
}

.navbar-toggle-btn {
	line-height: 0;
	font-size: 2rem;
}

/* Mobile responsive adjustments */
@media screen and (max-width: 767px) {
	.navbar-title {
		font-size: 1rem;
	}
	
	.navbar-subtitle {
		font-size: 0.65rem;
	}
}

@media screen and (min-width: 768px) {
	.navbar{
		display: none;
	}
}
</style>