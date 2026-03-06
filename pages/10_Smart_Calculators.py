import streamlit as st
from styles import apply_styles
from i18n import tr, ensure_lang

apply_styles()
ensure_lang()

st.title("🧮 " + (tr("calculators_title") if tr("calculators_title") != "calculators_title" else "Smart Calculators"))
st.caption("ROI / норма высева / баковая смесь + удобрения + конвертеры")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Yield/ROI", "Seeding rate", "Spray mix", "Fertilizer", "Converters"])

with tab1:
    st.subheader("Yield / ROI")
    c1, c2 = st.columns(2)
    with c1:
        area = st.number_input("Area (ha)", min_value=0.0, value=10.0, step=1.0, key="roi_area2")
        yld = st.number_input("Yield (t/ha)", min_value=0.0, value=4.5, step=0.1, key="roi_yld2")
    with c2:
        price = st.number_input("Price (UAH/t)", min_value=0.0, value=6500.0, step=100.0, key="roi_price2")
        cost = st.number_input("Cost (UAH/ha)", min_value=0.0, value=18000.0, step=500.0, key="roi_cost2")

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
    seeds_m2 = st.number_input("Target seeds per m²", min_value=0.0, value=450.0, step=10.0, key="seed_m2_2")
    tkw = st.number_input("TKW (1000 kernel weight, g)", min_value=0.0, value=45.0, step=1.0, key="seed_tkw_2")
    germ = st.number_input("Germination (%)", min_value=1.0, max_value=100.0, value=92.0, step=1.0, key="seed_germ_2")
    rate = (seeds_m2 * tkw * 10) / (germ/100.0) if germ > 0 else 0.0
    st.success(f"Approx seeding rate: {rate:,.1f} kg/ha")

with tab3:
    st.subheader("Spray mix")
    tank = st.number_input("Tank volume (L)", min_value=0.0, value=200.0, step=10.0, key="spr_tank2")
    dose = st.number_input("Product dose (L/ha)", min_value=0.0, value=0.5, step=0.05, key="spr_dose2")
    water = st.number_input("Water rate (L/ha)", min_value=1.0, value=200.0, step=10.0, key="spr_water2")
    ha = tank / water if water > 0 else 0
    product = ha * dose
    st.info(f"Tank covers ~ {ha:,.2f} ha")
    st.success(f"Add product: {product:,.2f} L per tank")

with tab4:
    st.subheader("Fertilizer (N-P-K)")
    st.caption("Вводишь целевые кг/га элементов — получаешь сколько продукта нужно (кг/га).")

    colA, colB = st.columns(2)
    with colA:
        target_n = st.number_input("Target N (kg/ha)", min_value=0.0, value=80.0, step=5.0, key="fert_n")
        target_p2o5 = st.number_input("Target P2O5 (kg/ha)", min_value=0.0, value=40.0, step=5.0, key="fert_p")
        target_k2o = st.number_input("Target K2O (kg/ha)", min_value=0.0, value=40.0, step=5.0, key="fert_k")
    with colB:
        st.markdown("**Choose product**")
        product = st.selectbox("Product", ["Urea (46% N)", "Ammonium nitrate (34% N)", "DAP (18-46-0)", "NPK 16-16-16", "KCl (0-0-60)"], key="fert_prod")

    def calc(product):
        if product == "Urea (46% N)":
            return ("N", target_n / 0.46 if target_n>0 else 0)
        if product == "Ammonium nitrate (34% N)":
            return ("N", target_n / 0.34 if target_n>0 else 0)
        if product == "DAP (18-46-0)":
            # use P2O5 target primarily
            kg = target_p2o5 / 0.46 if target_p2o5>0 else 0
            n_from = kg * 0.18
            return ("P2O5", kg, n_from)
        if product == "NPK 16-16-16":
            # satisfy the max of targets by limiting element
            kg_n = target_n / 0.16 if target_n>0 else 0
            kg_p = target_p2o5 / 0.16 if target_p2o5>0 else 0
            kg_k = target_k2o / 0.16 if target_k2o>0 else 0
            kg = max(kg_n, kg_p, kg_k)
            return ("NPK", kg)
        if product == "KCl (0-0-60)":
            return ("K2O", target_k2o / 0.60 if target_k2o>0 else 0)

    out = calc(product)
    if product == "DAP (18-46-0)":
        st.success(f"Need DAP: {out[1]:,.1f} kg/ha (gives N ≈ {out[2]:,.1f} kg/ha)")
    else:
        st.success(f"Need product: {out[1]:,.1f} kg/ha")

with tab5:
    st.subheader("Converters")
    ha = st.number_input("ha", min_value=0.0, value=10.0, step=1.0, key="conv_ha")
    acres = ha * 2.47105
    st.info(f"{ha:,.2f} ha = {acres:,.2f} acres")

    kg_ha = st.number_input("kg/ha", min_value=0.0, value=200.0, step=10.0, key="conv_kg_ha")
    lb_acre = kg_ha * 0.892179
    st.info(f"{kg_ha:,.1f} kg/ha ≈ {lb_acre:,.1f} lb/acre")



