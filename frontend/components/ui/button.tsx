import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import { Loader2 } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-accent text-accent-fg shadow-card hover:bg-accent-hover",
        secondary: "border border-border bg-surface text-text shadow-card hover:bg-surface-2",
        ghost: "text-text-2 hover:bg-surface-2 hover:text-text",
        danger: "bg-danger text-white shadow-card hover:opacity-90",
        link: "h-auto px-0 text-accent underline-offset-4 hover:underline",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-11 px-5 text-[15px]", icon: "size-9" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export function Button({ className, variant, size, asChild, loading, children, disabled, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  return (
    <Comp className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>
      {asChild ? children : (
        <>
          {loading && <Loader2 className="animate-spin" aria-hidden />}
          {children}
        </>
      )}
    </Comp>
  );
}

export { buttonVariants };
