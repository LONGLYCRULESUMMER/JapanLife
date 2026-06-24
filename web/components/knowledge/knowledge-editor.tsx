"use client";

import { Field, Input, Textarea } from "@/components/ui/field";
import { DOMAINS, LANGUAGES } from "@/lib/types";
import type { Domain, KnowledgeDocPayload, KnowledgeLanguage } from "@/lib/types";

const domainLabels: Record<Domain, string> = {
  tax: "Tax",
  visa: "Visa",
  ward_office: "Ward Office",
};

const languageLabels: Record<KnowledgeLanguage, string> = {
  en: "English",
  ja: "Japanese",
  mixed: "Mixed",
};

type KnowledgeEditorProps = {
  value: KnowledgeDocPayload;
  onChange: (value: KnowledgeDocPayload) => void;
  errors?: Partial<Record<keyof KnowledgeDocPayload, string>>;
  disabled?: boolean;
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function KnowledgeEditor({ value, onChange, errors = {}, disabled = false }: KnowledgeEditorProps) {
  function set<K extends keyof KnowledgeDocPayload>(key: K, val: KnowledgeDocPayload[K]) {
    onChange({ ...value, [key]: val });
  }

  return (
    <div className="grid gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Domain" required error={errors.domain} id="editor-domain">
          <select
            id="editor-domain"
            className={cx(
              "min-h-11 w-full rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-[#eff8f3] ring-1 ring-white/10 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55",
              errors.domain && "ring-[var(--danger)]",
            )}
            value={value.domain}
            onChange={(e) => set("domain", e.target.value as Domain)}
            disabled={disabled}
            aria-invalid={errors.domain ? true : undefined}
          >
            {DOMAINS.map((d) => (
              <option key={d} value={d} className="bg-[#07110f]">
                {domainLabels[d]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Language" required error={errors.language} id="editor-language">
          <select
            id="editor-language"
            className={cx(
              "min-h-11 w-full rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-[#eff8f3] ring-1 ring-white/10 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55",
              errors.language && "ring-[var(--danger)]",
            )}
            value={value.language}
            onChange={(e) => set("language", e.target.value as KnowledgeLanguage)}
            disabled={disabled}
            aria-invalid={errors.language ? true : undefined}
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l} className="bg-[#07110f]">
                {languageLabels[l]}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Filename" required error={errors.filename} id="editor-filename" hint="Unique slug used as the document identifier.">
        <Input
          id="editor-filename"
          value={value.filename}
          onChange={(e) => set("filename", e.target.value)}
          disabled={disabled}
          invalid={!!errors.filename}
          autoComplete="off"
          spellCheck={false}
        />
      </Field>

      <Field label="Document title" required error={errors.doc_title} id="editor-doc-title">
        <Input
          id="editor-doc-title"
          value={value.doc_title}
          onChange={(e) => set("doc_title", e.target.value)}
          disabled={disabled}
          invalid={!!errors.doc_title}
        />
      </Field>

      <Field label="Source URL" error={errors.source_url} id="editor-source-url" hint="Original reference URL (optional).">
        <Input
          id="editor-source-url"
          type="url"
          value={value.source_url}
          onChange={(e) => set("source_url", e.target.value)}
          disabled={disabled}
          invalid={!!errors.source_url}
        />
      </Field>

      <Field label="Markdown body" required error={errors.body} id="editor-body" hint="Full document content in Markdown.">
        <Textarea
          id="editor-body"
          className="min-h-[28rem]"
          value={value.body}
          onChange={(e) => set("body", e.target.value)}
          disabled={disabled}
          invalid={!!errors.body}
          spellCheck={false}
        />
      </Field>
    </div>
  );
}
