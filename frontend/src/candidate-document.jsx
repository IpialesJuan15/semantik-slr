import React, {useEffect,useRef,useState} from 'react'
import {api} from './api.js'
import './pdf-assistant.css'

const cooldownKey='semantik-groq-retry-at'
const geminiModels=['gemini-3.8-flash','gemini-3.5-flash-lite']
function savedCooldown(){try{return Number(sessionStorage.getItem(cooldownKey))||0}catch{return 0}}
function providerName(value){return value==='gemini'?'Gemini':value==='groq'?'Groq':value==='cloud'?'OpenAI (histórico)':'Ollama'}
function describeAssessment(item){
 if(item.analyzed===false)return 'Sin consultar'
 if(item.evidence_status==='quote_unverified')return 'Cita no verificable'
 if(item.evidence_status==='insufficient_support')return 'La cita no basta para este criterio'
 if(item.assessment==='incierto'||!item.quote_verified)return 'Evidencia insuficiente o parcial'
 if(item.kind==='inclusion')return item.assessment==='apoya'?'Sugiere que cumple':'Sugiere que no cumple'
 return item.assessment==='apoya'?'Sugiere un motivo de exclusión':'No respalda este motivo de exclusión'
}
function facetName(facet){return ({setting:'Lugar y participantes',ai_tool:'Herramienta de IA',method:'Método del estudio',technique:'Técnica de IA'})[facet]||'Pasaje relacionado'}
function selectionName(retrieval){return retrieval?.method==='semantic'?'Búsqueda semántica en el PDF':retrieval?.method==='lexical'?'Búsqueda por términos en el PDF':'Selección de pasajes anterior'}
function PdfPageLink({articleId,page,children}){return <a href={`/api/articles/${articleId}/document.pdf#page=${page}`} target="_blank" rel="noreferrer">{children||`Ver página ${page} en el PDF`}</a>}
function evidenceFor(item){
 const evidence=Array.isArray(item.evidence)?item.evidence.filter(part=>part?.quote?.trim()&&Number.isInteger(part.page)&&part.page>0):[]
 if(evidence.length)return evidence
 return item.quote_verified&&item.quote?.trim()&&Number.isInteger(item.page)?[{page:item.page,quote:item.quote}]:[]
}
function explanationFor(item){
 if(item.evidence_status==='quote_unverified')return 'La cita propuesta no se encontró en el texto enviado. No se usa como evidencia para resolver este criterio.'
 if(item.explanation?.trim())return item.explanation
 return 'La información recuperada no permite resolver este criterio. Esto no equivale a excluir el artículo.'
}
function InlinePage({articleId,page,sha256}){
 const [open,setOpen]=useState(false),[content,setContent]=useState(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0)
 useEffect(()=>{
  if(!open)return
  let active=true
  setContent(null);setError('')
  api(`/articles/${articleId}/document/pages/${page}${sha256?`?sha256=${encodeURIComponent(sha256)}`:''}`).then(value=>{if(active)setContent(value)}).catch(reason=>{if(active)setError(reason.message)})
  return()=>{active=false}
 },[open,articleId,page,sha256,attempt])
 return <details className="pdf-inline-page" onToggle={event=>setOpen(event.currentTarget.open)}>
  <summary>Leer página {page} aquí</summary>
  {!content&&!error&&<p role="status">Cargando el texto guardado…</p>}
  {error&&<div role="alert"><p>{error}</p><button type="button" onClick={()=>setAttempt(value=>value+1)}>Volver a cargar la página</button></div>}
  {content&&<><p className="pdf-help">Texto extraído de la página {content.page}. Las tablas y columnas pueden perder su formato.</p><div className="pdf-full-page" role="region" aria-label={`Texto completo de la página ${page}`} tabIndex={0}>{content.text}</div></>}
 </details>
}
function EvidenceCard({part,index,articleId,sha256}){
 return <div className="pdf-evidence-card">
  <div className="pdf-evidence-heading"><strong>Cita {index+1}</strong><span>Página {part.page} · Texto localizado</span></div>
  <blockquote>{part.quote}</blockquote>
  {part.context?.trim()&&part.context.trim()!==part.quote.trim()&&<details className="pdf-inline-context"><summary>Leer el contexto aquí</summary><p>{part.context}</p></details>}
  <InlinePage articleId={articleId} page={part.page} sha256={sha256}/>
  <PdfPageLink articleId={articleId} page={part.page}/>
 </div>
}
function Proposal({item,index,selected,articleId,sha256}){
 const evidence=evidenceFor(item)
 const limitations=Array.isArray(item.limitations)?item.limitations.filter(value=>typeof value==='string'&&value.trim()):[]
 const uncertain=item.assessment==='incierto'||!item.quote_verified
 return <details className={`pdf-proposal ${selected?'selected-proposal':''}`} open={selected}>
  <summary><span>{item.kind==='inclusion'?'Inclusión':'Exclusión'} · {item.criterion}</span><b className={`pdf-verdict ${uncertain?'uncertain':''}`}>{describeAssessment(item)}</b></summary>
  {item.analyzed===false?<p className="pdf-help">Seleccionaste este criterio. Pulsa «Explicar este criterio» para consultarlo.</p>:<div className="pdf-proposal-body">
   <p className="pdf-explanation">{explanationFor(item)}</p>
   {limitations.length>0&&<div className="pdf-limitations"><strong>Qué falta aclarar</strong><ul>{limitations.map((value,i)=><li key={i}>{value}</li>)}</ul></div>}
   {evidence.length>0?<div className="pdf-checked-evidence"><h6>{evidence.length===1?'Evidencia en el artículo':`${evidence.length} citas del artículo`}</h6>{evidence.map((part,i)=><EvidenceCard key={`${index}-${i}`} part={part} index={i} articleId={articleId} sha256={sha256}/>)}</div>:<p className="pdf-no-evidence">No hay una cita comprobada para mostrar.</p>}
   {(item.evidence_validation_version||0)<3&&<p className="pdf-older-result">Respuesta de una versión anterior. Vuelve a consultar este criterio para obtener citas con contexto y una explicación actualizada.</p>}
  </div>}
 </details>
}

export function CandidateDocument({articleId,onSaved,review}){
 const [document,setDocument]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('')
 const [suggestion,setSuggestion]=useState(null),[thinking,setThinking]=useState(false),[llmError,setLlmError]=useState('')
 const [provider,setProvider]=useState('gemini'),[geminiReady,setGeminiReady]=useState(null),[groqReady,setGroqReady]=useState(null),[geminiModel,setGeminiModel]=useState('gemini-3.5-flash-lite')
 const [criterionIndex,setCriterionIndex]=useState(0),[retrieval,setRetrieval]=useState('semantic')
 const [preview,setPreview]=useState(null),[locating,setLocating]=useState(false),[previewError,setPreviewError]=useState('')
 const [retryAt,setRetryAt]=useState(savedCooldown),[now,setNow]=useState(Date.now)
 const scope=useRef(0)
 const criteria=[['inclusion',review.inclusion],['exclusion',review.exclusion]].flatMap(([kind,value])=>String(value||'').split('\n').map(line=>line.replace(/^[\s\-•]+/,'').trim()).filter(Boolean).map((text,index)=>({kind,text,number:index+1})))
 const occupied=working||thinking||locating
 const waitSeconds=Math.max(0,Math.ceil((retryAt-now)/1000))
 const canRead=document?.status==='read'&&!document.truncated
 const selected=criteria[criterionIndex]
 const savedItems=suggestion?.status==='ready'?suggestion.criteria||[]:[]
 const analyzed=savedItems.filter(item=>item.analyzed!==false)
 const uncertainCount=analyzed.filter(item=>item.assessment==='incierto'||!item.quote_verified).length
 const remaining=criteria.map((criterion,index)=>({...criterion,index})).filter(item=>!savedItems[item.index]||savedItems[item.index].analyzed===false)
 const possibleExclusion=analyzed.some(item=>item.quote_verified&&((item.kind==='inclusion'&&item.assessment==='contradice')||(item.kind==='exclusion'&&item.assessment==='apoya')))
 const currentProposal=savedItems[criterionIndex]||{criterion:selected?.text,kind:selected?.kind,analyzed:false}
 const providerLabel=providerName(provider)
 const actionDisabled=occupied||!canRead||!criteria.length||(provider==='groq'&&(waitSeconds>0||groqReady===false))||(provider==='gemini'&&geminiReady===false)
 useEffect(()=>{
  const current=++scope.current
  setDocument(null);setSuggestion(null);setError('');setLlmError('');setPreview(null);setPreviewError('');setCriterionIndex(0);setWorking(false);setThinking(false);setLocating(false);setProvider('gemini');setGeminiModel('gemini-3.5-flash-lite')
  Promise.all([api(`/articles/${articleId}/document`),api(`/articles/${articleId}/document/llm-review`)]).then(([value,saved])=>{if(scope.current===current){setDocument(value);setSuggestion(saved);if(saved.status==='ready'){setProvider(saved.provider==='cloud'?'gemini':saved.provider||'gemini');if(geminiModels.includes(saved.model))setGeminiModel(saved.model);const first=saved.criteria?.findIndex(item=>item.analyzed!==false);if(first>=0)setCriterionIndex(first)}}}).catch(reason=>{if(scope.current===current)setError(reason.message)})
  api('/status').then(value=>{if(scope.current===current){setGeminiReady(value.gemini_key_configured);setGroqReady(value.groq_key_configured)}}).catch(()=>{})
  return()=>{scope.current++}
 },[articleId,review.protocol_version])
 useEffect(()=>{if(retryAt<=Date.now())return;const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[retryAt])
 function beginCooldown(seconds){const until=Date.now()+Math.max(1,seconds)*1000;setRetryAt(until);setNow(Date.now());try{sessionStorage.setItem(cooldownKey,String(until))}catch{}}
 function chooseCriterion(index){setCriterionIndex(index);setPreview(null);setPreviewError('');setLlmError('')}
 function chooseRetrieval(value){setRetrieval(value);setPreview(null);setPreviewError('');setLlmError('')}
 async function run(request){
  const current=scope.current;setWorking(true);setError('')
  try{const result=await request();if(scope.current!==current)return;setDocument(result);setSuggestion({status:'missing'});setPreview(null);setPreviewError('');setLlmError('');await onSaved?.()}
  catch(reason){if(scope.current===current)setError(reason.message)}
  finally{if(scope.current===current)setWorking(false)}
 }
 async function locatePassages(){
  const current=scope.current;setLocating(true);setPreviewError('');setPreview(null)
  try{const result=await api(`/articles/${articleId}/document/passages`,{method:'POST',body:{criterion_index:criterionIndex,retrieval}});if(scope.current===current)setPreview(result)}
  catch(reason){if(scope.current===current)setPreviewError(reason.message)}
  finally{if(scope.current===current)setLocating(false)}
 }
 async function reviewPdf(){
  const current=scope.current;setThinking(true);setLlmError('')
  try{
   const result=await api(`/articles/${articleId}/document/llm-review`,{method:'POST',body:provider==='groq'?{provider,criterion_index:criterionIndex,retrieval}:provider==='gemini'?{provider,criterion_index:criterionIndex,gemini_model:geminiModel,retrieval}:{provider,retrieval}})
   if(provider==='groq')beginCooldown(60)
   if(scope.current!==current)return
   setSuggestion(result);await onSaved?.()
  }catch(reason){
   if(provider==='groq'&&reason.status===429)beginCooldown(reason.retryAfter||60)
   if(scope.current===current)setLlmError(reason.message)
  }finally{if(scope.current===current)setThinking(false)}
 }
 async function upload(event){
  const input=event.target;if(!input.files[0])return
  const body=new FormData();body.append('file',input.files[0])
  await run(()=>api(`/articles/${articleId}/document/upload`,{method:'POST',body}));input.value=''
 }
 const documentActions=<><div className="button-row document-actions"><button type="button" disabled={occupied||!document} onClick={()=>run(()=>api(`/articles/${articleId}/document/from-openalex`,{method:'POST'}))}>{working?'Procesando…':document?.status==='read'?'Buscar otra versión abierta':'Buscar PDF abierto por DOI'}</button><label className="file-button">{working?'Procesando…':'Adjuntar PDF'}<input type="file" accept=".pdf,application/pdf" disabled={occupied} onChange={upload}/></label></div><p className="fine-print">Máximo 8 MB y 80 páginas, con texto seleccionable.</p></>
 return <section className="candidate-document" aria-label="Evidencia del PDF candidato">
  <div className="document-heading"><div><h4>Lectura asistida del artículo</h4><p>Explicación, citas y contexto en un mismo lugar.</p></div>{document?.status==='read'&&<span className="document-state">PDF leído · {document.page_count} páginas</span>}</div>
  {!document&&!error&&<p role="status">Comprobando el PDF guardado…</p>}
  {document?.status==='missing'&&<><p>Busca una versión abierta o adjunta el PDF para analizar sus criterios.</p>{documentActions}</>}
  {document?.status==='read'&&<>
   {document.truncated&&<p className="document-warning">La extracción quedó incompleta. Reemplaza el PDF para poder usar el asistente.</p>}
   <div className="pdf-assistant">
    <div className="pdf-analysis-controls">
     <label className="field"><span>Criterio a revisar</span><select value={criterionIndex} disabled={occupied} onChange={event=>chooseCriterion(Number(event.target.value))}>{criteria.map((item,index)=><option key={index} value={index}>{item.kind==='inclusion'?'Inclusión':'Exclusión'} {item.number}: {item.text}</option>)}</select></label>
     {selected&&<p className="pdf-selected-criterion">{selected.text}</p>}
     <details className="pdf-settings"><summary>IA: {providerLabel}{provider==='gemini'?` · ${geminiModel==='gemini-3.5-flash-lite'?'3.5 Flash Lite':'3.8 Flash'}`:''} <span>Cambiar</span></summary>
      <div className="pdf-settings-fields"><label className="field"><span>Dónde procesar los pasajes</span><select value={provider} disabled={occupied} onChange={event=>{setProvider(event.target.value);setLlmError('')}}><option value="gemini">Gemini</option><option value="groq">Groq · qwen/qwen3.8-27b</option><option value="local">En mi equipo · Ollama qwen2.5:3b</option></select></label>
      {provider==='gemini'&&<label className="field"><span>Modelo Gemini</span><select value={geminiModel} disabled={occupied} onChange={event=>{setGeminiModel(event.target.value);setLlmError('')}}><option value="gemini-3.5-flash-lite">3.5 Flash Lite · menor costo</option><option value="gemini-3.8-flash">3.8 Flash · más capaz</option></select></label>}</div>
     </details>
     <p className="pdf-help">{provider==='local'?'Ollama analiza los criterios en tu equipo; requiere el modelo qwen2.5:3b.':`${providerLabel} recibe título, DOI, el criterio elegido y pasajes con sus páginas; el PDF completo no se envía. Su API tiene límites y puede generar costos.`}</p>
     {((provider==='groq'&&groqReady===false)||(provider==='gemini'&&geminiReady===false))&&<p className="document-warning">Configura {provider==='groq'?'SEMANTIK_GROQ_API_KEY':'SEMANTIK_GEMINI_API_KEY'} en la terminal y reinicia la aplicación. No compartas la clave.</p>}
     <button className="primary pdf-generate" type="button" disabled={actionDisabled} onClick={reviewPdf}>{thinking?'Preparando explicación…':provider==='groq'&&waitSeconds>0?`Disponible en ${waitSeconds} s`:provider==='local'?'Explicar criterios con Ollama':`Explicar este criterio con ${providerLabel}`}</button>
     {provider==='groq'&&waitSeconds>0&&<p className="pdf-help">Pausa por los límites del plan. Puedes seguir leyendo las citas guardadas.</p>}
     {thinking&&<p role="status" className="pdf-help">Buscando evidencia y preparando la explicación. Tu decisión no cambia.</p>}
     {llmError&&<p className="pdf-error" role="alert">{llmError}</p>}
    </div>
    {suggestion?.status==='ready'&&<section className="pdf-proposals" aria-label="Resultados de lectura asistida">
     <div className="pdf-proposals-heading"><h5>Evidencia para tu decisión</h5><span>{analyzed.length} de {criteria.length} consultados</span></div>
     <div className="pdf-review-summary"><span>{uncertainCount} con dudas</span><span>{remaining.length} sin consultar</span><span>{suggestion.model} · Protocolo v{suggestion.protocol_version}</span></div>
     <p className="pdf-help">Las citas se localizan en el texto extraído. La explicación es una propuesta de IA; comprueba su sentido al decidir.</p>
     {possibleExclusion&&<p className="pdf-decision-note">Hay evidencia candidata de un motivo de exclusión. Lee la explicación y las citas antes de registrar tu decisión.</p>}
     {selected&&<Proposal key={`selected-${criterionIndex}-${suggestion.model}`} item={currentProposal} index={criterionIndex} selected articleId={articleId} sha256={suggestion.document_sha256}/>}
     {savedItems.map((item,index)=>index!==criterionIndex&&item.analyzed!==false?<Proposal key={index} item={item} index={index} selected={false} articleId={articleId} sha256={suggestion.document_sha256}/>:null)}
     {remaining.length>0&&<details className="pdf-pending"><summary>{remaining.length} criterios sin consultar</summary><div>{remaining.map(item=><button type="button" key={item.index} disabled={occupied} onClick={()=>chooseCriterion(item.index)}>{item.kind==='inclusion'?'Inclusión':'Exclusión'} {item.number}: {item.text}</button>)}</div></details>}
     {(provider==='groq'||provider==='gemini')&&remaining.some(item=>item.index!==criterionIndex)&&<button type="button" className="pdf-next" disabled={occupied} onClick={()=>chooseCriterion(remaining.find(item=>item.index!==criterionIndex).index)}>Elegir siguiente criterio sin consultar</button>}
     <details className="pdf-provenance"><summary>Procedencia y consumo</summary><p>Proveedor: {providerName(suggestion.provider)}. Modelo: {suggestion.model}. {suggestion.passages_examined||0} pasajes enviados entre las consultas guardadas; pueden repetirse.</p>{suggestion.usage?.total_tokens>0&&<p>{suggestion.usage.total_tokens.toLocaleString('es-EC')} tokens acumulados informados por la API.</p>}<p>Los resultados dejan de ser vigentes si cambias el PDF o el protocolo.</p></details>
    </section>}
    <details className="pdf-provenance pdf-advanced"><summary>Opciones de búsqueda y pasajes recuperados</summary>
     <label className="field"><span>Cómo buscar en el PDF</span><select value={retrieval} disabled={occupied} onChange={event=>chooseRetrieval(event.target.value)}><option value="semantic">Por significado · modelo local</option><option value="lexical">Por términos · sin modelo</option></select></label>
     <p className="pdf-help">{retrieval==='semantic'?'Compara el criterio con fragmentos de las páginas leídas usando el modelo local.':'Busca términos relacionados; puede omitir información expresada de otra manera.'} Esta búsqueda es local y no consume solicitudes del proveedor.</p>
     <button type="button" disabled={occupied||!canRead||!criteria.length} onClick={locatePassages}>{locating?'Localizando pasajes…':'Ver pasajes para este criterio'}</button>
     {previewError&&<div className="pdf-error" role="alert"><p>{previewError}</p>{retrieval==='semantic'&&<button type="button" disabled={occupied} onClick={()=>chooseRetrieval('lexical')}>Elegir búsqueda por términos</button>}</div>}
     {preview&&<div className="pdf-passages"><p className="pdf-help">{preview.passages.length} pasajes · {selectionName(preview.retrieval)} · {preview.retrieval?.chunks_indexed??'—'} fragmentos comparados. Son pistas de lectura, no conclusiones.</p>{preview.passages.length===0&&<p>No se localizaron pasajes suficientes para este criterio.</p>}{preview.passages.map((passage,index)=><details className="pdf-passage" key={index}><summary>{facetName(passage.facet)} · Página {passage.page}</summary><blockquote>{passage.text}</blockquote><PdfPageLink articleId={articleId} page={passage.page}/></details>)}</div>}
    </details>
   </div>
   <details className="pdf-source" open={document.truncated||undefined}><summary>PDF original, procedencia y reemplazo</summary>
    <p>{document.page_count} páginas · {(document.characters||0).toLocaleString('es-EC')} caracteres extraídos. Procedencia: {document.source_type==='OpenAlex'?'enlace abierto registrado por OpenAlex':'PDF adjuntado por el investigador'}.</p>
    <div className="button-row"><a className="button" href={`/api/articles/${articleId}/document.pdf`} target="_blank" rel="noreferrer">Abrir PDF completo</a>{document.source_url&&<a href={document.source_url} target="_blank" rel="noreferrer">Ver origen del PDF</a>}</div>
    <p className="fine-print">Comprueba que el título y el DOI del archivo correspondan al candidato.</p>
    <details className="document-pages"><summary>Texto extraído por página</summary>{(document.page_previews||[]).map(page=><div key={page.page}><strong>Página {page.page}</strong><p>{page.text}</p></div>)}{document.page_count>(document.page_previews||[]).length&&<p>Vista previa de las páginas leídas; el resto del texto permanece guardado para el análisis.</p>}</details>
    {documentActions}
   </details>
  </>}
  {error&&<p className="error" role="alert">{error}</p>}
 </section>
}
