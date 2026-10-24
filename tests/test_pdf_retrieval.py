import numpy as np
from backend.app import pdf_retrieval as r


def test_cache_and_exact_page_fragments(tmp_path, monkeypatch):
    calls=[]
    class Encoder:
        def embed(self, texts, **kwargs):
            calls.append(list(texts))
            for text in texts:
                vector=np.zeros(384);vector[0]=1
                yield vector
    monkeypatch.setattr(r,'semantic_model',lambda: Encoder())
    pages=[{'page':2,'text':'University students participated in this empirical study. '*25}]
    args=(pages,[{'text':'University students'}],'hash',tmp_path/'cache.db')
    first=r.retrieve_passages(*args)
    second=r.retrieve_passages(*args)
    assert first['retrieval']['cache_hit'] is False
    assert second['retrieval']['cache_hit'] is True
    assert len(calls)==3
    for item in first['passages']:
        assert item['text']==pages[0]['text'][item['start']:item['end']]
        assert item['page']==2


def test_lexical_needs_no_model(tmp_path, monkeypatch):
    def fail(): raise AssertionError('Should not load model')
    monkeypatch.setattr(r,'semantic_model',fail)
    result=r.retrieve_passages([{'page':1,'text':'University students participated in experiments.'}], [{'text':'students'}],'hash',tmp_path/'cache.db','lexical')
    assert result['retrieval']['method']=='lexical'
    assert result['passages'][0]['similarity']>0


def test_geography_prefers_candidate_study_and_excludes_bibliography(tmp_path, monkeypatch):
    class Encoder:
        def embed(self, texts, **kwargs):
            for text in texts:
                vector=np.zeros(384)
                vector[0]=1
                yield vector
    monkeypatch.setattr(r,'semantic_model',lambda: Encoder())
    pages=[
        {'page':1,'text':'The study sample consisted of Saudi postgraduate students at King Faisal University. '*7},
        {'page':2,'text':'Previous studies have explored learning in different countries. '*8},
        {'page':3,'text':'References\nCalle, M. (2021). Latin American Conference on Learning Analytics in Peru. '*8},
    ]
    result=r.retrieve_passages(pages,[{'text':'Datos de aplicaciones de IA en América Latina'}], 'pdf', tmp_path/'geo.db')
    assert result['retrieval']['bibliography_excluded'] is True
    assert result['passages']
    assert all(p['page']==1 for p in result['passages'])
    assert 'Saudi postgraduate students' in result['passages'][0]['text']
