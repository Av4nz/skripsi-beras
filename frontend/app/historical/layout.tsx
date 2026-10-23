import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data Historis",
  description:
    "Jelajahi data historis harga enam jenis beras di pasar tradisional DI Yogyakarta dari PIHPS.",
};

export default function HistoricalLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
