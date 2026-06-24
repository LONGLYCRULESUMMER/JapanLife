import type { ComponentPropsWithoutRef } from "react";

type PanelVariant = "default" | "elevated" | "accent" | "danger";

const variants: Record<PanelVariant, string> = {
  default: "bg-white/[0.045] ring-white/10",
  elevated: "bg-[var(--surface-elevated)]/85 ring-white/12 shadow-[0_24px_80px_rgb(0_0_0/0.22)]",
  accent: "bg-[var(--accent)]/[0.08] ring-[var(--accent)]/25",
  danger: "bg-[var(--danger)]/[0.08] ring-[var(--danger)]/25",
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export type PanelProps = ComponentPropsWithoutRef<"div"> & {
  variant?: PanelVariant;
};

export function Panel({ className, variant = "default", ...props }: PanelProps) {
  return (
    <div
      className={cx(
        "rounded-[var(--radius-card)] p-5 text-[#eff8f3] ring-1 backdrop-blur md:p-6",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export function PanelHeader({ className, ...props }: ComponentPropsWithoutRef<"div">) {
  return <div className={cx("mb-5 grid gap-2", className)} {...props} />;
}

export function PanelTitle({ className, ...props }: ComponentPropsWithoutRef<"h2">) {
  return <h2 className={cx("text-2xl font-semibold tracking-[-0.04em] text-[#eff8f3]", className)} {...props} />;
}

export function PanelDescription({ className, ...props }: ComponentPropsWithoutRef<"p">) {
  return <p className={cx("max-w-[65ch] text-sm leading-6 text-[var(--text-muted)]", className)} {...props} />;
}
