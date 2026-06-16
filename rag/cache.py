"""Lightweight, swappable caches for JapanLife.

Two small, dependency-free caches that keep the retrieval path fast while staying
easy to reason about (and easy to replace with Redis later):

- :class:`SqliteKVCache` / :class:`EmbeddingCache` — persistent embedding cache so
  identical query/text embeddings are computed once. Keyed by ``sha256(model+text)``.
- :class:`TTLCache` — in-memory, time-boxed cache for ``(query, domain, top_k)``
  retrieval results, to absorb repeated identical lookups (and their rerank cost).

Everything is gated by ``core.config.settings`` and is a no-op when disabled, so
behaviour is unchanged unless a cache is explicitly turned on.

Concurrency: this is a single-process demo. ``SqliteKVCache`` and ``TTLCache`` guard
their state with a ``threading.Lock`` so they are safe under FastAPI's threadpool. For
multi-process / multi-replica deployments, swap in a shared store (e.g. Redis) behind
the same ``get``/``set`` interface.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable, Hashable, Protocol


class KVCache(Protocol):
    """Minimal string key/value interface (Redis-compatible subset)."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class SqliteKVCache:
    """Thread-safe string KV store backed by a single SQLite file."""

    def __init__(self, path: str):
        self._lock = threading.Lock()
        parent = Path(path).expanduser().parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)"
        )
        self._conn.commit()

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (key, value)
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _embedding_key(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}\x00{text}".encode("utf-8")).hexdigest()


class EmbeddingCache:
    """Persist text → embedding vectors. Wraps any :class:`KVCache`."""

    def __init__(self, path: str, model: str, kv: KVCache | None = None):
        self._kv: KVCache = kv or SqliteKVCache(path)
        self._model = model

    def get(self, text: str) -> list[float] | None:
        raw = self._kv.get(_embedding_key(self._model, text))
        return json.loads(raw) if raw is not None else None

    def set(self, text: str, vector: list[float]) -> None:
        self._kv.set(_embedding_key(self._model, text), json.dumps(vector))

    def get_many(self, texts: list[str]) -> list[list[float] | None]:
        return [self.get(t) for t in texts]

    def set_many(self, texts: list[str], vectors: list[list[float]]) -> None:
        for text, vector in zip(texts, vectors):
            self.set(text, vector)


class TTLCache:
    """Thread-safe in-memory cache whose entries expire after ``ttl_seconds``."""

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._store: dict[Hashable, tuple[float, object]] = {}

    def get(self, key: Hashable):
        now = self._clock()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: Hashable, value) -> None:
        with self._lock:
            self._store[key] = (self._clock() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# --- Process-wide singletons, gated by settings -----------------------------------

_embedding_cache: EmbeddingCache | None = None
_embedding_cache_key: tuple[str, str] | None = None
_retrieval_cache: TTLCache | None = None


def get_embedding_cache() -> EmbeddingCache | None:
    """Return the shared embedding cache, or ``None`` when disabled via settings."""
    global _embedding_cache, _embedding_cache_key
    from core.config import settings

    if not settings.enable_embedding_cache:
        return None
    key = (settings.embedding_cache_path, settings.embedding_model)
    if _embedding_cache is None or _embedding_cache_key != key:
        _embedding_cache = EmbeddingCache(
            settings.embedding_cache_path, settings.embedding_model
        )
        _embedding_cache_key = key
    return _embedding_cache


def get_retrieval_cache() -> TTLCache | None:
    """Return the shared retrieval TTL cache, or ``None`` when disabled via settings."""
    global _retrieval_cache
    from core.config import settings

    if not settings.enable_retrieval_cache:
        return None
    if _retrieval_cache is None:
        _retrieval_cache = TTLCache(settings.cache_ttl_seconds)
    return _retrieval_cache


def reset_caches() -> None:
    """Drop the process-wide cache singletons (used by tests and after config changes)."""
    global _embedding_cache, _embedding_cache_key, _retrieval_cache
    _embedding_cache = None
    _embedding_cache_key = None
    _retrieval_cache = None
