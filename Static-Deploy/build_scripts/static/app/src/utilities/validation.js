import { parse } from "cidr-tools";

/**
 * Validation rules for WireGuard configuration fields
 */
export const ValidationRules = {
  /**
   * Port validation (0-65353)
   * @param {string|number} value - Port number to validate
   * @returns {boolean} - Whether the port is valid
   */
  port: (value) => {
    const port = Number(value);
    return value !== "" && 
           port >= 0 && 
           port <= 65353 && 
           Number.isInteger(port);
  },
  
  /**
   * Configuration name validation
   * @param {string} value - Configuration name to validate
   * @param {Array} existingConfigs - Array of existing configurations to check for duplicates
   * @returns {boolean} - Whether the configuration name is valid
   */
  configName: (value, existingConfigs) => {
    return value && 
           value.length <= 15 &&
           /^[a-zA-Z0-9_=+.-]+$/.test(value) && 
           !existingConfigs.find(x => x.Name === value);
  },
  
  /**
   * CIDR address validation
   * @param {string} value - CIDR address to validate
   * @returns {boolean} - Whether the address is valid
   */
  address: (value) => {
    try {
      if (!value || !value.includes('/')) return false;
      
      const parts = value.trim().split("/").filter(x => x.length > 0);
      if (parts.length !== 2) return false;
      
      // Validate IP address format
      const ipParts = parts[0].split('.');
      if (ipParts.length !== 4) return false;
      
      for (const part of ipParts) {
        const num = parseInt(part);
        if (isNaN(num) || num < 0 || num > 255) return false;
      }
      
      // Validate subnet mask
      const subnet = parseInt(parts[1]);
      if (isNaN(subnet) || subnet < 0 || subnet > 32) return false;
      
      // Final validation using cidr-tools
      parse(value);
      return true;
    } catch {
      return false;
    }
  },
  
  /**
   * AmneziaWG specific parameter validation rules
   */
  awgParams: {
    /**
     * Validates Jc (junk packets count)
     */
    Jc: (val) => {
      const value = Number(val);
      return val !== "" && 
             value >= 1 && 
             value <= 128 && 
             Number.isInteger(value);
    },
    
    /**
     * Validates Jmin (minimum junk packet size)
     */
    Jmin: (val, max) => {
      const value = Number(val);
      const maxValue = Number(max);
      return val !== "" && 
             value >= 0 && 
             value <= 1280 && 
             (!max || value < maxValue);
    },
    
    /**
     * Validates Jmax (maximum junk packet size)
     */
    Jmax: (val, min) => {
      const value = Number(val);
      const minValue = Number(min);
      return val !== "" && 
             value > 0 && 
             value <= 1280 && 
             (!min || value > minValue);
    },
    
    /**
     * Validates S1 (handshake initiation junk data size)
     */
    S1: (val, s2) => {
      const value = Number(val);
      const s2Value = Number(s2);
      return val !== "" && 
             value >= 15 && 
             value <= 150 && 
             (!s2 || value + 56 !== s2Value);
    },
    
    /**
     * Validates S2 (handshake response junk data size)
     */
    S2: (val, s1) => {
      const value = Number(val);
      const s1Value = Number(s1);
      return val !== "" && 
             value >= 15 && 
             value <= 150 && 
             (!s1 || s1Value + 56 !== value);
    }
  }
};

/**
 * Updates the validation state of a DOM element
 * @param {HTMLElement} element - Element to update
 * @param {boolean} isValid - Whether the element's value is valid
 */
export const updateValidationState = (element, isValid) => {
  if (!element) return;
  
  element.classList.remove("is-invalid", "is-valid");
  element.classList.add(isValid ? "is-valid" : "is-invalid");
};

/**
 * Validates H-values (handshake message types)
 * @param {Array<number|string>} values - Array of H-values to validate
 * @returns {Object} - Validation result and unique values
 */
export const validateHValues = (values) => {
  // Filter valid H-values and convert to numbers
  const validValues = values
    .map(v => Number(v))
    .filter(v => !isNaN(v) && v >= 5 && v <= 2147483647);
  
  // Create set of unique values
  const uniqueHValues = new Set(validValues);
  
  // Check if we have exactly 4 unique valid values
  const isValid = values.length === 4 && uniqueHValues.size === 4;
  
  return {
    isValid,
    uniqueValues: uniqueHValues,
    errors: isValid ? [] : [
      uniqueHValues.size !== 4 && 'All H-values must be unique',
      values.some(v => v < 5 || v > 2147483647) && 'H-values must be between 5 and 2147483647'
    ].filter(Boolean)
  };
};

/**
 * Validates a complete WireGuard configuration
 * @param {Object} config - Configuration object to validate
 * @param {Array} existingConfigs - Array of existing configurations
 * @returns {Object} - Validation result with errors if any
 */
export const validateConfiguration = (config, existingConfigs) => {
  const errors = [];
  
  // Required fields
  const requiredFields = ['ConfigurationName', 'Address', 'ListenPort', 'PrivateKey'];
  for (const field of requiredFields) {
    if (!config[field]) {
      errors.push(`${field} is required`);
    }
  }
  
  // Field-specific validation
  if (config.ConfigurationName && !ValidationRules.configName(config.ConfigurationName, existingConfigs)) {
    errors.push('Invalid configuration name');
  }
  
  if (config.Address && !ValidationRules.address(config.Address)) {
    errors.push('Invalid CIDR address');
  }
  
  if (config.ListenPort && !ValidationRules.port(config.ListenPort)) {
    errors.push('Invalid port number');
  }
  
  // AmneziaWG specific validation
  if (config.Protocol === 'awg') {
    const awgFields = ['Jc', 'Jmin', 'Jmax', 'S1', 'S2'];
    for (const field of awgFields) {
      if (!ValidationRules.awgParams[field](config[field])) {
        errors.push(`Invalid ${field} value`);
      }
    }
    
    // Validate H-values
    const hValues = [config.H1, config.H2, config.H3, config.H4];
    const hValidation = validateHValues(hValues);
    if (!hValidation.isValid) {
      errors.push(...hValidation.errors);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Calculate available IPs from CIDR range
 * @param {string} cidr - CIDR address range
 * @returns {number} - Number of available IPs
 */
export const calculateAvailableIPs = (cidr) => {
  try {
    if (!ValidationRules.address(cidr)) return 0;
    
    const parsed = parse(cidr);
    return parsed.end - parsed.start;
  } catch {
    return 0;
  }
};