"""Ingestion job endpoints — process selected files & track progress.

POST /api/v1/jobs/process  → queue a multi-file ingestion job
GET  /api/v1/jobs/{job_id} → poll per-file progress
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from config.settings import DEFAULT_TENANT_ID
from src.api.auth import CurrentUser, get_current_user
from src.processing.job_manager import create_job, get_job, run_job

logger = logging.getLogger(__name__)

router = APIRouter()


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

    Creates a Firestore job document and dispatches processing to a
    background task.  Returns immediately with a ``job_id`` for polling.
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

    # Dispatch to background
    background_tasks.add_task(run_job, tenant_id, job_id)

    logger.info(
        "Queued ingestion job %s (%d files, source=%s, user=%s)",
        job_id, len(file_dicts), body.source_type, current_user.uid,
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
