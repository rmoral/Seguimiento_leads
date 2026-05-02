from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import FollowUp, Lead, User
from app.schemas.followup import FollowUpCreate, FollowUpOut, FollowUpUpdate

router = APIRouter(prefix="/followups", tags=["followups"])


@router.get("", response_model=list[FollowUpOut])
def list_followups(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[FollowUp]:
    stmt = (
        select(FollowUp)
        .join(Lead, Lead.id == FollowUp.lead_id)
        .where(Lead.tenant_id == current.tenant_id)
    )
    if status_filter:
        stmt = stmt.where(FollowUp.status == status_filter)
    stmt = stmt.order_by(FollowUp.scheduled_at.asc())
    return list(db.scalars(stmt).all())


@router.post("", response_model=FollowUpOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> FollowUp:
    lead = db.get(Lead, payload.lead_id)
    if lead is None or lead.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Lead not found")

    fu = FollowUp(**payload.model_dump())
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


def _get_or_404(fu_id: int, tenant_id: int, db: Session) -> FollowUp:
    fu = db.get(FollowUp, fu_id)
    if fu is None:
        raise HTTPException(status_code=404, detail="FollowUp not found")
    lead = db.get(Lead, fu.lead_id)
    if lead is None or lead.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="FollowUp not found")
    return fu


@router.patch("/{fu_id}", response_model=FollowUpOut)
def update_followup(
    fu_id: int,
    payload: FollowUpUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> FollowUp:
    fu = _get_or_404(fu_id, current.tenant_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fu, field, value)
    db.commit()
    db.refresh(fu)
    return fu


@router.delete("/{fu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_followup(
    fu_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    fu = _get_or_404(fu_id, current.tenant_id, db)
    db.delete(fu)
    db.commit()
