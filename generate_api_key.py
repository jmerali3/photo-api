#!/usr/bin/env python3
"""
Generate a secure API key for the photo-api.
Run this script to generate a new API key for production use Only one client (self) so this is fine fo rnow.
"""

import secrets

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    api_key = generate_api_key()
    print("Generated secure API key:")
    print(f"API_KEY={api_key}")
    print("\nAdd this to your .env file or environment variables.")
    print("Keep this key secure and don't commit it to version control!")