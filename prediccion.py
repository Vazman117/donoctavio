import json
import math


# =========================
# CONFIG
# =========================

TOTAL_EQUIPOS = 18

MAX_FAVORITO = 0.68
K_LOGISTICO = 5.8
MIN_PROB = 0.01


# NUEVOS PESOS
PESO_FORMA = 0.40
PESO_WINRATE = 0.28
PESO_GOLES = 0.20
PESO_LOCALIA = 0.12
PESO_POS = 0.05



# =========================
# BASE
# =========================

def cargar_equipos():
    with open(
        "equipos.json",
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def obtener_equipo(nombre,db):
    key=nombre.lower().replace(" ","")
    return db.get(key)



def limitar(v,a,b):
    return max(a,min(v,b))



# =========================
# FUERZA
# =========================

def calcular_fuerza(
    forma,
    win_rate,
    posicion,
    goles_diff,
    partidos,
    es_local,
    motivacion=1.0
):

    pos_score=(
        TOTAL_EQUIPOS-posicion
    )/(TOTAL_EQUIPOS-1)

    goles_norm=limitar(
        goles_diff/partidos,
        -1,
        1
    )

    localia=PESO_LOCALIA if es_local else 0


    fuerza=(
        forma*PESO_FORMA+
        win_rate*PESO_WINRATE+
        goles_norm*PESO_GOLES+
        pos_score*PESO_POS+
        localia
    )

    fuerza*=motivacion

    return fuerza



# =========================
# SANITY RULE
# evita favoritos absurdos
# =========================

def dominancia_penalizacion(
    local,
    visita,
    prob_local,
    prob_visit
):

    local_domina=0
    visita_domina=0

    for campo in [
        "forma",
        "win_rate",
        "goles_diff"
    ]:

        if local[campo]>visita[campo]:
            local_domina+=1

        elif visita[campo]>local[campo]:
            visita_domina+=1


    # si visitante domina todo
    if visita_domina==3 and prob_local>0.55:
        prob_local=0.55
        prob_visit=0.45


    # si local domina todo
    if local_domina==3 and prob_visit>0.55:
        prob_visit=0.55
        prob_local=0.45


    return prob_local,prob_visit




# =========================
# PREDICCION
# =========================

def predecir_probabilidades(
    equipo_local,
    equipo_visitante
):

    def datos(e):
        return {
            "forma":e["forma"],
            "win_rate":e["win_rate"],
            "posicion":e["posicion"],
            "goles_diff":e["goles_diff"],
            "partidos":e["partidos"],
            "es_local":e["es_local"],
            "motivacion":e.get(
                "motivacion",
                1.0
            )
        }


    f_local=calcular_fuerza(
        **datos(equipo_local)
    )

    f_visit=calcular_fuerza(
        **datos(equipo_visitante)
    )


    # =========
    # LOGISTICA
    # =========

    score=f_local-f_visit

    prob_local=1/(
        1+math.exp(
            -K_LOGISTICO*score
        )
    )

    prob_visit=1-prob_local


    # ======================
    # SANITY CHECK
    # ======================

    prob_local,prob_visit=(
        dominancia_penalizacion(
            equipo_local,
            equipo_visitante,
            prob_local,
            prob_visit
        )
    )


    # ======================
    # CAP FAVORITOS
    # ======================

    if prob_local>MAX_FAVORITO:
        prob_local=MAX_FAVORITO
        prob_visit=1-prob_local

    if prob_visit>MAX_FAVORITO:
        prob_visit=MAX_FAVORITO
        prob_local=1-prob_visit


    # ======================
    # EMPATE SOLO ALERTA
    # no roba masa fuerte
    # ======================

    diferencia=abs(score)

    if diferencia<0.06:
        prob_empate=0.25

    elif diferencia<0.12:
        prob_empate=0.18

    else:
        prob_empate=0.12


    # sólo reduce poquito
    ajuste=1-(prob_empate*0.35)

    prob_local*=ajuste
    prob_visit*=ajuste


    suma=(
        prob_local+
        prob_visit+
        prob_empate
    )

    prob_local/=suma
    prob_visit/=suma
    prob_empate/=suma


    # ======================
    # CONFIANZA
    # ======================

    gap=abs(
        prob_local-prob_visit
    )

    if gap<0.08:
        confianza="coin_flip"

    elif gap<0.15:
        confianza="media"

    else:
        confianza="alta"


    return{

        "local":prob_local,
        "visitante":prob_visit,
        "empate":prob_empate,

        "fuerza_local":f_local,
        "fuerza_visitante":f_visit,

        "diferencia":diferencia,
        "confianza":confianza
    }



# =========================
# GUARDAR
# =========================

def guardar_resultado(
    partido,
    archivo="partidos.json"
):

    try:
        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:
            data=json.load(f)

    except:
        data=[]

    data.append(partido)

    with open(
        archivo,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )



# =========================
# GENERAR
# =========================

def generar_partido(
    id,
    local_nombre,
    visitante_nombre,
    db
):

    local=obtener_equipo(
        local_nombre,
        db
    )

    visita=obtener_equipo(
        visitante_nombre,
        db
    )


    if not local or not visita:
        raise ValueError(
            "Equipo no encontrado"
        )


    local["es_local"]=True
    visita["es_local"]=False


    r=predecir_probabilidades(
        local,
        visita
    )


    if (
      r["local"]>r["visitante"]
      and
      r["local"]>r["empate"]
    ):
        pred=local_nombre

    elif (
      r["visitante"]>r["local"]
      and
      r["visitante"]>r["empate"]
    ):
        pred=visitante_nombre

    else:
        pred="Empate"



    output={

        "id":id,

        "local":local_nombre,
        "visitante":visitante_nombre,

        "prob_local":r["local"],
        "prob_empate":r["empate"],
        "prob_visitante":r["visitante"],

        "fuerza_local":r["fuerza_local"],
        "fuerza_visitante":r["fuerza_visitante"],

        "confianza":r["confianza"],
        "prediccion":pred
    }


    guardar_resultado(output)

    return output



# =========================
# TEST
# =========================

if __name__=="__main__":

    db=cargar_equipos()

    generar_partido(
        9,
        "Necaxa",
        "Chivas",
        db
    )

    print("✅ Partido generado")