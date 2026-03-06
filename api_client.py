import requests


def api_healthcheck(base_url: str) -> bool:
    try:
        base_url = (base_url or "").strip().rstrip("/")
        r = requests.get(f"{base_url}/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def call_api_advice(
    base_url: str,
    crop: str,
    stage: str,
    symptoms: str,
    timeout_s: int = 20,
    field: str = "General",
    mode: str = "Expert",
    include_weather: bool = False,
) -> str:
    base_url = (base_url or "").strip().rstrip("/")
    url = f"{base_url}/advice"
    payload = {
        "crop": (crop or "").strip(),
        "stage": (stage or "").strip(),
        "symptoms": (symptoms or "").strip(),
        "field": (field or "General").strip(),
        "mode": (mode or "Expert").strip(),
        "include_weather": bool(include_weather),
    }

    if not payload["symptoms"]:
        return "Fill at least the symptoms/question field."

    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
        if r.status_code == 422:
            return "API returned 422. Check crop/stage/symptoms payload format."
        r.raise_for_status()
        data = r.json()
        return data.get("advice") or "No 'advice' field in API response."
    except requests.exceptions.ConnectionError:
        return f"Cannot connect to API: {base_url}"
    except requests.exceptions.Timeout:
        return "API timeout."
    except Exception as e:
        return f"API error: {e}"
