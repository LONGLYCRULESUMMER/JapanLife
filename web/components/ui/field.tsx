import { cloneElement, isValidElement } from "react";
import type { ComponentPropsWithoutRef, ReactElement, ReactNode } from "react";

type FieldControlProps = {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
};

type ControlElement = ReactElement<{
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
}>;

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

function fieldId(label: string): string {
  const slug = label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug ? `field-${slug}` : "field-control";
}

function describedBy(id: string, hint?: ReactNode, error?: ReactNode): string | undefined {
  return [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
}

function withControlProps(children: ReactNode | ((props: FieldControlProps) => ReactNode), props: FieldControlProps): ReactNode {
  if (typeof children === "function") return children(props);

  if (!isValidElement(children)) return children;

  const child = children as ControlElement;
  return cloneElement(child, {
    id: child.props.id ?? props.id,
    "aria-describedby": [child.props["aria-describedby"], props["aria-describedby"]].filter(Boolean).join(" ") || undefined,
    "aria-invalid": child.props["aria-invalid"] ?? props["aria-invalid"],
  });
}

export type FieldProps = Omit<ComponentPropsWithoutRef<"div">, "children"> & {
  label: string;
  id?: string;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  children: ReactNode | ((props: FieldControlProps) => ReactNode);
};

export function Field({ className, label, id, hint, error, required = false, children, ...props }: FieldProps) {
  const controlId = id ?? fieldId(label);
  const descriptionIds = describedBy(controlId, hint, error);
  const controlProps: FieldControlProps = {
    id: controlId,
    "aria-describedby": descriptionIds,
    "aria-invalid": error ? true : undefined,
  };

  return (
    <div className={cx("grid gap-2", className)} {...props}>
      <label htmlFor={controlId} className="text-sm font-medium text-[#eff8f3]">
        {label}
        {required ? <span className="text-[var(--accent)]" aria-label="required"> *</span> : null}
      </label>
      {withControlProps(children, controlProps)}
      {hint ? (
        <p id={`${controlId}-hint`} className="text-xs leading-5 text-[var(--text-muted)]">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${controlId}-error`} className="text-xs leading-5 text-[#ff9c9c]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export type InputProps = ComponentPropsWithoutRef<"input"> & {
  invalid?: boolean;
};

export function Input({ className, invalid = false, ...props }: InputProps) {
  return (
    <input
      className={cx(
        "min-h-11 rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-[#eff8f3] ring-1 ring-white/10 transition placeholder:text-[#8aa098] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55",
        invalid && "ring-[var(--danger)] focus-visible:ring-[var(--danger)]",
        className,
      )}
      aria-invalid={invalid || props["aria-invalid"] || undefined}
      {...props}
    />
  );
}

export type TextareaProps = ComponentPropsWithoutRef<"textarea"> & {
  invalid?: boolean;
};

export function Textarea({ className, invalid = false, ...props }: TextareaProps) {
  return (
    <textarea
      className={cx(
        "min-h-48 resize-y rounded-2xl bg-white/[0.06] px-4 py-3 font-mono text-sm leading-6 text-[#eff8f3] ring-1 ring-white/10 transition placeholder:text-[#8aa098] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55",
        invalid && "ring-[var(--danger)] focus-visible:ring-[var(--danger)]",
        className,
      )}
      aria-invalid={invalid || props["aria-invalid"] || undefined}
      {...props}
    />
  );
}
