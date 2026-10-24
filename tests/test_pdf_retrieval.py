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
