"""Document chunking strategies for RAG.

Two chunk types are produced:

* **fact** – one chunk per extracted key-value field.  These are short,
  self-contained statements designed for high-precision grounding.
* **semantic** – markdown is split into sections by headings.  Long sections
  are further split into overlapping windows so no chunk exceeds
  ``MAX_CHUNK_CHARS``.
"""

from __future__ import annotations

from typing import List, Dict, Any
import re
import logging
import hashlib

logger = logging.getLogger(__name__)

# Limits ------------------------------------------------------------------
MAX_CHUNK_CHARS = 2000       # hard cap per chunk (≈500 tokens)
OVERLAP_CHARS = 200          # overlap between split windows
MIN_CHUNK_CHARS = 30         # skip anything shorter


class Chunker:
    """Implements dual chunking strategy: Semantic + Extracted-Field Facts."""

    # --------------------------------------------------------------------- #
    #  Public API                                                            #
    # --------------------------------------------------------------------- #
    @staticmethod
    def chunk_document(normalized_data: dict, markdown_content: str) -> List[dict]:
        """Create semantic and fact-based chunks from a document.

        Args:
            normalized_data: Output from ``DocumentNormalizer.normalize()``.
            markdown_content: Full markdown text from Azure CU.

        Returns:
            Deduplicated list of chunk dicts with keys
            ``text``, ``chunk_type``, ``metadata``.
        """
        chunks: List[dict] = []

        # 1. Extracted-Field Fact Chunks
        fact_chunks = Chunker._generate_fact_chunks(normalized_data)
        chunks.extend(fact_chunks)

        # 2. Semantic Chunks from Markdown
        if markdown_content and markdown_content.strip():
            semantic_chunks = Chunker._generate_semantic_chunks(
                markdown_content, normalized_data
            )
            chunks.extend(semantic_chunks)
        else:
            logger.warning("No markdown content provided – skipping semantic chunks")

        # 3. Deduplicate (same text → keep first occurrence)
        chunks = Chunker._deduplicate(chunks)

        # 4. Fallback: if we still have 0 chunks but there *is* content,
        #    create a single "full_document" chunk so the document is
        #    queryable.  This covers very short documents whose sections
        #    individually fall below MIN_CHUNK_CHARS.
        if not chunks and markdown_content and markdown_content.strip():
            entity = normalized_data.get("entity", "the entity")
            doc_type = normalized_data.get("document_type", "Document")
            fallback_text = markdown_content.strip()
            chunks.append(
                {
                    "text": f"Context: {entity} – {doc_type}\n\n{fallback_text}",
                    "chunk_type": "semantic",
                    "metadata": {
                        "entity": entity,
                        "statement": doc_type,
                        "is_fact": False,
                        "is_fallback": True,
                    },
                }
            )
            logger.info("Created 1 fallback chunk for short document")

        logger.info(
            "Chunking complete: %d total (%d fact, %d semantic)",
            len(chunks),
            sum(1 for c in chunks if c["chunk_type"] == "fact"),
            sum(1 for c in chunks if c["chunk_type"] == "semantic"),
        )
        return chunks

    # --------------------------------------------------------------------- #
    #  Fact chunks                                                           #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _generate_fact_chunks(data: dict) -> List[dict]:
        """Create one chunk per non-null extracted field for precise grounding."""
        chunks: List[dict] = []
        metrics: dict = data.get("metrics", {})
        entity: str = data.get("entity", "the entity")
        period: str = data.get("period_end") or "the reporting period"
        doc_type: str = data.get("document_type", "Document")

        for field_key, value in metrics.items():
            # Skip internal/meta keys
            if field_key.startswith("_"):
                continue
            if value is None:
                continue

            friendly_name = field_key.replace("_", " ").title()
            text = (
                f"{friendly_name} for {entity} as of {period} is {value}. "
                f"(Source: {doc_type})"
            )

            chunks.append(
                {
                    "text": text,
                    "chunk_type": "fact",
                    "metadata": {
                        "entity": entity,
                        "statement": doc_type,
                        "field": field_key,
                        "period": period,
                        "is_fact": True,
                    },
                }
            )
        return chunks

    # --------------------------------------------------------------------- #
    #  Semantic chunks                                                       #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _generate_semantic_chunks(markdown: str, data: dict) -> List[dict]:
        """Split markdown into sections by headers, then window-split large ones."""
        chunks: List[dict] = []
        entity: str = data.get("entity", "the company")
        doc_type: str = data.get("document_type", "Document")

        # Split by markdown headers (# through ####) while preserving the header
        raw_sections = re.split(r"(?m)^(#{1,4}\s+.*)", markdown)

        # re.split with a capturing group interleaves headers and bodies.
        # Reassemble header + body pairs.
        sections: List[str] = []
        i = 0
        while i < len(raw_sections):
            part = raw_sections[i]
            # Is this a header line?
            if re.match(r"^#{1,4}\s+", part):
                body = raw_sections[i + 1] if i + 1 < len(raw_sections) else ""
                sections.append(part + "\n" + body)
                i += 2
            else:
                # Leading text before the first header
                if part.strip():
                    sections.append(part)
                i += 1

        for section in sections:
            clean = section.strip()
            if len(clean) < MIN_CHUNK_CHARS:
                continue

            # Window-split long sections
            windows = Chunker._window_split(clean)

            for window_text in windows:
                contextual_text = (
                    f"Context: {entity} – {doc_type}\n\n{window_text}"
                )
                chunks.append(
                    {
                        "text": contextual_text,
                        "chunk_type": "semantic",
                        "metadata": {
                            "entity": entity,
                            "statement": doc_type,
                            "is_fact": False,
                        },
                    }
                )

        return chunks

    # --------------------------------------------------------------------- #
    #  Helpers                                                               #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _window_split(text: str) -> List[str]:
        """Split *text* into overlapping windows of ≤ ``MAX_CHUNK_CHARS``."""
        if len(text) <= MAX_CHUNK_CHARS:
            return [text]

        windows: List[str] = []
        start = 0
        while start < len(text):
            end = start + MAX_CHUNK_CHARS

            # Try to break at a paragraph or sentence boundary
            if end < len(text):
                # Prefer paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + MAX_CHUNK_CHARS // 3:
                    end = para_break
                else:
                    # Prefer sentence break
                    sent_break = text.rfind(". ", start, end)
                    if sent_break > start + MAX_CHUNK_CHARS // 3:
                        end = sent_break + 1  # include the period

            windows.append(text[start:end].strip())
            start = end - OVERLAP_CHARS  # step back for overlap

            # Prevent infinite loop
            if start >= len(text):
                break

        return [w for w in windows if len(w) >= MIN_CHUNK_CHARS]

    @staticmethod
    def _deduplicate(chunks: List[dict]) -> List[dict]:
        """Remove chunks with identical text (keep first occurrence)."""
        seen: set = set()
        unique: List[dict] = []
        for chunk in chunks:
            h = hashlib.md5(chunk["text"].encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(chunk)
        return unique
