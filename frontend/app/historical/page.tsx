"use client";

import React, { useState, useEffect } from "react";
import { HargaBerasSchema } from "@/types/api";
import { apiService } from "@/services/api";
import { formatMonthYear, toCsv, downloadTextFile } from "@/lib/utils";
import { HistoricalChart } from "@/components/charts/HistoricalChart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, Search, ArrowUpDown, ChevronLeft, ChevronRight, Database, CalendarRange, Clock, Download, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function SortHead({
  label,
  k,
  align = "right",
  onSort,
}: {
  label: string;
  k: keyof HargaBerasSchema;
  align?: "left" | "right";
  onSort: (key: keyof HargaBerasSchema) => void;
}) {
  return (
    <TableHead className={align === "right" ? "text-right" : ""}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onSort(k)}
        className={`h-8 gap-1.5 px-2 text-muted-foreground hover:text-foreground ${align === "right" ? "-mr-2 ml-auto" : "-ml-2"}`}
      >
        {label} <ArrowUpDown className="size-3.5 opacity-60" />
      </Button>
    </TableHead>
  );
}

export default function HistoricalPage() {
  const [data, setData] = useState<HargaBerasSchema[]>([]);
  const [loading, setLoading] = useState(true);

  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: keyof HargaBerasSchema; direction: "asc" | "desc" } | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [rangeYears, setRangeYears] = useState<number | "all">("all");
  const itemsPerPage = 12;

  const RANGE_OPTIONS = [
    { label: "1 Thn", value: 1 },
    { label: "2 Thn", value: 2 },
    { label: "3 Thn", value: 3 },
    { label: "5 Thn", value: 5 },
    { label: "Semua", value: "all" },
  ] as const;

  useEffect(() => {
    async function loadData() {
      try {
        const hist = await apiService.getHistoricalData();
        setData(hist);
      } catch (error) {
        console.error("Failed to load historical data", error);
        toast.error("Gagal memuat data historis dari server", { id: "historical-data-error" });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const rangeFilteredData = React.useMemo(() => {
    if (rangeYears === "all" || data.length === 0) return data;
    const latest = new Date(data[data.length - 1].date);
    const cutoff = new Date(
      Date.UTC(latest.getUTCFullYear() - rangeYears, latest.getUTCMonth(), latest.getUTCDate())
    );
    return data.filter((item) => new Date(item.date) >= cutoff);
  }, [data, rangeYears]);

  const filteredData = React.useMemo(() => {
    let result = rangeFilteredData;
    if (searchTerm) {
      result = result.filter((item) => item.date.includes(searchTerm));
    }
    if (sortConfig !== null) {
      result = [...result].sort((a, b) => {
        const valA = a[sortConfig.key] ?? (typeof a[sortConfig.key] === "string" ? "" : 0);
        const valB = b[sortConfig.key] ?? (typeof b[sortConfig.key] === "string" ? "" : 0);
        if (valA < valB) return sortConfig.direction === "asc" ? -1 : 1;
        if (valA > valB) return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [rangeFilteredData, searchTerm, sortConfig]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const requestSort = (key: keyof HargaBerasSchema) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
    setCurrentPage(1);
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(val);

  const formatDate = (dateStr: string) =>
    new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" }).format(new Date(dateStr));

  const handleDownloadCsv = () => {
    if (filteredData.length === 0) {
      toast.error("Tidak ada data untuk diunduh");
      return;
    }
    const csv = toCsv(filteredData, [
      { label: "Tanggal", value: (r) => r.date },
      { label: "Bulan/Tahun", value: (r) => formatMonthYear(r.date) },
      { label: "Harga Beras (Rp)", value: (r) => r.price },
      { label: "Harga GKG (Rp)", value: (r) => r.harga_gkg ?? "" },
      { label: "Curah Hujan (mm)", value: (r) => r.curah_hujan ?? "" },
      { label: "Produksi Padi (Ton)", value: (r) => r.produksi_padi ?? "" },
      { label: "Inflasi Pangan (%)", value: (r) => r.inflasi_pangan ?? "" },
      { label: "Lebaran", value: (r) => r.lebaran },
    ]);
    const filename = `data-historis-beras_${filteredData[0].date}_${filteredData[filteredData.length - 1].date}.csv`;
    downloadTextFile(filename, csv);
    toast.success(`Berhasil mengunduh ${filteredData.length} baris data`);
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  const period =
    data.length > 0 ? `${formatMonthYear(data[0].date)} – ${formatMonthYear(data[data.length - 1].date)}` : "-";

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <header>
        <Badge variant="secondary" className="mb-4">
          <Database /> Dataset Penelitian
        </Badge>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Data Historis</h1>
        <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
          Jelajahi data historis harga beras dan faktor eksternal yang menjadi dasar pelatihan model prediksi.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <Badge variant="muted"><Database /> {data.length} baris</Badge>
          <Badge variant="muted"><CalendarRange /> {period}</Badge>
          <Badge variant="muted"><Clock /> Bulanan</Badge>
        </div>
      </header>

      {/* Chart */}
      <Card className="mt-10">
        <CardHeader className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <CardTitle>Tren Harga Beras &amp; Gabah</CardTitle>
            <CardDescription className="mt-1">
              Perbandingan harga Beras Medium II dengan harga Gabah Kering Giling (Rp/kg). Faktor lain
              (curah hujan, produksi, inflasi) tersedia pada tabel di bawah.
            </CardDescription>
          </div>
          <div
            role="group"
            aria-label="Pilih rentang waktu"
            className="inline-flex shrink-0 items-center gap-0.5 rounded-full border border-border/70 bg-muted/30 p-1"
          >
            {RANGE_OPTIONS.map((opt) => {
              const active = rangeYears === opt.value;
              return (
                <Button
                  key={opt.label}
                  variant={active ? "secondary" : "ghost"}
                  size="sm"
                  aria-pressed={active}
                  onClick={() => {
                    setRangeYears(opt.value);
                    setCurrentPage(1);
                  }}
                  className={`h-8 rounded-full px-3 text-xs ${active ? "" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {opt.label}
                </Button>
              );
            })}
          </div>
        </CardHeader>
        <CardContent>
          <HistoricalChart data={rangeFilteredData} className="h-[320px] sm:h-[420px]" />
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="mt-6">
        <CardHeader className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <CardTitle>Tabel Dataset</CardTitle>
            <CardDescription className="mt-1">Cari, urutkan, dan unduh data lengkap.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Cari tahun (mis. 2023)…"
                className="h-10 w-full pl-9 sm:w-56"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>
            <Button
              variant="outline"
              size="lg"
              onClick={handleDownloadCsv}
              disabled={filteredData.length === 0}
              className="shrink-0 rounded-full"
            >
              <Download className="size-4 sm:mr-1" />
              <span className="hidden sm:inline">Unduh CSV</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-xl border border-border/70">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40">
                  <SortHead label="Bulan/Tahun" k="date" align="left" onSort={requestSort} />
                  <SortHead label="Harga Beras" k="price" onSort={requestSort} />
                  <SortHead label="Harga GKG" k="harga_gkg" onSort={requestSort} />
                  <SortHead label="Curah Hujan (mm)" k="curah_hujan" onSort={requestSort} />
                  <SortHead label="Produksi (Ton)" k="produksi_padi" onSort={requestSort} />
                  <SortHead label="Inflasi (%)" k="inflasi_pangan" onSort={requestSort} />
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData.length > 0 ? (
                  paginatedData.map((row, i) => (
                    <TableRow key={row.date + i}>
                      <TableCell className="font-medium">{formatDate(row.date)}</TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">{formatCurrency(row.price)}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {row.harga_gkg != null ? formatCurrency(row.harga_gkg) : "-"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{row.curah_hujan ?? "-"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {row.produksi_padi != null ? row.produksi_padi.toLocaleString("id-ID") : "-"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {row.inflasi_pangan != null ? row.inflasi_pangan.toFixed(2) : "-"}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                      Data tidak ditemukan.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex flex-col items-center justify-between gap-3 sm:flex-row">
            <span className="text-sm text-muted-foreground">
              Menampilkan {filteredData.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1} –{" "}
              {Math.min(currentPage * itemsPerPage, filteredData.length)} dari {filteredData.length} data
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="size-4" /> Sebelumnya
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                disabled={currentPage >= totalPages || totalPages === 0}
              >
                Selanjutnya <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>

          <p className="mt-5 flex items-center gap-1.5 border-t border-border/60 pt-4 text-xs text-muted-foreground">
            <Sparkles className="size-3.5 text-secondary" />
            Sumber: PIHPS Nasional, Badan Pangan Nasional (Bapanas), Badan Pusat Statistik, dan Open-Meteo — telah diintegrasikan &amp; ditransformasi untuk pelatihan model.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
