<template>
  <section class="label-panel" v-if="trace">
    <header class="label-header">
      <div>
        <p class="eyebrow">Event {{ trace.eventId }} · Trace {{ trace.traceId }}</p>
        <h1>{{ currentLabelText }}</h1>
      </div>
      <div class="label-header-actions">
        <div class="label-toolbar">
          <button
            type="button"
            class="visual-mode-switch"
            :class="{ analysis: visualMode === 'analysis' }"
            :disabled="!canToggleVisualMode"
            :aria-pressed="visualMode === 'analysis'"
            @click="emit('set-visual-mode', visualMode === 'raw' ? 'analysis' : 'raw')"
          >
            <span class="visual-mode-thumb"></span>
            <span class="visual-mode-option visual-mode-option--raw">Raw</span>
            <span class="visual-mode-option visual-mode-option--analysis">Analysis</span>
          </button>
          <div class="label-legend">
            <span>Left / h: normal</span>
            <span>Right / l: strange</span>
          </div>
        </div>
        <span class="visual-mode-hint">
          {{ canToggleVisualMode ? "Press F to toggle in browse mode." : "Available in browse mode." }}
        </span>
      </div>
    </header>

    <TracePlot :trace="trace" :visual-mode="visualMode" />

    <div class="trace-meta">
      <div class="meta-card">
        <span class="meta-title">Trace key</span>
        <strong>{{ trace.eventId }} / {{ trace.traceId }}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-title">Input mode</span>
        <strong>{{ modeLabel }}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-title">Session</span>
        <strong>{{ sessionLabel }}</strong>
      </div>
      <div class="meta-card" v-if="trace.reviewProgress">
        <span class="meta-title">Review progress</span>
        <strong>{{ trace.reviewProgress.current }} / {{ trace.reviewProgress.total }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import TracePlot from "../components/TracePlot.vue";

const emit = defineEmits(["set-visual-mode"]);

const props = defineProps({
  trace: { type: Object, required: true },
  currentLabelText: { type: String, required: true },
  mode: { type: String, required: true },
  visualMode: { type: String, required: true },
  sessionMode: { type: String, required: true },
  reviewFilter: { type: Object, default: null },
  canToggleVisualMode: { type: Boolean, default: false },
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

const sessionLabel = computed(() => {
  if (props.sessionMode !== "review") {
    return "Label mode";
  }
  if (!props.reviewFilter?.label) {
    return `Review ${props.reviewFilter?.family || ""} labels`.trim();
  }
  if (props.reviewFilter.family === "normal") {
    if (props.reviewFilter.label === "4+") {
      return "Review 4+ peaks";
    }
    return `Review ${props.reviewFilter.label === "9" ? "9+ peaks" : `${props.reviewFilter.label} peak${props.reviewFilter.label === "1" ? "" : "s"}`}`;
  }
  return `Review strange: ${props.reviewFilter.label}`;
});
</script>
