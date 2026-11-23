#!/usr/bin/env python3
# just a... COLLECTION of apps — a tiny launcher for the "just a..." app family.
#
# Shows a banner header and a row per app. An INSTALLED app's banner launches it
# when clicked, and gets an "Update" button at the right edge of its banner when a
# newer VERSION is published on GitHub. An app that ISN'T installed shows an
# "Install" button that downloads it from the repo and runs its own install.sh —
# installing it on this machine (menu entry, launcher, file type and all).
import os, re, sys, subprocess

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
                                   QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSizePolicy)
    from PySide6.QtGui import QPixmap, QIcon, QCursor
    from PySide6.QtCore import Qt, QUrl, QProcess, QTimer
    from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
except ImportError:
    sys.stderr.write("just a... COLLECTION of apps needs PySide6 (use your distro package):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... COLLECTION of apps"
ORG = "justacollectionofapps"
VERSION = "1.1-00"

HERE = os.path.dirname(os.path.abspath(__file__))
SHARE = os.path.dirname(HERE)            # ~/.local/share
BANNER_IMG = os.path.join(HERE, 'banner.png')

UPDATE_REPO = "janszafranski/just-a-collection-of-apps"
UPDATE_BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/{UPDATE_REPO}/{UPDATE_BRANCH}"
TARBALL = f"https://github.com/{UPDATE_REPO}/archive/refs/heads/{UPDATE_BRANCH}.tar.gz"

# The app family. Each app is a directory under ~/.local/share/<key>/ holding
# <key>.py, with a launcher at ~/.local/bin/<key>. `dir` is the app's folder in
# the repository (holds <key>.py, banner.png and install.sh).
APPS = [
    dict(key='webcreator',  dir='apps/webcreator',  name='just a... WEBcreator',
         desc='Design a website by laying pages out, then publish it as plain HTML.'),
    dict(key='pagecreator', dir='apps/pagecreator', name='just a... PAGEcreator',
         desc='Design print documents page by page, then export them as PDF.'),
    dict(key='paint', dir='apps/paint', name='just a... PAINT',
         desc='Edit and paint images — brush, shapes, fill and text — then save a PNG or JPG.'),
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
    """One app: its banner (click to launch when installed), a short description,
    and an Update or Install button pinned to the top-right of the banner."""
    def __init__(self, win, info, launcher, py_path, banner_path, display_name, desc='', installed=True):
        super().__init__()
        self.win = win
        self.info = info
        self.launcher = launcher
        self.py_path = py_path
        self.banner_path = banner_path
        self.display_name = display_name
        self.installed = installed
        self.setObjectName('approw')

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)
        self._pm = QPixmap(banner_path) if (banner_path and os.path.isfile(banner_path)) else None
        if self._pm is None or self._pm.isNull():
            self._pm = None
            self.logo.setText(display_name)
            self.logo.setStyleSheet('font-size:22px;font-weight:bold;padding:26px;color:#e6e8ea;background:#2b2f36;')
        lay.addWidget(self.logo)

        if not installed:
            self.setStyleSheet('#approw{}')      # dimmed look via opacity on the logo
            self.logo.setStyleSheet(self.logo.styleSheet() + 'opacity:.6;')

        if desc:
            self.caption = QLabel(desc)
            self.caption.setObjectName('appdesc')
            self.caption.setWordWrap(True)
            self.caption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lay.addWidget(self.caption)

        self._wire_launch()

        # Update button (installed apps) — top-right of the banner
        self.update_btn = QPushButton('Update', self)
        self.update_btn.setObjectName('updatebtn')
        self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.do_update)
        self.update_data = None
        self.update_version = None

        # Install button (not-installed apps) — top-right of the banner
        self.install_btn = QPushButton('Install', self)
        self.install_btn.setObjectName('installbtn')
        self.install_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.install_btn.setVisible(not installed)
        self.install_btn.clicked.connect(self.do_install)
        self._proc = None

        if not installed:
            self.win.fetch_banner(self)          # pull the banner from the repo to show it

    def _wire_launch(self):
        hand = self.installed
        self.logo.setCursor(QCursor(Qt.PointingHandCursor if hand else Qt.ArrowCursor))
        self.logo.mousePressEvent = (lambda e: self.launch()) if hand else (lambda e: None)
        if hasattr(self, 'caption'):
            self.caption.setCursor(QCursor(Qt.PointingHandCursor if hand else Qt.ArrowCursor))
            self.caption.mousePressEvent = (lambda e: self.launch()) if hand else (lambda e: None)

    def set_banner_width(self, w):
        self._bw = w
        if self._pm is not None and not self._pm.isNull():
            self.logo.setPixmap(self._pm.scaledToWidth(w, Qt.SmoothTransformation))
        QTimer.singleShot(0, lambda: (self._place_btn(self.update_btn), self._place_btn(self.install_btn)))

    def set_banner_pixmap(self, pm):
        """Called when a not-installed app's banner has been downloaded."""
        if pm is None or pm.isNull():
            return
        self._pm = pm
        self.logo.setText('')
        self.logo.setStyleSheet('opacity:.6;')
        self.set_banner_width(getattr(self, '_bw', self.width() or 320))

    def _place_btn(self, btn):
        if btn.isVisible():
            btn.adjustSize()
            btn.move(self.width() - btn.width() - 12, 12)
            btn.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_btn(self.update_btn)
        self._place_btn(self.install_btn)

    def launch(self):
        if not self.installed:
            return
        started = False
        try:
            subprocess.Popen(['setsid', self.launcher], start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            started = True
        except Exception:
            try:
                started = QProcess.startDetached(self.launcher, [])
            except Exception:
                started = False
        if started:
            QTimer.singleShot(400, QApplication.quit)

    # ---- update (installed apps) ----
    def offer_update(self, version, data):
        self.update_version = version
        self.update_data = data
        self.update_btn.setText(f'Update to {version}')
        self.update_btn.setToolTip(f'Version {version} is available. Click to install.')
        self.update_btn.setVisible(True)
        self._place_btn(self.update_btn)

    def do_update(self):
        if not self.update_data:
            return
        try:
            compile(self.update_data, os.path.basename(self.py_path), 'exec')
        except SyntaxError:
            self.update_btn.setText('Download damaged'); self.update_btn.setEnabled(False); return
        try:
            import shutil
            if os.path.isfile(self.py_path):
                shutil.copy2(self.py_path, self.py_path + '.bak')
            tmp = self.py_path + '.new'
            with open(tmp, 'wb') as fh:
                fh.write(self.update_data)
            os.chmod(tmp, os.stat(self.py_path).st_mode if os.path.isfile(self.py_path) else 0o755)
            os.replace(tmp, self.py_path)
        except OSError as ex:
            self.update_btn.setText("Couldn't update"); self.update_btn.setToolTip(str(ex)); self.update_btn.setEnabled(False); return
        self.update_btn.setText('Updated — relaunch'); self.update_btn.setEnabled(False); self.update_data = None

    # ---- install (not-installed apps) ----
    def do_install(self):
        if self._proc is not None:
            return
        self.install_btn.setEnabled(False); self.install_btn.setText('Installing…'); self._place_btn(self.install_btn)
        appdir = self.info['dir']
        script = (
            'set -e; tmp="$(mktemp -d)"; trap \'rm -rf "$tmp"\' EXIT; '
            f'curl -fsSL "{TARBALL}" | tar -xz -C "$tmp" --strip-components=1; '
            f'bash "$tmp/{appdir}/install.sh"'
        )
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.finished.connect(self._install_done)
        self._proc.errorOccurred.connect(lambda *_: self._install_done(1, None))
        self._proc.start('bash', ['-lc', script])

    def _install_done(self, code, status):
        out = ''
        try:
            out = bytes(self._proc.readAllStandardOutput()).decode(errors='replace') if self._proc else ''
        except Exception:
            pass
        self._proc = None
        if code == 0 and os.path.isfile(self.py_path):
            self.installed = True
            self.install_btn.setVisible(False)
            self.display_name = read_local_app_name(self.py_path) or self.display_name
            if os.path.isfile(self.banner_path):
                self.set_banner_pixmap(QPixmap(self.banner_path))
                self.logo.setStyleSheet('')
            self._wire_launch()
            self.win.check_update(self)
        else:
            self.install_btn.setEnabled(True); self.install_btn.setText('Install failed — retry')
            self.install_btn.setToolTip((out or 'Install did not complete.')[-600:])
            self._place_btn(self.install_btn)


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
        self.BANNER_W = 320

        self.header = QLabel()
        self.header.setAlignment(Qt.AlignCenter)
        self._header_pm = QPixmap(BANNER_IMG) if os.path.isfile(BANNER_IMG) else None
        if self._header_pm is None or self._header_pm.isNull():
            self.header.setText(APP)
            self.header.setStyleSheet('font-size:28px;font-weight:bold;padding:40px;background:#2b2f36;color:#f4f4f4;')
        outer.addWidget(self.header)

        self.rows = []
        self.build_rows()

        self.setStyleSheet('''
            QMainWindow { background: #1c1f24; }
            #approw { background: transparent; }
            #appdesc { color: #c7ccd2; font-size: 12px; padding: 9px 14px 13px 14px; background: #22262c; }
            #updatebtn { padding: 7px 14px; border-radius: 8px; font-weight: 600; font-size: 12px;
                background: #c0392b; color: #ffffff; border: 1px solid rgba(255,255,255,.25); }
            #updatebtn:hover { background: #d9483b; }
            #updatebtn:disabled { background: #8a8f96; color: #e8e8e8; }
            #installbtn { padding: 7px 14px; border-radius: 8px; font-weight: 600; font-size: 12px;
                background: #2a7d6b; color: #ffffff; border: 1px solid rgba(255,255,255,.25); }
            #installbtn:hover { background: #329181; }
            #installbtn:disabled { background: #8a8f96; color: #e8e8e8; }
        ''')

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

        for row in self.rows:
            if row.installed:
                self.check_update(row)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        fg = self.frameGeometry(); fg.moveCenter(screen.center()); self.move(fg.topLeft())

    def showEvent(self, e):
        super().showEvent(e)
        self._center_on_screen()

    def build_rows(self):
        for info in APPS:
            key = info['key']
            app_dir = os.path.join(SHARE, key)
            py_path = os.path.join(app_dir, key + '.py')
            launcher = os.path.join(os.path.expanduser('~/.local/bin'), key)
            banner_path = os.path.join(app_dir, 'banner.png')
            installed = os.path.isfile(py_path)
            name = (read_local_app_name(py_path) if installed else None) or info.get('name') or key
            row = AppRow(self, info, launcher, py_path, banner_path, name, info.get('desc', ''), installed)
            self.outer.addWidget(row)
            self.rows.append(row)

    def fetch_banner(self, row):
        """Download a not-installed app's banner from the repo so its row looks right."""
        url = f"{RAW}/{row.info['dir']}/banner.png"
        req = QNetworkRequest(QUrl(url)); req.setTransferTimeout(20000)
        reply = self.nam.get(req)
        def done():
            try:
                if reply.error() == QNetworkReply.NoError:
                    pm = QPixmap(); pm.loadFromData(bytes(reply.readAll()))
                    row.set_banner_pixmap(pm)
            finally:
                reply.deleteLater()
        reply.finished.connect(done)

    def check_update(self, row):
        path = row.info['dir'] + '/' + row.info['key'] + '.py'
        url = f"{RAW}/{path}"
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.AlwaysNetwork)
        req.setRawHeader(b'Cache-Control', b'no-cache'); req.setTransferTimeout(20000)
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self.update_checked(reply, row))

    def update_checked(self, reply, row):
        try:
            if reply.error() != QNetworkReply.NoError:
                return
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
