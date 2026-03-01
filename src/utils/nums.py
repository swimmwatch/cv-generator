import secrets


def secure_random_float():
    """Generate a secure random float in the range [0.0, 1.0]."""
    return secrets.randbelow(1 << 53) / float((1 << 53) - 1)
