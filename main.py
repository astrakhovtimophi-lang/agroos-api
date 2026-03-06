import streamlit as st

# --- PWA (manifest + service worker) ---
st.markdown("""
<link rel="manifest" href="/static/manifest.webmanifest">
<meta name="theme-color" content="#00ff88">
<script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/static/sw.js").catch(()=>{});
    });
  }
</script>
""", unsafe_allow_html=True)

from styles import apply_styles
from i18n import LANGUAGES, INV_LANG, tr, ensure_lang
from settings_store import set_lang

st.set_page_config(page_title="AgroOS", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

apply_styles()
ensure_lang()

with st.sidebar:
    with st.expander("⚙️ " + tr("settings"), expanded=False):
        current_name = INV_LANG.get(st.session_state["lang"], "English")

        lang_name = st.selectbox(
            tr("language"),
            list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index(current_name) if current_name in LANGUAGES else 0,
            key="lang_select_main",
        )

        new_lang = LANGUAGES[lang_name]
        if new_lang != st.session_state["lang"]:
            st.session_state["lang"] = new_lang
            set_lang(new_lang)
            st.rerun()

        st.caption(tr("pages_hint"))

st.markdown(
    '<div class="hero-wrap">'
    '<h1 class="hero-title">' + tr("app_title") + '</h1>'
    '<div class="hero-by">By Astrakhov</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="card"><b>' + tr("home_title") + '</b><br/>' + tr("pages_hint") + '</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">' + tr("by") + '</div>', unsafe_allow_html=True)
