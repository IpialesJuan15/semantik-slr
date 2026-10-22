import React, {useEffect,useState} from 'react'

export function AnalysisPanel({articles,engine,setEngine,busy,job,status,onStart,onEvaluate,evaluation}){
 const included=articles.filter(article=>article.decision==='included').length
 const excluded=articles.filter(article=>article.decision==='excluded').length
 const complete=articles.length>0&&articles.every(article=>article.analysis)
 const [expanded,setExpanded]=useState(!complete)
 useEffect(()=>setExpanded(!complete),[complete])
 return <section className={`panel analysis-panel ${expanded?'':'compact-analysis'}`} id="analysis-controls"><div className="section-heading"><div><h2>{complete?'Análisis disponible':'Analizar candidatos'}</h2><p>{complete?'Los fragmentos de evidencia están en el detalle de cada artículo.':'Compara títulos y resúmenes con los criterios. Después revisa los fragmentos en cada artículo.'}</p></div>{complete?<button type="button" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>{expanded?'Cerrar opciones':'Volver a analizar'}</button>:<span className="pill">Apoyo a la revisión</span>}</div>
 {expanded&&<>
  <div className="analysis-inline"><label className="field"><span>Método de comparación</span><select value={engine} onChange={event=>setEngine(event.target.value)}><option value="lexical">TF-IDF · sin descarga adicional</option><option value="semantic">Similitud semántica · modelo local</option></select></label><button className="primary" disabled={busy||!!job||!articles.length} onClick={onStart}>{job?'Analizando…':'Analizar artículos'}</button></div>
  <p className="fine-print">{engine==='semantic'?`Usa ${status?.model||'MiniLM multilingüe'}. Requiere activar-ia.bat la primera vez.`:'TF-IDF funciona con la instalación básica y compara palabras, no equivalencias de significado.'} Los puntajes orientan el orden de lectura; la decisión siempre es tuya.</p>
  <details className="advanced-analysis"><summary>Evaluación exploratoria para la tesis</summary><p>Con al menos 3 incluidos y 3 excluidos, un nuevo análisis puede entrenar un clasificador experimental. Para calcular precisión, recall y F1 locales necesitas al menos 5 de cada clase. Estas cifras no demuestran cobertura de la búsqueda ni validación independiente.</p><p>Decisiones disponibles: {included} incluidos y {excluded} excluidos.</p><button disabled={busy||!!job||included<5||excluded<5} onClick={onEvaluate}>Calcular precisión, recall y F1</button>{evaluation&&<p className="fine-print">Precisión {evaluation.precision.toFixed(3)} · Recall {evaluation.recall.toFixed(3)} · F1 {evaluation.f1.toFixed(3)}. {evaluation.limitation}</p>}</details></>}
 </section>
}
