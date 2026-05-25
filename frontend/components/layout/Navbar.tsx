"use client";

import * as React from "react";
import { Moon, Sun, Menu } from "lucide-react";
import { useTheme } from "next-themes";
import { Button, buttonVariants } from "@/components/ui/button";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, LineChart, Database, Info } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";

const navItems = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "Forecast", href: "/forecast", icon: LineChart },
  { name: "Historical Data", href: "/historical", icon: Database },
  { name: "About", href: "/about", icon: Info },
];

export function Navbar() {
  const { theme, setTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="flex h-16 items-center px-4 md:px-6">
        <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
          <SheetTrigger className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "lg:hidden mr-2")}>
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle Menu</span>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0 flex flex-col bg-background">
            <SheetHeader className="p-6 text-left sr-only">
              <SheetTitle>Navigation Menu</SheetTitle>
            </SheetHeader>
            <div className="flex items-center gap-2 px-6 py-6 mt-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <LineChart size={18} />
              </div>
              <span className="text-lg font-bold tracking-tight text-foreground">RicePredict</span>
            </div>
            
            <nav className="flex flex-col gap-2 flex-1 px-4 mt-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-3 text-base font-medium transition-all duration-200",
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

            <div className="mt-auto p-4 mb-4">
              <div className="rounded-lg bg-secondary/10 p-4 border border-secondary/20">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Sistem Prediksi Harga Beras Medium II berbasis Hybrid Model Prophet dan XGBoost.
                </p>
              </div>
            </div>
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-2 lg:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <LineChart size={18} />
          </div>
          <span className="text-lg font-bold tracking-tight">RicePredict</span>
        </div>

        <div className="ml-auto flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            className="rounded-full"
          >
            <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
