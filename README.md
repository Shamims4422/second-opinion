<img width="1198" height="411" alt="image" src="https://github.com/user-attachments/assets/a26fdf77-1208-49b9-a512-ef58103aaf45" />
# SecondOpinion

Experience-based risk scoring for AI-agent actions — fully local, $0 to run, no API keys.

An AI agent (or a person) submits a proposed action. SecondOpinion compares it against similar
past experiences using local sentence embeddings, checks which of those succeeded or failed,
and returns a transparent, statistically derived confidence score with a decision:
**approve**, **revise**, or **block**. After the action runs, the caller reports the real
outcome — and that outcome changes future scores.

See [PLAN.md](PLAN.md) for the full specification.

## The problem

AI agents fail in repetitive, predictable ways: clicking sponsored results that ignore the
user's constraints, deleting too broadly, replying-all to the wrong thread. Most agent stacks
either don't check proposed actions at all, or ask another LLM to judge them — which is slow,
costly, and opaque. SecondOpinion takes a different position: **if an action similar to this one
has failed before, that is evidence worth acting on**, and simple weighted statistics over
recorded outcomes are enough to surface it — reproducibly, in milliseconds, for free.

## Architecture

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

No external services. The only network call ever made is downloading the embedding model
(`sentence-transformers/all-MiniLM-L6-v2`, ~90 MB) once; it is cached locally afterwards.

## The scoring algorithm

No LLM anywhere in the scoring path. The confidence score is a weighted combination of four
transparent components:

```python
confidence = (
    0.45 * weighted_success_rate   # successes weighted by similarity
    + 0.25 * average_similarity    # how close the retrieved evidence is
    + 0.20 * evidence_strength     # min(evidence_count / 10, 1.0)
    + 0.10 * tool_reliability      # historical success rate of the tool
)
```

- **Weighted success rate** — `Σ(similarity × success) / Σ(similarity)`: a highly similar
  failure counts for more than a vaguely similar success.
- **Average similarity** — low-similarity evidence produces less confident scores.
- **Evidence strength** — confidence saturates at 10 pieces of evidence.
- **Tool reliability** — per-tool success rate across all recorded outcomes; a neutral 0.5
  is used for tools with no history.

Decisions: confidence ≥ 0.75 → **approve**, 0.45–0.74 → **revise**, < 0.45 → **block**.
With no evidence at all (cold start) the score is a fixed 0.5 / **revise** — the system
refuses to fake confidence it doesn't have. Thresholds are configurable via environment
variables (see `.env.example`); the defaults are starting points and should be tuned against
your own outcome data.

## Installation

Requires Python 3.12+.

```bash
git clone https://github.com/Shamims4422/second-opinion.git
cd second-opinion
python -m venv .venv
.venv\Scripts\activate          # Windows (use `source .venv/bin/activate` on macOS/Linux)
pip install -e ".[dev]"
uvicorn app.main:app
```

Then open:

- Web UI: http://localhost:8000/ui/
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Optionally load 40 example experiences first:

```bash
python scripts/seed_database.py
```

### Docker

```bash
docker build -t secondopinion .
docker run -p 8000:8000 secondopinion
```

The container runs as a non-root user and keeps its SQLite database and model cache in
`/srv/secondopinion/data`.

## API examples

Evaluate a proposed action:

```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Find the cheapest nonstop flight to Chicago",
    "proposed_action": "Click the first sponsored flight result",
    "tool_name": "browser"
  }'
```

```json
{
  "evaluation_id": 1,
  "experience_id": 41,
  "decision": "block",
  "confidence": 0.4111,
  "reason": "5 similar past action(s) were found (average similarity 0.68); 1 succeeded and 4 failed. Historically, 'browser' actions succeed 50% of the time.",
  "evidence_count": 5,
  "similar_experiences": [
    {"experience_id": 1, "similarity": 1.0, "was_successful": false},
    {"experience_id": 2, "similarity": 0.8889, "was_successful": false}
  ],
  "scoring_version": "v1"
}
```

Report what actually happened (this feeds future scores):

```bash
curl -X PATCH http://localhost:8000/api/v1/experiences/41/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "was_successful": false,
    "outcome": "The selected flight had one stop.",
    "failure_reason": "The action ignored the nonstop requirement."
  }'
```

Other endpoints: `POST/GET/DELETE /api/v1/experiences`,
`GET /api/v1/experiences/similar?task=...&action=...`, `GET /api/v1/evaluations`.
Full interactive documentation at `/docs`.

## Web UI

`/ui` serves a single static HTML/CSS/JS page: an evaluation form, the decision with a
confidence bar, the similar experiences that drove the score, and an outcome form to close
the loop. No frontend framework, no build step.

## Testing

```bash
pytest --cov=app          # 52 tests, coverage is ~97%
ruff check .              # lint
```

The test suite covers scoring edge cases (all-success, all-failure, mixed, cold start,
similarity weighting, bounds), API validation and error shapes, retrieval ordering and
thresholds, and — most importantly — **full-cycle learning tests** proving that recorded
outcomes change subsequent decisions: repeated failures drive the same action from
`revise` (0.5) to `block`, repeated successes drive it to `approve`.

Tests use a deterministic fake embedder, so they run offline and never download the model.

## Design decisions

- **SQLite + NumPy instead of a vector DB.** Embeddings are stored as JSON-serialized arrays
  in a `TEXT` column and compared in memory with NumPy cosine similarity. This is an
  intentional trade-off: zero infrastructure, fully inspectable, and fine up to a few
  thousand rows. It scans every embedding per query — Qdrant is the documented upgrade path
  when that stops being fine.
- **No LLM in the scoring loop.** The score is reproducible arithmetic you can verify by
  hand. The same inputs always produce the same output, tests can assert exact behavior, and
  an explanation string falls out of the computation for free. An LLM-scored mode is a
  planned *ablation comparison*, not a replacement.
- **The evaluated action becomes an experience.** Every evaluation records the proposed
  action, so the caller can PATCH its real outcome later — the feedback loop needs no extra
  bookkeeping on the client side.
- **Cold start returns 0.5 / revise**, never a confident-looking score derived from nothing.
- **Table creation via `Base.metadata.create_all`** at startup rather than Alembic
  migrations — appropriate for a single-user local SQLite service; migrations become worth
  their overhead when there's shared data to preserve across schema changes.

## Limitations

- Similarity retrieval loads all embeddings into memory per query — O(n) scan, fine for
  thousands of experiences, not millions.
- Scores are only as good as the recorded outcomes; sparse or biased feedback produces
  sparse or biased confidence.
- Text similarity can conflate actions that read alike but behave differently (and miss
  ones that read differently but fail alike).
- The decision thresholds ship as sensible defaults, not empirically calibrated values —
  calibrate them against your own eval set.
- Single-process, single-user by design; there is no auth.

## Future improvements

See [PLAN.md section 18](PLAN.md#18-future-roadmap--not-part-of-v1--document-only):
Qdrant for scalable vector search, an optional LLM-scored mode as an ablation, wrapping a
real agent (LangGraph) around the critic, PostgreSQL + Redis for multi-user dashboards, and
calibration-curve visualizations.

## Research inspiration

> SecondOpinion is inspired by research on experience-based confidence estimation, but the
> application architecture, scoring system, and implementation were developed independently.
