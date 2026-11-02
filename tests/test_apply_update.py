"""Tests para la integración de decisiones en la revisión base (apply-update)."""
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.published import DOI


def _client_with_base(tmp_path):
    """Devuelve un client con una revisión que tiene base publicada sin confirmar."""
    db = tmp_path / 'db.sqlite3'
    client = TestClient(create_app(db))
    client.__enter__()
    response = client.post('/api/reviews/from-published', json={'doi': f'https://doi.org/{DOI}'})
    assert response.status_code == 201
    return client, response.json()['id']


def _confirm_base(client, rid, last_included_date='2021-06-30'):
    """Sube un PDF mínimo y confirma el método de la base."""
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 40 700 Td (Artificial intelligence applications in Latin American higher education: a systematic review.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    client.post(f'/api/reviews/{rid}/base-pdf', files={'file': ('base.pdf', output.getvalue(), 'application/pdf')})
    base = client.get(f'/api/reviews/{rid}/published-base').json()
    payload = {key: base[key] for key in ('questions', 'inclusion', 'exclusion', 'sources', 'search_strategy', 'search_date', 'last_included_date')}
    payload['last_included_date'] = last_included_date
    response = client.put(f'/api/reviews/{rid}/published-base', json=payload)
    assert response.status_code == 200 and response.json()['confirmed'] is True


def test_apply_update_adds_included_studies_and_updates_cutoff(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid)

    # Agregar candidatos
    client.post(f'/api/reviews/{rid}/articles', json={'title': 'New AI study 2023', 'abstract': 'University students and AI', 'year': 2023, 'doi': '10.1234/new2023'})
    client.post(f'/api/reviews/{rid}/articles', json={'title': 'Unrelated study', 'abstract': 'Geology report', 'year': 2023})

    aid1 = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
    aid2 = client.get(f'/api/reviews/{rid}/articles').json()[1]['id']

    client.put(f'/api/articles/{aid1}/decision', json={'decision': 'included', 'reason': 'Cumple todos los criterios'})
    client.put(f'/api/articles/{aid2}/decision', json={'decision': 'excluded', 'reason': 'No es educación superior'})

    cutoff = (date.today() - timedelta(days=1)).isoformat()
    response = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': cutoff})
    assert response.status_code == 200
    result = response.json()
    assert result['cycle'] == 1
    assert result['included_count'] == 1
    assert result['excluded_count'] == 1
    assert result['cutoff_date'] == cutoff
    assert result['total_studies'] == 32  # 31 originales + 1 nuevo

    # La base ahora tiene el nuevo corte
    base = client.get(f'/api/reviews/{rid}/published-base').json()
    assert base['last_included_date'] == cutoff
    assert len(base['studies']) == 32
    assert base['update_history'][0]['cycle'] == 1

    # Los artículos del ciclo 1 ya no aparecen en current
    current = client.get(f'/api/reviews/{rid}/articles').json()
    assert current == []

    # Pero sí aparecen con cycle=1
    cycle1 = client.get(f'/api/reviews/{rid}/articles?cycle=1').json()
    assert len(cycle1) == 2

    # Y con cycle=all aparecen todos
    all_articles = client.get(f'/api/reviews/{rid}/articles?cycle=all').json()
    assert len(all_articles) == 2

    # El protocolo se actualizó con la nueva fecha de corte
    review = client.get(f'/api/reviews/{rid}').json()
    assert f'posterior a {cutoff}' in review['inclusion']


def test_apply_update_blocks_if_pending(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid)

    client.post(f'/api/reviews/{rid}/articles', json={'title': 'Pending study', 'abstract': 'AI in university', 'year': 2023})

    cutoff = (date.today() - timedelta(days=1)).isoformat()
    response = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': cutoff})
    assert response.status_code == 422
    assert 'pendiente' in response.json()['detail'].lower()


def test_apply_update_blocks_if_base_not_confirmed(tmp_path):
    client, rid = _client_with_base(tmp_path)
    # No confirmamos la base

    cutoff = (date.today() - timedelta(days=1)).isoformat()
    response = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': cutoff})
    assert response.status_code == 422


def test_apply_update_blocks_future_cutoff(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid)

    future = (date.today() + timedelta(days=10)).isoformat()
    response = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': future})
    assert response.status_code == 422


def test_apply_update_blocks_cutoff_before_previous(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid, last_included_date='2023-12-31')

    # Intentar con fecha anterior al corte actual
    response = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': '2023-06-30'})
    assert response.status_code == 422
    assert '2023-12-31' in response.json()['detail']


def test_multiple_cycles_accumulate_studies(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid)

    # Ciclo 1
    client.post(f'/api/reviews/{rid}/articles', json={'title': 'Study cycle 1', 'abstract': 'AI university', 'year': 2022})
    aid = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
    client.put(f'/api/articles/{aid}/decision', json={'decision': 'included', 'reason': 'Cumple criterios'})
    client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': '2022-12-31'})

    base = client.get(f'/api/reviews/{rid}/published-base').json()
    assert len(base['studies']) == 32
    assert base['last_included_date'] == '2022-12-31'

    # Ciclo 2
    client.post(f'/api/reviews/{rid}/articles', json={'title': 'Study cycle 2', 'abstract': 'ML higher education', 'year': 2023})
    aid2 = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
    client.put(f'/api/articles/{aid2}/decision', json={'decision': 'included', 'reason': 'Cumple criterios'})
    result = client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': '2023-12-31'}).json()

    assert result['cycle'] == 2
    assert result['total_studies'] == 33

    base = client.get(f'/api/reviews/{rid}/published-base').json()
    assert len(base['update_history']) == 2
    assert base['update_history'][1]['cycle'] == 2

    # current está vacío
    assert client.get(f'/api/reviews/{rid}/articles').json() == []

    # cycle=all muestra todos
    all_art = client.get(f'/api/reviews/{rid}/articles?cycle=all').json()
    assert len(all_art) == 2

    events = {e['kind'] for e in client.get(f'/api/reviews/{rid}/history').json()}
    assert 'update_applied' in events


def test_apply_update_event_recorded(tmp_path):
    client, rid = _client_with_base(tmp_path)
    _confirm_base(client, rid)

    client.post(f'/api/reviews/{rid}/articles', json={'title': 'A study', 'abstract': 'AI', 'year': 2022})
    aid = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
    client.put(f'/api/articles/{aid}/decision', json={'decision': 'excluded', 'reason': 'No cumple'})
    client.post(f'/api/reviews/{rid}/apply-update', json={'cutoff_date': '2022-12-31'})

    events = client.get(f'/api/reviews/{rid}/history').json()
    update_events = [e for e in events if e['kind'] == 'update_applied']
    assert len(update_events) == 1
    payload = update_events[0]['payload']
    assert payload['cycle'] == 1
    assert payload['included_count'] == 0
    assert payload['excluded_count'] == 1
