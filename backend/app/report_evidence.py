"""Freeze PDF/LLM provenance in reports without copying PDF binaries."""

import html
import json


def snapshot_document_evidence(db, article_id, protocol_version):
    document = db.execute('''SELECT sha256, source_type, source_url, filename,
        page_count, characters, truncated, created_at FROM article_documents
        WHERE article_id=?''', (article_id,)).fetchone()
    if document is None:
        return None
    metadata = dict(document)
    metadata['truncated'] = bool(metadata['truncated'])
    # The current PDF and protocol must both match. Old proposals remain in the
    # database, but must never be presented as evidence for today's protocol.
    proposal = db.execute('''SELECT result_json, created_at FROM document_reviews
        WHERE article_id=? AND protocol_version=? AND document_sha256=?
        ORDER BY id DESC LIMIT 1''', (article_id, protocol_version, metadata['sha256'])).fetchone()
    return {'document': metadata,
            'proposal': {**json.loads(proposal['result_json']), 'generated_at': proposal['created_at']}
            if proposal else None}


def render_document_evidence(articles):
    """Render only the frozen report contents, never the live article state."""
    records = [article for article in articles if article.get('document_evidence')]
    if not records:
        return ''
    escape = lambda value: html.escape(str(value if value is not None else ''))
    sections = ['<h2>Lectura asistida de los PDF</h2><p>Las propuestas de IA que siguen '
                'son independientes de las decisiones humanas de la tabla anterior. '
                'Una cita localizada en el PDF no demuestra que su interpretación sea correcta. '
                'Solo se incluyen propuestas del PDF y protocolo vigentes al generar esta versión.</p>']
    labels = {'apoya': 'Apoya el criterio', 'contradice': 'Contradice el criterio',
              'incierto': 'Evidencia insuficiente'}
    methods = {'semantic': 'Embeddings del PDF', 'lexical': 'Comparación de palabras',
               'legacy': 'Selección anterior por términos'}
    for article in records:
        evidence = article['document_evidence']
        document = evidence['document']
        proposal = evidence.get('proposal')
        sections.append(f'<section class="pdf-evidence"><h3>{escape(article["title"])}</h3>'
                        f'<p>PDF: {escape(document["page_count"])} páginas. '
                        f'Procedencia: {escape(document["source_type"])}. '
                        f'Extraído: {escape(document["created_at"])}.</p>'
                        f'<p>Origen registrado: {escape(document.get("source_url") or document.get("filename"))}</p>'
                        f'<small>SHA-256 del PDF: {escape(document["sha256"])}</small>')
        if document.get('truncated'):
            sections.append('<p>La extracción de este PDF quedó incompleta.</p>')
        if not proposal:
            sections.append('<p>Sin propuesta de IA vigente para este PDF y protocolo.</p></section>')
            continue
        sections.append(f'<p>Proveedor: {escape(proposal.get("provider", "local"))}. '
                        f'Modelo: {escape(proposal.get("model"))}. '
                        f'Protocolo v{escape(proposal.get("protocol_version"))}. '
                        f'Última solicitud guardada: {escape(proposal.get("generated_at"))}.</p>')
        retrieval = proposal.get('retrieval') or {}
        if retrieval:
            method = retrieval.get('method', 'legacy')
            sections.append('<p>Recuperación de pasajes en la última solicitud: ' + escape(methods.get(method, method)) +
                            '. Modelo: ' + escape(retrieval.get('model', '')) + '.</p>')
        sections.append(f'<p>Pasajes enviados, contando repeticiones entre consultas: '
                        f'{escape(proposal.get("passages_examined"))}. '
                        f'Tokens informados por la API: {escape((proposal.get("usage") or {}).get("total_tokens", "No informado"))}.</p>')
        for item in proposal.get('criteria', []):
            kind = 'Exclusión' if item.get('kind') == 'exclusion' else 'Inclusión'
            sections.append(f'<div class="criterion-evidence"><h4>{kind}: {escape(item.get("criterion"))}</h4>')
            if item.get('analyzed') is False:
                sections.append('<p>No consultado con este proveedor.</p></div>')
                continue
            item_retrieval = item.get('retrieval') or {}
            method = item_retrieval.get('method', 'legacy')
            sections.append('<p>Pasajes para este criterio: ' + escape(methods.get(method, method)) +
                            ('. Modelo: ' + escape(item_retrieval['model']) if item_retrieval.get('model') else '') + '.</p>')
            sections.append('<p>Propuesta de IA: <strong>' + escape(labels.get(item.get('assessment'), 'Evidencia insuficiente')) + '</strong>.</p>')
            if item.get('quote_verified'):
                sections.append(f'<blockquote>{escape(item.get("quote"))}</blockquote>'
                                f'<p>Página {escape(item.get("page"))}; coincidencia textual comprobada.</p>'
                                f'<p>{escape(item.get("explanation"))}</p>')
            else:
                sections.append('<p>Sin cita comprobable. Requiere lectura del investigador.</p>')
            facets = item.get('evidence_facets') or {}
            if facets:
                sections.append('<p>Evidencia localizada por partes: '
                                + ('lugar del estudio; ' if facets.get('setting_found') else 'lugar no localizado; ')
                                + ('herramienta de IA; ' if facets.get('ai_tool_found') else 'herramienta no localizada; ')
                                + ('técnica ML/DL/NLP mencionada en los pasajes.' if facets.get('technique_stated_in_passages')
                                   else 'técnica interna no identificada en los pasajes.') + '</p>')
                for passage in item.get('selected_passages') or []:
                    if passage.get('facet') in ('setting', 'ai_tool'):
                        label = 'Lugar y participantes' if passage['facet'] == 'setting' else 'Herramienta de IA'
                        sections.append('<p>' + label + ', página ' + escape(passage.get('page')) +
                                        ' (pasaje localizado, verificar interpretación):</p><blockquote>' +
                                        escape(passage.get('text')) + '</blockquote>')
            sections.append('</div>')
        sections.append('</section>')
    return ''.join(sections)
