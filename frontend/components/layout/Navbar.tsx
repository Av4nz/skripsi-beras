"use client";

import * as React from "react";
import { Moon, Sun, Menu, Wheat, Home, LineChart, Database, Info } from "lucide-react";
import { useTheme } from "next-themes";
import { Button, buttonVariants } from "@/components/ui/button";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";

const navItems = [
  { name: "Beranda", href: "/", icon: Home },
  { name: "Prediksi", href: "/forecast", icon: LineChart },
  { name: "Data Historis", href: "/historical", icon: Database },
  { name: "Tentang", href: "/about", icon: Info },
];

function Brand({ onClick }: { onClick?: () => void }) {
  return (
    <Link href="/" onClick={onClick} className="group flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/30 transition-transform group-hover:-rotate-6">
        <Wheat size={20} />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-heading text-lg font-semibold tracking-tight text-foreground">
          RicePredict
        </span>
        <span className="text-[0.7rem] font-medium uppercase tracking-wider text-muted-foreground">
          Harga Beras · DIY
        </span>
      </span>
    </Link>
  );
}

export function Navbar() {
  const { resolvedTheme, setTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        {/* Mobile menu */}
        <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
          <SheetTrigger className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "lg:hidden")}>
            <Menu className="h-5 w-5" />
            <span className="sr-only">Buka menu</span>
          </SheetTrigger>
          <SheetContent side="left" className="flex w-72 flex-col gap-0 bg-background p-0">
            <SheetHeader className="border-b p-6 text-left">
              <SheetTitle className="sr-only">Menu Navigasi</SheetTitle>
              <Brand onClick={() => setIsMobileMenuOpen(false)} />
            </SheetHeader>
            <nav className="flex flex-1 flex-col gap-1 p-4">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-3 text-base font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon size={18} />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            <div className="border-t p-4">
              <Link
                href="/forecast"
                onClick={() => setIsMobileMenuOpen(false)}
                className={cn(buttonVariants({ size: "lg" }), "w-full")}
              >
                Coba Prediksi Harga
              </Link>
            </div>
          </SheetContent>
        </Sheet>

        <Brand />

        {/* Desktop nav */}
        <nav className="ml-6 hidden items-center gap-1 lg:flex">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.name}
                {isActive && (
                  <span className="absolute inset-x-3.5 -bottom-px h-0.5 rounded-full bg-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="rounded-full text-muted-foreground hover:text-foreground"
            aria-label="Ganti tema terang/gelap"
          >
            <Sun className="h-[1.15rem] w-[1.15rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
            <Moon className="absolute h-[1.15rem] w-[1.15rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          </Button>
          <Link
            href="/forecast"
            className={cn(buttonVariants({ size: "lg" }), "hidden rounded-full px-5 sm:inline-flex")}
          >
            Coba Prediksi
          </Link>
        </div>
      </div>
    </header>
  );
}
