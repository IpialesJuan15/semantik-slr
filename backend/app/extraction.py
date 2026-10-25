"""Human-confirmed extraction facts, each backed by an exact PDF page quote."""
import json
from .documents import clean_pdf_text

FIELDS = {
    'country': ('País y contexto', 'Where was this study conducted? university country participants setting'),
    'participants': ('Participantes', 'Study sample participants students professors number context'),
    'ai_tool': ('Herramienta de IA', 'AI software tool used in this study generated texts chatbot application'),
    'ai_technique': ('Técnica de IA', 'Method used by AI tool machine learning deep learning natural language processing NLP'),
    'method': ('Método de investigación', 'Research methodology study design data collection experiment'),
    'outcomes': ('Resultados principales', 'Findings results of this study outcomes reported'),
}

def verify_facts(facts, pages):
    indexed = {page['page']: clean_pdf_text(page['text']) for page in pages}
    verified = {}
    for name, item in facts.items():
        if name not in FIELDS or not isinstance(item, dict):
            raise ValueError('La ficha contiene un campo desconocido.')
        value = str(item.get('value') or '').strip()
        quote = str(item.get('quote') or '').strip()
        page = item.get('page')
        if not value and not quote and page is None:
            continue
        if not value or len(value) > 1000 or not quote or len(quote) > 800 or type(page) is not int or page not in indexed:
            raise ValueError(f'Completa valor, cita y página válidos para «{FIELDS[name][0]}».')
        compact = lambda text: ' '.join(clean_pdf_text(text).split()).casefold()
        if len(compact(quote)) < 20 or compact(quote) not in compact(indexed[page]):
            raise ValueError(f'La cita de «{FIELDS[name][0]}» no aparece en la página {page} del PDF. Selecciona un pasaje extraído de esa página.')
        verified[name] = {'value': value, 'quote': quote, 'page': page, 'verified': True}
    return verified

def latest_extraction(db, article_id, protocol_version, sha):
    row = db.execute('''SELECT data_json,created_at FROM article_extractions
        WHERE article_id=? AND protocol_version=? AND document_sha256=? ORDER BY id DESC LIMIT 1''',
        (article_id,protocol_version,sha)).fetchone()
    return {'facts':json.loads(row['data_json']),'created_at':row['created_at']} if row else {'facts':{},'created_at':None}
