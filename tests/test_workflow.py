import hashlib
import io
import json
import sqlite3
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from backend.app.main import create_app
from backend.app.analysis import analyze
from backend.app.evaluation import evaluate
from backend.app.sources import search_openalex

PROTOCOL={'title':'IA universitaria','question':'Artificial intelligence tutoring in university education','inclusion':'University students\nLearning outcomes','exclusion':'Primary school pupils'}

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'db.sqlite3')) as client:
        yield client

def new_review(client):
    response=client.post('/api/reviews',json=PROTOCOL)
    assert response.status_code==201
    return response.json()['id']

def wait_job(client, job_id):
    end=time.monotonic()+12
    while time.monotonic()<end:
        result=client.get('/api/jobs/'+job_id).json()
        if result['status']!='running': return result
        time.sleep(.02)
    raise AssertionError('El trabajo no terminó')

def test_full_flow_dedup_analysis_decision_snapshot(client):
    rid=new_review(client)
    paper={'title':'AI tutoring in university education','abstract':'University students learned using artificial intelligence tutoring. Learning outcomes improved.', 'doi':'https://doi.org/10.1234/TEST','year':2024,'is_oa':True}
    assert client.post(f'/api/reviews/{rid}/articles',json=paper).json()['added']==1
    assert client.post(f'/api/reviews/{rid}/articles',json={**paper,'doi':'10.1234/test','title':'Another title'}).json()['duplicates']==1
    assert client.post(f'/api/reviews/{rid}/articles',json={**paper,'doi':''}).json()['duplicates']==1
    unrelated={'title':'Volcanic rock chemistry','abstract':'Mineral samples from a volcano reveal geological processes.'}
    client.post(f'/api/reviews/{rid}/articles',json=unrelated)
    job=client.post(f'/api/reviews/{rid}/analyze',json={'engine':'lexical'})
    assert job.status_code==202
    assert wait_job(client,job.json()['id'])['status']=='completed'
    rows=client.get(f'/api/reviews/{rid}/articles').json()
    assert rows[0]['title']==paper['title'] and rows[0]['score']>rows[1]['score']
    assert all(a['decision']=='pending' for a in rows)
    for row in rows:
        text=row['title']+'\n'+row['abstract']
        for evidence in row['analysis']['evidence']:
            assert evidence['exact_match']
            assert text[evidence['start']:evidence['end']]==evidence['quote']
    aid=rows[0]['id']
    assert client.put(f'/api/articles/{aid}/decision',json={'decision':'included','reason':'University population confirmed'}).status_code==200
    report=client.post(f'/api/reviews/{rid}/reports').json()
    original=client.get(f'/api/reports/{report["id"]}.json')
    assert hashlib.sha256(original.content).hexdigest()==report['sha256']
    assert original.json()['counts']=={'included':1,'excluded':0,'pending':1}
    readable=client.get(f'/api/reports/{report["id"]}.html')
    assert readable.status_code==200 and 'Registro de evidencia' in readable.text
    assert 'University population confirmed' in readable.text
    assert client.put(f'/api/reviews/{rid}',json={**PROTOCOL,'question':'New population'}).status_code==200
    assert client.get(f'/api/reviews/{rid}').json()['protocol_version']==2
    assert all(a['analysis'] is None for a in client.get(f'/api/reviews/{rid}/articles').json())
    assert next(a for a in client.get(f'/api/reviews/{rid}/articles').json() if a['id']==aid)['decision_version']==1
    assert client.get(f'/api/reports/{report["id"]}.json').content==original.content
    events=client.get(f'/api/reviews/{rid}/history').json()
    assert {'protocol_created','manual_import','analysis_completed','human_decision','report_created','protocol_updated'}<={e['kind'] for e in events}

def test_import_atomic_validation_and_csv_safe(client):
    rid=new_review(client)
    invalid=[{'title':'Valid'},{'title':''}]
    assert client.post(f'/api/reviews/{rid}/import',files={'file':('articles.json',json.dumps(invalid),'application/json')}).status_code==422
    assert client.get(f'/api/reviews/{rid}/articles').json()==[]
    csv='title,abstract,year,is_oa\n=FORMULA,Original abstract,2024,true\n'
    assert client.post(f'/api/reviews/{rid}/import',files={'file':('articles.csv',csv,'text/csv')}).json()['added']==1
    assert "'=FORMULA" in client.get(f'/api/reviews/{rid}/export.csv').text
    assert client.post(f'/api/reviews/{rid}/articles',json={'title':'bad link','url':'javascript:alert(1)'}).status_code==422

def test_openalex_mapping_and_search_history(client,monkeypatch):
    def fake_get(self,url,params):
        assert url=='https://api.openalex.org/works'
        assert params['filter']=='is_oa:true,from_publication_date:2020-01-01,to_publication_date:2026-12-31'
        return httpx.Response(200,json={'meta':{'count':50},'results':[{'display_name':'Paper','doi':'https://doi.org/10.123/a','abstract_inverted_index':{'University':[0],'students':[1]},'open_access':{'is_oa':True},'publication_year':2024,'authorships':[]}]})
    monkeypatch.setattr(httpx.Client,'get',fake_get)
    records,total=search_openalex('education',2020,2026,25)
    assert records[0]['abstract']=='University students' and total==50
    assert records[0]['doi']=='10.123/a'

def test_search_endpoint_records_success_and_failure(client,monkeypatch):
    from backend.app import main
    rid=new_review(client)
    monkeypatch.setattr(main,'search_openalex',lambda *args:([{'title':'Fixture paper','abstract':'University students'}],1))
    result=client.post(f'/api/reviews/{rid}/search',json={'query':'education'})
    assert result.status_code==200 and result.json()['added']==1
    assert result.json()['exhaustive'] is False
    def failing(*args): raise ValueError('Connection unavailable')
    monkeypatch.setattr(main,'search_openalex',failing)
    assert client.post(f'/api/reviews/{rid}/search',json={'query':'education'}).status_code==502
    assert len(client.get(f'/api/reviews/{rid}/articles').json())==1
    assert client.get(f'/api/reviews/{rid}/history').json()[0]['kind']=='search_failed'

def test_existing_database_migrates_without_data_loss(tmp_path):
    path=tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE reviews(id INTEGER PRIMARY KEY,title TEXT,question TEXT,inclusion TEXT,exclusion TEXT,created_at TEXT)')
        db.execute('INSERT INTO reviews VALUES (1,?,?,?,?,?)',('Old','Question','Include','Exclude','2026-01-01T00:00:00Z'))
    with TestClient(create_app(path)) as client:
        row=client.get('/api/reviews/1').json()
        assert row['title']=='Old' and row['protocol_version']==1 and row['base_text']==''

def test_pdf_text_import_and_invalid_upload(client):
    rid=new_review(client)
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 40 700 Td (Systematic review of artificial intelligence in university education.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output)
    result=client.post(f'/api/reviews/{rid}/base-pdf',files={'file':('base.pdf',output.getvalue(),'application/pdf')})
    assert result.status_code==200 and 'Systematic review' in result.json()['text']
    assert client.get(f'/api/reviews/{rid}').json()['base_filename']=='base.pdf'
    assert client.post(f'/api/reviews/{rid}/base-pdf',files={'file':('fake.pdf',b'not a pdf')}).status_code==422

def training_articles():
    # Datos sintéticos usados exclusivamente por las pruebas.
    return [{'id':i,'title':f'University learning study {i}' if i<5 else f'Volcano chemistry study {i}','abstract':'University students and learning outcomes' if i<5 else 'Volcanic minerals and chemistry samples','decision':'included' if i<5 else 'excluded'} for i in range(10)]

def test_classifier_and_holdout_use_separate_labels():
    articles=training_articles()+[{'id':11,'title':'University students using AI tutoring','abstract':'Learning outcomes for university students','decision':'pending'}]
    output=analyze({**PROTOCOL,'protocol_version':1},articles,'lexical')
    assert output[-1]['analysis']['recommendation']['training_examples']==10
    assert output[-1]['analysis']['recommendation']['validated'] is False
    result=evaluate(articles,'lexical')
    assert set(result['train_ids']).isdisjoint(result['test_ids'])
    assert result['training_count']==6 and result['test_count']==4
    assert 0<=result['f1']<=1 and sum(map(sum,result['confusion_matrix']))==4

def test_missing_semantic_model_fails_honestly(client,monkeypatch):
    from backend.app import analysis
    rid=new_review(client)
    client.post(f'/api/reviews/{rid}/articles',json={'title':'University AI study'})
    def unavailable(): raise ValueError('Modelo no descargado')
    monkeypatch.setattr(analysis,'semantic_model',unavailable)
    job=client.post(f'/api/reviews/{rid}/analyze',json={'engine':'semantic'}).json()
    result=wait_job(client,job['id'])
    assert result['status']=='failed' and result['error']=='Modelo no descargado'
    assert client.get(f'/api/reviews/{rid}/articles').json()[0]['analysis'] is None

def test_semantic_pipeline_with_injected_test_vectors(monkeypatch):
    # Verifica el circuito matemático, no la calidad del modelo preentrenado.
    import numpy as np
    from backend.app import analysis
    class TestEncoder:
        def embed(self,texts,batch_size=8):
            for text in texts:
                yield np.asarray([1.0 if 'University' in text else 0.1, 0.4, 0.2])
    monkeypatch.setattr(analysis,'semantic_model',lambda:TestEncoder())
    result=analyze({**PROTOCOL,'protocol_version':1},training_articles(),'semantic')
    assert len(result)==10 and result[0]['analysis']['engine']=='semantic'
    assert all(-1.001<=row['score']<=1.001 for row in result)
    assert all(e['exact_match'] for row in result for e in row['analysis']['evidence'])
