# fastapi-service-template

The skeleton every service in this portfolio is cloned from: async FastAPI on
Postgres and Redis, API-key auth, real migrations, structured logs, a test suite that
runs with no infrastructure, and CI that checks lint, types, unit tests, a real
database, and the Docker build.

It is deliberately small. Read the whole thing in one sitting, then delete `items`
and build the actual service.

---

## Quickstart

### With Docker (Postgres + Redis + API)

```bash
cp .env.example .env
docker compose up --build
```

Migrations run before the server accepts traffic. Then:

```bash
curl localhost:8000/healthz
curl localhost:8000/readyz
curl -H "X-API-Key: dev-key-change-me" localhost:8000/items
open http://localhost:8000/docs
```

### Without Docker (SQLite, no services required)

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"

export APP_DATABASE_URL="sqlite+aiosqlite:///./local.sqlite3"
alembic upgrade head
uvicorn app.main:app --reload
```

`uv` is faster if you have it: `uv venv && uv pip install -e ".[dev]"`.

---

## Layout

```
src/app/
  config.py       Settings. The only module that reads the environment.
  logging.py      JSON log lines + a request-id context variable.
  errors.py       AppError hierarchy; the only module that knows HTTP status codes.
  db.py           Async engine, session factory, request-scoped session.
  cache.py        Cache protocol, Redis implementation, in-process fallback.
  deps.py         Shared dependencies: settings, session, cache, auth, pagination.
  models.py       SQLAlchemy models. Alembic diffs against these.
  schemas.py      Pydantic wire contracts, kept separate from the models.
  repository.py   Data access. Routers never write SQL.
  routers/        health.py (ops), items.py (the worked example)
  main.py         App factory, lifespan, request middleware.
migrations/       Alembic. One initial revision, reversible.
tests/            Runs on SQLite by default; CI reruns it against Postgres.
```

## Decisions worth knowing

**Settings come from `app.state`, not a module-level cache.** `get_settings` in
`deps.py` reads `request.app.state.settings`. A cached module-level factory means a
test app built with different settings silently reads the real environment - which is
exactly the bug this template hit on its first test run.

**Schemas are not models.** The database shape and the public API shape are allowed
to drift. Serialising ORM objects straight to clients locks the API to the schema.

**Repositories, not fat routers.** Routers translate HTTP; repositories translate SQL.
Each is testable without the other.

**Liveness and readiness are different endpoints.** `/healthz` asks "is this process
wedged"; `/readyz` asks "can I serve traffic", which depends on Postgres and Redis.
Conflating them makes a brief database blip restart every replica.

**Errors are typed, not ad-hoc.** Business code raises `NotFoundError`; only
`errors.py` maps that to 404. Every error response carries the request id.

**API keys are compared with `secrets.compare_digest`.** `==` on a secret leaks its
length and prefix through timing.

**The cache has an in-process fallback.** No Redis running means the same code path,
not a spray of `if cache is not None` checks.

**Migrations run in the entrypoint, never at import.** Two replicas calling
`create_all` at startup race each other.

**The cache is invalidated on write, not rewritten.** The write path should not have
to know the shape of every cached representation.

---

## Configuration

Every variable is prefixed `APP_` and defined in `src/app/config.py`.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `local` | `local` / `ci` / `staging` / `prod`. Docs are disabled in prod. |
| `APP_LOG_LEVEL` | `INFO` | |
| `APP_API_KEYS` | `dev-key-change-me` | Comma-separated. Rotate by adding, then removing. |
| `APP_DATABASE_URL` | local Postgres | Must be an async driver (`+asyncpg` / `+aiosqlite`). |
| `APP_REDIS_URL` | empty | Empty means the in-process cache. |
| `APP_CACHE_TTL_SECONDS` | `60` | |

## Endpoints

| Method | Path | Auth | |
| --- | --- | --- | --- |
| GET | `/healthz` | no | Liveness |
| GET | `/readyz` | no | Readiness; 503 when a dependency is down |
| POST | `/items` | yes | 201, or 409 on duplicate name |
| GET | `/items` | yes | Paginated, `?limit`, `?offset`, `?q` |
| GET | `/items/{id}` | yes | Cached for `APP_CACHE_TTL_SECONDS` |
| PATCH | `/items/{id}` | yes | Partial update, invalidates the cache |
| DELETE | `/items/{id}` | yes | 204 |

## Working on it

```bash
pytest -q                 # 16 tests, no infrastructure needed
ruff check . && ruff format .
mypy

alembic revision --autogenerate -m "add whatever"   # needs a live database
alembic upgrade head
alembic downgrade -1                                 # always check it reverses
```

To run the suite against real Postgres:
`TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app pytest -q`

## CI

`.github/workflows/ci.yml` runs three jobs on every push and PR: **quality**
(ruff, ruff format, mypy, pytest on SQLite), **integration** (the same suite against a
real Postgres, plus a migration up/down/up round trip), and **docker** (the image
builds).

## Deploying to Fly.io

```bash
fly launch --no-deploy
fly postgres create && fly postgres attach <name>
fly redis create
fly secrets set APP_API_KEYS=<a real key> APP_ENV=prod
fly deploy
```

Set the release command to `alembic upgrade head` so migrations run once per deploy
rather than once per machine.

## License

MIT.
