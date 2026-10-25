import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './research-workbench.css'
import './workflow-polish.css'
import { Workspace } from './workspace.jsx'
import { ReviewForm } from './review-form.jsx'
import { api } from './api.js'

function App() {
  const [path, setPath] = useState(location.pathname)
  const [reviews, setReviews] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [template, setTemplate] = useState(null)
  function go(to) { history.pushState({}, '', to); setPath(to); setError(''); window.scrollTo(0, 0) }
  useEffect(() => { const pop=()=>setPath(location.pathname); addEventListener('popstate',pop); return ()=>removeEventListener('popstate',pop) }, [])
  useEffect(() => { if(path !== '/') return; let active=true; setLoading(true); api('/reviews').then(data=>{if(active)setReviews(data)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)}); return ()=>{active=false} }, [path])
  useEffect(()=>{if(path==='/reviews/new')api('/published-template').then(setTemplate).catch(e=>setError(e.message))},[path])
  const shown = reviews.filter(r=>`${r.title} ${r.question}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="app-layout"><a href="#main" className="skip">Ir al contenido</a>
    <aside className="sidebar"><button className="brand" onClick={()=>go('/')}><span className="logo">s</span><span>semantik<small>Revisiones vivas</small></span></button><div className="nav-group"><p>Investigación</p><button className={path==='/'?'nav active':'nav'} onClick={()=>go('/')}><span>▦</span> Mis revisiones</button><button className={path==='/reviews/new'?'nav active':'nav'} onClick={()=>go('/reviews/new')}><span>＋</span> Cargar revisión publicada</button></div><div className="side-note"><strong>Tu criterio, respaldado por evidencia.</strong><p>Explora, compara y documenta cada decisión.</p><small>Versión 0.13.1 · Uso local</small></div></aside>
    <div className="page"><header><span>Espacio de investigación</span><span className="version">Prototipo de tesis</span></header><main id="main">
      {error&&<div role="alert" className="error">{error}</div>}
      {path==='/'?<><div className="page-title"><div><h1>Mis revisiones</h1><p>Parte de una publicación original y registra los cambios con evidencia.</p></div><button className="primary" onClick={()=>go('/reviews/new')}>Cargar revisión publicada</button></div>
      <div className="overview"><div><b>{reviews.length}</b><span>Revisiones</span></div><div><b>{reviews.reduce((n,r)=>n+r.article_count,0)}</b><span>Artículos registrados</span></div><div><b>{reviews.reduce((n,r)=>n+r.included_count,0)}</b><span>Incluidos por el revisor</span></div></div>
      <div className="section-heading"><h2>Biblioteca de proyectos</h2><input aria-label="Buscar revisión" className="search-input" placeholder="Buscar por título o pregunta" value={query} onChange={e=>setQuery(e.target.value)}/></div>
      {loading?<p>Cargando revisiones…</p>:shown.length?<div className="project-list">{shown.map(r=><button className="project-row" key={r.id} onClick={()=>go(`/reviews/${r.id}`)}><span className="project-symbol">▤</span><span className="project-info"><strong>{r.title}</strong><span>{r.question}</span><small>Proyecto #{r.id} · Creado {new Date(r.created_at).toLocaleDateString('es-EC')} · Protocolo v{r.protocol_version} · {r.article_count} {r.article_count===1?'candidato nuevo':'candidatos nuevos'}</small></span><span className="open-label">Abrir revisión</span></button>)}</div>:<div className="empty"><h2>{query?'No hay coincidencias':'Comienza con una revisión publicada'}</h2><p>{query?'Prueba con otro término.':'Carga el caso base preparado y confirma su método con el PDF original.'}</p>{!query&&<button className="primary" onClick={()=>go('/reviews/new')}>Cargar revisión publicada</button>}</div>}
      <div className="workflow"><h3>Recorrido de una actualización</h3><div><span>Confirmar estudio base</span><span>Buscar publicaciones nuevas</span><span>Analizar y decidir</span><span>Generar reporte</span></div><p>Los 31 estudios originales se muestran por separado de los nuevos candidatos.</p></div></>:path==='/reviews/new'?<><button className="back" onClick={()=>go('/')}>Volver a mis revisiones</button><h1>Cargar revisión publicada</h1><p className="subtitle">Empieza con el caso base que acabamos de revisar. Después podrás adjuntar y confirmar su PDF.</p>{template&&<section className="panel published-choice"><h2>{template.title}</h2><p>{template.authors} · {template.year} · {template.original_count} estudios originales · {template.license}</p><p>DOI: <a href={template.source_url} target="_blank" rel="noreferrer">{template.doi}</a></p><p className="fine-print">La ficha y las tablas son una transcripción inicial de esta publicación. Tendrás que cotejarlas con el PDF y confirmar el método.</p><button className="primary" onClick={async()=>{setLoading(true);try{const r=await api('/reviews/from-published',{method:'POST',body:{doi:template.doi}});go(`/reviews/${r.id}`)}catch(e){setError(e.message)}finally{setLoading(false)}}} disabled={loading}>{loading?'Creando…':'Crear revisión desde este estudio'}</button></section>}<details className="manual-option"><summary>Crear una revisión manual sin estudio base</summary><p>Esta opción conserva el flujo anterior para pruebas. El caso de tesis empieza con una revisión publicada.</p><ReviewForm onSave={async values=>{const r=await api('/reviews',{method:'POST',body:values});go(`/reviews/${r.id}`)}}/></details></>:<Workspace key={path} id={path.split('/').pop()} go={go}/>}
    </main><footer>Semantik SLR · Decisiones humanas, evidencia trazable.</footer></div>
  </div>
}
createRoot(document.getElementById('root')).render(<App/>);
