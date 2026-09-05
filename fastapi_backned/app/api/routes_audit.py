from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import AuditLog


router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit/{purchase_intent_id}")
async def get_audit_trail(
    purchase_intent_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).where(
        AuditLog.purchase_intent_id == purchase_intent_id
    ).order_by(AuditLog.created_at)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "purchase_intent_id": log.purchase_intent_id,
            "actor": log.actor,
            "event": log.event,
            "payload": log.payload,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]