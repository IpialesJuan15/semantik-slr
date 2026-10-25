"""Extraction is human-confirmed, page-checked and frozen in reports."""
from fastapi.testclient import TestClient
from backend.app.main import create_app
from test_candidate_documents import sample_pdf


def test_extraction_requires_current_inclusion_and_exact_quote_and_freezes_report(tmp_path):
    with TestClient(create_app(tmp_path/'extraction.sqlite3')) as client:
        review={'title':'AI review','question':'How is AI used?','inclusion':'Empirical study','exclusion':'Opinion'}
        rid=client.post('/api/reviews',json=review).json()['id']
        client.post(f'/api/reviews/{rid}/articles',json={'title':'University AI study','doi':'10.1234/ai'})
        aid=client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
        client.post(f'/api/articles/{aid}/document/upload',files={'file':('study.pdf',sample_pdf(),'application/pdf')})
        fact={'country':{'value':'Ecuador','page':1,'quote':'Empirical artificial intelligence study at a university in Ecuador with sixty participants.'}}
        url=f'/api/articles/{aid}/extraction'
        assert client.put(url,json={'facts':fact}).status_code==422
        client.put(f'/api/articles/{aid}/decision',json={'decision':'included','reason':'Empirical study in Ecuador'})
        bad={'country':{**fact['country'],'quote':'Invented quote about a different country'}}
        assert client.put(url,json={'facts':bad}).status_code==422
        saved=client.put(url,json={'facts':fact})
        assert saved.status_code==200 and saved.json()['facts']['country']['verified'] is True
        assert client.get(url).json()['facts']['country']['page']==1
        report=client.post(f'/api/reviews/{rid}/reports').json()['id']
        snapshot=client.get(f'/api/reports/{report}.json').json()
        assert snapshot['articles'][0]['extraction']['facts']['country']['value']=='Ecuador'
        assert 'Ficha confirmada por el investigador' in client.get(f'/api/reports/{report}.html').text
        new={'country':{**fact['country'],'value':'Country updated'}}
        assert client.put(url,json={'facts':new}).status_code==200
        assert client.get(f'/api/reports/{report}.json').json()==snapshot
        client.put(f'/api/reviews/{rid}',json={**review,'inclusion':'Changed inclusion'})
        assert client.get(url).json()['facts']=={}


def test_extraction_rejects_unknown_field_and_missing_pdf(tmp_path):
    with TestClient(create_app(tmp_path/'extraction.sqlite3')) as client:
        rid=client.post('/api/reviews',json={'title':'R','question':'Q','inclusion':'I','exclusion':'E'}).json()['id']
        client.post(f'/api/reviews/{rid}/articles',json={'title':'Candidate'})
        aid=client.get(f'/api/reviews/{rid}/articles').json()[0]['id']
        client.put(f'/api/articles/{aid}/decision',json={'decision':'included','reason':'Confirmed source'})
        assert client.put(f'/api/articles/{aid}/extraction',json={'facts':{'country':{'value':'X','page':1,'quote':'A sufficiently long quotation from the study'}}}).status_code==422
        client.post(f'/api/articles/{aid}/document/upload',files={'file':('study.pdf',sample_pdf(),'application/pdf')})
        assert client.put(f'/api/articles/{aid}/extraction',json={'facts':{'unknown':{'value':'X','page':1,'quote':'Empirical artificial intelligence study at a university in Ecuador with sixty participants.'}}}).status_code==422
