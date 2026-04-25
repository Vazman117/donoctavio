import json
import math


# =============================
# CARGAR BASE
# =============================

def cargar_equipos():
    with open(
        "equipos.json",
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def obtener_equipo(nombre, db):
    key = nombre.lower().replace(" ", "")
    return db.get(key)



# =============================
# CONFIG
# =============================

TOTAL_EQUIPOS = 18

K_LOGISTICO = 5.8
MAX_FAVORITO = 0.68

# NUEVOS PESOS (posición casi muerta)
PESO_FORMA = 0.50
PESO_WINRATE = 0.18
PESO_GOLES = 0.20
PESO_POS = 0.02
PESO_LOCALIA = 0.10



def limitar(v,a,b):
    return max(a,min(v,b))



# =============================
# FUERZA
# =============================

def calcular_fuerza(
    forma,
    win_rate,
    posicion,
    goles_diff,
    partidos,
    es_local
):

    pos_score = (
        TOTAL_EQUIPOS - posicion
    )/(TOTAL_EQUIPOS-1)


    goles_norm = limitar(
        goles_diff/partidos,
        -1,
        1
    )


    localia = PESO_LOCALIA if es_local else 0


    return (
        forma * PESO_FORMA +
        win_rate * PESO_WINRATE +
        goles_norm * PESO_GOLES +
        pos_score * PESO_POS +
        localia
    )



# =============================
# SANITY CHECK
# =============================

def dominancia_penalizacion(
    local,
    visitante,
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

        if local[campo] > visitante[campo]:
            local_domina +=1

        elif visitante[campo] > local[campo]:
            visita_domina +=1


    if visita_domina==3 and prob_local>0.56:
        prob_local=.56
        prob_visit=.44


    if local_domina==3 and prob_visit>0.56:
        prob_visit=.56
        prob_local=.44


    return prob_local,prob_visit




# =============================
# PROBABILIDADES
# =============================

def predecir_probabilidades(
    equipo_local,
    equipo_visitante
):


    def filtrar_equipo(equipo):
        return {
            "forma":equipo["forma"],
            "win_rate":equipo["win_rate"],
            "posicion":equipo["posicion"],
            "goles_diff":equipo["goles_diff"],
            "partidos":equipo["partidos"],
            "es_local":equipo["es_local"]
        }



    f_local=calcular_fuerza(
        **filtrar_equipo(equipo_local)
    )

    f_visitante=calcular_fuerza(
        **filtrar_equipo(equipo_visitante)
    )


    # =====================
    # LOGISTICA
    # =====================

    score=f_local-f_visitante

    prob_local=1/(
        1+math.exp(
            -K_LOGISTICO*score
        )
    )

    prob_visitante=1-prob_local


    # =====================
    # SANITY CHECK
    # =====================

    prob_local,prob_visitante=(
        dominancia_penalizacion(
            equipo_local,
            equipo_visitante,
            prob_local,
            prob_visitante
        )
    )


    # =====================
    # CAP DE FAVORITOS
    # =====================

    if prob_local>MAX_FAVORITO:
        prob_local=MAX_FAVORITO
        prob_visitante=1-prob_local


    if prob_visitante>MAX_FAVORITO:
        prob_visitante=MAX_FAVORITO
        prob_local=1-prob_visitante



    diferencia=abs(score)


    # =====================
    # EMPATE (menos invasivo)
    # =====================

    if diferencia<0.06:
        prob_empate=.24

    elif diferencia<0.12:
        prob_empate=.18

    else:
        prob_empate=.12


    ajuste=1-(prob_empate*.30)

    prob_local*=ajuste
    prob_visitante*=ajuste


    suma=(
      prob_local+
      prob_visitante+
      prob_empate
    )


    prob_local/=suma
    prob_visitante/=suma
    prob_empate/=suma



    # =====================
    # CONFIANZA
    # =====================

    gap=abs(
      prob_local-prob_visitante
    )


    if gap<0.08:
        confianza="coin_flip"

    elif gap<0.15:
        confianza="media"

    else:
        confianza="alta"



    return{

        "local":prob_local,
        "empate":prob_empate,
        "visitante":prob_visitante,

        "fuerza_local":f_local,
        "fuerza_visitante":f_visitante,

        "diferencia":diferencia,
        "confianza":confianza
    }




# =============================
# GUARDAR
# =============================

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



# =============================
# GENERAR PARTIDO
# =============================

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

    visitante=obtener_equipo(
        visitante_nombre,
        db
    )


    if not local or not visitante:
        raise ValueError(
            "❌ Equipo no encontrado"
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



    # OUTPUT ORIGINAL RESTAURADO
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

    print(
      "✅ Partido generado y guardado"
    )