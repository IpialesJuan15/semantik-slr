import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const blank = { title: '', question: '', inclusion: '', exclusion: '' }

function Icon({ name, size = 20 }) {
  const paths = {
    layers: <><rect x="4" y="4" width="13" height="15" rx="2" /><path d="M8 8h5M8 12h5M19 8h1v12a2 2 0 0 1-2 2H9" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    left: <path d="m15 18-6-6 6-6" />,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    book: <><path d="M3 5.5C6 4 9 4 12 6c3-2 6-2 9-.5V19c-3-1.5-6-1.5-9 .5-3-2-6-2-9-.5z" /><path d="M12 6v13.5" /></>,
    spark: <path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8zM19 17l.6 1.4L21 19l-1.4.6L19 21l-.6-1.4L17 19l1.4-.6z" />,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

async function api(path, options) {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) throw new Error(response.status === 404 ? 'No encontramos esa revisión.' : 'No se pudo completar la operación. Inténtalo de nuevo.')
  return response.json()
}

function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [reviews, setReviews] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [values, setValues] = useState(blank)
  const [saving, setSaving] = useState(false)

  function navigate(to) {
    window.history.pushState({}, '', to)
    setPath(to)
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    if (path === '/') {
      api('/reviews').then(data => { if (active) setReviews(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    } else if (path.startsWith('/reviews/') && path !== '/reviews/new') {
      api(path).then(data => { if (active) setSelected(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    } else {
      setLoading(false)
    }
    return () => { active = false }
  }, [path])

  async function submit(event) {
    event.preventDefault()
    setError('')
    const data = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()]))
    if (Object.values(data).some(value => !value)) {
      setError('Completa todos los campos para guardar la revisión.')
      return
    }
    setSaving(true)
    try {
      const review = await api('/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
      setValues(blank)
      navigate(`/reviews/${review.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const filtered = reviews.filter(review => `${review.title} ${review.question}`.toLowerCase().includes(search.toLowerCase()))
  const open = (event, to) => { event.preventDefault(); navigate(to) }
  const link = (to, text, className = '') => <a href={to} className={className} onClick={event => open(event, to)}>{text}</a>

  return <div className="shell">
    <a className="skip" href="#content">Ir al contenido</a>
    <aside className="sidebar">
      {link('/', <><span className="brand-mark"><Icon name="layers" size={19} /></span><span className="brand-name">semantik<span>SLR</span></span></>, 'brand')}
      <div className="side-section">ESPACIO DE TRABAJO</div>
      {link('/', <><Icon name="grid" size={19} /> Mis revisiones</>, `side-link ${path === '/' ? 'active' : ''}`)}
      {link('/reviews/new', <><Icon name="plus" size={19} /> Nueva revisión</>, `side-link ${path === '/reviews/new' ? 'active' : ''}`)}
      <div className="sidebar-bottom"><span className="status-dot" /> Primera fase en desarrollo<p>Define y consulta el protocolo de tu revisión sistemática.</p></div>
    </aside>
    <div className="page">
      <header className="topbar"><div className="breadcrumbs">Espacio de trabajo <span>/</span> <strong>{path === '/reviews/new' ? 'Nueva revisión' : path === '/' ? 'Mis revisiones' : 'Detalle de revisión'}</strong></div><span className="top-pill"><Icon name="spark" size={16} /> Prototipo académico</span></header>
      <main id="content" className="content">
        {error && <div className="alert" role="alert">{error}</div>}
        {path === '/' && <>
          <div className="eyebrow"><span className="eyebrow-line" /> TU BIBLIOTECA CIENTÍFICA</div>
          <div className="page-head"><div><h1>Mis revisiones<span className="period">.</span></h1><p>Un punto de partida claro para mantener viva tu investigación.</p></div>{link('/reviews/new', <><Icon name="plus" size={18} /> Nueva revisión</>, 'primary-button')}</div>
          <div className="stats"><div className="stat"><div className="stat-icon teal"><Icon name="book" /></div><div><strong>{reviews.length}</strong><span>Revisiones registradas</span></div></div><div className="stat"><div className="stat-icon amber"><Icon name="clock" /></div><div><strong>01</strong><span>Fase actual · Protocolo</span></div></div></div>
          <div className="section-heading"><div><h2>Tus proyectos</h2><p>Revisiones en las que estás trabajando</p></div><label className="search"><Icon name="search" size={18} /><input aria-label="Buscar revisiones" placeholder="Buscar revisión..." value={search} onChange={event => setSearch(event.target.value)} /></label></div>
          {loading ? <div className="placeholder">Cargando tus revisiones…</div> : filtered.length ? <div className="review-grid">{filtered.map(review => <article className="review-card" key={review.id}><div className="card-top"><span className="stage"><span className="stage-dot" /> PROTOCOLO</span><span className="card-index">#{String(review.id).padStart(2, '0')}</span></div><h3>{review.title}</h3><p>{review.question}</p><div className="card-footer"><span>{new Date(review.created_at).toLocaleDateString('es-EC', { day: 'numeric', month: 'short', year: 'numeric' })}</span>{link(`/reviews/${review.id}`, <><span>Ver revisión</span><Icon name="arrow" size={16} /></>, 'card-link')}</div></article>)}</div> : <div className="empty"><span className="empty-icon"><Icon name={search ? 'search' : 'book'} size={32} /></span><h3>{search ? 'Sin resultados' : 'Empieza con tu primera revisión'}</h3><p>{search ? 'Prueba con otro título o pregunta.' : 'Registra tu pregunta de investigación y los criterios para seleccionar estudios.'}</p>{!search && link('/reviews/new', <><Icon name="plus" size={17} /> Crear revisión</>, 'primary-button')}</div>}
          <div className="next-banner"><div className="next-icon"><Icon name="spark" size={23} /></div><div><strong>Un protocolo sólido es el primer paso.</strong><p>La búsqueda de artículos y el análisis semántico llegarán en las siguientes fases.</p></div></div>
        </>}
        {path === '/reviews/new' && <>
          {link('/', <><Icon name="left" size={16} /> Volver a mis revisiones</>, 'back-link')}
          <div className="eyebrow"><span className="eyebrow-line" /> PASO 01 · CONFIGURACIÓN</div>
          <h1>Nueva revisión<span className="period">.</span></h1><p className="intro">Define qué quieres investigar y cómo seleccionarás la evidencia.</p>
          <div className="form-layout"><form className="form-card" onSubmit={submit}><div className="form-section-head"><span className="form-number">01</span><div><h2>Información del protocolo</h2><p>Esta información servirá de base para las búsquedas futuras.</p></div></div>
            {[['title', 'Título de la revisión', 'Por ejemplo: Inteligencia artificial en educación superior', 200, 'Un nombre claro para identificar tu proyecto.'], ['question', 'Pregunta de investigación', '¿Cómo se utiliza la inteligencia artificial para apoyar el aprendizaje universitario?', 2000, 'La pregunta que guiará la selección de estudios.'], ['inclusion', 'Criterios de inclusión', 'Por ejemplo: Estudios con estudiantes universitarios.', 10000, 'Escribe un criterio por línea.'], ['exclusion', 'Criterios de exclusión', 'Por ejemplo: Estudios centrados exclusivamente en educación escolar.', 10000, 'Escribe un criterio por línea.']].map(([key, label, placeholder, max, help]) => <div className="field" key={key}><label htmlFor={key}>{label}<span> *</span></label><small>{help}</small>{key === 'title' ? <input id={key} value={values[key]} maxLength={max} onChange={event => setValues({ ...values, [key]: event.target.value })} placeholder={placeholder} required /> : <textarea id={key} value={values[key]} maxLength={max} rows={4} onChange={event => setValues({ ...values, [key]: event.target.value })} placeholder={placeholder} required />}</div>)}
            <div className="form-footer">{link('/', 'Cancelar', 'text-button')}<button className="primary-button" disabled={saving} type="submit">{saving ? 'Guardando…' : 'Guardar revisión'} <Icon name="arrow" size={17} /></button></div>
          </form><div className="tip-card"><span className="tip-icon"><Icon name="spark" /></span><h3>Consejo metodológico</h3><p>Estos datos son el punto de partida. Cuando elijas la revisión sistemática base, confirma su pregunta y sus criterios originales antes de buscar nuevos estudios.</p><div className="tip-foot"><Icon name="check" size={16} /> Puedes empezar con un ejemplo y crear otra revisión después.</div></div></div>
        </>}
        {path.startsWith('/reviews/') && path !== '/reviews/new' && <>
          {link('/', <><Icon name="left" size={16} /> Volver a mis revisiones</>, 'back-link')}
          {loading ? <div className="placeholder">Cargando revisión…</div> : selected && <><div className="eyebrow"><span className="eyebrow-line" /> REVISIÓN #{String(selected.id).padStart(2, '0')}</div><h1 className="detail-title">{selected.title}<span className="period">.</span></h1><div className="detail-meta"><span className="stage"><span className="stage-dot" /> PROTOCOLO REGISTRADO</span><span>Creada el {new Date(selected.created_at).toLocaleDateString('es-EC', { day: 'numeric', month: 'long', year: 'numeric' })}</span></div><section className="detail-card"><div className="detail-label"><span className="detail-number">01</span> PREGUNTA DE INVESTIGACIÓN</div><p className="research-question">{selected.question}</p></section><div className="criteria-grid"><section className="detail-card"><div className="detail-label"><span className="detail-number include">+</span> CRITERIOS DE INCLUSIÓN</div><ul>{selected.inclusion.split('\n').filter(Boolean).map((line, index) => <li key={index}>{line}</li>)}</ul></section><section className="detail-card"><div className="detail-label"><span className="detail-number exclude">−</span> CRITERIOS DE EXCLUSIÓN</div><ul>{selected.exclusion.split('\n').filter(Boolean).map((line, index) => <li key={index}>{line}</li>)}</ul></section></div><div className="next-banner"><div className="next-icon"><Icon name="check" /></div><div><strong>Tu protocolo está guardado.</strong><p>Puedes volver a consultarlo desde Mis revisiones. La búsqueda de artículos se añadirá en una próxima fase.</p></div></div></>}
        </>}
      </main><footer>Semantik SLR <span>·</span> Plataforma de vigilancia científica <span>·</span> Prototipo académico</footer>
    </div>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
