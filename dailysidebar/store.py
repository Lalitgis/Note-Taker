"""Local storage and planning logic for Daily Sidebar Next.

Everything lives in one SQLite file. This module has no Qt imports so it can
be tested on its own.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta

PRIORITIES = ["High", "Medium", "Low"]
DEFAULT_CATEGORIES = [
    "Research", "Reading", "Writing", "Experiments", "Analysis",
    "Meetings", "Teaching", "Admin", "Personal",
]
REPEATS = ["", "daily", "weekdays", "weekly", "monthly"]
PAPER_STATUSES = ["To read", "Reading", "Read"]
PROJECT_STATUSES = ["Active", "On hold", "Done"]
PROJECT_COLORS = ["#527B63", "#4F7CAC", "#8E6BA8", "#C08A3E", "#B85C5C", "#4E9A9A", "#7A7F4A"]

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DEFAULT_SETTINGS = {
    "theme": "system",          # light | dark | system
    "accent": "Sage",
    "focus_minutes": 25,
    "short_break": 5,
    "long_break": 15,
    "sessions_before_long": 4,
    "focus_sound": True,
    "close_to_tray": False,   # off: closing the window quits
    "start_compact": False,
    "compact_on_top": True,
    "compact_opacity": 100,
    "tray_hint_shown": False,
    "imported_v1": False,
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_data_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "DailySidebarNext")
    else:
        folder = os.path.join(os.path.expanduser("~"), ".daily_sidebar_next")
    os.makedirs(folder, exist_ok=True)
    return folder


def v1_data_path() -> str:
    """Where the first Daily Sidebar kept its JSON file."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "DailySidebar", "data.json")
    return os.path.join(os.path.expanduser("~"), ".daily_sidebar", "data.json")


# --------------------------------------------------------------------------
# Dates and quick-add parsing
# --------------------------------------------------------------------------

def parse_date(value: str, today: date | None = None) -> str:
    """Accept '', ISO, d/m/Y, today, tomorrow, tmr, +N, weekday names. Return ISO or ''."""
    today = today or date.today()
    v = (value or "").strip().lower()
    if not v:
        return ""
    if v in ("today", "tod"):
        return today.isoformat()
    if v in ("tomorrow", "tmr", "tmrw"):
        return (today + timedelta(days=1)).isoformat()
    if v in ("nextweek", "next-week"):
        return (today + timedelta(days=7 - today.weekday())).isoformat()
    if re.fullmatch(r"\+\d{1,3}", v):
        return (today + timedelta(days=int(v[1:]))).isoformat()
    if re.fullmatch(r"\+\d{1,2}w", v):
        return (today + timedelta(weeks=int(v[1:-1]))).isoformat()
    full = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if v in WEEKDAYS or v in full:
        idx = WEEKDAYS.index(v[:3])
        ahead = (idx - today.weekday()) % 7 or 7
        return (today + timedelta(days=ahead)).isoformat()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})", v)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        try:
            cand = date(today.year, mo, d)
        except ValueError:
            raise ValueError(f"Can't read date '{value}'")
        if cand < today:
            cand = date(today.year + 1, mo, d)
        return cand.isoformat()
    raise ValueError(f"Can't read date '{value}'. Try 2026-12-01, 01/12, today, tomorrow, +3 or fri.")


def _is_date_token(tok: str) -> bool:
    try:
        return bool(parse_date(tok))
    except ValueError:
        return False


def parse_quick_add(text: str, today: date | None = None) -> dict:
    """Turn 'Read GWAS paper !high #reading @Thesis fri' into task fields.

    !high/!h/!1/!!!  priority     #word  category    @word  project name
    a date word (today, tomorrow, fri, +3, 12/03, 2026-12-01) or due:<date>
    *daily / *weekly / *weekdays / *monthly  repeat
    """
    today = today or date.today()
    result = {"title": "", "priority": "Medium", "category": "", "project": "",
              "due": "", "repeat": ""}
    words = []
    prio_map = {"!h": "High", "!high": "High", "!1": "High", "!!!": "High",
                "!m": "Medium", "!med": "Medium", "!medium": "Medium", "!2": "Medium", "!!": "Medium",
                "!l": "Low", "!low": "Low", "!3": "Low", "!": "Low"}
    for tok in (text or "").split():
        low = tok.lower()
        if low in prio_map:
            result["priority"] = prio_map[low]
        elif tok.startswith("#") and len(tok) > 1:
            result["category"] = tok[1:].replace("_", " ").strip().capitalize()
        elif tok.startswith("@") and len(tok) > 1:
            result["project"] = tok[1:].replace("_", " ")
        elif low.startswith("due:") and len(low) > 4:
            result["due"] = parse_date(low[4:], today)
        elif low.startswith("*") and low[1:] in REPEATS[1:]:
            result["repeat"] = low[1:]
        elif _is_date_token(low) and not result["due"]:
            result["due"] = parse_date(low, today)
        else:
            words.append(tok)
    result["title"] = " ".join(words).strip()
    return result


def next_occurrence(due: str, repeat: str, today: date | None = None) -> str:
    today = today or date.today()
    start = date.fromisoformat(due) if due else today
    if repeat == "daily":
        nxt = start + timedelta(days=1)
    elif repeat == "weekdays":
        nxt = start + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
    elif repeat == "weekly":
        nxt = start + timedelta(days=7)
    elif repeat == "monthly":
        y, m = (start.year + (start.month // 12), start.month % 12 + 1)
        day = min(start.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                              31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
        nxt = date(y, m, day)
    else:
        return ""
    # Don't schedule into the past if the task was finished late.
    while nxt < today and repeat in ("daily", "weekdays"):
        nxt += timedelta(days=1)
        while repeat == "weekdays" and nxt.weekday() >= 5:
            nxt += timedelta(days=1)
    return nxt.isoformat()


def due_info(due: str, done: bool = False, today: date | None = None) -> tuple[str, str]:
    """Return (label, tone) for a due date. tone: danger | warn | muted | ''."""
    if not due:
        return "", ""
    today = today or date.today()
    d = date.fromisoformat(due)
    delta = (d - today).days
    if done:
        return d.strftime("%d %b"), "muted"
    if delta < 0:
        return ("Yesterday" if delta == -1 else f"{-delta} days overdue"), "danger"
    if delta == 0:
        return "Today", "warn"
    if delta == 1:
        return "Tomorrow", "warn"
    if delta < 7:
        return d.strftime("%A"), "muted"
    if d.year == today.year:
        return d.strftime("%d %b"), "muted"
    return d.strftime("%d %b %Y"), "muted"


def group_label(task: dict, today: date | None = None) -> str:
    today = today or date.today()
    if task.get("done"):
        return "Completed"
    due = task.get("due")
    if not due:
        if task.get("my_day") and task["my_day"] <= today.isoformat():
            return "Today"
        return "No date"
    d = date.fromisoformat(due)
    delta = (d - today).days
    if delta < 0:
        return "Overdue"
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta < 7:
        return "This week"
    return "Later"


GROUP_ORDER = ["Overdue", "Today", "Tomorrow", "This week", "Later", "No date", "Completed"]


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#527B63',
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active',
    deadline TEXT,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'Medium',
    category TEXT NOT NULL DEFAULT '',
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    due TEXT,
    my_day TEXT,
    repeat TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL,
    completed TEXT
);
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    year TEXT NOT NULL DEFAULT '',
    venue TEXT NOT NULL DEFAULT '',
    link TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'To read',
    rating INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_notes (
    day TEXT PRIMARY KEY,
    body TEXT NOT NULL DEFAULT '',
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    pinned INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS focus_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    label TEXT NOT NULL DEFAULT '',
    started TEXT NOT NULL,
    minutes REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
"""


class Store:
    def __init__(self, path: str | None = None):
        if path is None:
            path = os.path.join(default_data_dir(), "data.db")
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    def _rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def _one(self, sql, args=()):
        r = self.db.execute(sql, args).fetchone()
        return dict(r) if r else None

    # ---- settings ----------------------------------------------------------
    def get(self, key, default=None):
        r = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if r is None:
            return DEFAULT_SETTINGS.get(key, default) if default is None else default
        try:
            return json.loads(r[0])
        except json.JSONDecodeError:
            return default

    def set(self, key, value):
        self.db.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)))
        self.db.commit()

    # ---- projects ----------------------------------------------------------
    def projects(self, include_done=True) -> list[dict]:
        rows = self._rows("""
            SELECT p.*, COUNT(t.id) AS total, COALESCE(SUM(t.done), 0) AS done_count
            FROM projects p LEFT JOIN tasks t ON t.project_id = p.id
            GROUP BY p.id ORDER BY CASE p.status WHEN 'Active' THEN 0 WHEN 'On hold' THEN 1 ELSE 2 END, p.name COLLATE NOCASE
        """)
        return [r for r in rows if include_done or r["status"] != "Done"]

    def project(self, pid) -> dict | None:
        return self._one("SELECT * FROM projects WHERE id=?", (pid,))

    def project_by_name(self, name: str, create=False) -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        p = self._one("SELECT * FROM projects WHERE lower(name)=lower(?)", (name,))
        if p is None:
            p = self._one("SELECT * FROM projects WHERE lower(name) LIKE lower(?) ORDER BY length(name)",
                          (name + "%",))
        if p is None and create:
            p = self.add_project(name)
        return p

    def add_project(self, name, color=None, description="", status="Active", deadline="") -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Project name is empty")
        if color is None:
            n = self.db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            color = PROJECT_COLORS[n % len(PROJECT_COLORS)]
        cur = self.db.execute(
            "INSERT INTO projects(name, color, description, status, deadline, created) VALUES(?,?,?,?,?,?)",
            (name, color, description, status, deadline or None, now_iso()))
        self.db.commit()
        return self.project(cur.lastrowid)

    def update_project(self, pid, **fields):
        allowed = {"name", "color", "description", "status", "deadline"}
        self._update("projects", pid, fields, allowed)
        return self.project(pid)

    def delete_project(self, pid):
        self.db.execute("UPDATE tasks SET project_id=NULL WHERE project_id=?", (pid,))
        self.db.execute("DELETE FROM projects WHERE id=?", (pid,))
        self.db.commit()

    def _update(self, table, rid, fields, allowed):
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(f"UPDATE {table} SET {cols} WHERE id=?", (*fields.values(), rid))
        self.db.commit()

    # ---- tasks -------------------------------------------------------------
    TASK_SELECT = """
        SELECT t.*, p.name AS project_name, p.color AS project_color
        FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
    """

    @staticmethod
    def _sort_key(t):
        order = {p: i for i, p in enumerate(PRIORITIES)}
        return (t["done"], t["due"] or "9999-99-99", order.get(t["priority"], 9), t["created"])

    def task(self, tid) -> dict | None:
        return self._one(self.TASK_SELECT + " WHERE t.id=?", (tid,))

    def tasks(self, view="all", project_id=None, category=None, search="",
              today: date | None = None, day: str | None = None) -> list[dict]:
        """Views: today, upcoming, overdue, all, open, done, day (needs `day`)."""
        today_s = (today or date.today()).isoformat()
        where, args = [], []
        if view == "today":
            where.append("(t.done=0 AND ((t.due IS NOT NULL AND t.due <= ?) OR (t.my_day IS NOT NULL AND t.my_day <= ?)))"
                         " OR (t.done=1 AND substr(t.completed,1,10)=? AND"
                         " ((t.due IS NOT NULL AND t.due <= ?) OR t.my_day IS NOT NULL))")
            args += [today_s, today_s, today_s, today_s]
        elif view == "upcoming":
            where.append("t.done=0 AND t.due > ?")
            args.append(today_s)
        elif view == "overdue":
            where.append("t.done=0 AND t.due < ?")
            args.append(today_s)
        elif view == "open":
            where.append("t.done=0")
        elif view == "done":
            where.append("t.done=1")
        elif view == "day":
            where.append("(t.due = ? OR (t.due IS NULL AND (t.my_day = ? OR substr(t.completed,1,10) = ?)))")
            args += [day, day, day]
        if project_id is not None:
            where.append("t.project_id=?")
            args.append(project_id)
        if category:
            where.append("t.category=?")
            args.append(category)
        if search:
            where.append("(t.title LIKE ? OR t.notes LIKE ? OR t.category LIKE ?)")
            s = f"%{search}%"
            args += [s, s, s]
        sql = self.TASK_SELECT + (" WHERE " + " AND ".join(f"({w})" for w in where) if where else "")
        rows = self._rows(sql, args)
        if view == "done":
            return sorted(rows, key=lambda t: t["completed"] or "", reverse=True)
        return sorted(rows, key=self._sort_key)

    def counts(self, today: date | None = None) -> dict:
        t = (today or date.today()).isoformat()
        week_end = ((today or date.today()) + timedelta(days=7)).isoformat()
        q = lambda sql, a=(): self.db.execute(sql, a).fetchone()[0]  # noqa: E731
        today_rows = self.tasks("today", today=today)
        return {
            "today": len(today_rows),
            "today_done": sum(1 for r in today_rows if r["done"]),
            "overdue": q("SELECT COUNT(*) FROM tasks WHERE done=0 AND due < ?", (t,)),
            "upcoming": q("SELECT COUNT(*) FROM tasks WHERE done=0 AND due > ?", (t,)),
            "week": q("SELECT COUNT(*) FROM tasks WHERE done=0 AND due >= ? AND due <= ?", (t, week_end)),
            "open": q("SELECT COUNT(*) FROM tasks WHERE done=0"),
            "done": q("SELECT COUNT(*) FROM tasks WHERE done=1"),
            "all": q("SELECT COUNT(*) FROM tasks"),
        }

    def categories(self) -> list[str]:
        used = [r[0] for r in self.db.execute(
            "SELECT DISTINCT category FROM tasks WHERE category != '' ORDER BY category COLLATE NOCASE")]
        out = list(DEFAULT_CATEGORIES)
        out += [c for c in used if c not in out]
        return out

    def add_task(self, title, priority="Medium", category="", project_id=None, due="",
                 my_day="", repeat="", notes="") -> dict:
        title = (title or "").strip()
        if not title:
            raise ValueError("Task title is empty")
        cur = self.db.execute(
            "INSERT INTO tasks(title, notes, priority, category, project_id, due, my_day, repeat, done, created)"
            " VALUES(?,?,?,?,?,?,?,?,0,?)",
            (title, notes, priority if priority in PRIORITIES else "Medium", category or "",
             project_id, due or None, my_day or None, repeat if repeat in REPEATS else "", now_iso()))
        self.db.commit()
        return self.task(cur.lastrowid)

    def quick_add(self, text, defaults: dict | None = None, today: date | None = None) -> dict:
        """Parse text and add a task. `defaults` may hold project_id, due, my_day, category."""
        defaults = defaults or {}
        p = parse_quick_add(text, today)
        if not p["title"]:
            raise ValueError("Task title is empty")
        project_id = defaults.get("project_id")
        if p["project"]:
            proj = self.project_by_name(p["project"], create=True)
            project_id = proj["id"]
        due = p["due"] or defaults.get("due", "")
        my_day = defaults.get("my_day", "") if not p["due"] else ""
        return self.add_task(p["title"], p["priority"], p["category"] or defaults.get("category", ""),
                             project_id, due, my_day, p["repeat"])

    def update_task(self, tid, **fields) -> dict:
        if "title" in fields:
            fields["title"] = (fields["title"] or "").strip()
            if not fields["title"]:
                raise ValueError("Task title is empty")
        for k in ("due", "my_day"):
            if k in fields and not fields[k]:
                fields[k] = None
        allowed = {"title", "notes", "priority", "category", "project_id", "due", "my_day", "repeat"}
        self._update("tasks", tid, fields, allowed)
        return self.task(tid)

    def set_done(self, tid, done: bool, today: date | None = None) -> dict | None:
        """Mark done/undone. Returns the newly created next task for repeating tasks."""
        t = self.task(tid)
        if t is None:
            raise KeyError(tid)
        self.db.execute("UPDATE tasks SET done=?, completed=? WHERE id=?",
                        (1 if done else 0, now_iso() if done else None, tid))
        self.db.commit()
        if done and t["repeat"] and not t["done"]:
            nxt = next_occurrence(t["due"] or (today or date.today()).isoformat(), t["repeat"], today)
            return self.add_task(t["title"], t["priority"], t["category"], t["project_id"], nxt,
                                 "", t["repeat"], t["notes"])
        return None

    def delete_task(self, tid) -> dict:
        row = self._one("SELECT * FROM tasks WHERE id=?", (tid,))
        self.db.execute("DELETE FROM tasks WHERE id=?", (tid,))
        self.db.commit()
        return row

    def restore_task(self, row: dict):
        cols = list(row.keys())
        self.db.execute(f"INSERT INTO tasks({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                        tuple(row.values()))
        self.db.commit()

    def tasks_by_day(self, start: str, end: str) -> dict[str, list[dict]]:
        rows = self._rows(self.TASK_SELECT + " WHERE t.due >= ? AND t.due <= ?", (start, end))
        out: dict[str, list[dict]] = {}
        for r in sorted(rows, key=self._sort_key):
            out.setdefault(r["due"], []).append(r)
        return out

    # ---- papers ------------------------------------------------------------
    def papers(self, status=None, search="") -> list[dict]:
        where, args = [], []
        if status:
            where.append("status=?")
            args.append(status)
        if search:
            s = f"%{search}%"
            where.append("(title LIKE ? OR authors LIKE ? OR tags LIKE ? OR venue LIKE ? OR notes LIKE ?)")
            args += [s] * 5
        sql = "SELECT * FROM papers" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY CASE status WHEN 'Reading' THEN 0 WHEN 'To read' THEN 1 ELSE 2 END, updated DESC"
        return self._rows(sql, args)

    def paper(self, pid):
        return self._one("SELECT * FROM papers WHERE id=?", (pid,))

    def add_paper(self, title, **fields) -> dict:
        title = (title or "").strip()
        link = fields.get("link", "")
        if not title and not link:
            raise ValueError("Paper title is empty")
        if not title:
            title = link
        cur = self.db.execute(
            "INSERT INTO papers(title, authors, year, venue, link, status, rating, tags, notes, created, updated)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (title, fields.get("authors", ""), str(fields.get("year", "") or ""), fields.get("venue", ""),
             link, fields.get("status", "To read"), int(fields.get("rating", 0) or 0),
             fields.get("tags", ""), fields.get("notes", ""), now_iso(), now_iso()))
        self.db.commit()
        return self.paper(cur.lastrowid)

    def update_paper(self, pid, **fields):
        allowed = {"title", "authors", "year", "venue", "link", "status", "rating", "tags", "notes"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        fields["updated"] = now_iso()
        self._update("papers", pid, fields, allowed | {"updated"})
        return self.paper(pid)

    def delete_paper(self, pid):
        self.db.execute("DELETE FROM papers WHERE id=?", (pid,))
        self.db.commit()

    def paper_counts(self) -> dict:
        out = {s: 0 for s in PAPER_STATUSES}
        for s, n in self.db.execute("SELECT status, COUNT(*) FROM papers GROUP BY status"):
            out[s] = n
        out["All"] = sum(out.values())
        return out

    # ---- notes -------------------------------------------------------------
    def daily_note(self, day: str) -> str:
        r = self.db.execute("SELECT body FROM daily_notes WHERE day=?", (day,)).fetchone()
        return r[0] if r else ""

    def set_daily_note(self, day: str, body: str):
        if body.strip():
            self.db.execute("INSERT INTO daily_notes(day, body, updated) VALUES(?,?,?) "
                            "ON CONFLICT(day) DO UPDATE SET body=excluded.body, updated=excluded.updated",
                            (day, body, now_iso()))
        else:
            self.db.execute("DELETE FROM daily_notes WHERE day=?", (day,))
        self.db.commit()

    def note_days(self, start: str, end: str) -> set[str]:
        return {r[0] for r in self.db.execute(
            "SELECT day FROM daily_notes WHERE day >= ? AND day <= ?", (start, end))}

    def notes(self, search="") -> list[dict]:
        if search:
            s = f"%{search}%"
            return self._rows("SELECT * FROM notes WHERE title LIKE ? OR body LIKE ? "
                              "ORDER BY pinned DESC, updated DESC", (s, s))
        return self._rows("SELECT * FROM notes ORDER BY pinned DESC, updated DESC")

    def note(self, nid):
        return self._one("SELECT * FROM notes WHERE id=?", (nid,))

    def add_note(self, title="Untitled", body="") -> dict:
        cur = self.db.execute("INSERT INTO notes(title, body, pinned, created, updated) VALUES(?,?,0,?,?)",
                              (title, body, now_iso(), now_iso()))
        self.db.commit()
        return self.note(cur.lastrowid)

    def update_note(self, nid, **fields):
        fields["updated"] = now_iso()
        self._update("notes", nid, fields, {"title", "body", "pinned", "updated"})

    def delete_note(self, nid):
        self.db.execute("DELETE FROM notes WHERE id=?", (nid,))
        self.db.commit()

    def search_daily_notes(self, search) -> list[dict]:
        return self._rows("SELECT * FROM daily_notes WHERE body LIKE ? ORDER BY day DESC LIMIT 20",
                          (f"%{search}%",))

    # ---- focus -------------------------------------------------------------
    def log_focus(self, minutes: float, task_id=None, label="", started: str | None = None):
        if minutes <= 0:
            return
        self.db.execute("INSERT INTO focus_sessions(task_id, label, started, minutes) VALUES(?,?,?,?)",
                        (task_id, label, started or now_iso(), round(minutes, 2)))
        self.db.commit()

    def focus_minutes(self, start: str, end: str) -> float:
        """Minutes logged between two ISO dates, inclusive."""
        r = self.db.execute("SELECT COALESCE(SUM(minutes),0) FROM focus_sessions "
                            "WHERE substr(started,1,10) >= ? AND substr(started,1,10) <= ?", (start, end))
        return float(r.fetchone()[0])

    def focus_by_day(self, days=7, today: date | None = None) -> list[tuple[str, float]]:
        today = today or date.today()
        out = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            out.append((d, self.focus_minutes(d, d)))
        return out

    def focus_sessions(self, day: str) -> list[dict]:
        return self._rows("""SELECT f.*, t.title AS task_title FROM focus_sessions f
                              LEFT JOIN tasks t ON t.id = f.task_id
                              WHERE substr(f.started,1,10)=? ORDER BY f.started DESC""", (day,))

    # ---- import / export / backup -------------------------------------------
    def import_v1(self, path: str) -> tuple[int, int]:
        """Import tasks and notes from the first Daily Sidebar's data.json.
        Returns (tasks, notes) imported. Reads the file only; never changes it."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        days = (data or {}).get("days", {}) or {}
        n_tasks = n_notes = 0
        existing = {(r["title"].lower(), r["my_day"] or r["due"] or "")
                    for r in self._rows("SELECT title, my_day, due FROM tasks")}
        for day, content in sorted(days.items()):
            for t in content.get("tasks", []):
                title = (t.get("text") or "").strip()
                if not title:
                    continue
                due = t.get("deadline") or ""
                key = (title.lower(), due or day)
                if key in existing:
                    continue
                existing.add(key)
                self.db.execute(
                    "INSERT INTO tasks(title, priority, category, due, my_day, done, created, completed)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (title, t.get("priority") if t.get("priority") in PRIORITIES else "Medium",
                     "" if t.get("category") in (None, "General") else t.get("category"),
                     due or None, None if due else day, 1 if t.get("done") else 0,
                     t.get("created") or f"{day}T09:00:00",
                     t.get("completed") or (f"{day}T18:00:00" if t.get("done") else None)))
                n_tasks += 1
            body = (content.get("notes") or "").strip()
            if body:
                old = self.daily_note(day)
                if body not in old:
                    self.set_daily_note(day, (old + "\n\n" + body).strip() if old else body)
                    n_notes += 1
        self.db.commit()
        return n_tasks, n_notes

    def export_json(self, path: str):
        out = {"app": "Daily Sidebar Next", "exported": now_iso()}
        for table in ("projects", "tasks", "papers", "daily_notes", "notes", "focus_sessions", "settings"):
            out[table] = self._rows(f"SELECT * FROM {table}")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def daily_backup(self, keep=10) -> str | None:
        """Copy the database to backups/ once per day; keep the newest `keep` copies."""
        folder = os.path.join(os.path.dirname(os.path.abspath(self.path)), "backups")
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, f"data-{date.today().isoformat()}.db")
        if os.path.exists(target):
            return None
        dst = sqlite3.connect(target)
        with dst:
            self.db.backup(dst)
        dst.close()
        files = sorted(f for f in os.listdir(folder) if f.startswith("data-") and f.endswith(".db"))
        for old in files[:-keep]:
            try:
                os.remove(os.path.join(folder, old))
            except OSError:
                pass
        return target

    def is_empty(self) -> bool:
        return self.db.execute("SELECT (SELECT COUNT(*) FROM tasks) + (SELECT COUNT(*) FROM daily_notes)").fetchone()[0] == 0

    def search_all(self, text: str, limit=8) -> dict[str, list[dict]]:
        text = text.strip()
        if not text:
            return {}
        return {
            "tasks": self.tasks("all", search=text)[:limit],
            "projects": [p for p in self.projects() if text.lower() in p["name"].lower()][:limit],
            "papers": self.papers(search=text)[:limit],
            "notes": self.notes(search=text)[:limit],
            "daily": self.search_daily_notes(text)[:limit],
        }
