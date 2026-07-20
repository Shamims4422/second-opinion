from fastapi.testclient import TestClient


def create_experience(client: TestClient, task: str, action: str, tool: str = "browser") -> dict:
    response = client.post(
        "/api/v1/experiences",
        json={"task": task, "proposed_action": action, "tool_name": tool},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_similar_on_empty_database_returns_empty(client: TestClient) -> None:
    response = client.get(
        "/api/v1/experiences/similar",
        params={"task": "book a flight", "action": "click search"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_similar_returns_closest_match_first(client: TestClient) -> None:
    flight = create_experience(
        client, "find cheapest nonstop flight chicago", "click first sponsored flight result"
    )
    create_experience(client, "delete temporary log files", "run remove command", tool="shell")

    response = client.get(
        "/api/v1/experiences/similar",
        params={
            "task": "find cheapest nonstop flight chicago",
            "action": "click first sponsored flight result",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["experience_id"] == flight["id"]
    assert body[0]["similarity"] > 0.9
    assert body[0]["was_successful"] is None


def test_similar_respects_limit(client: TestClient) -> None:
    for i in range(4):
        create_experience(
            client, "find cheapest nonstop flight chicago", f"click flight option number {i}"
        )
    response = client.get(
        "/api/v1/experiences/similar",
        params={
            "task": "find cheapest nonstop flight chicago",
            "action": "click a flight option",
            "limit": 2,
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_similar_excludes_unrelated_experiences(client: TestClient) -> None:
    create_experience(client, "send weekly report email", "attach spreadsheet", tool="email")
    response = client.get(
        "/api/v1/experiences/similar",
        params={"task": "compile rust kernel module", "action": "invoke cargo build"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_similar_requires_task_and_action(client: TestClient) -> None:
    response = client.get("/api/v1/experiences/similar", params={"task": "only task"})
    assert response.status_code == 422
