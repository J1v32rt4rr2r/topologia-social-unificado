from topologia.models.schemas import EstadoCultural, OperacionCinetica
from topologia.models.patterns import OPERACIONES_CINETICAS


def detectar_operaciones(estado: EstadoCultural) -> list[OperacionCinetica]:
    operaciones: list[OperacionCinetica] = []
    nodos_map = {n.nodo_id: n for n in estado.nodos}

    politico = nodos_map.get("POLITICA")
    economia = nodos_map.get("ECONOMIA")
    trabajo = nodos_map.get("TRABAJO")
    lenguaje = nodos_map.get("LENGUAJE")
    religion = nodos_map.get("RELIGION")
    educacion = nodos_map.get("EDUCACION")
    etica = nodos_map.get("ETICA_ESTETICA")
    tecnologia = nodos_map.get("TECNOLOGIA")
    continuidad = nodos_map.get("CONTINUIDAD")

    # O4a: Polarización (diferencias altas entre M_m y M_l en POLITICA)
    if politico and abs(politico.dimension_m - politico.dimension_l) > 3.0:
        operaciones.append(OperacionCinetica(
            codigo="O4a",
            nombre=OPERACIONES_CINETICAS["O4a"]["nombre"],
            intensidad=min(abs(politico.dimension_m - politico.dimension_l) / 10.0, 1.0),
            nodos_implicados=["POLITICA"],
            descripcion="Divergencia alta entre dimensión material y lógica en política.",
            evidencia=f"M_m={politico.dimension_m:.1f}, M_l={politico.dimension_l:.1f}",
        ))

    # O5: Entropía (degradación generalizada, M < 3.0 en múltiples nodos)
    bajos = [n.nodo_id for n in estado.nodos if n.dimension_m < 3.0 or n.dimension_s < 3.0]
    if len(bajos) >= 3:
        operaciones.append(OperacionCinetica(
            codigo="O5",
            nombre=OPERACIONES_CINETICAS["O5"]["nombre"],
            intensidad=min(len(bajos) / 9.0, 1.0),
            nodos_implicados=bajos,
            descripcion="Degradación material o social en múltiples nodos.",
            evidencia=f"Nodos con M<3.0: {', '.join(bajos)}",
        ))

    # O6: Órbita parasitaria (asimetría ECONOMÍA vs TRABAJO)
    if economia and trabajo:
        dif_eco_trab = abs(economia.dimension_m - trabajo.dimension_m)
        if dif_eco_trab > 3.0:
            operaciones.append(OperacionCinetica(
                codigo="O6",
                nombre=OPERACIONES_CINETICAS["O6"]["nombre"],
                intensidad=min(dif_eco_trab / 10.0, 1.0),
                nodos_implicados=["ECONOMIA", "TRABAJO"],
                descripcion="Asimetría material entre economía y trabajo.",
                evidencia=f"Economía M_m={economia.dimension_m:.1f}, Trabajo M_m={trabajo.dimension_m:.1f}",
            ))

    # O3a: Vertical devocional (RELIGIÓN alta, EDUCACIÓN baja)
    if religion and educacion:
        dif_rel_edu = religion.dimension_l - educacion.dimension_l
        if dif_rel_edu > 3.0:
            operaciones.append(OperacionCinetica(
                codigo="O3a",
                nombre=OPERACIONES_CINETICAS["O3a"]["nombre"],
                intensidad=min(dif_rel_edu / 10.0, 1.0),
                nodos_implicados=["RELIGION", "EDUCACION"],
                descripcion="Sacralización vs educación. Distancia valórica.",
                evidencia=f"Religión M_l={religion.dimension_l:.1f}, Educación M_l={educacion.dimension_l:.1f}",
            ))

    # O9: Escape horizontal (TECNOLOGÍA y LENGUAJE altos, CONTINUIDAD bajo)
    if tecnologia and lenguaje and continuidad:
        promedio_escape = (tecnologia.dimension_m + lenguaje.dimension_l) / 2
        if promedio_escape > 6.0 and continuidad.dimension_m < 3.0:
            operaciones.append(OperacionCinetica(
                codigo="O9",
                nombre=OPERACIONES_CINETICAS["O9"]["nombre"],
                intensidad=min((promedio_escape - continuidad.dimension_m) / 10.0, 1.0),
                nodos_implicados=["TECNOLOGIA", "LENGUAJE", "CONTINUIDAD"],
                descripcion="Fuga hacia tecnología y nuevas narrativas, abandono de la memoria.",
                evidencia=f"Tecnología M_m={tecnologia.dimension_m:.1f}, Continuidad M_m={continuidad.dimension_m:.1f}",
            ))

    # O11: Círculo expansivo (ETICA y EDUCACIÓN altas, delta bajo)
    if etica and educacion:
        if etica.dimension_s > 6.0 and educacion.dimension_s > 6.0:
            operaciones.append(OperacionCinetica(
                codigo="O11",
                nombre=OPERACIONES_CINETICAS["O11"]["nombre"],
                intensidad=min((etica.dimension_s + educacion.dimension_s) / 20.0, 1.0),
                nodos_implicados=["ETICA_ESTETICA", "EDUCACION"],
                descripcion="Organización social expansiva en ética y educación.",
                evidencia=f"Ética M_s={etica.dimension_s:.1f}, Educación M_s={educacion.dimension_s:.1f}",
            ))

    # Delta general: si es alto, tensión sistémica (O1b)
    if estado.delta_promedio >= 45:
        operaciones.append(OperacionCinetica(
            codigo="O1b",
            nombre=OPERACIONES_CINETICAS["O1b"]["nombre"],
            intensidad=min(estado.delta_promedio / 90.0, 1.0),
            nodos_implicados=[n.nodo_id for n in estado.nodos if n.fragil],
            descripcion="Tensión sistémica generalizada.",
            evidencia=f"δ promedio = {estado.delta_promedio:.1f}°",
        ))

    return operaciones
