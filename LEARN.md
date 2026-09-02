# Week 1 drills

This repo is the answer key. The point of week 1 is to be able to rebuild it without
one. Work through the drills, then delete your copy and write the pieces again from a
blank file.

The test after each day is the same: **close this repo and do it from memory.**

---

## Day 1 - Git, properly

You can `add`, `commit`, `push`. The gap is everything that happens when work goes
sideways, which is where a messy history actually costs you.

Cover: branching; merge vs rebase and when each is right; `rebase -i` to squash and
reword; conflict resolution; `.gitignore`; atomic commits; `git log --oneline --graph`;
`reflog` as the undo button; the PR workflow.

**Drill** - on your `cube-trainer` repo, not this one:

1. `git switch -c drill/rebase`
2. Three separate commits, each doing one thing.
3. `git rebase -i main` - squash the last two, reword the first.
4. Change the same line on `main` and on your branch, rebase, resolve the conflict.
5. Push, open a PR, merge it.
6. `git reflog`, then reset to a commit from step 2 and back again.

**Done when:** you can create and resolve a conflict on purpose without looking
anything up, and you know what `reflog` is for before you need it.

---

## Day 2 - The Python you skipped

Cover: decorators, including `functools.wraps` and decorators that take arguments;
generators and `yield`; context managers (`contextlib.asynccontextmanager` is used in
`main.py`); `async`/`await`; `asyncio.gather`; `httpx.AsyncClient`; type hints;
Pydantic v2 models and validators; `src/` layout; pytest fixtures.

Read in this repo: `config.py` (a validator that turns a comma string into a list),
`cache.py` (a `Protocol` - structural typing, no inheritance), `db.py` (an async
generator dependency), `main.py` (`asynccontextmanager` for lifespan).

**Drill** - a new throwaway file:

1. Fetch 50 URLs concurrently with `httpx.AsyncClient` and `asyncio.gather`.
2. Put a rate-limiting decorator on the fetch, capped at 5 concurrent requests
   (`asyncio.Semaphore`), preserving the wrapped function's name with `functools.wraps`.
3. Make the decorator take the limit as an argument - so it is a decorator factory,
   which is the part everyone gets wrong.
4. Feed the results through a generator pipeline that filters then transforms, and
   confirm nothing is materialised until you iterate.
5. Test it with pytest and a fixture, no network.

**Done when:** you can explain why a decorator factory has three nested functions, and
what `yield` buys you over building a list.

---

## Day 3 - FastAPI and Postgres

Cover: routers; dependency injection and why `Annotated[X, Depends(...)]` is the
modern form; request/response models; exception handlers; SQLAlchemy 2.0 async
(`Mapped`, `mapped_column`, `async_sessionmaker`); Alembic; API-key auth.

Read in this repo, in this order: `deps.py`, `db.py`, `repository.py`,
`routers/items.py`, `errors.py`.

**Drill** - build a second resource in this repo:

1. Add a `Tag` model with a many-to-many relation to `Item`.
2. `alembic revision --autogenerate -m "add tags"`, read the generated file before
   trusting it, apply it, then `alembic downgrade -1` and confirm it reverses.
3. A `TagRepository` and a `/tags` router with the same shape as `items`.
4. `POST /items/{id}/tags` to attach one, returning 404 for either missing id.
5. Tests for all of it, including the failure cases.

**Done when:** you can write a router, a repository, and a migration without copying
from `items.py`.

---

## Day 4 - Docker, CI, deploy

Cover: `Dockerfile` layer caching and why dependencies are copied before source;
multi-stage builds; `docker compose` with healthchecks and `depends_on: condition`;
config through the environment; GitHub Actions; a real deploy.

Read in this repo: `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`.

> **Docker is not installed on this machine.** Install Docker Desktop for Windows
> first - WSL2 backend - and check `docker --version` and `docker compose version`.

**Drill:**

1. `docker compose up --build`, then hit `/readyz` and confirm both checks pass.
2. `docker compose stop redis`, hit `/readyz` again, watch it return 503. That is
   readiness doing its job.
3. Break the Dockerfile on purpose: copy `src` before `pyproject.toml`, rebuild
   twice, and watch the dependency layer stop being cached.
4. Push to GitHub and get all three CI jobs green.
5. Deploy to Fly.io. Set `APP_API_KEYS` as a secret, not an env var in the config.
6. Hit the public URL. That link goes in your CV this week.

**Done when:** there is a URL a stranger can open.

---

## What to be able to answer

By Sunday you should be able to answer these cold, because interviewers ask them:

- Why is the session a dependency rather than a global?
- What does `pool_pre_ping` prevent?
- Why does `/readyz` exist separately from `/healthz`?
- Why `secrets.compare_digest` instead of `==`?
- What breaks if two replicas both run `create_all` at startup?
- Why is `ItemOut` a different class from `Item`?
- Why does the update path delete the cache key instead of overwriting it?
- What does a multi-stage Docker build actually save you?

If any answer is fuzzy, the fix is in this repo - go read that file.
