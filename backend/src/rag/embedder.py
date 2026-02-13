"""OpenAI embedding generation with batching, retry, and safety.

Key improvements over the naive implementation:

* **Batch size limit** – OpenAI allows a maximum of ~2048 inputs per call and
  enforces a token-per-request limit.  We conservatively cap at 100 items per
  call (well under the limit) and loop.
* **Empty / whitespace guard** – empty strings are replaced with a placeholder
  so the API never receives an empty input (which causes a 400 error).
* **Exponential back-off retry** – transient network or rate-limit errors are
  retried up to ``MAX_RETRIES`` times.
"""

from __future__ import annotations

import logging
import time
from typing import List

from openai import OpenAI
from config.settings import settings

logger = logging.getLogger(__name__)

# Tunables ----------------------------------------------------------------
BATCH_SIZE = 100          # inputs per embeddings.create() call
MAX_RETRIES = 3           # retry attempts on transient failure
PLACEHOLDER = "[empty]"   # fallback for empty texts


class Embedder:
    """Wrapper for OpenAI embedding generation."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model

    # ------------------------------------------------------------------ #
    #  Single text                                                        #
    # ------------------------------------------------------------------ #
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single string."""
        text = self._sanitise(text)
        return self._call_with_retry([text])[0]

    # ------------------------------------------------------------------ #
    #  Batch                                                              #
    # ------------------------------------------------------------------ #
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings.

        Long lists are automatically split into sub-batches of
        ``BATCH_SIZE`` so we stay within OpenAI request limits.
        """
        if not texts:
            return []

        sanitised = [self._sanitise(t) for t in texts]
        all_embeddings: List[List[float]] = []

        for start in range(0, len(sanitised), BATCH_SIZE):
            batch = sanitised[start : start + BATCH_SIZE]
            batch_embeddings = self._call_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
            logger.debug(
                "Embedded batch %d–%d / %d",
                start, start + len(batch), len(sanitised),
            )

        return all_embeddings

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _call_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Call the embeddings API with exponential back-off retry."""
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model,
                )
                return [data.embedding for data in response.data]
            except Exception as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "Embedding attempt %d/%d failed (%s). Retrying in %ds…",
                    attempt, MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
        raise RuntimeError(
            f"Embedding failed after {MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    @staticmethod
    def _sanitise(text: str) -> str:
        """Ensure *text* is non-empty (OpenAI rejects empty strings)."""
        if not text or not text.strip():
            return PLACEHOLDER
        return text
