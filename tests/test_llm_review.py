import json

from fastapi.testclient import TestClient

from backend.app.documents import clean_pdf_text
from backend.app.llm_review import generate_local_review
from backend.app.main import create_app
from test_candidate_documents import sample_pdf


def test_pdf_digit_glyphs_are_cleaned():
    assert clean_pdf_text('PUBLISHED /one.tnum/five.tnum May /two.tnum/zero.tnum/two.tnum/three.tnum') == 'PUBLISHED 15 May 2023'


def test_local_llm_only_exposes_quotes_found_on_the_cited_page(monkeypatch):
    from backend.app import llm_review
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'response': json.dumps({'items': [
                {'index': 0, 'assessment': 'contradice', 'page': 8,
                 'quote': 'Saudi postgraduate students at King Faisal University',
                 'explanation': 'El estudio se realizó en Arabia Saudita.'},
                {'index': 1, 'assessment': 'apoya', 'page': 8,
                 'quote': 'This nonexistent quote was invented by the model',
                 'explanation': 'Texto inventado.'}]})}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    review = {'inclusion': 'Datos de América Latina', 'exclusion': 'Sin investigación empírica', 'protocol_version': 3}
    pages = [{'page': 1, 'text': 'The title and abstract of the candidate study.'},
             {'page': 8, 'text': 'The study included Saudi postgraduate students at King Faisal University in 2023.'}]
    result = generate_local_review(review, {'title': 'Study', 'doi': '10.1234/example'}, pages, 'hash')
    assert result['criteria'][0]['quote_verified'] is True
    assert result['criteria'][0]['page'] == 8
    assert result['criteria'][1]['quote_verified'] is False
    assert result['criteria'][1]['assessment'] == 'incierto'
    assert 'Texto inventado' not in result['criteria'][1]['explanation']


def test_llm_suggestion_is_separate_from_human_decision_and_protocol_version(tmp_path, monkeypatch):
    from backend.app import main
    with TestClient(create_app(tmp_path / 'llm.sqlite3')) as client:
        review = {'title': 'Research', 'question': 'Which articles?', 'inclusion': 'Empirical study', 'exclusion': 'Opinion'}
        rid = client.post('/api/reviews', json=review).json()['id']
        client.post(f'/api/reviews/{rid}/articles', json={'title': 'Empirical AI in Ecuador', 'doi': '10.1234/example'})
        aid = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
        assert client.post(f'/api/articles/{aid}/document/llm-review').status_code == 422
        client.post(f'/api/articles/{aid}/document/upload', files={'file': ('sample.pdf', sample_pdf(), 'application/pdf')})
        def fake_review(review, article, pages, sha):
            return {'model': 'test-model', 'document_sha256': sha, 'protocol_version': review['protocol_version'],
                    'criteria': [{'criterion': 'Empirical study', 'kind': 'inclusion', 'assessment': 'incierto',
                                  'page': None, 'quote': '', 'explanation': 'Sin cita', 'quote_verified': False}],
                    'passages_examined': 1, 'warning': 'Propuesta experimental'}
        monkeypatch.setattr(main, 'generate_local_review', fake_review)
        result = client.post(f'/api/articles/{aid}/document/llm-review')
        assert result.status_code == 200 and result.json()['status'] == 'ready'
        assert client.get(f'/api/articles/{aid}/document/llm-review').json()['model'] == 'test-model'
        assert client.get(f'/api/reviews/{rid}/articles').json()[0]['decision'] == 'pending'
        review['inclusion'] = 'Empirical study in Latin America'
        assert client.put(f'/api/reviews/{rid}', json=review).status_code == 200
        assert client.get(f'/api/articles/{aid}/document/llm-review').json() == {'status': 'missing'}
