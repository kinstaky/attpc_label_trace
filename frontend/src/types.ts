export interface SessionPayload {
  mode: "label" | "review";
  run: number | null;
  source?: "label_set" | "filter_file" | null;
  family?: "normal" | "strange" | null;
  label?: string | null;
  filterFile?: string | null;
}

export interface StrangeLabel {
  name: string;
  shortcutKey: string;
}

export interface NormalSummaryItem {
  bucket: number;
  title: string;
  count: number;
}

export interface StrangeSummaryItem {
  name: string;
  shortcutKey?: string;
  count: number;
}

export interface ReviewProgress {
  current: number;
  total: number;
}

export interface CurrentLabel {
  family: "normal" | "strange";
  label: string;
}

export interface TracePayload {
  run?: number;
  eventId: number;
  traceId: number;
  raw: number[];
  trace: number[];
  transformed: number[];
  currentLabel: CurrentLabel | null;
  reviewProgress: ReviewProgress | null;
}

export interface FilterFileItem {
  name: string;
}

export interface HistogramAvailabilityEntry {
  all: boolean;
  labeled: boolean;
  filtered: boolean;
}

export interface BootstrapPayload {
  appType: "merged";
  workspace: string;
  tracePath: string;
  databaseFile: string;
  runs: number[];
  filterFiles: FilterFileItem[];
  histogramAvailability: Record<
    string,
    Record<"cdf" | "amplitude", HistogramAvailabilityEntry>
  >;
  normalSummary: NormalSummaryItem[];
  strangeSummary: StrangeSummaryItem[];
  strangeLabels: StrangeLabel[];
  session: SessionPayload;
}

export interface HistogramSeries {
  labelKey: string;
  title: string;
  traceCount: number | null;
  histogram: number[] | number[][];
}

export interface HistogramPayload {
  metric: "cdf" | "amplitude";
  mode: "all" | "labeled" | "filtered";
  run: number;
  filterFile?: string | null;
  veto?: boolean;
  thresholds?: number[];
  valueBinCount?: number;
  binCount?: number;
  series: HistogramSeries[];
}

export interface HistogramJobProgress {
  current: number;
  total: number;
  percent: number;
  unit: string;
  message: string;
}

export interface HistogramJobCreateResponse {
  jobId: string;
}

export interface HistogramJobProgressMessage extends HistogramJobProgress {
  type: "progress";
}

export interface HistogramJobCompleteMessage {
  type: "complete";
  payload: HistogramPayload;
}

export interface HistogramJobErrorMessage {
  type: "error";
  detail: string;
}

export type HistogramJobMessage =
  | HistogramJobProgressMessage
  | HistogramJobCompleteMessage
  | HistogramJobErrorMessage;

export interface LabelAssignResponse {
  labeledCount?: number;
  normalSummary: NormalSummaryItem[];
  strangeSummary: StrangeSummaryItem[];
  currentLabel: CurrentLabel;
}

export interface SessionResponse {
  session: SessionPayload;
  trace?: TracePayload | null;
  traceCount?: number;
}
