import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArrowDown, Database, Cpu, BrainCircuit, Activity, Target } from "lucide-react";
import { apiService } from "@/services/api";
import { MetricsSchema } from "@/types/api";

export const dynamic = "force-dynamic";

export default async function AboutPage() {
  let metricsData: MetricsSchema[] = [];
  try {
    metricsData = await apiService.getMetrics();
  } catch (error) {
    console.error("Failed to fetch metrics", error);
  }

  return (
    <div className="flex flex-col gap-8 max-w-5xl mx-auto w-full">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold tracking-tight">Metodologi & Arsitektur Sistem</h1>
        <p className="text-muted-foreground text-lg max-w-3xl mx-auto">
          Penjelasan rinci mengenai model Hybrid Prophet-XGBoost dan alur pemrosesan data untuk memprediksi harga beras Medium II.
        </p>
      </div>

      {/* Workflow Diagram */}
      <Card className="border-primary/20 shadow-lg">
        <CardHeader className="text-center pb-2">
          <CardTitle>Alur Prediksi Model Hybrid (Workflow)</CardTitle>
          <CardDescription>Diagram alir arsitektur sistem peramalan</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center gap-4 py-4 w-full">
            
            {/* Step 1 */}
            <div className="flex flex-col items-center justify-center p-4 w-64 rounded-xl bg-card border shadow-sm relative group transition-all hover:border-primary">
              <Database className="h-8 w-8 text-chart-2 mb-2" />
              <span className="font-semibold text-center">Historical Data</span>
              <span className="text-xs text-muted-foreground text-center">Time series Harga Beras</span>
            </div>

            <ArrowDown className="text-muted-foreground h-6 w-6" />

            {/* Step 2 */}
            <div className="flex flex-col items-center justify-center p-4 w-64 rounded-xl bg-card border shadow-sm relative group transition-all hover:border-primary">
              <Activity className="h-8 w-8 text-primary mb-2" />
              <span className="font-semibold text-center">Prophet Forecast</span>
              <span className="text-xs text-muted-foreground text-center">Trend linear & Seasonality</span>
            </div>

            <ArrowDown className="text-muted-foreground h-6 w-6" />

            {/* Step 3 */}
            <div className="flex flex-col items-center justify-center p-4 w-64 rounded-xl bg-secondary/20 border border-secondary shadow-sm">
              <BrainCircuit className="h-8 w-8 text-primary mb-2" />
              <span className="font-semibold text-center text-foreground">Residual Calculation</span>
              <span className="text-xs text-muted-foreground text-center">Error = Aktual - Prediksi Prophet</span>
            </div>

            <ArrowDown className="text-muted-foreground h-6 w-6" />

            {/* Step 4 */}
            <div className="flex flex-col items-center justify-center p-4 w-72 rounded-xl bg-card border shadow-sm relative group transition-all hover:border-primary">
              <Cpu className="h-8 w-8 text-chart-4 mb-2" />
              <span className="font-semibold text-center">XGBoost Residual Prediction</span>
              <span className="text-xs text-muted-foreground text-center">Faktor Eksternal: Hujan, Inflasi, Produksi, GKG</span>
            </div>

            <ArrowDown className="text-muted-foreground h-6 w-6" />

            {/* Step 5 */}
            <div className="flex flex-col items-center justify-center p-5 w-80 rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20 border-primary">
              <span className="font-bold text-lg text-center tracking-tight">Final Hybrid Forecast</span>
              <span className="text-sm opacity-90 text-center mt-1">Prediksi Prophet + Prediksi Residual XGBoost</span>
            </div>

          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sumber Data */}
        <Card>
          <CardHeader>
            <CardTitle>Sumber Data</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div>
              <p className="font-semibold text-foreground">PIHPS Nasional:</p>
              <ul className="list-disc pl-5"><li>Digunakan untuk data harga Beras Medium II DI Yogyakarta.</li></ul>
            </div>
            <div>
              <p className="font-semibold text-foreground">Badan Pusat Statistik (BPS):</p>
              <ul className="list-disc pl-5">
                <li>Digunakan untuk data harga Gabah Kering Giling (GKG).</li>
                <li>Digunakan untuk data produksi padi.</li>
                <li>Digunakan untuk data inflasi pangan.</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-foreground">NASA POWER:</p>
              <ul className="list-disc pl-5"><li>Digunakan untuk data curah hujan historis.</li></ul>
            </div>
            <p className="mt-4 italic pt-2 border-t">Seluruh data telah melalui proses integrasi dan transformasi sebelum digunakan pada model prediksi.</p>
          </CardContent>
        </Card>

        {/* Variabel Prediksi */}
        <Card>
          <CardHeader>
            <CardTitle>Variabel Prediksi</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <ul className="list-disc pl-5 space-y-1">
              <li>Harga Gabah Kering Giling (GKG)</li>
              <li>Curah Hujan</li>
              <li>Produksi Padi</li>
              <li>Inflasi Pangan</li>
              <li>Faktor Musiman Lebaran</li>
            </ul>
            <p className="mt-4 italic pt-2 border-t">Variabel tersebut digunakan sebagai faktor eksternal dalam proses prediksi residual menggunakan model XGBoost untuk meningkatkan hasil prediksi Prophet.</p>
          </CardContent>
        </Card>

        {/* Keterbatasan Sistem */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Keterbatasan Sistem</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <ul className="list-disc pl-5 space-y-2">
              <li>Prediksi merupakan estimasi berdasarkan data historis dan variabel eksternal yang tersedia.</li>
              <li>Perubahan kebijakan pemerintah, kondisi pasar, atau kejadian tak terduga dapat mempengaruhi harga aktual.</li>
              <li>Faktor eksternal yang tidak tersedia dalam dataset tidak dapat dimodelkan oleh sistem.</li>
              <li>Hasil prediksi tidak menjamin harga aktual pada masa mendatang.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tentang Hybrid Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-muted-foreground">
            <p>
              Pendekatan model tunggal seringkali kurang optimal dalam menangkap semua pola pada data time series ekonomi. Harga beras memiliki pola trend dan musiman (seasonality) yang kuat, tetapi juga rentan terhadap volatilitas jangka pendek akibat faktor cuaca atau kebijakan.
            </p>
            <p>
              Dengan arsitektur hybrid, kita menggabungkan kekuatan <strong>Facebook Prophet</strong> yang sangat baik dalam menangani pola musiman yang jelas, dengan <strong>XGBoost</strong>, algoritma machine learning berbasis tree yang handal dalam menemukan pola non-linear dari interaksi fitur-fitur eksternal (curah hujan, inflasi, dll) terhadap residual (error) dari Prophet.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recursive Forecasting</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-muted-foreground">
            <p>
              Dalam sistem ini, prediksi dilakukan menggunakan teknik <strong>Recursive Multi-step Forecasting</strong>. Untuk memprediksi harga beras hingga 12 bulan ke depan, model memprediksi harga di bulan pertama. Harga prediksi tersebut kemudian digunakan sebagai input (lag) untuk memprediksi harga di bulan kedua, dan seterusnya.
            </p>
            <p>
              Teknik ini memungkinkan kita untuk melihat tren harga jangka menengah tanpa harus melatih model terpisah untuk setiap periode kedepan, meskipun akumulasi error harus diawasi dengan cermat.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Technology Stack</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-card border text-center font-medium">Next.js App Router</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">Tailwind CSS v4</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">Recharts</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">FastAPI (Python)</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">Facebook Prophet</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">XGBoost</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">Pandas / Scikit-Learn</div>
            <div className="p-4 rounded-lg bg-card border text-center font-medium">TypeScript</div>
          </div>
        </CardContent>
      </Card>

      {metricsData.length > 0 && (
        <Card className="border-primary/20 shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Perbandingan Performa Model (Metrik Evaluasi)
            </CardTitle>
            <CardDescription>
              Tabel ini membandingkan tingkat error antara model dasar (Prophet) dan model hybrid. Model dengan MAPE terendah digunakan sebagai model final dalam sistem.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-75">Nama Model</TableHead>
                    <TableHead className="text-right">MAPE (%)</TableHead>
                    <TableHead className="text-right">MAE (Rp)</TableHead>
                    <TableHead className="text-right">RMSE (Rp)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {metricsData.map((m) => {
                    const formattedModelName = m.model
                      .split('_')
                      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                      .join(' ');
                      
                    return (
                    <TableRow key={m.model}>
                      <TableCell className="font-medium">{formattedModelName}</TableCell>
                      <TableCell className="text-right">{m.mape.toFixed(2)}%</TableCell>
                      <TableCell className="text-right">
                        {new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(m.mae)}
                      </TableCell>
                      <TableCell className="text-right">
                        {new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(m.rmse)}
                      </TableCell>
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
  );
}
