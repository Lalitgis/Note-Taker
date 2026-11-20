import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLineEdit, QWidget

from ..store import PAPER_STATUSES
from ..widgets import Page, label, button, Segmented, EmptyState, clear_layout, popup_menu


def open_link(link: str):
    link = link.strip()
    if not link:
        return
    if re.match(r"^10\.\d{4,}/", link):
        link = "https://doi.org/" + link
    url = QUrl(link) if re.match(r"^[a-z]+://", link, re.I) else QUrl.fromLocalFile(link)
    QDesktopServices.openUrl(url)


class PaperRow(QFrame):
    def __init__(self, page, p):
        super().__init__()
        self.page = page
        self.p = p
        self.setObjectName("paperRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 11, 10, 11)
        lay.setSpacing(12)
        icon = {"To read": "▢", "Reading": "◐", "Read": "■"}.get(p["status"], "▢")
        ic = label(icon, "statIcon")
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(label(p["title"], "paperTitle", wrap=True))
        meta = " · ".join(x for x in (p["authors"], str(p["year"] or ""), p["venue"]) if x)
        if meta:
            col.addWidget(label(meta, "muted", wrap=True))
        chips = QHBoxLayout()
        chips.setSpacing(5)
        chips.addWidget(label(p["status"], {"Reading": "chipAccent", "Read": "chip"}.get(p["status"], "chipWarn")))
        for tag in [t.strip() for t in p["tags"].split(",") if t.strip()][:4]:
            chips.addWidget(label("#" + tag, "chip"))
        if p["notes"].strip():
            chips.addWidget(label("≡ notes", "chip"))
        chips.addStretch()
        col.addLayout(chips)
        lay.addLayout(col, 1)
        if p["rating"]:
            lay.addWidget(label("★" * p["rating"], "stars"), 0, Qt.AlignmentFlag.AlignTop)
        if p["link"]:
            lay.addWidget(button("↗", "iconButton", lambda: open_link(p["link"]), "Open link"),
                          0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(button("⋯", "iconButton", self.menu, "More"), 0, Qt.AlignmentFlag.AlignTop)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.page.ctx.edit_paper(self.p["id"])

    def contextMenuEvent(self, e):
        self.menu(e.globalPos())

    def menu(self, pos=None):
        from PySide6.QtGui import QCursor
        s = self.page.ctx.store
        pid = self.p["id"]
        items = [(f"Mark as {st}", (lambda st=st: (s.update_paper(pid, status=st), self.page.ctx.notify())))
                 for st in PAPER_STATUSES if st != self.p["status"]]
        items += [None, ("Add “Read this” task for today", lambda: self.page.make_task(self.p)),
                  ("Edit…", lambda: self.page.ctx.edit_paper(pid))]
        if self.p["link"]:
            items.append(("Open link", lambda: open_link(self.p["link"])))
        popup_menu(items, pos if pos is not None and not isinstance(pos, bool) else QCursor.pos())


class ReadingPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Reading", "Papers, books and anything you mean to read.")
        self.header.addWidget(button("+ Add paper", "primaryButton", lambda: ctx.new_paper()))
        self.filter = "All"

        add = QHBoxLayout()
        self.quick = QLineEdit()
        self.quick.setObjectName("quickAdd")
        self.quick.setPlaceholderText("Quick add: paste a title, DOI (10.xxxx/…) or URL and press Enter")
        self.quick.returnPressed.connect(self.quick_add)
        add.addWidget(self.quick, 1)
        self.outer.addLayout(add)

        bar = QHBoxLayout()
        self.seg = Segmented(["All"] + PAPER_STATUSES, "All")
        self.seg.changed.connect(self._set_filter)
        bar.addWidget(self.seg)
        bar.addStretch()
        self.search = QLineEdit()
        self.search.setObjectName("searchBox")
        self.search.setPlaceholderText("Search title, author, tag…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(220)
        self.search.textChanged.connect(lambda _: self.refresh())
        bar.addWidget(self.search)
        self.outer.addLayout(bar)

        w = QWidget()
        self.list = QVBoxLayout(w)
        self.list.setContentsMargins(0, 0, 0, 0)
        self.list.setSpacing(8)
        self.outer.addWidget(w, 1)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def quick_add(self):
        text = self.quick.text().strip()
        if not text:
            return
        is_link = bool(re.match(r"^(https?://|10\.\d{4,}/|doi:)", text, re.I))
        if text.lower().startswith("doi:"):
            text = text[4:].strip()
        fields = {"link": text} if is_link else {}
        title = "" if is_link else text
        status = self.filter if self.filter in PAPER_STATUSES else "To read"
        p = self.ctx.store.add_paper(title, status=status, **fields)
        self.quick.clear()
        self.ctx.notify()
        if is_link:
            self.ctx.toast("Added. Click it to fill in the title and details.")
        else:
            self.ctx.toast(f"Added “{p['title']}”")

    def make_task(self, p):
        from datetime import date
        self.ctx.store.add_task(f"Read: {p['title']}", category="Reading", my_day=date.today().isoformat())
        if p["status"] == "To read":
            self.ctx.store.update_paper(p["id"], status="Reading")
        self.ctx.notify()
        self.ctx.toast("Added to today's tasks")

    def refresh(self):
        s = self.ctx.store
        counts = s.paper_counts()
        for st in ["All"] + PAPER_STATUSES:
            self.seg.set_label(st, f"{st}  {counts[st]}" if counts[st] else st)
        papers = s.papers(None if self.filter == "All" else self.filter, self.search.text().strip())
        clear_layout(self.list)
        if not papers:
            self.list.addWidget(EmptyState("▤", "Your reading list is empty" if not counts["All"] else "No matches",
                                           "Add papers with the box above. Track what you're reading, rate it and keep notes."))
        for p in papers:
            self.list.addWidget(PaperRow(self, p))
        self.list.addStretch()
        self.subtitle_label.setText(f"{counts['Reading']} in progress · {counts['To read']} to read · {counts['Read']} read")
