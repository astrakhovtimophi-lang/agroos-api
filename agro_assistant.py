from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import requests
from shapely.geometry import shape

from agro_utils import (
    DATA_DIR,
    field_names_and_features,
    load_economics,
    load_events,
    load_ndvi_history,
    load_tasks,
    now_iso,
    read_json,
    write_json,
)

ASSISTANT_HISTORY_FILE = DATA_DIR / "assistant_history.json"

CROP_OPTIONS = ["Wheat", "Corn", "Sunflower", "Soy", "Other"]
STAGE_OPTIONS = [
    "Pre-sowing",
    "Emergence",
    "Vegetative",
    "Flowering",
    "Grain fill",
    "Maturity",
    "Unknown",
]

INTENT_KEYWORDS = {
    "disease": ["болез", "disease", "fung", "гриб", "плям", "spot", "інфек", "infection"],
    "pests": ["вред", "pest", "insect", "гусен", "aphid", "жук", "тля"],
    "nutrition": ["удобр", "npk", "азот", "nitrogen", "фосфор", "potassium", "питан", "живлен"],
    "irrigation": ["полив", "irrig", "влага", "moisture", "water", "зрош"],
    "ndvi": ["ndvi", "зон", "satellite", "спутник", "veg index", "индекс"],
    "economics": ["roi", "маржа", "profit", "cost", "эконом", "себестоим"],
    "weather": ["погод", "weather", "дожд", "rain", "мороз", "frost", "wind", "ветер"],
}

SYMPTOM_RULES = [
    (
        ["yellow", "yellowing", "желт", "жовт"],
        "Possible nitrogen deficiency or root stress.",
        [
            "Check lower leaves first: uniform yellowing suggests nutrition issue.",
            "Verify soil moisture before N application.",
            "Use split N feeding instead of one heavy dose.",
        ],
    ),
    (
        ["spot", "пятн", "плям", "lesion", "некроз"],
        "Possible fungal pressure.",
        [
            "Scout 20-30 plants across field zones before spraying.",
            "Separate disease from spray burn by pattern and progression.",
            "Schedule fungicide within stable low-wind window.",
        ],
    ),
    (
        ["hole", "дыр", "погриз", "bite", "chew"],
        "Possible pest damage.",
        [
            "Inspect edge rows and underside of leaves first.",
            "Count pests per plant and compare with threshold.",
            "Prefer targeted treatment over blanket spraying.",
        ],
    ),
    (
        ["wilt", "вян", "в'ян", "droop"],
        "Possible water stress or root limitations.",
        [
            "Check soil profile moisture at 10-30 cm.",
            "Reduce stress window with earlier irrigation timing.",
            "Re-check in 24h and compare canopy recovery.",
        ],
    ),
]

PLAYBOOK = {
    "wheat": {
        "pre-sowing": [
            "Confirm seed treatment and calibrate seeding rate by TKW and germination.",
            "Balance starter phosphorus for root establishment.",
        ],
        "emergence": [
            "Check stand uniformity and early weed pressure.",
            "Avoid heavy nitrogen if soil is too dry.",
        ],
        "vegetative": [
            "Prioritize nitrogen split and monitor disease entry points.",
            "Use NDVI zones for variable-rate management.",
        ],
        "flowering": [
            "Protect flag leaf and flowering window from fungal pressure.",
            "Avoid operations during strong wind or heat stress hours.",
        ],
        "grain fill": [
            "Focus on moisture conservation and disease containment.",
            "Track NDVI trend and estimate yield potential weekly.",
        ],
        "maturity": [
            "Plan harvest logistics and moisture-based timing.",
            "Lock final economics and storage strategy.",
        ],
    },
    "corn": {
        "vegetative": [
            "Nitrogen side-dress efficiency depends on soil moisture.",
            "Watch for early pest pockets near field edges.",
        ],
        "flowering": [
            "Protect pollination period from heat and water stress.",
            "Ensure adequate potassium support for stress resilience.",
        ],
        "grain fill": [
            "Maintain leaf health and avoid late nutrient shocks.",
            "Update yield forecast with NDVI and rainfall.",
        ],
    },
    "sunflower": {
        "vegetative": [
            "Track boron-sensitive growth stages carefully.",
            "Watch downy mildew and leaf spot indicators.",
        ],
        "flowering": [
            "Minimize stress during flowering and seed set.",
            "Plan disease check with humid weather windows.",
        ],
    },
    "soy": {
        "vegetative": [
            "Check nodulation before extra nitrogen decisions.",
            "Prioritize weed control timing for canopy closure.",
        ],
        "flowering": [
            "Monitor moisture and foliar disease risks.",
            "Protect reproductive stages with timely scouting.",
        ],
    },
}


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def detect_intents(question: str) -> List[str]:
    t = _norm(question)
    found: List[str] = []
    for intent, keys in INTENT_KEYWORDS.items():
        if any(k in t for k in keys):
            found.append(intent)
    if not found:
        found = ["general"]
    return found


def detect_symptom_guidance(question: str) -> List[Dict[str, Any]]:
    t = _norm(question)
    out: List[Dict[str, Any]] = []
    for keys, cause, actions in SYMPTOM_RULES:
        if any(k in t for k in keys):
            out.append({"cause": cause, "actions": actions})
    return out


def _field_centroid(field_name: str) -> Tuple[float | None, float | None]:
    if not field_name or field_name == "General":
        return None, None

    names, feats = field_names_and_features()
    if field_name not in names:
        return None, None

    feat = feats[names.index(field_name)]
    geom = feat.get("geometry")
    if not geom:
        return None, None

    try:
        poly = shape(geom)
        c = poly.centroid
        return float(c.y), float(c.x)
    except Exception:
        return None, None


def _fetch_weather(lat: float, lon: float) -> Dict[str, Any]:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "forecast_days": 3,
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("daily", {})

        dates = data.get("time", [])
        tmins = data.get("temperature_2m_min", [])
        rains = data.get("precipitation_sum", [])
        winds = data.get("wind_speed_10m_max", [])

        alerts: List[str] = []
        for i, day in enumerate(dates):
            tmin = _safe_float(tmins[i], 999) if i < len(tmins) else 999
            rain = _safe_float(rains[i], 0) if i < len(rains) else 0
            wind = _safe_float(winds[i], 0) if i < len(winds) else 0

            if tmin <= 2:
                alerts.append(f"{day}: frost risk (min {tmin:.1f} C)")
            if rain >= 15:
                alerts.append(f"{day}: heavy rain ({rain:.1f} mm)")
            if wind >= 12:
                alerts.append(f"{day}: strong wind ({wind:.1f} m/s)")

        return {
            "ok": True,
            "alerts": alerts,
            "next_day": {
                "date": dates[0] if dates else None,
                "tmin": _safe_float(tmins[0], 0.0) if tmins else None,
                "rain": _safe_float(rains[0], 0.0) if rains else None,
                "wind": _safe_float(winds[0], 0.0) if winds else None,
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "alerts": []}


def build_field_context(field_name: str, include_weather: bool = True) -> Dict[str, Any]:
    field = field_name if field_name and field_name != "No field" else "General"

    ndvi_rows = [r for r in load_ndvi_history() if str(r.get("field")) == field]
    ndvi_rows.sort(key=lambda x: str(x.get("date") or ""))

    latest_ndvi = None
    ndvi_drop_pct = None
    if ndvi_rows:
        latest_ndvi = _safe_float(ndvi_rows[-1].get("ndvi_mean"), None)
        prev = ndvi_rows[:-1][-3:]
        if prev and latest_ndvi is not None:
            prev_avg = sum(_safe_float(x.get("ndvi_mean"), 0.0) for x in prev) / len(prev)
            if prev_avg > 0:
                ndvi_drop_pct = (latest_ndvi - prev_avg) / prev_avg * 100.0

    econ_rows = [r for r in load_economics() if str(r.get("field")) == field]
    margin_sum = sum(_safe_float(r.get("margin_uah"), 0.0) for r in econ_rows)
    revenue_sum = sum(_safe_float(r.get("revenue_uah"), 0.0) for r in econ_rows)
    cost_sum = sum(_safe_float(r.get("total_cost_uah"), 0.0) for r in econ_rows)

    events = [e for e in load_events() if str(e.get("field")) == field]
    recent_cutoff = (datetime.now() - timedelta(days=14)).date().isoformat()
    recent_events = [e for e in events if str(e.get("event_date") or "") >= recent_cutoff]

    overdue_tasks = 0
    cutoff = datetime.now() - timedelta(days=3)
    for t in load_tasks():
        if bool(t.get("done")):
            continue
        created_raw = str(t.get("created") or "")
        try:
            created_dt = datetime.fromisoformat(created_raw)
        except Exception:
            continue
        if created_dt <= cutoff:
            overdue_tasks += 1

    lat, lon = _field_centroid(field)
    weather = None
    if include_weather and lat is not None and lon is not None:
        weather = _fetch_weather(lat, lon)

    return {
        "field": field,
        "latest_ndvi": latest_ndvi,
        "ndvi_drop_pct": ndvi_drop_pct,
        "ndvi_points": len(ndvi_rows),
        "events_14d": len(recent_events),
        "overdue_tasks": overdue_tasks,
        "revenue_uah": revenue_sum,
        "cost_uah": cost_sum,
        "margin_uah": margin_sum,
        "lat": lat,
        "lon": lon,
        "weather": weather,
    }


def _stage_key(stage: str) -> str:
    s = _norm(stage)
    if "pre" in s or "посев" in s or "sowing" in s:
        return "pre-sowing"
    if "emerg" in s or "всход" in s:
        return "emergence"
    if "veget" in s or "вег" in s or "кущ" in s:
        return "vegetative"
    if "flower" in s or "цвет" in s:
        return "flowering"
    if "grain" in s or "налив" in s:
        return "grain fill"
    if "matur" in s or "спел" in s:
        return "maturity"
    return "unknown"


def _crop_key(crop: str) -> str:
    c = _norm(crop)
    if "wheat" in c or "пшени" in c:
        return "wheat"
    if "corn" in c or "maize" in c or "куку" in c:
        return "corn"
    if "sunflower" in c or "подсол" in c:
        return "sunflower"
    if "soy" in c or "соя" in c:
        return "soy"
    return "wheat"


def _mode_level(mode: str) -> int:
    m = _norm(mode)
    if "deep" in m:
        return 3
    if "expert" in m:
        return 2
    return 1


def generate_expert_response(
    question: str,
    field_name: str,
    crop: str,
    stage: str,
    mode: str = "expert",
    include_weather: bool = True,
) -> Dict[str, Any]:
    intents = detect_intents(question)
    symptom_guidance = detect_symptom_guidance(question)
    context = build_field_context(field_name, include_weather=include_weather)

    crop_key = _crop_key(crop)
    stage_key = _stage_key(stage)
    level = _mode_level(mode)

    stage_actions = PLAYBOOK.get(crop_key, {}).get(stage_key, [])

    risks: List[str] = []
    actions_24h: List[str] = []
    actions_7d: List[str] = []
    checks: List[str] = []

    latest_ndvi = context.get("latest_ndvi")
    ndvi_drop_pct = context.get("ndvi_drop_pct")

    if latest_ndvi is not None and latest_ndvi < 0.45:
        risks.append(f"Low NDVI ({latest_ndvi:.3f}) indicates crop stress.")
        actions_24h.append("Inspect low-vigor zones first and verify root/leaf condition.")
        actions_7d.append("Apply variable-rate correction instead of uniform treatment.")

    if ndvi_drop_pct is not None and ndvi_drop_pct <= -12:
        risks.append(f"NDVI dropped {abs(ndvi_drop_pct):.1f}% versus recent baseline.")
        actions_24h.append("Compare latest satellite scene with field scouting points.")
        actions_7d.append("Recalculate zone priorities and update treatment map.")

    weather = context.get("weather") or {}
    weather_alerts_raw = weather.get("alerts") if isinstance(weather, dict) else []
    weather_alerts = weather_alerts_raw if isinstance(weather_alerts_raw, list) else []
    for wa in weather_alerts[:3]:
        risks.append(f"Weather alert: {wa}.")
    if weather_alerts:
        actions_24h.append("Adjust spray/field operations to low-wind and no-rain windows.")

    if context.get("margin_uah", 0.0) < 0:
        risks.append("Negative economic margin in recorded periods.")
        actions_7d.append("Prioritize interventions with highest yield protection per UAH spent.")

    if context.get("overdue_tasks", 0) > 0:
        actions_24h.append(f"Close overdue tasks: {context['overdue_tasks']} waiting more than 3 days.")

    if "nutrition" in intents:
        actions_24h.append("Run quick NPK balance check using current NDVI and target yield.")
        actions_7d.append("Split nitrogen dose into 2 applications to reduce weather risk.")
        checks.append("Soil N, P, K lab values or latest SoilGrids layer snapshot.")

    if "disease" in intents:
        actions_24h.append("Scout 20-30 plants across zones before fungicide decision.")
        actions_7d.append("Track lesion progression by photo points every 2-3 days.")
        checks.append("Canopy humidity window and lesion spread speed.")

    if "pests" in intents:
        actions_24h.append("Check edge rows and underside of leaves for active pest stages.")
        actions_7d.append("Use threshold-based targeted control map.")
        checks.append("Pests per plant and affected area percentage.")

    if "irrigation" in intents:
        actions_24h.append("Measure soil moisture at 10-30 cm in low NDVI zones.")
        actions_7d.append("Shift irrigation timing to reduce midday stress.")

    if "economics" in intents:
        checks.append("Update break-even price and margin after each major treatment.")
        actions_7d.append("Compare intervention ROI by field zone before full-field spend.")

    for sg in symptom_guidance:
        risks.append(sg["cause"])
        for a in sg["actions"]:
            actions_24h.append(a)

    for a in stage_actions:
        actions_7d.append(a)

    def uniq(values: List[str]) -> List[str]:
        seen = set()
        out = []
        for v in values:
            key = v.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    risks = uniq(risks)
    actions_24h = uniq(actions_24h)
    actions_7d = uniq(actions_7d)
    checks = uniq(checks)

    if not risks:
        risks = ["No critical risk found from current inputs, but keep weekly scouting cadence."]
    if not actions_24h:
        actions_24h = ["Perform focused field scouting in weakest zone and record photo evidence."]
    if not actions_7d:
        actions_7d = ["Refresh NDVI and economics snapshot before next operation cycle."]

    lines: List[str] = []
    lines.append("### Expert Agro Assistant")
    lines.append(f"- Field: **{context['field']}**")
    lines.append(f"- Crop / stage: **{crop} / {stage}**")
    lines.append(f"- Detected focus: **{', '.join(intents)}**")
    if latest_ndvi is not None:
        lines.append(f"- Latest NDVI: **{latest_ndvi:.3f}**")
    if ndvi_drop_pct is not None:
        lines.append(f"- NDVI delta vs baseline: **{ndvi_drop_pct:+.1f}%**")

    lines.append("\n### Key Risks")
    for r in risks[: (6 if level >= 2 else 3)]:
        lines.append(f"- {r}")

    lines.append("\n### 24h Action Plan")
    for a in actions_24h[: (8 if level >= 2 else 4)]:
        lines.append(f"- {a}")

    lines.append("\n### 7-day Plan")
    for a in actions_7d[: (8 if level >= 2 else 4)]:
        lines.append(f"- {a}")

    lines.append("\n### What To Measure Next")
    base_checks = [
        "Leaf photo points in strong/weak zones.",
        "Recent operation log (dose, date, weather).",
        "Soil moisture in 2 depths.",
    ]
    for c in uniq(base_checks + checks)[: (10 if level == 3 else 6)]:
        lines.append(f"- {c}")

    if level >= 3:
        lines.append("\n### Deep Mode")
        lines.append("- Prioritize interventions by expected yield protection per unit cost.")
        lines.append("- Re-run NDVI zoning after each major weather event.")
        lines.append("- Validate decisions with 3-zone ground truth (high/medium/low vigor).")

    answer = "\n".join(lines)
    return {
        "answer": answer,
        "context": context,
        "intents": intents,
        "symptom_guidance": symptom_guidance,
    }


def append_assistant_history(payload: Dict[str, Any]) -> None:
    rows = read_json(ASSISTANT_HISTORY_FILE, [])
    if not isinstance(rows, list):
        rows = []

    item = dict(payload)
    item.setdefault("created_at", now_iso())
    rows.append(item)
    write_json(ASSISTANT_HISTORY_FILE, rows)
