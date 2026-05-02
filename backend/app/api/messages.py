from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import EmailAccount, Lead, User
from app.schemas.message import SendMessageIn, SendMessageOut, SyncResult
from app.services.email import get_provider
from app.services.messaging import send_message, sync_inbox

router = APIRouter(prefix="/email-accounts/{account_id}", tags=["messages"])


def _account_or_404(
    account_id: int, db: Session, current: User
) -> EmailAccount:
    acc = db.get(EmailAccount, account_id)
    if acc is None or acc.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Email account not found")
    return acc


@router.post("/send", response_model=SendMessageOut, status_code=status.HTTP_201_CREATED)
def send(
    account_id: int,
    payload: SendMessageIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> SendMessageOut:
    acc = _account_or_404(account_id, db, current)
    lead = db.get(Lead, payload.lead_id)
    if lead is None or lead.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Lead not found")

    provider = get_provider(acc.provider)
    try:
        contact = send_message(
            db=db,
            account=acc,
            lead=lead,
            provider=provider,
            subject=payload.subject,
            body=payload.body,
            to=payload.to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Send failed: {exc}") from exc

    return SendMessageOut(contact_id=contact.id, external_id=contact.external_id or "")


@router.post("/sync", response_model=SyncResult)
def sync(
    account_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> SyncResult:
    acc = _account_or_404(account_id, db, current)
    provider = get_provider(acc.provider)
    try:
        result = sync_inbox(db=db, account=acc, provider=provider)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc
    return SyncResult(**result)
