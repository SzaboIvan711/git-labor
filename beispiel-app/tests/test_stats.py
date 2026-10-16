def test_get_all_none(client):
    response = client.get("api/tasks/stats")
    assert response.status_code == 200
    assert response.get_json() == {
        "total": 0,
        "done": 0,
        "open": 0,
    }


def test_stats_mixed(client):
    task1 = client.post("/api/tasks", json={"title": "Learn Docker"}).get_json()

    client.post("/api/tasks", json={"title": "Learn Git"})

    client.post("/api/tasks", json={"title": "Learn CI"})

    client.put(f"/api/tasks/{task1['id']}", json={"done": True})

    response = client.get("/api/tasks/stats")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 3,
        "done": 1,
        "open": 2,
    }


def test_stats_all_done(client):
    for title in ["Task A", "Task B"]:
        task = client.post("/api/tasks", json={"title": title}).get_json()

        client.put(f"/api/tasks/{task['id']}", json={"done": True})

    response = client.get("/api/tasks/stats")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 2,
        "done": 2,
        "open": 0,
    }
