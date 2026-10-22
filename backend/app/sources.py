import hashlib
import os
import re
import unicodedata

import httpx


def normalize_doi(value):
    value = value.strip().lower()
    for prefix in ('https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'doi:'):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value.strip()


def identity(article):
    doi = normalize_doi(article.get('doi', ''))
    if doi:
        return 'doi:' + doi
    title = unicodedata.normalize('NFKD', article['title']).casefold()
    title = re.sub(r'[^\w]+', ' ', title).strip()
    return 'title:' + hashlib.sha256(title.encode()).hexdigest()


def abstract_text(index):
    if not isinstance(index, dict):
        return ''
    words = [(position, word) for word, positions in index.items() for position in positions if isinstance(position, int)]
    return ' '.join(word for _, word in sorted(words))[:50000]


def search_openalex(query, year_from, year_to, limit, date_from=None):
    first_date = str(date_from) if date_from else f'{year_from}-01-01'
    params = {'search': query, 'filter': f'is_oa:true,from_publication_date:{first_date},to_publication_date:{year_to}-12-31', 'per-page': limit}
    key = os.getenv('OPENALEX_API_KEY')
    if key:
        params['api_key'] = key
    try:
        with httpx.Client(timeout=35, headers={'User-Agent': 'SemantikSLR/0.2 (academic review prototype)'}) as client:
            response = client.get('https://api.openalex.org/works', params=params)
    except httpx.HTTPError:
        raise ValueError('No se pudo conectar con OpenAlex. Comprueba la conexión y el acceso a api.openalex.org.') from None
    if response.status_code in (401, 403):
        raise ValueError('OpenAlex rechazó el acceso. Comprueba el permiso de red y configura OPENALEX_API_KEY en el equipo si la API exige una clave.')
    if response.status_code == 429:
        raise ValueError('OpenAlex alcanzó su límite de consultas. Espera y vuelve a intentarlo.')
    if response.status_code != 200:
        raise ValueError(f'OpenAlex respondió con el estado {response.status_code}. No se guardaron resultados de esta consulta.')
    try:
        payload = response.json()
        records = payload['results']
        if not isinstance(records, list):
            raise ValueError()
    except (ValueError, KeyError):
        raise ValueError('OpenAlex devolvió una respuesta no reconocida.') from None
    results = []
    for item in records:
        location = item.get('best_oa_location') or item.get('primary_location') or {}
        results.append({
            'title': item.get('display_name') or 'Sin título',
            'abstract': abstract_text(item.get('abstract_inverted_index')),
            'doi': normalize_doi(item.get('doi') or ''), 'year': item.get('publication_year'),
            'authors': ', '.join((a.get('author') or {}).get('display_name', '') for a in item.get('authorships', [])[:30]),
            'url': location.get('landing_page_url') or item.get('id', ''),
            'source': 'OpenAlex', 'is_oa': bool((item.get('open_access') or {}).get('is_oa')),
        })
    return results, payload.get('meta', {}).get('count', len(results))
