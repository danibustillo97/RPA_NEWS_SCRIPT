"""
Datos de referencia de dominio para la ingestión de LAB.

Clasificación (docs/LAB_ARCHITECTURE_AUDIT.md sección N.2): REUSE — estos
diccionarios estaban triplicados y ligeramente distintos entre `main.py`,
`script.py` y `src/sources_config/sources.py`. Acá quedan consolidados en
un solo lugar, como **datos de referencia/contexto**, no como mecanismo
de decisión editorial.

Deliberadamente NO incluye las funciones `detect_category/league/country/
team()` que tenía `main.py` — esas están clasificadas LEGACY (sección
N.2): eran exactamente la "inteligencia editorial débil" que Claude Code
reemplaza. Los diccionarios siguen siendo útiles como contexto que las
skills editoriales de Claude Code pueden consultar en fases posteriores,
pero la ingestión de Fase 1 no los usa para clasificar nada — solo trae
materia prima cruda, sin opinar.

NEWS_SOURCES reutiliza la lista completa de `main.py` (54 fuentes) tal
cual — decidir si conviene acotarla a fuentes puramente deportivas es una
decisión editorial pendiente (auditoría, sección "Riesgos"), no algo que
LAB decida solo en Fase 1.
"""

LEAGUE_KEYWORDS: dict[str, str] = {
    "premier": "Premier League", "laliga": "La Liga", "liga española": "La Liga",
    "bundesliga": "Bundesliga", "serie a": "Serie A", "champions": "Champions League",
    "libertadores": "Copa Libertadores", "sudamericana": "Copa Sudamericana", "mls": "MLS",
    "colombia": "Liga BetPlay", "argentina": "Liga Profesional Argentina",
    "brasil": "Brasileirão", "liga mx": "Liga MX", "ecuador": "LigaPro",
    "perú": "Liga 1", "uruguay": "Primera División Uruguay",
    "paraguay": "Primera División Paraguay", "chile": "Primera División Chile",
}

COUNTRIES: list[str] = [
    "colombia", "españa", "argentina", "brasil", "méxico", "alemania", "inglaterra",
    "italia", "francia", "ecuador", "perú", "uruguay", "chile", "paraguay",
    "venezuela", "estados unidos",
]

TEAMS: list[str] = [
    "junior", "junior de barranquilla", "barcelona", "real madrid", "manchester",
    "liverpool", "juventus", "bayern", "inter", "milan", "river", "boca", "nacional",
    "américa", "santa fe", "medellín", "atlético nacional", "flamengo", "palmeiras",
    "pumas", "chivas", "cruz azul",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "deporte": ["fútbol", "liga", "gol", "equipo", "partido", "copa", "jugador", "deporte", "champions", "final"],
    "economía": ["economía", "bolsa", "dólar", "finanzas", "impuestos", "negocios", "banco", "comercio"],
    "política": ["política", "elección", "congreso", "senado", "presidente", "ministro", "gobierno", "alcalde"],
    "salud": ["salud", "virus", "covid", "enfermedad", "hospital", "vacuna", "medicina"],
    "tecnología": ["tecnología", "software", "hardware", "internet", "redes sociales", "ciencia", "robot", "inteligencia artificial"],
    "internacional": ["eeuu", "china", "rusia", "venezuela", "ucrania", "naciones unidas", "acuerdo", "conflicto", "europa"],
    "cultura": ["cultura", "cine", "música", "arte", "literatura", "concierto", "exposición"],
    "entretenimiento": ["farandula", "celebridad", "espectáculo", "show", "televisión", "reality"],
    "judicial": ["corte", "justicia", "denuncia", "proceso", "fiscalía", "juez", "sentencia"],
    "colombia": ["colombia", "bogotá", "medellín", "cali", "barranquilla", "cartagena"],
}

# Idéntica a NEWS_SOURCES de main.py (líneas 67-83) — misma fuente probada.
NEWS_SOURCES: list[str] = [
    "https://www.eltiempo.com/", "https://www.elcolombiano.com/", "https://www.semana.com/",
    "https://caracol.com.co/", "https://www.rcnradio.com/", "https://www.larepublica.co/",
    "https://www.bluradio.com/", "https://www.elespectador.com/", "https://noticias.canal1.com.co/",
    "https://www.vanguardia.com/", "https://www.elheraldo.co/", "https://zonacero.com/",
    "https://www.adnradio.com.co/", "https://www.elpais.com.co/", "https://www.antena2.com/",
    "https://www.futbolred.com/", "https://deportes.canalrcn.com/", "https://www.infobae.com/",
    "https://www.tycsports.com/", "https://www.ole.com.ar/", "https://www.clarin.com/",
    "https://www.lanacion.com.ar/", "https://www.marca.com/", "https://as.com/",
    "https://www.mundodeportivo.com/", "https://www.elmundo.es/", "https://elpais.com/",
    "https://cnnespanol.cnn.com/", "https://www.bbc.com/mundo", "https://www.eluniverso.com/",
    "https://www.abc.es/", "https://www.20minutos.es/", "https://www.expansion.com/",
    "https://www.xataka.com/", "https://hipertextual.com/", "https://www.fayerwayer.com/",
    "https://techcetera.co/", "https://www.dw.com/es/", "https://www.nytimes.com/es/",
    "https://www.nationalgeographic.com.es/", "https://www.noticiasrcn.com/tecnologia",
    "https://www.portafolio.co/", "https://www.dinero.com/", "https://forbes.co/",
    "https://www.sopitas.com/", "https://www.latercera.com/", "https://www.bolavip.com/",
    "https://www.goal.com/es", "https://www.elcomercio.pe/", "https://www.elbocon.pe/",
    "https://www.larepublica.pe/", "https://www.mediotiempo.com/",
    "https://www.debate.com.mx/deportes/", "https://www.univision.com/noticias/",
    "https://www.culturagenial.com/es/", "https://www.elcultural.com/",
    "https://www.elconfidencial.com/cultura/",
]
