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
