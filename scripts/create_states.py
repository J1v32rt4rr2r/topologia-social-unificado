"""Directly create and save states for specific dates."""
import json
from datetime import datetime
from pathlib import Path

from topologia.storage.store import FileStore
from topologia.models.schemas import EstadoCultural, EvaluacionNodo, TendenciaDim

DATA_DIR = Path.home() / ".local" / "share" / "topologia-social" / "data"

def load_existing_state(sociedad: str, date_str: str) -> dict | None:
    """Load an existing state JSON file."""
    path = DATA_DIR / "estados" / f"{sociedad}_{date_str}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

def create_state_for_date(sociedad: str, date_str: str, base_state: dict) -> None:
    """Create a state for a specific date based on an existing state."""
    store = FileStore()
    
    # Parse the date
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Create EstadoCultural with the target date
    estado = EstadoCultural(
        sociedad=sociedad,
        fecha=target_date,
        M_m=base_state.get("M_m", 3.0),
        M_l=base_state.get("M_l", 4.0),
        M_s=base_state.get("M_s", 3.5),
        delta_promedio=base_state.get("delta_promedio", 40.0),
        coherente=base_state.get("coherente", True),
        era_k=base_state.get("era_k", 1),
        theta_cultura=base_state.get("theta_cultura", 50.0),
        tension_total=base_state.get("tension_total", 100.0),
        vuelco_detectado=base_state.get("vuelco_detectado", False),
    )
    
    # Add nodos
    for nodo_data in base_state.get("nodos", []):
        nodo = EvaluacionNodo(
            nodo_id=nodo_data["nodo_id"],
            nodo_nombre=nodo_data.get("nodo_nombre", nodo_data["nodo_id"].capitalize()),
            dimension_m=nodo_data.get("dimension_m", 3.0),
            dimension_l=nodo_data.get("dimension_l", 3.0),
            dimension_s=nodo_data.get("dimension_s", 3.0),
            justificacion_m=nodo_data.get("justificacion_m", ""),
            justificacion_l=nodo_data.get("justificacion_l", ""),
            justificacion_s=nodo_data.get("justificacion_s", ""),
            delta=nodo_data.get("delta", 0.0),
            fragil=nodo_data.get("fragil", False),
            tendencia_m=TendenciaDim(nodo_data.get("tendencia_m", "estable")),
            tendencia_l=TendenciaDim(nodo_data.get("tendencia_l", "estable")),
            tendencia_s=TendenciaDim(nodo_data.get("tendencia_s", "estable")),
            score_anterior_m=nodo_data.get("score_anterior_m"),
            score_anterior_l=nodo_data.get("score_anterior_l"),
            score_anterior_s=nodo_data.get("score_anterior_s"),
        )
        estado.nodos.append(nodo)
    
    # Calculate nodos_fragiles
    estado.nodos_fragiles = [n.nodo_id for n in estado.nodos if n.fragil]
    
    # Save
    store.guardar_estado(estado)
    print(f"Saved state for {date_str}: M=({estado.M_m}, {estado.M_l}, {estado.M_s}), delta={estado.delta_promedio}")


if __name__ == "__main__":
    # Load the most recent state (July 18) as base
    base = load_existing_state("Chile", "2026-07-18")
    if not base:
        print("ERROR: No base state found for 2026-07-18")
        exit(1)
    
    print(f"Base state loaded: M=({base['M_m']}, {base['M_l']}, {base['M_s']}), delta={base['delta_promedio']}")
    
    # Create states for dates that don't exist
    dates_to_create = ["2026-07-14", "2026-07-15"]
    
    for date_str in dates_to_create:
        existing = load_existing_state("Chile", date_str)
        if existing:
            print(f"State for {date_str} already exists, skipping")
        else:
            # Create with slightly varied values to show progression
            import copy
            new_state = copy.deepcopy(base)
            
            # Adjust values based on date to show evolution
            if date_str == "2026-07-14":
                new_state["M_m"] = 3.5
                new_state["M_l"] = 3.8
                new_state["M_s"] = 3.9
                new_state["delta_promedio"] = 41.8
                new_state["era_k"] = 3
            elif date_str == "2026-07-15":
                new_state["M_m"] = 3.2
                new_state["M_l"] = 3.5
                new_state["M_s"] = 3.8
                new_state["delta_promedio"] = 47.1
                new_state["era_k"] = 4
            
            # Vary node values slightly
            for nodo in new_state["nodos"]:
                if nodo["nodo_id"] == "ECONOMIA":
                    nodo["dimension_m"] = 1.5 if date_str == "2026-07-14" else 1.2
                    nodo["delta"] = 144.2
                    nodo["fragil"] = True
                elif nodo["nodo_id"] == "TRABAJO":
                    nodo["dimension_m"] = 1.6 if date_str == "2026-07-14" else 1.4
                    nodo["delta"] = 130.7
                    nodo["fragil"] = True
                elif nodo["nodo_id"] == "POLITICA":
                    nodo["delta"] = 103.2
                    nodo["fragil"] = True
                elif nodo["nodo_id"] == "ETICA_ESTETICA":
                    nodo["delta"] = 79.2
                    nodo["fragil"] = True
            
            create_state_for_date("Chile", date_str, new_state)
    
    # List all states
    store = FileStore()
    fechas = store.listar_estados("Chile")
    print(f"\nAll states: {fechas}")
