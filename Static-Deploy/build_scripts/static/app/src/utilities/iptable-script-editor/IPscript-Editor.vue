<template>
    <div>
      <form @submit.prevent="emitRules">
        <div v-for="(rule, index) in iptableRules" :key="index" class="rule-entry">
          <label :for="`field-${index}`">Field:</label>
          <input
            :id="`field-${index}`"
            v-model="iptableRules[index].field"
            placeholder="Enter field value"
            class="input-field"
          />
  
          <label :for="`value-${index}`">Value:</label>
          <input
            :id="`value-${index}`"
            v-model="iptableRules[index].value"
            placeholder="Enter value"
            class="input-field"
          />
  
          <button type="button" @click="removeRule(index)" class="remove-button">
            Remove
          </button>
        </div>
  
        <button type="button" @click="addRule" class="add-button">
          Add Rule
        </button>
  
        <button :disabled="!isDirty" type="submit" class="save-button">
          Save Rules
        </button>
      </form>
    </div>
  </template>
  
  <script>
  export default {
    props: {
      value: Array, // Expecting a v-model binding to handle rules as JSON
    },
    data() {
      return {
        iptableRules: [...this.value], // Initialize with the prop value
        originalRules: [...this.value], // Keep a copy of the initial state
        isDirty: false,
      };
    },
    watch: {
      value: {
        immediate: true,
        handler(newValue) {
          this.iptableRules = [...newValue];
          this.originalRules = [...newValue];
          this.checkDirty();
        },
      },
    },
    methods: {
      checkDirty() {
        this.isDirty = JSON.stringify(this.iptableRules) !== JSON.stringify(this.originalRules);
      },
      addRule() {
        this.iptableRules.push({ field: "", value: "" });
        this.checkDirty();
      },
      removeRule(index) {
        this.iptableRules.splice(index, 1);
        this.checkDirty();
      },
      emitRules() {
        this.$emit("input", this.iptableRules); // Emit updated rules for v-model
        this.originalRules = [...this.iptableRules]; // Reset original rules
        this.isDirty = false;
      },
    },
  };
  </script>
  
  <style scoped>
  .rule-entry {
    margin-bottom: 1rem;
    display: flex;
    gap: 1rem;
    align-items: center;
  }
  
  .input-field {
    padding: 0.5rem;
    font-size: 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
  }
  
  .add-button,
  .remove-button,
  .save-button {
    padding: 0.5rem 1rem;
    margin: 0.5rem 0;
    font-size: 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  
  .add-button {
    background-color: #4caf50;
    color: white;
  }
  
  .remove-button {
    background-color: #f44336;
    color: white;
  }
  
  .save-button {
    background-color: #008cba;
    color: white;
  }
  
  .save-button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
  </style>
  