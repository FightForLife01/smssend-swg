# FILE: app/services/rate_limit.py
# Scop:
#   - Rate limiting DB-backed, compatibil cu multi-worker și Postgres.
#
# Debug:
#   - Dacă pare că nu limitează, verifică tabela `rate_limits` și valorile `key`.
#   - Dacă primești erori de concurență pe Postgres, următorul nivel e UPSERT atomic.

from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import RateLimitState


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

    # blocat încă
    if state.blocked_until and state.blocked_until > now:
        retry_after = int((state.blocked_until - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Prea multe cereri. Reîncearcă mai târziu.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    # reset window dacă a trecut
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
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Prea multe cereri. Reîncearcă mai târziu.",
            headers={"Retry-After": str(max(1, block_seconds))},
        )

    db.commit()
