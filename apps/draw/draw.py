#!/usr/bin/env python3
# just a... DRAWmaster — a tiny VECTOR drawing app: shapes, lines, freehand paths
# and polylines, each with a fill and an outline, saved as SVG (infinitely scalable)
# or PNG. The vector sibling of just a... PAINTcanvas (raster) and companion to the
# page/web designers.
import sys, os, copy, math

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QColorDialog,
                                   QFileDialog, QMessageBox, QSpinBox, QLabel, QDialog, QVBoxLayout,
                                   QHBoxLayout, QPushButton, QComboBox, QScrollArea, QDockWidget,
                                   QListWidget, QListWidgetItem, QLineEdit, QFontComboBox, QInputDialog)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QFont, QFontMetricsF, QPainterPath, QActionGroup, QPolygonF,
                               QLinearGradient, QRadialGradient)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings
    from PySide6.QtSvg import QSvgGenerator
except ImportError:
    sys.stderr.write("just a... DRAWmaster needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... DRAWmaster"
ORG = "justadrawmaster"
VERSION = "1.4-00"
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


# ---------------------------------------------------------------- QuickShapes
QUICKSHAPES = [
    ('triangle', 'Triangle'), ('rtriangle', 'Right triangle'), ('diamond', 'Diamond'),
    ('pentagon', 'Pentagon'), ('hexagon', 'Hexagon'), ('octagon', 'Octagon'),
    ('star5', 'Star (5-point)'), ('star6', 'Star (6-point)'), ('arrow', 'Arrow'),
    ('darrow', 'Double arrow'), ('chevron', 'Chevron'), ('plus', 'Cross'),
    ('parallelogram', 'Parallelogram'), ('trapezoid', 'Trapezoid'), ('heart', 'Heart'),
    ('lightning', 'Lightning bolt'), ('speech', 'Speech bubble'), ('cloud', 'Cloud'),
]
QS_KEYS = [k for k, _ in QUICKSHAPES]

def _qs_poly(pts):
    pp = QPainterPath(); pp.addPolygon(QPolygonF([QPointF(x, y) for x, y in pts])); pp.closeSubpath(); return pp

def quickshape_path(name, w, h):
    cx, cy = w / 2, h / 2
    if name == 'triangle':  return _qs_poly([(cx, 0), (w, h), (0, h)])
    if name == 'rtriangle': return _qs_poly([(0, 0), (0, h), (w, h)])
    if name == 'diamond':   return _qs_poly([(cx, 0), (w, cy), (cx, h), (0, cy)])
    if name in ('pentagon', 'hexagon', 'octagon'):
        n = {'pentagon': 5, 'hexagon': 6, 'octagon': 8}[name]; off = -math.pi / 2
        return _qs_poly([(cx + cx * math.cos(off + i * 2 * math.pi / n),
                          cy + cy * math.sin(off + i * 2 * math.pi / n)) for i in range(n)])
    if name in ('star5', 'star6'):
        n = 5 if name == 'star5' else 6; off = -math.pi / 2; inner = 0.42 if n == 5 else 0.5
        pts = []
        for i in range(n * 2):
            k = 1.0 if i % 2 == 0 else inner; a = off + i * math.pi / n
            pts.append((cx + cx * k * math.cos(a), cy + cy * k * math.sin(a)))
        return _qs_poly(pts)
    if name == 'arrow':
        return _qs_poly([(0, h * .3), (w * .6, h * .3), (w * .6, 0), (w, cy),
                         (w * .6, h), (w * .6, h * .7), (0, h * .7)])
    if name == 'darrow':
        return _qs_poly([(0, cy), (w * .25, 0), (w * .25, h * .3), (w * .75, h * .3), (w * .75, 0),
                         (w, cy), (w * .75, h), (w * .75, h * .7), (w * .25, h * .7), (w * .25, h)])
    if name == 'chevron':
        return _qs_poly([(0, 0), (w * .6, 0), (w, cy), (w * .6, h), (0, h), (w * .4, cy)])
    if name == 'plus':
        t = 1 / 3
        return _qs_poly([(w * t, 0), (w * (1 - t), 0), (w * (1 - t), h * t), (w, h * t), (w, h * (1 - t)),
                         (w * (1 - t), h * (1 - t)), (w * (1 - t), h), (w * t, h), (w * t, h * (1 - t)),
                         (0, h * (1 - t)), (0, h * t), (w * t, h * t)])
    if name == 'parallelogram': return _qs_poly([(w * .25, 0), (w, 0), (w * .75, h), (0, h)])
    if name == 'trapezoid':     return _qs_poly([(w * .25, 0), (w * .75, 0), (w, h), (0, h)])
    if name == 'lightning':
        return _qs_poly([(w * .55, 0), (w * .1, h * .55), (w * .45, h * .55), (w * .3, h),
                         (w * .9, h * .4), (w * .52, h * .4)])
    if name == 'heart':
        pp = QPainterPath(); pp.moveTo(w * .5, h * .25)
        pp.cubicTo(w * .5, h * .1, w * .1, h * .1, w * .1, h * .35)
        pp.cubicTo(w * .1, h * .55, w * .35, h * .7, w * .5, h * .9)
        pp.cubicTo(w * .65, h * .7, w * .9, h * .55, w * .9, h * .35)
        pp.cubicTo(w * .9, h * .1, w * .5, h * .1, w * .5, h * .25); pp.closeSubpath(); return pp
    if name == 'speech':
        bh = h * .78; rad = min(w, bh) * .18
        pp = QPainterPath(); pp.addRoundedRect(QRectF(0, 0, w, bh), rad, rad)
        tail = QPainterPath(); tail.moveTo(w * .28, bh - 1); tail.lineTo(w * .2, h); tail.lineTo(w * .5, bh - 1)
        tail.closeSubpath(); return pp.united(tail)
    if name == 'cloud':
        def _ell(x, y, ww, hh):
            q = QPainterPath(); q.addEllipse(QRectF(x, y, ww, hh)); return q
        pp = _ell(w * .04, h * .45, w * .44, h * .48)
        for rc in [(w * .18, h * .12, w * .42, h * .62), (w * .44, h * .22, w * .40, h * .54),
                   (w * .52, h * .45, w * .44, h * .48)]:
            pp = pp.united(_ell(*rc))
        return pp.simplified()
    pp = QPainterPath(); pp.addRect(QRectF(0, 0, w, h)); return pp

# ---------------------------------------------------------------- Object effects
def obj_silhouette(o):
    """(path in local 0-based coords, world x, world y, w, h) for drop-shadow/glow."""
    t = o['type']; pp = QPainterPath()
    if t == 'rect': pp.addRect(QRectF(0, 0, o['w'], o['h']))
    elif t == 'ellipse': pp.addEllipse(QRectF(0, 0, o['w'], o['h']))
    elif t == 'quick': pp = quickshape_path(o['shape'], o['w'], o['h'])
    elif t == 'text':
        fm = QFontMetricsF(text_font(o))
        pp.addText(0, fm.ascent(), text_font(o), o.get('text', ''))
        br = pp.boundingRect(); pp.translate(-br.x(), -br.y())
        return pp, o['x'] + br.x(), o['y'] + br.y(), br.width() or 1, br.height() or 1
    elif t in ('line', 'path', 'poly'):
        from PySide6.QtGui import QPainterPathStroker
        r = obj_rect(o); poly = QPolygonF([QPointF(x - r.x(), y - r.y()) for x, y in o['pts']])
        base = QPainterPath(); base.addPolygon(poly)
        if o.get('closed'): base.closeSubpath()
        if o.get('closed') and o.get('fill'):
            pp = base
        else:
            stk = QPainterPathStroker(); stk.setWidth(max(2, o.get('sw', 2)))
            stk.setCapStyle(Qt.RoundCap); stk.setJoinStyle(Qt.RoundJoin); pp = stk.createStroke(base)
        br = pp.boundingRect()
        return pp.translated(-br.x(), -br.y()), r.x() + br.x(), r.y() + br.y(), br.width(), br.height()
    else:
        return None, 0, 0, 0, 0
    return pp, o['x'], o['y'], o['w'], o['h']

def _fx_image(path, w, h, color, blur, pad):
    W, H = int(w + 2 * pad), int(h + 2 * pad)
    base = QImage(W, H, QImage.Format_ARGB32_Premultiplied); base.fill(Qt.transparent)
    q = QPainter(base); q.setRenderHint(QPainter.Antialiasing)
    q.translate(pad, pad); q.setPen(Qt.NoPen); q.setBrush(QColor(color)); q.drawPath(path); q.end()
    if blur <= 0: return base
    f = max(2, int(round(blur / 1.5)))
    small = base.scaled(max(1, W // f), max(1, H // f), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return small.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

def draw_object_fx(p, o):
    sh = o.get('shadow'); gl = o.get('glow')
    if not sh and not gl: return
    sil, ox, oy, w, h = obj_silhouette(o)
    if sil is None or w < 1 or h < 1: return
    def stamp(color, blur, dx, dy, op, twice=False):
        pad = int(blur) + 6; img = _fx_image(sil, w, h, color, blur, pad)
        p.save(); p.setOpacity(p.opacity() * op / 100.0)
        p.drawImage(QPointF(ox + dx - pad, oy + dy - pad), img)
        if twice: p.drawImage(QPointF(ox + dx - pad, oy + dy - pad), img)
        p.restore()
    if gl: stamp(gl.get('color', '#ffe08a'), max(1, gl.get('blur', 12)), 0, 0, gl.get('opacity', 70), True)
    if sh: stamp(sh.get('color', '#000000'), max(0, sh.get('blur', 8)), sh.get('dx', 6), sh.get('dy', 6), sh.get('opacity', 45))


def text_font(o):
    """The QFont for a text object (family + pixel size)."""
    f = QFont(o.get('family', 'Noto Sans')); f.setPixelSize(max(1, int(o.get('size', 48)))); return f

def text_size(o):
    """(width, height) of a text object's drawn box, measured from its font."""
    fm = QFontMetricsF(text_font(o))
    br = fm.boundingRect(o.get('text', ''))
    return max(1.0, br.width()), max(1.0, fm.height())


def obj_rect(o):
    t = o['type']
    if t in ('rect', 'ellipse', 'quick'):
        return QRectF(o['x'], o['y'], o['w'], o['h']).normalized()
    if t == 'text':
        tw, th = text_size(o)
        return QRectF(o['x'], o['y'], tw, th)
    xs = [p[0] for p in o['pts']]; ys = [p[1] for p in o['pts']]
    return QRectF(min(xs), min(ys), max(xs) - min(xs) or 1, max(ys) - min(ys) or 1)


def fill_brush(o):
    """The fill brush for an object — a gradient (grad dict) or a flat colour.
    Gradients are mapped across the object's bounding box, so they render the same
    on screen, in PNG and (via the SVG defs) in a browser. Mirrors PAGEdesigner."""
    g = o.get('grad')
    if g:
        r = obj_rect(o); w = r.width() or 1; h = r.height() or 1
        if g.get('type') == 'radial':
            rg = QRadialGradient(r.x() + w / 2, r.y() + h / 2, max(w, h) / 2)
            rg.setColorAt(0, QColor(g.get('c1', '#ffffff'))); rg.setColorAt(1, QColor(g.get('c2', '#000000')))
            return QBrush(rg)
        ang = math.radians(g.get('angle', 90)); cx, cy = r.x() + w / 2, r.y() + h / 2
        dx, dy = math.cos(ang), math.sin(ang)
        lg = QLinearGradient(cx - dx * w / 2, cy - dy * h / 2, cx + dx * w / 2, cy + dy * h / 2)
        lg.setColorAt(0, QColor(g.get('c1', '#ffffff'))); lg.setColorAt(1, QColor(g.get('c2', '#000000')))
        return QBrush(lg)
    return QBrush(QColor(o['fill'])) if o.get('fill') else QBrush(Qt.NoBrush)


def svg_grad_def(g, gid):
    """A <linearGradient>/<radialGradient> def (objectBoundingBox) for the given grad dict."""
    if g.get('type') == 'radial':
        return (f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">'
                f'<stop offset="0%" stop-color="{g.get("c1", "#fff")}"/>'
                f'<stop offset="100%" stop-color="{g.get("c2", "#000")}"/></radialGradient>')
    rad = math.radians(g.get('angle', 90))
    x1, y1 = 50 - 50 * math.cos(rad), 50 - 50 * math.sin(rad)
    x2, y2 = 50 + 50 * math.cos(rad), 50 + 50 * math.sin(rad)
    return (f'<linearGradient id="{gid}" x1="{x1:.1f}%" y1="{y1:.1f}%" x2="{x2:.1f}%" y2="{y2:.1f}%">'
            f'<stop offset="0%" stop-color="{g.get("c1", "#fff")}"/>'
            f'<stop offset="100%" stop-color="{g.get("c2", "#000")}"/></linearGradient>')


def svg_text_el(o, idx=0):
    """A real SVG <text> element for a text object — font-family/size/fill, baseline at
    the object's ascent, so it renders in any browser and round-trips (the full editable
    model also rides along in the SVG <desc>). Returns (defs, element): a gradient-filled
    text carries its own <linearGradient>/<radialGradient> def."""
    import html as _H
    fm = QFontMetricsF(text_font(o))
    x = o['x']; y = o['y'] + fm.ascent()
    fam = _H.escape(o.get('family', 'Noto Sans'), quote=True)
    sz = max(1, int(o.get('size', 48)))
    g = o.get('grad'); defs = ''
    if g:
        gid = f'txtgrad{idx}'; defs = svg_grad_def(g, gid); fill = f'url(#{gid})'
    else:
        fill = o.get('fill') or 'none'
    stroke = f' stroke="{o["stroke"]}" stroke-width="{o.get("sw", 2)}"' if o.get('stroke') else ''
    body = _H.escape(o.get('text', ''))
    el = (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{fam}" font-size="{sz}" '
          f'fill="{fill}"{stroke} xml:space="preserve">{body}</text>')
    return defs, el


def paint_object(p, o, selected=False, skip_text=False):
    if skip_text and o.get('type') == 'text':
        draw_object_fx(p, o); return   # keep shadow/glow; the SVG <text> draws the glyphs
    draw_object_fx(p, o)
    pen = QPen(QColor(o['stroke']), o.get('sw', 2)) if o.get('stroke') else QPen(Qt.NoPen)
    pen.setJoinStyle(Qt.RoundJoin); pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(fill_brush(o))
    t = o['type']
    if t == 'rect':
        p.drawRect(QRectF(o['x'], o['y'], o['w'], o['h']))
    elif t == 'ellipse':
        p.drawEllipse(QRectF(o['x'], o['y'], o['w'], o['h']))
    elif t == 'quick':
        p.save(); p.translate(o['x'], o['y']); p.drawPath(quickshape_path(o['shape'], o['w'], o['h'])); p.restore()
    elif t == 'text':
        # Draw glyphs as a filled path so a fill/gradient/outline all apply, and so
        # it renders identically offscreen (a bare QPainter.drawText can misbehave
        # headless). Baseline sits at the font ascent inside the object's box.
        fm = QFontMetricsF(text_font(o)); tp = QPainterPath()
        tp.addText(o['x'], o['y'] + fm.ascent(), text_font(o), o.get('text', ''))
        if not o.get('stroke'): p.setPen(Qt.NoPen)
        p.drawPath(tp)
    elif t in ('line', 'path', 'poly'):
        poly = QPolygonF([QPointF(x, y) for x, y in o['pts']])
        if o.get('fill') and len(o['pts']) > 2:
            path = QPainterPath(); path.addPolygon(poly)
            if o.get('closed'): path.closeSubpath()
            p.drawPath(path)
        else:
            p.drawPolyline(poly) if not o.get('closed') else p.drawPolygon(poly)
    if selected:
        r = obj_rect(o).adjusted(-3, -3, 3, 3)
        sp = QPen(QColor('#2a7df0'), 1, Qt.DashLine); sp.setCosmetic(True)
        p.setPen(sp); p.setBrush(Qt.NoBrush); p.drawRect(r)


class Canvas(QWidget):
    def __init__(self, win, w=1000, h=700):
        super().__init__()
        self.win = win
        self.W, self.H = w, h
        self.zoom = 1.0
        self.objs = []
        # Layers: metadata kept apart from the flat object list for backward compatibility.
        # Each object carries o['layer'] = a layer id; the list order within a layer is the
        # z-order. Paint = each visible layer in order, its objects in list order.
        self.layers = [{'id': 1, 'name': 'Layer 1', 'visible': True}]
        self._next_layer = 2
        self.active_layer = 1
        self.sel = None
        self.tool = 'select'
        self.fill = QColor('#cfe3ef'); self.stroke = QColor('#1f2a30'); self.sw = 2
        self.quick_shape = 'star5'
        self.start = None; self.cur = None; self.drag_off = None; self.poly_pts = None
        self.undo, self.redo = [], []
        self.setMouseTracking(True); self.setCursor(Qt.CrossCursor); self._fit()

    def _fit(self):
        self.setMinimumSize(int(self.W * self.zoom), int(self.H * self.zoom)); self.resize(self.minimumSize()); self.update()

    def snapshot(self):
        self.undo.append(copy.deepcopy(self.objs))
        if len(self.undo) > 60: self.undo.pop(0)
        self.redo.clear()

    def do_undo(self):
        if self.undo: self.redo.append(copy.deepcopy(self.objs)); self.objs = self.undo.pop(); self.sel = None; self.update()

    def do_redo(self):
        if self.redo: self.undo.append(copy.deepcopy(self.objs)); self.objs = self.redo.pop(); self.sel = None; self.update()

    def set_zoom(self, z): self.zoom = max(0.1, min(16, z)); self._fit()

    # ---------------------------------------------------------------- layers / z-order
    def _layer_ids(self):
        return [ly['id'] for ly in self.layers]

    def obj_layer(self, o):
        """The layer id an object belongs to — falling back to the first layer so old
        files (and objects without a 'layer' key) always have somewhere to live."""
        lid = o.get('layer')
        return lid if lid in self._layer_ids() else self.layers[0]['id']

    def ordered_objs(self, visible_only=True):
        """Objects in paint order: each layer (bottom→top), its objects in list order."""
        out = []
        for ly in self.layers:
            if visible_only and not ly.get('visible', True): continue
            out += [o for o in self.objs if self.obj_layer(o) == ly['id']]
        return out

    def reset_layers(self):
        self.layers = [{'id': 1, 'name': 'Layer 1', 'visible': True}]
        self._next_layer = 2; self.active_layer = 1

    def restore_layers(self, layers):
        """Rebuild the layer stack from a loaded file, or synthesise one for an older
        file (no 'layers' key) so every object still has a home layer."""
        if layers:
            self.layers = [{'id': ly.get('id'), 'name': ly.get('name', 'Layer'),
                            'visible': ly.get('visible', True)} for ly in layers if ly.get('id') is not None]
        if not self.layers:
            self.reset_layers()
        self._next_layer = max([ly['id'] for ly in self.layers] + [0]) + 1
        self.active_layer = self.layers[0]['id']

    def add_layer(self):
        self.snapshot()
        lid = self._next_layer; self._next_layer += 1
        self.layers.append({'id': lid, 'name': f'Layer {lid}', 'visible': True})
        self.active_layer = lid; self.update(); return lid

    def delete_layer(self, lid):
        if len(self.layers) <= 1: return
        self.snapshot()
        self.objs = [o for o in self.objs if self.obj_layer(o) != lid]
        self.layers = [ly for ly in self.layers if ly['id'] != lid]
        if self.active_layer == lid: self.active_layer = self.layers[0]['id']
        if self.sel is not None and self.sel not in self.objs: self.sel = None
        self.update()

    def rename_layer(self, lid, name):
        for ly in self.layers:
            if ly['id'] == lid: ly['name'] = name
        self.update()

    def toggle_layer(self, lid, vis):
        for ly in self.layers:
            if ly['id'] == lid: ly['visible'] = bool(vis)
        self.update()

    def move_layer(self, lid, delta):
        """Shuffle a layer up/down the stack (delta -1 = down in paint order)."""
        i = next((k for k, ly in enumerate(self.layers) if ly['id'] == lid), None)
        if i is None: return
        j = max(0, min(len(self.layers) - 1, i + delta))
        if i == j: return
        self.snapshot(); self.layers.insert(j, self.layers.pop(i)); self.update()

    def sel_to_layer(self, lid):
        if self.sel is None: return
        self.snapshot(); self.sel['layer'] = lid; self.update()

    def z_order(self, where):
        """Move the selected object within self.objs: 'front'/'back'/'forward'/'backward'."""
        o = self.sel
        if o is None or o not in self.objs: return
        self.snapshot(); i = self.objs.index(o); self.objs.remove(o)
        if where == 'front': self.objs.append(o)
        elif where == 'back': self.objs.insert(0, o)
        elif where == 'forward': self.objs.insert(min(len(self.objs), i + 1), o)
        elif where == 'backward': self.objs.insert(max(0, i - 1), o)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#e9ebee'))
        p.fillRect(QRectF(0, 0, self.W * self.zoom, self.H * self.zoom), QColor('#ffffff'))
        p.scale(self.zoom, self.zoom)
        for o in self.ordered_objs():
            paint_object(p, o, o is self.sel)
        if self.start and self.cur and self.tool in ('rect', 'ellipse', 'line', 'quick'):
            tmp = self._shape_from(self.start, self.cur)
            if tmp: paint_object(p, tmp)
        if self.poly_pts and len(self.poly_pts) >= 1:
            prev = {'type': 'poly', 'pts': self.poly_pts + ([self.cur] if self.cur else []),
                    'stroke': self.stroke.name(), 'sw': self.sw, 'fill': None, 'closed': False}
            paint_object(p, prev)
        p.end()

    def pos(self, e):
        return (e.position().x() / self.zoom, e.position().y() / self.zoom)

    def _shape_from(self, a, b):
        x1, y1 = a; x2, y2 = b
        base = dict(stroke=self.stroke.name(), sw=self.sw, fill=self.fill.name() if self.tool != 'line' else None,
                    layer=self.active_layer)
        if self.tool == 'line':
            return dict(type='line', pts=[a, b], **base)
        if self.tool == 'quick':
            return dict(type='quick', shape=self.quick_shape, x=min(x1, x2), y=min(y1, y2),
                        w=abs(x2 - x1) or 1, h=abs(y2 - y1) or 1, **base)
        return dict(type=self.tool, x=min(x1, x2), y=min(y1, y2), w=abs(x2 - x1), h=abs(y2 - y1), **base)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        pt = self.pos(e)
        if self.tool == 'select':
            hit = next((o for o in reversed(self.ordered_objs()) if obj_rect(o).adjusted(-3, -3, 3, 3).contains(QPointF(*pt))), None)
            self.sel = hit
            if hit:
                r = obj_rect(hit); self.drag_off = (pt[0] - r.x(), pt[1] - r.y())
            self.update(); self.win.sync_props(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick'):
            self.start = pt; self.cur = pt; return
        if self.tool == 'text':
            self.win.place_text(pt); return
        if self.tool == 'freehand':
            self.snapshot()
            self.objs.append(dict(type='path', pts=[pt], stroke=self.stroke.name(), sw=self.sw, fill=None,
                                  closed=False, layer=self.active_layer))
            self.cur = pt; return
        if self.tool == 'pen':
            if self.poly_pts is None: self.snapshot(); self.poly_pts = []
            self.poly_pts.append(pt); self.cur = pt; self.update(); return

    def mouseMoveEvent(self, e):
        pt = self.pos(e); self.win.set_pos(pt)
        if self.tool == 'select' and self.sel is not None and (e.buttons() & Qt.LeftButton) and self.drag_off:
            if not self.undo or self.undo[-1] is not self.objs:
                pass
            self._move_sel(pt); self.update(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick') and self.start and (e.buttons() & Qt.LeftButton):
            self.cur = pt; self.update()
        elif self.tool == 'freehand' and (e.buttons() & Qt.LeftButton) and self.objs:
            self.objs[-1]['pts'].append(pt); self.update()
        elif self.tool == 'pen' and self.poly_pts is not None:
            self.cur = pt; self.update()

    def mousePressSnapMove(self): pass

    def _move_sel(self, pt):
        o = self.sel; r = obj_rect(o); nx = pt[0] - self.drag_off[0]; ny = pt[1] - self.drag_off[1]
        dx, dy = nx - r.x(), ny - r.y()
        if o['type'] in ('rect', 'ellipse', 'quick', 'text'):
            o['x'] += dx; o['y'] += dy
        else:
            o['pts'] = [(x + dx, y + dy) for x, y in o['pts']]

    def mouseReleaseEvent(self, e):
        if self.tool in ('rect', 'ellipse', 'line', 'quick') and self.start:
            if self.cur and (abs(self.cur[0] - self.start[0]) > 2 or abs(self.cur[1] - self.start[1]) > 2):
                self.snapshot(); self.objs.append(self._shape_from(self.start, self.cur)); self.sel = self.objs[-1]
            self.start = self.cur = None; self.update(); self.win.sync_props()
        elif self.tool == 'select' and self.sel is not None and self.drag_off:
            self.drag_off = None

    def mouseDoubleClickEvent(self, e):
        if self.tool == 'pen' and self.poly_pts and len(self.poly_pts) >= 2:
            self.objs.append(dict(type='poly', pts=self.poly_pts[:], stroke=self.stroke.name(), sw=self.sw,
                                  fill=self.fill.name(), closed=True, layer=self.active_layer))
            self.sel = self.objs[-1]; self.poly_pts = None; self.cur = None; self.update()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.sel is not None:
            self.snapshot(); self.objs.remove(self.sel); self.sel = None; self.update()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.tool == 'pen' and self.poly_pts and len(self.poly_pts) >= 2:
            self.objs.append(dict(type='poly', pts=self.poly_pts[:], stroke=self.stroke.name(), sw=self.sw,
                                  fill=None, closed=False, layer=self.active_layer))
            self.poly_pts = None; self.cur = None; self.update()

    def apply_to_sel(self, fill=None, stroke=None, sw=None):
        if self.sel is None: return
        self.snapshot()
        if fill is not None: self.sel['fill'] = fill; self.sel.pop('grad', None)  # a solid fill replaces any gradient
        if stroke is not None: self.sel['stroke'] = stroke
        if sw is not None: self.sel['sw'] = sw
        self.update()

    def render_to(self, painter, skip_text=False):
        for o in self.ordered_objs():
            paint_object(painter, o, False, skip_text=skip_text)

    def export_svg(self, path):
        import json, base64, re
        gen = QSvgGenerator(); gen.setFileName(path); gen.setSize(QSize(self.W, self.H))
        gen.setViewBox(QRect(0, 0, self.W, self.H)); gen.setTitle('just a... DRAWmaster')
        # Embed the editable object model so DRAWmaster can re-open its own SVGs losslessly.
        blob = base64.b64encode(json.dumps({'W': self.W, 'H': self.H, 'objs': self.objs,
                                             'layers': self.layers}).encode()).decode()
        gen.setDescription('justadraw1:' + blob)
        # QSvgGenerator renders shapes (gradients become <linearGradient>/<radialGradient>
        # natively) but turns glyphs into paths — so we skip text here and splice real
        # <text> elements in afterwards, in paint order, for an editable, browser-true SVG.
        p = QPainter(gen); p.setRenderHint(QPainter.Antialiasing); self.render_to(p, skip_text=True); p.end()
        tobjs = [o for o in self.ordered_objs() if o.get('type') == 'text']
        if tobjs:
            defs, els = [], []
            for i, o in enumerate(tobjs):
                d, e = svg_text_el(o, i)
                if d: defs.append(d)
                els.append(e)
            inject = (f'<defs>{"".join(defs)}</defs>' if defs else '') + ''.join(els)
            try:
                with open(path, encoding='utf-8') as fh: txt = fh.read()
                txt = re.sub(r'</svg>\s*$', inject + '</svg>\n', txt, count=1)
                with open(path, 'w', encoding='utf-8') as fh: fh.write(txt)
            except OSError:
                pass

    def load_svg(self, path):
        """True = opened an editable DRAWmaster SVG; None = foreign SVG; False = error."""
        import json, base64, re
        try:
            with open(path, encoding='utf-8', errors='replace') as fh: txt = fh.read()
        except OSError:
            return False
        m = re.search(r'<desc>(.*?)</desc>', txt, re.S)
        tag = (m.group(1).strip() if m else '')
        if not tag.startswith('justadraw1:'):
            return None
        try:
            data = json.loads(base64.b64decode(tag[len('justadraw1:'):]).decode())
            self.snapshot(); self.objs = data.get('objs', []); self.sel = None
            self.W = int(data.get('W', self.W)); self.H = int(data.get('H', self.H))
            self.restore_layers(data.get('layers')); self._fit()
            return True
        except Exception:
            return False

    def export_png(self, path):
        img = QImage(self.W, self.H, QImage.Format_ARGB32); img.fill(QColor('#ffffff'))
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); self.render_to(p); p.end()
        return img.save(path)


class Main(QMainWindow):
    TOOLS = [('select', 'Select', '⬚'), ('freehand', 'Freehand', '✎'), ('pen', 'Pen (polyline)', '✐'),
             ('line', 'Line', '╱'), ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'),
             ('quick', 'QuickShape', '★'), ('text', 'Text', 'T')]

    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, 'DRAWmaster')
        self.path = None
        self.canvas = Canvas(self)
        self.load_bundled_fonts()
        sa = QScrollArea(); sa.setWidget(self.canvas); sa.setAlignment(Qt.AlignCenter)
        sa.setStyleSheet('QScrollArea{background:#cfd4da;border:none}')
        self.setCentralWidget(sa)
        self.build_layers_dock()
        self.build_menu(); self.build_tools()
        self.setWindowTitle(APP); self.resize(1180, 820)
        self.pos_lbl = QLabel('  '); self.statusBar().addPermanentWidget(self.pos_lbl)
        self.refresh_layers()

    def load_bundled_fonts(self):
        """Register the display/script fonts shipped in fonts/ (shared with the rest of
        the just a... suite) so they're available desktop-wide."""
        from PySide6.QtGui import QFontDatabase
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(('.ttf', '.otf')):
                    QFontDatabase.addApplicationFont(os.path.join(d, fn))

    # ---------------------------------------------------------------- Layers panel
    def build_layers_dock(self):
        """A dock listing layers top (front) to bottom (back): add, delete, rename,
        show/hide, reorder, and move the selected object between layers."""
        from PySide6.QtWidgets import QCheckBox, QWidget as _W
        self.layers_dock = QDockWidget('Layers', self)
        self.layers_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable |
                                     QDockWidget.DockWidgetClosable)
        body = _W(); v = QVBoxLayout(body); v.setContentsMargins(6, 6, 6, 6)
        self.layer_list = QListWidget()
        self.layer_list.currentRowChanged.connect(self._layer_row_changed)
        self.layer_list.itemChanged.connect(self._layer_item_changed)
        v.addWidget(self.layer_list)
        row = QHBoxLayout()
        for txt, tip, slot in (('＋', 'Add a new layer', self._ui_add_layer),
                               ('－', 'Delete the current layer', self._ui_del_layer),
                               ('▲', 'Move layer up (towards front)', lambda: self._ui_move_layer(1)),
                               ('▼', 'Move layer down (towards back)', lambda: self._ui_move_layer(-1)),
                               ('✎', 'Rename the current layer', self._ui_rename_layer)):
            b = QPushButton(txt); b.setToolTip(tip); b.setFixedWidth(34); b.clicked.connect(slot); row.addWidget(b)
        v.addLayout(row)
        mv = QHBoxLayout(); mv.addWidget(QLabel('Selection →'))
        self.move_to_cb = QComboBox(); self.move_to_cb.setToolTip('Move the selected object to this layer')
        self.move_to_cb.activated.connect(self._ui_move_sel_to_layer); mv.addWidget(self.move_to_cb, 1)
        v.addLayout(mv)
        self.layers_dock.setWidget(body)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layers_dock)

    def refresh_layers(self):
        """Rebuild the layers list to match the canvas. The list shows layers front→back
        (so the top row is the frontmost), each with a show/hide checkbox."""
        c = self.canvas; lst = self.layer_list
        lst.blockSignals(True); lst.clear()
        for ly in reversed(c.layers):              # front (last painted) at the top
            it = QListWidgetItem(ly['name'])
            it.setData(Qt.UserRole, ly['id'])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if ly.get('visible', True) else Qt.Unchecked)
            lst.addItem(it)
            if ly['id'] == c.active_layer: lst.setCurrentItem(it)
        lst.blockSignals(False)
        self.move_to_cb.blockSignals(True); self.move_to_cb.clear()
        for ly in reversed(c.layers): self.move_to_cb.addItem(ly['name'], ly['id'])
        self.move_to_cb.blockSignals(False)

    def _cur_layer_id(self):
        it = self.layer_list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _layer_row_changed(self, _row):
        lid = self._cur_layer_id()
        if lid is not None: self.canvas.active_layer = lid

    def _layer_item_changed(self, it):
        lid = it.data(Qt.UserRole)
        if lid is not None:
            self.canvas.toggle_layer(lid, it.checkState() == Qt.Checked)

    def _ui_add_layer(self):
        self.canvas.add_layer(); self.refresh_layers()

    def _ui_del_layer(self):
        lid = self._cur_layer_id()
        if lid is not None: self.canvas.delete_layer(lid); self.refresh_layers()

    def _ui_move_layer(self, delta):
        lid = self._cur_layer_id()
        if lid is not None: self.canvas.move_layer(lid, delta); self.refresh_layers()

    def _ui_rename_layer(self):
        lid = self._cur_layer_id()
        if lid is None: return
        cur = next((ly['name'] for ly in self.canvas.layers if ly['id'] == lid), '')
        name, ok = QInputDialog.getText(self, 'Rename layer', 'Layer name:', text=cur)
        if ok and name.strip(): self.canvas.rename_layer(lid, name.strip()); self.refresh_layers()

    def _ui_move_sel_to_layer(self, _i):
        lid = self.move_to_cb.currentData()
        if lid is not None: self.canvas.sel_to_layer(lid)

    def build_tools(self):
        tt = QToolBar('Tools'); tt.setOrientation(Qt.Vertical); tt.setIconSize(QSize(22, 22))
        self.tg = QActionGroup(self); self.tool_acts = {}
        for tid, label, glyph in self.TOOLS:
            a = QAction(glyph_icon(glyph), label, self); a.setCheckable(True); a.setToolTip(label)
            a.triggered.connect(lambda _=0, t=tid: setattr(self.canvas, 'tool', t)); self.tg.addAction(a); tt.addAction(a)
            self.tool_acts[tid] = a
            if tid == 'select': a.setChecked(True)
        self.addToolBar(Qt.LeftToolBarArea, tt)
        top = QToolBar('Style'); top.setIconSize(QSize(18, 18)); self.addToolBar(Qt.TopToolBarArea, top)
        self.fill_btn = QPushButton('Fill'); self.fill_btn.clicked.connect(self.pick_fill); top.addWidget(self.fill_btn)
        self.stroke_btn = QPushButton('Line'); self.stroke_btn.clicked.connect(self.pick_stroke); top.addWidget(self.stroke_btn)
        top.addWidget(QLabel(' Width '))
        self.sw_spin = QSpinBox(); self.sw_spin.setRange(0, 80); self.sw_spin.setValue(self.canvas.sw); self.sw_spin.setSuffix(' px')
        self.sw_spin.valueChanged.connect(self.set_sw); top.addWidget(self.sw_spin)
        top.addSeparator()
        top.addSeparator()
        top.addWidget(QLabel(' Shape '))
        self.shape_cb = QComboBox()
        for k, lbl in QUICKSHAPES: self.shape_cb.addItem(lbl, k)
        self.shape_cb.setToolTip('QuickShape to draw — then drag on the canvas')
        self.shape_cb.activated.connect(self.pick_quickshape); top.addWidget(self.shape_cb)
        self.fx_btn = QPushButton('Effects…'); self.fx_btn.setToolTip('Drop shadow & glow on the selected object')
        self.fx_btn.clicked.connect(self.effects_dialog); top.addWidget(self.fx_btn)
        self.grad_btn = QPushButton('Gradient…'); self.grad_btn.setToolTip('Linear or radial gradient fill for the selected shape')
        self.grad_btn.clicked.connect(self.gradient_dialog); top.addWidget(self.grad_btn)
        top.addSeparator()
        for txt, slot in (('Zoom +', lambda: self.canvas.set_zoom(self.canvas.zoom * 1.25)),
                          ('Zoom −', lambda: self.canvas.set_zoom(self.canvas.zoom / 1.25)),
                          ('100%', lambda: self.canvas.set_zoom(1.0))):
            b = QPushButton(txt); b.clicked.connect(slot); top.addWidget(b)
        self._paint_btns()

    def pick_quickshape(self, i):
        self.canvas.quick_shape = self.shape_cb.itemData(i)
        self.canvas.tool = 'quick'; self.tool_acts['quick'].setChecked(True)

    def effects_dialog(self):
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first (the Select tool), then add effects.')
            return
        from PySide6.QtWidgets import QCheckBox, QFormLayout, QDialogButtonBox
        s0 = o.get('shadow') or {}; g0 = o.get('glow') or {}
        dlg = QDialog(self); dlg.setWindowTitle('Effects — Shadow & Glow'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        s_on = QCheckBox('Enable drop shadow'); s_on.setChecked(bool(o.get('shadow')))
        sdx = QSpinBox(); sdx.setRange(-100, 100); sdx.setSuffix(' px'); sdx.setValue(int(s0.get('dx', 6)))
        sdy = QSpinBox(); sdy.setRange(-100, 100); sdy.setSuffix(' px'); sdy.setValue(int(s0.get('dy', 6)))
        sbl = QSpinBox(); sbl.setRange(0, 80); sbl.setSuffix(' px'); sbl.setValue(int(s0.get('blur', 8)))
        sop = QSpinBox(); sop.setRange(0, 100); sop.setSuffix(' %'); sop.setValue(int(s0.get('opacity', 45)))
        scol = [s0.get('color', '#000000')]; scb = QPushButton('Shadow colour')
        g_on = QCheckBox('Enable outer glow'); g_on.setChecked(bool(o.get('glow')))
        gbl = QSpinBox(); gbl.setRange(1, 80); gbl.setSuffix(' px'); gbl.setValue(int(g0.get('blur', 12)))
        gop = QSpinBox(); gop.setRange(0, 100); gop.setSuffix(' %'); gop.setValue(int(g0.get('opacity', 70)))
        gcol = [g0.get('color', '#ffd54a')]; gcb = QPushButton('Glow colour')
        def tint(btn, holder):
            c = QColor(holder[0]); btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')
        def pick(holder, btn):
            c = QColorDialog.getColor(QColor(holder[0]), self, 'Colour')
            if c.isValid(): holder[0] = c.name(); tint(btn, holder)
        scb.clicked.connect(lambda: pick(scol, scb)); gcb.clicked.connect(lambda: pick(gcol, gcb))
        tint(scb, scol); tint(gcb, gcol)
        for lbl, wdg in (('', s_on), ('Offset across:', sdx), ('Offset down:', sdy), ('Shadow blur:', sbl),
                         ('Shadow strength:', sop), ('Shadow colour:', scb), ('', g_on),
                         ('Glow spread:', gbl), ('Glow strength:', gop), ('Glow colour:', gcb)):
            form.addRow(lbl, wdg)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        o['shadow'] = {'dx': sdx.value(), 'dy': sdy.value(), 'blur': sbl.value(),
                       'opacity': sop.value(), 'color': scol[0]} if s_on.isChecked() else None
        o['glow'] = {'blur': gbl.value(), 'opacity': gop.value(), 'color': gcol[0]} if g_on.isChecked() else None
        if not o['shadow']: o.pop('shadow', None)
        if not o['glow']: o.pop('glow', None)
        self.canvas.update()

    # ---------------------------------------------------------------- text (artistic)
    def _text_dialog(self, text='Text', family=None, size=48, title='Add Text'):
        """Collect the string, font family (bundled + system fonts) and pixel size.
        Returns (text, family, size) or None if cancelled."""
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        dlg = QDialog(self); dlg.setWindowTitle(title); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        te = QLineEdit(text); te.setMinimumWidth(240)
        fc = QFontComboBox(); fc.setCurrentFont(QFont(family or 'Noto Sans'))
        sz = QSpinBox(); sz.setRange(4, 800); sz.setSuffix(' px'); sz.setValue(int(size))
        form.addRow('Text:', te); form.addRow('Font:', fc); form.addRow('Size:', sz)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return None
        s = te.text() or 'Text'
        return s, fc.currentFont().family(), sz.value()

    def place_text(self, pt):
        """Called by the canvas when the Text tool is clicked — opens the dialog and
        drops a new text object at the click, with the current fill as its colour."""
        res = self._text_dialog(title='Add Text')
        if not res: return
        s, fam, size = res
        self.canvas.snapshot()
        o = dict(type='text', x=pt[0], y=pt[1], text=s, family=fam, size=size,
                 fill=self.canvas.fill.name(), stroke=None, sw=0, layer=self.canvas.active_layer)
        self.canvas.objs.append(o); self.canvas.sel = o
        self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True)
        self.canvas.update(); self.refresh_layers()

    def edit_text(self):
        """Re-open the text dialog on the selected text object to change its words/font/size."""
        o = self.canvas.sel
        if o is None or o.get('type') != 'text':
            QMessageBox.information(self, APP, 'Select a text object first, then Edit Text.')
            return
        res = self._text_dialog(o.get('text', ''), o.get('family'), o.get('size', 48), 'Edit Text')
        if not res: return
        self.canvas.snapshot()
        o['text'], o['family'], o['size'] = res
        self.canvas.update()

    # ---------------------------------------------------------------- gradient fill
    def gradient_dialog(self):
        """Linear or radial gradient fill for the selected shape — two colours + angle.
        Mirrors PAGEdesigner's 'grad' dict ({c1,c2,angle,type}). Cleared via Remove."""
        o = self.canvas.sel
        if o is None or o.get('type') not in ('rect', 'ellipse', 'quick', 'poly', 'text'):
            QMessageBox.information(self, APP, 'Select a shape first (rectangle, ellipse, QuickShape, '
                                   'a closed pen shape or text), then add a gradient fill.')
            return
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        g0 = o.get('grad') or {}
        c1 = [g0.get('c1', '#ffd54a')]; c2 = [g0.get('c2', '#2a7d6b')]
        dlg = QDialog(self); dlg.setWindowTitle('Gradient Fill'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        kind = QComboBox(); kind.addItem('Linear', 'linear'); kind.addItem('Radial', 'radial')
        kind.setCurrentIndex(1 if g0.get('type') == 'radial' else 0)
        b1 = QPushButton('Start colour'); b2 = QPushButton('End colour')
        ang = QSpinBox(); ang.setRange(0, 360); ang.setSuffix('°'); ang.setValue(int(g0.get('angle', 90)))
        def tint(btn, holder):
            c = QColor(holder[0]); btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')
        def pick(holder, btn):
            c = QColorDialog.getColor(QColor(holder[0]), self, 'Gradient colour')
            if c.isValid(): holder[0] = c.name(); tint(btn, holder)
        b1.clicked.connect(lambda: pick(c1, b1)); b2.clicked.connect(lambda: pick(c2, b2))
        tint(b1, c1); tint(b2, c2)
        form.addRow('Type:', kind); form.addRow('Start colour:', b1)
        form.addRow('End colour:', b2); form.addRow('Angle (linear):', ang)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        rm = QPushButton('Remove gradient'); bb.addButton(rm, QDialogButtonBox.ResetRole)
        rm.clicked.connect(lambda: (self._remove_gradient(o), dlg.reject()))
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        o['grad'] = {'c1': c1[0], 'c2': c2[0], 'angle': ang.value(), 'type': kind.currentData()}
        self.canvas.update()

    def _remove_gradient(self, o):
        if o.get('grad'):
            self.canvas.snapshot(); o.pop('grad', None); self.canvas.update()

    def build_menu(self):
        m = self.menuBar()
        f = m.addMenu('&File')
        f.addAction(self.act('&New…', self.new, QKeySequence.New))
        f.addAction(self.act('&Open SVG…', self.open_svg, QKeySequence.Open))
        f.addAction(self.act('&Save as SVG…', self.save_svg, QKeySequence.Save))
        f.addAction(self.act('&Export PNG…', self.export_png))
        f.addAction(self.act('Edit in &PAINTcanvas…', self.edit_in_paint))
        f.addSeparator(); f.addAction(self.act('&Quit', self.close, QKeySequence.Quit))
        e = m.addMenu('&Edit')
        e.addAction(self.act('&Undo', self.canvas.do_undo, QKeySequence.Undo))
        e.addAction(self.act('&Redo', self.canvas.do_redo, QKeySequence.Redo))
        e.addSeparator()
        e.addAction(self.act('Edit &Text…', self.edit_text))
        e.addAction(self.act('&Gradient Fill…', self.gradient_dialog))
        a = m.addMenu('&Arrange')
        a.addAction(self.act('Bring to &Front', lambda: self.canvas.z_order('front'), QKeySequence('Ctrl+Shift+]')))
        a.addAction(self.act('Send to &Back', lambda: self.canvas.z_order('back'), QKeySequence('Ctrl+Shift+[')))
        a.addAction(self.act('Bring For&ward', lambda: self.canvas.z_order('forward'), QKeySequence('Ctrl+]')))
        a.addAction(self.act('Send Back&ward', lambda: self.canvas.z_order('backward'), QKeySequence('Ctrl+[')))
        a.addSeparator()
        a.addAction(self.act('Show &Layers Panel', lambda: self.layers_dock.setVisible(True)))
        h = m.addMenu('&Help')
        h.addAction(self.act('&User Guide', self.open_manual)); h.addAction(self.act('&Quick Start Guide', self.open_quickstart))
        h.addSeparator(); h.addAction(self.act('&About', self.about))

    def act(self, t, slot, sc=None):
        a = QAction(t, self); a.triggered.connect(slot)
        if sc: a.setShortcut(sc)
        return a

    def edit_in_paint(self):
        """Rasterise the drawing to a PNG and open it in just a… PAINTcanvas for raster
        touch-ups. One-way: a vector drawing can't re-absorb an edited bitmap."""
        import shutil, subprocess
        exe = shutil.which('paint') or os.path.expanduser('~/.local/bin/paint')
        if not os.path.exists(exe):
            QMessageBox.information(self, APP, 'just a… PAINTcanvas isn’t installed yet.\n\n'
                                   'Install it from the “just a… CREATORsuite” launcher.')
            return
        base = os.path.splitext(os.path.basename(self.path))[0] if self.path else 'drawing'
        path = os.path.join(_just_dir('pics'), base + '.png')
        if not self.canvas.export_png(path):
            QMessageBox.warning(self, APP, 'Could not export the drawing.'); return
        _justapps_recent('paint', path)
        subprocess.Popen([exe, path], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.statusBar().showMessage(f'Opened {os.path.basename(path)} in PAINTcanvas for raster editing.', 5000)

    def set_pos(self, p): self.pos_lbl.setText(f'{int(p[0])}, {int(p[1])}   ')
    def set_sw(self, v): self.canvas.sw = v; self.canvas.apply_to_sel(sw=v)

    def _paint_btns(self):
        for btn, col in ((self.fill_btn, self.canvas.fill), (self.stroke_btn, self.canvas.stroke)):
            btn.setStyleSheet(f'QPushButton{{background:{col.name()};color:{"#fff" if col.lightness()<140 else "#000"};'
                              'border:1px solid #888;border-radius:5px;padding:5px 12px;font-weight:600}}')

    def pick_fill(self):
        c = QColorDialog.getColor(self.canvas.fill, self, 'Fill colour', QColorDialog.ShowAlphaChannel)
        if c.isValid(): self.canvas.fill = c; self._paint_btns(); self.canvas.apply_to_sel(fill=c.name())

    def pick_stroke(self):
        c = QColorDialog.getColor(self.canvas.stroke, self, 'Line colour')
        if c.isValid(): self.canvas.stroke = c; self._paint_btns(); self.canvas.apply_to_sel(stroke=c.name())

    def sync_props(self):
        o = self.canvas.sel
        if o:
            if o.get('fill'): self.canvas.fill = QColor(o['fill'])
            if o.get('stroke'): self.canvas.stroke = QColor(o['stroke'])
            self.sw_spin.blockSignals(True); self.sw_spin.setValue(int(o.get('sw', 2))); self.sw_spin.blockSignals(False)
            self._paint_btns()

    def new(self):
        w, ok = 1000, True
        dlg = QDialog(self); dlg.setWindowTitle('New Drawing'); v = QVBoxLayout(dlg)
        cb = QComboBox(); PRE = [('1000 × 700', 1000, 700), ('A4 (794 × 1123)', 794, 1123),
                                 ('1920 × 1080', 1920, 1080), ('800 × 800', 800, 800)]
        for n, _, _ in PRE: cb.addItem(n)
        v.addWidget(QLabel('Canvas size:')); v.addWidget(cb)
        row = QHBoxLayout(); ok_b = QPushButton('Create'); cancel = QPushButton('Cancel')
        ok_b.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject); row.addWidget(cancel); row.addWidget(ok_b); v.addLayout(row)
        if dlg.exec():
            _, w, h = PRE[cb.currentIndex()]
            self.canvas.snapshot(); self.canvas.objs = []; self.canvas.sel = None; self.canvas.W, self.canvas.H = w, h
            self.canvas.reset_layers(); self.canvas._fit(); self.refresh_layers(); self.path = None

    def save_svg(self):
        start = (os.path.splitext(self.path)[0] if self.path else os.path.join(_just_dir('docs'), 'drawing')) + '.svg'
        path, _ = QFileDialog.getSaveFileName(self, 'Save SVG', start, 'SVG (*.svg)')
        if not path: return
        if not path.lower().endswith('.svg'): path += '.svg'
        self.canvas.export_svg(path); self.path = path
        _justapps_recent('draw', path); self.statusBar().showMessage(f'Saved {path}', 4000)

    def export_png(self):
        start = (os.path.splitext(self.path)[0] if self.path else os.path.join(_just_dir('pics'), 'drawing')) + '.png'
        path, _ = QFileDialog.getSaveFileName(self, 'Export PNG', start, 'PNG (*.png)')
        if not path: return
        if not path.lower().endswith('.png'): path += '.png'
        self.canvas.export_png(path)
        _justapps_recent('paint', path); self.statusBar().showMessage(f'Exported {path}', 4000)

    def open_svg(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open SVG', _just_dir('docs'), 'SVG drawings (*.svg);;All files (*)')
        if path: self._open_path(path)

    def _open_path(self, path):
        r = self.canvas.load_svg(path)
        if r is True:
            self.path = path; self.refresh_layers()
            _justapps_recent('draw', path); self.statusBar().showMessage(f'Opened {path}', 4000)
        elif r is None:
            QMessageBox.information(self, APP, 'That SVG wasn’t made by DRAWmaster, so its shapes can’t be loaded '
                                   'for editing here. DRAWmaster can re-open the drawings it saved itself.')
        else:
            QMessageBox.warning(self, APP, 'Could not open that drawing.')

    def _open_doc(self, path):
        """Open a bundled HTML guide in an in-app window (falls back to the browser)."""
        _p = path
        if os.path.isfile(_p):
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView
                from PySide6.QtWidgets import QDialog, QVBoxLayout
                from PySide6.QtCore import QUrl as _U, Qt as _Qt
                _dlg = QDialog(self); _dlg.setWindowTitle('just a... DRAWmaster — Help'); _dlg.setWindowFlag(_Qt.Window, True); _dlg.resize(920, 840)
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

    def open_manual(self):
        self._open_doc(MANUAL)

    def open_quickstart(self):
        self._open_doc(QUICKSTART)

    def about(self):
        QMessageBox.about(self, f'About {APP}', f'<b>{APP}</b><br>Version {VERSION}<br><br>A tiny vector '
                          'drawing app — shapes, lines and paths saved as scalable SVG.')


def glyph_icon(glyph, size=22):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(QColor('#dfe3e8'))
    f = QFont('Noto Sans'); f.setPixelSize(int(size * 0.7)); p.setFont(f); p.drawText(pm.rect(), Qt.AlignCenter, glyph); p.end()
    return QIcon(pm)


def main():
    QApplication.setDesktopFileName('draw')
    app = QApplication(sys.argv)
    app.setApplicationName('DRAWmaster'); app.setApplicationDisplayName(APP)
    app.setOrganizationName(ORG); app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon.fromTheme('draw'))
    w = Main(); w.show()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and os.path.isfile(args[0]): w._open_path(args[0])
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
