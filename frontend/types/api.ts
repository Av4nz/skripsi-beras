export interface ExternalFeatures {
  harga_gkg: number;
  curah_hujan: number;
  produksi_padi: number;
  inflasi_pangan: number;
  lebaran: number;
}

export interface PredictionRequest {
  period: number;
  external_features?: ExternalFeatures | null;
}

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

export interface PredictionDetails {
  steps: StepDetail[];
}

export interface PredictionResponse {
  prediction: number | number[];
  series: TimeSeriesPoint[];
  details: PredictionDetails;
}

export interface HargaBerasSchema {
  date: string;
  price: number;
  lebaran: number;
  harga_gkg: number | null;
  curah_hujan: number | null;
  produksi_padi: number | null;
  inflasi_pangan: number | null;
}

export interface MetricsSchema {
  model: string;
  mae: number;
  mape: number;
  rmse: number;
}

// Frontend-specific extended interfaces
export interface DashboardMetrics {
  mape: number;
  mae: number;
  rmse: number;
  latestPrice: number;
  priceTrend: "up" | "down" | "stable";
  trendValue: number;
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
