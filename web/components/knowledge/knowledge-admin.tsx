"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createKnowledgeDoc,
  deleteKnowledgeDoc,
  getKnowledgeDoc,
  listKnowledgeDocs,
  previewChunks,
  triggerKnowledgeReindex,
  updateKnowledgeDoc,
  validateKnowledgeDoc,
} from "@/lib/api";
import type { ChunkPreview, Domain, IngestJob, KnowledgeDoc, KnowledgeDocPayload, KnowledgeValidation } from "@/lib/types";
import { DOMAINS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { KnowledgeEditor } from "./knowledge-editor";

const DOMAIN_LABELS: Record<Domain, string> = {
  tax: "Tax",
  visa: "Visa",
  ward_office: "Ward Office",
};

const EMPTY_PAYLOAD: KnowledgeDocPayload = {
  domain: "tax",
  filename: "",
  doc_title: "",
  source_url: "",
  language: "en",
  body: "",
};

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

function docToPayload(doc: KnowledgeDoc): KnowledgeDocPayload {
  return {
    domain: doc.domain,
    filename: doc.filename,
    doc_title: doc.doc_title,
    source_url: doc.source_url,
    language: doc.language,
    body: doc.body ?? "",
  };
}

type AlertProps = { type: "success" | "error" | "warning"; message: string };

function Alert({ type, message }: AlertProps) {
  const styles = {
    success: "bg-[var(--accent)]/[0.08] ring-[var(--accent)]/25 text-[var(--accent)]",
    error: "bg-[var(--danger)]/[0.08] ring-[var(--danger)]/25 text-[#ffb3b3]",
    warning: "bg-amber-300/[0.08] ring-amber-300/25 text-amber-200",
  };
  return (
    <div className={cx("rounded-xl p-3 text-sm ring-1", styles[type])} role={type === "error" ? "alert" : "status"}>
      {message}
    </div>
  );
}

type ChunkListProps = { chunks: ChunkPreview[]; loading: boolean; error: string | null };

function ChunkList({ chunks, loading, error }: ChunkListProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-white/[0.05]" />
        ))}
      </div>
    );
  }
  if (error) return <Alert type="error" message={error} />;
  if (chunks.length === 0) return <p className="text-sm text-[var(--text-muted)]">No chunks available.</p>;
  return (
    <ol className="space-y-3" aria-label="Document chunks">
      {chunks.map((chunk, idx) => (
        <li key={chunk.chunk_id} className="rounded-xl bg-white/[0.04] p-4 ring-1 ring-white/10">
          <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">
            Chunk {idx + 1} / {chunk.chunk_id}
          </p>
          <p className="whitespace-pre-wrap font-mono text-xs leading-5 text-[#eff8f3]">{chunk.text}</p>
        </li>
      ))}
    </ol>
  );
}

export function KnowledgeAdmin() {
  const listRequestRef = useRef(0);
  const docRequestRef = useRef(0);
  const validationRequestRef = useRef(0);
  const chunksRequestRef = useRef(0);

  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [domainFilter, setDomainFilter] = useState<Domain | "">("");
  const [searchQuery, setSearchQuery] = useState("");

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [activeDoc, setActiveDoc] = useState<KnowledgeDoc | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const [isNew, setIsNew] = useState(false);
  const [payload, setPayload] = useState<KnowledgeDocPayload>(EMPTY_PAYLOAD);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof KnowledgeDocPayload, string>>>({});

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const [validation, setValidation] = useState<KnowledgeValidation | null>(null);
  const [validating, setValidating] = useState(false);
  const [validateError, setValidateError] = useState<string | null>(null);

  const [chunks, setChunks] = useState<ChunkPreview[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunksError, setChunksError] = useState<string | null>(null);
  const [showChunks, setShowChunks] = useState(false);

  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [reindexJob, setReindexJob] = useState<IngestJob | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexError, setReindexError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    const requestId = listRequestRef.current + 1;
    listRequestRef.current = requestId;
    setListLoading(true);
    setListError(null);
    try {
      const res = await listKnowledgeDocs(domainFilter, searchQuery);
      if (listRequestRef.current !== requestId) return;
      setDocs(res.documents);
    } catch (err) {
      if (listRequestRef.current !== requestId) return;
      setListError(err instanceof ApiError ? err.detail : "Failed to load documents.");
    } finally {
      if (listRequestRef.current === requestId) setListLoading(false);
    }
  }, [domainFilter, searchQuery]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const selectDoc = useCallback(async (docId: string) => {
    const requestId = docRequestRef.current + 1;
    docRequestRef.current = requestId;
    validationRequestRef.current += 1;
    chunksRequestRef.current += 1;
    setSelectedDocId(docId);
    setIsNew(false);
    setActiveDoc(null);
    setDocError(null);
    setDocLoading(true);
    setShowChunks(false);
    setChunks([]);
    setChunksError(null);
    setChunksLoading(false);
    setValidation(null);
    setValidateError(null);
    setValidating(false);
    setSaveSuccess(null);
    setSaveError(null);
    setDeleteError(null);
    setFieldErrors({});
    try {
      const doc = await getKnowledgeDoc(docId);
      if (docRequestRef.current !== requestId) return;
      setActiveDoc(doc);
      setPayload(docToPayload(doc));
    } catch (err) {
      if (docRequestRef.current !== requestId) return;
      setDocError(err instanceof ApiError ? err.detail : "Failed to load document.");
    } finally {
      if (docRequestRef.current === requestId) setDocLoading(false);
    }
  }, []);

  function startNew() {
    docRequestRef.current += 1;
    validationRequestRef.current += 1;
    chunksRequestRef.current += 1;
    setSelectedDocId(null);
    setIsNew(true);
    setActiveDoc(null);
    setDocError(null);
    setPayload(EMPTY_PAYLOAD);
    setFieldErrors({});
    setSaveError(null);
    setSaveSuccess(null);
    setValidation(null);
    setValidateError(null);
    setValidating(false);
    setShowChunks(false);
    setChunks([]);
    setChunksError(null);
    setChunksLoading(false);
    setDeleteError(null);
  }

  function clearEditor() {
    docRequestRef.current += 1;
    validationRequestRef.current += 1;
    chunksRequestRef.current += 1;
    setSelectedDocId(null);
    setIsNew(false);
    setActiveDoc(null);
    setPayload(EMPTY_PAYLOAD);
    setFieldErrors({});
    setSaveSuccess(null);
    setSaveError(null);
    setValidation(null);
    setValidateError(null);
    setValidating(false);
    setShowChunks(false);
    setChunks([]);
    setChunksError(null);
    setChunksLoading(false);
  }

  async function handleValidate() {
    const editorRequestId = docRequestRef.current;
    const validationRequestId = validationRequestRef.current + 1;
    validationRequestRef.current = validationRequestId;
    setValidating(true);
    setValidateError(null);
    setValidation(null);
    try {
      const result = await validateKnowledgeDoc(payload);
      if (validationRequestRef.current !== validationRequestId || docRequestRef.current !== editorRequestId) return;
      setValidation(result);
    } catch (err) {
      if (validationRequestRef.current !== validationRequestId || docRequestRef.current !== editorRequestId) return;
      setValidateError(err instanceof ApiError ? err.detail : "Validation request failed.");
    } finally {
      if (validationRequestRef.current === validationRequestId) setValidating(false);
    }
  }

  async function handleSave() {
    const editorRequestId = docRequestRef.current;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);
    setFieldErrors({});
    try {
      if (isNew) {
        const created = await createKnowledgeDoc(payload);
        await loadList();
        if (docRequestRef.current !== editorRequestId) return;
        setSaveSuccess(`Document "${created.doc_title}" created.`);
        setIsNew(false);
        setSelectedDocId(created.doc_id);
        setActiveDoc(created);
      } else if (activeDoc && selectedDocId === activeDoc.doc_id) {
        const updated = await updateKnowledgeDoc(activeDoc.doc_id, payload);
        await loadList();
        if (docRequestRef.current !== editorRequestId) return;
        setSaveSuccess(`Document "${updated.doc_title}" saved.`);
        setActiveDoc(updated);
      } else {
        setSaveError("Load the selected document before saving.");
      }
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.detail : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!activeDoc) return;
    if (!window.confirm(`Delete "${activeDoc.doc_title}"? This action cannot be undone.`)) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteKnowledgeDoc(activeDoc.doc_id);
      clearEditor();
      await loadList();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  }

  async function handlePreviewChunks() {
    if (!activeDoc) return;
    const editorRequestId = docRequestRef.current;
    const chunksRequestId = chunksRequestRef.current + 1;
    chunksRequestRef.current = chunksRequestId;
    setShowChunks(true);
    setChunksLoading(true);
    setChunksError(null);
    setChunks([]);
    try {
      const res = await previewChunks(activeDoc.doc_id);
      if (chunksRequestRef.current !== chunksRequestId || docRequestRef.current !== editorRequestId) return;
      setChunks(res.chunks);
    } catch (err) {
      if (chunksRequestRef.current !== chunksRequestId || docRequestRef.current !== editorRequestId) return;
      setChunksError(err instanceof ApiError ? err.detail : "Failed to load chunks.");
    } finally {
      if (chunksRequestRef.current === chunksRequestId) setChunksLoading(false);
    }
  }

  async function handleReindex() {
    setReindexing(true);
    setReindexError(null);
    setReindexJob(null);
    try {
      const job = await triggerKnowledgeReindex();
      setReindexJob(job);
    } catch (err) {
      setReindexError(err instanceof ApiError ? err.detail : "Reindex failed.");
    } finally {
      setReindexing(false);
    }
  }

  const hasEditor = isNew || selectedDocId !== null;
  const editorLocked = saving || deleting || validating || chunksLoading || reindexing;

  function updatePayload(next: KnowledgeDocPayload) {
    setPayload(next);
    setValidation(null);
    setValidateError(null);
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.04em] text-[#eff8f3]">Knowledge base</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Manage documents ingested into the retrieval index.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleReindex()}
            isLoading={reindexing}
            loadingLabel="Reindexing..."
            disabled={editorLocked}
          >
            Reindex all
          </Button>
          <Button size="sm" onClick={startNew} disabled={editorLocked}>
            New document
          </Button>
        </div>
      </div>

      {reindexJob && (
        <div className="mb-4">
          <Alert
            type="success"
            message={`Reindex job started: ${reindexJob.id} (${reindexJob.status})`}
          />
        </div>
      )}
      {reindexError && (
        <div className="mb-4">
          <Alert type="error" message={reindexError} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Document list */}
        <aside>
          <Panel className="sticky top-24">
            <div className="mb-4 grid gap-3">
              <Field label="Filter by domain" id="filter-domain">
                <select
                  id="filter-domain"
                  className="min-h-9 w-full rounded-xl bg-white/[0.06] px-3 py-2 text-sm text-[#eff8f3] ring-1 ring-white/10 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  value={domainFilter}
                  onChange={(e) => setDomainFilter(e.target.value as Domain | "")}
                >
                  <option value="" className="bg-[#07110f]">All domains</option>
                  {DOMAINS.map((d) => (
                    <option key={d} value={d} className="bg-[#07110f]">
                      {DOMAIN_LABELS[d]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Search" id="filter-search">
                <Input
                  id="filter-search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Title or filename..."
                  className="min-h-9 rounded-xl py-2 text-sm"
                />
              </Field>
            </div>

            {listLoading && (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded-xl bg-white/[0.05]" />
                ))}
              </div>
            )}
            {listError && <Alert type="error" message={listError} />}
            {!listLoading && !listError && docs.length === 0 && (
              <p className="py-6 text-center text-sm text-[var(--text-muted)]">No documents found.</p>
            )}
            {!listLoading && !listError && docs.length > 0 && (
              <ul className="space-y-1" aria-label="Document list">
                {docs.map((doc) => (
                  <li key={doc.doc_id}>
                    <button
                      className={cx(
                        "w-full rounded-xl p-3 text-left transition-colors focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-55",
                        selectedDocId === doc.doc_id
                          ? "bg-[var(--accent)]/10 ring-1 ring-[var(--accent)]/25"
                          : "hover:bg-white/[0.06]",
                      )}
                      disabled={editorLocked}
                      onClick={() => void selectDoc(doc.doc_id)}
                      aria-current={selectedDocId === doc.doc_id ? "true" : undefined}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium text-[#eff8f3] line-clamp-1">{doc.doc_title}</span>
                        <Badge variant="neutral" className="shrink-0 text-[10px]">
                          {DOMAIN_LABELS[doc.domain]}
                        </Badge>
                      </div>
                      <p className="mt-0.5 font-mono text-xs text-[var(--text-muted)] line-clamp-1">{doc.filename}</p>
                      {doc.needs_reindex && (
                        <span className="mt-1 inline-block rounded-full bg-amber-300/10 px-2 py-0.5 text-[10px] font-medium text-amber-200 ring-1 ring-amber-300/25">
                          Needs reindex
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </aside>

        {/* Editor panel */}
        <section aria-label="Document editor">
          {!hasEditor && (
            <div className="flex min-h-[40vh] items-center justify-center rounded-[var(--radius-card)] border border-dashed border-white/15 text-sm text-[var(--text-muted)]">
              Select a document or create a new one.
            </div>
          )}

          {hasEditor && (
            <Panel>
              {docLoading && (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 animate-pulse rounded-xl bg-white/[0.05]" />
                  ))}
                </div>
              )}
              {docError && <Alert type="error" message={docError} />}
              {!docLoading && !docError && (
                <>
                  <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold tracking-[-0.03em] text-[#eff8f3]">
                      {isNew ? "New document" : (activeDoc?.doc_title ?? "Edit document")}
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {!isNew && activeDoc && (
                        <>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => void handlePreviewChunks()}
                            isLoading={chunksLoading}
                            loadingLabel="Loading..."
                            disabled={editorLocked}
                          >
                            Preview chunks
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => void handleDelete()}
                            isLoading={deleting}
                            loadingLabel="Deleting..."
                            disabled={editorLocked}
                          >
                            Delete
                          </Button>
                        </>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void handleValidate()}
                        isLoading={validating}
                        loadingLabel="Validating..."
                        disabled={editorLocked}
                      >
                        Validate
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => void handleSave()}
                        isLoading={saving}
                        loadingLabel="Saving..."
                        disabled={editorLocked}
                      >
                        {isNew ? "Create" : "Save"}
                      </Button>
                    </div>
                  </div>

                  {saveSuccess && <div className="mb-4"><Alert type="success" message={saveSuccess} /></div>}
                  {saveError && <div className="mb-4"><Alert type="error" message={saveError} /></div>}
                  {deleteError && <div className="mb-4"><Alert type="error" message={deleteError} /></div>}

                  {validation && (
                    <div className="mb-4 rounded-xl bg-white/[0.04] p-4 ring-1 ring-white/10">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                        Validation result
                      </p>
                      <div className="flex items-center gap-2 text-sm">
                        <span
                          className={cx(
                            "rounded-full px-2 py-0.5 text-xs font-medium ring-1",
                            validation.valid
                              ? "bg-[var(--accent)]/10 text-[var(--accent)] ring-[var(--accent)]/25"
                              : "bg-[var(--danger)]/10 text-[#ffb3b3] ring-[var(--danger)]/25",
                          )}
                        >
                          {validation.valid ? "Valid" : "Invalid"}
                        </span>
                      </div>
                      {validation.errors.length > 0 && (
                        <ul className="mt-3 space-y-1" aria-label="Validation errors">
                          {validation.errors.map((e, i) => (
                            <li key={i} className="text-xs text-[#ffb3b3]">
                              {e}
                            </li>
                          ))}
                        </ul>
                      )}
                      {validation.warnings.length > 0 && (
                        <ul className="mt-3 space-y-1" aria-label="Validation warnings">
                          {validation.warnings.map((w, i) => (
                            <li key={i} className="text-xs text-amber-200">
                              {w}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {validateError && <div className="mb-4"><Alert type="error" message={validateError} /></div>}

                  <KnowledgeEditor
                    value={payload}
                    onChange={updatePayload}
                    errors={fieldErrors}
                    disabled={editorLocked}
                  />

                  {showChunks && (
                    <div className="mt-8">
                      <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                        Chunk preview
                      </h3>
                      <ChunkList chunks={chunks} loading={chunksLoading} error={chunksError} />
                    </div>
                  )}
                </>
              )}
            </Panel>
          )}
        </section>
      </div>
    </div>
  );
}
