# FILE: app/services/audit.py

from typing import Optional, Dict, Any

from fastapi import Request
from sqlalchemy.orm import Session

from ..models import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    user_id: Optional[int],
    request: Optional[Request] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    ip = None
    user_agent = None
    if request:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip=ip,
        user_agent=user_agent,
        details=str(details)[:2000] if details else None,
    )
    db.add(log)
    db.commit()
