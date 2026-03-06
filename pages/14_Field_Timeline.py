from datetime import date

import pandas as pd
import streamlit as st
from i18n import tr

from agro_utils import add_event, field_names_and_features, load_events, sync_planner_to_events
from styles import apply_styles

apply_styles()

st.title(tr("module_timeline"))
st.caption("History of operations, notes, diagnostics and costs by field.")

if st.button("Sync from Planner/Journal", key="timeline_sync"):
    result = sync_planner_to_events()
    st.success(f"Added from Planner: {result['tasks']} tasks, {result['notes']} journal notes.")

field_names, _ = field_names_and_features()
field_options = ["General"] + field_names

with st.form("timeline_add_event", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        field_name = st.selectbox("Field", field_options, index=0)
    with c2:
        event_type = st.selectbox(
            "Event type",
            [
                "sowing",
                "fertilization",
                "spraying",
                "irrigation",
                "scouting",
                "harvest",
                "diagnostics",
                "note",
            ],
            index=0,
        )
    with c3:
        event_date = st.date_input("Date", value=date.today())

    cost = st.number_input("Cost (UAH)", min_value=0.0, value=0.0, step=100.0)
    note = st.text_area("Note", placeholder="What was done, dose, observations, result...")
    submit = st.form_submit_button("Add event")

if submit:
    add_event(
        field_name=field_name,
        event_type=event_type,
        event_date=event_date.isoformat(),
        cost=cost,
        note=note.strip(),
        source="timeline_page",
    )
    st.success("Event added.")

rows = load_events()
if not rows:
    st.info("No timeline events yet.")
    st.stop()

df = pd.DataFrame(rows)
if "event_date" not in df.columns:
    st.info("No valid timeline entries yet.")
    st.stop()

df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
df = df.dropna(subset=["event_date"])
if df.empty:
    st.info("No valid timeline dates found.")
    st.stop()

flt1, flt2, flt3 = st.columns(3)
with flt1:
    field_filter = st.selectbox("Filter field", ["All"] + sorted(df["field"].fillna("General").astype(str).unique().tolist()))
with flt2:
    event_filter = st.multiselect("Event types", sorted(df["event_type"].fillna("note").astype(str).unique().tolist()))
with flt3:
    d_from, d_to = st.date_input(
        "Period",
        value=(df["event_date"].min().date(), df["event_date"].max().date()),
    )

view = df.copy()
if field_filter != "All":
    view = view[view["field"].astype(str) == field_filter]
if event_filter:
    view = view[view["event_type"].astype(str).isin(event_filter)]
view = view[(view["event_date"].dt.date >= d_from) & (view["event_date"].dt.date <= d_to)]
view = view.sort_values("event_date", ascending=False)

if view.empty:
    st.warning("No events for selected filters.")
    st.stop()

st.subheader("Timeline table")
show_cols = [c for c in ["event_date", "field", "event_type", "cost", "note", "source"] if c in view.columns]
st.dataframe(view[show_cols], use_container_width=True, hide_index=True)

st.subheader("Cost dynamics")
by_day = view.groupby(view["event_date"].dt.date)["cost"].sum().reset_index(name="cost_uah")
by_day = by_day.sort_values("event_date")
st.line_chart(by_day.set_index("event_date"))

st.download_button(
    "Download timeline CSV",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="field_timeline.csv",
    mime="text/csv",
)
