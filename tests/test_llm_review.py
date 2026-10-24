import json

import pytest

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
        monkeypatch.setattr(main, 'generate_cloud_review', lambda review, article, pages, sha:
                            {**fake_review(review, article, pages, sha), 'provider': 'cloud', 'model': 'fake-cloud'})
        cloud = client.post(f'/api/articles/{aid}/document/llm-review', json={'provider': 'cloud'})
        assert cloud.status_code == 200 and cloud.json()['provider'] == 'cloud'
        assert client.get(f'/api/articles/{aid}/document/llm-review').json()['model'] == 'fake-cloud'
        review['inclusion'] = 'Empirical study in Latin America'
        assert client.put(f'/api/reviews/{rid}', json=review).status_code == 200
        assert client.get(f'/api/articles/{aid}/document/llm-review').json() == {'status': 'missing'}


def test_cloud_request_sends_selected_passages_and_checks_quotes(monkeypatch):
    from backend.app import llm_review
    monkeypatch.delenv('SEMANTIK_OPENAI_API_KEY', raising=False)
    review = {'inclusion': 'Estudio empírico en América Latina', 'exclusion': 'Fuera de América Latina', 'protocol_version': 3}
    article = {'title': 'Candidate study', 'doi': '10.1234/example'}
    pages = [{'page': 1, 'text': 'A published empirical study of Saudi postgraduate students at King Faisal University.' * 30}]
    with pytest.raises(ValueError, match='SEMANTIK_OPENAI_API_KEY'):
        llm_review.generate_cloud_review(review, article, pages, 'hash')
    monkeypatch.setenv('SEMANTIK_OPENAI_API_KEY', 'test-secret')
    captured = {}
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': json.dumps({'items': [
                {'index': 0, 'assessment': 'contradice', 'page': 1,
                 'quote': 'Saudi postgraduate students at King Faisal University',
                 'explanation': 'El estudio está fuera de América Latina.'},
                {'index': 1, 'assessment': 'apoya', 'page': 1,
                 'quote': 'This quote is absent from the PDF text entirely',
                 'explanation': 'No debe mostrarse.'}]})}}],
                    'usage': {'prompt_tokens': 450, 'completion_tokens': 180, 'total_tokens': 630}}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.update({'url': url, **kwargs})
            return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    result = llm_review.generate_cloud_review(review, article, pages, 'hash')
    assert captured['url'] == llm_review.CLOUD_URL
    assert captured['headers']['Authorization'] == 'Bearer test-secret'
    sent = json.loads(captured['json']['messages'][1]['content'])
    assert set(sent) == {'article', 'criteria', 'pdf_passages'}
    assert sum(len(p['text']) for p in sent['pdf_passages']) <= 12 * 900
    assert result['provider'] == 'cloud' and result['model'] == llm_review.CLOUD_MODEL
    assert result['usage']['total_tokens'] == 630
    assert result['criteria'][0]['quote_verified'] is True
    assert result['criteria'][1]['quote_verified'] is False
    assert 'No debe mostrarse' not in result['criteria'][1]['explanation']
