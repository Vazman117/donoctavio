import json
import math


# =============================
# CONFIG
# =============================

TOTAL_EQUIPOS = 18

MAX_FAVORITO = 0.72
MIN_PROB = 0.01

K_LOGISTICO = 5.5   # sensibilidad del modelo

# pesos reajustados
PESO_FORMA = 0.34
PESO_WINRATE = 0.25
PESO_POS = 0.13
PESO_GOLES = 0.18
PESO_LOCALIA = 0.10


# =============================
# CARGAR BASE
# =============================

def cargar_equipos():
    with open("equipos.json","r",encoding="utf-8") as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    key = nombre.lower().replace(" ","")
    return db.get(key)


# =============================
# UTILIDADES
# =============================

def limitar(valor,minimo,maximo):
    return max(minimo,min(valor,maximo))


# =============================
# NUEVA FUERZA
# =============================

def calcular_fuerza(
        forma,
        win_rate,
        posicion,
        goles_diff,
        partidos,
        es_local,
        motivacion=1.0
):

    # posición normalizada (mejor que 1/pos)
    pos_score = (TOTAL_EQUIPOS - posicion) / (TOTAL_EQUIPOS-1)

    # evitar extremos locos
    goles_norm = limitar(
        goles_diff / partidos,
        -1,
        1
    )

    localia = PESO_LOCALIA if es_local else 0

    fuerza = (
        (forma * PESO_FORMA) +
        (win_rate * PESO_WINRATE) +
        (pos_score * PESO_POS) +
        (goles_norm * PESO_GOLES) +
        localia
    )

    fuerza *= motivacion

    return fuerza


# =============================
# PREDICCIÓN
# =============================

def predecir_probabilidades(equipo_local,equipo_visitante):

    def filtrar_equipo(e):
        return {
            "forma":e["forma"],
            "win_rate":e["win_rate"],
            "posicion":e["posicion"],
            "goles_diff":e["goles_diff"],
            "partidos":e["partidos"],
            "es_local":e["es_local"],
            "motivacion":e.get("motivacion",1.0)
        }


    f_local = calcular_fuerza(**filtrar_equipo(equipo_local))
    f_visit = calcular_fuerza(**filtrar_equipo(equipo_visitante))



    # ==================================
    # LOGÍSTICA (gran cambio)
    # ==================================

    score = f_local - f_visit

    prob_local = 1/(1+math.exp(-K_LOGISTICO*score))
    prob_visit = 1-prob_local


    # ==================================
    # DIFERENCIA RELATIVA
    # ==================================

    diferencia = abs(score)


    # ==================================
    # EMPATE DINÁMICO
    # ==================================

    prob_empate = (
        0.26 *
        (1/(1+diferencia*8))
    )

    # si muy parejos subir empate
    if diferencia < 0.08:
        prob_empate += 0.05


    promedio_goles = (
        equipo_local["goles_diff"] +
        equipo_visitante["goles_diff"]
    ) / (
        equipo_local["partidos"] +
        equipo_visitante["partidos"]
    )

    if promedio_goles < 0.10:
        prob_empate += 0.03


    prob_empate = limitar(
        prob_empate,
        0.15,
        0.34
    )


    ajuste = 1-prob_empate

    prob_local *= ajuste
    prob_visit *= ajuste



    # ==================================
    # CAP FAVORITOS EXTREMOS
    # ==================================

    if prob_local > MAX_FAVORITO:
        exceso = prob_local-MAX_FAVORITO
        prob_local = MAX_FAVORITO
        prob_visit += exceso

    if prob_visit > MAX_FAVORITO:
        exceso = prob_visit-MAX_FAVORITO
        prob_visit = MAX_FAVORITO
        prob_local += exceso


    # mínimos
    prob_local=max(MIN_PROB,prob_local)
    prob_visit=max(MIN_PROB,prob_visit)
    prob_empate=max(MIN_PROB,prob_empate)


    # normalizar
    suma=prob_local+prob_visit+prob_empate

    prob_local/=suma
    prob_visit/=suma
    prob_empate/=suma



    # ==================================
    # CLASIFICAR CONFIANZA
    # ==================================

    gap=abs(prob_local-prob_visit)

    if gap<0.08:
        nivel="coin_flip"
    elif gap<0.15:
        nivel="media"
    else:
        nivel="alta"



    return {
        "local":prob_local,
        "empate":prob_empate,
        "visitante":prob_visit,
        "fuerza_local":f_local,
        "fuerza_visitante":f_visit,
        "diferencia":diferencia,
        "confianza":nivel
    }


# =============================
# GUARDAR
# =============================

def guardar_resultado(partido,archivo="partidos.json"):

    try:
        with open(archivo,"r",encoding="utf-8") as f:
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



# =============================
# GENERAR PARTIDO
# =============================

def generar_partido(
        id,
        local_nombre,
        visitante_nombre,
        db
):

    local=obtener_equipo(local_nombre,db)
    visitante=obtener_equipo(visitante_nombre,db)

    if not local or not visitante:
        raise ValueError(
            "Equipo no encontrado"
        )


    local["es_local"]=True
    visitante["es_local"]=False


    resultado=predecir_probabilidades(
        local,
        visitante
    )


    if (
       resultado["local"]>
       resultado["visitante"]
       and
       resultado["local"]>
       resultado["empate"]
    ):
        pred=local_nombre

    elif (
       resultado["visitante"]>
       resultado["local"]
       and
       resultado["visitante"]>
       resultado["empate"]
    ):
        pred=visitante_nombre

    else:
        pred="Empate"



    output={

        "id":id,

        "local":local_nombre,
        "visitante":visitante_nombre,

        "logo_local":local.get("escudo"),
        "logo_visitante":visitante.get("escudo"),

        "prob_local":resultado["local"],
        "prob_empate":resultado["empate"],
        "prob_visitante":resultado["visitante"],

        "fuerza_local":resultado["fuerza_local"],
        "fuerza_visitante":resultado["fuerza_visitante"],

        "diferencia":resultado["diferencia"],
        "confianza":resultado["confianza"],

        "prediccion":pred
    }

    guardar_resultado(output)

    return output



# =============================
# TEST
# =============================

if __name__=="__main__":

    db=cargar_equipos()

    generar_partido(
        9,
        "Necaxa",
        "Chivas",
        db
    )

    print("✅ Partido generado.")