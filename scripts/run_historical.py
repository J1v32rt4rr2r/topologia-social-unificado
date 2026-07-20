"""Run daily cycles for specific dates to fill historical data."""
import sys
import types
from datetime import datetime
from unittest.mock import patch

def run_daily_for_date(target_date_str: str):
    """Run ciclo_diario with a specific date."""
    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # Patch datetime.now to return our target date
    original_datetime = datetime
    
    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return original_datetime(target.year, target.month, target.day, 
                                      target.hour, target.minute, target.second,
                                      tzinfo=tz)
    
    # Patch the datetime module used by schemas and store
    import topologia.models.schemas as schemas_mod
    import topologia.storage.store as store_mod
    import topologia.orchestrator as orch_mod
    import topologia.agents.redactor as redactor_mod
    import topologia.reportes.panel as panel_mod
    import topologia.reportes.informe as informe_mod
    
    # Save originals
    orig_schemas_datetime = schemas_mod.datetime
    orig_store_datetime = store_mod.datetime
    
    # Apply patches
    schemas_mod.datetime = MockDatetime
    store_mod.datetime = MockDatetime
    
    try:
        from topologia.orchestrator import Orchestrator
        orch = Orchestrator()
        print(f"\n{'='*60}")
        print(f"  CICLO DIARIO: {target_date_str}")
        print(f"{'='*60}")
        informe = orch.ciclo_diario("Chile")
        print(f"Resumen: {informe.resumen_ejecutivo}")
        for alerta in informe.alertas:
            print(f"  [{alerta.tipo.value}] {alerta.mensaje}")
        print(f"OK - {target_date_str} completado")
        return True
    except Exception as e:
        print(f"ERROR en {target_date_str}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        schemas_mod.datetime = orig_schemas_datetime
        store_mod.datetime = orig_store_datetime


if __name__ == "__main__":
    dates = ["2026-07-13", "2026-07-14", "2026-07-15"]
    
    # Check if specific dates were passed as arguments
    if len(sys.argv) > 1:
        dates = sys.argv[1:]
    
    for d in dates:
        run_daily_for_date(d)
