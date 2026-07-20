from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Outcome

EVALUATION_REQUEST = {
    "task": "find cheapest nonstop flight chicago",
    "proposed_action": "click first sponsored flight result",
    "tool_name": "browser",
}


def create_experience(client: TestClient, task: str, action: str, tool: str = "browser") -> dict:
    response = client.post(
        "/api/v1/experiences",
        json={"task": task, "proposed_action": action, "tool_name": tool},
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_outcome(db_session: Session, experience_id: int, was_successful: bool) -> None:
    db_session.add(Outcome(experience_id=experience_id, was_successful=was_successful))
    db_session.commit()


def seed_similar_experiences(
    client: TestClient, db_session: Session, successes: int, failures: int
) -> None:
    for i in range(successes + failures):
        created = create_experience(
            client,
            EVALUATION_REQUEST["task"],
            f"click sponsored flight result number {i}",
        )
        add_outcome(db_session, created["id"], was_successful=i < successes)


def test_cold_start_evaluation(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "revise"
    assert body["confidence"] == 0.5
    assert body["evidence_count"] == 0
    assert body["reason"] == "Not enough previous experience is available."
    assert body["similar_experiences"] == []
    assert body["scoring_version"] == "v1"


def test_evaluation_response_format(client: TestClient, db_session: Session) -> None:
    seed_similar_experiences(client, db_session, successes=2, failures=1)
    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "evaluation_id",
        "experience_id",
        "decision",
        "confidence",
        "reason",
        "evidence_count",
        "similar_experiences",
        "scoring_version",
    }
    assert body["evidence_count"] == 3
    assert len(body["similar_experiences"]) == 3
    first = body["similar_experiences"][0]
    assert set(first) == {"experience_id", "similarity", "was_successful"}


def test_successful_history_raises_confidence(client: TestClient, db_session: Session) -> None:
    seed_similar_experiences(client, db_session, successes=5, failures=0)
    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    body = response.json()
    assert body["decision"] == "approve"
    assert body["confidence"] > 0.75


def test_failed_history_lowers_confidence(client: TestClient, db_session: Session) -> None:
    seed_similar_experiences(client, db_session, successes=0, failures=5)
    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    body = response.json()
    assert body["decision"] == "block"
    assert body["confidence"] < 0.45


def test_experiences_without_outcomes_are_not_evidence(
    client: TestClient, db_session: Session
) -> None:
    with_outcome = create_experience(
        client, EVALUATION_REQUEST["task"], "click sponsored flight result variant"
    )
    add_outcome(db_session, with_outcome["id"], was_successful=True)
    create_experience(client, EVALUATION_REQUEST["task"], "click sponsored flight result again")

    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    body = response.json()
    assert body["evidence_count"] == 1
    assert len(body["similar_experiences"]) == 2
    successes = [s["was_successful"] for s in body["similar_experiences"]]
    assert successes.count(None) == 1


def test_evaluation_records_experience_with_decision_status(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    experience_id = response.json()["experience_id"]
    experience = client.get(f"/api/v1/experiences/{experience_id}").json()
    assert experience["status"] == "revised"


def test_evaluation_missing_fields_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations", json={"task": "incomplete"})
    assert response.status_code == 422


def test_evaluation_history(client: TestClient) -> None:
    client.post("/api/v1/evaluations", json=EVALUATION_REQUEST)
    client.post("/api/v1/evaluations", json={**EVALUATION_REQUEST, "tool_name": "shell"})
    response = client.get("/api/v1/evaluations")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {"id", "experience_id", "confidence", "decision", "evidence_count"} <= set(body[0])
