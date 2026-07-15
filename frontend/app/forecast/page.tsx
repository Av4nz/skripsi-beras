"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { apiService } from "@/services/api";
import { HargaBerasSchema, StepDetail } from "@/types/api";
import { Loader2, Settings2, Sparkles, LineChart, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";

const formatCurrency = (val: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(val);

const monthLong = (dateStr: string) =>
  new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" }).format(new Date(dateStr));

export default function ForecastPage() {
  const [historicalData, setHistoricalData] = useState<HargaBerasSchema[]>([]);
  const [predictions, setPredictions] = useState<StepDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // Form State
  const [horizon, setHorizon] = useState(6);
  const [gkgPrice, setGkgPrice] = useState(6000);
  const [rainfall, setRainfall] = useState(150);
  const [production, setProduction] = useState(20000);
  const [inflation, setInflation] = useState(2.5);
  const [isLebaran, setIsLebaran] = useState(false);

  useEffect(() => {
    async function loadInitialData() {
      try {
        const hist = await apiService.getHistoricalData();
        setHistoricalData(hist.slice(-12));

        if (hist.length > 0) {
          const latest = hist[hist.length - 1];
          if (latest.harga_gkg !== null) setGkgPrice(latest.harga_gkg);
          if (latest.curah_hujan !== null) setRainfall(latest.curah_hujan);
          if (latest.produksi_padi !== null) setProduction(latest.produksi_padi);
          if (latest.inflasi_pangan !== null) setInflation(latest.inflasi_pangan);
          if (latest.lebaran !== null) setIsLebaran(latest.lebaran === 1);
        }
      } catch (error) {
        console.error("Failed to load historical data", error);
        toast.error("Gagal memuat data historis dari server", { id: "historical-data-error" });
      } finally {
        setInitialLoading(false);
      }
    }
    loadInitialData();
  }, []);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await apiService.predict({
        period: horizon,
        external_features: {
          harga_gkg: gkgPrice,
          curah_hujan: rainfall,
          produksi_padi: production,
          inflasi_pangan: inflation,
          lebaran: isLebaran ? 1 : 0,
        },
      });
      setPredictions(result.details?.steps || []);
      toast.success("Simulasi berhasil dijalankan", { id: "predict-success" });
    } catch (error) {
      console.error("Prediction failed", error);
      toast.error("Gagal menjalankan simulasi prediksi", { id: "predict-error" });
    } finally {
      setLoading(false);
    }
  };

  const currentPrice = historicalData[historicalData.length - 1]?.price ?? 0;
  const lastStep = predictions[predictions.length - 1];
  const change = lastStep ? lastStep.final_prediction - currentPrice : 0;
  const changeTrend: "up" | "down" | "stable" = change > 0 ? "up" : change < 0 ? "down" : "stable";
  const ChangeIcon = changeTrend === "up" ? TrendingUp : changeTrend === "down" ? TrendingDown : Minus;
  const changeVariant = changeTrend === "up" ? "destructive" : changeTrend === "down" ? "success" : "muted";

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <header>
        <Badge variant="secondary" className="mb-4">
          <Sparkles /> Simulasi Interaktif
        </Badge>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          Simulasi Prediksi Harga
        </h1>
        <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
          Atur faktor eksternal dan lihat bagaimana model hybrid memproyeksikan harga Beras Medium II
          beberapa bulan ke depan.
        </p>
      </header>

      <div className="mt-10 grid gap-6 lg:grid-cols-5">
        {/* Form */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="size-5 text-primary" />
                Parameter Prediksi
              </CardTitle>
              <CardDescription>Atur asumsi faktor eksternal untuk skenario prediksi</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePredict} className="space-y-6">
                <div className="space-y-5">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <Label>Horizon Prediksi</Label>
                      <Badge variant="muted">{horizon} bulan</Badge>
                    </div>
                    <Slider
                      value={[horizon]}
                      min={1}
                      max={12}
                      step={1}
                      onValueChange={(val) => setHorizon(Array.isArray(val) ? val[0] : val)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Harga GKG Rata-rata (Rp)</Label>
                    <Input type="number" min={0} value={gkgPrice} onChange={(e) => setGkgPrice(Number(e.target.value))} />
                  </div>

                  <div className="space-y-2">
                    <Label>Curah Hujan (mm)</Label>
                    <Input type="number" step="0.01" min={0} value={rainfall} onChange={(e) => setRainfall(Number(e.target.value))} />
                  </div>

                  <div className="space-y-2">
                    <Label>Estimasi Produksi Padi (Ton)</Label>
                    <Input type="number" step="0.01" min={0} value={production} onChange={(e) => setProduction(Number(e.target.value))} />
                  </div>

                  <div className="space-y-2">
                    <Label>Tingkat Inflasi (%)</Label>
                    <Input type="number" step="0.1" value={inflation} onChange={(e) => setInflation(Number(e.target.value))} />
                  </div>

                  <div className="flex items-center justify-between gap-4 rounded-xl border border-border/60 bg-muted/30 p-3.5">
                    <div className="space-y-0.5">
                      <Label>Faktor Musiman Lebaran</Label>
                      <p className="text-xs text-muted-foreground">Aktifkan bila periode mencakup Idul Fitri</p>
                    </div>
                    <Switch checked={isLebaran} onCheckedChange={setIsLebaran} />
                  </div>
                </div>

                <Button type="submit" size="lg" className="w-full rounded-full" disabled={loading || initialLoading}>
                  {loading && <Loader2 className="animate-spin" />}
                  Jalankan Simulasi
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card size="sm" className="bg-section-muted">
            <CardHeader>
              <CardTitle className="text-base">Pengaruh Faktor Eksternal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm text-muted-foreground">
              <p>· <strong className="font-semibold text-foreground">Harga GKG naik</strong> → harga beras cenderung naik.</p>
              <p>· <strong className="font-semibold text-foreground">Produksi padi naik</strong> → harga cenderung stabil/turun.</p>
              <p>· <strong className="font-semibold text-foreground">Inflasi naik</strong> → harga beras cenderung naik.</p>
              <p>· <strong className="font-semibold text-foreground">Curah hujan</strong> memengaruhi produksi &amp; distribusi.</p>
              <p>· <strong className="font-semibold text-foreground">Lebaran</strong> menaikkan permintaan musiman.</p>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="flex flex-col gap-6 lg:col-span-3">
          {/* Result hero */}
          {lastStep && (
            <Card className="bg-hero-gradient ring-primary/20 animate-in fade-in slide-in-from-bottom-3 duration-500">
              <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Proyeksi harga · {monthLong(lastStep.date)}
                  </p>
                  <div className="mt-1.5 flex items-end gap-2">
                    <span className="font-sans text-4xl font-bold tracking-tight tabular-nums text-foreground sm:text-5xl">
                      {formatCurrency(lastStep.final_prediction)}
                    </span>
                    <span className="pb-1.5 text-sm font-medium text-muted-foreground">/kg</span>
                  </div>
                </div>
                <div className="flex flex-col items-start gap-1.5 sm:items-end">
                  <Badge variant={changeVariant}>
                    <ChangeIcon /> {formatCurrency(Math.abs(change))}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    vs harga terkini ({formatCurrency(currentPrice)})
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="size-5 text-primary" />
                Visualisasi Hasil Prediksi
              </CardTitle>
            </CardHeader>
            <CardContent>
              {initialLoading ? (
                <div className="flex h-[300px] items-center justify-center sm:h-[400px]">
                  <Loader2 className="size-8 animate-spin text-muted-foreground" />
                </div>
              ) : predictions.length === 0 ? (
                <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-center sm:h-[400px]">
                  <span className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <Sparkles className="size-6" />
                  </span>
                  <p className="max-w-xs text-muted-foreground">
                    Atur parameter di samping lalu jalankan simulasi untuk melihat proyeksi harga.
                  </p>
                </div>
              ) : (
                <ForecastChart
                  historicalData={historicalData}
                  predictions={predictions}
                  className="h-[300px] sm:h-[420px]"
                />
              )}
            </CardContent>
          </Card>

          {predictions.length > 0 && (
            <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <CardHeader>
                <CardTitle>Rincian Prediksi</CardTitle>
                <CardDescription className="mt-1">
                  <span className="font-semibold text-foreground">
                    Prediksi Final = Prophet + Koreksi Residual XGBoost
                  </span>
                  <br />
                  Faktor eksternal (GKG, curah hujan, produksi, inflasi, Lebaran) membentuk prediksi
                  dasar Prophet; XGBoost mengoreksi sisa galat dari pola riwayat harga.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden rounded-xl border border-border/70">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/40">
                        <TableHead>Bulan</TableHead>
                        <TableHead className="text-right">Prophet</TableHead>
                        <TableHead className="text-right">Koreksi XGBoost</TableHead>
                        <TableHead className="text-right font-semibold text-primary">Final</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {predictions.map((p) => (
                        <TableRow key={p.date}>
                          <TableCell className="font-medium">{monthLong(p.date)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatCurrency(p.yhat)}</TableCell>
                          <TableCell
                            className={`text-right tabular-nums ${
                              p.residual > 0 ? "text-destructive dark:text-red-400" : "text-primary"
                            }`}
                          >
                            {p.residual > 0 ? "+" : ""}
                            {formatCurrency(p.residual)}
                          </TableCell>
                          <TableCell className="text-right font-bold tabular-nums">
                            {formatCurrency(p.final_prediction)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
