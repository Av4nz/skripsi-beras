import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  className?: string;
}

export function MetricCard({
  title,
  value,
  description,
  icon,
  trend,
  trendValue,
  className,
}: MetricCardProps) {
  return (
    <Card className={cn("overflow-hidden transition-all hover:shadow-md hover:border-primary/50", className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {(description || trendValue) && (
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
            {trendValue && (
              <span
                className={cn(
                  "font-medium",
                  trend === "up" ? "text-destructive" : trend === "down" ? "text-primary" : "text-muted-foreground"
                )}
              >
                {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"} {trendValue}
              </span>
            )}
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
