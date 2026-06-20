"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { apiService } from "@/services/api";
import { HargaBerasSchema, StepDetail } from "@/types/api";
import { Loader2, Settings2 } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";

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
        setHistoricalData(hist.slice(-12)); // Last 12 months for chart context
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
        }
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

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(val);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Simulasi Prediksi</h1>
        <p className="text-muted-foreground mt-2">
          Atur parameter eksternal untuk melihat bagaimana variabel mempengaruhi prediksi harga beras ke depan.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Configuration Form and Info */}
        <div className="xl:col-span-1 flex flex-col gap-6">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                Parameter Prediksi
              </CardTitle>
              <CardDescription>Sesuaikan faktor pendukung model XGBoost</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePredict} className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label>Horizon Prediksi (Bulan)</Label>
                      <span className="text-sm font-medium">{horizon}</span>
                    </div>
                    <Slider 
                      value={[horizon]} 
                      min={1} 
                      max={12} 
                      step={1} 
                      onValueChange={(val) => setHorizon(Array.isArray(val) ? val[0] : (val as any)[0] || val as any)} 
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Harga GKG Rata-rata (Rp)</Label>
                    <Input 
                      type="number" 
                      min={0}
                      value={gkgPrice} 
                      onChange={(e) => setGkgPrice(Number(e.target.value))} 
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Curah Hujan (mm)</Label>
                    <Input 
                      type="number" 
                      min={0}
                      value={rainfall} 
                      onChange={(e) => setRainfall(Number(e.target.value))} 
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Estimasi Produksi Padi (Ton)</Label>
                    <Input 
                      type="number" 
                      min={0}
                      value={production} 
                      onChange={(e) => setProduction(Number(e.target.value))} 
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Tingkat Inflasi (%)</Label>
                    <Input 
                      type="number" 
                      step="0.1"
                      value={inflation} 
                      onChange={(e) => setInflation(Number(e.target.value))} 
                    />
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="space-y-0.5">
                      <Label>Faktor Musiman Lebaran</Label>
                      <p className="text-xs text-muted-foreground">Aktifkan jika periode prediksi mencakup Idul Fitri</p>
                    </div>
                    <Switch checked={isLebaran} onCheckedChange={setIsLebaran} />
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={loading || initialLoading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Jalankan Simulasi
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="h-fit">
            <CardHeader>
              <CardTitle>Pengaruh Faktor Eksternal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>• <strong>Harga GKG meningkat</strong> → harga beras cenderung meningkat.</p>
              <p>• <strong>Produksi padi meningkat</strong> → harga beras cenderung lebih stabil atau menurun.</p>
              <p>• <strong>Inflasi meningkat</strong> → harga beras cenderung meningkat.</p>
              <p>• <strong>Curah hujan</strong> dapat mempengaruhi produksi dan distribusi beras.</p>
              <p>• <strong>Faktor musiman Lebaran</strong> dapat meningkatkan permintaan dan mempengaruhi harga.</p>
            </CardContent>
          </Card>
        </div>

        {/* Results Area */}
        <div className="xl:col-span-2 flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Visualisasi Hasil Prediksi</CardTitle>
            </CardHeader>
            <CardContent className="min-h-[400px]">
              {initialLoading ? (
                <div className="flex items-center justify-center h-full min-h-[350px]">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ForecastChart historicalData={historicalData} predictions={predictions} height={400} />
              )}
            </CardContent>
          </Card>

          {predictions.length > 0 && (
            <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <CardHeader>
                <CardTitle>Rincian Prediksi Harga</CardTitle>
                <CardDescription className="text-sm mt-1">
                  <span className="font-semibold text-foreground">Prediksi Final = Prediksi Prophet + Koreksi Residual XGBoost</span><br/>
                  Model XGBoost digunakan untuk memperbaiki kesalahan prediksi (residual) dari model Prophet menggunakan faktor eksternal seperti GKG, curah hujan, produksi padi, inflasi, dan faktor musiman.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Bulan</TableHead>
                        <TableHead className="text-right">Prophet Base</TableHead>
                        <TableHead className="text-right">Koreksi XGBoost (Residual)</TableHead>
                        <TableHead className="text-right font-bold text-primary">Prediksi Final</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {predictions.map((p) => {
                        const date = new Date(p.date);
                        const formattedDate = new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" }).format(date);
                        
                        return (
                          <TableRow key={p.date}>
                            <TableCell className="font-medium">{formattedDate}</TableCell>
                            <TableCell className="text-right">{formatCurrency(p.yhat)}</TableCell>
                            <TableCell className={`text-right ${p.residual > 0 ? "text-destructive" : "text-primary"}`}>
                              {p.residual > 0 ? "+" : ""}{formatCurrency(p.residual)}
                            </TableCell>
                            <TableCell className="text-right font-bold">{formatCurrency(p.final_prediction)}</TableCell>
                          </TableRow>
                        );
                      })}
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
