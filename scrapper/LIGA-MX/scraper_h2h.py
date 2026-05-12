import requests
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.espn.com.mx/",
    "Origin": "https://www.espn.com.mx"
}

TEAMS_URL    = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams"
SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/teams/{team_id}/schedule"

# =============================
# CONFIGURA AQUÍ LOS CRUCES
# =============================
# Cambia estos nombres cada liguilla.
# Usa el nombre exacto como aparece en ESPN.

CRUCES_LIGUILLA = [
    ("Pumas UNAM",    "Pachuca"),
    ("Guadalajara",   "Cruz Azul"),
]

# Temporadas a incluir (seasonType ids de ESPN)
TEMPORADAS = {
    "apertura_2025":          ["1", "5", "6", "7"],   # regular + liguilla
    "clausura_2026":          ["8", "12", "13", "14"],        # regular (liguilla se agrega cuando exista)
}


# =============================
# OBTENER IDs DE EQUIPOS
# =============================

def obtener_ids_equipos():
    print("🔍 Obteniendo IDs de equipos...")
    r = requests.get(TEAMS_URL, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        raise Exception(f"Error {r.status_code} al obtener equipos")

    data = r.json()
    ids = {}
    for sport in data.get("sports", []):
        for league in sport.get("leagues", []):
            for t in league.get("teams", []):
                team = t["team"]
                ids[team["displayName"]] = team["id"]

    print(f"  ✅ {len(ids)} equipos encontrados")
    return ids


# =============================
# OBTENER PARTIDOS DE UN EQUIPO
# =============================

def obtener_partidos_equipo(team_id, season_ids):
    url = SCHEDULE_URL.format(team_id=team_id)
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200 or len(r.text) < 100:
        return []

    data = r.json()
    partidos = []

    for evento in data.get("events", []):
        st_id = str(evento.get("seasonType", {}).get("id", ""))
        if st_id not in season_ids:
            continue

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

        try:
            mis_goles   = int(float(mi_equipo.get("score", {}).get("displayValue", 0) or 0))
            goles_rival = int(float(rival.get("score", {}).get("displayValue", 0) or 0))
        except:
            mis_goles = goles_rival = 0

        partidos.append({
            "evento_id":   evento.get("id"),
            "fecha":       evento.get("date"),
            "temporada":   evento.get("seasonType", {}).get("name", ""),
            "season_id":   st_id,
            "es_local":    mi_equipo.get("homeAway") == "home",
            "rival_id":    rival.get("id"),
            "rival_nombre": rival.get("team", {}).get("displayName", ""),
            "goles_favor":  mis_goles,
            "goles_contra": goles_rival,
        })

    partidos.sort(key=lambda x: x["fecha"], reverse=True)
    return partidos


# =============================
# EXTRAER H2H DE UN CRUCE
# =============================

def extraer_h2h(nombre_a, nombre_b, id_a, id_b):
    """
    Descarga partidos de ambos equipos y encuentra
    los enfrentamientos directos entre ellos.
    """
    todos_ids = list(set(TEMPORADAS["apertura_2025"] + TEMPORADAS["clausura_2026"]))

    partidos_a = obtener_partidos_equipo(id_a, todos_ids)
    time.sleep(0.4)
    partidos_b = obtener_partidos_equipo(id_b, todos_ids)
    time.sleep(0.4)

    # Índice de partidos del equipo B por evento_id
    ids_b = {p["evento_id"] for p in partidos_b}

    h2h_apertura  = []
    h2h_clausura  = []

    for p in partidos_a:
        if p["evento_id"] not in ids_b:
            continue

        # Normalizar: siempre desde perspectiva del local real
        if p["es_local"]:
            local     = nombre_a
            visitante = nombre_b
            goles_l   = p["goles_favor"]
            goles_v   = p["goles_contra"]
        else:
            local     = nombre_b
            visitante = nombre_a
            goles_l   = p["goles_contra"]
            goles_v   = p["goles_favor"]

        entrada = {
            "fecha":           p["fecha"][:10],
            "temporada":       p["temporada"],
            "local":           local,
            "visitante":       visitante,
            "goles_local":     goles_l,
            "goles_visitante": goles_v,
        }

        if p["season_id"] in TEMPORADAS["clausura_2026"]:
            h2h_clausura.append(entrada)
        else:
            h2h_apertura.append(entrada)

    return {
        "clausura_2026": sorted(h2h_clausura, key=lambda x: x["fecha"], reverse=True),
        "apertura_2025": sorted(h2h_apertura, key=lambda x: x["fecha"], reverse=True),
    }


# =============================
# RESUMEN H2H
# =============================

def calcular_resumen(h2h_list, equipo_a, equipo_b):
    """
    Calcula victorias/empates/derrotas desde la perspectiva
    del primer equipo del cruce (equipo_a).
    """
    victorias_a = 0
    empates     = 0
    victorias_b = 0

    for p in h2h_list:
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        es_local_a = p["local"] == equipo_a

        if gl == gv:
            empates += 1
        elif gl > gv:
            if es_local_a:
                victorias_a += 1
            else:
                victorias_b += 1
        else:
            if es_local_a:
                victorias_b += 1
            else:
                victorias_a += 1

    total = victorias_a + empates + victorias_b
    return {
        "partidos":          total,
        f"victorias_{equipo_a.lower().replace(' ', '_')}": victorias_a,
        "empates":           empates,
        f"victorias_{equipo_b.lower().replace(' ', '_')}": victorias_b,
    }


# =============================
# MAIN
# =============================

def main():
    print("\n🏆 Scraper H2H Liguilla Liga MX\n" + "="*40)

    # Obtener IDs
    ids_equipos = obtener_ids_equipos()

    resultado_final = {}

    for nombre_a, nombre_b in CRUCES_LIGUILLA:
        print(f"\n⚽ {nombre_a} vs {nombre_b}")

        id_a = ids_equipos.get(nombre_a)
        id_b = ids_equipos.get(nombre_b)

        if not id_a:
            print(f"  ❌ No se encontró ID para: {nombre_a}")
            continue
        if not id_b:
            print(f"  ❌ No se encontró ID para: {nombre_b}")
            continue

        print(f"  IDs: {nombre_a}={id_a} | {nombre_b}={id_b}")

        h2h = extraer_h2h(nombre_a, nombre_b, id_a, id_b)

        todos = h2h["clausura_2026"] + h2h["apertura_2025"]
        resumen_clausura  = calcular_resumen(h2h["clausura_2026"], nombre_a, nombre_b)
        resumen_apertura  = calcular_resumen(h2h["apertura_2025"], nombre_a, nombre_b)
        resumen_total     = calcular_resumen(todos, nombre_a, nombre_b)

        print(f"  Clausura 2026: {len(h2h['clausura_2026'])} partidos")
        print(f"  Apertura 2025: {len(h2h['apertura_2025'])} partidos")

        key = f"{nombre_a.lower().replace(' ', '_')}_vs_{nombre_b.lower().replace(' ', '_')}"
        resultado_final[key] = {
            "equipo_a":        nombre_a,
            "equipo_b":        nombre_b,
            "clausura_2026":   h2h["clausura_2026"],
            "apertura_2025":   h2h["apertura_2025"],
            "resumen": {
                "clausura_2026": resumen_clausura,
                "apertura_2025": resumen_apertura,
                "total":         resumen_total,
            }
        }

    # Guardar
    with open("h2h_liguilla.json", "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)

    print("\n✅ h2h_liguilla.json guardado")
    print(f"   {len(resultado_final)} cruces procesados")


if __name__ == "__main__":
    main()
