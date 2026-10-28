def test_list_is_empty_initially(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_task_returns_201_and_body(client):
    response = client.post("/api/tasks", json={"title": "Write the report"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["title"] == "Write the report"
    assert body["done"] is False
    assert isinstance(body["id"], int)


def test_created_task_appears_in_list(client):
    client.post("/api/tasks", json={"title": "Buy milk"})
    titles = [t["title"] for t in client.get("/api/tasks").get_json()]
    assert titles == ["Buy milk"]


def test_title_is_trimmed(client):
    body = client.post("/api/tasks", json={"title": "  padded  "}).get_json()
    assert body["title"] == "padded"


def test_empty_title_is_rejected(client):
    response = client.post("/api/tasks", json={"title": "   "})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_missing_title_is_rejected(client):
    assert client.post("/api/tasks", json={}).status_code == 400


def test_non_string_title_is_rejected(client):
    assert client.post("/api/tasks", json={"title": 42}).status_code == 400


def test_overlong_title_is_rejected(client):
    response = client.post("/api/tasks", json={"title": "x" * 201})
    assert response.status_code == 400


def test_get_single_task(client):
    created = client.post("/api/tasks", json={"title": "Read a book"}).get_json()
    response = client.get(f"/api/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_get_unknown_task_returns_404(client):
    assert client.get("/api/tasks/999").status_code == 404


def test_mark_task_as_done(client):
    created = client.post("/api/tasks", json={"title": "Do laundry"}).get_json()
    response = client.put(f"/api/tasks/{created['id']}", json={"done": True})
    assert response.status_code == 200
    assert response.get_json()["done"] is True


def test_update_requires_boolean_done(client):
    created = client.post("/api/tasks", json={"title": "Task"}).get_json()
    response = client.put(f"/api/tasks/{created['id']}", json={"done": "yes"})
    assert response.status_code == 400


def test_update_unknown_task_returns_404(client):
    assert client.put("/api/tasks/999", json={"done": True}).status_code == 404


def test_delete_task(client):
    created = client.post("/api/tasks", json={"title": "Temporary"}).get_json()
    assert client.delete(f"/api/tasks/{created['id']}").status_code == 204
    assert client.get("/api/tasks").get_json() == []


def test_delete_unknown_task_returns_404(client):
    assert client.delete("/api/tasks/999").status_code == 404
