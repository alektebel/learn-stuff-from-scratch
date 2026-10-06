def normalize_code(code: str) -> str:
    """Canonical form used as the key of PROMOTIONS."""
    return code.strip().upper()
