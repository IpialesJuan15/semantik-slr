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


@pytest.mark.parametrize(('code', 'retry_after', 'expected'), [
    ('insufficient_quota', '', 'Facturación y Límites'),
    ('rate_limit_exceeded', '30', 'Espera 30 segundos'),
    ('', '', 'Puede faltar cuota'),
])
def test_cloud_429_explains_known_cause_without_echoing_provider_message(monkeypatch, code, retry_after, expected):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_OPENAI_API_KEY', 'test-secret')
    class FakeResponse:
        status_code = 429
        headers = {'Retry-After': retry_after}
        def json(self):
            return {'error': {'code': code, 'message': 'PRIVATE_PROVIDER_MESSAGE'}}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    review = {'inclusion': 'Estudio empírico', 'exclusion': 'Opinión', 'protocol_version': 1}
    article = {'title': 'Candidate', 'doi': '10.1234/example'}
    pages = [{'page': 1, 'text': 'Empirical study with university students in Latin America.'}]
    with pytest.raises(ValueError) as caught:
        llm_review.generate_cloud_review(review, article, pages, 'hash')
    assert expected in str(caught.value)
    assert 'PRIVATE_PROVIDER_MESSAGE' not in str(caught.value)
    assert 'test-secret' not in str(caught.value)


def test_groq_uses_exact_model_and_free_tier_output_cap(monkeypatch):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GROQ_API_KEY', 'test-groq-secret')
    captured = {}
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': json.dumps({'items': [
                {'index': 0, 'assessment': 'contradice', 'page': 8,
                 'quote': 'Saudi postgraduate students at King Faisal University',
                 'explanation': 'El estudio no está en América Latina.'}]})}}],
                    'usage': {'prompt_tokens': 210, 'completion_tokens': 85, 'total_tokens': 295}}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.update({'url': url, **kwargs})
            return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    review = {'inclusion': 'Datos de América Latina\nEstudio empírico', 'exclusion': 'Opinión', 'protocol_version': 3}
    article = {'title': 'Study', 'doi': '10.1234/example'}
    pages = [{'page': 8, 'text': 'The study included Saudi postgraduate students at King Faisal University in 2023.'}]
    result = llm_review.generate_groq_review(review, article, pages, 'hash', 0)
    sent = captured['json']
    assert captured['url'] == llm_review.GROQ_URL
    assert sent['model'] == 'qwen/qwen3.8-27b'
    assert sent['max_completion_tokens'] == 300
    assert captured['headers']['Authorization'] == 'Bearer test-groq-secret'
    assert len(json.loads(sent['messages'][1]['content'])['criteria']) == 1
    assert result['provider'] == 'groq' and result['criterion_index'] == 0
    assert result['criteria'][0]['quote_verified'] is True
    assert result['usage']['total_tokens'] == 295


def test_groq_reviews_accumulate_per_criterion_without_changing_human_decision(tmp_path, monkeypatch):
    from backend.app import main
    with TestClient(create_app(tmp_path / 'groq.sqlite3')) as client:
        rid = client.post('/api/reviews', json={'title': 'Research', 'question': 'Which articles?',
            'inclusion': 'Estudio en América Latina\nEstudio empírico', 'exclusion': 'Opinión'}).json()['id']
        client.post(f'/api/reviews/{rid}/articles', json={'title': 'Candidate', 'doi': '10.1234/example'})
        aid = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
        client.post(f'/api/articles/{aid}/document/upload', files={'file': ('study.pdf', sample_pdf(), 'application/pdf')})
        def fake_groq(review, article, pages, sha, index):
            criterion = main.criteria_for(review)[index]
            return {'provider': 'groq', 'model': main.GROQ_MODEL, 'document_sha256': sha,
                'protocol_version': review['protocol_version'], 'passages_examined': 3,
                'criteria': [{'criterion': criterion['text'], 'kind': criterion['kind'],
                    'assessment': 'incierto', 'page': None, 'quote': '',
                    'explanation': 'Sin cita', 'quote_verified': False}],
                'usage': {'prompt_tokens': 150, 'completion_tokens': 60, 'total_tokens': 210},
                'warning': 'Propuesta experimental'}
        monkeypatch.setattr(main, 'generate_groq_review', fake_groq)
        first = client.post(f'/api/articles/{aid}/document/llm-review', json={'provider': 'groq', 'criterion_index': 0})
        assert first.status_code == 200 and first.json()['completed_criteria'] == 1
        assert first.json()['criteria'][1]['analyzed'] is False
        second = client.post(f'/api/articles/{aid}/document/llm-review', json={'provider': 'groq', 'criterion_index': 1})
        assert second.status_code == 200 and second.json()['completed_criteria'] == 2
        assert second.json()['criteria'][0]['analyzed'] is True
        assert second.json()['usage']['total_tokens'] == 420
        assert client.get(f'/api/articles/{aid}/document/llm-review').json()['completed_criteria'] == 2
        assert client.get(f'/api/reviews/{rid}/articles').json()[0]['decision'] == 'pending'


def test_groq_limit_has_actionable_message_and_keeps_provider_text_private(monkeypatch):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GROQ_API_KEY', 'test-groq-secret')
    class FakeResponse:
        status_code = 429
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    review = {'inclusion': 'Estudio empírico', 'exclusion': 'Opinión', 'protocol_version': 1}
    with pytest.raises(ValueError, match='Espera al menos un minuto') as caught:
        llm_review.generate_groq_review(review, {'title': 'Candidate', 'doi': ''},
                                         [{'page': 1, 'text': 'Empirical study with university students in Latin America.'}],
                                         'hash', 0)
    assert 'test-groq-secret' not in str(caught.value)
