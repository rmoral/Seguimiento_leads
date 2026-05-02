from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Tenant, User
from app.schemas.tenant import TenantSettingsOut, TenantSettingsUpdate

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/settings", response_model=TenantSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Tenant:
    tenant = db.get(Tenant, current.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/settings", response_model=TenantSettingsOut)
def update_settings(
    payload: TenantSettingsUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Tenant:
    tenant = db.get(Tenant, current.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    db.commit()
    db.refresh(tenant)
    return tenant
