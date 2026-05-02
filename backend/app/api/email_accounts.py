"""Endpoints to connect, list and disconnect email accounts (Gmail in Phase 2)."""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import EmailAccount, User
from app.schemas.email_account import AuthorizationUrlOut, EmailAccountOut
from app.services.crypto import encrypt_json
from app.services.email import get_provider
from app.services.email.factory import supported_providers
from app.services.oauth_state import make_state, parse_state

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


@router.get("", response_model=list[EmailAccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[EmailAccount]:
    stmt = (
        select(EmailAccount)
        .where(EmailAccount.tenant_id == current.tenant_id)
        .order_by(EmailAccount.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    acc = db.get(EmailAccount, account_id)
    if acc is None or acc.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Email account not found")
    db.delete(acc)
    db.commit()


@router.post("/{provider}/authorize", response_model=AuthorizationUrlOut)
def authorize(
    provider: str,
    current: User = Depends(get_current_user),
) -> AuthorizationUrlOut:
    if provider not in supported_providers():
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if provider == "gmail" and not (settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET):
        raise HTTPException(
            status_code=503,
            detail="Gmail OAuth is not configured on this server",
        )

    state = make_state(current.id, current.tenant_id, provider)
    url = get_provider(provider).authorization_url(state)
    return AuthorizationUrlOut(authorization_url=url)


@router.get("/{provider}/callback")
def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """OAuth redirect target. Exchanges the code for tokens, stores the
    encrypted credentials and bounces the browser back to the frontend."""
    try:
        ctx = parse_state(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    if ctx["provider"] != provider:
        raise HTTPException(status_code=400, detail="State/provider mismatch")

    impl = get_provider(provider)
    try:
        email, tokens = impl.exchange_code(code)
    except Exception as exc:  # provider errors bubble up as 502
        raise HTTPException(status_code=502, detail=f"OAuth exchange failed: {exc}") from exc

    existing = db.scalar(
        select(EmailAccount).where(
            EmailAccount.tenant_id == ctx["tenant_id"],
            EmailAccount.email == email,
        )
    )
    encrypted = encrypt_json(tokens)
    if existing:
        existing.oauth_tokens = encrypted
        existing.provider = provider
    else:
        db.add(
            EmailAccount(
                tenant_id=ctx["tenant_id"],
                user_id=ctx["user_id"],
                provider=provider,
                email=email,
                oauth_tokens=encrypted,
            )
        )
    db.commit()

    qs = urlencode({"connected": email})
    return RedirectResponse(
        url=f"{settings.OAUTH_FRONTEND_REDIRECT}?{qs}",
        status_code=302,
    )
