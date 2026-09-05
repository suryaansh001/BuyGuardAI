from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog


async def log_event(
    session: AsyncSession,
    purchase_intent_id: int | None,
    actor: str,
    event: str,
    payload: dict,
) -> AuditLog:
    log = AuditLog(
        purchase_intent_id=purchase_intent_id,
        actor=actor,
        event=event,
        payload=payload,
    )
    session.add(log)
    await session.flush()
    return log