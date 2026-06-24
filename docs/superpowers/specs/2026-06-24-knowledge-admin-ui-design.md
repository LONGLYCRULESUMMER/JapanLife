# JapanLife Knowledge Admin UI Design

- **Date**: 2026-06-24
- **Status**: Approved for implementation planning
- **Author**: @coda1997 + Copilot
- **Scope**: Replace the Streamlit demo plan with a production-grade Next.js frontend that separates the user Agent interface from the knowledge-base admin interface, while adding Git-based Markdown management APIs, validation, chunk preview, full ingest, and stale chunk cleanup.

---

## 1. Background

JapanLife currently manages the knowledge base through Git-tracked Markdown files under:

```text
knowledge/tax/
knowledge/visa/
knowledge/ward_office/
```

The existing system can:

- index all active Markdown files through `make ingest` or `POST /admin/ingest`
- inspect retrieval through `GET /search`
- list ingest jobs through `/admin/ingest/jobs`

It cannot yet:

- list knowledge documents through an admin UI
- create or edit Markdown documents through the backend
- soft-delete documents safely
- preview chunking before ingest
- validate front-matter/source URLs from a management surface
- clean stale ES/Qdrant chunks after source Markdown deletion

This design keeps Markdown as the source of truth and adds management surfaces around it.

---

## 2. Goals

1. Provide a production-grade frontend suitable for local demo and resume discussion.
2. Keep the current Git-based Markdown workflow.
3. Support create, read, update, and soft delete for `knowledge/<domain>/*.md`.
4. Add front-matter validation and source URL checks.
5. Add chunk preview without writing to ES/Qdrant.
6. Add full reindex with stale chunk cleanup so deletes do not leave old vectors searchable.
7. Preserve existing RAG, Agent, and retrieval behavior for normal users.
8. Split user-facing Agent chat and admin knowledge management into independent routes and layouts.

---

## 3. Non-Goals

- No database CMS in this phase.
- No full login/RBAC/multi-user approval workflow in this phase. A lightweight `ADMIN_TOKEN` gate is allowed for `/admin/*`.
- No automatic Git branch/commit/PR creation from the UI.
- No rich text editor; Markdown text editing is enough.
- No real-time web crawler or official-site synchronization.

---

## 4. Architecture

Use a four-layer design:

```text
Next.js frontend
  /chat             user-facing Agent + retrieval inspector
  /admin/knowledge  admin knowledge operations
        ↓ HTTP
FastAPI /admin/knowledge/* routes
        ↓
Knowledge admin service
        ↓
Markdown files + manifest + ES/Qdrant cleanup hooks
```

### 4.1 Source of Truth

Markdown files remain the source of truth. New and edited documents are written to:

```text
knowledge/<domain>/<slug>.md
```

Supported domains:

```text
tax
visa
ward_office
```

### 4.2 Manifest

Add a small manifest file for index lifecycle tracking:

```text
knowledge/.manifest.json
```

The manifest records the last successfully indexed chunk IDs:

```json
{
  "documents": {
    "tax/01-tax-filing-overview.md": {
      "status": "active",
      "chunk_ids": ["..."],
      "updated_at": "2026-06-24T00:00:00Z"
    }
  },
  "deleted_documents": {
    "visa/old-doc.md": {
      "deleted_at": "2026-06-24T00:00:00Z",
      "chunk_ids": ["..."]
    }
  }
}
```

This manifest is not a content store. It only tracks what chunks should exist in ES/Qdrant.

---

## 5. Admin API

Add new routes under `/admin/knowledge`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/knowledge/docs?domain=&q=` | List active documents with metadata summary. |
| `GET` | `/admin/knowledge/docs/{doc_id}` | Return one document's front-matter and Markdown body. |
| `POST` | `/admin/knowledge/docs` | Create a new Markdown document. |
| `PUT` | `/admin/knowledge/docs/{doc_id}` | Update an existing Markdown document. |
| `DELETE` | `/admin/knowledge/docs/{doc_id}` | Soft-delete a document by moving it to `.trash`. |
| `POST` | `/admin/knowledge/validate` | Validate front-matter, filename, source URL, and Markdown shape. |
| `GET` | `/admin/knowledge/docs/{doc_id}/chunks` | Preview chunks for one document without ingesting. |
| `POST` | `/admin/knowledge/reindex` | Run full ingest plus stale chunk cleanup as a background job. |

Existing `/admin/ingest` remains available. The new `/admin/knowledge/reindex` wraps the same indexing behavior but also updates the manifest and removes stale chunks.

---

## 6. Product Frontend

The primary frontend is a new Next.js App Router project under `web/`.

```text
web/
  app/
    page.tsx
    chat/page.tsx
    admin/knowledge/page.tsx
  components/
    chat/
    knowledge/
    retrieval/
    shell/
    ui/
  lib/
    api.ts
    types.ts
    config.ts
```

### 6.1 User route: `/chat`

The user-facing surface contains:

- Agent chat using `/chat/stream`
- route and tool status display
- citations display
- retrieval inspector using `/search`
- loading, empty, and error states

### 6.2 Admin route: `/admin/knowledge`

The admin surface contains:

- document browser with domain filter and search
- Markdown metadata/body editor
- Validate
- Preview chunks
- Save
- Soft delete
- Reindex knowledge base
- reindex job status

The admin route is separate from the user route and uses its own admin shell/navigation. A lightweight `ADMIN_TOKEN` boundary may protect `/admin/*`; full auth/RBAC remains a future production-hardening item.

### 6.3 Taste-skill visual direction

The frontend follows the installed `taste-skill` guidance:

- production dark-tech/product-console aesthetic
- `Geist` and `Geist Mono`, not Inter
- one desaturated emerald accent
- separate public and admin layouts
- explicit loading, empty, and error states
- no generic three-card feature row as the primary layout
- no AI-purple default gradient
- accessible focus states and form labels
- `min-h-[100dvh]` for viewport stability

---

## 6. Legacy Streamlit

`streamlit_app.py` may remain temporarily as a legacy demo, but it is no longer the target production frontend and should not receive the Knowledge Admin implementation.

---

## 7. Data Flow

### 7.1 Create

```text
UI form
 -> POST /admin/knowledge/docs
 -> validate domain + slug + front-matter
 -> write knowledge/<domain>/<slug>.md
 -> return doc summary with needs_reindex=true
```

The document is not searchable until reindex runs.

### 7.2 Update

```text
UI edit
 -> PUT /admin/knowledge/docs/{doc_id}
 -> validate path stays inside knowledge/<domain>
 -> overwrite Markdown file
 -> return doc summary with needs_reindex=true
```

### 7.3 Soft Delete

```text
DELETE /admin/knowledge/docs/{doc_id}
 -> move file to knowledge/.trash/<domain>/<filename>
 -> preserve deleted doc_id in manifest
 -> mark needs_reindex=true
```

The soft-deleted file is no longer loaded by the normal `knowledge/*/*.md` ingest glob.

### 7.4 Reindex With Stale Cleanup

```text
active Markdown files
 -> build chunks
 -> upsert active chunks to ES/Qdrant
 -> compute current_chunk_ids
 -> compare with manifest previous_chunk_ids
 -> delete stale chunk IDs from ES/Qdrant
 -> write updated manifest
```

This fixes the current limitation where deleted Markdown files can leave stale vectors behind.

### 7.5 Chunk Preview

```text
Markdown file
 -> split front-matter
 -> chunk_markdown()
 -> return chunk_id, section_path, chunk_index, preview text
```

Chunk preview never writes embeddings or index records.

---

## 8. Validation and Error Handling

Validation rules:

- `domain` must be one of `tax`, `visa`, `ward_office`.
- slug/filename must match a safe pattern such as `[a-z0-9][a-z0-9-]*.(ja.)?md`.
- resolved file paths must stay inside the repository's `knowledge/` directory.
- front-matter must include `doc_title`, `source_url`, and `language`.
- `language` must be `en`, `ja`, or `mixed`.
- body must contain at least one Markdown heading.

Error handling:

- Invalid domain/path/front-matter returns `400`.
- Missing document returns `404`.
- Source URL check failures are warnings, not hard failures, because government sites may return `403` to automated checks.
- Reindex/stale cleanup failures mark the background job as `failed`.
- Delete defaults to soft delete; no hard delete endpoint is exposed in the MVP.

---

## 9. Testing

### 9.1 Unit Tests

Add tests for:

- front-matter parse/render round trip
- safe doc ID to path resolution
- invalid slug rejection
- list documents
- create/update/soft delete document
- chunk preview
- manifest diff calculation

### 9.2 API Tests

Add FastAPI tests for:

- `GET /admin/knowledge/docs`
- `POST /admin/knowledge/docs`
- `PUT /admin/knowledge/docs/{doc_id}`
- `DELETE /admin/knowledge/docs/{doc_id}`
- `GET /admin/knowledge/docs/{doc_id}/chunks`
- `POST /admin/knowledge/reindex`

Tests should use a temporary knowledge directory so they do not mutate real project data.

### 9.3 Stale Cleanup Regression

Add a regression test where:

1. manifest contains old chunk IDs
2. current chunk build no longer includes one old ID
3. cleanup calls ES/Qdrant delete for the stale ID

---

## 10. Security Notes

This is a local/demo admin tool. It should still be safe by default:

- no arbitrary file paths
- no hidden path traversal through `doc_id`
- no hard delete from the UI
- no silent success when reindex fails

Production hardening would add authentication, RBAC, audit logs, rate limiting, and PR-based review workflow.

---

## 11. Interview Positioning

This feature lets the project be described as:

> A Git-based knowledge admin layer for RAG: Markdown remains the source of truth, the admin UI supports create/edit/soft-delete/validate/chunk-preview, and the reindex job uses a manifest to clean stale ES/Qdrant chunks so deleted documents do not remain retrievable.

This is stronger than a simple demo UI because it addresses the lifecycle of knowledge documents, not only chat and search.
