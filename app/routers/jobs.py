import uuid
import json
from datetime import timedelta, datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from temporalio.client import Client
from temporalio.common import RetryPolicy

from ..models import FromUploadRequest, FromURLRequest, JobStatus
from ..settings import get_settings, Settings
from ..deps import get_s3_client
from ..auth import get_current_user
from ..database import get_db, JobLog

router: APIRouter = APIRouter()

# This will be set by the main app during startup
temporal_client: Optional[Client] = None

def set_temporal_client(client: Client) -> None:
    """Set the temporal client instance"""
    global temporal_client
    temporal_client = client

@router.post("/jobs/from-upload", response_model=JobStatus)
async def start_from_upload(
    req: FromUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db)
) -> JobStatus:
    """Start an image processing job from an uploaded S3 object."""
    s: Settings = get_settings()
    s3: Any = get_s3_client()

    # Verify S3 object exists
    try:
        obj_info = s3.head_object(Bucket=s.s3_bucket_raw, Key=req.key)
    except Exception:
        raise HTTPException(400, f"S3 object not found or not accessible: {req.key}")

    if not temporal_client:
        raise HTTPException(500, "Temporal client not initialized")

    job_id: str = f"img-{uuid.uuid4()}"

    # Extract filename from S3 key
    filename: str = req.key.split('/')[-1]

    # Create job log entry (if database is available)
    job_log = None
    if db:
        job_log = JobLog(
            job_id=job_id,
            job_type="upload",
            filename=filename,
            s3_key=req.key,
            content_type=obj_info.get('ContentType'),
            job_metadata=json.dumps(req.job_metadata) if req.job_metadata else None,
            temporal_workflow_id=job_id,
            temporal_task_queue=s.temporal_task_queue,
            started_at=datetime.utcnow(),
            status="submitted"
        )

        db.add(job_log)
        await db.commit()
        await db.refresh(job_log)

    # Start Temporal workflow
    workflow_input = {
        "job_id": job_id,
        "bucket": s.s3_bucket_raw,
        "key": req.key,
        "expected_content_type": obj_info.get('ContentType')
    }

    try:
        await temporal_client.start_workflow(
            "image_processing_workflow",
            workflow_input,
            id=job_id,
            task_queue=s.temporal_task_queue,
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )

        # Update status to started (if database is available)
        if db and job_log:
            job_log.status = "started"
            await db.commit()

    except Exception as e:
        # Update status to failed (if database is available)
        if db and job_log:
            job_log.status = "failed"
            job_log.error_message = str(e)
            await db.commit()
        raise HTTPException(500, f"Failed to start workflow: {str(e)}")

    return JobStatus(job_id=job_id, status="started")

@router.post("/jobs/from-url", response_model=JobStatus)
async def start_from_url(
    req: FromURLRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db)
) -> JobStatus:
    """Start an image processing job from a URL."""
    raise HTTPException(
        status_code=501,
        detail="URL ingestion is not implemented. Use the /jobs/from-upload endpoint instead."
    )

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db)
) -> JobStatus:
    """Get the status and result of a job."""
    if not temporal_client:
        raise HTTPException(500, "Temporal client not initialized")

    # Get job log from database (if available)
    job_log = None
    if db:
        job_log = await db.get(JobLog, job_id)
        if not job_log:
            raise HTTPException(404, f"Job not found: {job_id}")

    try:
        handle = temporal_client.get_workflow_handle(job_id)
        info = await handle.describe()
        status: str = info.status.name.lower()
        result: Optional[Dict[str, Any]] = None

        if status == "completed":
            result = await handle.result()
            # Update database with completion (if available)
            if db and job_log and job_log.status != "completed":
                job_log.status = "completed"
                job_log.completed_at = datetime.utcnow()
                await db.commit()

        elif status == "failed":
            # Update database with failure (if available)
            if db and job_log and job_log.status != "failed":
                job_log.status = "failed"
                job_log.completed_at = datetime.utcnow()
                try:
                    # Try to get the failure reason
                    result = await handle.result()
                except Exception as e:
                    job_log.error_message = str(e)
                await db.commit()

        elif status in ["running", "continued_as_new"]:
            # Update status if it changed (if database available)
            if db and job_log and job_log.status != "running":
                job_log.status = "running"
                await db.commit()

        return JobStatus(job_id=job_id, status=status, result=result)

    except Exception as e:
        # Job might be deleted from Temporal but still in our DB
        if db and job_log:
            job_log.status = "unknown"
            job_log.error_message = f"Temporal query failed: {str(e)}"
            await db.commit()
        raise HTTPException(404, f"Job not found in Temporal: {job_id}")
