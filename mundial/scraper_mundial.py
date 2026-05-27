# scraper_mundial.py
#
# INSTALAR:
# pip install requests
#
# EJECUTAR:
# python scraper_mundial.py
#
# GENERA:
# /mundial/data/grupos.json
# /mundial/data/tabla.json
# /mundial/data/hoy.json

import os
import json
import requests
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

os.makedirs(DATA_DIR, exist_ok=True)

# =====================================================
# HELPERS
# =====================================================

def guardar_json(nombre, data):

    ruta = os.path.join(DATA_DIR, nombre)

    with open(ruta, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"✓ {nombre} generado")


def stat(stats, name, default=0):

    for s in stats:

        if s.get("name") == name:
            return s.get("value", default)

    return default


# =====================================================
# GRUPOS
# =====================================================

def obtener_grupos():

    url = (
        "https://site.api.espn.com/apis/v2/"
        "sports/soccer/fifa.world/standings"
    )

    response = requests.get(url)

    data = response.json()

    grupos = []

    children = data.get("children", [])

    for group in children:

        grupo_obj = {
            "grupo": group.get("name", ""),
            "equipos": []
        }

        entries = (
            group.get("standings", {})
            .get("entries", [])
        )

        for entry in entries:

            team = entry.get("team", {})
            stats = entry.get("stats", [])

            partidos = stat(stats, "gamesPlayed")
            goles_favor = stat(stats, "pointsFor")
            goles_contra = stat(stats, "pointsAgainst")

            equipo = {

                "posicion":
                    stat(stats, "rank"),

                "equipo":
                    team.get("displayName", ""),

                "partidos":
                    partidos,

                "ganados":
                    stat(stats, "wins"),

                "empatados":
                    stat(stats, "ties"),

                "perdidos":
                    stat(stats, "losses"),

                "goles_favor":
                    goles_favor,

                "goles_contra":
                    goles_contra,

                "diferencia_goles":
                    stat(stats, "pointDifferential"),

                "puntos":
                    stat(stats, "points"),

                "escudo":
                    (
                        team.get("logos", [{}])[0]
                        .get("href", "")
                    ),

                "abreviacion":
                    team.get("abbreviation", ""),

                # =================================
                # TUS VARIABLES
                # =================================

                "forma_ponderada": 0,
                "forma_liga": 0,

                "ultimos_5_liga": [],

                "imbatido_streak": 0,

                "forma_liga_local": 0,

                "ultimos_5_liga_local": [],

                "liga_local_slug": "",

                # =================================
                # COMPETENCIAS
                # =================================

                "competencias": {

                    "fifa.world": {

                        "partidos":
                            partidos,

                        "ganados":
                            stat(stats, "wins"),

                        "empatados":
                            stat(stats, "ties"),

                        "perdidos":
                            stat(stats, "losses"),

                        "goles_favor":
                            goles_favor,

                        "goles_contra":
                            goles_contra,

                        "goles_favor_promedio":
                            round(
                                goles_favor /
                                max(partidos, 1),
                                2
                            ),

                        "goles_contra_promedio":
                            round(
                                goles_contra /
                                max(partidos, 1),
                                2
                            ),

                        "partidos_local": 0,
                        "ganados_local": 0,
                        "empatados_local": 0,
                        "perdidos_local": 0,

                        "win_rate_local": 0,

                        "partidos_visita": 0,
                        "ganados_visita": 0,
                        "empatados_visita": 0,
                        "perdidos_visita": 0,

                        "win_rate_visita": 0,

                        "ultimos_5": [],

                        "imbatido_streak": 0
                    }
                }
            }

            grupo_obj["equipos"].append(
                equipo
            )

        grupos.append(grupo_obj)

    guardar_json(
        "grupos.json",
        grupos
    )

    return grupos


# =====================================================
# TABLA GENERAL
# =====================================================

def generar_tabla(grupos):

    tabla = []

    for grupo in grupos:

        for eq in grupo["equipos"]:

            tabla.append({

                "grupo":
                    grupo["grupo"],

                "posicion":
                    eq["posicion"],

                "equipo":
                    eq["equipo"],

                "abreviacion":
                    eq["abreviacion"],

                "escudo":
                    eq["escudo"],

                "puntos":
                    eq["puntos"],

                "diferencia_goles":
                    eq["diferencia_goles"],

                "goles_favor":
                    eq["goles_favor"],

                "goles_contra":
                    eq["goles_contra"],

                "partidos":
                    eq["partidos"]
            })

    tabla.sort(

        key=lambda x: (
            x["puntos"],
            x["diferencia_goles"],
            x["goles_favor"]
        ),

        reverse=True
    )

    guardar_json(
        "tabla.json",
        tabla
    )


# =====================================================
# PARTIDOS DE HOY
# =====================================================

def obtener_hoy():

    fecha = datetime.now().strftime(
        "%Y%m%d"
    )

    url = (
        f"{BASE}/scoreboard"
        f"?dates={fecha}"
    )

    response = requests.get(url)

    data = response.json()

    events = data.get("events", [])

    partidos = []

    for event in events:

        comp = (
            event.get("competitions", [{}])[0]
        )

        competitors = (
            comp.get("competitors", [])
        )

        local = next(
            (
                c for c in competitors
                if c.get("homeAway") == "home"
            ),
            {}
        )

        visitante = next(
            (
                c for c in competitors
                if c.get("homeAway") == "away"
            ),
            {}
        )

        partido = {

            "id":
                event.get("id"),

            "fecha":
                event.get("date"),

            "estado":
                (
                    comp.get("status", {})
                    .get("type", {})
                    .get("description", "")
                ),

            "minuto":
                (
                    comp.get("status", {})
                    .get("displayClock", "")
                ),

            "estadio":
                (
                    comp.get("venue", {})
                    .get("fullName", "")
                ),

            "local": {

                "nombre":
                    (
                        local.get("team", {})
                        .get("displayName", "")
                    ),

                "abreviacion":
                    (
                        local.get("team", {})
                        .get("abbreviation", "")
                    ),

                "escudo":
                    (
                        local.get("team", {})
                        .get("logo", "")
                    ),

                "goles":
                    int(local.get("score", 0))
            },

            "visitante": {

                "nombre":
                    (
                        visitante.get("team", {})
                        .get("displayName", "")
                    ),

                "abreviacion":
                    (
                        visitante.get("team", {})
                        .get("abbreviation", "")
                    ),

                "escudo":
                    (
                        visitante.get("team", {})
                        .get("logo", "")
                    ),

                "goles":
                    int(visitante.get("score", 0))
            }
        }

        partidos.append(partido)

    guardar_json(
        "hoy.json",
        partidos
    )


# =====================================================
# MAIN
# =====================================================

def main():

    print("\nActualizando Mundial...\n")

    grupos = obtener_grupos()

    generar_tabla(grupos)

    obtener_hoy()

    print("\n✓ Todo actualizado\n")


if __name__ == "__main__":
    main()