import pandas as pd
import streamlit as st

from agro_utils import (
    load_compliance,
    load_crop_plan,
    load_operations,
    load_scouting,
    load_warehouse_transactions,
)
from styles import apply_styles

apply_styles()

st.title("🏠 AgroOS Command Home")
st.caption("Daily workflow hub for field monitoring, planning and execution.")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Crop plans", len(load_crop_plan()))
c2.metric("Operations", len(load_operations()))
c3.metric("Scouting", len(load_scouting()))
c4.metric("Compliance checks", len(load_compliance()))
c5.metric("Warehouse tx", len(load_warehouse_transactions()))

st.subheader("Recommended daily workflow")
steps = pd.DataFrame(
    [
        {"Step": "1", "Open module": "NDVI Pro", "Goal": "Check stress zones and vegetation changes"},
        {"Step": "2", "Open module": "AI Agro Assistant", "Goal": "Get action plan from field context"},
        {"Step": "3", "Open module": "Operations Center / Scouting", "Goal": "Assign field checks and tasks"},
        {"Step": "4", "Open module": "Operations Center / Operations", "Goal": "Plan and record treatments/works"},
        {"Step": "5", "Open module": "Operations Center / Compliance", "Goal": "Validate pesticide safety constraints"},
        {"Step": "6", "Open module": "Field Economics + PDF Reports", "Goal": "Track ROI and send report"},
    ]
)
st.dataframe(steps, use_container_width=True, hide_index=True)

st.subheader("Where to find key functions")
map_df = pd.DataFrame(
    [
        {"Need": "Satellite indices, cloud-resilient maps", "Module": "02_NDVI_Auto"},
        {"Need": "VRA zones export", "Module": "04_Zones_Field"},
        {"Need": "Time-series NDVI alerts", "Module": "16_NDVI_Trends_Alerts"},
        {"Need": "Operations, machinery, warehouse, scouting, compliance", "Module": "22_Farm_Operations_Center"},
        {"Need": "Expert agronomy decisions", "Module": "21_AI_Agro_Assistant"},
        {"Need": "Financial control", "Module": "17_Field_Economics"},
        {"Need": "Management report", "Module": "20_PDF_Reports"},
    ]
)
st.dataframe(map_df, use_container_width=True, hide_index=True)

