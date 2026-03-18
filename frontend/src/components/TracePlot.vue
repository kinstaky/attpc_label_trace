<template>
  <div class="trace-plot-stack">
    <div ref="primaryRoot" class="trace-plot"></div>
    <div
      v-if="visualMode === 'analysis'"
      ref="secondaryRoot"
      class="trace-plot trace-plot--secondary"
    ></div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  trace: { type: Object, default: null },
  visualMode: { type: String, default: "raw" },
});

const primaryRoot = ref(null);
const secondaryRoot = ref(null);

function sampleIndices(values) {
  return values.map((_, index) => index);
}

function renderRawPlot() {
  if (!primaryRoot.value || !props.trace) {
    return;
  }
  Plotly.react(
    primaryRoot.value,
    [
      {
        type: "scatter",
        mode: "lines",
        x: sampleIndices(props.trace.raw),
        y: props.trace.raw,
        line: {
          color: "#174f40",
          width: 2,
        },
        name: "Raw trace",
      },
    ],
    {
      title: { text: "Raw Trace", x: 0.02, xanchor: "left" },
      margin: { t: 48, r: 24, b: 48, l: 56 },
      paper_bgcolor: "#fffdf8",
      plot_bgcolor: "#fffdf8",
      font: {
        family: "ui-sans-serif, system-ui, sans-serif",
        color: "#222",
      },
      xaxis: {
        title: "Sample",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
      yaxis: {
        title: "Amplitude",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
      showlegend: false,
    },
    {
      displayModeBar: false,
      responsive: true,
    },
  );
}

function renderAnalysisPlots() {
  if (!primaryRoot.value || !secondaryRoot.value || !props.trace) {
    return;
  }

  Plotly.react(
    primaryRoot.value,
    [
      {
        type: "scatter",
        mode: "lines",
        x: sampleIndices(props.trace.raw),
        y: props.trace.raw,
        line: {
          color: "#b46b2f",
          width: 1.8,
        },
        name: "Raw trace",
      },
      {
        type: "scatter",
        mode: "lines",
        x: sampleIndices(props.trace.trace),
        y: props.trace.trace,
        line: {
          color: "#174f40",
          width: 2.2,
        },
        name: "Baseline removed",
      },
    ],
    {
      title: { text: "Time Domain", x: 0.02, xanchor: "left" },
      margin: { t: 48, r: 24, b: 48, l: 56 },
      paper_bgcolor: "#fffdf8",
      plot_bgcolor: "#fffdf8",
      font: {
        family: "ui-sans-serif, system-ui, sans-serif",
        color: "#222",
      },
      legend: {
        orientation: "h",
        x: 1,
        xanchor: "right",
        y: 1.16,
      },
      xaxis: {
        title: "Sample",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
      yaxis: {
        title: "Amplitude",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
    },
    {
      displayModeBar: false,
      responsive: true,
    },
  );

  Plotly.react(
    secondaryRoot.value,
    [
      {
        type: "scatter",
        mode: "lines",
        x: sampleIndices(props.trace.transformed),
        y: props.trace.transformed,
        line: {
          color: "#3b5ba9",
          width: 2,
        },
        fill: "tozeroy",
        fillcolor: "rgba(59, 91, 169, 0.16)",
        name: "Frequency distribution",
      },
    ],
    {
      title: { text: "Frequency Distribution", x: 0.02, xanchor: "left" },
      margin: { t: 48, r: 24, b: 48, l: 56 },
      paper_bgcolor: "#fffdf8",
      plot_bgcolor: "#fffdf8",
      font: {
        family: "ui-sans-serif, system-ui, sans-serif",
        color: "#222",
      },
      xaxis: {
        title: "Frequency bin",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
      yaxis: {
        title: "Magnitude",
        zeroline: false,
        gridcolor: "#e7dfcf",
      },
      showlegend: false,
    },
    {
      displayModeBar: false,
      responsive: true,
    },
  );
}

async function renderPlots() {
  if (!props.trace || !primaryRoot.value) {
    return;
  }

  await nextTick();

  if (props.visualMode === "analysis") {
    renderAnalysisPlots();
    return;
  }

  renderRawPlot();
  if (secondaryRoot.value) {
    Plotly.purge(secondaryRoot.value);
  }
}

onMounted(() => {
  void renderPlots();
});
watch(() => props.trace, () => {
  void renderPlots();
}, { deep: true });
watch(() => props.visualMode, () => {
  void renderPlots();
});

onBeforeUnmount(() => {
  if (primaryRoot.value) {
    Plotly.purge(primaryRoot.value);
  }
  if (secondaryRoot.value) {
    Plotly.purge(secondaryRoot.value);
  }
});
</script>
