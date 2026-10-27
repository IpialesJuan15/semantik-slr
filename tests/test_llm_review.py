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
        monkeypatch.setattr(main, 'generate_gemini_review', lambda review, article, pages, sha:
                            {**fake_review(review, article, pages, sha), 'provider': 'gemini', 'model': 'fake-gemini'})
        gemini = client.post(f'/api/articles/{aid}/document/llm-review', json={'provider': 'gemini'})
        assert gemini.status_code == 200 and gemini.json()['provider'] == 'gemini'
        assert client.get(f'/api/articles/{aid}/document/llm-review').json()['model'] == 'fake-gemini'
        assert client.post(f'/api/articles/{aid}/document/llm-review', json={'provider': 'cloud'}).status_code == 422
        review['inclusion'] = 'Empirical study in Latin America'
        assert client.put(f'/api/reviews/{rid}', json=review).status_code == 200
        assert client.get(f'/api/articles/{aid}/document/llm-review').json() == {'status': 'missing'}


def test_gemini_request_sends_selected_passages_and_checks_quotes(monkeypatch):
    from backend.app import llm_review
    monkeypatch.delenv('SEMANTIK_GEMINI_API_KEY', raising=False)
    review = {'inclusion': 'Estudio empírico en América Latina', 'exclusion': 'Fuera de América Latina', 'protocol_version': 3}
    article = {'title': 'Candidate study', 'doi': '10.1234/example'}
    pages = [{'page': 1, 'text': 'A published empirical study of Saudi postgraduate students at King Faisal University.' * 30}]
    with pytest.raises(ValueError, match='SEMANTIK_GEMINI_API_KEY'):
        llm_review.generate_gemini_review(review, article, pages, 'hash')
    monkeypatch.setenv('SEMANTIK_GEMINI_API_KEY', 'test-secret')
    captured = {}
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'items': [
                {'index': 0, 'assessment': 'contradice', 'page': 1,
                 'quote': 'Saudi postgraduate students at King Faisal University',
                 'explanation': 'El estudio está fuera de América Latina.'},
                {'index': 1, 'assessment': 'apoya', 'page': 1,
                 'quote': 'This quote is absent from the PDF text entirely',
                 'explanation': 'No debe mostrarse.'}]})}]}}],
                    'usageMetadata': {'promptTokenCount': 450, 'candidatesTokenCount': 180, 'totalTokenCount': 630}}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.update({'url': url, **kwargs})
            return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    result = llm_review.generate_gemini_review(review, article, pages, 'hash')
    assert captured['url'] == llm_review.GEMINI_URL
    assert captured['headers']['x-goog-api-key'] == 'test-secret'
    assert 'test-secret' not in captured['url']
    assert captured['json']['generationConfig']['responseMimeType'] == 'application/json'
    sent = json.loads(captured['json']['contents'][0]['parts'][0]['text'])
    assert set(sent) == {'article', 'criteria', 'pdf_passages'}
    assert sum(len(p['text']) for p in sent['pdf_passages']) <= 12 * 900
    assert result['provider'] == 'gemini' and result['model'] == llm_review.GEMINI_MODEL
    assert result['usage']['total_tokens'] == 630
    assert result['criteria'][0]['quote_verified'] is True
    assert result['criteria'][1]['quote_verified'] is False
    assert 'No debe mostrarse' not in result['criteria'][1]['explanation']


@pytest.mark.parametrize(('retry_after', 'expected'), [
    ('30', 'Espera 30 segundos'),
    ('', 'Revisa Uso y límites'),
])
def test_gemini_429_explains_limit_without_echoing_provider_message(monkeypatch, retry_after, expected):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GEMINI_API_KEY', 'test-secret')
    class FakeResponse:
        status_code = 429
        headers = {'Retry-After': retry_after}
        def json(self):
            return {'error': {'message': 'PRIVATE_PROVIDER_MESSAGE'}}
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
        llm_review.generate_gemini_review(review, article, pages, 'hash')
    assert expected in str(caught.value)
    assert 'PRIVATE_PROVIDER_MESSAGE' not in str(caught.value)
    assert 'test-secret' not in str(caught.value)


def test_gemini_rejects_truncated_answer_and_status_reports_only_presence(monkeypatch, tmp_path):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GEMINI_API_KEY', 'test-secret')
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [
                {'text': '{"items": []}'}]}}]}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    with pytest.raises(ValueError, match='no terminó'):
        llm_review.generate_gemini_review(
            {'inclusion': 'Estudio empírico', 'exclusion': '', 'protocol_version': 3},
            {'title': 'Study', 'doi': '10.1234/example'},
            [{'page': 1, 'text': 'A quantitative study enrolled 60 university students.'}], 'hash')
    with TestClient(create_app(tmp_path / 'status.sqlite3')) as client:
        status = client.get('/api/status').json()
    assert status['gemini_key_configured'] is True
    assert 'cloud_llm_configured' not in status
    assert 'test-secret' not in str(status)


def test_gemini_404_chooses_available_flash_model_without_exposing_key(monkeypatch):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GEMINI_API_KEY', 'test-secret')
    monkeypatch.delenv('SEMANTIK_GEMINI_MODEL', raising=False)
    requested = []
    class FakeResponse:
        def __init__(self, status_code, body): self.status_code, self.body = status_code, body
        def json(self): return self.body
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            requested.append(url)
            if url.endswith('/gemini-3.8-flash:generateContent'):
                return FakeResponse(404, {'error': {'message': 'PRIVATE_PROVIDER_MESSAGE'}})
            return FakeResponse(200, {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
                {'text': json.dumps({'assessment': 'incierto', 'page': None, 'quote': '', 'explanation': 'Sin prueba'})}]}}]})
        def get(self, url, **kwargs):
            assert kwargs['headers']['x-goog-api-key'] == 'test-secret'
            return FakeResponse(200, {'models': [
                {'name': 'models/gemini-3-flash-preview', 'supportedGenerationMethods': ['generateContent']},
                {'name': 'models/gemini-2.5-pro', 'supportedGenerationMethods': ['generateContent']}]})
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    result = llm_review.generate_gemini_review(
        {'inclusion': 'Estudio empírico', 'exclusion': '', 'protocol_version': 3},
        {'title': 'Study', 'doi': '10.1234/example'},
        [{'page': 1, 'text': 'This study used a quantitative design with 60 university students.'}], 'hash')
    assert requested[-1].endswith('/gemini-3-flash-preview:generateContent')
    assert result['model'] == 'gemini-3-flash-preview'
    assert 'test-secret' not in str(result)


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


@pytest.mark.parametrize('content', [
    '{"assessment":"contradice","page":8,"quote":"Saudi postgraduate students at King Faisal University","explanation":"El estudio es saudí."}',
    'assistant\n```json\n{"assessment":"contradice","page":8,"quote":"Saudi postgraduate students at King Faisal University","explanation":"El estudio es saudí."}\n```',
])
def test_groq_accepts_single_criterion_json_and_fenced_response(monkeypatch, content):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GROQ_API_KEY', 'test-groq-secret')
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}]}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    review = {'inclusion': 'Datos de América Latina', 'exclusion': 'Opinión', 'protocol_version': 3}
    pages = [{'page': 8, 'text': 'The study included Saudi postgraduate students at King Faisal University in 2023.'}]
    result = llm_review.generate_groq_review(review, {'title': 'Study', 'doi': '10.1234/example'}, pages, 'hash', 0)
    assert result['criteria'][0]['assessment'] == 'contradice'
    assert result['criteria'][0]['quote_verified'] is True


def test_groq_explains_truncated_json_without_saving(monkeypatch):
    from backend.app import llm_review
    monkeypatch.setenv('SEMANTIK_GROQ_API_KEY', 'test-groq-secret')
    class FakeResponse:
        status_code = 200
        def json(self):
            return {'choices': [{'message': {'content': '{"assessment":"contradice"'}, 'finish_reason': 'length'}]}
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(llm_review.httpx, 'Client', FakeClient)
    with pytest.raises(ValueError, match='agotó los 300 tokens'):
        llm_review.generate_groq_review(
            {'inclusion': 'Datos de América Latina', 'exclusion': '', 'protocol_version': 3},
            {'title': 'Study', 'doi': '10.1234/example'},
            [{'page': 8, 'text': 'Saudi postgraduate students at King Faisal University in 2023.'}], 'hash', 0)


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


def test_uncertain_answer_is_distinct_from_unverifiable_quote():
    from backend.app.llm_review import checked_result
    criteria=[{'kind':'inclusion','text':'Lugar y técnica de IA'}]
    pages=[{'page':2,'text':'Participants at a Costa Rican public university used AI writing software.'}]
    review={'protocol_version':3}
    uncertain=checked_result('{"assessment":"incierto","page":null,"quote":"","explanation":"Falta la técnica"}',criteria,pages,pages,review,'hash','groq','model')
    assert uncertain['criteria'][0]['evidence_status']=='model_uncertain'
    invented=checked_result('{"assessment":"apoya","page":2,"quote":"Machine learning was used in this study","explanation":"Inventado"}',criteria,pages,pages,review,'hash','groq','model')
    assert invented['criteria'][0]['evidence_status']=='quote_unverified'
    assert invented['criteria'][0]['assessment']=='incierto'
    assert 'Inventado' not in invented['criteria'][0]['explanation']


def test_empirical_claim_needs_methodological_quote_even_when_quote_exists():
    from backend.app.llm_review import checked_result
    criterion = [{'kind': 'inclusion', 'text': 'Investigación primaria empírica.'}]
    pages = [{'page': 11, 'text': 'The study was conducted from August 2022 to March 2023. '
                               'A quantitative quasi-experimental design involved eight students.'}]
    review = {'protocol_version': 3}
    weak = checked_result(json.dumps({'assessment': 'apoya', 'page': 11,
        'quote': 'The study was conducted from August 2022 to March 2023.',
        'explanation': 'Las fechas demuestran investigación empírica.'}),
        criterion, pages, pages, review, 'hash', 'groq', 'model')['criteria'][0]
    assert weak['quote_verified'] is True
    assert weak['assessment'] == 'incierto'
    assert weak['evidence_status'] == 'insufficient_support'
    assert 'Las fechas demuestran' not in weak['explanation']
    strong = checked_result(json.dumps({'assessment': 'apoya', 'page': 11,
        'quote': 'A quantitative quasi-experimental design involved eight students.',
        'explanation': 'Describe diseño y muestra.'}),
        criterion, pages, pages, review, 'hash', 'groq', 'model')['criteria'][0]
    assert strong['assessment'] == 'apoya'
    assert strong['evidence_status'] == 'verified'
