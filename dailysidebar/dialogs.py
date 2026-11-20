"""Edit dialogs and the Ctrl+K command palette."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPlainTextEdit, QComboBox,
    QDateEdit, QCheckBox, QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem, QMessageBox,
    QSpinBox, QWidget,
)

from .store import PRIORITIES, REPEATS, PAPER_STATUSES, PROJECT_STATUSES, PROJECT_COLORS
from .widgets import label, button, hbox


class _Base(QDialog):
    def __init__(self, parent, title, width=460):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.setModal(True)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(22, 20, 22, 18)
        self.lay.setSpacing(12)
        self.form = QFormLayout()
        self.form.setSpacing(10)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.deleted = False

    def finish(self, delete_text=None):
        self.lay.addLayout(self.form)
        row = QHBoxLayout()
        if delete_text:
            d = button(delete_text, "dangerButton", self._delete)
            row.addWidget(d)
        row.addStretch()
        row.addWidget(button("Cancel", None, self.reject))
        self.ok = button("Save", "primaryButton", self._save)
        self.ok.setDefault(True)
        row.addWidget(self.ok)
        self.lay.addSpacing(4)
        self.lay.addLayout(row)

    def _delete(self):
        self.deleted = True
        self.accept()

    def _save(self):
        self.accept()

    @staticmethod
    def _date_edit(value: str):
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        chk = QCheckBox()
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("ddd d MMM yyyy")
        if value:
            de.setDate(QDate.fromString(value, "yyyy-MM-dd"))
            chk.setChecked(True)
        else:
            de.setDate(QDate.currentDate())
            de.setEnabled(False)
        chk.toggled.connect(de.setEnabled)
        lay.addWidget(chk)
        lay.addWidget(de, 1)
        quick = QHBoxLayout()
        for text, days in (("Today", 0), ("Tmrw", 1), ("+1w", 7)):
            b = button(text, "ghostButton")
            b.clicked.connect(lambda _=False, d=days: (chk.setChecked(True),
                                                        de.setDate(QDate.currentDate().addDays(d))))
            lay.addWidget(b)
        holder.value = lambda: de.date().toString("yyyy-MM-dd") if chk.isChecked() else ""
        return holder


class TaskDialog(_Base):
    def __init__(self, parent, store, task: dict | None = None, defaults: dict | None = None):
        super().__init__(parent, "Edit task" if task else "New task", 500)
        self.store = store
        t = task or {"title": "", "notes": "", "priority": "Medium", "category": "", "project_id": None,
                     "due": "", "my_day": "", "repeat": ""}
        t = {**t, **(defaults or {})} if not task else t
        self.title = QLineEdit(t["title"])
        self.title.setObjectName("titleEdit")
        self.title.setPlaceholderText("What needs doing?")
        self.lay.addWidget(self.title)

        self.priority = QComboBox()
        self.priority.addItems(PRIORITIES)
        self.priority.setCurrentText(t["priority"])
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems([""] + store.categories())
        self.category.setCurrentText(t["category"] or "")
        self.project = QComboBox()
        self.project.addItem("No project", None)
        for p in store.projects():
            self.project.addItem(p["name"], p["id"])
        idx = self.project.findData(t["project_id"])
        self.project.setCurrentIndex(max(0, idx))
        self.due = self._date_edit(t["due"] or "")
        self.repeat = QComboBox()
        for r in REPEATS:
            self.repeat.addItem(r.capitalize() if r else "Doesn't repeat", r)
        self.repeat.setCurrentIndex(max(0, self.repeat.findData(t["repeat"] or "")))
        self.my_day = QCheckBox("Show in Today even without a due date")
        self.my_day.setChecked(bool(t.get("my_day")))
        self.notes = QPlainTextEdit(t["notes"] or "")
        self.notes.setPlaceholderText("Notes, links, next steps…")
        self.notes.setMinimumHeight(110)

        self.form.addRow("Priority", self.priority)
        self.form.addRow("Category", self.category)
        self.form.addRow("Project", self.project)
        self.form.addRow("Due", self.due)
        self.form.addRow("Repeat", self.repeat)
        self.form.addRow("My Day", self.my_day)
        self.form.addRow("Notes", self.notes)
        self.finish("Delete" if task else None)
        self.title.setFocus()

    def values(self) -> dict:
        return {
            "title": self.title.text(),
            "priority": self.priority.currentText(),
            "category": self.category.currentText().strip(),
            "project_id": self.project.currentData(),
            "due": self.due.value(),
            "repeat": self.repeat.currentData(),
            "my_day": date.today().isoformat() if self.my_day.isChecked() else "",
            "notes": self.notes.toPlainText(),
        }

    def _save(self):
        if not self.title.text().strip():
            self.title.setFocus()
            self.title.setPlaceholderText("A task needs a title")
            return
        self.accept()


class ProjectDialog(_Base):
    def __init__(self, parent, project: dict | None = None):
        super().__init__(parent, "Edit project" if project else "New project")
        p = project or {"name": "", "description": "", "status": "Active", "color": None, "deadline": ""}
        self.name = QLineEdit(p["name"])
        self.name.setObjectName("titleEdit")
        self.name.setPlaceholderText("Project name, e.g. Chapter 2 – GWAS")
        self.lay.addWidget(self.name)
        self.description = QPlainTextEdit(p["description"])
        self.description.setPlaceholderText("Goal, scope, collaborators…")
        self.description.setMaximumHeight(90)
        self.status = QComboBox()
        self.status.addItems(PROJECT_STATUSES)
        self.status.setCurrentText(p["status"])
        self.deadline = self._date_edit(p.get("deadline") or "")
        self.color = p["color"] or PROJECT_COLORS[0]
        sw = QHBoxLayout()
        sw.setSpacing(6)
        self.swatches = []
        for col in PROJECT_COLORS:
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, cc=col: self._pick(cc))
            self.swatches.append((col, b))
            sw.addWidget(b)
        sw.addStretch()
        self._pick(self.color)
        self.form.addRow("Description", self.description)
        self.form.addRow("Status", self.status)
        self.form.addRow("Deadline", self.deadline)
        self.form.addRow("Colour", sw)
        self.finish("Delete project" if project else None)
        self.name.setFocus()

    def _pick(self, col):
        self.color = col
        for cc, b in self.swatches:
            b.setChecked(cc == col)
            border = "3px solid rgba(0,0,0,0.35)" if cc == col else "0"
            b.setStyleSheet(f"background:{cc}; border:{border};")

    def values(self):
        return {"name": self.name.text().strip(), "description": self.description.toPlainText(),
                "status": self.status.currentText(), "color": self.color, "deadline": self.deadline.value() or None}

    def _save(self):
        if not self.name.text().strip():
            self.name.setFocus()
            return
        self.accept()

    def _delete(self):
        if QMessageBox.question(self, "Delete project",
                                "Delete this project? Its tasks are kept and moved to No project.") \
                == QMessageBox.StandardButton.Yes:
            super()._delete()


class PaperDialog(_Base):
    def __init__(self, parent, paper: dict | None = None):
        super().__init__(parent, "Edit paper" if paper else "Add paper", 520)
        p = paper or {"title": "", "authors": "", "year": "", "venue": "", "link": "", "status": "To read",
                      "rating": 0, "tags": "", "notes": ""}
        self.title = QLineEdit(p["title"])
        self.title.setObjectName("titleEdit")
        self.title.setPlaceholderText("Paper or book title")
        self.lay.addWidget(self.title)
        self.authors = QLineEdit(p["authors"])
        self.authors.setPlaceholderText("Smith J, Lee K, …")
        self.year = QLineEdit(str(p["year"] or ""))
        self.year.setMaximumWidth(80)
        self.venue = QLineEdit(p["venue"])
        self.venue.setPlaceholderText("Journal / conference")
        self.link = QLineEdit(p["link"])
        self.link.setPlaceholderText("https://doi.org/… or a file path")
        self.status = QComboBox()
        self.status.addItems(PAPER_STATUSES)
        self.status.setCurrentText(p["status"])
        self.rating = QSpinBox()
        self.rating.setRange(0, 5)
        self.rating.setSuffix(" ★")
        self.rating.setValue(int(p["rating"] or 0))
        self.tags = QLineEdit(p["tags"])
        self.tags.setPlaceholderText("gwas, sorghum, methods")
        self.notes = QPlainTextEdit(p["notes"])
        self.notes.setPlaceholderText("Key findings, methods, how it relates to your work…")
        self.notes.setMinimumHeight(130)
        self.form.addRow("Authors", self.authors)
        self.form.addRow("Year / venue", hbox(self.year, self.venue))
        self.form.addRow("Link / DOI", self.link)
        self.form.addRow("Status", hbox(self.status, label("Rating", "mutedBody"), self.rating, None))
        self.form.addRow("Tags", self.tags)
        self.form.addRow("Notes", self.notes)
        self.finish("Delete" if paper else None)
        self.title.setFocus()

    def values(self):
        return {"title": self.title.text().strip(), "authors": self.authors.text().strip(),
                "year": self.year.text().strip(), "venue": self.venue.text().strip(),
                "link": self.link.text().strip(), "status": self.status.currentText(),
                "rating": self.rating.value(), "tags": self.tags.text().strip(),
                "notes": self.notes.toPlainText()}

    def _save(self):
        if not self.title.text().strip() and not self.link.text().strip():
            self.title.setFocus()
            return
        self.accept()

    def _delete(self):
        if QMessageBox.question(self, "Delete paper", "Remove this paper from your reading list?") \
                == QMessageBox.StandardButton.Yes:
            super()._delete()


class CommandPalette(QDialog):
    """Ctrl+K: jump to pages, run actions, and search everything."""

    def __init__(self, parent, ctx, initial=""):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.ctx = ctx
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        root = QFrame()
        root.setObjectName("paletteRoot")
        outer.addWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(4)
        self.input = QLineEdit(initial)
        self.input.setObjectName("paletteInput")
        self.input.setPlaceholderText("Search tasks, notes, papers… or type a command")
        lay.addWidget(self.input)
        self.list = QListWidget()
        self.list.setObjectName("palette")
        self.list.setMinimumHeight(330)
        lay.addWidget(self.list)
        self.list.setContentsMargins(8, 0, 8, 0)
        hint = label("  ↑↓ to move   ·   Enter to open   ·   Esc to close", "faint")
        lay.addWidget(hint)
        self.input.textChanged.connect(self.populate)
        self.input.returnPressed.connect(self.activate)
        self.list.itemActivated.connect(lambda _: self.activate())
        self.list.itemClicked.connect(lambda _: self.activate())
        self.populate()
        if parent:
            g = parent.geometry()
            self.move(g.x() + (g.width() - 560) // 2, g.y() + 90)
        QTimer.singleShot(0, self.input.setFocus)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            row = self.list.currentRow() + (1 if e.key() == Qt.Key.Key_Down else -1)
            while 0 <= row < self.list.count() and not (self.list.item(row).flags() & Qt.ItemFlag.ItemIsSelectable):
                row += 1 if e.key() == Qt.Key.Key_Down else -1
            if 0 <= row < self.list.count():
                self.list.setCurrentRow(row)
            return
        super().keyPressEvent(e)

    def _header(self, text):
        it = QListWidgetItem(text.upper())
        it.setFlags(Qt.ItemFlag.NoItemFlags)
        f = it.font()
        f.setPointSize(8)
        f.setBold(True)
        it.setFont(f)
        self.list.addItem(it)

    def _item(self, text, action):
        it = QListWidgetItem(text)
        it.setData(Qt.ItemDataRole.UserRole, action)
        self.list.addItem(it)

    def populate(self):
        self.list.clear()
        q = self.input.text().strip()
        ql = q.lower()
        commands = self.ctx.commands()
        matched = [(t, a) for t, a in commands if not ql or ql in t.lower()]
        if q:
            res = self.ctx.store.search_all(q)
            if res.get("tasks"):
                self._header("Tasks")
                for t in res["tasks"]:
                    mark = "✓" if t["done"] else "○"
                    self._item(f"{mark}  {t['title']}", ("task", t["id"]))
            if res.get("projects"):
                self._header("Projects")
                for p in res["projects"]:
                    self._item(f"◇  {p['name']}", ("project", p["id"]))
            if res.get("papers"):
                self._header("Reading")
                for p in res["papers"]:
                    self._item(f"▤  {p['title']}", ("paper", p["id"]))
            if res.get("notes"):
                self._header("Notes")
                for n in res["notes"]:
                    self._item(f"✎  {n['title'] or 'Untitled'}", ("note", n["id"]))
            if res.get("daily"):
                self._header("Daily log")
                for d in res["daily"]:
                    snippet = d["body"].strip().splitlines()[0][:60] if d["body"].strip() else ""
                    self._item(f"▦  {d['day']}  ·  {snippet}", ("daily", d["day"]))
            self._header("Create")
            self._item(f"+  New task “{q}”", ("newtask", q))
        if matched:
            self._header("Commands")
            for t, a in matched:
                self._item(t, ("cmd", a))
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemFlag.ItemIsSelectable:
                self.list.setCurrentRow(i)
                break

    def activate(self):
        it = self.list.currentItem()
        if not it:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self.accept()
        QTimer.singleShot(0, lambda: self.ctx.open_result(*data))
