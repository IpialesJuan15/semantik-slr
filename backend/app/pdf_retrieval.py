"""Local PDF retrieval with persisted vectors and explicit lexical fallback."""
import hashlib
import json
import re
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from .analysis import semantic_model, MODEL, MODEL_REVISION
from .documents import clean_pdf_text
from .storage import connect

LOCK = threading.Lock()
REFERENCE_HEADING = re.compile(r'(?im)^\s*(references|bibliography|referencias|bibliografía)\s*$')
BACK_MATTER = re.compile(r'\b(author contributions|author information|acknowledg(?:e)?ments|conflict of interest|declaration of competing interests|contribuciones de los autores|agradecimientos|financiación)\b', re.I)
MAIN_STUDY = re.compile(r'\b(this study|the present study|our study|our (?:system|model)|study sample|participants|setting and sample|research methodology|we (?:conducted|recruited|used|applied|evaluated|implemented)|investigation|este estudio|la presente investigación|la muestra|participantes|método|metodología|investigação|amostra)\b', re.I)
CITED_WORK = re.compile(r'\b(et al\.|according to|previous studies|prior studies|studies have|researchers have|según|estudios previos)\b|\([^)]*\b(?:19|20)\d{2}\b[^)]*\)', re.I)
PLACE_CRITERION = re.compile(r'am[eé]rica latina|latin america|latinoam[eé]rica|pa[ií]s|country|geogr[aá]f|regi[oó]n', re.I)
LOCATION_CUE = re.compile(r'\b(?:in|at|from|en|de|em)\s+(?:(?:a|an|the|una|un|la|el)\s+)?[A-ZÁÉÍÓÚ][\wÀ-ÿ-]+(?:\s+[A-ZÁÉÍÓÚ][\wÀ-ÿ-]+){0,4}\b')
AI_CRITERION = re.compile(r'inteligencia artificial|\bIA\b|artificial intelligence|\bAI\b|\bNLP\b|\bML\b|\bDL\b', re.I)
DIRECT_TOOL_USE = re.compile(r'\b(?:created|generated|produced|written)\s+using\s+|\b(?:chatbot|AI|artificial intelligence|NLP|ML|DL)[- ]?(?:based |powered )?(?:system|tool|software|model|application|generator)?\s*(?:was |were )?(?:used|designed|developed|implemented|applied)|textos? generados? (?:con|mediante)|(?:usamos|utilizamos|empleamos)\s+', re.I)
TOOL_USE = re.compile(r'AI[- ]written|AI[- ]generated|created using\s+[A-Za-z][\w.]*|chatbot system|AI[- ]powered|AI piece of software|artificial intelligence (?:software|tool|system)|textos? generados? (?:con|mediante) IA', re.I)
TECHNIQUE = re.compile(r'\b(?:machine learning|deep learning|natural language processing|aprendizaje automático|aprendizaje profundo|procesamiento del lenguaje natural|NLP|ML|DL)\b', re.I)
METHOD_USE = re.compile(r'\b(?:the|our) (?:model|classifier|algorithm|system|tool|application) (?:was |is |were |uses? |used |relies? |applies? |employs? )', re.I)
EMPIRICAL_CRITERION = re.compile(r'emp[ií]ric|empirical|conceptual|opiniones?\b|opinion\b', re.I)
EMPIRICAL_METHOD = re.compile(r'\b(?:quasi[- ]?experimental|experimental design|research design|study design|quantitative|qualitative|mixed methods?|methodolog(?:y|ical)|methods?|methodolog[ií]a|m[eé]todos?|dise[ñn]o|cuasiexperimental|participants?|participantes?|sample of|study sample|muestra de|data (?:were|was) collected|data collection|datos (?:fueron |se )?recopilados|encuestas?|entrevistas?|survey|interviews?|statistical analysis|an[aá]lisis estad[ií]stico)\b', re.I)
EMPIRICAL_NONSTUDY = re.compile(r'\b(?:literature review|systematic review|conceptual paper|theoretical paper|opinion piece|revisi[oó]n de literatura|revisi[oó]n sistem[aá]tica|art[ií]culo conceptual|ensayo te[oó]rico|art[ií]culo de opini[oó]n)\b', re.I)


def page_chunks(text, page, target=900, maximum=1200):
    """Keep adjacent sentences together and preserve offsets in cleaned PDF text.

    PDF extraction may remove punctuation or paragraphs. Only those unusually
    long units use a word boundary; their partial context is explicitly marked.
    """
    units = []
    start = 0
    boundaries = [m.start() for m in re.finditer(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])|\n[ \t]*\n', text)] + [len(text)]
    for boundary in boundaries:
        end = boundary
        while start < end and text[start].isspace(): start += 1
        while end > start and text[end - 1].isspace(): end -= 1
        partial_start = False
        while end - start > maximum:
            split = text.rfind(' ', start + maximum // 2, start + maximum)
            if split < 0: split = start + maximum
            units.append((start, split, partial_start, True))
            start = split
            while start < end and text[start].isspace(): start += 1
            partial_start = True
        if end > start:
            units.append((start, end, partial_start, False))
        start = boundary
    chunks = []
    index = 0
    while index < len(units):
        last = index
        while last + 1 < len(units) and units[last + 1][1] - units[index][0] <= target:
            last += 1
        start, end = units[index][0], units[last][1]
        chunks.append({'page': page, 'text': text[start:end], 'start': start, 'end': end,
                       'partial_start': units[index][2], 'partial_end': units[last][3]})
        if last == len(units) - 1:
            break
        # One sentence of overlap keeps a method and the following sample or
        # result together when the group boundary falls between them.
        index = last if last > index else last + 1
    return chunks


def retrieve_passages(pages, criteria, pdf_hash, database_path, method='semantic', limit=6):
    chunks = []
    bibliography = False
    for page in pages:
        text = clean_pdf_text(page['text'])
        heading = REFERENCE_HEADING.search(text)
        back_matter = BACK_MATTER.search(text)
        if bibliography:
            continue
        cut = min((match.start() for match in (heading, back_matter) if match), default=None)
        if cut is not None:
            text = text[:cut]
            bibliography = True
        chunks.extend(page_chunks(text, page['page']))
    if not chunks: raise ValueError('No hay texto suficiente en el PDF.')
    queries = [c['text'] for c in criteria]
    texts = [c['text'] for c in chunks]
    hit = False
    if method == 'semantic':
        key = hashlib.sha256((pdf_hash + MODEL_REVISION + json.dumps(chunks, ensure_ascii=False)).encode()).hexdigest()
        with LOCK:
            model = semantic_model()
            with connect(database_path) as db:
                db.execute('CREATE TABLE IF NOT EXISTS pdf_embedding_cache (key TEXT PRIMARY KEY, vectors TEXT NOT NULL)')
                row = db.execute('SELECT vectors FROM pdf_embedding_cache WHERE key=?', (key,)).fetchone()
                vectors = None
                if row:
                    try:
                        candidate = np.asarray(json.loads(row['vectors']), dtype=float)
                        if candidate.shape == (len(chunks), 384) and np.isfinite(candidate).all():
                            vectors = candidate
                            hit = True
                    except (ValueError, TypeError): pass
                if vectors is None:
                    vectors = normalize(np.asarray(list(model.embed(texts, batch_size=8))))
                    db.execute('INSERT OR REPLACE INTO pdf_embedding_cache VALUES (?,?)', (key, json.dumps(vectors.tolist())))
            query_vectors = normalize(np.asarray(list(model.embed(queries, batch_size=8))))
        scores = (vectors @ query_vectors.T).max(axis=1)
        name = MODEL
    elif method == 'lexical':
        vectors = TfidfVectorizer(strip_accents='unicode').fit_transform(texts + queries)
        scores = (vectors[:len(texts)] @ vectors[len(texts):].T).toarray().max(axis=1)
        name = 'TF-IDF'
    else: raise ValueError('Selecciona recuperación semántica o léxica.')
    # Ranking is advisory. Main-study signals reduce the chance that a cited
    # article is mistaken for the candidate's own sample or location.
    geography = any(PLACE_CRITERION.search(query) for query in queries)
    empirical = any(EMPIRICAL_CRITERION.search(query) for query in queries)
    compound = geography and any(AI_CRITERION.search(query) for query in queries)
    limit = max(1, min(int(limit), 12))
    adjusted = []
    for i, chunk in enumerate(chunks):
        excerpt = chunk['text']
        main = bool(MAIN_STUDY.search(excerpt))
        cited = bool(CITED_WORK.search(excerpt))
        priority = .22 if main else 0
        if chunk['page'] <= 2 and main: priority += .16
        if cited and not main: priority -= .28
        if geography and not main: priority -= .14
        if empirical and (EMPIRICAL_METHOD.search(excerpt) or EMPIRICAL_NONSTUDY.search(excerpt)):
            priority += .85
        if empirical and not (EMPIRICAL_METHOD.search(excerpt) or EMPIRICAL_NONSTUDY.search(excerpt)):
            priority -= .85
        if compound and TECHNIQUE.search(excerpt) and not cited:
            priority += .2
        adjusted.append(float(scores[i]) + priority)
    selected = []
    counts = {}
    ranked = [int(i) for i in np.argsort(-np.asarray(adjusted), kind='stable')]
    def add(i, facet=None):
        chunk = chunks[i]
        if i in used:
            if facet:
                item = next(p for p in selected if p['page'] == chunk['page'] and p['start'] == chunk['start'])
                if facet not in item['facets']: item['facets'].append(facet)
            return False
        if len(selected) >= limit or counts.get(chunk['page'], 0) >= 3:
            return False
        if method == 'lexical' and scores[i] <= 0 and not facet and not (
                empirical and (EMPIRICAL_METHOD.search(chunk['text']) or EMPIRICAL_NONSTUDY.search(chunk['text']))):
            return False
        selected.append({**chunk, 'similarity': round(float(scores[i]), 4), 'facet': facet or 'related',
                         'facets': [facet] if facet else []})
        used.add(i)
        counts[chunk['page']] = counts.get(chunk['page'], 0) + 1
        return True
    used = set()
    if compound:
        for i in ranked:
            text = chunks[i]['text']
            if MAIN_STUDY.search(text) and LOCATION_CUE.search(text):
                add(i, 'setting')
                break
        tool_candidates = [i for i in ranked if (TOOL_USE.search(chunks[i]['text']) or DIRECT_TOOL_USE.search(chunks[i]['text']))
                           and (not CITED_WORK.search(chunks[i]['text']) or MAIN_STUDY.search(chunks[i]['text']))]
        tool_candidates.sort(key=lambda i: (not bool(DIRECT_TOOL_USE.search(chunks[i]['text'])), -adjusted[i]))
        for i in tool_candidates:
            if add(i, 'ai_tool'): break
        for i in ranked:
            excerpt = chunks[i]['text']
            if TECHNIQUE.search(excerpt) and (not CITED_WORK.search(excerpt) or MAIN_STUDY.search(excerpt)):
                # This hint locates terminology, it does not certify its use in
                # the candidate study. The context is preserved for validation.
                add(i, 'technique')
                break
    if empirical:
        for i in ranked:
            excerpt = chunks[i]['text']
            if EMPIRICAL_METHOD.search(excerpt) and (not CITED_WORK.search(excerpt) or MAIN_STUDY.search(excerpt)):
                add(i, 'method')
                break
    for i in ranked:
        text = chunks[i]['text']
        if empirical and not (EMPIRICAL_METHOD.search(text) or EMPIRICAL_NONSTUDY.search(text)):
            continue
        if geography and (not MAIN_STUDY.search(text) or not LOCATION_CUE.search(text)) and not compound:
            continue
        if geography and compound and not (MAIN_STUDY.search(text) and LOCATION_CUE.search(text)
                                           or TOOL_USE.search(text) or DIRECT_TOOL_USE.search(text)
                                           or TECHNIQUE.search(text) and not CITED_WORK.search(text)):
            continue
        add(i)
        if len(selected) >= limit: break
    facets = {'setting_found': any('setting' in p['facets'] for p in selected),
              'ai_tool_found': any('ai_tool' in p['facets'] for p in selected),
              'technique_stated_in_passages': any(TECHNIQUE.search(p['text']) and
                  (MAIN_STUDY.search(p['text']) or METHOD_USE.search(p['text'])) for p in selected)} if compound else None
    return {'passages': selected, 'facets': facets, 'retrieval': {'method': method, 'model': name,
        'model_revision': MODEL_REVISION if method == 'semantic' else None,
        'chunks_indexed': len(chunks), 'selected_count': len(selected), 'cache_hit': hit, 'bibliography_excluded': bibliography}}
