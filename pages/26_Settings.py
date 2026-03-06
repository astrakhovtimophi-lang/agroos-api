import streamlit as st

from i18n import render_language_picker, tr
from styles import apply_styles

apply_styles()

st.title("⚙️ " + tr("settings"))
st.caption(tr("settings_page_hint"))

st.subheader(tr("language"))
render_language_picker(widget_key="lang_select_settings_page")
st.info(tr("settings_lang_hint"))
