# Secure Notes Backend

This is the backend component for the Secure Notes application, built using FastAPI + SQLAlchemy + PostgreSQL.

## Setup

### Environment Variables
Copy `.env.example` to `.env` and fill in appropriate values.

**Required variables:**
- `POSTGRES_URL`        (e.g. `localhost` or the database container's host)
- `POSTGRES_USER`       (your DB username)
- `POSTGRES_PASSWORD`   (your DB password)
- `POSTGRES_DB`         (DB name for app)
- `POSTGRES_PORT`       (default: 5432)
- `JWT_SECRET_KEY`      (random secure value for JWT signing)
- `JWT_ALGORITHM`       (default: HS256)

### Running the Backend
Install dependencies as per `requirements.txt`, then run the app:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Database Integration
The backend expects the database schema to exist; see [notes_database/README.md](../secure-notes-application-244277-244293/notes_database/README.md) for schema creation instructions.

### API Integration
Set your frontend to use the backend's API base URL via environment (`NEXT_PUBLIC_API_BASE_URL`)

**Swagger/OpenAPI docs:**  
FastAPI serves OpenAPI docs at `/docs` and JSON schema at `/openapi.json`.  
See example usage in the `src/app/api.ts` file in frontend.

---

**Troubleshooting:**  
- "OperationalError" or "could not connect": check DB running, network, and credentials
- "JWT error": check `JWT_SECRET_KEY` and algorithm are set and match between containers