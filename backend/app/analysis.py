import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import normalize

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_REPOSITORY = 'Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q'
MODEL_REVISION = 'faf4aa4225822f3bc6376869cb1164e8e3feedd0'
CACHE = Path(__file__).resolve().parents[2] / '.local/models'
MODEL_PATH = CACHE / 'models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q' / 'snapshots' / MODEL_REVISION
os.environ.setdefault('HF_HOME', str(CACHE / 'huggingface'))
os.environ.setdefault('HF_XET_CACHE', str(CACHE / 'xet'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')


def verify_model():
    expected = {
        'model_optimized.onnx': '634d0f66c29dc934c8fa72b8a4fe91dd4d420a22f1d82a241058d4316e659a99',
        'tokenizer.json': 'fa685fc160bbdbab64058d4fc91b60e62d207e8dc60b9af5c002c5ab946ded00',
    }
    for name, digest in expected.items():
        with (MODEL_PATH/name).open('rb') as file:
            if hashlib.file_digest(file,'sha256').hexdigest()!=digest:
                raise ValueError('La integridad del modelo no coincide con la versión fijada. Repite la descarga desde la fuente oficial.')


@lru_cache(maxsize=1)
def semantic_model():
    try:
        verify_model()
        from fastembed import TextEmbedding
        return TextEmbedding(model_name=MODEL, cache_dir=str(CACHE), threads=2, local_files_only=True, specific_model_path=str(MODEL_PATH))
    except Exception:
        raise ValueError('El modelo semántico no está disponible. Instala requirements-ai.txt y ejecuta python -m backend.download_model con acceso a Hugging Face. Puedes usar la comparación léxica mientras tanto.') from None


def snippets(text):
    # Fragmentos exactos: no se traducen ni se generan frases.
    return [match.group(0) for match in re.finditer(r'[^\n.!?]+[.!?]?', text) if match.group(0).strip()][:80]


def analyze(review, articles, engine):
    question = review['question']
    criteria = [('inclusion', value.strip()) for value in review['inclusion'].splitlines() if value.strip()]
    criteria += [('exclusion', value.strip()) for value in review['exclusion'].splitlines() if value.strip()]
    if len(criteria) > 40:
        raise ValueError('Usa como máximo 40 criterios para este prototipo.')
    documents = [(a['title'] + '\n' + a['abstract'])[:52000] for a in articles]
    chunks = [snippets(doc) for doc in documents]
    texts = [question] + [criterion for _, criterion in criteria] + documents + [chunk for group in chunks for chunk in group]
    if engine == 'semantic':
        model = semantic_model()
        vectors = normalize(np.asarray(list(model.embed(texts, batch_size=8))))
        model_name = MODEL
    else:
        try:
            vectors = TfidfVectorizer(ngram_range=(1, 2), max_features=12000, strip_accents='unicode').fit_transform(texts)
        except ValueError:
            raise ValueError('No hay suficiente texto para comparar los artículos.') from None
        model_name = 'TF-IDF (referencia léxica, no semántica)'
    start = 1 + len(criteria)
    doc_vectors = vectors[start:start + len(documents)]
    if engine == 'semantic':
        offset = start + len(documents)
        pooled = []
        for i, group in enumerate(chunks):
            pooled.append(vectors[offset:offset+len(group)].mean(axis=0) if group else doc_vectors[i])
            offset += len(group)
        doc_vectors = normalize(np.asarray(pooled))
    scores = doc_vectors @ vectors[0].reshape(-1, 1) if engine == 'semantic' else doc_vectors @ vectors[0].T
    scores = np.asarray(scores if engine == 'semantic' else scores.toarray()).ravel()
    labeled = [i for i, a in enumerate(articles) if a['decision'] in ('included', 'excluded')]
    labels = [int(articles[i]['decision'] == 'included') for i in labeled]
    predictions = None
    if labels.count(0) >= 3 and labels.count(1) >= 3:
        classifier = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
        classifier.fit(doc_vectors[labeled], labels)
        predictions = classifier.predict_proba(doc_vectors)[:, 1]
    cursor = start + len(documents)
    output = []
    for i, article in enumerate(articles):
        count = len(chunks[i])
        evidence = []
        for j, (kind, criterion) in enumerate(criteria):
            if count:
                values = vectors[cursor:cursor+count] @ vectors[j+1].reshape(-1, 1) if engine == 'semantic' else vectors[cursor:cursor+count] @ vectors[j+1].T
                values = np.asarray(values if engine == 'semantic' else values.toarray()).ravel()
                best = int(values.argmax())
                quote = chunks[i][best]
                offset = documents[i].find(quote)
                # Una coincidencia textual no establece elegibilidad metodológica.
                evidence.append({'kind': kind, 'criterion': criterion, 'quote': quote, 'start': offset, 'end': offset + len(quote), 'exact_match': offset >= 0 and documents[i][offset:offset+len(quote)] == quote, 'similarity': round(float(values[best]), 4), 'signal_present': float(values[best]) > 0, 'status': 'requires_human_review'})
        cursor += count
        recommendation = None
        if predictions is not None and article['decision'] == 'pending':
            recommendation = {'label': 'included' if predictions[i] >= .5 else 'excluded', 'score': round(float(predictions[i]), 4), 'model': 'LogisticRegression', 'training_examples': len(labels), 'validated': False}
        output.append({'id': article['id'], 'score': round(float(scores[i]), 4), 'analysis': {
            'engine': engine, 'model': model_name, 'protocol_version': review['protocol_version'],
            'model_revision': MODEL_REVISION if engine == 'semantic' else None,
            'text_sha256': hashlib.sha256(documents[i].encode()).hexdigest(),
            'scope': 'title_and_abstract', 'max_sentence_fragments': 80,
            'missing_abstract': not bool(article['abstract'].strip()),
            'evidence': evidence, 'recommendation': recommendation,
            'classifier_status': 'trained_on_reviewer_decisions' if predictions is not None else 'needs_3_included_and_3_excluded',
        }})
    return output
