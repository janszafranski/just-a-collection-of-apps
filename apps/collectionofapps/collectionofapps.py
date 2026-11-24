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
                                   QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSizePolicy,
                                   QListWidget, QListWidgetItem, QToolButton)
    from PySide6.QtGui import QPixmap, QIcon, QCursor, QColor, QPainter, QFont
    from PySide6.QtCore import Qt, QUrl, QProcess, QTimer, QSize, QFileSystemWatcher, QSettings
    from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
except ImportError:
    sys.stderr.write("just a... COLLECTION of apps needs PySide6 (use your distro package):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... COLLECTION of apps"
ORG = "justacollectionofapps"
VERSION = "1.2-00"

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
    dict(key='pagecreator', dir='apps/pagecreator', name='just a... PAGEdesigner',
         desc='Design print documents page by page, then export them as PDF.'),
    dict(key='paint', dir='apps/paint', name='just a... PAINTcanvas',
         desc='Edit and paint images — brush, shapes, fill and text — then save a PNG or JPG.'),
    dict(key='draw', dir='apps/draw', name='just a... DRAWmaster',
         desc='Draw with vectors — shapes, lines and paths — and save a scalable SVG.'),
    # add more apps here
]

# ---- the shared "just a..." file world -------------------------------------
HOME = os.path.expanduser('~')
JUST_DOCS = os.path.join(HOME, 'Documents', 'just a...')
JUST_PICS = os.path.join(HOME, 'Pictures', 'just a...')
JUST_DIRS = [JUST_DOCS, JUST_PICS]
RECENTS_FILE = os.path.join(HOME, '.local/share/justapps/recents.json')

# which file extensions belong to which app, and the reverse
APP_EXTS = {'webcreator': ['.webc'], 'pagecreator': ['.pagc'],
            'draw': ['.svg'], 'paint': ['.png', '.jpg', '.jpeg']}
EXT_APP = {e: k for k, exts in APP_EXTS.items() for e in exts}
APP_LABELS = {a['key']: a['name'] for a in APPS}
# badge glyph + colour for non-image files (image files show a real thumbnail)
APP_BADGE = {'webcreator': ('W', '#1f6f63'), 'pagecreator': ('P', '#9e2f2f'),
             'draw': ('D', '#3a6ea5'), 'paint': ('A', '#b5651d')}
IMG_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')


def load_recents():
    import json
    try:
        with open(RECENTS_FILE) as fh:
            data = json.load(fh)
    except Exception:
        return []
    out = []
    for e in data:
        if isinstance(e, dict) and isinstance(e.get('path'), str) and os.path.isfile(e['path']):
            out.append(e)
    return out


def scan_files():
    """Every file in the two 'just a...' folders, newest first: {path, app, mtime}."""
    items = []
    for d in JUST_DIRS:
        if not os.path.isdir(d):
            continue
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            app = EXT_APP.get(os.path.splitext(name)[1].lower())
            if not app:
                continue
            try:
                mt = os.path.getmtime(p)
            except OSError:
                mt = 0
            items.append({'path': p, 'app': app, 'mtime': mt})
    items.sort(key=lambda x: -x['mtime'])
    return items


def _log_recent(appkey, path):
    import json, time
    try:
        d = os.path.dirname(RECENTS_FILE); os.makedirs(d, exist_ok=True)
        try:
            with open(RECENTS_FILE) as fh: data = json.load(fh)
        except Exception: data = []
        data = [e for e in data if isinstance(e, dict) and e.get('path') != path]
        data.insert(0, {'app': appkey, 'path': path, 't': int(time.time())})
        with open(RECENTS_FILE, 'w') as fh: json.dump(data[:50], fh)
    except Exception: pass


def find_importable():
    """Native project files living OUTSIDE the 'just a...' folders — the user's older work.
    Reads WEB/PAGE recent-file settings plus a shallow scan of the usual folders.
    Only DRAWmaster-made SVGs (with the embedded tag) count; foreign SVGs are skipped."""
    found = {}
    for org, appn, key in (('justawebcreator', 'WEBcreator', 'webcreator'),
                           ('justapagecreator', 'PAGEdesigner', 'pagecreator')):
        try:
            r = QSettings(org, appn).value('recent', [], type=list) or []
            for p in r:
                if isinstance(p, str) and os.path.isfile(p): found[p] = key
        except Exception:
            pass
    skip = {'node_modules', '__pycache__', '.git', 'Android', 'Sdk'}
    for dirpath, dirnames, filenames in os.walk(HOME):
        depth = dirpath[len(HOME):].count(os.sep)
        if depth >= 2:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in skip]
        if os.path.abspath(dirpath) in (os.path.abspath(JUST_DOCS), os.path.abspath(JUST_PICS)):
            continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in ('.webc', '.pagc', '.svg'):
                continue
            p = os.path.join(dirpath, fn)
            if p in found:
                continue
            if ext == '.svg':
                try:
                    with open(p, encoding='utf-8', errors='ignore') as fh:
                        if 'justadraw1:' not in fh.read(4000): continue
                except Exception:
                    continue
            found[p] = EXT_APP.get(ext)
    out = []
    for p, app in found.items():
        if os.path.dirname(p) in (JUST_DOCS, JUST_PICS):
            continue
        try: mt = os.path.getmtime(p)
        except OSError: mt = 0
        out.append({'path': p, 'app': app, 'mtime': mt})
    out.sort(key=lambda x: -x['mtime'])
    return out


def make_file_icon(app, path):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMG_EXTS:
        pm = QPixmap(path)
        if not pm.isNull():
            return QIcon(pm.scaled(QSize(44, 44), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    glyph, col = APP_BADGE.get(app, ('•', '#555'))
    pm = QPixmap(44, 44); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen); p.setBrush(QColor(col)); p.drawRoundedRect(3, 3, 38, 38, 9, 9)
    p.setPen(QColor('#ffffff')); f = QFont('Noto Sans'); f.setPixelSize(22); f.setBold(True); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, glyph); p.end()
    return QIcon(pm)


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
        # Single click filters the file pane to this app; double click opens the app.
        self.logo.setCursor(QCursor(Qt.PointingHandCursor))
        self.logo.mousePressEvent = lambda e: self.win.select_app(self)
        self.logo.mouseDoubleClickEvent = lambda e: self.launch()
        if hasattr(self, 'caption'):
            self.caption.setCursor(QCursor(Qt.PointingHandCursor))
            self.caption.mousePressEvent = lambda e: self.win.select_app(self)
            self.caption.mouseDoubleClickEvent = lambda e: self.launch()

    def set_selected(self, on):
        self.setStyleSheet('#approw{background:#283642;}' if on else '#approw{background:transparent;}')

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
        # Open the app fresh (no file). The hub stays open as a launching pad.
        if not self.installed:
            return
        self.win.run_cmd(self.info['key'])

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


class FilePane(QWidget):
    """The right-hand hub: a collapsible Recent list and a full file list for the
    two 'just a...' folders, filtered to the selected app. Open a file to launch it."""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.filter_app = None
        self.setObjectName('filepane')
        v = QVBoxLayout(self); v.setContentsMargins(16, 16, 16, 16); v.setSpacing(8)

        self.title = QLabel('Your files'); self.title.setObjectName('panetitle'); v.addWidget(self.title)
        head = QHBoxLayout()
        self.sub = QLabel('Everything you make with the apps, in one place.')
        self.sub.setObjectName('panesub'); self.sub.setWordWrap(True)
        head.addWidget(self.sub, 1)
        self.import_btn = QPushButton('Import older files…'); self.import_btn.setObjectName('importbtn')
        self.import_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.import_btn.setToolTip('Find projects you saved before, and copy them into your “just a...” folders')
        self.import_btn.clicked.connect(lambda: self.win.import_dialog())
        head.addWidget(self.import_btn, 0, Qt.AlignTop)
        v.addLayout(head)

        self.rec_toggle = QToolButton(); self.rec_toggle.setObjectName('section')
        self.rec_toggle.setText('▾  Recent'); self.rec_toggle.setCheckable(True); self.rec_toggle.setChecked(True)
        self.rec_toggle.setCursor(QCursor(Qt.PointingHandCursor)); self.rec_toggle.clicked.connect(self.toggle_recent)
        v.addWidget(self.rec_toggle)
        self.rec_list = QListWidget(); self.rec_list.setObjectName('filelist'); self.rec_list.setMaximumHeight(200)
        self.rec_list.setIconSize(QSize(44, 44))
        self.rec_list.itemActivated.connect(self.open_item); self.rec_list.itemDoubleClicked.connect(self.open_item)
        v.addWidget(self.rec_list)

        self.files_lbl = QLabel('All files'); self.files_lbl.setObjectName('section'); v.addWidget(self.files_lbl)
        self.files_list = QListWidget(); self.files_list.setObjectName('filelist'); self.files_list.setIconSize(QSize(44, 44))
        self.files_list.itemActivated.connect(self.open_item); self.files_list.itemDoubleClicked.connect(self.open_item)
        v.addWidget(self.files_list, 1)
        self.empty = QLabel(''); self.empty.setObjectName('empty'); self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignCenter); v.addWidget(self.empty, 1)

        self.watcher = QFileSystemWatcher(self)
        for d in JUST_DIRS:
            try: os.makedirs(d, exist_ok=True)
            except OSError: pass
            if os.path.isdir(d): self.watcher.addPath(d)
        self.watcher.directoryChanged.connect(lambda _=None: self.refresh())
        self.refresh()

    def toggle_recent(self):
        on = self.rec_toggle.isChecked()
        self.rec_list.setVisible(on)
        self.rec_toggle.setText(('▾' if on else '▸') + '  Recent')

    def set_filter(self, app_key):
        self.filter_app = app_key
        name = APP_LABELS.get(app_key)
        self.title.setText(name if name else 'Your files')
        self.files_lbl.setText((name + ' files') if name else 'All files')
        self.refresh()

    def _add(self, listw, path, app, mtime=None):
        import time
        it = QListWidgetItem(make_file_icon(app, path), os.path.basename(path))
        folder = os.path.dirname(path).replace(HOME, '~')
        when = ('  ·  ' + time.strftime('%d %b %Y', time.localtime(mtime))) if mtime else ''
        it.setToolTip(f'{path}{when}\nOpens in {APP_LABELS.get(app, app)}')
        it.setData(Qt.UserRole, (app, path))
        listw.addItem(it)

    def refresh(self):
        exts = APP_EXTS.get(self.filter_app)
        self.rec_list.clear()
        for e in load_recents():
            if self.filter_app and e.get('app') != self.filter_app:
                continue
            self._add(self.rec_list, e['path'], e.get('app', ''))
        if self.rec_list.count() == 0:
            it = QListWidgetItem('Nothing opened recently'); it.setFlags(Qt.NoItemFlags); self.rec_list.addItem(it)

        self.files_list.clear(); n = 0
        for f in scan_files():
            if exts and os.path.splitext(f['path'])[1].lower() not in exts:
                continue
            self._add(self.files_list, f['path'], f['app'], f['mtime']); n += 1
        if n == 0:
            self.files_list.hide(); self.empty.show()
            where = APP_LABELS.get(self.filter_app, 'the apps')
            self.empty.setText(f'No files yet.\n\nMake something in {where} and save it —\nit will show up here automatically.')
        else:
            self.empty.hide(); self.files_list.show()

    def open_item(self, it):
        d = it.data(Qt.UserRole)
        if d:
            self.win.launch_file(d[0], d[1])


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP)
        self.nam = QNetworkAccessManager(self)
        self.BANNER_W = 320
        self.selected_key = None

        central = QWidget(); self.setCentralWidget(central)
        body = QHBoxLayout(central); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)

        # LEFT column — the title banner and a scrollable stack of app rows
        self.SBW = 16                                   # room for the vertical scrollbar
        leftw = QWidget(); leftw.setObjectName('leftcol'); leftw.setFixedWidth(self.BANNER_W + self.SBW)
        left = QVBoxLayout(leftw); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(0)
        self.header = QLabel(); self.header.setAlignment(Qt.AlignCenter)
        self._header_pm = QPixmap(BANNER_IMG) if os.path.isfile(BANNER_IMG) else None
        if self._header_pm is None or self._header_pm.isNull():
            self.header.setText(APP)
            self.header.setStyleSheet('font-size:22px;font-weight:bold;padding:30px;background:#2b2f36;color:#f4f4f4;')
        else:
            self.header.setPixmap(self._header_pm.scaledToWidth(self.BANNER_W + self.SBW, Qt.SmoothTransformation))
        left.addWidget(self.header)
        rowholder = QWidget()
        self.rows_layout = QVBoxLayout(rowholder)
        self.rows_layout.setContentsMargins(0, 0, 0, 0); self.rows_layout.setSpacing(0)
        self.rows = []
        self.build_rows()
        self.rows_layout.addStretch(1)
        rowscroll = QScrollArea(); rowscroll.setWidget(rowholder); rowscroll.setWidgetResizable(True)
        rowscroll.setObjectName('rowscroll'); rowscroll.setFrameShape(QFrame.NoFrame)
        rowscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left.addWidget(rowscroll, 1)
        body.addWidget(leftw)

        # RIGHT — the file hub
        self.filepane = FilePane(self)
        body.addWidget(self.filepane, 1)

        self.setStyleSheet('''
            QMainWindow { background: #1c1f24; }
            #leftcol { background: #1c1f24; border-right: 1px solid #2b2f36; }
            #rowscroll { background: transparent; border: none; }
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
            #filepane { background: #191c21; }
            #panetitle { color: #f0f2f4; font-size: 18px; font-weight: 700; }
            #panesub { color: #8b929b; font-size: 12px; }
            QToolButton#section { color: #cfd4da; font-size: 13px; font-weight: 600; border: none;
                padding: 6px 0; text-align: left; }
            QLabel#section { color: #9aa1a9; font-size: 12px; font-weight: 600; padding-top: 4px; }
            #filelist { background: #20242b; border: 1px solid #2c313a; border-radius: 8px;
                color: #dfe3e8; padding: 4px; outline: none; }
            #filelist::item { padding: 7px; border-radius: 6px; }
            #filelist::item:selected { background: #2f6f8f; color: #ffffff; }
            #empty { color: #7a828c; font-size: 13px; }
            #importbtn { background: #2b3a44; color: #cfe3ef; border: 1px solid #3a4a55;
                border-radius: 7px; padding: 5px 10px; font-size: 11px; }
            #importbtn:hover { background: #34454f; }
        ''')

        for row in self.rows:
            row.set_banner_width(self.BANNER_W)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(840, screen.width()), min(780, int(screen.height() * 0.9)))
        self.setMinimumSize(560, 460)
        self._center_on_screen()

        for row in self.rows:
            if row.installed:
                self.check_update(row)

    def select_app(self, row):
        key = row.info['key']
        self.selected_key = None if self.selected_key == key else key
        for r in self.rows:
            r.set_selected(r.info['key'] == self.selected_key)
        self.filepane.set_filter(self.selected_key)

    def run_cmd(self, key, args=None):
        launcher = os.path.join(os.path.expanduser('~/.local/bin'), key)
        args = args or []
        try:
            subprocess.Popen(['setsid', launcher] + args, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try: QProcess.startDetached(launcher, args)
            except Exception: pass

    def launch_file(self, app, path):
        self.run_cmd(app, [path])

    def import_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                                       QListWidgetItem, QPushButton, QLabel, QDialogButtonBox, QMessageBox)
        import shutil
        btn = self.filepane.import_btn
        btn.setText('Searching…'); btn.setEnabled(False); QApplication.processEvents()
        cands = find_importable()
        btn.setText('Import older files…'); btn.setEnabled(True)
        dlg = QDialog(self); dlg.setWindowTitle('Import older files'); dlg.resize(600, 480)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel('Projects found outside your “just a...” folders. Tick the ones to copy in — '
                           'the originals are left exactly where they are.'))
        lw = QListWidget(); lw.setIconSize(QSize(40, 40)); v.addWidget(lw, 1)
        for c in cands:
            it = QListWidgetItem(make_file_icon(c['app'], c['path']),
                                 f"{os.path.basename(c['path'])}      {os.path.dirname(c['path']).replace(HOME, '~')}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Unchecked)
            it.setToolTip(c['path']); it.setData(Qt.UserRole, c); lw.addItem(it)
        if not cands:
            it = QListWidgetItem('Nothing to import — everything is already in place.'); it.setFlags(Qt.NoItemFlags); lw.addItem(it)
        row = QHBoxLayout()
        ball = QPushButton('Select all'); bnone = QPushButton('Select none')
        ball.clicked.connect(lambda: [lw.item(i).setCheckState(Qt.Checked) for i in range(lw.count()) if lw.item(i).data(Qt.UserRole)])
        bnone.clicked.connect(lambda: [lw.item(i).setCheckState(Qt.Unchecked) for i in range(lw.count()) if lw.item(i).data(Qt.UserRole)])
        row.addWidget(ball); row.addWidget(bnone); row.addStretch(1); v.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Copy in')
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        if not dlg.exec():
            return
        n = 0
        for i in range(lw.count()):
            it = lw.item(i); c = it.data(Qt.UserRole)
            if not c or it.checkState() != Qt.Checked:
                continue
            ext = os.path.splitext(c['path'])[1].lower()
            dest_dir = JUST_PICS if ext in IMG_EXTS else JUST_DOCS
            try: os.makedirs(dest_dir, exist_ok=True)
            except OSError: pass
            dest = os.path.join(dest_dir, os.path.basename(c['path']))
            b, e = os.path.splitext(dest); k = 1
            while os.path.exists(dest):
                dest = f'{b} ({k}){e}'; k += 1
            try:
                shutil.copy2(c['path'], dest); _log_recent(c['app'], dest); n += 1
            except Exception:
                pass
        self.filepane.refresh()
        QMessageBox.information(self, APP, f'Copied {n} file(s) into your “just a...” folders.'
                               if n else 'No files were copied.')

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
            self.rows_layout.addWidget(row)
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
