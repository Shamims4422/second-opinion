from fastapi.testclient import TestClient

PROPOSED_ACTION = {
    "task": "find cheapest nonstop flight chicago",
    "proposed_action": "click first sponsored flight result",
    "tool_name": "browser",
}

FAILED_OUTCOME = {
    "was_successful": False,
    "outcome": "The selected flight had one stop.",
    "failure_reason": "The action ignored the nonstop requirement.",
}


def evaluate(client: TestClient) -> dict:
    response = client.post("/api/v1/evaluations", json=PROPOSED_ACTION)
    assert response.status_code == 201, response.text
    return response.json()


def test_submit_outcome_marks_experience_completed(client: TestClient) -> None:
    experience_id = evaluate(client)["experience_id"]
    response = client.patch(f"/api/v1/experiences/{experience_id}/outcome", json=FAILED_OUTCOME)
    assert response.status_code == 200
    body = response.json()
    assert body["experience_id"] == experience_id
    assert body["was_successful"] is False
    assert body["outcome_description"] == FAILED_OUTCOME["outcome"]
    assert body["failure_reason"] == FAILED_OUTCOME["failure_reason"]

    experience = client.get(f"/api/v1/experiences/{experience_id}").json()
    assert experience["status"] == "completed"


def test_duplicate_outcome_rejected(client: TestClient) -> None:
    experience_id = evaluate(client)["experience_id"]
    first = client.patch(f"/api/v1/experiences/{experience_id}/outcome", json=FAILED_OUTCOME)
    assert first.status_code == 200
    second = client.patch(
        f"/api/v1/experiences/{experience_id}/outcome",
        json={"was_successful": True},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_OUTCOME"


def test_outcome_for_unknown_experience(client: TestClient) -> None:
    response = client.patch("/api/v1/experiences/999/outcome", json=FAILED_OUTCOME)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXPERIENCE_NOT_FOUND"


def test_outcome_requires_was_successful(client: TestClient) -> None:
    experience_id = evaluate(client)["experience_id"]
    response = client.patch(
        f"/api/v1/experiences/{experience_id}/outcome",
        json={"outcome": "something happened"},
    )
    assert response.status_code == 422


def test_recorded_outcomes_change_future_scores(client: TestClient) -> None:
    """The core learning claim: the same proposed action scores differently
    once real outcomes exist for similar past experiences."""
    baseline = evaluate(client)
    assert baseline["decision"] == "revise"
    assert baseline["confidence"] == 0.5
    assert baseline["evidence_count"] == 0

    # Report that the action failed in reality.
    client.patch(
        f"/api/v1/experiences/{baseline['experience_id']}/outcome", json=FAILED_OUTCOME
    )

    after_failure = evaluate(client)
    assert after_failure["evidence_count"] == 1
    assert after_failure["confidence"] < baseline["confidence"]

    # Keep reporting failures; confidence should keep dropping until blocked.
    for _ in range(3):
        client.patch(
            f"/api/v1/experiences/{after_failure['experience_id']}/outcome",
            json=FAILED_OUTCOME,
        )
        after_failure = evaluate(client)

    assert after_failure["decision"] == "block"


def test_successful_outcomes_raise_future_scores(client: TestClient) -> None:
    baseline = evaluate(client)
    previous_confidence = baseline["confidence"]
    experience_id = baseline["experience_id"]

    for _ in range(6):
        client.patch(
            f"/api/v1/experiences/{experience_id}/outcome",
            json={"was_successful": True, "outcome": "Found the nonstop flight."},
        )
        result = evaluate(client)
        assert result["confidence"] >= previous_confidence
        previous_confidence = result["confidence"]
        experience_id = result["experience_id"]

    assert result["decision"] == "approve"
