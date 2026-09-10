import Link from "next/link";
import type { Metadata } from "next";
import {
  Activity,
  ArrowRight,
  CloudRain,
  Coins,
  Minus,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { MetricCard } from "@/components/ui/MetricCard";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { apiService, API_BASE_URL } from "@/services/api";
import { MetricsSchema, HargaBerasSchema, PredictionResponse } from "@/types/api";
import { formatMonthYear, cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Beranda",
  description:
    "Ringkasan harga beras terkini, akurasi model, dan tinjauan prediksi 6 bulan ke depan untuk DI Yogyakarta.",
};

export const dynamic = "force-dynamic";

const formatRupiah = (v: number) =>
  new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(v);

function InsightCard({
  icon,
  iconClass,
  title,
  desc,
}: {
  icon: React.ReactNode;
  iconClass: string;
  title: string;
  desc: string;
}) {
  return (
    <Card className="h-full gap-3">
      <CardHeader className="flex flex-row items-center gap-3">
        <span
          className={cn(
            "flex size-10 shrink-0 items-center justify-center rounded-xl [&_svg]:size-5",
            iconClass
          )}
        >
          {icon}
        </span>
        <CardTitle className="text-base font-semibold">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground">{desc}</p>
      </CardContent>
    </Card>
  );
}

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
      period: 6,
      external_features: {
        harga_gkg: latestHistorical?.harga_gkg ?? 7800,
        curah_hujan: latestHistorical?.curah_hujan ?? 150,
        produksi_padi: latestHistorical?.produksi_padi ?? 40000,
        inflasi_pangan: latestHistorical?.inflasi_pangan ?? 0.5,
        lebaran: latestHistorical?.lebaran ?? 0,
      },
    });
  } catch (error) {
    console.error("Failed to fetch data from backend:", error);
    hasError = true;
  }

  if (hasError) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-6xl flex-col items-center justify-center px-4 py-16 text-center">
        <div className="mb-4 rounded-full bg-destructive/10 p-4">
          <Activity className="h-8 w-8 text-destructive" />
        </div>
        <h2 className="mb-2 text-2xl font-semibold">Gagal Memuat Data Server</h2>
        <p className="max-w-md text-muted-foreground">
          Terjadi kesalahan saat mengambil data dari backend. Pastikan server backend FastAPI
          berjalan dan dapat diakses di{" "}
          <code className="rounded bg-muted px-1 py-0.5">{API_BASE_URL}</code>.
        </p>
      </div>
    );
  }
  
  // Display the metrics of the model actually deployed for predictions (tuned hybrid),
  // not merely whichever model happens to have the lowest MAPE.
  const metrics =
    metricsData.find((m) => m.model === "hybrid_tuned") ??
    metricsData.find((m) => m.model === "hybrid") ??
    metricsData[0] ??
    { mae: 0, mape: 0, rmse: 0 };
  
  // Calculate latest price and trend
  const latestData = historical[historical.length - 1];
  const previousData = historical[historical.length - 2];
  const firstData = historical[0];

  const rangeStart = firstData ? formatMonthYear(firstData.date) : "-";
  const rangeEnd = latestData ? formatMonthYear(latestData.date) : "-";

  const latestPrice = latestData?.price || 0;
  const previousPrice = previousData?.price || 0;

  const priceDiff = latestPrice - previousPrice;
  const priceTrend: "up" | "down" | "stable" =
    priceDiff > 0 ? "up" : priceDiff < 0 ? "down" : "stable";
  const trendValue = Math.abs(priceDiff);
  const TrendIcon = priceTrend === "up" ? TrendingUp : priceTrend === "down" ? TrendingDown : Minus;
  const trendVariant = priceTrend === "up" ? "destructive" : priceTrend === "down" ? "success" : "muted";

  // Dynamic insights
  const priceInsightTitle =
    priceTrend === "up" ? "Tren Harga Naik" : priceTrend === "down" ? "Tren Harga Turun" : "Harga Stabil";
  const priceInsightDesc =
    priceTrend === "up"
      ? `Tercatat kenaikan Rp ${trendValue} dari bulan sebelumnya. Faktor musiman atau eksternal mungkin sedang menekan pasokan.`
      : priceTrend === "down"
      ? `Harga dalam tren penurunan (turun Rp ${trendValue}). Pasokan kemungkinan melimpah di pasar.`
      : `Harga beras relatif stabil tanpa fluktuasi berarti dari bulan lalu.`;

  const latestRainfall = latestData?.curah_hujan || 0;
  const previousRainfall = previousData?.curah_hujan || 0;
  const rainfallDiff = latestRainfall - previousRainfall;

  let rainfallTitle = "Curah Hujan Stabil";
  let rainfallDesc = `Curah hujan tercatat ${latestRainfall} mm, stabil dan mendukung operasional pengeringan GKG.`;
  if (rainfallDiff > 50) {
    rainfallTitle = "Curah Hujan Meningkat Tajam";
    rainfallDesc = `Anomali kenaikan tajam (+${rainfallDiff.toFixed(0)} mm) menjadi ${latestRainfall} mm. Berisiko menghambat penjemuran gabah.`;
  } else if (rainfallDiff > 10) {
    rainfallTitle = "Curah Hujan Meningkat";
    rainfallDesc = `Tercatat kenaikan curah hujan (+${rainfallDiff.toFixed(0)} mm). Perlu waspada terhadap kualitas GKG petani.`;
  } else if (rainfallDiff < -50) {
    rainfallTitle = "Curah Hujan Turun Tajam";
    rainfallDesc = `Penurunan drastis (${rainfallDiff.toFixed(0)} mm), menandakan musim kemarau yang dapat mengancam volume panen.`;
  } else if (rainfallDiff < -10) {
    rainfallTitle = "Curah Hujan Menurun";
    rainfallDesc = `Curah hujan berkurang menjadi ${latestRainfall} mm. Kondisi ideal untuk pengeringan gabah hasil panen.`;
  }

  const latestInflation = latestData?.inflasi_pangan || 0;
  const previousInflation = previousData?.inflasi_pangan || 0;
  const inflationDiff = latestInflation - previousInflation;

  let inflationTitle = "Inflasi Pangan Stabil";
  let inflationDesc = `Inflasi daerah terkendali di ${latestInflation.toFixed(2)}%, meredam volatilitas harga beras.`;
  if (inflationDiff > 0.5) {
    inflationTitle = "Inflasi Pangan Melonjak";
    inflationDesc = `Lonjakan inflasi tajam ke ${latestInflation.toFixed(2)}%. Risiko tinggi daya beli masyarakat menurun.`;
  } else if (inflationDiff > 0.1) {
    inflationTitle = "Tren Inflasi Naik";
    inflationDesc = `Inflasi perlahan naik ke level ${latestInflation.toFixed(2)}%. Memberi sedikit tekanan pada harga bahan pokok.`;
  } else if (inflationDiff < -0.1) {
    inflationTitle = "Tren Inflasi Menurun";
    inflationDesc = `Penurunan inflasi ke ${latestInflation.toFixed(2)}% memberi sinyal positif bagi stabilitas ekonomi daerah.`;
  }

  const horizon = predictionsResult.details?.steps?.length ?? 6;

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="bg-hero-gradient border-b border-border/60">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-2 lg:items-center lg:px-8">
          <div>
            <Badge variant="secondary" className="mb-5">
              <Sparkles /> Prediksi Harga Pangan · DIY
            </Badge>
            <h1 className="font-heading text-4xl font-semibold leading-[1.06] tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Pantau &amp; prediksi <span className="text-primary">harga beras</span> di Yogyakarta
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Informasi harga Beras Medium II yang akurat dan transparan, ditenagai{" "}
              <span className="font-medium text-foreground">Hybrid Model</span> Prophet + XGBoost —
              untuk membantu keputusan masyarakat, pedagang, dan pemerintah daerah.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/forecast"
                className={cn(buttonVariants({ size: "lg" }), "rounded-full px-6")}
              >
                Lihat Prediksi <ArrowRight />
              </Link>
              <Link
                href="/historical"
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-full px-6")}
              >
                Data Historis
              </Link>
            </div>
          </div>

          {/* Hero price stat */}
          <div className="rounded-3xl border border-border/60 bg-card/80 p-6 shadow-xl shadow-primary/5 backdrop-blur-sm sm:p-8">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Coins className="size-4 text-primary" /> Harga Beras Medium II · DIY
            </div>
            <div className="mt-4 flex items-end gap-2">
              <span className="font-sans text-5xl font-bold tracking-tight tabular-nums text-foreground sm:text-6xl">
                {formatRupiah(latestPrice)}
              </span>
              <span className="pb-2 text-base font-medium text-muted-foreground">/kg</span>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              <Badge variant={trendVariant}>
                <TrendIcon /> Rp {trendValue}
              </Badge>
              <span className="text-sm text-muted-foreground">dibanding bulan lalu</span>
            </div>
            <div className="mt-6 flex items-center gap-2 border-t border-border/60 pt-4 text-sm text-muted-foreground">
              <Activity className="size-4 text-secondary" /> Data terbaru:{" "}
              <span className="font-medium text-foreground">{rangeEnd}</span>
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        {/* Forecast overview */}
        <section className="py-14 sm:py-16">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
                Tinjauan prediksi {horizon} bulan ke depan
              </h2>
              <p className="mt-1.5 text-muted-foreground">
                Perbandingan harga aktual dengan proyeksi model hybrid.
              </p>
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                Proyeksi dihitung dengan mengasumsikan faktor eksternal (harga gabah kering giling,
                curah hujan, produksi padi, dan inflasi pangan) tetap pada nilai terakhir yang
                tersedia, yaitu data {rangeEnd}. Perubahan kondisi nyata dapat menggeser hasil
                prediksi.
              </p>
            </div>
            <Link
              href="/forecast"
              className={cn(buttonVariants({ variant: "outline" }), "rounded-full")}
            >
              Simulasi sendiri <ArrowRight />
            </Link>
          </div>
          <Card>
            <CardContent>
              <ForecastChart
                historicalData={historical.slice(-12)}
                predictions={predictionsResult.details?.steps || []}
                className="h-[320px] sm:h-[420px]"
              />
            </CardContent>
          </Card>
        </section>

        {/* Insights */}
        <section className="pb-14 sm:pb-16">
          <div className="mb-6 flex items-center gap-3">
            <h2 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
              Sorotan pasar
            </h2>
            <Badge variant="muted">Otomatis</Badge>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            <InsightCard
              icon={<TrendIcon />}
              iconClass={
                priceTrend === "up"
                  ? "bg-destructive/10 text-destructive"
                  : priceTrend === "down"
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground"
              }
              title={priceInsightTitle}
              desc={priceInsightDesc}
            />
            <InsightCard
              icon={<CloudRain />}
              iconClass="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              title={rainfallTitle}
              desc={rainfallDesc}
            />
            <InsightCard
              icon={<ShieldCheck />}
              iconClass="bg-accent/20 text-accent-foreground dark:text-accent"
              title={inflationTitle}
              desc={inflationDesc}
            />
          </div>
        </section>

        {/* Model accuracy */}
        <section className="pb-14 sm:pb-16">
          <div className="mb-6">
            <h2 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
              Seberapa akurat prediksinya?
            </h2>
            <p className="mt-1.5 max-w-2xl text-muted-foreground">
              Model dievaluasi pada data uji menggunakan tiga metrik standar. Semakin kecil
              nilainya, semakin dekat prediksi dengan harga sebenarnya.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-3">
            <MetricCard
              title="MAPE"
              value={`${metrics.mape}%`}
              description="Rata-rata galat persentase"
              icon={<Target />}
              iconClassName="bg-primary/10 text-primary"
              tooltip="Mean Absolute Percentage Error — rata-rata persentase kesalahan prediksi. Semakin kecil semakin akurat."
            />
            <MetricCard
              title="MAE"
              value={`Rp ${metrics.mae}`}
              description="Rata-rata selisih absolut"
              icon={<Activity />}
              iconClassName="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              tooltip="Mean Absolute Error — rata-rata selisih absolut antara hasil prediksi dan harga aktual."
            />
            <MetricCard
              title="RMSE"
              value={`Rp ${metrics.rmse}`}
              description="Akar rata-rata galat kuadrat"
              icon={<TrendingUp />}
              iconClassName="bg-accent/20 text-accent-foreground dark:text-accent"
              tooltip="Root Mean Square Error — memberi penalti lebih besar pada kesalahan yang tinggi."
            />
          </div>
          <div className="mt-5 rounded-xl border border-border/70 bg-section-muted p-4 text-sm text-muted-foreground sm:p-5">
            Angka di atas berlaku pada{" "}
            <span className="font-medium text-foreground">mode skenario</span>, yaitu ketika kondisi
            faktor eksternal bulan yang diprediksi sudah diketahui atau diasumsikan. Bila sistem hanya
            memakai data bulan terakhir yang tersedia, seperti nilai bawaan pada halaman prediksi,
            MAPE-nya sekitar <span className="font-medium text-foreground">9,91%</span>.{" "}
            <Link
              href="/about"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Lihat perbandingannya di Metodologi
            </Link>
            .
          </div>
        </section>

        {/* Methodology teaser */}
        <section className="pb-16">
          <Card className="overflow-hidden bg-section-muted ring-secondary/20">
            <CardContent className="grid gap-8 py-2 md:grid-cols-2 md:items-center">
              <div>
                <Badge variant="accent" className="mb-4">
                  Metodologi
                </Badge>
                <h2 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
                  Dua model, satu prediksi yang lebih tajam
                </h2>
                <p className="mt-3 text-muted-foreground">
                  <span className="font-medium text-foreground">Prophet</span> menangkap tren, pola
                  musiman, dan faktor eksternal (harga gabah, curah hujan, produksi, inflasi) sebagai
                  regressor; lalu <span className="font-medium text-foreground">XGBoost</span>{" "}
                  mengoreksi sisa galatnya dari pola riwayat harga.
                </p>
                <Link
                  href="/about"
                  className={cn(buttonVariants({ size: "lg" }), "mt-6 rounded-full px-6")}
                >
                  Pelajari metodologi <ArrowRight />
                </Link>
              </div>
              <div className="grid gap-4">
                <div className="rounded-2xl border border-border/60 bg-card p-5">
                  <h3 className="font-semibold text-foreground">1 · Facebook Prophet</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    Model dasar: menangkap tren jangka panjang, musiman tahunan, dan pengaruh faktor eksternal harga beras.
                  </p>
                </div>
                <div className="rounded-2xl border border-border/60 bg-card p-5">
                  <h3 className="font-semibold text-foreground">2 · XGBoost (residual)</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    Mengoreksi sisa galat Prophet dari pola riwayat harga (lag &amp; residual).
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
