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
  Wheat,
  TrendingUp,
  BadgeInfo,
} from "lucide-react";
import { apiService } from "@/services/api";
import { RiceMetricRow } from "@/types/api";
import { cn, formatPersen } from "@/lib/utils";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Metodologi & Arsitektur",
  description:
    "Penjelasan metodologi prediksi harga beras (Prophet + XGBoost), pembanding sederhana, sumber data, dan keterbatasan sistem.",
};

export const dynamic = "force-dynamic";

const rupiah = (v: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(v);

const JENIS_ACUAN = "Medium II";
const NAMA_MODEL: Record<string, string> = {
  naive: "Harga bulan ini dipertahankan",
  arima: "ARIMA(1,1,0)",
  prophet: "Prophet",
  hybrid: "Hybrid (Prophet + XGBoost)",
};
const URUTAN_MODEL = ["naive", "arima", "prophet", "hybrid"];

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
    items: [
      "Harga beras DI Yogyakarta menurut jenis: Bawah I dan II, Medium I dan II, Super I dan II",
      "Rata-rata harian per bulan. Penelitian memakai Januari 2021 sampai Mei 2026, bulan baru ditambahkan otomatis setiap bulan",
    ],
    iconClass: "bg-primary/10 text-primary",
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
  let metrik: RiceMetricRow[] = [];
  let protokol = "";
  try {
    const m = await apiService.getMetrik(JENIS_ACUAN);
    metrik = m.metrik;
    protokol = m.protokol;
  } catch (error) {
    console.error("Failed to fetch metrics", error);
  }
  const baris = (model: string, h: number) => metrik.find((x) => x.model === model && x.horizon === h);
  const HORIZON_TAMPIL = [1, 3, 6];

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
          memproyeksikan harga beras menurut jenis, lalu membandingkannya secara terbuka dengan dua
          pembanding sederhana.
        </p>
      </header>

      {/* Workflow */}
      <Card className="mt-12">
        <CardHeader className="text-center">
          <CardTitle>Alur Model Hybrid</CardTitle>
          <CardDescription>Dari riwayat harga hingga prediksi akhir</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-2">
            <FlowStep
              icon={<Database />}
              iconClass="bg-secondary/15 text-secondary dark:text-secondary-foreground"
              title="Riwayat Harga"
              desc="Deret waktu bulanan harga satu jenis beras"
            />
            <ArrowDown className="size-5 text-muted-foreground" />
            <FlowStep
              icon={<Activity />}
              iconClass="bg-primary/10 text-primary"
              title="Prediksi Prophet"
              desc="Menangkap tren dan pola musiman tahunan dari riwayat harga"
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
              title="XGBoost Koreksi Residual"
              desc="Mengoreksi sisa galat dari pola riwayat harga (lag dan residual)"
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
        <div className="grid gap-5 sm:grid-cols-2">
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
              punya tren dan pola musiman, tetapi juga dipengaruhi cuaca dan kebijakan.
            </p>
            <p>
              Arsitektur hybrid menggabungkan <span className="font-medium text-foreground">Prophet</span>{" "}
              (tren dan pola musiman) dengan{" "}
              <span className="font-medium text-foreground">XGBoost</span>{" "}
              (mengoreksi sisa galat Prophet dari pola riwayat harga). Keunggulannya diuji secara
              terbuka terhadap pembanding sederhana di bawah.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Prediksi Beberapa Bulan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-muted-foreground">
            <p>
              Prediksi lebih dari satu bulan memakai{" "}
              <span className="font-medium text-foreground">recursive multi-step forecasting</span>: hasil
              bulan pertama menjadi masukan bulan berikutnya.
            </p>
            <p>
              Galat membesar seiring jumlah bulan, seperti terlihat pada tabel pengujian di bawah. Karena
              itu satu bulan ke depan adalah horizon yang paling dapat dipertanggungjawabkan.
            </p>
          </CardContent>
        </Card>

        {/* Tanpa faktor eksternal */}
        <Card>
          <CardHeader>
            <CardTitle>Tanpa Faktor Eksternal</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Model hanya memakai <span className="font-medium text-foreground">riwayat harga beras
              per jenis</span> dan pola bulan dalam setahun. Pengguna tidak memasukkan faktor apa pun.
              Pada pengujian, menambahkan faktor eksternal seperti harga gabah, curah hujan, produksi
              padi, dan inflasi pangan tidak meningkatkan ketepatan prediksi harga bulan berikutnya,
              sehingga faktor tersebut tidak dipakai dan tidak ditampilkan.
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
                "Prediksi adalah estimasi dari pola riwayat harga, bukan kepastian harga.",
                "Pada data pengujian, mempertahankan harga bulan ini lebih akurat daripada model hybrid.",
                "Hasil pengujian memakai 65 bulan (Januari 2021 sampai Mei 2026) dan satu wilayah, DI Yogyakarta. Bulan yang ditambahkan sesudahnya ikut memperbarui model tetapi tidak dihitung ulang dalam tabel pengujian.",
                "Keenam jenis beras bergerak serempak, sehingga hasil per jenis bukan bukti yang saling bebas.",
                "Kebijakan pemerintah, kondisi pasar, atau kejadian tak terduga dapat memengaruhi harga aktual.",
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

      {/* Perbandingan model dari hasil pengujian */}
      {metrik.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="size-5 text-primary" />
              Hasil Pengujian Model
            </CardTitle>
            <CardDescription>
              MAPE (%) untuk Beras {JENIS_ACUAN}, semakin kecil semakin baik. Model sistem adalah
              Hybrid. {protokol && `Protokol: ${protokol}.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40">
                    <TableHead>Model</TableHead>
                    {HORIZON_TAMPIL.map((h) => (
                      <TableHead key={h} className="text-right">
                        {h} bulan
                      </TableHead>
                    ))}
                    <TableHead className="text-right">MAE 1 bulan (Rp)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {URUTAN_MODEL.map((model) => (
                    <TableRow key={model} className={model === "hybrid" ? "bg-primary/5" : undefined}>
                      <TableCell className="font-medium">
                        <span className="flex items-center gap-2">
                          {NAMA_MODEL[model]}
                          {model === "hybrid" && <Badge variant="success">Model sistem</Badge>}
                        </span>
                      </TableCell>
                      {HORIZON_TAMPIL.map((h) => (
                        <TableCell key={h} className="text-right tabular-nums">
                          {baris(model, h) ? formatPersen(baris(model, h)!.mape) : "-"}
                        </TableCell>
                      ))}
                      <TableCell className="text-right tabular-nums">
                        {baris(model, 1) ? rupiah(baris(model, 1)!.mae) : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Pada data ini, mempertahankan harga bulan ini dan ARIMA lebih akurat daripada model hybrid,
              dan galat hybrid membesar tajam untuk beberapa bulan ke depan. Harga beras DIY sangat
              stabil: pada sebagian besar bulan, harganya tidak berubah dari bulan sebelumnya. Hasil ini diuji pada
              data lampau dan tidak menjamin harga di masa depan.
            </p>
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
