import router from "@/router/router.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

// CSRF token cache
let csrfToken = null;
let csrfTokenPromise = null;

const getUrl = (url) => {
	const store = DashboardConfigurationStore();
	const apiKey = store.getActiveCrossServer();
	if (apiKey){
		return `${apiKey.host}${url}`
	}
	
	// console.log("URL fetching: ", import.meta.env.MODE === 'development' ? url
	// 	: `${window.location.protocol}//${(window.location.host + window.location.pathname + url).replace(/\/\//g, '/')}`)
	return import.meta.env.MODE === 'development' ? url 
		: `${window.location.protocol}//${(window.location.host + window.location.pathname + url).replace(/\/\//g, '/')}`
}

// Fetch CSRF token from server
const fetchCsrfToken = async () => {
	// Check if session is expired - don't try to fetch if we know we're not authenticated
	const store = DashboardConfigurationStore();
	if (store.sessionExpired) {
		csrfToken = null;
		return null;
	}
	
	if (csrfTokenPromise) {
		return csrfTokenPromise;
	}
	
	csrfTokenPromise = fetch(`${getUrl('/api/csrf-token')}`, {
		headers: {
			"content-type": "application/json"
		},
		credentials: 'include'
	})
	.then(response => {
		// Handle 401 (Unauthorized) gracefully - user not authenticated yet
		if (response.status === 401) {
			csrfToken = null;
			// Mark session as expired if we get 401
			const store = DashboardConfigurationStore();
			store.handleSessionExpiration();
			return null;
		}
		if (response.ok) {
			return response.json();
		}
		throw new Error(`Failed to fetch CSRF token: ${response.status}`);
	})
	.then(data => {
		if (data && data.status && data.data && data.data.csrf_token) {
			csrfToken = data.data.csrf_token;
			return csrfToken;
		}
		// Invalid response but not an error - user might not be authenticated
		csrfToken = null;
		return null;
	})
	.catch(error => {
		// Only log non-401 errors as warnings
		if (error.message && !error.message.includes('401')) {
			console.warn('CSRF token fetch failed:', error);
		}
		csrfToken = null;
		return null;
	})
	.finally(() => {
		csrfTokenPromise = null;
	});
	
	return csrfTokenPromise;
};

// Export function to clear CSRF token (e.g., on logout)
export const clearCsrfToken = () => {
	csrfToken = null;
	csrfTokenPromise = null;
};

// Export function to refresh CSRF token
export const refreshCsrfToken = async () => {
	csrfToken = null;
	csrfTokenPromise = null;
	return await fetchCsrfToken();
};

const getHeaders = (method = 'GET') => {
	let headers = {
		"content-type": "application/json"
	}
	const store = DashboardConfigurationStore();
	const apiKey = store.getActiveCrossServer();
	if (apiKey){
		headers['wg-dashboard-apikey'] = apiKey.apiKey
	}
	
	// Add CSRF token for state-changing methods (when available)
	if (method !== 'GET' && csrfToken) {
		headers['X-CSRF-Token'] = csrfToken;
	}
	
	return headers
}

export const fetchGet = async (url, params=undefined, callback=undefined) => {
	const store = DashboardConfigurationStore();
	
	// Allow authenticate and validateAuthentication even if session expired
	const exemptUrls = ['/api/authenticate', '/api/validateAuthentication'];
	const isExempt = exemptUrls.some(exemptUrl => url.includes(exemptUrl));
	
	// Prevent API calls if session expired (except exempt URLs)
	if (store.sessionExpired && !isExempt) {
		console.warn('Session expired - blocking API call to:', url);
		if (callback) {
			callback({ status: false, message: 'Session expired' });
		}
		return;
	}
	
	const urlSearchParams = new URLSearchParams(params);
	try {
		const response = await fetch(`${getUrl(url)}?${urlSearchParams.toString()}`, {
			headers: getHeaders('GET'),
			credentials: 'include'
		});
		
		const store = DashboardConfigurationStore();
		if (!response.ok){
			if (response.status !== 200){
				if (response.status === 401){
					// Stop all polling intervals IMMEDIATELY to prevent rate limit lockout
					store.handleSessionExpiration();
					store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
					// Redirect immediately - don't wait for callback
					router.push({path: '/signin'})
					if (callback) {
						callback({ status: false, message: 'Session expired' });
					}
					return; // Exit early to prevent further processing
				} else if (response.status === 429) {
					// Redirect to 429 page for rate limiting
					// Only get retry_after time, don't disclose other limit details
					response.json().then(data => {
						if (data && data.data && data.data.retry_after) {
							const params = new URLSearchParams({
								retry_after: data.data.retry_after
							})
							router.push({path: `/429?${params.toString()}`})
						} else {
							router.push({path: '/429'})
						}
					}).catch(() => {
						router.push({path: '/429'})
					})
					if (callback) {
						callback({ status: false, message: 'Rate limit exceeded' });
					}
					return;
				} else {
					throw new Error(response.statusText)
				}
			}
		} else {
			const data = await response.json();
			// Check response body for session expiration (validateAuthentication returns status: false)
			if (data && !data.status && url.includes('/api/validateAuthentication')) {
				const store = DashboardConfigurationStore();
				store.handleSessionExpiration();
			}
			if (callback) {
				callback(data);
			}
		}
	} catch (x) {
		console.log(x)
		// Only redirect to signin if it's not a 429 error (already handled above)
		if (x.message && !x.message.includes('429')) {
			router.push({path: '/signin'})
		}
		if (callback) {
			callback({ status: false, message: x.message || 'Request failed' });
		}
	}
}

export const fetchPost = async (url, body, callback) => {
	const store = DashboardConfigurationStore();
	
	// Allow authenticate and other exempt endpoints even if session expired
	const exemptPaths = ['/api/authenticate', '/api/validate-csrf', '/api/handshake', '/api/health'];
	const isExempt = exemptPaths.some(path => url.includes(path));
	
	// Prevent API calls if session expired (except exempt URLs)
	if (store.sessionExpired && !isExempt) {
		console.warn('Session expired - blocking API call to:', url);
		if (callback) {
			callback({ status: false, message: 'Session expired' });
		}
		return;
	}
	
	// Fetch CSRF token for authenticated POST requests (except exempt endpoints)
	const needsCsrf = !exemptPaths.some(path => url.includes(path));
	
	// Ensure we have a CSRF token before making POST request
	// Only fetch if we're not in a session-expired state
	if (needsCsrf && !csrfToken && !store.sessionExpired) {
		await fetchCsrfToken();
	}
	
	// Make the POST request
	let response = await fetch(`${getUrl(url)}`, {
		headers: getHeaders('POST'),
		method: "POST",
		body: JSON.stringify(body),
		credentials: 'include'
	});
	
	// Handle CSRF token errors - retry once with fresh token
	if (response.status === 403) {
		try {
			const errorData = await response.clone().json();
			if (errorData.message && (errorData.message.includes('CSRF') || errorData.message.includes('csrf') || 
			    errorData.error && (errorData.error.includes('CSRF') || errorData.error.includes('csrf')))) {
				// CSRF token invalid or missing - try refreshing token once
				console.warn('CSRF token error, refreshing token and retrying...');
				csrfToken = null;
				const newToken = await fetchCsrfToken();
				
				if (newToken) {
					// Retry the request with new token
					response = await fetch(`${getUrl(url)}`, {
						headers: getHeaders('POST'),
						method: "POST",
						body: JSON.stringify(body),
						credentials: 'include'
					});
					
					// If retry still fails, show message
					if (response.status === 403) {
						store.newMessage("Security", "Session token expired, please refresh the page", "warning");
					}
				} else {
					store.newMessage("Security", "Session token expired, please refresh the page", "warning");
				}
			}
		} catch (e) {
			// Couldn't parse error response, continue with original response
			console.warn('Could not parse CSRF error response:', e);
		}
	}
	
	// Handle the response
	try {
		if (!response.ok) {
			if (response.status !== 200) {
				if (response.status === 401) {
					// Stop all polling intervals IMMEDIATELY to prevent rate limit lockout
					const store = DashboardConfigurationStore();
					store.handleSessionExpiration();
					store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning");
					router.push({path: '/signin'});
					return; // Exit early to prevent further processing
				} else if (response.status === 429) {
					// Redirect to 429 page for rate limiting
					try {
						const data = await response.json();
						if (data && data.data && data.data.retry_after) {
							const params = new URLSearchParams({
								retry_after: data.data.retry_after
							});
							router.push({path: `/429?${params.toString()}`});
						} else {
							router.push({path: '/429'});
						}
					} catch (e) {
						router.push({path: '/429'});
					}
					return;
				} else {
					throw new Error(response.statusText);
				}
			}
		}
		
		const data = await response.json();
		if (callback) {
			callback(data);
		}
	} catch (x) {
		console.log(x);
		// Only redirect to signin if it's not a 429 error (already handled above)
		if (x.message && !x.message.includes('429')) {
			router.push({path: '/signin'});
		}
	}
}
