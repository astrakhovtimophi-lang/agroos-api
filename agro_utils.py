from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FIELDS_FILE = DATA_DIR / "fields.geojson"
TASKS_FILE = DATA_DIR / "tasks.json"
JOURNAL_FILE = DATA_DIR / "journal.json"
EVENTS_FILE = DATA_DIR / "field_events.json"
NDVI_HISTORY_FILE = DATA_DIR / "ndvi_history.json"
ECONOMICS_FILE = DATA_DIR / "economics.json"
ALERT_RULES_FILE = DATA_DIR / "alert_rules.json"
ALERT_LOG_FILE = DATA_DIR / "alert_log.json"
PHOTO_DIAG_FILE = DATA_DIR / "photo_diagnostics.json"
NUTRITION_FILE = DATA_DIR / "nutrition_plans.json"
USERS_FILE = DATA_DIR / "users.json"

CROP_PLAN_FILE = DATA_DIR / "crop_plan.json"
OPERATIONS_FILE = DATA_DIR / "operations_log.json"
MACHINERY_LOG_FILE = DATA_DIR / "machinery_log.json"
WAREHOUSE_TX_FILE = DATA_DIR / "warehouse_transactions.json"
SCOUTING_FILE = DATA_DIR / "scouting_log.json"
TELEMATICS_FILE = DATA_DIR / "telematics_log.json"
COMPLIANCE_FILE = DATA_DIR / "compliance_log.json"
PESTICIDES_FILE = DATA_DIR / "pesticides_catalog.json"
FIELD_GROUPS_FILE = DATA_DIR / "field_groups.json"
AUTOSTEER_PLANS_FILE = DATA_DIR / "autosteer_plans.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_list(path: Path) -> List[Dict[str, Any]]:
    rows = read_json(path, [])
    return rows if isinstance(rows, list) else []


def append_to_list(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = load_list(path)
    item = dict(payload)
    item.setdefault("created_at", now_iso())
    rows.append(item)
    write_json(path, rows)
    return item


def load_fields_fc() -> Dict[str, Any]:
    fc = read_json(FIELDS_FILE, {"type": "FeatureCollection", "features": []})
    if isinstance(fc, dict) and isinstance(fc.get("features"), list):
        return fc
    return {"type": "FeatureCollection", "features": []}


def field_names_and_features() -> Tuple[List[str], List[Dict[str, Any]]]:
    names: List[str] = []
    feats: List[Dict[str, Any]] = []
    for feat in load_fields_fc().get("features", []):
        if not isinstance(feat, dict):
            continue
        geom = feat.get("geometry")
        if not geom:
            continue
        props = feat.get("properties") or {}
        name = props.get("name") or f"field_{len(names) + 1}"
        names.append(str(name))
        feats.append(feat)
    return names, feats


def load_tasks() -> List[Dict[str, Any]]:
    data = read_json(TASKS_FILE, [])
    return data if isinstance(data, list) else []


def load_journal() -> List[Dict[str, Any]]:
    data = read_json(JOURNAL_FILE, [])
    return data if isinstance(data, list) else []


def load_events() -> List[Dict[str, Any]]:
    return load_list(EVENTS_FILE)


def save_events(events: List[Dict[str, Any]]) -> None:
    write_json(EVENTS_FILE, events)


def add_event(
    field_name: str,
    event_type: str,
    event_date: str,
    note: str = "",
    cost: float = 0.0,
    source: str = "manual",
    source_ref: str = "",
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    events = load_events()
    event = {
        "id": f"ev_{int(datetime.now().timestamp() * 1000)}_{len(events) + 1}",
        "field": field_name,
        "event_type": event_type,
        "event_date": event_date,
        "cost": float(cost or 0.0),
        "note": note,
        "source": source,
        "source_ref": source_ref,
        "meta": meta or {},
        "created_at": now_iso(),
    }
    events.append(event)
    save_events(events)
    return event


def sync_planner_to_events() -> Dict[str, int]:
    events = load_events()
    existing_refs = {str(e.get("source_ref") or "") for e in events}
    added_tasks = 0
    added_notes = 0

    for i, t in enumerate(load_tasks()):
        created = str(t.get("created") or "")
        title = str(t.get("task") or "").strip()
        if not title:
            continue
        ref = f"task:{i}:{created}:{title}"
        if ref in existing_refs:
            continue
        add_event(
            field_name="General",
            event_type="task_done" if bool(t.get("done")) else "task",
            event_date=(created[:10] if created else now_iso()[:10]),
            note=f"{title} (priority: {t.get('priority', 'Normal')})",
            source="planner",
            source_ref=ref,
        )
        existing_refs.add(ref)
        added_tasks += 1

    for i, n in enumerate(load_journal()):
        ts = str(n.get("ts") or "")
        title = str(n.get("title") or "Note").strip() or "Note"
        note = str(n.get("note") or "").strip()
        ref = f"journal:{i}:{ts}:{title}"
        if ref in existing_refs:
            continue
        add_event(
            field_name="General",
            event_type="journal",
            event_date=(ts[:10] if ts else now_iso()[:10]),
            note=f"{title}: {note}".strip(),
            source="journal",
            source_ref=ref,
        )
        existing_refs.add(ref)
        added_notes += 1

    return {"tasks": added_tasks, "notes": added_notes}


def load_ndvi_history() -> List[Dict[str, Any]]:
    return load_list(NDVI_HISTORY_FILE)


def add_ndvi_record(field_name: str, date_str: str, ndvi_mean: float, source: str = "manual") -> Dict[str, Any]:
    return append_to_list(
        NDVI_HISTORY_FILE,
        {
            "field": field_name,
            "date": date_str,
            "ndvi_mean": float(ndvi_mean),
            "source": source,
        },
    )


def latest_ndvi_for_field(field_name: str) -> float | None:
    rows = [r for r in load_ndvi_history() if str(r.get("field")) == str(field_name)]
    if not rows:
        return None
    rows.sort(key=lambda x: str(x.get("date") or ""))
    try:
        return float(rows[-1].get("ndvi_mean"))
    except Exception:
        return None


def load_economics() -> List[Dict[str, Any]]:
    return load_list(ECONOMICS_FILE)


def add_economic_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(ECONOMICS_FILE, payload)


def load_alert_rules() -> Dict[str, Any]:
    data = read_json(ALERT_RULES_FILE, {})
    return data if isinstance(data, dict) else {}


def save_alert_rules(payload: Dict[str, Any]) -> None:
    write_json(ALERT_RULES_FILE, payload)


def append_alert_log(alerts: List[Dict[str, Any]]) -> None:
    rows = load_list(ALERT_LOG_FILE)
    rows.append({"at": now_iso(), "alerts": alerts})
    write_json(ALERT_LOG_FILE, rows)


def append_photo_diag(payload: Dict[str, Any]) -> None:
    append_to_list(PHOTO_DIAG_FILE, payload)


def append_nutrition_plan(payload: Dict[str, Any]) -> None:
    append_to_list(NUTRITION_FILE, payload)


def load_users() -> List[Dict[str, Any]]:
    return load_list(USERS_FILE)


def save_users(users: List[Dict[str, Any]]) -> None:
    write_json(USERS_FILE, users)


# --- Operations modules ---
def load_crop_plan() -> List[Dict[str, Any]]:
    return load_list(CROP_PLAN_FILE)


def append_crop_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(CROP_PLAN_FILE, payload)


def load_operations() -> List[Dict[str, Any]]:
    return load_list(OPERATIONS_FILE)


def append_operation(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(OPERATIONS_FILE, payload)


def load_machinery_logs() -> List[Dict[str, Any]]:
    return load_list(MACHINERY_LOG_FILE)


def append_machinery_log(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(MACHINERY_LOG_FILE, payload)


def load_warehouse_transactions() -> List[Dict[str, Any]]:
    return load_list(WAREHOUSE_TX_FILE)


def append_warehouse_transaction(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(WAREHOUSE_TX_FILE, payload)


def load_scouting() -> List[Dict[str, Any]]:
    return load_list(SCOUTING_FILE)


def append_scouting(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(SCOUTING_FILE, payload)


def load_telematics() -> List[Dict[str, Any]]:
    return load_list(TELEMATICS_FILE)


def append_telematics(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(TELEMATICS_FILE, payload)


def load_compliance() -> List[Dict[str, Any]]:
    return load_list(COMPLIANCE_FILE)


def append_compliance(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(COMPLIANCE_FILE, payload)


def load_pesticides_catalog() -> List[Dict[str, Any]]:
    rows = load_list(PESTICIDES_FILE)
    if rows:
        return rows

    defaults = [
        {
            "product": "Fungicide A",
            "crop": "Wheat",
            "max_dose_l_ha": 1.0,
            "rei_hours": 24,
            "phi_days": 30,
            "active": "tebuconazole",
        },
        {
            "product": "Herbicide B",
            "crop": "Corn",
            "max_dose_l_ha": 1.5,
            "rei_hours": 12,
            "phi_days": 45,
            "active": "nicosulfuron",
        },
        {
            "product": "Insecticide C",
            "crop": "Sunflower",
            "max_dose_l_ha": 0.3,
            "rei_hours": 24,
            "phi_days": 20,
            "active": "lambda-cyhalothrin",
        },
    ]
    write_json(PESTICIDES_FILE, defaults)
    return defaults


def save_pesticides_catalog(rows: List[Dict[str, Any]]) -> None:
    write_json(PESTICIDES_FILE, rows)


def load_field_groups() -> List[Dict[str, Any]]:
    return load_list(FIELD_GROUPS_FILE)


def save_field_groups(rows: List[Dict[str, Any]]) -> None:
    write_json(FIELD_GROUPS_FILE, rows)





def load_autosteer_plans() -> List[Dict[str, Any]]:
    return load_list(AUTOSTEER_PLANS_FILE)


def append_autosteer_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    return append_to_list(AUTOSTEER_PLANS_FILE, payload)
