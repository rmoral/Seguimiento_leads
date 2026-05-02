# Seguimiento de Leads

Aplicación de gestión y seguimiento de leads con plantillas de correo, recordatorios automáticos e inteligencia artificial para clasificar respuestas y proponer contestaciones.

## Estado

**Fase 1 — Esqueleto + CRUD de leads** *(completada)*
**Fase 2 — Integración Gmail** *(completada)*
**Fase 3 — Recordatorios automáticos** *(completada)*

- [x] Backend FastAPI + PostgreSQL + Alembic
- [x] Modelos: Tenant, User, Lead, Contact, Template, FollowUp, EmailAccount
- [x] Auth JWT (registro, login, usuario actual)
- [x] CRUD de leads, plantillas, seguimientos y contactos
- [x] Frontend React + Tailwind con login y tabla de leads
- [x] Docker Compose listo
- [x] OAuth con Gmail, tokens cifrados con Fernet
- [x] Envío de correos desde la cuenta conectada (genera Contact saliente)
- [x] Sincronización del buzón: empareja por dirección de correo, deduplica por message_id, promueve estado del lead a `responded`
- [x] Abstracción `EmailProvider` lista para añadir Outlook/SMTP
- [x] Worker Celery + Beat: sincronización de buzones cada 15 min, detección diaria de leads silenciosos, digest diario al usuario
- [x] Configuración por tenant del umbral de días y activación de recordatorios

Siguientes fases:
- **Fase 4** — Clasificación y propuestas de respuesta con Claude

## Tareas automáticas (Fase 3)

Tres tareas periódicas se ejecutan en el worker Celery:

| Tarea | Frecuencia | Qué hace |
|---|---|---|
| `sync_all_inboxes` | cada 15 min | Por cada `EmailAccount` conectada, descarga correos nuevos. Un fallo en una cuenta no detiene las demás. |
| `create_followups_for_silent_leads` | diaria, 06:00 UTC | Crea un `FollowUp` pendiente para cada lead que lleva más de N días sin respuesta (N por tenant). Saltea leads en estado terminal (`won`/`lost`/`cold`) o que ya tienen un seguimiento pendiente. |
| `send_daily_digest` | diaria, 07:00 UTC | Envía a cada usuario un correo con la lista de seguimientos pendientes. Usa la cuenta Gmail conectada del propio tenant. No re-envía si ya se envió hoy. |

Cada tenant configura desde **Ajustes → Recordatorios automáticos**:
- `auto_reminders_enabled`: activa/desactiva la generación
- `reminder_after_days`: umbral en días (1–365)

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic |
| DB | PostgreSQL 16 |
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Auth | JWT (HS256) |
| Email | Gmail API (extensible vía `EmailProvider`); tokens cifrados con Fernet |
| Workers (fase 3) | Celery + Redis |
| IA (fase 4) | Claude API |
| Despliegue | Docker Compose (AWS EC2) |

## Multi-tenant

Cada usuario pertenece a un `Tenant`. Todas las tablas de negocio incluyen `tenant_id` y los endpoints filtran por el tenant del usuario autenticado.

## Arranque rápido

```bash
cp .env.example .env
# Genera la clave de cifrado (obligatoria en producción):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Pega el valor en ENCRYPTION_KEY dentro de .env
docker compose up --build
```

- API: http://localhost:8000 (docs en `/docs`)
- Frontend: http://localhost:5173

## Configurar Gmail OAuth (Fase 2)

Para conectar cuentas de Gmail necesitas credenciales OAuth en Google Cloud:

1. Entra en https://console.cloud.google.com/ y crea un proyecto.
2. **APIs y servicios → Biblioteca**: habilita **Gmail API**.
3. **APIs y servicios → Pantalla de consentimiento OAuth**: configura el consentimiento (modo *External* en pruebas, añade tu correo como tester). Scopes mínimos:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `openid` y `userinfo.email`
4. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth → Aplicación web**:
   - URI de redirección autorizada (local): `http://localhost:8000/email-accounts/gmail/callback`
   - URI de redirección autorizada (producción): `https://TU_DOMINIO/email-accounts/gmail/callback`
5. Copia el *Client ID* y *Client Secret* a tu `.env`:
   ```
   GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
   GMAIL_CLIENT_SECRET=xxx
   GMAIL_REDIRECT_URI=http://localhost:8000/email-accounts/gmail/callback
   OAUTH_FRONTEND_REDIRECT=http://localhost:5173/settings
   ```

Luego en la app: **Ajustes → Conectar Gmail**. Tras autorizar quedará listada y podrás:
- **Sincronizar**: descarga correos nuevos del buzón y los asocia a leads cuya dirección coincida.
- Desde un lead, **Enviar**: envía un correo (queda registrado como `Contact` saliente).

Las credenciales OAuth se almacenan cifradas (Fernet) usando `ENCRYPTION_KEY`. **Nunca** las comitas.

## Estructura

```
seguimiento_leads/
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/       # Routers
│   │   ├── core/      # Config, security
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   ├── alembic/       # Migrations
│   └── tests/
├── frontend/          # React app
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       └── pages/
└── docker-compose.yml
```

## Tests

El juego de pruebas cubre auth, JWT, leads, plantillas, seguimientos, contactos, casos límite y aislamiento por tenant. Se ejecuta con cobertura mínima del 85%.

### Ejecución local (sin Docker)

```bash
make install      # crea backend/.venv y descarga dependencias
make test         # ejecuta toda la suite con cobertura
make test-fast    # solo tests, sin cobertura (más rápido)
```

Tras `make test`, el informe HTML está en `backend/htmlcov/index.html`.

### Ejecución dentro de Docker

```bash
docker compose exec backend pytest
```

### Ejecución de un test concreto

```bash
cd backend && .venv/bin/pytest tests/test_leads.py::TestLeadCRUD -v
```

### CI

Cada push a `main` o a una rama `claude/**` ejecuta:

- Backend: `pytest` con cobertura
- Frontend: `tsc --noEmit` y `vite build`

Definido en `.github/workflows/ci.yml`.
