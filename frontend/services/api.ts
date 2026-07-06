import axios from "axios";
import { HargaBerasSchema, MetricsSchema, PredictionRequest, PredictionResponse } from "@/types/api";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  async getMetrics(): Promise<MetricsSchema[]> {
    const response = await apiClient.get<MetricsSchema[]>("/metrics");
    return response.data;
  },

  async getHistoricalData(skip = 0, limit = 100): Promise<HargaBerasSchema[]> {
    // We request a larger limit if needed, or default to backend's 100
    // Backend orders by date DESC, so we might want to reverse it for charts
    const response = await apiClient.get<HargaBerasSchema[]>(`/data/historical?skip=${skip}&limit=${limit}`);
    // Reverse to get chronological order (oldest first) for UI charts
    return response.data.reverse();
  },

  async predict(request: PredictionRequest): Promise<PredictionResponse> {
    const response = await apiClient.post<PredictionResponse>("/predict", request);
    return response.data;
  },
};
