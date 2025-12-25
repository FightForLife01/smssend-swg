# FILE: app/services/auth/enforce_rate_limit.py
# Scop:
#   - Rate limit DB-backed (nu memory hack, merge și cu multi-worker).
#
# Debug:
#   - Dacă rate-limit nu pare să funcționeze, verifică ce key generezi și dacă ai commit.

from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models import RateLimitState


def enforce_rate_limit_or_raise(
    db: Session,
    *,
    key: str,
    max_count: int,
    window_seconds: int,
    block_seconds: int,
) -> None:
    now = datetime.utcnow()

    state = db.query(RateLimitState).filter(RateLimitState.key == key).first()

    if not state:
        state = RateLimitState(
            key=key,
            window_started_at=now,
            count=1,
            blocked_until=None,
            updated_at=now,
        )
        db.add(state)
        db.commit()
        return

    # Dacă e blocat încă
    if state.blocked_until and state.blocked_until > now:
        retry_after = int((state.blocked_until - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Prea multe cereri. Reîncearcă mai târziu.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    # Reset window dacă a trecut
    window_end = state.window_started_at + timedelta(seconds=window_seconds)
    if now >= window_end:
        state.window_started_at = now
        state.count = 0
        state.blocked_until = None

    state.count += 1
    state.updated_at = now

    if state.count > max_count:
        state.blocked_until = now + timedelta(seconds=block_seconds)
        db.commit()
        retry_after = int(block_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Prea multe cereri. Reîncearcă mai târziu.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    db.commit()
