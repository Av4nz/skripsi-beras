export interface TimeSeriesPoint {
  date: string;
  value: number;
  type: string; // "actual" | "forecast"
}

export interface DecompositionComponent {
  name: string;
  label: string;
  contribution: number;
}

export interface PredictionDecomposition {
  trend: number;
  components: DecompositionComponent[];
}

export interface StepDetail {
  step: number;
  date: string;
  yhat: number;
  residual: number;
  final_prediction: number;
  features_used: Record<string, number>;
  decomposition?: PredictionDecomposition | null;
}

// ---------------------------------------------------------------------------
// API "Beras": per jenis beras, tanpa masukan faktor eksternal
// ---------------------------------------------------------------------------
export type JenisBeras = string;

export interface HargaJenisPoint {
  date: string;
  price: number;
}

export interface RiceStep {
  step: number;
  date: string;
  hybrid: number;
  prophet: number;
  residual: number;
  naive: number;
  arima: number;
  decomposition?: PredictionDecomposition | null;
}

export interface RicePredictionResponse {
  jenis: string;
  horizon: number;
  origin_date: string;
  origin_price: number;
  steps: RiceStep[];
  series: TimeSeriesPoint[];
}

export interface RiceMetricRow {
  horizon: number;
  model: "naive" | "arima" | "prophet" | "hybrid";
  n_uji: number;
  mape: number;
  mae: number;
  rmse: number;
}

export interface RiceMetricsResponse {
  jenis: string;
  protokol: string;
  metrik: RiceMetricRow[];
}
