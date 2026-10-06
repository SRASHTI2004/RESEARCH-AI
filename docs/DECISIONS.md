# Engineering decisions log

This file records decisions made during the rebuild that weren't explicitly
specified, along with the reasoning, so the "why" isn't lost. Newest entries
at the bottom of each phase section.

## Phase 0 — Git foundation & config

- **Git repo location:** the pre-existing `.git` on this machine was rooted at
  the home directory, not at the project folder — it
  belonged to an unrelated old "calculator" project (remotes `calculator` /
  `calculator-project`, an unrelated repo). That repo was left
  completely untouched (deleting/rewriting a repo outside this project's
  scope is risky and unnecessary). Instead, a fresh git repo was initialized
  directly inside `researchai/`, scoped correctly to just this project. The
  stray-remote cleanup didn't apply once this was discovered —
  there was nothing to remove from the new repo.
- **Dependency pinning:** the project's venv had no packages actually
  installed (`pip freeze` was empty), so versions were pinned to known-good
  recent stable releases compatible with Python 3.12 rather than introspected
  from the environment. Versions will be bumped deliberately, not floated.
- **`.env.example`:** added `GROQ_MODEL` alongside `GROQ_API_KEY` in
  anticipation of Phase 1's shared LLM client factory, which reads the model
  name from env instead of hardcoding it in every agent file.
- **API key rotation:** an exposed API key was rotated
  before this phase began.

## Scope decisions carried over from planning

- **MinIO is deferred** to an optional Phase 9 — the final report (including
  numbered sources) is stored as text/JSON in Postgres, which is sufficient
  for a single-file text artifact and avoids standing up object storage for
  no real benefit at this project's scale.
- **Search provider is behind an interface** (`SearchProvider` protocol) so
  DuckDuckGo (free, no key) is the default implementation and Tavily (or
  others) can be swapped in later without touching pipeline logic.

## Phase 1 — Backend restructure & LLM layer

- **Layout:** `app/core` (config, logging, llm), `app/pipeline` (LangGraph
  agents + graph), `app/schemas` (Pydantic I/O), `app/services` (orchestration
  layer between routers and the pipeline), `app/api/routers` (HTTP layer).
  `app/services/research_service.py` is a thin passthrough today but is
  where Phase 2 (search) and Phase 3 (persistence) logic will live, so
  routers never import pipeline internals directly.
- **LLM layer made provider-agnostic mid-phase** (user request, folded into
  Phase 1 rather than deferred): `app/core/llm/` is now a package —
  `base.py` (the `LLMProvider` interface), `providers.py` (Gemini, Groq,
  Ollama implementations), `factory.py` (ordered fallback + per-provider
  retry/backoff). Default chain is `gemini,groq` (Ollama is local-only and
  opt-in — it's not auto-selected since most environments won't have a
  local server running).
- **Rate-limit detection is text-based** (`ProviderRateLimited` raised when
  the exception message contains markers like "429", "quota", "rate limit").
  This is a pragmatic choice — provider SDKs don't expose a consistent
  structured error type across Gemini/Groq/Ollama — and it's exercised
  directly in tests via a stub provider rather than relying on a real
  provider actually hitting its rate limit.
- **Per-stage model override** is intentionally minimal: only a
  `*_WRITER_MODEL` override per provider (the Writer stage is the one most
  likely to benefit from a stronger model; Researcher/Analyzer/Reviewer use
  each provider's default model). A fully generic per-stage-per-provider
  matrix was judged not worth the config complexity at this project's scale.
- **Status vocabulary:** each agent sets `status` to the stage it just
  *completed* (`researching` → `analyzing` → `writing` → `done`), or
  `failed` with an `error` message. The graph uses conditional edges to
  short-circuit remaining stages once `status == "failed"` — this is the
  foundation Phase 5's per-stage progress persistence will build on.
- **Retry budget is read at call time, not decoration time:** the
  `@retry` decorator in `factory._call_with_retries` is applied to a
  function defined *inside* the call (not at module import), so
  `settings.llm_max_retries` can be changed at runtime (and in tests via
  monkeypatch) without re-importing anything.
- **Dev dependencies split out** into `requirements-dev.txt` (pytest,
  pytest-mock, httpx) layered on top of `requirements.txt` — this is the
  standard split so production images don't install test tooling.

## Phase 2 — Pivot to Company Research Brief

- **Search library:** `duckduckgo-search` is deprecated upstream in favor of
  `ddgs` (same author, same `DDGS` class/API) — used `ddgs` directly rather
  than the deprecated package. Confirmed live: it searches across DuckDuckGo
  plus several other backends (Brave, Mojeek, Yahoo, Startpage, Google) and
  falls back automatically when one is rate-limited (observed live: Brave
  and Google both returned 429 for some queries and it transparently used
  another backend).
- **Content extraction:** `trafilatura.fetch_url()` returned nothing against
  at least one real site (likely a default-UA/TLS
  quirk); switched to fetching with `requests` (custom User-Agent, explicit
  timeout) and passing the HTML string into `trafilatura.extract()`
  separately — more robust and keeps fetch timeout under our own control.
  `fetch_page_text()` never raises; a failed fetch falls back to the
  search-result snippet rather than dropping the source.
- **Groq's model catalog had moved on:** `llama-3.3-70b-versatile`
  (the original hardcoded model) now 404s — Groq's currently-available free
  models are OpenAI's open-weight `gpt-oss` family. Defaults updated to
  `openai/gpt-oss-20b` (default/fast stages) and `openai/gpt-oss-120b`
  (Writer stage override). **Lesson:** free-tier model catalogs change
  under you; this is exactly why the model name is an env var, not a
  hardcoded string.
- **Known limitation — Groq free tier is tight for a 4-stage pipeline:**
  Groq's free tier caps at 8000 tokens/minute, and each stage's prompt
  includes the previous stages' full output, so cumulative usage across
  Researcher → Analyzer → Writer → Reviewer can exceed that within the same
  rolling minute for content-rich companies — confirmed live (3/4 stages
  succeeded with real content before the Reviewer stage hit the cap). The
  fallback/retry logic handled it exactly as designed (backoff, then a
  clear "rate limited" error) — but with only Groq configured there's no
  second provider to fall back *to*. **Recommendation documented in
  README:** add a free Gemini API key (`GEMINI_API_KEY`) as the primary
  provider — its free tier is substantially more generous — and Groq
  becomes a true fallback rather than the only option. Default
  `search_results_per_query` (2) and `search_max_content_chars` (1200) were
  also trimmed from initial values (3 / 4000) specifically to reduce the
  chance of hitting this on Groq-only setups.
- **Real bug found via live smoke test, not mocks:** Groq's `gpt-oss-120b`
  returned HTTP 200 with a genuinely empty content string on one real call
  under load (reasoning tokens likely consumed the completion budget before
  any final-answer tokens were emitted). Mocked tests couldn't have caught
  this — they mock at the `invoke_llm` boundary. Fixed by treating an
  empty/whitespace response as a retryable failure
  (`EmptyLLMResponseError`) inside `_call_with_retries`, so it now retries
  and ultimately falls back to the next provider instead of silently
  producing an empty report. Covered by
  `test_empty_response_is_treated_as_failure_and_falls_back`.
- **Reviewer's "fact-check" is an LLM self-review, not a real verifier:**
  it re-reads the draft against the source list and is instructed to flag
  claims whose citation number doesn't exist — this catches citation
  bookkeeping errors (wrong/missing [n]) but does NOT verify that the cited
  source *actually supports* the claim's content (that would need per-claim
  NLI/entailment checking against source text, out of scope here). This
  is listed under Known limitations in the README.
- **Tavily was not implemented** (only the `SearchProvider` interface
  exists for it) — DuckDuckGo/`ddgs` fully satisfies the free, no-key
  requirement, and adding Tavily later is a single new file in
  `app/core/search/` plus a registry entry.

## Phase 3 — Persistence

- **SQLite fallback, Postgres-targeted schema:** `app/core/db.py` reads
  `DATABASE_URL` directly — no Postgres-only column types were used
  (`String`/`Text`/`DateTime`/`Integer` only), so the autogenerated Alembic
  migration (verified live against SQLite in this no-Docker environment)
  applies unchanged against Postgres. `docker-compose.yml` (Phase 7) will
  point `DATABASE_URL` at Postgres; nothing in the models/migration needs
  to change for that.
- **MinIO still deferred** (per the original scope change) — report text
  and numbered sources are columns/rows in Postgres (`research_jobs`,
  `research_sources`), not files.
- **A failed job is still persisted**, not discarded: `research_service.
  run_research` creates the job row before running the pipeline and saves
  whatever state exists (including partial research/analysis/report from
  stages that succeeded before a later stage failed, plus the error
  message) regardless of outcome. Verified live: a Reviewer-stage failure
  still left research/analysis/report from the 3 successful stages
  queryable via `GET /research/{id}`, and the job shows up with
  `status=failed` in `GET /research` history. This is what makes a later
  history page in the UI meaningful even for failed runs.
- **No user/ownership column yet** — `ResearchJob` has no `owner_id`.
  Deliberately deferred to Phase 4, which introduces `users` and adds the
  foreign key in its own migration, rather than guessing at the auth shape
  now.
- **`sources` API field drops the fetched `content`** (only
  index/title/url/snippet are returned) — `content` is the full
  (up to ~1200-char) page extract used only as LLM input; returning it over
  the API would bloat responses for no UI benefit.
- **List endpoint added now, not deferred to the frontend phase** —
  `GET /research` (history) and `GET /research/{id}` exist as soon as
  persistence does, since they're trivial once the repository layer exists
  and Phase 6's history page needs them.

## Phase 4 — Auth & RBAC

- **`bcrypt` directly, not passlib:** passlib's bcrypt backend has known
  compatibility problems with bcrypt>=4.1 (it probes a removed
  `__about__` attribute). Calling `bcrypt.hashpw`/`checkpw` directly avoids
  an unmaintained compatibility shim entirely for one extra line of code.
- **`PyJWT`, not python-jose:** simpler API, more actively maintained,
  does everything needed here (HS256 sign/verify, exp/iat handling).
- **Access + refresh tokens both carry a `type` claim** (`"access"` /
  `"refresh"`) so one can never be replayed as the other — enforced in
  `get_current_user` (access-only) and `auth_service.refresh_access_token`
  (refresh-only), and covered by
  `test_refresh_rejects_an_access_token`.
- **No refresh-token revocation/blacklist store.** A stolen refresh token
  is valid until it expires (7 days by default) — there's no server-side
  way to invalidate one early (e.g. on logout or compromise). Accepted as a
  known limitation (a token denylist is the next step) rather than building a token-denylist table for a
  portfolio project at this scale.
- **No self-service admin promotion endpoint exists, deliberately.** A new
  user can never become `admin` through the API — only by direct DB
  access (what the test suite does via `make_user_headers(..., admin=True)`
  manipulating the test DB directly). This avoids a privilege-escalation
  hole; a real deployment would seed the first admin via a migration or
  CLI command.
- **`/auth/login` takes JSON, not an OAuth2 form body.** `OAuth2PasswordBearer`
  is still used for the Bearer-token extraction dependency and Swagger's
  "Authorize" button, but the actual login endpoint takes a plain
  `{email, password}` JSON body — simpler for the React client in Phase 6,
  which will never construct a form-encoded request body.
- **404, not 403, for another user's job.** `GET /research/{id}` returns
  404 whether the job doesn't exist or just isn't yours — this avoids
  confirming to a caller that a given job ID exists at all (a 403 would
  leak that). Covered by `test_user_cannot_see_another_users_job`.
- **No `require_admin` dependency added** — there's currently no
  admin-only *action* in the app (only admin-vs-own row-level filtering on
  `GET /research`, handled inline). Adding an unused reusable dependency
  for a gate that doesn't exist yet would be dead code; if a user-management
  endpoint is added later, `require_admin` is a 3-line dependency to write
  then.
- **Migration downgrade fixed by hand:** Alembic's autogenerated downgrade
  for this migration called `drop_constraint(None, ...)` — an unnamed
  constraint reference that fails on SQLite (and most backends). Rewrote
  both directions using `op.batch_alter_table` with an explicit FK name
  (`fk_research_jobs_owner_id_users`); verified live that `alembic
  downgrade -1` then `alembic upgrade head` both succeed cleanly. This is a
  common Alembic/SQLite gotcha worth knowing, not a one-off bug.

## Phase 5 — Async processing & per-stage progress

- **Celery eager mode as the no-Redis fallback**, not a hand-rolled
  "pretend async" shim: `CELERY_TASK_ALWAYS_EAGER=true` (default here) runs
  `.delay()` synchronously in-process — the same task code path a real
  Redis-backed worker runs, just not actually backgrounded. `docker-compose`
  sets it `false` and runs a real `celery worker` process; nothing in
  `app/worker/tasks.py` changes between the two modes.
- **`graph.stream()`, not `graph.invoke()`, is what makes per-stage
  progress possible.** LangGraph's default stream mode yields
  `{node_name: output}` after *every* node completes (confirmed against
  the installed langgraph 0.2.62 with a throwaway test graph before
  wiring this in) — the task persists the job row after each yielded
  update, so status moves researching → analyzing → writing → done (or
  failed) as it actually happens, not all at once at the end.
- **API contract change: `POST /research` now always returns 202**, never
  502 — it's an async job-creation endpoint now, so success/failure of the
  pipeline itself is conveyed through the `status`/`error` fields in the
  response body (and via polling `GET /research/{id}`), not the HTTP
  status code. Under eager mode the body may already show `status=done` or
  `failed` by the time the 202 arrives (the task already ran
  synchronously) — that's expected and documented, not a bug; a
  Redis-backed worker would return `status=pending` immediately instead.
- **A real bug caught before it shipped:** the Celery task opens its own
  DB session (`SessionLocal()`) independent of FastAPI's
  `Depends(get_db)` — overriding `get_db` for tests (as Phase 3 already
  did) silently does NOT redirect the task's session. First test run
  showed every job stuck at `status="pending"` because the task was
  writing to a different test still passed by writing to the real
  `app.db` file instead of the in-memory test DB. Fixed with an autouse
  fixture patching `app.worker.tasks.SessionLocal` directly (same
  module-attribute-patching pattern used for mocking the LLM/search
  calls). A second, related issue: a test reading progress through a
  long-lived `db_session` fixture while the task's own session writes to
  the *same* StaticPool-shared SQLite connection needs
  `db_session.rollback()` before each read, or it sees a stale snapshot
  from its own still-open transaction instead of the task's latest
  commits — this is a StaticPool/SQLite-testing-specific gotcha, not a
  general multi-session issue (Postgres session isolation behaves
  differently).
- **Celery + native Windows worker processes don't mix well** (Celery's
  default prefork pool needs `os.fork()`, which Windows lacks). Not a
  blocker here since eager mode never starts a worker process at all; the
  real `celery -A app.worker.celery_app worker` command is meant to run
  inside the Linux container from `docker-compose` (Phase 7) — documented
  as a Windows-specific caveat in the README, not something worked around
  in code.

## Phase 6 — React + TypeScript frontend

- **Hand-scaffolded, not `npm create vite`:** this machine's Node is
  20.11.0; the current `create-vite` and several latest-major packages
  (vite 8, vitest 5, jsdom 30, `@testing-library/jest-dom` 7) all require
  Node ≥20.19/22+ and failed outright. Rather than requiring a Node
  upgrade, every package was pinned to the newest version that still
  supports Node 20.11 (vite 6.4.3, vitest 3.2.7, jsdom 26, jest-dom 6.6.3,
  etc. — checked individually via `npm view <pkg> engines` before
  pinning). React 19, react-router 7, and TanStack Query 5 all install and
  run fine regardless (no Node-version gate on the runtime libraries, only
  on the build/test tooling).
- **One known, accepted dev-only vulnerability:** `npm audit` flags
  `@vitest/mocker` (moderate, path-traversal in the test runner's mocking
  layer) — fixing it requires Vitest 5, which needs Node 22+. It's a
  dev-dependency that never ships in the production build; documented
  here rather than silently ignored. Re-run `npm audit` after any future
  Node upgrade.
- **`POST /research` now returns 202, not 200/201** on the frontend's
  "create brief" call — the UI always navigates to `/briefs/:id` and polls
  from there, the same whether the job is still `pending` (real worker) or
  already `done`/`failed` (eager-mode dev fallback). No separate code path
  for the two cases.
- **Polling via `refetchInterval`, not a WebSocket/SSE push channel.**
  TanStack Query's `refetchInterval` callback stops polling once
  `status` is `done`/`failed`. Simpler and sufficient at this scale; a
  WebSocket would be the next step for true push updates.
- **TS types for API responses are hand-written** (`src/api/types.ts`),
  not generated from the FastAPI OpenAPI schema. For a project this size
  the duplication is small and explicit; `openapi-typescript` codegen
  would be the natural upgrade if the schema grew or drifted often enough
  to cause bugs.
- **jsPDF is dynamically imported** inside the export handler, not a
  top-level import — it (plus its `html2canvas`/`dompurify` dependencies)
  added ~230KB gzipped to the *main* bundle in an initial build; splitting
  it into its own chunk means that cost is only paid by someone who
  actually clicks "Export PDF".
- **`dashboard.py` (Streamlit) is retired**, not kept alongside the React
  app — maintaining two frontends against the same (now async + auth'd)
  API wasn't worth it once React existed; `streamlit` dropped from
  `requirements.txt`.
- **CORS wired now, out of Phase 8's order**, because the frontend
  literally cannot call the API cross-origin without it — `CORS_ORIGINS`
  env var (default `http://localhost:5173`, the Vite dev server). Full
  security hardening (rate limiting, stricter prod origin policy) is still
  Phase 8.
- **No browser-automation visual check** — no browser-automation tool
  was set up, so the UI wasn't clicked through in an
  actual browser. What *was* verified: `tsc -b` (clean), `vite build`
  (clean, reasonable bundle sizes after the jsPDF split), `vitest run`
  (13/13 passing, including the trickiest logic — the 401-refresh-retry
  flow in the API client), the Vite dev server booting and serving
  `index.html`, and a live CORS preflight + register/login/`/auth/me`
  round-trip against the real running backend with the frontend's exact
  origin header. The data contracts (TS types vs. Pydantic schemas) match
  by inspection. A manual click-through is still owed
  (register → new brief → watch it progress → history) before considering
  this phase fully done.

## Phase 7 — DevOps & quality gates

- **mypy needed the pydantic plugin** (`plugins = ["pydantic.mypy"]` in
  `pyproject.toml`) — without it, mypy can't see past pydantic's
  metaclass-generated `__init__` and wrongly flagged `ChatGoogleGenerativeAI`'s
  `google_api_key` kwarg (actually valid — it's a field alias) as an
  unexpected argument. With the plugin, zero errors.
- **`B008` (Depends-in-default-args) is ignored project-wide** in Ruff —
  it's FastAPI's own documented, idiomatic dependency-injection pattern,
  not a bug; the bugbear rule just doesn't special-case FastAPI.
- **Found and discarded a real upgrade attempt mid-phase:**
  `langchain-google-genai` 2.0.9 (installed since Phase 1) emits a
  `FutureWarning` that its underlying `google.generativeai` SDK is fully
  deprecated upstream in favor of `google.genai`. Tried upgrading to
  `langchain-google-genai==4.4.0` (which uses the new SDK) — it requires
  `langchain-core>=1.0`, which conflicts with `langchain-groq==0.2.3`,
  `langchain-ollama==0.2.3`, and `langgraph==0.2.62` (all pinned to
  `langchain-core<0.4`). Upgrading just one provider package would mean
  upgrading the entire LangChain stack simultaneously — real breaking-change
  risk, out of scope for a quality-gates phase. Reverted to 2.0.9 (still
  functional, just unmaintained upstream) and documented this as a known
  tech-debt item / upgrade path rather than silently leaving the warning
  unexplained. Good interview talking point: dependency version skew in a
  fast-moving ecosystem, and when an upgrade is/isn't worth the risk.
- **A real, interview-worthy bug mypy caught:** `AIMessage.content` from
  every LangChain chat model is typed `str | list[str | dict]` (to allow
  multimodal responses), but `LLMProvider.invoke()` promises a plain `str`.
  Every provider was silently relying on it always being a string at
  runtime for our text-only prompts. Added `_as_text()` to assert this
  explicitly (raises `TypeError` if it's ever not a string) instead of
  suppressing the mypy error — turns a latent assumption into a checked
  one.
- **Dockerfiles/docker-compose.yml are written but NOT verified live** —
  Docker wasn't available yet (checked again this phase;
  still absent). Validated what's possible without it: `docker-compose.yml`
  parses as valid YAML with the expected 5 services
  (postgres/redis/api/worker/frontend), and the Postgres-compatible
  schema/`DATABASE_URL`-only design from Phase 3 means the same migrations
  that ran against SQLite here should apply unchanged against the
  Postgres container. **Still to do: run `docker compose up --build`
  once** to confirm — this is the single biggest unverified piece of the
  whole rebuild.
- **`api`/`worker` share one Dockerfile image**, differing only by the
  `command:` override in docker-compose (`worker` runs
  `celery -A app.worker.celery_app worker` instead of the default
  `alembic upgrade head && uvicorn ...`) — avoids maintaining two nearly
  identical images.
- **Vite bakes `VITE_API_URL` in at build time, not runtime** — so
  `frontend/Dockerfile` takes it as a build `ARG`, not a container
  `environment:` variable (a runtime env var would have no effect; the
  value has to be set before `npm run build` runs inside the image).
- **CI needs no API keys or infra at all**: the backend job never touches
  Groq/Gemini/a real database (everything's mocked per Phase 1-3's test
  design) and Celery defaults to eager mode, so `CELERY_TASK_ALWAYS_EAGER`
  doesn't even need setting in CI. This was a deliberate design payoff
  from earlier phases, not incidental — a CI pipeline that needed real
  secrets or `services:` containers would be meaningfully more complex to
  set up and maintain.
- **Pre-commit's mypy/frontend-lint hooks use `language: system`**, not an
  isolated mirror environment — they run via whatever `mypy`/`npm` is on
  PATH (the project's own venv must be active). This is deliberate: an
  isolated mirror would need its own duplicate copy of every stub package
  and the pydantic plugin config to agree with `pyproject.toml`, which is
  more to keep in sync than it's worth here.

## Phase 8 — Observability & security hardening

- **Rate limiting via `slowapi`**, keyed by client IP, `memory://` storage
  by default (fine for a single dev process — `RATE_LIMIT_STORAGE_URI` env
  var points it at Redis for a real multi-worker deployment, a different
  DB index than Celery's broker/backend so keys never collide). Applied to
  `/auth/register` (5/min), `/auth/login` (10/min), `/auth/refresh`
  (20/min), and `POST /research` (10/min — it's the expensive,
  pipeline-triggering endpoint). Live-verified: the 6th register attempt
  in a minute correctly gets 429.
- **Request-logging middleware is deliberately minimal** — method, path,
  status, duration only, no bodies or headers. Logging request bodies
  would mean writing plaintext passwords (`/auth/login`,
  `/auth/register`) straight into application logs; that's a worse
  security posture than not having request logging at all.
- **CORS now rejects a `*` origin at startup**, not just at request time —
  a wildcard origin combined with `allow_credentials=True` (this app sends
  Bearer tokens) is already rejected by browsers per the CORS spec, but
  failing loudly at app startup is a clearer signal than a silently-broken
  CORS policy discovered later in production.
- **Found and fixed a real test-isolation bug the new rate limiter
  caused**: `TestClient` always presents the same fake client address, so
  without resetting the limiter between tests, auth-endpoint rate limits
  (exercised by nearly every test via `auth_headers`/`make_user_headers`)
  got exhausted partway through the suite and every subsequent test saw
  429s instead of real responses. Fixed with an autouse
  `limiter.reset()` fixture — the same category of shared-global-state
  issue as Phase 5's `SessionLocal` patching, different root cause.
- **Secrets audit**: `git log --all -p` across every commit, searched for
  known key-prefix patterns (`gsk_`, `AIzaSy`, `sk-`) and generic
  `password=...`-shaped strings — found nothing. `.env` has never been
  tracked (confirmed via `git log --all -- .env`, empty). This is expected
  given Phase 0's git-history reset, but worth actually checking rather
  than assuming.
- **Health check, input validation already existed** from earlier phases
  (Phase 1's `/health`, Pydantic schemas with field constraints
  throughout) — nothing new needed here beyond confirming they're still
  in place.

## Phase 9 (optional) — Object storage

- **`boto3`, not the `minio` SDK** — boto3 is the standard AWS S3 client;
  since MinIO is fully S3-API-compatible, the exact same code works against
  real AWS S3 in production by changing only the endpoint URL and
  credentials. Stronger, more transferable skill to demonstrate than a
  MinIO-specific client.
- **Graceful degradation, same pattern as the LLM provider chain and
  Celery's eager mode**: blank storage credentials (the default) mean
  `is_configured()` is false and every `storage.*` call is a no-op
  returning `None` — never an exception. A completed research job is
  never blocked or failed by object storage being absent or unreachable;
  the export upload happens *after* the job is already marked `done`, in
  a `try/except` that only logs on failure. Covered by
  `test_run_research_job_tolerates_upload_failure`.
- **Client-side export (Phase 6) still works regardless** — Markdown/PDF
  generation happens entirely in the browser from data already in the API
  response. The object-storage export is a *second*, independent path
  ("the server also kept a copy"), not a replacement.
- **`GET /research/{id}/export` returns a short-lived presigned URL**
  (1 hour), not the file itself — the API process never proxies the
  download; the browser fetches directly from MinIO/S3. 404 (not an
  empty/null field) when no export exists, consistent with the project's
  existing "don't confirm things that aren't there" pattern from Phase 4's
  ownership checks.
- **Bucket creation is idempotent and lazy** (`head_bucket` then
  `create_bucket` only on 404) — happens on first upload, not at app
  startup, so a dev who never configures storage never triggers an
  unnecessary MinIO connection attempt at all.
- **Not live-verified** (no Docker/MinIO run yet, same
  limitation as Phase 7) — fully covered by mocked unit tests
  (`tests/test_storage.py`, plus the worker-task integration tests) that
  exercise the real `boto3` exception types (`ClientError`) against a fake
  client, not just stubbed-out success paths. Still to do: confirm a
  real upload/download round-trip after `docker compose up`.

---

# Job Search Assistant extension (JSA phases 1–6)

The project was extended (October 2026) from a single-feature Company
Research Brief app into a personal Job Search Assistant. The brief feature
is kept intact and becomes a "Generate company brief" button on each job.
Phases below are numbered **JSA 1–6** so they don't collide with the
original rebuild's Phases 0–10 above. Nothing here auto-applies to jobs or
auto-sends messages — that's a hard rule, not a missing feature.

## JSA plan (decided up front)

| # | Scope | Key choice |
|---|---|---|
| 1 | Sourcing + storage + rule filter | Public ATS APIs + public remote feeds only; one `jobs` table deduped by fingerprint |
| 2 | LLM scoring + daily digest | Batch-score only the rule-ranked top 30; Telegram + Gmail SMTP independently; CLI + Windows Task Scheduler |
| 3 | Tracker UI | `applications` table, per-user, status pipeline + notes + follow-up dates |
| 4 | Referral helper | Deterministic templates (no LLM, nothing sent, no LinkedIn scraping) |
| 5 | Resume tailoring | Structured YAML master resume; LLM may only reorder/reword; a validator rejects any new number/skill |
| 6 | Brief integration + docs | Reuse `enqueue_research`; reuse a recent brief for the same company |

## JSA Phase 1 — Sourcing, storage, pre-filter

### Sources verified live on 2026-10-03

Every source was called for real before any code was written, and its
terms were read (from the response itself where the API embeds them):

| Source | Endpoint | Terms / limits | Status |
|---|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` | Public Job Board API, published for displaying postings | ✅ used |
| Lever | `api.lever.co/v0/postings/{board}?mode=json` | Public Postings API | ✅ used |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{board}` | Public Posting API | ✅ used |
| Remotive | `remotive.com/api/remote-jobs?category=software-dev` | Link back + credit Remotive; "max 4 times a day"; jobs delayed 24h; no re-submitting to other aggregators | ✅ used, min interval 8h |
| Remote OK | `remoteok.com/api` | Link back + name Remote OK as source; don't use their logo | ✅ used |
| We Work Remotely | category RSS feeds (`/categories/remote-*-programming-jobs.rss`) | No public JSON API; RSS is published for syndication, `robots.txt` allows `/` | ✅ used (RSS) |
| Himalayas | `himalayas.app/jobs/api/search` | Link back + credit Himalayas; data cached 24h ("polling more than once per day provides no benefit"); 20 jobs/page | ✅ used, min interval 20h |
| Arbeitnow | `arbeitnow.com/api/job-board-api` | "Free public API… please do not abuse", link back appreciated. Mostly EU/German jobs → few pass the India/remote filter | ✅ used |
| Adzuna (India) | `api.adzuna.com/v1/api/jobs/in/search/1` | Free developer key required (`app_id` + `app_key`) | ⏸ implemented, **skipped until you add a key** (returns 400 without one) |

**Not used, by design:** LinkedIn, Naukri, Indeed, Glassdoor, Wellfound —
their terms forbid scraping and none offers a free public jobs API.

**Live run result:** 4,472 postings fetched across the 8 keyless sources in
~75 s → 3,638 unique jobs after dedupe → 52 pass the pre-filter.

### Decisions

- **One source interface** (`JobSource.fetch() -> list[NormalizedJob]`)
  mirroring the existing `LLMProvider` / `SearchProvider` pattern. All
  network access goes through `app/core/jobsources/http.py` so tests stub
  exactly two functions, and an autouse fixture makes any un-stubbed call
  fail loudly.
- **Company watchlist** in `config/companies.yaml` (committed — it isn't
  personal). Seeded with 23 boards that were verified to respond on
  2026-10-03 (Indian companies + global companies that hire in India or
  remote). A board that 404s later is logged and skipped; only if *every*
  board of an ATS fails is that source marked `error`.
- **Dedupe key = fingerprint(company, title)**, normalized (case,
  punctuation, "(Remote)", "(m/f/d)" removed). Location is deliberately
  excluded so an aggregator re-post collapses onto the official listing.
  Trade-off: the same title in two cities at one company collapses into
  one row — acceptable for a personal digest (you want one entry per role).
- **Official boards win:** within a run and across runs, a Greenhouse/
  Lever/Ashby copy replaces an aggregator copy of the same role
  (`official_source=True` is shown as a badge and adds +5 to the rule score).
- **`first_seen_at` / `last_seen_at`** on every job; "new" = first seen in
  this run. Digest state (`digested_at`) is added in JSA Phase 2.
- **Per-source polling intervals** via a `source_runs` table (also powers
  the "last fetched" status in the UI and `python -m app.cli sources`).
  `--force` overrides them for manual runs.
- **Pre-filter is biased towards inclusion** — a false reject silently
  loses a job, a false accept just costs one LLM slot. Order: seniority
  words → level-2+ titles (`SDE 2`, `Engineer II`, `Engineer 3`) → title
  must look like a dev role → excluded title words → "N+ years experience"
  (smallest number found, sentence-bounded) → location.
- **Location rules:** India city / "India" passes (any Indian city by
  default; `accept_any_india_city: false` restricts onsite roles to
  `preferred_cities`). Remote passes only if nothing but "remote" /
  "worldwide" / "anywhere" / "APAC" remains — `Remote (US)`,
  `Foster City, CA` or `Pakistan` mean the role is limited to that region.
- **Tightened after looking at real data:** the first live run let through
  "Video Editor Intern", "SDE 2 Infra", and remote roles pinned to US
  cities. `intern` was removed from the title-include list (tech intern
  titles already contain engineer/developer/SDE), a level-2+ title rule was
  added, and the location rule was inverted from "reject known foreign
  regions" to "reject anything that isn't India/global". 80 → 52 matches,
  all plausibly relevant.
- **Genuineness checks** (`app/services/genuineness.py`) are heuristics
  worded as "check this": fees/deposits, Telegram/WhatsApp contact,
  personal email domains, guaranteed placement/no interview, per-day or
  commission-only pay, unusually high pay for a junior title, vague/missing
  company, very short description. Flags never hide a job.
- **Profile** lives in `config/profile.yaml` (git-ignored). If it's missing
  the app falls back to the committed `config/profile.example.yaml` with a
  warning, so a fresh clone still runs.
- **Forbidden-files check:** the brief asked to "update the existing
  forbidden-files check", but none existed (only `.gitignore`). Created
  `scripts/check_forbidden_files.py` (blocks `.env*` except examples,
  `config/profile.yaml`, `data/private/*`, `*.db`, `*resume*.pdf/.docx`,
  keys), wired into pre-commit (staged files) and CI (all tracked files),
  with a test that asserts the repo is currently clean.
- **SQLite timezone gotcha:** `DateTime(timezone=True)` comes back naive on
  SQLite; `ensure_utc()` re-attaches UTC before any date arithmetic so the
  same code works on SQLite and Postgres.
- **New deps:** `PyYAML` (config files), `defusedxml` (parsing WWR's RSS
  safely — no XML entity-expansion attacks from a remote feed).

## JSA Phase 2 — LLM scoring + daily digest

- **Scoring only the top N:** the rule score picks the 30 most promising
  unscored jobs (first seen in the last 14 days); the LLM scores them in
  batches of 10 (3 calls/day) with a 13 s pause between calls. Each job
  gets `llm_score` 0–100, a one-sentence `llm_reason`, and
  `fresher_friendly`. Unscored jobs (LLM down) are just retried next run.
  Output parsing tolerates code fences/prose around the JSON; scores are
  clamped; unknown ids ignored; 2 consecutive failed batches stop the run
  early rather than burning quota.
- **Gemini model retired (found live):** `gemini-2.0-flash` (the repo's
  default since Phase 1) now returns 404 "no longer available", so every
  call had been silently falling back to Groq after wasted retries.
  Switched defaults to Google's rolling alias `gemini-flash-latest`, and
  made 404/"not found"/"no longer available" errors **non-retryable** in
  the LLM factory (they fail the same way every time).
- **Free-tier reality (found live, Oct 2026):** `gemini-flash-latest` is
  5 requests/min and **20 requests/day** on the free tier, and quotas are
  per model. So scoring got its own stage model — `GEMINI_SCORING_MODEL=
  gemini-flash-lite-latest` (and `GROQ_SCORING_MODEL`) — keeping the daily
  job off the company-brief pipeline's quota. Google no longer publishes
  free-tier numbers (only in AI Studio), so this was decided empirically.
- **Daily-quota circuit breaker:** when a provider reports a *per-day*
  quota exhaustion, the factory skips that (provider, stage) for an hour
  instead of re-hitting it (with retries and backoff) for every batch.
  Per-minute limits don't trigger it.
- **Smart description excerpt (found live):** a 1,000-char prefix cut off
  Rubrik's "2027 graduates only" line (char 1,270) and the LLM scored an
  ineligible internship 60. The prompt now sends a 250-char intro plus the
  lines that decide fit (requirements, years, batch, CGPA, location) — same
  token budget, far better signal. The prompt also includes education and
  says a clearly unmet hard requirement means < 30.
- **Years rule broadened (found live):** "3+ years of professional
  software development" and "4–5 years building production apps" have no
  word "experience". A `+` or a range now counts as a requirement; "ago",
  "old", "warranty" etc. don't. 52 → 36 jobs pass on the live data.
- **Digest selection:** AI-scored jobs ≥ `DIGEST_MIN_SCORE` (40) first,
  best first; free slots are topped up with not-yet-scored jobs by rule
  score, labelled "(rule)" — so an LLM outage still yields a digest.
  Only jobs first seen within 7 days; each job is sent at most once.
- **Two independent channels:** Telegram (one compact HTML message, split
  on item boundaries under the 4,096-char limit) and email via SMTP
  (Gmail + App Password; multipart text + HTML table with title, company,
  location, score, reason, red flags, apply link, and "open in app"
  link). Each channel is `disabled` / `not configured` / `sent` /
  `failed: …` independently; a failure is logged and never aborts the run.
  Jobs are marked `digested_at` only if **at least one** channel delivered
  — otherwise they stay queued for tomorrow.
- **Secrets:** the Telegram token is part of the API URL, so a raw
  `requests` exception would print it. Notifier errors are re-raised with
  the token/password replaced by `***` and `from None` (no chained
  traceback). A test injects both secrets into the failure path and asserts
  neither appears in logs or results. `.env.example` placeholders
  (`your-…-here`) count as "not configured".
- **`test-digest`** sends a "[TEST]" digest to every *configured* channel
  even if its `DIGEST_*_ENABLED` flag is still false (verify before you
  switch it on), marks nothing as sent, and uses a sample item when the DB
  is empty.
- **Scheduling: CLI + Windows Task Scheduler** (`scripts/run_daily.ps1`,
  `scripts/register_daily_task.ps1`). Considered: APScheduler inside the
  API process (only runs while the server is up — a laptop's dev server
  usually isn't at 9 am) and GitHub Actions cron (the SQLite DB with
  first-seen/digest state wouldn't persist between runs, and secrets plus
  personal profile would have to live in GitHub). Task Scheduler with
  `-StartWhenAvailable` runs a missed job when the laptop wakes up; no
  Docker, no extra RAM while idle.
- **`run-daily` never raises:** fetch, score and digest are isolated steps
  — all sources failing still scores/sends what's stored; the LLM failing
  still sends a rule-ranked digest.

## JSA Phase 3 — Application tracker

- **`applications` table, per user** (unlike `jobs`, which are shared):
  status (`saved → applied → referral_asked → interview → rejected/offer`),
  notes, `applied_on`, `follow_up_on`. Unique per (user, job) — saving a
  job twice returns the existing entry (idempotent "Save" button).
- **`job_id` is nullable**, so you can also track a role found elsewhere
  (college group, referral) by title + company; title/company/url/location
  are copied from the job at save time so the entry stays readable even if
  the posting is cleaned up later (`ON DELETE SET NULL`).
- **Strictly owner-only, no admin override** — unlike research briefs,
  tracker notes are personal. Other users (admins included) get 404.
- **Follow-up defaults:** moving to `applied` sets `applied_on` = today and
  a reminder 7 days out; `referral_asked` → 5 days; `interview` → 3 days —
  only when you didn't send a date yourself. Changing status resets the
  reminder to the new stage's default. Reminders only count while the
  application is active (not rejected/offer).
- **Reminders surface in two places:** the tracker (overdue / due-today
  badges, "due this week" filter) and the daily digest ("Follow-ups due"
  section in both Telegram and email). The digest includes every user's
  due follow-ups because the digest channels belong to the one person who
  runs this install — documented single-user assumption.
- **Frontend:** `/jobs` (filters: search, min score, source, recency,
  fresher-only, show filtered-out; source status line; Save button),
  `/jobs/:id` (score, reason, red flags, apply link, tracker editor,
  description), `/tracker` (status chips with counts, follow-up filter,
  search, inline status/date/notes editing, manual entries, `?focus=` deep
  link used by the digest). `/` now redirects to `/jobs`; the brief form
  moved to `/briefs/new`. Notes save on blur rather than per keystroke.
- **Dates:** follow-ups are calendar dates (`DATE`, not timestamps), and the
  frontend computes "today" in local time — `toISOString()` is UTC and is
  a day behind in IST before 05:30.

## JSA Phase 4 — Referral helper

- **Templates, not an LLM.** Search strings, checklist and drafts are
  built deterministically from `profile.yaml` + the posting. Reasons:
  instant and free (no quota), and every claim in a draft is traceable —
  the only skills mentioned are ones that are in your profile **and** the
  posting; recipient names are a `[Name]` placeholder, never guessed.
- **No LinkedIn automation of any kind.** The backend never contacts
  LinkedIn. Search strings are text to paste; the "Open search" links are
  plain `linkedin.com/search/results/people/?keywords=…` (or Google) URLs
  that open in *your* browser, under your own session. A `site:linkedin.com/in`
  Google query is offered as a fallback for when LinkedIn search is limited.
- **Searches:** alumni of your college at the company (skipped with a hint
  if `college` is empty), people in the role (title stripped of team/level
  noise: "Software Engineer, Backend (Python)" → "Software Engineer"),
  recruiters / talent acquisition, engineering managers.
- **Drafts:** referral ask, a LinkedIn connection note kept under the
  300-character limit (with shorter fallbacks), recruiter intro ("is this
  open to freshers?"), and a single polite follow-up.
- **Checklist** favours warm paths (alumni → mutuals → team engineers →
  recruiters → college groups) and good manners (ask one or two people,
  confirm the role is open, log it in the tracker).
- **"I asked for a referral"** sets the tracker status to `referral_asked`
  (creating the entry if needed), which also schedules a 5-day follow-up.
- Tests now always use `config/profile.example.yaml` (autouse fixture) —
  no test can read your real profile.

## JSA Phase 5 — Resume tailoring

- **Master resume is structured YAML, not a PDF/DOCX.** `data/private/master_resume.yaml`
  (git-ignored; blocked by `scripts/check_forbidden_files.py`; example in
  `data/master_resume.example.yaml`). Parsing an arbitrary PDF reliably is
  hard; a structured file makes "never invent" checkable because every
  bullet has a stable ID tied to its own job/project.
- **Code orders, the LLM only rewords, a validator decides.** Projects,
  bullets and skills are re-ranked by overlap with the posting's
  technologies (experience keeps chronological order; nothing is added or
  dropped). The LLM rewords the summary and bullets, returned as JSON by
  bullet ID. Each rewrite is checked against *its own item*: no new numbers
  (digits or number words), no technology that item never mentioned, no
  new capitalised names. A failing rewrite is discarded, the original is
  kept and a warning shown. If the LLM is unavailable you still get the
  reordering (`used_llm=false`).
- **Missing keywords are shown, never added.** "In the posting but not in
  your resume" is a prompt for *you* — add it to the master only if true.
- **Keyword vocabulary avoids everyday words** ("go", "rest", "spring") so
  "Spring 2027 internship" isn't read as a technology.
- **Exports:** fpdf2 (PDF) and python-docx (DOCX), single column, standard
  section headings, plain bullets, real selectable text — ATS-friendly. The
  PDF uses a built-in font (no OS font dependency), so typographic
  characters are mapped to ASCII.
- **Tailored versions are stored** (`tailored_resumes`, owner-only like
  the tracker) with the diff, warnings and keywords, so you can see what
  you sent to which company. Downloads go through an authenticated blob
  fetch (a plain link can't carry the bearer token).
- **Synchronous endpoint** (one LLM call, ~5–15 s) rather than a Celery
  job — simpler, and rate-limited to 10/min.

## JSA Phase 6 — Company brief integration + docs

- **No schema change to link jobs and briefs.** A job's brief is found by
  company name (trimmed, case-insensitive) among *your* briefs:
  `GET /jobs/{id}/brief` returns the latest or `null`. Adding a
  `job_id` to `research_jobs` would tie one brief to one posting, but a
  brief is about the company — five Acme jobs should share one brief.
- **`POST /jobs/{id}/brief` reuses `enqueue_research()`** — the exact path
  `POST /research` uses, so progress polling, history, export and
  ownership rules all apply unchanged. Rate-limited 10/min like `/research`.
- **Reuse before regenerate.** A brief costs four LLM calls, so the job
  page shows "View company brief" when one exists and "Regenerate" as a
  secondary action. A failed brief isn't offered for viewing.
- **Docs:** README rewritten around the Job Search Assistant (setup for
  personal files, Telegram/Gmail, Task Scheduler, a daily routine).
