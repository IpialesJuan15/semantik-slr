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


def test_author_contributions_do_not_count_as_study_evidence(tmp_path, monkeypatch):
    class Encoder:
        def embed(self, texts, **kwargs):
            for text in texts:
                vector=np.zeros(384);vector[0]=1
                yield vector
    monkeypatch.setattr(r,'semantic_model',lambda: Encoder())
    pages=[
        {'page':1,'text':'The study sample consisted of Saudi postgraduate students at King Faisal University. '*7},
        {'page':14,'text':'Participants agreed to participate in this study. Author contributions AAl-A implemented the study. '*8},
        {'page':15,'text':'References\nA Latin American conference paper.'},
    ]
    result=r.retrieve_passages(pages,[{'text':'Datos de América Latina'}], 'pdf', tmp_path/'back.db')
    assert result['passages']
    assert all(item['page']==1 for item in result['passages'])


def test_compound_criterion_returns_setting_and_tool_separately(tmp_path, monkeypatch):
    class Encoder:
        def embed(self, texts, **kwargs):
            for text in texts:
                vector=np.zeros(384);vector[0]=1
                yield vector
    monkeypatch.setattr(r,'semantic_model',lambda: Encoder())
    pages=[
        {'page':2,'text':('This investigation involved eight TESOL students at a Costa Rican public university, ten university professors and one AI piece of software. ')*4},
        {'page':11,'text':('This study used a language elicitation process. The AI-written texts were created using copy.ai. ')*5},
        {'page':18,'text':'References\nMachine learning in Latin American higher education. '*5},
    ]
    result=r.retrieve_passages(pages,[{'text':'Datos sobre aplicaciones de IA en instituciones de educación superior de América Latina, en particular ML, DL o NLP.'}], 'compound',tmp_path/'compound.db')
    assert result['facets']=={'setting_found':True,'ai_tool_found':True,'technique_stated_in_passages':False}
    by_facet={p['facet']:p for p in result['passages']}
    assert by_facet['setting']['page']==2
    assert by_facet['ai_tool']['page']==11
    assert 'copy.ai' in by_facet['ai_tool']['text']
    assert all(p['page'] != 18 for p in result['passages'])


def test_empirical_criterion_prefers_method_over_study_dates(tmp_path):
    pages = [
        {'page': 1, 'text': 'The study was conducted from August 2022 to March 2023. '*9},
        {'page': 2, 'text': 'A quantitative quasi-experimental design involved eight students and ten professors. Data were collected using a writing assessment. '*5},
    ]
    result = r.retrieve_passages(pages, [{'text': 'Investigación primaria empírica'}],
                                 'empirical', tmp_path / 'empirical.db', 'lexical')
    assert result['passages']
    assert all(passage['page'] == 2 for passage in result['passages'])


def test_chunks_keep_complete_method_sentence_and_exact_surrounding_text():
    introduction = 'The introduction describes the background of this investigation. ' * 6
    method = ('This study used a quantitative quasi-experimental design involving eight students and ten professors, '
              'with writing assessments collected before and after the intervention.')
    text = introduction + method + ' The collected data were analyzed using descriptive statistics. ' * 12
    chunks = r.page_chunks(text, 9)
    assert any(method in item['text'] for item in chunks)
    assert len(chunks) > 1
    assert any(a['end'] > b['start'] for a, b in zip(chunks, chunks[1:]))
    for item in chunks:
        assert item['text'] == text[item['start']:item['end']]
        assert len(item['text']) <= 1200
        assert not item['partial_start'] and not item['partial_end']
        assert item['text'].endswith('.')


def test_unpunctuated_pdf_context_is_bounded_and_marks_partial_units():
    text = 'unpunctuated extracted text ' * 200
    chunks = r.page_chunks(text, 3)
    assert chunks[0]['partial_end'] is True
    assert any(item['partial_start'] for item in chunks[1:])
    assert max(len(item['text']) for item in chunks) <= 1200
    assert all(item['text'] == text[item['start']:item['end']] for item in chunks)


def test_compound_criterion_retrieves_technique_beyond_location_page(tmp_path, monkeypatch):
    class Encoder:
        def embed(self, texts, **kwargs):
            for text in texts:
                vector = np.zeros(384); vector[0] = 1
                yield vector
    monkeypatch.setattr(r, 'semantic_model', lambda: Encoder())
    pages = [
        {'page': 2, 'text': 'This investigation enrolled university students at a public university in Costa Rica.'},
        {'page': 9, 'text': 'The AI-generated writing samples were created using a generative assistant for this study.'},
        {'page': 10, 'text': 'The system used natural language processing to produce feedback for the collected writing samples.'},
        {'page': 11, 'text': 'According to Perez et al. (2022), deep learning improves image recognition.'},
        {'page': 14, 'text': 'References\nMachine learning for learning analytics in Latin America.'},
    ]
    result = r.retrieve_passages(pages, [{'text': 'Aplicaciones de IA en educación superior de América Latina con NLP.'}],
                                 'technique', tmp_path / 'technique.db', limit=6)
    assert {'setting', 'ai_tool', 'technique'} <= {facet for p in result['passages'] for facet in p['facets']}
    technique = next(p for p in result['passages'] if 'technique' in p['facets'])
    assert technique['page'] == 10
    assert result['facets']['technique_stated_in_passages'] is True
    assert not any(p['page'] in (11, 14) for p in result['passages'])


def test_requested_limit_can_return_more_than_three_relevant_pages(tmp_path):
    pages = [{'page': i, 'text': f'This study used interviews with students in sample {i}.'} for i in range(1, 8)]
    result = r.retrieve_passages(pages, [{'text': 'Investigación empírica'}], 'limit', tmp_path / 'limit.db',
                                 method='lexical', limit=5)
    assert len(result['passages']) == 5


def test_tool_instrument_is_preferred_to_comparison_with_human_writing(tmp_path):
    """A comparison result must not crowd out the tool actually used."""
    from backend.app.pdf_retrieval import retrieve_passages
    pages = [
        {'page': 2, 'text': 'This study involved university students in Ecuador and examined AI writing.'},
        {'page': 8, 'text': 'Students wrote their paragraphs independently. The AI-written texts were created using ExampleWriter. The generated paragraphs were selected for the writing assessment.'},
        {'page': 12, 'text': 'AI-generated paragraphs can easily compete with those created by humans. These results describe artificial intelligence in higher education in Latin America.'},
    ]
    result = retrieve_passages(pages, [{'kind': 'inclusion', 'text': 'Artificial intelligence in higher education in Latin America.'}], 'sample', tmp_path / 'ranking.sqlite3', method='lexical', limit=2)
    tools = [p for p in result['passages'] if 'ai_tool' in p['facets']]
    assert tools and tools[0]['page'] == 8
