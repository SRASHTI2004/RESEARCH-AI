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
