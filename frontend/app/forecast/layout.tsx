import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Simulasi Prediksi",
  description:
    "Simulasikan prediksi harga beras dengan menyesuaikan faktor eksternal seperti curah hujan, produksi padi, inflasi, dan harga GKG.",
};

export default function ForecastLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
