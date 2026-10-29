import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from backend.app.documents import public_https
from backend.app.main import create_app


def sample_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 40 700 Td (Empirical artificial intelligence study at a university in Ecuador with sixty participants.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_candidate_pdf_is_saved_with_page_provenance_without_changing_decision(tmp_path, monkeypatch):
    from backend.app import main
    pdf = sample_pdf()
    with TestClient(create_app(tmp_path / 'research.sqlite3')) as client:
        review = client.post('/api/reviews', json={'title': 'AI in universities', 'question': 'How is AI used?', 'inclusion': 'Empirical studies', 'exclusion': 'Opinion articles'}).json()
        rid = review['id']
        assert client.post(f'/api/reviews/{rid}/articles', json={'title': 'Empirical AI in Ecuador', 'doi': '10.1234/example', 'abstract': 'AI at a university.'}).status_code == 201
        article_id = client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
        assert client.get(f'/api/articles/{article_id}/document').json() == {'status': 'missing'}
        assert client.get(f'/api/articles/{article_id}/document/pages/1').status_code == 404
        monkeypatch.setattr(main, 'openalex_pdf_urls', lambda doi: ['https://journal.example/broken.pdf', 'https://repository.example/article.pdf'])
        attempted = []
        def fake_download(url):
            attempted.append(url)
            if 'broken' in url: raise ValueError('Enlace roto')
            return pdf, url
        monkeypatch.setattr(main, 'download_pdf', fake_download)
        result = client.post(f'/api/articles/{article_id}/document/from-openalex')
        assert result.status_code == 200, result.text
        data = result.json()
        assert data['status'] == 'read' and data['page_count'] == 1 and data['source_type'] == 'OpenAlex'
        assert len(attempted) == 2 and data['source_url'] == attempted[-1]
        assert data['page_previews'][0]['page'] == 1 and 'Ecuador' in data['page_previews'][0]['text']
        assert client.get(f'/api/articles/{article_id}/document.pdf').content == pdf
        page = client.get(f'/api/articles/{article_id}/document/pages/1',params={'sha256':data['sha256']})
        assert page.status_code == 200 and page.json()['document_sha256'] == data['sha256']
        assert 'sixty participants' in page.json()['text']
        assert client.get(f'/api/articles/{article_id}/document/pages/1?sha256=stale').status_code == 409
        assert client.get(f'/api/articles/{article_id}/document/pages/2').status_code == 404
        assert client.get(f'/api/articles/{article_id}/document/pages/0').status_code == 404
        assert client.get(f'/api/reviews/{rid}/articles').json()[0]['decision'] == 'pending'
        assert 'candidate_pdf_read' in [event['kind'] for event in client.get(f'/api/reviews/{rid}/history').json()]
        bad = client.post(f'/api/articles/{article_id}/document/upload', files={'file': ('wrong.pdf', b'not a PDF', 'application/pdf')})
        assert bad.status_code == 422
        assert client.get(f'/api/articles/{article_id}/document').json()['sha256'] == data['sha256']
        uploaded = client.post(f'/api/articles/{article_id}/document/upload', files={'file': ('study.pdf', pdf, 'application/pdf')})
        assert uploaded.status_code == 200 and uploaded.json()['source_type'] == 'Investigador'
        assert client.get(f'/api/articles/{article_id}/document').json()['source_type'] == 'Investigador'
    with TestClient(create_app(tmp_path / 'research.sqlite3')) as client:
        assert client.get(f'/api/articles/{article_id}/document').json()['page_count'] == 1


def test_pdf_fetch_rejects_private_destinations():
    assert not public_https('http://example.org/file.pdf')
    assert not public_https('https://127.0.0.1/private.pdf')
    assert not public_https('https://169.254.169.254/metadata')
    assert not public_https('https://user:password@example.org/file.pdf')
