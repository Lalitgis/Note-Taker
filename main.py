"""Daily Sidebar Next: a calm research planner for Windows.

Run:  python main.py            (uses %APPDATA%\\DailySidebarNext\\data.db)
      python main.py D:\\my.db   (use a different data file)
"""
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from dailysidebar import __version__
from dailysidebar.store import Store
from dailysidebar.window import MainWindow, APP_NAME

SERVER_NAME = "DailySidebarNext-single-instance"


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DailySidebar.Next")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("DailySidebar")
    app.setQuitOnLastWindowClosed(False)
    if os.name == "nt":
        app.setFont(QFont("Segoe UI", 10))

    # Only one copy at a time: a second launch just brings the first one forward.
    probe = QLocalSocket()
    probe.connectToServer(SERVER_NAME)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)

    path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    store = Store(path)
    window = MainWindow(store)

    def on_connection():
        sock = server.nextPendingConnection()
        if sock:
            sock.readyRead.connect(lambda: (sock.readAll(), window.show_full()))

    server.newConnection.connect(on_connection)

    if store.get("start_compact"):
        window.compact.show()
    else:
        window.show()
    QTimer.singleShot(400, window.first_run)
    code = app.exec()
    store.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
