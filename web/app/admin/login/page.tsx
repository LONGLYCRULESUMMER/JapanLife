"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Field, Input } from "@/components/ui/field";
import { Button } from "@/components/ui/button";

export default function AdminLoginPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim()) {
      setError("Token is required.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/session", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token }),
        credentials: "same-origin",
      });
      if (res.status === 204) {
        setSuccess(true);
        router.push("/admin/knowledge");
      } else if (res.status === 401) {
        setError("Invalid token. Please try again.");
      } else if (res.status === 503) {
        setError("Admin authentication is not configured on this server.");
      } else {
        setError(`Unexpected response: ${res.status}`);
      }
    } catch {
      setError("Network error. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-[100dvh] overflow-x-clip">
      <div className="flex min-h-[100dvh] items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <span className="mx-auto mb-4 grid size-10 place-items-center rounded-xl bg-[var(--accent)] text-sm font-bold text-[#07110f] shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]">
              JL
            </span>
            <h1 className="text-xl font-semibold tracking-[-0.03em] text-[#eff8f3]">Admin sign in</h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Enter your admin token to continue.</p>
          </div>

          <div className="rounded-[var(--radius-card)] bg-white/[0.045] p-6 ring-1 ring-white/10 backdrop-blur">
            {success ? (
              <p className="text-center text-sm text-[var(--accent)]">Signed in. Redirecting...</p>
            ) : (
              <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                <div className="grid gap-4">
                  <Field label="Admin token" required id="admin-token" error={error ?? undefined}>
                    <Input
                      id="admin-token"
                      type="password"
                      value={token}
                      onChange={(e) => {
                        setToken(e.target.value);
                        setError(null);
                      }}
                      disabled={loading}
                      invalid={!!error}
                      autoComplete="current-password"
                      autoFocus
                    />
                  </Field>
                  <Button
                    type="submit"
                    isLoading={loading}
                    loadingLabel="Signing in..."
                    disabled={loading}
                    className="w-full"
                  >
                    Sign in
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
