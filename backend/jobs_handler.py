"""SQS worker Lambda entry point for ingestion jobs."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from runtime_bootstrap import bootstrap_runtime

bootstrap_runtime()

from src.processing.job_manager import run_job

logger = logging.getLogger(__name__)


def _run_message(body: Dict[str, Any]) -> None:
    tenant_id = body["tenant_id"]
    job_id = body["job_id"]
    asyncio.run(run_job(tenant_id, job_id))


def handler(event, context):  # noqa: ANN001
    """Process queued ingestion jobs from SQS.

    Returns partial batch failures so only failed messages are retried.
    """
    records = event.get("Records", [])
    if not records:
        _run_message(event)
        return {"status": "completed"}

    failures = []
    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            body = record.get("body", {})
            if isinstance(body, str):
                body = json.loads(body)
            _run_message(body)
        except Exception:
            logger.exception("Failed to process job message %s", message_id)
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
