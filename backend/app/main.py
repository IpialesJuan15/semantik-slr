import csv
import hashlib
import html
import io
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader
from .analysis import analyze, MODEL
from .documents import MAX_PDF_BYTES, clean_pdf_text, download_pdf, extract_pdf, openalex_pdf_urls
from .evaluation import evaluate
from .pdf_retrieval import retrieve_passages
from .llm_review import GROQ_MODEL, criteria_for, generate_cloud_review, generate_groq_review, generate_local_review
from .published import DOI as PUBLISHED_DOI, template as published_template, update_inclusion
from .sources import SourceLimitError, identity, normalize_doi, search_doaj, search_openalex
from .storage import article_json, connect, event, initialize

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_BUILD = ROOT / 'frontend/dist'

class ReviewInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    inclusion: str = Field(min_length=1, max_length=10000)
    exclusion: str = Field(min_length=1, max_length=10000)
    base_reference: str = Field(default='', max_length=1000)
    search_query: str = Field(default='', max_length=1000)
    @field_validator('title', 'question', 'inclusion', 'exclusion')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('Completa este campo.')
        return value.strip()

class ArticleInput(BaseModel):
    title: str = Field(min_length=1, max_length=2000)
    abstract: str = Field(default='', max_length=50000)
    doi: str = Field(default='', max_length=300)
    year: int | None = Field(default=None, ge=1800, le=2100)
    authors: str = Field(default='', max_length=5000)
    url: str = Field(default='', max_length=2000)
    is_oa: bool = False
    @field_validator('title')
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError('El título es obligatorio.')
        return value.strip()
    @field_validator('url')
    @classmethod
    def valid_url(cls, value):
        if value and not value.startswith(('https://', 'http://')): raise ValueError('Usa una URL http o https.')
        return value

class SearchInput(BaseModel):
    source: Literal['openalex', 'doaj'] = 'openalex'
    query: str = Field(min_length=3, max_length=1000)
    year_from: int = Field(default=2020, ge=1800, le=2100)
    year_to: int = Field(default_factory=lambda: date.today().year, ge=1800, le=2100)
    limit: int = Field(default=25, ge=1, le=100)
    date_from: date | None = None
    date_to: date | None = None

class DecisionInput(BaseModel):
    decision: Literal['pending', 'included', 'excluded']
    reason: str = Field(min_length=3, max_length=4000)
    @field_validator('reason')
    @classmethod
    def valid_reason(cls, value):
        if len(value.strip()) < 3: raise ValueError('Explica el motivo de la decisión.')
        return value.strip()

class AnalysisInput(BaseModel):
    engine: Literal['lexical', 'semantic'] = 'lexical'

class LLMReviewInput(BaseModel):
    retrieval: Literal['semantic', 'lexical', 'legacy'] = 'legacy'
    provider: Literal['local', 'cloud', 'groq'] = 'local'
    criterion_index: int | None = Field(default=None, ge=0, le=11)

class PublishedInput(BaseModel):
    doi: str = Field(min_length=3, max_length=300)

class PublishedMethodInput(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=10)
    inclusion: list[str] = Field(min_length=1, max_length=40)
    exclusion: list[str] = Field(min_length=1, max_length=40)
    sources: list[str] = Field(min_length=1, max_length=20)
    search_strategy: str = Field(min_length=10, max_length=5000)
    search_date: str = Field(pattern=r'^\d{4}-\d{2}$')
    last_included_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    @field_validator('questions', 'inclusion', 'exclusion', 'sources')
    @classmethod
    def nonempty_items(cls, values):
        if any(not value.strip() or len(value)>2000 for value in values):
            raise ValueError('Cada elemento debe tener contenido y máximo 2000 caracteres.')
        return [value.strip() for value in values]
    @field_validator('search_date')
    @classmethod
    def valid_month(cls, value):
        try: date.fromisoformat(value+'-01')
        except ValueError: raise ValueError('Indica un mes válido.') from None
        return value
    @field_validator('last_included_date')
    @classmethod
    def valid_cutoff(cls, value):
        try: date.fromisoformat(value)
        except ValueError: raise ValueError('Indica una fecha válida.') from None
        return value

def create_app(database_path=None):
    path = Path(database_path or os.getenv('SEMANTIK_DATABASE', ROOT / '.local/reviews.sqlite3'))
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='semantik-analysis')
    job_lock = threading.Lock()
    @asynccontextmanager
    async def lifespan(app):
        initialize(path)
        yield
        executor.shutdown(wait=True)
    app = FastAPI(title='Semantik SLR', version='0.12.2', lifespan=lifespan)

    def get_review(db, review_id):
        row = db.execute('SELECT * FROM reviews WHERE id=?', (review_id,)).fetchone()
        if row is None: raise HTTPException(404, 'No encontramos esa revisión.')
        return dict(row)

    def get_published(db, review_id):
        row = db.execute('SELECT * FROM published_bases WHERE review_id=?',(review_id,)).fetchone()
        if row is None: raise HTTPException(404,'Esta revisión no tiene un estudio publicado registrado.')
        return {**json.loads(row['snapshot']), 'confirmed':bool(row['confirmed']), 'created_at':row['created_at']}

    def is_base_publication(record, base):
        doi=normalize_doi(record.get('doi',''))
        return bool((doi and doi==normalize_doi(base['doi'])) or identity({'title':record['title']})==identity({'title':base['title']}))

    def base_snapshot(db, review_id):
        row=db.execute('SELECT snapshot FROM published_bases WHERE review_id=?',(review_id,)).fetchone()
        return json.loads(row['snapshot']) if row else None

    def add_articles(db, review_id, records, source):
        added = 0
        base_row = db.execute('SELECT snapshot FROM published_bases WHERE review_id=?', (review_id,)).fetchone()
        base = json.loads(base_row['snapshot']) if base_row else None
        for record in records:
            record = dict(record)
            doi = normalize_doi(record.get('doi', ''))
            key = identity(record)
            title_key = identity({'title': record['title']})
            if base and is_base_publication(record,base): continue
            existing = db.execute('SELECT title,doi FROM articles WHERE review_id=?', (review_id,)).fetchall()
            if any((doi and normalize_doi(row['doi']) == doi) or identity({'title':row['title']}) == title_key for row in existing): continue
            db.execute('INSERT INTO articles (review_id,identity,title,abstract,doi,year,authors,url,source,is_oa) VALUES (?,?,?,?,?,?,?,?,?,?)', (review_id,key,record['title'],record.get('abstract',''),doi,record.get('year'),record.get('authors',''),record.get('url',''),source,int(record.get('is_oa',False))))
            added += 1
        return added

    def get_candidate(db, article_id):
        row = db.execute('SELECT * FROM articles WHERE id=?', (article_id,)).fetchone()
        if row is None: raise HTTPException(404, 'Artículo no encontrado.')
        base = base_snapshot(db, row['review_id'])
        if base and is_base_publication(dict(row), base):
            raise HTTPException(422, 'Esta es la revisión base, no un artículo candidato nuevo.')
        return row

    def save_document(article_id, content, source_type, source_url='', filename='articulo.pdf'):
        try: extracted = extract_pdf(content)
        except ValueError as error: raise HTTPException(422, str(error)) from None
        with connect(path) as db:
            article = get_candidate(db, article_id)
            db.execute('''INSERT INTO article_documents
                (article_id,source_type,source_url,filename,sha256,page_count,characters,truncated,pages_json,pdf)
                VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(article_id) DO UPDATE SET
                source_type=excluded.source_type,source_url=excluded.source_url,filename=excluded.filename,
                sha256=excluded.sha256,page_count=excluded.page_count,characters=excluded.characters,
                truncated=excluded.truncated,pages_json=excluded.pages_json,pdf=excluded.pdf,
                created_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')''',
                (article_id, source_type, source_url, filename, extracted['sha256'],
                 extracted['page_count'], extracted['characters'], int(extracted['truncated']),
                 json.dumps(extracted['pages'], ensure_ascii=False), content))
            event(db, article['review_id'], 'candidate_pdf_read',
                  {'article_id': article_id, 'source_type': source_type, 'source_url': source_url,
                   'sha256': extracted['sha256'], 'pages': extracted['page_count'],
                   'characters': extracted['characters'], 'truncated': extracted['truncated']})
        return document_info(article_id)

    def document_info(article_id):
        with connect(path) as db:
            get_candidate(db, article_id)
            row = db.execute('''SELECT source_type,source_url,filename,sha256,page_count,
                characters,truncated,pages_json FROM article_documents WHERE article_id=?''', (article_id,)).fetchone()
        if row is None:
            return {'status': 'missing'}
        return {'status': 'read', 'source_type': row['source_type'], 'source_url': row['source_url'],
                'filename': row['filename'], 'sha256': row['sha256'], 'page_count': row['page_count'],
                'characters': row['characters'], 'truncated': bool(row['truncated']),
                'page_previews': [{'page': page['page'], 'text': clean_pdf_text(page['text'])[:1200]}
                                  for page in json.loads(row['pages_json']) if page['text'].strip()][:12]}

    @app.get('/health')
    def health():
        with connect(path) as db: db.execute('SELECT count(*) FROM reviews').fetchone()
        return {'status':'ok'}

    @app.get('/api/status')
    def status():
        import importlib.util
        return {'semantic_package_installed': importlib.util.find_spec('fastembed') is not None, 'model':MODEL, 'openalex_key_configured':bool(os.getenv('OPENALEX_API_KEY')), 'cloud_llm_configured':bool(os.getenv('SEMANTIK_OPENAI_API_KEY')), 'groq_key_configured':bool(os.getenv('SEMANTIK_GROQ_API_KEY')), 'mode':'local_single_user', 'version':'0.12.2'}

    @app.get('/api/published-template')
    def published_template_info():
        info = published_template(PUBLISHED_DOI)
        return {key:info[key] for key in ('doi','title','authors','year','source_url','license','original_count','method_source')}

    @app.post('/api/reviews/from-published', status_code=201)
    def create_from_published(payload: PublishedInput):
        try: base = published_template(payload.doi)
        except ValueError as error: raise HTTPException(422,str(error)) from None
        with connect(path) as db:
            cursor = db.execute('INSERT INTO reviews (title,question,inclusion,exclusion,base_reference,search_query) VALUES (?,?,?,?,?,?)',(
                base['title'], '\n'.join(base['questions']), update_inclusion(base),
                '\n'.join(base['exclusion']), base['doi'], 'artificial intelligence higher education Latin America'))
            db.execute('INSERT INTO published_bases (review_id,doi,snapshot) VALUES (?,?,?)',(
                cursor.lastrowid,base['doi'],json.dumps(base,ensure_ascii=False)))
            event(db,cursor.lastrowid,'published_base_created',{'doi':base['doi'],'original_count':base['original_count'],'confirmed':False})
            return get_review(db,cursor.lastrowid)

    @app.get('/api/reviews/{review_id}/published-base')
    def published_base(review_id:int):
        with connect(path) as db:
            get_review(db,review_id)
            return get_published(db,review_id)

    @app.put('/api/reviews/{review_id}/published-base')
    def confirm_published_base(review_id:int, payload:PublishedMethodInput):
        with connect(path) as db:
            review=get_review(db,review_id)
            base=get_published(db,review_id)
            if not review['base_text']:
                raise HTTPException(422,'Sube primero el PDF original con texto seleccionable.')
            updated=payload.model_dump()
            for key,value in updated.items(): base[key]=value
            changed = (review['question']!='\n'.join(base['questions']) or
                       review['inclusion']!=update_inclusion(base) or
                       review['exclusion']!='\n'.join(base['exclusion']))
            if changed:
                db.execute('UPDATE reviews SET question=?,inclusion=?,exclusion=?,protocol_version=protocol_version+1 WHERE id=?',(
                    '\n'.join(base['questions']),update_inclusion(base),'\n'.join(base['exclusion']),review_id))
                db.execute('UPDATE articles SET score=NULL,analysis=NULL,analyzed_version=NULL WHERE review_id=?',(review_id,))
            db.execute('UPDATE published_bases SET snapshot=?,confirmed=1 WHERE review_id=?',(
                json.dumps({k:v for k,v in base.items() if k not in ('confirmed','created_at')},ensure_ascii=False),review_id))
            event(db,review_id,'published_base_confirmed',{'doi':base['doi'],'method_changed':changed,'protocol_version':review['protocol_version']+int(changed)})
            return get_published(db,review_id)

    @app.get('/api/reviews')
    def reviews():
        with connect(path) as db:
            rows = db.execute("SELECT r.*, (SELECT count(*) FROM articles a WHERE a.review_id=r.id) article_count, (SELECT count(*) FROM articles a WHERE a.review_id=r.id AND a.decision='included') included_count FROM reviews r ORDER BY r.id DESC").fetchall()
            result=[]
            for row in rows:
                item={k:row[k] for k in row.keys() if k != 'base_text'}
                base=base_snapshot(db,row['id'])
                if base:
                    legacy=[article for article in db.execute('SELECT title,doi,decision FROM articles WHERE review_id=?',(row['id'],)) if is_base_publication(dict(article),base)]
                    item['article_count']-=len(legacy)
                    item['included_count']-=sum(article['decision']=='included' for article in legacy)
                result.append(item)
        return result

    @app.post('/api/reviews', status_code=201)
    def create_review(payload: ReviewInput):
        with connect(path) as db:
            values = payload.model_dump()
            cursor = db.execute('INSERT INTO reviews (title,question,inclusion,exclusion,base_reference,search_query) VALUES (?,?,?,?,?,?)', tuple(values.values()))
            event(db,cursor.lastrowid,'protocol_created',values)
            return get_review(db,cursor.lastrowid)

    @app.get('/api/reviews/{review_id}')
    def review(review_id:int):
        with connect(path) as db: return get_review(db,review_id)

    @app.put('/api/reviews/{review_id}')
    def edit_review(review_id:int, payload:ReviewInput):
        with connect(path) as db:
            previous = get_review(db,review_id)
            values = payload.model_dump()
            db.execute('UPDATE reviews SET title=?,question=?,inclusion=?,exclusion=?,base_reference=?,search_query=?,protocol_version=protocol_version+1 WHERE id=?', (*values.values(),review_id))
            db.execute('UPDATE articles SET score=NULL,analysis=NULL,analyzed_version=NULL WHERE review_id=?',(review_id,))
            db.execute('UPDATE published_bases SET confirmed=0 WHERE review_id=?',(review_id,))
            event(db,review_id,'protocol_updated',{'previous':{k:previous[k] for k in values},'current':values,'previous_version':previous['protocol_version'],'decisions_require_recheck':True})
            return get_review(db,review_id)

    @app.post('/api/reviews/{review_id}/base-pdf')
    async def upload_base(review_id:int, file:UploadFile=File(...)):
        with connect(path) as db: get_review(db,review_id)
        content = await file.read(8*1024*1024+1)
        await file.close()
        if len(content)>8*1024*1024: raise HTTPException(413,'El PDF debe ocupar como máximo 8 MB.')
        if not content.startswith(b'%PDF'): raise HTTPException(422,'Selecciona un archivo PDF válido.')
        try:
            pdf = PdfReader(io.BytesIO(content))
            if pdf.is_encrypted or len(pdf.pages)>80: raise ValueError()
            text = '\n\n'.join(page.extract_text() or '' for page in pdf.pages)[:120000]
        except Exception:
            raise HTTPException(422,'El PDF debe ser legible, sin contraseña y de hasta 80 páginas.') from None
        if len(text.strip())<50: raise HTTPException(422,'No se pudo extraer texto. Usa un PDF con texto seleccionable; el OCR todavía no está disponible.')
        with connect(path) as db:
            base_row=db.execute('SELECT snapshot FROM published_bases WHERE review_id=?',(review_id,)).fetchone()
            source_match=None
            if base_row:
                base_data=json.loads(base_row['snapshot'])
                simplified=' '.join(text.casefold().split()).replace('‑','-').replace('–','-')
                source_match=base_data['doi'] in simplified or base_data['title'].casefold() in simplified
                if not source_match:
                    raise HTTPException(422,'No se encontró el DOI ni el título esperado en este PDF. Selecciona la revisión publicada correcta.')
            db.execute('UPDATE reviews SET base_text=?,base_filename=? WHERE id=?',(text,Path(file.filename or 'revision.pdf').name,review_id))
            db.execute('UPDATE published_bases SET confirmed=0 WHERE review_id=?',(review_id,))
            event(db,review_id,'base_pdf_imported',{'filename':Path(file.filename or 'revision.pdf').name,'sha256':hashlib.sha256(content).hexdigest(),'pages':len(pdf.pages),'source_match':source_match})
        return {'characters':len(text),'pages':len(pdf.pages),'text':text,'source_match':source_match}

    @app.get('/api/reviews/{review_id}/articles')
    def articles(review_id:int):
        with connect(path) as db:
            get_review(db,review_id)
            base=base_snapshot(db,review_id)
            return [{**article_json(row),'is_base_publication':bool(base and is_base_publication(dict(row),base))} for row in db.execute('SELECT * FROM articles WHERE review_id=? ORDER BY score DESC,id DESC',(review_id,))]

    @app.get('/api/articles/{article_id}/document')
    def candidate_document(article_id: int):
        return document_info(article_id)

    @app.get('/api/articles/{article_id}/document.pdf')
    def candidate_document_pdf(article_id: int):
        with connect(path) as db:
            get_candidate(db, article_id)
            row = db.execute('SELECT pdf FROM article_documents WHERE article_id=?', (article_id,)).fetchone()
        if row is None: raise HTTPException(404, 'Este candidato todavía no tiene un PDF guardado.')
        return Response(content=row['pdf'], media_type='application/pdf', headers={'Content-Disposition': 'inline; filename="articulo.pdf"'})

    @app.post('/api/articles/{article_id}/document/from-openalex')
    def fetch_candidate_document(article_id: int):
        with connect(path) as db:
            article = dict(get_candidate(db, article_id))
        try:
            urls = openalex_pdf_urls(article['doi'])
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        last_error = None
        for url in urls[:5]:
            try:
                content, final_url = download_pdf(url)
                return save_document(article_id, content, 'OpenAlex', final_url)
            except (ValueError, HTTPException) as error:
                last_error = error
        raise HTTPException(422, 'No se pudo leer ninguna de las versiones PDF abiertas registradas. Comprueba la fuente o adjunta el PDF manualmente.') from last_error

    @app.post('/api/articles/{article_id}/document/upload')
    async def upload_candidate_document(article_id: int, file: UploadFile = File(...)):
        with connect(path) as db: get_candidate(db, article_id)
        content = await file.read(MAX_PDF_BYTES + 1)
        await file.close()
        if len(content) > MAX_PDF_BYTES: raise HTTPException(413, 'El PDF debe ocupar como máximo 8 MB.')
        return save_document(article_id, content, 'Investigador', filename=Path(file.filename or 'articulo.pdf').name)

    @app.get('/api/articles/{article_id}/document/llm-review')
    def latest_document_review(article_id: int):
        with connect(path) as db:
            article = get_candidate(db, article_id)
            review = get_review(db, article['review_id'])
            document = db.execute('SELECT sha256 FROM article_documents WHERE article_id=?', (article_id,)).fetchone()
            if document is None: return {'status': 'missing'}
            row = db.execute('''SELECT * FROM document_reviews WHERE article_id=?
                AND protocol_version=? AND document_sha256=? ORDER BY id DESC LIMIT 1''',
                (article_id, review['protocol_version'], document['sha256'])).fetchone()
        return {'status': 'ready', 'created_at': row['created_at'], **json.loads(row['result_json'])} if row else {'status': 'missing'}

    @app.post('/api/articles/{article_id}/document/passages')
    def preview_passages(article_id: int, payload: LLMReviewInput):
        with connect(path) as db:
            article = get_candidate(db, article_id)
            review = get_review(db, article['review_id'])
            document = db.execute('SELECT * FROM article_documents WHERE article_id=?', (article_id,)).fetchone()
        if not document or document['truncated']:
            raise HTTPException(422, 'Adjunta un PDF con extracción completa.')
        try:
            criteria = criteria_for(review)
            if payload.criterion_index is None or payload.criterion_index >= len(criteria):
                raise ValueError('Selecciona un criterio válido.')
            return retrieve_passages(json.loads(document['pages_json']), [criteria[payload.criterion_index]], document['sha256'], path, payload.retrieval)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/articles/{article_id}/document/llm-review')
    def create_document_review(article_id: int, payload: LLMReviewInput = LLMReviewInput()):
        with connect(path) as db:
            article = dict(get_candidate(db, article_id))
            review = get_review(db, article['review_id'])
            document = db.execute('SELECT sha256,pages_json,truncated FROM article_documents WHERE article_id=?', (article_id,)).fetchone()
        if document is None: raise HTTPException(422, 'Busca o adjunta primero el PDF de este candidato.')
        if document['truncated']:
            raise HTTPException(422, 'La extracción del PDF quedó incompleta. Revisa el archivo antes de usar el LLM.')
        try:
            pages = json.loads(document['pages_json'])
            context = None
            if payload.retrieval != 'legacy':
                chosen = criteria_for(review)
                if payload.provider == 'groq':
                    if payload.criterion_index is None or payload.criterion_index >= len(chosen):
                        raise ValueError('Selecciona un criterio válido.')
                    chosen = [chosen[payload.criterion_index]]
                context = retrieve_passages(pages, chosen, document['sha256'], path, payload.retrieval)
                if not context['passages']:
                    raise ValueError('No se hallaron pasajes del estudio principal para este criterio. Revisa el PDF manualmente; no se consultó el LLM.')
            options = {'context': context} if context else {}
            if payload.provider == 'groq':
                result = generate_groq_review(review, article, pages, document['sha256'], payload.criterion_index, **options)
            else:
                generator = generate_cloud_review if payload.provider == 'cloud' else generate_local_review
                result = generator(review, article, pages, document['sha256'], **options)
            if context:
                result['retrieval'] = context['retrieval']
                for item in result['criteria']:
                    item.update(retrieval=context['retrieval'], selected_passages=context['passages'], generated_at=datetime.now(timezone.utc).isoformat())
        except ValueError as error:
            if hasattr(error, 'retry_after_seconds'):
                raise HTTPException(429, {'message': str(error), 'retry_after_seconds': error.retry_after_seconds}) from None
            raise HTTPException(422, str(error)) from None
        with connect(path) as db:
            get_candidate(db, article_id)
            current = get_review(db, article['review_id'])
            current_document = db.execute('SELECT sha256 FROM article_documents WHERE article_id=?', (article_id,)).fetchone()
            if current['protocol_version'] != review['protocol_version'] or not current_document or current_document['sha256'] != document['sha256']:
                raise HTTPException(409, 'El protocolo o PDF cambió durante el análisis. Vuelve a ejecutarlo.')
            if payload.provider == 'groq':
                all_criteria = criteria_for(review)
                previous = db.execute('''SELECT result_json FROM document_reviews WHERE article_id=?
                    AND protocol_version=? AND document_sha256=? AND model=? ORDER BY id DESC LIMIT 1''',
                    (article_id, review['protocol_version'], document['sha256'], GROQ_MODEL)).fetchone()
                old = json.loads(previous['result_json']) if previous else {}
                old_items = old.get('criteria') or []
                current_items = []
                for index, criterion in enumerate(all_criteria):
                    fallback = {'criterion': criterion['text'], 'kind': criterion['kind'],
                                'assessment': 'incierto', 'page': None, 'quote': '',
                                'explanation': 'Este criterio aún no se ha analizado con Groq.',
                                'quote_verified': False, 'analyzed': False}
                    prior = old_items[index] if index < len(old_items) else None
                    if prior and prior.get('criterion') == criterion['text'] and prior.get('kind') == criterion['kind']:
                        fallback = prior
                    current_items.append(fallback)
                selected_item = result['criteria'][0]
                current_items[payload.criterion_index] = {**selected_item, 'analyzed': True}
                result['criteria'] = current_items
                result['completed_criteria'] = sum(item.get('analyzed') for item in current_items)
                result['passages_examined'] += old.get('passages_examined', 0)
                result['usage'] = {name: result['usage'].get(name, 0) + (old.get('usage') or {}).get(name, 0)
                                   for name in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
            db.execute('INSERT INTO document_reviews (article_id,protocol_version,document_sha256,model,result_json) VALUES (?,?,?,?,?)',
                       (article_id, review['protocol_version'], document['sha256'], result['model'], json.dumps(result, ensure_ascii=False)))
            event(db, article['review_id'], 'llm_pdf_review_created',
                  {'article_id': article_id, 'provider': payload.provider, 'model': result['model'], 'protocol_version': review['protocol_version'],
                   'document_sha256': document['sha256'], 'criterion_index': payload.criterion_index if payload.provider == 'groq' else None,
                   'verified_quotes': sum(item['quote_verified'] for item in result['criteria'])})
        return {'status': 'ready', **result}

    @app.post('/api/reviews/{review_id}/articles',status_code=201)
    def add_article(review_id:int,payload:ArticleInput):
        with connect(path) as db:
            get_review(db,review_id)
            added = add_articles(db,review_id,[payload.model_dump()],'Manual')
            event(db,review_id,'manual_import',{'added':added,'duplicates':1-added})
        return {'added':added,'duplicates':1-added}

    @app.post('/api/reviews/{review_id}/import')
    async def import_articles(review_id:int,file:UploadFile=File(...)):
        content = await file.read(4*1024*1024+1)
        await file.close()
        if len(content)>4*1024*1024: raise HTTPException(413,'El archivo debe ocupar como máximo 4 MB.')
        try:
            text=content.decode('utf-8-sig')
            raw=json.loads(text) if (file.filename or '').lower().endswith('.json') else list(csv.DictReader(io.StringIO(text)))
            if not isinstance(raw,list) or not 1<=len(raw)<=500: raise ValueError()
            normalized=[]
            for row in raw:
                if row.get('year') == '': row['year']=None
                if row.get('is_oa') == '': row['is_oa']=False
                normalized.append(ArticleInput.model_validate(row).model_dump())
        except Exception:
            raise HTTPException(422,'Usa JSON (lista) o CSV UTF-8 con title, abstract, doi, year, authors, url e is_oa. El título es obligatorio; máximo 500 registros.') from None
        with connect(path) as db:
            get_review(db,review_id)
            added=add_articles(db,review_id,normalized,'Archivo importado')
            event(db,review_id,'file_import',{'added':added,'duplicates':len(raw)-added,'sha256':hashlib.sha256(content).hexdigest()})
        return {'added':added,'duplicates':len(raw)-added}

    @app.post('/api/reviews/{review_id}/search')
    def search(review_id:int,payload:SearchInput):
        if payload.year_from>payload.year_to: raise HTTPException(422,'El año inicial debe ser menor o igual al final.')
        with connect(path) as db:
            get_review(db,review_id)
            base_row=db.execute('SELECT snapshot,confirmed FROM published_bases WHERE review_id=?',(review_id,)).fetchone()
        if payload.date_from and not payload.year_from<=payload.date_from.year<=payload.year_to:
            raise HTTPException(422,'Revisa el rango de fechas de la búsqueda.')
        if payload.date_to and not payload.year_from<=payload.date_to.year<=payload.year_to:
            raise HTTPException(422,'Revisa el rango de fechas de la búsqueda.')
        if payload.date_to and payload.date_to>date.today():
            raise HTTPException(422,'La fecha final no puede ser posterior a hoy.')
        first_date=payload.date_from or date(payload.year_from,1,1)
        last_date=min(payload.date_to or date.today(),date(payload.year_to,12,31),date.today())
        if base_row:
            if not base_row['confirmed']: raise HTTPException(422,'Confirma primero el método del estudio base.')
            cutoff=date.fromisoformat(json.loads(base_row['snapshot'])['last_included_date'])+timedelta(days=1)
            first_date=max(first_date,cutoff)
        if first_date>last_date: raise HTTPException(422,'La fecha final debe ser posterior al inicio de la actualización.')
        source_name='OpenAlex' if payload.source=='openalex' else 'DOAJ'
        search_source=search_openalex if payload.source=='openalex' else search_doaj
        try: records,total=search_source(payload.query,payload.year_from,last_date.year,payload.limit,first_date,last_date)
        except SourceLimitError as error:
            with connect(path) as db: event(db,review_id,'search_failed',{'request':payload.model_dump(mode='json'),'source':source_name,'reason':'rate_limit'})
            raise HTTPException(429,str(error),headers={'Retry-After':str(error.retry_after)} if error.retry_after is not None else None) from None
        except ValueError as error:
            with connect(path) as db: event(db,review_id,'search_failed',{'request':payload.model_dump(mode='json'),'source':source_name,'reason':'source_error'})
            raise HTTPException(502,str(error)) from None
        with connect(path) as db:
            base=json.loads(base_row['snapshot']) if base_row else None
            candidates=[row for row in records if not(base and is_base_publication(row,base))]
            base_skipped=len(records)-len(candidates)
            added=add_articles(db,review_id,candidates,source_name)
            uncertain=sum(bool(row.get('date_uncertain')) for row in candidates) if payload.source=='doaj' else 0
            result={'source':source_name,'query':payload.query,'date_from':first_date.isoformat(),'date_to':last_date.isoformat(),'year_to':last_date.year,'retrieved':len(records),'added':added,'duplicates':len(candidates)-added,'base_skipped':base_skipped,'total_available':total,'limit':payload.limit,'exhaustive':False,'date_uncertain_count':uncertain}
            event(db,review_id,'search_completed',result)
        return result

    @app.put('/api/articles/{article_id}/decision')
    def decision(article_id:int,payload:DecisionInput):
        with connect(path) as db:
            previous=db.execute('SELECT * FROM articles WHERE id=?',(article_id,)).fetchone()
            if previous is None: raise HTTPException(404,'Artículo no encontrado.')
            protocol=get_review(db,previous['review_id'])
            db.execute('UPDATE articles SET decision=?,reason=?,decision_version=? WHERE id=?',(payload.decision,payload.reason,protocol['protocol_version'],article_id))
            event(db,previous['review_id'],'human_decision',{'article_id':article_id,'previous_decision':previous['decision'],'previous_reason':previous['reason'],**payload.model_dump(),'protocol_version':protocol['protocol_version']})
            return article_json(db.execute('SELECT * FROM articles WHERE id=?',(article_id,)).fetchone())

    def run_analysis(job_id,review_id,engine):
        try:
            with connect(path) as db:
                review=get_review(db,review_id)
                base=base_snapshot(db,review_id)
                articles=[dict(row) for row in db.execute('SELECT * FROM articles WHERE review_id=? ORDER BY id',(review_id,))]
                if base: articles=[article for article in articles if not is_base_publication(article,base)]
                for article in articles:
                    if article['decision_version'] != review['protocol_version']:
                        article['decision']='pending'
            output=analyze(review,articles,engine)
            with connect(path) as db:
                if get_review(db,review_id)['protocol_version']!=review['protocol_version']: raise ValueError('El protocolo cambió durante el análisis. Vuelve a ejecutarlo.')
                for item in output:
                    db.execute('UPDATE articles SET score=?,analysis=?,analyzed_version=? WHERE id=?',(item['score'],json.dumps(item['analysis'],ensure_ascii=False),review['protocol_version'],item['id']))
                event(db,review_id,'analysis_completed',{'engine':engine,'model':output[0]['analysis']['model'],'articles':len(output),'protocol_version':review['protocol_version']})
                db.execute("UPDATE jobs SET status='completed' WHERE id=?",(job_id,))
        except Exception as error:
            message=str(error) if isinstance(error,ValueError) else 'El análisis falló. Comprueba las dependencias y vuelve a intentarlo.'
            with connect(path) as db: db.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(message,job_id))

    @app.post('/api/reviews/{review_id}/analyze',status_code=202)
    def start_analysis(review_id:int,payload:AnalysisInput):
        with job_lock, connect(path) as db:
            get_review(db,review_id)
            base=base_snapshot(db,review_id)
            records=[dict(row) for row in db.execute('SELECT title,doi FROM articles WHERE review_id=?',(review_id,))]
            count=sum(not(base and is_base_publication(row,base)) for row in records)
            if not count: raise HTTPException(422,'Añade artículos antes de analizar.')
            if count>500: raise HTTPException(422,'Este prototipo analiza como máximo 500 artículos por revisión.')
            if db.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone(): raise HTTPException(409,'Ya hay un análisis en curso. Espera a que termine.')
            job_id=uuid.uuid4().hex
            db.execute('INSERT INTO jobs (id,review_id,status,engine) VALUES (?,?,?,?)',(job_id,review_id,'running',payload.engine))
        executor.submit(run_analysis,job_id,review_id,payload.engine)
        return {'id':job_id,'status':'running'}

    @app.get('/api/jobs/{job_id}')
    def job(job_id:str):
        with connect(path) as db: row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None: raise HTTPException(404,'Análisis no encontrado.')
        return dict(row)

    @app.post('/api/reviews/{review_id}/evaluate')
    def evaluation(review_id:int,payload:AnalysisInput):
        with connect(path) as db:
            review=get_review(db,review_id)
            base=base_snapshot(db,review_id)
            rows=[dict(row) for row in db.execute('SELECT * FROM articles WHERE review_id=? AND decision_version=? ORDER BY id',(review_id,review['protocol_version']))]
            if base: rows=[row for row in rows if not is_base_publication(row,base)]
        try:
            result=evaluate(rows,payload.engine)
        except ValueError as error:
            raise HTTPException(422,str(error)) from None
        with connect(path) as db: event(db,review_id,'exploratory_evaluation',result)
        return result

    @app.get('/api/reviews/{review_id}/history')
    def history(review_id:int):
        with connect(path) as db:
            get_review(db,review_id)
            return [{**dict(row),'payload':json.loads(row['payload'])} for row in db.execute('SELECT * FROM events WHERE review_id=? ORDER BY id DESC',(review_id,))]

    @app.post('/api/reviews/{review_id}/reports',status_code=201)
    def create_report(review_id:int):
        from .report_evidence import snapshot_document_evidence
        with connect(path) as db:
            review=get_review(db,review_id)
            published_row=db.execute('SELECT snapshot,confirmed FROM published_bases WHERE review_id=?',(review_id,)).fetchone()
            if published_row and not published_row['confirmed']:
                raise HTTPException(422,'Confirma el método del estudio base antes de generar un reporte.')
            base=json.loads(published_row['snapshot']) if published_row else None
            all_articles=[article_json(row) for row in db.execute('SELECT * FROM articles WHERE review_id=? ORDER BY id',(review_id,))]
            legacy_base_records=[article for article in all_articles if base and is_base_publication(article,base)]
            articles=[article for article in all_articles if article not in legacy_base_records]
            if not articles: raise HTTPException(422,'Añade artículos antes de generar el reporte.')
            for article in articles:
                article['document_evidence'] = snapshot_document_evidence(db, article['id'], review['protocol_version'])
            history=[{**dict(row),'payload':json.loads(row['payload'])} for row in db.execute('SELECT * FROM events WHERE review_id=? ORDER BY id',(review_id,))]
            review.pop('base_text',None)
            published_base={**json.loads(published_row['snapshot']),'confirmed':bool(published_row['confirmed'])} if published_row else None
            snapshot={'schema_version':4,'created_at':datetime.now(timezone.utc).isoformat(),'review':review,'published_base':published_base,'articles':articles,'legacy_base_records':legacy_base_records,'history':history,'counts':{state:sum(a['decision']==state for a in articles) for state in ['included','excluded','pending']},'limitations':['Reporte estructurado, no metaanálisis ni nueva síntesis narrativa.','La búsqueda limitada no garantiza cobertura exhaustiva.','Las recomendaciones de modelos requieren validación humana.','Los puntajes de similitud no son probabilidades de inclusión.','Las propuestas del PDF son sugerencias de IA separadas de las decisiones humanas; una cita presente no valida su interpretación.','Esta versión conserva procedencia, pasajes y propuestas; no incluye los archivos PDF originales.']}
            snapshot['decisions_needing_recheck']=[a['id'] for a in articles if a['decision']!='pending' and a['decision_version']!=review['protocol_version']]
            snapshot['status']='draft' if snapshot['counts']['pending'] or snapshot['decisions_needing_recheck'] else 'screened'
            serialized=json.dumps(snapshot,ensure_ascii=False,sort_keys=True)
            digest=hashlib.sha256(serialized.encode()).hexdigest()
            version=db.execute('SELECT coalesce(max(version),0)+1 FROM reports WHERE review_id=?',(review_id,)).fetchone()[0]
            cursor=db.execute('INSERT INTO reports (review_id,version,snapshot,sha256) VALUES (?,?,?,?)',(review_id,version,serialized,digest))
            event(db,review_id,'report_created',{'version':version,'sha256':digest})
            return {'id':cursor.lastrowid,'version':version,'sha256':digest}

    @app.get('/api/reviews/{review_id}/reports')
    def reports(review_id:int):
        with connect(path) as db:
            get_review(db,review_id)
            rows=db.execute('SELECT id,version,sha256,created_at,snapshot FROM reports WHERE review_id=? ORDER BY version DESC',(review_id,)).fetchall()
            result=[]
            for row in rows:
                item={key:row[key] for key in ('id','version','sha256','created_at')}
                data=json.loads(row['snapshot'])
                item['status']=data.get('status') or ('draft' if data.get('counts',{}).get('pending') or data.get('decisions_needing_recheck') else 'screened')
                result.append(item)
            return result

    @app.get('/api/reports/{report_id}.json')
    def report_download(report_id:int):
        with connect(path) as db: row=db.execute('SELECT * FROM reports WHERE id=?',(report_id,)).fetchone()
        if row is None: raise HTTPException(404,'Reporte no encontrado.')
        filename='semantik-revision-{}-v{}.json'.format(row['review_id'],row['version'])
        return Response(row['snapshot'],media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{filename}"'})

    @app.get('/api/reports/{report_id}.html')
    def readable_report(report_id:int):
        from .report_evidence import render_document_evidence
        with connect(path) as db: row=db.execute('SELECT * FROM reports WHERE id=?',(report_id,)).fetchone()
        if row is None: raise HTTPException(404,'Reporte no encontrado.')
        data=json.loads(row['snapshot']); review=data['review']
        escape=lambda value: html.escape(str(value if value is not None else ''))
        names={'included':'Incluido','excluded':'Excluido','pending':'Pendiente'}
        rows=''.join('<tr>'+''.join('<td>'+escape(value)+'</td>' for value in [a['title'],a['year'],a['doi'],a['source'],names[a['decision']],a['reason']])+'</tr>' for a in data['articles'])
        base=data.get('published_base')
        base_section=''
        if base:
            categories=''.join('<li>'+escape(item['name'])+': '+escape(item['count'])+'</li>' for item in base['application_counts'])
            base_section=f'''<h2>Estudio original publicado</h2><p>DOI: {escape(base['doi'])}. Estudios incluidos en la publicación: {escape(base['original_count'])}. Método confirmado en esta aplicación: {"sí" if base['confirmed'] else "no"}.</p><p>Las categorías originales de la tabla 2 son:</p><ul>{categories}</ul><p>Los estudios originales están separados de los candidatos nuevos. {len(data.get('legacy_base_records',[]))} registro(s) histórico(s) de la propia revisión base se conservan en el JSON y se excluyen del recuento de candidatos. Las búsquedas en DOAJ y OpenAlex no reproducen la estrategia de las cuatro bases originales.</p>'''
        document=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Reporte v{row['version']}</title>
        <style>body{{font:15px/1.65 Arial,sans-serif;color:#34313d;background:white;margin:40px;max-width:1100px}}h1,h2{{color:#5f4778}}table{{width:100%;border-collapse:collapse;font-size:12px}}td,th{{padding:9px;border:1px solid #e4e2eb;text-align:left;overflow-wrap:anywhere}}th{{background:#f5f2f8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}small{{overflow-wrap:anywhere}}.pdf-evidence{{margin:32px 0;overflow-wrap:anywhere}}.criterion-evidence{{border-top:1px solid #e4e2eb;padding:12px 0}}blockquote{{font-family:Georgia,serif;border-left:3px solid #7251a2;padding-left:16px;margin-left:0;max-width:75ch}}@media print{{body{{margin:15px}}tr,.criterion-evidence{{break-inside:avoid}}}}@media(max-width:600px){{body{{margin:16px}}}}</style>
        <h1>{escape(review['title'])}</h1><p>Reporte de actualización v{row['version']} · {escape(data['created_at'])}</p><p><strong>{'Borrador de cribado: quedan artículos pendientes o decisiones por revisar.' if data.get('status')=='draft' else 'Cribado registrado: verifica la cobertura antes de usar este reporte como síntesis final.'}</strong></p>
        {base_section}<h2>Protocolo v{review['protocol_version']}</h2><p>{escape(review['question'])}</p>
        <p>Revisión base: {escape(review['base_reference'])}</p><h3>Inclusión</h3><pre>{escape(review['inclusion'])}</pre><h3>Exclusión</h3><pre>{escape(review['exclusion'])}</pre>
        <h2>Registro de evidencia</h2><p>Incluidos: {data['counts']['included']} · Excluidos: {data['counts']['excluded']} · Pendientes: {data['counts']['pending']}</p>
        <p>Decisiones que necesitan revisión por cambio de protocolo: {len(data.get('decisions_needing_recheck',[]))}</p>
        <table><thead><tr><th>Título</th><th>Año</th><th>DOI</th><th>Fuente</th><th>Decisión</th><th>Motivo</th></tr></thead><tbody>{rows}</tbody></table>
        {render_document_evidence(data['articles'])}
        <h2>Alcance y limitaciones</h2><ul>{''.join('<li>'+escape(v)+'</li>' for v in data['limitations'])}</ul>
        <h2>Trazabilidad</h2><small>SHA-256 del reporte JSON: {escape(row['sha256'])}</small><pre>{escape(json.dumps(data['history'],ensure_ascii=False,indent=2))}</pre></html>'''
        return Response(document,media_type='text/html',headers={'Content-Disposition':f'attachment; filename="semantik-reporte-v{row["version"]}.html"'})

    @app.get('/api/reviews/{review_id}/export.csv')
    def export_csv(review_id:int):
        with connect(path) as db:
            get_review(db,review_id)
            base=base_snapshot(db,review_id)
            records=[dict(row) for row in db.execute('SELECT title,doi,year,authors,source,decision,reason,score FROM articles WHERE review_id=? ORDER BY id',(review_id,))]
            if base: records=[row for row in records if not is_base_publication(row,base)]
        fields=['title','doi','year','authors','source','decision','reason','score']
        output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader()
        for record in records:
            writer.writerow({key:("'"+str(value) if str(value).lstrip().startswith(('=','+','-','@')) else value) for key,value in record.items()})
        return Response('\ufeff'+output.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="revision-{review_id}-articulos.csv"'})

    if (FRONTEND_BUILD/'assets').exists(): app.mount('/assets',StaticFiles(directory=FRONTEND_BUILD/'assets'),name='assets')
    @app.get('/')
    @app.get('/reviews/new')
    @app.get('/reviews/{review_id}')
    def frontend():
        if not (FRONTEND_BUILD/'index.html').exists(): raise HTTPException(503,'Compila el frontend con npm run build.')
        return FileResponse(FRONTEND_BUILD/'index.html',headers={'Cache-Control':'no-cache'})
    return app

app=create_app()
