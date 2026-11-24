#!/usr/bin/env python3
# just a... PAINTcanvas — a tiny raster (bitmap) image editor: paint, erase, draw shapes,
# fill, pick colours, add text, and save a PNG/JPG. The photo-editing companion to
# just a... PAGEcreator / WEBcreator (and the vector sibling of just a... DRAW).
import sys, os

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QColorDialog,
                                   QFileDialog, QMessageBox, QSpinBox, QLabel, QInputDialog,
                                   QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QCursor, QFont, QPainterPath, QActionGroup)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings
except ImportError:
    sys.stderr.write("just a... PAINTcanvas needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... PAINTcanvas"
ORG = "justapaint"
VERSION = "1.0-00"
HERE = os.path.dirname(os.path.abspath(__file__))
BANNER_IMG = os.path.join(HERE, 'banner.png')
MANUAL = os.path.join(HERE, 'manual.html')

CHECK = None   # transparency checkerboard, built once


def checker():
    global CHECK
    if CHECK is None:
        CHECK = QPixmap(16, 16); CHECK.fill(QColor('#ffffff'))
        p = QPainter(CHECK); p.fillRect(0, 0, 8, 8, QColor('#d7dade')); p.fillRect(8, 8, 8, 8, QColor('#d7dade')); p.end()
    return CHECK


class Canvas(QWidget):
    def __init__(self, win, w=1000, h=700):
        super().__init__()
        self.win = win
        self.img = QImage(w, h, QImage.Format_ARGB32)
        self.img.fill(QColor('#ffffff'))
        self.zoom = 1.0
        self.tool = 'brush'
        self.color = QColor('#1f2a30')
        self.size = 6
        self.last = None
        self.start = None
        self.preview = None            # (tool, QPoint start, QPoint cur) while dragging a shape
        self.undo, self.redo = [], []
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._fit()

    def _fit(self):
        self.setMinimumSize(int(self.img.width() * self.zoom), int(self.img.height() * self.zoom))
        self.resize(self.minimumSize()); self.update()

    # ---- history ----
    def snapshot(self):
        self.undo.append(self.img.copy())
        if len(self.undo) > 40:
            self.undo.pop(0)
        self.redo.clear()
        self.win.update_title()

    def do_undo(self):
        if self.undo:
            self.redo.append(self.img.copy()); self.img = self.undo.pop(); self._fit()

    def do_redo(self):
        if self.redo:
            self.undo.append(self.img.copy()); self.img = self.redo.pop(); self._fit()

    # ---- view ----
    def set_zoom(self, z):
        self.zoom = max(0.1, min(16.0, z)); self._fit()

    def paintEvent(self, e):
        p = QPainter(self)
        r = QRectF(0, 0, self.img.width() * self.zoom, self.img.height() * self.zoom)
        p.fillRect(self.rect(), QColor('#2b2f36'))
        p.setBrush(QBrush(checker())); p.setPen(Qt.NoPen); p.drawRect(r)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
        p.drawImage(r, self.img, QRectF(0, 0, self.img.width(), self.img.height()))
        if self.preview:
            tool, a, b = self.preview
            p.save(); p.scale(self.zoom, self.zoom)
            pen = QPen(self.color, self.size); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            if tool == 'line': p.drawLine(a, b)
            elif tool == 'rect': p.drawRect(QRectF(a, b).normalized())
            elif tool == 'ellipse': p.drawEllipse(QRectF(a, b).normalized())
            p.restore()
        p.end()

    def img_pos(self, e):
        return QPoint(int(e.position().x() / self.zoom), int(e.position().y() / self.zoom))

    def _pen(self):
        pen = QPen(self.color, self.size); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        pos = self.img_pos(e)
        if self.tool == 'picker':
            if self.img.rect().contains(pos):
                self.win.set_color(self.img.pixelColor(pos))
            return
        if self.tool == 'fill':
            self.snapshot(); self.flood_fill(pos, self.color); self.update(); return
        if self.tool == 'text':
            txt, ok = QInputDialog.getText(self.win, 'Text', 'Text to add:')
            if ok and txt:
                self.snapshot(); p = QPainter(self.img); p.setPen(self.color)
                f = QFont('Noto Sans'); f.setPixelSize(max(8, self.size * 4)); p.setFont(f)
                p.drawText(QPointF(pos.x(), pos.y()), txt); p.end(); self.update()
            return
        self.snapshot()
        if self.tool in ('brush', 'eraser'):
            self.last = pos; self._stroke(pos, pos)
        else:                               # line / rect / ellipse
            self.start = pos; self.preview = (self.tool, pos, pos)
        self.update()

    def mouseMoveEvent(self, e):
        pos = self.img_pos(e)
        self.win.set_pos(pos)
        if not (e.buttons() & Qt.LeftButton): return
        if self.tool in ('brush', 'eraser') and self.last is not None:
            self._stroke(self.last, pos); self.last = pos; self.update()
        elif self.tool in ('line', 'rect', 'ellipse') and self.start is not None:
            self.preview = (self.tool, self.start, pos); self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton: return
        pos = self.img_pos(e)
        if self.tool in ('line', 'rect', 'ellipse') and self.start is not None:
            p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing); p.setPen(self._pen()); p.setBrush(Qt.NoBrush)
            if self.tool == 'line': p.drawLine(self.start, pos)
            elif self.tool == 'rect': p.drawRect(QRect(self.start, pos).normalized())
            else: p.drawEllipse(QRect(self.start, pos).normalized())
            p.end()
        self.last = self.start = self.preview = None
        self.update()

    def _stroke(self, a, b):
        p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing)
        if self.tool == 'eraser':
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.transparent, self.size); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
        else:
            p.setPen(self._pen())
        p.drawLine(a, b); p.end()

    def flood_fill(self, pos, new):
        if not self.img.rect().contains(pos): return
        target = self.img.pixel(pos)
        nc = new.rgba()
        if target == nc: return
        w, h = self.img.width(), self.img.height()
        stack = [(pos.x(), pos.y())]
        seen = set()
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen: continue
            if self.img.pixel(x, y) != target: continue
            seen.add((x, y)); self.img.setPixel(x, y, nc)
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    def new_image(self, w, h, bg):
        self.snapshot(); self.img = QImage(w, h, QImage.Format_ARGB32); self.img.fill(bg); self._fit()

    def load(self, img):
        self.snapshot(); self.img = img.convertToFormat(QImage.Format_ARGB32); self._fit()


class Main(QMainWindow):
    TOOLS = [('brush', 'Brush', '🖌'), ('eraser', 'Eraser', '◻'), ('line', 'Line', '╱'),
             ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'), ('fill', 'Fill', '🪣'),
             ('picker', 'Pick colour', '🎯'), ('text', 'Text', 'A')]

    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, 'PAINT')
        self.path = None
        self.canvas = Canvas(self)
        from PySide6.QtWidgets import QScrollArea
        sa = QScrollArea(); sa.setWidget(self.canvas); sa.setAlignment(Qt.AlignCenter)
        sa.setStyleSheet('QScrollArea{background:#20242a;border:none}')
        self.setCentralWidget(sa)
        self.build_menu(); self.build_tools()
        self.setWindowTitle(APP); self.resize(1180, 820)
        self.status = self.statusBar(); self.pos_lbl = QLabel('  '); self.status.addPermanentWidget(self.pos_lbl)
        self.set_color(self.canvas.color)

    # ---- toolbars ----
    def build_tools(self):
        tt = QToolBar('Tools'); tt.setOrientation(Qt.Vertical); tt.setIconSize(QSize(22, 22))
        self.tool_group = QActionGroup(self)
        for tid, label, glyph in self.TOOLS:
            a = QAction(letter_icon(glyph), label, self); a.setCheckable(True)
            a.setToolTip(label); a.triggered.connect(lambda _=0, t=tid: self.set_tool(t))
            self.tool_group.addAction(a); tt.addAction(a)
            if tid == 'brush': a.setChecked(True)
        self.addToolBar(Qt.LeftToolBarArea, tt)

        top = QToolBar('Paint'); top.setIconSize(QSize(20, 20)); self.addToolBar(Qt.TopToolBarArea, top)
        self.col_btn = QPushButton('  Colour  '); self.col_btn.clicked.connect(self.pick_color); top.addWidget(self.col_btn)
        top.addWidget(QLabel(' Size '))
        self.size_spin = QSpinBox(); self.size_spin.setRange(1, 200); self.size_spin.setValue(self.canvas.size)
        self.size_spin.setSuffix(' px'); self.size_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'size', v)); top.addWidget(self.size_spin)
        top.addSeparator()
        for txt, slot in (('Zoom +', lambda: self.canvas.set_zoom(self.canvas.zoom * 1.25)),
                          ('Zoom −', lambda: self.canvas.set_zoom(self.canvas.zoom / 1.25)),
                          ('100%', lambda: self.canvas.set_zoom(1.0))):
            b = QPushButton(txt); b.clicked.connect(slot); top.addWidget(b)

    def build_menu(self):
        m = self.menuBar()
        f = m.addMenu('&File')
        f.addAction(self.act('&New…', self.new, QKeySequence.New))
        f.addAction(self.act('&Open…', self.open, QKeySequence.Open))
        f.addAction(self.act('&Save', self.save, QKeySequence.Save))
        f.addAction(self.act('Save &As…', self.save_as, QKeySequence.SaveAs))
        f.addSeparator(); f.addAction(self.act('&Quit', self.close, QKeySequence.Quit))
        e = m.addMenu('&Edit')
        e.addAction(self.act('&Undo', self.canvas.do_undo, QKeySequence.Undo))
        e.addAction(self.act('&Redo', self.canvas.do_redo, QKeySequence.Redo))
        h = m.addMenu('&Help')
        h.addAction(self.act('&User Guide', self.open_manual))
        h.addAction(self.act('&About', self.about))

    def act(self, text, slot, sc=None):
        a = QAction(text, self);  a.triggered.connect(slot)
        if sc: a.setShortcut(sc)
        return a

    # ---- state ----
    def set_tool(self, t): self.canvas.tool = t
    def set_pos(self, p): self.pos_lbl.setText(f'{p.x()}, {p.y()}   ')

    def set_color(self, c):
        self.canvas.color = QColor(c)
        self.col_btn.setStyleSheet(f'QPushButton{{background:{QColor(c).name()};color:{"#fff" if QColor(c).lightness()<140 else "#000"};'
                                   'border:1px solid #888;border-radius:5px;padding:5px 12px;font-weight:600}}')

    def pick_color(self):
        c = QColorDialog.getColor(self.canvas.color, self, 'Colour')
        if c.isValid(): self.set_color(c)

    def update_title(self):
        self.setWindowTitle(f'{os.path.basename(self.path) if self.path else "Untitled"} — {APP}')

    # ---- file ----
    def new(self):
        dlg = QDialog(self); dlg.setWindowTitle('New Image'); v = QVBoxLayout(dlg)
        preset = QComboBox()
        PRE = [('1000 × 700', 1000, 700), ('1920 × 1080 (HD)', 1920, 1080), ('800 × 800 (square)', 800, 800),
               ('A4 @150dpi (1240 × 1754)', 1240, 1754), ('1080 × 1080 (social)', 1080, 1080)]
        for n, _, _ in PRE: preset.addItem(n)
        v.addWidget(QLabel('Size:')); v.addWidget(preset)
        bg = [QColor('#ffffff')]
        bgb = QPushButton('Background: white');
        def pb():
            c = QColorDialog.getColor(bg[0], dlg, 'Background');
            if c.isValid(): bg[0] = c; bgb.setText(f'Background: {c.name()}')
        bgb.clicked.connect(pb); v.addWidget(bgb)
        row = QHBoxLayout(); ok = QPushButton('Create'); cancel = QPushButton('Cancel')
        ok.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject); row.addWidget(cancel); row.addWidget(ok); v.addLayout(row)
        if dlg.exec():
            _, w, h = PRE[preset.currentIndex()]
            self.canvas.new_image(w, h, bg[0]); self.path = None; self.update_title()

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open image', os.path.expanduser('~'),
                                              'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)')
        if not path: return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP, "Couldn't open that image."); return
        self.canvas.load(img); self.path = path; self.update_title()

    def save(self):
        if not self.path or not self.path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return self.save_as()
        self._write(self.path)

    def save_as(self):
        start = self.path or os.path.join(os.path.expanduser('~'), 'image.png')
        path, _ = QFileDialog.getSaveFileName(self, 'Save image', start, 'PNG (*.png);;JPEG (*.jpg)')
        if not path: return
        if not path.lower().endswith(('.png', '.jpg', '.jpeg')): path += '.png'
        self._write(path); self.path = path; self.update_title()

    def _write(self, path):
        img = self.canvas.img
        if path.lower().endswith(('.jpg', '.jpeg')):
            flat = QImage(img.size(), QImage.Format_RGB32); flat.fill(QColor('#ffffff'))
            p = QPainter(flat); p.drawImage(0, 0, img); p.end(); img = flat
        if img.save(path):
            self.status.showMessage(f'Saved to {path}', 4000)
        else:
            QMessageBox.warning(self, APP, "Couldn't save the image.")

    def open_manual(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        if os.path.isfile(MANUAL):
            QDesktopServices.openUrl(QUrl.fromLocalFile(MANUAL))
        else:
            QDesktopServices.openUrl(QUrl('https://janszafranski.github.io/just-a-collection-of-apps/'))

    def about(self):
        QMessageBox.about(self, f'About {APP}',
                          f'<b>{APP}</b><br>Version {VERSION}<br><br>A tiny raster image editor — paint, '
                          'shapes, fill, text and save a PNG/JPG.<br>The companion to just a… PAGEdesigner '
                          'and WEBcreator.')


def letter_icon(glyph, size=22):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(QColor('#dfe3e8'))
    f = QFont('Noto Sans'); f.setPixelSize(int(size * 0.72)); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, glyph); p.end()
    return QIcon(pm)


def main():
    QApplication.setDesktopFileName('paint')
    app = QApplication(sys.argv)
    app.setApplicationName('PAINTcanvas'); app.setApplicationDisplayName(APP)
    app.setOrganizationName(ORG); app.setApplicationVersion(VERSION)
    w = Main()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and os.path.isfile(args[0]):
        img = QImage(args[0])
        if not img.isNull(): w.canvas.load(img); w.path = args[0]; w.update_title()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
