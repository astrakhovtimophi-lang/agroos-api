import streamlit as st
from i18n import tr
from styles import apply_styles
import json
from pathlib import Path
from datetime import datetime

apply_styles()
st.title(tr("planner"))

DATA = Path("data")
DATA.mkdir(exist_ok=True)
TASKS_FILE = DATA / "tasks.json"
JOURNAL_FILE = DATA / "journal.json"

def load_json(p):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except:
            return []
    return []

def save_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

tasks = load_json(TASKS_FILE)
journal = load_json(JOURNAL_FILE)

tab1, tab2 = st.tabs(["Tasks", "Journal"])

with tab1:
    st.subheader("Tasks")
    with st.form("add_task", clear_on_submit=True):
        t = st.text_input("Task", placeholder="e.g. spray field #2")
        pr = st.selectbox("Priority", ["Low","Normal","High"], index=1, key="task_pr")
        ok = st.form_submit_button("Add")
    if ok and t.strip():
        tasks.append({"task": t.strip(), "priority": pr, "created": datetime.now().isoformat(timespec="seconds"), "done": False})
        save_json(TASKS_FILE, tasks)

    for i, it in enumerate(tasks):
        cols = st.columns([0.08, 0.72, 0.2])
        done = cols[0].checkbox("", value=it.get("done", False), key=f"done_{i}")
        it["done"] = done
        cols[1].write(f"**{it['task']}**  \n{it['priority']} • {it['created']}")
        if cols[2].button("Delete", key=f"del_{i}"):
            tasks.pop(i)
            save_json(TASKS_FILE, tasks)
            st.rerun()

    save_json(TASKS_FILE, tasks)

with tab2:
    st.subheader("Journal")
    with st.form("add_note", clear_on_submit=True):
        title = st.text_input("Title", placeholder="Field note")
        note = st.text_area("Note")
        ok2 = st.form_submit_button("Save")
    if ok2 and (title.strip() or note.strip()):
        journal.append({"title": title.strip() or "Note", "note": note.strip(), "ts": datetime.now().isoformat(timespec="seconds")})
        save_json(JOURNAL_FILE, journal)

    for j in reversed(journal[-30:]):
        st.markdown(f"**{j['title']}**  \n{j['ts']}")
        st.write(j["note"])
        st.divider()





