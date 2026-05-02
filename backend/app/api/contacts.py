from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Contact, Lead, User
from app.schemas.contact import ContactCreate, ContactOut

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/by-lead/{lead_id}", response_model=list[ContactOut])
def list_contacts_for_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Contact]:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Lead not found")

    stmt = (
        select(Contact)
        .where(Contact.lead_id == lead_id)
        .order_by(Contact.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Contact:
    lead = db.get(Lead, payload.lead_id)
    if lead is None or lead.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Lead not found")

    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
