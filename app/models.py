from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class InitUploadRequest(BaseModel):
    content_type: str = Field(..., description="MIME type, e.g. image/jpeg")
    max_bytes: int = Field(25_000_000, description="Max size in bytes")
    key_prefix: Optional[str] = Field(None, description="Optional S3 key prefix")

class InitUploadResponse(BaseModel):
    url: str
    fields: Dict[str, Any]
    key: str

class FromUploadRequest(BaseModel):
    key: str
    job_metadata: Optional[Dict[str, Any]] = None

class FromURLRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    job_metadata: Optional[Dict[str, Any]] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None