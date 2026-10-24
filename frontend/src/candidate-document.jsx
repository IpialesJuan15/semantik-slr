import React, {useEffect,useState} from 'react'
import {api} from './api.js'

export function CandidateDocument({articleId,onSaved}){
 const [document,setDocument]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('')
 useEffect(()=>{let active=true;setDocument(null);setError('');api(`/articles/${articleId}/document`).then(value=>{if(active)setDocument(value)}).catch(reason=>{if(active)setError(reason.message)});return()=>{active=false}},[articleId])
 async function run(request){
  setWorking(true);setError('')
  try{const result=await request();setDocument(result);await onSaved?.()}
  catch(reason){setError(reason.message)}
  finally{setWorking(false)}
 }
 async function upload(event){
  const input=event.target
  if(!input.files[0])return
  const body=new FormData();body.append('file',input.files[0])
  await run(()=>api(`/articles/${articleId}/document/upload`,{method:'POST',body}))
  input.value=''
 }
 return <section className="candidate-document" aria-label="Texto completo del candidato">
  <div className="document-heading"><div><h4>Texto completo</h4><p>Comprueba qué páginas pudo leer el sistema antes de usar una sugerencia de IA.</p></div>{document?.status==='read'&&<span className="document-state">PDF leído</span>}</div>
  {!document&&<p>Comprobando si ya hay un PDF guardado…</p>}
  {document?.status==='missing'&&<p>Todavía no se ha leído el PDF de este candidato. El análisis actual utiliza solo título y resumen.</p>}
  {document?.status==='read'&&<>
   <p><strong>{document.page_count} páginas · {document.characters.toLocaleString('es-EC')} caracteres extraídos.</strong> Procedencia: {document.source_type==='OpenAlex'?'enlace abierto registrado por OpenAlex':'PDF adjuntado por el investigador'}.</p>
   {document.truncated&&<p className="document-warning">El texto superó el límite de extracción; no se procesó completo.</p>}
   <p className="document-warning">Comprueba que el título y el DOI del PDF correspondan a este artículo. El modelo semántico actual aún no usa este texto; el LLM se añadirá en la siguiente fase.</p>
   <div className="button-row"><a className="button" href={`/api/articles/${articleId}/document.pdf`} target="_blank" rel="noreferrer">Abrir PDF guardado</a>{document.source_url&&<a href={document.source_url} target="_blank" rel="noreferrer">Ver origen del PDF</a>}</div>
   <details className="document-pages"><summary>Ver fragmentos extraídos por página</summary>{document.page_previews.map(page=><div key={page.page}><strong>Página {page.page}</strong><p>{page.text}</p></div>)}{document.page_count>document.page_previews.length&&<p>Se muestra una vista previa; el texto completo de las páginas leídas queda guardado para el análisis posterior.</p>}</details>
  </>}
  <div className="button-row document-actions"><button type="button" disabled={working||!document} onClick={()=>run(()=>api(`/articles/${articleId}/document/from-openalex`,{method:'POST'}))}>{working?'Procesando…':document?.status==='read'?'Buscar otra versión abierta':'Buscar PDF abierto por DOI'}</button><label className="file-button">{working?'Procesando…':'Adjuntar PDF'}<input type="file" accept=".pdf,application/pdf" disabled={working} onChange={upload}/></label></div>
  <p className="fine-print">Máximo 8 MB y 80 páginas, con texto seleccionable. La búsqueda automática puede fallar aunque el artículo sea de acceso abierto; en ese caso, comprueba la fuente y adjunta el PDF.</p>
  {error&&<p className="error" role="alert">{error}</p>}
 </section>
}
