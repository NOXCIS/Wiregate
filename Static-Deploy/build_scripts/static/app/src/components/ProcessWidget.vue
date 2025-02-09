<script setup>
  import { onBeforeUnmount, onMounted, ref, computed } from "vue";
  import { fetchGet } from "@/utilities/fetch.js";
  import LocaleText from "@/components/text/localeText.vue";
  import Process from "@/components/systemStatusComponents/process.vue";
  
  const data = ref(undefined);
  let interval = null;
  
  const highlightKeywords = [
    'tor',
    'snowflake',
    'webtunnel',
    'obfs4'
  ];
  
  const isHighlightedProcess = (processName) => {
    return highlightKeywords.some(keyword => processName.includes(keyword));
  };
  
  const sortedProcesses = computed(() => {
    if (!data.value || !data.value.process) return [];
    return data.value.process.cpu_top_10
      .slice(0, 8)
      .sort((a, b) => {
        const aHighlighted = isHighlightedProcess(a.name);
        const bHighlighted = isHighlightedProcess(b.name);
        if (aHighlighted && !bHighlighted) return -1;
        if (!aHighlighted && bHighlighted) return 1;
        return b.cpu_percent - a.cpu_percent;
      });
  });
  
  const getData = () => {
    fetchGet("/api/systemStatus", {}, (res) => {
      data.value = res.data;
    });
  };
  
  onMounted(() => {
    getData();
    interval = setInterval(() => {
      getData();
    }, 5000);
  });
  
  onBeforeUnmount(() => {
    clearInterval(interval);
  });
</script>

<template>
    
        <div class="card-body">
          <div class="row">
            <div class="col-sm-12 d-flex flex-column gap-3">
              <div class="d-flex align-items-center">
                <h3 class="text-muted mb-0">
                  <i class="bi bi-cpu-fill me-2"></i>
                  <LocaleText t="CPU"></LocaleText>
                </h3>
                <h3 class="ms-auto text-muted mb-0">
                  <span v-if="data">
                    {{ data.cpu.cpu_percent }}%
                  </span>
                  <span v-else class="spinner-border"></span>
                </h3>
              </div>
              <div class="progress" role="progressbar" style="height: 10px">
                <div class="progress-bar" :style="{width: `${data?.cpu.cpu_percent}%` }"></div>
              </div>
              <h5 class="mb-0 text-body">Processes</h5>
              <div class="position-relative" style="height: 200px; overflow-y: auto">
                <TransitionGroup name="process" tag="div" class="text-muted process-container">
                  <Process 
                    v-for="p in sortedProcesses"
                    :key="p.pid"
                    :cpu="true"
                    :process="p"
                    :class="{'text-danger': isHighlightedProcess(p.name)}"
                  ></Process>
                </TransitionGroup>
              </div>
            </div>
          </div>
        </div>
    
  </template>
  

  
  <style scoped>
  .process-widget {
    margin-bottom: 20px;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 5px;
  }
  
  .title {
    height: 18px;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }
  
  .process-list {
    position: relative;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .process-item {
    transition: all 0.5s ease-in-out;
  }
  

  
  .process-enter-active, .process-leave-active {
    transition: all 0.5s ease-in-out;
  }
  
  .process-enter-from, .process-leave-to {
    opacity: 0;
    transform: translateY(20px);
  }
  </style>