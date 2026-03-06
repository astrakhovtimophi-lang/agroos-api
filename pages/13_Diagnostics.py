import streamlit as st
from i18n import tr
from styles import apply_styles
import sys
import os
import importlib

apply_styles()
st.title(tr("diagnostics"))

st.write("Python:", sys.version)
st.write("Working dir:", os.getcwd())

pkgs = ["streamlit","numpy","pillow","matplotlib","pandas","folium","streamlit_folium","pystac_client","shapely","pyproj","rasterio"]
ok = True
for p in pkgs:
    try:
        importlib.import_module(p)
        st.success(f"OK: {p}")
    except Exception as e:
        ok = False
        st.error(f"FAIL: {p} -> {e}")

if ok:
    st.success("All core packages are installed.")
else:
    st.warning("Some packages missing. Run: pip install -r requirements.txt")





