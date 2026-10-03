"""Technology vocabulary for keyword alignment and the no-invention check.

Terms that are also everyday words ("go", "rest", "express", "spring",
"c", "r") are left out or spelled unambiguously ("golang", "rest api",
"express.js", "spring boot") — "Spring 2027 internship" and "go-to-market"
would otherwise count as technologies.

Used two ways: (1) which of a posting's technologies your master resume
already has (and which are gaps — never auto-added), and (2) catching a
reworded bullet that mentions a technology its original item never did.
"""

import re

TECH_TERMS: tuple[str, ...] = (
    # languages
    "python", "java", "javascript", "typescript", "golang", "rust", "c++", "c#", "ruby", "php",
    "kotlin", "swift", "scala", "dart", "sql", "bash", "html", "css", "sass",
    # frontend
    "react", "react native", "next.js", "vue", "vue.js", "angular", "svelte", "redux", "tailwind",
    "tailwind css", "vite", "webpack", "jquery", "bootstrap", "material ui", "tanstack query",
    "react query", "react hook form", "zod",
    # backend / frameworks
    "fastapi", "django", "flask", "node.js", "express.js", "nestjs", "spring boot", ".net",
    "asp.net", "ruby on rails", "laravel", "graphql", "rest api", "restful", "grpc", "websockets", "pydantic",
    "sqlalchemy", "alembic", "celery", "langchain", "langgraph", "openai", "llm", "rag",
    # data
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch", "kafka",
    "rabbitmq", "dynamodb", "cassandra", "clickhouse", "snowflake", "bigquery", "pandas", "numpy",
    "spark", "airflow", "dbt", "pytorch", "tensorflow", "scikit-learn", "machine learning",
    # infra / tooling
    "docker", "kubernetes", "terraform", "ansible", "aws", "gcp", "azure", "aws lambda", "s3", "ec2",
    "minio", "nginx", "linux", "git", "github", "github actions", "gitlab", "ci/cd", "jenkins",
    "prometheus", "grafana", "sentry", "jwt", "oauth", "pytest", "jest", "vitest", "cypress",
    "playwright", "selenium", "eslint", "prettier", "ruff", "mypy", "figma", "jira", "postman",
    "microservices", "serverless", "agile", "scrum",
)  # fmt: skip

_VOCABULARY = frozenset(TECH_TERMS)


# Different spellings of the same technology count as one, so "REST API
# endpoints" -> "RESTful APIs" is a legitimate rewording, not a new skill.
CANONICAL = {
    "restful": "rest api",
    "postgres": "postgresql",
    "vue": "vue.js",
    "tailwind": "tailwind css",
    "react query": "tanstack query",
}

_cache: dict[str, re.Pattern[str]] = {}


def _pattern(term: str) -> re.Pattern[str]:
    if term not in _cache:
        # Optional plural "s": "REST APIs" contains "rest api".
        _cache[term] = re.compile(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])")
    return _cache[term]


def is_term(word: str) -> bool:
    return word.lower() in _VOCABULARY


def find_terms(text: str, extra: list[str] | None = None) -> set[str]:
    """Canonical lower-cased vocabulary terms (plus `extra`, e.g. the user's
    own skills) present in text."""
    haystack = text.lower()
    vocabulary = _VOCABULARY | {t.lower() for t in extra or []}
    return {CANONICAL.get(term, term) for term in vocabulary if _pattern(term).search(haystack)}
