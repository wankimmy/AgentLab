def test_list_guides_at_least_five(auth_client):
    response = auth_client.get("/api/v1/guides")
    assert response.status_code == 200
    guides = response.json()
    assert len(guides) >= 5


def test_get_guide_by_slug(auth_client):
    response = auth_client.get("/api/v1/guides/what-is-an-agent")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "what-is-an-agent"
    assert len(data["sections"]) >= 1
