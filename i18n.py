import streamlit as st
from settings_store import get_lang

LANGUAGES = {
    "Українська": "ua",
    "English": "en",
    "Русский": "ru",
}
INV_LANG = {v:k for k,v in LANGUAGES.items()}

TEXT = {
  "settings": {"ua":"Налаштування", "en":"Settings", "ru":"Настройки"},
  "language": {"ua":"Мова", "en":"Language", "ru":"Язык"},
  "app_title": {"ua":"AgroOS — агроплатформа", "en":"AgroOS — agronomy platform", "ru":"AgroOS — агроплатформа"},
  "home_title": {"ua":"Головна", "en":"Home", "ru":"Главная"},
  "pages_hint": {"ua":"Модулі відкривай у меню Pages зліва.", "en":"Open modules in the Pages menu (left).", "ru":"Открывай модули в меню Pages слева."},
  "by": {"ua":"By Astrakhov", "en":"By Astrakhov", "ru":"By Astrakhov"},

  "ndvi_title": {"ua":"NDVI Авто (поле)", "en":"NDVI Auto (field)", "ru":"NDVI Авто (поле)"},
  "ai_photo_title": {"ua":"AI Аналіз фото", "en":"AI Photo Analysis", "ru":"AI Анализ фото"},
  "calculators_title": {"ua":"Калькулятори", "en":"Calculators", "ru":"Калькуляторы"},
  "planner_title": {"ua":"Планувальник і журнал", "en":"Planner & Journal", "ru":"Планировщик и журнал"},
  "diagnostics_title": {"ua":"Діагностика", "en":"Diagnostics", "ru":"Диагностика"},
}

def ensure_lang():
    if "lang" not in st.session_state or st.session_state["lang"] not in ("ua","en","ru"):
        st.session_state["lang"] = get_lang("ua")

def tr(key: str) -> str:
    ensure_lang()
    return TEXT.get(key, {}).get(st.session_state["lang"], key)



