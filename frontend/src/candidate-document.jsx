import React, {useEffect,useState} from 'react'
import {api} from './api.js'

export function CandidateDocument({articleId,onSaved,review}){
 const [document,setDocument]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('')
 const [suggestion,setSuggestion]=useState(null),[thinking,setThinking]=useState(false),[llmError,setLlmError]=useState('')
 const [provider,setProvider]=useState('groq'),[cloudReady,setCloudReady]=useState(null),[groqReady,setGroqReady]=useState(null),[criterionIndex,setCriterionIndex]=useState(0)
 const criteria=[['inclusion',review.inclusion],['exclusion',review.exclusion]].flatMap(([kind,value])=>String(value||'').split('\n').map(line=>line.replace(/^[\s\-•]+/,'').trim()).filter(Boolean).map(text=>({kind,text})))
 useEffect(()=>{let active=true;setDocument(null);setSuggestion(null);setError('');setLlmError('');Promise.all([api(`/articles/${articleId}/document`),api(`/articles/${articleId}/document/llm-review`)]).then(([value,saved])=>{if(active){setDocument(value);setSuggestion(saved);if(saved.status==='ready')setProvider(saved.provider||'local')}}).catch(reason=>{if(active)setError(reason.message)});api('/status').then(value=>{if(active){setCloudReady(value.cloud_llm_configured);setGroqReady(value.groq_key_configured)}}).catch(()=>{});return()=>{active=false}},[articleId])
 async function run(request){
  setWorking(true);setError('')
  try{const result=await request();setDocument(result);setSuggestion({status:'missing'});await onSaved?.()}
  catch(reason){setError(reason.message)}
  finally{setWorking(false)}
 }
 async function reviewPdf(){
  setThinking(true);setLlmError('')
  try{const result=await api(`/articles/${articleId}/document/llm-review`,{method:'POST',body:provider==='groq'?{provider,criterion_index:criterionIndex}:{provider}});setSuggestion(result);if(provider==='groq'){const next=result.criteria.findIndex(item=>!item.analyzed);if(next>=0)setCriterionIndex(next)}await onSaved?.()}
  catch(reason){setLlmError(reason.message)}
  finally{setThinking(false)}
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
   <p className="document-warning">Comprueba que el título y el DOI del PDF correspondan a este artículo. El modelo semántico actual solo analiza título y resumen; el asistente de abajo examina pasajes del PDF por separado.</p>
   <div className="button-row"><a className="button" href={`/api/articles/${articleId}/document.pdf`} target="_blank" rel="noreferrer">Abrir PDF guardado</a>{document.source_url&&<a href={document.source_url} target="_blank" rel="noreferrer">Ver origen del PDF</a>}</div>
   <details className="document-pages"><summary>Ver fragmentos extraídos por página</summary>{document.page_previews.map(page=><div key={page.page}><strong>Página {page.page}</strong><p>{page.text}</p></div>)}{document.page_count>document.page_previews.length&&<p>Se muestra una vista previa; el texto completo de las páginas leídas queda guardado para el análisis posterior.</p>}</details>
   <div className="local-review">
    <h5>Asistente de lectura del PDF</h5>
    <p>El LLM propone una explicación por criterio a partir de pasajes seleccionados de todas las páginas. Comprueba cada cita y su interpretación antes de decidir.</p>
    <label className="field llm-provider"><span>Dónde procesar los pasajes</span>
     <select value={provider} disabled={thinking} onChange={event=>setProvider(event.target.value)}>
      <option value="groq">Groq · qwen/qwen3.8-27b</option>
      <option value="cloud">OpenAI en la nube · gpt-4.1-mini</option>
      <option value="local">Ollama en mi equipo · qwen2.5:3b</option>
     </select>
    </label>
    {provider==='groq'?<>
     <p className="llm-provider-note">Groq recibe título, DOI, el criterio elegido y pasajes con sus páginas. El PDF completo no se envía. El plan gratuito tiene límites: analizaremos un criterio por solicitud.{groqReady===false?' Falta configurar SEMANTIK_GROQ_API_KEY en el servidor.':''}</p>
     <label className="field llm-provider"><span>Criterio a revisar</span>
      <select value={criterionIndex} disabled={thinking} onChange={event=>setCriterionIndex(Number(event.target.value))}>
       {criteria.map((item,index)=><option key={index} value={index}>{(item.kind==='inclusion'?'Inclusión ':'Exclusión ')+(index+1)+': '+item.text}</option>)}
      </select>
     </label>
    </>:provider==='cloud'?<p className="llm-provider-note">Se enviarán título, DOI, criterios y hasta 12 pasajes con sus páginas a OpenAI; el PDF completo no se envía. La API puede generar costos.{cloudReady===false?' Falta configurar SEMANTIK_OPENAI_API_KEY en el servidor.':''}</p>:<p className="llm-provider-note">Ollama procesa los pasajes en tu equipo. Debes instalar qwen2.5:3b; en 8 GB puede tardar varios minutos.</p>}
    <button type="button" disabled={thinking||working||document.truncated||(provider==='groq'&&!criteria.length)} onClick={reviewPdf}>
     {thinking?'Leyendo pasajes del PDF…':provider==='groq'?'Analizar este criterio con Groq':suggestion?.status==='ready'&&(suggestion.provider||'local')===provider?'Volver a generar propuestas':provider==='cloud'?'Generar con OpenAI':'Generar con Ollama'}
    </button>
    {thinking&&<p role="status">Mantén abierta esta página mientras termina la propuesta.</p>}
    {llmError&&<p className="error" role="alert">{llmError}</p>}
    {suggestion?.status==='ready'&&<div className="local-review-results">
     <p><strong>{suggestion.model}</strong> · {suggestion.provider==='groq'?'Groq':suggestion.provider==='cloud'?'Nube':'Local'} · {suggestion.passages_examined} pasajes consultados · Protocolo v{suggestion.protocol_version}</p>
     {suggestion.provider==='groq'&&<p>{suggestion.completed_criteria||1} de {suggestion.criteria.length} criterios consultados con Groq. Para otro criterio, selecciónalo arriba y vuelve a pulsar el botón.</p>}
     {suggestion.usage?.total_tokens>0&&<p>Consumo informado por la API: {suggestion.usage.total_tokens.toLocaleString('es-EC')} tokens.</p>}
     <p>«Apoya» sugiere que se cumple ese criterio; «contradice» sugiere que no. Ninguno equivale a una decisión automática.</p>
     <p className="document-warning">{suggestion.warning}</p>
     {suggestion.criteria.map((item,index)=><div className="local-criterion" key={index}>
      <strong>{item.kind==='inclusion'?'Inclusión':'Exclusión'}: {item.criterion}</strong>
      {item.analyzed===false?<p>Aún no se analizó este criterio con Groq.</p>:<><p>Propuesta: <b>{item.assessment}</b></p>{item.quote_verified?<><blockquote>{item.quote}</blockquote><small>Texto localizado en la página {item.page}. Comprueba su sentido en el PDF.</small><p>{item.explanation}</p></>:<p>Sin cita comprobable para este criterio. Revisa el PDF manualmente.</p>}</>}
     </div>)}
    </div>}
   </div>
  </>}
  <div className="button-row document-actions"><button type="button" disabled={working||!document} onClick={()=>run(()=>api(`/articles/${articleId}/document/from-openalex`,{method:'POST'}))}>{working?'Procesando…':document?.status==='read'?'Buscar otra versión abierta':'Buscar PDF abierto por DOI'}</button><label className="file-button">{working?'Procesando…':'Adjuntar PDF'}<input type="file" accept=".pdf,application/pdf" disabled={working} onChange={upload}/></label></div>
  <p className="fine-print">Máximo 8 MB y 80 páginas, con texto seleccionable. La búsqueda automática puede fallar aunque el artículo sea de acceso abierto; en ese caso, comprueba la fuente y adjunta el PDF.</p>
  {error&&<p className="error" role="alert">{error}</p>}
 </section>
}
