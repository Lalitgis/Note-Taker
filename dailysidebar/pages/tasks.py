from datetime import date

from PySide6.QtWidgets import QHBoxLayout, QComboBox, QLineEdit

from ..widgets import Page, Segmented, TaskList, QuickAdd, button, label

VIEWS = ["Today", "Upcoming", "Overdue", "All open", "Done"]
VIEW_KEYS = {"Today": "today", "Upcoming": "upcoming", "Overdue": "overdue", "All open": "open", "Done": "done"}
EMPTY = {
    "Today": ("☀", "Nothing planned for today", "Add a task above, or give tasks a due date of today."),
    "Upcoming": ("▦", "No upcoming deadlines", "Tasks with a future due date show up here."),
    "Overdue": ("✓", "Nothing overdue", "You're on top of things."),
    "All open": ("✦", "No open tasks", "Add your first task above."),
    "Done": ("○", "Nothing completed yet", "Finished tasks are collected here."),
}


class TasksPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Tasks", "Everything on your plate, grouped by when it's due.")
        self.header.addWidget(button("+ New task", "primaryButton", lambda: ctx.new_task()))
        self.view = "Today"

        self.quick = QuickAdd(ctx, self._defaults)
        self.outer.addWidget(self.quick)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.seg = Segmented(VIEWS, self.view)
        self.seg.changed.connect(self._set_view)
        bar.addWidget(self.seg)
        bar.addStretch()
        self.category = QComboBox()
        self.category.setMinimumWidth(130)
        self.category.currentIndexChanged.connect(lambda _: self.refresh())
        self.project = QComboBox()
        self.project.setMinimumWidth(130)
        self.project.currentIndexChanged.connect(lambda _: self.refresh())
        self.search = QLineEdit()
        self.search.setObjectName("searchBox")
        self.search.setPlaceholderText("Filter…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(170)
        self.search.textChanged.connect(lambda _: self.refresh())
        bar.addWidget(self.category)
        bar.addWidget(self.project)
        bar.addWidget(self.search)
        self.outer.addLayout(bar)

        self.list = TaskList(ctx, grouped=True)
        self.outer.addWidget(self.list, 1)
        self._filling = False

    def _defaults(self):
        d = {}
        if self.view == "Today":
            d["my_day"] = date.today().isoformat()
        if self.project.currentData():
            d["project_id"] = self.project.currentData()
        if self.category.currentData():
            d["category"] = self.category.currentData()
        return d

    def _set_view(self, v):
        self.view = v
        self.refresh()

    def set_view(self, v):
        if v in VIEWS:
            self.seg.set_current(v)
            self.view = v

    def _fill_filters(self):
        self._filling = True
        s = self.ctx.store
        cur_c, cur_p = self.category.currentData(), self.project.currentData()
        self.category.blockSignals(True)
        self.project.blockSignals(True)
        self.category.clear()
        self.category.addItem("All categories", None)
        for c in s.categories():
            self.category.addItem("#" + c, c)
        self.category.setCurrentIndex(max(0, self.category.findData(cur_c)))
        self.project.clear()
        self.project.addItem("All projects", None)
        for p in s.projects():
            self.project.addItem(p["name"], p["id"])
        self.project.setCurrentIndex(max(0, self.project.findData(cur_p)))
        self.category.blockSignals(False)
        self.project.blockSignals(False)
        self._filling = False

    def refresh(self):
        if self._filling:
            return
        s = self.ctx.store
        if not self.category.count():
            self._fill_filters()
        c = s.counts()
        self.seg.set_label("Today", f"Today  {c['today'] - c['today_done']}" if c["today"] else "Today")
        self.seg.set_label("Upcoming", f"Upcoming  {c['upcoming']}" if c["upcoming"] else "Upcoming")
        self.seg.set_label("Overdue", f"Overdue  {c['overdue']}" if c["overdue"] else "Overdue")
        self.seg.set_label("All open", f"All open  {c['open']}" if c["open"] else "All open")
        tasks = s.tasks(VIEW_KEYS[self.view], project_id=self.project.currentData(),
                        category=self.category.currentData(), search=self.search.text().strip())
        grouped = self.view != "Done"
        self.list.grouped = grouped
        self.list.set_tasks(tasks, EMPTY[self.view], done_collapsible=self.view != "Today")
        n = len([t for t in tasks if not t["done"]])
        self.subtitle_label.setText(
            f"{n} open task{'s' if n != 1 else ''} in this view." if self.view != "Done"
            else f"{len(tasks)} completed.")

    def showEvent(self, e):
        self._fill_filters()
        super().showEvent(e)

    def focus_quick_add(self):
        self.quick.focus()
