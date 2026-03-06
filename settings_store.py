import json
from pathlib import Path

SETTINGS_PATH = Path("data") / "settings.json"

def load_settings() -> dict:
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except:
        pass
    return {}

def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

def get_lang(default: str = "ua") -> str:
    s = load_settings()
    lang = s.get("lang", default)
    if lang not in ("ua","en","ru"):
        return default
    return lang

def set_lang(lang: str) -> None:
    if lang not in ("ua","en","ru"):
        return
    s = load_settings()
    s["lang"] = lang
    save_settings(s)



