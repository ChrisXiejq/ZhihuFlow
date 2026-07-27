import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  action?: ReactNode;
}

export function Card({ action, children, className, title, ...props }: CardProps) {
  return (
    <article
      className={cn(
        "rounded-[26px] border border-white/10 bg-panel p-6 shadow-[0_22px_54px_rgba(0,0,0,0.26)] backdrop-blur-xl",
        className,
      )}
      {...props}
    >
      {(title || action) && (
        <div className="mb-5 flex items-center justify-between gap-4">
          {title ? <h3 className="text-[22px] font-extrabold tracking-tight text-white">{title}</h3> : <span />}
          {action}
        </div>
      )}
      {children}
    </article>
  );
}

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: "muted" | "ok" | "warn" }) {
  const toneClass =
    tone === "ok"
      ? "border-success/30 text-success"
      : tone === "warn"
        ? "border-gold/35 text-gold"
        : "border-white/10 text-slate-400";
  return <span className={cn("rounded-full border px-3 py-1 text-xs font-semibold", toneClass)}>{children}</span>;
}
