# FILE: app/services/audit.py

from typing import Optional, Dict, Any
import json

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

    details_str = None
    if details is not None:
        try:
            details_str = json.dumps(details, ensure_ascii=False, default=str)[:2000]
        except Exception:
            details_str = str(details)[:2000]

    log = AuditLog(
        user_id=user_id,
        action=action,
        ip=ip,
        user_agent=(user_agent or "")[:255] if user_agent else None,
        details=details_str,
    )
    db.add(log)
    db.commit()
