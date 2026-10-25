import React from 'react'

export function SearchReceipt({event,onSearch}){
 if(!event)return null
 const result=event.payload
 const end=result.date_to||`${result.year_to}-12-31`
 const partial=result.total_available!=null&&result.total_available>result.retrieved
 return <section className="search-receipt" aria-label="Última búsqueda registrada">
  <div className="receipt-heading"><div><small>Última búsqueda registrada</small><h2>{result.source} · {result.date_from} a {end}</h2></div><span className="receipt-status">{partial?'Resultados por recorrer':'Consulta limitada'}</span></div>
  <details className="receipt-details"><summary><span>Consulta: <strong>{result.query}</strong></span><span><b>{result.retrieved}</b> recuperados · <b>{result.added}</b> nuevos</span></summary><div className="receipt-facts"><span><b>{result.retrieved}</b> {result.retrieved===1?'recuperado':'recuperados'} en esta consulta</span><span><b>{result.added}</b> {result.added===1?'candidato añadido':'candidatos añadidos'}</span>{result.total_available!=null&&<span><b>{result.total_available}</b> {result.total_available===1?'resultado indicado':'resultados indicados'} por la fuente</span>}</div><p className="receipt-explain">{partial?'Esta consulta recuperó solo parte de los resultados de la fuente.':'Esta consulta terminó su página de resultados; otras fuentes y estrategias aún pueden aportar estudios.'} Cambiar las fechas no elimina candidatos guardados.</p><button type="button" onClick={onSearch}>Cambiar consulta o fechas</button></details>
 </section>
}
