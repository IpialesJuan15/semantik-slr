"""Local PDF retrieval with persisted vectors and explicit lexical fallback."""
import hashlib
import json
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from .analysis import semantic_model, MODEL, MODEL_REVISION
from .documents import clean_pdf_text
from .storage import connect

LOCK = threading.Lock()

def retrieve_passages(pages, criteria, pdf_hash, database_path, method='semantic', limit=6):
    chunks = []
    for page in pages:
        text = clean_pdf_text(page['text'])
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
    selected = []
    counts = {}
    for i in np.argsort(-scores, kind='stable'):
        chunk = chunks[int(i)]
        if counts.get(chunk['page'], 0) >= 2: continue
        selected.append({**chunk, 'similarity': round(float(scores[i]), 4)})
        counts[chunk['page']] = counts.get(chunk['page'], 0) + 1
        if len(selected) >= limit: break
    return {'passages': selected, 'retrieval': {'method': method, 'model': name,
        'model_revision': MODEL_REVISION if method == 'semantic' else None,
        'chunks_indexed': len(chunks), 'selected_count': len(selected), 'cache_hit': hit}}
