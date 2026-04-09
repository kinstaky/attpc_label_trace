import { computed, reactive } from "vue";

import { getHistogram } from "../api";
import { useShellStore } from "./shell";
import type { HistogramPayload, HistogramSeries } from "../types";

const DEFAULT_CDF_PROJECTION_BIN = 60;
const LABEL_ORDER_SUFFIX = ":labeled";

type HistogramMetric = "cdf" | "amplitude";
type HistogramMode = "all" | "labeled" | "filtered";
type ScaleMode = "linear" | "log";
type CdfRenderMode = "2d" | "projection";

interface HistogramState {
  selectedRun: number | null;
  selectedMetric: HistogramMetric;
  selectedMode: HistogramMode;
  selectedHistogramFilter: string;
  histogram: HistogramPayload | null;
  cdfScaleMode: ScaleMode;
  amplitudeScaleMode: ScaleMode;
  cdfRenderMode: CdfRenderMode;
  cdfProjectionBin: number;
  loading: boolean;
  error: string;
}

const state = reactive<HistogramState>({
  selectedRun: null,
  selectedMetric: "cdf",
  selectedMode: "all",
  selectedHistogramFilter: "",
  histogram: null,
  cdfScaleMode: "linear",
  amplitudeScaleMode: "linear",
  cdfRenderMode: "2d",
  cdfProjectionBin: DEFAULT_CDF_PROJECTION_BIN,
  loading: false,
  error: "",
});

const labeledSeriesOrder = reactive<Record<string, string[]>>({});

function clearTransientUi(): void {
  state.error = "";
}

function currentSeriesOrderKey(): string | null {
  if (state.selectedMode !== "labeled") {
    return null;
  }
  return `${state.selectedMetric}${LABEL_ORDER_SUFFIX}`;
}

function syncCurrentSeriesOrder(): void {
  const orderKey = currentSeriesOrderKey();
  const series = state.histogram?.series || [];
  if (!orderKey || !series.length) {
    return;
  }

  const presentKeys = series.map((item) => item.labelKey);
  const existingOrder = labeledSeriesOrder[orderKey] || [];
  const nextOrder = [
    ...existingOrder.filter((key) => presentKeys.includes(key)),
    ...presentKeys.filter((key) => !existingOrder.includes(key)),
  ];

  labeledSeriesOrder[orderKey] = nextOrder;
}

function ensureInitialized(): void {
  const shell = useShellStore();
  if (state.selectedRun === null) {
    state.selectedRun = shell.state.selectedRun;
  }
  if (!state.selectedHistogramFilter) {
    state.selectedHistogramFilter =
      shell.state.bootstrap?.filterFiles?.[0]?.name || "";
  }
}

function getAvailability() {
  const shell = useShellStore();
  if (state.selectedRun === null || !shell.state.bootstrap) {
    return null;
  }
  return shell.state.bootstrap.histogramAvailability?.[String(state.selectedRun)] || null;
}

function ensureModeAvailability(): void {
  const availability = getAvailability();
  if (!availability) {
    return;
  }
  const metricAvailability = availability?.[state.selectedMetric] || {};
  if (!metricAvailability?.[state.selectedMode]) {
    state.selectedMode =
      (["all", "labeled", "filtered"] as HistogramMode[]).find(
        (mode) => metricAvailability?.[mode],
      ) || "all";
  }
}

async function loadHistogram(): Promise<void> {
  ensureInitialized();
  if (state.selectedRun === null) {
    state.histogram = null;
    return;
  }
  state.loading = true;
  clearTransientUi();
  ensureModeAvailability();
  try {
    state.histogram = await getHistogram(
      state.selectedMetric,
      state.selectedMode,
      state.selectedRun,
      state.selectedMode === "filtered" ? state.selectedHistogramFilter : "",
    );
    syncCurrentSeriesOrder();
  } catch (error) {
    state.histogram = null;
    state.error = error instanceof Error ? error.message : String(error);
  } finally {
    state.loading = false;
  }
}

async function init(): Promise<void> {
  ensureInitialized();
  await loadHistogram();
}

async function setSelectedRun(run: number | string | null): Promise<void> {
  const shell = useShellStore();
  shell.setSelectedRun(run);
  state.selectedRun = run === null ? null : Number(run);
  await loadHistogram();
}

async function setSelectedMetric(metric: HistogramMetric): Promise<void> {
  state.selectedMetric = metric;
  await loadHistogram();
}

async function setSelectedMode(mode: HistogramMode): Promise<void> {
  state.selectedMode = mode;
  if (mode === "filtered" && !state.selectedHistogramFilter) {
    const shell = useShellStore();
    state.selectedHistogramFilter =
      shell.state.bootstrap?.filterFiles?.[0]?.name || "";
  }
  await loadHistogram();
}

async function setSelectedHistogramFilter(name: string): Promise<void> {
  state.selectedHistogramFilter = name;
  await loadHistogram();
}

function setScaleMode(mode: ScaleMode): void {
  if (mode !== "linear" && mode !== "log") {
    return;
  }
  if (state.selectedMetric === "cdf") {
    state.cdfScaleMode = mode;
    return;
  }
  state.amplitudeScaleMode = mode;
}

function setCdfRenderMode(mode: CdfRenderMode): void {
  if (mode !== "2d" && mode !== "projection") {
    return;
  }
  state.cdfRenderMode = mode;
}

function setCdfProjectionBin(value: number | string): void {
  const parsed = Number.parseInt(String(value), 10);
  if (Number.isNaN(parsed)) {
    return;
  }
  state.cdfProjectionBin = Math.min(150, Math.max(1, parsed));
}

function reorderCurrentSeries(sourceKey: string, targetKey: string): void {
  const orderKey = currentSeriesOrderKey();
  if (!orderKey || sourceKey === targetKey) {
    return;
  }

  syncCurrentSeriesOrder();
  const currentOrder = [...(labeledSeriesOrder[orderKey] || [])];
  const sourceIndex = currentOrder.indexOf(sourceKey);
  const targetIndex = currentOrder.indexOf(targetKey);

  if (sourceIndex < 0 || targetIndex < 0) {
    return;
  }

  const [movedKey] = currentOrder.splice(sourceIndex, 1);
  currentOrder.splice(targetIndex, 0, movedKey);
  labeledSeriesOrder[orderKey] = currentOrder;
}

const scaleMode = computed<ScaleMode>(() =>
  state.selectedMetric === "cdf" ? state.cdfScaleMode : state.amplitudeScaleMode,
);

const orderedSeries = computed<HistogramSeries[]>(() => {
  const series = state.histogram?.series || [];
  const orderKey = currentSeriesOrderKey();
  if (!orderKey || series.length <= 1) {
    return series;
  }

  const order = labeledSeriesOrder[orderKey] || [];
  const positions = new Map(order.map((key, index) => [key, index]));
  return [...series].sort(
    (left, right) =>
      (positions.get(left.labelKey) ?? Number.MAX_SAFE_INTEGER) -
      (positions.get(right.labelKey) ?? Number.MAX_SAFE_INTEGER),
  );
});

export function useHistogramStore() {
  return {
    state,
    scaleMode,
    orderedSeries,
    init,
    getAvailability,
    loadHistogram,
    setSelectedRun,
    setSelectedMetric,
    setSelectedMode,
    setSelectedHistogramFilter,
    setScaleMode,
    setCdfRenderMode,
    setCdfProjectionBin,
    reorderCurrentSeries,
  };
}
