"""Synthetic fixtures verify audit behavior, not model accuracy."""

import hashlib
import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.storage import connect
from test_candidate_documents import sample_pdf


PROTOCOL = {'title': 'Review of AI', 'question': 'How is AI used?',
            'inclusion': 'Empirical university study', 'exclusion': 'Opinion'}


def seed(client, path):
    rid = client.post('/api/reviews', json=PROTOCOL).json()['id']
    client.post(f'/api/reviews/{rid}/articles', json={'title': 'Candidate <script>alert(1)</script>',
                                                  'doi': '10.1234/example'})
    aid = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
    document = client.post(f'/api/articles/{aid}/document/upload',
                          files={'file': ('candidate.pdf', sample_pdf(), 'application/pdf')}).json()
    return rid, aid, document['sha256']


def save_proposal(path, aid, sha, version=1, explanation='Human interpretation still required'):
    result = {'provider': 'groq', 'model': 'synthetic-test-model', 'protocol_version': version,
              'document_sha256': sha, 'passages_examined': 2,
              'usage': {'total_tokens': 200},
              'retrieval': {'method': 'semantic', 'model': 'synthetic-encoder'},
              'criteria': [{'criterion': 'Empirical university study', 'kind': 'inclusion',
                            'assessment': 'apoya', 'quote_verified': True, 'page': 1,
                            'quote': 'A synthetic <script>alert(2)</script> quote',
                            'explanation': explanation, 'analyzed': True,
                            'retrieval': {'method': 'semantic', 'model': 'synthetic-encoder'},
                            'selected_passages': [{'page': 1, 'text': 'Synthetic passage', 'start': 0, 'end': 17}]},
                           {'criterion': 'Opinion', 'kind': 'exclusion', 'assessment': 'incierto',
                            'quote_verified': False, 'page': None, 'quote': 'Unverified quote must stay hidden',
                            'explanation': 'Unverified explanation must stay hidden'}]}
    with connect(path) as db:
        db.execute('''INSERT INTO document_reviews
            (article_id, protocol_version, document_sha256, model, result_json)
            VALUES (?,?,?,?,?)''', (aid, version, sha, result['model'], json.dumps(result)))
    return result


def snapshot(client, rid):
    report = client.post(f'/api/reviews/{rid}/reports')
    assert report.status_code == 201, report.text
    response = client.get(f'/api/reports/{report.json()["id"]}.json')
    return report.json(), response


def test_report_freezes_pdf_proposals_and_preserves_human_pending_status(tmp_path):
    path = tmp_path / 'reports.sqlite3'
    with TestClient(create_app(path)) as client:
        rid, aid, sha = seed(client, path)
        save_proposal(path, aid, sha)
        report, response = snapshot(client, rid)
        data = response.json()
        assert data['schema_version'] == 5
        assert data['status'] == 'draft' and data['counts']['pending'] == 1
        assert data['articles'][0]['decision'] == 'pending'
        evidence = data['articles'][0]['document_evidence']
        assert evidence['document']['sha256'] == sha
        assert 'pdf' not in evidence['document'] and 'pages_json' not in evidence['document']
        assert evidence['proposal']['provider'] == 'groq'
        assert evidence['proposal']['criteria'][0]['selected_passages'][0]['page'] == 1
        assert hashlib.sha256(response.content).hexdigest() == report['sha256']
        readable = client.get(f'/api/reports/{report["id"]}.html').text
        assert 'Borrador de cribado' in readable and 'Lectura asistida de los PDF' in readable
        assert 'synthetic-encoder' in readable and 'Página 1' in readable
        assert '<script>' not in readable and '&lt;script&gt;' in readable
        assert 'Unverified quote must stay hidden' not in readable
        assert 'Unverified explanation must stay hidden' not in readable

        save_proposal(path, aid, sha, explanation='New explanation after report')
        client.put(f'/api/articles/{aid}/decision', json={'decision': 'included', 'reason': 'Human confirmed'})
        client.put(f'/api/reviews/{rid}', json={**PROTOCOL, 'inclusion': 'Changed criterion'})
        assert client.get(f'/api/reports/{report["id"]}.json').content == response.content
        assert client.get(f'/api/reports/{report["id"]}.html').text == readable


def test_report_filters_stale_pdf_and_protocol_proposals(tmp_path):
    path = tmp_path / 'reports.sqlite3'
    with TestClient(create_app(path)) as client:
        rid, aid, sha = seed(client, path)
        save_proposal(path, aid, 'obsolete-pdf')
        save_proposal(path, aid, sha, version=99)
        _, response = snapshot(client, rid)
        assert response.json()['articles'][0]['document_evidence']['proposal'] is None
        save_proposal(path, aid, sha, explanation='Current proposal')
        save_proposal(path, aid, 'obsolete-pdf', explanation='Newer but wrong PDF')
        _, response = snapshot(client, rid)
        assert response.json()['articles'][0]['document_evidence']['proposal']['criteria'][0]['explanation'] == 'Current proposal'
        client.put(f'/api/reviews/{rid}', json={**PROTOCOL, 'inclusion': 'Changed criterion'})
        _, response = snapshot(client, rid)
        assert response.json()['articles'][0]['document_evidence']['proposal'] is None


def test_older_report_without_pdf_evidence_still_renders(tmp_path):
    path = tmp_path / 'reports.sqlite3'
    with TestClient(create_app(path)) as client:
        rid, aid, sha = seed(client, path)
        report, response = snapshot(client, rid)
        legacy = response.json()
        legacy['schema_version'] = 3
        for article in legacy['articles']:
            article.pop('document_evidence', None)
        with connect(path) as db:
            db.execute('UPDATE reports SET snapshot=? WHERE id=?', (json.dumps(legacy), report['id']))
        readable = client.get(f'/api/reports/{report["id"]}.html')
        assert readable.status_code == 200
        assert 'Registro de evidencia' in readable.text and 'Lectura asistida de los PDF' not in readable.text
