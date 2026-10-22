"""The publication's historical studies must never become newly found candidates."""
import io
from datetime import date

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from backend.app.main import create_app
from backend.app.published import DOI


def sample_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 40 700 Td (Artificial intelligence applications in Latin American higher education: a systematic review.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_published_base_confirmation_search_cutoff_and_snapshot(tmp_path, monkeypatch):
    database = tmp_path / 'review.sqlite3'
    with TestClient(create_app(database)) as client:
        assert client.post('/api/reviews/from-published', json={'doi': '10.1234/unknown'}).status_code == 422
        response = client.post('/api/reviews/from-published', json={'doi': f'https://doi.org/{DOI}'})
        assert response.status_code == 201
        rid = response.json()['id']
        base = client.get(f'/api/reviews/{rid}/published-base').json()
        assert len(base['studies']) == base['original_count'] == 31
        assert sum(item['count'] for item in base['application_counts']) == 31
        assert [item['original_id'] for item in base['studies']] == list(range(1, 32))
        assert client.get(f'/api/reviews/{rid}/articles').json() == []
        assert 'posterior a 2021-06-30' in client.get(f'/api/reviews/{rid}').json()['inclusion']
        assert client.post(f'/api/reviews/{rid}/search', json={'query': 'artificial intelligence'}).status_code == 422
        payload = {key: base[key] for key in ('questions', 'inclusion', 'exclusion', 'sources', 'search_strategy', 'search_date', 'last_included_date')}
        assert client.put(f'/api/reviews/{rid}/published-base', json=payload).status_code == 422
        uploaded = client.post(f'/api/reviews/{rid}/base-pdf', files={'file': ('original.pdf', sample_pdf(), 'application/pdf')})
        assert uploaded.status_code == 200 and uploaded.json()['source_match'] is True
        payload['questions'][0] += ' [confirmada]'
        confirmed = client.put(f'/api/reviews/{rid}/published-base', json=payload)
        assert confirmed.status_code == 200 and confirmed.json()['confirmed'] is True
        assert client.get(f'/api/reviews/{rid}').json()['protocol_version'] == 2

        from backend.app import main
        seen = {}
        def fake_search(query, year_from, year_to, limit, first_date, last_date):
            seen['first_date'] = first_date
            seen['last_date'] = last_date
            return [{'title': base['title'], 'doi': base['doi'], 'year': 2022}, {'title': 'New empirical study', 'abstract': 'Artificial intelligence at a university in Ecuador.', 'year': 2024}], 2
        monkeypatch.setattr(main, 'search_openalex', fake_search)
        result = client.post(f'/api/reviews/{rid}/search', json={'query': 'artificial intelligence', 'year_from': 2020, 'year_to': 2024, 'date_to': '2024-09-15', 'limit': 25})
        assert result.status_code == 200 and seen['first_date'] == date(2021, 7, 1) and seen['last_date'] == date(2024, 9, 15)
        assert result.json()['added'] == 1 and result.json()['base_skipped'] == 1 and result.json()['date_from'] == '2021-07-01' and result.json()['date_to'] == '2024-09-15'
        assert len(client.get(f'/api/reviews/{rid}/articles').json()) == 1
        assert client.post(f'/api/reviews/{rid}/articles', json={'title':base['title'],'doi':base['doi']}).json()['added'] == 0
        assert client.post(f'/api/reviews/{rid}/search',json={'query':'artificial intelligence','year_from':2021,'year_to':2100,'date_to':'2100-01-01'}).status_code==422
        report = client.post(f'/api/reviews/{rid}/reports').json()
        snapshot = client.get(f'/api/reports/{report["id"]}.json').json()
        assert snapshot['published_base']['original_count'] == 31
        assert len(snapshot['articles']) == 1
        html = client.get(f'/api/reports/{report["id"]}.html').text
        assert 'Estudio original publicado' in html and '10.1186/s41239-022-00326-w' in html
        client.post(f'/api/reviews/{rid}/base-pdf', files={'file': ('original.pdf', sample_pdf(), 'application/pdf')})
        assert client.get(f'/api/reviews/{rid}/published-base').json()['confirmed'] is False
        assert client.post(f'/api/reviews/{rid}/search', json={'query': 'artificial intelligence'}).status_code == 422
    with TestClient(create_app(database)) as client:
        assert client.get(f'/api/reviews/{rid}/published-base').json()['original_count'] == 31
