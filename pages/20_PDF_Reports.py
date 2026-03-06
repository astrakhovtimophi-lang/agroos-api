import io
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.backends.backend_pdf import PdfPages

from agro_utils import (
    field_names_and_features,
    load_economics,
    load_events,
    load_ndvi_history,
    load_tasks,
    now_iso,
)
from styles import apply_styles

apply_styles()

st.title("📄 PDF Reports")
st.caption("Generate field report for selected period in one click.")

field_names, _ = field_names_and_features()
if not field_names:
    field_names = ["General"]

c1, c2, c3 = st.columns(3)
with c1:
    field_name = st.selectbox("Field", field_names)
with c2:
    date_from = st.date_input("From", value=date.today().replace(day=1))
with c3:
    date_to = st.date_input("To", value=date.today())


def to_date(series):
    return pd.to_datetime(series, errors="coerce").dt.date


all_events = pd.DataFrame(load_events())
all_ndvi = pd.DataFrame(load_ndvi_history())
all_econ = pd.DataFrame(load_economics())
all_tasks = pd.DataFrame(load_tasks())

if not all_events.empty:
    all_events = all_events[all_events["field"].astype(str) == field_name].copy()
    all_events["event_day"] = to_date(all_events["event_date"])
    all_events = all_events[(all_events["event_day"] >= date_from) & (all_events["event_day"] <= date_to)]

if not all_ndvi.empty:
    all_ndvi = all_ndvi[all_ndvi["field"].astype(str) == field_name].copy()
    all_ndvi["day"] = to_date(all_ndvi["date"])
    all_ndvi = all_ndvi[(all_ndvi["day"] >= date_from) & (all_ndvi["day"] <= date_to)]

if not all_econ.empty:
    all_econ = all_econ[all_econ["field"].astype(str) == field_name].copy()
    all_econ["day"] = to_date(all_econ["date"])
    all_econ = all_econ[(all_econ["day"] >= date_from) & (all_econ["day"] <= date_to)]

open_tasks = 0
if not all_tasks.empty and "done" in all_tasks.columns:
    open_tasks = int((~all_tasks["done"].astype(bool)).sum())

summary = {
    "field": field_name,
    "period": f"{date_from.isoformat()} .. {date_to.isoformat()}",
    "events_count": int(len(all_events)) if not all_events.empty else 0,
    "avg_ndvi": float(all_ndvi["ndvi_mean"].mean()) if not all_ndvi.empty else None,
    "latest_ndvi": float(all_ndvi.sort_values("day").iloc[-1]["ndvi_mean"]) if not all_ndvi.empty else None,
    "revenue_uah": float(all_econ["revenue_uah"].sum()) if not all_econ.empty else 0.0,
    "cost_uah": float(all_econ["total_cost_uah"].sum()) if not all_econ.empty else 0.0,
    "margin_uah": float(all_econ["margin_uah"].sum()) if not all_econ.empty else 0.0,
    "open_tasks": open_tasks,
}

avg_ndvi_txt = "-" if summary["avg_ndvi"] is None else f"{summary['avg_ndvi']:.3f}"
latest_ndvi_txt = "-" if summary["latest_ndvi"] is None else f"{summary['latest_ndvi']:.3f}"

st.subheader("Report preview")
preview = pd.DataFrame(
    [
        {"metric": "Events", "value": summary["events_count"]},
        {"metric": "Avg NDVI", "value": avg_ndvi_txt},
        {"metric": "Latest NDVI", "value": latest_ndvi_txt},
        {"metric": "Revenue (UAH)", "value": f"{summary['revenue_uah']:,.0f}"},
        {"metric": "Cost (UAH)", "value": f"{summary['cost_uah']:,.0f}"},
        {"metric": "Margin (UAH)", "value": f"{summary['margin_uah']:,.0f}"},
        {"metric": "Open tasks", "value": summary["open_tasks"]},
    ]
)
st.dataframe(preview, use_container_width=True, hide_index=True)


def build_pdf():
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        ax = fig.add_subplot(111)
        ax.axis("off")

        lines = [
            "AgroOS Field Report",
            "",
            f"Generated: {now_iso()}",
            f"Field: {summary['field']}",
            f"Period: {summary['period']}",
            "",
            f"Events count: {summary['events_count']}",
            f"Average NDVI: {avg_ndvi_txt}",
            f"Latest NDVI: {latest_ndvi_txt}",
            f"Revenue: {summary['revenue_uah']:,.0f} UAH",
            f"Cost: {summary['cost_uah']:,.0f} UAH",
            f"Margin: {summary['margin_uah']:,.0f} UAH",
            f"Open tasks: {summary['open_tasks']}",
        ]
        ax.text(0.05, 0.97, "\n".join(lines), va="top", fontsize=11)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        if not all_ndvi.empty:
            nd = all_ndvi.sort_values("day")
            fig2 = plt.figure(figsize=(10, 4))
            ax2 = fig2.add_subplot(111)
            ax2.plot(pd.to_datetime(nd["day"]), nd["ndvi_mean"], marker="o")
            ax2.set_title("NDVI trend")
            ax2.set_ylabel("NDVI")
            ax2.grid(alpha=0.3)
            pdf.savefig(fig2, bbox_inches="tight")
            plt.close(fig2)

        if not all_econ.empty:
            fig3 = plt.figure(figsize=(10, 4))
            ax3 = fig3.add_subplot(111)
            vals = [summary["revenue_uah"], summary["cost_uah"], summary["margin_uah"]]
            ax3.bar(["Revenue", "Cost", "Margin"], vals)
            ax3.set_title("Economics summary")
            ax3.grid(axis="y", alpha=0.3)
            pdf.savefig(fig3, bbox_inches="tight")
            plt.close(fig3)

        if not all_events.empty:
            fig4 = plt.figure(figsize=(10, 6))
            ax4 = fig4.add_subplot(111)
            ax4.axis("off")
            top_events = all_events.sort_values("event_day", ascending=False).head(15)
            rows = [
                f"{r.get('event_day')} | {r.get('event_type')} | {str(r.get('note') or '')[:90]}"
                for _, r in top_events.iterrows()
            ]
            ax4.text(0.02, 0.98, "Latest events:\n\n" + "\n".join(rows), va="top", fontsize=9)
            pdf.savefig(fig4, bbox_inches="tight")
            plt.close(fig4)

    return buf.getvalue()


if st.button("Generate PDF report"):
    pdf_bytes = build_pdf()
    st.success("Report generated.")
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"agro_report_{field_name.replace(' ', '_')}_{date_from.isoformat()}_{date_to.isoformat()}.pdf",
        mime="application/pdf",
    )
