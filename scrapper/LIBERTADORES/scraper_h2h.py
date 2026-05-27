import requests
import json
import time

# ============================================================
# H2H SCRAPER — COPA LIBERTADORES 2026  (Fase de Grupos)
# Basado en la ESPN public API (no requiere API key)
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.espn.com.mx/",
    "Origin": "https://www.espn.com.mx",
}

LEAGUE_SLUG  = "conmebol.libertadores"
TEAMS_URL    = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE_SLUG}/teams"
SCHEDULE_URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE_SLUG}/teams/{{team_id}}/schedule"

# URL alternativa con año explícito (2026)
SCHEDULE_URL_YEAR = (
    f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE_SLUG}"
    f"/teams/{{team_id}}/schedule?season=2026"
)

# ============================================================
# CONFIGURA AQUÍ LOS CRUCES DE TU JORNADA 6
# ============================================================
CRUCES_JORNADA_6 = [
    ("Lanús",    "Mirassol"),
    ("Liga de Quito", "Always Ready"),
    ("Flamengo", "Cusco FC"),    
    ("Estudiantes de La Plata", "Independiente Medellín"),
    ("Coquimbo Unido", "Nacional"),
    ("Universitario", "Deportes Tolima"),
    ("Independiente del Valle", "Rosario Central"),
    ("Universidad Central", "Libertad"),
    ("Cerro Porteño", "Sporting Cristal"),
    ("Palmeiras", "Atlético Junior"),
    ("Corinthians", "Platense"),
    ("Peñarol", "Independiente Santa Fe"),
    ("Fluminenses", "Deportivo La Guaira"),
    ("Bolívar", "Independiente Rivadavia"),
    ("Boca Juniors", "Universidad Católica"),
    ("Cruzeiro", "Barcelona SC"),
]

# Palabra clave para identificar Fase de Grupos en el nombre de temporada de ESPN.
# ESPN puede llamarla "Group Stage", "Fase de Grupos", "Regular Season", etc.
PALABRAS_FASE_GRUPOS = ["group", "fase", "regular", "groups"]

# Temporada de interés
TEMPORADA_OBJETIVO = "2026"


# ============================================================
# DIAGNÓSTICO: imprime TODOS los season types disponibles
# para un equipo dado — útil para depurar IDs incorrectos.
# ============================================================

def diagnosticar_season_types(team_id, nombre):
    """Descarga el schedule y muestra todos los season types únicos encontrados."""
    for url_tpl in [SCHEDULE_URL_YEAR, SCHEDULE_URL]:
        url = url_tpl.format(team_id=team_id)
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200 or len(r.text) < 100:
            continue

        data = r.json()
        season_types_vistos = {}
        total_eventos = 0

        for evento in data.get("events", []):
            total_eventos += 1
            st = evento.get("seasonType", {})
            sid   = str(st.get("id", "?"))
            sname = st.get("name", "?")
            fecha = evento.get("date", "")[:10]
            completado = evento.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("completed", False)
            season_types_vistos[sid] = sname
            # Muestra los 3 primeros eventos de cada tipo
            # (solo en diagnóstico)

        print(f"\n  📋 [{nombre}] URL: {url}")
        print(f"     Total eventos encontrados: {total_eventos}")
        print(f"     Season types detectados:")
        for sid, sname in season_types_vistos.items():
            print(f"       id={sid!r:>4}  →  {sname!r}")

        if total_eventos > 0:
            return  # Con una URL que funcione, basta


# ============================================================
# OBTENER IDs DE EQUIPOS
# ============================================================

def obtener_ids_equipos():
    print("🔍 Obteniendo IDs de equipos de la Libertadores...")
    r = requests.get(TEAMS_URL, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        raise Exception(f"Error {r.status_code} al obtener equipos: {r.text[:200]}")

    data = r.json()
    ids = {}
    for sport in data.get("sports", []):
        for league in sport.get("leagues", []):
            for t in league.get("teams", []):
                team = t["team"]
                ids[team["displayName"]] = team["id"]

    print(f"  ✅ {len(ids)} equipos encontrados")
    if ids:
        print("  Nombres disponibles:", list(ids.keys()))
    return ids


# ============================================================
# DETECTAR SEASON TYPE IDs DE LA FASE DE GRUPOS
# ============================================================

def detectar_season_ids_grupos(team_id):
    """
    Descarga el schedule del equipo e infiere qué season type IDs
    corresponden a la Fase de Grupos 2026.

    Estrategia:
      1. Usa la URL con ?season=2026 primero.
      2. Acepta un season type si su nombre contiene alguna de las
         PALABRAS_FASE_GRUPOS o si el año del evento es 2026.
      3. Si no encuentra nada, devuelve TODOS los IDs presentes
         (fallback permisivo) para no perder partidos.
    """
    ids_grupos = set()
    todos_ids  = set()

    for url_tpl in [SCHEDULE_URL_YEAR, SCHEDULE_URL]:
        url = url_tpl.format(team_id=team_id)
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except Exception as e:
            print(f"  ⚠️  Error de red: {e}")
            continue

        if r.status_code != 200 or len(r.text) < 100:
            continue

        data = r.json()
        for evento in data.get("events", []):
            st    = evento.get("seasonType", {})
            sid   = str(st.get("id", ""))
            sname = (st.get("name", "") or "").lower()
            fecha = evento.get("date", "")[:4]  # año

            if sid:
                todos_ids.add(sid)
                # Coincide por nombre de fase O por año 2026
                if any(p in sname for p in PALABRAS_FASE_GRUPOS) or fecha == TEMPORADA_OBJETIVO:
                    ids_grupos.add(sid)

        if todos_ids:
            break  # URL funcional encontrada

    if ids_grupos:
        return ids_grupos

    # Fallback: si no encontramos coincidencias por nombre, aceptamos todos
    print("  ⚠️  No se detectaron season types por nombre — usando todos los disponibles (fallback)")
    return todos_ids


# ============================================================
# OBTENER PARTIDOS COMPLETADOS DE UN EQUIPO
# ============================================================

def obtener_partidos_equipo(team_id, season_ids_permitidos=None):
    """
    Descarga todos los partidos completados del equipo.
    Si season_ids_permitidos es None, no filtra por season type.
    """
    resultado = []

    for url_tpl in [SCHEDULE_URL_YEAR, SCHEDULE_URL]:
        url = url_tpl.format(team_id=team_id)
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except Exception as e:
            print(f"  ⚠️  Error de red: {e}")
            continue

        if r.status_code != 200 or len(r.text) < 100:
            print(f"  ⚠️  Sin datos para team_id={team_id} ({r.status_code})")
            continue

        data = r.json()

        for evento in data.get("events", []):
            # ── Filtro de season type (permisivo si no se especifica) ──
            st_id = str(evento.get("seasonType", {}).get("id", ""))
            if season_ids_permitidos and st_id not in season_ids_permitidos:
                continue

            # ── Solo partidos ya jugados ──
            comp = evento.get("competitions", [{}])[0]
            completado = comp.get("status", {}).get("type", {}).get("completed", False)
            if not completado:
                continue

            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            mi_equipo = next((c for c in competitors if str(c["id"]) == str(team_id)), None)
            rival     = next((c for c in competitors if str(c["id"]) != str(team_id)), None)
            if not mi_equipo or not rival:
                continue

            try:
                mis_goles   = int(float(mi_equipo.get("score", {}).get("displayValue", 0) or 0))
                goles_rival = int(float(rival.get("score", {}).get("displayValue", 0) or 0))
            except Exception:
                mis_goles = goles_rival = 0

            resultado.append({
                "evento_id":    evento.get("id"),
                "fecha":        evento.get("date", "")[:10],
                "temporada":    evento.get("seasonType", {}).get("name", ""),
                "season_id":    st_id,
                "jornada":      evento.get("week", {}).get("number", "?") if evento.get("week") else "?",
                "es_local":     mi_equipo.get("homeAway") == "home",
                "rival_id":     rival.get("id"),
                "rival_nombre": rival.get("team", {}).get("displayName", ""),
                "goles_favor":  mis_goles,
                "goles_contra": goles_rival,
            })

        if resultado:
            break  # URL funcional encontrada

    return sorted(resultado, key=lambda x: x["fecha"], reverse=True)


# ============================================================
# CRUZAR H2H ENTRE DOS EQUIPOS
# ============================================================

def extraer_h2h(nombre_a, nombre_b, id_a, id_b, season_ids=None):
    partidos_a = obtener_partidos_equipo(id_a, season_ids)
    time.sleep(0.4)
    partidos_b = obtener_partidos_equipo(id_b, season_ids)
    time.sleep(0.4)

    ids_b = {p["evento_id"] for p in partidos_b}
    h2h   = []

    for p in partidos_a:
        if p["evento_id"] not in ids_b:
            continue

        if p["es_local"]:
            local, visitante = nombre_a, nombre_b
            gl, gv           = p["goles_favor"], p["goles_contra"]
        else:
            local, visitante = nombre_b, nombre_a
            gl, gv           = p["goles_contra"], p["goles_favor"]

        h2h.append({
            "fecha":           p["fecha"],
            "jornada":         p["jornada"],
            "temporada":       p["temporada"],
            "local":           local,
            "visitante":       visitante,
            "goles_local":     gl,
            "goles_visitante": gv,
        })

    return sorted(h2h, key=lambda x: x["fecha"], reverse=True)


# ============================================================
# RESUMEN ESTADÍSTICO DESDE PERSPECTIVA DEL EQUIPO A
# ============================================================

def calcular_resumen(h2h_list, equipo_a, equipo_b):
    victorias_a = empates = victorias_b = 0
    gf_a = gc_a = 0

    for p in h2h_list:
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        es_local_a = p["local"] == equipo_a

        if es_local_a:
            gf_a += gl; gc_a += gv
        else:
            gf_a += gv; gc_a += gl

        if gl == gv:
            empates += 1
        elif gl > gv:
            if es_local_a: victorias_a += 1
            else:          victorias_b += 1
        else:
            if es_local_a: victorias_b += 1
            else:          victorias_a += 1

    key_a = equipo_a.lower().replace(" ", "_")
    key_b = equipo_b.lower().replace(" ", "_")
    total = victorias_a + empates + victorias_b

    return {
        "partidos":               total,
        f"victorias_{key_a}":     victorias_a,
        "empates":                empates,
        f"victorias_{key_b}":     victorias_b,
        f"goles_favor_{key_a}":   gf_a,
        f"goles_contra_{key_a}":  gc_a,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n🏆 Scraper H2H — Copa Libertadores 2026 (Fase de Grupos)\n" + "=" * 55)

    ids_equipos = obtener_ids_equipos()

    # ── Diagnóstico de season types (usa el primer equipo que exista) ──
    print("\n🔬 Diagnóstico de season types disponibles en ESPN...")
    primer_equipo = next(
        (nombre for nombre, _ in CRUCES_JORNADA_6 if nombre in ids_equipos), None
    )
    if primer_equipo:
        diagnosticar_season_types(ids_equipos[primer_equipo], primer_equipo)

    # ── Detectar IDs de fase de grupos dinámicamente ──
    season_ids = None
    if primer_equipo:
        season_ids = detectar_season_ids_grupos(ids_equipos[primer_equipo])
        print(f"\n  🎯 Season type IDs seleccionados para fase de grupos: {season_ids}")

    resultado_final = {}

    for nombre_a, nombre_b in CRUCES_JORNADA_6:
        print(f"\n⚽  {nombre_a}  vs  {nombre_b}")

        id_a = ids_equipos.get(nombre_a)
        id_b = ids_equipos.get(nombre_b)

        # ── Búsqueda tolerante de nombres ──
        if not id_a:
            # Intenta match parcial (ej. "Independiente Medellín" vs "Ind. Medellín")
            for k, v in ids_equipos.items():
                if nombre_a.lower() in k.lower() or k.lower() in nombre_a.lower():
                    print(f"  ℹ️  '{nombre_a}' → match parcial con '{k}'")
                    id_a = v
                    nombre_a = k
                    break

        if not id_b:
            for k, v in ids_equipos.items():
                if nombre_b.lower() in k.lower() or k.lower() in nombre_b.lower():
                    print(f"  ℹ️  '{nombre_b}' → match parcial con '{k}'")
                    id_b = v
                    nombre_b = k
                    break

        if not id_a:
            print(f"  ❌ No se encontró ID para: {nombre_a}")
            continue
        if not id_b:
            print(f"  ❌ No se encontró ID para: {nombre_b}")
            continue

        print(f"  IDs → {nombre_a}: {id_a}  |  {nombre_b}: {id_b}")

        h2h     = extraer_h2h(nombre_a, nombre_b, id_a, id_b, season_ids)
        resumen = calcular_resumen(h2h, nombre_a, nombre_b)

        print(f"  Partidos H2H encontrados: {len(h2h)}")
        for p in h2h:
            if p["goles_local"] == p["goles_visitante"]:
                resultado = "="
            elif p["goles_local"] > p["goles_visitante"]:
                resultado = "🏠"
            else:
                resultado = "✈️"
            print(f"    J{p['jornada']}  {p['fecha']}  "
                  f"{p['local']} {p['goles_local']}-{p['goles_visitante']} {p['visitante']}  {resultado}")

        key = f"{nombre_a.lower().replace(' ', '_')}_vs_{nombre_b.lower().replace(' ', '_')}"
        resultado_final[key] = {
            "torneo":   "Copa Libertadores 2026",
            "fase":     "Fase de Grupos",
            "equipo_a": nombre_a,
            "equipo_b": nombre_b,
            "partidos": h2h,
            "resumen":  resumen,
        }

    # ── Guardar JSON ──────────────────────────────────────────
    output_file = "h2h_libertadores.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)

    print(f"\n✅ {output_file} guardado")
    print(f"   {len(resultado_final)} cruce(s) procesado(s)")


if __name__ == "__main__":
    main()