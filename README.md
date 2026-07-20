# CriticLoop

Experience-based risk scoring for AI-agent actions — fully local, no paid APIs.

An AI agent (or a user) submits a proposed action; CriticLoop compares it against similar past
experiences and returns a transparent, statistically derived confidence score with a decision:
`approve`, `revise`, or `block`. See [PLAN.md](PLAN.md) for the full specification.

## Status

Phase 4 — confidence scoring and the core evaluation endpoint.
`POST /api/v1/evaluations` embeds the proposed action, retrieves similar past
experiences, and returns an `approve`/`revise`/`block` decision with a
transparent weighted confidence score (no LLM in the loop). The feedback
endpoint that records real outcomes lands next.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (use `source .venv/bin/activate` on macOS/Linux)
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Then visit http://localhost:8000/health → `{"status": "healthy"}`.

Interactive API docs: http://localhost:8000/docs

## Tests

```bash
pytest
```

## Lint

```bash
ruff check .
```
