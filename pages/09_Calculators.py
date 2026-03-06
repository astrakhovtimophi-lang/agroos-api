import streamlit as st
from i18n import tr
from styles import apply_styles

apply_styles()
st.title(tr("calculators"))

tab1, tab2, tab3 = st.tabs(["Yield/ROI", "Seeding rate", "Spray mix"])

with tab1:
    st.subheader("Yield / ROI")
    c1, c2 = st.columns(2)
    with c1:
        area = st.number_input("Area (ha)", min_value=0.0, value=10.0, step=1.0, key="roi_area")
        yld = st.number_input("Yield (t/ha)", min_value=0.0, value=4.5, step=0.1, key="roi_yld")
    with c2:
        price = st.number_input("Price (UAH/t)", min_value=0.0, value=6500.0, step=100.0, key="roi_price")
        cost = st.number_input("Cost (UAH/ha)", min_value=0.0, value=18000.0, step=500.0, key="roi_cost")

    total_t = area * yld
    revenue = total_t * price
    total_cost = area * cost
    profit = revenue - total_cost
    roi = (profit / total_cost * 100.0) if total_cost > 0 else 0.0

    a,b,c,d = st.columns(4)
    a.metric("Total yield", f"{total_t:,.2f} t")
    b.metric("Revenue", f"{revenue:,.0f} UAH")
    c.metric("Cost", f"{total_cost:,.0f} UAH")
    d.metric("ROI", f"{roi:,.1f}%")

with tab2:
    st.subheader("Seeding rate")
    seeds_m2 = st.number_input("Target plants (seeds) per m²", min_value=0.0, value=450.0, step=10.0, key="seed_m2")
    tkw = st.number_input("TKW (1000 kernel weight, g)", min_value=0.0, value=45.0, step=1.0, key="seed_tkw")
    germ = st.number_input("Germination (%)", min_value=1.0, max_value=100.0, value=92.0, step=1.0, key="seed_germ")
    rate = (seeds_m2 * tkw * 10) / (germ/100.0)  # rough kg/ha
    st.success(f"Approx seeding rate: {rate:,.1f} kg/ha")

with tab3:
    st.subheader("Spray mix")
    tank = st.number_input("Tank volume (L)", min_value=0.0, value=200.0, step=10.0, key="spr_tank")
    dose = st.number_input("Product dose (L/ha)", min_value=0.0, value=0.5, step=0.05, key="spr_dose")
    water = st.number_input("Water rate (L/ha)", min_value=1.0, value=200.0, step=10.0, key="spr_water")
    ha = tank / water if water > 0 else 0
    product = ha * dose
    st.info(f"Tank covers ~ {ha:,.2f} ha")
    st.success(f"Add product: {product:,.2f} L per tank")





