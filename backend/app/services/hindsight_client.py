"""The ONLY module that talks to Hindsight.

Everything else in the codebase calls this wrapper, so if an SDK signature changes there is
exactly one file to fix. Operations used:

* retain  - store an incident or runbook (extracts facts, entities and time)
* recall  - fast, no-LLM retrieval of relevant stored facts (evidence panel)
* reflect - agentic reasoning over memory, with structured output and cited sources
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app import config

log = logging.getLogger(__name__)


class HindsightUnavailable(RuntimeError):
    """Raised when Hindsight cannot be reached or rejects a call. Callers should degrade gracefully."""


@dataclass
class Evidence:
    """One remembered fact, normalised so the rest of the app never sees SDK objects."""

    id: str
    text: str
    type: str = ""
    context: Optional[str] = None
    document_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    occurred_start: Optional[str] = None


@dataclass
class ReflectResult:
    text: str
    structured: Optional[dict[str, Any]] = None
    structured_error: Optional[str] = None
    sources: list[Evidence] = field(default_factory=list)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Read a field from an SDK object or a plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_evidence(obj: Any) -> Evidence:
    return Evidence(
        id=str(_get(obj, "id", "")),
        text=_get(obj, "text", "") or "",
        type=_get(obj, "type", "") or "",
        context=_get(obj, "context"),
        document_id=_get(obj, "document_id"),
        tags=list(_get(obj, "tags", None) or []),
        occurred_start=_get(obj, "occurred_start"),
    )


def _make_client() -> Any:
    """Build the SDK client. The import is lazy so scripts can run --dry-run without the SDK."""
    try:
        from hindsight_client import Hindsight as Client  # pip install hindsight-client
    except ImportError:  # the docs also show this name for the hindsight-all package
        from hindsight import HindsightClient as Client  # type: ignore

    kwargs: dict[str, Any] = {"base_url": config.HINDSIGHT_URL}
    if config.HINDSIGHT_API_KEY:
        kwargs["api_key"] = config.HINDSIGHT_API_KEY
    try:
        return Client(**kwargs)
    except TypeError:
        # Older or different client signature without api_key.
        if "api_key" in kwargs:
            log.warning("Client rejected api_key argument; continuing without it.")
            kwargs.pop("api_key")
        return Client(**kwargs)


class HindsightMemory:
    """Incident memory backed by one Hindsight bank."""

    def __init__(self, client: Any = None, bank_id: Optional[str] = None) -> None:
        self._client = client
        self.bank_id = bank_id or config.BANK_ID

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = _make_client()
        return self._client

    # -------------------------------------------------------------------- bank
    def ensure_bank(self, name: str = "Incident Response Agent") -> None:
        """Create the memory bank if it does not exist yet. Safe to call repeatedly."""
        try:
            self.client.create_bank(bank_id=self.bank_id, name=name)
            log.info("Bank '%s' is ready.", self.bank_id)
        except Exception as exc:
            text = str(exc).lower()
            if "already exists" in text or "409" in text or "conflict" in text:
                return  # the bank is already there, which is fine
            raise HindsightUnavailable(f"could not create bank '{self.bank_id}': {exc}") from exc

    def close(self) -> None:
        """Close the underlying HTTP session (avoids the 'Unclosed connector' warning)."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # closing must never raise
                pass

    # ------------------------------------------------------------------ retain
    def retain_items(self, items: list[dict[str, Any]], attempts: int = 4) -> None:
        """Store items. Each item may carry: content, context, timestamp, document_id, tags, metadata.

        A stable document_id makes retain idempotent: re-seeding replaces instead of duplicating.
        Retries with backoff to ride out rate limits (HTTP 429) on bursts.
        """
        payload = items
        for attempt in range(1, attempts + 1):
            try:
                self.client.retain_batch(bank_id=self.bank_id, items=payload)
                return
            except Exception as exc:  # SDK raises its own exception types
                # If the SDK rejects the optional observation_scopes field, drop it once and retry.
                if any("observation_scopes" in it for it in payload) and "observation_scopes" in str(exc):
                    log.warning("observation_scopes not accepted by this client version; retrying without it.")
                    payload = [{k: v for k, v in it.items() if k != "observation_scopes"} for it in payload]
                    continue
                if attempt == attempts:
                    raise HindsightUnavailable(f"retain failed after {attempts} attempts: {exc}") from exc
                delay = 2**attempt
                log.warning("retain attempt %d failed (%s); retrying in %ds", attempt, exc, delay)
                time.sleep(delay)

    # ------------------------------------------------------------------ recall
    def recall(
        self,
        query: str,
        tags: Optional[list[str]] = None,
        tags_match: str = "any_strict",
        types: Optional[list[str]] = None,
        max_tokens: int = 2048,
        budget: str = "mid",
    ) -> list[Evidence]:
        """Fast retrieval with no LLM call. Use for the evidence panel."""
        kwargs: dict[str, Any] = {
            "bank_id": self.bank_id,
            "query": query,
            "max_tokens": max_tokens,
            "budget": budget,
        }
        if tags:
            kwargs["tags"] = tags
            kwargs["tags_match"] = tags_match
        if types:
            kwargs["types"] = types
        try:
            response = self.client.recall(**kwargs)
        except Exception as exc:
            raise HindsightUnavailable(f"recall failed: {exc}") from exc
        return [_to_evidence(r) for r in (_get(response, "results", []) or [])]

    # ----------------------------------------------------------------- reflect
    def reflect(
        self,
        query: str,
        response_schema: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        tags_match: str = "any_strict",
        budget: str = "mid",
    ) -> ReflectResult:
        """Agentic reasoning over memory. Returns text, optional structured output and cited sources.

        Note: reflect is driven by tool calls, so the LLM configured on the Hindsight side must
        support tool calling. If it does not, Hindsight returns an error (HTTP 500).
        """
        kwargs: dict[str, Any] = {
            "bank_id": self.bank_id,
            "query": query,
            "budget": budget,
            "include_facts": True,  # returns based_on: the memories actually used
        }
        if response_schema:
            kwargs["response_schema"] = response_schema
        if tags:
            kwargs["tags"] = tags
            kwargs["tags_match"] = tags_match
        try:
            response = self.client.reflect(**kwargs)
        except Exception as exc:
            raise HindsightUnavailable(f"reflect failed: {exc}") from exc

        based_on = _get(response, "based_on")
        memories = _get(based_on, "memories", []) or []
        return ReflectResult(
            text=_get(response, "text", "") or "",
            structured=_get(response, "structured_output"),
            structured_error=_get(response, "structured_output_error"),
            sources=[_to_evidence(m) for m in memories],
        )