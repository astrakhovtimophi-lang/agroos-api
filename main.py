# main.py
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import streamlit as st
from PIL import Image

import google.generativeai as genai
import requests


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="AgroOS Pro",
    layout="wide",
    page_icon="🌱",
)


# =========================
# STYLES (Premium UI + animations)
# =========================
st.markdown(
    """
<style>
:root{
  --bg1:#0f2027;
  --bg2:#203a43;
  --bg3:#2c5364;
  --glass: rgba(255,255,255,0.08);
  --stroke: rgba(255,255,255,0.12);
  --accent:#00ff88;
  --accent2:#00c3ff;
  --text:#e8f6f3;
  --muted: rgba(232,246,243,0.75);
}

.stApp{
  background: radial-gradient(1200px 700px at 15% 10%, rgba(0,255,136,0.10), transparent 55%),
              radial-gradient(1000px 700px at 85% 15%, rgba(0,195,255,0.10), transparent 55%),
              linear-gradient(135deg,var(--bg1),var(--bg2),var(--bg3));
  color: var(--text);
}

.block-container{ padding-top: 1.25rem; padding-bottom: 4.2rem; }

@keyframes floatIn {
  from { opacity: 0; transform: translateY(14px) scale(0.99); }
  to   { opacity: 1; transform: translateY(0px) scale(1); }
}

@keyframes shimmer {
  0% { background-position: 0% 50%;}
  50%{ background-position: 100% 50%;}
  100%{ background-position: 0% 50%;}
}

.hero{
  padding: 18px 18px 6px 18px;
  border-radius: 22px;
  background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.05));
  border: 1px solid var(--stroke);
  backdrop-filter: blur(14px);
  animation: floatIn .45s ease;
}

.title{
  font-size: 2.6rem;
  font-weight: 900;
  line-height: 1.05;
  text-align: center;
  margin: 4px 0 8px 0;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  background-size: 200% 200%;
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  animation: shimmer 4s ease infinite;
}

.subtitle{
  text-align:center;
  color: var(--muted);
  margin: 0 0 10px 0;
  font-size: 0.98rem;
}

.card{
  background: var(--glass);
  border: 1px solid var(--stroke);
  border-radius: 20px;
  padding: 18px;
  margin: 14px 0;
  backdrop-filter: blur(14px);
  animation: floatIn .35s ease;
}

.card h3{ margin: 0 0 8px 0; }
.card small{ color: var(--muted); }

.pill{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: rgba(0,0,0,0.18);
  color: var(--muted);
  font-size: 12px;
}

.hr{
  height:1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
  margin: 14px 0;
}

.stButton>button{
  height: 56px;
  font-size: 16px;
  font-weight: 700;
  border-radius: 16px;
  background: linear-gradient(145deg, #1f2c3a, #111a24);
  border: 1px solid rgba(0,255,136,0.55);
  transition: transform .15s ease, border-color .15s ease;
}
.stButton>button:hover{
  transform: translateY(-1px) scale(1.01);
  border-color: rgba(0,195,255,0.65);
}

.footer{
  position: fixed;
  left: 0; right: 0; bottom: 0;
  padding: 8px 10px;
  text-align:center;
  font-size: 11px;
  letter-spacing: 2px;
  color: rgba(232,246,243,0.7);
  background: rgba(0,0,0,0.45);
  border-top: 1px solid rgba(255,255,255,0.12);
  backdrop-filter: blur(10px);
  z-index: 999;
}

kbd{
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.15);
  border-bottom-color: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# DATA STRUCTURES
# =========================
@dataclass
class GenAIStatus:
    ok: bool
    model_name: Optional[str] = None
    error: Optional[str] = None


# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = "Главная"

if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []

if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = st.secrets.get("GEMINI_KEY", "")

if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

if "last_status" not in st.session_state:
    st.session_state.last_status = GenAIStatus(ok=False, error="API key не задан")

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = "http://127.0.0.1:8000"


# =========================
# HELPERS
# =========================
def now_hhmm() -> str:
    return time.strftime("%H:%M")


def push_history(kind: str, title: str, content: str, meta: Optional[dict] = None) -> None:
    st.session_state.history.append(
        {
            "time": now_hhmm(),
            "kind": kind,
            "title": title,
            "content": content,
            "meta": meta or {},
        }
    )


def export_history_txt() -> str:
    lines = []
    for item in st.session_state.history:
        lines.append(f"[{item['time']}] {item['kind']} — {item['title']}")
        lines.append(item["content"])
        lines.append("-" * 60)
    return "\n".join(lines).strip()


def genai_connect(api_key: str) -> GenAIStatus:
    if not api_key or not api_key.strip():
        return GenAIStatus(ok=False, error="Введите Gemini API key")

    try:
        genai.configure(api_key=api_key.strip())

        preferred = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-1.0-pro-vision",
            "gemini-1.0-pro",
        ]

        available = []
        try:
            for m in genai.list_models():
                available.append(m.name.replace("models/", ""))
        except Exception:
            available = []

        chosen = None
        if available:
            for cand in preferred:
                if cand in available:
                    chosen = cand
                    break
            if not chosen and available:
                chosen = available[0]
        else:
            chosen = preferred[0]

        st.session_state.selected_model = chosen
        return GenAIStatus(ok=True, model_name=chosen)
    except Exception as e:
        return GenAIStatus(ok=False, error=str(e))


def get_model() -> Optional[genai.GenerativeModel]:
    if not st.session_state.last_status.ok or not st.session_state.selected_model:
        return None
    try:
        return genai.GenerativeModel(st.session_state.selected_model)
    except Exception:
        return None


def llm_analyze_image(model: genai.GenerativeModel, img: Image.Image, lang: str) -> str:
    prompt = f"""
Проанализируй фото растения.

НУЖНО:
- Определи культуру (если возможно)
- Найди болезни/вредителей/дефициты (с вероятностями словами: низк/средн/высок)
- Возможные причины
- Рекомендации: что делать сейчас + что проверить
- Уровень угрозы

Важно: если по фото нельзя уверенно — так и скажи и попроси нужные ракурсы/детали.
Язык ответа: {lang}
"""
    resp = model.generate_content([prompt, img])
    return getattr(resp, "text", "").strip() or "Пустой ответ модели."


def call_api_advice(base_url: str, crop: str, stage: str, symptoms: str, timeout_s: int = 20) -> str:
    """
    Безопасный вызов FastAPI /advice, чтобы не ловить 422 и красиво показывать ошибки.
    Ожидаемый ответ: {"crop": "...", "stage": "...", "advice": "..."}
    """
    base_url = (base_url or "").strip().rstrip("/")
    url = f"{base_url}/advice"

    payload = {
        "crop": (crop or "").strip(),
        "stage": (stage or "").strip(),
        "symptoms": (symptoms or "").strip(),
    }

    # Защита от 422: пустые поля
    if not payload["crop"] or not payload["stage"] or not payload["symptoms"]:
        return "❗ Заполни поля: Культура, Фаза и Симптомы (иначе API вернёт 422)."

    try:
        r = requests.post(url, json=payload, timeout=timeout_s)
        if r.status_code == 422:
            # Частая ошибка — неправильный JSON или пустые поля
            return "❗ API вернул 422 (Unprocessable Content). Проверь: crop/stage/symptoms передаются и не пустые."
        r.raise_for_status()
        data = r.json()
        advice = data.get("advice") or data.get("result")
        return advice or "⚠️ API вернул ответ без поля 'advice'."
    except requests.exceptions.ConnectionError:
        return f"❗ Не могу подключиться к API: {base_url}\n\nПроверь что запущено:\npython -m uvicorn api:app --reload --port 8000"
    except requests.exceptions.Timeout:
        return "❗ Таймаут: API слишком долго отвечает. Попробуй ещё раз."
    except Exception as e:
        return f"❗ Ошибка запроса к API: {e}"


def api_healthcheck(base_url: str) -> bool:
    try:
        base_url = (base_url or "").strip().rstrip("/")
        r = requests.get(f"{base_url}/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("### ⚙️ Настройки")

    st.session_state.api_base_url = st.text_input(
        "FastAPI URL",
        value=st.session_state.api_base_url,
        help="Локально: http://127.0.0.1:8000  |  Потом можно будет поставить URL с хостинга (Render/Railway).",
    )

    api_ok = api_healthcheck(st.session_state.api_base_url)
    if api_ok:
        st.success("FastAPI: работает ✅")
    else:
        st.warning("FastAPI: не найден ❗ (запусти uvicorn)")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    st.session_state.gemini_key = st.text_input(
        "Gemini API Key (для фото-сканера)",
        type="password",
        value=st.session_state.gemini_key,
        help="Нужен только для фото-анализа. Текст-диагноз работает через FastAPI.",
    )

    if st.button("🔌 Подключить Gemini", use_container_width=True):
        st.session_state.last_status = genai_connect(st.session_state.gemini_key)

    status = st.session_state.last_status
    if status.ok:
        st.success(f"Gemini подключён ✅\n\nМодель: **{status.model_name}**")
    else:
        st.info("Gemini не обязателен (нужен только для фото).")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    pages = ["Главная", "🔬 AI Сканер (фото)", "🧠 Текст-диагноз (через API)", "💰 Финансы", "📒 Журнал"]
    st.session_state.page = st.radio("Навигация", pages, index=pages.index(st.session_state.page))

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    lang = st.selectbox("Язык ответа (для фото-сканера)", ["Русский", "Українська"], index=0)
    st.session_state.ai_lang = "Русский" if lang == "Русский" else "Українська"

    st.caption("Запуск:\n- API: python -m uvicorn api:app --reload --port 8000\n- UI:  python -m streamlit run main.py")


# =========================
# UI: HEADER
# =========================
st.markdown(
    """
<div class="hero">
  <div class="title">🌱 AGRO OS PRO</div>
  <div class="subtitle">FastAPI (backend) • Streamlit (UI) — прототип стартапа</div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================
# PAGES
# =========================
def page_home():
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
<div class="card">
  <h3>🔬 AI Сканер (фото)</h3>
  <small>Фото → анализ (болезни/вредители/дефициты). Нужен Gemini ключ.</small><br><br>
  <span class="pill">Gemini</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Открыть сканер", use_container_width=True):
            st.session_state.page = "🔬 AI Сканер (фото)"

    with col2:
        st.markdown(
            """
<div class="card">
  <h3>🧠 Текст-диагноз (API)</h3>
  <small>Без фото: культура/фаза/симптомы → ответ от FastAPI.</small><br><br>
  <span class="pill">FastAPI</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Открыть текст-диагноз", use_container_width=True):
            st.session_state.page = "🧠 Текст-диагноз (через API)"

    with col3:
        st.markdown(
            """
<div class="card">
  <h3>💰 Финансы</h3>
  <small>Выручка/прибыль/ROI — без AI.</small><br><br>
  <span class="pill">Calculator</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Открыть финансы", use_container_width=True):
            st.session_state.page = "💰 Финансы"

    st.markdown(
        f"""
<div class="card">
  <h3>Статус</h3>
  <small>
  FastAPI URL: <b>{st.session_state.api_base_url}</b><br>
  FastAPI: <b>{"OK ✅" if api_healthcheck(st.session_state.api_base_url) else "OFF ❗"}</b><br>
  Gemini: <b>{"OK ✅" if st.session_state.last_status.ok else "OFF (не обязателен)"}</b>
  </small>
  <div class="hr"></div>
  <small>Подсказка: <kbd>docs</kbd> → {st.session_state.api_base_url.rstrip("/")}/docs</small>
</div>
""",
        unsafe_allow_html=True,
    )


def page_scanner_photo():
    st.markdown(
        "<div class='card'><h3>🔬 AI Сканер (фото)</h3><small>Загрузи фото листа/растения (лучше 2-3 ракурса + крупный план)</small></div>",
        unsafe_allow_html=True,
    )

    model = get_model()
    status = st.session_state.last_status

    uploaded = st.file_uploader("Фото растения", type=["png", "jpg", "jpeg"])
    if uploaded:
        img = Image.open(uploaded).convert("RGB")
        st.image(img, use_container_width=True)

    colA, colB = st.columns([1, 1])
    with colA:
        run = st.button(
            "🚀 Анализировать фото",
            use_container_width=True,
            disabled=(not uploaded or not status.ok or model is None),
        )
    with colB:
        if st.button("🧹 Очистить историю", use_container_width=True):
            st.session_state.history = []
            st.success("История очищена")

    if not status.ok or model is None:
        st.info("Для фото-анализа нужен Gemini API Key (в сайдбаре).")
        return

    if uploaded and run:
        with st.spinner("AI анализирует фото…"):
            try:
                result = llm_analyze_image(model, img, st.session_state.ai_lang)
                st.markdown(f"<div class='card'>{result}</div>", unsafe_allow_html=True)
                push_history("SCAN", "Анализ фото", result, meta={"model": st.session_state.selected_model})
            except Exception as e:
                st.error(f"Ошибка анализа: {e}")


def page_text_diag_api():
    st.markdown(
        "<div class='card'><h3>🧠 Текст-диагноз (через FastAPI)</h3><small>Эта страница НЕ использует Gemini. Она отправляет данные в /advice и показывает ответ.</small></div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        crop = st.text_input("Культура", value="пшеница")
        stage = st.text_input("Фаза (например: кущение/колошение/3-5 листьев)", value="кущение")
    with c2:
        region = st.text_input("Регион (опционально)", value="")
        weather = st.text_input("Погода/условия (опционально)", value="")

    symptoms = st.text_area(
        "Симптомы / что видишь на поле",
        height=140,
        placeholder="Например: желтые пятна, подсыхают кончики, скручиваются листья, налет…",
    )

    merged = f"{symptoms}\n\nРегион: {region}\nУсловия: {weather}".strip()

    colA, colB = st.columns([1, 1])
    with colA:
        run = st.button("🚀 Получить рекомендации (API)", use_container_width=True, disabled=(not symptoms.strip()))
    with colB:
        if st.button("📌 Добавить заметку в журнал", use_container_width=True, disabled=(not symptoms.strip())):
            note = f"Культура: {crop}\nФаза: {stage}\nРегион: {region}\nУсловия: {weather}\n\nСимптомы:\n{symptoms}"
            push_history("NOTE", "Заметка", note)
            st.success("Заметка добавлена в журнал")

    if run:
        with st.spinner("FastAPI думает…"):
            result = call_api_advice(st.session_state.api_base_url, crop, stage, merged)
            st.markdown(f"<div class='card'>{result}</div>", unsafe_allow_html=True)
            push_history("API", "Текст-диагноз (API)", result, meta={"crop": crop, "stage": stage, "api": st.session_state.api_base_url})


def page_finance():
    st.markdown("<div class='card'><h3>💰 Финансовый анализ</h3><small>Быстро посчитать выручку/прибыль/ROI</small></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        area = st.number_input("Площадь (га)", value=10.0, min_value=0.0, step=1.0)
        yield_ha = st.number_input("Урожайность (т/га)", value=4.0, min_value=0.0, step=0.1)
    with col2:
        price = st.number_input("Цена (₴ / т)", value=6000.0, min_value=0.0, step=100.0)
        costs = st.number_input("Расходы (₴)", value=100000.0, min_value=0.0, step=1000.0)

    if st.button("📊 Рассчитать", use_container_width=True):
        revenue = area * yield_ha * price
        profit = revenue - costs
        roi = (profit / costs * 100) if costs > 0 else 0.0

        result = (
            f"💰 Выручка: {revenue:,.0f} ₴\n"
            f"📊 Прибыль: {profit:,.0f} ₴\n"
            f"🚀 ROI: {roi:.1f} %"
        )

        st.markdown(
            f"""
<div class='card'>
<b>Результат</b><div class='hr'></div>
{result.replace(chr(10), "<br>")}
</div>
""",
            unsafe_allow_html=True,
        )
        push_history("FIN", "Финансы", result, meta={"area": area, "yield": yield_ha, "price": price, "costs": costs})


def page_history():
    st.markdown("<div class='card'><h3>📒 Журнал</h3><small>История анализов/заметок/финансов</small></div>", unsafe_allow_html=True)

    if not st.session_state.history:
        st.info("История пуста")
        return

    top = st.columns([1, 1, 1])
    with top[0]:
        if st.button("🧹 Очистить историю", use_container_width=True):
            st.session_state.history = []
            st.success("История очищена")
            st.rerun()

    with top[1]:
        txt = export_history_txt()
        st.download_button(
            "⬇️ Экспорт TXT",
            data=txt.encode("utf-8"),
            file_name=f"agroos_history_{time.strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with top[2]:
        st.caption(f"Записей: **{len(st.session_state.history)}**")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    for i, item in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(f"🕒 {item['time']} • {item['kind']} • {item['title']}", expanded=(i <= 2)):
            st.write(item["content"])
            if item.get("meta"):
                st.caption(f"meta: {item['meta']}")


# =========================
# ROUTER
# =========================
page = st.session_state.page

if page == "Главная":
    page_home()
elif page == "🔬 AI Сканер (фото)":
    page_scanner_photo()
elif page == "🧠 Текст-диагноз (через API)":
    page_text_diag_api()
elif page == "💰 Финансы":
    page_finance()
elif page == "📒 Журнал":
    page_history()


# =========================
# FOOTER
# =========================
st.markdown(
    """
<div class="footer">
AGRO AI SYSTEM • 2026 • Streamlit UI + FastAPI Backend
</div>
""",
    unsafe_allow_html=True,
)