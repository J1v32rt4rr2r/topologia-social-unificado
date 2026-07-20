import typer

app = typer.Typer(
    name="topologia",
    help="Sistema multi-agente para observación topológica de la cultura",
)


@app.command()
def observe(sociedad: str = "Chile"):
    """Ejecuta ciclo completo de observación diaria."""
    from topologia.orchestrator import Orchestrator
    orch = Orchestrator()
    resultado = orch.observar(sociedad)
    print(f"Estado cultural: M=({resultado.M_m:.1f}, {resultado.M_l:.1f}, {resultado.M_s:.1f})")
    print(f"Delta promedio: {resultado.delta_promedio:.1f}°")
    print(f"Coherente: {resultado.coherente}")
    if resultado.nodos_fragiles:
        print(f"Nodos frágiles: {', '.join(resultado.nodos_fragiles)}")


@app.command()
def learn(ruta_poema: str):
    """Ejecuta pipeline analógico (Taller del Artista) sobre un poema."""
    from topologia.agents.artista import Artista
    artista = Artista()
    resultado = artista.taller(ruta_poema)
    print(f"Patrones descubiertos: {len(resultado)}")
    for p in resultado:
        print(f"  {p.id}: {p.forma}")


@app.command()
def pipeline(ruta_texto: str):
    """Ejecuta pipeline analógico completo (6 fases) sobre un texto."""
    from topologia.pipeline import Pipeline
    pipe = Pipeline()
    resultado = pipe.ejecutar(ruta_texto)
    print(resultado.resumen())


@app.command()
def daily(sociedad: str = "Chile"):
    """Ciclo completo: recolectar → observar → especular → estudiar → redactar."""
    from topologia.orchestrator import Orchestrator
    orch = Orchestrator()
    informe = orch.ciclo_diario(sociedad)
    print(f"\n=== INFORME DIARIO: {sociedad} ===")
    print(informe.resumen_ejecutivo)
    for alerta in informe.alertas:
        print(f"[{alerta.tipo.value}] {alerta.mensaje}")
    from topologia.storage.store import FileStore
    store = FileStore()
    ruta = store.base / "reportes"
    print(f"\nInforme guardado en: {ruta}")


@app.command(name="server")
def serve(host: str = "0.0.0.0", port: int = 8000):
    """Inicia servidor web con dashboard."""
    import uvicorn
    uvicorn.run("topologia.server.app:app", host=host, port=port, reload=True)


@app.command()
def state(sociedad: str = "Chile"):
    """Muestra el último estado cultural registrado."""
    from topologia.storage.store import FileStore
    store = FileStore()
    estado = store.cargar_estado(sociedad)
    if estado is None:
        print(f"No hay estado registrado para {sociedad}")
        return
    print(f"Sociedad: {estado.sociedad}")
    print(f"Fecha: {estado.fecha}")
    print(f"M = ({estado.M_m:.1f}, {estado.M_l:.1f}, {estado.M_s:.1f})")
    print(f"delta = {estado.delta_promedio:.1f} deg")
    print(f"Coherente: {estado.coherente}")
    for nodo in estado.nodos:
        frag = " [FRAGIL]" if nodo.fragil else ""
        print(f"  {nodo.nodo_id}: M_m={nodo.dimension_m:.1f} M_l={nodo.dimension_l:.1f} M_s={nodo.dimension_s:.1f} delta={nodo.delta:.1f}{frag}")
    if estado.m_m:
        print(f"\nFormas complejas (e^(2pi*i / m)):")
        print(f"  M_m: m={estado.m_m:.3f}  theta={estado.theta_m:.1f} deg")
        print(f"  M_l: m={estado.m_l:.3f}  theta={estado.theta_l:.1f} deg")
        print(f"  M_s: m={estado.m_s:.3f}  theta={estado.theta_s:.1f} deg")
        print(f"  Coherencia interna: {estado.coherencia_interna:.1f} deg")


@app.command()
def report(sociedad: str = "Chile"):
    """Genera informe HTML interactivo del último estado (modo standalone: sin especulaciones/estudios).
    Ejecuta 'daily' primero para incluir análisis completo con LLM."""
    from topologia.reportes.informe import generar_informe_html
    ruta = generar_informe_html(sociedad)
    if ruta:
        print(f"Informe generado: {ruta}")
        print("  Modo standalone (solo datos de estado + operaciones)")
        print("  Para informe completo con especulaciones y estudios, ejecute 'daily' primero")
    else:
        print("No hay datos de estado. Ejecute 'observe' o 'daily' primero.")


@app.command()
def panel(sociedad: str = "Chile"):
    """Genera panel HTML de comparación."""
    from topologia.reportes.panel import generar_panel
    ruta = generar_panel(sociedad)
    print(f"Panel generado en: {ruta}")


@app.command()
def rss(limite: int = 5):
    """Extrae y muestra noticias desde fuentes RSS configuradas."""
    from topologia.web.rss import obtener_items
    items = obtener_items(limite=limite)
    if not items:
        print("No se obtuvieron noticias.")
        return
    print(f"=== {len(items)} noticias obtenidas ===")
    for it in items[:limite]:
        print(f"\n[{it.id}] {it.titulo}")
        print(f"    Fuente: {it.fuente}")
        print(f"    {it.contenido[:200]}...")


@app.command()
def trends(keyword: str):
    """Analiza semánticamente una palabra clave con el LLM."""
    from topologia.web.analizador import AnalizadorSemantico
    at = AnalizadorSemantico()
    resultado = at.analizar(keyword)
    print(f"Relevancia: {resultado.relevancia}")
    print(f"Análisis: {resultado.analisis}")


@app.command()
def graficos(
    sociedad: str = "Chile",
    antes: str | None = None,
    despues: str | None = None,
    abrir: bool = False,
):
    """Genera 5 gráficos de análisis cultural (e^(2πi/m))."""
    from scripts.analisis_graficos import generar_todos

    archivos = generar_todos(sociedad, antes, despues)
    print(f"\n{len(archivos)} gráficos generados en reportes/")
    for a in archivos:
        print(f"  {a.name}")
    if abrir:
        import os
        for a in archivos:
            os.startfile(str(a))


@app.command()
def test_llm():
    """Prueba de conectividad con el LLM configurado."""
    from topologia.models.llm import test_llm
    resultado = test_llm()
    print(resultado)


if __name__ == "__main__":
    app()
