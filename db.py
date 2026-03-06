import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path("data") / "agro.db"

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with _connect() as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            crop TEXT,
            stage TEXT,
            region TEXT,
            weather TEXT,
            symptoms TEXT,
            result TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            due_date TEXT,
            title TEXT NOT NULL,
            field TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            notes TEXT
        )
        """)
        con.commit()

def add_diary(created_at: str, crop: str, stage: str, region: str, weather: str, symptoms: str, result: str):
    with _connect() as con:
        con.execute(
            "INSERT INTO diary(created_at,crop,stage,region,weather,symptoms,result) VALUES(?,?,?,?,?,?,?)",
            (created_at, crop, stage, region, weather, symptoms, result),
        )
        con.commit()

def list_diary(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM diary ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

def add_task(created_at: str, due_date: str, title: str, field: str, notes: str):
    with _connect() as con:
        con.execute(
            "INSERT INTO tasks(created_at,due_date,title,field,status,notes) VALUES(?,?,?,?,?,?)",
            (created_at, due_date, title, field, "todo", notes),
        )
        con.commit()

def list_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _connect() as con:
        con.row_factory = sqlite3.Row
        if status and status != "all":
            rows = con.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY id DESC",
                (status,),
            ).fetchall()
        else:
            rows = con.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

def set_task_status(task_id: int, status: str):
    with _connect() as con:
        con.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
        con.commit()


