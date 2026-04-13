from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.base import get_db
from src.database.models import DocumentChunk
from src.database.firestore_service import FirestoreService
from config.settings import DEFAULT_TENANT_ID
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_datetime(val) -> datetime | None:
    """Safely convert a Firestore timestamp or string to a Python datetime."""
    if val is None:
        return None
    # Firestore Timestamp object
    if hasattr(val, "seconds"):
        from google.protobuf.timestamp_pb2 import Timestamp as PbTimestamp
        try:
            return datetime.fromtimestamp(val.seconds + val.nanos / 1e9, tz=timezone.utc).replace(tzinfo=None)
        except Exception:
            return None
    # google.cloud.firestore DatetimeWithNanoseconds
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    # ISO string
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None
    return None


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics from Firestore (documents) and Postgres (chunks).

    This endpoint is designed to NEVER fail – if any data source is
    unavailable it will return 0 for the affected counters instead of
    raising a 500 error.
    """
    total_docs = 0
    docs_today = 0
    docs_this_week = 0
    unique_entities = 0
    total_chunks = 0
    connected_files = 0

    now = datetime.utcnow()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=now.weekday())

    # ── Document stats from Firestore ────────────────────────────
    try:
        firestore_svc = FirestoreService(tenant_id=DEFAULT_TENANT_ID)
        all_docs = firestore_svc.list_documents(status="active", limit=10000)
        total_docs = len(all_docs)

        for doc in all_docs:
            dt = _to_datetime(doc.get("created_at"))
            if dt and dt >= start_of_today:
                docs_today += 1
            if dt and dt >= start_of_week:
                docs_this_week += 1

        unique_entities = len(
            {doc.get("entity_name", "") for doc in all_docs if doc.get("entity_name")}
        )
    except Exception as exc:
        logger.error("Firestore document stats failed: %s", exc)

    # ── Connected source files (from source_connections) ─────────
    try:
        from src.utils.firebase import firestore_client
        conns_ref = (
            firestore_client
            .collection("tenants")
            .document(DEFAULT_TENANT_ID)
            .collection("source_connections")
        )
        for doc in conns_ref.stream():
            data = doc.to_dict()
            connected_files += data.get("file_count", 0)
    except Exception as exc:
        logger.error("Source connections stats failed: %s", exc)

    # ── Chunk count from Postgres (pgvector) ─────────────────────
    try:
        total_chunks = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.tenant_id == DEFAULT_TENANT_ID
        ).scalar() or 0
    except Exception as exc:
        logger.error("Postgres chunk count failed: %s", exc)

    return {
        "total_documents": total_docs,
        "documents_today": docs_today,
        "documents_this_week": docs_this_week,
        "total_chunks": total_chunks,
        "unique_entities": unique_entities,
        "connected_files": connected_files,
        "system_status": "OPTIMAL",
    }
