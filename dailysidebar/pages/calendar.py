import calendar as cal
from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget, QSizePolicy

from ..widgets import Page, label, button, card, TaskList, QuickAdd, clear_layout, ElidedLabel


class DayCell(QFrame):
    def __init__(self, page, day: date, in_month: bool, tasks, has_note: bool, selected: bool):
        super().__init__()
        self.page = page
        self.day = day
        today = date.today()
        if selected:
            name = "calCellSelected"
        elif day == today:
            name = "calCellToday"
        elif not in_month:
            name = "calCellOther"
        else:
            name = "calCell"
        self.setObjectName(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(74)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 5)
        lay.setSpacing(2)
        top = QHBoxLayout()
        dn = label(str(day.day), "calDayToday" if day == today else ("calDay" if in_month else "calDayOther"))
        top.addWidget(dn)
        top.addStretch()
        if has_note:
            n = label("✎", "faint")
            n.setToolTip("Has a daily note")
            top.addWidget(n)
        lay.addLayout(top)
        for t in tasks[:3]:
            nm = "calItemDone" if t["done"] else ("calItemHigh" if t["priority"] == "High" else "calItem")
            it = ElidedLabel(t["title"], nm)
            lay.addWidget(it)
        if len(tasks) > 3:
            lay.addWidget(label(f"+{len(tasks) - 3} more", "faint"))
        lay.addStretch()

    def mouseReleaseEvent(self, e):
        self.page.select(self.day)

    def mouseDoubleClickEvent(self, e):
        self.page.ctx.new_task({"due": self.day.isoformat()})


class CalendarPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Calendar", "Deadlines and daily notes at a glance.")
        today = date.today()
        self.month = date(today.year, today.month, 1)
        self.selected = today

        nav = QHBoxLayout()
        nav.setSpacing(6)
        nav.addWidget(button("‹", "calNav", lambda: self.shift(-1), "Previous month"))
        nav.addWidget(button("Today", None, self.go_today))
        nav.addWidget(button("›", "calNav", lambda: self.shift(1), "Next month"))
        self.header.addLayout(nav)

        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(8)
        self.month_label = label("", "sectionTitle")
        left.addWidget(self.month_label)
        wd = QGridLayout()
        wd.setSpacing(6)
        for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            wd.addWidget(label(name, "weekday"), 0, i)
        left.addLayout(wd)
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        for i in range(7):
            self.grid.setColumnStretch(i, 1)
        self.grid.setContentsMargins(0, 0, 0, 0)
        gw = QWidget()
        gw.setLayout(self.grid)
        left.addWidget(gw, 1)
        left.addWidget(label("Click a day to see it · double-click to add a task due that day", "faint"))

        side, sl = card(margins=(16, 14, 16, 14), spacing=10)
        side.setMinimumWidth(300)
        side.setMaximumWidth(360)
        self.day_title = label("", "sectionTitle")
        self.day_sub = label("", "muted")
        sl.addWidget(self.day_title)
        sl.addWidget(self.day_sub)
        self.quick = QuickAdd(ctx, lambda: {"due": self.selected.isoformat()}, "Add a task for this day…", compact=True)
        sl.addWidget(self.quick)
        self.day_tasks = TaskList(ctx, grouped=False, compact=True)
        sl.addWidget(self.day_tasks)
        sl.addWidget(label("DAILY NOTE", "eyebrow"))
        self.note_preview = label("", "mutedBody", wrap=True)
        self.note_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sl.addWidget(self.note_preview)
        sl.addWidget(button("Open in Notes →", "ghostButton", lambda: ctx.navigate("Notes", day=self.selected.isoformat())))
        sl.addStretch()

        body.addLayout(left, 1)
        body.addWidget(side)
        self.outer.addLayout(body, 1)

    def shift(self, n):
        y, m = self.month.year, self.month.month + n
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        self.month = date(y, m, 1)
        self.refresh()

    def go_today(self):
        t = date.today()
        self.month = date(t.year, t.month, 1)
        self.selected = t
        self.refresh()

    def select(self, day):
        self.selected = day
        if day.month != self.month.month or day.year != self.month.year:
            self.month = date(day.year, day.month, 1)
        self.refresh()

    def refresh(self):
        s = self.ctx.store
        self.month_label.setText(self.month.strftime("%B %Y"))
        weeks = cal.Calendar(firstweekday=0).monthdatescalendar(self.month.year, self.month.month)
        start, end = weeks[0][0], weeks[-1][-1]
        by_day = s.tasks_by_day(start.isoformat(), end.isoformat())
        note_days = s.note_days(start.isoformat(), end.isoformat())
        clear_layout(self.grid)
        for r, week in enumerate(weeks):
            self.grid.setRowStretch(r, 1)
            for c, d in enumerate(week):
                cell = DayCell(self, d, d.month == self.month.month, by_day.get(d.isoformat(), []),
                               d.isoformat() in note_days, d == self.selected)
                self.grid.addWidget(cell, r, c)
        for r in range(len(weeks), 6):
            self.grid.setRowStretch(r, 0)

        d = self.selected
        delta = (d - date.today()).days
        rel = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(delta, "")
        self.day_title.setText(d.strftime("%A, %d %B"))
        self.day_sub.setText((rel + "  ·  " if rel else "") + f"Week {d.isocalendar()[1]}")
        self.day_tasks.set_tasks(s.tasks("day", day=d.isoformat()),
                                 ("", "Nothing due", "Add a task for this day above."))
        note = s.daily_note(d.isoformat()).strip()
        self.note_preview.setText(note[:400] + ("…" if len(note) > 400 else "") if note else "No note for this day.")
