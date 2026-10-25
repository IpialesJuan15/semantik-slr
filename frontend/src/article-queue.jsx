import React from 'react'
import {labels} from './api.js'

export function ArticleQueue({articles,visible,selected,onSelect,query,onQuery,status,onStatus,yearView,onYearView,fromDate,toDate,recheckCount}){
 const filtered=status!=='all'||yearView!=='all'||query.trim()
 const pending=articles.filter(article=>article.decision==='pending').length
 return <div className="queue-side">
  <div className="queue-heading"><div><h2>Lista de lectura</h2><p>{visible.length} {visible.length===1?'visible':'visibles'} de {articles.length} {articles.length===1?'candidato':'candidatos'} · {pending} {pending===1?'pendiente':'pendientes'} en total</p></div></div>
  <div className="queue-filter-panel">
   <label className="field queue-search"><span>Buscar artículo</span><input type="search" value={query} onChange={event=>onQuery(event.target.value)} placeholder="Título o autor"/></label>
   <details className="queue-more-filters"><summary>Filtrar por decisión o año{(status!=='all'||yearView!=='all')?' · activos':''}</summary><div className="queue-filter-grid"><label className="field"><span>Decisión</span><select value={status} onChange={event=>onStatus(event.target.value)}><option value="all">Todas</option>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}{recheckCount>0&&<option value="recheck">Revisar por protocolo ({recheckCount})</option>}</select></label>
   <label className="field"><span>Años guardados</span><select value={yearView} onChange={event=>onYearView(event.target.value)}><option value="all">Todos los años</option><option value="range">Solo {fromDate.slice(0,4)}–{toDate.slice(0,4)}</option></select></label></div><p>Los filtros solo cambian esta lista.</p></details>
   {filtered&&<button type="button" className="subtle-button clear-filters" onClick={()=>{onQuery('');onStatus('all');onYearView('all')}}>Quitar filtros</button>}
  </div>
  {!visible.length?<div className="empty queue-empty"><h3>{articles.length?'No hay candidatos con estos filtros':'Todavía no hay candidatos'}</h3><p>{articles.length?'Prueba otros años o decisiones.':'Busca en DOAJ u OpenAlex o importa artículos.'}</p>{filtered&&<button type="button" onClick={()=>{onQuery('');onStatus('all');onYearView('all')}}>Mostrar todos</button>}</div>:
   <div className="article-list">{visible.map(article=><button type="button" className={'article-row '+(selected===article.id?'chosen':'')} key={article.id} onClick={()=>onSelect(article.id)} aria-current={selected===article.id?'true':undefined}><span className="article-copy"><strong>{article.title}</strong><small>{article.year||'Sin año'} · {article.source} · {article.authors||'Autores no registrados'}</small></span><span className={'state '+article.decision}>{labels[article.decision]}</span><span className="score">{article.score===null?'Sin analizar':`Parecido ${article.score.toFixed(2)}`}</span></button>)}</div>}
 </div>
}
