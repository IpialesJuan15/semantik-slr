"""Experimental screening suggestions with checked PDF quotes."""

import json
import os
import re

import httpx

from .documents import clean_pdf_text

OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
MODEL = 'qwen2.5:3b'
CLOUD_MODEL = 'gpt-4.1-mini'
CLOUD_URL = 'https://api.openai.com/v1/chat/completions'
GROQ_MODEL = 'qwen/qwen3.8-27b'
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
MAX_CRITERIA = 12


def criteria_for(review):
    criteria = []
    for kind, field in (('inclusion', 'inclusion'), ('exclusion', 'exclusion')):
        for line in review[field].splitlines():
            line = line.strip(' -•\t')
            if line:
                criteria.append({'kind': kind, 'text': line})
    if not criteria or len(criteria) > MAX_CRITERIA:
        raise ValueError('El asistente admite de 1 a 12 criterios. Ajusta el protocolo o revisa manualmente este artículo.')
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


def request_context(review, article, pages):
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
    return criteria, passages, instructions, prompt


def checked_result(raw_text, criteria, passages, pages, review, pdf_hash, provider, model, usage=None):
    try:
        raw = json.loads(raw_text)
    except (ValueError, TypeError):
        raw = None
        if isinstance(raw_text, str):
            decoder = json.JSONDecoder()
            for match in re.finditer(r'\{', raw_text):
                try:
                    candidate, _ = decoder.raw_decode(raw_text[match.start():])
                except ValueError:
                    continue
                if isinstance(candidate, dict) and ('items' in candidate or 'assessment' in candidate):
                    raw = candidate
                    break
    if not isinstance(raw, dict):
        raise ValueError('El LLM devolvió una respuesta no estructurada. Vuelve a intentar o revisa el PDF manualmente.') from None
    if isinstance(raw.get('items'), list):
        raw_items = raw['items']
    elif len(criteria) == 1 and 'assessment' in raw:
        raw_items = [{**raw, 'index': 0}]
    else:
        raise ValueError('El LLM devolvió una respuesta no estructurada. Vuelve a intentar o revisa el PDF manualmente.')
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
    return {'provider': provider, 'model': model, 'document_sha256': pdf_hash,
            'protocol_version': review['protocol_version'], 'passages_examined': len(passages),
            'criteria': results, 'scope': 'experimental_pdf_passages', 'usage': usage or {},
            'warning': 'Cita presente en el PDF no significa interpretación correcta. Verifica cada criterio y decide tú.'}


def generate_local_review(review, article, pages, pdf_hash):
    criteria, passages, instructions, prompt = request_context(review, article, pages)
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
    try: raw_text = response.json()['response']
    except (ValueError, KeyError, TypeError):
        raise ValueError('Ollama devolvió una respuesta no reconocida.') from None
    return checked_result(raw_text, criteria, passages, pages, review, pdf_hash, 'local', MODEL)


def generate_cloud_review(review, article, pages, pdf_hash):
    key = os.getenv('SEMANTIK_OPENAI_API_KEY', '').strip()
    if not key:
        raise ValueError('Falta SEMANTIK_OPENAI_API_KEY. Configura tu clave en la terminal que inicia la aplicación; no la pegues en el chat.')
    criteria, passages, instructions, prompt = request_context(review, article, pages)
    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=10)) as client:
            response = client.post(CLOUD_URL,
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                json={'model': CLOUD_MODEL, 'messages': [
                    {'role': 'system', 'content': instructions},
                    {'role': 'user', 'content': prompt}],
                    'response_format': {'type': 'json_object'},
                    'temperature': 0, 'max_completion_tokens': 2200})
    except httpx.TimeoutException:
        raise ValueError('El LLM en la nube tardó demasiado. Vuelve a intentar más tarde.') from None
    except httpx.HTTPError:
        raise ValueError('No se pudo conectar con el LLM en la nube. Comprueba Internet y vuelve a intentar.') from None
    if response.status_code in (401, 403):
        raise ValueError('La API rechazó la clave o el acceso al modelo. Revisa tu cuenta y la clave configurada.')
    if response.status_code == 429:
        try:
            error = response.json().get('error') or {}
            code = str(error.get('code') or error.get('type') or '').casefold()
        except (ValueError, TypeError, AttributeError):
            code = ''
        if code in ('insufficient_quota', 'billing_hard_limit_reached', 'billing_not_active'):
            raise ValueError('Tu cuenta de API no tiene cuota o presupuesto disponible. Revisa Facturación y Límites en platform.openai.com. La suscripción de ChatGPT no incluye saldo para la API.')
        if code == 'rate_limit_exceeded':
            delay = response.headers.get('Retry-After', '')
            wait = f' Espera {delay} segundos antes de repetir.' if delay.isdigit() and 0 < int(delay) <= 3600 else ' Espera unos minutos antes de repetir.'
            raise ValueError('La API alcanzó un límite temporal de solicitudes.' + wait)
        raise ValueError('OpenAI respondió 429. Puede faltar cuota de API o haber un límite temporal. Revisa Facturación, Uso y Límites en platform.openai.com antes de repetir.')
    if response.status_code != 200:
        raise ValueError(f'La API del LLM respondió {response.status_code}. No se guardó ninguna propuesta.')
    try:
        payload = response.json()
        raw_text = payload['choices'][0]['message']['content']
        usage = payload.get('usage') or {}
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError('La API devolvió una respuesta no reconocida. No se guardó ninguna propuesta.') from None
    safe_usage = {field: int(usage[field]) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                  if isinstance(usage.get(field), int) and usage[field] >= 0}
    return checked_result(raw_text, criteria, passages, pages, review, pdf_hash,
                          'cloud', CLOUD_MODEL, safe_usage)


def generate_groq_review(review, article, pages, pdf_hash, criterion_index):
    """Generate one criterion at a time to stay below the free OTPM cap."""
    key = os.getenv('SEMANTIK_GROQ_API_KEY', '').strip()
    if not key:
        raise ValueError('Falta SEMANTIK_GROQ_API_KEY. Configura tu clave de Groq en la terminal que inicia la aplicación; no la pegues en el chat.')
    all_criteria = criteria_for(review)
    if criterion_index is None or not 0 <= criterion_index < len(all_criteria):
        raise ValueError('Elige un criterio válido antes de consultar Groq.')
    chosen = all_criteria[criterion_index]
    single_review = {**review,
                     'inclusion': chosen['text'] if chosen['kind'] == 'inclusion' else '',
                     'exclusion': chosen['text'] if chosen['kind'] == 'exclusion' else ''}
    criteria, passages, _, prompt = request_context(single_review, article, pages)
    instructions = (
        'Eres un asistente de cribado de revisiones sistemáticas. Responde en español con un único '
        'objeto JSON: {"assessment":"apoya|contradice|incierto","page":1,'
        '"quote":"cita textual exacta","explanation":"explicación breve"}. '
        'Evalúa solamente el criterio del usuario. Cita un pasaje exacto de hasta 150 caracteres de '
        'pdf_passages, con su página, y explica en hasta 25 palabras. Si no hay cita relevante, usa '
        'incierto, page null y quote vacío. No inventes país, fecha, páginas ni citas. '
        'Un pasaje de otro estudio citado no demuestra el lugar del estudio principal. '
        'No incluyas razonamiento previo ni bloques Markdown. La decisión final es humana.'
    )
    try:
        with httpx.Client(timeout=httpx.Timeout(90, connect=10)) as client:
            response = client.post(GROQ_URL,
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                json={'model': GROQ_MODEL, 'messages': [
                    {'role': 'system', 'content': instructions},
                    {'role': 'user', 'content': prompt}],
                    'temperature': 0, 'max_completion_tokens': 300, 'stream': False})
    except httpx.TimeoutException:
        raise ValueError('Groq tardó demasiado. Vuelve a intentar con este criterio más tarde.') from None
    except httpx.HTTPError:
        raise ValueError('No se pudo conectar con Groq. Comprueba Internet y vuelve a intentar.') from None
    if response.status_code in (401, 403):
        raise ValueError('Groq rechazó la clave o el acceso al modelo. Revisa tu proyecto y la clave configurada.')
    if response.status_code == 429:
        raise ValueError('Groq alcanzó el límite gratuito de tokens o solicitudes. Espera al menos un minuto antes de analizar otro criterio; no necesitas cambiar de plan para esta prueba.')
    if response.status_code != 200:
        raise ValueError(f'Groq respondió {response.status_code}. No se guardó ninguna propuesta.')
    try:
        payload = response.json()
        choice = payload['choices'][0]
        raw_text = choice['message']['content']
        usage = payload.get('usage') or {}
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError('Groq devolvió una respuesta no reconocida. No se guardó ninguna propuesta.') from None
    safe_usage = {field: int(usage[field]) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                  if isinstance(usage.get(field), int) and usage[field] >= 0}
    if choice.get('finish_reason') == 'length':
        raise ValueError('Groq agotó los 300 tokens de respuesta antes de terminar el JSON. Espera al menos un minuto y vuelve a intentar este criterio; no se guardó ninguna propuesta.')
    result = checked_result(raw_text, criteria, passages, pages, review, pdf_hash,
                            'groq', GROQ_MODEL, safe_usage)
    result['criterion_index'] = criterion_index
    return result
