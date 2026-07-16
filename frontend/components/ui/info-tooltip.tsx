"use client"

import * as React from "react"
import { Popover as PopoverPrimitive } from "@base-ui/react/popover"
import { Info } from "lucide-react"

import { cn } from "@/lib/utils"

type Side = "top" | "right" | "bottom" | "left"

interface InfoTooltipProps {
  /** Teks penjelasan yang ditampilkan. */
  content: React.ReactNode
  /** Sisi popup terhadap ikon. */
  side?: Side
  /** Label aksesibilitas untuk trigger (dibaca screen reader). */
  label?: string
  /** Kelas tambahan untuk ikon trigger. */
  className?: string
  /** Ganti ikon default (Info) bila perlu. */
  children?: React.ReactNode
}

/**
 * Tooltip informasi yang bekerja di desktop maupun mobile.
 *
 * Dibangun di atas Base UI Popover, bukan atribut `title` HTML (yang hanya
 * muncul saat hover di desktop). Popup terbuka saat hover memakai pointer mouse
 * (desktop) dan saat tap/klik (semua perangkat), lalu tertutup dengan tap di
 * luar area atau menekan Escape.
 */
function InfoTooltip({
  content,
  side = "top",
  label = "Informasi",
  className,
  children,
}: InfoTooltipProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger
        aria-label={label}
        // Hover hanya untuk pointer mouse; perangkat sentuh memakai tap (klik).
        onPointerEnter={(event) => {
          if (event.pointerType === "mouse") setOpen(true)
        }}
        onPointerLeave={(event) => {
          if (event.pointerType === "mouse") setOpen(false)
        }}
        className={cn(
          "inline-flex cursor-help items-center justify-center rounded-full text-muted-foreground/60 outline-none transition-colors hover:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/50 data-popup-open:text-muted-foreground",
          className
        )}
      >
        {children ?? <Info className="h-3.5 w-3.5" />}
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Positioner side={side} sideOffset={6} collisionPadding={8} className="z-50">
          <PopoverPrimitive.Popup
            className={cn(
              "max-w-[min(18rem,calc(100vw-1rem))] rounded-lg border bg-popover px-3 py-2 text-xs leading-relaxed text-popover-foreground shadow-md",
              "origin-[var(--transform-origin)] transition-[transform,opacity] duration-150",
              "data-starting-style:scale-95 data-starting-style:opacity-0 data-ending-style:scale-95 data-ending-style:opacity-0"
            )}
          >
            {content}
          </PopoverPrimitive.Popup>
        </PopoverPrimitive.Positioner>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}

export { InfoTooltip }
