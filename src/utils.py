import re

def sanitize_name(name: str) -> str:
    """Sanitize string to be used as a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()
