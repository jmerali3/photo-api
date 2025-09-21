from functools import lru_cache
import boto3
from .settings import get_settings

@lru_cache
def get_s3_client():
    s = get_settings()
    return boto3.client("s3", region_name=s.aws_region)