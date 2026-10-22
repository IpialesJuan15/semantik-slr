import httpx
from datetime import date
from fastapi.testclient import TestClient
from urllib.parse import unquote

from backend.app.main import create_app
from backend.app.sources import SourceLimitError, search_doaj, search_openalex


def test_doaj_maps_oa_articles_and_year_filter(monkeypatch):
    def fake_get(self, url, params):
        assert unquote(url) == 'https://doaj.org/api/search/articles/(artificial intelligence) AND bibjson.year:[2021 TO 2024]'
        assert params == {'page': 1, 'pageSize': 25}
        return httpx.Response(200, json={'total': 120, 'results': [
            {'bibjson': {'title': 'AI in Latin American universities', 'year': '2024', 'abstract': 'Empirical university study', 'identifier': [{'type': 'doi', 'id': 'https://doi.org/10.1234/ABC'}], 'author': [{'name': 'A. Author'}], 'link': [{'type': 'fulltext', 'url': 'https://example.org/paper'}]}},
            {'bibjson': {'title': 'Old paper', 'year': '2019'}},
            {'bibjson': {'title': 'Year-only paper', 'year': '2021'}},
            {'bibjson': {'title': 'Early 2021 paper', 'year': '2021', 'month': 'March'}},
            {'bibjson': {'title': 'Late 2024 paper', 'year': '2024', 'month': 'December'}},
            {'bibjson': {'title': 'Boundary 2024 paper', 'year': '2024', 'month': 'September'}},
            {'bibjson': {'title': 'Future 2026 paper', 'year': '2026'}},
        ]})
    monkeypatch.setattr(httpx.Client, 'get', fake_get)
    records, total = search_doaj('artificial intelligence', 2021, 2024, 25, date(2021, 7, 1), date(2024, 9, 15))
    assert total == 120 and len(records) == 3
    assert records[0]['doi'] == '10.1234/abc'
    assert records[0]['source'] == 'DOAJ' and records[0]['is_oa'] is True
    assert records[1]['year'] == 2021 and records[1]['date_uncertain'] is True
    assert records[2]['title'] == 'Boundary 2024 paper' and records[2]['date_uncertain'] is True


def test_openalex_limit_is_explained_and_no_articles_are_saved(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENALEX_API_KEY', raising=False)
    def fake_get(self, url, params):
        return httpx.Response(429, headers={'X-RateLimit-Reset': '3600'})
    with monkeypatch.context() as isolated:
        isolated.setattr(httpx.Client, 'get', fake_get)
        try:
            search_openalex('university education', 2021, 2026, 25)
            assert False, 'Expected the rate limit'
        except SourceLimitError as error:
            assert error.retry_after == 3600
            assert 'cuota diaria' in str(error) and 'DOAJ' in str(error)

    from backend.app import main
    monkeypatch.setattr(main, 'search_openalex', lambda *args: (_ for _ in ()).throw(SourceLimitError('OpenAlex: espera o usa DOAJ', 60)))
    with TestClient(create_app(tmp_path / 'source.sqlite3')) as client:
        rid = client.post('/api/reviews', json={'title': 'Review', 'question': 'University AI?', 'inclusion': 'University students', 'exclusion': 'Schools'}).json()['id']
        response = client.post(f'/api/reviews/{rid}/search', json={'source': 'openalex', 'query': 'university education'})
        assert response.status_code == 429 and response.headers['retry-after'] == '60'
        assert client.get(f'/api/reviews/{rid}/articles').json() == []
        assert client.get(f'/api/reviews/{rid}/history').json()[0]['payload']['reason'] == 'rate_limit'


def test_doaj_is_selectable_and_source_is_recorded(tmp_path, monkeypatch):
    from backend.app import main
    monkeypatch.setattr(main, 'search_doaj', lambda *args: ([{'title': 'Real candidate', 'year': 2024, 'source': 'DOAJ', 'is_oa': True}], 1))
    with TestClient(create_app(tmp_path / 'doaj.sqlite3')) as client:
        rid = client.post('/api/reviews', json={'title': 'Review', 'question': 'University AI?', 'inclusion': 'University students', 'exclusion': 'Schools'}).json()['id']
        response = client.post(f'/api/reviews/{rid}/search', json={'source': 'doaj', 'query': 'university education'})
        assert response.status_code == 200 and response.json()['source'] == 'DOAJ'
        assert client.get(f'/api/reviews/{rid}/articles').json()[0]['source'] == 'DOAJ'
        assert client.get(f'/api/reviews/{rid}/history').json()[0]['payload']['source'] == 'DOAJ'
