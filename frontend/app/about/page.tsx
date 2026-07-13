import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  ArrowDown,
  Database,
  Cpu,
  BrainCircuit,
  Activity,
  Target,
  Sigma,
  CloudRain,
  Wheat,
  TrendingUp,
  BadgeInfo,
} from "lucide-react";
import { apiService } from "@/services/api";
import { MetricsSchema } from "@/types/api";
import { cn } from "@/lib/utils";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Metodologi & Arsitektur",
  description:
    "Penjelasan metodologi Hybrid Forecasting (Prophet + XGBoost), sumber data, dan arsitektur sistem prediksi harga beras.",
};

export const dynamic = "force-dynamic";

const rupiah = (v: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(v);

function FlowStep({
  icon,
  iconClass,
  title,
  desc,
  highlight,
}: {
  icon: React.ReactNode;
  iconClass?: string;
  title: string;
  desc: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex w-full max-w-md items-center gap-4 rounded-2xl border p-4 transition-colors",
        highlight
          ? "border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/20"
          : "border-border/60 bg-card hover:border-primary/40"
      )}
    >
      <span
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-xl [&_svg]:size-5",
          highlight ? "bg-white/15 text-primary-foreground" : iconClass
        )}
      >
        {icon}
      </span>
      <div>
        <p className={cn("font-semibold", highlight ? "text-primary-foreground" : "text-foreground")}>{title}</p>
        <p className={cn("text-sm", highlight ? "text-primary-foreground/85" : "text-muted-foreground")}>{desc}</p>
      </div>
    </div>
  );
}

const dataSources = [
  {
    icon: <Wheat />,
    name: "PIHPS Nasional",
    items: ["Harga Beras Medium II — DI Yogyakarta (variabel target)"],
    iconClass: "bg-primary/10 text-primary",
  },
  {
    icon: <Database />,
    name: "Badan Pusat Statistik (BPS)",
    items: ["Harga Gabah Kering Giling (GKG)", "Produksi padi", "Inflasi pangan"],
    iconClass: "bg-secondary/15 text-secondary dark:text-secondary-foreground",
  },
  {
    icon: <CloudRain />,
    name: "NASA POWER",
    items: ["Curah hujan historis (berbasis satelit)"],
    iconClass: "bg-accent/20 text-accent-foreground dark:text-accent",
  },
];

const techStack = [
  "Next.js 16",
  "React 19",
  "Tailwind CSS v4",
  "Recharts",
  "FastAPI (Python)",
  "Facebook Prophet",
  "XGBoost",
  "Pandas / Scikit-Learn",
  "PostgreSQL",
  "TypeScript",
];

export default async function AboutPage() {
  let metricsData: MetricsSchema[] = [];
  try {
    metricsData = await apiService.getMetrics();
  } catch (error) {
    console.error("Failed to fetch metrics", error);
  }

  const bestMape = metricsData.length ? Math.min(...metricsData.map((m) => m.mape)) : null;

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      {/* Header */}
      <header className="text-center">
        <Badge variant="secondary" className="mb-4">
          <BadgeInfo /> Metodologi
        </Badge>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">
          Bagaimana prediksi ini dibuat
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Sistem menggabungkan <span className="font-medium text-foreground">Prophet</span> dan{" "}
          <span className="font-medium text-foreground">XGBoost</span> dalam satu model hybrid untuk
          memprediksi harga Beras Medium II secara akurat dan transparan.
        </p>
      </header>

      {/* Workflow */}
      <Card className="mt-12">
        <CardHeader className="text-center">
          <CardTitle>Alur Model Hybrid</CardTitle>
          <CardDescription>Dari data historis hingga prediksi akhir</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-2">
            <FlowStep
              icon={<Database />}
              iconClass="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              title="Data Historis"
              desc="Deret waktu bulanan harga beras + faktor eksternal"
            />
            <ArrowDown className="size-5 text-muted-foreground" />
            <FlowStep
              icon={<Activity />}
              iconClass="bg-primary/10 text-primary"
              title="Prediksi Prophet"
              desc="Menangkap tren & pola musiman"
            />
            <ArrowDown className="size-5 text-muted-foreground" />
            <FlowStep
              icon={<Sigma />}
              iconClass="bg-accent/20 text-accent-foreground dark:text-accent"
              title="Hitung Residual"
              desc="Residual = harga aktual − prediksi Prophet"
            />
            <ArrowDown className="size-5 text-muted-foreground" />
            <FlowStep
              icon={<Cpu />}
              iconClass="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              title="XGBoost Prediksi Residual"
              desc="Belajar dari curah hujan, inflasi, produksi, GKG, Lebaran"
            />
            <ArrowDown className="size-5 text-muted-foreground" />
            <FlowStep
              icon={<BrainCircuit />}
              title="Prediksi Hybrid Final"
              desc="Prediksi Prophet + koreksi residual XGBoost"
              highlight
            />
          </div>
        </CardContent>
      </Card>

      {/* Data sources */}
      <section className="mt-6">
        <div className="grid gap-5 md:grid-cols-3">
          {dataSources.map((s) => (
            <Card key={s.name} className="h-full gap-3">
              <CardHeader className="flex flex-row items-center gap-3">
                <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl [&_svg]:size-5", s.iconClass)}>
                  {s.icon}
                </span>
                <CardTitle className="text-base">{s.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5 text-sm text-muted-foreground">
                  {s.items.map((it) => (
                    <li key={it} className="flex gap-2">
                      <span className="mt-2 size-1 shrink-0 rounded-full bg-primary" />
                      {it}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Explanations */}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Mengapa Hybrid?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-muted-foreground">
            <p>
              Model tunggal sering kurang optimal menangkap semua pola pada data ekonomi. Harga beras
              punya tren &amp; musiman yang kuat, tetapi juga volatil akibat cuaca dan kebijakan.
            </p>
            <p>
              Arsitektur hybrid menggabungkan <span className="font-medium text-foreground">Prophet</span>{" "}
              (unggul pada pola musiman) dengan <span className="font-medium text-foreground">XGBoost</span>{" "}
              (unggul menemukan pola non-linear faktor eksternal terhadap residual Prophet).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recursive Forecasting</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-muted-foreground">
            <p>
              Prediksi multi-periode memakai <span className="font-medium text-foreground">recursive
              multi-step forecasting</span>: hasil bulan pertama menjadi input (lag) untuk bulan
              berikutnya, dan seterusnya.
            </p>
            <p>
              Teknik ini menampilkan tren jangka menengah dengan satu model, meski akumulasi galat perlu
              diawasi dengan cermat.
            </p>
          </CardContent>
        </Card>

        {/* Variabel */}
        <Card>
          <CardHeader>
            <CardTitle>Variabel Prediksi (Faktor Eksternal)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {["Harga GKG", "Curah Hujan", "Produksi Padi", "Inflasi Pangan", "Faktor Lebaran"].map((v) => (
                <Badge key={v} variant="muted">
                  {v}
                </Badge>
              ))}
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Variabel ini dipakai XGBoost untuk memprediksi residual dan menajamkan hasil Prophet.
            </p>
          </CardContent>
        </Card>

        {/* Keterbatasan */}
        <Card>
          <CardHeader>
            <CardTitle>Keterbatasan Sistem</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {[
                "Prediksi adalah estimasi berbasis data historis & variabel yang tersedia.",
                "Kebijakan pemerintah, kondisi pasar, atau kejadian tak terduga dapat memengaruhi harga aktual.",
                "Faktor di luar dataset tidak dapat dimodelkan sistem.",
                "Hasil prediksi tidak menjamin harga aktual di masa mendatang.",
              ].map((it) => (
                <li key={it} className="flex gap-2">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-muted-foreground/60" />
                  {it}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Metrics comparison */}
      {metricsData.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="size-5 text-primary" />
              Perbandingan Performa Model
            </CardTitle>
            <CardDescription>
              Error antar-model pada data uji. Model dengan MAPE terendah dipakai sebagai model final.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40">
                    <TableHead>Model</TableHead>
                    <TableHead className="text-right">MAPE (%)</TableHead>
                    <TableHead className="text-right">MAE (Rp)</TableHead>
                    <TableHead className="text-right">RMSE (Rp)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {metricsData.map((m) => {
                    const name = m.model
                      .split("_")
                      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                      .join(" ");
                    const isBest = bestMape !== null && m.mape === bestMape;
                    return (
                      <TableRow key={m.model} className={isBest ? "bg-primary/5" : undefined}>
                        <TableCell className="font-medium">
                          <span className="flex items-center gap-2">
                            {name}
                            {isBest && <Badge variant="success">Final</Badge>}
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{m.mape.toFixed(2)}%</TableCell>
                        <TableCell className="text-right tabular-nums">{rupiah(m.mae)}</TableCell>
                        <TableCell className="text-right tabular-nums">{rupiah(m.rmse)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tech stack */}
      <section className="mt-12 text-center">
        <h2 className="flex items-center justify-center gap-2 font-heading text-xl font-semibold tracking-tight">
          <TrendingUp className="size-5 text-primary" /> Teknologi yang Digunakan
        </h2>
        <div className="mt-5 flex flex-wrap justify-center gap-2.5">
          {techStack.map((t) => (
            <span
              key={t}
              className="rounded-full border border-border/70 bg-card px-4 py-1.5 text-sm font-medium text-foreground shadow-sm"
            >
              {t}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
