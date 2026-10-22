import hashlib
import calendar
import os
import re
import unicodedata
from urllib.parse import quote

import httpx


class SourceLimitError(ValueError):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


def retry_delay(response):
    for name in ('Retry-After', 'X-RateLimit-Reset'):
        value = response.headers.get(name, '')
        if value.isdigit():
            return min(int(value), 86400)
    return None


def delay_text(seconds):
    if seconds is None:
        return 'Consulta de nuevo más tarde.'
    if seconds >= 3600:
        return f'Prueba dentro de unas {max(1, round(seconds / 3600))} horas.'
    return f'Prueba dentro de {max(1, (seconds + 59) // 60)} minutos.'


def month_number(value):
    if not value: return None
    raw=str(value).strip()
    if raw.isdigit():
        number=int(raw)
        return number if 1<=number<=12 else None
    names=[name.lower() for name in calendar.month_name]
    short=[name.lower() for name in calendar.month_abbr]
    raw=raw.lower()
    return names.index(raw) if raw in names else short.index(raw) if raw in short else None


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
        with httpx.Client(timeout=35, headers={'User-Agent': 'SemantikSLR/0.3 (academic review prototype)'}) as client:
            response = client.get('https://api.openalex.org/works', params=params)
    except httpx.HTTPError:
        raise ValueError('No se pudo conectar con OpenAlex. Comprueba la conexión y el acceso a api.openalex.org.') from None
    if response.status_code in (401, 403):
        raise ValueError('OpenAlex rechazó el acceso. Comprueba el permiso de red y configura OPENALEX_API_KEY en el equipo si la API exige una clave.')
    if response.status_code == 429:
        delay=retry_delay(response)
        explanation=('Tu clave configurada agotó su cuota de OpenAlex.' if key else 'Sin clave, OpenAlex comparte una cuota diaria con otras personas de tu red.')
        raise SourceLimitError(f'{explanation} {delay_text(delay)} Puedes usar DOAJ mientras tanto o configurar una clave gratuita de OpenAlex.', delay)
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


def search_doaj(query, year_from, year_to, limit, date_from=None):
    """Search DOAJ article metadata; date precision is often only a year."""
    url='https://doaj.org/api/search/articles/'+quote(query.strip(), safe='')
    try:
        with httpx.Client(timeout=35, headers={'User-Agent':'SemantikSLR/0.3 (academic review prototype)'}) as client:
            response=client.get(url,params={'page':1,'pageSize':limit})
    except httpx.HTTPError:
        raise ValueError('No se pudo conectar con DOAJ. Comprueba la conexión y el acceso a doaj.org.') from None
    if response.status_code==429:
        delay=retry_delay(response)
        raise SourceLimitError(f'DOAJ limitó temporalmente sus consultas. {delay_text(delay)} Usa OpenAlex si está disponible.',delay)
    if response.status_code!=200:
        raise ValueError(f'DOAJ respondió con el estado {response.status_code}. No se guardaron resultados de esta consulta.')
    try:
        payload=response.json()
        works=payload['results']
        if not isinstance(works,list): raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise ValueError('DOAJ devolvió una respuesta no reconocida.') from None
    records=[]
    for work in works:
        bib=work.get('bibjson') or {}
        title=bib.get('title')
        if not isinstance(title,str) or not title.strip(): continue
        try: year=int(bib.get('year'))
        except (ValueError,TypeError): continue
        if not year_from<=year<=year_to: continue
        if date_from and year<date_from.year: continue
        month=month_number(bib.get('month'))
        if date_from and year==date_from.year and month is not None and month<date_from.month: continue
        date_uncertain=bool(date_from and year==date_from.year and (month is None or (month==date_from.month and date_from.day>1)))
        identifiers=bib.get('identifier') or []
        doi=next((item.get('id','') for item in identifiers if item.get('type','').lower()=='doi'), '')
        links=bib.get('link') or []
        url=next((item.get('url','') for item in links if item.get('type')=='fulltext'), '')
        if not url: url=next((item.get('url','') for item in links), '')
        records.append({'title':title.strip(),'abstract':bib.get('abstract') or '',
                        'doi':normalize_doi(doi),'year':year,
                        'authors':', '.join(item.get('name','') for item in (bib.get('author') or [])[:30]),
                        'url':url,'source':'DOAJ','is_oa':True,'date_uncertain':date_uncertain})
    return records, payload.get('total',len(works))
