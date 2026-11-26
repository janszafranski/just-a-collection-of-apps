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
                               QLinearGradient, QRadialGradient, QPdfWriter, QPageSize, QPageLayout)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings, QMarginsF, QBuffer, QByteArray
    from PySide6.QtSvg import QSvgGenerator
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    sys.stderr.write("just a... DRAWmaster needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... DRAWmaster"
ORG = "justadrawmaster"
VERSION = "1.6-00"
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

# ---------------------------------------------------------------- Node / Bézier paths
# A node path (type 'nodes') is a list of nodes, each {x, y, hin:[dx,dy], hout:[dx,dy],
# smooth:bool}; the control handles are stored *relative* to the node point. The path is
# built segment-by-segment with cubicTo, using each node's hout and the next node's hin.
def node_painter_path(o):
    """Build a QPainterPath for a node ('nodes') object from its node list."""
    nodes = o.get('nodes') or []
    pp = QPainterPath()
    if not nodes:
        return pp
    pp.moveTo(nodes[0]['x'], nodes[0]['y'])
    closed = o.get('closed')
    n = len(nodes)
    segs = n if closed else n - 1
    for i in range(segs):
        a = nodes[i]; b = nodes[(i + 1) % n]
        c1 = (a['x'] + a.get('hout', [0, 0])[0], a['y'] + a.get('hout', [0, 0])[1])
        c2 = (b['x'] + b.get('hin', [0, 0])[0], b['y'] + b.get('hin', [0, 0])[1])
        pp.cubicTo(c1[0], c1[1], c2[0], c2[1], b['x'], b['y'])
    if closed:
        pp.closeSubpath()
    return pp


def node_svg_d(o):
    """An SVG path 'd' string ('M .. C ..') for a node object — the browser-true form."""
    nodes = o.get('nodes') or []
    if not nodes:
        return ''
    parts = [f"M {nodes[0]['x']:.2f} {nodes[0]['y']:.2f}"]
    closed = o.get('closed')
    n = len(nodes)
    segs = n if closed else n - 1
    for i in range(segs):
        a = nodes[i]; b = nodes[(i + 1) % n]
        c1x = a['x'] + a.get('hout', [0, 0])[0]; c1y = a['y'] + a.get('hout', [0, 0])[1]
        c2x = b['x'] + b.get('hin', [0, 0])[0]; c2y = b['y'] + b.get('hin', [0, 0])[1]
        parts.append(f"C {c1x:.2f} {c1y:.2f} {c2x:.2f} {c2y:.2f} {b['x']:.2f} {b['y']:.2f}")
    if closed:
        parts.append('Z')
    return ' '.join(parts)


def nodes_from_obj(o):
    """Convert a rect / ellipse / quick / line / poly / path into a list of Bézier nodes,
    so 'Convert to Curves' can turn any object into an editable node path. Returns
    (nodes, closed) — the geometry is sampled in the object's own canvas coordinates."""
    t = o['type']
    K = 0.5522847498  # circle→Bézier kappa

    def corner(x, y):
        return {'x': float(x), 'y': float(y), 'hin': [0.0, 0.0], 'hout': [0.0, 0.0], 'smooth': False}

    if t == 'ellipse':
        x, y, w, h = o['x'], o['y'], o['w'], o['h']; rx, ry = w / 2, h / 2
        cx, cy = x + rx, y + ry
        pts = [(cx + rx, cy), (cx, cy + ry), (cx - rx, cy), (cx, cy - ry)]
        tang = [(0, ry * K), (-rx * K, 0), (0, -ry * K), (rx * K, 0)]
        nodes = []
        for (px, py), (tx, ty) in zip(pts, tang):
            nodes.append({'x': px, 'y': py, 'hin': [-tx, -ty], 'hout': [tx, ty], 'smooth': True})
        return nodes, True
    if t == 'rect':
        x, y, w, h = o['x'], o['y'], o['w'], o['h']
        return [corner(x, y), corner(x + w, y), corner(x + w, y + h), corner(x, y + h)], True
    if t == 'quick':
        pp = quickshape_path(o['shape'], o['w'], o['h']).translated(o['x'], o['y'])
        return _nodes_from_painterpath(pp)
    if t in ('line', 'poly', 'path'):
        pts = o.get('pts') or []
        return [corner(px, py) for (px, py) in pts], bool(o.get('closed'))
    return [], False


def _nodes_from_painterpath(pp):
    """Flatten a QPainterPath's elements into corner/curve nodes (best-effort — used when
    converting a QuickShape, whose outline may mix lines and cubics)."""
    nodes = []
    i = 0
    n = pp.elementCount()
    pending_ctrl = []
    closed = False
    while i < n:
        el = pp.elementAt(i)
        et = el.type
        if et == QPainterPath.MoveToElement:
            nodes.append({'x': el.x, 'y': el.y, 'hin': [0.0, 0.0], 'hout': [0.0, 0.0], 'smooth': False})
            i += 1
        elif et == QPainterPath.LineToElement:
            nodes.append({'x': el.x, 'y': el.y, 'hin': [0.0, 0.0], 'hout': [0.0, 0.0], 'smooth': False})
            i += 1
        elif et == QPainterPath.CurveToElement:
            # a cubic: this element is control1, next is control2, next is the endpoint
            c1 = el; c2 = pp.elementAt(i + 1); ep = pp.elementAt(i + 2)
            if nodes:
                nodes[-1]['hout'] = [c1.x - nodes[-1]['x'], c1.y - nodes[-1]['y']]
            nodes.append({'x': ep.x, 'y': ep.y, 'hin': [c2.x - ep.x, c2.y - ep.y],
                          'hout': [0.0, 0.0], 'smooth': True})
            i += 3
        else:
            i += 1
    # a closed QuickShape path ends near its start; drop a duplicate end node if so
    if len(nodes) >= 2:
        a, b = nodes[0], nodes[-1]
        if abs(a['x'] - b['x']) < 0.5 and abs(a['y'] - b['y']) < 0.5:
            if b.get('hin') != [0.0, 0.0]:
                a['hin'] = b['hin']
            nodes.pop()
            closed = True
        else:
            closed = True   # QuickShapes are closed outlines
    return nodes, closed


# ---------------------------------------------------------------- line dashes & arrowheads
def apply_dash(pen, style):
    """Set a solid / dashed / dotted pattern on a pen (scaled by the pen width)."""
    if style == 'dashed':
        pen.setStyle(Qt.CustomDashLine); pen.setDashPattern([4, 3])
    elif style == 'dotted':
        pen.setStyle(Qt.CustomDashLine); pen.setDashPattern([1, 2])
    else:
        pen.setStyle(Qt.SolidLine)
    return pen


def svg_dash_attr(o):
    """A stroke-dasharray attribute fragment for a dash style, scaled by stroke width."""
    style = o.get('dash', 'solid'); sw = max(1, o.get('sw', 2))
    if style == 'dashed':
        return f' stroke-dasharray="{4 * sw},{3 * sw}"'
    if style == 'dotted':
        return f' stroke-dasharray="{1 * sw},{2 * sw}"'
    return ''


def _polyline_points(o):
    """The ordered (x,y) points of an open-path-like object, for arrowhead placement."""
    t = o['type']
    if t in ('line', 'path', 'poly'):
        return list(o.get('pts') or [])
    if t == 'nodes':
        return [(nd['x'], nd['y']) for nd in (o.get('nodes') or [])]
    return []


def _arrow_head_path(tip, frm, size):
    """A filled triangular arrowhead QPainterPath at 'tip', pointing away from 'frm'."""
    tx, ty = tip; fx, fy = frm
    ang = math.atan2(ty - fy, tx - fx)
    a1 = ang + math.radians(150); a2 = ang - math.radians(150)
    p1 = (tx + size * math.cos(a1), ty + size * math.sin(a1))
    p2 = (tx + size * math.cos(a2), ty + size * math.sin(a2))
    pp = QPainterPath(); pp.moveTo(tx, ty); pp.lineTo(*p1); pp.lineTo(*p2); pp.closeSubpath()
    return pp


def draw_arrowheads(p, o):
    """Draw start/end arrowheads for a line / open path / open node path, if set."""
    which = o.get('arrow', 'none')
    if which == 'none':
        return
    pts = _polyline_points(o)
    if len(pts) < 2 or o.get('closed'):
        return
    size = max(8.0, (o.get('sw', 2) or 2) * 3.0)
    col = QColor(o.get('stroke') or '#000000')
    p.save(); p.setPen(Qt.NoPen); p.setBrush(col)
    if which in ('end', 'both'):
        p.drawPath(_arrow_head_path(pts[-1], pts[-2], size))
    if which in ('start', 'both'):
        p.drawPath(_arrow_head_path(pts[0], pts[1], size))
    p.restore()


def svg_arrowheads(o):
    """SVG <path> arrowheads (filled triangles) for an open line/path — returned as a
    string spliced into export. Mirrors draw_arrowheads for browser-true output."""
    which = o.get('arrow', 'none')
    if which == 'none' or o.get('closed'):
        return ''
    pts = _polyline_points(o)
    if len(pts) < 2:
        return ''
    size = max(8.0, (o.get('sw', 2) or 2) * 3.0)
    col = o.get('stroke') or '#000000'
    out = []

    def tri(tip, frm):
        pp = _arrow_head_path(tip, frm, size)
        d = []
        for i in range(pp.elementCount()):
            el = pp.elementAt(i)
            d.append(('M' if el.type == QPainterPath.MoveToElement else 'L') + f' {el.x:.2f} {el.y:.2f}')
        return f'<path d="{" ".join(d)} Z" fill="{col}" stroke="none"/>'

    if which in ('end', 'both'):
        out.append(tri(pts[-1], pts[-2]))
    if which in ('start', 'both'):
        out.append(tri(pts[0], pts[1]))
    return ''.join(out)


# ---------------------------------------------------------------- image objects
_IMG_CACHE = {}

def obj_image(o):
    """Decode an image object's embedded data-URI (or file path) to a QImage, cached by
    src in a side table so repeated paints don't re-decode (and so the object dict stays
    plain/serialisable/deep-copyable — no QImage ever lives on the object)."""
    src = o.get('src', '')
    cached = _IMG_CACHE.get(src)
    if isinstance(cached, QImage):
        return cached
    qi = QImage()
    try:
        if src.startswith('data:'):
            import base64
            head, _, b64 = src.partition(',')
            qi.loadFromData(base64.b64decode(b64))
        elif src:
            qi.load(src)
    except Exception:
        qi = QImage()
    if src:
        _IMG_CACHE[src] = qi
    return qi


def image_data_uri(path):
    """Read an image file and return a data: URI (keeps SVGs self-contained)."""
    import base64, mimetypes
    with open(path, 'rb') as fh:
        raw = fh.read()
    mime = mimetypes.guess_type(path)[0] or 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(raw).decode()


# ---------------------------------------------------------------- Object effects
def obj_silhouette(o):
    """(path in local 0-based coords, world x, world y, w, h) for drop-shadow/glow."""
    t = o['type']; pp = QPainterPath()
    if t == 'rect': pp.addRect(QRectF(0, 0, o['w'], o['h']))
    elif t == 'ellipse': pp.addEllipse(QRectF(0, 0, o['w'], o['h']))
    elif t == 'image': pp.addRect(QRectF(0, 0, o['w'], o['h']))
    elif t == 'quick': pp = quickshape_path(o['shape'], o['w'], o['h'])
    elif t == 'nodes':
        from PySide6.QtGui import QPainterPathStroker
        base = node_painter_path(o); r = obj_rect(o)
        base = base.translated(-r.x(), -r.y())
        if o.get('closed') and o.get('fill'):
            pp = base
        else:
            stk = QPainterPathStroker(); stk.setWidth(max(2, o.get('sw', 2)))
            stk.setCapStyle(Qt.RoundCap); stk.setJoinStyle(Qt.RoundJoin); pp = stk.createStroke(base)
        br = pp.boundingRect()
        return pp.translated(-br.x(), -br.y()), r.x() + br.x(), r.y() + br.y(), br.width() or 1, br.height() or 1
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
    if t in ('rect', 'ellipse', 'quick', 'image'):
        return QRectF(o['x'], o['y'], o['w'], o['h']).normalized()
    if t == 'text':
        tw, th = text_size(o)
        return QRectF(o['x'], o['y'], tw, th)
    if t == 'nodes':
        br = node_painter_path(o).boundingRect()
        return QRectF(br.x(), br.y(), br.width() or 1, br.height() or 1)
    xs = [p[0] for p in o['pts']]; ys = [p[1] for p in o['pts']]
    return QRectF(min(xs), min(ys), max(xs) - min(xs) or 1, max(ys) - min(ys) or 1)


def obj_center(o):
    """The centre of an object's (unrotated) bounding box — the pivot for rotation."""
    r = obj_rect(o)
    return r.x() + r.width() / 2, r.y() + r.height() / 2


def obj_rot(o):
    """Rotation in degrees (clockwise), 0 if the object is unrotated."""
    try: return float(o.get('rot', 0) or 0)
    except (TypeError, ValueError): return 0.0


def obj_bounds(o):
    """The axis-aligned bounding box of an object *after* its rotation — the box that
    actually contains it on the canvas. For an unrotated object this equals obj_rect."""
    r = obj_rect(o); a = obj_rot(o)
    if not a:
        return r
    cx, cy = r.x() + r.width() / 2, r.y() + r.height() / 2
    rad = math.radians(a); cosa, sina = math.cos(rad), math.sin(rad)
    xs, ys = [], []
    for px, py in ((r.left(), r.top()), (r.right(), r.top()),
                   (r.right(), r.bottom()), (r.left(), r.bottom())):
        dx, dy = px - cx, py - cy
        xs.append(cx + dx * cosa - dy * sina); ys.append(cy + dx * sina + dy * cosa)
    return QRectF(min(xs), min(ys), max(xs) - min(xs) or 1, max(ys) - min(ys) or 1)


def obj_hit(o, pt):
    """True if canvas point pt (x, y) is inside the object, honouring its rotation.
    The point is rotated back into the object's local (unrotated) frame, then tested
    against the padded bounding rect."""
    a = obj_rot(o); r = obj_rect(o).adjusted(-3, -3, 3, 3)
    px, py = pt
    if a:
        cx, cy = o and obj_center(o)
        rad = math.radians(-a); cosa, sina = math.cos(rad), math.sin(rad)
        dx, dy = px - cx, py - cy
        px, py = cx + dx * cosa - dy * sina, cy + dx * sina + dy * cosa
    return r.contains(QPointF(px, py))


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
    rot = obj_rot(o); tr = ''
    if rot:
        cx, cy = obj_center(o); tr = f' transform="rotate({rot:.3f} {cx:.2f} {cy:.2f})"'
    el = (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{fam}" font-size="{sz}" '
          f'fill="{fill}"{stroke} xml:space="preserve"{tr}>{body}</text>')
    return defs, el


def _rot_transform(o):
    """ transform="rotate(a cx cy)" fragment for a rotated object, else ''."""
    rot = obj_rot(o)
    if not rot:
        return ''
    cx, cy = obj_center(o)
    return f' transform="rotate({rot:.3f} {cx:.2f} {cy:.2f})"'


def _opacity_attr(o):
    op = obj_opacity(o)
    return f' opacity="{op:.3f}"' if op < 1.0 else ''


def svg_image_el(o):
    """A real SVG <image href="data:..." x y width height> element for an image object."""
    import html as _H
    src = _H.escape(o.get('src', ''), quote=True)
    return (f'<image href="{src}" x="{o["x"]:.2f}" y="{o["y"]:.2f}" '
            f'width="{o["w"]:.2f}" height="{o["h"]:.2f}" preserveAspectRatio="none"'
            f'{_rot_transform(o)}{_opacity_attr(o)}/>')


def svg_node_el(o, idx=0):
    """(defs, element) for a node ('nodes') object: a real <path d="M.. C..">, with its
    fill/stroke/dash, opacity and rotation — plus any arrowheads, so it is browser-true."""
    d = node_svg_d(o)
    if not d:
        return '', ''
    g = o.get('grad'); defs = ''
    if g and o.get('closed'):
        gid = f'ndgrad{idx}'; defs = svg_grad_def(g, gid); fill = f'url(#{gid})'
    else:
        fill = (o.get('fill') if (o.get('closed') and o.get('fill')) else 'none')
    stroke = o.get('stroke') or 'none'
    sw = o.get('sw', 2)
    el = (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
          f'stroke-linejoin="round" stroke-linecap="round"{svg_dash_attr(o)}'
          f'{_rot_transform(o)}{_opacity_attr(o)}/>')
    heads = svg_arrowheads(o)
    if heads:
        # wrap the arrowheads so a rotation applies to them too
        tr = _rot_transform(o); op = _opacity_attr(o)
        if tr or op:
            heads = f'<g{tr}{op}>{heads}</g>'
        el = el + heads
    return defs, el


def obj_opacity(o):
    """Object opacity in 0..1 (1 if unset)."""
    try:
        v = float(o.get('opacity', 1) if o.get('opacity') is not None else 1)
    except (TypeError, ValueError):
        return 1.0
    return max(0.0, min(1.0, v))


def paint_object(p, o, selected=False, skip_text=False):
    a = obj_rot(o)
    rotated = bool(a)
    op = obj_opacity(o)
    faded = op < 1.0
    if faded:
        p.save(); p.setOpacity(p.opacity() * op)
    if rotated:
        # Rotate about the object's centre. QPainter transforms are captured by
        # QSvgGenerator as a <g transform="..."> too, so rotation survives SVG export
        # for shapes (text is spliced separately with its own rotate()).
        cx, cy = obj_center(o)
        p.save(); p.translate(cx, cy); p.rotate(a); p.translate(-cx, -cy)
    _paint_object_body(p, o, selected, skip_text)
    if rotated:
        p.restore()
    if faded:
        p.restore()


def _paint_object_body(p, o, selected=False, skip_text=False):
    if skip_text and o.get('type') == 'text':
        draw_object_fx(p, o); return   # keep shadow/glow; the SVG <text> draws the glyphs
    draw_object_fx(p, o)
    pen = QPen(QColor(o['stroke']), o.get('sw', 2)) if o.get('stroke') else QPen(Qt.NoPen)
    pen.setJoinStyle(Qt.RoundJoin); pen.setCapStyle(Qt.RoundCap)
    if o.get('stroke') and o.get('dash', 'solid') != 'solid':
        apply_dash(pen, o.get('dash'))
    p.setPen(pen)
    p.setBrush(fill_brush(o))
    t = o['type']
    if t == 'rect':
        p.drawRect(QRectF(o['x'], o['y'], o['w'], o['h']))
    elif t == 'ellipse':
        p.drawEllipse(QRectF(o['x'], o['y'], o['w'], o['h']))
    elif t == 'image':
        img = obj_image(o)
        if not img.isNull():
            p.drawImage(QRectF(o['x'], o['y'], o['w'], o['h']), img)
        if o.get('stroke'):
            p.setBrush(Qt.NoBrush); p.drawRect(QRectF(o['x'], o['y'], o['w'], o['h']))
    elif t == 'quick':
        p.save(); p.translate(o['x'], o['y']); p.drawPath(quickshape_path(o['shape'], o['w'], o['h'])); p.restore()
    elif t == 'nodes':
        pp = node_painter_path(o)
        if o.get('closed') and o.get('fill'):
            p.drawPath(pp)
        else:
            p.setBrush(Qt.NoBrush); p.drawPath(pp)
        draw_arrowheads(p, o)
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
        draw_arrowheads(p, o)
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
        self.sels = []          # multi-selection (always includes self.sel when non-empty)
        self._next_gid = 1      # next group id to hand out
        self.tool = 'select'
        self.fill = QColor('#cfe3ef'); self.stroke = QColor('#1f2a30'); self.sw = 2
        self.quick_shape = 'star5'
        self.start = None; self.cur = None; self.drag_off = None; self.poly_pts = None
        # Pen (Bézier) tool: nodes being laid down, and the live smooth-drag node
        self.pen_nodes = None; self.pen_dragging = False
        # Node tool: the path being reshaped and which node/handle is grabbed
        self.node_obj = None; self.node_grab = None
        # transform/rubber-band drag state
        self.handle = None       # which transform handle is being dragged
        self.drag_start = None   # canvas pt where a handle/rubber drag began
        self.drag_orig = None    # deep snapshot of selected objects at drag start
        self.rubber = None       # (a, b) rubber-band rect while selecting
        # grid, guides & snapping (non-printing: screen only, never in PNG/SVG)
        self.show_grid = False
        self.grid = 20
        self.snap = True
        self.guides_h = []       # horizontal guide y-positions
        self.guides_v = []       # vertical guide x-positions
        self.undo, self.redo = [], []
        self.setMouseTracking(True); self.setCursor(Qt.CrossCursor); self._fit()

    def _fit(self):
        self.setMinimumSize(int(self.W * self.zoom), int(self.H * self.zoom)); self.resize(self.minimumSize()); self.update()

    def snapshot(self):
        self.undo.append(copy.deepcopy(self.objs))
        if len(self.undo) > 60: self.undo.pop(0)
        self.redo.clear()

    def do_undo(self):
        if self.undo: self.redo.append(copy.deepcopy(self.objs)); self.objs = self.undo.pop(); self.sel = None; self.sels = []; self.update()

    def do_redo(self):
        if self.redo: self.undo.append(copy.deepcopy(self.objs)); self.objs = self.redo.pop(); self.sel = None; self.sels = []; self.update()

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
        self.sels = [o for o in self.sels if o in self.objs]
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

    # ---------------------------------------------------------------- selection
    def _selection(self):
        """The current selection as a list (sel first), de-duplicated."""
        out = []
        for o in ([self.sel] if self.sel is not None else []) + self.sels:
            if o is not None and o in self.objs and o not in out:
                out.append(o)
        return out

    def _group_members(self, o):
        """All objects sharing o's group id (just o itself if ungrouped)."""
        gid = o.get('gid') if o else None
        if gid is None: return [o] if o is not None else []
        return [x for x in self.objs if x.get('gid') == gid]

    def set_selection(self, objs):
        """Expand a click/rubber selection to whole groups, and set sel/sels."""
        exp = []
        for o in objs:
            for m in self._group_members(o):
                if m not in exp: exp.append(m)
        self.sel = exp[0] if exp else None
        self.sels = exp
        self.win.sync_props()

    # ---------------------------------------------------------------- grouping
    def group_selection(self):
        sel = self._selection()
        if len(sel) < 2: return
        self.snapshot()
        gid = self._next_gid; self._next_gid += 1
        for o in sel: o['gid'] = gid
        self.set_selection(sel); self.update()

    def ungroup_selection(self):
        sel = self._selection()
        if not sel: return
        gids = {o.get('gid') for o in sel if o.get('gid') is not None}
        if not gids: return
        self.snapshot()
        for o in self.objs:
            if o.get('gid') in gids: o.pop('gid', None)
        self.set_selection(sel); self.update()

    # ---------------------------------------------------------------- align / distribute
    def align_selection(self, how):
        sel = self._selection()
        if len(sel) < 2: return
        self.snapshot()
        rects = {id(o): obj_bounds(o) for o in sel}
        xs0 = min(r.left() for r in rects.values()); xs1 = max(r.right() for r in rects.values())
        ys0 = min(r.top() for r in rects.values()); ys1 = max(r.bottom() for r in rects.values())
        for o in sel:
            r = rects[id(o)]; dx = dy = 0.0
            if how == 'left':    dx = xs0 - r.left()
            elif how == 'right': dx = xs1 - r.right()
            elif how == 'hcenter': dx = (xs0 + xs1) / 2 - (r.left() + r.right()) / 2
            elif how == 'top':   dy = ys0 - r.top()
            elif how == 'bottom': dy = ys1 - r.bottom()
            elif how == 'vcenter': dy = (ys0 + ys1) / 2 - (r.top() + r.bottom()) / 2
            if dx or dy: self._shift_obj(o, dx, dy)
        self.update()

    def distribute_selection(self, axis):
        sel = self._selection()
        if len(sel) < 3: return
        self.snapshot()
        key = (lambda o: obj_bounds(o).center().x()) if axis == 'h' else (lambda o: obj_bounds(o).center().y())
        ordered = sorted(sel, key=key)
        centres = [key(o) for o in ordered]
        lo, hi = centres[0], centres[-1]
        n = len(ordered)
        for i, o in enumerate(ordered):
            target = lo + (hi - lo) * i / (n - 1)
            d = target - key(o)
            if axis == 'h': self._shift_obj(o, d, 0)
            else: self._shift_obj(o, 0, d)
        self.update()

    def _shift_obj(self, o, dx, dy):
        """Translate a single object by (dx, dy) in canvas coords."""
        if o['type'] in ('rect', 'ellipse', 'quick', 'text', 'image'):
            o['x'] += dx; o['y'] += dy
        elif o['type'] == 'nodes':
            for nd in o.get('nodes', []):
                nd['x'] += dx; nd['y'] += dy
        else:
            o['pts'] = [(x + dx, y + dy) for x, y in o['pts']]

    # ---------------------------------------------------------------- grid & guides
    def set_grid(self, on=None, spacing=None):
        if on is not None: self.show_grid = bool(on)
        if spacing is not None: self.grid = max(2, int(spacing))
        self.update()

    def add_guide(self, orient, pos):
        (self.guides_h if orient == 'h' else self.guides_v).append(float(pos)); self.update()

    def clear_guides(self):
        self.guides_h = []; self.guides_v = []; self.update()

    def _snap_targets(self, exclude):
        """Candidate x and y snap lines: grid lines are handled numerically; here we
        gather guides and the edges/centres of every *other* object."""
        xs = list(self.guides_v); ys = list(self.guides_h)
        ex = set(id(o) for o in exclude)
        for o in self.objs:
            if id(o) in ex: continue
            r = obj_bounds(o)
            xs += [r.left(), r.center().x(), r.right()]
            ys += [r.top(), r.center().y(), r.bottom()]
        return xs, ys

    def _snap_delta(self, rect, exclude, tol=7):
        """Given a moving object's bounding rect, return (dx, dy) that snaps its
        edges/centre to the grid, guides or other objects' edges/centres."""
        if not self.snap: return 0.0, 0.0
        tol = tol / max(self.zoom, 0.01)
        cand_x, cand_y = self._snap_targets(exclude)
        mx = [rect.left(), rect.center().x(), rect.right()]
        my = [rect.top(), rect.center().y(), rect.bottom()]
        bx = by = None; bdx = bdy = tol
        for m in mx:
            if self.show_grid:
                g = round(m / self.grid) * self.grid
                if abs(g - m) < bdx: bdx = abs(g - m); bx = g - m
            for c in cand_x:
                if abs(c - m) < bdx: bdx = abs(c - m); bx = c - m
        for m in my:
            if self.show_grid:
                g = round(m / self.grid) * self.grid
                if abs(g - m) < bdy: bdy = abs(g - m); by = g - m
            for c in cand_y:
                if abs(c - m) < bdy: bdy = abs(c - m); by = c - m
        return (bx or 0.0), (by or 0.0)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#e9ebee'))
        p.fillRect(QRectF(0, 0, self.W * self.zoom, self.H * self.zoom), QColor('#ffffff'))
        p.scale(self.zoom, self.zoom)
        if self.show_grid:
            self._draw_grid(p)
        sel_set = set(id(o) for o in self._selection())
        for o in self.ordered_objs():
            paint_object(p, o, id(o) in sel_set)
        if self.start and self.cur and self.tool in ('rect', 'ellipse', 'line', 'quick'):
            tmp = self._shape_from(self.start, self.cur)
            if tmp: paint_object(p, tmp)
        if self.poly_pts and len(self.poly_pts) >= 1:
            prev = {'type': 'poly', 'pts': self.poly_pts + ([self.cur] if self.cur else []),
                    'stroke': self.stroke.name(), 'sw': self.sw, 'fill': None, 'closed': False}
            paint_object(p, prev)
        if self.tool == 'pen' and self.pen_nodes:
            self._draw_pen_preview(p)
        self._draw_guides(p)
        if self.rubber:
            self._draw_rubber(p)
        if self.tool == 'select':
            self._draw_handles(p)
        if self.tool == 'node' and self.node_obj is not None:
            self._draw_node_handles(p)
        p.end()

    def _draw_pen_preview(self, p):
        """Show the Bézier being laid down: the committed nodes + a rubber segment to the
        pointer, and the control handle while a smooth node is being dragged out."""
        nodes = list(self.pen_nodes)
        if self.cur and not self.pen_dragging:
            nodes = nodes + [{'x': self.cur[0], 'y': self.cur[1], 'hin': [0, 0], 'hout': [0, 0], 'smooth': False}]
        tmp = {'type': 'nodes', 'nodes': nodes, 'stroke': self.stroke.name(), 'sw': self.sw,
               'fill': None, 'closed': False}
        if len(nodes) >= 2:
            paint_object(p, tmp)
        pen = QPen(QColor('#2a7df0'), 1); pen.setCosmetic(True)
        hs = 4 / max(self.zoom, 0.01)
        for nd in self.pen_nodes:
            p.setPen(pen); p.setBrush(QColor('#ffffff'))
            p.drawRect(QRectF(nd['x'] - hs, nd['y'] - hs, hs * 2, hs * 2))
            if nd.get('hout') != [0, 0]:
                hx, hy = nd['x'] + nd['hout'][0], nd['y'] + nd['hout'][1]
                p.drawLine(QPointF(nd['x'], nd['y']), QPointF(hx, hy))
                p.setBrush(QColor('#2ab0e0')); p.drawEllipse(QPointF(hx, hy), hs, hs)

    def _draw_grid(self, p):
        pen = QPen(QColor('#d6dde2'), 1); pen.setCosmetic(True); p.setPen(pen)
        g = self.grid; x = 0
        while x <= self.W:
            p.drawLine(QPointF(x, 0), QPointF(x, self.H)); x += g
        y = 0
        while y <= self.H:
            p.drawLine(QPointF(0, y), QPointF(self.W, y)); y += g

    def _draw_guides(self, p):
        pen = QPen(QColor('#2ab0e0'), 1, Qt.DashLine); pen.setCosmetic(True); p.setPen(pen)
        for x in self.guides_v: p.drawLine(QPointF(x, 0), QPointF(x, self.H))
        for y in self.guides_h: p.drawLine(QPointF(0, y), QPointF(self.W, y))

    def _draw_rubber(self, p):
        a, b = self.rubber
        r = QRectF(QPointF(*a), QPointF(*b)).normalized()
        pen = QPen(QColor('#2a7df0'), 1, Qt.DashLine); pen.setCosmetic(True)
        p.setPen(pen); p.setBrush(QColor(42, 125, 240, 30)); p.drawRect(r)

    # ---------------------------------------------------------------- transform handles
    HANDLE_PX = 7

    def _handle_points(self):
        """Screen-space (unscaled) centre points of the 8 resize handles + rotate handle,
        for the single selected object. Returns {name: QPointF} in canvas coords (the
        rotated frame), or {} when zero/one object isn't singly selected."""
        sel = self._selection()
        if len(sel) != 1: return {}
        o = sel[0]; r = obj_rect(o)
        cx, cy = r.center().x(), r.center().y()
        pts = {'nw': (r.left(), r.top()), 'n': (cx, r.top()), 'ne': (r.right(), r.top()),
               'e': (r.right(), cy), 'se': (r.right(), r.bottom()), 's': (cx, r.bottom()),
               'sw': (r.left(), r.bottom()), 'w': (r.left(), cy),
               'rot': (cx, r.top() - 26 / max(self.zoom, 0.01))}
        a = obj_rot(o)
        if a:
            rad = math.radians(a); cosa, sina = math.cos(rad), math.sin(rad)
            out = {}
            for k, (px, py) in pts.items():
                dx, dy = px - cx, py - cy
                out[k] = QPointF(cx + dx * cosa - dy * sina, cy + dx * sina + dy * cosa)
            return out
        return {k: QPointF(x, y) for k, (x, y) in pts.items()}

    def _draw_handles(self, p):
        hp = self._handle_points()
        if not hp: return
        o = self._selection()[0]; r = obj_rect(o)
        p.save()
        a = obj_rot(o)
        if a:
            cx, cy = r.center().x(), r.center().y()
            p.translate(cx, cy); p.rotate(a); p.translate(-cx, -cy)
        box = QPen(QColor('#2a7df0'), 1, Qt.SolidLine); box.setCosmetic(True)
        p.setPen(box); p.setBrush(Qt.NoBrush); p.drawRect(r)
        p.restore()
        hs = self.HANDLE_PX / max(self.zoom, 0.01)
        pen = QPen(QColor('#1f6fd0'), 1); pen.setCosmetic(True)
        for k, c in hp.items():
            p.setPen(pen)
            if k == 'rot':
                p.setBrush(QColor('#2ab0e0'))
                p.drawEllipse(c, hs * .8, hs * .8)
            else:
                p.setBrush(QColor('#ffffff'))
                p.drawRect(QRectF(c.x() - hs / 2, c.y() - hs / 2, hs, hs))

    def _hit_handle(self, pt):
        hp = self._handle_points()
        tol = (self.HANDLE_PX + 4) / max(self.zoom, 0.01)
        for k, c in hp.items():
            if abs(c.x() - pt[0]) <= tol and abs(c.y() - pt[1]) <= tol:
                return k
        return None

    # ---------------------------------------------------------------- node editing
    def _draw_node_handles(self, p):
        """For the Node tool: draw each node as a square and its control handles as
        small circles on stalks."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return
        nodes = o.get('nodes', [])
        hs = 4.5 / max(self.zoom, 0.01)
        pen = QPen(QColor('#2a7df0'), 1); pen.setCosmetic(True)
        for nd in nodes:
            for key, col in (('hin', '#2ab0e0'), ('hout', '#2ab0e0')):
                h = nd.get(key, [0, 0])
                if h != [0, 0]:
                    hx, hy = nd['x'] + h[0], nd['y'] + h[1]
                    p.setPen(pen); p.drawLine(QPointF(nd['x'], nd['y']), QPointF(hx, hy))
                    p.setBrush(QColor(col)); p.drawEllipse(QPointF(hx, hy), hs * .9, hs * .9)
        for nd in nodes:
            p.setPen(pen); p.setBrush(QColor('#ffffff'))
            p.drawRect(QRectF(nd['x'] - hs, nd['y'] - hs, hs * 2, hs * 2))

    def _hit_node(self, pt):
        """Return ('node', i) / ('hin', i) / ('hout', i) for a grabbed node or handle,
        or None. Handles take priority over the node body."""
        o = self.node_obj
        if o is None:
            return None
        nodes = o.get('nodes', [])
        tol = 7 / max(self.zoom, 0.01)
        for i, nd in enumerate(nodes):
            for key in ('hin', 'hout'):
                h = nd.get(key, [0, 0])
                if h != [0, 0]:
                    hx, hy = nd['x'] + h[0], nd['y'] + h[1]
                    if abs(hx - pt[0]) <= tol and abs(hy - pt[1]) <= tol:
                        return (key, i)
        for i, nd in enumerate(nodes):
            if abs(nd['x'] - pt[0]) <= tol and abs(nd['y'] - pt[1]) <= tol:
                return ('node', i)
        return None

    def drag_node(self, i, nx, ny):
        """Programmatic/UI helper: move node i to (nx, ny), carrying its handles."""
        o = self.node_obj
        if o is None:
            return
        nodes = o.get('nodes', [])
        if 0 <= i < len(nodes):
            nodes[i]['x'] = nx; nodes[i]['y'] = ny
        self.update()

    def _drag_node_to(self, pt):
        """Mouse drag for the Node tool: move the grabbed node, or reshape a handle
        (a smooth node keeps its two handles mirrored)."""
        o = self.node_obj
        if o is None or self.node_grab is None:
            return
        kind, i = self.node_grab
        nodes = o.get('nodes', [])
        if not (0 <= i < len(nodes)):
            return
        nd = nodes[i]
        if kind == 'node':
            nd['x'], nd['y'] = pt[0], pt[1]
        else:
            dx, dy = pt[0] - nd['x'], pt[1] - nd['y']
            nd[kind] = [dx, dy]
            if nd.get('smooth'):
                other = 'hout' if kind == 'hin' else 'hin'
                nd[other] = [-dx, -dy]

    def convert_to_curves(self):
        """Turn the selected rect/ellipse/quick/line/poly/path into an editable node path."""
        o = self.sel
        if o is None or o not in self.objs:
            return
        if o.get('type') not in ('rect', 'ellipse', 'quick', 'line', 'poly', 'path'):
            return
        nodes, closed = nodes_from_obj(o)
        if not nodes:
            return
        self.snapshot()
        new = dict(type='nodes', nodes=nodes, closed=closed,
                   stroke=o.get('stroke'), sw=o.get('sw', 2),
                   fill=o.get('fill'), layer=self.obj_layer(o))
        for k in ('shadow', 'glow', 'grad', 'rot', 'opacity', 'gid', 'dash', 'arrow'):
            if o.get(k) is not None:
                new[k] = copy.deepcopy(o[k])
        i = self.objs.index(o); self.objs[i] = new
        self.set_selection([new])
        self.node_obj = new
        self.update()
        return new

    def combine_selection(self, op):
        """Boolean combine 2+ selected shapes into one node path via QPainterPath
        united / subtracted / intersected."""
        sel = self._selection()
        shapes = [o for o in sel if o.get('type') in ('rect', 'ellipse', 'quick', 'poly', 'nodes', 'path')]
        if len(shapes) < 2:
            return None
        self.snapshot()
        paths = [self._object_painterpath(o) for o in shapes]
        result = paths[0]
        for pp in paths[1:]:
            if op == 'union':
                result = result.united(pp)
            elif op == 'subtract':
                result = result.subtracted(pp)
            elif op == 'intersect':
                result = result.intersected(pp)
        result = result.simplified()
        nodes, closed = _nodes_from_painterpath(result)
        if not nodes:
            return None
        base = shapes[0]
        new = dict(type='nodes', nodes=nodes, closed=True,
                   stroke=base.get('stroke', '#1f2a30'), sw=base.get('sw', 2),
                   fill=base.get('fill', '#cfe3ef'), layer=self.obj_layer(base))
        for o in shapes:
            if o in self.objs:
                self.objs.remove(o)
        self.objs.append(new); self.set_selection([new]); self.update()
        return new

    def _object_painterpath(self, o):
        """A filled QPainterPath for a shape object in canvas coordinates (for combining)."""
        t = o['type']
        pp = QPainterPath()
        if t == 'rect':
            pp.addRect(QRectF(o['x'], o['y'], o['w'], o['h']))
        elif t == 'ellipse':
            pp.addEllipse(QRectF(o['x'], o['y'], o['w'], o['h']))
        elif t == 'quick':
            pp = quickshape_path(o['shape'], o['w'], o['h']).translated(o['x'], o['y'])
        elif t == 'nodes':
            pp = node_painter_path(o)
        elif t in ('poly', 'path'):
            pp.addPolygon(QPolygonF([QPointF(x, y) for x, y in o['pts']]))
            pp.closeSubpath()
        return pp

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
            # a transform handle on the single selected object takes priority
            h = self._hit_handle(pt)
            if h is not None:
                self.handle = h; self.drag_start = pt
                self.drag_orig = copy.deepcopy(self._selection())
                self.snapshot(); return
            hit = next((o for o in reversed(self.ordered_objs()) if obj_hit(o, pt)), None)
            shift = bool(e.modifiers() & Qt.ShiftModifier)
            if hit is None:
                if not shift: self.set_selection([])
                self.rubber = (pt, pt); self.drag_start = pt; self.update(); return
            cur = self._selection()
            if shift:
                members = self._group_members(hit)
                if hit in cur:
                    cur = [o for o in cur if o not in members]
                else:
                    cur = cur + [m for m in members if m not in cur]
                self.set_selection(cur)
            elif hit not in cur:
                self.set_selection([hit])
            self.drag_off = (pt[0], pt[1]); self.drag_orig = None
            self.update(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick'):
            self.start = pt; self.cur = pt; return
        if self.tool == 'text':
            self.win.place_text(pt); return
        if self.tool == 'image':
            self.win.import_image(at=pt); return
        if self.tool == 'freehand':
            self.snapshot()
            self.objs.append(dict(type='path', pts=[pt], stroke=self.stroke.name(), sw=self.sw, fill=None,
                                  closed=False, layer=self.active_layer))
            self.cur = pt; return
        if self.tool == 'pen':
            # Bézier pen: start a node here. A click leaves a corner node; a drag pulls out
            # symmetric control handles (a smooth node) — finished in mouseMoveEvent.
            if self.pen_nodes is None:
                self.snapshot(); self.pen_nodes = []
            self.pen_nodes.append({'x': pt[0], 'y': pt[1], 'hin': [0, 0], 'hout': [0, 0], 'smooth': False})
            self.pen_dragging = True; self.cur = pt; self.update(); return
        if self.tool == 'node':
            g = self._hit_node(pt)
            if g is not None:
                self.node_grab = g; self.drag_start = pt; self.snapshot(); return
            # clicking elsewhere picks a path to edit
            hit = next((o for o in reversed(self.ordered_objs())
                        if o.get('type') == 'nodes' and obj_hit(o, pt)), None)
            if hit is None:
                hit = next((o for o in reversed(self.ordered_objs()) if obj_hit(o, pt)), None)
                if hit is not None and hit.get('type') != 'nodes':
                    hit = None
            self.node_obj = hit; self.node_grab = None; self.update(); return

    def mouseMoveEvent(self, e):
        pt = self.pos(e); self.win.set_pos(pt)
        if self.tool == 'select' and self.handle is not None and (e.buttons() & Qt.LeftButton):
            self._drag_handle(pt, bool(e.modifiers() & Qt.ShiftModifier)); self.update(); return
        if self.tool == 'select' and self.rubber is not None and (e.buttons() & Qt.LeftButton):
            self.rubber = (self.drag_start, pt); self.update(); return
        if self.tool == 'select' and self.sel is not None and (e.buttons() & Qt.LeftButton) and self.drag_off:
            self._move_sel(pt); self.update(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick') and self.start and (e.buttons() & Qt.LeftButton):
            self.cur = pt; self.update()
        elif self.tool == 'freehand' and (e.buttons() & Qt.LeftButton) and self.objs:
            self.objs[-1]['pts'].append(pt); self.update()
        elif self.tool == 'pen' and self.pen_nodes:
            if self.pen_dragging and (e.buttons() & Qt.LeftButton):
                # drag out symmetric control handles on the node just placed → smooth node
                nd = self.pen_nodes[-1]
                dx, dy = pt[0] - nd['x'], pt[1] - nd['y']
                nd['hout'] = [dx, dy]; nd['hin'] = [-dx, -dy]; nd['smooth'] = True
            self.cur = pt; self.update()
        elif self.tool == 'node' and self.node_grab is not None and (e.buttons() & Qt.LeftButton):
            self._drag_node_to(pt); self.update()

    def mousePressSnapMove(self): pass

    def _move_sel(self, pt):
        sel = self._selection()
        if not sel: return
        # record the gesture start once, so a drag is a single undo step
        if self.drag_orig is None:
            self.snapshot(); self.drag_orig = True
        dx = pt[0] - self.drag_off[0]; dy = pt[1] - self.drag_off[1]
        self.drag_off = (pt[0], pt[1])
        for o in sel: self._shift_obj(o, dx, dy)
        # snap the whole selection as one, by its combined bounding box
        rects = [obj_bounds(o) for o in sel]
        combo = rects[0]
        for r in rects[1:]: combo = combo.united(r)
        sdx, sdy = self._snap_delta(combo, sel)
        if sdx or sdy:
            for o in sel: self._shift_obj(o, sdx, sdy)

    def _drag_handle(self, pt, shift):
        """Resize (corner/edge) or rotate the single selected object from its handle."""
        sel = self._selection()
        if len(sel) != 1 or not self.drag_orig: return
        o = sel[0]; orig = self.drag_orig[0]
        if self.handle == 'rot':
            cx, cy = obj_center(orig)
            ang = math.degrees(math.atan2(pt[1] - cy, pt[0] - cx)) + 90
            if shift: ang = round(ang / 15) * 15
            o['rot'] = round(ang, 2)
            return
        # resize: work in the object's *local* (unrotated) frame
        r0 = obj_rect(orig); a = obj_rot(orig)
        cx, cy = r0.center().x(), r0.center().y()
        lx, ly = pt
        if a:
            rad = math.radians(-a); cosa, sina = math.cos(rad), math.sin(rad)
            dx, dy = lx - cx, ly - cy
            lx, ly = cx + dx * cosa - dy * sina, cy + dx * sina + dy * cosa
        L, T, R, B = r0.left(), r0.top(), r0.right(), r0.bottom()
        hk = self.handle
        if 'w' in hk: L = lx
        if 'e' in hk: R = lx
        if 'n' in hk: T = ly
        if 's' in hk: B = ly
        nw = max(1.0, abs(R - L)); nh = max(1.0, abs(T - B))
        if shift and hk in ('nw', 'ne', 'se', 'sw'):   # proportional from the fixed corner
            sx = nw / (r0.width() or 1); sy = nh / (r0.height() or 1); s = max(sx, sy)
            nw = (r0.width() or 1) * s; nh = (r0.height() or 1) * s
            if 'w' in hk: L = R - nw
            else: R = L + nw
            if 'n' in hk: T = B - nh
            else: B = T + nh
        nx, ny = min(L, R), min(T, B)
        self._apply_resize(o, orig, nx, ny, nw, nh)

    def _apply_resize(self, o, orig, nx, ny, nw, nh):
        """Scale/reposition an object to the new local box (nx, ny, nw, nh)."""
        t = o['type']
        if t in ('rect', 'ellipse', 'quick', 'image'):
            o['x'], o['y'], o['w'], o['h'] = nx, ny, nw, nh
        elif t == 'text':
            # scale the pixel size by the height change; keep the top-left anchor
            r0 = obj_rect(orig); factor = nh / (r0.height() or 1)
            o['x'], o['y'] = nx, ny
            o['size'] = max(1, int(round(orig.get('size', 48) * factor)))
        elif t == 'nodes':
            r0 = obj_rect(orig)
            ox, oy = r0.x(), r0.y(); ow, oh = r0.width() or 1, r0.height() or 1
            sx, sy = nw / ow, nh / oh
            o['nodes'] = []
            for nd in orig['nodes']:
                o['nodes'].append({'x': nx + (nd['x'] - ox) * sx, 'y': ny + (nd['y'] - oy) * sy,
                                   'hin': [nd.get('hin', [0, 0])[0] * sx, nd.get('hin', [0, 0])[1] * sy],
                                   'hout': [nd.get('hout', [0, 0])[0] * sx, nd.get('hout', [0, 0])[1] * sy],
                                   'smooth': nd.get('smooth', False)})
        else:
            r0 = obj_rect(orig)
            ox, oy = r0.x(), r0.y(); ow, oh = r0.width() or 1, r0.height() or 1
            sx, sy = nw / ow, nh / oh
            o['pts'] = [(nx + (x - ox) * sx, ny + (y - oy) * sy) for x, y in orig['pts']]

    def mouseReleaseEvent(self, e):
        if self.tool in ('rect', 'ellipse', 'line', 'quick') and self.start:
            if self.cur and (abs(self.cur[0] - self.start[0]) > 2 or abs(self.cur[1] - self.start[1]) > 2):
                self.snapshot(); self.objs.append(self._shape_from(self.start, self.cur))
                self.set_selection([self.objs[-1]])
            self.start = self.cur = None; self.update(); self.win.sync_props()
        elif self.tool == 'select' and self.handle is not None:
            self.handle = None; self.drag_start = self.drag_orig = None; self.update(); self.win.sync_props()
        elif self.tool == 'select' and self.rubber is not None:
            a, b = self.rubber; box = QRectF(QPointF(*a), QPointF(*b)).normalized()
            self.rubber = None
            if box.width() > 3 or box.height() > 3:
                picked = [o for o in self.ordered_objs() if box.contains(obj_bounds(o))
                          or box.intersects(obj_bounds(o))]
                self.set_selection(picked)
            self.drag_start = None; self.update()
        elif self.tool == 'select' and self.sel is not None and self.drag_off:
            self.drag_off = None; self.drag_orig = None
        elif self.tool == 'pen' and self.pen_dragging:
            self.pen_dragging = False; self.update()
        elif self.tool == 'node' and self.node_grab is not None:
            self.node_grab = None; self.drag_start = None

    def _finish_pen(self, closed):
        """Commit the Bézier pen's nodes as a node path — closed+filled or open."""
        if not self.pen_nodes or len(self.pen_nodes) < 2:
            self.pen_nodes = None; self.pen_dragging = False; self.cur = None; self.update(); return
        o = dict(type='nodes', nodes=[dict(x=n['x'], y=n['y'], hin=list(n['hin']),
                                           hout=list(n['hout']), smooth=n['smooth']) for n in self.pen_nodes],
                 stroke=self.stroke.name(), sw=self.sw,
                 fill=self.fill.name() if closed else None, closed=closed, layer=self.active_layer)
        self.objs.append(o); self.set_selection([o])
        self.pen_nodes = None; self.pen_dragging = False; self.cur = None; self.update()

    def mouseDoubleClickEvent(self, e):
        if self.tool == 'pen' and self.pen_nodes and len(self.pen_nodes) >= 2:
            # the double-click fires an extra press that duplicates the last node — drop it
            if len(self.pen_nodes) >= 2:
                a, b = self.pen_nodes[-2], self.pen_nodes[-1]
                if abs(a['x'] - b['x']) < 3 and abs(a['y'] - b['y']) < 3 and b['hout'] == [0, 0]:
                    self.pen_nodes.pop()
            self._finish_pen(closed=True)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self._selection():
            self.snapshot()
            for o in self._selection():
                if o in self.objs: self.objs.remove(o)
            self.sel = None; self.sels = []; self.update(); self.win.sync_props()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.tool == 'pen' and self.pen_nodes and len(self.pen_nodes) >= 2:
            self._finish_pen(closed=False)

    def apply_to_sel(self, fill=None, stroke=None, sw=None):
        sel = self._selection()
        if not sel: return
        self.snapshot()
        for o in sel:
            if fill is not None: o['fill'] = fill; o.pop('grad', None)  # a solid fill replaces any gradient
            if stroke is not None: o['stroke'] = stroke
            if sw is not None: o['sw'] = sw
        self.update()

    def render_to(self, painter, skip_text=False, skip_special=False):
        """Paint every object. For SVG export, skip_special also omits image and node
        objects so they can be spliced as explicit <image>/<path> elements afterwards."""
        for o in self.ordered_objs():
            if skip_special and o.get('type') in ('image', 'nodes'):
                continue
            paint_object(painter, o, False, skip_text=skip_text)

    def export_svg(self, path):
        import json, base64, re
        gen = QSvgGenerator(); gen.setFileName(path); gen.setSize(QSize(self.W, self.H))
        gen.setViewBox(QRect(0, 0, self.W, self.H)); gen.setTitle('just a... DRAWmaster')
        # Embed the editable object model so DRAWmaster can re-open its own SVGs losslessly.
        # Strip transient keys (e.g. an image object's decoded _qimg cache) first.
        clean = [{k: v for k, v in o.items() if not k.startswith('_')} for o in self.objs]
        blob = base64.b64encode(json.dumps({'W': self.W, 'H': self.H, 'objs': clean,
                                             'layers': self.layers}).encode()).decode()
        gen.setDescription('justadraw1:' + blob)
        # QSvgGenerator renders shapes (gradients become <linearGradient>/<radialGradient>
        # natively) but turns glyphs into paths — so we skip text here and splice real
        # <text> elements in afterwards, in paint order, for an editable, browser-true SVG.
        p = QPainter(gen); p.setRenderHint(QPainter.Antialiasing)
        self.render_to(p, skip_text=True, skip_special=True); p.end()
        # Splice real, browser-true elements for text, images and node paths — in paint
        # order, so they stack correctly relative to one another. (Native shapes rendered
        # by QSvgGenerator sit below them, matching the previous text-splicing behaviour;
        # the embedded JSON model always carries the exact z-order for re-opening.)
        defs, els = [], []
        for i, o in enumerate(self.ordered_objs()):
            t = o.get('type')
            if t == 'text':
                d, e = svg_text_el(o, i)
            elif t == 'image':
                d, e = '', svg_image_el(o)
            elif t == 'nodes':
                d, e = svg_node_el(o, i)
            else:
                continue
            if d: defs.append(d)
            if e: els.append(e)
        if els:
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
            self.snapshot(); self.objs = data.get('objs', []); self.sel = None; self.sels = []
            self.W = int(data.get('W', self.W)); self.H = int(data.get('H', self.H))
            self.restore_layers(data.get('layers')); self._fit()
            gids = [o['gid'] for o in self.objs if isinstance(o.get('gid'), int)]
            self._next_gid = (max(gids) + 1) if gids else 1
            return True
        except Exception:
            return False

    def export_png(self, path):
        img = QImage(self.W, self.H, QImage.Format_ARGB32); img.fill(QColor('#ffffff'))
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); self.render_to(p); p.end()
        return img.save(path)


class Main(QMainWindow):
    TOOLS = [('select', 'Select', '⬚'), ('node', 'Node (edit curves)', '⌇'),
             ('freehand', 'Freehand', '✎'), ('pen', 'Pen (Bézier curves)', '✐'),
             ('line', 'Line', '╱'), ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'),
             ('quick', 'QuickShape', '★'), ('text', 'Text', 'T'), ('image', 'Image', '🖻')]

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
            a.triggered.connect(lambda _=0, t=tid: self.set_tool(t)); self.tg.addAction(a); tt.addAction(a)
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

    def set_tool(self, t):
        """Switch the active tool, tidying up any tool-specific drag state."""
        c = self.canvas
        if c.pen_nodes and t != 'pen':
            c.pen_nodes = None; c.pen_dragging = False; c.cur = None
        c.tool = t
        if t == 'node':
            # start editing whatever is selected, if it is (or can become) a node path
            c.node_obj = c.sel if (c.sel and c.sel.get('type') == 'nodes') else None
        else:
            c.node_obj = None; c.node_grab = None
        c.update()

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

    # ---------------------------------------------------------------- image import
    def import_image(self, at=None):
        """Place a picture on the canvas as an image object. The file is embedded as a
        data-URI so the drawing (and its SVG) stays self-contained."""
        path, _ = QFileDialog.getOpenFileName(self, 'Import Image', _just_dir('pics'),
                                              'Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All files (*)')
        if not path:
            self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True); return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP, 'Could not read that image file.'); return
        try:
            uri = image_data_uri(path)
        except OSError:
            QMessageBox.warning(self, APP, 'Could not read that image file.'); return
        w, h = img.width() or 1, img.height() or 1
        # fit a large image sensibly onto the canvas, keeping its aspect ratio
        maxw, maxh = self.canvas.W * 0.8, self.canvas.H * 0.8
        s = min(1.0, maxw / w, maxh / h)
        dw, dh = w * s, h * s
        x = at[0] if at else (self.canvas.W - dw) / 2
        y = at[1] if at else (self.canvas.H - dh) / 2
        self.canvas.snapshot()
        o = dict(type='image', x=x, y=y, w=dw, h=dh, src=uri, stroke=None, sw=0,
                 fill=None, layer=self.canvas.active_layer)
        self.canvas.objs.append(o); self.canvas.set_selection([o])
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
        if o is None or o.get('type') not in ('rect', 'ellipse', 'quick', 'poly', 'nodes', 'text'):
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

    # ---------------------------------------------------------------- curves / combine
    def convert_to_curves(self):
        o = self.canvas.sel
        if o is None or o.get('type') not in ('rect', 'ellipse', 'quick', 'line', 'poly', 'path'):
            QMessageBox.information(self, APP, 'Select a rectangle, ellipse, QuickShape, line or pen shape, '
                                   'then Convert to Curves to edit it with the Node tool.')
            return
        new = self.canvas.convert_to_curves()
        if new is not None:
            self.canvas.tool = 'node'; self.tool_acts['node'].setChecked(True)
            self.refresh_layers()

    def combine(self, op):
        new = self.canvas.combine_selection(op)
        if new is None:
            QMessageBox.information(self, APP, 'Select two or more overlapping shapes first, then Combine.')
            return
        self.refresh_layers()

    # ---------------------------------------------------------------- opacity / dash / arrows
    def opacity_dialog(self):
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first, then set its opacity.')
            return
        cur = int(round(obj_opacity(o) * 100))
        n, ok = QInputDialog.getInt(self, 'Opacity', 'Opacity (0–100 %):', cur, 0, 100, 5)
        if ok:
            self.canvas.snapshot()
            if n >= 100: o.pop('opacity', None)
            else: o['opacity'] = n / 100.0
            self.canvas.update()

    def line_style_dialog(self):
        """Dash style + arrowheads for the selected line / open path / open node path."""
        o = self.canvas.sel
        if o is None or o.get('type') not in ('line', 'path', 'poly', 'nodes'):
            QMessageBox.information(self, APP, 'Select a line, a freehand/pen path or a node path first, '
                                   'then set its dash style and arrowheads.')
            return
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        dlg = QDialog(self); dlg.setWindowTitle('Line Style — Dashes & Arrowheads'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        dcb = QComboBox()
        for lbl, k in (('Solid', 'solid'), ('Dashed', 'dashed'), ('Dotted', 'dotted')):
            dcb.addItem(lbl, k)
        dcb.setCurrentIndex(max(0, [i for i in range(dcb.count())
                                    if dcb.itemData(i) == o.get('dash', 'solid')][0] if o.get('dash', 'solid') in
                                   ('solid', 'dashed', 'dotted') else 0))
        acb = QComboBox()
        for lbl, k in (('None', 'none'), ('Start', 'start'), ('End', 'end'), ('Both ends', 'both')):
            acb.addItem(lbl, k)
        cur_arrow = o.get('arrow', 'none')
        acb.setCurrentIndex(next((i for i in range(acb.count()) if acb.itemData(i) == cur_arrow), 0))
        form.addRow('Dash style:', dcb); form.addRow('Arrowheads:', acb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        o['dash'] = dcb.currentData(); o['arrow'] = acb.currentData()
        if o['dash'] == 'solid': o.pop('dash', None)
        if o['arrow'] == 'none': o.pop('arrow', None)
        self.canvas.update()

    # ---------------------------------------------------------------- PDF & print
    def export_pdf(self):
        """Write a vector PDF at the canvas size, painting through paint_object so text
        stays text and shapes stay paths."""
        start = (os.path.splitext(self.path)[0] if self.path else os.path.join(_just_dir('docs'), 'drawing')) + '.pdf'
        path, _ = QFileDialog.getSaveFileName(self, 'Export PDF', start, 'PDF (*.pdf)')
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        self._paint_pdf(path)
        _justapps_recent('draw', path); self.statusBar().showMessage(f'Exported {path}', 4000)

    def _paint_pdf(self, path):
        from PySide6.QtCore import QSizeF
        W, H = self.canvas.W, self.canvas.H
        w = QPdfWriter(path); w.setResolution(96)
        # page size given in points (1 pt = 1/72"); treat canvas px as points at 72dpi so the
        # PDF page matches the canvas dimensions. ExactMatch keeps the exact W×H.
        psize = QPageSize(QSizeF(W, H), QPageSize.Point, '', QPageSize.ExactMatch)
        layout = QPageLayout(psize, QPageLayout.Portrait, QMarginsF(0, 0, 0, 0))
        w.setPageLayout(layout)
        p = QPainter(w); p.setRenderHint(QPainter.Antialiasing)
        # device is in dots at w.resolution() dpi; points→dots factor keeps 1 canvas px = 1 pt
        dpr = w.resolution() / 72.0
        p.scale(dpr, dpr)
        self.canvas.render_to(p)
        p.end()

    def print_drawing(self):
        """Print the drawing via the system print dialog, using the same vector paint path."""
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._paint_printer(printer)
        self.statusBar().showMessage('Sent to printer.', 4000)

    def _paint_printer(self, printer):
        W, H = self.canvas.W, self.canvas.H
        p = QPainter(printer); p.setRenderHint(QPainter.Antialiasing)
        area = printer.pageRect(QPrinter.DevicePixel)
        s = min(area.width() / W, area.height() / H)
        p.translate(area.x(), area.y()); p.scale(s, s)
        self.canvas.render_to(p)
        p.end()

    def build_menu(self):
        m = self.menuBar()
        f = m.addMenu('&File')
        f.addAction(self.act('&New…', self.new, QKeySequence.New))
        f.addAction(self.act('&Open SVG…', self.open_svg, QKeySequence.Open))
        f.addAction(self.act('&Save as SVG…', self.save_svg, QKeySequence.Save))
        f.addAction(self.act('&Export PNG…', self.export_png))
        f.addAction(self.act('Export P&DF…', self.export_pdf))
        f.addAction(self.act('&Import Image…', self.import_image))
        f.addAction(self.act('&Print…', self.print_drawing, QKeySequence.Print))
        f.addAction(self.act('Edit in &PAINTcanvas…', self.edit_in_paint))
        f.addSeparator(); f.addAction(self.act('&Quit', self.close, QKeySequence.Quit))
        e = m.addMenu('&Edit')
        e.addAction(self.act('&Undo', self.canvas.do_undo, QKeySequence.Undo))
        e.addAction(self.act('&Redo', self.canvas.do_redo, QKeySequence.Redo))
        e.addSeparator()
        e.addAction(self.act('Edit &Text…', self.edit_text))
        e.addAction(self.act('&Gradient Fill…', self.gradient_dialog))
        e.addAction(self.act('&Opacity…', self.opacity_dialog))
        e.addAction(self.act('&Line Style (Dashes & Arrows)…', self.line_style_dialog))
        e.addSeparator()
        e.addAction(self.act('Convert to &Curves', self.convert_to_curves, QKeySequence('Ctrl+Shift+C')))
        a = m.addMenu('&Arrange')
        a.addAction(self.act('Bring to &Front', lambda: self.canvas.z_order('front'), QKeySequence('Ctrl+Shift+]')))
        a.addAction(self.act('Send to &Back', lambda: self.canvas.z_order('back'), QKeySequence('Ctrl+Shift+[')))
        a.addAction(self.act('Bring For&ward', lambda: self.canvas.z_order('forward'), QKeySequence('Ctrl+]')))
        a.addAction(self.act('Send Back&ward', lambda: self.canvas.z_order('backward'), QKeySequence('Ctrl+[')))
        a.addSeparator()
        a.addAction(self.act('&Group', self.canvas.group_selection, QKeySequence('Ctrl+G')))
        a.addAction(self.act('&Ungroup', self.canvas.ungroup_selection, QKeySequence('Ctrl+Shift+G')))
        cm = a.addMenu('Com&bine')
        cm.addAction(self.act('&Union (Add)', lambda: self.combine('union')))
        cm.addAction(self.act('&Subtract (Front from Back)', lambda: self.combine('subtract')))
        cm.addAction(self.act('&Intersect', lambda: self.combine('intersect')))
        al = a.addMenu('A&lign')
        for lbl, how in (('Align Left', 'left'), ('Align Centre', 'hcenter'), ('Align Right', 'right'),
                         ('Align Top', 'top'), ('Align Middle', 'vcenter'), ('Align Bottom', 'bottom')):
            al.addAction(self.act(lbl, lambda _=0, h=how: self.canvas.align_selection(h)))
        ds = a.addMenu('&Distribute')
        ds.addAction(self.act('Distribute Horizontally', lambda: self.canvas.distribute_selection('h')))
        ds.addAction(self.act('Distribute Vertically', lambda: self.canvas.distribute_selection('v')))
        a.addSeparator()
        a.addAction(self.act('Show &Layers Panel', lambda: self.layers_dock.setVisible(True)))
        v = m.addMenu('&View')
        self.grid_act = self.act('Show &Grid', self.toggle_grid, QKeySequence('Ctrl+\''))
        self.grid_act.setCheckable(True); v.addAction(self.grid_act)
        v.addAction(self.act('Grid &Spacing…', self.grid_spacing_dialog))
        self.snap_act = self.act('&Snap to Grid && Guides', self.toggle_snap)
        self.snap_act.setCheckable(True); self.snap_act.setChecked(self.canvas.snap); v.addAction(self.snap_act)
        v.addSeparator()
        v.addAction(self.act('Add &Horizontal Guide…', lambda: self.add_guide_dialog('h')))
        v.addAction(self.act('Add &Vertical Guide…', lambda: self.add_guide_dialog('v')))
        v.addAction(self.act('&Clear Guides', self.canvas.clear_guides))
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

    # ---------------------------------------------------------------- view: grid/snap/guides
    def toggle_grid(self):
        self.canvas.set_grid(on=self.grid_act.isChecked())

    def toggle_snap(self):
        self.canvas.snap = self.snap_act.isChecked()

    def grid_spacing_dialog(self):
        n, ok = QInputDialog.getInt(self, 'Grid spacing', 'Grid spacing (pixels):',
                                    self.canvas.grid, 2, 500, 1)
        if ok:
            self.canvas.set_grid(spacing=n)
            self.grid_act.setChecked(True); self.canvas.set_grid(on=True)

    def add_guide_dialog(self, orient):
        W = self.canvas.W if orient == 'v' else self.canvas.H
        label = 'X position (pixels):' if orient == 'v' else 'Y position (pixels):'
        n, ok = QInputDialog.getInt(self, 'Add guide', label, W // 2, 0, max(W, 10000), 1)
        if ok: self.canvas.add_guide(orient, n)

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
            self.canvas.snapshot(); self.canvas.objs = []; self.canvas.sel = None; self.canvas.sels = []
            self.canvas.W, self.canvas.H = w, h
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
