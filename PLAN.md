# CriticLoop: Experience-Based Risk Scoring for AI Agents

**One-line description:** A Python service that predicts the reliability of proposed AI-agent actions using similar past experiences and weighted statistical scoring — no paid APIs, no cloud services, fully local.

**GitHub repository name:** `criticloop`

**Cost to build and run:** $0. Everything runs on your own machine.

---

## 1. What CriticLoop Does

A user or AI agent submits:

- The task it's trying to complete
- The action it plans to execute
- The tool it plans to use
- Optional environment context

CriticLoop then:

1. Finds similar previous actions using local sentence embeddings.
2. Reviews which of those previous actions succeeded or failed.
3. Calculates a confidence score using a transparent, weighted formula (no LLM in the loop).
4. Returns `approve`, `revise`, or `block`.
5. Records the real outcome after execution (submitted by the caller).
6. Uses that outcome to inform future decisions.

**Example:**

```text
Task: Find the cheapest nonstop flight to Chicago
Action: Click the first sponsored result
Tool: Browser

Decision: Revise
Confidence: 42%
Reason: Similar actions frequently selected sponsored flights
that did not meet the nonstop requirement.
```

---

## 2. Architecture

```text
Client or AI Agent
        │
        ▼
     FastAPI
        │
        ▼
Action Evaluation Service
        │
        ├── Embedding Generator (local, sentence-transformers)
        ├── Similarity Retriever (NumPy cosine similarity)
        ├── Confidence Scorer (weighted formula)
        └── Decision Engine
        │
        ▼
      SQLite
        │
        ▼
Experience and Outcome Records
```

No external services. No network calls at runtime except loading the embedding model once (cached locally after first download).

---

## 3. Technology Stack — 100% Free, 100% Local

| Area | Technology | Cost |
|---|---|---|
| Language | Python 3.12 | Free |
| API | FastAPI | Free |
| Validation | Pydantic | Free |
| Database | SQLite | Free, no server |
| ORM | SQLAlchemy | Free |
| Migrations | Alembic | Free |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Free, runs locally on CPU |
| Similarity | NumPy | Free |
| Testing | Pytest + FastAPI TestClient | Free |
| Code quality | Ruff | Free |
| Type checking | mypy | Free |
| Packaging | `pyproject.toml` | Free |
| Deployment | Docker (local only) | Free |
| CI | GitHub Actions | Free (public repo) |
| Frontend | Plain HTML/CSS/JavaScript | Free |
| Documentation | Swagger (auto from FastAPI) + README | Free |

**No API keys required anywhere in this project.** No OpenAI, no Claude API, no Qdrant Cloud, no hosted Postgres. Everything runs with `uvicorn app.main:app` on your laptop.

---

## 4. Explicitly Out of Scope for v1 (No Contradictions)

To keep this genuinely $0 and genuinely local, v1 deliberately does **not** include:

- LangGraph (adds an agent framework dependency and complexity before the core idea is proven)
- Qdrant (requires running a separate vector DB service — SQLite + NumPy is sufficient at this scale)
- Redis (no need for streaming until there's a live dashboard to stream to)
- PostgreSQL (SQLite is sufficient for a single-user local service)
- Next.js dashboard (a single static HTML/CSS/JS page is enough for v1)
- Any LLM API calls in the core scoring path (the scoring algorithm is fully transparent statistics — see Section 8)
- Docker Compose with multiple services (one Dockerfile is enough since there's only one service)

These are documented as **future extensions** in Section 18, not part of the current build.

---

## 5. Repository Structure

```text
criticloop/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── experiences.py
│   │   └── evaluations.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   ├── scoring_service.py
│   │   └── evaluation_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── experience_repository.py
│   │
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_experience_api.py
│   ├── test_evaluation_api.py
│   ├── test_retrieval_service.py
│   └── test_scoring_service.py
│
├── scripts/
│   └── seed_database.py
│
├── alembic/
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── LICENSE
├── pyproject.toml
├── PLAN.md          ← this document
└── README.md
```

---

## 6. Database Models

### Experience

```text
id
task
proposed_action
tool_name
environment_context
embedding          # stored as JSON-serialized list[float], no vector DB needed
status             # proposed | approved | revised | blocked | completed
created_at
```

### Outcome

```text
id
experience_id
was_successful
outcome_description
failure_reason
recorded_at
```

### Evaluation

```text
id
experience_id
confidence
decision
evidence_count
scoring_version    # lets you compare scoring algorithms later
created_at
```

**Note on embeddings in SQLite:** Since SQLite has no native vector type, embeddings are stored as JSON-serialized arrays in a `TEXT` column. At query time, all embeddings are loaded into memory and compared using NumPy cosine similarity. This is a documented, intentional design decision — fine up to a few thousand rows, and explicitly noted as a scaling limitation in the README (with Qdrant as the noted future upgrade path).

---

## 7. API Design

### Health check

```text
GET /health
→ {"status": "healthy"}
```

### Experience management

```text
POST   /api/v1/experiences
GET    /api/v1/experiences
GET    /api/v1/experiences/{experience_id}
PATCH  /api/v1/experiences/{experience_id}/outcome
DELETE /api/v1/experiences/{experience_id}
```

### Similarity retrieval

```text
GET /api/v1/experiences/similar?task=...&action=...&limit=5
```

### Evaluation (the core feature)

```text
POST /api/v1/evaluations
```

Request:

```json
{
  "task": "Find a nonstop flight to Chicago",
  "proposed_action": "Click the first sponsored flight",
  "tool_name": "browser",
  "environment_context": "Search result page"
}
```

Response:

```json
{
  "decision": "revise",
  "confidence": 0.61,
  "reason": "Three similar actions were found, but two failed.",
  "evidence_count": 3,
  "similar_experiences": [
    {
      "experience_id": 14,
      "similarity": 0.87,
      "was_successful": false
    }
  ],
  "scoring_version": "v1"
}
```

### View evaluation history

```text
GET /api/v1/evaluations
```

---

## 8. Confidence Scoring Design (No LLM — This Is the Core IP)

Fully transparent, reproducible, testable math. No hidden LLM judgment.

```python
confidence = (
    0.45 * weighted_success_rate
    + 0.25 * average_similarity
    + 0.20 * evidence_strength
    + 0.10 * tool_reliability
)
```

**Weighted success rate** — similar examples weighted by how similar they are:

```python
weighted_success_rate = (
    sum(similarity * success for each result)
    / sum(similarity for each result)
)
```

**Average similarity** — mean cosine similarity of retrieved experiences.

**Evidence strength** — more matching examples increase confidence, capped:

```python
evidence_strength = min(evidence_count / 10, 1.0)
```

**Tool reliability** — historical success rate per tool, tracked separately:

```text
browser: 0.72
filesystem: 0.85
shell: 0.63
email: 0.91
```

**Cold-start handling** — when there's not enough data, don't return false confidence:

```json
{
  "decision": "revise",
  "confidence": 0.5,
  "reason": "Not enough previous experience is available.",
  "evidence_count": 0
}
```

### Decision thresholds

```text
Confidence ≥ 0.75 → Approve
Confidence 0.45–0.74 → Revise
Confidence < 0.45 → Block
```

Thresholds should be tuned empirically against your eval set, not left arbitrary — document how you chose them.

---

## 9. Feedback Loop

After an action runs, the caller reports back what happened:

```text
PATCH /api/v1/experiences/{id}/outcome
```

```json
{
  "was_successful": false,
  "outcome": "The selected flight had one stop.",
  "failure_reason": "The action ignored the nonstop requirement."
}
```

This outcome is now part of the retrievable experience pool and affects all future evaluations. This is what makes the system genuinely improve over time — verify this with a test that shows scores changing after new outcomes are recorded.

---

## 10. Seed Data

Create 30–50 example experiences across four tool categories, with a mix of successful and unsuccessful outcomes:

- **Browser:** selecting sponsored results, submitting forms, clicking download links, comparing products, filtering search results
- **File:** deleting files, renaming files, overwriting files, reading configuration files
- **Shell:** installing packages, running tests, deleting directories, modifying environment variables
- **Email:** sending messages, replying to group threads, attaching files, using the correct recipient

Write this as `scripts/seed_database.py`, runnable with one command.

---

## 11. Testing Requirements (Target 80%+ Coverage)

**Scoring tests:**

- All similar experiences succeeded
- All similar experiences failed
- Mixed outcomes
- No previous experiences (cold start)
- Low-similarity experiences
- One highly similar failure among many old successes
- Confidence always stays between 0 and 1

**API tests:**

- Valid experience creation
- Missing required fields
- Invalid tool names
- Unknown experience IDs
- Outcome submission (including duplicate-outcome rejection)
- Evaluation response format

**Retrieval tests:**

- Correct number of results returned
- Results ordered by similarity
- Empty database
- Duplicate experiences
- Minimum similarity threshold behavior

---

## 12. Error Handling

```json
{
  "error": {
    "code": "EXPERIENCE_NOT_FOUND",
    "message": "No experience exists with ID 42."
  }
}
```

Handle: database unavailable, embedding model unavailable, empty action text, invalid outcome, duplicate outcome, no retrieval results, invalid configuration.

---

## 13. Logging & Security Basics

**Log:** request ID, endpoint, evaluation ID, confidence, decision, number of retrieved examples, processing time, errors. **Never log** API keys or private environment details (there shouldn't be any API keys in this project at all, since v1 has no external API calls).

**Security:** validate all request data, limit text lengths, reject executable code in inputs, keep any future secrets in environment variables, add CORS restrictions, avoid returning database internals, use parameterized queries (SQLAlchemy handles this), run the Docker container as a non-root user.

---

## 14. Development Order

### Phase 1 — Project setup

Python 3.12 venv → FastAPI → `/health` endpoint → Ruff + Pytest → first commit.

**Minimal starting code:**

```python
from fastapi import FastAPI

app = FastAPI(
    title="CriticLoop",
    description="Experience-based risk scoring for AI-agent actions.",
    version="0.1.0",
)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
```

**Milestone:** `GET http://localhost:8000/health` returns `{"status": "healthy"}`.

### Phase 2 — Database

SQLite → SQLAlchemy → Experience model → Pydantic schemas → CRUD endpoints → tests.

### Phase 3 — Retrieval

Sentence Transformers → generate + store embeddings → cosine similarity → top-k retrieval → tests.

### Phase 4 — Scoring

Implement each scoring component separately → combine → configurable thresholds → readable explanations → edge-case tests.

### Phase 5 — Feedback

Outcome records → update completed experiences → include outcomes in future scoring → prevent duplicate outcomes → full-cycle test.

### Phase 6 — Interface

Simple HTML form → JavaScript calling the API → display confidence/decision/similar experiences → outcome submission form.

### Phase 7 — Production preparation

Docker (single container) → environment config → structured logging → GitHub Actions → full test run → screenshots + demo video.

---

## 15. Suggested Schedule

| Week | Focus |
|---|---|
| 1 | Repo setup, FastAPI structure, database models, experience endpoints, initial tests |
| 2 | Embeddings, similarity retrieval, seed data, retrieval tests |
| 3 | Confidence scoring, decision thresholds, explanations, feedback endpoint |
| 4 | Interface, Docker, GitHub Actions, README, final testing |

Take longer if needed — understanding every part matters more than speed.

---

## 16. Definition of Done

- Public GitHub repo with clear structure and focused commit history (not one giant commit)
- Application starts with one command, $0 cost, no API keys needed
- Users can submit proposed actions and get a reproducible confidence score
- Service retrieves similar experiences via local embeddings
- Users can submit real outcomes, and those outcomes measurably affect future scores (test this explicitly)
- Automated tests pass with 80%+ coverage
- Docker runs successfully with one command
- GitHub Actions CI passes
- README explains architecture, scoring algorithm, design decisions, and limitations
- You can explain every important file without hesitation

---

## 17. README Must Include

1. Project description
2. Problem being solved
3. Architecture diagram
4. Core scoring algorithm (with the actual formula)
5. Installation instructions (should be `git clone` → `pip install` → `uvicorn app.main:app` — nothing else required)
6. API examples
7. Screenshots
8. Testing instructions
9. Design decisions (especially: why SQLite+NumPy instead of a vector DB, why no LLM in the scoring loop)
10. Limitations
11. Future improvements (link to Section 18 below)
12. Research inspiration disclosure:
    > CriticLoop is inspired by research on experience-based confidence estimation, but the application architecture, scoring system, and implementation were developed independently.

---

## 18. Future Roadmap (Not Part of v1 — Document Only)

Once v1 is working, tested, and deployed, these are legitimate next steps — but only after the core idea is proven:

- Swap SQLite + NumPy → Qdrant for scalable vector search
- Add an optional LLM-scored evaluation mode (`?mode=llm`) alongside the statistical scorer, as a direct ablation comparison (statistical vs LLM-scored: accuracy/latency tradeoff)
- Wrap a real agent (LangGraph) around the critic as a live gate instead of a manual API call
- Add PostgreSQL + Redis Streams if moving to a multi-user, real-time dashboard
- Replace the static HTML page with a Next.js dashboard showing calibration curves
- Add OpenTelemetry tracing once there's a distributed system worth tracing

---

## 19. What Not to Do

- Do not copy a tutorial project
- Do not paste generated code without understanding it
- Do not use a notebook
- Do not build several microservices for v1
- Do not make an LLM responsible for the core scoring logic
- Do not claim the system "learns" unless you can show outcomes changing later decisions with a test
- Do not claim accuracy numbers you didn't measure
- Do not add tools to the stack just to lengthen the list
- Do not wait until the end to write tests

---

**Your first task:** create the repo, build the Phase 1 minimal skeleton above, get `/health` working, commit it. Everything else follows phase by phase.
