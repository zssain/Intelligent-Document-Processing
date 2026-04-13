"""Ingestion job endpoints — process selected files & track progress.

POST /api/v1/jobs/process  → queue a multi-file ingestion job
GET  /api/v1/jobs/{job_id} → poll per-file progress
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Dict, List

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from config.settings import DEFAULT_TENANT_ID, settings
from src.api.auth import CurrentUser, get_current_user
from src.processing.job_manager import create_job, get_job, run_job

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache()
def _get_sqs_client():
    """Build an SQS client that works with either IAM role or explicit keys."""
    client_kwargs: Dict[str, Any] = {
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("sqs", **client_kwargs)


def _dispatch_job(tenant_id: str, job_id: str, background_tasks: BackgroundTasks) -> str:
    """Dispatch jobs through SQS when configured, otherwise fall back locally."""
    if settings.job_queue_url:
        message_kwargs: Dict[str, Any] = {
            "QueueUrl": settings.job_queue_url,
            "MessageBody": json.dumps({"tenant_id": tenant_id, "job_id": job_id}),
        }
        if settings.job_queue_url.endswith(".fifo"):
            message_kwargs["MessageGroupId"] = tenant_id or DEFAULT_TENANT_ID
            message_kwargs["MessageDeduplicationId"] = job_id
        _get_sqs_client().send_message(**message_kwargs)
        return "sqs"

    background_tasks.add_task(run_job, tenant_id, job_id)
    return "background_tasks"


# ── Request / Response models ─────────────────────────────────────────────

class FileRef(BaseModel):
    id: str = Field(..., description="Source-specific file identifier (S3 key / SP item_id / GDrive file_id)")
    name: str = Field(..., description="Display filename")


class ProcessRequest(BaseModel):
    source_type: str = Field(..., description="s3 | sharepoint | gdrive")
    files: List[FileRef] = Field(..., min_length=1, description="Files to process")


class ProcessResponse(BaseModel):
    job_id: str
    status: str = "queued"
    total_files: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_type: str
    created_by: str
    files: List[Dict[str, Any]]
    summary: Dict[str, int]
    created_at: Any = None
    started_at: Any = None
    completed_at: Any = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/process", response_model=ProcessResponse)
async def process_files(
    body: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Queue selected files for ingestion.

    Creates a Firestore job document and dispatches processing either to SQS
    (recommended for Lambda) or to an in-process background task fallback.
    """
    if body.source_type not in ("s3", "sharepoint", "gdrive"):
        raise HTTPException(status_code=400, detail="source_type must be s3, sharepoint, or gdrive")

    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID

    file_dicts = [{"id": f.id, "name": f.name} for f in body.files]
    job_id = create_job(
        tenant_id=tenant_id,
        user_id=current_user.uid,
        source_type=body.source_type,
        files=file_dicts,
    )

    dispatch_mode = _dispatch_job(tenant_id, job_id, background_tasks)

    logger.info(
        "Queued ingestion job %s (%d files, source=%s, user=%s, dispatch=%s)",
        job_id, len(file_dicts), body.source_type, current_user.uid, dispatch_mode,
    )

    return ProcessResponse(
        job_id=job_id,
        status="queued",
        total_files=len(file_dicts),
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Poll the status of an ingestion job (per-file progress)."""
    tenant_id = current_user.tenant_id or DEFAULT_TENANT_ID
    job = get_job(tenant_id, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Only the creator or an org_admin can view the job
    if job.get("created_by") != current_user.uid and current_user.role != "org_admin":
        raise HTTPException(status_code=403, detail="Not authorised to view this job")

    return JobStatusResponse(
        job_id=job.get("job_id", job_id),
        status=job.get("status", "unknown"),
        source_type=job.get("source_type", ""),
        created_by=job.get("created_by", ""),
        files=job.get("files", []),
        summary=job.get("summary", {}),
        created_at=job.get("created_at"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
    )
