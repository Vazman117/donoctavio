# scraper_mundial.py
#
# INSTALAR:
# pip install requests
#
# EJECUTAR:
# python scraper_mundial.py
#
# GENERA:
# /mundial/data/grupos.json       → posiciones por grupo
# /mundial/data/tabla.json        → tabla general
# /mundial/data/selecciones.json  → stats completas por selección
# /mundial/data/fixture.json      → partidos de hoy y mañana

import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone

# =====================================================
# CONFIG
# =====================================================

BASE_ESPN    = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
BASE_ESPN_V2 = "https://site.api.espn.com/apis/v2/sports/soccer"
BASE_SOCCER  = "https://site.api.espn.com/apis/site/v2/sports/soccer"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ------------------------------------------------------------------
# Altitud base conocida por selección (metros sobre el nivel del mar)
# ------------------------------------------------------------------
ALTITUD_BASE = {
    "ARG": 25,   "BOL": 3640, "BRA": 10,  "CHI": 520,  "COL": 2600,
    "ECU": 2850, "PAR": 124,  "PER": 154, "URU": 43,   "VEN": 900,
    "USA": 0,    "CAN": 116,  "MEX": 2240,"CRC": 1170, "JAM": 40,
    "PAN": 0,    "HON": 900,  "GUA": 1500,"SLV": 658,  "TRI": 11,
    "AUT": 171,  "BEL": 56,   "CRO": 122, "CZE": 399,  "DEN": 12,
    "ENG": 24,   "FRA": 35,   "GER": 117, "GRE": 170,  "HUN": 102,
    "ITA": 21,   "NED": 0,    "POL": 90,  "POR": 92,   "ROU": 85,
    "SCO": 15,   "SRB": 117,  "SLO": 295, "ESP": 650,  "SWE": 28,
    "SWZ": 540,  "TUR": 938,  "UKR": 179, "WAL": 50,   "ALB": 110,
    "BIH": 511,  "BUL": 550,  "GEO": 380, "ISL": 18,
    "KOS": 652,  "LVA": 7,    "MDA": 30,  "MKD": 245,  "MNE": 21,
    "NOR": 23,   "SVK": 172,  "FIN": 26,
    "EGY": 23,   "GHA": 61,   "CIV": 226, "MAR": 495,  "NGA": 60,
    "SEN": 22,   "TUN": 50,   "CMR": 760, "MLI": 381,  "ALG": 424,
    "RSA": 1700, "TAN": 1130, "ZIM": 1483,"UGA": 1189, "KEN": 1661,
    "AUS": 0,    "JPN": 40,   "KOR": 37,  "IRN": 1191, "SAU": 620,
    "QAT": 10,   "UAE": 5,    "CHN": 43,  "IDN": 8,    "IND": 216,
    "PHI": 15,   "THA": 2,    "MYS": 22,  "VIE": 12,   "BHR": 0,
    "OMA": 20,   "JOR": 820,  "IRQ": 34,  "SYR": 690,  "KUW": 55,
    "NZL": 30,   "FIJ": 18,
}

# ------------------------------------------------------------------
# Ranking FIFA masculino — edición abril 2026
# ------------------------------------------------------------------
RANKING_FIFA = {
    "ESP": (1,  1877.2), "ARG": (2,  1873.3), "FRA": (3,  1870.0),
    "ENG": (4,  1834.1), "BRA": (5,  1782.1), "POR": (6,  1764.9),
    "NED": (7,  1757.4), "BEL": (8,  1741.7), "GER": (9,  1720.0),
    "ITA": (10, 1711.5), "URU": (11, 1690.4), "COL": (12, 1687.2),
    "CRO": (13, 1658.7), "JPN": (14, 1650.5), "MAR": (15, 1645.1),
    "USA": (16, 1633.9), "MEX": (17, 1622.8), "SEN": (18, 1617.6),
    "DEN": (19, 1611.9), "SWZ": (20, 1609.2), "NOR": (21, 1600.4),
    "AUT": (22, 1595.7), "EGY": (23, 1589.3), "TUR": (24, 1584.1),
    "UKR": (25, 1572.6), "GHA": (26, 1560.8), "CIV": (27, 1551.3),
    "KOR": (28, 1545.9), "AUS": (29, 1539.4), "POL": (30, 1532.1),
    "IRN": (31, 1528.7), "PAR": (32, 1521.4), "RSA": (33, 1514.8),
    "ECU": (34, 1508.3), "SRB": (35, 1501.7), "CZE": (36, 1495.2),
    "CMR": (37, 1488.6), "BOL": (38, 1482.1), "SVK": (39, 1475.4),
    "HUN": (40, 1468.9), "NGA": (41, 1462.3), "NZL": (42, 1455.8),
    "SAU": (43, 1449.2), "CAN": (44, 1442.7), "TUN": (45, 1436.1),
    "PAN": (46, 1429.6), "ALB": (47, 1423.0), "GUA": (48, 1416.5),
    "VEN": (49, 1410.0), "CHN": (79, 1302.5), "IDN": (130, 1180.0),
}

# ------------------------------------------------------------------
# Sedes oficiales del Mundial 2026
# ------------------------------------------------------------------
SEDES_MUNDIAL = [
    {"ciudad": "Ciudad de México",       "pais": "MEX", "alt": 2240,
     "keywords": ["azteca","banorte","mexico city stadium","estadio ciudad de mexico"]},
    {"ciudad": "Guadalajara, Jalisco",   "pais": "MEX", "alt": 1566,
     "keywords": ["akron","guadalajara stadium","estadio akron"]},
    {"ciudad": "Monterrey, Nuevo León",  "pais": "MEX", "alt": 538,
     "keywords": ["bbva","bancomer","monterrey stadium","estadio bbva"]},
    {"ciudad": "Los Angeles, California","pais": "USA", "alt": 93,
     "keywords": ["sofi","sofi stadium","inglewood"]},
    {"ciudad": "Pasadena, California",   "pais": "USA", "alt": 236,
     "keywords": ["rose bowl"]},
    {"ciudad": "San Francisco Bay Area, California","pais": "USA","alt": 16,
     "keywords": ["levi","levis","santa clara"]},
    {"ciudad": "Seattle, Washington",    "pais": "USA", "alt": 0,
     "keywords": ["lumen field","lumen"]},
    {"ciudad": "East Rutherford, New Jersey","pais": "USA","alt": 5,
     "keywords": ["metlife","met life","new york stadium","new jersey"]},
    {"ciudad": "Philadelphia, Pennsylvania","pais": "USA","alt": 12,
     "keywords": ["lincoln financial","lincoln field","philadelphia stadium"]},
    {"ciudad": "Foxborough, Massachusetts","pais": "USA","alt": 25,
     "keywords": ["gillette","foxborough","boston stadium"]},
    {"ciudad": "Miami Gardens, Florida", "pais": "USA", "alt": 3,
     "keywords": ["hard rock","miami stadium","miami gardens"]},
    {"ciudad": "Arlington, Texas",       "pais": "USA", "alt": 188,
     "keywords": ["at&t stadium","att stadium","dallas stadium","arlington"]},
    {"ciudad": "Kansas City, Missouri",  "pais": "USA", "alt": 325,
     "keywords": ["arrowhead","kansas city"]},
    {"ciudad": "Houston, Texas",         "pais": "USA", "alt": 12,
     "keywords": ["nrg stadium","nrg","houston stadium"]},
    {"ciudad": "Atlanta, Georgia",       "pais": "USA", "alt": 320,
     "keywords": ["mercedes-benz","mercedes benz","atlanta stadium","georgia dome"]},
    {"ciudad": "Vancouver, British Columbia","pais": "CAN","alt": 4,
     "keywords": ["bc place","bc place stadium","vancouver"]},
    {"ciudad": "Toronto, Ontario",       "pais": "CAN", "alt": 76,
     "keywords": ["bmo field","bmo","toronto"]},
]

# =====================================================
# LEAGUES HISTÓRICAS — trasplantadas de scrapper_selecciones.py
# Orden: eliminatorias primero → torneos continentales → amistosos
# =====================================================

_LEAGUES_POR_CONF = {
    "UEFA": [
        "uefa.euroq",
        "uefa.nations",
        "uefa.euro",
        "fifa.world",
        "fifa.friendly",
    ],
    "CONMEBOL": [
        "conmebol.world.qualifier",
        "conmebol.america",
        "fifa.world",
        "fifa.friendly",
    ],
    "CONCACAF": [
        "concacaf.world.qualifier",
        "concacaf.nations.league",
        "concacaf.gold",
        "fifa.world",
        "fifa.friendly",
    ],
    "CAF": [
        "caf.qualifier",
        "caf.nations",
        "fifa.world",
        "fifa.friendly",
    ],
    "AFC": [
        "afc.qualifier",
        "afc.asian.cup",
        "fifa.world",
        "fifa.friendly",
    ],
    "OFC": [
        "ofc.nations",
        "fifa.friendly",
    ],
}

# Rangos de fechas — cubre todo el ciclo clasificatorio al Mundial 2026
_RANGOS_HISTORICOS = [
    "20230901-20231130",
    "20231201-20240229",
    "20240301-20240531",
    "20240601-20240831",
    "20240901-20241130",
    "20241201-20250228",
    "20250301-20250531",
    "20250601-20250831",
    "20250901-20251130",
    "20251201-20260229",
    "20260301-20260531",
    "20260601-20260610",
]

# Tipos de competencia → oficial / amistoso
_TIPOS_COMPETENCIA = {
    "fifa world cup":          "oficial",
    "copa america":            "oficial",
    "gold cup":                "oficial",
    "concacaf nations league": "oficial",
    "world cup qualifier":     "oficial",
    "world cup qualifying":    "oficial",
    "euro":                    "oficial",
    "nations league":          "oficial",
    "africa cup":              "oficial",
    "asian cup":               "oficial",
    "olympics":                "oficial",
    "friendly":                "amistoso",
    "international friendly":  "amistoso",
    "amistoso":                "amistoso",
}

# Mapa de confederaciones
_CONF_MAP: dict[str, str] = {}

def _build_conf_map():
    uefa = {
        "albania","andorra","armenia","austria","azerbaijan","belarus","belgium",
        "bosniaandherzegovina","bosniaherzegovina","bulgaria","croatia","cyprus",
        "czechrepublic","denmark","england","estonia","faroeislands","finland",
        "france","georgia","germany","greece","hungary","iceland","ireland",
        "israel","italy","kazakhstan","kosovo","latvia","liechtenstein","lithuania",
        "luxembourg","malta","moldova","montenegro","netherlands","northmacedonia",
        "norway","poland","portugal","romania","russia","sanmarino","scotland",
        "serbia","slovakia","slovenia","spain","sweden","switzerland","turkey",
        "ukraine","wales","northernireland","gibraltar",
    }
    conmebol = {
        "argentina","bolivia","brazil","brasil","chile","colombia","ecuador",
        "paraguay","peru","uruguay","venezuela",
    }
    concacaf = {
        "antigua","antiguaandbarbuda","bahamas","barbados","belize","bermuda",
        "canada","caymanislands","costarica","cuba","curacao","dominicanrepublic",
        "elsalvador","grenada","guatemala","guyana","haiti","honduras","jamaica",
        "martinique","mexico","nicaragua","panama","saintlucia","saintkitts",
        "suriname","trinidadandtobago","usa","unitedstates","trinidadtobago",
    }
    for n in uefa:     _CONF_MAP[n] = "UEFA"
    for n in conmebol: _CONF_MAP[n] = "CONMEBOL"
    for n in concacaf: _CONF_MAP[n] = "CONCACAF"

_build_conf_map()


# =====================================================
# HELPERS
# =====================================================

def guardar_json(nombre, data):
    ruta = os.path.join(DATA_DIR, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {nombre} generado")


def stat(stats, name, default=0):
    for s in stats:
        if s.get("name") == name:
            return s.get("value", default)
    return default


def get_json(url, params=None, reintentos=3):
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                print(f"  ⏳ Rate limit, esperando 10s...")
                time.sleep(10)
            elif r.status_code in (400, 404):
                return {}
            else:
                print(f"  ⚠ HTTP {r.status_code} → {url}")
                return {}
        except Exception as e:
            print(f"  ✗ Error ({intento+1}/{reintentos}): {e}")
            time.sleep(2)
    return {}


def altitud_seleccion(abrev):
    return ALTITUD_BASE.get(abrev.upper(), 0)


def info_sede(nombre_estadio):
    nombre_lower = nombre_estadio.lower().strip()
    for sede in SEDES_MUNDIAL:
        for kw in sede["keywords"]:
            if kw in nombre_lower or nombre_lower in kw:
                return {"ciudad": sede["ciudad"], "pais": sede["pais"], "alt": sede["alt"]}
    print(f"  ⚠ Sede no reconocida: '{nombre_estadio}'")
    return {"ciudad": nombre_estadio, "pais": "?", "alt": 0}


def contexto_altitud(alt):
    if alt < 500:
        return f"Sede a baja altitud ({alt}m)"
    elif alt < 1200:
        return f"Sede en altura moderada ({alt}m)"
    elif alt < 2000:
        return f"Sede en altura considerable ({alt}m)"
    else:
        return f"Sede en gran altitud ({alt}m)"


def normalizar_nombre(nombre: str) -> str:
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = str(nombre).lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def get_confederacion(nombre: str) -> str:
    key = normalizar_nombre(nombre)
    if key in _CONF_MAP:
        return _CONF_MAP[key]
    for k, v in _CONF_MAP.items():
        if k in key or key in k:
            return v
    if any(x in key for x in [
        "africa","egypt","nigeria","ghana","senegal","cameroon",
        "morocco","algeria","tunisia","ivory","cote","mali","congo",
        "guinea","zambia","angola","kenya","ethiopia","tanzania",
    ]):
        return "CAF"
    if any(x in key for x in [
        "japan","china","korea","iran","saudi","qatar","iraq",
        "australia","uae","india","thailand","vietnam","uzbekistan",
        "oman","bahrain","jordan","lebanon","syria","indonesia",
    ]):
        return "AFC"
    if any(x in key for x in ["zealand","fiji","samoa","oceania","tahiti","vanuatu"]):
        return "OFC"
    return "UEFA"


def clasificar_tipo(nombre_comp: str) -> str:
    nc = nombre_comp.lower()
    for clave, tipo in _TIPOS_COMPETENCIA.items():
        if clave in nc:
            return tipo
    return "oficial"


# =====================================================
# NÚCLEO: CAPTURA DE ESTADÍSTICAS POR SELECCIÓN
# (lógica trasplantada de scrapper_selecciones.py)
# Usa scoreboard por rangos de fechas en múltiples leagues
# en lugar del endpoint /schedule que devuelve 0 partidos
# =====================================================

def _scoreboard_rango(league: str, rango: str) -> list:
    """Descarga eventos terminados de un league en un rango de fechas."""
    data = get_json(
        f"{BASE_SOCCER}/{league}/scoreboard",
        {"dates": rango, "limit": 100},
        reintentos=1,
    )
    if not data:
        return []
    return [
        e for e in data.get("events", [])
        if e.get("competitions", [{}])[0]
           .get("status", {}).get("type", {}).get("state", "") == "post"
    ]


def _recolectar_eventos_seleccion(team_id: str, confederacion: str) -> list:
    """
    Recorre leagues históricos + rangos de fechas y devuelve todos
    los partidos terminados en los que participó team_id.
    Límite de 80 eventos para cubrir el ciclo eliminatorio completo.
    """
    todos   = {}
    leagues = _LEAGUES_POR_CONF.get(confederacion, ["fifa.friendly"])

    for league in leagues:
        for rango in _RANGOS_HISTORICOS:
            eventos = _scoreboard_rango(league, rango)
            for ev in eventos:
                try:
                    comp    = ev.get("competitions", [{}])[0]
                    equipos = comp.get("competitors", [])
                    ids     = [str(e.get("team", {}).get("id", "")) for e in equipos]
                    if str(team_id) not in ids:
                        continue
                    eid = ev.get("id", "")
                    if eid and eid not in todos:
                        todos[eid] = ev
                except Exception:
                    continue
            time.sleep(0.15)

        if len(todos) >= 80:
            return list(todos.values())

    return list(todos.values())


def scrape_stats_seleccion(team_id: str, nombre: str, confederacion: str) -> dict:
    """
    Procesa el historial recolectado y calcula todas las métricas:
    oficial vs amistoso, local/visita/neutro, goles, forma y racha.
    """
    stats = {
        # Oficiales
        "partidos_oficial":      0, "ganados_oficial":      0,
        "empatados_oficial":     0, "perdidos_oficial":     0,
        "goles_favor_oficial":   0.0, "goles_contra_oficial":  0.0,
        "forma_oficial":         0.0, "ultimos_5_oficial":     [],
        # Amistosos
        "partidos_amistoso":     0, "ganados_amistoso":      0,
        "empatados_amistoso":    0, "perdidos_amistoso":     0,
        "goles_favor_amistoso":  0.0, "goles_contra_amistoso": 0.0,
        "forma_amistosos":       0.0, "ultimos_5_amistoso":    [],
        # Local / Visita
        "partidos_local":    0, "ganados_local":    0,
        "empatados_local":   0, "perdidos_local":   0,
        "win_rate_local":    0.0,
        "partidos_visita":   0, "ganados_visita":   0,
        "empatados_visita":  0, "perdidos_visita":  0,
        "win_rate_visita":   0.0,
        "win_rate_neutro":   0.0,
        "imbatido_streak":   0,
        "_ciudades_local":   [],
        "_gf_of": [], "_gc_of": [],
        "_gf_am": [], "_gc_am": [],
    }

    eventos = _recolectar_eventos_seleccion(team_id, confederacion)
    if not eventos:
        return stats

    # Ordenar cronológicamente ascendente (más reciente al final)
    eventos_ordenados = sorted(eventos, key=lambda e: e.get("date", ""))
    streak_vivo = True

    # Recorremos de más reciente a más viejo para ultimos_5 y streak
    for evento in reversed(eventos_ordenados):
        try:
            comp   = evento.get("competitions", [{}])[0]
            estado = comp.get("status", {}).get("type", {}).get("state", "")
            if estado != "post":
                continue

            nombre_comp = (
                comp.get("type", {}).get("text", "")
                or comp.get("league", {}).get("name", "")
                or comp.get("tournament", {}).get("displayName", "")
                or ""
            )
            tipo = clasificar_tipo(nombre_comp)

            equipos   = comp.get("competitors", [])
            mi_equipo = next(
                (e for e in equipos
                 if str(e.get("team", {}).get("id", "")) == str(team_id)),
                None,
            )
            if not mi_equipo:
                continue

            es_local = mi_equipo.get("homeAway", "") == "home"
            ganador  = mi_equipo.get("winner", None)
            gf       = int(mi_equipo.get("score", 0) or 0)
            rival    = next(
                (e for e in equipos
                 if str(e.get("team", {}).get("id", "")) != str(team_id)),
                {},
            )
            gc  = int(rival.get("score", 0) or 0)
            res = "W" if ganador is True else ("L" if ganador is False else "D")

            # Acumular por tipo
            if tipo == "oficial":
                stats["partidos_oficial"] += 1
                if res == "W":   stats["ganados_oficial"]   += 1
                elif res == "D": stats["empatados_oficial"] += 1
                else:            stats["perdidos_oficial"]  += 1
                stats["_gf_of"].append(gf)
                stats["_gc_of"].append(gc)
                if len(stats["ultimos_5_oficial"]) < 5:
                    stats["ultimos_5_oficial"].append(res)
            else:
                stats["partidos_amistoso"] += 1
                if res == "W":   stats["ganados_amistoso"]   += 1
                elif res == "D": stats["empatados_amistoso"] += 1
                else:            stats["perdidos_amistoso"]  += 1
                stats["_gf_am"].append(gf)
                stats["_gc_am"].append(gc)
                if len(stats["ultimos_5_amistoso"]) < 5:
                    stats["ultimos_5_amistoso"].append(res)

            # Local / Visita
            if es_local:
                stats["partidos_local"] += 1
                if res == "W":   stats["ganados_local"]   += 1
                elif res == "D": stats["empatados_local"] += 1
                else:            stats["perdidos_local"]  += 1
                ciudad = comp.get("venue", {}).get("address", {}).get("city", "")
                if ciudad:
                    stats["_ciudades_local"].append(ciudad)
            else:
                stats["partidos_visita"] += 1
                if res == "W":   stats["ganados_visita"]   += 1
                elif res == "D": stats["empatados_visita"] += 1
                else:            stats["perdidos_visita"]  += 1

            # Racha imbatido
            if streak_vivo:
                if res != "L":
                    stats["imbatido_streak"] += 1
                else:
                    streak_vivo = False

        except Exception:
            continue

    # Promedios y tasas
    def avg(lst): return round(sum(lst) / len(lst), 3) if lst else 0.0
    def wr(g, p): return round(g / p, 4) if p > 0 else 0.0

    stats["goles_favor_oficial"]   = avg(stats["_gf_of"])
    stats["goles_contra_oficial"]  = avg(stats["_gc_of"])
    stats["goles_favor_amistoso"]  = avg(stats["_gf_am"])
    stats["goles_contra_amistoso"] = avg(stats["_gc_am"])

    stats["forma_oficial"] = round(
        (stats["ganados_oficial"] + stats["empatados_oficial"] * 0.4)
        / max(stats["partidos_oficial"], 1), 4
    )
    stats["forma_amistosos"] = round(
        (stats["ganados_amistoso"] + stats["empatados_amistoso"] * 0.4)
        / max(stats["partidos_amistoso"], 1), 4
    )
    stats["win_rate_local"]  = wr(stats["ganados_local"],  stats["partidos_local"])
    stats["win_rate_visita"] = wr(stats["ganados_visita"], stats["partidos_visita"])
    stats["win_rate_neutro"] = wr(
        stats["ganados_local"]  + stats["ganados_visita"],
        stats["partidos_local"] + stats["partidos_visita"],
    )

    # Limpiar listas temporales
    ciudades = stats.pop("_ciudades_local", [])
    for k in ["_gf_of", "_gc_of", "_gf_am", "_gc_am"]:
        del stats[k]

    stats["_ciudades_local"] = ciudades
    return stats


# =====================================================
# GRUPOS
# =====================================================

def obtener_grupos():
    url  = f"{BASE_ESPN_V2}/fifa.world/standings"
    data = get_json(url)

    grupos = []
    for group in data.get("children", []):
        grupo_obj = {
            "grupo":   group.get("name", ""),
            "equipos": [],
        }

        entries = group.get("standings", {}).get("entries", [])
        for entry in entries:
            team  = entry.get("team", {})
            stats = entry.get("stats", [])

            partidos     = stat(stats, "gamesPlayed")
            goles_favor  = stat(stats, "pointsFor")
            goles_contra = stat(stats, "pointsAgainst")

            equipo = {
                "posicion":         stat(stats, "rank"),
                "equipo":           team.get("displayName", ""),
                "abreviacion":      team.get("abbreviation", ""),
                "escudo":           (team.get("logos", [{}])[0].get("href", "")
                                     if team.get("logos") else ""),
                "partidos":         partidos,
                "ganados":          stat(stats, "wins"),
                "empatados":        stat(stats, "ties"),
                "perdidos":         stat(stats, "losses"),
                "goles_favor":      goles_favor,
                "goles_contra":     goles_contra,
                "diferencia_goles": stat(stats, "pointDifferential"),
                "puntos":           stat(stats, "points"),
            }
            grupo_obj["equipos"].append(equipo)

        grupos.append(grupo_obj)

    guardar_json("grupos.json", grupos)
    return grupos


# =====================================================
# TABLA GENERAL
# =====================================================

def generar_tabla(grupos):
    tabla = []
    for grupo in grupos:
        for eq in grupo["equipos"]:
            tabla.append({
                "grupo":            grupo["grupo"],
                "posicion":         eq["posicion"],
                "equipo":           eq["equipo"],
                "abreviacion":      eq["abreviacion"],
                "escudo":           eq["escudo"],
                "puntos":           eq["puntos"],
                "diferencia_goles": eq["diferencia_goles"],
                "goles_favor":      eq["goles_favor"],
                "goles_contra":     eq["goles_contra"],
                "partidos":         eq["partidos"],
            })

    tabla.sort(
        key=lambda x: (x["puntos"], x["diferencia_goles"], x["goles_favor"]),
        reverse=True,
    )
    guardar_json("tabla.json", tabla)


# =====================================================
# SELECCIONES — captura real vía scoreboard + rangos
# =====================================================

def obtener_selecciones(grupos):
    """
    Construye selecciones.json con stats completas por equipo.
    Usa scoreboard por rangos de fechas en múltiples leagues
    (eliminatorias + torneos + amistosos) en lugar del endpoint
    /schedule que solo ve fifa.world y devuelve 0 partidos.
    """

    # Reunir equipos únicos de los grupos
    equipos_vistos = {}
    for grupo in grupos:
        for eq in grupo["equipos"]:
            abrev = eq["abreviacion"]
            if abrev not in equipos_vistos:
                equipos_vistos[abrev] = eq

    # Necesitamos el id_espn de cada equipo para filtrar eventos
    teams_data = get_json(
        f"{BASE_SOCCER}/fifa.world/teams",
        {"season": "2026", "limit": 100},
    )
    id_por_abrev: dict[str, str] = {}
    conf_por_abrev: dict[str, str] = {}
    for entry in (
        teams_data.get("sports", [{}])[0]
                  .get("leagues", [{}])[0]
                  .get("teams", [])
    ):
        t     = entry.get("team", {})
        abrev = t.get("abbreviation", "").upper()
        if abrev:
            id_por_abrev[abrev]   = str(t.get("id", ""))
            conf_por_abrev[abrev] = t.get("displayConference", "")

    selecciones = {}
    total       = len(equipos_vistos)

    for i, (abrev, eq_base) in enumerate(equipos_vistos.items(), 1):
        nombre = eq_base["equipo"]
        escudo = eq_base["escudo"]

        id_espn       = id_por_abrev.get(abrev, "")
        confederacion = conf_por_abrev.get(abrev, "") or get_confederacion(nombre)

        print(f"  [{i}/{total}] {nombre} ({abrev})  id:{id_espn}  conf:{confederacion}")

        if not id_espn:
            print(f"    ⚠ Sin id_espn — stats vacías")
            stats_vacias = {
                "partidos_oficial": 0, "ganados_oficial": 0,
                "empatados_oficial": 0, "perdidos_oficial": 0,
                "goles_favor_oficial": 0.0, "goles_contra_oficial": 0.0,
                "forma_oficial": 0.0, "ultimos_5_oficial": [],
                "partidos_amistoso": 0, "ganados_amistoso": 0,
                "empatados_amistoso": 0, "perdidos_amistoso": 0,
                "goles_favor_amistoso": 0.0, "goles_contra_amistoso": 0.0,
                "forma_amistosos": 0.0, "ultimos_5_amistoso": [],
                "partidos_local": 0, "ganados_local": 0,
                "empatados_local": 0, "perdidos_local": 0,
                "win_rate_local": 0.0,
                "partidos_visita": 0, "ganados_visita": 0,
                "empatados_visita": 0, "perdidos_visita": 0,
                "win_rate_visita": 0.0, "win_rate_neutro": 0.0,
                "imbatido_streak": 0,
                "_ciudades_local": [],
            }
            stats = stats_vacias
        else:
            stats = scrape_stats_seleccion(id_espn, nombre, confederacion)

        ciudades_local = stats.pop("_ciudades_local", [])
        ranking_info   = RANKING_FIFA.get(abrev.upper(), (999, 0.0))
        slug           = normalizar_nombre(nombre)

        selecciones[slug] = {
            # Identidad
            "nombre":        nombre,
            "abreviacion":   abrev,
            "escudo":        escudo,
            "id_espn":       id_espn,
            "confederacion": confederacion,

            # Geografía
            "altitud_base":   altitud_seleccion(abrev),
            "ciudades_local": ciudades_local[:5],

            # Ranking FIFA
            "ranking_fifa": ranking_info[0],
            "puntos_fifa":  ranking_info[1],

            # Stats OFICIALES
            "partidos_oficial":      stats["partidos_oficial"],
            "ganados_oficial":       stats["ganados_oficial"],
            "empatados_oficial":     stats["empatados_oficial"],
            "perdidos_oficial":      stats["perdidos_oficial"],
            "goles_favor_oficial":   stats["goles_favor_oficial"],
            "goles_contra_oficial":  stats["goles_contra_oficial"],
            "forma_oficial":         stats["forma_oficial"],
            "ultimos_5_oficial":     stats["ultimos_5_oficial"],

            # Stats AMISTOSOS
            "partidos_amistoso":     stats["partidos_amistoso"],
            "ganados_amistoso":      stats["ganados_amistoso"],
            "empatados_amistoso":    stats["empatados_amistoso"],
            "perdidos_amistoso":     stats["perdidos_amistoso"],
            "goles_favor_amistoso":  stats["goles_favor_amistoso"],
            "goles_contra_amistoso": stats["goles_contra_amistoso"],
            "forma_amistosos":       stats["forma_amistosos"],
            "ultimos_5_amistoso":    stats["ultimos_5_amistoso"],

            # Local / Visita / Neutro
            "partidos_local":    stats["partidos_local"],
            "ganados_local":     stats["ganados_local"],
            "empatados_local":   stats["empatados_local"],
            "perdidos_local":    stats["perdidos_local"],
            "win_rate_local":    stats["win_rate_local"],
            "partidos_visita":   stats["partidos_visita"],
            "ganados_visita":    stats["ganados_visita"],
            "empatados_visita":  stats["empatados_visita"],
            "perdidos_visita":   stats["perdidos_visita"],
            "win_rate_visita":   stats["win_rate_visita"],
            "win_rate_neutro":   stats["win_rate_neutro"],

            # Racha
            "imbatido_streak": stats["imbatido_streak"],
        }

        time.sleep(0.3)

    guardar_json("selecciones.json", selecciones)
    return selecciones


# =====================================================
# FIXTURE (HOY + MAÑANA)
# =====================================================

def obtener_fixture(selecciones_por_nombre=None):
    ahora  = datetime.now(timezone.utc)
    fechas = [
        ahora.strftime("%Y%m%d"),
        (ahora + timedelta(days=1)).strftime("%Y%m%d"),
    ]

    nombre_a_slug = {}
    if selecciones_por_nombre:
        for slug, data in selecciones_por_nombre.items():
            nombre_a_slug[data["nombre"].lower()] = slug

    partidos = []

    for fecha in fechas:
        data = get_json(f"{BASE_ESPN}/scoreboard", params={"dates": fecha})

        for event in data.get("events", []):
            comp        = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            status      = comp.get("status", {}).get("type", {})

            local     = next((c for c in competitors if c.get("homeAway") == "home"), {})
            visitante = next((c for c in competitors if c.get("homeAway") == "away"), {})

            nombre_estadio  = comp.get("venue", {}).get("fullName", "")
            sede_info       = info_sede(nombre_estadio)

            abrev_local     = local.get("team",    {}).get("abbreviation", "")
            abrev_visitante = visitante.get("team",{}).get("abbreviation", "")
            id_local        = str(local.get("team",    {}).get("id", ""))
            id_visitante    = str(visitante.get("team",{}).get("id", ""))

            alt_sede      = sede_info["alt"]
            alt_local     = altitud_seleccion(abrev_local)
            alt_visitante = altitud_seleccion(abrev_visitante)

            partido = {
                "id":            event.get("id"),
                "fecha":         event.get("date"),
                "estado":        status.get("description", ""),
                "minuto":        comp.get("status", {}).get("displayClock", ""),
                "local":             local.get("team",    {}).get("displayName", ""),
                "visitante":         visitante.get("team",{}).get("displayName", ""),
                "id_espn_local":     id_local,
                "id_espn_visitante": id_visitante,
                "estadio":       nombre_estadio,
                "ciudad_sede":   sede_info["ciudad"],
                "pais_sede":     sede_info["pais"],
                "altitud_sede":  alt_sede,
                "altitud_base_local":     alt_local,
                "altitud_base_visitante": alt_visitante,
                "diferencia_altitud_local":     max(alt_sede - alt_local, 0),
                "diferencia_altitud_visitante": max(alt_sede - alt_visitante, 0),
                "contexto_altitud": contexto_altitud(alt_sede),
            }

            if status.get("completed", False) or status.get("name", "") == "STATUS_FINAL":
                partido["goles_local"]     = int(local.get("score",    0) or 0)
                partido["goles_visitante"] = int(visitante.get("score", 0) or 0)

            partidos.append(partido)

    guardar_json("fixture.json", partidos)
    return partidos


# =====================================================
# MAIN
# =====================================================

def main():
    print("\n╔══════════════════════════════╗")
    print("║   Actualizando Mundial 2026  ║")
    print("╚══════════════════════════════╝\n")

    print("▶ Grupos y tabla...")
    grupos = obtener_grupos()
    generar_tabla(grupos)

    print("\n▶ Selecciones (puede tardar 5-10 min por los rangos históricos)...")
    selecciones = obtener_selecciones(grupos)

    print("\n▶ Fixture (hoy + mañana)...")
    obtener_fixture(selecciones_por_nombre=selecciones)

    print("\n✓ Todo actualizado\n")


if __name__ == "__main__":
    main()