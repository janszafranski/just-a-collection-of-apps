#!/usr/bin/env python3
# just a... PAINTcanvas — a tiny raster (bitmap) image editor: paint, erase, draw shapes,
# fill, pick colours, add text, and save a PNG/JPG. The photo-editing companion to
# just a... PAGEcreator / WEBcreator (and the vector sibling of just a... DRAW).
import sys, os

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QColorDialog,
                                   QFileDialog, QMessageBox, QSpinBox, QLabel, QInputDialog,
                                   QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                                   QSlider, QCheckBox, QFormLayout, QDialogButtonBox,
                                   QDockWidget, QListWidget, QListWidgetItem)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QCursor, QFont, QPainterPath, QActionGroup,
                               QLinearGradient, QTransform)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings
except ImportError:
    sys.stderr.write("just a... PAINTcanvas needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... PAINTcanvas"
ORG = "justapaint"
VERSION = "1.5-00"
HERE = os.path.dirname(os.path.abspath(__file__))
BANNER_IMG = os.path.join(HERE, 'banner.png')
MANUAL = next((p for p in (os.path.join(HERE,'manual.pdf'), os.path.join(HERE,'manual.html')) if os.path.isfile(p)), os.path.join(HERE,'manual.pdf'))
QUICKSTART = next((p for p in (os.path.join(HERE,'quickstart.pdf'), os.path.join(HERE,'quickstart.html')) if os.path.isfile(p)), os.path.join(HERE,'quickstart.pdf'))


def _just_dir(kind):
    """The shared 'just a...' folder (kind='docs' → Documents, 'pics' → Pictures), created on demand."""
    base = os.path.expanduser('~/Documents' if kind == 'docs' else '~/Pictures')
    d = os.path.join(base, 'just a...')
    try: os.makedirs(d, exist_ok=True)
    except OSError: pass
    return d


def _justapps_recent(appkey, path):
    """Append to the shared recents log the CREATORsuite launcher reads."""
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

def adj_curves(lut, channel='rgb'):
    """Apply a 256-entry LUT (a list/array of 0..255) via Pillow point(). channel is
    'rgb' (all channels / luma-style) or 'r'/'g'/'b' for a single channel."""
    lut = [int(max(0, min(255, v))) for v in lut]

    def f(p):
        rgb = p.convert('RGB')
        if channel == 'rgb':
            rgb = rgb.point(lut * 3)
        else:
            ch = {'r': 0, 'g': 1, 'b': 2}[channel]
            bands = list(rgb.split())
            bands[ch] = bands[ch].point(lut)
            rgb = Image.merge('RGB', bands)
        return _merge_a(p, rgb)
    return f


def curve_lut(points):
    """Build a 256-entry LUT by linear interpolation through sorted (x,y) control points
    (each 0..255). Always anchored by clamping to the point range at the ends."""
    pts = sorted(points)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    if HAS_PIL:
        return _np.interp(_np.arange(256), xs, ys).round().astype('int').tolist()
    lut = []
    for x in range(256):
        if x <= xs[0]: lut.append(ys[0]); continue
        if x >= xs[-1]: lut.append(ys[-1]); continue
        for i in range(1, len(xs)):
            if x <= xs[i]:
                t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
                lut.append(round(ys[i - 1] + t * (ys[i] - ys[i - 1]))); break
    return lut


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

def adj_colorbalance(cr, mg, yb):
    def f(p):
        a = _np.asarray(p.convert('RGB')).astype(_np.float32)
        a[..., 0] = _np.clip(a[..., 0] + cr, 0, 255)
        a[..., 1] = _np.clip(a[..., 1] + mg, 0, 255)
        a[..., 2] = _np.clip(a[..., 2] + yb, 0, 255)
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


BLENDS = {
    'normal': QPainter.CompositionMode_SourceOver, 'multiply': QPainter.CompositionMode_Multiply,
    'screen': QPainter.CompositionMode_Screen, 'overlay': QPainter.CompositionMode_Overlay,
    'darken': QPainter.CompositionMode_Darken, 'lighten': QPainter.CompositionMode_Lighten,
    'add': QPainter.CompositionMode_Plus, 'difference': QPainter.CompositionMode_Difference,
}
BLEND_NAMES = ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'add', 'difference']


class Layer:
    def __init__(self, img, name='Layer', visible=True, opacity=1.0, blend='normal'):
        self.img = img; self.name = name; self.visible = visible
        self.opacity = opacity; self.blend = blend


class Canvas(QWidget):
    HIST = 24

    def __init__(self, win, w=1000, h=700):
        super().__init__()
        self.win = win
        base = QImage(w, h, QImage.Format_ARGB32); base.fill(QColor('#ffffff'))
        self.layers = [Layer(base, 'Background')]
        self.active = 0
        self.zoom = 1.0
        self.tool = 'brush'
        self.color = QColor('#1f2a30')
        self.size = 6
        self.cutout_tol = 45
        self.wand_tol = 32             # magic-wand colour tolerance (0..255-ish)
        self.wand_contiguous = True    # wand selects a connected region vs. the whole image
        self.last = None
        self.start = None
        self.preview = None            # (tool, QPoint start, QPoint cur) while dragging a shape
        # Selection. Either None, a marquee {'rect':QRect,'kind':'rect'|'ellipse'}, or a
        # free-form mask {'kind':'mask','mask':uint8 HxW ndarray (0..255; >0 = selected,
        # intermediate values = feathered edge)}. sel_mask() turns any of them into a mask.
        self.sel = None
        self.sel_drag = None           # (start, cur) while dragging a marquee
        self.clone_src = None          # clone-tool source anchor (Ctrl-click)
        self.clone_off = None          # clone offset once a stroke begins
        self.clone_base = None         # snapshot of the layer cloned FROM
        self.undo, self.redo = [], []
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._fit()

    # ---- layers ----
    @property
    def img(self):
        return self.layers[self.active].img

    @img.setter
    def img(self, value):
        self.layers[self.active].img = value

    def doc_w(self): return self.layers[0].img.width()
    def doc_h(self): return self.layers[0].img.height()

    def composited(self):
        """Flatten all visible layers to one QImage (for display and export)."""
        base = QImage(self.doc_w(), self.doc_h(), QImage.Format_ARGB32); base.fill(Qt.transparent)
        p = QPainter(base)
        for l in self.layers:
            if not l.visible or l.opacity <= 0: continue
            p.setOpacity(l.opacity)
            p.setCompositionMode(BLENDS.get(l.blend, QPainter.CompositionMode_SourceOver))
            p.drawImage(0, 0, l.img)
        p.end()
        return base

    def _copy_layers(self):
        return [Layer(l.img.copy(), l.name, l.visible, l.opacity, l.blend) for l in self.layers]

    def _unique_name(self, stem):
        taken = {l.name for l in self.layers}; i = 1
        while f'{stem} {i}' in taken: i += 1
        return f'{stem} {i}'

    def set_active(self, i):
        if 0 <= i < len(self.layers) and i != self.active:
            self.active = i; self.win.refresh_layers(); self.update()

    def set_layer_prop(self, **kw):
        l = self.layers[self.active]
        for k, v in kw.items():
            setattr(l, k, v)
        self.update()

    def add_layer(self):
        self.snapshot_full()
        im = QImage(self.doc_w(), self.doc_h(), QImage.Format_ARGB32); im.fill(Qt.transparent)
        self.active += 1; self.layers.insert(self.active, Layer(im, self._unique_name('Layer')))
        self.update(); self.win.refresh_layers()

    def duplicate_layer(self):
        self.snapshot_full()
        s = self.layers[self.active]
        self.layers.insert(self.active + 1, Layer(s.img.copy(), s.name + ' copy', s.visible, s.opacity, s.blend))
        self.active += 1; self.update(); self.win.refresh_layers()

    def delete_layer(self):
        if len(self.layers) <= 1: return
        self.snapshot_full(); del self.layers[self.active]
        self.active = min(self.active, len(self.layers) - 1); self.update(); self.win.refresh_layers()

    def merge_down(self):
        if self.active == 0: return
        self.snapshot_full()
        top = self.layers[self.active]; bot = self.layers[self.active - 1]
        if top.visible:
            p = QPainter(bot.img); p.setOpacity(top.opacity)
            p.setCompositionMode(BLENDS.get(top.blend, QPainter.CompositionMode_SourceOver))
            p.drawImage(0, 0, top.img); p.end()
        del self.layers[self.active]; self.active -= 1; self.update(); self.win.refresh_layers()

    def move_layer(self, delta):
        j = self.active + delta
        if 0 <= j < len(self.layers):
            self.snapshot_full()
            self.layers[self.active], self.layers[j] = self.layers[j], self.layers[self.active]
            self.active = j; self.update(); self.win.refresh_layers()

    def _fit(self):
        self.setMinimumSize(int(self.img.width() * self.zoom), int(self.img.height() * self.zoom))
        self.resize(self.minimumSize()); self.update()

    # ---- history (tagged: 'layer' = active layer only, 'full' = whole stack) ----
    def _cap(self):
        if len(self.undo) > self.HIST: self.undo.pop(0)

    def snapshot(self):
        self.undo.append(('layer', self.active, self.img.copy())); self._cap(); self.redo.clear(); self.win.update_title()

    def snapshot_full(self):
        self.undo.append(('full', self._copy_layers(), self.active)); self._cap(); self.redo.clear(); self.win.update_title()

    def push_undo_layer(self, idx, img):
        self.undo.append(('layer', idx, img)); self._cap(); self.redo.clear(); self.win.update_title()

    def _state_like(self, entry):
        if entry[0] == 'layer':
            idx = min(entry[1], len(self.layers) - 1)
            return ('layer', idx, self.layers[idx].img.copy())
        return ('full', self._copy_layers(), self.active)

    def _restore(self, entry):
        if entry[0] == 'layer':
            _, idx, img = entry
            if idx < len(self.layers): self.layers[idx].img = img
        else:
            _, layers, active = entry
            self.layers = layers; self.active = max(0, min(active, len(layers) - 1))

    def do_undo(self):
        if not self.undo: return
        self.redo.append(self._state_like(self.undo[-1]))
        self._restore(self.undo.pop()); self.win.refresh_layers(); self._fit()

    def do_redo(self):
        if not self.redo: return
        self.undo.append(self._state_like(self.redo[-1]))
        self._restore(self.redo.pop()); self.win.refresh_layers(); self._fit()

    # ---- view ----
    def set_zoom(self, z):
        self.zoom = max(0.1, min(16.0, z)); self._fit()

    def paintEvent(self, e):
        p = QPainter(self)
        r = QRectF(0, 0, self.img.width() * self.zoom, self.img.height() * self.zoom)
        p.fillRect(self.rect(), QColor('#2b2f36'))
        p.setBrush(QBrush(checker())); p.setPen(Qt.NoPen); p.drawRect(r)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
        comp = self.composited()
        p.drawImage(r, comp, QRectF(0, 0, comp.width(), comp.height()))
        if self.preview:
            tool, a, b = self.preview
            p.save(); p.scale(self.zoom, self.zoom)
            pen = QPen(self.color, self.size); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            if tool == 'line': p.drawLine(a, b)
            elif tool == 'rect': p.drawRect(QRectF(a, b).normalized())
            elif tool == 'ellipse': p.drawEllipse(QRectF(a, b).normalized())
            elif tool == 'gradient':
                gp = QPen(QColor('#000'), 1, Qt.DashLine); gp.setCosmetic(True); p.setPen(gp); p.drawLine(a, b)
            p.restore()
        if self.sel and self.sel.get('kind') == 'mask' and not self.sel_drag:
            ov = self._mask_overlay()
            if ov is not None:
                p.drawImage(r, ov, QRectF(0, 0, ov.width(), ov.height()))
        elif self.sel or self.sel_drag:
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

    def _mask_overlay(self):
        """A cached RGBA overlay (blue tint inside the mask + a white outline) for a
        mask selection, so marching-ants-ish feedback shows where it is."""
        if not HAS_PIL or not self.sel or self.sel.get('kind') != 'mask': return None
        m = self.sel['mask']
        cached = self.sel.get('_ov')
        if cached is not None and self.sel.get('_ov_shape') == m.shape:
            return cached
        h, w = m.shape
        ov = _np.zeros((h, w, 4), _np.uint8)
        inside = m > 0
        ov[..., 2] = 255                                   # blue tint
        ov[..., 3] = (m.astype(_np.uint16) * 60 // 255).astype(_np.uint8)  # faint fill
        # 1-px outline = edge of the selected region
        edge = _np.zeros((h, w), bool)
        edge[:-1, :] |= inside[:-1, :] != inside[1:, :]
        edge[:, :-1] |= inside[:, :-1] != inside[:, 1:]
        ov[edge] = (255, 255, 255, 230)
        img = pil2q(Image.fromarray(ov, 'RGBA'))
        self.sel['_ov'] = img; self.sel['_ov_shape'] = m.shape
        return img

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
        if self.tool == 'cutout':
            self.cutout_at(pos, self.cutout_tol); return
        if self.tool == 'wand':
            if HAS_PIL:
                self.wand_select(pos, self.wand_tol, self.wand_contiguous)
            else:
                self.win.status.showMessage('Magic wand needs Pillow and NumPy.', 3000)
            return
        if self.tool == 'text':
            res = self.win.ask_text()
            if res:
                txt, fam, px = res
                self.snapshot(); p = QPainter(self.img); p.setRenderHint(QPainter.TextAntialiasing); p.setPen(self.color)
                f = QFont(fam); f.setPixelSize(px); p.setFont(f)
                p.drawText(QPointF(pos.x(), pos.y()), txt); p.end(); self.update()
            return
        if self.tool in ('mrect', 'mellipse'):          # marquee selection — not an image edit
            self.start = pos; self.sel_drag = (pos, pos); self.update(); return
        if self.tool == 'clone' and (e.modifiers() & Qt.ControlModifier):
            self.clone_src = pos; self.clone_off = None
            self.win.status.showMessage('Clone source set — now paint to copy from it.', 3000); return
        if self.tool == 'redeye':
            if HAS_PIL: self.snapshot(); self.red_eye(pos); self.update()
            return
        self.snapshot()
        if self.tool in ('brush', 'eraser', 'dodge', 'burn'):
            self.last = pos; self._stroke(pos, pos)
        elif self.tool == 'clone':
            if self.clone_src is None:
                self.win.status.showMessage('Hold Ctrl and click to set a clone source first.', 3000)
                self.undo.pop(); return
            self.clone_base = self.img.copy()
            if self.clone_off is None:
                self.clone_off = (pos.x() - self.clone_src.x(), pos.y() - self.clone_src.y())
            self.last = pos; self._stroke(pos, pos)
        else:                               # line / rect / ellipse / gradient
            self.start = pos; self.preview = (self.tool, pos, pos)
        self.update()

    def mouseMoveEvent(self, e):
        pos = self.img_pos(e)
        self.win.set_pos(pos)
        if not (e.buttons() & Qt.LeftButton): return
        if self.tool in ('brush', 'eraser', 'dodge', 'burn', 'clone') and self.last is not None:
            self._stroke(self.last, pos); self.last = pos; self.update()
        elif self.tool in ('line', 'rect', 'ellipse', 'gradient') and self.start is not None:
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
        if self.tool == 'gradient' and self.start is not None:
            self._draw_gradient(self.start, pos)
        elif self.tool in ('line', 'rect', 'ellipse') and self.start is not None:
            p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing); p.setPen(self._pen()); p.setBrush(Qt.NoBrush)
            if self.tool == 'line': p.drawLine(self.start, pos)
            elif self.tool == 'rect': p.drawRect(QRect(self.start, pos).normalized())
            else: p.drawEllipse(QRect(self.start, pos).normalized())
            p.end()
        self.last = self.start = self.preview = None
        self.clone_base = None
        self.update()

    def _draw_gradient(self, a, b):
        g = QLinearGradient(QPointF(a), QPointF(b))
        c0 = QColor(self.color); c1 = QColor(self.color); c1.setAlpha(0)
        g.setColorAt(0, c0); g.setColorAt(1, c1)
        mask = self.sel_mask() if (self.sel and self.sel.get('kind') == 'mask') else None
        if mask is not None:                       # mask / feathered selection — blend in
            grad = QImage(self.img.size(), QImage.Format_ARGB32); grad.fill(Qt.transparent)
            gp = QPainter(grad); gp.fillRect(grad.rect(), QBrush(g)); gp.end()
            out = self.img.copy()
            over = _np.asarray(q2pil(grad)).astype(_np.float32)
            dst = _np.asarray(q2pil(out)).astype(_np.float32)
            # source-over of `over` onto `dst`, weighted by the selection mask
            sa = over[..., 3:4] / 255.0 * (mask.astype(_np.float32) / 255.0)[..., None]
            dst[..., :3] = over[..., :3] * sa + dst[..., :3] * (1 - sa)
            dst[..., 3:4] = _np.clip(over[..., 3:4] * sa + dst[..., 3:4], 0, 255)
            self.img = pil2q(Image.fromarray(dst.astype('uint8'), 'RGBA')); return
        p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing)
        reg = self.sel_region()
        if reg:
            r, kind = reg; path = QPainterPath()
            path.addEllipse(QRectF(r)) if kind == 'ellipse' else path.addRect(QRectF(r))
            p.setClipPath(path)
        p.fillRect(self.img.rect(), QBrush(g)); p.end()

    def red_eye(self, pos):
        r = max(8, self.size * 2)
        x0 = max(0, pos.x() - r); y0 = max(0, pos.y() - r)
        x1 = min(self.doc_w(), pos.x() + r); y1 = min(self.doc_h(), pos.y() + r)
        if x1 <= x0 or y1 <= y0: return
        sub = self.img.copy(QRect(x0, y0, x1 - x0, y1 - y0))
        a = _np.asarray(q2pil(sub)).astype(_np.int16)
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        mask = (R > 55) & (R > G * 1.4) & (R > B * 1.4)
        gray = (G + B) // 2
        a[..., 0] = _np.where(mask, gray, R)
        p = QPainter(self.img)
        p.drawImage(QPointF(x0, y0), pil2q(Image.fromarray(a.astype('uint8'), 'RGBA'))); p.end()

    def straighten(self, angle):
        w, h = self.doc_w(), self.doc_h()
        self.snapshot_full()
        for l in self.layers:
            big = l.img.transformed(QTransform().rotate(angle), Qt.SmoothTransformation)
            x = (big.width() - w) // 2; y = (big.height() - h) // 2
            l.img = big.copy(QRect(x, y, w, h))
        self.sel = None; self._fit()

    def _stroke(self, a, b):
        if self.tool == 'clone':
            self._clone_stroke(a, b); return
        p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing)
        if self.tool == 'eraser':
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.transparent, self.size); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
        elif self.tool in ('dodge', 'burn'):
            p.setOpacity(0.15)
            p.setCompositionMode(QPainter.CompositionMode_Screen if self.tool == 'dodge'
                                 else QPainter.CompositionMode_Multiply)
            col = QColor('#ffffff') if self.tool == 'dodge' else QColor('#000000')
            pen = QPen(col, self.size); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin); p.setPen(pen)
        else:
            p.setPen(self._pen())
        p.drawLine(a, b); p.end()

    def _clone_stroke(self, a, b):
        if self.clone_off is None or self.clone_base is None: return
        ox, oy = self.clone_off
        p = QPainter(self.img); p.setRenderHint(QPainter.Antialiasing)
        r = max(1, self.size / 2)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        n = max(1, int((dx * dx + dy * dy) ** 0.5))
        for i in range(n + 1):
            cx = a.x() + dx * i / n; cy = a.y() + dy * i / n
            path = QPainterPath(); path.addEllipse(QPointF(cx, cy), r, r)
            p.save(); p.setClipPath(path); p.drawImage(QPointF(ox, oy), self.clone_base); p.restore()
        p.end()

    # ---- selection & the PhotoPlus image engine ----
    def sel_region(self):
        """The bounding region of a rectangle/ellipse marquee (QRect, kind), or None.
        A mask selection has no simple rectangular region, so this returns None for it —
        callers that must honour a mask go through sel_mask()/_apply_to instead."""
        if not self.sel or self.sel.get('kind') == 'mask': return None
        r = self.sel['rect'].normalized().intersected(self.img.rect())
        if r.width() < 2 or r.height() < 2: return None
        return (r, self.sel['kind'])

    def sel_mask(self):
        """A uint8 HxW ndarray (0..255; >0 selected) for the CURRENT selection in the
        current image's geometry, or None if nothing is selected. rect/ellipse marquees
        are rasterised on demand; a 'mask' selection is returned (resized if the image
        geometry no longer matches). Needs numpy (HAS_PIL)."""
        if not self.sel or not HAS_PIL: return None
        w, h = self.img.width(), self.img.height()
        k = self.sel.get('kind')
        if k == 'mask':
            m = self.sel['mask']
            if m.shape != (h, w):
                mi = Image.fromarray(m, 'L').resize((w, h), Image.NEAREST)
                m = _np.asarray(mi)
            return m
        r = self.sel['rect'].normalized().intersected(self.img.rect())
        if r.width() < 2 or r.height() < 2: return None
        m = _np.zeros((h, w), _np.uint8)
        if k == 'ellipse':
            yy, xx = _np.ogrid[0:h, 0:w]
            cx = r.x() + r.width() / 2.0; cy = r.y() + r.height() / 2.0
            rx = max(1.0, r.width() / 2.0); ry = max(1.0, r.height() / 2.0)
            inside = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
            m[inside] = 255
        else:
            m[r.y():r.y() + r.height(), r.x():r.x() + r.width()] = 255
        return m

    def set_mask_sel(self, mask):
        """Adopt a uint8 HxW mask as the selection (or clear it if empty)."""
        if mask is None or not mask.any():
            self.sel = None
        else:
            self.sel = {'kind': 'mask', 'mask': mask.astype(_np.uint8)}
        self.update()

    def _apply_to(self, src, func):
        """Return a NEW QImage: `src` with `func` (a pil->pil op) applied to the
        selection, or to the whole image if there is none. No undo push.
        A mask selection (incl. a feathered one) blends the result in by the mask
        weight so edits fade across soft edges."""
        mask = self.sel_mask()
        if mask is None:
            # no selection, or no numpy: fall back to a plain rect/ellipse clip
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
        # mask (or rasterised marquee): run func on the whole image, blend by mask weight
        base = q2pil(src)
        res = func(base)
        if res.size != base.size:                 # a geometry-changing op can't be masked
            return pil2q(res)
        a = _np.asarray(base.convert('RGBA')).astype(_np.float32)
        b = _np.asarray(res.convert('RGBA')).astype(_np.float32)
        wgt = (mask.astype(_np.float32) / 255.0)[..., None]
        blended = a * (1.0 - wgt) + b * wgt
        return pil2q(Image.fromarray(blended.astype('uint8'), 'RGBA'))

    def apply_region(self, func):
        self.snapshot(); self.img = self._apply_to(self.img, func); self._fit()

    def select_all(self):
        self.sel = {'rect': self.img.rect(), 'kind': 'rect'}; self.update()

    def select_none(self):
        self.sel = None; self.update()

    # ---- magic wand & selection editing (feather / invert / grow / shrink) ----
    def wand_select(self, pos, tol, contiguous=True):
        """Build a mask selection of pixels whose colour is within `tol` of the clicked
        pixel — either the connected region (contiguous) or every matching pixel."""
        if not HAS_PIL or not self.img.rect().contains(pos): return
        a = _np.asarray(q2pil(self.img))[..., :3].astype(_np.int16)
        h, w = a.shape[:2]
        tr, tg, tb = (int(c) for c in a[pos.y(), pos.x()])
        thr = int(tol) * 3
        close = (_np.abs(a[..., 0] - tr) + _np.abs(a[..., 1] - tg)
                 + _np.abs(a[..., 2] - tb)) <= thr
        if contiguous:
            mask = self._flood_mask(close, pos.x(), pos.y())
        else:
            mask = _np.where(close, 255, 0).astype(_np.uint8)
        self.set_mask_sel(mask)

    @staticmethod
    def _flood_mask(close, sx, sy):
        """4-connected flood over a boolean 'close' map from (sx,sy); returns uint8 mask."""
        h, w = close.shape
        mask = _np.zeros((h, w), _np.uint8)
        if not close[sy, sx]: return mask
        seen = _np.zeros((h, w), bool)
        stack = [(sx, sy)]; seen[sy, sx] = True
        while stack:
            x, y = stack.pop()
            mask[y, x] = 255
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and close[ny, nx]:
                    seen[ny, nx] = True; stack.append((nx, ny))
        return mask

    def _ensure_mask_sel(self):
        """Promote any selection (rect/ellipse/none→all) to a mask so it can be edited."""
        if self.sel is None:
            self.select_all()
        m = self.sel_mask()
        if m is not None:
            self.sel = {'kind': 'mask', 'mask': m.astype(_np.uint8)}
        return m

    def invert_sel(self):
        if not HAS_PIL: return
        m = self._ensure_mask_sel()
        if m is None: return
        self.set_mask_sel(255 - m)

    def feather_sel(self, radius):
        if not HAS_PIL or radius <= 0: return
        if self._ensure_mask_sel() is None: return
        m = self.sel['mask']
        soft = Image.fromarray(m, 'L').filter(ImageFilter.GaussianBlur(float(radius)))
        self.set_mask_sel(_np.asarray(soft))

    def grow_sel(self, px):
        """Grow (px>0) or shrink (px<0) the selection by a pixel radius (MaxFilter/MinFilter)."""
        if not HAS_PIL or px == 0: return
        if self._ensure_mask_sel() is None: return
        m = Image.fromarray(self.sel['mask'], 'L')
        n = abs(int(px)); size = 2 * n + 1
        m = m.filter(ImageFilter.MaxFilter(size) if px > 0 else ImageFilter.MinFilter(size))
        self.set_mask_sel(_np.asarray(m))

    def _map_layers(self, fn):
        """Apply fn(QImage)->QImage to every layer (a whole-document change)."""
        self.snapshot_full()
        for l in self.layers:
            l.img = fn(l.img)
        self.sel = None; self._fit()

    def crop_to_sel(self):
        reg = self.sel_region()
        if reg is not None:
            r, _ = reg; self._map_layers(lambda im: im.copy(r)); return
        if self.sel and self.sel.get('kind') == 'mask':      # crop to the mask's bbox
            m = self.sel_mask()
            if m is None or not m.any(): return
            ys, xs = _np.where(m > 0)
            r = QRect(int(xs.min()), int(ys.min()),
                      int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
            self._map_layers(lambda im: im.copy(r))

    def resize_image(self, w, h):
        self._map_layers(lambda im: im.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32))

    def set_canvas_size(self, w, h):
        def grow(im):
            out = QImage(w, h, QImage.Format_ARGB32); out.fill(Qt.transparent)
            p = QPainter(out); p.drawImage(0, 0, im); p.end(); return out
        self._map_layers(grow)

    def rotate(self, deg):
        from PySide6.QtGui import QTransform
        self._map_layers(lambda im: im.transformed(QTransform().rotate(deg), Qt.SmoothTransformation))

    def flip(self, horizontal):
        self._map_layers(lambda im: im.mirrored(horizontal, not horizontal))

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

    def _flood_transparent(self, seeds, target_rgb, tol):
        """Erase to transparency the region connected to `seeds` whose colour is within
        `tol` of target_rgb. Already-transparent pixels are passable (so you can clear
        across a background that already has holes). The active layer must have alpha."""
        img = self.img; w, h = img.width(), img.height()
        tr, tg, tb = target_rgb; thr = tol * 3
        stack = list(seeds); seen = set()
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
                continue
            seen.add((x, y))
            px = img.pixel(x, y)
            if (px >> 24) & 0xff:                       # opaque enough to test
                r = (px >> 16) & 0xff; g = (px >> 8) & 0xff; b = px & 0xff
                if abs(r - tr) + abs(g - tg) + abs(b - tb) > thr:
                    continue                            # a boundary — don't cross it
                img.setPixel(x, y, 0)                   # fully transparent
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    def cutout_at(self, pos, tol):
        """Erase the background region you click on, to transparency."""
        if not self.img.rect().contains(pos):
            return
        self.snapshot()
        px = self.img.pixel(pos.x(), pos.y())
        self._flood_transparent([(pos.x(), pos.y())], ((px >> 16) & 0xff, (px >> 8) & 0xff, px & 0xff), tol)
        self.update(); self.win.update_title()

    def remove_bg_edges(self, tol):
        """Auto-remove the background that touches the four edges of the picture."""
        from collections import Counter
        self.snapshot()
        w, h = self.img.width(), self.img.height()
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        px = Counter(self.img.pixel(x, y) for (x, y) in corners).most_common(1)[0][0]
        self._flood_transparent(corners, ((px >> 16) & 0xff, (px >> 8) & 0xff, px & 0xff), tol)
        self.update(); self.win.update_title()

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
        self.snapshot_full()
        base = QImage(w, h, QImage.Format_ARGB32); base.fill(bg)
        self.layers = [Layer(base, 'Background')]; self.active = 0; self.sel = None
        self._fit(); self.win.refresh_layers()

    def load(self, img):
        self.snapshot_full()
        base = img.convertToFormat(QImage.Format_ARGB32)
        self.layers = [Layer(base, 'Background')]; self.active = 0; self.sel = None
        self._fit(); self.win.refresh_layers()


class AdjustDialog(QDialog):
    """Live-preview dialog for a parametric adjustment or filter. `sliders` is a list of
    (key, label, min, max, default, scale); `build(values)` returns a pil->pil function."""
    def __init__(self, win, title, sliders, build):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas; self.build = build
        self.setWindowTitle(title); self.setMinimumWidth(340)
        self.active_idx = self.canvas.active
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
        self.canvas.push_undo_layer(self.active_idx, self.base)
        super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class CurveWidget(QWidget):
    """A small editable tone curve: draggable control points over a 0–255 diagonal.
    Points are stored in curve space (x,y both 0..255, origin bottom-left). Emits via
    the `changed` callback whenever the curve moves."""
    def __init__(self, changed):
        super().__init__()
        self.changed = changed
        self.points = [(0, 0), (255, 255)]       # identity to start
        self.drag = None
        self.setMinimumSize(236, 236)
        self.setMouseTracking(True)

    def reset(self):
        self.points = [(0, 0), (255, 255)]; self.drag = None; self.update(); self.changed()

    def lut(self):
        return curve_lut(self.points)

    # curve-space <-> widget-space
    def _to_w(self, x, y):
        m = 10; w = self.width() - 2 * m; h = self.height() - 2 * m
        return QPointF(m + x / 255.0 * w, m + (1 - y / 255.0) * h)

    def _to_c(self, pt):
        m = 10; w = self.width() - 2 * m; h = self.height() - 2 * m
        x = (pt.x() - m) / max(1, w) * 255.0; y = (1 - (pt.y() - m) / max(1, h)) * 255.0
        return (int(max(0, min(255, round(x)))), int(max(0, min(255, round(y)))))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#1f242b'))
        m = 10; w = self.width() - 2 * m; h = self.height() - 2 * m
        p.setPen(QPen(QColor('#3a424c'), 1))
        for i in range(1, 4):
            p.drawLine(QPointF(m + i / 4 * w, m), QPointF(m + i / 4 * w, m + h))
            p.drawLine(QPointF(m, m + i / 4 * h), QPointF(m + w, m + i / 4 * h))
        p.setPen(QPen(QColor('#55606c'), 1, Qt.DashLine))
        p.drawLine(self._to_w(0, 0), self._to_w(255, 255))
        lut = self.lut()                          # the live curve
        path = QPainterPath(); path.moveTo(self._to_w(0, lut[0]))
        for x in range(1, 256): path.lineTo(self._to_w(x, lut[x]))
        p.setPen(QPen(QColor('#f0c040'), 2)); p.drawPath(path)
        p.setBrush(QColor('#ffffff')); p.setPen(QPen(QColor('#f0c040'), 1.5))
        for (x, y) in self.points:
            c = self._to_w(x, y); p.drawEllipse(c, 4, 4)
        p.end()

    def _nearest(self, pt):
        best = None; bd = 1e9
        for i, (x, y) in enumerate(self.points):
            w = self._to_w(x, y); d = (w.x() - pt.x()) ** 2 + (w.y() - pt.y()) ** 2
            if d < bd: bd = d; best = i
        return best if bd <= 14 ** 2 else None

    def mousePressEvent(self, e):
        pt = e.position(); i = self._nearest(pt)
        if e.button() == Qt.RightButton:          # remove a point (not the ends)
            if i is not None and 0 < i < len(self.points) - 1:
                del self.points[i]; self.update(); self.changed()
            return
        if i is None:                             # add a new point
            x, y = self._to_c(pt)
            self.points.append((x, y)); self.points.sort()
            i = self.points.index((x, y))
        self.drag = i; self.update()

    def mouseMoveEvent(self, e):
        if self.drag is None: return
        x, y = self._to_c(e.position())
        i = self.drag
        if i == 0: x = 0
        elif i == len(self.points) - 1: x = 255
        else:                                     # keep strictly between neighbours
            x = max(self.points[i - 1][0] + 1, min(self.points[i + 1][0] - 1, x))
        self.points[i] = (x, y); self.update(); self.changed()

    def mouseReleaseEvent(self, e):
        self.drag = None


class CurvesDialog(QDialog):
    """Adjust ▸ Curves — a draggable tone curve driving a 256-entry LUT, live-previewed
    and selection-aware, in the same spirit as AdjustDialog."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Curves'); self.setMinimumWidth(300)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()
        v = QVBoxLayout(self)
        row = QHBoxLayout(); row.addWidget(QLabel('Channel:'))
        self.chan = QComboBox(); self.chan.addItems(['RGB (all)', 'Red', 'Green', 'Blue'])
        self.chan.currentIndexChanged.connect(self._apply); row.addWidget(self.chan, 1)
        v.addLayout(row)
        self.curve = CurveWidget(self._apply); v.addWidget(self.curve)
        v.addWidget(QLabel('Click to add a point, drag to shape the curve, right-click to remove.'))
        rb = QHBoxLayout(); reset = QPushButton('Reset'); reset.clicked.connect(self.curve.reset)
        rb.addWidget(reset); rb.addStretch(1); v.addLayout(rb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._apply()

    def _chan(self):
        return ['rgb', 'r', 'g', 'b'][self.chan.currentIndex()]

    def _func(self):
        return adj_curves(self.curve.lut(), self._chan())

    def _apply(self):
        try:
            self.canvas.img = self.canvas._apply_to(self.base, self._func())
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()

    def accept(self):
        self.canvas.push_undo_layer(self.active_idx, self.base)
        super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class Main(QMainWindow):
    TOOLS = [('brush', 'Brush', '🖌'), ('eraser', 'Eraser', '◻'), ('line', 'Line', '╱'),
             ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'), ('fill', 'Fill', '🪣'),
             ('gradient', 'Gradient fill (drag)', '▨'), ('picker', 'Pick colour', '🎯'),
             ('text', 'Text', 'A'), ('clone', 'Clone — Ctrl-click to set source', '❏'),
             ('redeye', 'Red-eye removal', '◉'), ('dodge', 'Dodge — lighten', '☀'),
             ('burn', 'Burn — darken', '◐'),
             ('mrect', 'Select — rectangle', '⬚'), ('mellipse', 'Select — ellipse', '◌'),
             ('wand', 'Magic wand — click to select by colour', '✦'),
             ('cutout', 'Cutout — click a background to erase it to transparency', '✂')]

    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, 'PAINT')
        self.path = None
        self.canvas = Canvas(self)
        self.load_bundled_fonts()
        from PySide6.QtWidgets import QScrollArea
        sa = QScrollArea(); sa.setWidget(self.canvas); sa.setAlignment(Qt.AlignCenter)
        sa.setStyleSheet('QScrollArea{background:#20242a;border:none}')
        self.setCentralWidget(sa)
        self._layer_sync = False
        self.build_menu(); self.build_tools(); self.build_layers_dock()
        self.setWindowTitle(APP); self.resize(1180, 820)
        self.status = self.statusBar(); self.pos_lbl = QLabel('  '); self.status.addPermanentWidget(self.pos_lbl)
        self.set_color(self.canvas.color)
        self.refresh_layers()

    def build_layers_dock(self):
        dock = QDockWidget('Layers', self); dock.setObjectName('layersdock')
        dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(6, 6, 6, 6); v.setSpacing(6)
        self.blend_cb = QComboBox(); self.blend_cb.addItems([n.capitalize() for n in BLEND_NAMES])
        self.blend_cb.activated.connect(lambda i: self.canvas.set_layer_prop(blend=BLEND_NAMES[i]))
        v.addWidget(self.blend_cb)
        orow = QHBoxLayout(); orow.addWidget(QLabel('Opacity'))
        self.opacity_sl = QSlider(Qt.Horizontal); self.opacity_sl.setRange(0, 100); self.opacity_sl.setValue(100)
        self.opacity_sl.valueChanged.connect(lambda val: self.canvas.set_layer_prop(opacity=val / 100.0))
        orow.addWidget(self.opacity_sl, 1); v.addLayout(orow)
        self.layer_list = QListWidget()
        self.layer_list.currentRowChanged.connect(self._layer_row_changed)
        self.layer_list.itemChanged.connect(self._layer_item_changed)
        self.layer_list.itemDoubleClicked.connect(self._rename_layer)
        v.addWidget(self.layer_list, 1)
        btns = QHBoxLayout()
        for glyph, tip, slot in (('＋', 'Add layer', lambda: self.canvas.add_layer()),
                                 ('⧉', 'Duplicate layer', lambda: self.canvas.duplicate_layer()),
                                 ('⌄', 'Merge down', lambda: self.canvas.merge_down()),
                                 ('↑', 'Move up', lambda: self.canvas.move_layer(1)),
                                 ('↓', 'Move down', lambda: self.canvas.move_layer(-1)),
                                 ('🗑', 'Delete layer', lambda: self.canvas.delete_layer())):
            b = QPushButton(glyph); b.setToolTip(tip); b.setFixedWidth(34); b.clicked.connect(slot); btns.addWidget(b)
        v.addLayout(btns)
        dock.setWidget(w); self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.layers_dock = dock

    def refresh_layers(self):
        if not hasattr(self, 'layer_list'): return
        self._layer_sync = True
        self.layer_list.clear()
        for l in reversed(self.canvas.layers):
            it = QListWidgetItem(l.name)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if l.visible else Qt.Unchecked)
            self.layer_list.addItem(it)
        n = len(self.canvas.layers)
        self.layer_list.setCurrentRow(n - 1 - self.canvas.active)
        al = self.canvas.layers[self.canvas.active]
        self.opacity_sl.setValue(int(al.opacity * 100))
        self.blend_cb.setCurrentIndex(BLEND_NAMES.index(al.blend) if al.blend in BLEND_NAMES else 0)
        self._layer_sync = False

    def _layer_row_changed(self, row):
        if self._layer_sync or row < 0: return
        self.canvas.set_active(len(self.canvas.layers) - 1 - row)

    def _layer_item_changed(self, item):
        if self._layer_sync: return
        idx = len(self.canvas.layers) - 1 - self.layer_list.row(item)
        if 0 <= idx < len(self.canvas.layers):
            self.canvas.layers[idx].visible = (item.checkState() == Qt.Checked); self.canvas.update()

    def _rename_layer(self, item):
        idx = len(self.canvas.layers) - 1 - self.layer_list.row(item)
        name, ok = QInputDialog.getText(self, 'Rename Layer', 'Layer name:', text=self.canvas.layers[idx].name)
        if ok and name.strip():
            self.canvas.layers[idx].name = name.strip(); self.refresh_layers()

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
        self.wand_lbl = QLabel(' Wand tol ')
        self.wand_spin = QSpinBox(); self.wand_spin.setRange(0, 255); self.wand_spin.setValue(int(self.canvas.wand_tol))
        self.wand_spin.setToolTip('Magic-wand colour tolerance')
        self.wand_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'wand_tol', v))
        self.wand_cb = QCheckBox('Contiguous'); self.wand_cb.setChecked(self.canvas.wand_contiguous)
        self.wand_cb.setToolTip('Select only the connected region, not every matching pixel')
        self.wand_cb.toggled.connect(lambda on: setattr(self.canvas, 'wand_contiguous', on))
        for wdg in (self.wand_lbl, self.wand_spin, self.wand_cb):
            top.addWidget(wdg); wdg.setVisible(False)
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
        img.addAction(self.act('&Straighten…', self.dlg_straighten))
        img.addSeparator()
        img.addAction(self.act('Rotate 90° &Right', lambda: self.canvas.rotate(90)))
        img.addAction(self.act('Rotate 90° &Left', lambda: self.canvas.rotate(-90)))
        img.addAction(self.act('Rotate &180°', lambda: self.canvas.rotate(180)))
        img.addAction(self.act('Flip &Horizontal', lambda: self.canvas.flip(True)))
        img.addAction(self.act('Flip &Vertical', lambda: self.canvas.flip(False)))
        img.addSeparator()
        img.addAction(self.act('Cu&tout Studio… (remove background)', self.cutout_studio))

        adj = m.addMenu('&Adjust')
        adj.addAction(self.act('&Brightness / Contrast…', self.dlg_brightness))
        adj.addAction(self.act('&Levels…', self.dlg_levels))
        adj.addAction(self.act('Cur&ves…', self.dlg_curves))
        adj.addAction(self.act('&Hue / Saturation…', self.dlg_huesat))
        adj.addAction(self.act('Colour &Temperature…', self.dlg_temperature))
        adj.addAction(self.act('Colour &Balance…', self.dlg_colorbalance))
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
        sel.addSeparator()
        sel.addAction(self.act('&Invert', self.sel_invert, 'Ctrl+Shift+I'))
        sel.addAction(self.act('&Feather…', self.dlg_feather))
        sel.addAction(self.act('&Grow…', lambda: self.dlg_grow(1)))
        sel.addAction(self.act('S&hrink…', lambda: self.dlg_grow(-1)))

        lay = m.addMenu('&Layer')
        lay.addAction(self.act('&New Layer', lambda: self.canvas.add_layer()))
        lay.addAction(self.act('&Duplicate Layer', lambda: self.canvas.duplicate_layer()))
        lay.addAction(self.act('&Merge Down', lambda: self.canvas.merge_down()))
        lay.addAction(self.act('De&lete Layer', lambda: self.canvas.delete_layer()))

        fx = m.addMenu('Effe&cts')
        fx.addAction(self.act('Drop &Shadow…', lambda: self._fx_dialog('shadow')))
        fx.addAction(self.act('Outer &Glow…', lambda: self._fx_dialog('glow')))
        h = m.addMenu('&Help')
        h.addAction(self.act('&Quick Start', self.open_quickstart))
        h.addAction(self.act('&User Guide', self.open_manual))
        h.addAction(self.act('&About', self.about))

    def act(self, text, slot, sc=None):
        a = QAction(text, self);  a.triggered.connect(slot)
        if sc: a.setShortcut(sc)
        return a

    def load_bundled_fonts(self):
        """Register the display/script fonts shipped in fonts/ so they're offered in the
        Text tool's font picker (shared with the rest of the just a... suite)."""
        from PySide6.QtGui import QFontDatabase
        self.bundled_fonts = []
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(('.ttf', '.otf')):
                    QFontDatabase.addApplicationFont(os.path.join(d, fn))

    def ask_text(self):
        """Prompt for text, font and size before stamping it onto the canvas."""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                                       QSpinBox, QFontComboBox, QDialogButtonBox)
        dlg = QDialog(self); dlg.setWindowTitle('Add Text'); dlg.resize(440, 180)
        v = QVBoxLayout(dlg)
        le = QLineEdit(); le.setPlaceholderText('Text to add…')
        fc = QFontComboBox(); fc.setCurrentFont(QFont(getattr(self, '_text_font', 'Noto Sans')))
        sp = QSpinBox(); sp.setRange(6, 400); sp.setSuffix(' px'); sp.setValue(getattr(self, '_text_px', max(16, self.canvas.size * 4)))
        form = QFormLayout(); form.addRow('Text:', le); form.addRow('Font:', fc); form.addRow('Size:', sp)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        le.setFocus()
        if dlg.exec() != QDialog.Accepted or not le.text().strip():
            return None
        self._text_font = fc.currentFont().family(); self._text_px = sp.value()
        return (le.text(), self._text_font, self._text_px)

    def cutout_studio(self):
        """Remove a background to transparency: click it with the Cutout tool, or
        auto-remove the background that touches the edges."""
        from PySide6.QtWidgets import QSlider, QVBoxLayout, QHBoxLayout, QPushButton, QDialogButtonBox
        if not self.canvas.img.hasAlphaChannel():
            self.canvas.layers[self.canvas.active].img = self.canvas.img.convertToFormat(QImage.Format_ARGB32)
            self.canvas.update()
        dlg = QDialog(self); dlg.setWindowTitle('Cutout Studio'); dlg.resize(400, 240)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel('<b>Remove a background to transparency.</b>'))
        info = QLabel('Pick the <b>Cutout</b> tool, then click the background colour to erase it. '
                      'Raise the tolerance to catch more shades; lower it to protect the edges of your subject.')
        info.setWordWrap(True); v.addWidget(info)
        v.addWidget(QLabel('Tolerance:'))
        row = QHBoxLayout(); s = QSlider(Qt.Horizontal); s.setRange(0, 100); s.setValue(int(self.canvas.cutout_tol))
        val = QLabel(str(int(self.canvas.cutout_tol)))
        s.valueChanged.connect(lambda x: (setattr(self.canvas, 'cutout_tol', x), val.setText(str(x))))
        row.addWidget(s, 1); row.addWidget(val); v.addLayout(row)
        be = QPushButton('Remove background from the edges now')
        be.clicked.connect(lambda: self.canvas.remove_bg_edges(self.canvas.cutout_tol))
        v.addWidget(be)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.reject); bb.accepted.connect(dlg.accept)
        v.addWidget(bb)
        self.set_tool('cutout')
        dlg.exec()

    # ---- state ----
    def set_tool(self, t):
        self.canvas.tool = t
        if hasattr(self, 'wand_spin'):
            for wdg in (self.wand_lbl, self.wand_spin, self.wand_cb):
                wdg.setVisible(t == 'wand')
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

    def dlg_curves(self):
        if self._need_pil():
            CurvesDialog(self).exec()

    def sel_invert(self):
        if self._need_pil():
            if self.canvas.sel is None:
                QMessageBox.information(self, APP, 'Make a selection first, then invert it.'); return
            self.canvas.invert_sel()

    def dlg_feather(self):
        if not self._need_pil(): return
        if self.canvas.sel is None:
            QMessageBox.information(self, APP, 'Make a selection first, then feather its edges.'); return
        r, ok = QInputDialog.getInt(self, 'Feather Selection', 'Soften edges by (px):', 8, 1, 300)
        if ok: self.canvas.feather_sel(r)

    def dlg_grow(self, sign):
        if not self._need_pil(): return
        if self.canvas.sel is None:
            QMessageBox.information(self, APP, 'Make a selection first.'); return
        label = 'Grow' if sign > 0 else 'Shrink'
        r, ok = QInputDialog.getInt(self, f'{label} Selection', f'{label} by (px):', 4, 1, 300)
        if ok: self.canvas.grow_sel(sign * r)

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

    def dlg_colorbalance(self):
        if self._need_pil():
            AdjustDialog(self, 'Colour Balance',
                         [('cr', 'Cyan — Red:', -100, 100, 0, 1.0), ('mg', 'Magenta — Green:', -100, 100, 0, 1.0),
                          ('yb', 'Yellow — Blue:', -100, 100, 0, 1.0)],
                         lambda v: adj_colorbalance(v['cr'], v['mg'], v['yb'])).exec()

    def dlg_straighten(self):
        ang, ok = QInputDialog.getDouble(self, 'Straighten', 'Rotate by angle (°):', 0.0, -45.0, 45.0, 1)
        if ok and abs(ang) > 0.001: self.canvas.straighten(ang)

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
        img = self.canvas.composited()          # flatten all layers for export
        if path.lower().endswith(('.jpg', '.jpeg')):
            flat = QImage(img.size(), QImage.Format_RGB32); flat.fill(QColor('#ffffff'))
            p = QPainter(flat); p.drawImage(0, 0, img); p.end(); img = flat
        if img.save(path):
            self.status.showMessage(f'Saved to {path}', 4000); _justapps_recent('paint', path)
        else:
            QMessageBox.warning(self, APP, "Couldn't save the image.")

    def open_manual(self):
        self._open_help(MANUAL)

    def open_quickstart(self):
        self._open_help(QUICKSTART)

    def _open_help(self, path):
        """Open a bundled HTML guide in an in-app window (falls back to the browser)."""
        _p = path
        if os.path.isfile(_p):
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                from PySide6.QtWidgets import QDialog, QVBoxLayout
                from PySide6.QtCore import QUrl as _U, Qt as _Qt
                _dlg = QDialog(self); _dlg.setWindowTitle('just a... PAINTcanvas — Help'); _dlg.setWindowFlag(_Qt.Window, True); _dlg.resize(920, 840)
                _lay = QVBoxLayout(_dlg); _lay.setContentsMargins(0, 0, 0, 0)
                if _p.lower().endswith(".pdf"):
                    from PySide6.QtPdf import QPdfDocument
                    from PySide6.QtPdfWidgets import QPdfView
                    _pd = QPdfDocument(_dlg); _pd.load(_p)
                    _v = QPdfView(_dlg); _v.setDocument(_pd)
                    _v.setPageMode(QPdfView.PageMode.MultiPage); _v.setZoomMode(QPdfView.ZoomMode.FitToWidth)
                    self._doc_wins = getattr(self, "_doc_wins", []) + [_pd]
                else:
                    _v = QWebEngineView(_dlg); _v.load(_U.fromLocalFile(os.path.abspath(_p)))
                _lay.addWidget(_v)
                _dlg.show(); self._doc_wins = getattr(self, "_doc_wins", []) + [_dlg]; return
            except Exception:
                pass
        import shutil as _sh, subprocess as _sp
        _t = _p if os.path.isfile(_p) else "https://janszafranski.github.io/just-a-collection-of-apps/"
        _op = _sh.which("xdg-open")
        if _op:
            try:
                _sp.Popen([_op, _t], start_new_session=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL); return
            except Exception:
                pass
        from PySide6.QtGui import QDesktopServices as _QDS
        from PySide6.QtCore import QUrl as _U2
        _QDS.openUrl(_U2.fromLocalFile(_t) if os.path.isfile(_t) else _U2(_t))

    def about(self):
        QMessageBox.about(self, f'About {APP}',
                          f'<b>{APP}</b><br>Version {VERSION}<br><br>A tiny raster image editor — paint, '
                          'shapes, fill, text and save a PNG/JPG.<br>The companion to just a… PAGEdesigner '
                          'and WEBcreator.')


def letter_icon(glyph, size=22):
    # Draw the glyph in the CURRENT THEME's text colour so the tool icons are
    # visible on both light desktops (e.g. Mint) and dark ones — a hard-coded
    # light grey was invisible on a light toolbar.
    from PySide6.QtGui import QPalette
    app = QApplication.instance()
    col = app.palette().color(QPalette.WindowText) if app else QColor('#2b3238')
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(col)
    f = QFont('Noto Sans'); f.setPixelSize(int(size * 0.72)); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, glyph); p.end()
    return QIcon(pm)


def main():
    QApplication.setDesktopFileName('paint')
    app = QApplication(sys.argv)
    app.setApplicationName('PAINTcanvas'); app.setApplicationDisplayName(APP)
    app.setOrganizationName(ORG); app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon.fromTheme('paint'))
    w = Main()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and os.path.isfile(args[0]):
        img = QImage(args[0])
        if not img.isNull(): w.canvas.load(img); w.path = args[0]; w.update_title(); _justapps_recent('paint', args[0])
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
