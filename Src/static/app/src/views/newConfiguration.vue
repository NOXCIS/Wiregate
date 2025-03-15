<script>
import { parse } from "cidr-tools";
import "@/utilities/wireguard.js";
import { WireguardConfigurationsStore } from "@/stores/WireguardConfigurationsStore.js";
import { fetchPost } from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import { 
  generateTorIPTables, 
  generateTorIPTablesTeardown, 
  generatePlainIPTables, 
  generatePlainIPTablesTeardown, 
  generateBlankIPTables 
} from "@/utilities/iptablesConfig.js";
import { parseInterface } from "@/utilities/parseConfigurationFile.js";
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js";

export default {
   name: "newConfiguration",
  components: { LocaleText },
  async setup(){
    const store = WireguardConfigurationsStore()
    const dashboardStore = DashboardConfigurationStore();
    
    return {store, dashboardStore}
  },
  data() {
    return {
      isAWGOpen: false,
      selectedField: null,
      torEnabled: false,
      isManualIPTables: false, // New flag for manual IPTables editing
      newConfiguration: {
        ConfigurationName: "",
        Address: "",
        ListenPort: "",
        PrivateKey: "",
        PublicKey: "",
        PresharedKey: "",
        iptablesEnabled: false,
        PreUp: "",
        PreDown: "",
        PostUp: "",
        PostDown: "",
        Jc: "",
        Jmin: "",
        Jmax: "",
        S1: "",
        S2: "",
        H1: "",
        H2: "",
        H3: "",
        H4: "",
        Protocol: "wg"
      },
      previousIPTables: {
        PreUp: "",
        PreDown: "",
        PostUp: "",
        PostDown: ""
      },
      hasUnsavedChanges: false,
      descriptions: {
        Jc: "Defines the number of junk packets to send before the handshake (1-128). Recommended range: 3-10.",
        Jmin: "Specifies the minimum size of the junk packet payload in bytes (0-1280).",
        Jmax: "Specifies the maximum size of the junk packet payload in bytes (0-1280). Jmin must be less than Jmax.",
        S1: "Defines how many bytes of junk data are placed before the actual WireGuard data in the handshake initiation (15-150).",
        S2: "Defines how many bytes of junk data are placed before the actual WireGuard data in the handshake response (15-150). S1 + 56 must not equal S2.",
        H1: "Custom type for Handshake Initiation. Must be unique and between 5 and 2147483647.",
        H2: "Custom type for Handshake Response. Must be unique and between 5 and 2147483647.",
        H3: "Custom type for another WireGuard message. Must be unique and between 5 and 2147483647.",
        H4: "Custom type for yet another WireGuard message. Must be unique and between 5 and 2147483647."
      },
      numberOfAvailableIPs: "0",
      error: false,
      errorMessage: "",
      success: false,
      loading: false
    };
  },
  created() {
    this.wireguardGenerateKeypair();
    this.generateRandomValues();
    
    // Only set default IPTables scripts for brand new configurations if not uploading a file
    if (!this.newConfiguration.PostUp && !this.newConfiguration.PreDown) {
      this.newConfiguration.PostUp = generatePlainIPTables(this.newConfiguration);
      this.newConfiguration.PreDown = generatePlainIPTablesTeardown(this.newConfiguration);
      this.newConfiguration.PreUp = generateBlankIPTables(this.newConfiguration);
      this.newConfiguration.PostDown = generateBlankIPTables(this.newConfiguration);
    }
  },
  methods: {
    wireguardGenerateKeypair() {
      const wg = window.wireguard.generateKeypair();
      this.newConfiguration.PrivateKey = wg.privateKey;
      this.newConfiguration.PublicKey = wg.publicKey;
      this.newConfiguration.PresharedKey = wg.presharedKey;
    },
    generateRandomValues() {
      this.newConfiguration.Jc = Math.floor(Math.random() * 8) + 3;
      this.newConfiguration.Jmin = Math.floor(Math.random() * 50);
      this.newConfiguration.Jmax = Math.floor(Math.random() * (1280 - this.newConfiguration.Jmin)) + this.newConfiguration.Jmin + 1;
      do {
        this.newConfiguration.S1 = Math.floor(Math.random() * 136) + 15;
      } while (this.newConfiguration.S1 + 56 === this.newConfiguration.S2);
      do {
        this.newConfiguration.S2 = Math.floor(Math.random() * 136) + 15;
      } while (this.newConfiguration.S1 + 56 === this.newConfiguration.S2);
      let hValues = new Set();
      while (hValues.size < 4) {
        hValues.add(Math.floor(Math.random() * (2147483647 - 5 + 1)) + 5);
      }
      [this.newConfiguration.H1, this.newConfiguration.H2, this.newConfiguration.H3, this.newConfiguration.H4] = [...hValues];
    },
    validateHValues() {
      let hValues = [
        this.newConfiguration.H1,
        this.newConfiguration.H2,
        this.newConfiguration.H3,
        this.newConfiguration.H4
      ];
      
      let uniqueHValues = new Set(hValues.filter((v) => v !== '' && v >= 5 && v <= 2147483647));
      let isValid = hValues.length === uniqueHValues.size && uniqueHValues.size === 4;

      hValues.forEach((value, index) => {
        const ele = document.querySelector(`#H${index + 1}`);
        if (!ele) return;

        ele.classList.remove("is-invalid", "is-valid");
        
        if (
          value === '' || 
          !isValid || 
          value < 5 || 
          value > 2147483647
        ) {
          ele.classList.add("is-invalid");
        } else {
          ele.classList.add("is-valid");
        }
      });
    },
    validateListenPort(event) {
      const value = event.target.value;
      const ele = event.target;
      ele.classList.remove("is-invalid", "is-valid");
      
      if (value === "" || value < 0 || value > 65353 || !Number.isInteger(+value)) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },

    // Toggle IPTables between Tor and plain
    toggleIPTables() {
      if (this.isManualIPTables) {
        this.dashboardStore.newMessage(
          "WireGate",
          "Manual IPTables scripts are enabled. Disable manual mode to use automated scripts.",
          "warning"
        );
        return;
      }

      // Store current scripts before toggling
      this.previousIPTables = {
        PreUp: this.newConfiguration.PreUp,
        PostDown: this.newConfiguration.PostDown,
        PostUp: this.newConfiguration.PostUp,
        PreDown: this.newConfiguration.PreDown
      };

      this.torEnabled = !this.torEnabled;
      this.updateIPTablesScripts();
      this.hasUnsavedChanges = true;
    },

    // Update IPTables scripts based on toggle
    updateIPTablesScripts() {
      // Store current scripts before updating
      const previousScripts = {
        PreUp: this.newConfiguration.PreUp,
        PostDown: this.newConfiguration.PostDown,
        PostUp: this.newConfiguration.PostUp,
        PreDown: this.newConfiguration.PreDown
      };

      if (this.torEnabled) {
        // Generate new Tor IPTables scripts
        this.newConfiguration.PostUp = generateTorIPTables(this.newConfiguration);
        this.newConfiguration.PreDown = generateTorIPTablesTeardown(this.newConfiguration);
        // Optionally, handle PreUp and PostDown if necessary
        this.newConfiguration.PreUp = generateBlankIPTables(this.newConfiguration);
        this.newConfiguration.PostDown = generateBlankIPTables(this.newConfiguration);
      } else {
        // Generate new plain IPTables scripts
        this.newConfiguration.PostUp = generatePlainIPTables(this.newConfiguration);
        this.newConfiguration.PreDown = generatePlainIPTablesTeardown(this.newConfiguration);
        // Optionally, handle PreUp and PostDown if necessary
        this.newConfiguration.PreUp = generateBlankIPTables(this.newConfiguration);
        this.newConfiguration.PostDown = generateBlankIPTables(this.newConfiguration);
      }

      // Check if scripts have actually changed
      if (
        previousScripts.PreUp !== this.newConfiguration.PreUp ||
        previousScripts.PostDown !== this.newConfiguration.PostDown ||
        previousScripts.PostUp !== this.newConfiguration.PostUp ||
        previousScripts.PreDown !== this.newConfiguration.PreDown
      ) {
        this.hasUnsavedChanges = true;
      }
    },

    openFileUpload(){
      document.querySelector("#fileUpload").click();
    },
    readFile(e) {
      const file = e.target.files[0];
      if (!file) return false;
      
      const reader = new FileReader();
      reader.onload = (evt) => {
        const fileContent = evt.target.result;
        const parsedInterface = parseInterface(fileContent);
        
        if (parsedInterface) {
          // Set basic configuration
          this.newConfiguration = {
            ...this.newConfiguration,
            ConfigurationName: file.name.replace('.conf', ''),
            Protocol: parsedInterface.Protocol || 'wg',
            
            // IPTables scripts - always set these regardless of content
            PreUp: parsedInterface.PreUp || '',
            PostUp: parsedInterface.PostUp || '',
            PreDown: parsedInterface.PreDown || '',
            PostDown: parsedInterface.PostDown || '',
            
            // Other fields
            Address: parsedInterface.Address || '',
            ListenPort: parsedInterface.ListenPort?.toString() || '',
            PrivateKey: parsedInterface.PrivateKey || '',
            PublicKey: parsedInterface.PublicKey || '',
            PresharedKey: parsedInterface.PresharedKey || ''
          };

          // Handle AmneziaWG specific parameters if present
          if (parsedInterface.Protocol === 'awg') {
            this.isAWGOpen = true;
            const awgParams = ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4'];
            awgParams.forEach(param => {
              this.newConfiguration[param] = parsedInterface[param] || '';
            });
          }

          // If any IPTables scripts exist, show them in the UI
          const hasIptablesContent = parsedInterface.PreUp || 
                                    parsedInterface.PostUp || 
                                    parsedInterface.PreDown || 
                                    parsedInterface.PostDown;

          if (hasIptablesContent) {
            this.$nextTick(() => {
              // Open the IPTables accordion
              const accordion = document.querySelector('#newConfigurationOptionalAccordionCollapse');
              if (accordion) {
                accordion.classList.add('show');
                
                const button = document.querySelector('[data-bs-target="#newConfigurationOptionalAccordionCollapse"]');
                if (button) {
                  button.classList.remove('collapsed');
                  button.setAttribute('aria-expanded', 'true');
                }

                // Select the first non-empty IPTables field
                ['PreUp', 'PostUp', 'PreDown', 'PostDown'].some(field => {
                  if (parsedInterface[field]) {
                    this.selectedField = field;
                    return true;
                  }
                  return false;
                });
              }
            });
          }

          // Reset iptablesEnabled to false since it's independent of uploaded configs
          this.torEnabled = false;

          // If IPTables scripts are provided via the file, enable manual IPTables editing
          if (hasIptablesContent) {
            this.isManualIPTables = true;
          } else {
            this.isManualIPTables = false;
          }

          // Validate all fields after setting them
          this.$nextTick(() => {
            // Validate standard fields
            ['ListenPort', 'Address', 'PrivateKey'].forEach(field => {
              const input = document.querySelector(`#${field}`);
              if (input) {
                input.dispatchEvent(new Event('input'));
              }
            });

            // Validate AmneziaWG fields if needed
            if (this.newConfiguration.Protocol === 'awg') {
              ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4'].forEach(field => {
                const input = document.querySelector(`#${field}`);
                if (input) {
                  input.dispatchEvent(new Event('input'));
                }
              });
              this.validateHValues();
            }

            // If manual IPTables are enabled, validate them
            if (this.isManualIPTables) {
              ['PreUp', 'PostUp', 'PreDown', 'PostDown'].forEach(field => {
                const input = document.querySelector(`#${field}`);
                if (input) {
                  input.dispatchEvent(new Event('input'));
                }
              });
            }
          });

          // Show success message
          this.dashboardStore.newMessage(
            "WireGate",
            `Configuration file uploaded successfully`,
            "success"
          );
        } else {
          this.dashboardStore.newMessage(
            "WireGate",
            "Failed to upload configuration file",
            "danger"
          );
        }
      };
      reader.readAsText(file);
    },
    validateParameters() {
      this.resetValidation();
      let isValid = true;

      // Validate Configuration Name
      const configNameElement = document.querySelector("#ConfigurationName");
      if (configNameElement) {
        if (!this.newConfiguration.ConfigurationName || 
            !/^[a-zA-Z0-9_=+.-]{1,15}$/.test(this.newConfiguration.ConfigurationName) ||
            this.store.Configurations.find((x) => x.Name === this.newConfiguration.ConfigurationName)) {
          configNameElement.classList.add("is-invalid");
          isValid = false;
        } else {
          configNameElement.classList.add("is-valid");
        }
      }

      // Validate Address
      const addressElement = document.querySelector("#Address");
      if (addressElement) {
        try {
          if (!this.newConfiguration.Address || 
              this.newConfiguration.Address.trim().split("/").filter((x) => x.length > 0).length !== 2) {
            throw new Error();
          }
          parse(this.newConfiguration.Address);
          addressElement.classList.add("is-valid");
        } catch (e) {
          addressElement.classList.add("is-invalid");
          isValid = false;
        }
      }

      // Validate Listen Port
      const portElement = document.querySelector("#ListenPort");
      if (portElement) {
        const port = this.newConfiguration.ListenPort;
        if (port === "" || port < 0 || port > 65353 || !Number.isInteger(+port)) {
          portElement.classList.add("is-invalid");
          isValid = false;
        } else {
          portElement.classList.add("is-valid");
        }
      }

      // Validate IPTables fields if manual editing is enabled
      if (this.isManualIPTables) {
        ['PreUp', 'PostUp', 'PreDown', 'PostDown'].forEach(field => {
          const element = document.querySelector(`#${field}`);
          if (element) {
            if (!this.newConfiguration[field].trim()) {
              element.classList.add("is-invalid");
              isValid = false;
            } else {
              element.classList.add("is-valid");
            }
          }
        });
      }

      return isValid;
    },
    resetValidation() {
      const fields = ['ConfigurationName', 'Address', 'ListenPort', 'PreUp', 'PostUp', 'PreDown', 'PostDown'];
      fields.forEach(field => {
        const element = document.querySelector(`#${field}`);
        if (element) {
          element.classList.remove('is-invalid', 'is-valid');
        }
      });
      this.error = false;
      this.errorMessage = "";
    },
    async saveNewConfiguration() {
      if (this.validateParameters() && this.goodToSubmit) {
        this.loading = true;
        const apiData = this.prepareApiData();
        
        // For debugging: Log apiData to ensure scripts are included
        console.log("API Data to be sent:", apiData);

        try {
          await fetchPost("/api/addConfiguration", apiData, async (res) => {
            if (res.status) {
              this.success = true;
              await this.store.getConfigurations();
              this.$router.push(`/configuration/${this.newConfiguration.ConfigurationName}/peers`);
            } else {
              this.error = true;
              this.errorMessage = res.message;
              
              // Handle specific field errors
              if (res.data) {
                const errorField = document.querySelector(`#${res.data}`);
                if (errorField) {
                  errorField.classList.remove("is-valid");
                  errorField.classList.add("is-invalid");
                  
                  // Reset validation state after error
                  this.$nextTick(() => {
                    this.loading = false;
                    
                    errorField.addEventListener('input', () => {
                      errorField.classList.remove('is-invalid');
                      this.error = false;
                      this.errorMessage = "";
                    }, { once: true });
                  });
                }
              }
            }
          });
        } catch (error) {
          this.error = true;
          this.errorMessage = "An error occurred while saving the configuration. Please try again.";
          this.loading = false;
        }
        
        if (!this.success) {
          this.loading = false;
        }
      }
    },

    isAWGParamValid(param) {
      const value = this.newConfiguration[param];
      if (!value && value !== 0) return false;
      
      switch (param) {
        case 'Jc':
          return value >= 1 && value <= 128 && Number.isInteger(+value);
        case 'Jmin':
          return value >= 0 && value <= 1280 && 
                 Number.isInteger(+value) && 
                 (this.newConfiguration.Jmax === '' || +value < +this.newConfiguration.Jmax);
        case 'Jmax':
          return value > 0 && value <= 1280 && 
                 Number.isInteger(+value) && 
                 (this.newConfiguration.Jmin === '' || +value > +this.newConfiguration.Jmin);
        case 'S1':
          return value >= 15 && value <= 150 && 
                 Number.isInteger(+value) && 
                 (this.newConfiguration.S2 === '' || +value + 56 !== +this.newConfiguration.S2);
        case 'S2':
          return value >= 15 && value <= 150 && 
                 Number.isInteger(+value) && 
                 (this.newConfiguration.S1 === '' || +this.newConfiguration.S1 + 56 !== +value);
        case 'H1':
        case 'H2':
        case 'H3':
        case 'H4':
          const hValues = [
            this.newConfiguration.H1,
            this.newConfiguration.H2, 
            this.newConfiguration.H3,
            this.newConfiguration.H4
          ].filter(v => v !== '' && v >= 5 && v <= 2147483647);
          return value >= 5 && value <= 2147483647 && 
                 Number.isInteger(+value) &&
                 new Set(hValues).size === hValues.length;
        default:
          return false;
      }
    },

    isAWGParamInvalid(param) {
      const value = this.newConfiguration[param];
      return value !== '' && !this.isAWGParamValid(param);
    },


    prepareApiData() {
      const {
        ConfigurationName,
        Address,
        ListenPort,
        PrivateKey,
        PublicKey,
        PresharedKey,
        PreUp,
        PreDown,
        PostUp,
        PostDown,
        Jc,
        Jmin,
        Jmax,
        S1,
        S2,
        H1,
        H2,
        H3,
        H4,
        Protocol
      } = this.newConfiguration;

      let scripts = {
        PreUp,
        PreDown,
        PostUp,
        PostDown
      };

      if (!this.isManualIPTables) {
        // Generate scripts only if not in manual mode
        scripts = this.torEnabled ? 
          {
            PreUp: generateBlankIPTables(this.newConfiguration),
            PreDown: generateTorIPTablesTeardown(this.newConfiguration),
            PostUp: generateTorIPTables(this.newConfiguration),
            PostDown: generateBlankIPTables(this.newConfiguration)
          } : 
          {
            PreUp: generateBlankIPTables(this.newConfiguration),
            PreDown: generatePlainIPTablesTeardown(this.newConfiguration),
            PostUp: generatePlainIPTables(this.newConfiguration),
            PostDown: generateBlankIPTables(this.newConfiguration)
          };
      }

      const apiData = {
        ConfigurationName,
        Address,
        ListenPort,
        PrivateKey,
        PublicKey,
        PresharedKey,
        PreUp: scripts.PreUp,          // Include generated or manual PreUp
        PreDown: scripts.PreDown,      // Include generated or manual PreDown
        PostUp: scripts.PostUp,        // Include generated or manual PostUp
        PostDown: scripts.PostDown,    // Always include PostDown
        Protocol,
      };

      if (Protocol === 'awg') {
        Object.assign(apiData, {
          Jc,
          Jmin,
          Jmax,
          S1,
          S2,
          H1,
          H2,
          H3,
          H4,
        });
      }

      // Log the API data for debugging
      console.log("Prepared API Data:", apiData);

      return apiData;
    },
  },
  computed: {
    // Configuration Name Validity
    isConfigNameValid() {
      const name = this.newConfiguration.ConfigurationName;
      const isValidFormat = /^[a-zA-Z0-9_=+.-]{1,15}$/.test(name);
      const isUnique = !this.store.Configurations.find(x => x.Name === name);
      return isValidFormat && isUnique;
    },
    isConfigNameInvalid() {
      return !this.isConfigNameValid;
    },

    // Listen Port Validity
    isListenPortValid() {
      const port = this.newConfiguration.ListenPort;
      return port !== "" && port >= 1 && port <= 65353 && Number.isInteger(+port);
    },
    isListenPortInvalid() {
      return !this.isListenPortValid;
    },

    // Address Validity
    isAddressValid() {
      const address = this.newConfiguration.Address;
      try {
        if (
          !address ||
          address.trim().split("/").filter(x => x.length > 0).length !== 2
        ) {
          return false;
        }
        parse(address); // Assuming 'parse' throws an error for invalid CIDR
        return true;
      } catch (e) {
        return false;
      }
    },
    isAddressInvalid() {
      return !this.isAddressValid;
    },
    
    goodToSubmit() {
      return (
        this.isConfigNameValid &&
        this.isListenPortValid &&
        this.isAddressValid &&
        // Add other validation checks as needed
        [...document.querySelectorAll("input[required]")]
          .every(input => !input.classList.contains("is-invalid"))
      );
    },
  },
  watch: {
    'newConfiguration.PreUp'(newVal, oldVal) {
      if (oldVal && newVal !== oldVal) {
        this.hasUnsavedChanges = true;
      }
    },
    'newConfiguration.PostDown'(newVal, oldVal) {
      if (oldVal && newVal !== oldVal) {
        this.hasUnsavedChanges = true;
      }
    },
    'newConfiguration.PostUp'(newVal, oldVal) {
      if (oldVal && newVal !== oldVal) {
        this.hasUnsavedChanges = true;
      }
    },
    'newConfiguration.PreDown'(newVal, oldVal) {
      if (oldVal && newVal !== oldVal) {
        this.hasUnsavedChanges = true;
      }
    },
      
    // ConfigurationName watcher
    'newConfiguration.ConfigurationName'(newVal) {
      // Existing validation logic
      let ele = document.querySelector("#ConfigurationName");
      if (!ele) return;
      ele.classList.remove("is-invalid", "is-valid");
      
      const isInvalid = !/^[a-zA-Z0-9_=+.-]{1,15}$/.test(newVal) || 
                        newVal.length === 0 || 
                        this.store.Configurations.find(x => x.Name === newVal);
      
      if (isInvalid) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
        // Always update IPTables scripts when name is valid and not in manual mode
        if (!this.isManualIPTables) {
          this.updateIPTablesScripts();
        }
      }
    },

    // Address watcher
    'newConfiguration.Address'(newVal) {
      const ele = document.querySelector("#Address");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      try {
        if (!newVal || 
            newVal.trim().split("/").filter((x) => x.length > 0).length !== 2) {
          throw new Error();
        }
        parse(newVal);
        this.numberOfAvailableIPs = "Calculating..."; // Optional: Update with actual count if needed
        ele.classList.add("is-valid");
        
        // Always update IPTables scripts when address is valid and not in manual mode
        if (!this.isManualIPTables) {
          this.updateIPTablesScripts();
        }
      } catch (e) {
        this.numberOfAvailableIPs = "0";
        ele.classList.add("is-invalid");
      }
    },

    // Protocol watcher
    'newConfiguration.Protocol'(newVal) {
      if (this.torEnabled && !this.isManualIPTables) {
        this.updateIPTablesScripts();
      }
    },

    // IPTables toggle watcher
    iptablesEnabled(newVal) {
      if (!this.isManualIPTables) {
        this.updateIPTablesScripts();
      }
    },

    // Deep watcher for newConfiguration
    newConfiguration: {
      deep: true,
      handler(newVal, oldVal) {
        // Check if any IPTables-relevant fields have changed
        const relevantFields = ['ConfigurationName', 'Address', 'Protocol'];
        const hasRelevantChanges = relevantFields.some(field => newVal[field] !== oldVal[field]);
        
        if (hasRelevantChanges && this.torEnabled && !this.isManualIPTables) {
          this.updateIPTablesScripts();
        }
      }
    },

    // ListenPort watcher
    "newConfiguration.ListenPort"(newVal) {
      const ele = document.querySelector("#ListenPort");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");

      if (newVal === "" || newVal < 0 || newVal > 65353 || !Number.isInteger(+newVal)) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },
    // PrivateKey watcher
    "newConfiguration.PrivateKey": {
      handler(newVal) {
        if (newVal && window.wireguard) {
          try {
            this.newConfiguration.PublicKey = window.wireguard.generatePublicKey(newVal);
          } catch (e) {
            console.error('Error generating public key:', e);
          }
        }
      }
    },

    // AmneziaWG parameters watchers
    "newConfiguration.Jc"(newVal) {
      const ele = document.querySelector("#Jc");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      if (newVal === "" || newVal < 1 || newVal > 128 || !Number.isInteger(+newVal)) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },
    "newConfiguration.Jmin"(newVal) {
      const ele = document.querySelector("#Jmin");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      const Jmax = this.newConfiguration.Jmax;
      if (
        newVal === "" ||
        newVal < 0 || 
        newVal > 1280 || 
        (Jmax !== "" && +newVal >= +Jmax)
      ) {
        ele.classList.add("is-invalid");
        isValid = false;
      } else {
        ele.classList.add("is-valid");
      }
    },
    "newConfiguration.Jmax"(newVal) {
      const ele = document.querySelector("#Jmax");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      const Jmin = this.newConfiguration.Jmin;
      if (
        newVal === "" ||
        newVal <= 0 || 
        newVal > 1280 || 
        (Jmin !== "" && +newVal <= +Jmin)
      ) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },
    "newConfiguration.S1"(newVal) {
      const ele = document.querySelector("#S1");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      const S2 = this.newConfiguration.S2;
      if (
        newVal === "" ||
        newVal < 15 || 
        newVal > 150 || 
        (S2 !== "" && +newVal + 56 === +S2)
      ) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },
    "newConfiguration.S2"(newVal) {
      const ele = document.querySelector("#S2");
      if (!ele) return;

      ele.classList.remove("is-invalid", "is-valid");
      const S1 = this.newConfiguration.S1;
      if (
        newVal === "" ||
        newVal < 15 || 
        newVal > 150 || 
        (S1 !== "" && +S1 + 56 === +newVal)
      ) {
        ele.classList.add("is-invalid");
      } else {
        ele.classList.add("is-valid");
      }
    },
    "newConfiguration.H1"(newVal) {
      this.validateHValues();
    },
    "newConfiguration.H2"(newVal) {
      this.validateHValues();
    },
    "newConfiguration.H3"(newVal) {
      this.validateHValues();
    },
    "newConfiguration.H4"(newVal) {
      this.validateHValues();
    },

    // Handle manual IPTables toggle
    handleManualIPTablesToggle() {
      if (this.isManualIPTables) {
        // User opts to manage IPTables scripts manually
        // Optionally, confirm with the user
        if (confirm("Enabling manual IPTables script management will prevent automatic script generation. Continue?")) {
          this.hasUnsavedChanges = true;
          // Optionally, preserve existing scripts or reset them
        } else {
          // Revert the toggle if the user cancels
          this.isManualIPTables = false;
        }
      } else {
        // User opts to use automated IPTables scripts
        // Generate scripts based on current toggle state
        this.updateIPTablesScripts();
      }
    },
  },
 
  mounted() {
    const fileUpload = document.querySelector("#fileUpload");
    fileUpload.addEventListener("change", this.readFile, false)
  }
};
</script>


<template>
  <div class="mt-md-5 mt-3 text-body">
    <div class="ms-sm-auto d-flex mb-4 gap-2 flex-column">
      
      <!-- Header Section -->
      <div class="mb-4 d-flex align-items-center gap-4">
        <RouterLink to="/" class="btn btn-dark btn-brand p-2 shadow" style="border-radius: 100%">
          <h2 class="mb-0" style="line-height: 0">
            <i class="bi bi-arrow-left-circle"></i>
          </h2>
        </RouterLink>
        <h2 class="flex-column">
          <LocaleText t="New Configuration"></LocaleText>
        </h2>
        <div class="d-flex gap-2 ms-auto">
          <button class="titleBtn py-2 text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle"
                  @click="openFileUpload()"
                  type="button" aria-expanded="false">
            <i class="bi bi-upload me-2"></i>
            <LocaleText t="Upload File"></LocaleText>
          </button>
          <input type="file" id="fileUpload" multiple class="d-none" accept=".conf" />
        </div>
      </div>

      

      <!-- Form -->
      <form class="text-body d-flex flex-column gap-3" @submit.prevent="saveNewConfiguration">
        <div class="card rounded-3 shadow">
          <div class="card-header">
            <LocaleText t="Protocol"></LocaleText>
          </div>
          <div class="card-body d-flex gap-2 protocolBtnGroup">
            <a
              @click="this.newConfiguration.Protocol = 'wg'"
              :class="{'opacity-30': this.newConfiguration.Protocol !== 'wg'}"
              class="btn btn-primary wireguardBg border-0" style="flex-basis: 100%"
            >
              <i class="bi bi-check-circle-fill me-2" v-if="this.newConfiguration.Protocol === 'wg'"></i>
              <i class="bi bi-circle me-2" v-else></i>
              <strong>
                WireGuard
              </strong>
            </a>
            <a
              @click="this.newConfiguration.Protocol = 'awg'"
              :class="{'opacity-30': this.newConfiguration.Protocol !== 'awg'}"
              class="btn btn-primary amneziawgBg border-0" style="flex-basis: 100%"
            >
              <i class="bi bi-check-circle-fill me-2" v-if="this.newConfiguration.Protocol === 'awg'"></i>
              <i class="bi bi-circle me-2" v-else></i>
              <strong>
                AmneziaWG
              </strong>
            </a>
            <a
              @click="toggleIPTables"
              :class="{
                'btn-success': torEnabled, 
                'btn-secondary': !torEnabled,
                'opacity-30': !torEnabled || isManualIPTables
              }"
              class="btn border-0 torBg d-flex align-items-center justify-content-center position-relative" 
              style="flex-basis: 100%"
              :disabled="isManualIPTables"
            >
              <i class="bi bi-check-circle-fill me-2" v-if="torEnabled"></i>
              <i class="bi bi-circle me-2" v-else></i>
              <strong class="d-flex tor-logo align-items-center">
              </strong>
            </a>
          </div>
        </div>

        <!-- Configuration Name -->
<div class="card rounded-3 shadow">
  <div class="card-header">
    <LocaleText t="Configuration Name"></LocaleText>
  </div>
  <div class="card-body">
    <input
      type="text"
      class="form-control"
      :class="{
        'is-invalid': isConfigNameInvalid,
        'is-valid': isConfigNameValid
      }"
      placeholder="ex. wg1"
      id="ConfigurationName"
      autocomplete="off"
      aria-label="Configuration Name"
      v-model="newConfiguration.ConfigurationName"
      :disabled="loading"
      required
    />
    <div class="invalid-feedback">
      <div v-if="error">{{ errorMessage }}</div>
      <div v-else>
        <LocaleText t="Configuration name is invalid. Possible reasons:"></LocaleText>
        <ul class="mb-0">
          <li>
            <LocaleText t="Configuration name already exists."></LocaleText>
          </li>
          <li>
            <LocaleText t="Configuration name can only contain 15 lower/uppercase alphabet, numbers, underscore, equal sign, plus sign, period, and hyphen."></LocaleText>
          </li>
        </ul>
      </div>
    </div>
  </div>
</div>


        <!-- Listen Port Section -->
<div class="card rounded-3 shadow">
  <div class="card-header">
    <LocaleText t="Listen Port"></LocaleText>
  </div>
  <div class="card-body">
    <input 
      type="number" 
      class="form-control"
      :class="{
        'is-invalid': isListenPortInvalid,
        'is-valid': isListenPortValid
      }"
      placeholder="0-65353" 
      id="ListenPort" 
      autocomplete="off"
      aria-label="Listen Port"
      v-model.number="newConfiguration.ListenPort"
      :disabled="loading"
      min="1"
      max="65353"
      @input="validateListenPort"
      required
    >
    <div class="invalid-feedback">
      <div v-if="error">{{ errorMessage }}</div>
      <div v-else>
        <LocaleText t="Invalid port"></LocaleText>
      </div>
    </div>
  </div>
</div>


        <!-- Private/Public Key Section -->
        <div class="card rounded-3 shadow">
          <div class="card-header">
            <LocaleText t="Private Key"></LocaleText> & <LocaleText t="Public Key"></LocaleText>
          </div>
          <div class="card-body" style="font-family: var(--bs-font-monospace)">
            <div class="mb-2">
              <label class="text-muted fw-bold mb-1" for="PrivateKey">
                <small><LocaleText t="Private Key"></LocaleText></small>
              </label>
              <div class="input-group">
                <input 
                  type="text" 
                  class="form-control" 
                  id="PrivateKey" 
                  autocomplete="off"
                  aria-label="Private Key"
                  v-model="newConfiguration.PrivateKey" 
                  :disabled="loading"
                >
                <button 
                  class="btn btn-outline-primary" 
                  type="button" 
                  title="Regenerate Private Key"
                  @click="wireguardGenerateKeypair"
                  :disabled="loading"
                >
                  <i class="bi bi-arrow-repeat"></i>
                </button>
              </div>
            </div>
            <div>
              <label class="text-muted fw-bold mb-1" for="PublicKey">
                <small><LocaleText t="Public Key"></LocaleText></small>
              </label>
              <input 
                type="text" 
                class="form-control" 
                id="PublicKey" 
                autocomplete="off"
                aria-label="Public Key"
                v-model="newConfiguration.PublicKey"
                disabled
              >
            </div>
          </div>
        </div>

        <!-- IP Address/CIDR -->
<div class="card rounded-3 shadow">
  <div class="card-header d-flex align-items-center">
    <LocaleText t="IP Address/CIDR"></LocaleText>
    <span class="badge rounded-pill text-bg-success ms-auto">
      {{ numberOfAvailableIPs }} Available IPs
    </span>
  </div>
  <div class="card-body">
    <input 
      type="text" 
      class="form-control" 
      :class="{
        'is-invalid': isAddressInvalid,
        'is-valid': isAddressValid
      }"
      placeholder="Ex: 10.0.0.1/24" 
      id="Address" 
      autocomplete="off"
      aria-label="IP Address/CIDR"
      v-model="newConfiguration.Address"
      :disabled="loading"
      required
    >
    <div class="invalid-feedback">
      <div v-if="error">{{ errorMessage }}</div>
      <div v-else>
        IP Address/CIDR is invalid
      </div>
    </div>
  </div>
</div>


        <!-- Optional Settings for AmneziaWG Parameters -->
        <div v-if="newConfiguration.Protocol === 'awg'">
          <div class="card shadow" :class="{'rounded-3': isAWGOpen, 'rounded-pill': !isAWGOpen}">
            <div 
              @click="isAWGOpen = !isAWGOpen" 
              class="card-header awg-header fw-bold d-flex justify-content-between align-items-center cursor-pointer"
              :class="{'rounded-3': !isAWGOpen}"
            >
              <LocaleText t="AmneziaWG Parameters"></LocaleText>
              <i :class="['bi', isAWGOpen ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
            </div>
            
            <div v-show="isAWGOpen" class="card-body">
              <div v-for="key in ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4']" :key="key" class="mb-3">
                <label :for="key" class="text-muted fw-bold mb-1">
                  <small>{{ key }}</small>
                </label>
                <div v-if="descriptions[key]" class="form-text text-muted">
                  <small>{{ descriptions[key] }}</small>
                </div>
                <input
                  type="number"
                  class="form-control"
                  :class="{'is-invalid': isAWGParamInvalid(key), 'is-valid': isAWGParamValid(key)}"
                  v-model="newConfiguration[key]"
                  :id="key"
                  :placeholder="key"
                  autocomplete="off"
                  :aria-label="key"
                />
                <div class="invalid-feedback">
                  <LocaleText :t="`Invalid value for ${key}`"></LocaleText>
                </div>
                <div class="valid-feedback">
                  <LocaleText :t="`Valid value for ${key}`"></LocaleText>
                </div>
              </div>
            </div>
          </div>
        </div>

        <hr>


        <!-- IpTables Editor -->
        <div class="accordion" id="newConfigurationOptionalAccordion">
          <div class="border-primary-subtle accordion-item">
            <h2 class="accordion-header">
              <button 
                class="accordion-button " 
                type="button"
                data-bs-toggle="collapse" 
                data-bs-target="#newConfigurationOptionalAccordionCollapse"
              >
                <LocaleText t="IPTables Settings"></LocaleText>
                
              </button>
              
            </h2>

            <div 
              id="newConfigurationOptionalAccordionCollapse"
              class="accordion-collapse " 
              data-bs-parent="#newConfigurationOptionalAccordion"
            >
              <div class="accordion-body">
                

                  <!-- Manual IPTables Toggle -->
                  <div class="mb-4">
                    <div class="alert p-2" :class="isManualIPTables ? 'alert-warning' : 'alert-secondary'">
                      <div class="form-check form-switch d-flex align-items-center gap-3">
                        <input
                          class="form-check-input me-2"
                          type="checkbox" 
                          role="switch"
                          id="manualIPTablesToggle"
                          v-model="isManualIPTables"
                          @change="handleManualIPTablesToggle"
                        >
                        <label class="form-check-label mb-0" for="manualIPTablesToggle">
                          <LocaleText t="Manual Edit Mode" v-if="isManualIPTables"></LocaleText>
                          <LocaleText t="Enable Manual IPTables Scripts Editing" v-else></LocaleText>
                        </label>
                        <i class="bi ms-2" :class="isManualIPTables ? 'bi-exclamation-triangle-fill' : 'bi-exclamation-triangle-fill'"></i>
                      </div>
                    </div>
                  </div>

                <!-- Controls Section -->
                <div class="d-flex flex-column gap-3 mb-4">
                  <!-- Script Type Buttons -->
                  <div class="d-flex gap-2 flex-wrap">
                    <a 
                      v-for="field in ['PreUp', 'PreDown', 'PostUp', 'PostDown']"
                      :key="field"
                      class="btn bg-primary-subtle border-primary-subtle"
                      :class="selectedField === field ? 'btn-primary' : 'text-muted btn-outline-secondary'"
                      @click.prevent="selectedField = field"
                      href="#"
                      role="button"
                    >
                      {{ field }}
                    </a> 
                  </div>

                  

                  <!-- Unsaved Changes Badge -->
                  <div v-if="hasUnsavedChanges" class="d-flex justify-content-end">
                    <span class="badge bg-warning">
                      <i class="bi bi-exclamation-triangle me-1"></i>
                      Unsaved Changes
                    </span>
                  </div>
                </div>

                <!-- Editor Section -->
                <div v-if="selectedField" class="card rounded-3 shadow">
                  <div class="card-header d-flex align-items-center justify-content-between">
                    <span>{{ selectedField }}</span>
                    <button
                      class="btn btn-sm btn-warning"
                      @click.prevent="selectedField = null"
                    >
                      <i class="bi bi-x-lg"></i>
                    </button>
                  </div>
                  <div class="script-box p-0 text-primary-emphasis">
                    <textarea
                      :id="selectedField.toLowerCase()"
                      v-model="newConfiguration[selectedField]"
                      class="form-control script-box-active border-0 form-control-sm font-monospace resizable-textarea"
                      :placeholder="`Enter ${selectedField} commands...`"
                      rows="12"
                      spellcheck="false"
                      :disabled="loading"
                    ></textarea>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <button class="btn btn-dark btn-brand rounded-3 px-3 py-2 shadow ms-auto"
                :disabled="!this.goodToSubmit || this.loading || this.success">
          <span v-if="this.success" class="d-flex w-100">
            <LocaleText t="Success"></LocaleText>!
             <i class="bi bi-check-circle-fill ms-2"></i>
          </span>
          <span v-else-if="!this.loading" class="d-flex w-100">
            <i class="bi bi-save-fill me-2"></i>
            <LocaleText t="Save"></LocaleText>
          </span>
          <span v-else class="d-flex w-100 align-items-center">
            <LocaleText t="Saving..."></LocaleText>
            <span class="ms-2 spinner-border spinner-border-sm" role="status">
            </span>
          </span>
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.resizable-textarea {
  resize: vertical;
  overflow-y: auto;
  overflow-x: auto;
  min-height: 150px;
  max-height: 500px;
  width: 100%;
  border-radius: 0 0 0.5rem 0.5rem;
}

/* Scrollbar styling */
.resizable-textarea::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.resizable-textarea::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.resizable-textarea::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.resizable-textarea::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
