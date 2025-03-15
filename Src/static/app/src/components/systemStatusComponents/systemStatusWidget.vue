<script setup>
import {onBeforeUnmount, onMounted, ref, computed} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import CpuCore from "@/components/systemStatusComponents/cpuCore.vue";
import StorageMount from "@/components/systemStatusComponents/storageMount.vue";

const data = ref(null)
let interval = null;

onMounted(() => {
    getData()
    interval = setInterval(() => {
        getData()
    }, 5000)
})

onBeforeUnmount(() => {
    clearInterval(interval)
})

const getData = () => {
	fetchGet("/api/systemStatus", {}, (res) => {
		data.value = res.data
	})
}

// Computed properties to safely access nested data
const cpuPercent = computed(() => data.value?.cpu?.cpu_percent ?? 0);
const cpuPerCorePercents = computed(() => data.value?.cpu?.cpu_percent_per_cpu ?? []);
const diskData = computed(() => data.value?.disk ?? {});
const hasStorageData = computed(() => Object.keys(diskData.value).length > 0);
const primaryDiskPercent = computed(() => {
    const disks = Object.keys(diskData.value);
    return disks.length > 0 ? diskData.value[disks[0]]?.percent ?? 0 : 0;
});
const memoryPercent = computed(() => data.value?.memory?.virtual_memory?.percent ?? 0);
const swapPercent = computed(() => data.value?.memory?.swap_memory?.percent ?? 0);
</script>

<template>
	<!-- CPU Section -->
    <div class="row text-body g-3 mb-5">
		<div class="col-md-6 col-sm-12 col-xl-3">
			<div class="d-flex align-items-center">
				<h6 class="text-muted">
					<i class="bi bi-cpu-fill me-2"></i>
					<LocaleText t="CPU"></LocaleText>
				</h6>
				<h6 class="ms-auto">
							<span v-if="data">
								{{ data.cpu.cpu_percent }}%
							</span>
					<span v-else class="spinner-border spinner-border-sm"></span>
				</h6>
			</div>
			<div class="progress" role="progressbar" style="height: 6px">
				<div class="progress-bar" :style="{width: `${data?.cpu.cpu_percent}%` }"></div>
			</div>
			<div class="d-flex mt-2 gap-1">
				<CpuCore v-for="(cpu, count) in data?.cpu.cpu_percent_per_cpu"
				         :key="count"
				         :align="(count + 1) > Math.round(data?.cpu.cpu_percent_per_cpu.length / 2)"
				         :core_number="count" :percentage="cpu"
				></CpuCore>
			</div>
		</div>

        <!-- Storage Section -->
        <div class="col-md-6 col-sm-12 col-xl-3">
            <div class="d-flex align-items-center">
                <h6 class="text-muted">
                    <i class="bi bi-device-ssd-fill me-2"></i>
                    <LocaleText t="Storage"></LocaleText>
                </h6>
                <h6 class="ms-auto">
                    <span v-if="data !== null && hasStorageData">
                        {{ primaryDiskPercent }}%
                    </span>
                    <span v-else class="spinner-border spinner-border-sm"></span>
                </h6>
            </div>
            <div class="progress" role="progressbar" style="height: 6px">
                <div class="progress-bar bg-success" :style="{width: `${primaryDiskPercent}%` }"></div>
            </div>
            <div class="d-flex mt-2 gap-1">
                <StorageMount 
                    v-for="(disk, count) in Object.keys(diskData)"
                    :key="disk"
                    :align="(count + 1) > Math.round(Object.keys(diskData).length / 2)"
                    :mount="disk" 
                    :percentage="diskData[disk]?.percent ?? 0"
                ></StorageMount>
            </div>
        </div>

        <!-- Memory Section -->
        <div class="col-md-6 col-sm-12 col-xl-3">
            <div class="d-flex align-items-center">
                <h6 class="text-muted">
                    <i class="bi bi-memory me-2"></i>
                    <LocaleText t="Memory"></LocaleText>
                </h6>
                <h6 class="ms-auto">
                    <span v-if="data !== null">
                        {{ memoryPercent }}%
                    </span>
                    <span v-else class="spinner-border spinner-border-sm"></span>
                </h6>
            </div>
            <div class="progress" role="progressbar" style="height: 6px">
                <div class="progress-bar bg-info" :style="{width: `${memoryPercent}%` }"></div>
            </div>
        </div>

        <!-- Swap Memory Section -->
        <div class="col-md-6 col-sm-12 col-xl-3">
            <div class="d-flex align-items-center">
                <h6 class="text-muted">
                    <i class="bi bi-memory me-2"></i>
                    <LocaleText t="Swap Memory"></LocaleText>
                </h6>
                <h6 class="ms-auto">
                    <span v-if="data !== null">
                        {{ swapPercent }}%
                    </span>
                    <span v-else class="spinner-border spinner-border-sm"></span>
                </h6>
            </div>
            <div class="progress" role="progressbar" style="height: 6px">
                <div class="progress-bar bg-warning" :style="{width: `${swapPercent}%` }"></div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.progress-bar {
    width: 0;
    transition: all 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}
</style>