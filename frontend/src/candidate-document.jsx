import React, {useEffect,useRef,useState} from 'react'
import {api} from './api.js'
import './pdf-assistant.css'

const cooldownKey='semantik-groq-retry-at'
function savedCooldown(){try{return Number(sessionStorage.getItem(cooldownKey))||0}catch{return 0}}
function describeAssessment(item){
 if(item.analyzed===false)return 'Sin consultar'
 if(item.assessment==='incierto'||!item.quote_verified)return 'Falta evidencia comprobable'
 if(item.kind==='inclusion')return item.assessment==='apoya'?'Sugiere que cumple este criterio':'Sugiere que no cumple este criterio'
 return item.assessment==='apoya'?'Sugiere que este motivo de exclusión aplica':'Sugiere que este motivo de exclusión no aplica'
}
function selectionName(retrieval){return retrieval?.method==='semantic'?'Similitud semántica del PDF':retrieval?.method==='lexical'?'Búsqueda por términos en el PDF':'Selección de pasajes anterior'}
function PdfPageLink({articleId,page,children}){return <a href={`/api/articles/${articleId}/document.pdf#page=${page}`} target="_blank" rel="noreferrer">{children||`Abrir página ${page}`}</a>}

export function CandidateDocument({articleId,onSaved,review}){
 const [document,setDocument]=useState(null),[working,setWorking]=useState(false),[error,setError]=useState('')
 const [suggestion,setSuggestion]=useState(null),[thinking,setThinking]=useState(false),[llmError,setLlmError]=useState('')
 const [provider,setProvider]=useState('groq'),[cloudReady,setCloudReady]=useState(null),[groqReady,setGroqReady]=useState(null)
 const [criterionIndex,setCriterionIndex]=useState(0),[retrieval,setRetrieval]=useState('semantic')
 const [preview,setPreview]=useState(null),[locating,setLocating]=useState(false),[previewError,setPreviewError]=useState('')
 const [retryAt,setRetryAt]=useState(savedCooldown),[now,setNow]=useState(Date.now)
 const scope=useRef(0)
 const criteria=[['inclusion',review.inclusion],['exclusion',review.exclusion]].flatMap(([kind,value])=>String(value||'').split('\n').map(line=>line.replace(/^[\s\-•]+/,'').trim()).filter(Boolean).map((text,index)=>({kind,text,number:index+1})))
 const occupied=working||thinking||locating
 const waitSeconds=Math.max(0,Math.ceil((retryAt-now)/1000))
 const canRead=document?.status==='read'&&!document.truncated
 const selected=criteria[criterionIndex]
 const nextUnreviewed=criteria.findIndex((_,index)=>suggestion?.criteria?.[index]?.analyzed===false||!suggestion?.criteria?.[index])
 const possibleExclusion=suggestion?.criteria?.some(item=>item.quote_verified&&item.analyzed!==false&&((item.kind==='inclusion'&&item.assessment==='contradice')||(item.kind==='exclusion'&&item.assessment==='apoya')))
 useEffect(()=>{
  const current=++scope.current
  setDocument(null);setSuggestion(null);setError('');setLlmError('');setPreview(null);setPreviewError('');setCriterionIndex(0);setWorking(false);setThinking(false);setLocating(false)
  Promise.all([api(`/articles/${articleId}/document`),api(`/articles/${articleId}/document/llm-review`)]).then(([value,saved])=>{if(scope.current===current){setDocument(value);setSuggestion(saved);if(saved.status==='ready')setProvider(saved.provider||'local')}}).catch(reason=>{if(scope.current===current)setError(reason.message)})
  api('/status').then(value=>{if(scope.current===current){setCloudReady(value.cloud_llm_configured);setGroqReady(value.groq_key_configured)}}).catch(()=>{})
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
   const result=await api(`/articles/${articleId}/document/llm-review`,{method:'POST',body:provider==='groq'?{provider,criterion_index:criterionIndex,retrieval}:{provider,retrieval}})
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
 return <section className="candidate-document" aria-label="Texto completo del candidato">
  <div className="document-heading"><div><h4>Texto completo</h4><p>La evidencia conserva su página para que puedas contrastarla con el original.</p></div>{document?.status==='read'&&<span className="document-state">PDF leído</span>}</div>
  {!document&&!error&&<p role="status">Comprobando el PDF guardado…</p>}
  {document?.status==='missing'&&<p>Todavía no hay un PDF leído. Busca una versión abierta o adjunta el archivo para revisar su contenido.</p>}
  {document?.status==='read'&&<>
   <p><strong>{document.page_count} páginas · {document.characters.toLocaleString('es-EC')} caracteres extraídos.</strong> Procedencia: {document.source_type==='OpenAlex'?'enlace abierto registrado por OpenAlex':'PDF adjuntado por el investigador'}.</p>
   {document.truncated&&<p className="document-warning">La extracción quedó incompleta. Revisa o reemplaza el PDF antes de usar el asistente.</p>}
   <div className="button-row"><a className="button" href={`/api/articles/${articleId}/document.pdf`} target="_blank" rel="noreferrer">Abrir PDF guardado</a>{document.source_url&&<a href={document.source_url} target="_blank" rel="noreferrer">Ver origen del PDF</a>}</div>
   <p className="fine-print">Comprueba que el título y el DOI del archivo correspondan a este candidato.</p>
   <details className="document-pages"><summary>Ver texto extraído por página</summary>{document.page_previews.map(page=><div key={page.page}><strong>Página {page.page}</strong><p>{page.text}</p></div>)}{document.page_count>document.page_previews.length&&<p>Esta es una vista previa. Las páginas leídas quedan guardadas para localizar pasajes.</p>}</details>
   <div className="pdf-assistant">
    <h5>Comprobar un criterio en el PDF</h5>
    <p>Elige un criterio. Semantik buscará hasta tres fragmentos del estudio principal; después podrás pedir una explicación. Confirma siempre la cita en el PDF.</p>
    <div className="pdf-reading-step">
     <h6><span aria-hidden="true">1</span>Localizar evidencia</h6>
     <label className="field"><span>Criterio a revisar</span><select value={criterionIndex} disabled={occupied} onChange={event=>chooseCriterion(Number(event.target.value))}>{criteria.map((item,index)=><option key={index} value={index}>{item.kind==='inclusion'?'Inclusión':'Exclusión'} {item.number}: {item.text}</option>)}</select></label>
     {selected&&<p className="pdf-selected-criterion"><strong>{selected.kind==='inclusion'?'Inclusión':'Exclusión'} {selected.number}</strong>{selected.text}</p>}
     <label className="field"><span>Cómo buscar en el PDF</span><select value={retrieval} disabled={occupied} onChange={event=>chooseRetrieval(event.target.value)}><option value="semantic">Por significado · embeddings locales</option><option value="lexical">Por términos · alternativa sin modelo</option></select></label>
     <p className="pdf-help">{retrieval==='semantic'?'Compara el criterio con fragmentos de todas las páginas leídas. Usa el modelo semántico instalado en tu equipo.':'Busca coincidencias de palabras. Puede omitir información expresada de otra forma o en otro idioma.'} Esta consulta es local y no consume solicitudes de Groq.</p>
     <button type="button" disabled={occupied||!canRead||!criteria.length} onClick={locatePassages}>{locating?'Localizando pasajes…':preview?'Actualizar pasajes':'Localizar pasajes del PDF'}</button>
     {locating&&<p role="status" className="pdf-help">La primera preparación del PDF puede tardar. Los fragmentos preparados se reutilizan en próximas consultas.</p>}
     {previewError&&<div className="pdf-error" role="alert"><p>{previewError}</p>{retrieval==='semantic'&&<button type="button" disabled={occupied} onClick={()=>chooseRetrieval('lexical')}>Elegir búsqueda por términos</button>}</div>}
     {preview&&<div className="pdf-passages"><p className="pdf-preview-summary"><strong>{preview.passages.length} pasajes localizados</strong><span>{selectionName(preview.retrieval)}. Revisados {preview.retrieval?.chunks_indexed??'—'} fragmentos del documento.</span></p><p className="pdf-help">Se omiten las referencias bibliográficas. Si los fragmentos no tratan del estudio principal, revisa el PDF y decide tú.</p>{preview.passages.length===0&&<p role="status">No se encontraron pasajes suficientes del estudio principal. Revisa el PDF manualmente; no se consultará Groq.</p>}{preview.passages.map((passage,index)=><details className="pdf-passage" key={index} open={index===0}><summary>Página {passage.page} · Pasaje {index+1}</summary><blockquote>{passage.text}</blockquote><PdfPageLink articleId={articleId} page={passage.page}/></details>)}</div>}
    </div>
    <div className="pdf-reading-step">
     <h6><span aria-hidden="true">2</span>Obtener una explicación</h6>
     <label className="field"><span>Dónde procesar los pasajes</span><select value={provider} disabled={occupied} onChange={event=>{setProvider(event.target.value);setLlmError('')}}><option value="groq">Groq · qwen/qwen3.8-27b</option><option value="cloud">OpenAI · gpt-4.1-mini</option><option value="local">En mi equipo · Ollama qwen2.5:3b</option></select></label>
     <p className="pdf-help">{provider==='groq'?'Groq recibe título, DOI, el criterio y pasajes del PDF. Analiza un criterio por solicitud; el plan gratuito tiene límites.':provider==='cloud'?'OpenAI recibe título, DOI, todos los criterios y pasajes seleccionados del PDF. La API puede generar costos.':'Ollama analiza todos los criterios en tu equipo. Requiere qwen2.5:3b; con 8 GB puede tardar varios minutos.'} {provider!=='local'&&'El PDF completo no se envía.'}</p>
     {((provider==='groq'&&groqReady===false)||(provider==='cloud'&&cloudReady===false))&&<p className="document-warning">Configura {provider==='groq'?'SEMANTIK_GROQ_API_KEY':'SEMANTIK_OPENAI_API_KEY'} en la terminal y reinicia la aplicación. No compartas la clave.</p>}
     <button className="primary" type="button" disabled={occupied||!canRead||!criteria.length||(provider==='groq'&&(!preview?.passages?.length||waitSeconds>0||groqReady===false))||(provider==='cloud'&&cloudReady===false)} onClick={reviewPdf}>{thinking?'Preparando explicación…':provider==='groq'?(waitSeconds>0?`Disponible en ${waitSeconds} s`:'Explicar este criterio con Groq'):provider==='cloud'?'Explicar los criterios con OpenAI':'Explicar los criterios con Ollama'}</button>
     {provider==='groq'&&!preview&&<p className="pdf-help">Primero localiza evidencia del estudio principal en el paso 1.</p>}
     {provider==='groq'&&waitSeconds>0&&<p className="pdf-help">Pausa entre solicitudes para reducir errores por límite del plan. Puedes seguir leyendo el PDF y localizar otros pasajes.</p>}
     {thinking&&<p role="status" className="pdf-help">Puedes leer los pasajes mientras termina. La explicación no modifica tu decisión.</p>}
     {llmError&&<p className="pdf-error" role="alert">{llmError}</p>}
    </div>
    {suggestion?.status==='ready'&&<div className="pdf-proposals">
     <div className="pdf-proposals-heading"><h6>Propuestas guardadas</h6><span>{suggestion.criteria.filter(item=>item.analyzed!==false).length} de {suggestion.criteria.length} criterios consultados</span></div>
     <p className="pdf-help">{suggestion.model} · Protocolo v{suggestion.protocol_version}. Cada cita comprobada existe en el PDF; su interpretación requiere tu revisión.</p>
     {possibleExclusion&&<p className="document-warning">Hay una propuesta que podría justificar exclusión. Comprueba su cita: si confirmas un motivo suficiente, puedes registrar tu decisión sin consultar todos los criterios.</p>}
     {suggestion.criteria.map((item,index)=><details className="pdf-proposal" key={index} open={index===criterionIndex}><summary><span>{item.kind==='inclusion'?'Inclusión':'Exclusión'}: {item.criterion}</span><b className={item.assessment==='incierto'||item.analyzed===false?'pdf-verdict uncertain':'pdf-verdict'}>{describeAssessment(item)}</b></summary>{item.analyzed===false?<p>Este criterio todavía no se ha enviado al LLM.</p>:item.quote_verified?<><blockquote>{item.quote}</blockquote><PdfPageLink articleId={articleId} page={item.page}/><p className="pdf-explanation">{item.explanation}</p><small>{selectionName(item.retrieval||suggestion.retrieval)}</small></>:<p>El sistema no obtuvo una cita comprobable. Consulta el PDF manualmente; esto no significa que el artículo deba excluirse.</p>}</details>)}
     {provider==='groq'&&nextUnreviewed>=0&&nextUnreviewed!==criterionIndex&&<button type="button" disabled={occupied} onClick={()=>chooseCriterion(nextUnreviewed)}>Elegir otro criterio sin consultar</button>}
     <details className="pdf-provenance"><summary>Ver procedencia y consumo acumulado</summary><p>Proveedor: {suggestion.provider==='groq'?'Groq':suggestion.provider==='cloud'?'OpenAI':'Ollama'}. Modelo: {suggestion.model}.</p><p>{suggestion.passages_examined} pasajes enviados en total entre las consultas guardadas; pueden repetirse.</p>{suggestion.usage?.total_tokens>0&&<p>{suggestion.usage.total_tokens.toLocaleString('es-EC')} tokens acumulados de entrada y salida informados por la API.</p>}<p className="pdf-help">Los resultados dejan de mostrarse como vigentes si cambia el PDF o el protocolo.</p></details>
    </div>}
   </div>
  </>}
  <div className="button-row document-actions"><button type="button" disabled={occupied||!document} onClick={()=>run(()=>api(`/articles/${articleId}/document/from-openalex`,{method:'POST'}))}>{working?'Procesando…':document?.status==='read'?'Buscar otra versión abierta':'Buscar PDF abierto por DOI'}</button><label className="file-button">{working?'Procesando…':'Adjuntar PDF'}<input type="file" accept=".pdf,application/pdf" disabled={occupied} onChange={upload}/></label></div>
  <p className="fine-print">Máximo 8 MB y 80 páginas, con texto seleccionable. Si la búsqueda automática falla, comprueba la fuente y adjunta el PDF.</p>
  {error&&<p className="error" role="alert">{error}</p>}
 </section>
}
