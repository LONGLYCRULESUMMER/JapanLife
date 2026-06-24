import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const baseClasses =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-semibold outline-none transition-[background-color,border-color,color,box-shadow,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-55 aria-disabled:pointer-events-none aria-disabled:opacity-55";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-[var(--accent)] text-[#07110f] hover:bg-[var(--accent-strong)]",
  secondary: "bg-white/[0.08] text-[#eff8f3] ring-1 ring-white/15 hover:bg-white/[0.12] hover:ring-white/25",
  ghost: "bg-transparent text-[#eff8f3] ring-1 ring-transparent hover:bg-white/[0.08] hover:ring-white/10",
  danger: "bg-[var(--danger)] text-[#07110f] hover:bg-[#ff8f8f]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3.5 py-2 text-xs",
  md: "min-h-11 px-5 py-3 text-sm",
  lg: "min-h-12 px-6 py-3.5 text-base",
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export type ButtonProps = ComponentPropsWithoutRef<"button"> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  loadingLabel?: string;
};

export function buttonClasses({
  variant = "primary",
  size = "md",
  className,
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}): string {
  return cx(baseClasses, variantClasses[variant], sizeClasses[size], className);
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  isLoading = false,
  loadingLabel = "Loading...",
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      aria-busy={isLoading || undefined}
      className={buttonClasses({ variant, size, className })}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <span className="h-2 w-2 rounded-full bg-current opacity-80 motion-safe:animate-pulse" aria-hidden="true" />
          <span>{loadingLabel}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function SecondaryButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="secondary" {...props} />;
}

export type ButtonLinkProps = Omit<ComponentPropsWithoutRef<typeof Link>, "className" | "children" | "onClick"> & {
  className?: string;
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
};

export function ButtonLink({
  className,
  variant = "primary",
  size = "md",
  disabled = false,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      aria-disabled={disabled || undefined}
      className={buttonClasses({ variant, size, className: cx(disabled && "cursor-not-allowed", className) })}
      tabIndex={disabled ? -1 : undefined}
      {...props}
    >
      {children}
    </Link>
  );
}
