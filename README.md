# Seguimiento de Leads

Aplicación de gestión y seguimiento de leads con plantillas de correo, recordatorios automáticos e inteligencia artificial para clasificar respuestas y proponer contestaciones.

## Estado

**Fase 1 — Esqueleto + CRUD de leads** *(en curso)*

- [x] Backend FastAPI + PostgreSQL + Alembic
- [x] Modelos: Tenant, User, Lead, Contact, Template, FollowUp, EmailAccount
- [x] Auth JWT (registro, login, usuario actual)
- [x] CRUD de leads, plantillas, seguimientos y contactos
- [x] Frontend React + Tailwind con login y tabla de leads
- [x] Docker Compose listo

Siguientes fases:
- **Fase 2** — Integración Gmail (OAuth, envío y lectura de correos)
- **Fase 3** — Recordatorios automáticos vía Celery
- **Fase 4** — Clasificación y propuestas de respuesta con Claude

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic |
| DB | PostgreSQL 16 |
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Auth | JWT (HS256) |
| Workers (fase 3) | Celery + Redis |
| IA (fase 4) | Claude API |
| Despliegue | Docker Compose (AWS EC2) |

## Multi-tenant

Cada usuario pertenece a un `Tenant`. Todas las tablas de negocio incluyen `tenant_id` y los endpoints filtran por el tenant del usuario autenticado.

## Arranque rápido

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (docs en `/docs`)
- Frontend: http://localhost:5173

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
