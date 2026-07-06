import { MetricCard } from "@/components/ui/MetricCard";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { apiService } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity, Target, Coins, Zap, CloudRain, ShieldCheck } from "lucide-react";
import { MetricsSchema, HargaBerasSchema, PredictionResponse } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let metricsData: MetricsSchema[] = [];
  let historical: HargaBerasSchema[] = [];
  let predictionsResult: Partial<PredictionResponse> = { details: { steps: [] } };
  let hasError = false;

  try {
    metricsData = await apiService.getMetrics();
    historical = await apiService.getHistoricalData();
    const latestHistorical = historical[historical.length - 1];
    predictionsResult = await apiService.predict({
      period: 9,
      external_features: {
        harga_gkg: latestHistorical?.harga_gkg ?? 7800,
        curah_hujan: latestHistorical?.curah_hujan ?? 150,
        produksi_padi: latestHistorical?.produksi_padi ?? 40000,
        inflasi_pangan: latestHistorical?.inflasi_pangan ?? 0.5,
        lebaran: latestHistorical?.lebaran ?? 0
      }
    });
  } catch (error) {
    console.error("Failed to fetch data from backend:", error);
    hasError = true;
  }
  
  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center h-[60vh]">
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <Activity className="h-8 w-8 text-destructive" />
        </div>
        <h2 className="text-2xl font-semibold mb-2">Gagal Memuat Data Server</h2>
        <p className="text-muted-foreground max-w-md">
          Terjadi kesalahan saat mengambil data dari backend. Pastikan server backend FastAPI berjalan di <code className="bg-muted px-1 py-0.5 rounded">http://localhost:8000</code>.
        </p>
      </div>
    );
  }
  
  // Sort metrics by MAPE ascending to automatically display the best performing model (Tuned Hybrid)
  const sortedMetrics = [...metricsData].sort((a, b) => a.mape - b.mape);
  const metrics = sortedMetrics[0] || { mae: 0, mape: 0, rmse: 0 };
  
  // Calculate latest price and trend
  const latestData = historical[historical.length - 1];
  const previousData = historical[historical.length - 2];
  
  const latestPrice = latestData?.price || 0;
  const previousPrice = previousData?.price || 0;
  
  const priceDiff = latestPrice - previousPrice;
  const priceTrend = priceDiff > 0 ? "up" : priceDiff < 0 ? "down" : "stable";
  const trendValue = Math.abs(priceDiff);

  // Dynamic Insights Logic
  const priceInsightTitle = priceTrend === "up" ? "Tren Harga Naik" : priceTrend === "down" ? "Tren Harga Turun" : "Harga Stabil";
  const priceInsightDesc = priceTrend === "up" 
    ? `Tercatat kenaikan Rp ${trendValue} dari bulan sebelumnya. Faktor musiman atau eksternal mungkin sedang menekan pasokan.` 
    : priceTrend === "down" 
    ? `Harga dalam tren penurunan (turun Rp ${trendValue}). Pasokan kemungkinan melimpah di pasar.`
    : `Harga beras stabil di Rp ${latestPrice} tanpa fluktuasi berarti dari bulan lalu.`;
  const priceInsightColor = priceTrend === "up" ? "text-destructive" : priceTrend === "down" ? "text-primary" : "text-chart-4";
  const PriceIcon = priceTrend === "down" ? TrendingDown : TrendingUp;

  const latestRainfall = latestData?.curah_hujan || 0;
  const previousRainfall = previousData?.curah_hujan || 0;
  const rainfallDiff = latestRainfall - previousRainfall;
  
  let rainfallTitle = "Curah Hujan Stabil";
  let rainfallDesc = `Curah hujan tercatat ${latestRainfall} mm, stabil dan mendukung operasional pengeringan GKG.`;
  let rainfallIconColor = "text-chart-2";
  if (rainfallDiff > 50) {
    rainfallTitle = "Curah Hujan Meningkat Tajam";
    rainfallDesc = `Anomali kenaikan tajam (+${rainfallDiff.toFixed(0)} mm) menjadi ${latestRainfall} mm. Sangat berisiko menghambat penjemuran gabah.`;
    rainfallIconColor = "text-destructive";
  } else if (rainfallDiff > 10) {
    rainfallTitle = "Curah Hujan Meningkat";
    rainfallDesc = `Tercatat kenaikan curah hujan (+${rainfallDiff.toFixed(0)} mm). Perlu waspada terhadap kualitas GKG yang dihasilkan petani.`;
    rainfallIconColor = "text-chart-3";
  } else if (rainfallDiff < -50) {
    rainfallTitle = "Curah Hujan Turun Tajam";
    rainfallDesc = `Penurunan drastis (${rainfallDiff.toFixed(0)} mm). Menandakan musim kemarau yang dapat mengancam volume produksi panen.`;
    rainfallIconColor = "text-chart-4";
  } else if (rainfallDiff < -10) {
    rainfallTitle = "Curah Hujan Menurun";
    rainfallDesc = `Curah hujan berkurang menjadi ${latestRainfall} mm. Kondisi ideal untuk proses pengeringan gabah hasil panen.`;
    rainfallIconColor = "text-primary";
  }

  const latestInflation = latestData?.inflasi_pangan || 0;
  const previousInflation = previousData?.inflasi_pangan || 0;
  const inflationDiff = latestInflation - previousInflation;
  
  let inflationTitle = "Inflasi Pangan Stabil";
  let inflationDesc = `Inflasi daerah terkendali di ${latestInflation.toFixed(2)}%, meredam volatilitas harga beras secara ekstrim.`;
  let inflationIconColor = "text-primary";
  if (inflationDiff > 0.5) {
    inflationTitle = "Inflasi Pangan Melonjak";
    inflationDesc = `Lonjakan inflasi tajam ke ${latestInflation.toFixed(2)}% terdeteksi. Risiko tinggi daya beli masyarakat menurun.`;
    inflationIconColor = "text-destructive";
  } else if (inflationDiff > 0.1) {
    inflationTitle = "Tren Inflasi Naik";
    inflationDesc = `Inflasi perlahan naik ke level ${latestInflation.toFixed(2)}%. Memberikan sedikit tekanan pada harga bahan pokok.`;
    inflationIconColor = "text-chart-3";
  } else if (inflationDiff < -0.1) {
    inflationTitle = "Tren Inflasi Menurun";
    inflationDesc = `Penurunan inflasi ke ${latestInflation.toFixed(2)}% memberikan sinyal positif untuk stabilitas ekonomi daerah.`;
    inflationIconColor = "text-chart-4";
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Hero Section */}
      <section className="flex flex-col gap-2 relative">
        <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Sistem Prediksi Harga Beras Medium II
        </h1>
        <p className="text-muted-foreground text-lg max-w-3xl">
          Prediksi harga beras di DI Yogyakarta berbasis Hybrid Model Prophet dan XGBoost untuk mendukung ketahanan pangan daerah.
        </p>
        <div className="text-sm text-muted-foreground/80 mt-1 flex flex-col gap-0.5 sm:flex-row sm:gap-4 font-medium">
          <span className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5"/> Data historis: Januari 2021 – November 2025</span>
          <span className="hidden sm:inline">•</span>
          <span className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5"/> Terakhir diperbarui: November 2025</span>
        </div>
      </section>

      {/* Metrics Cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Harga Beras Terkini"
          value={new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(latestPrice)}
          description="per kg"
          icon={<Coins className="h-4 w-4 text-primary" />}
          trend={priceTrend}
          trendValue={`Rp ${trendValue}`}
        />
        <MetricCard
          title="MAPE (Model Accuracy)"
          value={`${metrics.mape}%`}
          description="Mean Absolute Percentage Error"
          icon={<Target className="h-4 w-4 text-chart-4" />}
          tooltip="Mean Absolute Percentage Error. Menunjukkan rata-rata persentase kesalahan prediksi. Semakin kecil nilainya maka model semakin akurat."
        />
        <MetricCard
          title="MAE (Error Absolut)"
          value={`Rp ${metrics.mae}`}
          description="Mean Absolute Error"
          icon={<Activity className="h-4 w-4 text-chart-3" />}
          tooltip="Mean Absolute Error. Menunjukkan rata-rata selisih absolut antara hasil prediksi dan harga aktual."
        />
        <MetricCard
          title="RMSE (Root Mean Square)"
          value={`Rp ${metrics.rmse}`}
          description="Root Mean Square Error"
          icon={<TrendingUp className="h-4 w-4 text-chart-2" />}
          tooltip="Root Mean Square Error. Mengukur besarnya kesalahan prediksi dengan penalti lebih besar untuk error yang tinggi."
        />
      </section>

      {/* Main Chart Area */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="col-span-1 lg:col-span-2 flex flex-col">
          <CardHeader>
            <CardTitle>Tinjauan Prediksi 6 Bulan Kedepan</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-100">
            <ForecastChart 
              historicalData={historical.slice(-12)} 
              predictions={predictionsResult.details?.steps || []}
            />
          </CardContent>
        </Card>

        {/* Quick Insights */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-md flex items-center gap-2">
                <PriceIcon className={`h-4 w-4 ${priceInsightColor}`} />
                {priceInsightTitle}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {priceInsightDesc}
              </p>
              <p className="text-xs text-muted-foreground/60 mt-3 italic border-t pt-2">Insight otomatis berdasarkan analisis data periode terbaru.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-md flex items-center gap-2">
                <CloudRain className={`h-4 w-4 ${rainfallIconColor}`} />
                {rainfallTitle}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {rainfallDesc}
              </p>
              <p className="text-xs text-muted-foreground/60 mt-3 italic border-t pt-2">Insight otomatis berdasarkan analisis data periode terbaru.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-md flex items-center gap-2">
                <ShieldCheck className={`h-4 w-4 ${inflationIconColor}`} />
                {inflationTitle}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {inflationDesc}
              </p>
              <p className="text-xs text-muted-foreground/60 mt-3 italic border-t pt-2">Insight otomatis berdasarkan analisis data periode terbaru.</p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* System Overview */}
      <section>
        <Card className="bg-secondary/10 border-secondary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-accent" />
              Metodologi Hybrid Forecasting
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-muted-foreground">
              <div>
                <h3 className="font-semibold text-foreground mb-2">1. Facebook Prophet</h3>
                <p>
                  Prophet digunakan sebagai model dasar (base model) untuk menangkap pola tren linear/non-linear serta efek musiman (seasonality) tahunan dari harga beras.
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">2. Extreme Gradient Boosting (XGBoost)</h3>
                <p>
                  XGBoost diterapkan untuk memprediksi nilai error (residual) dari Prophet menggunakan faktor eksternal seperti curah hujan, produksi, inflasi, dan harga GKG.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
