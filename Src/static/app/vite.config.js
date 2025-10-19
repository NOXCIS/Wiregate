import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import {proxy} from "./proxy.js";
import vue from '@vitejs/plugin-vue'
import {v1} from "uuid";

export default defineConfig(({mode}) => {
	// Check if DASHBOARD_MODE is set to 'prod'
	const isProduction = process.env.DASHBOARD_MODE === 'production';
	
	if (mode === 'electron'){
		return {
			emptyOutDir: false,
			base: './',
			plugins: [
				vue(),
			],
			resolve: {
				alias: {
					'@': fileURLToPath(new URL('./src', import.meta.url))
				}
			},
			build: {
				target: "es2022",
				outDir: '../../../../WireGate-Desktop',
				minify: 'terser',
				terserOptions: {
					compress: {
						drop_console: isProduction,
						drop_debugger: isProduction
					}
				},
				rollupOptions: {
					output: {
						entryFileNames: `assets/[name]-[hash].js`,
						chunkFileNames: `assets/[name]-[hash].js`,
						assetFileNames: `assets/[name]-[hash].[ext]`
					}
				}
			}
		}
	}

	return {
		base: "/static/app/dist",
		plugins: [
			vue(),
		],
		resolve: {
			alias: {
				'@': fileURLToPath(new URL('./src', import.meta.url))
			}
		},
		server:{
			proxy: {
				'/api': proxy
			},
			host: '0.0.0.0'
		},
		build: {
			target: "es2022",
			outDir: 'dist',
			minify: 'terser',
			terserOptions: {
				compress: {
					drop_console: isProduction,
					drop_debugger: isProduction
				}
			},
			rollupOptions: {
				output: {
					entryFileNames: `assets/[name]-[hash].js`,
					chunkFileNames: `assets/[name]-[hash].js`,
					assetFileNames: `assets/[name]-[hash].[ext]`
				}
			}
		}
	}
})