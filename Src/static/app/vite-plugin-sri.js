import { createHash } from 'crypto';
import { readFileSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

/**
 * Vite plugin to automatically add Subresource Integrity (SRI) attributes
 * to script and link tags in the generated HTML.
 * 
 * This plugin:
 * - Calculates SHA-384 hashes for all JS and CSS assets
 * - Adds integrity and crossorigin attributes to script/link tags
 * - Works with Vite's build process
 */
export function vitePluginSri() {
	let bundle = null;
	let outputDir = null;

	return {
		name: 'vite-plugin-sri',
		apply: 'build',
		generateBundle(options, bundleObj) {
			// Store bundle and output directory
			bundle = bundleObj;
			outputDir = options.dir || resolve(process.cwd(), 'dist');
		},
		writeBundle() {
			// After bundle is written, read and modify the HTML file
			if (!bundle || !outputDir) return;

			const htmlPath = join(outputDir, 'index.html');
			try {
				let html = readFileSync(htmlPath, 'utf-8');

				// Find all script and link tags with src/href attributes
				const scriptRegex = /<script[^>]+src=["']([^"']+)["'][^>]*>/g;
				const linkRegex = /<link[^>]+href=["']([^"']+)["'][^>]*>/g;

				// Process script tags
				html = html.replace(scriptRegex, (match, src) => {
					// Skip if already has integrity attribute
					if (match.includes('integrity=')) {
						return match;
					}

					// Calculate hash for the file
					const integrity = calculateIntegrity(src, bundle, outputDir);
					if (!integrity) {
						// If we can't calculate integrity, skip adding it
						// This is better than adding a wrong hash that blocks the script
						return match;
					}

					// Add integrity and crossorigin attributes
					// Remove existing crossorigin if present
					let newMatch = match.replace(/\s*crossorigin=["'][^"']*["']\s*/gi, '');
					// Add integrity and crossorigin before the closing >
					newMatch = newMatch.replace(/>$/, ` integrity="${integrity}" crossorigin="anonymous">`);

					return newMatch;
				});

				// Process link tags (CSS, etc.)
				html = html.replace(linkRegex, (match, href) => {
					// Only process CSS and preload links
					if (!match.includes('rel="stylesheet"') && 
					    !match.includes("rel='stylesheet'") &&
					    !match.includes('rel="preload"') &&
					    !match.includes("rel='preload'")) {
						return match;
					}

					// Skip if already has integrity attribute
					if (match.includes('integrity=')) {
						return match;
					}

					// Calculate hash for the file
					const integrity = calculateIntegrity(href, bundle, outputDir);
					if (!integrity) {
						return match;
					}

					// Add integrity and crossorigin attributes
					let newMatch = match.replace(/\s*crossorigin=["'][^"']*["']\s*/gi, '');
					newMatch = newMatch.replace(/>$/, ` integrity="${integrity}" crossorigin="anonymous">`);

					return newMatch;
				});

				// Write modified HTML back
				writeFileSync(htmlPath, html, 'utf-8');
			} catch (error) {
				console.warn('SRI plugin: Failed to modify HTML:', error.message);
			}
		}
	};
}

/**
 * Calculate SHA-384 integrity hash for a resource
 * In writeBundle hook, files are already written to disk, so read from filesystem
 */
function calculateIntegrity(src, bundle, outputDir) {
	try {
		// Clean the src path - remove query params and normalize
		let cleanSrc = src.split('?')[0];
		
		// Remove leading slash if present
		if (cleanSrc.startsWith('/')) {
			cleanSrc = cleanSrc.substring(1);
		}
		
		// Handle Vite's base path "/static/app/dist" - remove it if present
		if (cleanSrc.startsWith('static/app/dist/')) {
			cleanSrc = cleanSrc.replace('static/app/dist/', '');
		}
		
		// If the path already starts with "assets/", use it directly
		// Otherwise, prepend "assets/" (Vite outputs to assets/)
		let filePath;
		if (cleanSrc.startsWith('assets/')) {
			filePath = join(outputDir, cleanSrc);
		} else {
			// Extract just the filename if path is complex
			const fileName = cleanSrc.split('/').pop();
			filePath = join(outputDir, 'assets', fileName);
		}
		
		// Read file from disk (files are already written by writeBundle time)
		const content = readFileSync(filePath);
		
		// Calculate SHA-384 hash
		const hash = createHash('sha384')
			.update(content)
			.digest('base64');
		
		return `sha384-${hash}`;
	} catch (error) {
		// Return null if we can't calculate - don't add integrity attribute
		// Silently fail to avoid cluttering build output
		return null;
	}
}

