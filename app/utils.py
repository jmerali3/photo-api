import secrets

def generate_api_key() -> str:
    """
    Generate a secure random API key.
    Returns a URL-safe base64-encoded random string.
    """
    return secrets.token_urlsafe(32)