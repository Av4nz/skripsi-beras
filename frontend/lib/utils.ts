import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a date string (e.g. "2021-01-01") as "Bulan Tahun" in Indonesian,
 * e.g. "Januari 2021". Uses UTC to avoid timezone drift.
 */
export function formatMonthYear(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return new Intl.DateTimeFormat("id-ID", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/** Escape a single CSV field per RFC 4180 (quote if it contains , " or newline). */
function escapeCsvField(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Build a CSV string from a list of headers and rows.
 * `headers` maps a column label to a getter over each row.
 */
export function toCsv<T>(
  rows: T[],
  headers: { label: string; value: (row: T) => unknown }[]
): string {
  const headerLine = headers.map((h) => escapeCsvField(h.label)).join(",");
  const dataLines = rows.map((row) =>
    headers.map((h) => escapeCsvField(h.value(row))).join(",")
  );
  return [headerLine, ...dataLines].join("\r\n");
}

/**
 * Trigger a browser download of `content` as a file. Prepends a UTF-8 BOM so
 * Excel opens accented/Unicode text correctly. Client-side only.
 */
export function downloadTextFile(
  filename: string,
  content: string,
  mime = "text/csv;charset=utf-8"
): void {
  const blob = new Blob(["﻿" + content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
