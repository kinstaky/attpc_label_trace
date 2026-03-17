<template>
  <div ref="root" class="trace-plot"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  trace: { type: Object, default: null },
});

const root = ref(null);

function renderPlot() {
  if (!root.value || !props.trace) {
    return;
  }
  Plotly.react(
    root.value,
    [
      {
        type: "scatter",
        mode: "lines",
        x: props.trace.trace.map((_, index) => index),
        y: props.trace.trace,
        line: {
          color: "#174f40",
          width: 2,
        },
      },
    ],
    {
      margin: { t: 24, r: 24, b: 48, l: 56 },
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

onMounted(renderPlot);
watch(() => props.trace, renderPlot, { deep: true });

onBeforeUnmount(() => {
  if (root.value) {
    Plotly.purge(root.value);
  }
});
</script>
