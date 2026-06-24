import type { ComponentPropsWithoutRef } from "react";

type BadgeVariant = "neutral" | "accent" | "success" | "warning" | "danger";

const variants: Record<BadgeVariant, string> = {
  neutral: "bg-white/[0.07] text-[#dce8e2] ring-white/12",
  accent: "bg-[var(--accent)]/12 text-[var(--accent)] ring-[var(--accent)]/25",
  success: "bg-emerald-400/12 text-emerald-200 ring-emerald-300/25",
  warning: "bg-amber-300/12 text-amber-100 ring-amber-200/25",
  danger: "bg-[var(--danger)]/12 text-[#ffb3b3] ring-[var(--danger)]/25",
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export type BadgeProps = ComponentPropsWithoutRef<"span"> & {
  variant?: BadgeVariant;
};

export function Badge({ className, variant = "accent", ...props }: BadgeProps) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium leading-none ring-1",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
