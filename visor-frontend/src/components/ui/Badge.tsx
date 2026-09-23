import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "warning" | "danger" | "outline";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-sm border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        {
          "border-border bg-surface-secondary text-foreground": variant === "default",
          "border-success/30 bg-success/10 text-success": variant === "success",
          "border-warning/30 bg-warning/10 text-warning": variant === "warning",
          "border-danger/30 bg-danger/10 text-danger": variant === "danger",
          "border-border bg-transparent text-foreground": variant === "outline",
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }
