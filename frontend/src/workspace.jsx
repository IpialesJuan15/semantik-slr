import React, {useEffect,useRef,useState} from 'react'
import {api,date,labels} from './api.js'
import {ReviewForm} from './review-form.jsx'
import {PublishedBase} from './published-base.jsx'
import {SearchPanel} from './search-panel.jsx'
import {ReviewGuide} from './review-guide.jsx'
import {AnalysisPanel} from './analysis-panel.jsx'
import {SearchReceipt} from './search-receipt.jsx'
import {ArticleQueue} from './article-queue.jsx'
import {CandidateDocument} from './candidate-document.jsx'

const emptyArticle={title:'',abstract:'',doi:'',year:'',authors:'',url:'',is_oa:false};
function localToday(){const value=new Date();return `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`}
function followingDay(value){const day=new Date(`${value}T00:00:00Z`);day.setUTCDate(day.getUTCDate()+1);return day.toISOString().slice(0,10)}
const eventLabels={protocol_created:'Protocolo creado',protocol_updated:'Protocolo actualizado',published_base_created:'Revisión publicada registrada',published_base_confirmed:'Método original confirmado',manual_import:'Artículo registrado',file_import:'Archivo importado',search_completed:'Búsqueda completada',search_failed:'Búsqueda sin conexión',human_decision:'Decisión del investigador',analysis_completed:'Análisis completado',base_pdf_imported:'PDF base incorporado',candidate_pdf_read:'PDF del candidato leído',report_created:'Reporte generado',exploratory_evaluation:'Evaluación exploratoria'};
export function Workspace({id,go}){
 const [review,setReview]=useState(null),[base,setBase]=useState(null),[articles,setArticles]=useState([]),[history,setHistory]=useState([]),[reports,setReports]=useState([]),[tab,setTab]=useState(()=>{const saved=sessionStorage.getItem(`tab-${id}`);return saved==='analysis'?'articles':saved||'base'}),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[query,setQuery]=useState(''),[source,setSource]=useState(()=>sessionStorage.getItem(`source-${id}`)||'doaj'),[fromDate,setFromDate]=useState('2021-07-01'),[toDate,setToDate]=useState(localToday),[limit,setLimit]=useState(25),[filter,setFilter]=useState('all'),[dateView,setDateView]=useState('all'),[articleQuery,setArticleQuery]=useState(''),[selected,setSelected]=useState(null),[adding,setAdding]=useState(false),[showSearch,setShowSearch]=useState(false),[draft,setDraft]=useState(emptyArticle),[engine,setEngine]=useState('lexical'),[job,setJob]=useState(()=>sessionStorage.getItem(`job-${id}`)),[status,setStatus]=useState(null),[evaluation,setEvaluation]=useState(null);
 const datesReady=useRef(false)
 const activeArticle=articles.find(a=>a.id===selected);
 const baseCandidate=base&&articles.find(a=>a.doi?.toLowerCase()===base.doi.toLowerCase()||a.title.trim().toLowerCase()===base.title.trim().toLowerCase());
 const newArticles=articles.filter(a=>!a.is_base_publication);
 const pendingCount=newArticles.filter(a=>a.decision==='pending').length;
 const includedCount=newArticles.filter(a=>a.decision==='included').length;
 const staleDecisions=newArticles.filter(a=>a.decision!=='pending'&&a.decision_version!==review?.protocol_version);
 const lastSearch=history.find(item=>item.kind==='search_completed');
 const listFromDate=lastSearch?.payload?.date_from||fromDate;
 const listToDate=lastSearch?.payload?.date_to||(lastSearch?.payload?.year_to?`${lastSearch.payload.year_to}-12-31`:toDate);
 const filtered=newArticles.filter(a=>(filter==='all'||(filter==='recheck'?a.decision!=='pending'&&a.decision_version!==review?.protocol_version:a.decision===filter))&&(dateView==='all'||a.year>=Number(listFromDate.slice(0,4))&&a.year<=Number(listToDate.slice(0,4)))&&`${a.title} ${a.authors}`.toLowerCase().includes(articleQuery.toLowerCase()));
 function openTab(value){setTab(value);sessionStorage.setItem(`tab-${id}`,value);setError('');setNotice('');window.scrollTo(0,0)}
 function moveTo(id){document.getElementById(id)?.scrollIntoView({behavior:'smooth',block:'start'})}
 function chooseSource(value){setSource(value);sessionStorage.setItem(`source-${id}`,value)}
 function openSearch(){setTab('articles');setShowSearch(true);setTimeout(()=>moveTo('search-panel'),0)}
 function openRecheck(){setTab('articles');setFilter('recheck');setDateView('all');setArticleQuery('');setSelected(staleDecisions[0]?.id||null);setTimeout(()=>moveTo('article-review'),0)}
 async function refresh(){
  const [r,a,h,p,b]=await Promise.all([api(`/reviews/${id}`),api(`/reviews/${id}/articles`),api(`/reviews/${id}/history`),api(`/reviews/${id}/reports`),api(`/reviews/${id}/published-base`).catch(()=>null)])
  const minimum=b?followingDay(b.last_included_date):'1800-01-01'
  if(!datesReady.current){
   const latest=h.find(item=>item.kind==='search_completed')?.payload
   const start=latest?.date_from||(b?minimum:'2021-07-01')
   const end=latest?.date_to||(latest?.year_to?`${latest.year_to}-12-31`:localToday())
   const validStart=start<minimum?minimum:start
   const validEnd=end>localToday()?localToday():end
   setFromDate(validStart)
   setToDate(validEnd<validStart?localToday():validEnd)
   datesReady.current=true
  }else{
   setFromDate(current=>current<minimum?minimum:current)
   setToDate(current=>current<minimum?localToday():current)
  }
  setReview(r);setArticles(a);setHistory(h);setReports(p);setBase(b)
  return r
 }
 useEffect(()=>{let active=true;refresh().then(r=>{if(active)setQuery(r.search_query||'')}).catch(e=>{if(active)setError(e.message)});api('/status').then(setStatus).catch(()=>{});return()=>{active=false}},[id]);
 useEffect(()=>{if(review&&!base&&tab==='base')openTab('articles')},[review,base,tab]);
 useEffect(()=>{if(base?.confirmed&&tab==='base'&&!sessionStorage.getItem(`tab-${id}`))openTab('articles')},[base,tab,id]);
 useEffect(()=>{if(selected&&tab==='articles'&&window.matchMedia('(max-width: 900px)').matches)moveTo('article-detail')},[selected,tab]);
 useEffect(()=>{if(!job)return;let active=true;const timer=setInterval(async()=>{try{const state=await api(`/jobs/${job}`);if(!active)return;if(state.status!=='running'){clearInterval(timer);setJob(null);sessionStorage.removeItem(`job-${id}`);if(state.status==='failed')setError(state.error);else{await refresh();openTab('articles');setNotice('Análisis completado. Abre un artículo para revisar la evidencia y guardar tu decisión.')}}}catch(e){if(active){setError(e.message);setJob(null);sessionStorage.removeItem(`job-${id}`)}}},1500);return()=>{active=false;clearInterval(timer)}},[job,id]);
 async function action(fn,message){setError('');setNotice('');setBusy(true);try{const result=await fn();await refresh();setNotice(typeof message==='function'?message(result):message||'Cambios guardados.');return result}catch(e){setError(e.message);return null}finally{setBusy(false)}}
 async function upload(e,path){const input=e.target;if(!input.files[0])return;const data=new FormData();data.append('file',input.files[0]);await action(()=>api(`/reviews/${id}/${path}`,{method:'POST',body:data}),r=>r.added!==undefined?`${r.added} artículos añadidos; ${r.duplicates} duplicados omitidos.`:r.source_match===false?'PDF leído, pero no se encontró el título o DOI esperado. Comprueba que subiste la publicación correcta antes de confirmar.':`PDF leído: ${r.pages} páginas. Revisa y confirma los datos del método.`);input.value=''}
 async function startAnalysis(){const result=await action(()=>api(`/reviews/${id}/analyze`,{method:'POST',body:{engine}}),'Análisis iniciado. Puedes seguir consultando el protocolo.');if(result){setJob(result.id);sessionStorage.setItem(`job-${id}`,result.id)}}
 async function saveDecision(data){
  const current=articles.find(article=>article.id===selected)
  const result=await action(()=>api(`/articles/${selected}/decision`,{method:'PUT',body:data}),'Decisión guardada.')
  if(!result)return
  if(filter==='recheck'){
   const next=filtered.find(article=>article.id!==selected)
   setSelected(next?.id||null)
   if(!next)setFilter('all')
   setNotice(next?'Decisión actualizada. Se abrió la siguiente decisión anterior.':'Todas las decisiones anteriores quedaron revisadas.')
  }else if(current?.decision==='pending'&&data.decision!=='pending'){
   const next=filtered.find(article=>article.id!==selected&&article.decision==='pending')
   setSelected(next?.id||null)
   setNotice(next?'Decisión guardada. Se abrió el siguiente pendiente de esta vista.':'Decisión guardada. No quedan pendientes en esta vista; cambia los filtros para ver los demás.')
  }
 }
 if(!review)return <>{error?<p className="error" role="alert">{error}</p>:<p>Cargando revisión…</p>}<button className="back" onClick={()=>go('/')}>Volver a mis revisiones</button></>;
 return <><button className="back" onClick={()=>go('/')}>Mis revisiones</button><div className="workspace-title"><div><h1>{review.title}</h1><p className="subtitle">{base?`Basada en ${base.doi} · `:''}Protocolo v{review.protocol_version}</p></div><span className="pill">{base?(base.confirmed?'Método confirmado':'Método por confirmar'):'Revisión manual'}</span></div>
 <div className="review-counts">{base&&<span><b>{base.original_count}</b> estudios originales</span>}<span><b>{newArticles.length}</b> {newArticles.length===1?'candidato nuevo':'candidatos nuevos'}</span><span><b>{pendingCount}</b> {pendingCount===1?'pendiente':'pendientes'}</span><span><b>{includedCount}</b> {includedCount===1?'incluido nuevo':'incluidos nuevos'}</span></div>
 <nav className="tabs" aria-label="Secciones de la revisión">{(base?[['base','Estudio base'],['articles','Buscar y decidir'],['reports','Informes'],['history','Historial'],['protocol','Protocolo']]:[['articles','Buscar y decidir'],['reports','Informes'],['history','Historial'],['protocol','Protocolo']]).map(([key,label])=><button className={tab===key?'selected':''} key={key} onClick={()=>openTab(key)} aria-current={tab===key?'page':undefined}>{label}</button>)}</nav>
 {baseCandidate&&baseCandidate.decision!=='excluded'&&<div className="notice" role="status">La revisión base de 2022 aparece entre los candidatos guardados. Es el estudio que estás actualizando, no un estudio primario nuevo. Revisa su decisión antes de generar el informe. <button onClick={()=>{openTab('articles');setFilter('all');setDateView('all');setArticleQuery('');setSelected(baseCandidate.id);setTimeout(()=>moveTo('article-review'),0)}}>Abrir este registro</button></div>}{staleDecisions.length>0&&tab!=='articles'&&<div className="notice" role="status">Hay {staleDecisions.length} {staleDecisions.length===1?'decisión anterior':'decisiones anteriores'} por revisar con el protocolo actual. <button type="button" onClick={openRecheck}>Revisarlas ahora</button></div>}{error&&<p className="error" role="alert">{error}</p>}{notice&&<p className="notice" role="status">{notice}</p>}{job&&<p className="notice" role="status">Procesando análisis… Puedes mantener esta página abierta. La primera descarga del modelo puede tardar varios minutos. Los puntajes visibles pertenecen al análisis anterior hasta que termine el nuevo.</p>}
 {tab==='base'&&base&&<PublishedBase base={base} review={review} busy={busy} onUpload={e=>upload(e,'base-pdf')} onConfirm={values=>action(()=>api(`/reviews/${id}/published-base`,{method:'PUT',body:values}),'Método confirmado. Ya puedes buscar publicaciones posteriores a junio de 2021.')} onNext={()=>openTab('articles')}/>}
 {tab==='protocol'&&<><ReviewForm key={review.id} initial={review} onSave={async values=>{await api(`/reviews/${id}`,{method:'PUT',body:values});await refresh()}}/><section className="panel"><h2>Documento de revisión base</h2><p>Sube un PDF con texto seleccionable (hasta 8 MB y 80 páginas). La extracción recupera el texto; debes confirmar la pregunta y los criterios.</p><label className="file-button">{busy?'Procesando…':'Seleccionar PDF'}<input disabled={busy} type="file" accept=".pdf" onChange={e=>upload(e,'base-pdf')}/></label>{review.base_text&&<details className="source-text"><summary>{review.base_filename} · Ver texto extraído</summary><pre>{review.base_text}</pre></details>}</section></>}
 {tab==='articles'&&<>
 <ReviewGuide base={base} articles={newArticles} job={job} busy={busy} protocolVersion={review.protocol_version} staleCount={staleDecisions.length} onRecheck={openRecheck} onBase={()=>openTab('base')} onSearch={openSearch} onAnalyze={()=>moveTo('analysis-controls')} onReview={()=>{setFilter('pending');setDateView('all');setSelected(newArticles.find(a=>a.decision==='pending')?.id||null);setTimeout(()=>moveTo('article-review'),0)}} onReport={()=>openTab('reports')}/>
 <SearchReceipt event={lastSearch} onSearch={openSearch}/>
 {(!newArticles.length||showSearch)?<SearchPanel base={base} source={source} setSource={chooseSource} query={query} setQuery={setQuery} fromDate={fromDate} setFromDate={setFromDate} toDate={toDate} setToDate={setToDate} minimumDate={base?followingDay(base.last_included_date):null} today={localToday()} limit={limit} setLimit={setLimit} busy={busy} status={status} onBase={()=>openTab('base')} onSearch={async request=>{const result=await action(()=>api(`/reviews/${id}/search`,{method:'POST',body:request}),result=>`${result.source}: búsqueda del ${result.date_from} al ${result.date_to}; ${result.retrieved} recuperados, ${result.added} nuevos, ${result.duplicates} duplicados y ${result.base_skipped} del propio estudio base omitidos.${result.date_uncertain_count?` Verifica la fecha exacta de ${result.date_uncertain_count} registros de los años límite.`:''} Los candidatos anteriores permanecen guardados.`);if(result&&result.added){setShowSearch(false);setFilter('pending')}}}/>:!lastSearch&&<div className="search-return"><p>La revisión ya tiene candidatos guardados.</p><button onClick={openSearch}>Buscar más estudios</button></div>}
 {newArticles.length>0&&<AnalysisPanel articles={newArticles} engine={engine} setEngine={setEngine} busy={busy} job={job} status={status} onStart={startAnalysis} onEvaluate={()=>action(()=>api(`/reviews/${id}/evaluate`,{method:'POST',body:{engine}}),'Evaluación guardada en el historial.').then(result=>{if(result)setEvaluation(result)})} evaluation={evaluation}/>}
 <div className="section-heading"><h2>Artículos candidatos</h2><div className="button-row"><button onClick={()=>setAdding(!adding)}>{adding?'Cerrar formulario':'Añadir artículo'}</button><label className="file-button">Importar CSV / JSON<input type="file" accept=".csv,.json" disabled={busy} onChange={e=>upload(e,'import')}/></label></div></div>
 {adding&&<form className="panel" onSubmit={async e=>{e.preventDefault();const r=await action(()=>api(`/reviews/${id}/articles`,{method:'POST',body:{...draft,year:draft.year?Number(draft.year):null}}),r=>r.added?'Artículo añadido.':'El artículo ya está registrado; se omitió el duplicado.');if(r){setDraft(emptyArticle);setAdding(false)}}}><h3>Registrar un artículo real</h3><p>Introduce los metadatos de la fuente. El resumen debe conservar el texto original.</p>{[['title','Título'],['abstract','Resumen original'],['doi','DOI'],['authors','Autores'],['year','Año'],['url','Enlace a la fuente']].map(([key,label])=><label key={key} className="field"><span>{label}{key==='title'?' *':''}</span>{key==='abstract'?<textarea maxLength={50000} rows={5} value={draft[key]} onChange={e=>setDraft({...draft,[key]:e.target.value})}/>:<input required={key==='title'} type={key==='year'?'number':key==='url'?'url':'text'} value={draft[key]} onChange={e=>setDraft({...draft,[key]:e.target.value})}/>}</label>)}<label className="checkbox"><input type="checkbox" checked={draft.is_oa} onChange={e=>setDraft({...draft,is_oa:e.target.checked})}/> He comprobado que es de acceso abierto</label><button className="primary" disabled={busy}>Guardar artículo</button></form>}
 <div className="review-workbench" id="article-review"><ArticleQueue articles={newArticles} visible={filtered} selected={selected} onSelect={setSelected} query={articleQuery} onQuery={value=>{setArticleQuery(value);setSelected(null)}} status={filter} onStatus={value=>{setFilter(value);setSelected(null)}} yearView={dateView} onYearView={value=>{setDateView(value);setSelected(null)}} fromDate={listFromDate} toDate={listToDate} recheckCount={staleDecisions.length}/>
 <div className="reading-side" id="article-detail">{activeArticle?<ArticleDetail key={activeArticle.id} article={activeArticle} busy={busy} onClose={()=>setSelected(null)} onDecision={saveDecision} onDocumentSaved={refresh}/>:<div className="reading-empty"><h3>Elige un artículo para revisarlo</h3><p>Aquí verás su fuente, resumen, evidencia del análisis y el formulario para registrar tu decisión.</p></div>}</div></div>
 </>}
 {tab==='reports'&&<><section className="panel"><h2>Reportes de actualización</h2><p>Cada versión conserva el protocolo y las decisiones en el momento de crearla.</p>{pendingCount>0&&<div className="report-draft-note"><strong>Será un borrador de cribado</strong><span>Quedan {pendingCount} candidatos por decidir. Puedes guardar una versión de avance, pero todavía no es una síntesis final.</span><button type="button" onClick={()=>openTab('articles')}>Volver a revisar</button></div>}<div className="button-row"><button className="primary" disabled={busy||!newArticles.length||!!job||(base&&!base.confirmed)} onClick={()=>action(()=>api(`/reviews/${id}/reports`,{method:'POST'}),r=>`Reporte v${r.version} generado.`)}>Generar nueva versión</button><a className="button" href={`/api/reviews/${id}/export.csv`}>Exportar tabla CSV</a></div><p className="fine-print">El CSV refleja el estado actual. Los reportes JSON son versiones guardadas. El depósito en Zenodo y la asignación de DOI siguen pendientes.</p></section>{reports.length?<div className="panel">{reports.map(r=><div className="report-row" key={r.id}><div><strong>{r.status==='draft'?'Borrador':'Actualización'} v{r.version}</strong><p>{date(r.created_at)}</p><small className="hash">SHA-256: {r.sha256}</small></div><div className="button-row"><a className="button" href={`/api/reports/${r.id}.html`}>Informe para imprimir</a><a className="button" href={`/api/reports/${r.id}.json`}>Descargar JSON</a></div></div>)}</div>:<p className="empty">Todavía no se han generado reportes.</p>}</>}
 {tab==='history'&&<section className="panel"><h2>Trazabilidad del trabajo</h2><p>Registro de búsquedas, cambios metodológicos, análisis y decisiones.</p>{history.map(h=><details className="event" key={h.id}><summary><span>{eventLabels[h.kind]||h.kind}</span><time>{date(h.created_at)}</time></summary><pre>{JSON.stringify(h.payload,null,2)}</pre></details>)}</section>}
 </>;
}
function ArticleDetail({article,busy,onClose,onDecision,onDocumentSaved}){
 const [decision,setDecision]=useState(article.decision)
 const [reason,setReason]=useState(article.reason)
 const result=article.analysis
 return <section className="panel article-detail" aria-label="Expediente del candidato">
  <div className="section-heading"><div><small>Expediente del candidato</small><h2>Leer y decidir</h2></div><button type="button" onClick={onClose}>Cerrar expediente</button></div>
  <h3>{article.title}</h3>
  <div className="reading-facts"><span>{article.year||'Año sin registrar'}</span><span>{article.source}</span><span className={'state '+article.decision}>{labels[article.decision]}</span></div>
  <div className="button-row source-actions">{article.doi&&<a href={`https://doi.org/${encodeURIComponent(article.doi)}`} target="_blank" rel="noreferrer">Abrir DOI</a>}{/^https?:\/\//.test(article.url)&&<a href={article.url} target="_blank" rel="noreferrer">Ver texto en la fuente</a>}</div>
  <p className="reading-check">Antes de decidir, comprueba en la fuente la fecha de publicación, el país, el método y qué hizo realmente la herramienta de IA.</p>
  {article.source==='DOAJ'&&<p className="fine-print">DOAJ registró el año {article.year||'sin año'}. Si está cerca del límite de tu búsqueda, confirma día y mes en el artículo.</p>}
  <h4>Resumen original</h4><p className="abstract">{article.abstract||'Este registro no tiene resumen. Consulta la fuente antes de decidir.'}</p>
  <CandidateDocument articleId={article.id} onSaved={onDocumentSaved}/>
  {result&&<details className="evidence-drawer" id={`evidence-${article.id}`}><summary>Ver {result.evidence.length} fragmentos sugeridos por {result.engine==='semantic'?'el modelo semántico':'TF-IDF'}</summary><p>Son frases localizadas en el título o resumen. Pueden parecerse a un criterio sin demostrar que se cumple. El puntaje no es una probabilidad de inclusión.</p><small>Protocolo v{result.protocol_version} · {result.model}</small><div className="evidence-list">{result.evidence.map((item,index)=><div className="evidence" key={index}><strong>{item.kind==='inclusion'?'Criterio de inclusión':'Criterio de exclusión'}: {item.criterion}</strong><blockquote>{item.signal_present?item.quote:'No se localizó un fragmento cercano en título o resumen. Revisa la fuente.'}</blockquote><small>Parecido {item.similarity.toFixed(3)} · Verifica el criterio en el artículo</small></div>)}</div>{result.recommendation&&<p className="notice">Sugerencia experimental: {labels[result.recommendation.label]}. Entrenada con {result.recommendation.training_examples} decisiones; no validada de forma independiente.</p>}</details>}
  <form className="decision-form" onSubmit={event=>{event.preventDefault();onDecision({decision,reason})}}><div className="decision-heading"><h4>Tu decisión</h4><p>La decisión la toma el investigador. Explica qué encontraste en la fuente.</p></div><label className="field"><span>Estado</span><select aria-label="Decisión del investigador" value={decision} onChange={event=>setDecision(event.target.value)}>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><label className="field"><span>Motivo de la decisión *</span><textarea required minLength={3} maxLength={4000} rows={3} value={reason} onChange={event=>setReason(event.target.value)} placeholder="Ej.: estudio empírico en Costa Rica; describe el uso concreto de Copy.ai en evaluación de escritura."/></label><button className="primary" disabled={busy}>{busy?'Guardando…':'Guardar decisión'}</button></form>
 </section>
}
