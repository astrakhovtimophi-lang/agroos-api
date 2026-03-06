import streamlit as st

st.set_page_config(page_title="AgroOS", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

# --- PWA (manifest + service worker) ---
st.markdown("""
<link rel="manifest" href="/static/manifest.webmanifest">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icon-192.png">
<meta name="theme-color" content="#00ff88">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="AgroOS">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/static/sw.js?v=2").catch(()=>{});
    });
  }
</script>
""", unsafe_allow_html=True)

from styles import apply_styles
from i18n import tr, ensure_lang

apply_styles()
ensure_lang()

st.markdown(
    '<div class="hero-wrap">'
    '<h1 class="hero-title">' + tr("app_title") + '</h1>'
    '<div class="hero-by">By Astrakhov</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="card"><b>' + tr("home_title") + '</b><br/>' + tr("pages_hint") + '</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">' + tr("by") + '</div>', unsafe_allow_html=True)
