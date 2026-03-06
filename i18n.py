import streamlit as st

from settings_store import get_lang, set_lang

LANGUAGES = {
    "Українська": "ua",
    "English": "en",
    "Русский": "ru",
}
SUPPORTED_LANGS = tuple(LANGUAGES.values())
INV_LANG = {v: k for k, v in LANGUAGES.items()}

TEXT = {
    "settings": {"ua": "Налаштування", "en": "Settings", "ru": "Настройки"},
    "language": {"ua": "Мова", "en": "Language", "ru": "Язык"},
    "app_title": {"ua": "AgroOS — агроплатформа", "en": "AgroOS — agronomy platform", "ru": "AgroOS — агроплатформа"},
    "home_title": {"ua": "Головна", "en": "Home", "ru": "Главная"},
    "pages_hint": {
        "ua": "Модулі відкривай у меню Pages зліва.",
        "en": "Open modules in the Pages menu (left).",
        "ru": "Открывай модули в меню Pages слева.",
    },
    "quick_modules": {"ua": "Швидкий доступ", "en": "Quick modules", "ru": "Быстрый доступ"},
    "compact_menu_hint": {"ua": "Компактне меню модулів", "en": "Compact fallback menu", "ru": "Компактное меню модулей"},
    "more": {"ua": "Ще", "en": "More", "ru": "Еще"},
    "menu_sections": {"ua": "Розділи", "en": "Sections", "ru": "Разделы"},
    "by": {"ua": "By Astrakhov", "en": "By Astrakhov", "ru": "By Astrakhov"},

    "section_start": {"ua": "Старт", "en": "Start", "ru": "Старт"},
    "section_monitoring": {"ua": "Моніторинг", "en": "Monitoring", "ru": "Мониторинг"},
    "section_operations": {"ua": "Операції", "en": "Operations", "ru": "Операции"},
    "section_analytics": {"ua": "Аналітика", "en": "Analytics", "ru": "Аналитика"},
    "section_admin": {"ua": "Адмін", "en": "Admin", "ru": "Админ"},

    "module_landing": {"ua": "Лендінг", "en": "Landing", "ru": "Лендинг"},
    "module_home": {"ua": "Командний центр", "en": "Command Home", "ru": "Командный центр"},
    "module_ai_assistant": {"ua": "AI Агро Асистент", "en": "AI Agro Assistant", "ru": "AI Агро Ассистент"},
    "module_ops_center": {"ua": "Центр операцій", "en": "Operations Center", "ru": "Центр операций"},

    "module_ndvi_pro": {"ua": "NDVI Pro", "en": "NDVI Pro", "ru": "NDVI Pro"},
    "module_vra_zones": {"ua": "VRA Зони", "en": "VRA Zones", "ru": "VRA Зоны"},
    "module_ndvi_trends": {"ua": "NDVI Тренди", "en": "NDVI Trends", "ru": "NDVI Тренды"},
    "module_yield_import": {"ua": "Імпорт карти врожайності", "en": "Yield Map Import", "ru": "Импорт карты урожайности"},
    "module_soilgrids": {"ua": "SoilGrids", "en": "SoilGrids", "ru": "SoilGrids"},
    "module_soil_map": {"ua": "Карта ґрунтів", "en": "Soil Map", "ru": "Карта почв"},
    "module_weather": {"ua": "Погода", "en": "Weather", "ru": "Погода"},

    "module_field_manager": {"ua": "Менеджер полів", "en": "Field Manager", "ru": "Менеджер полей"},
    "module_field_groups": {"ua": "Групи полів + порівняння", "en": "Field Groups + Compare", "ru": "Группы полей + сравнение"},
    "module_autosteer": {"ua": "Автопілот трактора", "en": "Tractor AutoSteer Assist", "ru": "Автопилот трактора"},
    "module_planner": {"ua": "Планер та журнал", "en": "Planner & Journal", "ru": "Планер и журнал"},
    "module_smart_alerts": {"ua": "Розумні сповіщення", "en": "Smart Alerts", "ru": "Умные уведомления"},
    "module_timeline": {"ua": "Таймлайн поля", "en": "Field Timeline", "ru": "Таймлайн поля"},
    "module_photo_diag": {"ua": "Фото діагностика", "en": "Photo Diagnostics", "ru": "Фото диагностика"},
    "module_nutrition": {"ua": "Живлення", "en": "Nutrition", "ru": "Питание"},

    "module_yield_prediction": {"ua": "Прогноз врожаю", "en": "Yield Prediction", "ru": "Прогноз урожая"},
    "module_economics": {"ua": "Економіка поля", "en": "Field Economics", "ru": "Экономика поля"},
    "module_pdf_reports": {"ua": "PDF Звіти", "en": "PDF Reports", "ru": "PDF Отчеты"},
    "module_calculators": {"ua": "Калькулятори", "en": "Calculators", "ru": "Калькуляторы"},
    "module_smart_calculators": {"ua": "Розумні калькулятори", "en": "Smart Calculators", "ru": "Умные калькуляторы"},
    "module_diagnostics": {"ua": "Діагностика", "en": "Diagnostics", "ru": "Диагностика"},
    "module_users_access": {"ua": "Користувачі та доступ", "en": "Users & Access", "ru": "Пользователи и доступ"},

    "nav_home": {"ua": "Дім", "en": "Home", "ru": "Дом"},
    "nav_ndvi": {"ua": "NDVI", "en": "NDVI", "ru": "NDVI"},
    "nav_map": {"ua": "Мапа", "en": "Map", "ru": "Карта"},
    "nav_ai": {"ua": "AI", "en": "AI", "ru": "AI"},
    "open_ai_assistant": {"ua": "Відкрити AI Асистента", "en": "Open AI Assistant", "ru": "Открыть AI Ассистента"},

    "ndvi_title": {"ua": "NDVI Авто (поле)", "en": "NDVI Auto (field)", "ru": "NDVI Авто (поле)"},
    "ai_photo_title": {"ua": "AI Аналіз фото", "en": "AI Photo Analysis", "ru": "AI Анализ фото"},
    "calculators_title": {"ua": "Калькулятори", "en": "Calculators", "ru": "Калькуляторы"},
    "planner_title": {"ua": "Планувальник і журнал", "en": "Planner & Journal", "ru": "Планировщик и журнал"},
    "diagnostics_title": {"ua": "Діагностика", "en": "Diagnostics", "ru": "Диагностика"},
    "calculators": {"ua": "Калькулятори", "en": "Calculators", "ru": "Калькуляторы"},
    "planner": {"ua": "Планувальник і журнал", "en": "Planner & Journal", "ru": "Планировщик и журнал"},
    "diagnostics": {"ua": "Діагностика", "en": "Diagnostics", "ru": "Диагностика"},
}


def ensure_lang() -> None:
    if "lang" not in st.session_state or st.session_state["lang"] not in SUPPORTED_LANGS:
        st.session_state["lang"] = get_lang("ua")

    if st.session_state["lang"] not in SUPPORTED_LANGS:
        st.session_state["lang"] = "ua"


def tr(key: str) -> str:
    ensure_lang()
    values = TEXT.get(key, {})
    if not isinstance(values, dict):
        return key

    lang = st.session_state["lang"]
    return values.get(lang) or values.get("en") or values.get("ua") or key


def render_language_picker(widget_key: str = "lang_select_inline") -> None:
    ensure_lang()
    current_name = INV_LANG.get(st.session_state["lang"], "English")
    options = list(LANGUAGES.keys())
    current_idx = options.index(current_name) if current_name in options else 0

    lang_name = st.selectbox(tr("language"), options, index=current_idx, key=widget_key)
    new_lang = LANGUAGES.get(lang_name, "ua")

    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        set_lang(new_lang)
        st.rerun()


def render_language_settings(expanded: bool = False, widget_key: str = "lang_select_global", show_hint: bool = True) -> None:
    with st.expander("⚙️ " + tr("settings"), expanded=expanded):
        render_language_picker(widget_key=widget_key)
        if show_hint:
            st.caption(tr("pages_hint"))
