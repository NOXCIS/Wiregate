<template>
	<div class="container-fluid d-flex align-items-center justify-content-center min-vh-100 position-relative">
		<canvas id="matrix-rain" class="matrix-background"></canvas>
		<div class="text-center error-content">
			<div class="error-code mb-4">
				<img src="/img/noxcis-flag.svg" alt="Noxcis Flag" class="flag-image mb-3">
			</div>
			<div class="error-message mb-4">
				<h2 class="h3 mb-3">404 You're Lost</h2>
				
			</div>
			<div class="error-actions">
				<button 
					@click="goHome" 
					class="btn btn-outline-secondary btn-lg me-3"
					type="button"
				>
					<i class="bi bi-house-door me-2"></i>
					Go Home
				</button>
				<button 
					@click="goBack" 
					class="btn btn-outline-secondary btn-lg"
					type="button"
				>
					<i class="bi bi-arrow-left me-2"></i>
					Go Back
				</button>
			</div>
			<div class="mt-5">
				<div class="row justify-content-center">
					<div class="col-md-8">
						<div class="card border-0 shadow-sm">
							
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { useRouter } from 'vue-router'

export default {
	name: 'NotFound',
	setup() {
		const router = useRouter()

		const goHome = () => {
			router.push('/')
		}

		const goBack = () => {
			if (window.history.length > 1) {
				router.go(-1)
			} else {
				router.push('/')
			}
		}

		return {
			goHome,
			goBack
		}
	},
	methods: {
		initMatrixRain() {
			const canvas = document.getElementById('matrix-rain');
			if (!canvas) return;
			
			const ctx = canvas.getContext('2d');

			// Enable crisp text rendering
			ctx.imageSmoothingEnabled = false;
			ctx.textRendering = 'geometricPrecision';

			// Configuration
			const config = {
				delay: 0,
				fadeFactor: 0.05,
				interval: 95,
				colors: {
					primary: '#4cd964',    // Green
					secondary: '#33ff33',  // Bright green
					purple: {
						head: '#b31fff',     // Bright purple head
						tail: '#7a0cc4'      // Original purple tail
					},
					orange: {
						head: '#ff7b00',     // Bright orange head
						tail: '#e38e41'      // Original orange tail
					},
					cyan: '#00ffff'        // Cyan for easter eggs
				}
			};

			const fontSize = 14;
			const tileSize = fontSize + 2;
			const fontFamily = 'Consolas, monospace'; // Changed to Consolas for sharper rendering
			let columns = [];

			const getRandomStackHeight = () => {
				const maxStackHeight = Math.ceil(canvas.height / tileSize);
				return Math.floor(Math.random() * (maxStackHeight - 10 + 1)) + 10;
			};

			const getRandomText = () => {
				// Easter egg words with low probability
				const easterEggs = ['weir', 'noxis', 'james', 'wireguard', 'amnezia', 'WireGate', '404', 'not found'];
				const showEasterEgg = Math.random() < 0.0011; // 1% chance for easter egg

				if (showEasterEgg) {
					return {
						word: easterEggs[Math.floor(Math.random() * easterEggs.length)],
						isEasterEgg: true,
						charIndex: 0
					};
				}
				return {
					char: String.fromCharCode(Math.floor(Math.random() * (126 - 33 + 1)) + 33),
					isEasterEgg: false
				};
			};

			const getRandomColor = () => {
				// Distribution: 65% primary green, 15% secondary green, 10% purple, 10% orange
				const rand = Math.random();
				if (rand < 0.65) {
					return {
						color: config.colors.primary,
						glow: '#00ff2d',
						type: 'green'
					};
				} else if (rand < 0.80) {
					return {
						color: config.colors.secondary,
						glow: '#33ff33',
						type: 'green'
					};
				} else if (rand < 0.90) {
					return {
						color: config.colors.purple,
						glow: '#b31fff',
						type: 'purple'
					};
				} else {
					return {
						color: config.colors.orange,
						glow: '#ff7b00',
						type: 'orange'
					};
				}
			};

			const initColumns = () => {
				columns = [];
				const columnCount = Math.floor(canvas.width / tileSize);
				for (let i = 0; i < columnCount; i++) {
					const colorInfo = getRandomColor();
					columns.push({
						x: i * tileSize,
						stackCounter: Math.floor(Math.random() * 50),
						stackHeight: getRandomStackHeight(),
						colorInfo: colorInfo,
						intensity: 0.8 + Math.random() * 0.2,
						headPos: 0,
						easterEgg: null
					});
				}
			};

			const resizeCanvas = () => {
				const dpr = window.devicePixelRatio || 1;
				const rect = canvas.getBoundingClientRect();
				
				// Ensure we have valid dimensions
				if (rect.width === 0 || rect.height === 0) {
					// Fallback to window dimensions if canvas rect is not ready
					canvas.width = window.innerWidth * dpr;
					canvas.height = window.innerHeight * dpr;
					canvas.style.width = `${window.innerWidth}px`;
					canvas.style.height = `${window.innerHeight}px`;
				} else {
					canvas.width = rect.width * dpr;
					canvas.height = rect.height * dpr;
					canvas.style.width = `${rect.width}px`;
					canvas.style.height = `${rect.height}px`;
				}
				
				ctx.scale(dpr, dpr);
			};

			const draw = () => {
				// Skip drawing if canvas has no dimensions
				if (canvas.width === 0 || canvas.height === 0) {
					return;
				}

				ctx.font = `bold ${fontSize}px ${fontFamily}`;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				
				ctx.fillStyle = `rgba(0, 0, 0, ${config.fadeFactor})`;
				ctx.fillRect(0, 0, canvas.width, canvas.height);

				columns.forEach(column => {
					ctx.shadowBlur = 0;
					
					const stackProgress = column.stackCounter / column.stackHeight;
					let opacity = column.intensity * (1 - stackProgress * 0.3);
					
					let text;
					if (column.easterEgg) {
						// Continue displaying current easter egg word
						text = {
							char: column.easterEgg.word[column.easterEgg.charIndex],
							isEasterEgg: true
						};
						
						// Move to next character for next frame
						column.easterEgg.charIndex++;
						
						// Reset easter egg when word is complete
						if (column.easterEgg.charIndex >= column.easterEgg.word.length) {
							column.easterEgg = null;
						}
					} else {
						text = getRandomText();
						if (text.isEasterEgg) {
							// Start new easter egg word
							column.easterEgg = {
								word: text.word,
								charIndex: 1  // Start at 1 since we're using first char now
							};
							text.char = text.word[0];  // Use first character immediately
						}
					}
					
					if (text.isEasterEgg) {
						// Use cyan color for easter egg characters
						ctx.shadowBlur = 2;
						ctx.shadowColor = config.colors.cyan;
						ctx.fillStyle = `${config.colors.cyan}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}`;
					} else if (column.colorInfo.type === 'purple' || column.colorInfo.type === 'orange') {
						column.intensity = 0.85 + Math.sin(Date.now() * 0.005) * 0.15;
						
						column.headPos = column.stackCounter * tileSize;
						const gradientLength = 8;
						const distanceFromHead = Math.abs(column.headPos - (column.stackCounter * tileSize));
						const headIntensity = Math.max(0, 1 - (distanceFromHead / (gradientLength * tileSize)));
						
						const colorType = column.colorInfo.type;
						const headColor = config.colors[colorType].head;
						const tailColor = config.colors[colorType].tail;
						
						const r = parseInt(headColor.slice(1, 3), 16) * headIntensity + parseInt(tailColor.slice(1, 3), 16) * (1 - headIntensity);
						const g = parseInt(headColor.slice(3, 5), 16) * headIntensity + parseInt(tailColor.slice(3, 5), 16) * (1 - headIntensity);
						const b = parseInt(headColor.slice(5, 7), 16) * headIntensity + parseInt(tailColor.slice(5, 7), 16) * (1 - headIntensity);
						
						const specialOpacity = opacity * (0.9 + headIntensity * 0.3);
						
						// Add minimal shadow only for head characters
						if (headIntensity > 0.7) {
							ctx.shadowBlur = 1;
							ctx.shadowColor = column.colorInfo.type === 'purple' ? '#b31fff' : '#ff7b00';
						}
						
						ctx.fillStyle = `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${specialOpacity})`;
					} else {
						opacity *= 0.8;
						ctx.fillStyle = column.colorInfo.color.startsWith('#') ? 
							`${column.colorInfo.color}${Math.floor(opacity * 255).toString(16).padStart(2, '0')}` : 
							column.colorInfo.color;
					}

					// Draw characters with pixel-perfect positioning
					ctx.fillText(
						text.char,
						Math.round(column.x + tileSize/2),
						Math.round(column.stackCounter * tileSize + tileSize/2)
					);

					column.stackCounter++;
					if (column.stackCounter >= column.stackHeight) {
						column.stackCounter = 0;
						column.stackHeight = getRandomStackHeight();
						const newColorInfo = getRandomColor();
						column.colorInfo = newColorInfo;
						column.intensity = column.colorInfo.type === 'green' ? 
							0.8 + Math.random() * 0.2 : 
							0.9 + Math.random() * 0.1;
					}
				});
			};

			// Initialize canvas size first
			resizeCanvas();
			
			// Wait for next frame to ensure DOM is fully rendered
			this.$nextTick(() => {
				// Re-resize canvas to ensure correct dimensions
				resizeCanvas();
				
				// Initialize columns
				initColumns();

				// Start animation
				this.matrixInterval = setInterval(draw, config.interval);
			});

			// Handle window resize with debouncing
			let resizeTimeout;
			const handleResize = () => {
				clearTimeout(resizeTimeout);
				resizeTimeout = setTimeout(() => {
					clearInterval(this.matrixInterval);
					resizeCanvas();
					initColumns();
					this.matrixInterval = setInterval(draw, config.interval);
				}, 100);
			};

			window.addEventListener('resize', handleResize);
			
			// Store resize handler for cleanup
			this.handleResize = handleResize;
		}
	},
	mounted() {
		this.initMatrixRain();
	},
	beforeUnmount() {
		if (this.matrixInterval) {
			clearInterval(this.matrixInterval);
		}
		if (this.handleResize) {
			window.removeEventListener('resize', this.handleResize);
		}
	}
}
</script>

<style scoped>
@property --bgdegree {
	syntax: '<angle>';
	initial-value: 234deg;
	inherits: false;
}

@property --distance2 {
	syntax: '<percentage>';
	initial-value: 0%;
	inherits: false;
}

.min-vh-100 {
	min-height: 100vh;
	background: linear-gradient(var(--bgdegree), #150044 var(--distance2), #002e00 100%);
	animation: login 8s ease-in-out infinite;
}

@keyframes login {
	0% {
		--bgdegree: 234deg;
	}
	100% {
		--bgdegree: 594deg;
	}
}

.matrix-background {
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	z-index: 0;
	opacity: 0.50;
	pointer-events: none;
}

.error-content {
	position: relative;
	z-index: 1;
	background: rgba(0, 0, 0, 0.153);
	backdrop-filter: blur(10px);
	border-radius: 1rem;
	padding: 2rem;
	border: 1px solid rgba(255, 255, 255, 0.1);

	background-size: 200px auto;
	background-repeat: no-repeat;
	background-position: center 30%;
}

.error-code h1 {
	font-size: 8rem;
	line-height: 1;
	text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
	color: #4cd964 !important;
}

.error-message h2 {
	font-weight: 600;
	color: #ffffff;
}

.error-message p {
	color: #cccccc;
}

.error-actions .btn {
	border-radius: 0.5rem;
	padding: 0.75rem 1.5rem;
	font-weight: 500;
	transition: all 0.3s ease;
	backdrop-filter: blur(5px);
}

.error-actions .btn:hover {
	transform: translateY(-2px);
	box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.card {
	border-radius: 1rem;
	background: rgba(0, 0, 0, 0.8);
	backdrop-filter: blur(10px);
	border: 1px solid rgba(76, 217, 100, 0.3);
	position: relative;
}

.card-body {
	position: relative;
	z-index: 2;
}

.card-title {
	font-weight: 600;
	color: #4cd964;
	text-shadow: 0 0 10px rgba(76, 217, 100, 0.5);
}

.list-unstyled li {
	padding: 0.25rem 0;
	color: #cccccc;
}

.flag-image {
	max-width: 300px; /* Increased from 150px */
    padding-left: 10px;
	height: auto;
}

@media (max-width: 768px) {
	.error-code h1 {
		font-size: 6rem;
	}
	
	.error-actions .btn {
		display: block;
		width: 100%;
		margin-bottom: 1rem;
	}
	
	.error-actions .btn:last-child {
		margin-bottom: 0;
	}
	
	.error-content {
		padding: 1.5rem;
		margin: 0.5rem;
	}
}
</style>
