from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QProgressBar, QStackedWidget,
                               QWidget)

from ..store import due_info
from ..widgets import Page, label, button, TaskList, QuickAdd, EmptyState, clear_layout, Segmented


class ProjectCard(QFrame):
    def __init__(self, page, p):
        super().__init__()
        self.page = page
        self.p = p
        self.setObjectName("projectCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(156)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 14)
        lay.setSpacing(8)
        inner = QVBoxLayout()
        inner.setContentsMargins(16, 0, 16, 0)
        bar = QFrame()
        bar.setFixedSize(28, 5)
        bar.setStyleSheet(f"background:{p['color']}; border-radius:2px;")
        inner.addWidget(bar)
        inner.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(label(p["name"], "cardTitle", wrap=True), 1)
        st = {"Active": "chipAccent", "On hold": "chipWarn", "Done": "chip"}[p["status"]] \
            if p["status"] in ("Active", "On hold", "Done") else "chip"
        top.addWidget(label(p["status"], st), 0, Qt.AlignmentFlag.AlignTop)
        inner.addLayout(top)
        desc = p["description"].strip().splitlines()[0] if p["description"].strip() else "No description"
        inner.addWidget(label(desc[:120], "muted", wrap=True))
        inner.addStretch()
        total, done = p["total"], p["done_count"]
        pb = QProgressBar()
        pb.setRange(0, max(1, total))
        pb.setValue(done)
        pb.setTextVisible(False)
        pb.setStyleSheet(f"QProgressBar::chunk {{ background: {p['color']}; border-radius: 3px; }}")
        inner.addWidget(pb)
        foot = QHBoxLayout()
        foot.addWidget(label(f"{done} of {total} tasks done" if total else "No tasks yet", "muted"))
        foot.addStretch()
        if p.get("deadline"):
            text, tone = due_info(p["deadline"])
            foot.addWidget(label("◷ " + text, {"danger": "chipDanger", "warn": "chipWarn"}.get(tone, "chip")))
        inner.addLayout(foot)
        lay.addLayout(inner)

    def mouseReleaseEvent(self, e):
        self.page.open_project(self.p["id"])


class ProjectsPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Projects", "Keep research and professional work together.")
        self.new_btn = button("+ New project", "primaryButton", self.new_project)
        self.header.addWidget(self.new_btn)
        self.current = None
        self.filter = "Active"

        self.stack = QStackedWidget()
        self.outer.addWidget(self.stack, 1)

        # overview
        ov = QWidget()
        ol = QVBoxLayout(ov)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(12)
        self.seg = Segmented(["Active", "On hold", "Done", "All"], "Active")
        self.seg.changed.connect(self._set_filter)
        ol.addWidget(self.seg)
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        ol.addLayout(self.grid)
        ol.addStretch()
        self.stack.addWidget(ov)

        # detail
        dv = QWidget()
        dl = QVBoxLayout(dv)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(button("← All projects", "ghostButton", self.back))
        top.addStretch()
        top.addWidget(button("Edit project", None, self.edit_project))
        dl.addLayout(top)
        self.d_title = label("", "sectionTitle")
        self.d_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.d_desc = label("", "mutedBody", wrap=True)
        self.d_progress = QProgressBar()
        self.d_progress.setTextVisible(False)
        self.d_meta = label("", "muted")
        dl.addWidget(self.d_title)
        dl.addWidget(self.d_desc)
        dl.addWidget(self.d_progress)
        dl.addWidget(self.d_meta)
        self.quick = QuickAdd(ctx, lambda: {"project_id": self.current}, "Add a task to this project…")
        dl.addWidget(self.quick)
        self.d_tasks = TaskList(ctx, grouped=True, show_project=False)
        dl.addWidget(self.d_tasks)
        dl.addStretch()
        self.stack.addWidget(dv)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def new_project(self):
        pid = self.ctx.new_project()
        if pid:
            self.open_project(pid)

    def edit_project(self):
        if self.current and self.ctx.edit_project(self.current) == "deleted":
            self.back()

    def open_project(self, pid):
        self.current = pid
        self.stack.setCurrentIndex(1)
        self.refresh()

    def back(self):
        self.current = None
        self.stack.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        s = self.ctx.store
        if self.current is not None and s.project(self.current) is None:
            self.current = None
            self.stack.setCurrentIndex(0)
        if self.current is None:
            clear_layout(self.grid)
            projects = [p for p in s.projects() if self.filter == "All" or p["status"] == self.filter]
            if not projects:
                self.grid.addWidget(EmptyState("◇", "No projects here",
                                               "Projects group related tasks, like a thesis chapter, a paper or a grant."),
                                    0, 0, 1, 3)
            cols = 3
            for i, p in enumerate(projects):
                self.grid.addWidget(ProjectCard(self, p), i // cols, i % cols)
            for c in range(cols):
                self.grid.setColumnStretch(c, 1)
            return
        p = next(x for x in s.projects() if x["id"] == self.current)
        self.d_title.setText(f"<span style='color:{p['color']}'>●</span>  {p['name']}")
        self.d_desc.setText(p["description"] or "No description yet.")
        self.d_progress.setRange(0, max(1, p["total"]))
        self.d_progress.setValue(p["done_count"])
        self.d_progress.setStyleSheet(f"QProgressBar::chunk {{ background: {p['color']}; border-radius: 3px; }}")
        meta = f"{p['status']}  ·  {p['done_count']} of {p['total']} tasks done"
        if p.get("deadline"):
            meta += f"  ·  deadline {date.fromisoformat(p['deadline']).strftime('%d %b %Y')}"
        self.d_meta.setText(meta)
        self.d_tasks.set_tasks(s.tasks("all", project_id=self.current),
                               ("◇", "No tasks yet", "Break the project into small steps above."))
