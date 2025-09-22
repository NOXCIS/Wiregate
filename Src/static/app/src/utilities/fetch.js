import router from "@/router/router.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const getHeaders = () => {
	let headers = {
		"content-type": "application/json"
	}
	const store = DashboardConfigurationStore();
	const apiKey = store.getActiveCrossServer();
	if (apiKey){
		headers['wg-dashboard-apikey'] = apiKey.apiKey
	}
	return headers
}

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

export const fetchGet = async (url, params=undefined, callback=undefined) => {
	const urlSearchParams = new URLSearchParams(params);
	await fetch(`${getUrl(url)}?${urlSearchParams.toString()}`, {
		headers: getHeaders()
	})
	.then((x) => {
		const store = DashboardConfigurationStore();
		if (!x.ok){
			if (x.status !== 200){
				if (x.status === 401){
					store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
					router.push({path: '/signin'})
				} else if (x.status === 429) {
					// Redirect to 429 page for rate limiting
					// Only get retry_after time, don't disclose other limit details
					x.json().then(data => {
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
				} else {
					throw new Error(x.statusText)
				}
			}
		}else{
			return x.json()
		}
	}).then(x => callback ? callback(x) : undefined).catch(x => {
		console.log(x)
		// Only redirect to signin if it's not a 429 error (already handled above)
		if (x.message && !x.message.includes('429')) {
			router.push({path: '/signin'})
		}
	})
}

export const fetchPost = async (url, body, callback) => {
	await fetch(`${getUrl(url)}`, {
		headers: getHeaders(),
		method: "POST",
		body: JSON.stringify(body)
	}).then((x) => {
		const store = DashboardConfigurationStore();
		if (!x.ok){
			if (x.status !== 200){
				if (x.status === 401){
					store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
					router.push({path: '/signin'})
				} else if (x.status === 429) {
					// Redirect to 429 page for rate limiting
					// Only get retry_after time, don't disclose other limit details
					x.json().then(data => {
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
				} else {
					throw new Error(x.statusText)
				}
			}
		}else{
			return x.json()
		}
	}).then(x => callback ? callback(x) : undefined).catch(x => {
		console.log(x)
		// Only redirect to signin if it's not a 429 error (already handled above)
		if (x.message && !x.message.includes('429')) {
			router.push({path: '/signin'})
		}
	})
}