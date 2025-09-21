from functools import lru_cache
from typing import Any
import boto3
from .settings import get_settings, Settings

@lru_cache
def get_s3_client() -> Any:
    """
    Get cached S3 client instance.
    Returns boto3 S3 client configured with the current AWS region.
    """
    s: Settings = get_settings()
    return boto3.client("s3", region_name=s.aws_region)