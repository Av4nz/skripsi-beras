import Link from "next/link";
import { Wheat } from "lucide-react";

const navLinks = [
  { name: "Beranda", href: "/" },
  { name: "Prediksi", href: "/forecast" },
  { name: "Data Historis", href: "/historical" },
  { name: "Tentang", href: "/about" },
];

const dataSources = [
  { name: "PIHPS Nasional", detail: "Harga Beras", href: "https://www.bi.go.id/hargapangan" },
  { name: "Badan Pangan Nasional", detail: "GKG", href: "https://data.badanpangan.go.id" },
  { name: "Badan Pusat Statistik", detail: "Produksi · Inflasi", href: "https://www.bps.go.id" },
  { name: "Open-Meteo", detail: "Curah Hujan", href: "https://open-meteo.com" },
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-20 border-t border-border/60 bg-section-muted">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div className="lg:col-span-2 lg:pr-10">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Wheat size={20} />
              </span>
              <span className="font-heading text-lg font-semibold tracking-tight text-foreground">
                RicePredict
              </span>
            </div>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
              Sistem prediksi harga Beras Medium II di Daerah Istimewa Yogyakarta
              berbasis <span className="font-medium text-foreground">Hybrid Model</span> (Prophet + XGBoost).
              Menyajikan informasi harga yang akurat dan transparan untuk masyarakat.
            </p>
          </div>

          {/* Nav */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Navigasi
            </h3>
            <ul className="mt-4 space-y-2.5">
              {navLinks.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-primary"
                  >
                    {l.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Data sources — mendukung transparansi (Disclosure) */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Sumber Data
            </h3>
            <ul className="mt-4 space-y-2.5">
              {dataSources.map((s) => (
                <li key={s.name}>
                  <a
                    href={s.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group block text-sm text-muted-foreground transition-colors hover:text-primary"
                  >
                    <span className="font-medium text-foreground group-hover:text-primary">
                      {s.name}
                    </span>
                    <span className="block text-xs text-muted-foreground">{s.detail}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} RicePredict · Tugas Akhir Skripsi</p>
          <p className="max-w-lg sm:text-right">
            Hasil prediksi bersifat estimasi berbasis data historis dan tidak menjamin harga aktual di pasar.
          </p>
        </div>
      </div>
    </footer>
  );
}
