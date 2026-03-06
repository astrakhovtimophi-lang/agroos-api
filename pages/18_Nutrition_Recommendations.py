from datetime import date

import pandas as pd
import streamlit as st

from agro_utils import (
    add_event,
    append_nutrition_plan,
    field_names_and_features,
    latest_ndvi_for_field,
    now_iso,
)
from styles import apply_styles

apply_styles()

st.title("🌱 Nutrition Recommendations")
st.caption("NPK plan based on target yield, soil values, NDVI and rainfall forecast.")

field_names, _ = field_names_and_features()
if not field_names:
    field_names = ["General"]

coeffs = {
    "Wheat": {"N": 28.0, "P2O5": 12.0, "K2O": 20.0},
    "Corn": {"N": 24.0, "P2O5": 11.0, "K2O": 26.0},
    "Sunflower": {"N": 35.0, "P2O5": 15.0, "K2O": 55.0},
    "Soy": {"N": 8.0, "P2O5": 15.0, "K2O": 20.0},
}

c1, c2, c3 = st.columns(3)
with c1:
    field_name = st.selectbox("Field", field_names)
with c2:
    crop = st.selectbox("Crop", list(coeffs.keys()), index=0)
with c3:
    plan_date = st.date_input("Plan date", value=date.today())

d1, d2, d3 = st.columns(3)
with d1:
    target_yield = st.number_input("Target yield (t/ha)", min_value=0.5, value=5.0, step=0.1)
with d2:
    rainfall_7d = st.number_input("Rain forecast next 7 days (mm)", min_value=0.0, value=12.0, step=1.0)
with d3:
    ndvi_input_mode = st.selectbox("NDVI source", ["Auto (latest)", "Manual"])

auto_ndvi = latest_ndvi_for_field(field_name)
if ndvi_input_mode == "Auto (latest)":
    ndvi_val = auto_ndvi if auto_ndvi is not None else 0.55
    st.info(f"Using NDVI: {ndvi_val:.3f}" if auto_ndvi is not None else "No NDVI history for this field. Using fallback 0.55")
else:
    ndvi_val = st.number_input("Manual NDVI", min_value=-1.0, max_value=1.0, value=0.55, step=0.01, format="%.2f")

s1, s2, s3 = st.columns(3)
with s1:
    soil_n = st.number_input("Soil N (index)", min_value=0.0, value=40.0, step=1.0)
with s2:
    soil_p = st.number_input("Soil P (index)", min_value=0.0, value=25.0, step=1.0)
with s3:
    soil_k = st.number_input("Soil K (index)", min_value=0.0, value=180.0, step=1.0)

if st.button("Build NPK plan"):
    base = coeffs[crop]

    required_n = target_yield * base["N"]
    required_p = target_yield * base["P2O5"]
    required_k = target_yield * base["K2O"]

    available_n = soil_n * 0.45
    available_p = soil_p * 0.60
    available_k = soil_k * 0.20

    need_n = max(required_n - available_n, 0.0)
    need_p = max(required_p - available_p, 0.0)
    need_k = max(required_k - available_k, 0.0)

    ndvi_factor = 1.0
    if ndvi_val < 0.45:
        ndvi_factor = 1.10
    elif ndvi_val > 0.70:
        ndvi_factor = 0.92

    rain_factor_n = 1.0
    if rainfall_7d > 40:
        rain_factor_n = 1.08
    elif rainfall_7d < 5:
        rain_factor_n = 0.95

    final_n = round(need_n * ndvi_factor * rain_factor_n, 1)
    final_p = round(need_p * ndvi_factor, 1)
    final_k = round(need_k * ndvi_factor, 1)

    stages = [
        ("Pre-sowing", 0.35, 0.55, 0.45),
        ("Vegetative", 0.40, 0.30, 0.35),
        ("Reproductive", 0.25, 0.15, 0.20),
    ]

    plan_rows = []
    for stage, n_share, p_share, k_share in stages:
        plan_rows.append(
            {
                "stage": stage,
                "N_kg_ha": round(final_n * n_share, 1),
                "P2O5_kg_ha": round(final_p * p_share, 1),
                "K2O_kg_ha": round(final_k * k_share, 1),
            }
        )

    df = pd.DataFrame(plan_rows)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total N", f"{final_n:.1f} kg/ha")
    m2.metric("Total P2O5", f"{final_p:.1f} kg/ha")
    m3.metric("Total K2O", f"{final_k:.1f} kg/ha")

    st.subheader("Split plan")
    st.dataframe(df, use_container_width=True, hide_index=True)

    recommendations = []
    if rainfall_7d > 40:
        recommendations.append("High rainfall expected: split N into more applications to reduce leaching risk.")
    if ndvi_val < 0.45:
        recommendations.append("Low NDVI: prioritize quick-response nitrogen source and field scouting.")
    if final_p > 0:
        recommendations.append("Apply phosphorus earlier (pre-sowing/early stage) for root development.")

    if recommendations:
        st.subheader("Recommendations")
        for rec in recommendations:
            st.write(f"- {rec}")

    payload = {
        "created_at": now_iso(),
        "date": plan_date.isoformat(),
        "field": field_name,
        "crop": crop,
        "target_yield": target_yield,
        "ndvi": ndvi_val,
        "rainfall_7d": rainfall_7d,
        "soil": {"N": soil_n, "P": soil_p, "K": soil_k},
        "totals": {"N": final_n, "P2O5": final_p, "K2O": final_k},
        "split_plan": plan_rows,
    }
    append_nutrition_plan(payload)
    add_event(
        field_name=field_name,
        event_type="nutrition_plan",
        event_date=plan_date.isoformat(),
        note=f"NPK plan generated for {crop}: N={final_n}, P2O5={final_p}, K2O={final_k}",
        source="nutrition_page",
    )

    st.download_button(
        "Download plan CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"nutrition_plan_{field_name.replace(' ', '_')}_{plan_date.isoformat()}.csv",
        mime="text/csv",
    )

    st.success("Nutrition plan saved.")
