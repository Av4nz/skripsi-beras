import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data Historis",
  description:
    "Jelajahi data historis harga beras medium II DI Yogyakarta beserta faktor-faktor eksternal yang memengaruhinya.",
};

export default function HistoricalLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
