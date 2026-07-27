import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-extrabold transition duration-200 hover:-translate-y-0.5 disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-gradient-to-br from-cyan to-gold px-5 py-3 text-[#061014] shadow-glow",
        secondary: "border border-white/15 bg-white/8 px-5 py-3 text-white hover:border-cyan/50",
        ghost: "border border-white/10 bg-white/5 px-4 py-2 text-white hover:bg-white/10",
      },
      size: {
        default: "",
        lg: "px-7 py-4 text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ asChild = false, className, size, variant, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ className, size, variant }))} {...props} />;
}
