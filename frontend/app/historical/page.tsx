"use client";

import React, { useState, useEffect } from "react";
import { HargaBerasSchema } from "@/types/api";
import { apiService } from "@/services/api";
import { HistoricalChart } from "@/components/charts/HistoricalChart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, Search, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HistoricalPage() {
  const [data, setData] = useState<HargaBerasSchema[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filter/Sort/Pagination states
  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: keyof HargaBerasSchema; direction: "asc" | "desc" } | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12;

  useEffect(() => {
    async function loadData() {
      try {
        const hist = await apiService.getHistoricalData();
        setData(hist);
      } catch (error) {
        console.error("Failed to load historical data", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredData = React.useMemo(() => {
    let result = data;
    
    // Apply search filter (by year/date)
    if (searchTerm) {
      result = result.filter(item => 
        item.date.includes(searchTerm)
      );
    }
    
    // Apply sorting
    if (sortConfig !== null) {
      result = [...result].sort((a, b) => {
        const valA = a[sortConfig.key] ?? (typeof a[sortConfig.key] === 'string' ? "" : 0);
        const valB = b[sortConfig.key] ?? (typeof b[sortConfig.key] === 'string' ? "" : 0);
        if (valA < valB) {
          return sortConfig.direction === "asc" ? -1 : 1;
        }
        if (valA > valB) {
          return sortConfig.direction === "asc" ? 1 : -1;
        }
        return 0;
      });
    }
    
    return result;
  }, [data, searchTerm, sortConfig]);

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

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" }).format(d);
  };

  if (loading) {
    return (
      <div className="flex h-full min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dataset Historis</h1>
        <p className="text-muted-foreground mt-2">
          Eksplorasi data historis harga beras dan faktor eksternal yang digunakan untuk melatih model prediksi.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Visualisasi Tren Faktor Eksternal</CardTitle>
          <CardDescription>Perbandingan Harga Beras, Harga GKG, dan Inflasi</CardDescription>
        </CardHeader>
        <CardContent>
          <HistoricalChart data={data} height={400} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <div className="space-y-1">
            <CardTitle>Tabel Dataset Utama</CardTitle>
            <CardDescription>Menampilkan {filteredData.length} baris data</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Cari tahun (ex: 2023)..."
                className="w-64 pl-8"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <Button variant="ghost" onClick={() => requestSort("date")} className="hover:bg-transparent -ml-4 px-4">
                      Bulan/Tahun <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button variant="ghost" onClick={() => requestSort("price")} className="hover:bg-transparent justify-end w-full pr-0">
                      Harga Beras <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button variant="ghost" onClick={() => requestSort("harga_gkg")} className="hover:bg-transparent justify-end w-full pr-0">
                      Harga GKG <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button variant="ghost" onClick={() => requestSort("curah_hujan")} className="hover:bg-transparent justify-end w-full pr-0">
                      Curah Hujan (mm) <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button variant="ghost" onClick={() => requestSort("produksi_padi")} className="hover:bg-transparent justify-end w-full pr-0">
                      Produksi Padi (Ton) <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button variant="ghost" onClick={() => requestSort("inflasi_pangan")} className="hover:bg-transparent justify-end w-full pr-0">
                      Inflasi (%) <ArrowUpDown className="ml-2 h-4 w-4" />
                    </Button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData.length > 0 ? (
                  paginatedData.map((row, i) => (
                    <TableRow key={row.date + i}>
                      <TableCell className="font-medium">{formatDate(row.date)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(row.price)}</TableCell>
                      <TableCell className="text-right text-muted-foreground">{row.harga_gkg != null ? formatCurrency(row.harga_gkg) : "-"}</TableCell>
                      <TableCell className="text-right">{row.curah_hujan ?? "-"}</TableCell>
                      <TableCell className="text-right">{row.produksi_padi != null ? row.produksi_padi.toLocaleString("id-ID") : "-"}</TableCell>
                      <TableCell className="text-right">{row.inflasi_pangan != null ? row.inflasi_pangan.toFixed(2) : "-"}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="h-24 text-center">
                      Data tidak ditemukan.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-muted-foreground">
              Menampilkan {filteredData.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredData.length)} dari {filteredData.length} data
            </span>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Sebelumnya
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage >= totalPages || totalPages === 0}
              >
                Selanjutnya <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
