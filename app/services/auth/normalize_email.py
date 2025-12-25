# FILE: app/services/auth/normalize_email.py
# Scop:
#   - Normalizare email pentru deduplicare (case-insensitive).
#
# Debug:
#   - Dacă vezi duplicate, înseamnă că nu folosești email_normalized în query/UNIQUE.

def normalize_email(email: str) -> str:
    if email is None:
        return ""
    return str(email).strip().lower()
