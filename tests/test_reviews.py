import sqlite3

from fastapi.testclient import TestClient

from backend.app.main import create_app


def protocol(**overrides):
    return {"title": "IA en educación superior", "question": "¿Cómo apoya la IA el aprendizaje?", "inclusion": "Estudiantes universitarios\nInvestigación empírica", "exclusion": "Educación escolar", **overrides}


def test_create_read_and_persist_after_restart(tmp_path):
    database = tmp_path / "reviews.sqlite3"
    with TestClient(create_app(database)) as client:
        assert "Tu primera revisión empieza aquí" in client.get("/").text
        response = client.post("/reviews", data=protocol(), follow_redirects=False)
        assert response.status_code == 303
        detail_url = response.headers["location"]
        assert "Investigación empírica" in client.get(detail_url).text
    with TestClient(create_app(database)) as client:
        assert "IA en educación superior" in client.get("/").text
        assert "Educación escolar" in client.get(detail_url).text
        assert client.get("/health").json() == {"status": "ok"}


def test_invalid_input_preserves_values_and_does_not_save(tmp_path):
    database = tmp_path / "reviews.sqlite3"
    with TestClient(create_app(database)) as client:
        for changes in ({"title": "   "}, {"question": ""}, {"inclusion": ""}, {"exclusion": ""}, {"title": "a" * 201}):
            response = client.post("/reviews", data=protocol(**changes))
            assert response.status_code == 422
            assert 'role="alert"' in response.text
        assert "IA en educación superior" in client.post("/reviews", data=protocol(question="")).text
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_user_content_is_escaped_and_unknown_review_returns_404(tmp_path):
    with TestClient(create_app(tmp_path / "reviews.sqlite3")) as client:
        payload = '<script>alert("x")</script>'
        response = client.post("/reviews", data=protocol(title=payload))
        assert response.status_code == 200
        assert payload not in response.text
        assert "&lt;script&gt;" in response.text
        assert payload not in client.get("/").text
        assert client.get("/reviews/99999").status_code == 404
