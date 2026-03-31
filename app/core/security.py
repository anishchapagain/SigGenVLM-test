import hashlib

def hash_api_key(api_key: str) -> str:
    """Creates a fast, secure SHA-256 hash of the API Key."""
    return hashlib.sha256(api_key.encode()).hexdigest()
