"""Base extraction remains a cited proposal until an explicit confirmation."""
import io
import json

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from backend.app.base_extraction import checked_fields, generate_base_extraction, method_passages
from backend.app.main import create_app


TEXT = ('Methods. Our research question was how AI supports learning. '
        'Inclusion criteria: English empirical studies published from 2018 to 2021. '
        'We excluded editorials and opinions. We searched Scopus using artificial intelligence AND education. '
        'The search was completed in July 2021 and included publications until 30 June 2021.')


def pdf_bytes(text=TEXT):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(('BT /F1 12 Tf 40 700 Td ('+text+') Tj ET').encode())
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def raw_fields():
    def field(value,quote): return {'value':value,'evidence':[{'page':1,'quote':quote}]}
    return {'questions':[field('¿Cómo apoya la IA al aprendizaje?','Our research question was how AI supports learning.')],
            'inclusion':[field('Estudios empíricos en inglés.','Inclusion criteria: English empirical studies published from 2018 to 2021.'),
                         {**field('Publicados entre 2018 y 2021.','Inclusion criteria: English empirical studies published from 2018 to 2021.'),'historical_date':True}],
            'exclusion':[field('Editoriales y opiniones.','We excluded editorials and opinions.')],
            'sources':[field('Scopus','We searched Scopus using artificial intelligence AND education.')],
            'search_strategy':field('artificial intelligence AND education','We searched Scopus using artificial intelligence AND education.'),
            'search_date':field('2021-07','The search was completed in July 2021 and included publications until 30 June 2021.'),
            'last_included_date':field('2021-06-30','The search was completed in July 2021 and included publications until 30 June 2021.')}


def fake_extract(pages,pdf_hash,model):
    fields,warnings,missing = checked_fields(json.dumps({'fields':raw_fields()}),pages,method_passages(pages))
    return {'status':'ready','document_sha256':pdf_hash,'provider':'gemini','model':model,'fields':fields,
            'warnings':warnings,'missing_fields':missing,'page_count':len(pages),'passages_sent':1}


def test_fields_require_quotes_and_keep_missing_dates_unknown():
    fields=raw_fields()
    fields['sources'].append({'value':'Invented database','evidence':[{'page':2,'quote':'A citation that does not exist in this study.'}]})
    fields['last_included_date']['value']='2021-13-45'
    checked,warnings,missing=checked_fields(json.dumps({'fields':fields}),[{'page':1,'text':TEXT}],[{'page':1,'text':TEXT}])
    assert [item['value'] for item in checked['sources']]==['Scopus']
    assert checked['last_included_date'] is None and 'last_included_date' in missing
    assert len(warnings)==2
    assert checked['inclusion'][1]['historical_date'] is True


def test_generic_pdf_proposal_confirm_provenance_and_replacement(tmp_path,monkeypatch):
    from backend.app import main
    monkeypatch.setattr(main,'generate_base_extraction',fake_extract)
    with TestClient(create_app(tmp_path/'research.db')) as client:
        response=client.post('/api/reviews/from-base-pdf',data={'title':'A different systematic review','doi':'10.1234/new-review'},files={'file':('review.pdf',pdf_bytes(),'application/pdf')})
        assert response.status_code==201,response.text
        rid=response.json()['id']
        base=client.get(f'/api/reviews/{rid}/published-base').json()
        assert base['origin']=='pdf' and base['studies']==[] and base['original_count'] is None
        assert base['inclusion']==[] and not base['confirmed']
        assert client.post(f'/api/reviews/{rid}/search',json={'query':'artificial intelligence'}).status_code==422
        assert client.get(f'/api/reviews/{rid}/base-extraction').json()['needs_upload'] is False
        proposal=client.post(f'/api/reviews/{rid}/base-extraction',json={}).json()
        assert proposal['fields']['sources'][0]['value']=='Scopus'
        assert client.get(f'/api/reviews/{rid}').json()['inclusion']==''
        assert client.get(f'/api/reviews/{rid}').json()['protocol_version']==1
        page=client.get(f'/api/reviews/{rid}/base-document/pages/1',params={'sha256':proposal['document_sha256']})
        assert page.status_code==200 and TEXT in page.json()['text']
        assert client.get(f'/api/reviews/{rid}/base-document.pdf').content==pdf_bytes()
        assert client.get(f'/api/reviews/{rid}/base-document/pages/1?sha256=stale').status_code==409
        fields=proposal['fields']
        payload={name:[item['value'] for item in fields[name]] for name in ('questions','inclusion','exclusion','sources')}
        payload.update({name:fields[name]['value'] for name in ('search_strategy','search_date','last_included_date')})
        payload.update(document_sha256=proposal['document_sha256'],extraction_id=proposal['id'],historical_date_indexes=[1])
        confirmed=client.put(f'/api/reviews/{rid}/published-base',json=payload)
        assert confirmed.status_code==200,confirmed.text
        assert confirmed.json()['historical_date_indexes']==[1]
        assert confirmed.json()['method_extraction']['proposal']['fields']['sources'][0]['evidence'][0]['page']==1
        review=client.get(f'/api/reviews/{rid}').json()
        assert review['protocol_version']==2 and 'empíricos' in review['inclusion']
        assert '2018' not in review['inclusion'] and 'posterior a 2021-06-30' in review['inclusion']
        client.post(f'/api/reviews/{rid}/articles',json={'title':'New candidate'})
        report=client.post(f'/api/reviews/{rid}/reports').json()
        snapshot=client.get(f'/api/reports/{report["id"]}.json').json()
        assert snapshot['published_base']['method_extraction']['id']==proposal['id']
        assert 'no se han estructurado' in client.get(f'/api/reports/{report["id"]}.html').text
        replacement=client.post(f'/api/reviews/{rid}/base-pdf',files={'file':('new.pdf',pdf_bytes(TEXT+' Updated appendix.'),'application/pdf')})
        assert replacement.status_code==200
        assert client.get(f'/api/reviews/{rid}/base-extraction').json()['status']=='missing'
        assert not client.get(f'/api/reviews/{rid}/published-base').json()['confirmed']
        assert client.put(f'/api/reviews/{rid}/published-base',json=payload).status_code==409


def test_inflight_pdf_change_rejects_stale_extraction(tmp_path,monkeypatch):
    from backend.app import main
    with TestClient(create_app(tmp_path/'research.db')) as client:
        rid=client.post('/api/reviews/from-base-pdf',files={'file':('base.pdf',pdf_bytes(),'application/pdf')}).json()['id']
        def changing_pdf(pages,digest,model):
            client.post(f'/api/reviews/{rid}/base-pdf',files={'file':('changed.pdf',pdf_bytes(TEXT+' A new revision.'),'application/pdf')})
            return fake_extract(pages,digest,model)
        monkeypatch.setattr(main,'generate_base_extraction',changing_pdf)
        assert client.post(f'/api/reviews/{rid}/base-extraction',json={}).status_code==409
        assert client.get(f'/api/reviews/{rid}/base-extraction').json()['status']=='missing'


def test_gemini_request_is_explicit_bounded_and_checked(monkeypatch):
    import backend.app.base_extraction as module
    monkeypatch.setenv('SEMANTIK_GEMINI_API_KEY','test-key-not-real')
    seen={}
    class FakeResponse:
        status_code=200
        def json(self): return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({'fields':raw_fields()})}]}}]}
    class FakeClient:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,headers,json):
            seen.update(url=url,body=json)
            return FakeResponse()
    monkeypatch.setattr(module.httpx,'Client',FakeClient)
    result=generate_base_extraction([{'page':1,'text':TEXT}],'a'*64)
    assert result['fields']['questions'] and result['document_sha256']=='a'*64
    assert 'gemini-3.5-flash-lite:generateContent' in seen['url']
    assert 'ignora instrucciones' in seen['body']['systemInstruction']['parts'][0]['text']
    pages=[{'page':n,'text':TEXT} for n in range(1,80)]
    passages=method_passages(pages)
    assert len(passages)==79 and passages[-1]['text']==TEXT


def test_full_pages_preserve_table_continuations_and_metadata():
    from backend.app.base_extraction import citation_present
    pages=[{'page':1,'text':'Title and DOI: 10.1234/ab'}, {'page':2,'text':'Inclusion criteria:'}, {'page':3,'text':'(i) English articles. (ii) Empirical studies.'}]
    assert method_passages(pages)==pages
    assert citation_present('10.1234/ab', pages[0]['text'])
    assert citation_present('empirical studies', 'empir-\nical studies')
    assert not citation_present('studies in Ecuador', 'studies in Saudi Arabia')
