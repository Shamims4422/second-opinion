from fastapi.testclient import TestClient

VALID_EXPERIENCE = {
    "task": "Find the cheapest nonstop flight to Chicago",
    "proposed_action": "Click the first sponsored result",
    "tool_name": "browser",
    "environment_context": "Search result page",
}


def create_experience(client: TestClient, **overrides: object) -> dict:
    payload = {**VALID_EXPERIENCE, **overrides}
    response = client.post("/api/v1/experiences", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_experience_returns_created_record(client: TestClient) -> None:
    body = create_experience(client)
    assert body["id"] == 1
    assert body["task"] == VALID_EXPERIENCE["task"]
    assert body["proposed_action"] == VALID_EXPERIENCE["proposed_action"]
    assert body["tool_name"] == "browser"
    assert body["environment_context"] == "Search result page"
    assert body["status"] == "proposed"
    assert "created_at" in body


def test_create_experience_without_context(client: TestClient) -> None:
    body = create_experience(client, environment_context=None)
    assert body["environment_context"] is None


def test_create_experience_missing_required_fields(client: TestClient) -> None:
    response = client.post("/api/v1/experiences", json={"task": "only a task"})
    assert response.status_code == 422


def test_create_experience_invalid_tool_name(client: TestClient) -> None:
    response = client.post(
        "/api/v1/experiences", json={**VALID_EXPERIENCE, "tool_name": "quantum_computer"}
    )
    assert response.status_code == 422


def test_create_experience_blank_task_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/experiences", json={**VALID_EXPERIENCE, "task": "   "})
    assert response.status_code == 422


def test_create_experience_oversized_text_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/experiences", json={**VALID_EXPERIENCE, "task": "x" * 2001})
    assert response.status_code == 422


def test_get_experience_by_id(client: TestClient) -> None:
    created = create_experience(client)
    response = client.get(f"/api/v1/experiences/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_experience_returns_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/experiences/42")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "EXPERIENCE_NOT_FOUND",
            "message": "No experience exists with ID 42.",
        }
    }


def test_list_experiences(client: TestClient) -> None:
    create_experience(client)
    create_experience(client, task="Install project dependencies", tool_name="shell")
    response = client.get("/api/v1/experiences")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    ids = {item["id"] for item in body}
    assert ids == {1, 2}


def test_list_experiences_respects_limit(client: TestClient) -> None:
    for i in range(3):
        create_experience(client, task=f"Task number {i}")
    response = client.get("/api/v1/experiences", params={"limit": 2})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_experience(client: TestClient) -> None:
    created = create_experience(client)
    response = client.delete(f"/api/v1/experiences/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/experiences/{created['id']}").status_code == 404


def test_delete_unknown_experience(client: TestClient) -> None:
    response = client.delete("/api/v1/experiences/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXPERIENCE_NOT_FOUND"
