from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_db, JobLog
from ..auth import get_current_user

router: APIRouter = APIRouter()

@router.get("/admin/jobs")
async def list_jobs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List job logs with optional filtering.
    Admin endpoint for viewing job history and status.
    """
    query = select(JobLog)

    # Apply filters
    if status:
        query = query.where(JobLog.status == status)
    if job_type:
        query = query.where(JobLog.job_type == job_type)

    # Order by creation date (newest first)
    query = query.order_by(desc(JobLog.created_at))

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    # Convert to dict format
    job_list = []
    for job in jobs:
        job_dict = {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "filename": job.filename,
            "s3_key": job.s3_key,
            "source_url": job.source_url,
            "content_type": job.content_type,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message
        }
        job_list.append(job_dict)

    return {
        "jobs": job_list,
        "total": len(job_list),
        "offset": offset,
        "limit": limit
    }