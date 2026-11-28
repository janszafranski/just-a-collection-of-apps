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
                                   QListWidget, QListWidgetItem, QLineEdit, QInputDialog,
                                   QGridLayout, QSlider, QFormLayout, QDoubleSpinBox, QToolButton,
                                   QButtonGroup, QRadioButton, QCheckBox, QDialogButtonBox, QFrame,
                                   QSizePolicy)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QFont, QFontMetricsF, QPainterPath, QActionGroup, QPolygonF,
                               QLinearGradient, QRadialGradient, QPdfWriter, QPageSize, QPageLayout, QTransform)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings, QMarginsF, QBuffer, QByteArray, QTimer, QSizeF
    from PySide6.QtSvg import QSvgGenerator
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    sys.stderr.write("just a... DRAWmaster needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... DRAWmaster"
ORG = "justadrawmaster"
VERSION = "1.17-00"


# ===================================================================== font grouping
# FontManager-style grouping of the system fonts by broad style, shared with the rest
# of the just a... CREATORsuite (classifier copied verbatim from PAGEdesigner).
from PySide6.QtWidgets import QComboBox as _QComboBox
from PySide6.QtGui import QStandardItem as _QStandardItem
from PySide6.QtCore import Signal as _Signal
FONT_CATEGORY_ORDER = ['Sans serif', 'Serif', 'Slab serif', 'Display',
                       'Script', 'Handwriting', 'Monospace']


def font_category(name):
    """Classify a font family into a broad style group by its name (heuristic)."""
    n = (name or '').lower()
    def has(*ks): return any(k in n for k in ks)
    if has('mono', 'consol', 'courier', ' code', 'cousine', 'inconsolata', 'fira code', 'jetbrains', 'source code'):
        return 'Monospace'
    if has('script', 'brush', 'pacifico', 'lobster', 'dancing', 'satisfy', 'sacramento', 'allura',
           'alex brush', 'great vibes', 'tangerine', 'kaushan', 'cookie', 'parisienne', 'yellowtail',
           'pinyon', 'niconne', 'cursive', 'calligraph', 'vibes', 'pacific'):
        return 'Script'
    if has('hand', 'marker', 'permanent', 'indie', 'shadows into', 'gochi', 'patrick', 'architects',
           'reenie', 'nanum pen', 'just another', 'caveat', 'amatic', 'kalam', 'gloria', 'neucha'):
        return 'Handwriting'
    if has('slab', 'rockwell', 'zilla', 'josefin slab'):
        return 'Slab serif'
    if has('black', 'ultra', 'heavy', 'poster', 'display', 'titan', 'anton', 'bungee', 'bangers',
           'fredoka', 'righteous', 'alfa', 'abril', 'archivo black', 'bebas', 'oswald', 'passion',
           'staatliches', 'teko', 'fjalla', 'monoton', 'bowlby', 'creepster', 'faster', 'bowlby',
           'graduate', 'luckiest', 'bagel', 'bungee', 'rubik mono', 'squada', 'orbitron', 'press start'):
        return 'Display'
    if has('serif', 'times', 'georgia', 'garamond', ' roman', 'playfair', 'merriweather', 'lora',
           'pt serif', 'noto serif', 'crimson', 'cormorant', 'baskerville', 'eb garamond', 'vollkorn',
           'spectral', 'bitter', 'source serif', 'domine', 'frank ruhl', 'cardo', 'gentium', 'alegreya',
           'arvo', 'tinos', 'liberation serif'):
        return 'Serif'
    return 'Sans serif'


def group_fonts_by_style(families):
    """Return an OrderedDict {category: [families]} for the given font families,
    sorted within each group, categories in a fixed order, empty groups dropped."""
    import collections as _c
    cats = _c.OrderedDict((c, []) for c in FONT_CATEGORY_ORDER)
    for fam in families:
        cats[font_category(fam)].append(fam)
    return _c.OrderedDict((c, sorted(f, key=str.lower)) for c, f in cats.items() if f)


class GroupedFontCombo(_QComboBox):
    """A drop-in replacement for QFontComboBox that lists the system font families
    grouped by broad STYLE (Sans serif / Serif / Slab serif / Display / Script /
    Handwriting / Monospace), each under a disabled, non-selectable header. Every
    family item previews in its own typeface and carries the family string as its
    Qt.UserRole data. Emits familyChanged(str) when the selected family changes."""
    familyChanged = _Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.currentIndexChanged.connect(self._on_index)

    def _build(self):
        from PySide6.QtGui import QFontDatabase, QFont, QBrush, QColor
        from PySide6.QtCore import Qt
        fams = [f for f in QFontDatabase.families() if not f.startswith('.')]
        model = self.model()
        for cat, group in group_fonts_by_style(fams).items():
            hdr = _QStandardItem(cat)
            hf = QFont(); hf.setBold(True); hf.setPointSize(8)
            hdr.setFont(hf)
            hdr.setForeground(QBrush(QColor('#888888')))
            hdr.setFlags(Qt.NoItemFlags)   # disabled + non-selectable header
            model.appendRow(hdr)
            for fam in group:
                it = _QStandardItem(fam)
                pf = QFont(fam); pf.setPointSize(11)
                it.setFont(pf)
                it.setData(fam, Qt.UserRole)
                model.appendRow(it)
        # start on the first real family, never on a header row
        for i in range(self.count()):
            if self.itemData(i, Qt.UserRole):
                self.setCurrentIndex(i)
                break

    def _on_index(self, idx):
        fam = self.currentFamily()
        if fam:
            self.familyChanged.emit(fam)

    def currentFamily(self):
        return self.currentData(Qt.UserRole) or self.currentText()

    def setCurrentFamily(self, fam):
        if not fam:
            return
        target = str(fam).lower()
        for i in range(self.count()):
            d = self.itemData(i, Qt.UserRole)
            if d and str(d).lower() == target:
                self.setCurrentIndex(i)
                return
        # fall back to an exact text match if no data item lines up
        i = self.findText(str(fam))
        if i >= 0:
            self.setCurrentIndex(i)
# =====================================================================
TEXTURE_LIB = os.path.expanduser('~/.local/share/justapps/textures')
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


# ---------------------------------------------------------------- measurement units
# The drawing is always stored in pixels; units only change how lengths are *shown*
# (the status-bar readout and dimension-line labels). 96 px = 1 inch = 25.4 mm.
UNIT_PER_PX = {'px': 1.0, 'mm': 25.4 / 96.0, 'cm': 2.54 / 96.0}
UNIT_LABELS = [('Pixels', 'px'), ('Millimetres', 'mm'), ('Centimetres', 'cm')]

# Connectors resolve their object anchors against whatever object list is being painted.
# The canvas sets this before each paint so draw_connector() can find anchored objects
# even though paint_object() is otherwise given a single object.
_PAINT_OBJS = []


# ---------------------------------------------------------------- QuickShapes
QUICKSHAPES = [
    ('triangle', 'Triangle'), ('rtriangle', 'Right triangle'), ('diamond', 'Diamond'),
    ('pentagon', 'Pentagon'), ('hexagon', 'Hexagon'), ('octagon', 'Octagon'),
    ('star5', 'Star (5-point)'), ('star6', 'Star (6-point)'), ('arrow', 'Arrow'),
    ('darrow', 'Double arrow'), ('chevron', 'Chevron'), ('plus', 'Cross'),
    ('parallelogram', 'Parallelogram'), ('trapezoid', 'Trapezoid'), ('heart', 'Heart'),
    ('lightning', 'Lightning bolt'), ('speech', 'Speech bubble'), ('cloud', 'Cloud'),
    ('moon', 'Moon'), ('sun', 'Sun'), ('gear', 'Gear'),
]

# QuickShapes whose geometry has an adjustable parameter, surfaced as one draggable
# "cog" handle on the canvas (à la DrawPlus): key -> (param, label, lo, hi, default).
# 'points' = number of points/sides, 'inner' = star waist, 'phase' = moon fullness,
# 'teeth' = gear teeth. The value is stored on the object as o['qp'][param].
ADJUSTABLE_QS = {
    'star5':   ('inner', 'Star waist', 0.15, 0.85, 0.42),
    'star6':   ('inner', 'Star waist', 0.20, 0.90, 0.50),
    'pentagon':('points', 'Sides', 3, 12, 5),
    'hexagon': ('points', 'Sides', 3, 12, 6),
    'octagon': ('points', 'Sides', 3, 12, 8),
    'moon':    ('phase', 'Moon phase', 0.05, 0.95, 0.5),
    'sun':     ('points', 'Rays', 6, 24, 12),
    'gear':    ('teeth', 'Teeth', 5, 18, 9),
}

# Blend (compositing) modes for the Transparency panel: label -> (QPainter mode key,
# CSS mix-blend-mode name for SVG). The painter mode is resolved lazily (needs QPainter).
BLEND_MODES = [
    ('Normal', 'SourceOver', 'normal'), ('Multiply', 'Multiply', 'multiply'),
    ('Screen', 'Screen', 'screen'), ('Overlay', 'Overlay', 'overlay'),
    ('Darken', 'Darken', 'darken'), ('Lighten', 'Lighten', 'lighten'),
    ('Colour Dodge', 'ColorDodge', 'color-dodge'), ('Colour Burn', 'ColorBurn', 'color-burn'),
    ('Hard Light', 'HardLight', 'hard-light'), ('Soft Light', 'SoftLight', 'soft-light'),
    ('Difference', 'Difference', 'difference'), ('Exclusion', 'Exclusion', 'exclusion'),
]
BLEND_CSS = {k: css for _, k, css in BLEND_MODES}

# Named colour palettes for the Swatches panel (mirrors DrawPlus's swatch tabs).
SWATCH_PALETTES = {
    'Standard': ['#000000', '#444444', '#888888', '#bbbbbb', '#ffffff', '#e01b24',
                 '#ff7800', '#f6d32d', '#33d17a', '#2ec27e', '#3584e4', '#1a5fb4',
                 '#9141ac', '#e66100', '#c64600', '#613583'],
    'Mid Tones': ['#5b7a8c', '#6d8a7a', '#8a7a6d', '#8c6d7a', '#7a6d8c', '#6d7a8c',
                  '#9bae9b', '#aebb9b', '#bb9bae', '#9baebb', '#c0ad8f', '#8fadc0',
                  '#a89bae', '#aec09b', '#c09ba8', '#9bc0ad'],
    'Earth': ['#3b2f2f', '#6b4f2f', '#8a6d3b', '#a9814f', '#c6a76b', '#e3cf9e',
              '#5c6b3b', '#7a8a4f', '#4f6b5c', '#2f4f4f', '#7a5c3b', '#9e7a4f'],
    'Vivid': ['#ff0040', '#ff6a00', '#ffd400', '#9bff00', '#00ff88', '#00e5ff',
              '#007bff', '#5a00ff', '#c400ff', '#ff00aa', '#ff2975', '#00ffd0'],
    'Greyscale': ['#000000', '#1a1a1a', '#333333', '#4d4d4d', '#666666', '#808080',
                  '#999999', '#b3b3b3', '#cccccc', '#e6e6e6', '#f2f2f2', '#ffffff'],
}

# Preset object styles for the Styles panel: name -> fill / stroke / width / dash.
# Clicking one restyles the selection (like dropping a DrawPlus Line/Fill style on it).
DRAW_STYLES = [
    ('Ink outline',   dict(fill=None,        stroke='#1f2a30', sw=3, dash='solid')),
    ('Soft blue',     dict(fill='#cfe3ef',   stroke='#2b6c9c', sw=2, dash='solid')),
    ('Sunshine',      dict(fill='#ffe08a',   stroke='#e0a500', sw=3, dash='solid')),
    ('Leaf',          dict(fill='#bfe3b2',   stroke='#3a7d2c', sw=3, dash='solid')),
    ('Rose',          dict(fill='#f6c6d4',   stroke='#c3456b', sw=2, dash='solid')),
    ('Night',         dict(fill='#2b3a55',   stroke='#8fa6c9', sw=2, dash='solid')),
    ('Dashed red',    dict(fill=None,        stroke='#e01b24', sw=3, dash='dash')),
    ('Fat marker',    dict(fill='#ffffff',   stroke='#111111', sw=8, dash='solid')),
    ('Dotted grey',   dict(fill=None,        stroke='#666666', sw=2, dash='dot')),
    ('Mono fill',     dict(fill='#333333',   stroke=None,      sw=0, dash='solid')),
    ('Sky gradient',  dict(fill='#bfe0ff',   stroke='#3a7bd5', sw=2, dash='solid')),
    ('Coral',         dict(fill='#ff9478',   stroke='#d23b1f', sw=3, dash='solid')),
]


def _blend_mode(key):
    """Resolve a BLEND_MODES key to a QPainter.CompositionMode enum."""
    return getattr(QPainter, 'CompositionMode_' + key, QPainter.CompositionMode_SourceOver)
QS_KEYS = [k for k, _ in QUICKSHAPES]

def _qs_poly(pts):
    pp = QPainterPath(); pp.addPolygon(QPolygonF([QPointF(x, y) for x, y in pts])); pp.closeSubpath(); return pp

def quickshape_path(name, w, h, qp=None):
    """Outline for a QuickShape, optionally adjusted by qp (a dict of parameter values,
    see ADJUSTABLE_QS). qp lets a star change its waist, a polygon its side-count, the
    moon its phase, etc."""
    qp = qp or {}
    cx, cy = w / 2, h / 2
    if name == 'triangle':  return _qs_poly([(cx, 0), (w, h), (0, h)])
    if name == 'rtriangle': return _qs_poly([(0, 0), (0, h), (w, h)])
    if name == 'diamond':   return _qs_poly([(cx, 0), (w, cy), (cx, h), (0, cy)])
    if name in ('pentagon', 'hexagon', 'octagon'):
        n = int(qp.get('points', {'pentagon': 5, 'hexagon': 6, 'octagon': 8}[name])); off = -math.pi / 2
        return _qs_poly([(cx + cx * math.cos(off + i * 2 * math.pi / n),
                          cy + cy * math.sin(off + i * 2 * math.pi / n)) for i in range(n)])
    if name in ('star5', 'star6'):
        n = 5 if name == 'star5' else 6; off = -math.pi / 2
        inner = float(qp.get('inner', 0.42 if n == 5 else 0.5))
        pts = []
        for i in range(n * 2):
            k = 1.0 if i % 2 == 0 else inner; a = off + i * math.pi / n
            pts.append((cx + cx * k * math.cos(a), cy + cy * k * math.sin(a)))
        return _qs_poly(pts)
    if name == 'moon':
        # A crescent = the disc minus a disc shifted right by w*phase. The leftover lit
        # sliver grows with phase: →0 a thin sliver, 0.5 ≈ half-moon, →1 nearly full.
        phase = max(0.05, min(0.95, float(qp.get('phase', 0.5))))
        disc = QPainterPath(); disc.addEllipse(QRectF(0, 0, w, h))
        cut = QPainterPath(); cut.addEllipse(QRectF(w * phase, 0, w, h))
        return disc.subtracted(cut)
    if name == 'sun':
        rays = int(qp.get('points', 12)); core = 0.55
        pp = QPainterPath(); pp.addEllipse(QRectF(cx - cx * core, cy - cy * core, w * core, h * core))
        spike = QPainterPath()
        for i in range(rays):
            a = i * 2 * math.pi / rays; a2 = a + math.pi / rays
            spike.moveTo(cx + cx * core * math.cos(a - math.pi / rays), cy + cy * core * math.sin(a - math.pi / rays))
            spike.lineTo(cx + cx * math.cos(a), cy + cy * math.sin(a))
            spike.lineTo(cx + cx * core * math.cos(a2), cy + cy * core * math.sin(a2))
            spike.closeSubpath()
        return pp.united(spike).simplified()
    if name == 'gear':
        teeth = int(qp.get('teeth', 9)); ro, ri, hub = 1.0, 0.72, 0.28
        pts = []
        for i in range(teeth):
            for frac, rr in ((0.0, ro), (0.28, ro), (0.5, ri), (0.78, ri)):
                a = (i + frac) * 2 * math.pi / teeth - math.pi / 2
                pts.append((cx + cx * rr * math.cos(a), cy + cy * rr * math.sin(a)))
        pp = _qs_poly(pts)
        hole = QPainterPath(); hole.addEllipse(QRectF(cx - cx * hub, cy - cy * hub, w * hub, h * hub))
        return pp.subtracted(hole)
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


def _flatten_painterpath(pp, step=0.02):
    """Sample a QPainterPath into a flat list of (x,y) points (for calligraphic outlining
    of curved node paths). Uses QPainterPath.pointAtPercent across the whole path length."""
    pts = []
    n = max(2, int(1.0 / step))
    for i in range(n + 1):
        q = pp.pointAtPercent(i / n)
        pts.append((q.x(), q.y()))
    return pts


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
        pp = quickshape_path(o['shape'], o['w'], o['h'], o.get('qp')).translated(o['x'], o['y'])
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


# ---------------------------------------------------------------- Roughen & Knife cores
def _lcg(seed):
    """A tiny deterministic PRNG (32-bit LCG, Numerical-Recipes constants) yielding floats
    in [-1, 1). Used so Roughen is reproducible: same points+params+seed → same output."""
    state = int(seed) & 0xFFFFFFFF
    while True:
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        yield (state / 0xFFFFFFFF) * 2.0 - 1.0


def roughen_points(points, amplitude=10.0, freq=12.0, smooth=0.0, seed=1):
    """PURE core of the Roughen effect. Take a flat polyline `points` (list of (x,y)),
    resample it to roughly `freq` jitter points per 100px of outline, then displace each
    resampled point by a seeded-random amount (±amplitude) along the local normal. Returns
    a new list of (x,y). `smooth` 0..1 blends each displaced point toward its neighbours'
    average, softening spikes (0 = spiky, 1 = smoothed). Deterministic for a fixed seed."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        return pts
    closed = (abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6)
    # cumulative arc length
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    if total <= 0:
        return pts
    # resample uniformly to n samples (at least len(pts); density from freq per 100px)
    n = max(len(pts), int(total / 100.0 * max(1.0, freq)) + 1)
    cum = [0.0]
    for s in seg:
        cum.append(cum[-1] + s)
    samples = []
    for k in range(n + (0 if closed else 1)):
        d = total * (k / n)
        # locate segment containing arc-distance d
        j = 0
        while j < len(seg) and cum[j + 1] < d:
            j += 1
        if j >= len(seg):
            samples.append(pts[-1]); continue
        t = (d - cum[j]) / (seg[j] or 1.0)
        ax, ay = pts[j]; bx, by = pts[j + 1]
        samples.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    rng = _lcg(seed)
    out = []
    m = len(samples)
    for i in range(m):
        px, py = samples[i]
        # local tangent (from neighbours) → normal
        a = samples[(i - 1) % m] if closed else samples[max(0, i - 1)]
        b = samples[(i + 1) % m] if closed else samples[min(m - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        tl = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / tl, tx / tl
        if (not closed) and (i == 0 or i == m - 1):
            disp = 0.0  # pin the endpoints of an open path
        else:
            disp = next(rng) * amplitude
        out.append((px + nx * disp, py + ny * disp))
    if closed and out:
        out[-1] = out[0] if m == len(samples) else out[-1]
    # smoothing pass: blend toward neighbour average
    s = max(0.0, min(1.0, smooth))
    if s > 0:
        src = list(out)
        for _ in range(1 + int(s * 3)):
            nxt = []
            for i in range(len(src)):
                a = src[(i - 1) % len(src)] if closed else src[max(0, i - 1)]
                b = src[(i + 1) % len(src)] if closed else src[min(len(src) - 1, i + 1)]
                avg = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                nxt.append((src[i][0] * (1 - s) + avg[0] * s, src[i][1] * (1 - s) + avg[1] * s))
            src = nxt
        out = src
    return out


def _points_to_nodes(points, closed, smooth=0.0):
    """Turn a flat polyline into a node list. smooth=0 → corner nodes; smooth>0 → give each
    node tangent handles (Catmull-Rom-ish) scaled by smooth, for a flowing path."""
    pts = [(float(x), float(y)) for x, y in points]
    if closed and len(pts) >= 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6:
        pts = pts[:-1]
    n = len(pts)
    nodes = []
    s = max(0.0, min(1.0, smooth))
    for i in range(n):
        x, y = pts[i]
        if s <= 0 or n < 3:
            nodes.append({'x': x, 'y': y, 'hin': [0.0, 0.0], 'hout': [0.0, 0.0], 'smooth': False})
            continue
        prev = pts[(i - 1) % n] if closed else pts[max(0, i - 1)]
        nxt = pts[(i + 1) % n] if closed else pts[min(n - 1, i + 1)]
        tx, ty = (nxt[0] - prev[0]) * s / 3.0, (nxt[1] - prev[1]) * s / 3.0
        nodes.append({'x': x, 'y': y, 'hin': [-tx, -ty], 'hout': [tx, ty], 'smooth': True})
    return nodes


def knife_split(object_path, cut_p1, cut_p2):
    """PURE core of the Knife tool. Split a filled QPainterPath by the infinite line through
    cut_p1→cut_p2 by intersecting it with two large half-plane polygons (one on each side of
    the line). Returns a list of QPainterPath pieces: 2 when the line crosses the shape, else
    [object_path] (a miss leaves the object whole). cut points are (x,y) tuples."""
    if object_path is None or object_path.isEmpty():
        return [object_path] if object_path is not None else []
    x1, y1 = cut_p1; x2, y2 = cut_p2
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return [object_path]
    br = object_path.boundingRect()
    diag = math.hypot(br.width(), br.height()) + 10.0
    L = diag * 4.0  # extend the cut line well past the object both ways
    ux, uy = dx, dy
    ul = math.hypot(ux, uy) or 1.0
    ux, uy = ux / ul, uy / ul
    nx, ny = -uy, ux  # left normal
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    a = (cx - ux * L, cy - uy * L)   # far-back point on the line
    b = (cx + ux * L, cy + uy * L)   # far-forward point on the line
    pieces = []
    for sgn in (1.0, -1.0):
        off = (nx * L * sgn, ny * L * sgn)
        half = QPainterPath()
        half.moveTo(a[0], a[1])
        half.lineTo(b[0], b[1])
        half.lineTo(b[0] + off[0], b[1] + off[1])
        half.lineTo(a[0] + off[0], a[1] + off[1])
        half.closeSubpath()
        piece = object_path.intersected(half).simplified()
        if not piece.isEmpty() and piece.boundingRect().width() > 0.01 and piece.boundingRect().height() > 0.01:
            pieces.append(piece)
    if len(pieces) < 2:
        return [object_path]  # cut missed (or barely grazed) the shape → leave it whole
    return pieces


# ---------------------------------------------------------------- node editing helpers
def _bezier_point(p0, p1, p2, p3, t):
    """A cubic Bézier evaluated at t (0..1); each arg is an (x, y) tuple."""
    u = 1 - t
    a = u * u * u; b = 3 * u * u * t; c = 3 * u * t * t; d = t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def split_segment(nodes, i, closed, t=0.5):
    """Return a NEW node list with an extra node inserted on the segment that leaves node i
    (toward node i+1), at parameter t. The curve shape is preserved: for a cubic segment we
    subdivide with de Casteljau, rewriting the two endpoints' adjacent handles; a straight
    segment just gets a corner node at the lerp point. Handles are stored node-relative."""
    n = len(nodes); j = (i + 1) % n
    a = nodes[i]; b = nodes[j]
    ax, ay = a['x'], a['y']; bx, by = b['x'], b['y']
    p0 = (ax, ay)
    p1 = (ax + a.get('hout', [0, 0])[0], ay + a.get('hout', [0, 0])[1])
    p2 = (bx + b.get('hin', [0, 0])[0], by + b.get('hin', [0, 0])[1])
    p3 = (bx, by)
    # de Casteljau subdivision at t
    q0 = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
    q1 = (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
    q2 = (p2[0] + (p3[0] - p2[0]) * t, p2[1] + (p3[1] - p2[1]) * t)
    r0 = (q0[0] + (q1[0] - q0[0]) * t, q0[1] + (q1[1] - q0[1]) * t)
    r1 = (q1[0] + (q2[0] - q1[0]) * t, q1[1] + (q2[1] - q1[1]) * t)
    s = (r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t)   # the new node point
    out = [dict(nd, hin=list(nd.get('hin', [0, 0])), hout=list(nd.get('hout', [0, 0]))) for nd in nodes]
    out[i]['hout'] = [q0[0] - ax, q0[1] - ay]
    out[j]['hin'] = [q2[0] - bx, q2[1] - by]
    mid = {'x': s[0], 'y': s[1], 'hin': [r0[0] - s[0], r0[1] - s[1]],
           'hout': [r1[0] - s[0], r1[1] - s[1]], 'smooth': True}
    out.insert(i + 1, mid)
    return out


def set_node_type(nd, kind):
    """Convert a node in place to 'cusp' (independent handles), 'smooth' (handles collinear,
    lengths kept) or 'symmetric' (handles mirrored). Sets the 'smooth' flag to match."""
    hin = list(nd.get('hin', [0, 0])); hout = list(nd.get('hout', [0, 0]))
    if kind == 'cusp':
        nd['smooth'] = False
        return nd
    if kind == 'symmetric':
        # mirror: hin = -hout (prefer the longer handle as the master, else hin)
        if hout == [0, 0] and hin != [0, 0]:
            nd['hout'] = [-hin[0], -hin[1]]
        else:
            nd['hin'] = [-hout[0], -hout[1]]
        nd['smooth'] = True
        return nd
    # smooth: keep both lengths but make them collinear along a shared axis
    din = math.hypot(*hin); dout = math.hypot(*hout)
    if din > 1e-6 and dout > 1e-6:
        # average the two (opposite) directions, then re-project each handle onto it
        ax, ay = -hin[0] / din, -hin[1] / din; bx, by = hout[0] / dout, hout[1] / dout
        ux, uy = ax + bx, ay + by
        m = math.hypot(ux, uy)
        if m > 1e-6:
            ux, uy = ux / m, uy / m
            nd['hout'] = [ux * dout, uy * dout]; nd['hin'] = [-ux * din, -uy * din]
    elif din > 1e-6:
        nd['hout'] = [-hin[0], -hin[1]]
    elif dout > 1e-6:
        nd['hin'] = [-hout[0], -hout[1]]
    nd['smooth'] = True
    return nd


# ---------------------------------------------------------------- blend (morph) helpers
def _resample_nodes(nodes, count, closed):
    """Return `count` nodes sampled evenly (by Bézier parameter, per segment) along a node
    path. Resampled nodes are smooth with handles derived from the local tangent so the
    morph stays well-behaved; used to give two paths a common node count before blending."""
    n = len(nodes)
    if n == 0:
        return []
    if n == 1:
        return [dict(x=nodes[0]['x'], y=nodes[0]['y'], hin=[0, 0], hout=[0, 0], smooth=False) for _ in range(count)]
    segs = n if closed else n - 1

    def seg_pts(i):
        a = nodes[i]; b = nodes[(i + 1) % n]
        return ((a['x'], a['y']), (a['x'] + a.get('hout', [0, 0])[0], a['y'] + a.get('hout', [0, 0])[1]),
                (b['x'] + b.get('hin', [0, 0])[0], b['y'] + b.get('hin', [0, 0])[1]), (b['x'], b['y']))
    total = segs if closed else segs
    out = []
    span = count if closed else count - 1
    for k in range(count):
        g = (k / span) * segs if span else 0.0
        if g >= segs: g = segs - 1e-9
        si = int(g); lt = g - si
        p0, p1, p2, p3 = seg_pts(si)
        pt = _bezier_point(p0, p1, p2, p3, lt)
        # tangent via a small finite difference along the curve, scaled to a modest handle
        t2 = min(1.0, lt + 0.01); t1 = max(0.0, lt - 0.01)
        q2 = _bezier_point(p0, p1, p2, p3, t2); q1 = _bezier_point(p0, p1, p2, p3, t1)
        tx, ty = (q2[0] - q1[0]), (q2[1] - q1[1])
        m = math.hypot(tx, ty) or 1.0
        hl = (math.hypot(p3[0] - p0[0], p3[1] - p0[1]) or 1.0) / 3.0 / max(1, segs) * segs
        tx, ty = tx / m * hl, ty / m * hl
        out.append({'x': pt[0], 'y': pt[1], 'hin': [-tx, -ty], 'hout': [tx, ty], 'smooth': True})
    return out


def blend_paths(a_nodes, b_nodes, t, closed=False):
    """Interpolate two node lists at parameter t (0=a, 1=b). If the counts differ, resample
    the SHORTER list up to the longer count first, so both have matching node indices. Pure:
    returns a new node list."""
    na, nb = len(a_nodes), len(b_nodes)
    if na == 0 or nb == 0:
        return [dict(x=nd['x'], y=nd['y'], hin=list(nd.get('hin', [0, 0])),
                     hout=list(nd.get('hout', [0, 0])), smooth=nd.get('smooth', False))
                for nd in (b_nodes if t >= 0.5 else a_nodes)]
    if na != nb:
        m = max(na, nb)
        if na < m: a_nodes = _resample_nodes(a_nodes, m, closed)
        if nb < m: b_nodes = _resample_nodes(b_nodes, m, closed)
    out = []
    for p, q in zip(a_nodes, b_nodes):
        ph = p.get('hin', [0, 0]); qh = q.get('hin', [0, 0])
        po = p.get('hout', [0, 0]); qo = q.get('hout', [0, 0])
        out.append({'x': p['x'] + (q['x'] - p['x']) * t, 'y': p['y'] + (q['y'] - p['y']) * t,
                    'hin': [ph[0] + (qh[0] - ph[0]) * t, ph[1] + (qh[1] - ph[1]) * t],
                    'hout': [po[0] + (qo[0] - po[0]) * t, po[1] + (qo[1] - po[1]) * t],
                    'smooth': p.get('smooth', False) or q.get('smooth', False)})
    return out


def _lerp_color(ca, cb, t):
    """Lerp two colour strings (or None) in RGB; returns a '#rrggbb' string, or None if both
    are None (so a no-fill→no-fill blend stays unfilled)."""
    if ca is None and cb is None:
        return None
    qa = QColor(ca) if ca else QColor(cb); qb = QColor(cb) if cb else QColor(ca)
    r = round(qa.red() + (qb.red() - qa.red()) * t)
    g = round(qa.green() + (qb.green() - qa.green()) * t)
    b = round(qa.blue() + (qb.blue() - qa.blue()) * t)
    return QColor(r, g, b).name()


def blend_objects(a, b, steps):
    """Build `steps` intermediate node objects morphing object a → object b (geometry +
    fill + stroke + width). a and b must already be 'nodes' objects. Pure: returns a list
    of new obj dicts (the intermediates only, in a→b order)."""
    an, bn = a.get('nodes') or [], b.get('nodes') or []
    closed = bool(a.get('closed')) or bool(b.get('closed'))
    out = []
    for i in range(1, steps + 1):
        t = i / (steps + 1)
        nd = blend_paths(an, bn, t, closed)
        o = dict(type='nodes', nodes=nd, closed=closed,
                 fill=_lerp_color(a.get('fill'), b.get('fill'), t),
                 stroke=_lerp_color(a.get('stroke'), b.get('stroke'), t),
                 sw=a.get('sw', 2) + (b.get('sw', 2) - a.get('sw', 2)) * t)
        out.append(o)
    return out


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


# ---------------------------------------------------------------- texture / pattern fills
_TEX_CACHE = {}

def texfill_image(o):
    """Decode a texture/pattern fill's embedded data-URI (o['texfill']['src']) to a QImage,
    cached by src (like obj_image) so the object dict stays plain and serialisable."""
    tf = o.get('texfill') or {}
    src = tf.get('src', '')
    cached = _TEX_CACHE.get(src)
    if isinstance(cached, QImage):
        return cached
    qi = QImage()
    try:
        if src.startswith('data:'):
            import base64
            _, _, b64 = src.partition(',')
            qi.loadFromData(base64.b64decode(b64))
        elif src:
            qi.load(src)
    except Exception:
        qi = QImage()
    if src:
        _TEX_CACHE[src] = qi
    return qi


def texfill_brush(o):
    """A QBrush that paints an object's texture/pattern fill. mode='tile' tiles the image
    at its natural size; mode='stretch' scales one copy to fill the object's bounding box.
    Returns None if there is no (decodable) texture."""
    tf = o.get('texfill')
    if not tf:
        return None
    img = texfill_image(o)
    if img.isNull():
        return None
    if tf.get('mode', 'tile') == 'stretch':
        r = obj_rect(o); w = max(1, int(round(r.width()))); h = max(1, int(round(r.height())))
        scaled = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        br = QBrush(scaled)
        from PySide6.QtGui import QTransform
        br.setTransform(QTransform().translate(r.x(), r.y()))
        return br
    return QBrush(img)


def _texfill_scale(o):
    """The width/height a stretched texture copy is drawn at, for SVG <pattern> sizing."""
    r = obj_rect(o)
    return max(1.0, r.width()), max(1.0, r.height())


# ---------------------------------------------------------------- Object effects
def obj_silhouette(o):
    """(path in local 0-based coords, world x, world y, w, h) for drop-shadow/glow."""
    t = o['type']; pp = QPainterPath()
    if t == 'rect': pp.addRect(QRectF(0, 0, o['w'], o['h']))
    elif t == 'ellipse': pp.addEllipse(QRectF(0, 0, o['w'], o['h']))
    elif t == 'image': pp.addRect(QRectF(0, 0, o['w'], o['h']))
    elif t == 'quick': pp = quickshape_path(o['shape'], o['w'], o['h'], o.get('qp'))
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

# ---------------------------------------------------------------- Pressure Studio (profiles)
# A profile shapes a brush stroke's width along its length. Presets are stored by name;
# 'Custom' carries control points [(pos0..1, scale0..1), …] defining a width-multiplier curve.
PROFILE_PRESETS = {
    'Constant':    [(0.0, 1.0), (1.0, 1.0)],
    'Taper End':   [(0.0, 1.0), (1.0, 0.0)],
    'Taper Start': [(0.0, 0.0), (1.0, 1.0)],
    'Taper Both':  [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)],
    'Bulge':       [(0.0, 0.6), (0.5, 1.0), (1.0, 0.6)],
}
PROFILE_NAMES = ['Constant', 'Taper End', 'Taper Start', 'Taper Both', 'Bulge', 'Custom']

def profile_points(profile):
    """The control-point list [(pos,scale),…] for a profile descriptor (a preset name str,
    or a dict {'name':…, 'pts':[…]} where a 'Custom' name uses its own pts)."""
    if not profile:
        return PROFILE_PRESETS['Constant']
    if isinstance(profile, str):
        return PROFILE_PRESETS.get(profile, PROFILE_PRESETS['Constant'])
    name = profile.get('name', 'Constant')
    if name == 'Custom':
        cp = profile.get('pts') or []
        return cp if len(cp) >= 2 else PROFILE_PRESETS['Constant']
    return PROFILE_PRESETS.get(name, PROFILE_PRESETS['Constant'])

def profile_value(cp, t):
    """Linear-interpolate the multiplier curve `cp` (sorted by pos) at position t in 0..1."""
    cp = sorted(cp, key=lambda q: q[0])
    if t <= cp[0][0]: return cp[0][1]
    if t >= cp[-1][0]: return cp[-1][1]
    for i in range(len(cp) - 1):
        (p0, s0), (p1, s1) = cp[i], cp[i + 1]
        if p0 <= t <= p1:
            f = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            return s0 + (s1 - s0) * f
    return cp[-1][1]

def profile_widths(base_widths, profile):
    """Multiply each per-point width by the profile curve's value at that point's normalised
    arc-length position along the stroke. Returns a new width list (same length)."""
    n = len(base_widths)
    if n == 0:
        return []
    cp = profile_points(profile)
    if n == 1:
        return [base_widths[0] * profile_value(cp, 0.0)]
    return [base_widths[i] * profile_value(cp, i / (n - 1)) for i in range(n)]


# ---------------------------------------------------------------- calligraphic strokes
def calligraphic_outline(path_pts, sw, nib_angle):
    """A filled QPainterPath ribbon emulating a flat calligraphy nib held at `nib_angle`
    degrees. Walk the polyline; at each point offset by ±half-width perpendicular to the
    tangent, where the half-width scales with |sin(tangent − nib)| (thin when the path runs
    along the nib, thick across it). Builds one closed outline (forward edge + reverse edge).
    A small floor keeps the thin parts hairline-visible rather than vanishing."""
    pts = [(float(x), float(y)) for x, y in (path_pts or [])]
    n = len(pts)
    pp = QPainterPath()
    if n < 2:
        return pp
    nib = math.radians(nib_angle)
    half = max(0.5, sw) / 2.0
    floor = 0.12   # fraction of half-width kept at the thinnest, so the nib never disappears
    def tangent(i):
        if i == 0: a, b = pts[0], pts[1]
        elif i == n - 1: a, b = pts[n - 2], pts[n - 1]
        else: a, b = pts[i - 1], pts[i + 1]
        return math.atan2(b[1] - a[1], b[0] - a[0])
    left, right = [], []
    for i in range(n):
        x, y = pts[i]; tg = tangent(i)
        w = half * (floor + (1 - floor) * abs(math.sin(tg - nib)))
        nx, ny = -math.sin(tg), math.cos(tg)   # unit normal to the tangent
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    poly = left + right[::-1]
    pp.addPolygon(QPolygonF([QPointF(px, py) for px, py in poly])); pp.closeSubpath()
    return pp


def draw_brush(p, o):
    """A variable-width ink ribbon from a brush object's points + per-point widths
    (the 'pressure' is faked from pointer speed when drawn). Each segment quad and each
    round join is filled separately so overlaps stay solid (a single winding-fill path
    would leave lattice holes where sub-paths cancel). A pressure profile (o['profile'])
    reshapes the stored widths live when set."""
    pts = o.get('pts') or []; ws = o.get('widths') or []
    n = len(pts)
    if n == 0:
        return
    prof = o.get('profile')
    if prof and ws:
        ws = profile_widths(ws, prof)
    col = QColor(o.get('stroke') or o.get('fill') or '#1f2a30')
    p.setPen(Qt.NoPen); p.setBrush(col)
    def wat(i): return max(1.0, ws[i] if i < len(ws) else (ws[-1] if ws else 6.0))
    for i in range(n - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        w1, w2 = wat(i), wat(i + 1)
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        p.drawPolygon(QPolygonF([QPointF(x1 + nx * w1 / 2, y1 + ny * w1 / 2),
                                 QPointF(x2 + nx * w2 / 2, y2 + ny * w2 / 2),
                                 QPointF(x2 - nx * w2 / 2, y2 - ny * w2 / 2),
                                 QPointF(x1 - nx * w1 / 2, y1 - ny * w1 / 2)]))
    for i in range(n):
        x, y = pts[i]; r = wat(i) / 2; p.drawEllipse(QPointF(x, y), r, r)


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


def _obj_layer_img(o, pad=0):
    """Render an object's body (no behind/over effects) to its own transparent QImage, at
    the object's world bounding-box size + `pad` px of transparent margin all round. The
    object sits at (pad - ox, pad - oy) so its world-space geometry lands correctly. Returns
    (img, ox, oy) where (ox,oy) is the world top-left of the object's bounding box. Ported
    from PAGEcreator's _obj_layer, adapted to DRAWmaster's world-coordinate objects."""
    r = obj_rect(o)
    ox, oy = r.x(), r.y()
    w = max(1, int(math.ceil(r.width()))); h = max(1, int(math.ceil(r.height())))
    W, H = w + 2 * pad, h + 2 * pad
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied); img.fill(Qt.transparent)
    lp = QPainter(img); lp.setRenderHint(QPainter.Antialiasing); lp.setRenderHint(QPainter.SmoothPixmapTransform)
    lp.translate(pad - ox, pad - oy)
    # Draw the body WITHOUT its own effects (shadow/glow/reflect/feather/bevel/agrad) — just the object.
    o2 = {k: v for k, v in o.items()
          if k not in ('shadow', 'glow', 'reflect', 'feather', 'bevel', 'agrad', 'rot', 'opacity', 'blend')}
    _paint_object_body(lp, o2)
    lp.end()
    return img, ox, oy, w, h


# ---------------------------------------------------------------- Perspective & Envelope
# Non-destructive render-time warps (DrawPlus Perspective & Envelope). Both work on ANY
# object by warping its RENDERED pixels (via _obj_layer_img), keeping the underlying
# geometry intact. State lives in o['perspective'] (4 corner offsets) and o['envelope']
# (a grid of control-point offsets). Reset = pop the key.

def _warp_pts(bbox, pts):
    """Resolve a list of (fx, fy) control points to absolute world coords inside bbox.
    Each component is an offset in 0..1 fractions of the box (so 0,0 = TL; 1,1 = BR),
    plus the point's stored offset. Here pts are already absolute fractions — we just
    map fraction → world. Used by both warps so presets are resolution-independent."""
    x0, y0, w, h = bbox.x(), bbox.y(), bbox.width() or 1, bbox.height() or 1
    return [QPointF(x0 + fx * w, y0 + fy * h) for fx, fy in pts]


def perspective_transform(bbox, corners):
    """A QTransform that maps bbox's TL/TR/BR/BL to the four `corners` (each a fractional
    (fx, fy) offset of the box, where the undistorted box is [(0,0),(1,0),(1,1),(0,1)]).
    Returns identity if the quad is degenerate. corners order = TL, TR, BR, BL."""
    src = QPolygonF([QPointF(bbox.left(), bbox.top()), QPointF(bbox.right(), bbox.top()),
                     QPointF(bbox.right(), bbox.bottom()), QPointF(bbox.left(), bbox.bottom())])
    dst = QPolygonF(_warp_pts(bbox, corners))
    t = QTransform()
    if not QTransform.quadToQuad(src, dst, t):
        return QTransform()
    return t


def default_perspective():
    """The identity perspective: the 4 corners sit exactly on the box (TL,TR,BR,BL)."""
    return [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


def default_envelope(cols=2, rows=2):
    """An identity mesh of (cols+1)x(rows+1) control points, each the fractional position
    of a grid vertex over the box (so a flat mesh reproduces the box exactly)."""
    pts = []
    for j in range(rows + 1):
        for i in range(cols + 1):
            pts.append([i / cols, j / rows])
    return {'cols': cols, 'rows': rows, 'pts': pts}


ENVELOPE_PRESETS = ('reset', 'arch', 'bulge', 'pinch', 'wave')


def envelope_preset(name, cols=2, rows=2):
    """Build a preset control mesh. Returns an envelope dict (or None for reset)."""
    if name == 'reset':
        return None
    env = default_envelope(cols, rows)
    pts = env['pts']
    def idx(i, j): return j * (cols + 1) + i
    for j in range(rows + 1):
        for i in range(cols + 1):
            fx, fy = i / cols, j / rows
            if name == 'arch':
                # lift the top edge into an arch (centre rises), bottom flat
                pts[idx(i, j)][1] = fy - (1 - fy) * 0.35 * math.sin(math.pi * fx)
            elif name in ('bulge', 'pinch'):
                # barrel (bulge) / pincushion (pinch): push each vertex radially out from /
                # in toward the centre, strongest mid-edge, zero at the 4 corners.
                dx, dy = fx - 0.5, fy - 0.5
                rad = math.hypot(dx, dy)
                corner = math.hypot(0.5, 0.5)
                falloff = math.sin(math.pi * (rad / corner))   # 0 at centre & corners, 1 mid-edge
                k = (0.16 if name == 'bulge' else -0.28) * falloff
                pts[idx(i, j)][0] = fx + dx * 2 * k
                pts[idx(i, j)][1] = fy + dy * 2 * k
            elif name == 'wave':
                pts[idx(i, j)][1] = fy + 0.18 * math.sin(2 * math.pi * fx)
    return env


def envelope_cell_quad(env, bbox, i, j):
    """World-space destination quad (QPolygonF, TL,TR,BR,BL) for mesh cell (i, j), from
    the envelope's control points mapped through bbox. A flat mesh reproduces the cell's
    own sub-rectangle of the box exactly."""
    cols, rows = env.get('cols', 2), env.get('rows', 2)
    pts = env['pts']
    def cp(ii, jj):
        fx, fy = pts[jj * (cols + 1) + ii]
        return QPointF(bbox.x() + fx * (bbox.width() or 1), bbox.y() + fy * (bbox.height() or 1))
    return QPolygonF([cp(i, j), cp(i + 1, j), cp(i + 1, j + 1), cp(i, j + 1)])


def draw_object_warped(p, o, selected=False, skip_text=False):
    """Blit the object's rendered pixels through its perspective and/or envelope warp.
    Returns True if a warp was applied (so the caller skips the normal body draw)."""
    persp = o.get('perspective'); env = o.get('envelope')
    if not persp and not env:
        return False
    # Render the object's crisp pixels to an offscreen layer (supersampled a little for
    # smoother warped edges), keyed to its world bounding box.
    try:
        sx = math.hypot(p.worldTransform().m11(), p.worldTransform().m12()) or 1
    except Exception:
        sx = 1
    ss = max(1.0, min(sx, 4))                      # supersample factor
    r = obj_rect(o)
    ox, oy = r.x(), r.y(); w = r.width() or 1; h = r.height() or 1
    W = max(1, int(math.ceil(w * ss))); H = max(1, int(math.ceil(h * ss)))
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied); img.fill(Qt.transparent)
    lp = QPainter(img); lp.setRenderHint(QPainter.Antialiasing); lp.setRenderHint(QPainter.SmoothPixmapTransform)
    lp.scale(W / w, H / h); lp.translate(-ox, -oy)
    o2 = {k: v for k, v in o.items() if k not in ('perspective', 'envelope', 'rot', 'opacity', 'blend')}
    _paint_object_body(lp, o2, False, skip_text)
    lp.end()
    # unit box over the source image (0..1 → pixel coords)
    def src_quad(fx0, fy0, fx1, fy1):
        return QPolygonF([QPointF(fx0 * W, fy0 * H), QPointF(fx1 * W, fy0 * H),
                          QPointF(fx1 * W, fy1 * H), QPointF(fx0 * W, fy1 * H)])
    p.save(); p.setRenderHint(QPainter.SmoothPixmapTransform)
    if env:
        cols, rows = env.get('cols', 2), env.get('rows', 2)
        pt = perspective_transform(r, persp) if persp else None
        for j in range(rows):
            for i in range(cols):
                sq = src_quad(i / cols, j / rows, (i + 1) / cols, (j + 1) / rows)
                dq = envelope_cell_quad(env, r, i, j)
                if pt is not None:
                    dq = QPolygonF([pt.map(q) for q in dq])
                t = QTransform()
                if QTransform.quadToQuad(sq, dq, t):
                    # draw ONLY this cell's pixels: clip to its source sub-rect (grown a
                    # hair so adjacent cells overlap and leave no seam), under the transform.
                    sx0, sy0 = i / cols * W, j / rows * H
                    sx1, sy1 = (i + 1) / cols * W, (j + 1) / rows * H
                    p.save(); p.setTransform(t, True)
                    p.setClipRect(QRectF(sx0 - 0.5, sy0 - 0.5, (sx1 - sx0) + 1, (sy1 - sy0) + 1))
                    p.drawImage(0, 0, img); p.restore()
    else:
        dq = QPolygonF(_warp_pts(r, persp))
        sq = src_quad(0, 0, 1, 1)
        t = QTransform()
        if QTransform.quadToQuad(sq, dq, t):
            p.setTransform(t, True); p.drawImage(0, 0, img)
    p.restore()
    return True


def _blur_alpha_img(img, radius):
    """A copy of img whose ALPHA channel is box-blurred by radius (colour kept). Uses the
    module _box_blur — no new deps. Ported from PAGEcreator."""
    import numpy as np
    if radius <= 0: return img
    src = img.convertToFormat(QImage.Format_ARGB32)
    W, H = src.width(), src.height()
    arr = np.frombuffer(memoryview(src.constBits()), np.uint8).reshape((H, W, 4)).copy()
    a = arr[:, :, 3].astype(np.float32)
    a = _box_blur(a, int(radius))
    arr[:, :, 3] = np.clip(a, 0, 255).astype(np.uint8)
    return QImage(arr.tobytes(), W, H, QImage.Format_ARGB32).copy()


def draw_object_reflect(p, o):
    """A mirrored copy of the object fading downward below it (DrawPlus Reflection).
    Painted BEHIND the object so it sits under the real object's bottom edge. Ported from
    PAGEcreator, adapted to world coordinates."""
    rf = o.get('reflect')
    if not rf: return
    img, ox, oy, w, h = _obj_layer_img(o)
    gap = float(rf.get('gap', 4)); op = max(0, min(100, rf.get('opacity', 50))) / 100.0
    fall = max(0.01, min(1.0, rf.get('falloff', 60) / 100.0))   # fraction of height the fade spans
    ref = QImage(img.size(), QImage.Format_ARGB32_Premultiplied); ref.fill(Qt.transparent)
    rp = QPainter(ref); rp.drawImage(0, 0, img.mirrored(False, True))   # vertical flip
    mg = QLinearGradient(0, 0, 0, h)                                    # top = object's bottom edge
    mg.setColorAt(0.0, QColor(0, 0, 0, int(round(op * 255))))
    mg.setColorAt(fall, QColor(0, 0, 0, 0))
    if fall < 1.0: mg.setColorAt(1.0, QColor(0, 0, 0, 0))
    rp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    rp.fillRect(QRectF(0, 0, img.width(), img.height()), QBrush(mg)); rp.end()
    p.save(); p.drawImage(QRectF(ox, oy + h + gap, w, h), ref); p.restore()


def draw_object_fx_over(p, o):
    """Feather and bevel/emboss — drawn as an OVERLAY after the object body, because they
    modify the object's own pixels/edges rather than sitting behind it. Ported from
    PAGEcreator, adapted to world coordinates."""
    fe = o.get('feather'); bv = o.get('bevel')
    if not fe and not bv: return
    sil, sox, soy, sw, sh = obj_silhouette(o)   # local-0-based path + world top-left
    if fe and fe.get('radius', 0) > 0:
        rad = max(1, int(round(fe.get('radius', 6)))); pad = rad + 2
        img, ox, oy, w, h = _obj_layer_img(o, pad=pad)
        soft = _blur_alpha_img(img, rad)
        p.save()
        if sil is not None:
            # knock out the crisp original within the silhouette so only the soft copy shows
            p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 255))
            p.save(); p.translate(sox, soy); p.drawPath(sil); p.restore()
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawImage(QRectF(ox - pad, oy - pad, w + 2 * pad, h + 2 * pad), soft)
        p.restore()
    if bv:
        depth = max(1.0, float(bv.get('depth', 4))); soft = max(0.0, float(bv.get('soft', 2)))
        light = max(0, min(100, bv.get('light', 70))) / 100.0; ang = math.radians(bv.get('dir', 135))
        dx, dy = math.cos(ang), -math.sin(ang)   # screen y is down; dir measured maths-style
        if sil is None:
            r = obj_rect(o); sil = QPainterPath(); sil.addRect(QRectF(0, 0, r.width(), r.height()))
            sox, soy = r.x(), r.y()
        p.save(); p.translate(sox, soy); p.setClipPath(sil)
        pen_w = depth + soft
        hi = QColor(255, 255, 255, int(round(light * 170)))
        lo = QColor(0, 0, 0, int(round(light * 150)))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(hi, pen_w)); p.translate(dx * depth, dy * depth); p.drawPath(sil)
        p.translate(-2 * dx * depth, -2 * dy * depth)
        p.setPen(QPen(lo, pen_w)); p.drawPath(sil)
        p.restore()


def text_font(o):
    """The QFont for a text object (family + pixel size, optional bold/italic)."""
    f = QFont(o.get('family', 'Noto Sans')); f.setPixelSize(max(1, int(o.get('size', 48))))
    if o.get('bold'): f.setBold(True)
    if o.get('italic'): f.setItalic(True)
    return f

def text_size(o):
    """(width, height) of a text object's drawn box, measured from its font."""
    fm = QFontMetricsF(text_font(o))
    br = fm.boundingRect(o.get('text', ''))
    return max(1.0, br.width()), max(1.0, fm.height())


# ---------------------------------------------------------------- text on a path
def textpath_path(o):
    """A QPainterPath along which a 'text-on-path' object's glyphs flow — built from the
    polyline of points stored in o['pathpts'] (canvas coords). Returns None if the text
    object is not attached to a path."""
    pts = o.get('pathpts')
    if not pts or len(pts) < 2:
        return None
    pp = QPainterPath(); pp.moveTo(pts[0][0], pts[0][1])
    for x, y in pts[1:]:
        pp.lineTo(x, y)
    return pp


def draw_text_on_path(p, o):
    """Lay each glyph of a text-on-path object along its stored polyline, rotating each
    character to the local tangent. Honours fill/stroke like ordinary artistic text."""
    pp = textpath_path(o)
    if pp is None:
        return
    s = o.get('text', '')
    if not s:
        return
    font = text_font(o); fm = QFontMetricsF(font)
    total = pp.length() or 1.0
    adv = 0.0
    p.save()
    if o.get('stroke'):
        p.setPen(QPen(QColor(o['stroke']), o.get('sw', 2)))
    else:
        p.setPen(Qt.NoPen)
    p.setBrush(QColor(o['fill']) if o.get('fill') else Qt.NoBrush)
    for ch in s:
        cw = fm.horizontalAdvance(ch)
        at = adv + cw / 2.0
        if at > total:
            break
        pct = pp.percentAtLength(at)
        pt = pp.pointAtPercent(pct)
        ang = pp.angleAtPercent(pct)   # degrees, counter-clockwise
        glyph = QPainterPath()
        glyph.addText(-cw / 2.0, fm.ascent() - fm.height() / 2.0, font, ch)
        p.save()
        p.translate(pt.x(), pt.y()); p.rotate(-ang)
        p.drawPath(glyph)
        p.restore()
        adv += cw
    p.restore()


# ---------------------------------------------------------------- dimension lines & connectors
def _dim_label(o):
    """The measured length label for a dimension object, in the drawing's units."""
    pts = o.get('pts') or []
    if len(pts) < 2:
        return ''
    dx = pts[1][0] - pts[0][0]; dy = pts[1][1] - pts[0][1]
    dist_px = math.hypot(dx, dy)
    unit = o.get('unit', 'px')
    val = dist_px * UNIT_PER_PX.get(unit, 1.0)
    txt = f'{val:.1f}'.rstrip('0').rstrip('.')
    return f'{txt} {unit}'


def draw_dimension(p, o):
    """A dimension line: the measured segment, short end ticks perpendicular to it, and
    an auto length label centred above the line."""
    pts = o.get('pts') or []
    if len(pts) < 2:
        return
    (x1, y1), (x2, y2) = pts[0], pts[1]
    col = QColor(o.get('stroke') or '#1f2a30')
    sw = o.get('sw', 2)
    p.save()
    pen = QPen(col, sw); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    ang = math.atan2(y2 - y1, x2 - x1)
    tick = max(6.0, sw * 4.0)
    nx, ny = -math.sin(ang) * tick, math.cos(ang) * tick
    for (tx, ty) in ((x1, y1), (x2, y2)):
        p.drawLine(QPointF(tx - nx, ty - ny), QPointF(tx + nx, ty + ny))
    label = _dim_label(o)
    if label:
        font = text_font(o) if o.get('size') else QFont('Noto Sans')
        if not o.get('size'):
            font.setPixelSize(max(11, int(sw * 7)))
        fm = QFontMetricsF(font)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        lw = fm.horizontalAdvance(label)
        glyph = QPainterPath(); glyph.addText(-lw / 2, -fm.descent() - tick, font, label)
        p.save(); p.translate(mx, my)
        a = math.degrees(ang)
        if a > 90 or a < -90: a += 180   # keep the label upright
        p.rotate(a)
        p.setPen(Qt.NoPen); p.setBrush(col); p.drawPath(glyph); p.restore()
    p.restore()


def conn_endpoints(o, objs):
    """Resolve a connector's two endpoints to canvas coords. Each end is either a free
    point {pt:[x,y]} or an anchor to another object {anchor: gid} whose centre is used."""
    def resolve(end):
        if isinstance(end, dict) and end.get('anchor') is not None:
            tgt = next((x for x in objs if x.get('cid') == end['anchor']), None)
            if tgt is not None:
                cx, cy = obj_center(tgt)
                return (cx, cy)
        if isinstance(end, dict):
            return tuple(end.get('pt', (0, 0)))
        return tuple(end)
    return resolve(o.get('a')), resolve(o.get('b'))


def draw_connector(p, o, objs=None):
    """A connector line between two endpoints (free points or object anchors). Drawn as a
    simple straight line with an arrowhead at the end, in the object's stroke colour."""
    objs = objs if objs is not None else []
    a, b = conn_endpoints(o, objs)
    col = QColor(o.get('stroke') or '#1f2a30')
    sw = o.get('sw', 2)
    p.save()
    pen = QPen(col, sw); pen.setCapStyle(Qt.RoundCap)
    if o.get('dash', 'solid') != 'solid':
        apply_dash(pen, o.get('dash'))
    p.setPen(pen); p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(*a), QPointF(*b))
    if o.get('arrow', 'end') != 'none':
        size = max(8.0, sw * 3.0); p.setPen(Qt.NoPen); p.setBrush(col)
        which = o.get('arrow', 'end')
        if which in ('end', 'both'): p.drawPath(_arrow_head_path(b, a, size))
        if which in ('start', 'both'): p.drawPath(_arrow_head_path(a, b, size))
    p.restore()


def obj_rect(o):
    t = o['type']
    if t in ('rect', 'ellipse', 'quick', 'image'):
        return QRectF(o['x'], o['y'], o['w'], o['h']).normalized()
    if t == 'text':
        if o.get('pathpts'):
            pp = textpath_path(o)
            if pp is not None:
                br = pp.boundingRect(); m = max(2.0, o.get('size', 48))
                return QRectF(br.x() - m, br.y() - m, (br.width() or 1) + 2 * m, (br.height() or 1) + 2 * m)
        tw, th = text_size(o)
        return QRectF(o['x'], o['y'], tw, th)
    if t == 'nodes':
        br = node_painter_path(o).boundingRect()
        return QRectF(br.x(), br.y(), br.width() or 1, br.height() or 1)
    if t == 'conn':
        a, b = conn_endpoints(o, _PAINT_OBJS)
        xs = [a[0], b[0]]; ys = [a[1], b[1]]
        return QRectF(min(xs), min(ys), abs(xs[1] - xs[0]) or 1, abs(ys[1] - ys[0]) or 1)
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


def obj_fx_bounds(o):
    """obj_bounds expanded to include reflection (below) and feather (all round) so the
    visual extent isn't clipped (e.g. when exporting a selection). Conservative; ignores
    rotation of the reflection offset (reflection is unrotated-frame-relative here)."""
    r = obj_bounds(o)
    rf = o.get('reflect'); fe = o.get('feather')
    if rf:
        gap = float(rf.get('gap', 4))
        r = r.united(QRectF(r.x(), r.y() + gap, r.width(), 2 * r.height() + gap))
    if fe and fe.get('radius', 0) > 0:
        m = int(fe['radius']) + 2
        r = r.adjusted(-m, -m, m, m)
    return r


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


def grad_stops(g):
    """Normalised colour stops for a gradient dict → [(pos 0..1, '#rrggbb'), …].
    Prefers g['stops'] (multi-stop); falls back to the old 2-colour c1/c2 pair so
    drawings saved before multi-stop gradients still render. Ported from PAGEcreator."""
    ss = g.get('stops')
    if ss:
        out = [(max(0.0, min(1.0, float(s.get('pos', 0)))), s.get('color', '#000000')) for s in ss]
        out = sorted(out, key=lambda s: s[0])
        if out:
            return out
    return [(0.0, g.get('c1', '#ffffff')), (1.0, g.get('c2', '#000000'))]


def fill_brush(o):
    """The fill brush for an object — a texture/pattern, a gradient (grad dict) or a flat
    colour. A texture fill wins over a gradient, which wins over a flat colour. Gradients
    and textures are mapped across the object's bounding box, so they render the same on
    screen, in PNG and (via the SVG defs) in a browser. Mirrors PAGEdesigner. The gradient
    supports any number of stops (grad['stops']=[{pos,color}]) with a 2-colour c1/c2 fallback."""
    tb = texfill_brush(o)
    if tb is not None:
        return tb
    g = o.get('grad')
    if g:
        r = obj_rect(o); w = r.width() or 1; h = r.height() or 1; stops = grad_stops(g)
        if g.get('type') == 'radial':
            rg = QRadialGradient(r.x() + w / 2, r.y() + h / 2, max(w, h) / 2)
            for pos, col in stops: rg.setColorAt(pos, QColor(col))
            return QBrush(rg)
        ang = math.radians(g.get('angle', 90)); cx, cy = r.x() + w / 2, r.y() + h / 2
        dx, dy = math.cos(ang), math.sin(ang)
        lg = QLinearGradient(cx - dx * w / 2, cy - dy * h / 2, cx + dx * w / 2, cy + dy * h / 2)
        for pos, col in stops: lg.setColorAt(pos, QColor(col))
        return QBrush(lg)
    return QBrush(QColor(o['fill'])) if o.get('fill') else QBrush(Qt.NoBrush)


def svg_grad_def(g, gid):
    """A <linearGradient>/<radialGradient> def (objectBoundingBox) for the given grad dict —
    one <stop> per colour stop (multi-stop, with a 2-colour c1/c2 fallback)."""
    stops = ''.join(f'<stop offset="{pos * 100:.1f}%" stop-color="{col}"/>'
                    for pos, col in grad_stops(g))
    if g.get('type') == 'radial':
        return f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{stops}</radialGradient>'
    rad = math.radians(g.get('angle', 90))
    x1, y1 = 50 - 50 * math.cos(rad), 50 - 50 * math.sin(rad)
    x2, y2 = 50 + 50 * math.cos(rad), 50 + 50 * math.sin(rad)
    return (f'<linearGradient id="{gid}" x1="{x1:.1f}%" y1="{y1:.1f}%" x2="{x2:.1f}%" y2="{y2:.1f}%">'
            f'{stops}</linearGradient>')


def svg_texfill_def(o, pid):
    """An SVG <pattern> (with an embedded <image>) that paints an object's texture fill.
    A stretched fill uses one image scaled to the object's bounding box (patternUnits=
    objectBoundingBox, width/height 100%); a tiled fill repeats the image at its natural
    pixel size in userSpaceOnUse. Returns '' if there is no decodable texture."""
    import html as _H
    tf = o.get('texfill')
    if not tf:
        return ''
    img = texfill_image(o)
    if img.isNull():
        return ''
    src = _H.escape(tf.get('src', ''), quote=True)
    iw, ih = img.width() or 1, img.height() or 1
    if tf.get('mode', 'tile') == 'stretch':
        return (f'<pattern id="{pid}" patternUnits="objectBoundingBox" width="1" height="1">'
                f'<image href="{src}" x="0" y="0" width="{iw}" height="{ih}" '
                f'preserveAspectRatio="none"/></pattern>')
    r = obj_rect(o)
    return (f'<pattern id="{pid}" patternUnits="userSpaceOnUse" '
            f'x="{r.x():.2f}" y="{r.y():.2f}" width="{iw}" height="{ih}">'
            f'<image href="{src}" x="0" y="0" width="{iw}" height="{ih}"/></pattern>')


def svg_fill_value(o, idx=0):
    """(defs, fill) for a shape object's fill: a texture <pattern>, a gradient, or a flat
    colour — the value to drop into fill="…". Used by node/shape SVG splicing."""
    if o.get('texfill'):
        pid = f'tex{idx}'; d = svg_texfill_def(o, pid)
        if d:
            return d, f'url(#{pid})'
    g = o.get('grad')
    if g:
        gid = f'fgrad{idx}'; return svg_grad_def(g, gid), f'url(#{gid})'
    return '', (o.get('fill') or 'none')


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
    out = f' opacity="{op:.3f}"' if op < 1.0 else ''
    blend = o.get('blend')
    if blend and blend != 'SourceOver':
        out += f' style="mix-blend-mode:{BLEND_CSS.get(blend, "normal")}"'
    return out


def svg_image_el(o):
    """A real SVG <image href="data:..." x y width height> element for an image object."""
    import html as _H
    src = _H.escape(o.get('src', ''), quote=True)
    return (f'<image href="{src}" x="{o["x"]:.2f}" y="{o["y"]:.2f}" '
            f'width="{o["w"]:.2f}" height="{o["h"]:.2f}" preserveAspectRatio="none"'
            f'{_rot_transform(o)}{_opacity_attr(o)}/>')


def svg_shape_el(o, idx=0):
    """(defs, element) for a basic shape (rect/ellipse/quick/poly) that carries a texture
    fill — spliced explicitly so the <pattern> fill renders in a browser (QSvgGenerator
    can't express a texture). Returns ('', '') for anything without a texfill."""
    if not o.get('texfill'):
        return '', ''
    t = o.get('type')
    defs, fill = svg_fill_value(o, idx)
    stroke = o.get('stroke') or 'none'
    sw = o.get('sw', 2)
    common = f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{_rot_transform(o)}{_opacity_attr(o)}'
    if t == 'rect':
        el = f'<rect x="{o["x"]:.2f}" y="{o["y"]:.2f}" width="{o["w"]:.2f}" height="{o["h"]:.2f}" {common}/>'
    elif t == 'ellipse':
        cx = o['x'] + o['w'] / 2; cy = o['y'] + o['h'] / 2
        el = f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{o["w"]/2:.2f}" ry="{o["h"]/2:.2f}" {common}/>'
    elif t == 'quick':
        pp = quickshape_path(o['shape'], o['w'], o['h'], o.get('qp')).translated(o['x'], o['y'])
        el = f'<path d="{_painterpath_svg_d(pp)}" {common}/>'
    elif t in ('poly', 'path'):
        pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in o.get('pts', []))
        tag = 'polygon' if o.get('closed') else 'polyline'
        el = f'<{tag} points="{pts}" {common}/>'
    else:
        return '', ''
    return defs, el


def _painterpath_svg_d(pp):
    """A best-effort SVG 'd' string from a QPainterPath (lines + cubics), for splicing a
    QuickShape with a texture fill as a real <path>."""
    d = []
    i = 0; n = pp.elementCount()
    while i < n:
        el = pp.elementAt(i)
        if el.type == QPainterPath.MoveToElement:
            d.append(f'M {el.x:.2f} {el.y:.2f}'); i += 1
        elif el.type == QPainterPath.LineToElement:
            d.append(f'L {el.x:.2f} {el.y:.2f}'); i += 1
        elif el.type == QPainterPath.CurveToElement:
            c2 = pp.elementAt(i + 1); ep = pp.elementAt(i + 2)
            d.append(f'C {el.x:.2f} {el.y:.2f} {c2.x:.2f} {c2.y:.2f} {ep.x:.2f} {ep.y:.2f}'); i += 3
        else:
            i += 1
    d.append('Z')
    return ' '.join(d)


def svg_node_el(o, idx=0):
    """(defs, element) for a node ('nodes') object: a real <path d="M.. C..">, with its
    fill/stroke/dash, opacity and rotation — plus any arrowheads, so it is browser-true."""
    d = node_svg_d(o)
    if not d:
        return '', ''
    defs = ''
    if o.get('closed'):
        defs, fill = svg_fill_value(o, idx)
    else:
        fill = 'none'
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


def svg_textpath_el(o, idx=0):
    """(defs, element) for a text-on-path object: a <path> def the text follows, plus a
    <text><textPath href="#..."> that lays the glyphs along it — browser-true."""
    import html as _H
    pp = textpath_path(o)
    if pp is None:
        return '', ''
    pts = o.get('pathpts') or []
    d = 'M ' + ' L '.join(f'{x:.2f} {y:.2f}' for x, y in pts)
    pid = f'tpath{idx}'
    defs = f'<path id="{pid}" d="{d}" fill="none"/>'
    fam = _H.escape(o.get('family', 'Noto Sans'), quote=True)
    sz = max(1, int(o.get('size', 48)))
    fill = o.get('fill') or 'none'
    stroke = f' stroke="{o["stroke"]}" stroke-width="{o.get("sw", 2)}"' if o.get('stroke') else ''
    body = _H.escape(o.get('text', ''))
    el = (f'<text font-family="{fam}" font-size="{sz}" fill="{fill}"{stroke}'
          f'{_opacity_attr(o)}><textPath href="#{pid}" xlink:href="#{pid}">{body}</textPath></text>')
    return defs, el


def svg_dim_el(o, idx=0):
    """(defs, element) for a dimension object: the measured line with end ticks and an
    auto length label — assembled as plain SVG so it renders in any browser."""
    import html as _H
    pts = o.get('pts') or []
    if len(pts) < 2:
        return '', ''
    (x1, y1), (x2, y2) = pts[0], pts[1]
    col = o.get('stroke') or '#1f2a30'; sw = o.get('sw', 2)
    ang = math.atan2(y2 - y1, x2 - x1); tick = max(6.0, sw * 4.0)
    nx, ny = -math.sin(ang) * tick, math.cos(ang) * tick
    parts = [f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
             f'stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>']
    for (tx, ty) in ((x1, y1), (x2, y2)):
        parts.append(f'<line x1="{tx - nx:.2f}" y1="{ty - ny:.2f}" x2="{tx + nx:.2f}" y2="{ty + ny:.2f}" '
                     f'stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>')
    label = _dim_label(o)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        a = math.degrees(ang)
        if a > 90 or a < -90: a += 180
        fs = int(o.get('size') or max(11, int(sw * 7)))
        parts.append(f'<text x="{mx:.2f}" y="{my - tick:.2f}" fill="{col}" font-size="{fs}" '
                     f'font-family="Noto Sans" text-anchor="middle" '
                     f'transform="rotate({a:.2f} {mx:.2f} {my:.2f})">{_H.escape(label)}</text>')
    return '', f'<g{_opacity_attr(o)}>{"".join(parts)}</g>'


def svg_conn_el(o, idx=0, objs=None):
    """(defs, element) for a connector: a straight line between its resolved endpoints,
    with an end arrowhead, written as plain SVG."""
    objs = objs if objs is not None else _PAINT_OBJS
    a, b = conn_endpoints(o, objs)
    col = o.get('stroke') or '#1f2a30'; sw = o.get('sw', 2)
    parts = [f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" '
             f'stroke="{col}" stroke-width="{sw}" stroke-linecap="round"{svg_dash_attr(o)}/>']
    which = o.get('arrow', 'end')
    if which != 'none':
        size = max(8.0, sw * 3.0)

        def tri(tip, frm):
            pp = _arrow_head_path(tip, frm, size); d = []
            for i in range(pp.elementCount()):
                el = pp.elementAt(i)
                d.append(('M' if el.type == QPainterPath.MoveToElement else 'L') + f' {el.x:.2f} {el.y:.2f}')
            return f'<path d="{" ".join(d)} Z" fill="{col}" stroke="none"/>'
        if which in ('end', 'both'): parts.append(tri(b, a))
        if which in ('start', 'both'): parts.append(tri(a, b))
    return '', f'<g{_opacity_attr(o)}>{"".join(parts)}</g>'


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
    blend = o.get('blend')
    blended = bool(blend) and blend != 'SourceOver'
    faded = op < 1.0 or blended
    if faded:
        p.save(); p.setOpacity(p.opacity() * op)
        if blended:
            p.setCompositionMode(_blend_mode(blend))
    if rotated:
        # Rotate about the object's centre. QPainter transforms are captured by
        # QSvgGenerator as a <g transform="..."> too, so rotation survives SVG export
        # for shapes (text is spliced separately with its own rotate()).
        cx, cy = obj_center(o)
        p.save(); p.translate(cx, cy); p.rotate(a); p.translate(-cx, -cy)
    if o.get('perspective') or o.get('envelope'):
        draw_object_warped(p, o, selected, skip_text)   # render-time Perspective / Envelope warp
    elif o.get('agrad'):
        _paint_object_agrad(p, o, selected, skip_text)
    else:
        _paint_object_body(p, o, selected, skip_text)
    if rotated:
        p.restore()
    if faded:
        p.restore()


def _paint_object_agrad(p, o, selected=False, skip_text=False):
    """Transparency gradient (o['agrad']): render the object to a temp layer, multiply its
    alpha by a linear a1→a2 fade across the gradient angle, then draw the masked layer back
    at the painter's current opacity (so it composes with the flat opacity). Ported from
    PAGEcreator's paint_obj agrad wrapper, adapted to DRAWmaster's world coordinates.
    The layer spans the object's bounding box + margin so behind/over effects are kept."""
    ag = o['agrad']; r = obj_rect(o)
    ox, oy = r.x(), r.y(); w = r.width() or 1; h = r.height() or 1
    try:
        sx = math.hypot(p.worldTransform().m11(), p.worldTransform().m12()) or 1
    except Exception:
        sx = 1
    sx = max(0.5, min(sx, 8))
    pad = 48   # room for shadow/glow/reflection to live inside the layer
    W = max(1, int(math.ceil((w + 2 * pad) * sx))); H = max(1, int(math.ceil((h + 2 * pad) * sx)))
    layer = QImage(W, H, QImage.Format_ARGB32_Premultiplied); layer.fill(Qt.transparent)
    lp = QPainter(layer)
    lp.setRenderHint(QPainter.Antialiasing); lp.setRenderHint(QPainter.SmoothPixmapTransform)
    lp.scale(sx, sx); lp.translate(pad - ox, pad - oy)
    _paint_object_body(lp, o, selected, skip_text)
    # alpha mask: a1..a2 opacity across the gradient angle, applied with DestinationIn
    ang = math.radians(ag.get('angle', 0)); dx, dy = math.cos(ang), math.sin(ang)
    cx, cy = ox + w / 2, oy + h / 2
    mg = QLinearGradient(cx - dx * w / 2, cy - dy * h / 2, cx + dx * w / 2, cy + dy * h / 2)
    mg.setColorAt(0, QColor(0, 0, 0, int(round(max(0, min(100, ag.get('a1', 100))) * 2.55))))
    mg.setColorAt(1, QColor(0, 0, 0, int(round(max(0, min(100, ag.get('a2', 0))) * 2.55))))
    lp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    lp.setPen(Qt.NoPen); lp.setBrush(QBrush(mg))
    lp.drawRect(QRectF(ox - pad, oy - pad, w + 2 * pad, h + 2 * pad))
    lp.end()
    p.drawImage(QRectF(ox - pad, oy - pad, w + 2 * pad, h + 2 * pad), layer)


def _paint_object_body(p, o, selected=False, skip_text=False):
    if skip_text and o.get('type') == 'text' and not o.get('pathpts'):
        draw_object_fx(p, o); return   # keep shadow/glow; the SVG <text> draws the glyphs
    draw_object_reflect(p, o)   # mirrored copy sits behind/below the object
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
        p.save(); p.translate(o['x'], o['y']); p.drawPath(quickshape_path(o['shape'], o['w'], o['h'], o.get('qp'))); p.restore()
    elif t == 'nodes':
        pp = node_painter_path(o)
        if o.get('linestyle') == 'calligraphic' and not (o.get('closed') and o.get('fill')):
            samp = _flatten_painterpath(pp)
            rib = calligraphic_outline(samp, o.get('sw', 2), o.get('nib_angle', 45))
            p.save(); p.setPen(Qt.NoPen); p.setBrush(QColor(o.get('stroke') or '#1f2a30'))
            p.drawPath(rib); p.restore()
        elif o.get('closed') and o.get('fill'):
            p.drawPath(pp)
        else:
            p.setBrush(Qt.NoBrush); p.drawPath(pp)
        draw_arrowheads(p, o)
    elif t == 'text':
        if o.get('pathpts'):
            draw_text_on_path(p, o)   # glyphs flow along the attached path
        else:
            # Draw glyphs as a filled path so a fill/gradient/outline all apply, and so
            # it renders identically offscreen (a bare QPainter.drawText can misbehave
            # headless). Baseline sits at the font ascent inside the object's box.
            fm = QFontMetricsF(text_font(o)); tp = QPainterPath()
            tp.addText(o['x'], o['y'] + fm.ascent(), text_font(o), o.get('text', ''))
            if not o.get('stroke'): p.setPen(Qt.NoPen)
            p.drawPath(tp)
    elif t == 'brush':
        draw_brush(p, o)
    elif t == 'dim':
        draw_dimension(p, o)
    elif t == 'conn':
        draw_connector(p, o, _PAINT_OBJS)
    elif t in ('line', 'path', 'poly'):
        poly = QPolygonF([QPointF(x, y) for x, y in o['pts']])
        if o.get('linestyle') == 'calligraphic' and not (o.get('closed') and o.get('fill')):
            rib = calligraphic_outline(o['pts'], o.get('sw', 2), o.get('nib_angle', 45))
            p.save(); p.setPen(Qt.NoPen); p.setBrush(QColor(o.get('stroke') or '#1f2a30'))
            p.drawPath(rib); p.restore()
        elif o.get('fill') and len(o['pts']) > 2:
            path = QPainterPath(); path.addPolygon(poly)
            if o.get('closed'): path.closeSubpath()
            p.drawPath(path)
        else:
            p.drawPolyline(poly) if not o.get('closed') else p.drawPolygon(poly)
        draw_arrowheads(p, o)
    draw_object_fx_over(p, o)   # feather / bevel modify the object's own edges, drawn on top
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
        self.pending_image = None  # dict(uri,w,h) awaiting a click/drag placement
        # Pen (Bézier) tool: nodes being laid down, and the live smooth-drag node
        self.pen_nodes = None; self.pen_dragging = False
        # Node tool: the path being reshaped, which node/handle is grabbed, and which node
        # index is "selected" (for delete / type-convert via keys and menu)
        self.node_obj = None; self.node_grab = None; self.selected_node = None
        # Perspective / Envelope warp tools: which control point (index) is grabbed
        self.warp_grab = None
        # Knife tool: the cut line being dragged, as (p1, p2) or None
        self.knife_line = None
        # transform/rubber-band drag state
        self.handle = None       # which transform handle is being dragged
        self.drag_start = None   # canvas pt where a handle/rubber drag began
        self.drag_orig = None    # deep snapshot of selected objects at drag start
        self.rubber = None       # (a, b) rubber-band rect while selecting
        # grid, guides & snapping (non-printing: screen only, never in PNG/SVG)
        self.show_grid = False
        self.grid = 20
        self.snap = True
        self.unit = 'px'        # measurement unit for the readout & dimension labels
        self._next_cid = 1      # next connector-anchor id to hand out
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

    # ---------------------------------------------------------------- flip
    def flip_selection(self, axis):
        """Mirror the selection horizontally ('h') or vertically ('v') about the combined
        bounding box of the selection, moving/reflecting every member's geometry."""
        sel = self._selection()
        if not sel: return
        self.snapshot()
        rects = [obj_bounds(o) for o in sel]; combo = rects[0]
        for r in rects[1:]: combo = combo.united(r)
        cx = combo.center().x(); cy = combo.center().y()
        for o in sel: self._flip_obj(o, axis, cx, cy)
        self.update()

    def _flip_obj(self, o, axis, cx, cy):
        """Reflect one object's geometry across the vertical line x=cx (axis 'h') or the
        horizontal line y=cy (axis 'v'). Point lists mirror directly; boxed shapes mirror
        their top-left corner; node handles flip sign on the mirrored axis."""
        def fx(x): return 2 * cx - x if axis == 'h' else x
        def fy(y): return 2 * cy - y if axis == 'v' else y
        t = o['type']
        if t in ('rect', 'ellipse', 'quick', 'text', 'image'):
            if t == 'text' and o.get('pathpts'):
                o['pathpts'] = [(fx(x), fy(y)) for x, y in o['pathpts']]; return
            r = obj_rect(o)
            o['x'] = (2 * cx - (r.x() + r.width())) if axis == 'h' else r.x()
            o['y'] = (2 * cy - (r.y() + r.height())) if axis == 'v' else r.y()
        elif t == 'nodes':
            for nd in o.get('nodes', []):
                nd['x'], nd['y'] = fx(nd['x']), fy(nd['y'])
                hin = nd.get('hin', [0, 0]); hout = nd.get('hout', [0, 0])
                if axis == 'h':
                    nd['hin'] = [-hin[0], hin[1]]; nd['hout'] = [-hout[0], hout[1]]
                else:
                    nd['hin'] = [hin[0], -hin[1]]; nd['hout'] = [hout[0], -hout[1]]
        elif t == 'conn':
            for key in ('a', 'b'):
                end = o.get(key)
                if isinstance(end, dict) and end.get('anchor') is None and 'pt' in end:
                    px, py = end['pt']; end['pt'] = [fx(px), fy(py)]
        else:   # line / path / poly / dim (all carry 'pts')
            o['pts'] = [(fx(x), fy(y)) for x, y in o['pts']]

    # ---------------------------------------------------------------- lock / duplicate
    def toggle_lock(self):
        """Lock or unlock the selected objects. Locked objects set o['locked']=True and
        are skipped by click selection and dragging until unlocked."""
        sel = self._selection()
        if not sel: return
        self.snapshot()
        new_state = not all(o.get('locked') for o in sel)
        for o in sel:
            if new_state: o['locked'] = True
            else: o.pop('locked', None)
        self.update()

    def duplicate_selection(self, dx=16, dy=16):
        """Duplicate (clone) the selected objects as fresh copies offset by (dx, dy), and
        select the copies. Group membership is preserved by re-mapping group ids."""
        sel = self._selection()
        if not sel: return []
        self.snapshot()
        gid_map = {}; copies = []
        for o in sel:
            c = copy.deepcopy(o)
            c.pop('locked', None)
            g = c.get('gid')
            if g is not None:
                if g not in gid_map:
                    gid_map[g] = self._next_gid; self._next_gid += 1
                c['gid'] = gid_map[g]
            if c.get('cid') is not None:
                c['cid'] = self._next_cid; self._next_cid += 1
            self._shift_obj(c, dx, dy)
            self.objs.append(c); copies.append(c)
        self.set_selection(copies); self.update()
        return copies

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
        t = o['type']
        if t == 'text' and o.get('pathpts'):
            o['pathpts'] = [(x + dx, y + dy) for x, y in o['pathpts']]
        elif t in ('rect', 'ellipse', 'quick', 'text', 'image'):
            o['x'] += dx; o['y'] += dy
        elif t == 'nodes':
            for nd in o.get('nodes', []):
                nd['x'] += dx; nd['y'] += dy
        elif t == 'conn':
            for key in ('a', 'b'):
                end = o.get(key)
                if isinstance(end, dict) and end.get('anchor') is None and 'pt' in end:
                    px, py = end['pt']; end['pt'] = [px + dx, py + dy]
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
        global _PAINT_OBJS; _PAINT_OBJS = self.objs
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#e9ebee'))
        p.fillRect(QRectF(0, 0, self.W * self.zoom, self.H * self.zoom), QColor('#ffffff'))
        p.scale(self.zoom, self.zoom)
        if self.show_grid:
            self._draw_grid(p)
        sel_set = set(id(o) for o in self._selection())
        for o in self.ordered_objs():
            paint_object(p, o, id(o) in sel_set)
        if self.start and self.cur and self.tool in ('rect', 'ellipse', 'line', 'quick', 'dim', 'conn'):
            tmp = self._shape_from(self.start, self.cur)
            if tmp: paint_object(p, tmp)
        if self.tool == 'image' and self.pending_image and self.start and self.cur:
            r = QRectF(QPointF(*self.start), QPointF(*self.cur)).normalized()
            p.setPen(QPen(QColor('#2a7de1'), 0, Qt.DashLine)); p.setBrush(Qt.NoBrush)
            p.drawRect(r)
        if self.poly_pts and len(self.poly_pts) >= 1:
            prev = {'type': 'poly', 'pts': self.poly_pts + ([self.cur] if self.cur else []),
                    'stroke': self.stroke.name(), 'sw': self.sw, 'fill': None, 'closed': False}
            paint_object(p, prev)
        if self.tool == 'pen' and self.pen_nodes:
            self._draw_pen_preview(p)
        if self.tool == 'knife' and self.knife_line is not None:
            (ax, ay), (bx, by) = self.knife_line
            p.setPen(QPen(QColor('#e14d2a'), 0, Qt.DashLine)); p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(ax, ay), QPointF(bx, by))
        self._draw_guides(p)
        if self.rubber:
            self._draw_rubber(p)
        if self.tool == 'select':
            self._draw_handles(p)
        if self.tool == 'node' and self.node_obj is not None:
            self._draw_node_handles(p)
        if self.tool in ('perspective', 'envelope'):
            self._draw_warp_handles(p)
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

    def _qs_adjust(self, o):
        """If o is an adjustable QuickShape, return (param, lo, hi, current-value); else
        None. Drives the extra orange control handle (à la DrawPlus's yellow node)."""
        if o.get('type') != 'quick':
            return None
        spec = ADJUSTABLE_QS.get(o.get('shape'))
        if not spec:
            return None
        param, _label, lo, hi, default = spec
        val = (o.get('qp') or {}).get(param, default)
        return (param, lo, hi, val)

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
        adj = self._qs_adjust(o)
        if adj:
            param, lo, hi, val = adj
            frac = (val - lo) / (hi - lo) if hi > lo else 0.5
            pts['qparam'] = (r.left() + frac * r.width(), r.top() + 18 / max(self.zoom, 0.01))
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
            elif k == 'qparam':
                p.setPen(QPen(QColor('#e08000'), 1)); pen.setCosmetic(True)
                p.setBrush(QColor('#ffb43a'))
                dm = QPolygonF([QPointF(c.x(), c.y() - hs), QPointF(c.x() + hs, c.y()),
                                QPointF(c.x(), c.y() + hs), QPointF(c.x() - hs, c.y())])
                p.drawPolygon(dm)
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
        for i, nd in enumerate(nodes):
            if i == self.selected_node:
                p.setPen(pen); p.setBrush(QColor('#ff8a00'))
            else:
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

    # ---------------------------------------------------------------- Perspective / Envelope
    def _warp_target(self):
        """The single selected object the warp tools act on (or None)."""
        sel = self._selection()
        return sel[0] if len(sel) == 1 else None

    def _warp_points(self, o):
        """World-coord control points for the active warp tool over object o, as a list of
        QPointF (perspective → 4 corners; envelope → mesh grid). Ensures the key exists."""
        r = obj_rect(o)
        if self.tool == 'perspective':
            persp = o.get('perspective') or default_perspective()
            return _warp_pts(r, persp)
        env = o.get('envelope') or default_envelope()
        return _warp_pts(r, env['pts'])

    def _draw_warp_handles(self, p):
        """Draw the perspective corner box, or the envelope mesh grid, with draggable
        control points on the single selected object."""
        o = self._warp_target()
        if o is None: return
        pts = self._warp_points(o)
        hs = (self.HANDLE_PX + 1) / max(self.zoom, 0.01)
        pen = QPen(QColor('#8a3ffc'), 1, Qt.SolidLine); pen.setCosmetic(True)
        p.save(); p.setPen(pen); p.setBrush(Qt.NoBrush)
        if self.tool == 'perspective':
            p.drawPolygon(QPolygonF(pts + [pts[0]]))
        else:
            env = o.get('envelope') or default_envelope()
            cols, rows = env.get('cols', 2), env.get('rows', 2)
            def gp(i, j): return pts[j * (cols + 1) + i]
            for j in range(rows + 1):
                p.drawPolyline(QPolygonF([gp(i, j) for i in range(cols + 1)]))
            for i in range(cols + 1):
                p.drawPolyline(QPolygonF([gp(i, j) for j in range(rows + 1)]))
        p.setBrush(QColor('#ffffff'))
        for c in pts:
            p.drawEllipse(c, hs * .55, hs * .55)
        p.restore()

    def _hit_warp(self, pt):
        """Index of the warp control point under pt (within tolerance), or None."""
        o = self._warp_target()
        if o is None: return None
        pts = self._warp_points(o)
        tol = (self.HANDLE_PX + 5) / max(self.zoom, 0.01)
        for i, c in enumerate(pts):
            if abs(c.x() - pt[0]) <= tol and abs(c.y() - pt[1]) <= tol:
                return i
        return None

    def _drag_warp_to(self, pt):
        """Move the grabbed warp control point to pt, updating o['perspective']/['envelope']
        as a fractional offset of the object's bounding box (non-destructive)."""
        o = self._warp_target()
        if o is None or self.warp_grab is None: return
        r = obj_rect(o); w = r.width() or 1; h = r.height() or 1
        fx = (pt[0] - r.x()) / w; fy = (pt[1] - r.y()) / h
        if self.tool == 'perspective':
            persp = o.get('perspective')
            if persp is None:
                persp = default_perspective(); o['perspective'] = persp
            persp[self.warp_grab] = [fx, fy]
        else:
            env = o.get('envelope')
            if env is None:
                env = default_envelope(); o['envelope'] = env
            env['pts'][self.warp_grab] = [fx, fy]

    def _hit_segment(self, pt):
        """Return (seg_index, t) for the path segment nearest pt (within tolerance), or
        None. Used by the Node tool's double-click to insert a node on a segment."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return None
        nodes = o.get('nodes', []); n = len(nodes)
        if n < 2:
            return None
        tol = 8 / max(self.zoom, 0.01)
        closed = o.get('closed'); segs = n if closed else n - 1
        best = None
        for i in range(segs):
            a = nodes[i]; b = nodes[(i + 1) % n]
            p0 = (a['x'], a['y'])
            p1 = (a['x'] + a.get('hout', [0, 0])[0], a['y'] + a.get('hout', [0, 0])[1])
            p2 = (b['x'] + b.get('hin', [0, 0])[0], b['y'] + b.get('hin', [0, 0])[1])
            p3 = (b['x'], b['y'])
            for k in range(1, 24):
                t = k / 24.0
                sx, sy = _bezier_point(p0, p1, p2, p3, t)
                d = math.hypot(sx - pt[0], sy - pt[1])
                if d <= tol and (best is None or d < best[0]):
                    best = (d, i, t)
        return (best[1], best[2]) if best else None

    def add_node_at(self, pt):
        """Node tool: insert a node on the segment under pt (splitting the Bézier so the
        shape is unchanged). Returns True if a node was added."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return False
        hit = self._hit_segment(pt)
        if hit is None:
            return False
        i, t = hit
        self.snapshot()
        o['nodes'] = split_segment(o['nodes'], i, bool(o.get('closed')), t)
        self.selected_node = i + 1
        self.update(); return True

    def delete_selected_node(self):
        """Node tool: remove the selected (or hovered) node and reconnect its neighbours.
        A path shorter than 2 nodes is removed entirely."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return False
        nodes = o.get('nodes', [])
        i = self.selected_node
        if i is None or not (0 <= i < len(nodes)):
            return False
        self.snapshot()
        nodes.pop(i)
        if len(nodes) < 2:
            if o in self.objs: self.objs.remove(o)
            self.node_obj = None; self.selected_node = None
            self.sel = None; self.sels = []
        else:
            self.selected_node = min(i, len(nodes) - 1)
        self.update(); return True

    def set_selected_node_type(self, kind):
        """Convert the selected node to cusp / smooth / symmetric."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return False
        nodes = o.get('nodes', []); i = self.selected_node
        if i is None or not (0 <= i < len(nodes)):
            return False
        self.snapshot()
        set_node_type(nodes[i], kind)
        self.update(); return True

    def cycle_selected_node_type(self):
        """Cycle the selected node cusp → smooth → symmetric → cusp."""
        o = self.node_obj
        if o is None or o.get('type') != 'nodes':
            return False
        nodes = o.get('nodes', []); i = self.selected_node
        if i is None or not (0 <= i < len(nodes)):
            return False
        nd = nodes[i]
        hin = nd.get('hin', [0, 0]); hout = nd.get('hout', [0, 0])
        sym = nd.get('smooth') and abs(hin[0] + hout[0]) < 1e-6 and abs(hin[1] + hout[1]) < 1e-6
        if not nd.get('smooth'):
            nxt = 'smooth'
        elif not sym:
            nxt = 'symmetric'
        else:
            nxt = 'cusp'
        return self.set_selected_node_type(nxt)

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
        for k in ('shadow', 'glow', 'grad', 'rot', 'opacity', 'blend', 'gid', 'dash', 'arrow',
                  'agrad', 'reflect', 'feather', 'bevel', 'linestyle', 'nib_angle'):
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

    def _as_node_obj(self, o):
        """Return o as a 'nodes' object, converting non-node shapes to Bézier nodes (used by
        Blend). Returns None if o can't be converted."""
        if o.get('type') == 'nodes':
            return o
        if o.get('type') not in ('rect', 'ellipse', 'quick', 'line', 'poly', 'path'):
            return None
        nodes, closed = nodes_from_obj(o)
        if not nodes:
            return None
        new = dict(type='nodes', nodes=nodes, closed=closed,
                   stroke=o.get('stroke'), sw=o.get('sw', 2), fill=o.get('fill'))
        return new

    def blend_selection(self, steps):
        """DrawPlus Blend: morph between the two selected objects over `steps` intermediate
        shapes (geometry + fill + stroke + width), inserted BETWEEN the originals in z-order
        and grouped with them. Requires exactly two selected objects. Returns the new group's
        object list, or None."""
        sel = self._selection()
        if len(sel) != 2:
            return None
        a = self._as_node_obj(sel[0]); b = self._as_node_obj(sel[1])
        if a is None or b is None:
            return None
        self.snapshot()
        mids = blend_objects(a, b, steps)
        lid = self.obj_layer(sel[0])
        for o in mids:
            o['layer'] = lid
        gid = self._next_gid; self._next_gid += 1
        # z-order: keep the two originals where they are, drop the intermediates just after
        # the first original (so they sit between the pair) in paint order.
        try:
            ia = self.objs.index(sel[0])
        except ValueError:
            ia = len(self.objs) - 1
        for k, o in enumerate(mids):
            self.objs.insert(ia + 1 + k, o)
        members = [sel[0]] + mids + [sel[1]]
        for o in members:
            o['gid'] = gid
        self.set_selection(members); self.update()
        return members

    def _object_painterpath(self, o):
        """A filled QPainterPath for a shape object in canvas coordinates (for combining)."""
        t = o['type']
        pp = QPainterPath()
        if t == 'rect':
            pp.addRect(QRectF(o['x'], o['y'], o['w'], o['h']))
        elif t == 'ellipse':
            pp.addEllipse(QRectF(o['x'], o['y'], o['w'], o['h']))
        elif t == 'quick':
            pp = quickshape_path(o['shape'], o['w'], o['h'], o.get('qp')).translated(o['x'], o['y'])
        elif t == 'nodes':
            pp = node_painter_path(o)
        elif t in ('poly', 'path'):
            pp.addPolygon(QPolygonF([QPointF(x, y) for x, y in o['pts']]))
            pp.closeSubpath()
        return pp

    def _node_path_of(self, o):
        """Return o as a QPainterPath via its node form (converting rect/ellipse/… first),
        so Roughen/Knife can work on any convertible shape. (None if unconvertible.)"""
        if o.get('type') == 'nodes':
            return node_painter_path(o)
        n = self._as_node_obj(o)
        return node_painter_path(n) if n else None

    def roughen_selection(self, amplitude, freq, smooth):
        """Roughen each selected (convertible) object: flatten its outline, perturb it with
        roughen_points (seeded, reproducible), and replace it with a jagged node path."""
        sel = [o for o in self._selection()
               if o.get('type') in ('rect', 'ellipse', 'quick', 'line', 'poly', 'path', 'nodes')]
        if not sel:
            return 0
        self.snapshot()
        done = 0
        for o in list(sel):
            node_o = self._as_node_obj(o)
            if node_o is None:
                continue
            closed = bool(node_o.get('closed'))
            pp = node_painter_path(node_o)
            if pp.isEmpty():
                continue
            # flatten to a polyline sized to the outline length (denser than the default)
            length = max(1.0, pp.length())
            step = max(0.002, min(0.05, 60.0 / length))
            pts = _flatten_painterpath(pp, step)
            if closed and pts and (pts[0] != pts[-1]):
                pts = pts + [pts[0]]
            seed = o.get('_roughseed')
            if seed is None:
                seed = (abs(hash((round(pts[0][0], 1), round(pts[0][1], 1), len(pts)))) % 100000) + 1
            rough = roughen_points(pts, amplitude, freq, smooth, seed)
            nodes = _points_to_nodes(rough, closed, smooth)
            if len(nodes) < 2:
                continue
            new = dict(type='nodes', nodes=nodes, closed=closed, _roughseed=seed,
                       stroke=o.get('stroke', '#1f2a30'), sw=o.get('sw', 2),
                       fill=o.get('fill') if closed else None, layer=self.obj_layer(o))
            for k in ('shadow', 'glow', 'grad', 'rot', 'opacity', 'blend', 'gid', 'dash',
                      'agrad', 'reflect', 'feather', 'bevel'):
                if o.get(k) is not None:
                    new[k] = copy.deepcopy(o[k])
            i = self.objs.index(o); self.objs[i] = new
            done += 1
        if done:
            self.set_selection([x for x in self.objs if x.get('_roughseed') is not None][-done:])
            self.update()
        return done

    def knife_cut(self, p1, p2):
        """Cut every crossed (filled, convertible) object along the line p1→p2, replacing it
        with its pieces as node paths (fill/stroke preserved). Open strokes are skipped."""
        sel = self._selection()
        targets = sel if sel else self.ordered_objs()
        targets = [o for o in targets
                   if o.get('type') in ('rect', 'ellipse', 'quick', 'poly', 'nodes', 'path')]
        if not targets:
            return 0
        made = []
        snap_done = False
        for o in list(targets):
            if o.get('type') == 'nodes' and not o.get('closed'):
                continue  # open stroke — skip (filled shapes only)
            pp = self._node_path_of(o)
            if pp is None or pp.isEmpty():
                continue
            pieces = knife_split(pp, p1, p2)
            if len(pieces) < 2:
                continue
            if not snap_done:
                self.snapshot(); snap_done = True
            idx = self.objs.index(o) if o in self.objs else len(self.objs)
            new_objs = []
            for pc in pieces:
                nodes, closed = _nodes_from_painterpath(pc)
                if len(nodes) < 2:
                    continue
                npc = dict(type='nodes', nodes=nodes, closed=True,
                           stroke=o.get('stroke', '#1f2a30'), sw=o.get('sw', 2),
                           fill=o.get('fill', '#cfe3ef'), layer=self.obj_layer(o))
                for k in ('shadow', 'glow', 'opacity', 'blend'):
                    if o.get(k) is not None:
                        npc[k] = copy.deepcopy(o[k])
                new_objs.append(npc)
            if len(new_objs) < 2:
                continue
            if o in self.objs:
                self.objs.pop(idx)
            for j, npc in enumerate(new_objs):
                self.objs.insert(idx + j, npc)
            made.extend(new_objs)
        if made:
            self.set_selection(made); self.update()
        return len(made)

    def pos(self, e):
        return (e.position().x() / self.zoom, e.position().y() / self.zoom)

    def _shape_from(self, a, b):
        x1, y1 = a; x2, y2 = b
        base = dict(stroke=self.stroke.name(), sw=self.sw, fill=self.fill.name() if self.tool != 'line' else None,
                    layer=self.active_layer)
        if self.tool == 'line':
            return dict(type='line', pts=[a, b], **base)
        if self.tool == 'dim':
            return dict(type='dim', pts=[a, b], stroke=self.stroke.name(), sw=self.sw,
                        fill=None, unit=self.unit, layer=self.active_layer)
        if self.tool == 'conn':
            return dict(type='conn', a={'pt': list(a)}, b={'pt': list(b)},
                        stroke=self.stroke.name(), sw=self.sw, arrow='end',
                        fill=None, layer=self.active_layer)
        if self.tool == 'quick':
            return dict(type='quick', shape=self.quick_shape, x=min(x1, x2), y=min(y1, y2),
                        w=abs(x2 - x1) or 1, h=abs(y2 - y1) or 1, **base)
        return dict(type=self.tool, x=min(x1, x2), y=min(y1, y2), w=abs(x2 - x1), h=abs(y2 - y1), **base)

    def _cid_for(self, o):
        """The connector-anchor id of an object, assigning a fresh one the first time it
        is anchored so a connector can follow it when it moves."""
        if o.get('cid') is None:
            o['cid'] = self._next_cid; self._next_cid += 1
        return o['cid']

    def _make_connector(self, a, b):
        """Build a connector between two drag points. If a point lands on an object, that
        end anchors to the object's centre (and follows it); otherwise it stays a free point."""
        def end_for(pt):
            hit = next((o for o in reversed(self.ordered_objs())
                        if o.get('type') not in ('conn', 'dim') and obj_hit(o, pt)), None)
            if hit is not None:
                return {'anchor': self._cid_for(hit)}
            return {'pt': list(pt)}
        return dict(type='conn', a=end_for(a), b=end_for(b), stroke=self.stroke.name(),
                    sw=self.sw, arrow='end', fill=None, layer=self.active_layer)

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
            hit = next((o for o in reversed(self.ordered_objs())
                        if not o.get('locked') and obj_hit(o, pt)), None)
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
        if self.tool in ('rect', 'ellipse', 'line', 'quick', 'dim'):
            self.start = pt; self.cur = pt; return
        if self.tool == 'knife':
            self.knife_line = (pt, pt); return
        if self.tool == 'conn':
            self.start = pt; self.cur = pt; return
        if self.tool == 'text':
            self.win.place_text(pt); return
        if self.tool == 'image':
            if self.pending_image:
                self.start = pt; self.cur = pt
            else:
                self.win.import_image(at=pt)
            return
        if self.tool == 'brush':
            self.snapshot()
            self._brush_base = self.sw * 3 + 8
            ob = dict(type='brush', pts=[pt], widths=[self._brush_base * 0.45],
                      stroke=self.stroke.name(), fill=None, layer=self.active_layer)
            prof = getattr(self, 'brush_profile', None)
            if prof: ob['profile'] = copy.deepcopy(prof)
            self.objs.append(ob)
            self.update(); return
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
                self.node_grab = g; self.drag_start = pt; self.selected_node = g[1]
                self.snapshot(); self.update(); return
            # clicking elsewhere picks a path to edit
            hit = next((o for o in reversed(self.ordered_objs())
                        if o.get('type') == 'nodes' and obj_hit(o, pt)), None)
            if hit is None:
                hit = next((o for o in reversed(self.ordered_objs()) if obj_hit(o, pt)), None)
                if hit is not None and hit.get('type') != 'nodes':
                    hit = None
            self.node_obj = hit; self.node_grab = None; self.selected_node = None
            self.update(); return
        if self.tool in ('perspective', 'envelope'):
            o = self._warp_target()
            if o is None:
                # nothing selected: let a click pick an object so the tool has a target
                hit = next((x for x in reversed(self.ordered_objs())
                            if not x.get('locked') and obj_hit(x, pt)), None)
                if hit is not None: self.set_selection([hit])
                self.update(); return
            g = self._hit_warp(pt)
            if g is not None:
                self.snapshot(); self.warp_grab = g; self.drag_start = pt
            else:
                hit = next((x for x in reversed(self.ordered_objs())
                            if not x.get('locked') and obj_hit(x, pt)), None)
                if hit is not None and hit is not o: self.set_selection([hit])
            self.update(); return

    def mouseMoveEvent(self, e):
        pt = self.pos(e); self.win.set_pos(pt)
        if self.tool == 'select' and self.handle is not None and (e.buttons() & Qt.LeftButton):
            self._drag_handle(pt, bool(e.modifiers() & Qt.ShiftModifier)); self.update(); return
        if self.tool == 'select' and self.rubber is not None and (e.buttons() & Qt.LeftButton):
            self.rubber = (self.drag_start, pt); self.update(); return
        if self.tool == 'select' and self.sel is not None and (e.buttons() & Qt.LeftButton) and self.drag_off:
            self._move_sel(pt); self.update(); return
        if self.tool == 'knife' and self.knife_line is not None and (e.buttons() & Qt.LeftButton):
            self.knife_line = (self.knife_line[0], pt); self.update(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick', 'dim', 'conn', 'image') and self.start and (e.buttons() & Qt.LeftButton):
            self.cur = pt; self.update()
        elif self.tool == 'brush' and (e.buttons() & Qt.LeftButton) and self.objs and self.objs[-1].get('type') == 'brush':
            o = self.objs[-1]; lx, ly = o['pts'][-1]
            dist = math.hypot(pt[0] - lx, pt[1] - ly)
            if dist < 1.2: return
            base = getattr(self, '_brush_base', self.sw * 3 + 8)
            w = base * (1.0 - min(1.0, dist / 40.0) * 0.7)      # faster stroke → thinner (fake pressure)
            w = 0.5 * w + 0.5 * (o['widths'][-1] if o['widths'] else w)
            o['pts'].append(pt); o['widths'].append(w); self.update()
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
        elif self.tool in ('perspective', 'envelope') and self.warp_grab is not None and (e.buttons() & Qt.LeftButton):
            self._drag_warp_to(pt); self.update()

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
        if self.handle == 'qparam':
            adj = self._qs_adjust(o)
            if not adj: return
            param, lo, hi, _ = adj
            r0 = obj_rect(orig); a = obj_rot(orig)
            lx = pt[0]
            if a:
                cx, cy = r0.center().x(), r0.center().y()
                rad = math.radians(-a); dx, dy = pt[0] - cx, pt[1] - cy
                lx = cx + dx * math.cos(rad) - dy * math.sin(rad)
            frac = max(0.0, min(1.0, (lx - r0.left()) / (r0.width() or 1)))
            val = lo + frac * (hi - lo)
            if param in ('points', 'teeth'): val = round(val)
            o.setdefault('qp', {})[param] = val
            self.win.sync_props()
            return
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
        if self.tool == 'image' and self.pending_image and self.start:
            end = self.cur or self.start
            start = self.start; self.start = self.cur = None
            self.win.place_pending_image(start, end); self.win.sync_props(); return
        if self.tool in ('rect', 'ellipse', 'line', 'quick', 'dim') and self.start:
            if self.cur and (abs(self.cur[0] - self.start[0]) > 2 or abs(self.cur[1] - self.start[1]) > 2):
                self.snapshot(); self.objs.append(self._shape_from(self.start, self.cur))
                self.set_selection([self.objs[-1]])
            self.start = self.cur = None; self.update(); self.win.sync_props()
        elif self.tool == 'conn' and self.start:
            if self.cur and (abs(self.cur[0] - self.start[0]) > 2 or abs(self.cur[1] - self.start[1]) > 2):
                self.snapshot(); self.objs.append(self._make_connector(self.start, self.cur))
                self.set_selection([self.objs[-1]])
            self.start = self.cur = None; self.update(); self.win.sync_props()
        elif self.tool == 'knife' and self.knife_line is not None:
            p1, p2 = self.knife_line; self.knife_line = None
            if abs(p2[0] - p1[0]) > 2 or abs(p2[1] - p1[1]) > 2:
                self.knife_cut(p1, p2)
            self.update(); self.win.sync_props()
        elif self.tool == 'select' and self.handle is not None:
            self.handle = None; self.drag_start = self.drag_orig = None; self.update(); self.win.sync_props()
        elif self.tool == 'select' and self.rubber is not None:
            a, b = self.rubber; box = QRectF(QPointF(*a), QPointF(*b)).normalized()
            self.rubber = None
            if box.width() > 3 or box.height() > 3:
                picked = [o for o in self.ordered_objs() if not o.get('locked')
                          and (box.contains(obj_bounds(o)) or box.intersects(obj_bounds(o)))]
                self.set_selection(picked)
            self.drag_start = None; self.update()
        elif self.tool == 'select' and self.sel is not None and self.drag_off:
            self.drag_off = None; self.drag_orig = None
        elif self.tool == 'pen' and self.pen_dragging:
            self.pen_dragging = False; self.update()
        elif self.tool == 'node' and self.node_grab is not None:
            self.node_grab = None; self.drag_start = None
        elif self.tool in ('perspective', 'envelope') and self.warp_grab is not None:
            self.warp_grab = None; self.drag_start = None; self.win.sync_props()

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
        if self.tool == 'node' and self.node_obj is not None:
            pt = self.pos(e)
            g = self._hit_node(pt)
            if g is not None and g[0] == 'node':
                # double-click a node deletes it (reconnecting neighbours)
                self.selected_node = g[1]; self.delete_selected_node(); return
            # double-click a segment inserts a node (split Bézier, shape preserved)
            self.add_node_at(pt); return
        if self.tool == 'pen' and self.pen_nodes and len(self.pen_nodes) >= 2:
            # the double-click fires an extra press that duplicates the last node — drop it
            if len(self.pen_nodes) >= 2:
                a, b = self.pen_nodes[-2], self.pen_nodes[-1]
                if abs(a['x'] - b['x']) < 3 and abs(a['y'] - b['y']) < 3 and b['hout'] == [0, 0]:
                    self.pen_nodes.pop()
            self._finish_pen(closed=True)

    def keyPressEvent(self, e):
        if (self.tool == 'node' and self.node_obj is not None and self.selected_node is not None
                and e.key() in (Qt.Key_Delete, Qt.Key_Backspace)):
            self.delete_selected_node(); self.win.sync_props(); return
        if (self.tool == 'node' and self.node_obj is not None and self.selected_node is not None
                and e.key() == Qt.Key_C):
            self.cycle_selected_node_type(); return
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
            if fill is not None: o['fill'] = None if fill == '__none__' else fill; o.pop('grad', None)  # a solid fill replaces any gradient
            if stroke is not None: o['stroke'] = None if stroke == '__none__' else stroke
            if sw is not None: o['sw'] = sw
        self.update()

    def _scale_obj(self, o, ox, oy, sx, sy):
        """Scale a single object about the anchor (ox, oy) by (sx, sy) — used by the
        Transform panel to resize to an exact width/height."""
        def sp(x, y): return (ox + (x - ox) * sx, oy + (y - oy) * sy)
        t = o['type']
        if t in ('rect', 'ellipse', 'quick', 'image'):
            o['x'], o['y'] = sp(o['x'], o['y']); o['w'] *= sx; o['h'] *= sy
        elif t == 'text':
            o['x'], o['y'] = sp(o['x'], o['y']); o['size'] = max(1, o.get('size', 48) * sy)
        elif t == 'nodes':
            for nd in o.get('nodes', []):
                nd['x'], nd['y'] = sp(nd['x'], nd['y'])
                for k in ('hin', 'hout'):
                    h = nd.get(k, [0, 0]); nd[k] = [h[0] * sx, h[1] * sy]
        elif o.get('pts') is not None:
            o['pts'] = [sp(x, y) for x, y in o['pts']]

    def render_to(self, painter, skip_text=False, skip_special=False):
        """Paint every object. For SVG export, skip_special also omits image, node,
        texture-filled, dimension and connector objects so they can be spliced as explicit
        elements afterwards."""
        global _PAINT_OBJS; _PAINT_OBJS = self.objs
        for o in self.ordered_objs():
            if skip_special and (o.get('type') in ('image', 'nodes', 'dim', 'conn') or o.get('texfill')):
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
            if t == 'text' and o.get('pathpts'):
                d, e = svg_textpath_el(o, i)
            elif t == 'text':
                d, e = svg_text_el(o, i)
            elif t == 'image':
                d, e = '', svg_image_el(o)
            elif t == 'nodes':
                d, e = svg_node_el(o, i)
            elif t == 'dim':
                d, e = svg_dim_el(o, i)
            elif t == 'conn':
                d, e = svg_conn_el(o, i, self.objs)
            elif o.get('texfill'):
                d, e = svg_shape_el(o, i)
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
            cids = [o['cid'] for o in self.objs if isinstance(o.get('cid'), int)]
            self._next_cid = (max(cids) + 1) if cids else 1
            return True
        except Exception:
            return False

    def export_png(self, path):
        img = QImage(self.W, self.H, QImage.Format_ARGB32); img.fill(QColor('#ffffff'))
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); self.render_to(p); p.end()
        return img.save(path)


# ================================================================ Cutout Studio
def qimage_to_rgba(qi):
    """QImage → contiguous (H, W, 4) uint8 RGBA numpy array."""
    import numpy as np
    qi = qi.convertToFormat(QImage.Format_RGBA8888)
    w, h, bpl = qi.width(), qi.height(), qi.bytesPerLine()
    buf = np.frombuffer(memoryview(qi.constBits()), np.uint8)
    return buf.reshape((h, bpl))[:, :w * 4].reshape((h, w, 4)).copy()


def rgba_to_qimage(arr):
    """(H, W, 4) uint8 RGBA numpy array → a self-owning QImage."""
    import numpy as np
    arr = np.ascontiguousarray(arr, np.uint8)
    h, w = arr.shape[:2]
    return QImage(arr.tobytes(), w, h, w * 4, QImage.Format_RGBA8888).copy()


# ---------------------------------------------------------------- PhotoLab (ported from PAGEcreator)
try:
    from PIL import Image as _PILImage, ImageEnhance as _PILEnh
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

def _q2pil(qi):
    """QImage → PIL RGBA Image."""
    qi = qi.convertToFormat(QImage.Format_RGBA8888)
    w, h = qi.width(), qi.height()
    ba = qi.constBits().tobytes() if hasattr(qi.constBits(), 'tobytes') else bytes(qi.constBits())
    return _PILImage.frombytes('RGBA', (w, h), ba[:w * h * 4], 'raw', 'RGBA')

def _pil2q(im):
    """PIL Image → QImage (RGBA)."""
    im = im.convert('RGBA')
    return QImage(im.tobytes('raw', 'RGBA'), im.width, im.height, QImage.Format_RGBA8888).copy()

def apply_photolab(pil, params):
    src = pil if pil.mode == 'RGBA' else pil.convert('RGBA')
    a = src.split()[3]
    rgb = src.convert('RGB')
    def f(v): return max(0.05, 1.0 + v / 100.0)          # enhance factor from a ±% value
    b = params.get('brightness', 0); c = params.get('contrast', 0)
    s = params.get('saturation', 0); sh = params.get('sharpness', 0)
    temp = params.get('temperature', 0); hue = params.get('hue', 0)
    if b: rgb = _PILEnh.Brightness(rgb).enhance(f(b))
    if c: rgb = _PILEnh.Contrast(rgb).enhance(f(c))
    if s: rgb = _PILEnh.Color(rgb).enhance(f(s))
    if sh: rgb = _PILEnh.Sharpness(rgb).enhance(f(sh))
    if temp:
        # warm/cool: at ±100 shift R/B channels by ±~0.3× around 1.0
        rf = 1.0 + 0.3 * temp / 100.0; bf = 1.0 - 0.3 * temp / 100.0
        R, G, B = rgb.split()
        R = R.point(lambda px: min(255, int(px * rf)))
        B = B.point(lambda px: min(255, int(px * bf)))
        rgb = _PILImage.merge('RGB', (R, G, B))
    if hue:
        h, sv, vv = rgb.convert('HSV').split()
        d = int(round(hue * 255 / 360.0)) % 256
        h = h.point(lambda px: (px + d) % 256)
        rgb = _PILImage.merge('HSV', (h, sv, vv)).convert('RGB')
    return _PILImage.merge('RGBA', rgb.split() + (a,))


def _box_blur(a, r):
    """Separable box blur of a float32 (H, W) array, radius r (no SciPy needed)."""
    import numpy as np
    if r <= 0:
        return a
    k = 2 * r + 1
    for axis in (0, 1):
        n = a.shape[axis]
        pad = [(0, 0), (0, 0)]; pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis)
        lo = np.take(c, range(0, n), axis=axis)
        hi = np.take(c, range(k, k + n), axis=axis)
        a = (hi - lo) / k
    return a


# ---------------------------------------------------------------- AutoTrace / Vectorise
# Bitmap → editable vector node-paths (the DrawPlus Image Trace). Pure NumPy/PIL, no OpenCV:
# quantise → per-colour binary masks → flood-fill into blobs → Moore-neighbour boundary
# trace → Douglas–Peucker simplify → closed corner-node paths. trace_image() is GUI-free
# so it can be unit-tested; auto_trace() (on the window) wires it to the selected picture.

def _label_blobs(mask):
    """Label the connected foreground blobs of a bool mask (4-connectivity) with an
    iterative flood fill. Returns (labels int32 (H,W), count) — 0 is background."""
    import numpy as np
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    cur = 0
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if labels[sy, sx]:
            continue
        cur += 1
        stack = [(sy, sx)]; labels[sy, sx] = cur
        while stack:
            y, x = stack.pop()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur; stack.append((ny, nx))
    return labels, cur


def _trace_boundary(mask):
    """Moore-neighbour boundary trace of a single solid blob (bool mask). Returns an ordered
    list of (x, y) pixel corner points walking the outer contour clockwise. The contour is
    traced on the pixel grid so points are integer cell coordinates."""
    import numpy as np
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return []
    # start at the top-most, then left-most foreground pixel
    i0 = int(np.argmin(ys * mask.shape[1] + xs))
    start = (int(ys[i0]), int(xs[i0]))
    h, w = mask.shape
    def fg(y, x):
        return 0 <= y < h and 0 <= x < w and mask[y, x]
    # 8-neighbour offsets, clockwise starting from 'west'
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    contour = [start]
    cur = start
    b_dir = 0  # we entered 'start' coming from the west
    guard = 0; lim = 4 * int(mask.sum()) + 8
    first_step = None  # (pixel, b_dir) of the first step away from start — Jacob stop
    while guard < lim:
        guard += 1
        found = False
        # scan 8 neighbours clockwise beginning just after the backtrack direction
        for k in range(8):
            d = (b_dir + k) % 8
            dy, dx = nb[d]
            ny, nx = cur[0] + dy, cur[1] + dx
            if fg(ny, nx):
                # the new backtrack direction is opposite to the step we just took, +1 cw
                b_dir = (d + 4 + 1) % 8
                cur = (ny, nx)
                found = True
                break
        if not found:
            break  # isolated pixel
        step = (cur, b_dir)
        if first_step is None:
            first_step = step
        elif step == first_step:
            break  # Jacob's criterion: back at the start, repeating the first move
        contour.append(cur)
    # drop the trailing repeat of the start pixel if present
    if len(contour) > 1 and contour[-1] == contour[0]:
        contour.pop()
    # convert (row,col) → (x,y)
    return [(float(c[1]), float(c[0])) for c in contour]


def _perp_dist(p, a, b):
    """Perpendicular distance of point p from the line segment a→b."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _douglas_peucker(pts, tol):
    """Ramer–Douglas–Peucker simplification of an open polyline (iterative)."""
    n = len(pts)
    if n < 3:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        dmax, idx = 0.0, -1
        a, b = pts[i], pts[j]
        for k in range(i + 1, j):
            d = _perp_dist(pts[k], a, b)
            if d > dmax:
                dmax, idx = d, k
        if dmax > tol and idx != -1:
            keep[idx] = True
            stack.append((i, idx)); stack.append((idx, j))
    return [pts[k] for k in range(n) if keep[k]]


def _simplify_closed(pts, tol):
    """Douglas–Peucker for a CLOSED contour: simplify the open chain then de-dupe endpoints."""
    if len(pts) < 4:
        return pts
    out = _douglas_peucker(pts, tol)
    # the trace repeats the start as the last point; drop a duplicate tail
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out = out[:-1]
    # DP pins the open chain's first/last vertices; on a closed loop those may be
    # near-collinear with their wrap-around neighbours — drop any such redundant vertex.
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a = out[i - 1]; b = out[i]; c = out[(i + 1) % len(out)]
            if _perp_dist(b, a, c) <= tol:
                out.pop(i); changed = True; break
    return out


def _poly_area(pts):
    """Absolute shoelace area of a polygon (pixel units)."""
    n = len(pts)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) * 0.5


def trace_image(rgba, mode='logo', n_colors=6, tol=2.0, min_area=16, work_max=700):
    """Trace an (H,W,3|4) uint8 numpy image into vector regions. PURE (no GUI).

    mode: 'bw' (luminance threshold → foreground mask), 'logo' (quantise to n_colors flat
    colours), 'photo' (quantise to n_colors, default more). Returns a list of dicts
    ``{'nodes': [(x,y), ...], 'fill': '#rrggbb', 'area': float}`` in WORKING-pixel coords,
    ordered back-to-front (largest area first). Caller maps coords onto the canvas object.
    tol = Douglas–Peucker tolerance (px); min_area = skip blobs smaller than this (px²)."""
    import numpy as np
    from PIL import Image
    arr = np.asarray(rgba)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, -1)
    rgb = arr[:, :, :3].astype(np.uint8)
    h0, w0 = rgb.shape[:2]
    # cap the working resolution for speed; record the scale back to source pixels
    scale = min(1.0, float(work_max) / max(h0, w0))
    if scale < 1.0:
        im = Image.fromarray(rgb, 'RGB').resize((max(1, int(w0 * scale)), max(1, int(h0 * scale))),
                                                Image.BILINEAR)
        rgb = np.asarray(im, np.uint8)
    inv = (1.0 / scale) if scale else 1.0  # working-px → source-px multiplier
    h, w = rgb.shape[:2]

    regions = []  # (mask bool, fill hex)
    if mode == 'bw':
        lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
        # Otsu threshold (256-bin histogram)
        hist, _ = np.histogram(lum, bins=256, range=(0, 255))
        tot = hist.sum() or 1
        w_b = np.cumsum(hist); w_f = tot - w_b
        mean_b = np.cumsum(hist * np.arange(256)) / np.maximum(w_b, 1)
        gtot = (hist * np.arange(256)).sum()
        mean_f = (gtot - np.cumsum(hist * np.arange(256))) / np.maximum(w_f, 1)
        var = w_b * w_f * (mean_b - mean_f) ** 2
        thr = int(np.argmax(var[:-1])) if tot > 1 else 128
        dark = lum <= thr
        for m, fill in ((dark, '#000000'), (~dark, '#ffffff')):
            regions.append((m, fill))
    else:
        pim = Image.fromarray(rgb, 'RGB').quantize(colors=max(2, int(n_colors)),
                                                   method=Image.MEDIANCUT)
        idx = np.asarray(pim, np.int32)
        pal = pim.getpalette() or []
        used = np.unique(idx)
        for ci in used.tolist():
            m = idx == ci
            r, g, b = pal[ci * 3:ci * 3 + 3] if ci * 3 + 2 < len(pal) else (0, 0, 0)
            regions.append((m, '#%02x%02x%02x' % (int(r), int(g), int(b))))

    out = []
    for mask, fill in regions:
        if mask.sum() * (inv * inv) < min_area:
            continue
        labels, cnt = _label_blobs(mask)
        for lab in range(1, cnt + 1):
            blob = labels == lab
            a_src = int(blob.sum()) * inv * inv
            if a_src < min_area:
                continue
            contour = _trace_boundary(blob)
            if len(contour) < 3:
                continue
            simp = _simplify_closed(contour, tol)
            if len(simp) < 3:
                continue
            # map working-pixel coords → source-pixel coords
            nodes = [(x * inv, y * inv) for (x, y) in simp]
            out.append({'nodes': nodes, 'fill': fill, 'area': _poly_area(nodes)})
    out.sort(key=lambda d: d['area'], reverse=True)
    return out


class _CutoutView(QWidget):
    """The zoomable canvas inside Cutout Studio; forwards events to the dialog."""
    def __init__(self, dlg):
        super().__init__(); self.dlg = dlg
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, e): self.dlg._paint_view(self)
    def mousePressEvent(self, e): self.dlg._view_press(e)
    def mouseMoveEvent(self, e): self.dlg._view_move(e)
    def mouseReleaseEvent(self, e): self.dlg._view_release(e)


class ProfileCurve(QWidget):
    """A draggable width-multiplier curve for the Pressure Studio. X = position along the
    stroke (0..1), Y = width scale (0..1). Drag control points; double-click adds/removes.
    The top half shows the resulting ink-ribbon shape so the curve reads as a stroke."""
    def __init__(self, cp):
        super().__init__()
        self.cp = [list(q) for q in cp]
        self.setMinimumSize(300, 170); self.setMouseTracking(True)
        self.grab = None
    def set_points(self, cp):
        self.cp = sorted([list(q) for q in cp], key=lambda q: q[0]); self.update()
    def points(self):
        return [(round(p, 4), round(s, 4)) for p, s in sorted(self.cp, key=lambda q: q[0])]
    def _geo(self):
        m = 14; w = self.width() - 2 * m; h = self.height() - 2 * m; return m, w, h
    def _to_px(self, p, s):
        m, w, h = self._geo(); return QPointF(m + p * w, m + (1 - s) * h)
    def _from_px(self, x, y):
        m, w, h = self._geo()
        return max(0.0, min(1.0, (x - m) / (w or 1))), max(0.0, min(1.0, 1 - (y - m) / (h or 1)))
    def paintEvent(self, e):
        q = QPainter(self); q.setRenderHint(QPainter.Antialiasing)
        q.fillRect(self.rect(), QColor('#1b2228'))
        m, w, h = self._geo()
        cp = sorted(self.cp, key=lambda z: z[0])
        # ribbon preview (mirror the curve about a mid-line)
        midy = m + h * 0.5
        top = [QPointF(m + (i / 40) * w, midy - profile_value(cp, i / 40) * h * 0.42) for i in range(41)]
        bot = [QPointF(m + (i / 40) * w, midy + profile_value(cp, i / 40) * h * 0.42) for i in range(40, -1, -1)]
        q.setPen(Qt.NoPen); q.setBrush(QColor('#4cc2ff')); q.drawPolygon(QPolygonF(top + bot))
        # the curve itself + nodes
        q.setPen(QPen(QColor('#ffd54a'), 2))
        pts = [self._to_px(p, s) for p, s in cp]
        for i in range(len(pts) - 1): q.drawLine(pts[i], pts[i + 1])
        q.setBrush(QColor('#ffffff'))
        for pt in pts: q.drawEllipse(pt, 4, 4)
        q.end()
    def _hit(self, x, y):
        for i, (p, s) in enumerate(sorted(self.cp, key=lambda z: z[0])):
            pt = self._to_px(p, s)
            if (pt.x() - x) ** 2 + (pt.y() - y) ** 2 <= 49:
                return self.cp.index([p, s])
        return None
    def mousePressEvent(self, e):
        self.grab = self._hit(e.position().x(), e.position().y())
    def mouseMoveEvent(self, e):
        if self.grab is None: return
        p, s = self._from_px(e.position().x(), e.position().y())
        ends = sorted(self.cp, key=lambda z: z[0])
        g = self.cp[self.grab]
        if g is ends[0]: p = 0.0
        elif g is ends[-1]: p = 1.0
        g[0], g[1] = p, s; self.update()
    def mouseReleaseEvent(self, e): self.grab = None
    def mouseDoubleClickEvent(self, e):
        x, y = e.position().x(), e.position().y()
        i = self._hit(x, y)
        ends = sorted(self.cp, key=lambda z: z[0])
        if i is not None and self.cp[i] not in (ends[0], ends[-1]) and len(self.cp) > 2:
            del self.cp[i]
        else:
            p, s = self._from_px(x, y); self.cp.append([p, s])
        self.update()


class CutoutStudio(QDialog):
    """Extract the subject of a picture from its background — the DrawPlus Cutout Studio.

    Paint with the Discard (magic-wand flood), Keep and Erase brushes to build an alpha
    mask; the result is returned (OK) as a new RGBA image in ``self.result_rgba``."""
    WORK_MAX = 1200  # cap the working resolution so the flood fill stays snappy

    def __init__(self, parent, qimage):
        super().__init__(parent)
        import numpy as np
        self.setWindowTitle('Cutout Studio')
        self.result_rgba = None
        # decode + cap the working resolution
        w, h = qimage.width(), qimage.height()
        s = min(1.0, self.WORK_MAX / max(w, h))
        if s < 1.0:
            qimage = qimage.scaled(max(1, int(w * s)), max(1, int(h * s)),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.orig = qimage_to_rgba(qimage)                       # (H,W,4)
        self.rgb = self.orig[:, :, :3].astype(np.int32)
        H, W = self.orig.shape[:2]
        self.mask = np.where(self.orig[:, :, 3] > 8, np.uint8(255), np.uint8(0))
        self._undo = []
        self.mode = 'discard'
        self.brush = 24
        self.tol = 18
        self.feather = 1
        self.show_outline = True
        self.zoom = 1.0
        self._last = None

        root = QVBoxLayout(self)
        bar = QHBoxLayout(); root.addLayout(bar)
        self.mode_btns = {}
        for mid, lbl, tip in (('discard', 'Discard', 'Flood-remove the background you click on'),
                              ('keep', 'Keep', 'Paint back areas to keep'),
                              ('erase', 'Erase', 'Hand-erase stray areas')):
            b = QPushButton(lbl); b.setCheckable(True); b.setToolTip(tip)
            b.clicked.connect(lambda _=0, m=mid: self._set_mode(m))
            bar.addWidget(b); self.mode_btns[mid] = b
        self.mode_btns['discard'].setChecked(True)
        bar.addSpacing(12)
        bar.addWidget(QLabel('Brush:'))
        self.brush_sp = QSpinBox(); self.brush_sp.setRange(2, 200); self.brush_sp.setValue(self.brush)
        self.brush_sp.setSuffix(' px'); self.brush_sp.valueChanged.connect(lambda v: setattr(self, 'brush', v))
        bar.addWidget(self.brush_sp)
        bar.addWidget(QLabel('Grow tolerance:'))
        self.tol_sp = QSpinBox(); self.tol_sp.setRange(1, 100); self.tol_sp.setValue(self.tol)
        self.tol_sp.valueChanged.connect(lambda v: setattr(self, 'tol', v))
        bar.addWidget(self.tol_sp)
        self.outline_cb = QCheckBox('Show outline'); self.outline_cb.setChecked(True)
        self.outline_cb.toggled.connect(self._toggle_outline); bar.addWidget(self.outline_cb)
        bar.addStretch(1)
        undo_b = QPushButton('Undo'); undo_b.clicked.connect(self._undo_mask); bar.addWidget(undo_b)
        reset_b = QPushButton('Reset'); reset_b.clicked.connect(self._reset); bar.addWidget(reset_b)

        self.view = _CutoutView(self)
        self.scroll = QScrollArea(); self.scroll.setWidget(self.view)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet('QScrollArea{background:#5a5a5a;border:1px solid #888}')
        root.addWidget(self.scroll, 1)

        foot = QHBoxLayout(); root.addLayout(foot)
        foot.addWidget(QLabel('Zoom:'))
        self.zoom_sl = QSlider(Qt.Horizontal); self.zoom_sl.setRange(20, 400)
        self.zoom_sl.setFixedWidth(160); self.zoom_sl.valueChanged.connect(self._set_zoom_pct)
        foot.addWidget(self.zoom_sl)
        foot.addWidget(QLabel('Edge feather:'))
        self.feather_sp = QSpinBox(); self.feather_sp.setRange(0, 12); self.feather_sp.setValue(self.feather)
        self.feather_sp.valueChanged.connect(lambda v: setattr(self, 'feather', v))
        foot.addWidget(self.feather_sp)
        foot.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply cutout')
        bb.accepted.connect(self._accept); bb.rejected.connect(self.reject)
        foot.addWidget(bb)

        self.resize(860, 640)
        # fit to the available width once shown
        fit = max(0.2, min(2.0, 760 / max(1, W)))
        self.zoom_sl.setValue(int(round(fit * 100)))

    # ---- state helpers
    def _push_undo(self):
        self._undo.append(self.mask.copy())
        if len(self._undo) > 16: self._undo.pop(0)

    def _undo_mask(self):
        if self._undo:
            self.mask = self._undo.pop(); self.view.update()

    def _reset(self):
        import numpy as np
        self._push_undo()
        self.mask = np.where(self.orig[:, :, 3] > 8, np.uint8(255), np.uint8(0))
        self.view.update()

    def _set_mode(self, m):
        self.mode = m
        for mid, b in self.mode_btns.items(): b.setChecked(mid == m)

    def _toggle_outline(self, on):
        self.show_outline = on; self.view.update()

    def _set_zoom_pct(self, pct):
        self.zoom = pct / 100.0
        H, W = self.orig.shape[:2]
        self.view.setFixedSize(max(1, int(W * self.zoom)), max(1, int(H * self.zoom)))
        self.view.update()

    # ---- painting
    def _composite(self):
        """Build the display RGBA: original pixels, dimmed+checker where discarded."""
        import numpy as np
        H, W = self.orig.shape[:2]
        keep = self.mask > 0
        out = self.orig.copy()
        # checkerboard behind discarded pixels
        yy, xx = np.mgrid[0:H, 0:W]
        chk = (((xx // 8) + (yy // 8)) & 1).astype(np.uint8)
        board = np.where(chk[..., None] == 1, np.uint8(200), np.uint8(235))
        board = np.repeat(board, 3, axis=2)
        disc = ~keep
        out[disc, :3] = board[disc]
        out[:, :, 3] = 255
        if self.show_outline:
            edge = keep & ~(np.roll(keep, 1, 0) & np.roll(keep, -1, 0)
                            & np.roll(keep, 1, 1) & np.roll(keep, -1, 1))
            out[edge] = (255, 40, 40, 255)
        return out

    def _paint_view(self, view):
        qi = rgba_to_qimage(self._composite())
        p = QPainter(view)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1.0)
        p.drawImage(QRectF(0, 0, view.width(), view.height()), qi)
        p.end()

    def _view_xy(self, e):
        x = int(e.position().x() / self.zoom); y = int(e.position().y() / self.zoom)
        H, W = self.orig.shape[:2]
        return max(0, min(W - 1, x)), max(0, min(H - 1, y))

    def _view_press(self, e):
        if e.button() != Qt.LeftButton: return
        self._push_undo(); self._last = None
        self._apply_at(*self._view_xy(e)); self.view.update()

    def _view_move(self, e):
        if not (e.buttons() & Qt.LeftButton): return
        self._apply_at(*self._view_xy(e)); self.view.update()

    def _view_release(self, e):
        self._last = None

    # ---- brush application
    def _disc(self, cx, cy, value):
        import numpy as np
        r = max(1, self.brush // 2)
        H, W = self.mask.shape
        y0, y1 = max(0, cy - r), min(H, cy + r + 1)
        x0, x1 = max(0, cx - r), min(W, cx + r + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        self.mask[y0:y1, x0:x1][m] = value

    def _apply_at(self, x, y):
        if self.mode == 'keep':
            self._disc(x, y, 255)
        elif self.mode == 'erase':
            self._disc(x, y, 0)
        else:  # discard flood (magic wand) — only re-flood when crossing a new, still-kept pixel
            if self.mask[y, x] == 0: return
            if self._last is not None and self._last == (x, y): return
            self._last = (x, y)
            self._flood_discard(x, y)

    def _flood_discard(self, sx, sy):
        import numpy as np
        H, W = self.rgb.shape[:2]
        seed = self.rgb[sy, sx]
        thr = (self.tol / 100.0) * 441.673  # sqrt(3*255^2)
        d2 = ((self.rgb - seed) ** 2).sum(axis=2)
        similar = d2 <= (thr * thr)
        if not similar[sy, sx]: return
        out = np.zeros((H, W), bool)
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            free = similar[y] & ~out[y]
            if not free[x]: continue
            lf = np.nonzero(~free[:x])[0]
            xl = lf[-1] + 1 if lf.size else 0
            rf = np.nonzero(~free[x + 1:])[0]
            xr = x + rf[0] if rf.size else W - 1
            out[y, xl:xr + 1] = True
            for yy in (y - 1, y + 1):
                if 0 <= yy < H:
                    cand = similar[yy, xl:xr + 1] & ~out[yy, xl:xr + 1]
                    idx = np.nonzero(cand)[0]
                    if idx.size:
                        starts = idx[np.concatenate(([True], np.diff(idx) > 1))]
                        for st in starts: stack.append((xl + int(st), yy))
        self.mask[out] = 0

    # ---- result
    def _accept(self):
        import numpy as np
        keep = (self.mask > 0).astype(np.float32)
        if self.feather > 0:
            keep = _box_blur(keep, self.feather)
        alpha = np.clip(keep * (self.orig[:, :, 3].astype(np.float32)), 0, 255)
        out = self.orig.copy()
        out[:, :, 3] = alpha.astype(np.uint8)
        self.result_rgba = out
        self.accept()


class PhotoLabDialog(QDialog):
    """PhotoLab (ported from PAGEcreator): live Brightness/Contrast/Saturation/Sharpness/
    Warmth/Hue sliders over a before/after preview. OK → self.params holds the chosen
    adjustment; the caller runs apply_photolab() once at full resolution."""
    SLIDERS = [('brightness', 'Brightness', -100, 100), ('contrast', 'Contrast', -100, 100),
               ('saturation', 'Saturation', -100, 100), ('sharpness', 'Sharpness', -100, 200),
               ('temperature', 'Warmth', -100, 100), ('hue', 'Hue', -180, 180)]
    PREV_MAX = 320  # preview working size (full-res is applied only on OK)

    def __init__(self, parent, qimage):
        super().__init__(parent)
        self.setWindowTitle('PhotoLab — Adjust Picture')
        self.params = {k: 0 for k, _, _, _ in self.SLIDERS}
        w, h = qimage.width(), qimage.height()
        s = min(1.0, self.PREV_MAX / max(1, max(w, h)))
        if s < 1.0:
            qimage = qimage.scaled(max(1, int(w * s)), max(1, int(h * s)),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._before_q = qimage.convertToFormat(QImage.Format_ARGB32)
        self._prev_pil = _q2pil(self._before_q) if _HAS_PIL else None

        root = QVBoxLayout(self)
        pics = QHBoxLayout(); root.addLayout(pics)
        bcol = QVBoxLayout(); acol = QVBoxLayout(); pics.addLayout(bcol); pics.addLayout(acol)
        self._before_lbl = QLabel(); self._before_lbl.setAlignment(Qt.AlignCenter)
        self._after_lbl = QLabel(); self._after_lbl.setAlignment(Qt.AlignCenter)
        self._before_lbl.setPixmap(QPixmap.fromImage(self._before_q))
        bcol.addWidget(QLabel('<b>Before</b>', alignment=Qt.AlignCenter)); bcol.addWidget(self._before_lbl, 1)
        acol.addWidget(QLabel('<b>After</b>', alignment=Qt.AlignCenter)); acol.addWidget(self._after_lbl, 1)

        grid = QGridLayout(); root.addLayout(grid)
        self._sl = {}; self._val = {}
        for row, (key, name, lo, hi) in enumerate(self.SLIDERS):
            grid.addWidget(QLabel(name), row, 0)
            sl = QSlider(Qt.Horizontal); sl.setRange(lo, hi); sl.setValue(0); sl.setMinimumWidth(220)
            vl = QLabel('0'); vl.setMinimumWidth(34); vl.setAlignment(Qt.AlignRight)
            sl.valueChanged.connect(lambda v, k=key, l=vl: self._on_slide(k, v, l))
            grid.addWidget(sl, row, 1); grid.addWidget(vl, row, 2)
            self._sl[key] = sl; self._val[key] = vl

        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(90)
        self._timer.timeout.connect(self._render_preview)

        br = QHBoxLayout(); root.addLayout(br)
        reset = QPushButton('Reset'); reset.clicked.connect(self._reset); br.addWidget(reset); br.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); br.addWidget(bb)
        if not _HAS_PIL:
            bb.button(QDialogButtonBox.Ok).setEnabled(False)
            self._after_lbl.setText('Pillow not available')
        self._render_preview()

    def _on_slide(self, key, v, lbl):
        self.params[key] = v; lbl.setText(str(v)); self._timer.start()

    def _reset(self):
        for k, sl in self._sl.items(): sl.setValue(0)

    def _render_preview(self):
        if not _HAS_PIL or self._prev_pil is None: return
        try:
            out = apply_photolab(self._prev_pil, self.params)
            self._after_lbl.setPixmap(QPixmap.fromImage(_pil2q(out)))
        except Exception:
            self._after_lbl.setText('—')

    def is_identity(self):
        return not any(self.params.values())


# PDF publishing profiles (ported from PAGEcreator). Tuple: (label, img_cap_px, conformance).
# img_cap: down-rasterise embedded image objects to this longest-edge on export (None = leave full).
# conformance: advisory tag written into the PDF Title/Creator for the PDF/X-style profiles.
# These are HONEST approximations — no real CMYK conversion or embedded ICC; a RIP does the real work.
PDF_PROFILES = {
    'web':   ('Web / screen (RGB, images down-scaled)', 1600, ''),
    'print': ('Print (high quality, vector)',           None, ''),
    'x1a':   ('PDF/X-1a-style (press-ready)',           None, 'PDF/X-1a:2001 (approx — CMYK intent, no embedded ICC)'),
    'x3':    ('PDF/X-3-style (press-ready)',            None, 'PDF/X-3:2002 (approx — no embedded ICC)'),
}


class Main(QMainWindow):
    TOOLS = [('select', 'Select', '⬚'), ('node', 'Node (edit curves)', '⌇'),
             ('freehand', 'Freehand', '✎'), ('brush', 'Brush (pressure)', '🖌'), ('pen', 'Pen (Bézier curves)', '✐'),
             ('line', 'Line', '╱'), ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'),
             ('quick', 'QuickShape', '★'), ('text', 'Text', 'T'), ('image', 'Image', '🖻'),
             ('dim', 'Dimension line', '↔'), ('conn', 'Connector', '⌐'),
             ('perspective', 'Perspective (drag corners)', '◇'), ('envelope', 'Envelope (mesh warp)', '▦'),
             ('knife', 'Knife (cut shapes)', '🔪')]

    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, 'DRAWmaster')
        self.path = None
        self._pdf_profile = 'print'
        self.canvas = Canvas(self)
        self.load_bundled_fonts()
        sa = QScrollArea(); sa.setWidget(self.canvas); sa.setAlignment(Qt.AlignCenter)
        sa.setStyleSheet('QScrollArea{background:#cfd4da;border:none}')
        self.setCentralWidget(sa)
        self.build_menu(); self.build_tools()
        self.build_studio()
        self.setWindowTitle(APP); self.resize(1320, 860)
        self.pos_lbl = QLabel('  '); self.statusBar().addPermanentWidget(self.pos_lbl)
        self.refresh_layers(); self.sync_props()

    def load_bundled_fonts(self):
        """Register the display/script fonts shipped in fonts/ (shared with the rest of
        the just a... suite) so they're available desktop-wide."""
        from PySide6.QtGui import QFontDatabase
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(('.ttf', '.otf')):
                    QFontDatabase.addApplicationFont(os.path.join(d, fn))

    # ==================================================================== Studio docks
    # The right-hand "studio" mirrors the rest of the just a... suite: a Colour dock on
    # top, a tabified stack of property panels beneath it (Swatches / Line / Transparency
    # / Transform / Arrange / Styles / Layers / Text), and an Assets (clipart) dock on the
    # left. Everything is a QDockWidget, so the user can drag the splitter to resize, tear
    # a panel off, or re-tab it — exactly like PAGEdesigner & WEBcreator.
    def _dock(self, title, widget):
        d = QDockWidget(title, self)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable |
                      QDockWidget.DockWidgetClosable)
        d.setWidget(widget)
        return d

    def build_studio(self):
        self.d_colour = self._dock('Colour', self._colour_panel())
        self.d_swatch = self._dock('Swatches', self._swatch_panel())
        self.d_line   = self._dock('Line', self._line_panel())
        self.d_trans  = self._dock('Transparency', self._transparency_panel())
        self.d_xform  = self._dock('Transform', self._transform_panel())
        self.d_arr    = self._dock('Arrange', self._arrange_panel())
        self.d_styles = self._dock('Styles', self._styles_panel())
        self.d_layers = self._dock('Layers', self._layers_panel())
        self.d_fonts  = self._dock('Text', self._fonts_panel())
        self.layers_dock = self.d_layers           # kept for the View menu + older refs
        right = [self.d_colour, self.d_swatch, self.d_line, self.d_trans,
                 self.d_xform, self.d_arr, self.d_styles, self.d_layers, self.d_fonts]
        for d in right:
            self.addDockWidget(Qt.RightDockWidgetArea, d)
        # Colour sits on its own above the tabbed group
        self.splitDockWidget(self.d_colour, self.d_swatch, Qt.Vertical)
        for d in right[2:]:
            self.tabifyDockWidget(self.d_swatch, d)
        self.d_swatch.raise_()
        # Assets / clipart Gallery on the left (resizable), beside the tool palette
        self.d_assets = self._dock('Gallery', self._assets_panel())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.d_assets)
        try:
            self.resizeDocks([self.d_assets, self.d_colour], [210, 250], Qt.Horizontal)
            self.resizeDocks([self.d_colour], [150], Qt.Vertical)
        except Exception:
            pass

    def _panel(self):
        """A scrollable panel body with a tidy vertical layout."""
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(8, 8, 8, 8); v.setSpacing(6)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame); sa.setWidget(w)
        return sa, v

    # ---- Colour panel -------------------------------------------------------------
    def _colour_panel(self):
        sa, v = self._panel()
        grid = QGridLayout(); grid.setHorizontalSpacing(8)
        self.col_fill = QPushButton('Fill'); self.col_fill.setMinimumHeight(40)
        self.col_fill.clicked.connect(self.pick_fill)
        self.col_line = QPushButton('Line'); self.col_line.setMinimumHeight(40)
        self.col_line.clicked.connect(self.pick_stroke)
        swap = QToolButton(); swap.setText('⇄'); swap.setToolTip('Swap fill and line colours')
        swap.clicked.connect(self._swap_colours)
        nofill = QToolButton(); nofill.setText('⌀'); nofill.setToolTip('No fill (transparent)')
        nofill.clicked.connect(lambda: self._apply_colour(None, 'fill'))
        grid.addWidget(self.col_fill, 0, 0); grid.addWidget(self.col_line, 0, 1)
        grid.addWidget(swap, 0, 2); grid.addWidget(nofill, 0, 3)
        v.addLayout(grid)
        v.addWidget(QLabel('Recent'))
        self.recent_row = QHBoxLayout(); self.recent_row.setSpacing(3)
        self._recent_cols = []
        rw = QWidget(); rw.setLayout(self.recent_row); v.addWidget(rw)
        v.addStretch(1)
        return sa

    def _swap_colours(self):
        self.canvas.fill, self.canvas.stroke = self.canvas.stroke, self.canvas.fill
        o = self.canvas.sel
        if o:
            self.canvas.snapshot()
            o['fill'], o['stroke'] = o.get('stroke'), o.get('fill')
            self.canvas.update()
        self.sync_props()

    def _push_recent(self, hexcol):
        if not hexcol or hexcol in self._recent_cols: return
        self._recent_cols.insert(0, hexcol); self._recent_cols = self._recent_cols[:10]
        while self.recent_row.count():
            it = self.recent_row.takeAt(0); w = it.widget()
            if w: w.deleteLater()
        for c in self._recent_cols:
            b = QToolButton(); b.setFixedSize(20, 20)
            b.setStyleSheet(f'QToolButton{{background:{c};border:1px solid #777;border-radius:3px}}')
            b.clicked.connect(lambda _=0, col=c: self._apply_colour(col, self._swatch_target()))
            self.recent_row.addWidget(b)
        self.recent_row.addStretch(1)

    # ---- Swatches panel -----------------------------------------------------------
    def _swatch_panel(self):
        sa, v = self._panel()
        tgt = QHBoxLayout()
        self.sw_fill_rb = QRadioButton('Fill'); self.sw_fill_rb.setChecked(True)
        self.sw_line_rb = QRadioButton('Line')
        grp = QButtonGroup(self); grp.addButton(self.sw_fill_rb); grp.addButton(self.sw_line_rb)
        tgt.addWidget(QLabel('Apply to:')); tgt.addWidget(self.sw_fill_rb); tgt.addWidget(self.sw_line_rb); tgt.addStretch(1)
        v.addLayout(tgt)
        self.pal_cb = QComboBox(); self.pal_cb.addItems(list(SWATCH_PALETTES.keys()))
        self.pal_cb.currentTextChanged.connect(self._fill_swatch_grid)
        v.addWidget(self.pal_cb)
        self.swatch_host = QWidget(); self.swatch_grid = QGridLayout(self.swatch_host)
        self.swatch_grid.setSpacing(3); v.addWidget(self.swatch_host)
        v.addStretch(1)
        self._fill_swatch_grid('Standard')
        return sa

    def _swatch_target(self):
        return 'line' if getattr(self, 'sw_line_rb', None) and self.sw_line_rb.isChecked() else 'fill'

    def _fill_swatch_grid(self, name):
        while self.swatch_grid.count():
            it = self.swatch_grid.takeAt(0); w = it.widget()
            if w: w.deleteLater()
        cols = SWATCH_PALETTES.get(name, SWATCH_PALETTES['Standard'])
        for i, c in enumerate(cols):
            b = QToolButton(); b.setFixedSize(26, 26); b.setToolTip(c)
            b.setStyleSheet(f'QToolButton{{background:{c};border:1px solid #777;border-radius:3px}}')
            b.clicked.connect(lambda _=0, col=c: self._apply_colour(col, self._swatch_target()))
            self.swatch_grid.addWidget(b, i // 6, i % 6)

    def _apply_colour(self, hexcol, which):
        """Set the active fill/line colour and apply it to the current selection."""
        if which == 'fill':
            if hexcol: self.canvas.fill = QColor(hexcol)
            self.canvas.apply_to_sel(fill=hexcol if hexcol else '__none__')
        else:
            if hexcol: self.canvas.stroke = QColor(hexcol)
            self.canvas.apply_to_sel(stroke=hexcol if hexcol else '__none__')
        self._push_recent(hexcol)
        self.sync_props()

    # ---- Line panel ---------------------------------------------------------------
    def _line_panel(self):
        sa, v = self._panel()
        form = QFormLayout()
        self.ln_w = QSpinBox(); self.ln_w.setRange(0, 200); self.ln_w.setSuffix(' px')
        self.ln_w.setValue(self.canvas.sw); self.ln_w.valueChanged.connect(self.set_sw)
        self.ln_dash = QComboBox()
        for k, lbl in (('solid', 'Solid'), ('dash', 'Dashed'), ('dot', 'Dotted'), ('dashdot', 'Dash-dot')):
            self.ln_dash.addItem(lbl, k)
        self.ln_dash.activated.connect(lambda _=0: self._set_line_prop('dash', self.ln_dash.currentData()))
        self.ln_a0 = QComboBox(); self.ln_a1 = QComboBox()
        for cb in (self.ln_a0, self.ln_a1):
            for k, lbl in (('none', 'None'), ('arrow', 'Arrow'), ('dot', 'Dot')):
                cb.addItem(lbl, k)
        self.ln_a0.activated.connect(lambda _=0: self._set_arrows())
        self.ln_a1.activated.connect(lambda _=0: self._set_arrows())
        # calligraphic line style
        self.ln_calli = QCheckBox('Calligraphic nib')
        self.ln_calli.toggled.connect(self._set_calligraphic)
        self.ln_nib = QSpinBox(); self.ln_nib.setRange(0, 180); self.ln_nib.setSuffix('°'); self.ln_nib.setValue(45)
        self.ln_nib.valueChanged.connect(lambda v: self._set_line_prop('nib_angle', int(v)))
        form.addRow('Width:', self.ln_w); form.addRow('Style:', self.ln_dash)
        form.addRow('Start:', self.ln_a0); form.addRow('End:', self.ln_a1)
        form.addRow('', self.ln_calli); form.addRow('Nib angle:', self.ln_nib)
        v.addLayout(form); v.addStretch(1)
        return sa

    def _set_calligraphic(self, on):
        o = self.canvas.sel
        if o is None: return
        self.canvas.snapshot()
        for s in self.canvas._selection():
            if on:
                s['linestyle'] = 'calligraphic'
                s.setdefault('nib_angle', int(self.ln_nib.value()))
            else:
                s.pop('linestyle', None)
        self.canvas.update()

    def _set_line_prop(self, key, val):
        o = self.canvas.sel
        if o is None: return
        self.canvas.snapshot()
        for s in self.canvas._selection(): s[key] = val
        self.canvas.update()

    def _set_arrows(self):
        o = self.canvas.sel
        if o is None: return
        a0 = self.ln_a0.currentData(); a1 = self.ln_a1.currentData()
        start = a0 if a0 != 'none' else None; end = a1 if a1 != 'none' else None
        self.canvas.snapshot()
        for s in self.canvas._selection():
            s['arrow_start'] = start; s['arrow_end'] = end
            if start and end: s['arrow'] = 'both'
            elif end: s['arrow'] = 'end'
            elif start: s['arrow'] = 'start'
            else: s.pop('arrow', None)
        self.canvas.update()

    # ---- Transparency panel -------------------------------------------------------
    def _transparency_panel(self):
        sa, v = self._panel()
        v.addWidget(QLabel('Opacity'))
        row = QHBoxLayout()
        self.op_slider = QSlider(Qt.Horizontal); self.op_slider.setRange(0, 100); self.op_slider.setValue(100)
        self.op_slider.valueChanged.connect(self._op_changed)
        self.op_lbl = QLabel('100%'); self.op_lbl.setFixedWidth(42)
        row.addWidget(self.op_slider, 1); row.addWidget(self.op_lbl); v.addLayout(row)
        v.addWidget(QLabel('Blend mode'))
        self.blend_cb = QComboBox()
        for lbl, key, _css in BLEND_MODES: self.blend_cb.addItem(lbl, key)
        self.blend_cb.activated.connect(self._blend_changed)
        v.addWidget(self.blend_cb)
        v.addStretch(1)
        return sa

    def _op_changed(self, val):
        self.op_lbl.setText(f'{val}%')
        o = self.canvas.sel
        if o is None: return
        for s in self.canvas._selection():
            if val >= 100: s.pop('opacity', None)
            else: s['opacity'] = val / 100.0
        self.canvas.update()

    def _blend_changed(self, _i):
        key = self.blend_cb.currentData()
        o = self.canvas.sel
        if o is None: return
        self.canvas.snapshot()
        for s in self.canvas._selection():
            if key == 'SourceOver': s.pop('blend', None)
            else: s['blend'] = key
        self.canvas.update()

    # ---- Transform panel ----------------------------------------------------------
    def _transform_panel(self):
        sa, v = self._panel()
        form = QFormLayout()
        self.tf_x = QDoubleSpinBox(); self.tf_y = QDoubleSpinBox()
        self.tf_w = QDoubleSpinBox(); self.tf_h = QDoubleSpinBox()
        self.tf_r = QDoubleSpinBox()
        for s in (self.tf_x, self.tf_y, self.tf_w, self.tf_h):
            s.setRange(-10000, 10000); s.setSuffix(' px'); s.setDecimals(0)
        self.tf_w.setRange(1, 10000); self.tf_h.setRange(1, 10000)
        self.tf_r.setRange(-360, 360); self.tf_r.setSuffix('°'); self.tf_r.setDecimals(1)
        for s in (self.tf_x, self.tf_y, self.tf_w, self.tf_h, self.tf_r):
            s.editingFinished.connect(self._apply_transform)
        form.addRow('X:', self.tf_x); form.addRow('Y:', self.tf_y)
        form.addRow('Width:', self.tf_w); form.addRow('Height:', self.tf_h)
        form.addRow('Rotation:', self.tf_r)
        v.addLayout(form); v.addStretch(1)
        return sa

    def _apply_transform(self):
        o = self.canvas.sel
        if o is None: return
        r = obj_rect(o)
        nx, ny, nw, nh = self.tf_x.value(), self.tf_y.value(), self.tf_w.value(), self.tf_h.value()
        self.canvas.snapshot()
        # translate so the bounding box top-left lands on (nx, ny)
        self.canvas._shift_obj(o, nx - r.left(), ny - r.top())
        # then scale about that top-left to the requested size
        sx = nw / (r.width() or 1); sy = nh / (r.height() or 1)
        if abs(sx - 1) > 1e-6 or abs(sy - 1) > 1e-6:
            self.canvas._scale_obj(o, nx, ny, sx, sy)
        o['rot'] = self.tf_r.value() if abs(self.tf_r.value()) > 1e-6 else None
        if o['rot'] is None: o.pop('rot', None)
        self.canvas.update(); self.sync_props()

    # ---- Arrange panel ------------------------------------------------------------
    def _arrange_panel(self):
        sa, v = self._panel()
        def brow(items):
            row = QHBoxLayout()
            for txt, tip, slot in items:
                b = QPushButton(txt); b.setToolTip(tip); b.clicked.connect(slot); row.addWidget(b)
            v.addLayout(row)
        v.addWidget(QLabel('Order'))
        brow([('⤒', 'Bring to front', lambda: self.canvas.z_order('front')),
              ('↑', 'Bring forward', lambda: self.canvas.z_order('forward')),
              ('↓', 'Send backward', lambda: self.canvas.z_order('backward')),
              ('⤓', 'Send to back', lambda: self.canvas.z_order('back'))])
        v.addWidget(QLabel('Flip'))
        brow([('⇆ H', 'Flip horizontal', lambda: self.flip('h')),
              ('⇅ V', 'Flip vertical', lambda: self.flip('v'))])
        v.addWidget(QLabel('Align'))
        brow([('⊢', 'Align left', lambda: self.canvas.align_selection('left')),
              ('centre', 'Align centres', lambda: self.canvas.align_selection('hcenter')),
              ('⊣', 'Align right', lambda: self.canvas.align_selection('right'))])
        brow([('⊤', 'Align top', lambda: self.canvas.align_selection('top')),
              ('middle', 'Align middles', lambda: self.canvas.align_selection('vcenter')),
              ('⊥', 'Align bottom', lambda: self.canvas.align_selection('bottom'))])
        v.addWidget(QLabel('Distribute / group'))
        brow([('↔ dist', 'Distribute horizontally', lambda: self.canvas.distribute_selection('h')),
              ('↕ dist', 'Distribute vertically', lambda: self.canvas.distribute_selection('v'))])
        brow([('Group', 'Group selection', self.canvas.group_selection),
              ('Ungroup', 'Ungroup', self.canvas.ungroup_selection)])
        v.addStretch(1)
        return sa

    # ---- Styles panel -------------------------------------------------------------
    def _styles_panel(self):
        sa, v = self._panel()
        host = QWidget(); grid = QGridLayout(host); grid.setSpacing(6)
        for i, (name, st) in enumerate(DRAW_STYLES):
            b = QToolButton(); b.setToolTip(name); b.setIconSize(QSize(54, 40))
            b.setIcon(QIcon(self._style_thumb(st))); b.setAutoRaise(True)
            b.clicked.connect(lambda _=0, s=st: self._apply_style(s))
            grid.addWidget(b, i // 3, i % 3)
        v.addWidget(host); v.addStretch(1)
        return sa

    def _style_thumb(self, st):
        pm = QPixmap(56, 42); pm.fill(QColor('#f4f4f4'))
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(st['stroke']), min(6, st.get('sw', 2))) if st.get('stroke') else QPen(Qt.NoPen)
        if st.get('stroke') and st.get('dash', 'solid') != 'solid':
            apply_dash(pen, st['dash'])
        p.setPen(pen)
        p.setBrush(QColor(st['fill']) if st.get('fill') else Qt.NoBrush)
        p.drawRoundedRect(QRectF(8, 8, 40, 26), 5, 5); p.end()
        return pm

    def _apply_style(self, st):
        sel = self.canvas._selection()
        if not sel:
            QMessageBox.information(self, APP, 'Select one or more objects, then click a style to apply it.')
            return
        self.canvas.snapshot()
        for o in sel:
            o['fill'] = st.get('fill'); o['stroke'] = st.get('stroke')
            o['sw'] = st.get('sw', 2); o['dash'] = st.get('dash', 'solid')
        self.canvas.update(); self.sync_props()

    # ---- Layers panel (same controls as before, now a tab) ------------------------
    def _layers_panel(self):
        body = QWidget(); v = QVBoxLayout(body); v.setContentsMargins(6, 6, 6, 6)
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
        return body

    # ---- Text / Fonts panel -------------------------------------------------------
    def _fonts_panel(self):
        sa, v = self._panel()
        self.font_combo = GroupedFontCombo(); self.font_combo.setCurrentFamily('Noto Sans')
        self.font_combo.familyChanged.connect(self._font_apply)
        v.addWidget(QLabel('Font')); v.addWidget(self.font_combo)
        row = QHBoxLayout()
        self.font_size = QSpinBox(); self.font_size.setRange(4, 800); self.font_size.setSuffix(' px'); self.font_size.setValue(48)
        self.font_size.valueChanged.connect(self._font_apply)
        row.addWidget(QLabel('Size')); row.addWidget(self.font_size, 1); v.addLayout(row)
        bi = QHBoxLayout()
        self.font_bold = QToolButton(); self.font_bold.setText('B'); self.font_bold.setCheckable(True)
        self.font_italic = QToolButton(); self.font_italic.setText('I'); self.font_italic.setCheckable(True)
        self.font_bold.clicked.connect(self._font_apply); self.font_italic.clicked.connect(self._font_apply)
        bi.addWidget(self.font_bold); bi.addWidget(self.font_italic); bi.addStretch(1); v.addLayout(bi)
        addb = QPushButton('Add text…'); addb.clicked.connect(lambda: self._add_text_centre())
        v.addWidget(addb)
        v.addStretch(1)
        return sa

    def _add_text_centre(self):
        self.canvas.tool = 'text'
        self.place_text((self.canvas.W / 2 - 100, self.canvas.H / 2 - 30))

    def _font_apply(self, *a):
        o = self.canvas.sel
        if o is None or o.get('type') != 'text': return
        self.canvas.snapshot()
        o['family'] = self.font_combo.currentFamily()
        o['size'] = self.font_size.value()
        o['bold'] = self.font_bold.isChecked()
        o['italic'] = self.font_italic.isChecked()
        self.canvas.update()

    # ---- Assets / clipart Gallery (left dock) -------------------------------------
    def _assets_panel(self):
        sa, v = self._panel()
        v.addWidget(QLabel('Click a shape to drop it on the page:'))
        host = QWidget(); grid = QGridLayout(host); grid.setSpacing(5)
        for i, (key, label) in enumerate(QUICKSHAPES):
            b = QToolButton(); b.setToolTip(label); b.setIconSize(QSize(40, 40)); b.setAutoRaise(True)
            b.setIcon(QIcon(self._clip_thumb(key))); b.clicked.connect(lambda _=0, k=key: self._insert_clip(k))
            grid.addWidget(b, i // 3, i % 3)
        v.addWidget(host); v.addStretch(1)
        return sa

    def _clip_thumb(self, key):
        pm = QPixmap(44, 44); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#1f2a30'), 1.5)); p.setBrush(QColor('#cfe3ef'))
        p.translate(5, 5); p.drawPath(quickshape_path(key, 34, 34)); p.end()
        return pm

    def _insert_clip(self, key):
        c = self.canvas; c.snapshot()
        w = h = 160
        x = (c.W - w) / 2; y = (c.H - h) / 2
        o = dict(type='quick', shape=key, x=x, y=y, w=w, h=h,
                 fill=c.fill.name(), stroke=c.stroke.name(), sw=c.sw, layer=c.active_layer)
        if key in ADJUSTABLE_QS:
            param, _lbl, _lo, _hi, default = ADJUSTABLE_QS[key]
            o['qp'] = {param: default}
        c.objs.append(o); c.set_selection([o])
        c.tool = 'select'; self.tool_acts['select'].setChecked(True)
        c.update(); self.refresh_layers()

    # ---- keep the panels in step with the current selection -----------------------
    def _sync_studio(self):
        o = self.canvas.sel
        widgets = [getattr(self, n, None) for n in
                   ('op_slider', 'blend_cb', 'tf_x', 'tf_y', 'tf_w', 'tf_h', 'tf_r',
                    'ln_w', 'ln_dash', 'ln_calli', 'ln_nib', 'font_combo', 'font_size', 'font_bold', 'font_italic')]
        for w in widgets:
            if w is not None: w.blockSignals(True)
        try:
            if o is not None:
                if hasattr(self, 'op_slider'):
                    op = int(round(obj_opacity(o) * 100)); self.op_slider.setValue(op); self.op_lbl.setText(f'{op}%')
                if hasattr(self, 'blend_cb'):
                    key = o.get('blend', 'SourceOver')
                    idx = next((i for i in range(self.blend_cb.count()) if self.blend_cb.itemData(i) == key), 0)
                    self.blend_cb.setCurrentIndex(idx)
                if hasattr(self, 'tf_x'):
                    r = obj_rect(o)
                    self.tf_x.setValue(r.left()); self.tf_y.setValue(r.top())
                    self.tf_w.setValue(max(1, r.width())); self.tf_h.setValue(max(1, r.height()))
                    self.tf_r.setValue(obj_rot(o))
                if hasattr(self, 'ln_w'): self.ln_w.setValue(int(o.get('sw', 2)))
                if hasattr(self, 'ln_calli'):
                    self.ln_calli.setChecked(o.get('linestyle') == 'calligraphic')
                    self.ln_nib.setValue(int(o.get('nib_angle', 45)))
                if hasattr(self, 'font_combo') and o.get('type') == 'text':
                    self.font_combo.setCurrentFamily(o.get('family', 'Noto Sans'))
                    self.font_size.setValue(int(o.get('size', 48)))
                    self.font_bold.setChecked(bool(o.get('bold'))); self.font_italic.setChecked(bool(o.get('italic')))
        finally:
            for w in widgets:
                if w is not None: w.blockSignals(False)

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
        self.photolab_btn = QPushButton('PhotoLab…'); self.photolab_btn.setToolTip('PhotoLab — brightness/contrast/colour adjustments for the selected picture')
        self.photolab_btn.clicked.connect(self.photolab); top.addWidget(self.photolab_btn)
        self.cutout_btn = QPushButton('Cutout…'); self.cutout_btn.setToolTip('Cutout Studio — remove the background from the selected picture')
        self.cutout_btn.clicked.connect(self.cutout_studio); top.addWidget(self.cutout_btn)
        self.trace_btn = QPushButton('AutoTrace…'); self.trace_btn.setToolTip('AutoTrace / Vectorise — trace the selected picture into editable vector paths')
        self.trace_btn.clicked.connect(self.auto_trace); top.addWidget(self.trace_btn)
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
        if t != 'image':
            c.pending_image = None  # leaving the image tool drops any un-placed picture
        if t == 'node':
            # start editing whatever is selected, if it is (or can become) a node path
            c.node_obj = c.sel if (c.sel and c.sel.get('type') == 'nodes') else None
        else:
            c.node_obj = None; c.node_grab = None
        if t not in ('perspective', 'envelope'):
            c.warp_grab = None
        if t != 'knife':
            c.knife_line = None
        c.update()
        if t == 'image':
            self.begin_image_insert()

    def pick_quickshape(self, i):
        self.canvas.quick_shape = self.shape_cb.itemData(i)
        self.canvas.tool = 'quick'; self.tool_acts['quick'].setChecked(True)

    def roughen_dialog(self):
        """DrawPlus Roughen effect: perturb the selected shape(s)' outline into a jagged /
        rough node path. Amplitude = px of jitter, Detail = jitter points per 100px,
        Smoothness = 0 spiky … 100 flowing."""
        if not [o for o in self.canvas._selection()
                if o.get('type') in ('rect', 'ellipse', 'quick', 'line', 'poly', 'path', 'nodes')]:
            QMessageBox.information(self, APP, 'Select a shape first (the Select tool), then Roughen.')
            return
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        dlg = QDialog(self); dlg.setWindowTitle('Roughen'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        amp = QSpinBox(); amp.setRange(0, 200); amp.setSuffix(' px'); amp.setValue(10)
        det = QSpinBox(); det.setRange(1, 100); det.setValue(12)
        sm = QSpinBox(); sm.setRange(0, 100); sm.setSuffix(' %'); sm.setValue(0)
        form.addRow('Amplitude', amp); form.addRow('Detail (points / 100px)', det)
        form.addRow('Smoothness', sm)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        n = self.canvas.roughen_selection(float(amp.value()), float(det.value()), sm.value() / 100.0)
        if n:
            self.refresh_layers()

    def effects_dialog(self):
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first (the Select tool), then add effects.')
            return
        from PySide6.QtWidgets import QCheckBox, QFormLayout, QDialogButtonBox, QGroupBox
        s0 = o.get('shadow') or {}; g0 = o.get('glow') or {}
        r0 = o.get('reflect') or {}; f0 = o.get('feather') or {}; b0 = o.get('bevel') or {}
        dlg = QDialog(self); dlg.setWindowTitle('Effects — Shadow, Glow, Reflection, Feather & Bevel')
        lay = QVBoxLayout(dlg)
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
        # Reflection
        r_on = QCheckBox('Enable reflection'); r_on.setChecked(bool(o.get('reflect')))
        rop = QSpinBox(); rop.setRange(0, 100); rop.setSuffix(' %'); rop.setValue(int(r0.get('opacity', 50)))
        rfall = QSpinBox(); rfall.setRange(1, 100); rfall.setSuffix(' %'); rfall.setValue(int(r0.get('falloff', 60)))
        rgap = QSpinBox(); rgap.setRange(0, 100); rgap.setSuffix(' px'); rgap.setValue(int(r0.get('gap', 4)))
        rf_form = QFormLayout(); rg_box = QGroupBox('Reflection'); rg_box.setLayout(rf_form)
        rf_form.addRow('', r_on); rf_form.addRow('Strength:', rop)
        rf_form.addRow('Fade over:', rfall); rf_form.addRow('Gap:', rgap); lay.addWidget(rg_box)
        # Feather
        f_on = QCheckBox('Enable soft (feathered) edges'); f_on.setChecked(bool(o.get('feather')))
        frad = QSpinBox(); frad.setRange(1, 60); frad.setSuffix(' px'); frad.setValue(int(f0.get('radius', 6)))
        ff_form = QFormLayout(); fg_box = QGroupBox('Feather'); fg_box.setLayout(ff_form)
        ff_form.addRow('', f_on); ff_form.addRow('Radius:', frad); lay.addWidget(fg_box)
        # Bevel
        b_on = QCheckBox('Enable bevel / emboss'); b_on.setChecked(bool(o.get('bevel')))
        bdep = QSpinBox(); bdep.setRange(1, 40); bdep.setSuffix(' px'); bdep.setValue(int(b0.get('depth', 4)))
        bsoft = QSpinBox(); bsoft.setRange(0, 40); bsoft.setSuffix(' px'); bsoft.setValue(int(b0.get('soft', 2)))
        blight = QSpinBox(); blight.setRange(0, 100); blight.setSuffix(' %'); blight.setValue(int(b0.get('light', 70)))
        bdir = QSpinBox(); bdir.setRange(0, 360); bdir.setSuffix('°'); bdir.setValue(int(b0.get('dir', 135)))
        bf_form = QFormLayout(); bg_box = QGroupBox('Bevel / Emboss'); bg_box.setLayout(bf_form)
        bf_form.addRow('', b_on); bf_form.addRow('Depth:', bdep); bf_form.addRow('Softness:', bsoft)
        bf_form.addRow('Light strength:', blight); bf_form.addRow('Light angle:', bdir); lay.addWidget(bg_box)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        o['shadow'] = {'dx': sdx.value(), 'dy': sdy.value(), 'blur': sbl.value(),
                       'opacity': sop.value(), 'color': scol[0]} if s_on.isChecked() else None
        o['glow'] = {'blur': gbl.value(), 'opacity': gop.value(), 'color': gcol[0]} if g_on.isChecked() else None
        o['reflect'] = {'opacity': rop.value(), 'falloff': rfall.value(), 'gap': rgap.value()} if r_on.isChecked() else None
        o['feather'] = {'radius': frad.value()} if f_on.isChecked() else None
        o['bevel'] = {'depth': bdep.value(), 'soft': bsoft.value(),
                      'light': blight.value(), 'dir': bdir.value()} if b_on.isChecked() else None
        for k in ('shadow', 'glow', 'reflect', 'feather', 'bevel'):
            if not o.get(k): o.pop(k, None)
        self.canvas.update()

    # ---------------------------------------------------------------- Distort (Perspective / Envelope)
    def add_perspective(self):
        """Give the selected object a (fresh identity) perspective and switch to the tool
        so its corner handles are ready to drag."""
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first, then add a perspective.')
            return
        self.canvas.snapshot()
        if not o.get('perspective'):
            o['perspective'] = default_perspective()
        self.set_tool('perspective'); self.tool_acts['perspective'].setChecked(True)
        self.canvas.update()

    def reset_perspective(self):
        o = self.canvas.sel
        if o is not None and o.get('perspective'):
            self.canvas.snapshot(); o.pop('perspective', None); self.canvas.update()

    def add_envelope(self, preset='reset'):
        """Apply an envelope preset to the selected object (preset='reset' adds a flat 2×2
        identity mesh ready to drag) and switch to the Envelope tool."""
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first, then add an envelope.')
            return
        self.canvas.snapshot()
        if preset == 'reset':
            o['envelope'] = default_envelope()
        else:
            env = envelope_preset(preset)
            if env is not None: o['envelope'] = env
        self.set_tool('envelope'); self.tool_acts['envelope'].setChecked(True)
        self.canvas.update()

    def reset_envelope(self):
        o = self.canvas.sel
        if o is not None and o.get('envelope'):
            self.canvas.snapshot(); o.pop('envelope', None); self.canvas.update()

    # ---------------------------------------------------------------- Pressure Studio
    def pressure_studio(self):
        """Pick a pressure profile for the selected brush stroke(s), or set the default for
        new strokes. A preset dropdown loads a draggable curve; the curve edits a Custom
        profile. Applies profile reshaping live (draw_brush multiplies widths by the curve)."""
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox, QGroupBox
        sel = [s for s in self.canvas._selection() if s.get('type') == 'brush']
        o = sel[0] if sel else None
        cur = o.get('profile') if o else getattr(self.canvas, 'brush_profile', None)
        # resolve current profile to (name, control-points)
        if isinstance(cur, dict):
            name0 = cur.get('name', 'Constant'); cp0 = profile_points(cur)
        elif isinstance(cur, str):
            name0 = cur; cp0 = profile_points(cur)
        else:
            name0 = 'Constant'; cp0 = PROFILE_PRESETS['Constant']
        dlg = QDialog(self); dlg.setWindowTitle('Pressure Studio — stroke width profile')
        lay = QVBoxLayout(dlg)
        if not sel:
            lay.addWidget(QLabel('No brush stroke selected — this sets the default profile '
                                 'for new brush strokes.'))
        preset = QComboBox()
        for nm in PROFILE_NAMES: preset.addItem(nm, nm)
        preset.setCurrentIndex(PROFILE_NAMES.index(name0) if name0 in PROFILE_NAMES else 0)
        curve = ProfileCurve(cp0)
        form = QFormLayout(); form.addRow('Preset:', preset); lay.addLayout(form)
        lay.addWidget(QLabel('Width along stroke (drag points; double-click adds / removes):'))
        lay.addWidget(curve)
        def load_preset(_i=0):
            nm = preset.currentData()
            if nm != 'Custom':
                curve.set_points(PROFILE_PRESETS.get(nm, PROFILE_PRESETS['Constant']))
        preset.activated.connect(load_preset)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        nm = preset.currentData()
        if nm == 'Custom':
            prof = {'name': 'Custom', 'pts': [list(q) for q in curve.points()]}
        else:
            prof = {'name': nm}
        if sel:
            self.canvas.snapshot()
            for s in sel:
                s['profile'] = copy.deepcopy(prof)
                if s.get('widths') and s.get('pts'):   # bake nothing — draw_brush applies live
                    pass
            self.canvas.update()
        else:
            self.canvas.brush_profile = copy.deepcopy(prof)
        # also remember as the default for new strokes
        self.canvas.brush_profile = copy.deepcopy(prof)

    # ---------------------------------------------------------------- text (artistic)
    def _text_dialog(self, text='Text', family=None, size=48, title='Add Text'):
        """Collect the string, font family (bundled + system fonts) and pixel size.
        Returns (text, family, size) or None if cancelled."""
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        dlg = QDialog(self); dlg.setWindowTitle(title); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        te = QLineEdit(text); te.setMinimumWidth(240)
        fc = GroupedFontCombo(); fc.setCurrentFamily(family or 'Noto Sans')
        sz = QSpinBox(); sz.setRange(4, 800); sz.setSuffix(' px'); sz.setValue(int(size))
        form.addRow('Text:', te); form.addRow('Font:', fc); form.addRow('Size:', sz)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return None
        s = te.text() or 'Text'
        return s, fc.currentFamily(), sz.value()

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
    def _pick_image_file(self):
        """Prompt for a picture and return (data-URI, native_w, native_h) or None."""
        path, _ = QFileDialog.getOpenFileName(self, 'Insert Picture', _just_dir('pics'),
                                              'Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff);;All files (*)')
        if not path:
            return None
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP, 'Could not read that image file.'); return None
        try:
            uri = image_data_uri(path)
        except OSError:
            QMessageBox.warning(self, APP, 'Could not read that image file.'); return None
        return uri, img.width() or 1, img.height() or 1

    def _add_image_obj(self, uri, nw, nh, x, y, dw, dh):
        """Create and select an image object (shared by every insert path)."""
        self.canvas.snapshot()
        o = dict(type='image', x=x, y=y, w=dw, h=dh, src=uri, stroke=None, sw=0,
                 fill=None, layer=self.canvas.active_layer)
        self.canvas.objs.append(o); self.canvas.set_selection([o])
        self.canvas.update(); self.refresh_layers()
        return o

    def import_image(self, at=None):
        """Insert Picture from the menu — place it centred at a sensible fitted size.
        The file is embedded as a data-URI so the drawing (and its SVG) stays self-contained."""
        picked = self._pick_image_file()
        if not picked:
            self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True); return
        uri, w, h = picked
        maxw, maxh = self.canvas.W * 0.8, self.canvas.H * 0.8
        s = min(1.0, maxw / w, maxh / h)
        dw, dh = w * s, h * s
        x = at[0] if at else (self.canvas.W - dw) / 2
        y = at[1] if at else (self.canvas.H - dh) / 2
        self._add_image_obj(uri, w, h, x, y, dw, dh)
        self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True)

    def begin_image_insert(self):
        """Image tool: pick the file first, then let the user click (native size) or
        click-drag (custom size) on the canvas to place it — the DrawPlus flow."""
        picked = self._pick_image_file()
        if not picked:
            self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True); return
        uri, w, h = picked
        self.canvas.pending_image = dict(uri=uri, w=w, h=h)
        self.statusBar().showMessage('Click to place the picture, or drag to set its size.', 6000)

    def place_pending_image(self, start, end):
        """Drop the pending picture: a plain click = fitted native size centred on the
        click; a drag = fit inside the dragged rectangle (aspect preserved)."""
        pend = self.canvas.pending_image
        if not pend: return
        self.canvas.pending_image = None
        uri, w, h = pend['uri'], pend['w'], pend['h']
        dx, dy = abs(end[0] - start[0]), abs(end[1] - start[1])
        if dx > 4 and dy > 4:
            s = min(dx / w, dy / h)
            dw, dh = w * s, h * s
            x, y = min(start[0], end[0]), min(start[1], end[1])
        else:
            maxw, maxh = self.canvas.W * 0.8, self.canvas.H * 0.8
            s = min(1.0, maxw / w, maxh / h)
            dw, dh = w * s, h * s
            x, y = start[0] - dw / 2, start[1] - dh / 2
        self._add_image_obj(uri, w, h, x, y, dw, dh)
        self.canvas.tool = 'select'; self.tool_acts['select'].setChecked(True)

    def _selected_image(self, verb):
        """Return the selected image object, or warn and return None."""
        o = self.canvas.sel
        if o is None or o.get('type') != 'image':
            QMessageBox.information(self, APP, f'Select a picture first, then {verb}.')
            return None
        return o

    def cutout_studio(self):
        """Open Cutout Studio on the selected picture; apply the alpha cutout on OK."""
        o = self._selected_image('open Cutout Studio')
        if o is None: return
        qi = obj_image(o)
        if qi.isNull():
            QMessageBox.warning(self, APP, 'Could not read that picture.'); return
        dlg = CutoutStudio(self, qi)
        if not dlg.exec() or dlg.result_rgba is None: return
        import io, base64
        from PIL import Image
        buf = io.BytesIO()
        Image.fromarray(dlg.result_rgba, 'RGBA').save(buf, 'PNG')
        uri = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
        self.canvas.snapshot()
        _IMG_CACHE.pop(o.get('src', ''), None)
        o['src'] = uri
        self.canvas.update(); self.statusBar().showMessage('Cutout applied.', 4000)

    def photolab(self):
        """Open PhotoLab on the selected picture; apply the full-res adjustment on OK,
        writing the result back as a new data-URI src (same mechanism as cutout_studio)."""
        if not _HAS_PIL:
            QMessageBox.information(self, APP, 'PhotoLab needs the Pillow library '
                                   '(e.g. sudo pacman -S python-pillow). Or use Edit in PAINTcanvas.')
            return
        o = self._selected_image('open PhotoLab')
        if o is None: return
        qi = obj_image(o)
        if qi.isNull():
            QMessageBox.warning(self, APP, 'Could not read that picture.'); return
        dlg = PhotoLabDialog(self, qi)
        if not dlg.exec() or dlg.is_identity(): return
        try:
            import base64
            out = _pil2q(apply_photolab(_q2pil(qi), dlg.params))   # full-res, once
            ba = QByteArray(); buf = QBuffer(ba); buf.open(QBuffer.WriteOnly); out.save(buf, 'PNG'); buf.close()
            uri = 'data:image/png;base64,' + bytes(ba.toBase64()).decode()
            self.canvas.snapshot()
            _IMG_CACHE.pop(o.get('src', ''), None)
            o['src'] = uri
            self.canvas.update(); self.statusBar().showMessage('PhotoLab adjustment applied.', 4000)
        except Exception as ex:
            QMessageBox.warning(self, APP, f'Could not apply PhotoLab:\n{ex}')

    def replace_image(self):
        """Swap the selected picture's source for another file, keeping its frame."""
        o = self._selected_image('Replace Picture')
        if o is None: return
        picked = self._pick_image_file()
        if not picked: return
        uri, _w, _h = picked
        self.canvas.snapshot()
        _IMG_CACHE.pop(o.get('src', ''), None)
        o['src'] = uri
        self.canvas.update()

    # ---------------------------------------------------------------- AutoTrace / Vectorise
    def _autotrace_core(self, o, mode, n_colors, tol, min_area, keep):
        """GUI-free core: trace image object ``o`` and append the resulting node-paths to the
        canvas (grouped, registered over the image). Returns the list of new node objects.
        ``keep`` leaves the original picture in place; otherwise it is removed."""
        qi = obj_image(o)
        if qi.isNull():
            return []
        rgba = qimage_to_rgba(qi)
        src_h, src_w = rgba.shape[:2]
        regions = trace_image(rgba, mode=mode, n_colors=n_colors, tol=tol, min_area=min_area)
        if not regions:
            return []
        # source-pixel → canvas: scale by object w/h ÷ source size, offset by object x/y
        sx = o['w'] / max(1, src_w); sy = o['h'] / max(1, src_h)
        ox, oy = o['x'], o['y']; lyr = o.get('layer', self.canvas.active_layer)
        gid = self.canvas._next_gid; self.canvas._next_gid += 1
        new = []
        for reg in regions:  # already back-to-front (largest first)
            nodes = [dict(x=ox + px * sx, y=oy + py * sy, hin=[0.0, 0.0], hout=[0.0, 0.0],
                          smooth=False) for (px, py) in reg['nodes']]
            no = dict(type='nodes', nodes=nodes, closed=True, stroke=None, sw=0,
                      fill=reg['fill'], layer=lyr, gid=gid)
            new.append(no)
        idx = self.canvas.objs.index(o) if o in self.canvas.objs else len(self.canvas.objs)
        if keep:
            for k, no in enumerate(new):
                self.canvas.objs.insert(idx + 1 + k, no)
        else:
            self.canvas.objs.pop(idx)
            _IMG_CACHE.pop(o.get('src', ''), None)
            for k, no in enumerate(new):
                self.canvas.objs.insert(idx + k, no)
        return new

    def auto_trace(self):
        """Trace the selected picture into editable vector paths — the DrawPlus AutoTrace."""
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox, QGroupBox
        o = self._selected_image('AutoTrace / Vectorise')
        if o is None: return
        if obj_image(o).isNull():
            QMessageBox.warning(self, APP, 'Could not read that picture.'); return
        dlg = QDialog(self); dlg.setWindowTitle('AutoTrace / Vectorise')
        v = QVBoxLayout(dlg); form = QFormLayout()
        mode_cb = QComboBox()
        mode_cb.addItem('Black & White', 'bw')
        mode_cb.addItem('Logo / flat colour', 'logo')
        mode_cb.addItem('Photo', 'photo')
        mode_cb.setCurrentIndex(1)
        form.addRow('Mode:', mode_cb)
        cols = QSpinBox(); cols.setRange(2, 64); cols.setValue(6)
        form.addRow('Colours:', cols)
        detail = QSlider(Qt.Horizontal); detail.setRange(0, 100); detail.setValue(60)
        detail.setToolTip('Higher = more detail (less smoothing)')
        form.addRow('Detail:', detail)
        minspeck = QSpinBox(); minspeck.setRange(0, 5000); minspeck.setValue(16); minspeck.setSuffix(' px²')
        form.addRow('Min. region:', minspeck)
        v.addLayout(form)
        keep_cb = QCheckBox('Keep the original picture underneath'); keep_cb.setChecked(False)
        v.addWidget(keep_cb)
        def _sync():
            m = mode_cb.currentData()
            cols.setEnabled(m != 'bw')
            if m == 'photo' and cols.value() < 16: cols.setValue(16)
            elif m == 'logo' and cols.value() > 12: cols.setValue(6)
        mode_cb.currentIndexChanged.connect(_sync); _sync()
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Trace')
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not dlg.exec(): return
        mode = mode_cb.currentData()
        n_colors = cols.value()
        # detail 0..100 → tolerance ~6..0.3 px (more detail = smaller tolerance)
        tol = 0.3 + (100 - detail.value()) / 100.0 * 5.7
        min_area = minspeck.value()
        keep = keep_cb.isChecked()
        self.canvas.snapshot()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            new = self._autotrace_core(o, mode, n_colors, tol, min_area, keep)
        finally:
            QApplication.restoreOverrideCursor()
        if not new:
            QMessageBox.information(self, APP, 'AutoTrace produced no regions — try fewer '
                                    'colours or a smaller minimum region.'); return
        self.canvas.set_selection(new); self.canvas.update(); self.refresh_layers()
        self.statusBar().showMessage(f'AutoTrace: {len(new)} path(s) created.', 4000)

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
        """Linear or radial gradient fill for the selected shape — a multi-stop colour ramp
        (grad['stops']=[{pos,color}]) plus type + angle. Add/remove/reposition stops. Writes
        back a 2-colour c1/c2 pair too so older DRAWmaster builds still render. Cleared via Remove."""
        o = self.canvas.sel
        if o is None or o.get('type') not in ('rect', 'ellipse', 'quick', 'poly', 'nodes', 'text'):
            QMessageBox.information(self, APP, 'Select a shape first (rectangle, ellipse, QuickShape, '
                                   'a closed pen shape or text), then add a gradient fill.')
            return
        from PySide6.QtWidgets import (QFormLayout, QDialogButtonBox, QGroupBox, QScrollArea,
                                       QWidget, QHBoxLayout, QDoubleSpinBox)
        g0 = o.get('grad') or {}
        dlg = QDialog(self); dlg.setWindowTitle('Gradient Fill'); dlg.setMinimumWidth(360)
        lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        kind = QComboBox(); kind.addItem('Linear', 'linear'); kind.addItem('Radial', 'radial')
        kind.setCurrentIndex(1 if g0.get('type') == 'radial' else 0)
        ang = QSpinBox(); ang.setRange(0, 360); ang.setSuffix('°'); ang.setValue(int(g0.get('angle', 90)))
        form.addRow('Type:', kind); form.addRow('Angle (linear):', ang)
        # Stop editor — one row per stop: position + colour + remove.
        stops = [dict(pos=p, color=c) for p, c in grad_stops(g0)] if g0 else \
                [dict(pos=0.0, color='#ffd54a'), dict(pos=1.0, color='#2a7d6b')]
        box = QGroupBox('Colour stops'); bl = QVBoxLayout(box)
        rows_host = QWidget(); rows_lay = QVBoxLayout(rows_host); rows_lay.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(rows_host); lay.addWidget(box)
        def tint(btn, holder):
            c = QColor(holder[0]); btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')
        def rebuild():
            while rows_lay.count():
                it = rows_lay.takeAt(0); w = it.widget()
                if w: w.setParent(None)
            for i, st in enumerate(stops):
                row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0, 0, 0, 0)
                pos = QDoubleSpinBox(); pos.setRange(0.0, 1.0); pos.setSingleStep(0.05); pos.setDecimals(2)
                pos.setValue(float(st['pos']))
                pos.valueChanged.connect(lambda v, s=st: s.__setitem__('pos', v))
                holder = [st['color']]; cb = QPushButton('Colour')
                def mkpick(h, b, s):
                    def go():
                        c = QColorDialog.getColor(QColor(h[0]), self, 'Gradient colour')
                        if c.isValid(): h[0] = c.name(); s['color'] = c.name(); tint(b, h)
                    return go
                cb.clicked.connect(mkpick(holder, cb, st)); tint(cb, holder)
                rm = QPushButton('✕'); rm.setFixedWidth(28); rm.setEnabled(len(stops) > 2)
                def mkremove(s):
                    def go():
                        if len(stops) > 2: stops.remove(s); rebuild()
                    return go
                rm.clicked.connect(mkremove(st))
                rl.addWidget(QLabel(f'{i + 1}.')); rl.addWidget(pos, 1); rl.addWidget(cb, 1); rl.addWidget(rm)
                rows_lay.addWidget(row)
        rebuild()
        add = QPushButton('Add stop')
        def add_stop():
            stops.append(dict(pos=0.5, color='#ffffff')); rebuild()
        add.clicked.connect(add_stop); bl.addWidget(add)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        rm = QPushButton('Remove gradient'); bb.addButton(rm, QDialogButtonBox.ResetRole)
        rm.clicked.connect(lambda: (self._remove_gradient(o), dlg.reject()))
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        ss = sorted(({'pos': max(0.0, min(1.0, float(s['pos']))), 'color': s['color']} for s in stops),
                    key=lambda s: s['pos'])
        o['grad'] = {'stops': ss, 'c1': ss[0]['color'], 'c2': ss[-1]['color'],
                     'angle': ang.value(), 'type': kind.currentData()}
        self.canvas.update()

    def _remove_gradient(self, o):
        if o.get('grad'):
            self.canvas.snapshot(); o.pop('grad', None); self.canvas.update()

    # ---------------------------------------------------------------- transparency gradient
    def transparency_gradient_dialog(self):
        """A linear alpha fade across the selected object (o['agrad']), start→end opacity
        across an angle; composes with the flat opacity. Ported from PAGEcreator. Remove
        clears it. Works on any fillable object."""
        o = self.canvas.sel
        if o is None:
            QMessageBox.information(self, APP, 'Select an object first (the Select tool), then add a transparency gradient.')
            return
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        a0 = o.get('agrad') or {}
        dlg = QDialog(self); dlg.setWindowTitle('Transparency Gradient'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        ang = QSpinBox(); ang.setRange(0, 360); ang.setSuffix('°'); ang.setValue(int(a0.get('angle', 0)))
        a1 = QSpinBox(); a1.setRange(0, 100); a1.setSuffix(' %'); a1.setValue(int(a0.get('a1', 100)))
        a2 = QSpinBox(); a2.setRange(0, 100); a2.setSuffix(' %'); a2.setValue(int(a0.get('a2', 0)))
        form.addRow(QLabel('Fades the object across the angle, from the start opacity to the end opacity.'))
        form.addRow('Angle:', ang); form.addRow('Start opacity:', a1); form.addRow('End opacity:', a2)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        rm = QPushButton('Remove'); bb.addButton(rm, QDialogButtonBox.ResetRole)
        rm.clicked.connect(lambda: (self._remove_agrad(o), dlg.reject()))
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        self.canvas.snapshot()
        o['agrad'] = {'type': 'linear', 'angle': ang.value(), 'a1': a1.value(), 'a2': a2.value()}
        self.canvas.update()

    def _remove_agrad(self, o):
        if o.get('agrad'):
            self.canvas.snapshot(); o.pop('agrad', None); self.canvas.update()

    # ---------------------------------------------------------------- texture / pattern fill
    def _scan_texture_lib(self):
        """Return {category: [paths]} for the user's local texture library, if present.
        Scanned live from ~/.local/share/justapps/textures — never copied into the app."""
        lib = {}
        if not os.path.isdir(TEXTURE_LIB):
            return lib
        try:
            for cat in sorted(os.listdir(TEXTURE_LIB)):
                cd = os.path.join(TEXTURE_LIB, cat)
                if not os.path.isdir(cd):
                    continue
                files = sorted(os.path.join(cd, fn) for fn in os.listdir(cd)
                               if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')))
                if files:
                    lib[cat] = files
        except OSError:
            pass
        return lib

    def texture_fill_dialog(self):
        """Fill the selected shape with a tiled or stretched image — chosen from a file, or
        from the user's local texture library (15 categories). Stored on the object as a
        self-contained data-URI (o['texfill']) so it round-trips through the SVG."""
        o = self.canvas.sel
        if o is None or o.get('type') not in ('rect', 'ellipse', 'quick', 'poly', 'nodes', 'path'):
            QMessageBox.information(self, APP, 'Select a shape first (rectangle, ellipse, QuickShape or a '
                                   'closed pen shape), then add a texture or pattern fill.')
            return
        from PySide6.QtWidgets import QFormLayout, QDialogButtonBox
        lib = self._scan_texture_lib()
        dlg = QDialog(self); dlg.setWindowTitle('Texture / Pattern Fill'); lay = QVBoxLayout(dlg)
        form = QFormLayout(); lay.addLayout(form)
        cat = QComboBox(); pic = QComboBox()
        cat.addItem('(choose a file…)', None)
        for c in lib: cat.addItem(c, c)
        def refill(_i=0):
            pic.clear(); key = cat.currentData()
            if key and key in lib:
                for f in lib[key]: pic.addItem(os.path.basename(f), f)
            pic.setEnabled(pic.count() > 0)
        cat.activated.connect(refill); refill()
        mode = QComboBox(); mode.addItem('Tile (repeat)', 'tile'); mode.addItem('Stretch to fit', 'stretch')
        cur = o.get('texfill') or {}
        mode.setCurrentIndex(1 if cur.get('mode') == 'stretch' else 0)
        chosen = ['']; browse = QPushButton('Browse for an image file…')
        def do_browse():
            path, _ = QFileDialog.getOpenFileName(self, 'Pick a texture image', _just_dir('pics'),
                                                  'Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All files (*)')
            if path: chosen[0] = path; browse.setText(os.path.basename(path))
        browse.clicked.connect(do_browse)
        form.addRow('Library category:', cat); form.addRow('Texture:', pic)
        form.addRow('Or a file:', browse); form.addRow('Fill mode:', mode)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        rm = QPushButton('Remove texture'); bb.addButton(rm, QDialogButtonBox.ResetRole)
        rm.clicked.connect(lambda: (self._remove_texfill(o), dlg.reject()))
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); lay.addWidget(bb)
        if not dlg.exec(): return
        src = chosen[0] or (pic.currentData() if pic.isEnabled() else '')
        if not src:
            QMessageBox.information(self, APP, 'No image was chosen for the texture fill.')
            return
        try:
            uri = image_data_uri(src)
        except OSError:
            QMessageBox.warning(self, APP, 'Could not read that image file.'); return
        self.canvas.snapshot()
        o['texfill'] = {'src': uri, 'mode': mode.currentData()}
        o.pop('grad', None)   # a texture replaces any gradient
        self.canvas.update()

    def _remove_texfill(self, o):
        if o.get('texfill'):
            self.canvas.snapshot(); o.pop('texfill', None); self.canvas.update()

    # ---------------------------------------------------------------- fit text to a path
    def fit_text_to_path(self):
        """Attach a selected artistic-text object to a selected path/curve so its glyphs
        flow along it. Expects exactly one text object and one line/path/node object in the
        selection (or a selected text object and the top-most path beneath it)."""
        sel = self.canvas._selection()
        txt = next((o for o in sel if o.get('type') == 'text'), None)
        path = next((o for o in sel if o.get('type') in ('line', 'path', 'poly', 'nodes')), None)
        if txt is None:
            QMessageBox.information(self, APP, 'Select an artistic-text object and a line, freehand/pen path '
                                   'or node path, then Fit Text to Path.')
            return
        if path is None:
            QMessageBox.information(self, APP, 'Also select the line, path or curve for the text to follow '
                                   '(Shift-click to add it to the selection).')
            return
        pts = self._path_polyline(path)
        if len(pts) < 2:
            QMessageBox.information(self, APP, 'That path is too short to flow text along.')
            return
        self.canvas.snapshot()
        txt['pathpts'] = pts
        self.canvas.set_selection([txt]); self.canvas.update()

    def _path_polyline(self, o, samples=120):
        """A polyline [(x,y), …] sampling the given path object — straight points for a
        line/poly/path, and a dense sample of the Bézier for a node path."""
        t = o.get('type')
        if t in ('line', 'path', 'poly'):
            return [tuple(p) for p in o.get('pts', [])]
        if t == 'nodes':
            pp = node_painter_path(o); n = max(2, min(samples, int(pp.length() / 6) or samples))
            return [(pp.pointAtPercent(i / n).x(), pp.pointAtPercent(i / n).y()) for i in range(n + 1)]
        return []

    def detach_text_from_path(self):
        o = self.canvas.sel
        if o is None or o.get('type') != 'text' or not o.get('pathpts'):
            QMessageBox.information(self, APP, 'Select a text-on-a-path object first, then Detach Text from Path.')
            return
        self.canvas.snapshot(); o.pop('pathpts', None); self.canvas.update()

    # ---------------------------------------------------------------- flip / lock / duplicate
    def flip(self, axis):
        if not self.canvas._selection():
            QMessageBox.information(self, APP, 'Select an object first, then flip it.')
            return
        self.canvas.flip_selection(axis)

    def toggle_lock(self):
        if not self.canvas._selection():
            QMessageBox.information(self, APP, 'Select an object first, then lock or unlock it.')
            return
        self.canvas.toggle_lock(); self.canvas.update()

    def duplicate(self):
        if not self.canvas._selection():
            QMessageBox.information(self, APP, 'Select an object first, then duplicate it.')
            return
        self.canvas.duplicate_selection(); self.refresh_layers()

    # ---------------------------------------------------------------- measurement units
    def set_unit(self, unit):
        self.canvas.unit = unit
        for u, act in getattr(self, 'unit_acts', {}).items():
            act.setChecked(u == unit)
        # restyle any selected dimension line to the new unit's label
        for o in self.canvas._selection():
            if o.get('type') == 'dim': o['unit'] = unit
        self.canvas.update()

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

    def blend(self):
        if len(self.canvas._selection()) != 2:
            QMessageBox.information(self, APP, 'Select exactly two objects, then Blend to morph one into '
                                   'the other over a number of steps.')
            return
        n, ok = QInputDialog.getInt(self, 'Blend', 'Number of blend steps:', 6, 1, 100, 1)
        if not ok:
            return
        new = self.canvas.blend_selection(n)
        if new is None:
            QMessageBox.information(self, APP, 'Those two objects could not be blended. Pick two shapes, '
                                   'QuickShapes, lines or node paths.')
            return
        self.refresh_layers()

    def node_type(self, kind):
        if not self.canvas.set_selected_node_type(kind):
            QMessageBox.information(self, APP, 'Pick the Node tool, click a node on a path, then set its '
                                   'type (Cusp / Smooth / Symmetric).')

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
        stays text and shapes stay paths. A publishing Profile (web/print/PDF-X-style) tunes
        image handling and records an advisory conformance tag (see PDF_PROFILES)."""
        # Profile picker dialog
        prof = QComboBox()
        for k, (lbl, *_r) in PDF_PROFILES.items(): prof.addItem(lbl, k)
        prof.setCurrentIndex(max(0, prof.findData(self._pdf_profile)))
        dlg = QDialog(self); dlg.setWindowTitle('Export PDF')
        v = QVBoxLayout(dlg)
        fl = QFormLayout(); fl.addRow('Profile:', prof); v.addLayout(fl)
        v.addWidget(QLabel('Web down-scales embedded pictures to keep the file small.\n'
                           'Print keeps full-resolution vector output (the default).\n'
                           'The PDF/X-style profiles tag the file for prepress (approximate — no\n'
                           'embedded ICC and no true CMYK conversion; a RIP/preflight does the real work).'))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        if not dlg.exec(): return
        profile = prof.currentData(); self._pdf_profile = profile
        start = (os.path.splitext(self.path)[0] if self.path else os.path.join(_just_dir('docs'), 'drawing')) + '.pdf'
        path, _ = QFileDialog.getSaveFileName(self, 'Export PDF', start, 'PDF (*.pdf)')
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        self._paint_pdf(path, profile)
        _justapps_recent('draw', path); self.statusBar().showMessage(f'Exported {path}', 4000)

    def _paint_pdf(self, path, profile='print'):
        W, H = self.canvas.W, self.canvas.H
        lbl, img_cap, conf = PDF_PROFILES.get(profile, PDF_PROFILES['print'])
        # Web profile: temporarily override the decoded-image cache with down-scaled copies so
        # the exported file stays small. The originals in the object model are untouched; the
        # cache entries are restored afterwards.
        saved = {}
        if img_cap:
            for o in self.canvas.objs:
                if o.get('type') != 'image': continue
                src = o.get('src', '')
                if not src or src in saved: continue
                qi = obj_image(o)
                if not qi.isNull() and max(qi.width(), qi.height()) > img_cap:
                    saved[src] = _IMG_CACHE.get(src)
                    _IMG_CACHE[src] = qi.scaled(img_cap, img_cap, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        try:
            w = QPdfWriter(path); w.setResolution(96)
            # Record the profile in the PDF metadata. The conformance string for the PDF/X-style
            # profiles is advisory only — a prepress operator / RIP reads it; it is NOT real PDF/X.
            try:
                w.setCreator(f'{APP} {VERSION}' + ((' — ' + conf) if conf else ''))
                tag = lbl + ((' — ' + conf) if conf else '')
                w.setTitle((os.path.splitext(os.path.basename(path))[0] or 'Drawing') + f'  [{tag}]')
            except Exception:
                pass
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
        finally:
            for src, old in saved.items():
                if old is None: _IMG_CACHE.pop(src, None)
                else: _IMG_CACHE[src] = old

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
        f.addAction(self.act('Export as &Picture…', self.export_picture_dialog, 'Ctrl+Shift+E'))
        f.addAction(self.act('&Export PNG (quick)…', self.export_png))
        f.addAction(self.act('Export P&DF…', self.export_pdf))
        f.addAction(self.act('Insert &Picture…', self.import_image))
        f.addAction(self.act('&Print…', self.print_drawing, QKeySequence.Print))
        f.addAction(self.act('Edit in &PAINTcanvas…', self.edit_in_paint))
        f.addSeparator(); f.addAction(self.act('&Quit', self.close, QKeySequence.Quit))
        e = m.addMenu('&Edit')
        e.addAction(self.act('&Undo', self.canvas.do_undo, QKeySequence.Undo))
        e.addAction(self.act('&Redo', self.canvas.do_redo, QKeySequence.Redo))
        e.addSeparator()
        e.addAction(self.act('&Duplicate', self.duplicate, QKeySequence('Ctrl+D')))
        e.addSeparator()
        e.addAction(self.act('Edit &Text…', self.edit_text))
        e.addAction(self.act('&Gradient Fill…', self.gradient_dialog))
        e.addAction(self.act('Te&xture / Pattern Fill…', self.texture_fill_dialog))
        e.addAction(self.act('&Effects (Shadow, Glow, Reflection…)…', self.effects_dialog))
        e.addAction(self.act('Trans&parency Gradient…', self.transparency_gradient_dialog))
        e.addAction(self.act('&Opacity…', self.opacity_dialog))
        e.addAction(self.act('&Line Style (Dashes & Arrows)…', self.line_style_dialog))
        e.addAction(self.act('&Pressure Studio (brush profile)…', self.pressure_studio))
        e.addSeparator()
        e.addAction(self.act('Convert to &Curves', self.convert_to_curves, QKeySequence('Ctrl+Shift+C')))
        nm = e.addMenu('&Node')
        nm.addAction(self.act('Make &Cusp', lambda: self.node_type('cusp')))
        nm.addAction(self.act('Make &Smooth', lambda: self.node_type('smooth')))
        nm.addAction(self.act('Make S&ymmetric', lambda: self.node_type('symmetric')))
        nm.addSeparator()
        nm.addAction(self.act('C&ycle Node Type (press C)', self.canvas.cycle_selected_node_type))
        nm.addAction(self.act('&Delete Node', self.canvas.delete_selected_node))
        tm = m.addMenu('&Text')
        tm.addAction(self.act('Edit &Text…', self.edit_text))
        tm.addAction(self.act('&Fit Text to Path', self.fit_text_to_path))
        tm.addAction(self.act('&Detach Text from Path', self.detach_text_from_path))
        pm = m.addMenu('&Picture')
        pm.addAction(self.act('&Insert Picture…', self.import_image))
        pm.addAction(self.act('&PhotoLab…', self.photolab))
        pm.addAction(self.act('&Cutout Studio…', self.cutout_studio))
        pm.addAction(self.act('&AutoTrace / Vectorise…', self.auto_trace))
        pm.addAction(self.act('&Replace Picture…', self.replace_image))
        pm.addSeparator()
        pm.addAction(self.act('Edit in &PAINTcanvas…', self.edit_in_paint))
        a = m.addMenu('&Arrange')
        a.addAction(self.act('Bring to &Front', lambda: self.canvas.z_order('front'), QKeySequence('Ctrl+Shift+]')))
        a.addAction(self.act('Send to &Back', lambda: self.canvas.z_order('back'), QKeySequence('Ctrl+Shift+[')))
        a.addAction(self.act('Bring For&ward', lambda: self.canvas.z_order('forward'), QKeySequence('Ctrl+]')))
        a.addAction(self.act('Send Back&ward', lambda: self.canvas.z_order('backward'), QKeySequence('Ctrl+[')))
        a.addSeparator()
        a.addAction(self.act('Flip &Horizontal', lambda: self.flip('h')))
        a.addAction(self.act('Flip &Vertical', lambda: self.flip('v')))
        a.addAction(self.act('Loc&k / Unlock', self.toggle_lock, QKeySequence('Ctrl+L')))
        a.addSeparator()
        a.addAction(self.act('&Group', self.canvas.group_selection, QKeySequence('Ctrl+G')))
        a.addAction(self.act('&Ungroup', self.canvas.ungroup_selection, QKeySequence('Ctrl+Shift+G')))
        cm = a.addMenu('Com&bine')
        cm.addAction(self.act('&Union (Add)', lambda: self.combine('union')))
        cm.addAction(self.act('&Subtract (Front from Back)', lambda: self.combine('subtract')))
        cm.addAction(self.act('&Intersect', lambda: self.combine('intersect')))
        a.addAction(self.act('Ble&nd…', self.blend))
        a.addAction(self.act('Rou&ghen…', self.roughen_dialog))
        dm = a.addMenu('Dis&tort (Perspective / Envelope)')
        dm.addAction(self.act('Add &Perspective (drag corners)', self.add_perspective))
        dm.addAction(self.act('&Reset Perspective', self.reset_perspective))
        dm.addSeparator()
        dm.addAction(self.act('Add &Envelope (mesh warp)', lambda: self.add_envelope('reset')))
        for nm in ('arch', 'bulge', 'pinch', 'wave'):
            dm.addAction(self.act('Envelope: ' + nm.capitalize(), lambda _=0, n=nm: self.add_envelope(n)))
        dm.addAction(self.act('Reset En&velope', self.reset_envelope))
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
        v.addSeparator()
        um = v.addMenu('&Measurement Units')
        ug = QActionGroup(self); self.unit_acts = {}
        for lbl, u in UNIT_LABELS:
            ua = self.act(lbl, lambda _=0, uu=u: self.set_unit(uu))
            ua.setCheckable(True); ua.setChecked(u == self.canvas.unit)
            ug.addAction(ua); um.addAction(ua); self.unit_acts[u] = ua
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

    def set_pos(self, p):
        u = self.canvas.unit; k = UNIT_PER_PX.get(u, 1.0)
        if u == 'px':
            self.pos_lbl.setText(f'{int(p[0])}, {int(p[1])} px   ')
        else:
            self.pos_lbl.setText(f'{p[0] * k:.1f}, {p[1] * k:.1f} {u}   ')
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
        # colour-panel swatch labels follow the active fill/line
        if hasattr(self, 'col_fill'):
            for btn, col in ((self.col_fill, self.canvas.fill), (self.col_line, self.canvas.stroke)):
                btn.setStyleSheet(f'QPushButton{{background:{col.name()};color:{"#fff" if col.lightness()<140 else "#000"};'
                                  'border:1px solid #888;border-radius:5px;font-weight:600}}')
        self._sync_studio()

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

    def _export_src_rect(self, selection_only=False):
        """(ox, oy, w, h) of the area Export as Picture should capture — the whole canvas,
        or the fx-expanded bounding box of the current selection."""
        c = self.canvas
        sel = c._selection() if selection_only else None
        if sel:
            rects = [obj_fx_bounds(o) for o in sel]; r = rects[0]
            for rr in rects[1:]: r = r.united(rr)
            r = r.adjusted(-4, -4, 4, 4)
            return sel, r.left(), r.top(), r.width(), r.height()
        return None, 0, 0, c.W, c.H

    def _render_image(self, scale=1.0, transparent=False, selection_only=False,
                      out_w=None, out_h=None, supersample=False):
        """Rasterise the drawing (or just the selection) to a QImage on a white or transparent
        ground — the engine behind Export as Picture. Either give `scale` (× the source px) OR
        an explicit out_w/out_h. `supersample` renders at 2× then smooth-downscales for crisp edges."""
        c = self.canvas
        sel, ox, oy, ww, hh = self._export_src_rect(selection_only)
        if out_w is None:
            out_w = max(1, int(round(ww * scale)))
        if out_h is None:
            out_h = max(1, int(round(out_w * hh / max(1e-6, ww))))
        out_w = max(1, int(out_w)); out_h = max(1, int(out_h))
        ss = 2 if supersample else 1
        iw, ih = out_w * ss, out_h * ss
        img = QImage(iw, ih, QImage.Format_ARGB32)
        img.fill(Qt.transparent if transparent else QColor('#ffffff'))
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.scale(iw / max(1e-6, ww), ih / max(1e-6, hh)); p.translate(-ox, -oy)
        global _PAINT_OBJS; _PAINT_OBJS = c.objs
        objs = sel if sel else c.ordered_objs()
        for o in objs:
            paint_object(p, o, False)
        p.end()
        if ss != 1:
            img = img.scaled(out_w, out_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return img

    def export_picture_dialog(self):
        """Export as Picture — PNG/JPEG/TIFF/BMP/WebP, sized by scale %, DPI or an explicit
        pixel width, with JPEG/WebP quality, a 32-bit transparent background, supersampling
        and a live preview (the DrawPlus 'Export as Picture' dialog). Ported from PAGEcreator."""
        from PySide6.QtWidgets import QSlider, QWidget, QHBoxLayout, QDialogButtonBox
        c = self.canvas
        _, _ox, _oy, sw0, sh0 = self._export_src_rect(False)
        dlg = QDialog(self); dlg.setWindowTitle('Export as Picture'); dlg.setMinimumWidth(600)
        lay = QHBoxLayout(dlg)
        form = QFormLayout(); left = QVBoxLayout(); left.addLayout(form); lay.addLayout(left, 0)
        area = QComboBox(); area.addItem('Whole page', False)
        if c._selection(): area.addItem('Selected objects', True)
        fmt = QComboBox()
        for lbl, ext in (('PNG', 'png'), ('JPEG', 'jpg'), ('TIFF', 'tif'), ('BMP', 'bmp'), ('WebP', 'webp')):
            fmt.addItem(lbl, ext)
        method = QComboBox()
        method.addItem('Scale %', 'scale'); method.addItem('DPI', 'dpi'); method.addItem('Width (pixels)', 'px')
        scale = QSpinBox(); scale.setRange(5, 800); scale.setSuffix(' %'); scale.setValue(100)
        dpi = QSpinBox(); dpi.setRange(18, 1200); dpi.setSuffix(' dpi'); dpi.setValue(96)
        pxw = QSpinBox(); pxw.setRange(16, 20000); pxw.setSuffix(' px'); pxw.setValue(int(sw0))
        quality = QSlider(Qt.Horizontal); quality.setRange(0, 100); quality.setValue(90); qlbl = QLabel('90')
        quality.valueChanged.connect(lambda v: qlbl.setText(str(v)))
        qrow = QHBoxLayout(); qrow.addWidget(quality); qrow.addWidget(qlbl); qwrap = QWidget(); qwrap.setLayout(qrow)
        transp = QCheckBox('32-bit transparent background'); transp.setChecked(True)
        ssample = QCheckBox('Supersample (render 2× then downscale)'); ssample.setChecked(True)
        size_lbl = QLabel('—'); size_lbl.setStyleSheet('color:gray')
        form.addRow('Area:', area); form.addRow('Format:', fmt); form.addRow('Size by:', method)
        form.addRow('Scale:', scale); form.addRow('Resolution:', dpi); form.addRow('Pixel width:', pxw)
        form.addRow('Quality:', qwrap); form.addRow('', transp); form.addRow('', ssample)
        form.addRow('Output size:', size_lbl)
        prev = QLabel(); prev.setFixedSize(300, 300); prev.setAlignment(Qt.AlignCenter)
        prev.setStyleSheet('QLabel{background:#e9edf0;border:1px solid #bbb}')
        pv = QVBoxLayout(); pv.addWidget(QLabel('Preview')); pv.addWidget(prev); pv.addStretch(1); lay.addLayout(pv, 1)
        def src_size():
            _, _x, _y, ww, hh = self._export_src_rect(bool(area.currentData()))
            return ww, hh
        def out_size():
            ww, hh = src_size(); m = method.currentData()
            if m == 'scale': ow = ww * scale.value() / 100.0
            elif m == 'dpi': ow = ww * dpi.value() / 96.0
            else: ow = pxw.value()
            ow = max(1, int(round(ow))); oh = max(1, int(round(ow * hh / max(1e-6, ww))))
            return ow, oh
        def can_alpha(): return fmt.currentData() in ('png', 'webp')
        def refresh(*_):
            m = method.currentData()
            for wdg, mm in ((scale, 'scale'), (dpi, 'dpi'), (pxw, 'px')):
                wdg.setVisible(m == mm); form.labelForField(wdg).setVisible(m == mm)
            lossy = fmt.currentData() in ('jpg', 'webp')
            qwrap.setVisible(lossy); form.labelForField(qwrap).setVisible(lossy)
            transp.setEnabled(can_alpha())
            if not can_alpha(): transp.setChecked(False)
            ow, oh = out_size(); size_lbl.setText(f'{ow} × {oh} px')
            tr = transp.isChecked() and can_alpha()
            img = self._render_image(transparent=tr, selection_only=bool(area.currentData()),
                                     out_w=ow, out_h=oh, supersample=False)
            prev.setPixmap(QPixmap.fromImage(img).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        for wdg in (area, fmt, method): wdg.currentIndexChanged.connect(refresh)
        for sp in (scale, dpi, pxw): sp.valueChanged.connect(refresh)
        transp.toggled.connect(refresh)
        refresh()
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText('Export…')
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); left.addWidget(bb)
        if not dlg.exec(): return
        ext = fmt.currentData()
        start = (os.path.splitext(self.path)[0] if self.path else os.path.join(_just_dir('pics'), 'drawing')) + '.' + ext
        filt = {'png': 'PNG image (*.png)', 'jpg': 'JPEG image (*.jpg *.jpeg)', 'tif': 'TIFF image (*.tif *.tiff)',
                'bmp': 'BMP image (*.bmp)', 'webp': 'WebP image (*.webp)'}[ext]
        path, _ = QFileDialog.getSaveFileName(self, 'Export as Picture', start, filt)
        if not path: return
        if not path.lower().endswith('.' + ext) and not (ext == 'jpg' and path.lower().endswith('.jpeg')):
            path += '.' + ext
        ow, oh = out_size(); tr = transp.isChecked() and can_alpha()
        img = self._render_image(transparent=tr, selection_only=bool(area.currentData()),
                                 out_w=ow, out_h=oh, supersample=ssample.isChecked())
        if not tr and ext in ('jpg', 'tif', 'bmp'):
            flat = QImage(img.size(), QImage.Format_RGB32); flat.fill(QColor('#ffffff'))
            pp = QPainter(flat); pp.drawImage(0, 0, img); pp.end(); img = flat
        qual = quality.value() if ext in ('jpg', 'webp') else -1
        qfmt = {'png': 'PNG', 'jpg': 'JPEG', 'tif': 'TIFF', 'bmp': 'BMP', 'webp': 'WEBP'}[ext]
        if img.save(path, qfmt, qual):
            _justapps_recent('paint', path); self.statusBar().showMessage(f'Exported {ow}×{oh} to {path}', 4000)
        else:
            QMessageBox.warning(self, APP, "Couldn't save that picture.")

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
