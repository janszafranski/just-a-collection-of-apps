#!/usr/bin/env python3
# just a... PAINTcanvas — a tiny raster (bitmap) image editor: paint, erase, draw shapes,
# fill, pick colours, add text, and save a PNG/JPG. The photo-editing companion to
# just a... PAGEcreator / WEBcreator (and the vector sibling of just a... DRAW).
import sys, os

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QColorDialog,
                                   QFileDialog, QMessageBox, QSpinBox, QLabel, QInputDialog,
                                   QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                                   QSlider, QCheckBox, QFormLayout, QDialogButtonBox)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QCursor, QFont, QPainterPath, QActionGroup)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings
except ImportError:
    sys.stderr.write("just a... PAINTcanvas needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... PAINTcanvas"
ORG = "justapaint"
VERSION = "1.2-00"
HERE = os.path.dirname(os.path.abspath(__file__))
BANNER_IMG = os.path.join(HERE, 'banner.png')
MANUAL = os.path.join(HERE, 'manual.html')


def _just_dir(kind):
    """The shared 'just a...' folder (kind='docs' → Documents, 'pics' → Pictures), created on demand."""
    base = os.path.expanduser('~/Documents' if kind == 'docs' else '~/Pictures')
    d = os.path.join(base, 'just a...')
    try: os.makedirs(d, exist_ok=True)
    except OSError: pass
    return d


def _justapps_recent(appkey, path):
    """Append to the shared recents log the COLLECTION launcher reads."""
    import json, time
    try:
        d = os.path.expanduser('~/.local/share/justapps'); os.makedirs(d, exist_ok=True)
        f = os.path.join(d, 'recents.json')
        try:
            with open(f) as fh: data = json.load(fh)
        except Exception: data = []
        data = [e for e in data if isinstance(e, dict) and e.get('path') != path]
        data.insert(0, {'app': appkey, 'path': path, 't': int(time.time())})
        with open(f, 'w') as fh: json.dump(data[:50], fh)
    except Exception: pass

CHECK = None   # transparency checkerboard, built once


def checker():
    global CHECK
    if CHECK is None:
        CHECK = QPixmap(16, 16); CHECK.fill(QColor('#ffffff'))
        p = QPainter(CHECK); p.fillRect(0, 0, 8, 8, QColor('#d7dade')); p.fillRect(8, 8, 8, 8, QColor('#d7dade')); p.end()
    return CHECK


# ---------------------------------------------------------------- image engine (Pillow)
# PhotoPlus-style adjustments and filters run through Pillow; QImage <-> PIL below.
try:
    from PIL import Image, ImageEnhance, ImageOps, ImageFilter
    import numpy as _np
    HAS_PIL = True
except Exception:
    HAS_PIL = False


def q2pil(img):
    im = img.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombytes('RGBA', (im.width(), im.height()), im.constBits().tobytes())


def pil2q(pil):
    if pil.mode != 'RGBA':
        pil = pil.convert('RGBA')
    data = pil.tobytes('raw', 'RGBA')
    return QImage(data, pil.width, pil.height, QImage.Format_RGBA8888).convertToFormat(QImage.Format_ARGB32).copy()


def _merge_a(src, rgb):
    """Put an RGB result back together with the source's alpha channel."""
    return Image.merge('RGBA', rgb.convert('RGB').split() + (src.split()[3],))


# ---- one-shot adjustments: pil(RGBA) -> pil(RGBA) ----
def adj_invert(p):       return _merge_a(p, ImageOps.invert(p.convert('RGB')))
def adj_grayscale(p):    return _merge_a(p, ImageOps.grayscale(p).convert('RGB'))
def adj_autocontrast(p): return _merge_a(p, ImageOps.autocontrast(p.convert('RGB'), cutoff=1))
def adj_equalize(p):     return _merge_a(p, ImageOps.equalize(p.convert('RGB')))
def adj_sepia(p):        return _merge_a(p, ImageOps.colorize(ImageOps.grayscale(p),
                                          black=(30, 16, 8), white=(255, 240, 200), mid=(150, 110, 70)))

# ---- parametric adjustments: build a closure from the slider values ----
def adj_brightness(f):  return lambda p: _merge_a(p, ImageEnhance.Brightness(p.convert('RGB')).enhance(f))
def adj_contrast(f):    return lambda p: _merge_a(p, ImageEnhance.Contrast(p.convert('RGB')).enhance(f))
def adj_saturation(f):  return lambda p: _merge_a(p, ImageEnhance.Color(p.convert('RGB')).enhance(f))
def adj_posterize(b):   return lambda p: _merge_a(p, ImageOps.posterize(p.convert('RGB'), max(1, min(8, int(b)))))

def adj_threshold(t):
    return lambda p: _merge_a(p, p.convert('L').point(lambda v: 255 if v > t else 0).convert('RGB'))

def adj_hue(shift):
    def f(p):
        hsv = _np.asarray(p.convert('HSV')).astype(_np.int16)
        hsv[..., 0] = (hsv[..., 0] + int(shift / 360.0 * 255)) % 256
        return _merge_a(p, Image.fromarray(hsv.astype('uint8'), 'HSV').convert('RGB'))
    return f

def adj_levels(black, white, gamma):
    def f(p):
        a = _np.asarray(p.convert('RGB')).astype(_np.float32)
        w = max(black + 1, white)
        a = _np.clip((a - black) / (w - black), 0, 1) ** (1.0 / max(0.05, gamma))
        return _merge_a(p, Image.fromarray((a * 255).astype('uint8'), 'RGB'))
    return f

def adj_temperature(k):
    def f(p):
        a = _np.asarray(p.convert('RGB')).astype(_np.float32)
        a[..., 0] = _np.clip(a[..., 0] + k * 0.6, 0, 255)
        a[..., 2] = _np.clip(a[..., 2] - k * 0.6, 0, 255)
        return _merge_a(p, Image.fromarray(a.astype('uint8'), 'RGB'))
    return f

# ---- filters ----
def flt_gaussian(r):  return lambda p: p.filter(ImageFilter.GaussianBlur(max(0.1, r)))
def flt_unsharp(r):   return lambda p: p.filter(ImageFilter.UnsharpMask(radius=max(0.1, r), percent=160))
def flt_median(s):    return lambda p: p.filter(ImageFilter.MedianFilter(size=int(s) if int(s) % 2 else int(s) + 1))
def flt_sharpen(p):   return p.filter(ImageFilter.SHARPEN)
def flt_soften(p):    return p.filter(ImageFilter.SMOOTH_MORE)
def flt_detail(p):    return p.filter(ImageFilter.DETAIL)
def flt_emboss(p):    return _merge_a(p, p.convert('RGB').filter(ImageFilter.EMBOSS))
def flt_edges(p):     return _merge_a(p, p.convert('RGB').filter(ImageFilter.FIND_EDGES))
def flt_contour(p):   return _merge_a(p, p.convert('RGB').filter(ImageFilter.CONTOUR))


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
        self.sel = None                # {'rect': QRect, 'kind': 'rect'|'ellipse'} marquee selection
        self.sel_drag = None           # (start, cur) while dragging a marquee
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
        if self.sel or self.sel_drag:
            p.save(); p.scale(self.zoom, self.zoom)
            if self.sel_drag:
                a, b = self.sel_drag; r = QRectF(a, b).normalized()
                kind = 'ellipse' if self.tool == 'mellipse' else 'rect'
            else:
                r = QRectF(self.sel['rect']); kind = self.sel['kind']
            p.setBrush(Qt.NoBrush)
            for col, style in ((QColor('#ffffff'), Qt.SolidLine), (QColor('#000000'), Qt.DashLine)):
                pen = QPen(col, 1, style); pen.setCosmetic(True); p.setPen(pen)
                p.drawEllipse(r) if kind == 'ellipse' else p.drawRect(r)
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
        if self.tool in ('mrect', 'mellipse'):          # marquee selection — not an image edit
            self.start = pos; self.sel_drag = (pos, pos); self.update(); return
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
        elif self.tool in ('mrect', 'mellipse') and self.start is not None:
            self.sel_drag = (self.start, pos); self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton: return
        pos = self.img_pos(e)
        if self.tool in ('mrect', 'mellipse') and self.start is not None:
            r = QRect(self.start, pos).normalized()
            self.sel = ({'rect': r, 'kind': 'ellipse' if self.tool == 'mellipse' else 'rect'}
                        if r.width() > 2 and r.height() > 2 else None)
            self.start = self.sel_drag = None; self.update(); return
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

    # ---- selection & the PhotoPlus image engine ----
    def sel_region(self):
        if not self.sel: return None
        r = self.sel['rect'].normalized().intersected(self.img.rect())
        if r.width() < 2 or r.height() < 2: return None
        return (r, self.sel['kind'])

    def _apply_to(self, src, func):
        """Return a NEW QImage: `src` with `func` (a pil->pil op) applied to the
        selection, or to the whole image if there is none. No undo push."""
        reg = self.sel_region()
        if reg is None:
            return pil2q(func(q2pil(src)))
        r, kind = reg
        out = src.copy()
        res = pil2q(func(q2pil(src.copy(r))))
        p = QPainter(out)
        if kind == 'ellipse':
            path = QPainterPath(); path.addEllipse(QRectF(r)); p.setClipPath(path)
        p.drawImage(r.topLeft(), res); p.end()
        return out

    def apply_region(self, func):
        self.snapshot(); self.img = self._apply_to(self.img, func); self._fit()

    def select_all(self):
        self.sel = {'rect': self.img.rect(), 'kind': 'rect'}; self.update()

    def select_none(self):
        self.sel = None; self.update()

    def crop_to_sel(self):
        reg = self.sel_region()
        if reg is None: return
        r, _ = reg; self.snapshot(); self.img = self.img.copy(r); self.sel = None; self._fit()

    def resize_image(self, w, h):
        self.snapshot()
        self.img = self.img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)
        self.sel = None; self._fit()

    def set_canvas_size(self, w, h):
        self.snapshot()
        out = QImage(w, h, QImage.Format_ARGB32); out.fill(Qt.transparent)
        p = QPainter(out); p.drawImage(0, 0, self.img); p.end()
        self.img = out; self.sel = None; self._fit()

    def rotate(self, deg):
        from PySide6.QtGui import QTransform
        self.snapshot(); self.img = self.img.transformed(QTransform().rotate(deg), Qt.SmoothTransformation)
        self.sel = None; self._fit()

    def flip(self, horizontal):
        self.snapshot(); self.img = self.img.mirrored(horizontal, not horizontal); self.sel = None; self._fit()

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

    def apply_fx(self, color, blur, dx, dy, opacity, twice=False):
        """Composite a soft drop shadow / glow of the drawing's opaque pixels behind it."""
        self.snapshot()
        src = self.img; W, H = src.width(), src.height()
        # a solid-colour silhouette with the drawing's own alpha
        sil = QImage(W, H, QImage.Format_ARGB32_Premultiplied); sil.fill(Qt.transparent)
        q = QPainter(sil); q.drawImage(0, 0, src)
        q.setCompositionMode(QPainter.CompositionMode_SourceIn); q.fillRect(sil.rect(), QColor(color)); q.end()
        if blur > 0:
            f = max(2, int(round(blur / 1.5)))
            sm = sil.scaled(max(1, W // f), max(1, H // f), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            sil = sm.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        out = QImage(W, H, QImage.Format_ARGB32); out.fill(Qt.transparent)
        q = QPainter(out); q.setOpacity(opacity / 100.0)
        q.drawImage(QPointF(dx, dy), sil)
        if twice: q.drawImage(QPointF(dx, dy), sil)
        q.setOpacity(1.0); q.drawImage(0, 0, src); q.end()
        self.img = out; self._fit()

    def new_image(self, w, h, bg):
        self.snapshot(); self.img = QImage(w, h, QImage.Format_ARGB32); self.img.fill(bg); self._fit()

    def load(self, img):
        self.snapshot(); self.img = img.convertToFormat(QImage.Format_ARGB32); self._fit()


class AdjustDialog(QDialog):
    """Live-preview dialog for a parametric adjustment or filter. `sliders` is a list of
    (key, label, min, max, default, scale); `build(values)` returns a pil->pil function."""
    def __init__(self, win, title, sliders, build):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas; self.build = build
        self.setWindowTitle(title); self.setMinimumWidth(340)
        self.base = self.canvas.img.copy()
        v = QVBoxLayout(self); form = QFormLayout(); v.addLayout(form)
        self.rows = {}
        for key, label, lo, hi, default, scale in sliders:
            s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(default)
            val = QLabel(); val.setMinimumWidth(46); val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            s.valueChanged.connect(self._apply)
            rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
            holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250)
            form.addRow(label, holder); self.rows[key] = (s, scale, val)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._apply()

    def _values(self):
        return {k: s.value() / sc for k, (s, sc, _) in self.rows.items()}

    def _apply(self):
        for k, (s, sc, val) in self.rows.items():
            val.setText(f'{s.value() / sc:g}')
        try:
            self.canvas.img = self.canvas._apply_to(self.base, self.build(self._values()))
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()

    def accept(self):
        self.canvas.undo.append(self.base)
        if len(self.canvas.undo) > 40: self.canvas.undo.pop(0)
        self.canvas.redo.clear(); self.win.update_title()
        super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class Main(QMainWindow):
    TOOLS = [('brush', 'Brush', '🖌'), ('eraser', 'Eraser', '◻'), ('line', 'Line', '╱'),
             ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'), ('fill', 'Fill', '🪣'),
             ('picker', 'Pick colour', '🎯'), ('text', 'Text', 'A'),
             ('mrect', 'Select — rectangle', '⬚'), ('mellipse', 'Select — ellipse', '◌')]

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
        img = m.addMenu('&Image')
        img.addAction(self.act('&Resize Image…', self.resize_image))
        img.addAction(self.act('&Canvas Size…', self.canvas_size))
        img.addAction(self.act('Crop to &Selection', lambda: self.canvas.crop_to_sel()))
        img.addSeparator()
        img.addAction(self.act('Rotate 90° &Right', lambda: self.canvas.rotate(90)))
        img.addAction(self.act('Rotate 90° &Left', lambda: self.canvas.rotate(-90)))
        img.addAction(self.act('Rotate &180°', lambda: self.canvas.rotate(180)))
        img.addAction(self.act('Flip &Horizontal', lambda: self.canvas.flip(True)))
        img.addAction(self.act('Flip &Vertical', lambda: self.canvas.flip(False)))

        adj = m.addMenu('&Adjust')
        adj.addAction(self.act('&Brightness / Contrast…', self.dlg_brightness))
        adj.addAction(self.act('&Levels…', self.dlg_levels))
        adj.addAction(self.act('&Hue / Saturation…', self.dlg_huesat))
        adj.addAction(self.act('Colour &Temperature…', self.dlg_temperature))
        adj.addAction(self.act('&Threshold…', self.dlg_threshold))
        adj.addAction(self.act('&Posterize…', self.dlg_posterize))
        adj.addSeparator()
        adj.addAction(self.act('Auto &Contrast', lambda: self.canvas.apply_region(adj_autocontrast)))
        adj.addAction(self.act('&Equalize', lambda: self.canvas.apply_region(adj_equalize)))
        adj.addAction(self.act('&Greyscale', lambda: self.canvas.apply_region(adj_grayscale)))
        adj.addAction(self.act('&Invert (Negative)', lambda: self.canvas.apply_region(adj_invert)))
        adj.addAction(self.act('Se&pia', lambda: self.canvas.apply_region(adj_sepia)))

        flt = m.addMenu('Fil&ter')
        flt.addAction(self.act('&Gaussian Blur…', self.dlg_blur))
        flt.addAction(self.act('&Unsharp Mask…', self.dlg_unsharp))
        flt.addAction(self.act('&Median (Despeckle)…', self.dlg_median))
        flt.addSeparator()
        flt.addAction(self.act('&Sharpen', lambda: self.canvas.apply_region(flt_sharpen)))
        flt.addAction(self.act('S&often', lambda: self.canvas.apply_region(flt_soften)))
        flt.addAction(self.act('&Detail', lambda: self.canvas.apply_region(flt_detail)))
        flt.addAction(self.act('&Emboss', lambda: self.canvas.apply_region(flt_emboss)))
        flt.addAction(self.act('Find &Edges', lambda: self.canvas.apply_region(flt_edges)))
        flt.addAction(self.act('&Contour', lambda: self.canvas.apply_region(flt_contour)))

        sel = m.addMenu('&Select')
        sel.addAction(self.act('Select &All', lambda: self.canvas.select_all(), QKeySequence.SelectAll))
        sel.addAction(self.act('&Deselect', lambda: self.canvas.select_none(), QKeySequence.Deselect))

        fx = m.addMenu('Effe&cts')
        fx.addAction(self.act('Drop &Shadow…', lambda: self._fx_dialog('shadow')))
        fx.addAction(self.act('Outer &Glow…', lambda: self._fx_dialog('glow')))
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

    def _fx_dialog(self, kind):
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        glow = kind == 'glow'
        dlg = QDialog(self); dlg.setWindowTitle('Outer Glow' if glow else 'Drop Shadow'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        dx = QSpinBox(); dx.setRange(-300, 300); dx.setSuffix(' px'); dx.setValue(8)
        dy = QSpinBox(); dy.setRange(-300, 300); dy.setSuffix(' px'); dy.setValue(8)
        bl = QSpinBox(); bl.setRange(0, 150); bl.setSuffix(' px'); bl.setValue(18 if glow else 10)
        op = QSpinBox(); op.setRange(0, 100); op.setSuffix(' %'); op.setValue(75 if glow else 55)
        col = ['#ffd54a' if glow else '#000000']; cb = QPushButton('Colour')
        def tint():
            c = QColor(col[0]); cb.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')
        def pick():
            c = QColorDialog.getColor(QColor(col[0]), self, 'Colour')
            if c.isValid(): col[0] = c.name(); tint()
        cb.clicked.connect(pick); tint()
        rows = ([('Blur:', bl), ('Strength:', op), ('Colour:', cb)] if glow
                else [('Offset across:', dx), ('Offset down:', dy), ('Blur:', bl), ('Strength:', op), ('Colour:', cb)])
        for lbl, w in rows: form.addRow(lbl, w)
        note = QLabel('Adds a soft ' + ('glow around' if glow else 'shadow behind') + ' everything you have drawn. '
                      'It shows through transparent areas, so start from a transparent background (File ▸ New ▸ '
                      'Transparent) or erase the backdrop first.')
        note.setWordWrap(True); lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        if glow: self.canvas.apply_fx(col[0], bl.value(), 0, 0, op.value(), twice=True)
        else: self.canvas.apply_fx(col[0], bl.value(), dx.value(), dy.value(), op.value())

    # ---- PhotoPlus-style adjustments, filters, image ops ----
    def _need_pil(self):
        if not HAS_PIL:
            QMessageBox.information(self, APP, 'Adjustments and filters need the Pillow and NumPy libraries.\n\n'
                                   'Install them with your package manager, for example:\n'
                                   '    sudo pacman -S python-pillow python-numpy')
            return False
        return True

    def dlg_brightness(self):
        if self._need_pil():
            AdjustDialog(self, 'Brightness / Contrast',
                         [('b', 'Brightness:', 0, 200, 100, 100.0), ('c', 'Contrast:', 0, 200, 100, 100.0)],
                         lambda v: (lambda p: adj_contrast(v['c'])(adj_brightness(v['b'])(p)))).exec()

    def dlg_levels(self):
        if self._need_pil():
            AdjustDialog(self, 'Levels',
                         [('bl', 'Black point:', 0, 254, 0, 1.0), ('wh', 'White point:', 1, 255, 255, 1.0),
                          ('g', 'Gamma:', 10, 300, 100, 100.0)],
                         lambda v: adj_levels(v['bl'], v['wh'], v['g'])).exec()

    def dlg_huesat(self):
        if self._need_pil():
            AdjustDialog(self, 'Hue / Saturation',
                         [('h', 'Hue shift:', -180, 180, 0, 1.0), ('s', 'Saturation:', 0, 200, 100, 100.0)],
                         lambda v: (lambda p: adj_saturation(v['s'])(adj_hue(v['h'])(p)))).exec()

    def dlg_temperature(self):
        if self._need_pil():
            AdjustDialog(self, 'Colour Temperature', [('k', 'Warm ↔ Cool:', -100, 100, 0, 1.0)],
                         lambda v: adj_temperature(v['k'])).exec()

    def dlg_threshold(self):
        if self._need_pil():
            AdjustDialog(self, 'Threshold', [('t', 'Level:', 0, 255, 128, 1.0)],
                         lambda v: adj_threshold(v['t'])).exec()

    def dlg_posterize(self):
        if self._need_pil():
            AdjustDialog(self, 'Posterize', [('b', 'Levels:', 1, 8, 4, 1.0)],
                         lambda v: adj_posterize(v['b'])).exec()

    def dlg_blur(self):
        if self._need_pil():
            AdjustDialog(self, 'Gaussian Blur', [('r', 'Radius:', 0, 400, 30, 10.0)],
                         lambda v: flt_gaussian(v['r'])).exec()

    def dlg_unsharp(self):
        if self._need_pil():
            AdjustDialog(self, 'Unsharp Mask', [('r', 'Radius:', 1, 200, 30, 10.0)],
                         lambda v: flt_unsharp(v['r'])).exec()

    def dlg_median(self):
        if self._need_pil():
            AdjustDialog(self, 'Median (Despeckle)', [('s', 'Size:', 1, 9, 3, 1.0)],
                         lambda v: flt_median(v['s'])).exec()

    def resize_image(self):
        w, h = self.canvas.img.width(), self.canvas.img.height()
        nw, ok = QInputDialog.getInt(self, 'Resize Image', 'New width (px):', w, 1, 20000)
        if not ok: return
        nh, ok = QInputDialog.getInt(self, 'Resize Image', 'New height (px):', round(h * nw / w), 1, 20000)
        if ok: self.canvas.resize_image(nw, nh)

    def canvas_size(self):
        w, h = self.canvas.img.width(), self.canvas.img.height()
        nw, ok = QInputDialog.getInt(self, 'Canvas Size', 'Canvas width (px):', w, 1, 20000)
        if not ok: return
        nh, ok = QInputDialog.getInt(self, 'Canvas Size', 'Canvas height (px):', h, 1, 20000)
        if ok: self.canvas.set_canvas_size(nw, nh)

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
        from PySide6.QtWidgets import QCheckBox
        bg = [QColor('#ffffff')]
        bgb = QPushButton('Background: white')
        def pb():
            c = QColorDialog.getColor(bg[0], dlg, 'Background')
            if c.isValid(): bg[0] = c; bgb.setText(f'Background: {c.name()}'); trans.setChecked(False)
        bgb.clicked.connect(pb); v.addWidget(bgb)
        trans = QCheckBox('Transparent background (for shadows, logos and cut-outs)')
        trans.toggled.connect(lambda on: bgb.setEnabled(not on)); v.addWidget(trans)
        row = QHBoxLayout(); ok = QPushButton('Create'); cancel = QPushButton('Cancel')
        ok.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject); row.addWidget(cancel); row.addWidget(ok); v.addLayout(row)
        if dlg.exec():
            _, w, h = PRE[preset.currentIndex()]
            self.canvas.new_image(w, h, Qt.transparent if trans.isChecked() else bg[0])
            self.path = None; self.update_title()

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open image', _just_dir('pics'),
                                              'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)')
        if not path: return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP, "Couldn't open that image."); return
        self.canvas.load(img); self.path = path; self.update_title(); _justapps_recent('paint', path)

    def save(self):
        if not self.path or not self.path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return self.save_as()
        self._write(self.path)

    def save_as(self):
        start = self.path or os.path.join(_just_dir('pics'), 'image.png')
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
            self.status.showMessage(f'Saved to {path}', 4000); _justapps_recent('paint', path)
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
        if not img.isNull(): w.canvas.load(img); w.path = args[0]; w.update_title(); _justapps_recent('paint', args[0])
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
