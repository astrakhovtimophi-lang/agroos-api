import streamlit as st

from agro_assistant import (
    CROP_OPTIONS,
    STAGE_OPTIONS,
    append_assistant_history,
    build_field_context,
    generate_expert_response,
)
from agro_utils import add_event, field_names_and_features, now_iso
from styles import apply_styles

apply_styles()

st.title("🤖 AI Agro Assistant")
st.caption("Expert assistant for crop decisions: NDVI, nutrition, disease, weather, economics, and operations.")

names, _ = field_names_and_features()
field_pick = st.selectbox("Field", ["No field"] + names, index=0)
crop_pick = st.selectbox("Crop", CROP_OPTIONS, index=0)
stage_pick = st.selectbox("Stage", STAGE_OPTIONS, index=2)
mode_pick = st.selectbox("Response mode", ["Fast", "Expert", "Deep"], index=1)

c1, c2 = st.columns(2)
with c1:
    include_weather = st.checkbox("Include weather risks", value=True)
with c2:
    save_to_timeline = st.checkbox("Save each advice to timeline", value=True)

if st.button("Show context snapshot"):
    ctx = build_field_context(field_pick, include_weather=include_weather)
    st.json(ctx)

if "agro_assistant_chat" not in st.session_state:
    st.session_state["agro_assistant_chat"] = [
        {
            "role": "assistant",
            "content": "Ready. Ask about your field, symptoms, NDVI, nutrition, ROI or weather risks.",
        }
    ]

h1, h2 = st.columns([0.7, 0.3])
with h2:
    if st.button("Clear chat"):
        st.session_state["agro_assistant_chat"] = [
            {
                "role": "assistant",
                "content": "Chat cleared. Ask new question.",
            }
        ]
        st.rerun()

for msg in st.session_state["agro_assistant_chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

quick_cols = st.columns(3)
if quick_cols[0].button("NDVI dropped, what to do?"):
    st.session_state["agro_assistant_quick"] = "NDVI dropped over last week, what should I do first?"
if quick_cols[1].button("Symptoms on leaves"):
    st.session_state["agro_assistant_quick"] = "Yellow leaves and spots after rain. What are likely causes and actions?"
if quick_cols[2].button("How to improve ROI"):
    st.session_state["agro_assistant_quick"] = "How can I improve ROI this season without over-spending?"

prefill = st.session_state.pop("agro_assistant_quick", "")
if prefill:
    st.info(f"Quick prompt selected: {prefill}")

question = st.chat_input("Ask the agro assistant...")
if question is None and prefill:
    question = prefill

if question:
    st.session_state["agro_assistant_chat"].append({"role": "user", "content": question})

    with st.spinner("Assistant is preparing expert recommendation..."):
        result = generate_expert_response(
            question=question,
            field_name=field_pick,
            crop=crop_pick,
            stage=stage_pick,
            mode=mode_pick,
            include_weather=include_weather,
        )

    answer = result["answer"]
    st.session_state["agro_assistant_chat"].append({"role": "assistant", "content": answer})

    record = {
        "created_at": now_iso(),
        "field": None if field_pick == "No field" else field_pick,
        "crop": crop_pick,
        "stage": stage_pick,
        "mode": mode_pick,
        "question": question,
        "answer": answer,
        "intents": result.get("intents", []),
        "context": result.get("context", {}),
    }
    append_assistant_history(record)

    if save_to_timeline:
        event_field = "General" if field_pick == "No field" else field_pick
        brief = answer.split("\n", 1)[0]
        add_event(
            field_name=event_field,
            event_type="assistant_advice",
            event_date=now_iso()[:10],
            note=f"Q: {question[:160]} | A: {brief[:220]}",
            source="ai_agro_assistant",
            meta={"mode": mode_pick, "intents": result.get("intents", [])},
        )

    st.rerun()
