# Architecture (current state)

- `backend/app/main.py`: FastAPI routes and dependency wiring.
- `backend/app/models.py`: SQLAlchemy entities currently implemented for admins, customers, products, and purchases.
- `backend/app/core/security.py`: password hashing and signed bearer tokens.
- `backend/app/integrations/bale/client.py`: async HTTP client for verified minimal operations (`getMe`, `sendMessage`).
- `frontend/src`: RTL React dashboard starter.

SQLite is selected by default for local development. Production startup rejects SQLite and requires a sufficiently long secret key. The current code still calls `create_all` as a development bootstrap; replace it with versioned Alembic migrations before production use. The durable worker, scheduler, provider configuration store, and full domain service layers are not implemented yet.
