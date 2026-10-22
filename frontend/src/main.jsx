import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { Workspace } from './workspace.jsx'
import { ReviewForm } from './review-form.jsx'
import { api } from './api.js'

function App() {
  const [path, setPath] = useState(location.pathname)
  const [reviews, setReviews] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  function go(to) { history.pushState({}, '', to); setPath(to); setError(''); window.scrollTo(0, 0) }
  useEffect(() => { const pop=()=>setPath(location.pathname); addEventListener('popstate',pop); return ()=>removeEventListener('popstate',pop) }, [])
  useEffect(() => { if(path !== '/') return; let active=true; setLoading(true); api('/reviews').then(data=>{if(active)setReviews(data)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)}); return ()=>{active=false} }, [path])
  const shown = reviews.filter(r=>`${r.title} ${r.question}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="app-layout"><a href="#main" className="skip">Ir al contenido</a>
    <aside className="sidebar"><button className="brand" onClick={()=>go('/')}><span className="logo">s</span><span>semantik<small>Revisiones vivas</small></span></button><div className="nav-group"><p>Investigación</p><button className={path==='/'?'nav active':'nav'} onClick={()=>go('/')}><span>▦</span> Mis revisiones</button><button className={path==='/reviews/new'?'nav active':'nav'} onClick={()=>go('/reviews/new')}><span>＋</span> Crear revisión</button></div><div className="side-note"><strong>Tu criterio, respaldado por evidencia.</strong><p>Explora, compara y documenta cada decisión.</p><small>Versión 0.2 · Uso local</small></div></aside>
    <div className="page"><header><span>Espacio de investigación</span><span className="version">Prototipo de tesis</span></header><main id="main">
      {error&&<div role="alert" className="error">{error}</div>}
      {path==='/'?<><div className="page-title"><div><h1>Mis revisiones</h1><p>De una pregunta de investigación a un registro trazable de evidencia.</p></div><button className="primary" onClick={()=>go('/reviews/new')}>Crear revisión</button></div>
      <div className="overview"><div><b>{reviews.length}</b><span>Revisiones</span></div><div><b>{reviews.reduce((n,r)=>n+r.article_count,0)}</b><span>Artículos registrados</span></div><div><b>{reviews.reduce((n,r)=>n+r.included_count,0)}</b><span>Incluidos por el revisor</span></div></div>
      <div className="section-heading"><h2>Biblioteca de proyectos</h2><input aria-label="Buscar revisión" className="search-input" placeholder="Buscar por título o pregunta" value={query} onChange={e=>setQuery(e.target.value)}/></div>
      {loading?<p>Cargando revisiones…</p>:shown.length?<div className="project-list">{shown.map(r=><button className="project-row" key={r.id} onClick={()=>go(`/reviews/${r.id}`)}><span className="project-symbol">▤</span><span className="project-info"><strong>{r.title}</strong><span>{r.question}</span><small>Protocolo v{r.protocol_version} · {r.article_count} artículos</small></span><span className="open-label">Abrir</span></button>)}</div>:<div className="empty"><h2>{query?'No hay coincidencias':'Tu investigación empieza con una pregunta'}</h2><p>{query?'Prueba con otro término.':'Crea una revisión, define sus criterios e incorpora artículos para analizarlos.'}</p>{!query&&<button className="primary" onClick={()=>go('/reviews/new')}>Crear mi primera revisión</button>}</div>}
      <div className="workflow"><h3>Un proceso que puedes revisar</h3><div><span>Definir protocolo</span><span>Recuperar artículos</span><span>Analizar evidencia</span><span>Decidir y exportar</span></div><p>Cada consulta, modificación del protocolo y decisión queda registrada en el historial.</p></div></>:path==='/reviews/new'?<><button className="back" onClick={()=>go('/')}>Volver a mis revisiones</button><h1>Nueva revisión</h1><p className="subtitle">Define la pregunta y los criterios que orientarán tu trabajo.</p><ReviewForm onSave={async values=>{const r=await api('/reviews',{method:'POST',body:values});go(`/reviews/${r.id}`)}}/></>:<Workspace key={path} id={path.split('/').pop()} go={go}/>}
    </main><footer>Semantik SLR · Decisiones humanas, evidencia trazable.</footer></div>
  </div>
}
createRoot(document.getElementById('root')).render(<App/>);
