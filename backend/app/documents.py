"""Fetch and read candidate PDFs while preserving page-level provenance."""

import hashlib
import io
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from pypdf import PdfReader

from .sources import retry_delay

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 80
MAX_TEXT_CHARS = 160000
USER_AGENT = 'SemantikSLR/0.8 (academic review prototype)'


def public_https(url):
    """Reject local/private hosts, including each redirected destination."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.casefold().rstrip('.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        return False
    try:
        if not ipaddress.ip_address(host).is_global:
            return False
    except ValueError:
        pass
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        # In managed environments HTTPS traffic may resolve only through a proxy.
        # The proxy applies its own destination policy; local/private hostnames
        # and literal addresses are still rejected above.
        return bool(os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'))
    return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)


def openalex_pdf_urls(doi):
    if not doi:
        raise ValueError('Este candidato no tiene DOI. Adjunta el PDF si lo obtuviste de una fuente autorizada.')
    key = os.getenv('OPENALEX_API_KEY')
    params = {'filter': f'doi:https://doi.org/{doi}', 'per-page': 1}
    if key:
        params['api_key'] = key
    try:
        with httpx.Client(timeout=25, headers={'User-Agent': USER_AGENT}) as client:
            response = client.get('https://api.openalex.org/works', params=params)
    except httpx.HTTPError:
        raise ValueError('No se pudo consultar OpenAlex para localizar el PDF abierto.') from None
    if response.status_code == 429:
        wait = retry_delay(response)
        raise ValueError(f'OpenAlex alcanzó su límite. Vuelve a intentar más tarde{f" ({wait} segundos)" if wait is not None else ""}.')
    if response.status_code != 200:
        raise ValueError(f'OpenAlex respondió {response.status_code}; no se descargó ningún PDF.')
    try:
        works = response.json()['results']
    except (ValueError, KeyError, TypeError):
        raise ValueError('OpenAlex devolvió una respuesta no reconocida.') from None
    if not works:
        raise ValueError('OpenAlex no encontró este DOI. Puedes adjuntar el PDF manualmente.')
    work = works[0]
    if not (work.get('open_access') or {}).get('is_oa'):
        raise ValueError('OpenAlex no registra una versión abierta de este artículo. Comprueba la fuente o adjunta un PDF autorizado.')
    locations = [work.get('best_oa_location'), *(work.get('locations') or [])]
    urls = []
    for location in locations:
        if location and location.get('is_oa') and location.get('pdf_url'):
            url = location['pdf_url']
            if public_https(url) and url not in urls:
                urls.append(url)
    if urls:
        return urls
    raise ValueError('Hay una versión abierta registrada, pero no se encontró un enlace PDF utilizable. Comprueba la fuente o adjunta el PDF.')


def download_pdf(url):
    if not public_https(url):
        raise ValueError('El enlace al PDF no es una dirección HTTPS pública válida.')
    try:
        with httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=False, headers={'User-Agent': USER_AGENT, 'Accept': 'application/pdf'}) as client:
            for _ in range(6):
                if not public_https(url):
                    raise ValueError('La fuente redirigió el PDF a una dirección no permitida.')
                with client.stream('GET', url) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get('location')
                        if not location:
                            raise ValueError('La fuente redirigió sin indicar destino.')
                        url = urljoin(url, location)
                        continue
                    if response.status_code != 200:
                        raise ValueError(f'La fuente del PDF respondió {response.status_code}. Puedes adjuntar el archivo manualmente.')
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_PDF_BYTES:
                            raise ValueError('El PDF supera el límite de 8 MB. Puedes consultar la fuente directamente.')
                    return bytes(content), url
    except httpx.HTTPError:
        raise ValueError('No se pudo descargar el PDF abierto. Comprueba el enlace o adjúntalo manualmente.') from None
    raise ValueError('El enlace al PDF hizo demasiadas redirecciones.')


def extract_pdf(content):
    if not content.startswith(b'%PDF'):
        raise ValueError('La fuente no entregó un PDF válido.')
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
            raise ValueError('El PDF debe estar sin contraseña y tener hasta 80 páginas.')
        pages = []
        total = 0
        truncated = False
        for index, page in enumerate(reader.pages, 1):
            extracted = (page.extract_text() or '').strip()
            space = max(0, MAX_TEXT_CHARS - total)
            if len(extracted) > space:
                truncated = True
            extracted = extracted[:space]
            total += len(extracted)
            pages.append({'page': index, 'text': extracted})
        if total < 50:
            raise ValueError('No se pudo extraer texto del PDF. Puede ser un escaneo; el OCR todavía no está disponible.')
        return {'pages': pages, 'page_count': len(reader.pages), 'characters': total,
                'truncated': truncated, 'sha256': hashlib.sha256(content).hexdigest()}
    except ValueError:
        raise
    except Exception:
        raise ValueError('El archivo PDF no se pudo leer. Comprueba que no esté dañado.') from None
