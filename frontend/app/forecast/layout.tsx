import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Prediksi Harga Beras",
  description:
    "Prediksi harga beras per jenis di DI Yogyakarta untuk 1 sampai 6 bulan ke depan, dibandingkan dengan pembanding sederhana.",
};

export default function ForecastLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
