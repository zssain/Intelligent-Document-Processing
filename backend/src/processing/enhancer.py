"""GPT-4o enhancement stub (feature-flagged — currently disabled).

When ``ENABLE_GPT4O_ENHANCEMENT=true`` a future implementation will:
    1. Read the stored raw DI markdown from S3.
    2. Call GPT-4o to improve structure / tables / section clarity.
    3. Write back an ``enhanced_text`` + updated chunks & embeddings.
    4. Set ``enhancement_status`` to ``"enhanced"`` in Firestore.

For now this is a no-op scaffolding module that preserves the existing
text unchanged.
"""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def run_enhancer(
    document_id: str,
    mode: str = "default",
    *,
    tenant_id: Optional[str] = None,
) -> dict:
    """Run GPT-4o enhancement on a previously extracted document.

    Parameters
    ----------
    document_id:
        Firestore document ID whose raw extraction will be enhanced.
    mode:
        Enhancement mode — reserved for future use (e.g. ``"tables"``,
        ``"sections"``, ``"full"``).
    tenant_id:
        Tenant scope.  Defaults to ``DEFAULT_TENANT_ID``.

    Returns
    -------
    dict with keys ``status`` and ``enhanced_text`` (or ``error``).
    """
    if not settings.enable_gpt4o_enhancement:
        logger.info(
            "[enhancer] GPT-4o enhancement is disabled (feature flag off). "
            "Returning no-op for document %s.",
            document_id,
        )
        return {
            "status": "skipped",
            "reason": "feature_disabled",
            "document_id": document_id,
        }

    # ── Future implementation goes here ───────────────────────────────────
    # Steps:
    #   1. Read raw_extraction JSON from S3 (stored by pipeline)
    #   2. Send markdown to GPT-4o with a structured prompt
    #   3. Re-chunk + re-embed the enhanced text
    #   4. Replace Postgres chunks and update Firestore metadata
    #   5. Set enhancement_status = "enhanced"
    # ─────────────────────────────────────────────────────────────────────

    logger.warning(
        "[enhancer] GPT-4o enhancement is enabled but not yet implemented. "
        "Document %s was not enhanced.",
        document_id,
    )
    return {
        "status": "not_implemented",
        "reason": "enhancement_logic_pending",
        "document_id": document_id,
    }
