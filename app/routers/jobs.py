import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from temporalio.client import Client
from temporalio.common import RetryPolicy

from ..models import FromUploadRequest, FromURLRequest, JobStatus
from ..settings import get_settings
from ..deps import get_s3_client
from ..auth import get_current_user

router = APIRouter()

# This will be set by the main app during startup
temporal_client: Optional[Client] = None

def set_temporal_client(client: Client):
    """Set the temporal client instance"""
    global temporal_client
    temporal_client = client

@router.post("/jobs/from-upload", response_model=JobStatus)
async def start_from_upload(req: FromUploadRequest, current_user: dict = Depends(get_current_user)):
    s = get_settings()
    s3 = get_s3_client()

    try:
        s3.head_object(Bucket=s.s3_bucket_raw, Key=req.key)
    except Exception:
        raise HTTPException(400, f"S3 object not found or not accessible: {req.key}")

    if not temporal_client:
        raise HTTPException(500, "Temporal client not initialized")

    job_id = f"img-{uuid.uuid4()}"
    await temporal_client.start_workflow(
        "image_processing_workflow",
        {"source": "s3", "bucket": s.s3_bucket_raw, "key": req.key, "meta": req.job_metadata or {}},
        id=job_id,
        task_queue=s.temporal_task_queue,
        retry_policy=RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_attempts=3,
        ),
    )
    return JobStatus(job_id=job_id, status="started")

@router.post("/jobs/from-url", response_model=JobStatus)
async def start_from_url(req: FromURLRequest, current_user: dict = Depends(get_current_user)):
    s = get_settings()
    if not temporal_client:
        raise HTTPException(500, "Temporal client not initialized")

    job_id = f"img-{uuid.uuid4()}"
    await temporal_client.start_workflow(
        "image_processing_workflow",
        {"source": "url", "url": req.url, "filename": req.filename or "", "meta": req.job_metadata or {}},
        id=job_id,
        task_queue=s.temporal_task_queue,
        retry_policy=RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_attempts=3,
        ),
    )
    return JobStatus(job_id=job_id, status="started")

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def job_status(job_id: str, current_user: dict = Depends(get_current_user)):
    if not temporal_client:
        raise HTTPException(500, "Temporal client not initialized")
    try:
        handle = temporal_client.get_workflow_handle(job_id)
        info = await handle.describe()
        status = info.status.name.lower()
        result = None
        if status == "completed":
            result = await handle.result()
        return JobStatus(job_id=job_id, status=status, result=result)
    except Exception:
        raise HTTPException(404, f"Job not found: {job_id}")