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
  is called out explicitly as a limitation in the README.
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
  way to invalidate one early (e.g. on logout or compromise). Flagged as a
  known limitation and a concrete "what I'd add next" in
  the README rather than building a token-denylist table for a
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
