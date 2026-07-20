"""Prueba básica de imports y funcionalidad del sistema unificado."""

from topologia.models.schemas import (
    Especulacion, EstadoCultural, EvaluacionNodo,
    Estudio, AnalisisDim, PatronAnalogico, EstadoPatron,
    OperacionCinetica, InformeDiario, Alerta,
)
from topologia.models.patterns import listar_operaciones, get_operacion
from topologia.math.torus import mapear_a_toro_3d, coherencia_global
from topologia.math.operations import detectar_operaciones
from topologia.memoria.decisiones import DecisionDB
from topologia.memoria.bloques import BloquesMemoria
from topologia.paths import get_data_dir, get_memoria_dir, get_reportes_dir, get_estados_dir
from topologia.storage.store import FileStore


def test_sanitizar_sociedad():
    from topologia.server.routers.dashboard import _sanitizar_sociedad as s
    assert s("Chile") == "Chile"
    assert s("  Chile  ") == "Chile"
    assert s("") == "Chile"
    assert s("../../../etc") == "Chile"
    assert s("Costa Rica") == "Costa Rica"
    print("[OK] Sanitizador de sociedad funciona")


def test_orchestrator_imports():
    from topologia.orchestrator import Orchestrator
    o = Orchestrator()
    assert o is not None
    import topologia.models.schemas as s
    assert hasattr(s, "InformeDiario")
    print(f"[OK] Orchestrator instanciado, InformeDiario importable")


def test_paths():
    d = get_data_dir()
    assert str(d).endswith("data") or str(d).endswith("data\\")
    m = get_memoria_dir()
    assert "memoria" in str(m)
    r = get_reportes_dir()
    assert "reportes" in str(r)
    e = get_estados_dir()
    assert "estados" in str(e)
    print(f"[OK] Paths: data={d.parent.name}/{d.name}")


def test_especulacion():
    esp = Especulacion(patron_id="P-015", confianza=0.85, argumento="test")
    assert esp.patron_id == "P-015"
    assert esp.confianza == 0.85
    assert esp.argumento == "test"
    print("[OK] Especulación creada correctamente")


def test_toro_3d():
    x, y, z, i, u = mapear_a_toro_3d(5.0, 5.0, 5.0)
    assert isinstance(x, float)
    assert isinstance(y, float)
    assert isinstance(z, float)
    assert 0.0 <= i <= 1.0
    print(f"[OK] Mapeo a toro 3D: ({x:.2f}, {y:.2f}, {z:.2f})")


def test_coherencia():
    coh = coherencia_global([(5.0, 6.0, 4.0), (3.0, 7.0, 2.0)])
    assert "M_m" in coh
    assert "delta_promedio" in coh
    assert 0 <= coh["delta_promedio"] <= 180
    print(f"[OK] Coherencia: M_m={coh['M_m']:.1f}, delta={coh['delta_promedio']:.1f}°")


def test_operaciones_catalogo():
    ops = listar_operaciones()
    assert len(ops) == 17
    op = get_operacion("O4a")
    assert op is not None
    assert op.nombre == "Cuadrícula centrada"
    print(f"[OK] Catalogo: {len(ops)} operaciones, O4a={op.nombre}")


def test_estado_cultural():
    estado = EstadoCultural(
        sociedad="Chile",
        M_m=3.5,
        M_l=5.2,
        M_s=4.1,
        delta_promedio=42.0,
        coherente=True,
    )
    assert estado.sociedad == "Chile"
    assert estado.M_m == 3.5
    print(f"[OK] Estado cultural creado: M=({estado.M_m}, {estado.M_l}, {estado.M_s})")


def test_patron_analogico():
    patron = PatronAnalogico(
        id="P-015",
        forma="Caída vertical con acumulación basal",
        significado="La violencia del poder invisible se desata cuando no se ve",
    )
    assert patron.estado == EstadoPatron.especulativo
    assert patron.id == "P-015"
    print(f"[OK] Patron analogico: {patron.id} - {patron.forma[:30]}...")


def test_store():
    store = FileStore()
    assert store.base.exists()
    print(f"[OK] Store en: {store.base}")


def test_memoria():
    db = DecisionDB()
    stats = db.estadisticas()
    assert "total" in stats
    assert "por_tipo" in stats
    print(f"[OK] Memoria: {stats['total']} decisiones, {stats['patrones']} patrones")


def test_bloques():
    b = BloquesMemoria()
    b.escribir("test-blq", "contenido de prueba")
    leido = b.leer("test-blq")
    assert leido == "contenido de prueba"
    assert "test-blq" in b.listar()
    b.escribir("test-blq", "")
    print("[OK] Bloques de memoria funcionan")


def test_detectar_operaciones():
    estado = EstadoCultural(
        sociedad="Chile",
        M_m=3.0, M_l=5.0, M_s=4.0,
        delta_promedio=50.0,
        nodos=[
            EvaluacionNodo(
                nodo_id="POLITICA", nodo_nombre="Política",
                dimension_m=2.0, dimension_l=7.0, dimension_s=4.0,
                delta=55.0, fragil=True,
            ),
            EvaluacionNodo(
                nodo_id="ECONOMIA", nodo_nombre="Economía",
                dimension_m=2.5, dimension_l=5.0, dimension_s=3.0,
                delta=30.0,
            ),
            EvaluacionNodo(
                nodo_id="TRABAJO", nodo_nombre="Trabajo",
                dimension_m=6.0, dimension_l=4.0, dimension_s=5.0,
                delta=20.0,
            ),
        ],
        nodos_fragiles=["POLITICA"],
    )
    ops = detectar_operaciones(estado)
    assert len(ops) > 0
    print(f"[OK] Operaciones detectadas: {len(ops)}")
    for o in ops:
        print(f"   {o.codigo}: {o.nombre} (intensidad={o.intensidad:.2f})")


if __name__ == "__main__":
    test_especulacion()
    test_toro_3d()
    test_coherencia()
    test_operaciones_catalogo()
    test_estado_cultural()
    test_patron_analogico()
    test_store()
    test_memoria()
    test_bloques()
    test_detectar_operaciones()
    print("\n[OK] Todas las pruebas basicas pasaron")
