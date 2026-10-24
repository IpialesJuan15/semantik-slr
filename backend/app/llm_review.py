"""Experimental, locally generated screening suggestions with checked PDF quotes."""

import json
import os
import re

import httpx

from .documents import clean_pdf_text

OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
MODEL = 'qwen2.5:3b'
MAX_CRITERIA = 12


def criteria_for(review):
    criteria = []
    for kind, field in (('inclusion', 'inclusion'), ('exclusion', 'exclusion')):
        for line in review[field].splitlines():
            line = line.strip(' -•\t')
            if line:
                criteria.append({'kind': kind, 'text': line})
    if not criteria or len(criteria) > MAX_CRITERIA:
        raise ValueError('El asistente local admite de 1 a 12 criterios. Ajusta el protocolo o revisa manualmente este artículo.')
    return criteria


def passages_for(pages, criteria):
    """Inspect all extracted pages and keep a small, page-labelled context."""
    terms = set(re.findall(r'[a-záéíóúñ]{4,}', ' '.join(item['text'] for item in criteria).lower()))
    terms -= {'para', 'sobre', 'datos', 'esta', 'esta', 'como', 'trabajos', 'estudios', 'publicacion', 'articulo'}
    cues = re.compile(r'abstract|method|sample|setting|participants|result|finding|discussion|conclusion|university|higher education|latin america|saudi|country|empirical|chatbot', re.I)
    ranked = []
    for page in pages:
        value = clean_pdf_text(page['text'])
        for start in range(0, len(value), 850):
            excerpt = value[start:start + 900].strip()
            if len(excerpt) < 50:
                continue
            lower = excerpt.lower()
            score = sum(lower.count(term) for term in terms) + 3 * len(cues.findall(excerpt))
            if page['page'] == 1: score += 3
            ranked.append((score, page['page'], start, excerpt))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    chosen = []
    per_page = {}
    first_page = next((item for item in ranked if item[1] == 1), None)
    if first_page:
        chosen.append(first_page)
        per_page[1] = 1
    for item in ranked:
        if item in chosen or per_page.get(item[1], 0) >= 2:
            continue
        chosen.append(item)
        per_page[item[1]] = per_page.get(item[1], 0) + 1
        if len(chosen) == 12:
            break
    if not chosen:
        raise ValueError('El PDF no contiene pasajes suficientes para revisar.')
    return [{'page': page, 'text': excerpt} for _, page, _, excerpt in sorted(chosen, key=lambda item: (item[1], item[2]))]


def present_in_page(quote, page_text):
    if not isinstance(quote, str) or not 20 <= len(quote) <= 500:
        return False
    compact = lambda value: ' '.join(clean_pdf_text(value).split()).casefold()
    return compact(quote) in compact(page_text)


def generate_local_review(review, article, pages, pdf_hash):
    criteria = criteria_for(review)
    passages = passages_for(pages, criteria)
    instructions = (
        'Eres un asistente de cribado de revisiones sistemáticas. Responde en español con JSON válido: '
        '{"items":[{"index":0,"assessment":"apoya|contradice|incierto","page":1,'
        '"quote":"cita textual exacta","explanation":"explicación breve"}]}. '
        'Devuelve exactamente un item por criterio, usando index desde 0. Si no hay una cita exacta y relevante, '
        'usa assessment incierto, page null y quote vacío. Nunca inventes páginas, citas, fecha ni país. '
        'Un fragmento parecido no demuestra elegibilidad. Una cita que respalda exclusión geográfica debe '
        'referirse al estudio principal, no a otro trabajo citado. La decisión final corresponde al investigador.'
    )
    prompt = json.dumps({'article': {'title': article['title'], 'doi': article['doi']},
                         'criteria': [{'index': index, **item} for index, item in enumerate(criteria)],
                         'pdf_passages': passages}, ensure_ascii=False)
    try:
        with httpx.Client(timeout=httpx.Timeout(180, connect=5), trust_env=False) as client:
            response = client.post(OLLAMA_URL, json={'model': MODEL, 'system': instructions,
                'prompt': prompt, 'format': 'json', 'stream': False,
                'options': {'temperature': 0, 'num_ctx': 8192, 'num_predict': 2200}})
    except httpx.ConnectError:
        raise ValueError('Ollama local no está activo. Instálalo, ejecuta «ollama pull qwen2.5:3b» y vuelve a intentar.') from None
    except httpx.TimeoutException:
        raise ValueError('El LLM local tardó demasiado. Comprueba que Ollama siga activo y vuelve a intentar.') from None
    except httpx.HTTPError:
        raise ValueError('No se pudo consultar el LLM local. Comprueba Ollama y vuelve a intentar.') from None
    if response.status_code != 200:
        raise ValueError('Ollama no pudo generar la revisión. Comprueba que el modelo qwen2.5:3b esté descargado.')
    try:
        raw = json.loads(response.json()['response'])
        raw_items = raw['items']
        if not isinstance(raw_items, list): raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError('El LLM devolvió una respuesta no estructurada. Vuelve a intentar o revisa el PDF manualmente.') from None
    by_index = {}
    for item in raw_items:
        if isinstance(item, dict) and str(item.get('index', '')).isdigit():
            by_index[int(item['index'])] = item
    page_map = {page['page']: clean_pdf_text(page['text']) for page in pages}
    selected_pages = {item['page'] for item in passages}
    results = []
    for index, criterion in enumerate(criteria):
        proposal = by_index.get(index, {})
        page = proposal.get('page')
        if isinstance(page, str) and page.isdigit(): page = int(page)
        quote = proposal.get('quote', '')
        assessment = str(proposal.get('assessment', '')).strip().casefold()
        valid = (type(page) is int and page in selected_pages and page in page_map
                 and present_in_page(quote, page_map[page])
                 and assessment in ('apoya', 'contradice'))
        results.append({'criterion': criterion['text'], 'kind': criterion['kind'],
                        'assessment': assessment if valid else 'incierto',
                        'page': page if valid else None, 'quote': quote if valid else '',
                        'explanation': str(proposal.get('explanation', ''))[:400] if valid else
                        'No se obtuvo una cita textual comprobable para este criterio.',
                        'quote_verified': bool(valid)})
    return {'model': MODEL, 'document_sha256': pdf_hash,
            'protocol_version': review['protocol_version'], 'passages_examined': len(passages),
            'criteria': results, 'scope': 'experimental_pdf_passages',
            'warning': 'Cita presente en el PDF no significa interpretación correcta. Verifica cada criterio y decide tú.'}
