"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, LineChart, Database, Info } from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "Forecast", href: "/forecast", icon: LineChart },
  { name: "Historical Data", href: "/historical", icon: Database },
  { name: "About", href: "/about", icon: Info },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex w-64 flex-col border-r bg-card/50 backdrop-blur-sm px-4 py-6 sticky top-0 h-screen">
      <Link className="flex items-center gap-2 px-2 mb-8" href="/">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <LineChart size={18} />
        </div>
        <span className="text-lg font-bold tracking-tight text-foreground">RicePredict</span>
      </Link>

      <nav className="flex flex-col gap-2 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium transition-all duration-200",
                isActive 
                  ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
                  : "text-muted-foreground hover:bg-secondary/20 hover:text-foreground"
              )}
            >
              <Icon size={18} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-2">
        <div className="rounded-lg bg-secondary/10 p-4 border border-secondary/20">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Sistem Prediksi Harga Beras Medium II berbasis Hybrid Model Prophet dan XGBoost.
          </p>
        </div>
      </div>
    </aside>
  );
}
