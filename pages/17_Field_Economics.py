from datetime import date

import pandas as pd
import streamlit as st

from agro_utils import add_economic_record, add_event, field_names_and_features, load_economics, load_events
from styles import apply_styles

apply_styles()

st.title("💹 Field Economics")
st.caption("Cost, margin and ROI by field and crop.")

field_names, _ = field_names_and_features()
if not field_names:
    field_names = ["General"]

with st.form("econ_add", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        rec_date = st.date_input("Date", value=date.today())
    with c2:
        field_name = st.selectbox("Field", field_names)
    with c3:
        crop = st.text_input("Crop", value="Wheat")

    a1, a2, a3 = st.columns(3)
    with a1:
        area_ha = st.number_input("Area (ha)", min_value=0.1, value=10.0, step=0.1)
    with a2:
        yield_t_ha = st.number_input("Yield (t/ha)", min_value=0.0, value=4.5, step=0.1)
    with a3:
        price_uah_t = st.number_input("Price (UAH/t)", min_value=0.0, value=6500.0, step=100.0)

    b1, b2 = st.columns(2)
    with b1:
        variable_cost_uah_ha = st.number_input("Variable cost (UAH/ha)", min_value=0.0, value=16000.0, step=500.0)
    with b2:
        fixed_cost_uah_ha = st.number_input("Fixed cost (UAH/ha)", min_value=0.0, value=2000.0, step=100.0)

    include_timeline_costs = st.checkbox("Include timeline costs for this field", value=True)

    timeline_cost = 0.0
    if include_timeline_costs:
        for e in load_events():
            if str(e.get("field")) == str(field_name):
                try:
                    timeline_cost += float(e.get("cost") or 0.0)
                except Exception:
                    pass

    revenue = area_ha * yield_t_ha * price_uah_t
    total_cost = area_ha * (variable_cost_uah_ha + fixed_cost_uah_ha) + timeline_cost
    margin = revenue - total_cost
    roi = (margin / total_cost * 100.0) if total_cost > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"{revenue:,.0f} UAH")
    c2.metric("Total cost", f"{total_cost:,.0f} UAH")
    c3.metric("Margin", f"{margin:,.0f} UAH")
    c4.metric("ROI", f"{roi:,.1f}%")

    submit = st.form_submit_button("Save economics record")

if submit:
    payload = {
        "date": rec_date.isoformat(),
        "field": field_name,
        "crop": crop.strip() or "Unknown",
        "area_ha": area_ha,
        "yield_t_ha": yield_t_ha,
        "price_uah_t": price_uah_t,
        "variable_cost_uah_ha": variable_cost_uah_ha,
        "fixed_cost_uah_ha": fixed_cost_uah_ha,
        "timeline_cost_uah": timeline_cost,
        "revenue_uah": revenue,
        "total_cost_uah": total_cost,
        "margin_uah": margin,
        "roi_pct": roi,
    }
    add_economic_record(payload)
    add_event(
        field_name=field_name,
        event_type="economics",
        event_date=rec_date.isoformat(),
        note=f"Economics saved: margin {margin:,.0f} UAH, ROI {roi:.1f}%",
        cost=total_cost,
        source="economics_page",
    )
    st.success("Economics record saved.")

rows = load_economics()
if not rows:
    st.info("No economics data yet.")
    st.stop()

df = pd.DataFrame(rows)
st.subheader("Economics records")
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Summary by field")
summary_field = (
    df.groupby("field", as_index=False)
    .agg(
        revenue_uah=("revenue_uah", "sum"),
        total_cost_uah=("total_cost_uah", "sum"),
        margin_uah=("margin_uah", "sum"),
    )
)
summary_field["roi_pct"] = summary_field.apply(
    lambda r: (r["margin_uah"] / r["total_cost_uah"] * 100.0) if r["total_cost_uah"] > 0 else 0.0,
    axis=1,
)
st.dataframe(summary_field, use_container_width=True, hide_index=True)

st.bar_chart(summary_field.set_index("field")["margin_uah"])

st.download_button(
    "Download economics CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="economics_records.csv",
    mime="text/csv",
)
