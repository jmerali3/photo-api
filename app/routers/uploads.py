import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends

from ..models import InitUploadRequest, InitUploadResponse
from ..settings import get_settings
from ..deps import get_s3_client
from ..auth import get_current_user

router = APIRouter()

def _new_s3_key(prefix: Optional[str], ext: str) -> str:
    base = f"{time.strftime('%Y/%m/%d')}/{uuid.uuid4()}"
    if prefix:
        base = f"{prefix.rstrip('/')}/{base}"
    return f"{base}{ext}"

@router.post("/uploads/init", response_model=InitUploadResponse)
def init_upload(req: InitUploadRequest, current_user: dict = Depends(get_current_user)):
    s = get_settings()
    s3 = get_s3_client()

    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
        "image/heif": ".heic",
    }
    ext = ext_map.get(req.content_type, ".bin")
    key = _new_s3_key(req.key_prefix, ext)

    conditions = [
        {"content-type": req.content_type},
        ["content-length-range", 1, req.max_bytes],
        {"x-amz-meta-origin": "presigned"},
    ]
    fields = {"Content-Type": req.content_type, "x-amz-meta-origin": "presigned"}

    presign = s3.generate_presigned_post(
        Bucket=s.s3_bucket_raw,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=s.presign_expires_seconds,
    )
    return InitUploadResponse(url=presign["url"], fields=presign["fields"], key=key)