import Link from "next/link";
import type { Metadata } from "next";
import {
  Activity,
  ArrowRight,
  Coins,
  Minus,
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
import { HargaJenisPoint, RiceMetricRow, RicePredictionResponse } from "@/types/api";
import { formatMonthYear, formatPersen, cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Beranda",
  description:
    "Ringkasan harga beras terkini menurut jenis, tinjauan prediksi, dan perbandingan model dengan pembanding sederhana untuk DI Yogyakarta.",
};

export const dynamic = "force-dynamic";

const JENIS_UTAMA = "Medium II";
const HORIZON_BERANDA = 1;

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
  let metrik: RiceMetricRow[] = [];
  let historical: HargaJenisPoint[] = [];
  let prediksi: RicePredictionResponse | null = null;
  let hasError = false;

  try {
    [historical, prediksi, metrik] = await Promise.all([
      apiService.getHistoris(JENIS_UTAMA, 24),
      apiService.getPrediksi(JENIS_UTAMA, HORIZON_BERANDA),
      apiService.getMetrik(JENIS_UTAMA).then((m) => m.metrik),
    ]);
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
  
  const barisMetrik = (model: string) =>
    metrik.find((m) => m.horizon === HORIZON_BERANDA && m.model === model);
  const mHybrid = barisMetrik("hybrid");
  const mNaive = barisMetrik("naive");
  const mArima = barisMetrik("arima");
  const hybridKalah = !!mHybrid && !!mNaive && mHybrid.mape > mNaive.mape;
  
  // Calculate latest price and trend
  const latestData = historical[historical.length - 1];
  const previousData = historical[historical.length - 2];
  const firstData = historical[0];

  const rangeEnd = latestData ? formatMonthYear(latestData.date) : "-";

  const latestPrice = latestData?.price || 0;
  const previousPrice = previousData?.price || 0;

  const priceDiff = latestPrice - previousPrice;
  const priceTrend: "up" | "down" | "stable" =
    priceDiff > 0 ? "up" : priceDiff < 0 ? "down" : "stable";
  const trendValue = Math.abs(priceDiff);
  const TrendIcon = priceTrend === "up" ? TrendingUp : priceTrend === "down" ? TrendingDown : Minus;
  const trendVariant = priceTrend === "up" ? "destructive" : priceTrend === "down" ? "success" : "muted";

  // Dynamic insights (berdasarkan data harga, tanpa dugaan penyebab)
  const priceInsightTitle =
    priceTrend === "up" ? "Harga Naik" : priceTrend === "down" ? "Harga Turun" : "Harga Stabil";
  const priceInsightDesc =
    priceTrend === "up"
      ? `Tercatat kenaikan ${formatRupiah(trendValue)} dari bulan sebelumnya.`
      : priceTrend === "down"
      ? `Harga turun ${formatRupiah(trendValue)} dari bulan sebelumnya.`
      : `Harga relatif stabil tanpa perubahan dari bulan lalu.`;

  // Seberapa sering harga tidak berubah (dari riwayat yang dimuat)
  const bulanTetap = historical.filter((d, i) => i > 0 && d.price === historical[i - 1].price).length;
  const persenTetap = historical.length > 1 ? Math.round((bulanTetap / (historical.length - 1)) * 100) : 0;
  const tertinggi = historical.reduce((a, b) => (b.price > a.price ? b : a), historical[0] ?? { date: "", price: 0 });
  const terendah = historical.reduce((a, b) => (b.price < a.price ? b : a), historical[0] ?? { date: "", price: 0 });

  const langkah = prediksi?.steps ?? [];
  const langkahPertama = langkah[0];

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="bg-hero-gradient border-b border-border/60">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-2 lg:items-center lg:px-8">
          <div>
            <Badge variant="secondary" className="mb-5">
              <Sparkles /> Harga Beras · DIY
            </Badge>
            <h1 className="font-heading text-4xl font-semibold leading-[1.06] tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Pantau <span className="text-primary">harga beras</span> di Yogyakarta
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Harga enam jenis beras dari PIHPS, prediksi satu bulan ke depan dengan{" "}
              <span className="font-medium text-foreground">model hybrid</span> Prophet + XGBoost, dan
              perbandingan terbuka dengan pembanding sederhana. Prediksi adalah estimasi dari pola riwayat
              harga, bukan kepastian.
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
              <Coins className="size-4 text-primary" /> Harga Beras {JENIS_UTAMA} · DIY
            </div>
            <div className="mt-4 flex items-end gap-2">
              <span className="font-sans text-5xl font-bold tracking-tight tabular-nums text-foreground sm:text-6xl">
                {formatRupiah(latestPrice)}
              </span>
              <span className="pb-2 text-base font-medium text-muted-foreground">/kg</span>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              <Badge variant={trendVariant}>
                <TrendIcon /> {formatRupiah(trendValue)}
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
                Prediksi bulan depan: Beras {JENIS_UTAMA}
              </h2>
              <p className="mt-1.5 text-muted-foreground">
                Titik awal prediksi adalah bulan terakhir pada riwayat harga ({rangeEnd}). Model hybrid
                ditampilkan bersama dua pembanding sederhana.
              </p>
            </div>
            <Link
              href="/forecast"
              className={cn(buttonVariants({ variant: "outline" }), "rounded-full")}
            >
              Pilih jenis dan bulan <ArrowRight />
            </Link>
          </div>
          <Card>
            <CardContent className="space-y-5">
              {langkahPertama && (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-primary/30 bg-primary/5 p-4">
                    <p className="text-xs font-medium text-muted-foreground">
                      Hybrid · {formatMonthYear(langkahPertama.date)}
                    </p>
                    <p className="mt-1 font-sans text-2xl font-bold tabular-nums">{formatRupiah(langkahPertama.hybrid)}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-muted/30 p-4">
                    <p className="text-xs font-medium text-muted-foreground">Harga bulan ini dipertahankan</p>
                    <p className="mt-1 font-sans text-2xl font-semibold tabular-nums">{formatRupiah(langkahPertama.naive)}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-muted/30 p-4">
                    <p className="text-xs font-medium text-muted-foreground">ARIMA</p>
                    <p className="mt-1 font-sans text-2xl font-semibold tabular-nums">{formatRupiah(langkahPertama.arima)}</p>
                  </div>
                </div>
              )}
              <ForecastChart
                historicalData={historical.slice(-12).map((h) => ({
                  date: h.date,
                  price: h.price,
                  lebaran: 0,
                  harga_gkg: null,
                  curah_hujan: null,
                  produksi_padi: null,
                  inflasi_pangan: null,
                }))}
                predictions={langkah.map((st) => ({
                  step: st.step,
                  date: st.date,
                  yhat: st.prophet,
                  residual: st.residual,
                  final_prediction: st.hybrid,
                  features_used: {},
                  decomposition: st.decomposition,
                }))}
                comparison={langkah.map((st) => ({ date: st.date, naive: st.naive, arima: st.arima }))}
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
              icon={<Minus />}
              iconClass="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              title="Harga Sering Tidak Berubah"
              desc={`Dalam ${historical.length > 1 ? historical.length - 1 : 0} bulan terakhir, harga ${JENIS_UTAMA} tidak berubah pada ${persenTetap}% bulan. Karena itu mempertahankan harga bulan ini sulit dikalahkan sebagai prediksi.`}
            />
            <InsightCard
              icon={<Activity />}
              iconClass="bg-accent/20 text-accent-foreground dark:text-accent"
              title="Rentang Harga"
              desc={`Dalam ${historical.length} bulan terakhir, harga berkisar dari ${formatRupiah(terendah.price)} (${formatMonthYear(terendah.date)}) sampai ${formatRupiah(tertinggi.price)} (${formatMonthYear(tertinggi.date)}).`}
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
              Galat rata-rata persentase (MAPE) untuk prediksi satu bulan ke depan, diuji berjalan pada
              Januari 2024 sampai Mei 2026 untuk Beras {JENIS_UTAMA}
              {mHybrid ? ` (${mHybrid.n_uji} titik uji)` : ""}. Semakin kecil semakin baik.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-3">
            {mNaive && (
              <MetricCard
                title="Harga bulan ini dipertahankan"
                value={formatPersen(mNaive.mape)}
                description={`MAE ${formatRupiah(mNaive.mae)}`}
                icon={<Minus />}
                iconClassName="bg-secondary/15 text-secondary dark:text-secondary-foreground"
                tooltip="Pembanding paling sederhana: harga bulan depan dianggap sama dengan harga bulan ini."
              />
            )}
            {mArima && (
              <MetricCard
                title="ARIMA"
                value={formatPersen(mArima.mape)}
                description={`MAE ${formatRupiah(mArima.mae)}`}
                icon={<Activity />}
                iconClassName="bg-accent/20 text-accent-foreground dark:text-accent"
                tooltip="ARIMA(1,1,0): model statistik klasik untuk deret waktu."
              />
            )}
            {mHybrid && (
              <MetricCard
                title="Hybrid (model sistem)"
                value={formatPersen(mHybrid.mape)}
                description={`MAE ${formatRupiah(mHybrid.mae)}`}
                icon={<Target />}
                iconClassName="bg-primary/10 text-primary"
                tooltip="Prophet ditambah koreksi residual XGBoost."
              />
            )}
          </div>
          <div className="mt-5 rounded-xl border border-border/70 bg-section-muted p-4 text-sm text-muted-foreground sm:p-5">
            {hybridKalah
              ? "Pada data ini model hybrid tidak lebih akurat daripada mempertahankan harga bulan ini, dan galatnya membesar untuk beberapa bulan ke depan. "
              : "Pada data ini model hybrid lebih akurat daripada mempertahankan harga bulan ini. "}
            Hasil ini berasal dari pengujian pada data lampau dan tidak menjamin harga di masa depan.{" "}
            <Link
              href="/about"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Lihat metodologi dan hasil lengkap
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
                  Dua model, satu prediksi, dua pembanding
                </h2>
                <p className="mt-3 text-muted-foreground">
                  <span className="font-medium text-foreground">Prophet</span> menangkap tren dan pola
                  musiman dari riwayat harga; lalu{" "}
                  <span className="font-medium text-foreground">XGBoost</span>{" "}
                  mengoreksi sisa galatnya. Hasilnya dibandingkan terbuka dengan pembanding sederhana.
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
                    Model dasar: menangkap tren jangka panjang, pola musiman tahunan, dan penanda Idulfitri.
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
