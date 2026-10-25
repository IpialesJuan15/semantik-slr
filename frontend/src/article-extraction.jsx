import React,{useEffect,useState} from 'react'
import {api} from './api.js'
import './article-extraction.css'

const labels={country:'País y contexto',participants:'Participantes',ai_tool:'Herramienta de IA',ai_technique:'Técnica de IA',method:'Método de investigación',outcomes:'Resultados principales'}
const empty=()=>Object.fromEntries(Object.keys(labels).map(key=>[key,{value:'',quote:'',page:null}]))

export function ArticleExtraction({article,onSaved}){
 const [facts,setFacts]=useState(empty),[loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
 const [suggestions,setSuggestions]=useState({}),[searching,setSearching]=useState('')
 useEffect(()=>{let active=true;setLoaded(false);setFacts(empty());setError('');api(`/articles/${article.id}/extraction`).then(data=>{if(active){setFacts({...empty(),...data.facts});setLoaded(true)}}).catch(e=>{if(active){setError(e.message);setLoaded(true)}});return()=>{active=false}},[article.id])
 function change(key,field,value){setFacts(previous=>({...previous,[key]:{...previous[key],[field]:value}}));setNotice('')}
 async function find(key){setSearching(key);setError('');try{const result=await api(`/articles/${article.id}/extraction/suggest/${key}`,{method:'POST',body:{retrieval:'semantic'}});setSuggestions(previous=>({...previous,[key]:result.passages}));if(!result.passages.length)setNotice('No se hallaron pasajes suficientes. Comprueba el PDF manualmente.')}catch(e){setError(e.message)}finally{setSearching('')}}
 async function save(e){e.preventDefault();setBusy(true);setError('');setNotice('');try{const clean=Object.fromEntries(Object.entries(facts).filter(([,item])=>item.value?.trim()||item.quote?.trim()||item.page));if(!Object.keys(clean).length){setError('Completa al menos un dato con una cita del PDF.');return}const result=await api(`/articles/${article.id}/extraction`,{method:'PUT',body:{facts:clean}});setFacts({...empty(),...result.facts});setNotice('Ficha guardada. Sus datos se incluirán en el próximo informe.');await onSaved?.()}catch(e){setError(e.message)}finally{setBusy(false)}}
 if(article.decision!=='included')return null
 return <section className="article-extraction" aria-label="Ficha de extracción del estudio incluido">
  <h4>Ficha del estudio incluido</h4><p>Registra lo que encontraste en el PDF. Cada dato necesita una cita y página comprobables. Si un dato no consta, déjalo vacío.</p>
  {!loaded?<p>Cargando ficha…</p>:<form onSubmit={save}>
   {Object.entries(labels).map(([key,label])=><details className="extraction-field" key={key} open={key==='country'}><summary><span>{label}</span><small>{facts[key]?.value?'Dato registrado':'Sin registrar'}</small></summary>
    <label className="field"><span>Dato encontrado</span><input maxLength={1000} value={facts[key]?.value||''} onChange={e=>change(key,'value',e.target.value)} placeholder={key==='ai_technique'?'Ej.: NLP, solo si el artículo lo identifica':'Escribe el dato tal como lo describe el estudio'}/></label>
    <div className="extraction-page"><label className="field"><span>Página del PDF</span><input type="number" min="1" value={facts[key]?.page??''} onChange={e=>change(key,'page',e.target.value?Number(e.target.value):null)}/></label><button type="button" disabled={!!searching||busy} onClick={()=>find(key)}>{searching===key?'Buscando…':'Buscar cita en el PDF'}</button></div>
    {suggestions[key]&&<div className="extraction-suggestions"><p>Pasajes sugeridos. Comprueba el sentido en la fuente antes de usarlos.</p>{suggestions[key].map((p,i)=><details key={i}><summary>Página {p.page} · Pasaje {i+1}</summary><blockquote>{p.text}</blockquote><a href={`/api/articles/${article.id}/document.pdf#page=${p.page}`} target="_blank" rel="noreferrer">Abrir página {p.page}</a><button type="button" onClick={()=>setFacts(previous=>({...previous,[key]:{...previous[key],page:p.page,quote:p.text}}))}>Usar esta cita</button></details>)}</div>}
    <label className="field"><span>Cita textual del PDF</span><textarea rows={3} maxLength={800} value={facts[key]?.quote||''} onChange={e=>change(key,'quote',e.target.value)} placeholder="Selecciona un pasaje sugerido o copia una cita exacta de la página"/></label>
    {facts[key]?.page&&<a href={`/api/articles/${article.id}/document.pdf#page=${facts[key].page}`} target="_blank" rel="noreferrer">Comprobar página {facts[key].page}</a>}
   </details>)}
   {error&&<p className="error" role="alert">{error}</p>}{notice&&<p className="notice" role="status">{notice}</p>}
   <button className="primary" disabled={busy} type="submit">{busy?'Guardando ficha…':'Guardar ficha del estudio'}</button>
  </form>}
 </section>
}
