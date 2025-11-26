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
	const cpsParams = ['I1', 'I2', 'I3', 'I4', 'I5'];
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
	
	// Helper function to normalize CPS format (convert raw hex 0x... to <b 0x...> format)
	const normalizeCPSFormat = (cpsValue) => {
	  if (!cpsValue || !cpsValue.trim()) {
		return cpsValue;
	  }
	  
	  const trimmed = cpsValue.trim();
	  
	  // If it's already in CPS tag format (contains <b, <c, <t, <r, etc.), return as-is
	  if (trimmed.includes('<') && trimmed.includes('>')) {
		return trimmed;
	  }
	  
	  // Check if it's a raw hex value (starts with 0x)
	  if (trimmed.startsWith('0x')) {
		// Remove the 0x prefix and wrap in <b 0x...> tag
		const hexContent = trimmed.substring(2);
		// Validate hex content (only hex characters)
		if (/^[0-9a-fA-F]+$/.test(hexContent)) {
		  return `<b 0x${hexContent}>`;
		}
	  }
	  
	  // If it doesn't match any known format, return as-is
	  return trimmed;
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
		
		// Check if this is a CPS parameter (I1-I5)
		if (cpsParams.includes(key)) {
		  hasAmneziaParams = true;
		  // Normalize raw hex values (0x...) to CPS tag format (<b 0x...>)
		  configuration[key] = normalizeCPSFormat(value);
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
	
	// Helper function to normalize CPS format (convert raw hex 0x... to <b 0x...> format)
	const normalizeCPSFormat = (cpsValue) => {
	  if (!cpsValue || !cpsValue.trim()) {
		return cpsValue;
	  }
	  
	  const trimmed = cpsValue.trim();
	  
	  // If it's already in CPS tag format (contains <b, <c, <t, <r, etc.), return as-is
	  if (trimmed.includes('<') && trimmed.includes('>')) {
		return trimmed;
	  }
	  
	  // Check if it's a raw hex value (starts with 0x)
	  if (trimmed.startsWith('0x')) {
		// Remove the 0x prefix and wrap in <b 0x...> tag
		const hexContent = trimmed.substring(2);
		// Validate hex content (only hex characters)
		if (/^[0-9a-fA-F]+$/.test(hexContent)) {
		  return `<b 0x${hexContent}>`;
		}
	  }
	  
	  // If it doesn't match any known format, return as-is
	  return trimmed;
	};
	
	const cpsParams = ['I1', 'I2', 'I3', 'I4', 'I5'];
  
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
		  let value = line.substring(firstEqualsIndex + 1).trim();
		  
		  // Normalize I1-I5 CPS parameters (convert raw hex 0x... to <b 0x...> format)
		  if (cpsParams.includes(key)) {
			value = normalizeCPSFormat(value);
		  }
		  
		  if (key && value) {
			peers[pCounter][key] = value;
		  }
		}
	  }
	}
  
	return peers;
};