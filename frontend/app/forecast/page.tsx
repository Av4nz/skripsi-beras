"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { apiService } from "@/services/api";
import { HargaJenisPoint, RiceMetricRow, RicePredictionResponse } from "@/types/api";
import {
  AlertTriangle,
  BarChart3,
  Info,
  LineChart,
  Loader2,
  Minus,
  Settings2,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const MAX_HORIZON = 6;
const JENIS_BAWAAN = "Medium II";

const formatCurrency = (val: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(val);

const monthLong = (dateStr: string) =>
  new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" }).format(new Date(dateStr));

const persen = (v: number) => `${v.toFixed(2).replace(".", ",")}%`;

export default function ForecastPage() {
  const [jenisList, setJenisList] = useState<string[]>([]);
  const [jenis, setJenis] = useState(JENIS_BAWAAN);
  const [horizon, setHorizon] = useState(1);
  const [historis, setHistoris] = useState<HargaJenisPoint[]>([]);
  const [hasil, setHasil] = useState<RicePredictionResponse | null>(null);
  const [metrik, setMetrik] = useState<RiceMetricRow[]>([]);
  const [selectedStep, setSelectedStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiService
      .getJenis()
      .then(setJenisList)
      .catch(() => {
        setError("Gagal memuat daftar jenis beras dari server.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let batal = false;
    async function muat() {
      try {
        const [hist, pred, met] = await Promise.all([
          apiService.getHistoris(jenis, 12),
          apiService.getPrediksi(jenis, horizon),
          apiService.getMetrik(jenis),
        ]);
        if (batal) return;
        setHistoris(hist);
        setHasil(pred);
        setMetrik(met.metrik);
        setSelectedStep(0);
        setError(null);
      } catch (e) {
        if (batal) return;
        console.error("Gagal memuat prediksi", e);
        setError("Gagal memuat prediksi dari server. Coba lagi beberapa saat.");
        toast.error("Gagal memuat prediksi", { id: "predict-error" });
      } finally {
        if (!batal) setLoading(false);
      }
    }
    muat();
    return () => {
      batal = true;
    };
  }, [jenis, horizon]);

  const pilihJenis = (j: string) => {
    setLoading(true);
    setJenis(j);
  };
  const pilihHorizon = (h: number) => {
    setLoading(true);
    setHorizon(h);
  };

  const steps = hasil?.steps ?? [];
  const lastStep = steps[steps.length - 1];
  const selected = steps[selectedStep];
  const change = lastStep && hasil ? lastStep.hybrid - hasil.origin_price : 0;
  const trend: "up" | "down" | "stable" = change > 0 ? "up" : change < 0 ? "down" : "stable";
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendVariant = trend === "up" ? "destructive" : trend === "down" ? "success" : "muted";

  const baris = (model: string) => metrik.find((m) => m.horizon === horizon && m.model === model);
  const mHybrid = baris("hybrid");
  const mNaive = baris("naive");
  const mArima = baris("arima");

  const dekomp = selected?.decomposition;
  const maxAbs = dekomp ? Math.max(...dekomp.components.map((c) => Math.abs(c.contribution)), 1) : 1;

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <header>
        <Badge variant="secondary" className="mb-4">
          <Sparkles /> Prediksi Harga
        </Badge>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Prediksi Harga Beras
        </h1>
        <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
          Pilih jenis beras dan jumlah bulan. Sistem memproyeksikan harga dari riwayat harga terbaru
          dengan model hybrid Prophet dan XGBoost, lalu menampilkannya bersama dua pembanding sederhana.
        </p>
      </header>

      <div className="mt-10 grid gap-6 lg:grid-cols-5">
        {/* Pilihan */}
        <div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="size-5 text-primary" />
                Pilihan Prediksi
              </CardTitle>
              <CardDescription>
                Tidak ada masukan faktor eksternal. Titik awal prediksi adalah bulan terakhir pada riwayat
                harga jenis yang dipilih
                {hasil ? ` (${monthLong(hasil.origin_date)})` : ""}.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2.5">
                <Label id="label-jenis">Jenis Beras</Label>
                <div role="radiogroup" aria-labelledby="label-jenis" className="grid grid-cols-2 gap-2">
                  {jenisList.map((j) => (
                    <button
                      key={j}
                      type="button"
                      role="radio"
                      aria-checked={j === jenis}
                      disabled={loading && j !== jenis}
                      onClick={() => pilihJenis(j)}
                      className={cn(
                        "rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                        j === jenis
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border/70 text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      {j}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <Label>Jumlah Bulan ke Depan</Label>
                  <Badge variant="muted">{horizon} bulan</Badge>
                </div>
                <Slider
                  value={[horizon]}
                  min={1}
                  max={MAX_HORIZON}
                  step={1}
                  onValueChange={(val) => pilihHorizon(Array.isArray(val) ? val[0] : val)}
                />
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Galat membesar seiring jumlah bulan. Satu bulan adalah horizon yang paling dapat
                  dipertanggungjawabkan.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card size="sm" className="bg-section-muted">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Info className="size-4 text-primary" /> Cara Membaca Hasil
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm text-muted-foreground">
              <p>
                · <strong className="font-semibold text-foreground">Hybrid</strong> adalah prediksi
                model: tren dan pola musiman dari Prophet, ditambah koreksi XGBoost.
              </p>
              <p>
                · <strong className="font-semibold text-foreground">Harga bulan ini dipertahankan</strong>{" "}
                adalah pembanding paling sederhana: harga bulan depan dianggap sama dengan bulan ini.
              </p>
              <p>
                · <strong className="font-semibold text-foreground">ARIMA</strong> adalah pembanding
                statistik klasik.
              </p>
              <p>
                · Harga beras DIY sangat stabil, sehingga pembanding sederhana sering sulit dikalahkan.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Hasil */}
        <div className="flex min-w-0 flex-col gap-6 lg:col-span-3">
          {error && (
            <Card className="border-destructive/40">
              <CardContent className="flex items-start gap-3 text-sm" role="alert">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
                <span>{error}</span>
              </CardContent>
            </Card>
          )}

          {lastStep && hasil && (
            <Card className="bg-hero-gradient ring-primary/20 animate-in fade-in slide-in-from-bottom-3 duration-500">
              <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Prediksi hybrid · {hasil.jenis} · {monthLong(lastStep.date)}
                  </p>
                  <div className="mt-1.5 flex items-end gap-2">
                    <span className="font-sans text-4xl font-bold tracking-tight tabular-nums text-foreground sm:text-5xl">
                      {formatCurrency(lastStep.hybrid)}
                    </span>
                    <span className="pb-1.5 text-sm font-medium text-muted-foreground">/kg</span>
                  </div>
                </div>
                <div className="flex flex-col items-start gap-1.5 sm:items-end">
                  <Badge variant={trendVariant}>
                    <TrendIcon /> {formatCurrency(Math.abs(change))}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    vs harga {monthLong(hasil.origin_date)} ({formatCurrency(hasil.origin_price)})
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="size-5 text-primary" />
                Grafik Prediksi
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading && !hasil ? (
                <div className="flex h-[300px] items-center justify-center sm:h-[400px]" role="status" aria-live="polite">
                  <Loader2 className="size-8 animate-spin text-muted-foreground" />
                  <span className="sr-only">Memuat prediksi</span>
                </div>
              ) : hasil ? (
                <div className={cn(loading && "opacity-60 transition-opacity")} aria-busy={loading}>
                  <ForecastChart
                    historicalData={historis.map((h) => ({
                      date: h.date,
                      price: h.price,
                      lebaran: 0,
                      harga_gkg: null,
                      curah_hujan: null,
                      produksi_padi: null,
                      inflasi_pangan: null,
                    }))}
                    predictions={steps.map((s) => ({
                      step: s.step,
                      date: s.date,
                      yhat: s.prophet,
                      residual: s.residual,
                      final_prediction: s.hybrid,
                      features_used: {},
                      decomposition: s.decomposition,
                    }))}
                    comparison={steps.map((s) => ({ date: s.date, naive: s.naive, arima: s.arima }))}
                    className="h-[300px] sm:h-[420px]"
                  />
                </div>
              ) : null}
            </CardContent>
          </Card>

          {steps.length > 0 && (
            <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <CardHeader>
                <CardTitle>Perbandingan dengan Pembanding</CardTitle>
                <CardDescription className="mt-1">
                  Prediksi hybrid ditampilkan bersama dua pembanding sederhana untuk bulan yang sama.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto rounded-xl border border-border/70">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/40">
                        <TableHead>Bulan</TableHead>
                        <TableHead className="text-right font-semibold text-primary">Hybrid</TableHead>
                        <TableHead className="text-right">Harga bulan ini dipertahankan</TableHead>
                        <TableHead className="text-right">ARIMA</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {steps.map((p, idx) => (
                        <TableRow
                          key={p.date}
                          onClick={() => setSelectedStep(idx)}
                          className={cn(
                            "cursor-pointer transition-colors hover:bg-muted/40",
                            idx === selectedStep && "bg-primary/5"
                          )}
                        >
                          <TableCell className="font-medium">{monthLong(p.date)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums">{formatCurrency(p.hybrid)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatCurrency(p.naive)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatCurrency(p.arima)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {mHybrid && mNaive && mArima && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="size-5 text-primary" />
                  Seberapa Akurat untuk {horizon} Bulan?
                </CardTitle>
                <CardDescription className="mt-1">
                  Galat rata-rata persentase (MAPE) pada uji berjalan Januari 2024 sampai Mei 2026 untuk{" "}
                  {jenis} ({mHybrid.n_uji} titik uji). Semakin kecil semakin baik.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { nama: "Harga bulan ini dipertahankan", m: mNaive },
                    { nama: "ARIMA", m: mArima },
                    { nama: "Hybrid (model sistem)", m: mHybrid },
                  ].map(({ nama, m }) => (
                    <div key={nama} className="rounded-xl border border-border/60 bg-muted/30 p-3.5">
                      <p className="text-xs font-medium text-muted-foreground">{nama}</p>
                      <p className="mt-1 font-sans text-2xl font-semibold tabular-nums">{persen(m.mape)}</p>
                      <p className="text-xs text-muted-foreground">MAE {formatCurrency(m.mae)}</p>
                    </div>
                  ))}
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {mHybrid.mape > mNaive.mape
                    ? "Pada data ini model hybrid tidak lebih akurat daripada mempertahankan harga bulan ini. Hasil prediksi sebaiknya dibaca sebagai gambaran kecenderungan, bukan kepastian harga."
                    : "Pada data ini model hybrid lebih akurat daripada mempertahankan harga bulan ini."}{" "}
                  Angka ini dari uji pada data lampau dan tidak menjamin harga di masa depan.
                </p>
              </CardContent>
            </Card>
          )}

          {dekomp && selected && (
            <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <CardHeader>
                <CardTitle>Komponen Prediksi Dasar</CardTitle>
                <CardDescription className="mt-1">
                  Rincian prediksi dasar Prophet untuk{" "}
                  <span className="font-semibold text-foreground">{monthLong(selected.date)}</span>: tren
                  ditambah pola musiman tahunan. Klik bulan lain pada tabel untuk
                  melihat rinciannya.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 p-3.5">
                  <span className="text-sm font-medium text-muted-foreground">Tren dasar (baseline)</span>
                  <span className="font-sans text-lg font-semibold tabular-nums">{formatCurrency(dekomp.trend)}</span>
                </div>
                <div className="space-y-2.5">
                  {[...dekomp.components]
                    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
                    .map((c) => {
                      const pct = (Math.abs(c.contribution) / maxAbs) * 100;
                      const positive = c.contribution >= 0;
                      return (
                        <div key={c.name} className="flex items-center gap-3">
                          <span className="w-36 shrink-0 truncate text-sm text-foreground" title={c.label}>
                            {c.label}
                          </span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn("h-full rounded-full", positive ? "bg-primary" : "bg-destructive")}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span
                            className={cn(
                              "w-24 shrink-0 text-right text-sm font-medium tabular-nums",
                              positive ? "text-primary" : "text-destructive dark:text-red-400"
                            )}
                          >
                            {positive ? "+" : "-"}
                            {formatCurrency(Math.abs(c.contribution))}
                          </span>
                        </div>
                      );
                    })}
                </div>
                <p className="text-xs text-muted-foreground">
                  Prediksi dasar Prophet {formatCurrency(selected.prophet)}, ditambah koreksi XGBoost{" "}
                  {formatCurrency(selected.residual)}, menjadi prediksi hybrid {formatCurrency(selected.hybrid)}.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
