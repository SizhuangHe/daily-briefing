def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_briefing_endpoint(client):
    response = client.get("/api/v1/briefing")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "news" in data
    assert "stocks" in data
    assert "calendar" in data
    assert "inspiration" in data
