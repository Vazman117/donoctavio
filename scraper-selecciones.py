"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          SCRAPPER DE SELECCIONES NACIONALES — ESPN + FIFA                  ║
║          Optimizado para modelo_mundial.py                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Output JSON por selección:                                                ║
║                                                                            ║
║  {                                                                         ║
║    "nombre": "Mexico",                                                     ║
║    "abreviacion": "MEX",                                                   ║
║    "escudo": "https://...",                                                ║
║    "id_espn": "203",                                                       ║
║    "confederacion": "CONCACAF",                                            ║
║    "altitud_base": 2240,          ← altitud habitual del equipo            ║
║    "ranking_fifa": 15,                                                     ║
║    "puntos_fifa": 1681.03,                                                 ║
║    "partidos_oficial": 42,        ← solo competencias oficiales            ║
║    "ganados_oficial": 25,                                                  ║
║    "forma_oficial": 0.71,         ← (W + D*0.4) / partidos                ║
║    "ultimos_5_oficial": ["W","W","D","L","W"],                             ║
║    "goles_favor_oficial": 1.85,   ← promedio por partido                  ║
║    "goles_contra_oficial": 0.92,                                           ║
║    "partidos_amistoso": 18,                                                ║
║    "forma_amistosos": 0.62,                                                ║
║    "ultimos_5_amistoso": ["W","D","D","W","L"],                            ║
║    "goles_favor_amistoso": 1.44,                                           ║
║    "goles_contra_amistoso": 1.11,                                          ║
║    "win_rate_local": 0.72,        ← cuando juegan como local               ║
║    "win_rate_visita": 0.38,                                                ║
║    "win_rate_neutro": 0.54,       ← campo neutro (tourneos)                ║
║    "imbatido_streak": 4,          ← partidos sin perder consecutivos       ║
║    "ciudades_local": ["Mexico City","Guadalajara"],                        ║
║  }                                                                         ║
║                                                                            ║
║  Archivos de salida:                                                       ║
║    scrapper/<CARPETA>/selecciones.json                                     ║
║    scrapper/<CARPETA>/fixture.json                                         ║
║    scrapper/<CARPETA>/h2h.json                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Uso:
    python scrapper_selecciones.py --torneo mundial_2026_grupos --dias 90
    python scrapper_selecciones.py --torneo amistosos_jun2026
    python scrapper_selecciones.py --todos
"""

import requests
import json
import os
import re
import time
import argparse
from datetime import date, timedelta


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE TORNEOS
# ══════════════════════════════════════════════════════════════════════════════

TORNEOS_CONFIG = {
    "amistosos_jun2026": {
        "carpeta":     "AMISTOSOS-JUN2026",
        "espn_league": "fifa.friendly",
        "espn_season": "2026",
        "conf_sede":   "neutro",
        "perfil":      "amistoso_fifa",
        "descripcion": "Amistosos FIFA Junio 2026",
    },
    "copa_america_2026": {
        "carpeta":     "COPA-AMERICA-2026",
        "espn_league": "conmebol.america",
        "espn_season": "2026",
        "conf_sede":   "CONMEBOL",
        "perfil":      "torneo_continental",
        "descripcion": "Copa América 2026",
    },
    "gold_cup_2026": {
        "carpeta":     "GOLD-CUP-2026",
        "espn_league": "concacaf.gold",
        "espn_season": "2026",
        "conf_sede":   "CONCACAF",
        "perfil":      "torneo_continental",
        "descripcion": "Gold Cup 2026",
    },
    "nations_league_concacaf": {
        "carpeta":     "CONCACAF-NATIONS-LEAGUE",
        "espn_league": "concacaf.nations.league",
        "espn_season": "2026",
        "conf_sede":   "CONCACAF",
        "perfil":      "torneo_continental",
        "descripcion": "CONCACAF Nations League",
    },
    "eliminatoria_conmebol": {
        "carpeta":     "ELIMINATORIA-CONMEBOL",
        "espn_league": "conmebol.world.qualifier",
        "espn_season": "2026",
        "conf_sede":   "CONMEBOL",
        "perfil":      "eliminatoria",
        "descripcion": "Eliminatoria CONMEBOL 2026",
    },
    "eliminatoria_concacaf": {
        "carpeta":     "ELIMINATORIA-CONCACAF",
        "espn_league": "concacaf.world.qualifier",
        "espn_season": "2026",
        "conf_sede":   "CONCACAF",
        "perfil":      "eliminatoria",
        "descripcion": "Eliminatoria CONCACAF 2026",
    },
    "mundial_2026_grupos": {
        "carpeta":     "MUNDIAL-2026",
        "espn_league": "fifa.world",
        "espn_season": "2026",
        "conf_sede":   "CONCACAF",
        "perfil":      "mundial_grupos",
        "descripcion": "Copa del Mundo 2026 — Fase de Grupos",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# LEAGUES HISTÓRICAS PARA BUSCAR ESTADÍSTICAS DE CADA SELECCIÓN
# Se prueban en orden; se acumulan eventos sin duplicar.
# ══════════════════════════════════════════════════════════════════════════════

LEAGUES_HISTORICAS = [
    "fifa.world",
    "fifa.friendly",
    "conmebol.america",
    "concacaf.gold",
    "concacaf.nations.league",
    "conmebol.world.qualifier",
    "concacaf.world.qualifier",
    "uefa.nations",
    "uefa.euro",
    "uefa.euroq",
    "caf.nations",
    "afc.asian.cup",
]

# Temporadas a revisar para historial reciente (más reciente primero)
TEMPORADAS_HISTORIAL = ["2026", "2025", "2024", "2023"]

# ══════════════════════════════════════════════════════════════════════════════
# TABLA DE ALTITUDES
# ══════════════════════════════════════════════════════════════════════════════

ALTITUDES_CIUDADES = {
    # América del Sur
    "la paz": 3625, "potosi": 3967, "oruro": 3706,
    "quito": 2850, "cuenca": 2550, "ambato": 2577,
    "bogota": 2600, "medellin": 1495, "cali": 995,
    "manizales": 2153, "bucaramanga": 959,
    "lima": 18, "cusco": 3399, "arequipa": 2335, "huancayo": 3259,
    "buenos aires": 25, "cordoba": 571, "mendoza": 827,
    "san juan": 650, "tucuman": 481,
    "santiago": 520, "concepcion": 12, "valparaiso": 41,
    "montevideo": 43,
    "sao paulo": 760, "rio de janeiro": 10, "belo horizonte": 858,
    "brasilia": 1172, "porto alegre": 46, "salvador": 8,
    "fortaleza": 16, "recife": 4, "manaus": 44,
    "asuncion": 43,
    "caracas": 900, "maracaibo": 6,
    "guayaquil": 4,
    # América del Norte / CONCACAF
    "ciudad de mexico": 2240, "mexico city": 2240, "guadalajara": 1566,
    "monterrey": 538, "toluca": 2680, "puebla": 2135,
    "leon": 1884, "queretaro": 1820, "san luis potosi": 1877,
    "pachuca": 2426, "morelia": 1951, "merida": 8,
    "san jose": 1161, "liberia": 110,
    "tegucigalpa": 1004, "san pedro sula": 100,
    "guatemala city": 1500,
    "san salvador": 658,
    "managua": 56,
    "panama city": 0,
    "havana": 24, "kingston": 175,
    "port-au-prince": 37, "santo domingo": 14,
    "denver": 1609, "salt lake city": 1288, "dallas": 139,
    "houston": 12, "los angeles": 93, "new york": 10,
    "boston": 14, "miami": 4, "seattle": 54,
    "kansas city": 267, "atlanta": 320, "philadelphia": 12,
    "san francisco": 16, "nashville": 182, "orlando": 30,
    "minneapolis": 264, "chicago": 181, "washington": 25,
    "vancouver": 70, "toronto": 76, "montreal": 27, "edmonton": 671,
    # Europa
    "madrid": 657, "barcelona": 12, "bilbao": 19, "sevilla": 13,
    "valencia": 15, "zaragoza": 199,
    "london": 11, "manchester": 38, "liverpool": 25,
    "birmingham": 99, "glasgow": 23, "edinburgh": 47,
    "paris": 35, "lyon": 170, "marseille": 28,
    "berlin": 34, "munich": 520, "dortmund": 86,
    "hamburg": 9, "cologne": 45, "frankfurt": 99,
    "milan": 122, "rome": 21, "naples": 17, "turin": 239,
    "lisbon": 92, "porto": 86,
    "amsterdam": -2, "rotterdam": -5, "eindhoven": 21,
    "brussels": 56, "zurich": 408, "bern": 542, "geneva": 375,
    "vienna": 171, "salzburg": 424,
    "moscow": 156, "saint petersburg": 4,
    "warsaw": 107, "krakow": 219,
    "bucharest": 74, "sofia": 550, "belgrade": 116,
    "zagreb": 122, "athens": 74, "istanbul": 40, "ankara": 938,
    "baku": 28, "tbilisi": 490, "yerevan": 1000,
    "reykjavik": 64, "oslo": 23, "stockholm": 28,
    "copenhagen": 5, "helsinki": 26,
    # África
    "johannesburg": 1753, "pretoria": 1339, "durban": 5, "cape town": 17,
    "addis ababa": 2355, "nairobi": 1795, "kampala": 1190,
    "cairo": 74, "casablanca": 56, "rabat": 75, "marrakech": 466,
    "dakar": 22, "abidjan": 50, "accra": 61, "lagos": 41, "abuja": 476,
    "yaounde": 726, "tunis": 10, "algiers": 424,
    # Asia
    "tehran": 1191, "riyadh": 612, "jeddah": 17, "doha": 10,
    "dubai": 5, "abu dhabi": 5,
    "beijing": 44, "shanghai": 4, "seoul": 38,
    "tokyo": 40, "osaka": 5,
    "mumbai": 14, "delhi": 216,
    "jakarta": 8, "kuala lumpur": 22, "singapore": 15,
    "bangkok": 2, "hanoi": 6, "manila": 16,
    "tashkent": 455, "almaty": 817,
    # Oceanía
    "sydney": 58, "melbourne": 31, "brisbane": 27,
    "auckland": 22, "wellington": 126,
}

ALTITUD_BASE_SELECCIONES = {
    "bolivia": 3625, "colombia": 2600, "ecuador": 2850,
    "peru": 18, "venezuela": 900,
    "mexico": 2240, "toluca": 2680, "costarica": 1161,
    "honduras": 1004, "guatemala": 1500, "elsalvador": 658,
    "armenia": 1000, "georgia": 490, "switzerland": 408,
    "austria": 171, "usa": 25, "unitedstates": 25,
    "canada": 76, "ethiopia": 2355, "kenya": 1795,
    "southafrica": 1753, "iran": 1191, "turkey": 938,
    "turkey": 938, "turkey": 938,
}


def get_altitud_ciudad(ciudad: str) -> int:
    if not ciudad:
        return 0
    key = ciudad.lower().strip()
    if key in ALTITUDES_CIUDADES:
        return ALTITUDES_CIUDADES[key]
    for nombre, alt in ALTITUDES_CIUDADES.items():
        if nombre in key or key in nombre:
            return alt
    return 0


def get_altitud_base_seleccion(nombre: str, ciudades: list) -> int:
    altitudes = [get_altitud_ciudad(c) for c in ciudades if get_altitud_ciudad(c) > 0]
    if len(altitudes) >= 2:
        return int(sum(altitudes) / len(altitudes))
    key = normalizar_nombre(nombre)
    for k, v in ALTITUD_BASE_SELECCIONES.items():
        if k in key or key in k:
            return v
    return 15


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE HTTP
# ══════════════════════════════════════════════════════════════════════════════

BASE_ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def espn_get(url: str, params: dict = None, reintentos: int = 3) -> dict | None:
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                print(f"    ⏳ Rate limit, esperando 10s...")
                time.sleep(10)
            elif r.status_code in (400, 404):
                return None  # Equipo no pertenece a este league — silencioso, sin reintentar
            else:
                print(f"    ⚠️  HTTP {r.status_code} → {url}")
                return None
        except Exception as e:
            print(f"    ❌ Error ({intento+1}/{reintentos}): {e}")
            time.sleep(2)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# RANKING FIFA
# Estrategia en capas: API v3 → inside.fifa.com (discovery) → ESPN → hardcodeado
# ══════════════════════════════════════════════════════════════════════════════

def _fifa_get(url: str, headers: dict, timeout: int = 6) -> dict | None:
    """Request a FIFA con timeout corto — nunca bloquea más de `timeout` segundos."""
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def scrape_ranking_fifa() -> dict:
    print("  📊 Descargando Ranking FIFA...")
    ranking = {}

    headers_fifa = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept":     "application/json",
        "Origin":     "https://www.fifa.com",
        "Referer":    "https://www.fifa.com/",
    }

    # ── Capa 1: API pública FIFA v3 (timeout 6s, 1 intento cada URL) ─────────
    for api_url in [
        "https://api.fifa.com/api/v3/rankings/FIFA?locale=en&count=211",
        "https://api.fifa.com/api/v3/rankings/FIFA?locale=en",
    ]:
        data = _fifa_get(api_url, headers_fifa, timeout=6)
        if not data:
            continue
        items = data.get("Results", data.get("rankings", []))
        for entry in items:
            try:
                nombre_list = entry.get("TeamName", [{}])
                nombre = (
                    nombre_list[0].get("Description", "")
                    if nombre_list else entry.get("Name", "")
                )
                pos = int(entry.get("Rank", entry.get("rankingPosition", 0)))
                pts = float(entry.get("Points", entry.get("TotalPoints", 0)))
                if nombre and pos:
                    ranking[normalizar_nombre(nombre)] = {
                        "nombre": nombre, "ranking_fifa": pos, "puntos_fifa": round(pts, 2),
                    }
            except Exception:
                continue
        if ranking:
            print(f"    ✅ {len(ranking)} selecciones (FIFA API v3)")
            return ranking

    # ── Capa 2: inside.fifa.com — solo los dateIds ya descubiertos (máx 3) ───
    # El discovery ya los obtuvo en la consola; aquí los usamos con timeout corto.
    headers_inside = {**headers_fifa, "Referer": "https://inside.fifa.com/", "Origin": "https://inside.fifa.com"}

    discovered_ids = []
    data_html = _fifa_get(
        "https://inside.fifa.com/fifa-world-ranking/men",
        {**headers_inside, "Accept": "text/html,application/xhtml+xml"},
        timeout=8,
    )
    # _fifa_get espera JSON, así que hacemos la llamada cruda aquí
    try:
        r = requests.get(
            "https://inside.fifa.com/fifa-world-ranking/men",
            headers={**headers_inside, "Accept": "text/html,application/xhtml+xml"},
            timeout=8,
        )
        if r.status_code == 200:
            found = re.findall(r'"id"\s*:\s*"(id\d+)"', r.text) \
                 or re.findall(r'dateId=(id\d+)', r.text) \
                 or re.findall(r'\b(id\d{4,6})\b', r.text)
            if found:
                discovered_ids = sorted(set(found), key=lambda x: int(x[2:]), reverse=True)[:3]
    except Exception:
        pass

    # Solo intentar los 3 más recientes descubiertos + 2 conocidos confiables
    ids_a_probar = discovered_ids + [i for i in ["id14933", "id14870"] if i not in discovered_ids]
    ids_a_probar = ids_a_probar[:5]  # máximo 5 intentos totales

    for did in ids_a_probar:
        data = _fifa_get(
            f"https://inside.fifa.com/api/ranking-overview?locale=en&dateId={did}",
            headers_inside, timeout=6,
        )
        if not data or "rankings" not in data:
            continue
        for entry in data["rankings"]:
            try:
                nombre = entry.get("team", {}).get("name", "")
                pos    = int(entry.get("rankingPosition", 0))
                pts    = float(entry.get("totalPoints", 0))
                if nombre and pos:
                    ranking[normalizar_nombre(nombre)] = {
                        "nombre": nombre, "ranking_fifa": pos, "puntos_fifa": round(pts, 2),
                    }
            except Exception:
                continue
        if ranking:
            print(f"    ✅ {len(ranking)} selecciones (inside.fifa · {did})")
            return ranking

    # ── Capa 3: ESPN fallback ─────────────────────────────────────────────────
    print("    ⚠️  FIFA no disponible, intentando ESPN...")
    for espn_slug in ["fifa.world", "fifa.friendly"]:
        data = espn_get(f"{BASE_ESPN}/{espn_slug}/rankings")
        if not data:
            continue
        items = data.get("rankings", data.get("items", []))
        for entry in items:
            try:
                team   = entry.get("team", {})
                nombre = team.get("displayName", team.get("name", ""))
                pos    = int(entry.get("rank", entry.get("current", 0)))
                pts    = float(entry.get("points", entry.get("rankingPoints", 0)))
                if nombre and pos:
                    ranking[normalizar_nombre(nombre)] = {
                        "nombre": nombre, "ranking_fifa": pos, "puntos_fifa": round(pts, 2),
                    }
            except Exception:
                continue
        if ranking:
            print(f"    ✅ {len(ranking)} selecciones (ESPN/{espn_slug})")
            return ranking

    # ── Capa 4: hardcodeado abril 2026 ────────────────────────────────────────
    print("    ⚠️  Usando ranking hardcodeado (abril 2026)...")
    return _ranking_hardcodeado()


def _ranking_hardcodeado() -> dict:
    datos = [
        ("France", 1, 1877.32), ("Spain", 2, 1876.40),
        ("Argentina", 3, 1874.81), ("England", 4, 1825.97),
        ("Portugal", 5, 1763.83), ("Brazil", 6, 1761.16),
        ("Netherlands", 7, 1757.87), ("Morocco", 8, 1755.87),
        ("Belgium", 9, 1734.71), ("Germany", 10, 1730.37),
        ("Croatia", 11, 1717.07), ("Italy", 12, 1700.37),
        ("Colombia", 13, 1693.09), ("Senegal", 14, 1688.99),
        ("Mexico", 15, 1681.03), ("United States", 16, 1673.13),
        ("Uruguay", 17, 1673.07), ("Japan", 18, 1660.43),
        ("Switzerland", 19, 1649.40), ("Denmark", 20, 1620.81),
        ("Ecuador", 21, 1608.50), ("Austria", 22, 1601.20),
        ("Australia", 23, 1595.30), ("South Korea", 24, 1590.10),
        ("Ukraine", 25, 1582.40), ("Turkey", 26, 1578.90),
        ("Iran", 27, 1571.20), ("Poland", 28, 1565.80),
        ("Serbia", 29, 1558.30), ("Hungary", 30, 1551.70),
        ("Canada", 31, 1548.20), ("Chile", 32, 1542.60),
        ("Norway", 33, 1538.90), ("Czech Republic", 34, 1531.40),
        ("Sweden", 35, 1524.80), ("Algeria", 36, 1518.20),
        ("Egypt", 37, 1512.70), ("Ivory Coast", 38, 1507.30),
        ("Peru", 39, 1501.90), ("Slovakia", 40, 1496.50),
        ("Venezuela", 41, 1491.10), ("Nigeria", 42, 1485.70),
        ("Romania", 43, 1480.30), ("Scotland", 44, 1475.90),
        ("Paraguay", 45, 1470.50), ("Costa Rica", 46, 1452.30),
        ("Cameroon", 47, 1448.90), ("Tunisia", 48, 1444.50),
        ("Qatar", 49, 1440.10), ("Ghana", 50, 1435.70),
        ("Bolivia", 51, 1418.20), ("Saudi Arabia", 56, 1392.10),
        ("Honduras", 60, 1380.50), ("Iraq", 63, 1361.40),
        ("Panama", 65, 1355.20), ("El Salvador", 75, 1310.80),
        ("Jamaica", 80, 1295.40), ("Curacao", 82, 1288.70),
        ("Jordan", 85, 1278.60), ("New Zealand", 90, 1262.30),
        ("Lebanon", 95, 1245.60), ("Tanzania", 96, 1240.10),
        ("Zambia", 98, 1231.50), ("Guinea", 99, 1228.80),
        ("DR Congo", 100, 1225.40),
    ]
    return {
        normalizar_nombre(n): {"nombre": n, "ranking_fifa": p, "puntos_fifa": pt}
        for n, p, pt in datos
    }


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURE
# ══════════════════════════════════════════════════════════════════════════════

def scrape_fixture(league: str, season: str, dias_adelante: int = 14) -> list:
    hoy       = date.today()
    fecha_fin = hoy + timedelta(days=dias_adelante)
    rango     = f"{hoy.strftime('%Y%m%d')}-{fecha_fin.strftime('%Y%m%d')}"

    print(f"  📅 Descargando fixture {league} {season}  [{hoy} → {fecha_fin}]...")

    partidos = []
    url      = f"{BASE_ESPN}/{league}/scoreboard"

    # Intento 1: rango directo
    data = espn_get(url, {"season": season, "limit": 200, "dates": rango})
    if data and data.get("events"):
        partidos = _parsear_eventos(data["events"], solo_proximos=True)

    # Intento 2: semana a semana si no vino nada
    if not partidos:
        cursor = hoy
        while cursor <= fecha_fin:
            fin_sem = min(cursor + timedelta(days=6), fecha_fin)
            rango_s = f"{cursor.strftime('%Y%m%d')}-{fin_sem.strftime('%Y%m%d')}"
            d = espn_get(url, {"season": season, "limit": 100, "dates": rango_s})
            if d and d.get("events"):
                partidos += _parsear_eventos(d["events"], solo_proximos=True)
            cursor += timedelta(days=7)
            time.sleep(0.3)

    # Intento 3: schedule endpoint
    if not partidos:
        url_sched = f"{BASE_ESPN}/{league}/schedule"
        d = espn_get(url_sched, {"season": season, "limit": 200})
        if d and d.get("events"):
            partidos = _parsear_eventos(d["events"], solo_proximos=True)

    # Deduplicar por id
    vistos   = set()
    unicos   = []
    for p in partidos:
        if p["id"] not in vistos:
            vistos.add(p["id"])
            unicos.append(p)

    unicos.sort(key=lambda p: p["fecha"])

    print(f"    ✅ {len(unicos)} partidos próximos")
    for p in unicos[:3]:
        print(f"       {p['fecha'][:10]}  {p['local']} vs {p['visitante']}  "
              f"[{p['ciudad_sede'] or 'N/D'} — {p['altitud_sede']}m]")
    return unicos


def _parsear_eventos(eventos: list, solo_proximos: bool = True) -> list:
    partidos = []
    for evento in eventos:
        try:
            comp   = evento.get("competitions", [{}])[0]
            estado = comp.get("status", {}).get("type", {}).get("state", "pre")
            if solo_proximos and estado == "post":
                continue

            equipos    = comp.get("competitors", [])
            local_d    = next((e for e in equipos if e.get("homeAway") == "home"), {})
            visita_d   = next((e for e in equipos if e.get("homeAway") == "away"), {})
            n_local    = local_d.get("team", {}).get("displayName", "")
            n_visitante= visita_d.get("team", {}).get("displayName", "")
            if not n_local or not n_visitante:
                continue

            venue      = comp.get("venue", {})
            ciudad     = venue.get("address", {}).get("city", "")
            pais_sede  = venue.get("address", {}).get("country", "")
            alt_sede   = get_altitud_ciudad(ciudad) or get_altitud_ciudad(pais_sede)

            partidos.append({
                "id":                evento.get("id", ""),
                "fecha":             evento.get("date", ""),
                "estado":            estado,
                "local":             n_local,
                "visitante":         n_visitante,
                "id_espn_local":     local_d.get("team", {}).get("id", ""),
                "id_espn_visitante": visita_d.get("team", {}).get("id", ""),
                "estadio":           venue.get("fullName", venue.get("name", "")),
                "ciudad_sede":       ciudad,
                "pais_sede":         pais_sede,
                "altitud_sede":      alt_sede,
            })
        except Exception:
            continue
    return partidos


# ══════════════════════════════════════════════════════════════════════════════
# ESTADÍSTICAS POR SELECCIÓN
# FIX CENTRAL: busca en múltiples leagues y temporadas para obtener historial real
# ══════════════════════════════════════════════════════════════════════════════

TIPOS_COMPETENCIA = {
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


def clasificar_tipo(nombre_comp: str) -> str:
    nc = nombre_comp.lower()
    for clave, tipo in TIPOS_COMPETENCIA.items():
        if clave in nc:
            return tipo
    return "oficial"


# Leagues y rangos de fechas históricas por confederación
# Usamos scoreboard por fecha en lugar de /teams/{id}/schedule
# porque ese endpoint es bloqueado/vacío para selecciones en muchos casos.

_LEAGUES_CONF = {
    "UEFA":     ["uefa.nations", "uefa.euroq", "uefa.euro", "fifa.friendly"],
    "CONMEBOL": ["conmebol.world.qualifier", "conmebol.america", "fifa.friendly"],
    "CONCACAF": ["concacaf.world.qualifier", "concacaf.nations.league", "concacaf.gold", "fifa.friendly"],
    "CAF":      ["caf.nations", "caf.qualifier", "fifa.friendly"],
    "AFC":      ["afc.asian.cup", "afc.qualifier", "fifa.friendly"],
    "OFC":      ["fifa.friendly"],
}

# Rangos de fechas a scrapear (eliminatorias + torneos recientes)
_RANGOS_HISTORICOS = [
    "20230901-20231231",
    "20240301-20240630",
    "20240901-20241231",
    "20250301-20250630",
    "20250901-20251231",
    "20260101-20260531",
]


def _scoreboard_fechas(league: str, rango: str) -> list:
    """Descarga todos los partidos terminados de un league en un rango de fechas."""
    data = espn_get(
        f"{BASE_ESPN}/{league}/scoreboard",
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


def _recolectar_eventos_seleccion(team_id: str, confederacion: str = "UEFA") -> list:
    """
    Descarga partidos históricos del equipo usando scoreboard por fechas.
    Filtra solo los partidos donde participa team_id.
    Estrategia: leagues de su confederación primero, luego amistosos.
    Para cuando tiene 40+ partidos terminados.
    """
    todos   = {}
    leagues = _LEAGUES_CONF.get(confederacion, ["fifa.friendly"])

    for league in leagues:
        for rango in _RANGOS_HISTORICOS:
            eventos = _scoreboard_fechas(league, rango)
            for ev in eventos:
                try:
                    comp    = ev.get("competitions", [{}])[0]
                    equipos = comp.get("competitors", [])
                    ids_partido = [str(e.get("team", {}).get("id", "")) for e in equipos]
                    if str(team_id) not in ids_partido:
                        continue
                    eid = ev.get("id", "")
                    if eid and eid not in todos:
                        todos[eid] = ev
                except Exception:
                    continue
            time.sleep(0.15)

            if len(todos) >= 40:
                return list(todos.values())

    return list(todos.values())


def scrape_stats_seleccion(team_id: str, nombre: str, confederacion: str = "UEFA") -> dict:
    stats = {
        # Oficiales
        "partidos_oficial":        0, "ganados_oficial":        0,
        "empatados_oficial":       0, "perdidos_oficial":       0,
        "goles_favor_oficial":     0.0, "goles_contra_oficial": 0.0,
        "forma_oficial":           0.0, "ultimos_5_oficial":    [],
        # Amistosos
        "partidos_amistoso":       0, "ganados_amistoso":       0,
        "empatados_amistoso":      0, "perdidos_amistoso":      0,
        "goles_favor_amistoso":    0.0, "goles_contra_amistoso":0.0,
        "forma_amistosos":         0.0, "ultimos_5_amistoso":   [],
        # Local/Visita
        "partidos_local":          0, "ganados_local":          0,
        "empatados_local":         0, "perdidos_local":         0,
        "win_rate_local":          0.0,
        "partidos_visita":         0, "ganados_visita":         0,
        "empatados_visita":        0, "perdidos_visita":        0,
        "win_rate_visita":         0.0,
        "win_rate_neutro":         0.0,
        "imbatido_streak":         0,
        "_ciudades_local":         [],
        "_gf_of": [], "_gc_of": [],
        "_gf_am": [], "_gc_am": [],
    }

    eventos = _recolectar_eventos_seleccion(team_id, confederacion)
    if not eventos:
        return stats

    # Ordenar cronológicamente (más reciente último para streak, más reciente primero para ultimos_5)
    eventos_ordenados = sorted(
        eventos,
        key=lambda e: e.get("date", ""),
        reverse=False,  # ascendente → el último es el más reciente
    )

    streak_vivo = True

    for evento in reversed(eventos_ordenados):   # recorremos de más reciente a más viejo
        try:
            comp = evento.get("competitions", [{}])[0]

            # Solo partidos terminados
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
                (e for e in equipos if str(e.get("team", {}).get("id", "")) == str(team_id)),
                None,
            )
            if not mi_equipo:
                continue

            es_local  = mi_equipo.get("homeAway", "") == "home"
            ganador   = mi_equipo.get("winner", None)
            gf        = int(mi_equipo.get("score", 0) or 0)
            rival     = next(
                (e for e in equipos if str(e.get("team", {}).get("id", "")) != str(team_id)),
                {},
            )
            gc = int(rival.get("score", 0) or 0)

            res = "W" if ganador is True else ("L" if ganador is False else "D")

            # ── Acumular por tipo ──────────────────────────────────────────
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

            # ── Local / Visita ─────────────────────────────────────────────
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

            # ── Racha imbatido ─────────────────────────────────────────────
            if streak_vivo:
                if res != "L":
                    stats["imbatido_streak"] += 1
                else:
                    streak_vivo = False

        except Exception:
            continue

    # ── Promedios y tasas ──────────────────────────────────────────────────
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

    # Limpiar campos internos antes de retornar
    for k in ["_gf_of", "_gc_of", "_gf_am", "_gc_am"]:
        del stats[k]

    return stats


# ══════════════════════════════════════════════════════════════════════════════
# CONFEDERACIONES
# ══════════════════════════════════════════════════════════════════════════════

_CONF_MAP: dict[str, str] = {}


def _build_conf_map():
    global _CONF_MAP
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


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER PRINCIPAL DE SELECCIONES
# ══════════════════════════════════════════════════════════════════════════════

def scrape_selecciones_torneo(league: str, season: str, fixture: list) -> dict:
    print(f"  👥 Scrapeando estadísticas de selecciones...")

    # Recopilar equipos únicos del fixture
    equipos: dict[str, str] = {}  # nombre → id_espn
    for partido in fixture:
        if partido["local"] and partido["id_espn_local"]:
            equipos[partido["local"]] = partido["id_espn_local"]
        if partido["visitante"] and partido["id_espn_visitante"]:
            equipos[partido["visitante"]] = partido["id_espn_visitante"]

    # Si no hay fixture, pedir los equipos del torneo directamente
    if not equipos:
        url  = f"{BASE_ESPN}/{league}/teams"
        data = espn_get(url, {"season": season, "limit": 100})
        if data:
            for entry in (
                data.get("sports", [{}])[0]
                    .get("leagues", [{}])[0]
                    .get("teams", [])
            ):
                team   = entry.get("team", {})
                nombre = team.get("displayName", "")
                tid    = team.get("id", "")
                if nombre and tid:
                    equipos[nombre] = tid

    selecciones = {}
    total       = len(equipos)

    for i, (nombre, team_id) in enumerate(equipos.items(), 1):
        key = normalizar_nombre(nombre)
        print(f"    [{i}/{total}] {nombre} (id: {team_id})")

        confederacion  = get_confederacion(nombre)
        stats          = scrape_stats_seleccion(team_id, nombre, confederacion)
        ciudades_local = stats.pop("_ciudades_local", [])
        altitud_base   = get_altitud_base_seleccion(nombre, ciudades_local)
        time.sleep(0.3)

        selecciones[key] = {
            # ── Identidad ───────────────────────────────────────────────────
            "nombre":         nombre,
            "escudo":         f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
            "id_espn":        team_id,
            "confederacion":  confederacion,

            # ── Geografía ───────────────────────────────────────────────────
            "altitud_base":   altitud_base,
            "ciudades_local": ciudades_local[:5],

            # ── Ranking FIFA (se rellena después) ───────────────────────────
            "ranking_fifa":   None,
            "puntos_fifa":    None,

            # ── Estadísticas en partidos OFICIALES ──────────────────────────
            "partidos_oficial":        stats["partidos_oficial"],
            "ganados_oficial":         stats["ganados_oficial"],
            "empatados_oficial":       stats["empatados_oficial"],
            "perdidos_oficial":        stats["perdidos_oficial"],
            "goles_favor_oficial":     stats["goles_favor_oficial"],
            "goles_contra_oficial":    stats["goles_contra_oficial"],
            "forma_oficial":           stats["forma_oficial"],
            "ultimos_5_oficial":       stats["ultimos_5_oficial"],

            # ── Estadísticas en AMISTOSOS ────────────────────────────────────
            "partidos_amistoso":       stats["partidos_amistoso"],
            "ganados_amistoso":        stats["ganados_amistoso"],
            "empatados_amistoso":      stats["empatados_amistoso"],
            "perdidos_amistoso":       stats["perdidos_amistoso"],
            "goles_favor_amistoso":    stats["goles_favor_amistoso"],
            "goles_contra_amistoso":   stats["goles_contra_amistoso"],
            "forma_amistosos":         stats["forma_amistosos"],
            "ultimos_5_amistoso":      stats["ultimos_5_amistoso"],

            # ── Local / Visita / Neutro ──────────────────────────────────────
            "partidos_local":          stats["partidos_local"],
            "ganados_local":           stats["ganados_local"],
            "empatados_local":         stats["empatados_local"],
            "perdidos_local":          stats["perdidos_local"],
            "win_rate_local":          stats["win_rate_local"],
            "partidos_visita":         stats["partidos_visita"],
            "ganados_visita":          stats["ganados_visita"],
            "empatados_visita":        stats["empatados_visita"],
            "perdidos_visita":         stats["perdidos_visita"],
            "win_rate_visita":         stats["win_rate_visita"],
            "win_rate_neutro":         stats["win_rate_neutro"],

            # ── Racha ────────────────────────────────────────────────────────
            "imbatido_streak":         stats["imbatido_streak"],
        }

    print(f"    ✅ {len(selecciones)} selecciones procesadas")
    return selecciones



# ══════════════════════════════════════════════════════════════════════════════
# ALIASES — nombres ESPN → nombres del ranking FIFA
# ESPN usa nombres distintos para varias selecciones
# ══════════════════════════════════════════════════════════════════════════════

_ALIASES_ESPN: dict[str, str] = {
    # key normalizado ESPN  →  key normalizado del ranking FIFA
    "usa":                  "unitedstates",
    "unitedstatesofamerica":"unitedstates",
    "unitedstates":         "unitedstates",
    "korearepublic":        "southkorea",
    "republicofkorea":      "southkorea",
    "korea":                "southkorea",
    "turkiye":              "turkey",
    "turquia":              "turkey",
    "czechia":              "czechrepublic",
    "czechrepublic":        "czechrepublic",
    "cotedivoire":          "ivorycoast",
    "côted'ivoire":         "ivorycoast",
    "ivorycoast":           "ivorycoast",
    "curacao":              "curacao",
    "curaçao":              "curacao",
    "iriran":               "iran",
    "islamicrepublicofiran":"iran",
    "northernireland":      "northernireland",
    "republicofireland":    "ireland",
    "bosniaherzegovina":    "bosniaandherzegovina",
    "bosniaherzegovina":    "bosniaandherzegovina",
    "trinidadtobago":       "trinidadandtobago",
    "drcongo":              "drcongo",
    "congodr":              "drcongo",
    "democraticrepublicofthecongo": "drcongo",
    "capeverde":            "capeverde",
    "antiguabarbuda":       "antiguaandbarbuda",
    "saudiarabia":          "saudiarabia",
    "newzealand":           "newzealand",
    "elsalvador":           "elsalvador",
    "costarica":            "costarica",
    "panamacanal":          "panama",
    "uae":                  "unitedarabemirates",
    "unitedarabemirates":   "unitedarabemirates",
    "northmacedonia":       "northmacedonia",
    "macedonianorthmacedonia": "northmacedonia",
}


def _resolver_key_ranking(nombre_espn: str, ranking: dict) -> dict | None:
    """
    Busca una selección en el ranking por su nombre ESPN.
    Intenta: match exacto → alias → búsqueda parcial.
    """
    key = normalizar_nombre(nombre_espn)

    # 1. Match exacto
    if key in ranking:
        return ranking[key]

    # 2. Alias conocido
    alias_key = _ALIASES_ESPN.get(key)
    if alias_key and alias_key in ranking:
        return ranking[alias_key]

    # 3. Búsqueda parcial (el key del ranking está contenido en el key ESPN o viceversa)
    for rk, rv in ranking.items():
        if rk in key or key in rk:
            return rv

    return None

# ══════════════════════════════════════════════════════════════════════════════
# CRUZAR RANKING FIFA
# ══════════════════════════════════════════════════════════════════════════════

def enriquecer_con_ranking(selecciones: dict, ranking: dict) -> dict:
    enriched = 0
    sin_match = []
    for key, sel in selecciones.items():
        match = _resolver_key_ranking(sel["nombre"], ranking)
        if match:
            sel["ranking_fifa"] = match["ranking_fifa"]
            sel["puntos_fifa"]  = match["puntos_fifa"]
            enriched += 1
        else:
            sel["ranking_fifa"] = 999
            sel["puntos_fifa"]  = 500.0
            sin_match.append(sel["nombre"])

    print(f"    ✅ Ranking FIFA cruzado: {enriched}/{len(selecciones)}")
    if sin_match:
        print(f"    ⚠️  Sin match: {sin_match}")
    return selecciones


# ══════════════════════════════════════════════════════════════════════════════
# H2H
# ══════════════════════════════════════════════════════════════════════════════

def scrape_h2h_partido(
    id_local: str, id_visitante: str,
    nombre_local: str, nombre_visitante: str,
    league: str,
) -> dict | None:
    data = espn_get(
        f"{BASE_ESPN}/{league}/teams/{id_local}/schedule",
        {"limit": 50},
    )
    if not data:
        return None

    partidos_h2h = []
    for evento in data.get("events", []):
        try:
            comp    = evento.get("competitions", [{}])[0]
            equipos = comp.get("competitors", [])
            ids     = [str(e.get("team", {}).get("id", "")) for e in equipos]
            if str(id_visitante) not in ids:
                continue
            estado = comp.get("status", {}).get("type", {}).get("state", "")
            if estado != "post":
                continue
            local_e = next(e for e in equipos if e.get("homeAway") == "home")
            visit_e = next(e for e in equipos if e.get("homeAway") == "away")
            partidos_h2h.append({
                "fecha":           evento.get("date", "")[:10],
                "local":           local_e.get("team", {}).get("displayName", ""),
                "visitante":       visit_e.get("team", {}).get("displayName", ""),
                "goles_local":     int(local_e.get("score", 0) or 0),
                "goles_visitante": int(visit_e.get("score", 0) or 0),
            })
        except Exception:
            continue

    if not partidos_h2h:
        return None

    return {
        "equipo_a":           nombre_local,
        "equipo_b":           nombre_visitante,
        "partidos_recientes": partidos_h2h[:10],
    }


def scrape_h2h_torneo(fixture: list, league: str) -> dict:
    print(f"  🤝 Descargando H2H...")
    h2h = {}
    for partido in fixture:
        if not partido["id_espn_local"] or not partido["id_espn_visitante"]:
            continue
        resultado = scrape_h2h_partido(
            partido["id_espn_local"], partido["id_espn_visitante"],
            partido["local"], partido["visitante"],
            league,
        )
        if resultado:
            key = f"{normalizar_nombre(partido['local'])}_{normalizar_nombre(partido['visitante'])}"
            h2h[key] = resultado
        time.sleep(0.3)
    print(f"    ✅ {len(h2h)} cruces H2H")
    return h2h


# ══════════════════════════════════════════════════════════════════════════════
# ALTITUD RELATIVA EN FIXTURE
# ══════════════════════════════════════════════════════════════════════════════

def enriquecer_fixture_altitud(fixture: list, selecciones: dict) -> list:
    for partido in fixture:
        sel_l = selecciones.get(normalizar_nombre(partido["local"]), {})
        sel_v = selecciones.get(normalizar_nombre(partido["visitante"]), {})

        alt_base_l = sel_l.get("altitud_base", 15)
        alt_base_v = sel_v.get("altitud_base", 15)
        alt_sede   = partido.get("altitud_sede", 0) or 0

        partido["altitud_base_local"]           = alt_base_l
        partido["altitud_base_visitante"]       = alt_base_v
        partido["diferencia_altitud_local"]     = max(0, alt_sede - alt_base_l)
        partido["diferencia_altitud_visitante"] = max(0, alt_sede - alt_base_v)

        if alt_sede >= 2500:
            partido["contexto_altitud"] = f"Sede en altura extrema ({alt_sede}m)"
        elif alt_sede >= 1500:
            partido["contexto_altitud"] = f"Sede en altura considerable ({alt_sede}m)"
        elif alt_sede >= 800:
            partido["contexto_altitud"] = f"Sede en altura moderada ({alt_sede}m)"
        else:
            partido["contexto_altitud"] = f"Sede a nivel de mar/bajo ({alt_sede}m)"

    return fixture


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def normalizar_nombre(nombre: str) -> str:
    reemplazos = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}
    n = str(nombre).lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def guardar_json(data, ruta: str):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"    💾 {ruta}  ({len(data)} entradas)")


# ══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_scrapper(torneo_key: str, dias_adelante: int = 14):
    cfg = TORNEOS_CONFIG.get(torneo_key)
    if not cfg:
        print(f"❌ Torneo '{torneo_key}' no encontrado.")
        print(f"   Opciones: {list(TORNEOS_CONFIG.keys())}")
        return

    carpeta  = cfg["carpeta"]
    league   = cfg["espn_league"]
    season   = cfg["espn_season"]
    base_dir = os.path.join("scrapper", carpeta)

    print(f"\n{'='*60}")
    print(f"🌍  {cfg['descripcion']}")
    print(f"    League : {league}  |  Season : {season}")
    print(f"    Salida : {base_dir}/")
    print(f"{'='*60}\n")

    ranking     = scrape_ranking_fifa();                        time.sleep(0.5)
    fixture     = scrape_fixture(league, season, dias_adelante); time.sleep(0.5)
    selecciones = scrape_selecciones_torneo(league, season, fixture); time.sleep(0.5)

    print("\n  🔗 Cruzando ranking FIFA con selecciones...")
    selecciones = enriquecer_con_ranking(selecciones, ranking)

    h2h = scrape_h2h_torneo(fixture, league);                  time.sleep(0.5)

    print("\n  📐 Calculando altitudes relativas...")
    fixture = enriquecer_fixture_altitud(fixture, selecciones)

    print(f"\n  💾 Guardando en {base_dir}/")
    guardar_json(selecciones, os.path.join(base_dir, "selecciones.json"))
    guardar_json(fixture,     os.path.join(base_dir, "fixture.json"))
    guardar_json(h2h,         os.path.join(base_dir, "h2h.json"))

    print(f"\n{'='*60}")
    print(f"✅  Completado — {cfg['descripcion']}")
    print(f"    Selecciones : {len(selecciones)}")
    print(f"    Partidos    : {len(fixture)}")
    print(f"    H2H         : {len(h2h)}")

    if fixture:
        print(f"\n    📅 Próximos partidos:")
        for p in fixture[:6]:
            dif_v = p.get("diferencia_altitud_visitante", 0)
            warn  = f"  ⚠️  +{dif_v}m para {p['visitante']}" if dif_v > 800 else ""
            print(f"       {p['fecha'][:10]}  {p['local']:<22} vs {p['visitante']:<22}"
                  f"  [{p['ciudad_sede'] or 'N/D'} — {p['altitud_sede']}m]{warn}")

    if selecciones:
        print(f"\n    📊 Muestra de selecciones (ranking FIFA):")
        top = sorted(
            selecciones.values(),
            key=lambda s: s.get("ranking_fifa") or 999,
        )[:8]
        for s in top:
            of = s["partidos_oficial"]
            am = s["partidos_amistoso"]
            print(f"       #{s['ranking_fifa']:>3}  {s['nombre']:<22}  "
                  f"of:{of:>2}  am:{am:>2}  "
                  f"forma_of:{s['forma_oficial']:.2f}  "
                  f"alt:{s['altitud_base']}m")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrapper de selecciones nacionales — ESPN + FIFA"
    )
    parser.add_argument(
        "--torneo", type=str, default="amistosos_jun2026",
        help=f"Clave del torneo. Opciones: {list(TORNEOS_CONFIG.keys())}",
    )
    parser.add_argument(
        "--todos", action="store_true",
        help="Scrapea todos los torneos configurados",
    )
    parser.add_argument(
        "--dias", type=int, default=14,
        help="Días hacia adelante para buscar partidos (default: 14). Usa 90+ para el Mundial.",
    )
    args = parser.parse_args()

    if args.todos:
        for key in TORNEOS_CONFIG:
            run_scrapper(key, dias_adelante=args.dias)
            time.sleep(2)
    else:
        run_scrapper(args.torneo, dias_adelante=args.dias)