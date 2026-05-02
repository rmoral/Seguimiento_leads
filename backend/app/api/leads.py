from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Lead, User
from app.schemas.lead import LeadCreate, LeadOut, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, description="Search in name/email/company"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Lead]:
    stmt = select(Lead).where(Lead.tenant_id == current.tenant_id)
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Lead.name.ilike(like)) | (Lead.email.ilike(like)) | (Lead.company.ilike(like))
        )
    stmt = stmt.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Lead:
    lead = Lead(tenant_id=current.tenant_id, **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _get_lead_or_404(lead_id: int, tenant_id: int, db: Session) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Lead:
    return _get_lead_or_404(lead_id, current.tenant_id, db)


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Lead:
    lead = _get_lead_or_404(lead_id, current.tenant_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    lead = _get_lead_or_404(lead_id, current.tenant_id, db)
    db.delete(lead)
    db.commit()
