import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Info, TrendingDown, TrendingUp, Minus } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  /** Extra classes for the icon chip (e.g. change its tint). */
  iconClassName?: string;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  className?: string;
  tooltip?: string;
}

export function MetricCard({
  title,
  value,
  description,
  icon,
  iconClassName,
  trend,
  trendValue,
  className,
  tooltip,
}: MetricCardProps) {
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendVariant = trend === "up" ? "destructive" : trend === "down" ? "success" : "muted";

  return (
    <Card
      className={cn(
        "gap-3 transition-all hover:ring-primary/30 hover:shadow-md hover:shadow-primary/5",
        className
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          {tooltip && (
            <span
              title={tooltip}
              className="cursor-help text-muted-foreground/60 transition-colors hover:text-muted-foreground"
            >
              <Info className="h-3.5 w-3.5" />
            </span>
          )}
        </div>
        {icon && (
          <span
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary [&_svg]:size-5",
              iconClassName
            )}
          >
            {icon}
          </span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <div className="font-sans text-3xl font-bold tracking-tight tabular-nums text-foreground sm:text-[2.1rem]">
          {value}
        </div>
        {(description || trendValue) && (
          <div className="flex flex-wrap items-center gap-2">
            {trendValue && (
              <Badge variant={trendVariant}>
                <TrendIcon />
                {trendValue}
              </Badge>
            )}
            {description && (
              <span className="text-sm text-muted-foreground">{description}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
