import React from 'react'

export function SearchPanel({base,source,setSource,query,setQuery,from,setFrom,to,setTo,limit,setLimit,busy,status,onBase,onSearch}){
 return <section className="panel"><div className="section-heading"><div><h2>Buscar publicaciones nuevas</h2><p>Elige una fuente de acceso abierto. Se registrará la procedencia de cada consulta y de cada artículo incorporado.</p></div><span className="pill">{source==='openalex'?'OpenAlex':'DOAJ'}</span></div>
 {base&&!base.confirmed&&<p className="notice">Adjunta el PDF y confirma el método del estudio base antes de buscar. <button onClick={onBase}>Ir al estudio base</button></p>}
 <form onSubmit={event=>{event.preventDefault();onSearch({source,query,year_from:Number(from),year_to:Number(to),limit:Number(limit)})}}>
  <label className="field"><span>Fuente</span><select value={source} onChange={event=>setSource(event.target.value)}><option value="openalex">OpenAlex · cobertura amplia</option><option value="doaj">DOAJ · revistas de acceso abierto</option></select></label>
  <label className="field"><span>Consulta de búsqueda</span><input required minLength={3} maxLength={1000} value={query} onChange={event=>setQuery(event.target.value)} placeholder="artificial intelligence higher education"/></label>
  <div className="search-options"><label>Desde<input aria-label="Año inicial" type="number" min="1800" max="2100" value={from} onChange={event=>setFrom(event.target.value)} required/></label><label>Hasta<input aria-label="Año final" type="number" min="1800" max="2100" value={to} onChange={event=>setTo(event.target.value)} required/></label><label>Máximo<select value={limit} onChange={event=>setLimit(event.target.value)}><option>25</option><option>50</option><option>100</option></select></label><button className="primary" disabled={busy||(base&&!base.confirmed)}>{busy?'Consultando…':'Buscar en '+(source==='openalex'?'OpenAlex':'DOAJ')}</button></div>
 </form>
 {source==='openalex'?<p className="fine-print">{status?.openalex_key_configured?'Hay una clave de OpenAlex configurada.':'Sin clave, OpenAlex comparte una cuota diaria con otras personas de tu red.'} Si alcanzas el límite, puedes probar DOAJ o <a href="https://openalex.org/settings/api" target="_blank" rel="noreferrer">obtener una clave gratuita de OpenAlex</a>.</p>:<p className="fine-print">DOAJ agrupa revistas de acceso abierto. Suele informar solo el año: verifica la fecha exacta de los trabajos de 2021 antes de incluirlos.</p>}
 <p className="fine-print">La consulta empieza como mínimo después del 30 de junio de 2021 para este caso base. Una búsqueda limitada en estas fuentes no reproduce Web of Science, IEEE Xplore, SciELO y CAPES ni acredita exhaustividad.</p>
 </section>
}
