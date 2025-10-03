from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ProfileNotFound

from .settings import get_settings, Settings

@lru_cache
def get_s3_client() -> Any:
    """
    Get cached S3 client instance.
    Returns boto3 S3 client configured with the current AWS region.
    """
    s: Settings = get_settings()

    session_kwargs = {}
    if s.aws_profile:
        session_kwargs["profile_name"] = s.aws_profile

    try:
        session = boto3.Session(**session_kwargs)
    except ProfileNotFound as exc:
        raise RuntimeError(
            f"AWS profile '{s.aws_profile}' was configured but not found. Update your AWS credentials or unset AWS_PROFILE."
        ) from exc

    client_kwargs = {}
    if s.aws_region:
        client_kwargs["region_name"] = s.aws_region

    return session.client("s3", **client_kwargs)
