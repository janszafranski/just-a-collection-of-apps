#!/usr/bin/env python3
# just a... COLLECTION of apps — a tiny launcher for the "just a..." app family.
#
# Shows a banner header and a list of the installed apps. Each row is the
# app's own banner, which launches it when clicked. On startup the launcher
# checks each app's update source (the same GitHub raw file the app itself
# updates from) and, if a newer VERSION is published, drops an "Update" button
# on the end of that app's row.
import os, re, sys, subprocess

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
                                   QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSizePolicy)
    from PySide6.QtGui import QPixmap, QIcon, QCursor
    from PySide6.QtCore import Qt, QUrl, QProcess
    from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
except ImportError:
    sys.stderr.write("just a... COLLECTION of apps needs PySide6 (use your distro package):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... COLLECTION of apps"
ORG = "justacollectionofapps"
VERSION = "1.0-00"

HERE = os.path.dirname(os.path.abspath(__file__))
SHARE = os.path.dirname(HERE)            # ~/.local/share
BANNER_IMG = os.path.join(HERE, 'banner.png')

UPDATE_REPO = "janszafranski/just-a-collection-of-apps"
UPDATE_BRANCH = "main"

# The app family. Each app is a directory under ~/.local/share/<key>/ holding
# <key>.py, with a launcher at ~/.local/bin/<key>. update_path is that app's
# real file in the repository (NOT whatever the app's own — possibly wrong —
# UPDATE_PATH constant says), so the check is correct even before an app's
# self-update path is fixed.
APPS = [
    dict(key='webcreator',  update_path='apps/webcreator/webcreator.py'),
    dict(key='pagecreator', update_path='apps/pagecreator/pagecreator.py'),
    # add more apps here
]


def read_local_version(py_path):
    try:
        with open(py_path, 'r', encoding='utf-8', errors='replace') as fh:
            head = fh.read(8000)
        m = re.search(r'^VERSION = "([^"]+)"', head, re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def read_local_app_name(py_path):
    try:
        with open(py_path, 'r', encoding='utf-8', errors='replace') as fh:
            head = fh.read(8000)
        m = re.search(r'^APP = "([^"]+)"', head, re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def ver_tuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', v or '')[:4])


class AppRow(QFrame):
    """One app in the list: its banner (click to launch) + an update slot."""
    def __init__(self, info, launcher, py_path, banner_path, display_name):
        super().__init__()
        self.info = info
        self.launcher = launcher
        self.py_path = py_path
        self.display_name = display_name
        self.setObjectName('approw')
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # The banner fills the whole row edge-to-edge (no margins). The Update
        # button floats on top of it (top-right) so there's never a white gutter.
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)
        if banner_path and os.path.isfile(banner_path):
            self._pm = QPixmap(banner_path)
        else:
            self._pm = None
            self.logo.setText(display_name)
            self.logo.setStyleSheet('font-size:22px;font-weight:bold;padding:18px;')
        self.logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.logo.mousePressEvent = lambda e: self.launch()
        lay.addWidget(self.logo)

        # update button is a child of the row, positioned manually over the banner
        self.update_btn = QPushButton('Update', self)
        self.update_btn.setObjectName('updatebtn')
        self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.do_update)

        self.update_data = None
        self.update_version = None

    def set_banner_width(self, w):
        if self._pm is not None and not self._pm.isNull():
            self.logo.setPixmap(self._pm.scaledToWidth(w, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # keep the Update button pinned to the top-right corner of the banner
        if self.update_btn.isVisible():
            self.update_btn.adjustSize()
            self.update_btn.move(self.width() - self.update_btn.width() - 12, 12)

    def launch(self):
        try:
            QProcess.startDetached(self.launcher, [])
        except Exception:
            try:
                subprocess.Popen([self.launcher])
            except Exception:
                pass

    def offer_update(self, version, data):
        self.update_version = version
        self.update_data = data
        self.update_btn.setText(f'Update to {version}')
        self.update_btn.setToolTip(f'Version {version} is available. Click to install.')
        self.update_btn.setVisible(True)
        self.update_btn.raise_()
        self.update_btn.adjustSize()
        self.update_btn.move(self.width() - self.update_btn.width() - 12, 12)

    def do_update(self):
        if not self.update_data:
            return
        # sanity: the download must compile and name the app
        try:
            compile(self.update_data, os.path.basename(self.py_path), 'exec')
        except SyntaxError:
            self.update_btn.setText('Download damaged')
            self.update_btn.setEnabled(False)
            return
        try:
            import shutil
            if os.path.isfile(self.py_path):
                shutil.copy2(self.py_path, self.py_path + '.bak')
            tmp = self.py_path + '.new'
            with open(tmp, 'wb') as fh:
                fh.write(self.update_data)
            if os.path.isfile(self.py_path):
                os.chmod(tmp, os.stat(self.py_path).st_mode)
            else:
                os.chmod(tmp, 0o755)
            os.replace(tmp, self.py_path)
        except OSError as ex:
            self.update_btn.setText("Couldn't update")
            self.update_btn.setToolTip(str(ex))
            self.update_btn.setEnabled(False)
            return
        self.update_btn.setText('Updated — relaunch')
        self.update_btn.setEnabled(False)
        self.update_data = None


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.nam = QNetworkAccessManager(self)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.outer = outer

        # Every banner is the same width and fills the window edge-to-edge:
        # no margins, no spacing, no white borders anywhere.
        self.BANNER_W = 320

        # banner header
        self.header = QLabel()
        self.header.setAlignment(Qt.AlignCenter)
        self._header_pm = QPixmap(BANNER_IMG) if os.path.isfile(BANNER_IMG) else None
        if self._header_pm is None or self._header_pm.isNull():
            self.header.setText(APP)
            self.header.setStyleSheet('font-size:28px;font-weight:bold;padding:40px;'
                                      'background:#2b2f36;color:#f4f4f4;')
        outer.addWidget(self.header)

        # app rows, stacked directly under the header — no scroll frame, no margins
        self.rows = []
        self.build_rows()

        self.setStyleSheet('''
            QMainWindow { background: #1c1f24; }
            #approw { background: transparent; }
            #updatebtn {
                padding: 7px 14px; border-radius: 8px; font-weight: 600; font-size: 12px;
                background: #c0392b; color: #ffffff; border: 1px solid rgba(255,255,255,.25);
            }
            #updatebtn:hover { background: #d9483b; }
            #updatebtn:disabled { background: #8a8f96; color: #e8e8e8; }
        ''')

        # Width = banner width; all banners scaled to fill it. Nothing wider, no gutter.
        win_w = self.BANNER_W
        self.setFixedWidth(win_w)
        if self._header_pm is not None and not self._header_pm.isNull():
            self.header.setPixmap(self._header_pm.scaledToWidth(win_w, Qt.SmoothTransformation))
        for row in self.rows:
            row.set_banner_width(win_w)
        central.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        win_h = min(central.sizeHint().height(), int(screen.height() * 0.9))
        self.resize(win_w, win_h)
        self._center_on_screen()

        # kick off update checks after the window is up
        for row in self.rows:
            self.check_update(row)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        fg = self.frameGeometry()
        fg.moveCenter(screen.center())
        self.move(fg.topLeft())

    def showEvent(self, e):
        super().showEvent(e)
        # re-centre once the real frame size is known (WM may adjust it)
        self._center_on_screen()

    def build_rows(self):
        for info in APPS:
            key = info['key']
            app_dir = os.path.join(SHARE, key)
            py_path = os.path.join(app_dir, key + '.py')
            launcher = os.path.join(os.path.expanduser('~/.local/bin'), key)
            banner_path = os.path.join(app_dir, 'banner.png')
            if not os.path.isfile(py_path):
                continue  # app not installed
            name = read_local_app_name(py_path) or key
            row = AppRow(info, launcher, py_path, banner_path, name)
            self.outer.addWidget(row)
            self.rows.append(row)

    def check_update(self, row):
        path = row.info['update_path']
        url = f'https://raw.githubusercontent.com/{UPDATE_REPO}/{UPDATE_BRANCH}/{path}'
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.AlwaysNetwork)
        req.setRawHeader(b'Cache-Control', b'no-cache')
        req.setTransferTimeout(20000)
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self.update_checked(reply, row))

    def update_checked(self, reply, row):
        try:
            if reply.error() != QNetworkReply.NoError:
                return                      # offline / not published: no button, no fuss
            data = bytes(reply.readAll())
        finally:
            reply.deleteLater()
        m = re.search(rb'^VERSION = "([^"]+)"', data, re.M)
        if not m:
            return
        remote = m.group(1).decode()
        local = read_local_version(row.py_path)
        if local is None:
            return
        if ver_tuple(remote) > ver_tuple(local):
            row.offer_update(remote, data)


def main():
    QApplication.setDesktopFileName('collectionofapps')
    app = QApplication(sys.argv)
    app.setApplicationName('COLLECTIONofApps')
    app.setApplicationDisplayName(APP)
    app.setOrganizationName(ORG)
    app.setApplicationVersion(VERSION)
    w = Launcher()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
