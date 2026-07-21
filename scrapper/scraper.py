import requests
import json
import time
import os
import argparse
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.espn.com.mx/",
    "Origin": "https://www.espn.com.mx"
}

PESOS_FORMA = [0.35, 0.25, 0.20, 0.12, 0.08]

PESO_COMPETENCIA = {
    "mex.1":                  1.0,
    "mex.2":                  1.0,
    "eng.1":                  1.0,
    "esp.1":                  1.0,
    "ger.1":                  1.0,
    "fra.1":                  1.0,
    "ita.1":                  1.0,
    "ned.1":                  1.0,
    "bel.1":                  1.0,
    "bra.1":                  1.0,
    "usa.1":                  1.0,
    "sco.1":                  1.0,
    "gre.1":                  1.0,
    "rus.1":                  1.0,
    "arg.1":                  1.0,
    "col.1":                  1.0,
    "chi.1":                  1.0,
    "jpn.1":                  1.0,
    "uru.1":                  1.0,
    "ven.1":                  1.0,
    "ecu.1":                  1.0,
    "per.1":                  1.0,
    "usa.nwsl":               1.0,
    "mex.women":              1.0,
    "conmebol.libertadores":  0.90,
    "conmebol.sudamericana":  0.80,
    "concacaf.champions":     0.70,
    "concacaf.w.champions":   0.70,
    "uefa.champions":         0.60,
    "afc.champions":          0.60,
    "uefa.europa":            0.55,
    "uefa.europa.conf":       0.50,
    "eng.fa":                 0.40,
    "esp.copa":               0.40,
    "ger.dfb_pokal":          0.40,
    "fra.cup":                0.40,
    "mex.copa":               0.40,
}

LIGAS_CONFIG = {
    "mex.1": {
        "nombre":                  "Liga MX",
        "carpeta":                 "LIGA-MX",
        "copas":                   ["mex.1", "concacaf.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "mex.1",
        "tiene_apertura_clausura": True,
    },
    "mex.2": {
        "nombre":                  "Liga de Expansión MX",
        "carpeta":                 "LIGA-MX-EXPANSION",
        "copas":                   ["mex.2"],
        "es_torneo_copa":          False,
        "liga_principal":          "mex.2",
        "tiene_apertura_clausura": True,
    },
    "eng.1": {
        "nombre":                  "Premier League",
        "carpeta":                 "PREMIER-LEAGUE",
        "copas":                   ["eng.1", "uefa.champions", "eng.fa"],
        "es_torneo_copa":          False,
        "liga_principal":          "eng.1",
        "tiene_apertura_clausura": False,
    },
    "esp.1": {
        "nombre":                  "La Liga",
        "carpeta":                 "LALIGA",
        "copas":                   ["esp.1", "uefa.champions", "esp.copa"],
        "es_torneo_copa":          False,
        "liga_principal":          "esp.1",
        "tiene_apertura_clausura": False,
    },
    "ger.1": {
        "nombre":                  "Bundesliga",
        "carpeta":                 "BUNDESLIGA",
        "copas":                   ["ger.1", "uefa.champions", "ger.dfb_pokal"],
        "es_torneo_copa":          False,
        "liga_principal":          "ger.1",
        "tiene_apertura_clausura": False,
    },
    "fra.1": {
        "nombre":                  "Ligue 1",
        "carpeta":                 "LIGUE-1",
        "copas":                   ["fra.1", "uefa.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "fra.1",
        "tiene_apertura_clausura": False,
    },
    "ned.1": {
        "nombre":                  "Eredivisie",
        "carpeta":                 "EREDIVISIE",
        "copas":                   ["ned.1", "uefa.europa"],
        "es_torneo_copa":          False,
        "liga_principal":          "ned.1",
        "tiene_apertura_clausura": False,
    },
    "bel.1": {
        "nombre":                  "Belgian Pro League",
        "carpeta":                 "BELGIAN-PRO-LEAGUE",
        "copas":                   ["bel.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "bel.1",
        "tiene_apertura_clausura": False,
    },
    "bra.1": {
        "nombre":                  "Brasileirao Serie A",
        "carpeta":                 "BRASILEIRAO-SERIE-A",
        "copas":                   ["bra.1", "conmebol.libertadores", "conmebol.sudamericana"],
        "es_torneo_copa":          False,
        "liga_principal":          "bra.1",
        "tiene_apertura_clausura": False,
    },
    "arg.1": {
        "nombre":                  "Liga Profesional Argentina",
        "carpeta":                 "LIGA-PROFESIONAL-ARGENTINA",
        "copas":                   [
            "arg.1",
            "conmebol.libertadores",
            "conmebol.sudamericana"
        ],
        "es_torneo_copa":          False,
        "tiene_grupos":            True,
        "liga_principal":          "arg.1",
        "tiene_apertura_clausura": True,
    },
    "usa.1": {
        "nombre":                  "MLS",
        "carpeta":                 "MLS",
        "copas":                   ["usa.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "usa.1",
        "tiene_apertura_clausura": False,
    },
    "sco.1": {
        "nombre":                  "Scottish Premiership",
        "carpeta":                 "SCOTTISH-PREMIERSHIP",
        "copas":                   ["sco.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "sco.1",
        "tiene_apertura_clausura": False,
    },
    "gre.1": {
        "nombre":                  "Super League Grecia",
        "carpeta":                 "SUPERLIGA-GRECIA",
        "copas":                   ["gre.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "gre.1",
        "tiene_apertura_clausura": False,
    },
    "rus.1": {
        "nombre":                  "Liga Premier Rusia",
        "carpeta":                 "LIGAPREMIER-RUSIA",
        "copas":                   ["rus.1"],
        "es_torneo_copa":          False,
        "liga_principal":          "rus.1",
        "tiene_apertura_clausura": False,
    },
    "chi.1": {
        "nombre":                  "Liga Chilena Primera División",
        "carpeta":                 "LIGA-CHILENA",
        "copas":                   ["chi.1", "conmebol.libertadores", "conmebol.sudamericana"],
        "es_torneo_copa":          False,
        "liga_principal":          "chi.1",
        "tiene_apertura_clausura": False,
    },
    "jpn.1": {
        "nombre":                  "J1 League",
        "carpeta":                 "J1-LEAGUE",
        "copas":                   ["jpn.1", "afc.champions"],
        "es_torneo_copa":          False,
        "liga_principal":          "jpn.1",
        "tiene_apertura_clausura": False,
    },
    "ger.dfb_pokal": {
        "nombre":                  "DFB-Pokal (Copa Alemana)",
        "carpeta":                 "DFB-POKAL",
        "copas":                   ["ger.dfb_pokal"],
        "es_torneo_copa":          True,
        "liga_principal":          "ger.dfb_pokal",
        "tiene_apertura_clausura": False,
        "ligas_locales":           ["ger.1", "ger.2"],
    },
    "uefa.europa": {
        "nombre":                  "UEFA Europa League",
        "carpeta":                 "EUROPA-LEAGUE",
        "copas":                   ["uefa.europa"],
        "es_torneo_copa":          True,
        "liga_principal":          "uefa.europa",
        "tiene_apertura_clausura": False,
        "ligas_locales":           ["eng.1", "esp.1", "ger.1", "fra.1", "ita.1",
                                    "ned.1", "por.1", "bel.1", "sco.1", "gre.1"],
    },
    # ── GRUPOS ───────────────────────────────────────────────────────────
    "conmebol.libertadores": {
        "nombre":                  "CONMEBOL Libertadores",
        "carpeta":                 "LIBERTADORES",
        "copas":                   ["conmebol.libertadores"],
        "es_torneo_copa":          True,
        "tiene_grupos":            True,           # <-- NUEVO
        "liga_principal":          "conmebol.libertadores",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["bra.1", "arg.1", "col.1", "chi.1",
                                    "uru.1", "ven.1", "ecu.1", "per.1", "mex.1"],
    },
    "conmebol.sudamericana": {
        "nombre":                  "CONMEBOL Sudamericana",
        "carpeta":                 "SUDAMERICANA",
        "copas":                   ["conmebol.sudamericana"],
        "es_torneo_copa":          True,
        "tiene_grupos":            True,           # <-- NUEVO
        "liga_principal":          "conmebol.sudamericana",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["bra.1", "arg.1", "col.1", "chi.1",
                                    "uru.1", "ven.1", "ecu.1", "per.1"],
    },
    "concacaf.w.champions": {
        "nombre":                  "Concacaf W Champions Cup",
        "carpeta":                 "CONCACAF-W-CHAMPIONS",
        "copas":                   ["concacaf.w.champions"],
        "es_torneo_copa":          True,
        "liga_principal":          "concacaf.w.champions",
        "tiene_apertura_clausura": False,
        "season_type_id":          "2",
        "ligas_locales":           ["usa.nwsl", "mex.women"],
    },
}


# ─────────────────────────────────────────────
# DIAGNÓSTICO
# ─────────────────────────────────────────────

def diagnosticar(liga_slug):
    standings_url  = f"https://site.api.espn.com/apis/v2/sports/soccer/{liga_slug}/standings"
    teams_url      = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams"
    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/scoreboard"

    print("🔎 DIAGNÓSTICO DE ENDPOINTS\n")
    urls = {
        "standings":  standings_url,
        "teams":      teams_url,
        "scoreboard": scoreboard_url,
    }
    resultados = {}
    for nombre, url in urls.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            size = len(r.text)
            ok = r.status_code == 200 and size > 100
            print(f"  {'✅' if ok else '❌'} {nombre}: HTTP {r.status_code} | {size} chars")
            if ok:
                resultados[nombre] = r.json()
            else:
                print(f"     Respuesta: {r.text[:120]}")
                resultados[nombre] = None
        except Exception as e:
            print(f"  ❌ {nombre}: ERROR - {e}")
            resultados[nombre] = None
    print()
    return resultados


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_stat(stats, name):
    for s in stats:
        if s.get("name") == name:
            return s.get("value", 0)
    return 0


def normalizar(nombre):
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    n = nombre.lower().replace(" ", "")
    for a, b in reemplazos.items():
        n = n.replace(a, b)
    return n


def calcular_forma_ponderada(partidos):
    ultimos = partidos[:5]
    while len(ultimos) < 5:
        ultimos.append(None)
    score = 0.0
    for i, p in enumerate(ultimos):
        if p is None:
            continue
        pts       = 1.0 if p["resultado"] == "W" else (0.5 if p["resultado"] == "D" else 0.0)
        peso_pos  = PESOS_FORMA[i]
        peso_comp = PESO_COMPETENCIA.get(p["liga"], 0.5)
        score    += pts * peso_pos * peso_comp
    return round(score, 4)


def calcular_imbatido_streak(resultados):
    streak = 0
    for r in resultados:
        if r in ("W", "D"):
            streak += 1
        else:
            break
    return streak


# ─────────────────────────────────────────────
# PARSEAR ENTRY (helper compartido)
# ─────────────────────────────────────────────

def _parsear_entry(entry):
    team    = entry.get("team", {})
    stats   = entry.get("stats", [])
    team_id = team.get("id")
    if not team_id:
        return None

    ganados     = int(get_stat(stats, "wins"))
    empatados   = int(get_stat(stats, "ties"))
    perdidos    = int(get_stat(stats, "losses"))
    partidos    = int(get_stat(stats, "gamesPlayed"))
    puntos      = int(get_stat(stats, "points"))
    gf          = int(get_stat(stats, "pointsFor"))
    gc          = int(get_stat(stats, "pointsAgainst"))
    posicion    = int(get_stat(stats, "rank"))
    rank_change = int(get_stat(stats, "rankChange"))
    logo_url    = team.get("logos", [{}])[0].get("href", "")

    fila = {
        "posicion":         posicion,
        "equipo":           team["displayName"],
        "id":               team_id,
        "partidos":         partidos,
        "ganados":          ganados,
        "empatados":        empatados,
        "perdidos":         perdidos,
        "goles_favor":      gf,
        "goles_contra":     gc,
        "diferencia_goles": gf - gc,
        "puntos":           puntos,
    }

    equipo = {
        "nombre":               team["displayName"],
        "abreviacion":          team.get("abbreviation", ""),
        "escudo":               logo_url,
        "posicion":             posicion,
        "posicion_anterior":    posicion - rank_change,
        "tendencia_posicion":   rank_change,
        "partidos":             partidos,
        "ganados":              ganados,
        "empatados":            empatados,
        "perdidos":             perdidos,
        "puntos":               puntos,
        "goles_favor":          gf,
        "goles_contra":         gc,
        "goles_diff":           gf - gc,
        "goles_favor_promedio":  round(gf / partidos, 3) if partidos else 0,
        "goles_contra_promedio": round(gc / partidos, 3) if partidos else 0,
        "competencias":         {},
        "forma_ponderada":      0.0,
        "forma_liga":           0.0,
        "ultimos_5_liga":       [],
        "imbatido_streak":      0,
        "forma_liga_local":     None,
        "ultimos_5_liga_local": None,
        "liga_local_slug":      None,
    }
    return team_id, fila, equipo


# ─────────────────────────────────────────────
# PARSEAR STANDINGS (liga plana)
# ─────────────────────────────────────────────

def parsear_standings(data):
    tabla        = []
    equipos_dict = {}

    children = data.get("children", [])
    if children:
        for idx, child in enumerate(children):
            child_name = child.get("name", f"grupo_{idx}")
            entries = (
                child.get("standings", {}).get("entries", [])
                or child.get("entries", [])
            )
            if entries:
                print(f"  children[{idx}] ({child_name}): {len(entries)} equipos ✅")
                for entry in entries:
                    resultado = _parsear_entry(entry)
                    if resultado is None:
                        continue
                    team_id, fila, equipo = resultado
                    if team_id not in equipos_dict:
                        tabla.append(fila)
                        equipos_dict[team_id] = equipo

        if equipos_dict:
            print(f"  Total tras merge de {len(children)} conferencia(s): {len(equipos_dict)} equipos ✅")
            tabla.sort(key=lambda x: x["posicion"])
            return tabla, equipos_dict

    try:
        entries = data["standings"]["entries"]
        print("  Estructura: standings.entries ✅")
        for entry in entries:
            resultado = _parsear_entry(entry)
            if resultado is None:
                continue
            team_id, fila, equipo = resultado
            if team_id not in equipos_dict:
                tabla.append(fila)
                equipos_dict[team_id] = equipo
        if equipos_dict:
            tabla.sort(key=lambda x: x["posicion"])
            return tabla, equipos_dict
    except (KeyError, TypeError):
        pass

    try:
        entries = data["entries"]
        print("  Estructura: entries ✅")
        for entry in entries:
            resultado = _parsear_entry(entry)
            if resultado is None:
                continue
            team_id, fila, equipo = resultado
            if team_id not in equipos_dict:
                tabla.append(fila)
                equipos_dict[team_id] = equipo
        if equipos_dict:
            tabla.sort(key=lambda x: x["posicion"])
            return tabla, equipos_dict
    except (KeyError, TypeError):
        pass

    print("  ❌ No se encontraron entries. Keys:", list(data.keys()))
    return tabla, equipos_dict


# ─────────────────────────────────────────────
# PARSEAR STANDINGS CON GRUPOS  (NUEVO)
# ─────────────────────────────────────────────

def parsear_standings_grupos(data):
    """
    Preserva la estructura de grupos del torneo.

    Retorna:
      grupos_list  — lista de dicts { "grupo": str, "equipos": [fila, ...] }
      equipos_dict — dict { team_id: equipo } para el loop de partidos
    """
    grupos_list  = []
    equipos_dict = {}

    children = data.get("children", [])
    if not children:
        print("  ❌ No se encontraron children[] para estructura de grupos.")
        return grupos_list, equipos_dict

    print(f"  Grupos detectados en standings: {len(children)}")

    for idx, child in enumerate(children):
        nombre_grupo = (
            child.get("name")
            or child.get("abbreviation")
            or f"Grupo {idx + 1}"
        )
        entries = (
            child.get("standings", {}).get("entries", [])
            or child.get("entries", [])
        )
        if not entries:
            print(f"  ⚠️  {nombre_grupo}: sin entries, se omite")
            continue

        equipos_grupo = []
        for entry in entries:
            resultado = _parsear_entry(entry)
            if resultado is None:
                continue
            team_id, fila, equipo = resultado
            equipos_grupo.append(fila)          # fila conserva "id" temporalmente
            if team_id not in equipos_dict:
                equipos_dict[team_id] = equipo

        equipos_grupo.sort(key=lambda x: x["posicion"])
        grupos_list.append({
            "grupo":   nombre_grupo,
            "equipos": equipos_grupo,
        })
        print(f"  ✅ {nombre_grupo}: {len(equipos_grupo)} equipos")

    print(f"  Total equipos únicos: {len(equipos_dict)}")
    return grupos_list, equipos_dict


# ─────────────────────────────────────────────
# FALLBACK: EQUIPOS DESDE MÚLTIPLES FUENTES
# ─────────────────────────────────────────────

def _extraer_equipo_info(team):
    logos = team.get("logos", [])
    escudo = logos[0].get("href", "") if logos else team.get("logo", "")
    return {
        "nombre":      team.get("displayName", ""),
        "abreviacion": team.get("abbreviation", ""),
        "escudo":      escudo,
    }


def obtener_equipos_desde_standings_grupos(data):
    equipos = {}
    children = data.get("children", [])
    if not children:
        return equipos

    print(f"  → Standings con {len(children)} grupo(s) detectados")
    for grupo in children:
        entries = (
            grupo.get("standings", {}).get("entries", [])
            or grupo.get("entries", [])
        )
        for entry in entries:
            team    = entry.get("team", {})
            stats   = entry.get("stats", [])
            team_id = team.get("id")
            if not team_id or team_id in equipos:
                continue

            ganados   = int(get_stat(stats, "wins"))
            empatados = int(get_stat(stats, "ties"))
            perdidos  = int(get_stat(stats, "losses"))
            partidos  = int(get_stat(stats, "gamesPlayed"))
            puntos    = int(get_stat(stats, "points"))
            gf        = int(get_stat(stats, "pointsFor"))
            gc        = int(get_stat(stats, "pointsAgainst"))
            posicion  = int(get_stat(stats, "rank")) or 9
            logos     = team.get("logos", [])
            escudo    = logos[0].get("href", "") if logos else ""

            equipos[team_id] = {
                "nombre":               team.get("displayName", ""),
                "abreviacion":          team.get("abbreviation", ""),
                "escudo":               escudo,
                "posicion":             posicion,
                "posicion_anterior":    posicion,
                "tendencia_posicion":   0,
                "partidos":             partidos,
                "ganados":              ganados,
                "empatados":            empatados,
                "perdidos":             perdidos,
                "puntos":               puntos,
                "goles_favor":          gf,
                "goles_contra":         gc,
                "goles_diff":           gf - gc,
                "goles_favor_promedio":  round(gf / partidos, 3) if partidos else 0,
                "goles_contra_promedio": round(gc / partidos, 3) if partidos else 0,
                "competencias":         {},
                "forma_ponderada":      0.0,
                "forma_liga":           0.0,
                "ultimos_5_liga":       [],
                "imbatido_streak":      0,
                "forma_liga_local":     None,
                "ultimos_5_liga_local": None,
                "liga_local_slug":      None,
            }

    print(f"  → {len(equipos)} equipos extraídos de grupos")
    return equipos


def obtener_equipos_desde_teams(liga_slug):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/teams"
    equipos = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200 or len(r.text) < 100:
            return equipos
        data = r.json()
        for sport in data.get("sports", []):
            for league in sport.get("leagues", []):
                for t in league.get("teams", []):
                    team    = t.get("team", {})
                    team_id = team.get("id")
                    if team_id and team_id not in equipos:
                        equipos[team_id] = _extraer_equipo_info(team)
        print(f"  → {len(equipos)} equipos desde /teams")
    except Exception as e:
        print(f"  ⚠️  Teams endpoint error: {e}")
    return equipos


def obtener_equipos_desde_scoreboard(liga_slug, semanas=8):
    from datetime import timedelta

    equipos = {}
    hoy     = datetime.now(timezone.utc)

    fechas = []
    for i in range(semanas):
        fecha = hoy - timedelta(weeks=i)
        fechas.append(fecha.strftime("%Y%m%d"))

    for fecha_str in fechas:
        url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer"
               f"/{liga_slug}/scoreboard?dates={fecha_str}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                continue
            data = r.json()
            for evento in data.get("events", []):
                for comp in evento.get("competitions", []):
                    for competitor in comp.get("competitors", []):
                        team    = competitor.get("team", {})
                        team_id = team.get("id")
                        if team_id and team_id not in equipos:
                            equipos[team_id] = _extraer_equipo_info(team)
            time.sleep(0.2)
        except Exception:
            continue

    print(f"  → {len(equipos)} equipos desde scoreboard ({semanas} semanas)")
    return equipos


def obtener_equipos_copa_cascada(liga_slug, standings_data):
    equipos = obtener_equipos_desde_standings_grupos(standings_data or {})
    if len(equipos) >= 4:
        print(f"  ✅ Equipos obtenidos desde standings por grupos: {len(equipos)}")
        return equipos

    print("  ⚠️  Grupos insuficientes — intentando /teams...")
    equipos_teams = obtener_equipos_desde_teams(liga_slug)
    if len(equipos_teams) >= 4:
        print(f"  ✅ Equipos obtenidos desde /teams: {len(equipos_teams)}")
        return {
            tid: construir_equipo_copa(tid, info)
            for tid, info in equipos_teams.items()
        }

    print("  ⚠️  /teams insuficiente — usando scoreboard multi-fecha...")
    equipos_sb = obtener_equipos_desde_scoreboard(liga_slug, semanas=10)
    if equipos_sb:
        print(f"  ✅ Equipos obtenidos desde scoreboard: {len(equipos_sb)}")
        return {
            tid: construir_equipo_copa(tid, info)
            for tid, info in equipos_sb.items()
        }

    print("  ❌ No se pudieron obtener equipos por ninguna vía.")
    return {}


def construir_equipo_copa(team_id, info):
    return {
        "nombre":               info["nombre"],
        "abreviacion":          info["abreviacion"],
        "escudo":               info["escudo"],
        "posicion":             9,
        "posicion_anterior":    9,
        "tendencia_posicion":   0,
        "partidos":             0,
        "ganados":              0,
        "empatados":            0,
        "perdidos":             0,
        "puntos":               0,
        "goles_favor":          0,
        "goles_contra":         0,
        "goles_diff":           0,
        "goles_favor_promedio":  0.0,
        "goles_contra_promedio": 0.0,
        "competencias":         {},
        "forma_ponderada":      0.0,
        "forma_liga":           0.0,
        "ultimos_5_liga":       [],
        "imbatido_streak":      0,
        "forma_liga_local":     None,
        "ultimos_5_liga_local": None,
        "liga_local_slug":      None,
    }


# ─────────────────────────────────────────────
# PARTIDOS POR EQUIPO
# ─────────────────────────────────────────────

def obtener_partidos_equipo(team_id, copas):
    todos_partidos = []
    fechas_vistas  = set()

    for liga in copas:
        url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer"
               f"/{liga}/teams/{team_id}/schedule")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                continue
            data = r.json()
        except Exception:
            continue

        for evento in data.get("events", []):
            comp = evento.get("competitions", [{}])[0]
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue

            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            mi_equipo = next((c for c in competitors if str(c["id"]) == str(team_id)), None)
            rival     = next((c for c in competitors if str(c["id"]) != str(team_id)), None)
            if not mi_equipo or not rival:
                continue

            fecha = evento.get("date")
            if fecha in fechas_vistas:
                continue
            fechas_vistas.add(fecha)

            gane   = mi_equipo.get("winner", False)
            empate = not gane and not rival.get("winner", False)

            try:
                mis_goles   = int(float(mi_equipo.get("score", {}).get("displayValue", 0) or 0))
                goles_rival = int(float(rival.get("score",    {}).get("displayValue", 0) or 0))
            except Exception:
                mis_goles = goles_rival = 0

            todos_partidos.append({
                "fecha":        fecha,
                "liga":         liga,
                "es_local":     mi_equipo.get("homeAway") == "home",
                "resultado":    "W" if gane else ("D" if empate else "L"),
                "goles_favor":  mis_goles,
                "goles_contra": goles_rival,
            })

    todos_partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return todos_partidos


# ─────────────────────────────────────────────
# FIXTURE DE LA JORNADA ACTUAL COMPLETA  (ACTUALIZADO)
# ─────────────────────────────────────────────

def obtener_fixture_jornada(liga_slug):

    def _fmt(iso_str):
        return iso_str[:10].replace("-", "")

    base_url = (
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_slug}/scoreboard"
    )

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10)

        if r.status_code != 200 or len(r.text) < 100:
            print(f"  ❌ Fixture: HTTP {r.status_code}")
            return None

        data = r.json()

    except Exception as e:
        print(f"  ❌ Fixture: ERROR - {e}")
        return None

    leagues = data.get("leagues", [])
    league = leagues[0] if leagues else {}

    calendar = league.get("calendar", [])
    calendar_type = league.get("calendarType")

    temporada = None

    season_info = data.get("season", {})

    if isinstance(season_info, dict):
        temporada = season_info.get("year") or season_info.get("slug")

    hoy = datetime.now(timezone.utc).date()

    fecha_inicio = None
    fecha_fin = None
    jornada_num = None

    # ==========================================================
    # CASO 1: ESPN clásico (startDate/endDate)
    # ==========================================================

    entradas_calendar = []

    for c in calendar:

        if isinstance(c, dict) and "entries" in c:
            entradas_calendar.extend(c["entries"])
        else:
            entradas_calendar.append(c)

    candidato_futuro = None

    for c in entradas_calendar:

        if not isinstance(c, dict):
            continue

        if "startDate" not in c or "endDate" not in c:
            continue

        try:

            ini = datetime.fromisoformat(
                c["startDate"].replace("Z", "+00:00")
            ).date()

            fin = datetime.fromisoformat(
                c["endDate"].replace("Z", "+00:00")
            ).date()

        except Exception:
            continue

        if ini <= hoy <= fin:

            fecha_inicio = c["startDate"]
            fecha_fin = c["endDate"]
            jornada_num = c.get("value")

            break

        if ini > hoy and (
            candidato_futuro is None
            or ini < candidato_futuro[0]
        ):
            candidato_futuro = (ini, c)

    if fecha_inicio is None and candidato_futuro:

        _, c = candidato_futuro

        fecha_inicio = c["startDate"]
        fecha_fin = c["endDate"]
        jornada_num = c.get("value")

    # ==========================================================
    # CASO 2: Brasileirão / MLS / ligas calendarType=day
    # ==========================================================

    if fecha_inicio is None and calendar_type == "day":

        fechas = []

        for item in calendar:

            if not isinstance(item, str):
                continue

            try:

                d = datetime.fromisoformat(
                    item.replace("Z", "+00:00")
                ).date()

                if d >= hoy:
                    fechas.append(d)

            except Exception:
                continue

        fechas.sort()

        if fechas:

            inicio = fechas[0]
            fin = inicio

            for d in fechas[1:]:

                if (d - fin).days <= 1:
                    fin = d
                else:
                    break

            fecha_inicio = inicio.isoformat() + "T00:00:00Z"
            fecha_fin = fin.isoformat() + "T23:59:59Z"

            jornada_num = "day-block"

            print(
                f"  → CalendarType=day detectado: "
                f"{inicio} -> {fin}"
            )

    # ==========================================================
    # CONSULTA FINAL DEL RANGO
    # ==========================================================

    eventos = data.get("events", [])

    if fecha_inicio and fecha_fin:

        inicio_fmt = _fmt(fecha_inicio)
        fin_fmt = _fmt(fecha_fin)

        if inicio_fmt == fin_fmt:
            rango = inicio_fmt
        else:
            rango = f"{inicio_fmt}-{fin_fmt}"

        url_rango = f"{base_url}?dates={rango}"

        print(f"  → Consultando rango: {rango}")

        try:

            r2 = requests.get(
                url_rango,
                headers=HEADERS,
                timeout=10
            )

            if r2.status_code == 200 and len(r2.text) > 100:

                data2 = r2.json()

                eventos = data2.get("events", eventos)

                print(
                    f"  → {len(eventos)} partido(s) encontrados"
                )

            else:

                print(
                    f"  ⚠️ HTTP {r2.status_code} "
                    f"usando eventos iniciales"
                )

        except Exception as e:

            print(
                f"  ⚠️ Error consultando rango: {e}"
            )

    else:

        print(
            "  ⚠️ No se pudo determinar la jornada "
            "usando eventos iniciales"
        )

    partidos = []

    for evento in eventos:

        comp = evento.get("competitions", [{}])[0]

        competitors = comp.get("competitors", [])

        if len(competitors) < 2:
            continue

        local = next(
            (
                c
                for c in competitors
                if c.get("homeAway") == "home"
            ),
            competitors[0]
        )

        visitante = next(
            (
                c
                for c in competitors
                if c.get("homeAway") == "away"
            ),
            competitors[1]
        )

        status_type = comp.get("status", {}).get("type", {})

        estado = status_type.get(
            "description",
            "Programado"
        )

        completado = bool(
            status_type.get("completed", False)
        )

        en_vivo = status_type.get("state") == "in"

        def _score(c):

            try:

                val = c.get(
                    "score",
                    {}
                ).get(
                    "displayValue",
                    None
                )

                if val is None or val == "":
                    return None

                return int(float(val))

            except Exception:
                return None

        venue_info = comp.get("venue", {})

        partidos.append({
            "id_evento": evento.get("id"),
            "fecha": evento.get("date"),
            "jornada_nombre": evento.get("shortName", ""),
            "equipo_local": local.get("team", {}).get("displayName", ""),
            "escudo_local": (
                local.get("team", {}).get("logos") or [{}]
            )[0].get("href", ""),
            "equipo_visitante": visitante.get("team", {}).get("displayName", ""),
            "escudo_visitante": (
                visitante.get("team", {}).get("logos") or [{}]
            )[0].get("href", ""),
            "estadio": venue_info.get("fullName", ""),
            "ciudad": venue_info.get("address", {}).get("city", ""),
            "estado": estado,
            "en_vivo": en_vivo,
            "finalizado": completado,
            "goles_local": _score(local) if (completado or en_vivo) else None,
            "goles_visitante": _score(visitante) if (completado or en_vivo) else None,
        })

    partidos.sort(
        key=lambda x: x["fecha"] or ""
    )

    return {
        "liga": liga_slug,
        "jornada": jornada_num,
        "temporada": temporada,
        "partidos": partidos,
    }

# ─────────────────────────────────────────────
# STATS POR COMPETENCIA
# ─────────────────────────────────────────────

def calcular_stats_competencia(partidos):
    if not partidos:
        return {}

    locales = [p for p in partidos if p["es_local"]]
    visitas = [p for p in partidos if not p["es_local"]]

    def w(lst): return sum(1 for p in lst if p["resultado"] == "W")
    def d(lst): return sum(1 for p in lst if p["resultado"] == "D")
    def l(lst): return sum(1 for p in lst if p["resultado"] == "L")

    pl       = len(locales)
    pv       = len(visitas)
    total    = len(partidos)
    gf_total = sum(p["goles_favor"]  for p in partidos)
    gc_total = sum(p["goles_contra"] for p in partidos)
    resultados = [p["resultado"] for p in partidos]

    return {
        "partidos":               total,
        "ganados":                w(partidos),
        "empatados":              d(partidos),
        "perdidos":               l(partidos),
        "goles_favor":            gf_total,
        "goles_contra":           gc_total,
        "goles_favor_promedio":   round(gf_total / total, 3) if total else 0,
        "goles_contra_promedio":  round(gc_total / total, 3) if total else 0,
        "partidos_local":         pl,
        "ganados_local":          w(locales),
        "empatados_local":        d(locales),
        "perdidos_local":         l(locales),
        "win_rate_local":         round(w(locales) / pl, 3) if pl else 0,
        "partidos_visita":        pv,
        "ganados_visita":         w(visitas),
        "empatados_visita":       d(visitas),
        "perdidos_visita":        l(visitas),
        "win_rate_visita":        round(w(visitas) / pv, 3) if pv else 0,
        "ultimos_5":              resultados[:5],
        "imbatido_streak":        calcular_imbatido_streak(resultados),
    }


def calcular_stats(partidos, liga_principal):
    if not partidos:
        return {}, 0.0

    por_competencia = {}
    for p in partidos:
        por_competencia.setdefault(p["liga"], []).append(p)

    competencias = {
        liga: calcular_stats_competencia(ps)
        for liga, ps in por_competencia.items()
    }

    forma_combinada = calcular_forma_ponderada(partidos)
    return competencias, forma_combinada


# ─────────────────────────────────────────────
# FORMA EN LIGA LOCAL (torneos copa)
# ─────────────────────────────────────────────

def obtener_forma_liga_local(team_id, ligas_locales):
    for liga_slug in ligas_locales:
        try:
            partidos = obtener_partidos_equipo(team_id, [liga_slug])
            partidos_liga = [p for p in partidos if p["liga"] == liga_slug]
            if partidos_liga:
                forma  = calcular_forma_ponderada(partidos_liga)
                ul5    = [p["resultado"] for p in partidos_liga[:5]]
                return forma, ul5, liga_slug
        except Exception:
            continue
    return 0.0, [], None


# ─────────────────────────────────────────────
# GUARDADO
# ─────────────────────────────────────────────

def guardar_json(data, carpeta, filename):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, filename)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Guardado: {ruta}")


# ─────────────────────────────────────────────
# MAIN: SCRAPEAR LIGA O TORNEO
# ─────────────────────────────────────────────

def scrapear_liga(liga_slug):
    config = LIGAS_CONFIG.get(liga_slug)
    if not config:
        print(f"❌ Slug '{liga_slug}' no encontrado en LIGAS_CONFIG.")
        return

    es_copa        = config.get("es_torneo_copa", False)
    tiene_grupos   = config.get("tiene_grupos", False)        # NUEVO
    liga_principal = config["liga_principal"]
    copas          = config["copas"]
    ligas_locales  = config.get("ligas_locales", [])

    print(f"\n🚀 Scraper — {config['nombre']} ({liga_slug})")
    print(f"   Tipo: {'Torneo con grupos' if tiene_grupos else ('Torneo copa' if es_copa else 'Liga regular')}")
    print("=" * 50)

    datos = diagnosticar(liga_slug)

    print("📊 Procesando equipos...")
    tabla        = []
    grupos_list  = []                                          # NUEVO
    equipos_dict = {}

    if not es_copa:
        # ── Liga regular ──────────────────────────────────────────────────
        if datos.get("standings"):
            tabla, equipos_dict = parsear_standings(datos["standings"])
            print(f"  ✅ {len(equipos_dict)} equipos desde standings")
        else:
            print("  ❌ No hay standings para liga regular. Abortando.")
            return

    elif tiene_grupos:
        # ── Torneo con fase de grupos (Libertadores, Sudamericana, etc.) ──
        if datos.get("standings"):
            print("  → Torneo con grupos: parseando estructura de grupos...")
            grupos_list, equipos_dict = parsear_standings_grupos(datos["standings"])
        else:
            print("  ❌ No hay standings con grupos. Abortando.")
            return

    else:
        # ── Torneo copa sin grupos ────────────────────────────────────────
        print("  → Torneo copa: usando estrategia en cascada...")
        equipos_dict = obtener_equipos_copa_cascada(liga_slug, datos.get("standings"))

    if not equipos_dict:
        print("  ❌ No se encontraron equipos. Abortando.")
        return

    print(f"\n📅 Obteniendo partidos ({', '.join(copas)})...")

    for team_id in list(equipos_dict.keys()):
        nombre = equipos_dict[team_id]["nombre"]
        print(f"  🔄 {nombre}...")

        try:
            partidos = obtener_partidos_equipo(team_id, copas)
            competencias, forma_combinada = calcular_stats(partidos, liga_principal)

            eq = equipos_dict[team_id]
            eq["competencias"]    = competencias
            eq["forma_ponderada"] = forma_combinada

            stats_principal = competencias.get(liga_principal, {})
            eq["forma_liga"]      = calcular_forma_ponderada(
                [p for p in partidos if p["liga"] == liga_principal]
            )
            eq["ultimos_5_liga"]  = stats_principal.get("ultimos_5", [])
            eq["imbatido_streak"] = stats_principal.get("imbatido_streak", 0)

            if es_copa and stats_principal:
                eq["partidos"]               = stats_principal.get("partidos", 0)
                eq["ganados"]                = stats_principal.get("ganados", 0)
                eq["empatados"]              = stats_principal.get("empatados", 0)
                eq["perdidos"]               = stats_principal.get("perdidos", 0)
                eq["goles_favor"]            = stats_principal.get("goles_favor", 0)
                eq["goles_contra"]           = stats_principal.get("goles_contra", 0)
                eq["goles_diff"]             = eq["goles_favor"] - eq["goles_contra"]
                eq["goles_favor_promedio"]   = stats_principal.get("goles_favor_promedio", 0.0)
                eq["goles_contra_promedio"]  = stats_principal.get("goles_contra_promedio", 0.0)

            if es_copa and ligas_locales:
                print(f"     → Buscando forma en liga local...")
                forma_local, ul5_local, liga_encontrada = obtener_forma_liga_local(
                    team_id, ligas_locales
                )
                eq["forma_liga_local"]     = forma_local
                eq["ultimos_5_liga_local"] = ul5_local
                eq["liga_local_slug"]      = liga_encontrada
                if liga_encontrada:
                    print(f"     → Liga local: {liga_encontrada} | Forma: {forma_local}")
                else:
                    print(f"     → Liga local no encontrada")

            time.sleep(0.3)

        except Exception as e:
            print(f"    ⚠️  Error procesando {nombre}: {e}")

    # ─────────────────────────────────────────
    # FIXTURE DE LA JORNADA ACTUAL COMPLETA
    # ─────────────────────────────────────────

    print(f"\n📅 Obteniendo fixture de la jornada actual ({liga_principal})...")
    fixture = obtener_fixture_jornada(liga_principal)
    if fixture and fixture["partidos"]:
        jornada_txt = fixture["jornada"] if fixture["jornada"] is not None else "?"
        print(f"  ✅ Jornada {jornada_txt}: {len(fixture['partidos'])} partido(s)")
        guardar_json(fixture, config["carpeta"], "fixture.json")
    else:
        print("  ⚠️  No se pudo obtener fixture de la jornada actual.")

    # ─────────────────────────────────────────
    # GUARDADO
    # ─────────────────────────────────────────

    if tiene_grupos and grupos_list:
        # grupos.json: estructura por grupo con stats enriquecidas
        grupos_export = []
        for g in grupos_list:
            equipos_grupo_export = []
            for fila in g["equipos"]:
                team_id = fila.get("id")
                eq_data = equipos_dict.get(team_id, {})
                equipo_out = {k: v for k, v in fila.items() if k != "id"}
                # Inyectar campos enriquecidos de equipos_dict
                equipo_out["escudo"]               = eq_data.get("escudo", "")
                equipo_out["abreviacion"]          = eq_data.get("abreviacion", "")
                equipo_out["forma_ponderada"]      = eq_data.get("forma_ponderada", 0.0)
                equipo_out["forma_liga"]           = eq_data.get("forma_liga", 0.0)
                equipo_out["ultimos_5_liga"]       = eq_data.get("ultimos_5_liga", [])
                equipo_out["imbatido_streak"]      = eq_data.get("imbatido_streak", 0)
                equipo_out["forma_liga_local"]     = eq_data.get("forma_liga_local")
                equipo_out["ultimos_5_liga_local"] = eq_data.get("ultimos_5_liga_local")
                equipo_out["liga_local_slug"]      = eq_data.get("liga_local_slug")
                equipo_out["competencias"]         = eq_data.get("competencias", {})
                equipos_grupo_export.append(equipo_out)

            grupos_export.append({
                "grupo":   g["grupo"],
                "equipos": equipos_grupo_export,
            })

        guardar_json(grupos_export, config["carpeta"], "grupos.json")

    elif tabla:
        tabla_export = [{k: v for k, v in t.items() if k != "id"} for t in tabla]
        guardar_json(tabla_export, config["carpeta"], "tabla.json")

    # equipos.json: siempre se guarda (indexado por nombre normalizado)
    equipos_final = {}
    for team_id, datos_equipo in equipos_dict.items():
        key = normalizar(datos_equipo["nombre"])
        equipos_final[key] = datos_equipo
    guardar_json(equipos_final, config["carpeta"], "equipos.json")

    # ─────────────────────────────────────────
    # RESUMEN
    # ─────────────────────────────────────────

    print(f"\n📋 RESUMEN — {config['nombre']}")
    print(f"   Equipos scrapeados: {len(equipos_final)}")
    print(f"   Carpeta: {config['carpeta']}/")

    if tiene_grupos and grupos_list:
        print(f"\n🏆 Grupos ({len(grupos_list)}):")
        for g in grupos_list:
            lider = g["equipos"][0] if g["equipos"] else {}
            print(f"   {g['grupo']}: líder → {lider.get('equipo','?')} ({lider.get('puntos','?')} pts)")
    elif tabla:
        print(f"\n🏆 Top 5:")
        for t in tabla[:5]:
            print(f"   {t['posicion']}. {t['equipo']} — {t['puntos']} pts")

    if fixture and fixture["partidos"]:
        jornada_txt = fixture["jornada"] if fixture["jornada"] is not None else "?"
        print(f"\n📅 Fixture jornada {jornada_txt}:")
        for p in fixture["partidos"][:10]:
            marcador = (
                f"{p['goles_local']}-{p['goles_visitante']}"
                if p["finalizado"] or p["en_vivo"] else "vs"
            )
            print(f"   {p['equipo_local']} {marcador} {p['equipo_visitante']}  ({p['estado']})")
    print()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scraper ESPN — Ligas y torneos, una carpeta por competencia"
    )
    parser.add_argument(
        "--liga",
        type=str,
        help=(
            "Slug de la liga o torneo. Ejemplos:\n"
            "  python scrapper.py --liga mex.1\n"
            "  python scrapper.py --liga conmebol.libertadores\n"
            "  python scrapper.py --liga conmebol.sudamericana\n"
            "  python scrapper.py --liga all\n"
            "  python scrapper.py --liga ligas\n"
            "  python scrapper.py --liga torneos"
        )
    )
    args = parser.parse_args()

    if not args.liga:
        print("Uso:")
        print("  python scrapper.py --liga mex.1")
        print("  python scrapper.py --liga conmebol.libertadores")
        print("  python scrapper.py --liga all")
        print("  python scrapper.py --liga ligas")
        print("  python scrapper.py --liga torneos")
        print("\nLigas y torneos disponibles:")
        print("\n  LIGAS REGULARES:")
        for slug, cfg in LIGAS_CONFIG.items():
            if not cfg.get("es_torneo_copa"):
                print(f"    {slug:<30} {cfg['nombre']}")
        print("\n  TORNEOS / COPAS:")
        for slug, cfg in LIGAS_CONFIG.items():
            if cfg.get("es_torneo_copa"):
                tipo = " [grupos]" if cfg.get("tiene_grupos") else ""
                print(f"    {slug:<30} {cfg['nombre']}{tipo}")

    elif args.liga == "all":
        for slug in LIGAS_CONFIG:
            scrapear_liga(slug)
            time.sleep(2)

    elif args.liga == "ligas":
        slugs = [s for s, c in LIGAS_CONFIG.items() if not c.get("es_torneo_copa")]
        for slug in slugs:
            scrapear_liga(slug)
            time.sleep(2)

    elif args.liga == "torneos":
        slugs = [s for s, c in LIGAS_CONFIG.items() if c.get("es_torneo_copa")]
        for slug in slugs:
            scrapear_liga(slug)
            time.sleep(2)

    else:
        scrapear_liga(args.liga)