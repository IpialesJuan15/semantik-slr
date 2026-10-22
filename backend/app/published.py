"""Curated starting point transcribed from the cited open-access publication.

The original studies are provenance records, not newly retrieved candidates. The
fields below are a compact transcription of Tables 1 and 2; the researcher must
confirm them against the PDF before using them in a thesis analysis.
"""

from .sources import normalize_doi

DOI = '10.1186/s41239-022-00326-w'
TITLE = 'Artificial intelligence applications in Latin American higher education: a systematic review'
SOURCE_URL = f'https://doi.org/{DOI}'

QUESTIONS = [
    'What and how AI-based applications are being used by higher education institutions in Latin America?',
    'What are the common AI techniques, software tools, and AI algorithms used in Latin American higher education?',
    'What education topics and issues are being addressed by AI applications in Latin American higher education institutions?',
]
INCLUSION = [
    'Fecha de publicación entre julio de 2016 y junio de 2021.',
    'Publicación en inglés, español o portugués.',
    'Artículo de revista revisada por pares o trabajo de conferencia.',
    'Investigación primaria empírica.',
    'Datos sobre aplicaciones de IA en instituciones de educación superior de América Latina, en particular ML, DL o NLP.',
]
EXCLUSION = [
    'Trabajos conceptuales u opiniones sin investigación empírica primaria.',
    'Trabajos centrados en tecnologías distintas de IA, como realidad virtual o aumentada, 3D o sensores EEG/ECG.',
    'Aplicaciones de agricultura, economía, medicina o industria sin relación con la educación superior latinoamericana.',
]
SOURCES = ['Web of Science', 'IEEE Xplore', 'SciELO', 'CAPES Portal']
SEARCH_STRATEGY = '("artificial intelligence" OR "machine learning" OR "deep learning" OR "natural language processing" OR chatbot* OR "neural network*") AND ("higher education" OR "universit*"), más el nombre de cada país latinoamericano; búsqueda en inglés, español y portugués.'
APPLICATIONS = {
    'Modelos predictivos en educación': [1, 2, 3, 6, 8, 13, 14, 15, 20, 21, 23, 24, 25, 28, 29, 31],
    'Análisis de contenido asistido por IA': [12, 16, 18, 22, 26, 27],
    'Tecnología asistiva (chatbots)': [5, 7, 9, 11, 17],
    'Analítica inteligente (clasificación)': [4, 10, 30],
    'Análisis de imágenes (reconocimiento facial)': [19],
}
# ID, cita abreviada, país. Tabla 1 de Salas-Pilco y Yang (2022), pp. 8–10.
ROWS = [
    (1, 'Bedregal-Alpaca et al. (2020)', 'Perú'),
    (2, 'Bojorque y Pesántez-Avilés (2020)', 'Ecuador'),
    (3, 'Castrillón et al. (2020)', 'Colombia'),
    (4, 'Chacón-Sánchez et al. (2020)', 'Colombia'),
    (5, 'Choque-Díaz et al. (2018)', 'Perú'),
    (6, 'Contreras et al. (2020)', 'Colombia'),
    (7, 'Cordero et al. (2020)', 'Ecuador'),
    (8, 'da Fonseca Silveira et al. (2019)', 'Brasil'),
    (9, 'Dehon et al. (2018)', 'Brasil'),
    (10, 'Delahoz-Dominguez et al. (2020)', 'Colombia'),
    (11, 'Espinosa Rodríguez et al. (2018)', 'México'),
    (12, 'Fiallos et al. (2017)', 'Ecuador'),
    (13, 'García-González y Skrita (2019)', 'Colombia'),
    (14, 'García-Vélez et al. (2019)', 'Ecuador'),
    (15, 'Gómez Cravioto et al. (2020)', 'México'),
    (16, 'Gutiérrez et al. (2018)', 'México'),
    (17, 'Klos et al. (2021)', 'Argentina'),
    (18, 'Mendoza Jurado (2020)', 'Bolivia'),
    (19, 'Menezes et al. (2020)', 'Brasil'),
    (20, 'Miranda y Guzmán (2017)', 'Chile'),
    (21, 'Nieto et al. (2019)', 'Colombia'),
    (22, 'Okoye et al. (2020)', 'México'),
    (23, 'Palacios et al. (2021)', 'Chile'),
    (24, 'Sandoval-Palis et al. (2020)', 'Ecuador'),
    (25, 'Santos et al. (2020)', 'Brasil'),
    (26, 'Sayama et al. (2019)', 'Brasil'),
    (27, 'Tapia-Leon et al. (2017)', 'Ecuador'),
    (28, 'Torres Soto et al. (2019)', 'México'),
    (29, 'Ulloa Cazarez y López Martín (2018)', 'México'),
    (30, 'Villaseñor et al. (2017)', 'México'),
    (31, 'Visbal-Cadavid et al. (2019)', 'Colombia'),
]


def update_inclusion(base):
    """Keep the original date range in provenance, not in new-study screening."""
    return '\n'.join(base['inclusion'][1:] + [
        f'Para la actualización: fecha de publicación posterior a {base["last_included_date"]}.'
    ])


def template(doi):
    if normalize_doi(doi) != DOI:
        raise ValueError('Por ahora solo está preparada la revisión de Salas-Pilco y Yang. Otras revisiones se podrán registrar en una fase posterior.')
    application_by_id = {study_id: name for name, ids in APPLICATIONS.items() for study_id in ids}
    assert len(ROWS) == 31 and set(application_by_id) == set(range(1, 32))
    return {
        'doi': DOI, 'title': TITLE, 'authors': 'Sdenka Zobeida Salas-Pilco; Yuqin Yang',
        'year': 2022, 'source_url': SOURCE_URL, 'license': 'CC BY',
        'questions': QUESTIONS, 'sources': SOURCES, 'search_date': '2021-07',
        'last_included_date': '2021-06-30', 'search_strategy': SEARCH_STRATEGY,
        'inclusion': INCLUSION, 'exclusion': EXCLUSION,
        'original_count': 31, 'initial_candidates': 2397,
        'studies': [{'original_id': ident, 'citation': citation, 'country': country,
                     'application': application_by_id[ident], 'source_table': 'Tabla 1, pp. 8–10'}
                    for ident, citation, country in ROWS],
        'application_counts': [{'name': name, 'count': len(ids), 'source_table': 'Tabla 2, p. 11'}
                               for name, ids in APPLICATIONS.items()],
        'method_source': 'Texto del artículo aportado por el investigador; método, pp. 5–7; tablas 1 y 2, pp. 8–11.',
        'coverage_note': 'DOAJ y OpenAlex no replican las cuatro bases originales ni sus consultas multilingües. La estrategia debe revisarse antes de declarar una actualización sistemática.',
    }
