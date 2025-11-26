<script setup>
import {computed, defineComponent, onBeforeUnmount, onMounted, reactive, ref, useTemplateRef, watch} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import { Line, Bar } from 'vue-chartjs'
import {
	Chart,
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement
} from 'chart.js';
Chart.register(
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement
);

import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import dayjs from "dayjs";
const props = defineProps({
	configurationPeers: Array,
	configurationInfo: Object
})

const MAX_DATA_POINTS = 30
const peerDataHistory = new Map()

const historySentData = ref({
	timestamp: [],
	data: []
})

const historyReceivedData = ref({
	timestamp: [],
	data: []
})

const dashboardStore = DashboardConfigurationStore()
const fetchRealtimeTrafficInterval = ref(undefined)
const fetchRealtimeTraffic = async () => {
	console.log('Fetching traffic for:', props.configurationInfo.Name) // Debug log
	await fetchGet("/api/getConfigurationRealtimeTraffic", {
		configurationName: props.configurationInfo.Name
	}, (res) => {
		console.log('Received traffic data:', res.data) // Debug log
		
		// Check if response is valid and has data
		if (!res || !res.status || !res.data) {
			console.warn('Invalid traffic data response:', res)
			return
		}
		
		let timestamp = dayjs().format("hh:mm:ss A")
		
		// Ensure sent and recv are numbers (default to 0 if missing)
		const sent = res.data.sent ?? 0
		const recv = res.data.recv ?? 0
		
		if (sent !== 0 || recv !== 0) {
			// Add new data points
			historySentData.value.timestamp.push(timestamp)
			historySentData.value.data.push(sent)
			historyReceivedData.value.timestamp.push(timestamp)
			historyReceivedData.value.data.push(recv)

			console.log('Updated chart data:', { // Debug log
				sent: historySentData.value,
				received: historyReceivedData.value
			})

			// Limit array size
			if (historySentData.value.timestamp.length > MAX_DATA_POINTS) {
				historySentData.value.timestamp.shift()
				historySentData.value.data.shift()
				historyReceivedData.value.timestamp.shift()
				historyReceivedData.value.data.shift()
			}
		} else if (historySentData.value.data.length > 0) {
			// Add zero values to show the drop in traffic
			historySentData.value.timestamp.push(timestamp)
			historySentData.value.data.push(0)
			historyReceivedData.value.timestamp.push(timestamp)
			historyReceivedData.value.data.push(0)

			// Maintain array size limit
			if (historySentData.value.timestamp.length > MAX_DATA_POINTS) {
				historySentData.value.timestamp.shift()
				historySentData.value.data.shift()
				historyReceivedData.value.timestamp.shift()
				historyReceivedData.value.data.shift()
			}
		}
	})
}
const toggleFetchRealtimeTraffic = () => {
	console.log('Toggling realtime traffic for:', props.configurationInfo.Name) // Debug log
	
	// Clear existing interval
	if (fetchRealtimeTrafficInterval.value) {
		console.log('Clearing existing interval') // Debug log
		dashboardStore.unregisterInterval(fetchRealtimeTrafficInterval.value);
		clearInterval(fetchRealtimeTrafficInterval.value)
		fetchRealtimeTrafficInterval.value = undefined
	}
	
	// Set new interval if configuration is active
	if (props.configurationInfo.Status) {
		const refreshInterval = dashboardStore.Configuration.Server.dashboard_refresh_interval
		console.log(`Setting new interval with refresh rate: ${refreshInterval}ms`) // Debug log
		fetchRealtimeTrafficInterval.value = setInterval(() => {
			fetchRealtimeTraffic()
		}, refreshInterval)
		// Register interval with global tracker
		if (fetchRealtimeTrafficInterval.value) {
			dashboardStore.registerInterval(fetchRealtimeTrafficInterval.value);
		}
		// Fetch initial data
		fetchRealtimeTraffic()
	}
}

onMounted(() => {
	toggleFetchRealtimeTraffic()
})

watch(() => props.configurationInfo.Status, () => {
	toggleFetchRealtimeTraffic()
})

watch(() => dashboardStore.Configuration.Server.dashboard_refresh_interval, () => {
	toggleFetchRealtimeTraffic()
})

onBeforeUnmount(() => {
	if (fetchRealtimeTrafficInterval.value) {
		dashboardStore.unregisterInterval(fetchRealtimeTrafficInterval.value);
		clearInterval(fetchRealtimeTrafficInterval.value)
		fetchRealtimeTrafficInterval.value = undefined;
	}
})

// Add this at the top level of the component to maintain color mappings
const peerColorMap = new Map()

// Modified color generation function
const getColorForPeer = (peerId) => {
	if (peerColorMap.has(peerId)) {
		return peerColorMap.get(peerId)
	}

	const goldenRatio = 0.618033988749895
	let hue = Math.random()
	
	// Make sure we generate a color that's not too close to existing ones
	if (peerColorMap.size > 0) {
		hue = (peerColorMap.size * goldenRatio) % 1
	}
	
	const h = hue * 360
	const s = 0.7
	const l = 0.6
	
	const rgb = hslToRgb(h, s, l)
	const color = rgbToHex(rgb[0], rgb[1], rgb[2])
	
	peerColorMap.set(peerId, color)
	return color
}

const hslToRgb = (h, s, l) => {
	let r, g, b;

	if (s === 0) {
		r = g = b = l;
	} else {
		const hue2rgb = (p, q, t) => {
			if (t < 0) t += 1;
			if (t > 1) t -= 1;
			if (t < 1/6) return p + (q - p) * 6 * t;
			if (t < 1/2) return q;
			if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
			return p;
		}

		const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
		const p = 2 * l - q;
		r = hue2rgb(p, q, h / 360 + 1/3);
		g = hue2rgb(p, q, h / 360);
		b = hue2rgb(p, q, h / 360 - 1/3);
	}

	return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

const rgbToHex = (r, g, b) => {
	return '#' + [r, g, b].map(x => {
		const hex = x.toString(16);
		return hex.length === 1 ? '0' + hex : hex;
	}).join('');
}

// Add function to manage peer history
const updatePeerHistory = (peer) => {
	const timestamp = dayjs().format("hh:mm:ss A")
	const totalData = peer.cumu_data + peer.total_data
	
	if (!peerDataHistory.has(peer.id)) {
		peerDataHistory.set(peer.id, {
			timestamps: [timestamp],
			values: [totalData]
		})
	} else {
		const history = peerDataHistory.get(peer.id)
		history.timestamps.push(timestamp)
		history.values.push(totalData)
		
		// Keep only last MAX_DATA_POINTS
		if (history.timestamps.length > MAX_DATA_POINTS) {
			history.timestamps.shift()
			history.values.shift()
		}
	}
}

// Update the peersDataUsageChartData computed property
const peersDataUsageChartData = computed(() => {
	const activePeers = props.configurationPeers.filter(x => (x.cumu_data + x.total_data) > 0)
	
	// Update history for all active peers
	activePeers.forEach(updatePeerHistory)
	
	return {
		labels: [...new Set(Array.from(peerDataHistory.values())
			.flatMap(history => history.timestamps))].sort(),
		datasets: activePeers.map(peer => ({
			label: peer.name || `Untitled Peer - ${peer.id}`,
			data: peerDataHistory.get(peer.id)?.values || [],
			fill: false,
			borderColor: getColorForPeer(peer.id),
			backgroundColor: getColorForPeer(peer.id),
			tension: 0.4,
			pointRadius: 2
		}))
	}
})

const peersRealtimeSentData = computed(() => {
	return {
		labels: [...historySentData.value.timestamp],
		datasets: [
			{
				label: 'Data Sent',
				data: [...historySentData.value.data],
				fill: false,
				borderColor: '#198754',
				backgroundColor: '#198754',
				tension: 0
			},
		],
	}
})
const peersRealtimeReceivedData = computed(() => {
	return {
		labels: [...historyReceivedData.value.timestamp],
		datasets: [
			{
				label: 'Data Received',
				data: [...historyReceivedData.value.data],
				fill: false,
				borderColor: '#0d6efd',
				backgroundColor: '#0d6efd',
				tension: 0
			},
		],
	}
})


const peersDataUsageChartOption = computed(() => {
	return {
		responsive: true,
		plugins: {
			legend: {
				display: true,
				position: 'top'
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.formattedValue} GB`
					}
				}
			}
		},
		scales: {
			x: {
				ticks: {
					display: true,
					maxRotation: 45,
					minRotation: 45
				},
				grid: {
					display: true,
					color: 'rgba(255, 255, 255, 0.1)'
				},
			},
			y: {
				beginAtZero: true,
				ticks: {
					callback: (val, index) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} GB`
					}
				},
				grid: {
					display: true,
					color: 'rgba(255, 255, 255, 0.1)'
				},
			}
		},
		animation: {
			duration: 750
		}
	}
})
const realtimePeersChartOption = computed(() => {
	return {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: false
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.formattedValue} Mb/s`
					}
				}
			}
		},
		scales: {
			x: {
				ticks: {
					display: false,
				},
				grid: {
					display: true
				},
			},
			y: {
				beginAtZero: true,
				ticks: {
					callback: (val, index) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} Mb/s`
					}
				},
				grid: {
					display: true
				},
			}
		},
		animation: {
			duration: 0
		}
	}
})

// Clean up the color map when the component is unmounted
onBeforeUnmount(() => {
	peerColorMap.clear()
	peerDataHistory.clear()
})

// Add watcher for configuration status changes
watch(() => props.configurationInfo.Status, (newStatus) => {
	if (!newStatus) {
		// Clear histories when configuration is stopped
		peerDataHistory.clear()
	}
})
</script>

<template>
	<div class="row gx-2 gy-2 mb-3">
		<div class="col-12">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0">
					<small class="text-muted">
						<LocaleText t="Peers Data Usage"></LocaleText>
					</small></div>
				<div class="card-body pt-1">
					<Line
						:data="peersDataUsageChartData"
						:options="peersDataUsageChartOption"
						style="width: 100%; height: 200px;  max-height: 200px"></Line>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Real Time Received Data Usage"></LocaleText>
					</small>
					<small class="text-primary fw-bold ms-auto" v-if="historyReceivedData.data.length > 0">
						{{historyReceivedData.data[historyReceivedData.data.length - 1]}} Mb/s
					</small>
				</div>
				<div class="card-body pt-1">
					<Line
						:options="realtimePeersChartOption"
						:data="peersRealtimeReceivedData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Real Time Sent Data Usage"></LocaleText>
					</small>
					<small class="text-success fw-bold ms-auto"  v-if="historySentData.data.length > 0">
						{{historySentData.data[historySentData.data.length - 1]}} Mb/s
					</small>
				</div>
				<div class="card-body  pt-1">
					<Line
						:options="realtimePeersChartOption"
						:data="peersRealtimeSentData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>