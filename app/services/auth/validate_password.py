# FILE: app/services/auth/validate_password.py
# Scop:
#   - Politică parole enterprise (min 12, complexitate, fără date personale).
#
# Debug:
#   - Dacă userii se plâng, ajustezi regula "3 din 4 categorii" dintr-un singur loc.

import re
from fastapi import HTTPException, status


def validate_password_or_raise(password: str, *, email: str, first_name: str, last_name: str) -> None:
    pw = str(password or "")

    if len(pw) < 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola trebuie să aibă minim 12 caractere.")
    if len(pw) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola este prea lungă (max 128).")
    if pw.strip() != pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate începe/termina cu spații.")

    has_lower = bool(re.search(r"[a-z]", pw))
    has_upper = bool(re.search(r"[A-Z]", pw))
    has_digit = bool(re.search(r"\d", pw))
    has_sym = bool(re.search(r"[^A-Za-z0-9]", pw))
    score = sum([has_lower, has_upper, has_digit, has_sym])

    if score < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parola trebuie să conțină cel puțin 3 din: litere mici, litere mari, cifre, simboluri.",
        )

    # Evităm parole care includ identitatea (basic defense)
    e = (email or "").split("@")[0].lower()
    fn = (first_name or "").lower()
    ln = (last_name or "").lower()
    pw_low = pw.lower()

    if e and e in pw_low:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate conține emailul.")
    if fn and len(fn) >= 3 and fn in pw_low:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate conține prenumele.")
    if ln and len(ln) >= 3 and ln in pw_low:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parola nu poate conține numele.")
