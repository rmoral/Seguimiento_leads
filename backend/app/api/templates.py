from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Template, User
from app.schemas.template import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Template]:
    stmt = (
        select(Template)
        .where(Template.tenant_id == current.tenant_id)
        .order_by(Template.name.asc())
    )
    return list(db.scalars(stmt).all())


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Template:
    tpl = Template(tenant_id=current.tenant_id, **payload.model_dump())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


def _get_or_404(tpl_id: int, tenant_id: int, db: Session) -> Template:
    tpl = db.get(Template, tpl_id)
    if tpl is None or tpl.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.patch("/{tpl_id}", response_model=TemplateOut)
def update_template(
    tpl_id: int,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Template:
    tpl = _get_or_404(tpl_id, current.tenant_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{tpl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    tpl_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    tpl = _get_or_404(tpl_id, current.tenant_id, db)
    db.delete(tpl)
    db.commit()
