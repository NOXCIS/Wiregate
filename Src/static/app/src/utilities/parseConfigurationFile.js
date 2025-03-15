export const parseInterface = (conf) => {
	const lineSplit = conf.split("\n");
	const configuration = {
	  Protocol: 'wg', // Default to regular WireGuard
	  // Initialize IPTables fields with empty strings
	  PreUp: '',
	  PostUp: '',
	  PreDown: '',
	  PostDown: ''
	};
  
	// Check for AmneziaWG parameters
	const amneziaParams = ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4'];
	let hasAmneziaParams = false;
  
	// Helper function to normalize IPTables scripts
	const normalizeIPTablesScript = (script) => {
	  if (!script) return '';
	  // Handle cases where commands are on separate lines and remove empty commands
	  return script.split(';')
		.map(cmd => cmd.trim())
		.filter(cmd => cmd)
		.join(';\n');
	};
  
	// Helper function to validate numeric parameters
	const validateNumericParam = (value, min, max) => {
	  const num = parseInt(value, 10);
	  return !isNaN(num) && num >= min && num <= max ? num : null;
	};
  
	for (let line of lineSplit) {
	  // Break if we hit the Peer section
	  if (line.trim() === "[Peer]") break;
	  if (line.trim() === "[Interface]") continue;
	  // Skip empty lines and comments
	  if (line.trim().length === 0 || line.trim().startsWith('#')) continue;
  
	  // Normalize the line by trimming whitespace and standardizing separator
	  let normalizedLine = line.trim();
	  
	  // Find the first equals sign to properly handle values that may contain equals signs
	  const firstEqualsIndex = normalizedLine.indexOf('=');
	  if (firstEqualsIndex !== -1) {
		// Split the line into key and value using the index of the first equals sign
		const key = normalizedLine.substring(0, firstEqualsIndex).trim();
		// Get everything after the first equals sign as the value
		const value = normalizedLine.substring(firstEqualsIndex + 1).trim();
  
		// Check if this is an AmneziaWG parameter
		if (amneziaParams.includes(key)) {
		  hasAmneziaParams = true;
		  // Validate and convert AmneziaWG parameters
		  switch(key) {
			case 'Jc':
			  configuration[key] = validateNumericParam(value, 1, 128);
			  break;
			case 'Jmin':
			case 'Jmax':
			  configuration[key] = validateNumericParam(value, 0, 1280);
			  break;
			case 'S1':
			case 'S2':
			  configuration[key] = validateNumericParam(value, 15, 150);
			  break;
			case 'H1':
			case 'H2':
			case 'H3':
			case 'H4':
			  configuration[key] = validateNumericParam(value, 5, 2147483647);
			  break;
		  }
		  continue;
		}
  
		// Process standard WireGuard parameters
		switch(key) {
		  case "ListenPort":
			const port = validateNumericParam(value, 0, 65535);
			if (port !== null) {
			  configuration[key] = port;
			}
			break;
  
		  case "PreUp":
		  case "PreDown":
		  case "PostUp":
		  case "PostDown":
			// Always set IPTables fields, normalizing empty or invalid values to empty string
			configuration[key] = normalizeIPTablesScript(value);
			// Check for Tor configuration
			if ((key === "PostUp" || key === "PreDown") && 
				value?.toLowerCase().includes('tor')) {
			  configuration.isTorEnabled = true;
			}
			break;
  
		  case "Address":
			// Store the address as-is, validation will be handled by the UI
			configuration[key] = value;
			break;
  
		  case "PrivateKey":
			// Store key as-is, validation will be handled by the UI
			configuration[key] = value;
			break;
  
		  case "PublicKey":
		  case "PresharedKey":
			// Store keys as-is, validation will be handled by the UI
			configuration[key] = value;
			break;
  
		  default:
			// Store any additional parameters
			configuration[key] = value;
		}
	  }
	}
  
	// Set protocol if AmneziaWG parameters were found
	if (hasAmneziaParams) {
	  configuration.Protocol = 'awg';
	}
  
	// Ensure all required fields exist
	const requiredFields = ['Address', 'ListenPort', 'PrivateKey'];
	const missingFields = requiredFields.filter(field => !configuration[field]);
	
	if (missingFields.length > 0) {
	  console.warn('Missing required fields:', missingFields);
	}	
	return configuration;
};
  
export const parsePeers = (conf) => {
	const lineSplit = conf.split("\n");
	const peers = [];
	let pCounter = -1;
	
	const firstPeer = lineSplit.findIndex(line => line.trim() === "[Peer]");
	if (firstPeer === -1) return false;
  
	for (let l = firstPeer; l < lineSplit.length; l++) {
	  const line = lineSplit[l].trim();
	  
	  if (line === "[Peer]") {
		pCounter += 1;
		peers.push({
		  name: "",
		  enabled: true // Default to enabled
		});
	  } else if (line && !line.startsWith('#')) {
		// Skip empty lines and comments
		// Use the same first-equals-only parsing logic for peers
		const firstEqualsIndex = line.indexOf('=');
		if (firstEqualsIndex !== -1) {
		  const key = line.substring(0, firstEqualsIndex).trim();
		  const value = line.substring(firstEqualsIndex + 1).trim();
		  if (key && value) {
			peers[pCounter][key] = value;
		  }
		}
	  }
	}
  
	return peers;
};