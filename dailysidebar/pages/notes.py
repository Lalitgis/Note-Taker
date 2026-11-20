from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QMessageBox, QStackedWidget, QWidget)

from ..widgets import Page, label, button

DAILY_TEMPLATE = """Focus for today:
-

Progress / results:
-

Blockers & questions:
-

Ideas:
-

Tomorrow:
-
"""

MEETING_TEMPLATE = """Meeting:
Date: {date}
People:

Agenda:
-

Notes:
-

Action items:
- [ ]
"""


class NotesPage(Page):
    """Left: Daily log + notebook list. Right: an editor that saves as you type."""

    def __init__(self, ctx):
        super().__init__(ctx, "Notes", "A daily research log and a notebook for everything else.")
        self.header.addWidget(button("+ New note", "primaryButton", self.new_note))
        self.day = date.today()
        self.note_id = None
        self.mode = "daily"
        self._loading = False

        body = QHBoxLayout()
        body.setSpacing(16)

        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(250)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(10, 12, 10, 10)
        sl.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("searchBox")
        self.search.setPlaceholderText("Search notes…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self._fill_list())
        sl.addWidget(self.search)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._picked)
        sl.addWidget(self.list, 1)
        body.addWidget(side)

        ed = QFrame()
        ed.setObjectName("card")
        el = QVBoxLayout(ed)
        el.setContentsMargins(26, 18, 26, 16)
        el.setSpacing(8)

        # header row: date navigator (daily) or title (notebook)
        self.head_stack = QStackedWidget()
        self.head_stack.setFixedHeight(46)
        self.head_stack.setStyleSheet("QStackedWidget { background: transparent; }")
        dn = QWidget()
        dl = QHBoxLayout(dn)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.addWidget(button("‹", "calNav", lambda: self.shift(-1), "Previous day"))
        self.day_label = label("", "pageTitle")
        self.day_label.setStyleSheet("font-size: 20px;")
        dl.addWidget(self.day_label)
        dl.addWidget(button("›", "calNav", lambda: self.shift(1), "Next day"))
        dl.addStretch()
        self.today_btn = button("Today", None, self.go_today)
        dl.addWidget(self.today_btn)
        dl.addWidget(button("Insert template", "ghostButton", self.insert_daily_template))
        self.head_stack.addWidget(dn)
        tn = QWidget()
        tl = QHBoxLayout(tn)
        tl.setContentsMargins(0, 0, 0, 0)
        self.title = QLineEdit()
        self.title.setObjectName("titleEdit")
        self.title.setPlaceholderText("Untitled")
        self.title.textChanged.connect(self._changed)
        tl.addWidget(self.title, 1)
        self.pin_btn = button("☆ Pin", "ghostButton", self.toggle_pin)
        tl.addWidget(self.pin_btn)
        tl.addWidget(button("Meeting template", "ghostButton", self.insert_meeting_template))
        tl.addWidget(button("Delete", "dangerButton", self.delete_note))
        self.head_stack.addWidget(tn)
        el.addWidget(self.head_stack)

        self.meta = label("", "faint")
        el.addWidget(self.meta)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("bareEditor")
        self.editor.textChanged.connect(self._changed)
        el.addWidget(self.editor, 1)
        body.addWidget(ed, 1)
        self.outer.addLayout(body, 1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.save)

    # ---- list --------------------------------------------------------------
    def _fill_list(self):
        s = self.ctx.store
        q = self.search.text().strip()
        self.list.blockSignals(True)
        self.list.clear()
        head = QListWidgetItem("DAILY LOG")
        head.setFlags(Qt.ItemFlag.NoItemFlags)
        self.list.addItem(head)
        today = date.today()
        days = []
        if q:
            days = [date.fromisoformat(d["day"]) for d in s.search_daily_notes(q)]
        else:
            start = (today - timedelta(days=30)).isoformat()
            have = sorted(s.note_days(start, today.isoformat()), reverse=True)
            days = [today] + [date.fromisoformat(d) for d in have if d != today.isoformat()][:6]
        for d in days:
            text = "☀  Today" if d == today else "▦  " + d.strftime("%a %d %b")
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, ("daily", d.isoformat()))
            self.list.addItem(it)
            if self.mode == "daily" and d == self.day:
                it.setSelected(True)
        head2 = QListWidgetItem("NOTEBOOK")
        head2.setFlags(Qt.ItemFlag.NoItemFlags)
        self.list.addItem(head2)
        notes = s.notes(q)
        if not notes:
            empty = QListWidgetItem("   No notes yet" if not q else "   No matches")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(empty)
        for n in notes:
            it = QListWidgetItem(("★  " if n["pinned"] else "✎  ") + (n["title"] or "Untitled"))
            it.setData(Qt.ItemDataRole.UserRole, ("note", n["id"]))
            it.setToolTip(f"Edited {n['updated'].replace('T', ' ')[:16]}")
            self.list.addItem(it)
            if self.mode == "note" and n["id"] == self.note_id:
                it.setSelected(True)
        for i in range(self.list.count()):
            it = self.list.item(i)
            if not it.flags() & Qt.ItemFlag.ItemIsSelectable:
                f = it.font()
                if it.text().isupper():
                    f.setPointSize(8)
                    f.setBold(True)
                it.setFont(f)
        self.list.blockSignals(False)

    def _picked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self.save()
        if data[0] == "daily":
            self.open_day(date.fromisoformat(data[1]))
        else:
            self.open_note(data[1])

    # ---- open --------------------------------------------------------------
    def open_day(self, d: date):
        self.save()
        self.mode = "daily"
        self.note_id = None
        self.day = d
        self.head_stack.setCurrentIndex(0)
        self._load()

    def open_note(self, nid):
        self.save()
        self.mode = "note"
        self.note_id = nid
        self.head_stack.setCurrentIndex(1)
        self._load()

    def _load(self):
        s = self.ctx.store
        self._loading = True
        if self.mode == "daily":
            d = self.day
            delta = (d - date.today()).days
            rel = {0: "Today", -1: "Yesterday", 1: "Tomorrow"}.get(delta)
            self.day_label.setText(d.strftime("%A, %d %B %Y"))
            self.meta.setText((rel + "  ·  " if rel else "") + f"Week {d.isocalendar()[1]}  ·  saved automatically")
            self.today_btn.setVisible(delta != 0)
            self.editor.setPlaceholderText("What did you work on? What did you learn? What's next?\n\n"
                                           "Tip: “Insert template” adds a short structure for a research log.")
            self.editor.setPlainText(s.daily_note(d.isoformat()))
        else:
            n = s.note(self.note_id)
            if n is None:
                self._loading = False
                self.open_day(date.today())
                return
            self.title.setText(n["title"])
            self.pin_btn.setText("★ Pinned" if n["pinned"] else "☆ Pin")
            self.meta.setText(f"Created {n['created'][:10]}  ·  edited {n['updated'].replace('T', ' ')[:16]}")
            self.editor.setPlaceholderText("Start writing…")
            self.editor.setPlainText(n["body"])
        self._loading = False
        self._fill_list()

    # ---- editing -----------------------------------------------------------
    def _changed(self, *_):
        if self._loading:
            return
        self.meta.setText("Saving…")
        self.timer.start(600)

    def save(self):
        if not self.timer.isActive() and self.meta.text() != "Saving…":
            return
        self.timer.stop()
        s = self.ctx.store
        if self.mode == "daily":
            s.set_daily_note(self.day.isoformat(), self.editor.toPlainText())
            self.meta.setText(f"Week {self.day.isocalendar()[1]}  ·  saved {datetime.now().strftime('%H:%M')}")
        elif self.note_id is not None and s.note(self.note_id):
            title = self.title.text().strip() or "Untitled"
            old = s.note(self.note_id)["title"]
            s.update_note(self.note_id, title=title, body=self.editor.toPlainText())
            self.meta.setText(f"Saved {datetime.now().strftime('%H:%M')}")
            if old != title:
                self._fill_list()

    def shift(self, n):
        self.open_day(self.day + timedelta(days=n))

    def go_today(self):
        self.open_day(date.today())

    def new_note(self):
        self.save()
        n = self.ctx.store.add_note("")
        self.open_note(n["id"])
        self.title.setFocus()

    def toggle_pin(self):
        n = self.ctx.store.note(self.note_id)
        if n:
            self.ctx.store.update_note(self.note_id, pinned=0 if n["pinned"] else 1)
            self.pin_btn.setText("☆ Pin" if n["pinned"] else "★ Pinned")
            self._fill_list()

    def delete_note(self):
        if self.note_id is None:
            return
        if QMessageBox.question(self, "Delete note", "Delete this note? This can't be undone.") \
                != QMessageBox.StandardButton.Yes:
            return
        self.timer.stop()
        self.ctx.store.delete_note(self.note_id)
        self.meta.setText("")
        self.open_day(date.today())

    def _insert(self, text):
        cur = self.editor.textCursor()
        if self.editor.toPlainText().strip():
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n\n" + text)
        else:
            cur.insertText(text)
        self.editor.setFocus()

    def insert_daily_template(self):
        self._insert(DAILY_TEMPLATE)

    def insert_meeting_template(self):
        self._insert(MEETING_TEMPLATE.format(date=date.today().strftime("%d %B %Y")))

    def refresh(self):
        if not self.editor.hasFocus() and not self.title.hasFocus():
            self._load()

    def hideEvent(self, e):
        self.save()
        super().hideEvent(e)
