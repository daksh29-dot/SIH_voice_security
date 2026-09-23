"use client";

import * as React from "react"
import { motion, HTMLMotionProps } from "framer-motion"
import { cn } from "@/lib/utils"

export interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "default", disabled, ...props }, ref) => {
    return (
      <motion.button
        ref={ref}
        whileTap={disabled ? undefined : { scale: 0.98 }}
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center rounded-sm text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-border focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
          {
            "bg-foreground text-background shadow-sm hover:bg-foreground/90": variant === "primary",
            "bg-surface-secondary text-foreground border border-border shadow-sm hover:bg-surface-secondary/80": variant === "secondary",
            "hover:bg-surface-secondary hover:text-foreground": variant === "ghost",
            "border border-border bg-transparent shadow-sm hover:bg-surface-secondary hover:text-foreground": variant === "outline",
            "bg-danger text-foreground shadow-sm hover:bg-danger/90 focus-visible:ring-danger": variant === "danger",
            
            "h-9 px-4 py-2": size === "default",
            "h-8 px-3 text-xs": size === "sm",
            "h-10 px-8": size === "lg",
            "h-9 w-9": size === "icon",
          },
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
