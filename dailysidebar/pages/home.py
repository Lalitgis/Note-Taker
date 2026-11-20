from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QPlainTextEdit, QGridLayout, QWidget

from ..store import due_info
from ..widgets import (Page, label, button, card, hbox, vbox, TaskList, QuickAdd, ProgressRing,
                       clear_layout, EmptyState)


def greeting(now: datetime) -> str:
    h = now.hour
    if h < 5:
        return "Working late"
    if h < 12:
        return "Good morning"
    if h < 18:
        return "Good afternoon"
    return "Good evening"


class StatCard(QFrame):
    def __init__(self, caption, icon, on_click=None, extra=None):
        super().__init__()
        self.setObjectName("statCard")
        self.on_click = on_click
        if on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.addWidget(label(caption, "muted"))
        top.addStretch()
        top.addWidget(label(icon, "statIcon"))
        lay.addLayout(top)
        self.value = label("0", "statValue")
        self.note = label("", "muted")
        if extra is not None:
            lay.addLayout(hbox(self.value, None, extra))
        else:
            lay.addWidget(self.value)
        lay.addWidget(self.note)

    def set(self, value, note="", alert=False):
        self.value.setText(str(value))
        self.value.setObjectName("statValueAlert" if alert else "statValue")
        self.value.style().unpolish(self.value)
        self.value.style().polish(self.value)
        self.note.setText(note)

    def mouseReleaseEvent(self, e):
        if self.on_click:
            self.on_click()


class HomePage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Good morning", "")
        self.clock = label("", "bigTime")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.header.addWidget(self.clock)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.ring = ProgressRing(ctx, 40, 5)
        self.s_today = StatCard("Today", "◷", lambda: ctx.navigate("Tasks", view="Today"), self.ring)
        self.s_overdue = StatCard("Overdue", "!", lambda: ctx.navigate("Tasks", view="Overdue"))
        self.s_week = StatCard("Due in 7 days", "▦", lambda: ctx.navigate("Tasks", view="Upcoming"))
        self.s_focus = StatCard("Focus this week", "◎", lambda: ctx.navigate("Focus"))
        for i, w in enumerate((self.s_today, self.s_overdue, self.s_week, self.s_focus)):
            stats.addWidget(w, 0, i)
        self.outer.addLayout(stats)

        content = QHBoxLayout()
        content.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(label("Today's plan", "sectionTitle"))
        head.addStretch()
        head.addWidget(button("All tasks →", "ghostButton", lambda: ctx.navigate("Tasks")))
        left.addLayout(head)
        self.quick = QuickAdd(ctx, lambda: {"my_day": date.today().isoformat()})
        left.addWidget(self.quick)
        self.task_list = TaskList(ctx, grouped=True)
        left.addWidget(self.task_list)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(14)

        up, self.up_lay = card()
        uh = QHBoxLayout()
        uh.addWidget(label("Coming up", "cardTitle"))
        uh.addStretch()
        uh.addWidget(button("Calendar →", "ghostButton", lambda: ctx.navigate("Calendar")))
        self.up_lay.addLayout(uh)
        self.up_items = QVBoxLayout()
        self.up_items.setSpacing(8)
        self.up_lay.addLayout(self.up_items)
        right.addWidget(up)

        nt, nl = card()
        nh = QHBoxLayout()
        nh.addWidget(label("Today's note", "cardTitle"))
        nh.addStretch()
        self.saved = label("", "faint")
        nh.addWidget(self.saved)
        nl.addLayout(nh)
        self.note = QPlainTextEdit()
        self.note.setObjectName("bareEditor")
        self.note.setPlaceholderText("Ideas, meeting takeaways, what you learned today…\nSaved automatically.")
        self.note.setMinimumHeight(130)
        self.note.textChanged.connect(self._note_changed)
        nl.addWidget(self.note)
        right.addWidget(nt)
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.timeout.connect(self._save_note)
        self._loading = False

        rd, self.rd_lay = card()
        rh = QHBoxLayout()
        rh.addWidget(label("Currently reading", "cardTitle"))
        rh.addStretch()
        rh.addWidget(button("Reading →", "ghostButton", lambda: ctx.navigate("Reading")))
        self.rd_lay.addLayout(rh)
        self.rd_items = QVBoxLayout()
        self.rd_items.setSpacing(6)
        self.rd_lay.addLayout(self.rd_items)
        right.addWidget(rd)
        right.addStretch()

        lw = QWidget()
        lw.setLayout(left)
        rw = QWidget()
        rw.setLayout(right)
        rw.setMinimumWidth(280)
        rw.setMaximumWidth(400)
        content.addWidget(lw, 3)
        content.addWidget(rw, 2)
        self.outer.addLayout(content, 1)
        self.tick()

    def tick(self):
        now = datetime.now()
        self.clock.setText(now.strftime("%H:%M"))
        self.title_label.setText(f"{greeting(now)}.")
        week = now.isocalendar()[1]
        self.subtitle_label.setText(now.strftime("%A, %d %B %Y") + f"  ·  Week {week}")

    def refresh(self):
        s = self.ctx.store
        today = date.today()
        c = s.counts()
        open_today = c["today"] - c["today_done"]
        self.s_today.set(f"{c['today_done']}/{c['today']}" if c["today"] else "0",
                         "All done, nice work" if c["today"] and not open_today else
                         (f"{open_today} left" if c["today"] else "Nothing planned yet"))
        self.ring.set_value(c["today_done"] / c["today"] if c["today"] else 0)
        self.s_overdue.set(c["overdue"], "Needs attention" if c["overdue"] else "You're on track",
                           alert=c["overdue"] > 0)
        self.s_week.set(c["week"], f"{c['open']} open in total")
        week_start = today - timedelta(days=today.weekday())
        mins = s.focus_minutes(week_start.isoformat(), today.isoformat())
        h, m = divmod(int(mins), 60)
        self.s_focus.set(f"{h}h {m:02d}m" if h else f"{m}m", f"{int(s.focus_minutes(today.isoformat(), today.isoformat()))}m today")

        self.task_list.set_tasks(s.tasks("today"),
                                 ("☀", "A clear day", "Add what you want to get done today above."))

        clear_layout(self.up_items)
        upcoming = [t for t in s.tasks("upcoming") if t["due"] <= (today + timedelta(days=14)).isoformat()][:6]
        if not upcoming:
            self.up_items.addWidget(label("No deadlines in the next two weeks.", "mutedBody", wrap=True))
        for t in upcoming:
            d = date.fromisoformat(t["due"])
            when, tone = due_info(t["due"])
            eyebrow = label(d.strftime("%a %d %b").upper() + ("  ·  " + t["project_name"] if t["project_name"] else ""),
                            "eyebrow")
            eyebrow.setContentsMargins(0, 0, 0, 0)
            eyebrow.setStyleSheet("padding:0;")
            title = label(t["title"], "bodyText", wrap=True)
            title.setCursor(Qt.CursorShape.PointingHandCursor)
            title.mousePressEvent = lambda e, tid=t["id"]: self.ctx.edit_task(tid)
            self.up_items.addLayout(vbox(eyebrow, title, spacing=1))

        if not self.note.hasFocus():
            self._loading = True
            self.note.setPlainText(s.daily_note(today.isoformat()))
            self._loading = False

        clear_layout(self.rd_items)
        reading = s.papers("Reading")[:3] or s.papers("To read")[:2]
        if not reading:
            self.rd_items.addWidget(label("Nothing on your list. Add papers on the Reading page.", "mutedBody", wrap=True))
        for p in reading:
            t = label(p["title"], "bodyText", wrap=True)
            t.setCursor(Qt.CursorShape.PointingHandCursor)
            t.mousePressEvent = lambda e, pid=p["id"]: self.ctx.edit_paper(pid)
            meta = " · ".join(x for x in (p["authors"].split(",")[0].strip(), str(p["year"] or "")) if x)
            self.rd_items.addLayout(vbox(t, label(meta or p["status"], "muted"), spacing=1))

    def _note_changed(self):
        if self._loading:
            return
        self.saved.setText("Saving…")
        self._note_timer.start(700)

    def _save_note(self):
        self.ctx.store.set_daily_note(date.today().isoformat(), self.note.toPlainText())
        self.saved.setText("Saved")

    def focus_quick_add(self):
        self.quick.focus()
