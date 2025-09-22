<script>
import LocaleText from "@/components/text/localeText.vue";
import dayjs from "dayjs";

export default {
	name: "message",
	methods: {
		dayjs,
		hide(){
			this.ct()
			this.message.show = false;
		},
		show(){
			this.timeout = setTimeout(() => {
				this.message.show = false
			}, 3000)
		},
		ct(){
			clearTimeout(this.timeout)
		}
	},
	components: {LocaleText},
	props: {
		message: Object
	},
	mounted() {
		this.show();
	},
	data(){
		return {
			dismiss: false,
			timeout: null
		}
	},
}
</script>

<template>
	<div
		@mouseenter="dismiss = true; this.ct()"
		@mouseleave="dismiss = false; this.show()"
		class="card shadow rounded-3 position-relative message ms-auto"
	     :id="this.message.id">
		<div
			:class="{
			'text-bg-danger': this.message.type === 'danger', 
			'text-bg-success': this.message.type === 'success',
			'text-bg-warning': this.message.type === 'warning'}"
			class="card-header">
			<Transition name="zoom" mode="out-in">
				<div class="d-flex" v-if="!dismiss">
					<small class="fw-bold d-block" style="text-transform: uppercase">
						<LocaleText t="FROM "></LocaleText>
						{{this.message.from}}
					</small>
					<small class="ms-auto">
						{{dayjs().format("hh:mm A")}}
					</small>
				</div>
				<div v-else>
					<small 
						@click="hide()"
						class="d-block mx-auto w-100 text-center" style="cursor: pointer">
						<i class="bi bi-x-lg me-2"></i><LocaleText t="Dismiss"></LocaleText>
					</small>
				</div>
			</Transition>
		</div>
		<div class="card-body d-flex align-items-center gap-3">
			<div>
				{{this.message.content}}
			</div>
			
		</div>
	</div>
</template>

<style scoped>
	.message{
		width: 100%;
	}
	
	@media screen and (min-width: 576px) {
		.message{
			width: 400px;
		}
	}
	
	/* Message type header styling */
	.card-header {
		border: none !important;
		padding: 0.75rem 1rem;
	}
	
	/* Ensure proper contrast for message types */
	.text-bg-danger {
		background-color: #dc3545 !important;
		color: #ffffff !important;
	}
	
	.text-bg-success {
		background-color: #198754 !important;
		color: #ffffff !important;
	}
	
	.text-bg-warning {
		background-color: #ffc107 !important;
		color: #000000 !important;
	}
	
	/* Dark theme adjustments */
	[data-bs-theme="dark"] .text-bg-danger {
		background-color: #dc3545 !important;
		color: #ffffff !important;
	}
	
	[data-bs-theme="dark"] .text-bg-success {
		background-color: #198754 !important;
		color: #ffffff !important;
	}
	
	[data-bs-theme="dark"] .text-bg-warning {
		background-color: #ffc107 !important;
		color: #000000 !important;
	}
	
</style>