import React from 'react'

export function ReviewGuide({base,articles,job,busy,onBase,onSearch,onAnalyze,onReview,onReport}){
 const pending=articles.filter(article=>article.decision==='pending')
 const reviewed=articles.length-pending.length
 const hasAnalysis=articles.length>0&&articles.every(article=>article.analysis)
 let title,description,action,label
 if(base&&!base.confirmed){
  title='Confirma el estudio base'
  description='Adjunta el PDF original y verifica el método antes de buscar publicaciones posteriores.'
  action=onBase;label='Ir al estudio base'
 }else if(!articles.length){
  title='Busca los primeros candidatos'
  description='Consulta DOAJ u OpenAlex. Después podrás comparar títulos y resúmenes con tus criterios.'
  action=onSearch;label='Ir a la búsqueda'
 }else if(job){
  title='Estamos comparando los artículos'
  description='El análisis puede tardar unos minutos. Al terminar, vuelve aquí para leer la evidencia y decidir.'
  action=null;label='Análisis en curso'
 }else if(!pending.length){
  title='Prepara el informe de actualización'
  description='Todos los candidatos tienen una decisión. Puedes generar un reporte con la evidencia y el historial.'
  action=onReport;label='Ver informes'
 }else if(!hasAnalysis){
  title='Analiza los candidatos encontrados'
  description='La comparación ordenará los artículos y mostrará fragmentos relevantes para tus criterios.'
  action=onAnalyze;label='Configurar análisis'
 }else if(pending.length){
  title=`Revisa ${pending.length} ${pending.length===1?'artículo pendiente':'artículos pendientes'}`
  description='Abre un candidato, comprueba la fuente y el resumen, y guarda tu decisión con un motivo.'
  action=onReview;label='Revisar el siguiente'
 }
 return <section className="review-guide" aria-label="Siguiente paso"><div className="guide-copy"><span className="guide-label">Siguiente paso</span><h2>{title}</h2><p>{description}</p><div className="guide-progress" aria-label={`${reviewed} de ${articles.length} candidatos revisados`}><span style={{width:articles.length?`${reviewed/articles.length*100}%`:'0%'}}/></div><small>{articles.length?`${reviewed} de ${articles.length} candidatos revisados`:'La revisión comienza con la búsqueda'}</small></div>{action&&<button className="primary" disabled={busy} onClick={action}>{label}</button>}</section>
}
