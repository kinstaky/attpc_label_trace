<template>
  <section class="label-panel" v-if="trace">
    <header class="label-header">
      <div>
        <p class="eyebrow">Event {{ trace.eventId }} · Trace {{ trace.traceId }}</p>
        <h1>{{ currentLabelText }}</h1>
      </div>
      <div class="label-legend">
        <span>Left / h: normal</span>
        <span>Right / l: strange</span>
      </div>
    </header>

    <TracePlot :trace="trace" />

    <div class="trace-meta">
      <div class="meta-card">
        <span class="meta-title">Trace key</span>
        <strong>{{ trace.eventId }} / {{ trace.traceId }}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-title">Mode</span>
        <strong>{{ modeLabel }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import TracePlot from "../components/TracePlot.vue";

const props = defineProps({
  trace: { type: Object, required: true },
  currentLabelText: { type: String, required: true },
  mode: { type: String, required: true },
});

const modeLabel = computed(() => {
  if (props.mode === "await_normal_peak") {
    return "Waiting for normal peak selection";
  }
  if (props.mode === "await_strange_choice") {
    return "Waiting for strange label selection";
  }
  return "Browse";
});
</script>
