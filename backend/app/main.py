from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, contacts, email_accounts, followups, leads, messages, templates
from app.core.config import settings

app = FastAPI(title="Seguimiento Leads API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(templates.router)
app.include_router(followups.router)
app.include_router(contacts.router)
app.include_router(email_accounts.router)
app.include_router(messages.router)
