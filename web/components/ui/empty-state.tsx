import type { ReactNode } from "react";
import { Panel } from "./panel";

type EmptyStateProps = {
  title: string;
  body: string;
  action?: ReactNode;
  className?: string;
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function EmptyState({ title, body, action, className }: EmptyStateProps) {
  return (
    <Panel className={cx("grid justify-items-center gap-3 text-center", className)}>
      <h3 className="text-lg font-semibold tracking-[-0.02em] text-[#eff8f3]">{title}</h3>
      <p className="max-w-[52ch] text-sm leading-6 text-[var(--text-muted)]">{body}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </Panel>
  );
}

export function ErrorState({
  title = "Something went wrong.",
  body = "Try again or check the service status.",
  action,
  className,
}: Partial<EmptyStateProps>) {
  return (
    <Panel variant="danger" className={cx("grid justify-items-center gap-3 text-center", className)} role="alert">
      <h3 className="text-lg font-semibold tracking-[-0.02em] text-[#ffe0e0]">{title}</h3>
      <p className="max-w-[52ch] text-sm leading-6 text-[#ffbdbd]">{body}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </Panel>
  );
}
