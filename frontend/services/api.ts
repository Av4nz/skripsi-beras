import axios from "axios";
import {
  HargaJenisPoint,
  RiceMetricsResponse,
  RicePredictionResponse,
} from "@/types/api";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  // ----- API Beras: per jenis, tanpa masukan faktor eksternal -----
  async getJenis(): Promise<string[]> {
    const response = await apiClient.get<string[]>("/beras/jenis");
    return response.data;
  },

  async getHistoris(jenis: string, limit = 120): Promise<HargaJenisPoint[]> {
    const response = await apiClient.get<HargaJenisPoint[]>("/beras/historis", { params: { jenis, limit } });
    return response.data;
  },

  async getPrediksi(jenis: string, horizon = 1): Promise<RicePredictionResponse> {
    const response = await apiClient.get<RicePredictionResponse>("/beras/prediksi", { params: { jenis, horizon } });
    return response.data;
  },

  async getMetrik(jenis: string): Promise<RiceMetricsResponse> {
    const response = await apiClient.get<RiceMetricsResponse>("/beras/metrik", { params: { jenis } });
    return response.data;
  },
};
