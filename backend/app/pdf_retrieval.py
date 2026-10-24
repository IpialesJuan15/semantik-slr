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
MAIN_STUDY = re.compile(r'\b(this study|the present study|our study|study sample|participants|setting and sample|research methodology|we conducted|we recruited|investigation|este estudio|la presente investigación|la muestra|participantes|método|metodología|investigação|amostra)\b', re.I)
CITED_WORK = re.compile(r'\b(et al\.|according to|previous studies|prior studies|studies have|researchers have|según|estudios previos)\b|\([^)]*\b(?:19|20)\d{2}\b[^)]*\)', re.I)
PLACE_CRITERION = re.compile(r'am[eé]rica latina|latin america|latinoam[eé]rica|pa[ií]s|country|geogr[aá]f|regi[oó]n', re.I)


def retrieve_passages(pages, criteria, pdf_hash, database_path, method='semantic', limit=6):
    chunks = []
    bibliography = False
    for page in pages:
        text = clean_pdf_text(page['text'])
        heading = REFERENCE_HEADING.search(text)
        if bibliography:
            continue
        if heading:
            text = text[:heading.start()]
            bibliography = True
        start = 0
        while start < len(text):
            end = min(start + 420, len(text))
            if end < len(text):
                boundary = text.rfind(' ', start + 200, end)
                if boundary > start: end = boundary
            if text[start:end].strip():
                chunks.append({'page': page['page'], 'text': text[start:end], 'start': start, 'end': end})
            if end == len(text): break
            start = end + 1
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
    adjusted = []
    for i, chunk in enumerate(chunks):
        excerpt = chunk['text']
        main = bool(MAIN_STUDY.search(excerpt))
        cited = bool(CITED_WORK.search(excerpt))
        priority = .22 if main else 0
        if chunk['page'] <= 2 and main: priority += .16
        if cited and not main: priority -= .28
        if geography and not main: priority -= .14
        adjusted.append(float(scores[i]) + priority)
    selected = []
    counts = {}
    for i in np.argsort(-np.asarray(adjusted), kind='stable'):
        if geography and not MAIN_STUDY.search(chunks[int(i)]['text']):
            continue
        if method == 'lexical' and scores[int(i)] <= 0:
            continue
        chunk = chunks[int(i)]
        if counts.get(chunk['page'], 0) >= 2: continue
        selected.append({**chunk, 'similarity': round(float(scores[i]), 4)})
        counts[chunk['page']] = counts.get(chunk['page'], 0) + 1
        if len(selected) >= min(limit, 3): break
    return {'passages': selected, 'retrieval': {'method': method, 'model': name,
        'model_revision': MODEL_REVISION if method == 'semantic' else None,
        'chunks_indexed': len(chunks), 'selected_count': len(selected), 'cache_hit': hit, 'bibliography_excluded': bibliography}}
