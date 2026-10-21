import sqlite3

from fastapi.testclient import TestClient

from backend.app.main import create_app


def protocol(**overrides):
    return {"title": "IA en educación superior", "question": "¿Cómo apoya la IA el aprendizaje?", "inclusion": "Estudiantes universitarios\nInvestigación empírica", "exclusion": "Educación escolar", **overrides}


def test_create_read_and_persist_after_restart(tmp_path):
    database = tmp_path / "reviews.sqlite3"
    with TestClient(create_app(database)) as client:
        assert client.get("/api/reviews").json() == []
        response = client.post("/api/reviews", json=protocol())
        assert response.status_code == 201
        review_id = response.json()["id"]
        assert "Investigación empírica" in client.get(f"/api/reviews/{review_id}").json()["inclusion"]
    with TestClient(create_app(database)) as client:
        assert client.get("/api/reviews").json()[0]["title"] == "IA en educación superior"
        assert "Educación escolar" in client.get(f"/api/reviews/{review_id}").json()["exclusion"]
        assert client.get("/health").json() == {"status": "ok"}


def test_invalid_input_preserves_values_and_does_not_save(tmp_path):
    database = tmp_path / "reviews.sqlite3"
    with TestClient(create_app(database)) as client:
        for changes in ({"title": "   "}, {"question": ""}, {"inclusion": ""}, {"exclusion": ""}, {"title": "a" * 201}):
            response = client.post("/api/reviews", json=protocol(**changes))
            assert response.status_code == 422
        assert client.get("/api/reviews").json() == []
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_user_content_is_returned_as_data_and_unknown_review_returns_404(tmp_path):
    with TestClient(create_app(tmp_path / "reviews.sqlite3")) as client:
        payload = '<script>alert("x")</script>'
        response = client.post("/api/reviews", json=protocol(title=payload))
        assert response.status_code == 201
        assert response.json()["title"] == payload
        assert client.get("/api/reviews").json()[0]["title"] == payload
        assert client.get("/api/reviews/99999").status_code == 404
