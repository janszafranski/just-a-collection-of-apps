#!/usr/bin/env python3
# just a... PAINTcanvas — a tiny raster (bitmap) image editor: paint, erase, draw shapes,
# fill, pick colours, add text, and save a PNG/JPG. The photo-editing companion to
# just a... PAGEcreator / WEBcreator (and the vector sibling of just a... DRAW).
import sys, os, math, random

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QColorDialog,
                                   QFileDialog, QMessageBox, QSpinBox, QLabel, QInputDialog,
                                   QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                                   QSlider, QCheckBox, QFormLayout, QDialogButtonBox,
                                   QDockWidget, QListWidget, QListWidgetItem,
                                   QGroupBox, QDoubleSpinBox)
    from PySide6.QtGui import (QImage, QPainter, QPen, QColor, QBrush, QPixmap, QAction, QIcon,
                               QKeySequence, QCursor, QFont, QPainterPath, QActionGroup,
                               QLinearGradient, QRadialGradient, QConicalGradient, QPolygonF,
                               QTransform)
    from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QSettings
except ImportError:
    sys.stderr.write("just a... PAINTcanvas needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... PAINTcanvas"
ORG = "justapaint"
VERSION = "1.25-00"


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


IMAGE_LIBRARY_DIR = os.path.expanduser('~/.local/share/justapps/images')
FRAME_LIBRARY_DIR = os.path.expanduser('~/.local/share/justapps/frames')
_IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def scan_image_library(root=None):
    """Scan the local stock-photo library for LEAF directories that directly contain
    photos, and return them as pickable categories. Read live, never copied.

    Returns a list of (label, dirpath) sorted by label, where `label` is the directory's
    path relative to the images root (e.g. 'Premium Image Collection 6 / People'). A copy
    may still be streaming in, so a partial or absent library is handled gracefully."""
    root = root or IMAGE_LIBRARY_DIR
    root = os.path.realpath(os.path.expanduser(root))
    cats = []
    if not os.path.isdir(root):
        return cats
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        dirnames.sort()
        has_img = any(f.lower().endswith(_IMG_EXTS) for f in filenames)
        if has_img:
            rel = os.path.relpath(dirpath, root)
            label = ' / '.join(rel.split(os.sep)) if rel != '.' else os.path.basename(root)
            cats.append((label, dirpath))
    cats.sort(key=lambda c: c[0].lower())
    return cats


def scan_frame_library(root=None):
    """Scan the local decorative frame/edge library for LEAF directories that directly
    contain frames, returned as pickable categories. The frame library is DEEPLY nested
    (e.g. 'Extreme Edges / Vol. 1 Artistic Edges / …'), so this reuses the same recursive
    leaf-dir walk as scan_image_library, rooted at FRAME_LIBRARY_DIR. Read live, never
    copied; a partial/absent library (a copy still streaming in) is handled gracefully.

    Returns a list of (label, dirpath) sorted by label, where `label` is the directory's
    path relative to the frames root joined with ' / '."""
    return scan_image_library(root or FRAME_LIBRARY_DIR)


def library_thumbnail(path, px=140):
    """Decode a thumbnail for `path` SMALL and FAST via QImageReader.setScaledSize —
    the source photos are ~6.7 MB each, so they must never be loaded at full size for a
    grid. Returns a QPixmap scaled to roughly px×px (or a null QPixmap on failure)."""
    from PySide6.QtGui import QImageReader
    rd = QImageReader(path)
    rd.setAutoTransform(True)
    sz = rd.size()
    if sz.isValid() and (sz.width() > px or sz.height() > px):
        if sz.width() >= sz.height():
            rd.setScaledSize(QSize(px, max(1, round(px * sz.height() / sz.width()))))
        else:
            rd.setScaledSize(QSize(max(1, round(px * sz.width() / sz.height())), px))
    img = rd.read()
    return QPixmap.fromImage(img) if not img.isNull() else QPixmap()


def library_picker(parent, title='Open from Library'):
    """Shared Image-Library picker mirroring PAGEdesigner's bitmap_fill_dialog swatch
    grid: a Browse-for-image button, a category dropdown, and a scrollable thumbnail grid.
    Thumbnails are decoded small/fast via library_thumbnail (QImageReader scaled size) and
    only the CURRENT category's grid is built, rebuilt lazily on category change.

    Returns the chosen full image path, or None if cancelled / nothing chosen."""
    from PySide6.QtWidgets import QScrollArea, QGridLayout, QToolButton
    chosen = {'path': None}
    dlg = QDialog(parent); dlg.setWindowTitle(title); dlg.resize(620, 640)
    v = QVBoxLayout(dlg)
    lbl = QLabel('Browse your local stock-photo library by category and open a photo '
                 'straight in — or Browse for any image on your computer.')
    lbl.setWordWrap(True); v.addWidget(lbl)
    sel_lbl = QLabel('Nothing chosen yet.'); sel_lbl.setStyleSheet('color:#5c6b73')
    row = QHBoxLayout(); bbrowse = QPushButton('Browse for an image…')
    row.addWidget(bbrowse); row.addWidget(sel_lbl, 1); v.addLayout(row)

    def choose(path):
        chosen['path'] = path; sel_lbl.setText('Chosen: ' + os.path.basename(path))
        okbtn.setEnabled(True)

    def browse():
        p, _ = QFileDialog.getOpenFileName(dlg, 'Choose an image', _just_dir('pics'),
                                           'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)')
        if p: choose(p)
    bbrowse.clicked.connect(browse)

    cats = scan_image_library()
    if cats:
        v.addWidget(QLabel('<b>Image library</b> — pick a category, then click a photo:'))
        catcombo = QComboBox()
        for label, _d in cats: catcombo.addItem(label)
        v.addWidget(catcombo)
        area = QScrollArea(); area.setWidgetResizable(True); area.setMinimumHeight(360); v.addWidget(area, 1)
        holder = QWidget(); hv = QGridLayout(holder); area.setWidget(holder)

        def load_cat(idx):
            while hv.count():
                it = hv.takeAt(0); w = it.widget()
                if w: w.deleteLater()
            if idx < 0 or idx >= len(cats): return
            d = cats[idx][1]
            try:
                files = sorted([f for f in os.listdir(d) if f.lower().endswith(_IMG_EXTS)])[:120]
            except OSError:
                files = []
            for i, fn in enumerate(files):
                fp = os.path.join(d, fn)
                tb = QToolButton(); pm = library_thumbnail(fp, 140)
                if not pm.isNull(): tb.setIcon(QIcon(pm))
                tb.setIconSize(QSize(120, 120)); tb.setToolTip(fn)
                tb.setCursor(Qt.PointingHandCursor); tb.setAutoRaise(True)
                tb.clicked.connect(lambda _=0, fp=fp: choose(fp))
                hv.addWidget(tb, i // 4, i % 4)
        catcombo.currentIndexChanged.connect(load_cat); load_cat(0)
    else:
        note = QLabel('<span style="color:gray">No image library found at '
                      '~/.local/share/justapps/images yet — use Browse for an image instead.</span>')
        note.setWordWrap(True); v.addWidget(note)

    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    okbtn = bb.button(QDialogButtonBox.Ok); okbtn.setText('Open this photo'); okbtn.setEnabled(False)
    bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    if dlg.exec() != QDialog.Accepted:
        return None
    return chosen['path']


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

# OpenCV is an OPTIONAL extra: when present it gives the Smart Mask tool a
# grabCut-quality cut-out (Fluid-Mask-grade edges). Everything still works
# without it via a NumPy colour-model fallback (see smart_mask()).
try:
    import cv2 as _cv2
    HAS_CV2 = True
except Exception:
    _cv2 = None
    HAS_CV2 = False


def q2pil(img):
    im = img.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombytes('RGBA', (im.width(), im.height()), im.constBits().tobytes())


def pil2q(pil):
    if pil.mode != 'RGBA':
        pil = pil.convert('RGBA')
    data = pil.tobytes('raw', 'RGBA')
    return QImage(data, pil.width, pil.height, QImage.Format_RGBA8888).convertToFormat(QImage.Format_ARGB32).copy()


def build_transform(bbox, sx, sy, angle, skew, anchor=None):
    """Pure matrix helper for Free Transform. `bbox` is the content rect
    (x, y, w, h) in image coords; `sx`/`sy` are scale factors, `angle` degrees,
    `skew` = (kx, ky) horizontal/vertical shear factors. Transform order is
    translate(anchor) -> rotate -> scale -> skew -> translate(-anchor), so the
    box pivots about `anchor` (default = bbox centre). Returns a QTransform that
    maps ORIGINAL image coords to transformed image coords."""
    x, y, w, h = bbox
    if anchor is None:
        anchor = (x + w / 2.0, y + h / 2.0)
    ax, ay = anchor
    kx, ky = (skew if skew is not None else (0.0, 0.0))
    t = QTransform()
    t.translate(ax, ay)
    t.rotate(angle)
    t.scale(sx, sy)
    t.shear(kx, ky)
    t.translate(-ax, -ay)
    return t


def apply_transform(qimg, transform, out_size=None):
    """Render `qimg` (a QImage) through `transform` into a new ARGB32 QImage.
    If `out_size` (w, h) is given the result is that size with the transform
    applied in image coords; otherwise Qt sizes the result to the transformed
    bounds (and the mapping origin shifts — use mapRect to locate content)."""
    src = qimg.convertToFormat(QImage.Format_ARGB32)
    if out_size is None:
        return src.transformed(transform, Qt.SmoothTransformation)
    w, h = out_size
    out = QImage(int(w), int(h), QImage.Format_ARGB32); out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setTransform(transform)
    p.drawImage(0, 0, src)
    p.end()
    return out


def alpha_bbox(rgba, threshold=0):
    """Bounding box of pixels whose alpha is > `threshold` in an HxWx4 uint8
    array. Returns (x, y, w, h) or None if nothing passes the threshold."""
    import numpy as np
    if rgba is None or rgba.ndim != 3 or rgba.shape[2] < 4:
        return None
    mask = rgba[..., 3] > threshold
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return None
    y0, y1 = int(rows[0]), int(rows[-1])
    x0, x1 = int(cols[0]), int(cols[-1])
    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def _merge_a(src, rgb):
    """Put an RGB result back together with the source's alpha channel."""
    return Image.merge('RGBA', rgb.convert('RGB').split() + (src.split()[3],))


def _largest_content_rect(mask, max_dim=1000):
    """Largest axis-aligned rectangle that covers only True cells of 2-D bool `mask`.
    Returns (x0, y0, x1, y1) half-open in the ORIGINAL coordinates, or None.

    This is PanoramaPlus's "Auto Min Crop": a stitch warps the frames onto a wider
    canvas and leaves ragged black wedges around the content, so the biggest gap-free
    rectangle is what squares the panorama off. The search runs on a copy down-scaled
    to `max_dim` (a few-thousand-px pano would make the per-row scan crawl otherwise),
    then maps the result back and insets by one source step so the crop never bites
    into the black. Needs NumPy."""
    import numpy as np
    h, w = mask.shape
    scale = 1.0
    small = mask
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        sh, sw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
        ys = (np.arange(sh) / scale).astype(np.int64).clip(0, h - 1)
        xs = (np.arange(sw) / scale).astype(np.int64).clip(0, w - 1)
        small = mask[ys][:, xs]
    sh, sw = small.shape
    heights = np.zeros(sw, dtype=np.int64)
    best = (0, 0, 0, 0, 0)                 # area, x0, y0, x1, y1 in small coords
    for y in range(sh):
        heights = np.where(small[y], heights + 1, 0)
        hh = heights.tolist(); hh.append(0)     # sentinel flushes the stack
        stack = []                              # (start_col, bar_height), heights ascending
        for i in range(sw + 1):
            cur = hh[i]; start = i
            while stack and stack[-1][1] > cur:
                idx, ph = stack.pop()
                area = ph * (i - idx)
                if area > best[0]:
                    best = (area, idx, y - ph + 1, i, y + 1)
                start = idx
            stack.append((start, cur))
    if best[0] <= 0:
        return None
    _, x0, y0, x1, y1 = best
    if scale != 1.0:
        inv = 1.0 / scale
        pad = int(np.ceil(inv))
        x0 = int(np.floor(x0 * inv)) + pad; y0 = int(np.floor(y0 * inv)) + pad
        x1 = int(np.ceil(x1 * inv)) - pad;  y1 = int(np.ceil(y1 * inv)) - pad
    x0 = max(0, min(x0, w)); x1 = max(0, min(x1, w))
    y0 = max(0, min(y0, h)); y1 = max(0, min(y1, h))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return (x0, y0, x1, y1)


def apply_mask(img, mask):
    """Return a NEW QImage: `img` with its alpha multiplied by `mask` (a greyscale
    QImage; white=255 keeps the pixel, black=0 hides it). Sizes are reconciled. Uses
    numpy when available for an accurate luma→alpha multiply, else a Qt fallback that
    treats the mask as a straight alpha stencil."""
    src = img.convertToFormat(QImage.Format_ARGB32)
    m = mask
    if m.size() != src.size():
        m = m.scaled(src.width(), src.height())
    if HAS_PIL:
        rgba = _np.asarray(q2pil(src)).astype(_np.uint16)
        ml = _np.asarray(q2pil(m).convert('L')).astype(_np.uint16)
        rgba[..., 3] = (rgba[..., 3] * ml // 255).astype(_np.uint16)
        return pil2q(Image.fromarray(rgba.astype('uint8'), 'RGBA'))
    out = src.copy()
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, m)                 # mask's own alpha gates the result
    p.end()
    return out


def new_mask(w, h, white=True):
    """A fresh greyscale mask QImage, filled white (all opaque) or black (all hidden)."""
    m = QImage(w, h, QImage.Format_Grayscale8)
    m.fill(QColor('#ffffff') if white else QColor('#000000'))
    return m


def _feather_mask(binary, feather):
    """Soften a 0/255 uint8 HxW mask's edges with a Gaussian of radius `feather` (px).
    feather<=0 returns the hard mask unchanged."""
    if feather <= 0:
        return binary.astype(_np.uint8)
    soft = Image.fromarray(binary.astype('uint8'), 'L').filter(
        ImageFilter.GaussianBlur(float(feather)))
    return _np.asarray(soft).astype(_np.uint8)


def points_to_mask(points, w, h):
    """Rasterise a closed polygon (a list of (x,y) points) to a 0/255 uint8 HxW mask.
    Shared by the Lasso (freehand) and Polygon selection tools — the result is adopted
    as a mask selection exactly like the Magic wand's. Pure (no window): fills a
    QPainterPath into a Grayscale8 QImage, then reads it back as NumPy. Fewer than 3
    points (no area) yields an all-zero mask."""
    m = _np.zeros((h, w), _np.uint8)
    if not HAS_PIL or w <= 0 or h <= 0 or len(points) < 3:
        return m
    img = QImage(w, h, QImage.Format_Grayscale8); img.fill(0)
    path = QPainterPath(); path.addPolygon(QPolygonF([QPointF(float(x), float(y)) for x, y in points]))
    path.closeSubpath()
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing, False)
    p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(255, 255, 255))); p.drawPath(path); p.end()
    buf = img.constBits()
    arr = _np.frombuffer(buf, _np.uint8, count=img.bytesPerLine() * h).reshape(h, img.bytesPerLine())[:, :w]
    return _np.where(arr > 127, 255, 0).astype(_np.uint8)


def _smart_mask_fallback(rgb, keep, remove, feather=0):
    """NumPy-only foreground/background separation (no OpenCV). Builds a Gaussian
    colour model (mean + covariance) for the KEEP-scribbled and REMOVE-scribbled
    pixels, then classifies every pixel to the nearer model by Mahalanobis-ish
    distance. Returns a 0..255 uint8 mask (255 = foreground), feathered."""
    h, w = rgb.shape[:2]
    data = rgb.reshape(-1, 3).astype(_np.float64)
    kf = keep.reshape(-1)
    rf = remove.reshape(-1)
    fg_px = data[kf]
    bg_px = data[rf]
    if fg_px.shape[0] == 0 or bg_px.shape[0] == 0:
        # not enough guidance — everything the user marked KEEP is the subject
        out = _np.where(keep, 255, 0).astype(_np.uint8)
        return _feather_mask(out, feather)

    def model(px):
        mean = px.mean(axis=0)
        cov = _np.cov(px.T) if px.shape[0] > 1 else _np.eye(3)
        cov = cov + _np.eye(3) * 1.0           # regularise (avoid singular)
        try:
            inv = _np.linalg.inv(cov)
        except _np.linalg.LinAlgError:
            inv = _np.eye(3)
        return mean, inv

    fg_mean, fg_inv = model(fg_px)
    bg_mean, bg_inv = model(bg_px)

    def dist(inv, mean):
        d = data - mean
        return _np.einsum('ij,jk,ik->i', d, inv, d)

    fg_d = dist(fg_inv, fg_mean)
    bg_d = dist(bg_inv, bg_mean)
    fg = (fg_d <= bg_d).reshape(h, w)
    # honour the scribbles exactly where the user painted them
    fg = fg | keep
    fg = fg & ~remove
    out = _np.where(fg, 255, 0).astype(_np.uint8)
    return _feather_mask(out, feather)


def smart_mask(rgb, keep, remove, feather=0, force_fallback=False):
    """Fluid-Mask-style scribble cut-out. Given an RGB image (HxWx3 uint8) and two
    boolean HxW scribble maps — `keep` over the subject, `remove` over the
    background — return a 0..255 uint8 HxW mask where 255 = foreground (the subject).

    With OpenCV present (and force_fallback False) this seeds cv2.grabCut from the
    scribbles (GC_FGD under KEEP, GC_BGD under REMOVE, GC_PR_FGD elsewhere) and runs
    a few GC_INIT_WITH_MASK iterations — the sharp, Fluid-Mask-grade path. Otherwise a
    pure NumPy colour-model fallback is used. `feather` applies a Gaussian to the
    binary result for soft edges (hair/foliage). This is a pure function (no Qt)."""
    rgb = _np.ascontiguousarray(rgb[..., :3].astype(_np.uint8))
    keep = _np.ascontiguousarray(keep.astype(bool))
    remove = _np.ascontiguousarray(remove.astype(bool))
    h, w = rgb.shape[:2]
    if not keep.any():
        return _np.zeros((h, w), _np.uint8)

    if HAS_CV2 and not force_fallback:
        try:
            gc = _np.full((h, w), _cv2.GC_PR_FGD, _np.uint8)
            gc[remove] = _cv2.GC_BGD
            gc[keep] = _cv2.GC_FGD
            if not (gc == _cv2.GC_BGD).any():
                # grabCut needs some background seed — treat the border as probable bg
                gc_pr = _np.full((h, w), _cv2.GC_PR_BGD, _np.uint8)
                gc_pr[keep] = _cv2.GC_FGD
                gc = gc_pr
            bgdm = _np.zeros((1, 65), _np.float64)
            fgdm = _np.zeros((1, 65), _np.float64)
            bgr = rgb[..., ::-1].copy()
            _cv2.grabCut(bgr, gc, None, bgdm, fgdm, 5, _cv2.GC_INIT_WITH_MASK)
            fg = (gc == _cv2.GC_FGD) | (gc == _cv2.GC_PR_FGD)
            fg = fg | keep
            fg = fg & ~remove
            out = _np.where(fg, 255, 0).astype(_np.uint8)
            if out.any():
                return _feather_mask(out, feather)
            # grabCut collapsed to nothing — fall through to the NumPy model
        except Exception:
            pass
    return _smart_mask_fallback(rgb, keep, remove, feather)


# ---------------------------------------------------------------- skin smoothing
# A portrait-retouch filter in the spirit of a skin-smoothing plug-in: find the skin
# by its tone, smooth it with an EDGE-PRESERVING filter (so eyes, lips, hair and
# nostrils stay sharp), then blend the smoothed version back by an amount while
# keeping some of the original fine texture so it never looks plastic. Pure functions
# (no Qt): they take and return numpy RGB arrays so they can be unit-tested headless.

def skin_mask(rgb):
    """Detect skin in an HxWx3 (or x4) uint8 RGB image by its tone. Uses the classic
    YCrCb skin box (133<=Cr<=173, 77<=Cb<=127) intersected with a permissive HSV hue
    band, then lightly morphs/feathers the result. Returns a 0..255 uint8 HxW mask
    (255 = confident skin). Needs numpy (HAS_PIL)."""
    rgb = _np.ascontiguousarray(rgb[..., :3].astype(_np.float32))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # YCrCb (ITU-R BT.601) — the Cr/Cb skin box is the workhorse skin detector.
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cr = (r - y) * 0.713 + 128.0
    cb = (b - y) * 0.564 + 128.0
    skin = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)
    # HSV guard: skin hue sits in the red–yellow wedge, and must have some saturation
    # (so near-grey pixels in the Cr/Cb box — e.g. teeth, whites of eyes — drop out).
    mx = _np.maximum(_np.maximum(r, g), b)
    mn = _np.minimum(_np.minimum(r, g), b)
    diff = mx - mn
    sat = _np.where(mx > 0, diff / _np.maximum(mx, 1.0), 0.0)
    hue = _np.zeros_like(mx)
    nz = diff > 1e-6
    rc = _np.where(mx == r, (g - b) / _np.where(nz, diff, 1.0), 0.0)
    gc = _np.where(mx == g, 2.0 + (b - r) / _np.where(nz, diff, 1.0), 0.0)
    bc = _np.where(mx == b, 4.0 + (r - g) / _np.where(nz, diff, 1.0), 0.0)
    hue = (_np.where(mx == r, rc, _np.where(mx == g, gc, bc)) * 60.0) % 360.0
    hue_ok = ((hue <= 55) | (hue >= 335)) & (sat >= 0.12) & (sat <= 0.75) & (mx >= 50)
    binary = _np.where(skin & hue_ok, 255, 0).astype(_np.uint8)
    # clean up: close small holes, drop specks, then feather the edge.
    if HAS_CV2:
        k = _cv2.getStructuringElement(_cv2.MORPH_ELLIPSE, (5, 5))
        binary = _cv2.morphologyEx(binary, _cv2.MORPH_CLOSE, k)
        binary = _cv2.morphologyEx(binary, _cv2.MORPH_OPEN, k)
    else:
        soft = Image.fromarray(binary, 'L').filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
        binary = _np.asarray(soft).astype(_np.uint8)
    return _feather_mask(binary, 3)


def _edge_preserving_smooth(rgb, radius, force_fallback=False):
    """Return an edge-preserving smoothed copy of an HxWx3 uint8 RGB image. Prefers
    cv2.bilateralFilter (big flats smoothed, strong edges kept); otherwise a NumPy
    fallback: a median pass (kills speckle/pores) followed by a light Gaussian, both
    edge-friendlier than a plain blur."""
    radius = max(1, int(round(radius)))
    if HAS_CV2 and not force_fallback:
        d = max(5, radius * 2 + 1)
        sigma = 35.0 + radius * 12.0
        out = rgb
        for _ in range(2):                           # two passes deepen the smoothing
            out = _cv2.bilateralFilter(out, d, sigma, float(radius * 2))
        return out
    # pure-NumPy / Pillow fallback. The MEDIAN filter is the edge-preserving workhorse
    # (a hard black/white step survives it); repeat it to deepen the smoothing. A
    # tiny Gaussian only knocks off the last of the speckle without greying edges.
    im = Image.fromarray(rgb, 'RGB')
    msz = radius if radius % 2 else radius + 1
    msz = max(3, min(9, msz))
    passes = 2 + min(3, radius // 3)
    for _ in range(passes):
        im = im.filter(ImageFilter.MedianFilter(size=msz))
    return _np.asarray(im).astype(_np.uint8)


def smooth_skin(rgb, amount=0.7, radius=8, detail=0.3, skin_only=True,
                extra_mask=None, force_fallback=False):
    """Portrait skin-retouch. Edge-preservingly smooth an HxWx3 (or x4) uint8 RGB
    image, add back a `detail` fraction of the original high-frequency texture so it
    does not go plastic, then blend the result over the original by `amount`,
    restricted to the detected skin when `skin_only` (optionally intersected with
    `extra_mask`, a 0..255 HxW weight — e.g. the current selection). The mask edge is
    feathered so the retouch fades in. Returns a fresh HxWx3 uint8 array.

    With OpenCV present (and force_fallback False) the smooth is cv2.bilateralFilter;
    otherwise a NumPy median+Gaussian fallback. A pure function — no Qt."""
    src = _np.ascontiguousarray(rgb[..., :3].astype(_np.uint8))
    h, w = src.shape[:2]
    amount = float(max(0.0, min(1.0, amount)))
    detail = float(max(0.0, min(1.0, detail)))

    smoothed = _edge_preserving_smooth(src, radius, force_fallback=force_fallback)
    sf = smoothed.astype(_np.float32)
    of = src.astype(_np.float32)
    # detail-preserve: give back a fraction of the original minus smoothed (the fine
    # high-frequency skin texture) so pores/freckles aren't fully erased.
    retouch = sf + (of - sf) * detail

    # per-pixel blend weight (0..1): amount, gated by the skin mask / selection.
    weight = _np.full((h, w), amount, _np.float32)
    if skin_only:
        m = skin_mask(src).astype(_np.float32) / 255.0
        weight = weight * m
    if extra_mask is not None:
        em = extra_mask
        if em.shape[:2] != (h, w):
            em = _np.asarray(Image.fromarray(em.astype('uint8'), 'L').resize((w, h), Image.NEAREST))
        weight = weight * (em.astype(_np.float32) / 255.0)

    out = of * (1.0 - weight[..., None]) + retouch * weight[..., None]
    return _np.clip(out, 0, 255).astype(_np.uint8)


# ---------------------------------------------------------------- smart enlarge
# Intelligent photo up-scaling in the spirit of BenVista PhotoZoom's S-Spline:
# make a small picture bigger while keeping edges crisp, dodging the soft/jaggy
# look of a plain resize. Clean-room recipe (NOT their algorithm): a high-quality
# Lanczos resample, an optional light denoise so we don't amplify grain, then an
# edge-aware unsharp mask to restore the apparent detail lost in blowing it up.
# Pure function (no Qt) so it can be unit-tested headless.

def _gaussian_blur_rgb(rgb, radius, force_fallback=False):
    """Light Gaussian blur of an HxWx3 uint8 RGB array (the unsharp-mask low pass)."""
    radius = float(max(0.1, radius))
    if HAS_CV2 and not force_fallback:
        k = int(radius * 3) | 1                      # odd kernel ~3σ
        return _cv2.GaussianBlur(rgb, (k, k), radius)
    im = Image.fromarray(rgb, 'RGB').filter(ImageFilter.GaussianBlur(radius))
    return _np.asarray(im).astype(_np.uint8)


def _denoise_rgb(rgb, strength, force_fallback=False):
    """Light colour denoise of an HxWx3 uint8 RGB array. Prefers cv2's Non-Local
    Means (fastNlMeansDenoisingColored); otherwise a Pillow MedianFilter. `strength`
    is 0..1 — scales the filter strength / median size."""
    strength = float(max(0.0, min(1.0, strength)))
    if strength <= 0:
        return rgb
    if HAS_CV2 and not force_fallback:
        h = 3.0 + strength * 12.0                    # luma/chroma denoise amount
        return _cv2.fastNlMeansDenoisingColored(rgb, None, h, h, 7, 21)
    msz = 3 if strength < 0.6 else 5                 # 3×3 for light, 5×5 for strong
    im = Image.fromarray(rgb, 'RGB').filter(ImageFilter.MedianFilter(size=msz))
    return _np.asarray(im).astype(_np.uint8)


def smart_enlarge(rgb, new_w, new_h, sharpen=0.5, denoise=0.0, force_fallback=False):
    """Intelligently up-scale an HxWx3 (or x4) uint8 RGB image to (new_w, new_h).

    Recipe: optional light denoise on the SOURCE (so grain isn't magnified), a
    high-quality Lanczos resample up to the new size, then an edge-aware unsharp
    mask — ``sharpened = img + amount*(img - gaussianblur(img))`` — to put back the
    crispness a plain resize loses. `sharpen` (0..1) scales the unsharp amount;
    `denoise` (0..1) scales the pre-pass. Returns a fresh HxWx3 uint8 array of the
    new size. Prefers OpenCV (cv2.INTER_LANCZOS4); with `force_fallback` or no cv2 it
    uses Pillow's Image.LANCZOS. A pure function — no Qt."""
    src = _np.ascontiguousarray(rgb[..., :3].astype(_np.uint8))
    new_w = max(1, int(new_w)); new_h = max(1, int(new_h))
    sharpen = float(max(0.0, min(1.0, sharpen)))
    denoise = float(max(0.0, min(1.0, denoise)))

    # 1) denoise the source before enlarging, so we don't amplify grain/speckle.
    if denoise > 0:
        src = _denoise_rgb(src, denoise, force_fallback=force_fallback)

    # 2) high-quality Lanczos resample to the target size (the sharp resampler).
    if HAS_CV2 and not force_fallback:
        up = _cv2.resize(src, (new_w, new_h), interpolation=_cv2.INTER_LANCZOS4)
    else:
        im = Image.fromarray(src, 'RGB').resize((new_w, new_h), Image.LANCZOS)
        up = _np.asarray(im).astype(_np.uint8)
    up = _np.ascontiguousarray(up.astype(_np.uint8))

    # 3) edge-aware unsharp mask: restore the apparent detail lost in up-scaling.
    if sharpen > 0:
        amount = sharpen * 1.5                       # tasteful 0..1.5 strength
        radius = 1.0 + (max(new_w, new_h) / max(src.shape[1], src.shape[0])) * 0.5
        blur = _gaussian_blur_rgb(up, radius, force_fallback=force_fallback).astype(_np.float32)
        upf = up.astype(_np.float32)
        out = upf + amount * (upf - blur)
        up = _np.clip(out, 0, 255).astype(_np.uint8)
    return up


# ---------------------------------------------------------------- Photo FX
# A clean-room reimagining of the "Twisting Pixels" photo-plugin idea — one-click
# photographic FILM LOOKS (in the spirit of VirtualPhotographer) and photo-to-art
# ART STYLES (in the spirit of PhotoArtMaster / ArtStudio) — written from scratch
# with modern techniques. The film looks are pure NumPy/PIL (tone curves, channel
# mixing, split-toning, grain, vignette). The art styles prefer OpenCV's
# non-photorealistic-rendering filters where present (cv2.stylization /
# pencilSketch / detailEnhance / edgePreservingFilter, and an oil effect) and fall
# back to equivalent NumPy/PIL recipes everywhere, following the same HAS_CV2 guard
# used by Smart Mask / Smooth Skin / Smart Enlarge. Both entry points are pure
# functions (no Qt): they take and return HxWx3 uint8 RGB arrays so they can be
# unit-tested headless.

def _apply_lut_rgb(rgb, lut):
    """Map an HxWx3 uint8 array through a 256-entry LUT (list/array, same LUT on
    all channels). Vectorised, returns uint8."""
    lut = _np.clip(_np.asarray(lut), 0, 255).astype(_np.uint8)
    return lut[rgb]


def _tone_curve_lut(points):
    """256-entry uint8 LUT interpolated through (x, y) control points (each 0..255)."""
    pts = sorted(points)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return _np.clip(_np.interp(_np.arange(256), xs, ys), 0, 255).astype(_np.uint8)


def _luma(rgb):
    """ITU-R BT.601 luma of an HxWx3 float array, returned HxW float."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _channel_mix_bw(rgb, wr, wg, wb):
    """Weighted B&W channel mix (the digital equivalent of a colour filter on
    panchromatic film). Weights are normalised; returns an HxWx3 grey float array."""
    s = wr + wg + wb
    if abs(s) < 1e-6:
        wr, wg, wb, s = 0.299, 0.587, 0.114, 1.0
    y = (rgb[..., 0] * wr + rgb[..., 1] * wg + rgb[..., 2] * wb) / s
    y = _np.clip(y, 0, 255)
    return _np.dstack([y, y, y])


def _split_tone(rgb, shadow_rgb, hi_rgb, balance=0.5, strength=0.5):
    """Split-tone: tint the shadows towards `shadow_rgb` and the highlights towards
    `hi_rgb` (each an (r,g,b) 0..255 triple) by `strength`. `balance` (0..1) sets the
    luma pivot between the two tints. Operates on a float HxWx3 array, returns float."""
    y = _luma(rgb) / 255.0
    # a smooth highlight weight pivoting at `balance`
    hi_w = _np.clip((y - (balance - 0.5)) , 0.0, 1.0)
    hi_w = hi_w * hi_w * (3 - 2 * hi_w)          # smoothstep
    sh_w = 1.0 - hi_w
    sh = _np.asarray(shadow_rgb, _np.float32)
    hi = _np.asarray(hi_rgb, _np.float32)
    tint = sh_w[..., None] * sh + hi_w[..., None] * hi
    # blend towards the tint in a soft-light-ish way, scaled by strength
    out = rgb * (1.0 - strength) + (rgb * 0.5 + tint * 0.5) * strength
    return out


def _saturate(rgb, factor):
    """Scale saturation of a float HxWx3 array about its luma by `factor`."""
    y = _luma(rgb)[..., None]
    return y + (rgb - y) * factor


def _vignette(rgb, amount, feather=0.55):
    """Darken the corners of a float HxWx3 array radially. `amount` 0..1 = how dark
    the extreme corner gets; `feather` sets how far in the darkening reaches."""
    if amount <= 0:
        return rgb
    h, w = rgb.shape[:2]
    yy, xx = _np.ogrid[0:h, 0:w]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    d = _np.sqrt(((xx - cx) / max(1.0, cx)) ** 2 + ((yy - cy) / max(1.0, cy)) ** 2)
    d = d / _np.sqrt(2.0)                         # 0 centre .. 1 corner
    inner = max(0.0, min(0.99, 1.0 - feather))
    mask = _np.clip((d - inner) / max(1e-3, 1.0 - inner), 0.0, 1.0)
    mask = mask * mask * (3 - 2 * mask)           # smoothstep falloff
    factor = 1.0 - amount * mask
    return rgb * factor[..., None]


def _add_grain(rgb, strength, seed=12345):
    """Add monochromatic film grain (correlated across channels) to a float HxWx3
    array. `strength` 0..1 scales the noise sigma (~0..26 levels)."""
    if strength <= 0:
        return rgb
    rng = _np.random.default_rng(seed)
    h, w = rgb.shape[:2]
    sigma = strength * 26.0
    noise = rng.normal(0.0, sigma, (h, w, 1)).astype(_np.float32)
    return rgb + noise


# Film-look presets, defined as DATA so they're easy to read and extend. Each is a
# combination of: an optional B&W channel mix (`bw`: (wr,wg,wb)), a per-channel tone
# curve set (`curves`: dict of 'rgb'/'r'/'g'/'b' -> control points), a saturation
# multiplier (`sat`), a split-tone (`split`: (shadow_rgb, hi_rgb, balance, strength)),
# and default grain / vignette amounts (0..1) that the slider scales.
FILM_LOOKS = {
    'bw_classic': {
        'label': 'B&W Classic',
        'desc': 'Neutral black & white with a gentle contrast S-curve — the everyday monochrome conversion.',
        'bw': (0.299, 0.587, 0.114),
        'curves': {'rgb': [(0, 0), (64, 52), (128, 132), (192, 206), (255, 255)]},
        'grain': 0.18, 'vignette': 0.12,
    },
    'bw_red': {
        'label': 'B&W Red Filter',
        'desc': 'Monochrome through a red filter — dark dramatic skies and bright skin, the classic landscape look.',
        'bw': (0.80, 0.20, 0.02),
        'curves': {'rgb': [(0, 0), (60, 44), (128, 134), (200, 216), (255, 255)]},
        'grain': 0.20, 'vignette': 0.18,
    },
    'vintage': {
        'label': 'Vintage / Faded',
        'desc': 'Lifted, faded shadows with a warm-yellow highlight wash and muted colour — an aged print.',
        'curves': {'rgb': [(0, 28), (64, 78), (128, 140), (192, 198), (255, 236)]},
        'sat': 0.78,
        'split': ((70, 56, 40), (236, 222, 170), 0.5, 0.35),
        'grain': 0.22, 'vignette': 0.28,
    },
    'cross_process': {
        'label': 'Cross Process',
        'desc': 'The punchy, skewed colour of C-41 film run in E-6 chemistry — teal shadows, yellow-green highlights.',
        'curves': {'r': [(0, 0), (64, 48), (128, 140), (192, 214), (255, 255)],
                   'g': [(0, 10), (128, 128), (255, 248)],
                   'b': [(0, 30), (128, 120), (255, 220)]},
        'sat': 1.25,
        'split': ((20, 70, 80), (230, 225, 120), 0.5, 0.3),
        'grain': 0.18, 'vignette': 0.2,
    },
    'warm_portrait': {
        'label': 'Warm Portrait',
        'desc': 'Soft warm skin tones with gently lifted shadows and a golden highlight — flattering for people.',
        'curves': {'r': [(0, 12), (128, 138), (255, 255)],
                   'b': [(0, 0), (128, 118), (255, 240)]},
        'sat': 1.05,
        'split': ((60, 40, 30), (255, 238, 200), 0.55, 0.28),
        'grain': 0.1, 'vignette': 0.22,
    },
    'cool_cinematic': {
        'label': 'Cool Cinematic',
        'desc': 'The teal-and-orange blockbuster grade: cool blue shadows, warm highlights, crushed contrast.',
        'curves': {'rgb': [(0, 14), (48, 40), (128, 128), (208, 220), (255, 244)]},
        'sat': 1.1,
        'split': ((18, 52, 78), (240, 170, 96), 0.5, 0.4),
        'grain': 0.14, 'vignette': 0.3,
    },
    'sepia': {
        'label': 'Sepia',
        'desc': 'Warm brown-toned monochrome — the look of an old photographic print.',
        'bw': (0.299, 0.587, 0.114),
        'curves': {'rgb': [(0, 0), (128, 128), (255, 255)]},
        'split': ((42, 26, 14), (255, 232, 180), 0.5, 0.85),
        'grain': 0.16, 'vignette': 0.2,
    },
}

FILM_LOOK_ORDER = ['bw_classic', 'bw_red', 'vintage', 'cross_process',
                   'warm_portrait', 'cool_cinematic', 'sepia']


def apply_film_look(rgb, preset_key, grain=None, vignette=None):
    """Apply a VirtualPhotographer-style photographic FILM LOOK to an HxWx3 (or x4)
    uint8 RGB image and return a fresh HxWx3 uint8 array. `preset_key` indexes
    FILM_LOOKS. `grain` and `vignette` (each 0..1) override the preset defaults when
    given, else the preset's own amounts are used. Pure NumPy/PIL (no OpenCV needed,
    no Qt): tone curves + channel-mix B&W + split-toning + grain + vignette."""
    preset = FILM_LOOKS.get(preset_key, FILM_LOOKS['bw_classic'])
    src = _np.ascontiguousarray(rgb[..., :3].astype(_np.uint8))
    f = src.astype(_np.float32)

    # 1) B&W channel mix (if the preset is monochrome)
    if 'bw' in preset:
        wr, wg, wb = preset['bw']
        f = _channel_mix_bw(f, wr, wg, wb)

    # 2) per-channel tone curves
    curves = preset.get('curves')
    if curves:
        work = _np.clip(f, 0, 255).astype(_np.uint8)
        if 'rgb' in curves:
            work = _apply_lut_rgb(work, _tone_curve_lut(curves['rgb']))
        for ci, key in enumerate(('r', 'g', 'b')):
            if key in curves:
                lut = _tone_curve_lut(curves[key])
                work[..., ci] = lut[work[..., ci]]
        f = work.astype(_np.float32)

    # 3) saturation
    if 'sat' in preset:
        f = _saturate(f, preset['sat'])

    # 4) split-tone (shadows / highlights tint)
    if 'split' in preset:
        sh, hi, bal, strg = preset['split']
        f = _split_tone(_np.clip(f, 0, 255), sh, hi, bal, strg)

    # 5) grain + 6) vignette (slider overrides the preset default)
    g = preset.get('grain', 0.0) if grain is None else float(grain)
    v = preset.get('vignette', 0.0) if vignette is None else float(vignette)
    f = _add_grain(f, max(0.0, min(1.0, g)))
    f = _vignette(f, max(0.0, min(1.0, v)))

    return _np.clip(f, 0, 255).astype(_np.uint8)


# ---- art styles -----------------------------------------------------------
def _oil_paint_numpy(rgb, radius, levels=20):
    """NumPy fallback oil-paint filter: for each pixel pick the MOST COMMON intensity
    bucket in its neighbourhood and average the colours that fall in that bucket — the
    classic 'oilify' recipe. radius sets the window; levels the number of buckets."""
    src = rgb.astype(_np.uint8)
    h, w = src.shape[:2]
    r = max(1, int(radius))
    inten = (_luma(src.astype(_np.float32)) * (levels / 255.0)).astype(_np.int32)
    inten = _np.clip(inten, 0, levels - 1)
    pad = _np.pad(src, ((r, r), (r, r), (0, 0)), mode='edge')
    padi = _np.pad(inten, ((r, r), (r, r)), mode='edge')
    out = _np.empty_like(src)
    # bucket counts and colour sums over the sliding window (vectorised per bucket)
    counts = _np.zeros((h, w, levels), _np.int32)
    sums = _np.zeros((h, w, levels, 3), _np.float32)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            bi = padi[r + dy:r + dy + h, r + dx:r + dx + w]        # HxW bucket index
            px = pad[r + dy:r + dy + h, r + dx:r + dx + w].astype(_np.float32)
            yy, xx = _np.ogrid[0:h, 0:w]
            counts[yy, xx, bi] += 1
            sums[yy, xx, bi] += px
    best = counts.argmax(axis=2)                                   # HxW most-common bucket
    yy, xx = _np.ogrid[0:h, 0:w]
    cnt = counts[yy, xx, best][..., None].astype(_np.float32)
    out = (sums[yy, xx, best] / _np.maximum(cnt, 1.0))
    return _np.clip(out, 0, 255).astype(_np.uint8)


def _edges_numpy(gray, block=9, c=7):
    """Adaptive-threshold-ish edge map (NumPy): a pixel is an edge (0) where it is
    darker than its local mean by `c`, else white (255). `gray` is HxW uint8."""
    g = Image.fromarray(gray.astype('uint8'), 'L')
    mean = _np.asarray(g.filter(ImageFilter.BoxBlur(max(1, block // 2)))).astype(_np.int16)
    e = _np.where(gray.astype(_np.int16) < mean - c, 0, 255).astype(_np.uint8)
    return e


ART_STYLES = {
    'oil': {
        'label': 'Oil Painting',
        'desc': 'Thick daubs of paint — flat colour patches with soft, brushed edges.',
    },
    'watercolour': {
        'label': 'Watercolour',
        'desc': 'Soft washes of colour with the detail smoothed away, in the manner of a watercolour.',
    },
    'pencil_grey': {
        'label': 'Pencil Sketch (grey)',
        'desc': 'A graphite pencil drawing — pale paper with soft shading lines.',
    },
    'pencil_colour': {
        'label': 'Pencil Sketch (colour)',
        'desc': 'A coloured-pencil sketch — the pencil shading tinted with the photo’s colours.',
    },
    'cartoon': {
        'label': 'Cartoon / Comic',
        'desc': 'Bold flat colour with heavy black outlines — a comic-book / cel-shaded look.',
    },
    'detail': {
        'label': 'Detail Boost',
        'desc': 'An HDR-ish punch that lifts local detail and texture without a halo.',
    },
}

ART_STYLE_ORDER = ['oil', 'watercolour', 'pencil_grey', 'pencil_colour', 'cartoon', 'detail']


def apply_art_style(rgb, style_key, strength=0.6, force_fallback=False):
    """Turn a photo into art (PhotoArtMaster-style). Takes an HxWx3 (or x4) uint8 RGB
    image and returns a fresh HxWx3 uint8 array. `style_key` indexes ART_STYLES;
    `strength` (0..1) scales the effect. Prefers OpenCV's non-photorealistic filters
    (cv2.stylization / pencilSketch / detailEnhance / edgePreservingFilter, and an oil
    effect) and always provides a NumPy/PIL fallback (set `force_fallback` to force
    it). Pure function — no Qt."""
    src = _np.ascontiguousarray(rgb[..., :3].astype(_np.uint8))
    strength = float(max(0.0, min(1.0, strength)))
    h, w = src.shape[:2]
    use_cv2 = HAS_CV2 and not force_fallback

    def blend(result):
        """Mix the stylised result back over the original by `strength` so the slider
        goes from the photo (0) to the full effect (1)."""
        a = src.astype(_np.float32); b = result.astype(_np.float32)
        return _np.clip(a * (1.0 - strength) + b * strength, 0, 255).astype(_np.uint8)

    if style_key == 'oil':
        radius = 3 + int(round(strength * 5))         # 3..8
        result = None
        if use_cv2:
            try:                                      # cv2.xphoto.oilPainting if the contrib build has it
                import cv2.xphoto as _xp              # noqa: F401
                bgr = src[..., ::-1]
                op = _cv2.xphoto.oilPainting(bgr, radius, 1)
                result = _np.ascontiguousarray(op[..., ::-1])
            except Exception:
                try:                                  # stylization gives a painterly, flat-patch look too
                    bgr = src[..., ::-1]
                    st = _cv2.stylization(bgr, sigma_s=60, sigma_r=0.45)
                    result = _np.ascontiguousarray(st[..., ::-1])
                except Exception:
                    result = None
        if result is None:
            result = _oil_paint_numpy(src, radius, levels=18)
        return blend(result)

    if style_key == 'watercolour':
        result = None
        if use_cv2:
            try:
                bgr = src[..., ::-1]
                st = _cv2.stylization(bgr, sigma_s=60, sigma_r=0.6)
                result = _np.ascontiguousarray(st[..., ::-1])
            except Exception:
                try:
                    bgr = src[..., ::-1]
                    ep = _cv2.edgePreservingFilter(bgr, flags=1, sigma_s=60, sigma_r=0.4)
                    result = _np.ascontiguousarray(ep[..., ::-1])
                except Exception:
                    result = None
        if result is None:
            # fallback: edge-preserving smooth (reuses Smooth Skin's engine) +
            # a touch of median to pool colour into washes, then slight saturation.
            smooth = _edge_preserving_smooth(src, 6, force_fallback=True)
            im = Image.fromarray(smooth, 'RGB').filter(ImageFilter.MedianFilter(5))
            wc = _saturate(_np.asarray(im).astype(_np.float32), 1.12)
            result = _np.clip(wc, 0, 255).astype(_np.uint8)
        return blend(result)

    if style_key == 'pencil_grey':
        result = None
        if use_cv2:
            try:
                bgr = src[..., ::-1]
                grey, _col = _cv2.pencilSketch(bgr, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
                result = _np.dstack([grey, grey, grey])
            except Exception:
                result = None
        if result is None:
            result = _pencil_numpy(src, coloured=False)
        return blend(result)

    if style_key == 'pencil_colour':
        result = None
        if use_cv2:
            try:
                bgr = src[..., ::-1]
                _grey, col = _cv2.pencilSketch(bgr, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
                result = _np.ascontiguousarray(col[..., ::-1])
            except Exception:
                result = None
        if result is None:
            result = _pencil_numpy(src, coloured=True)
        return blend(result)

    if style_key == 'cartoon':
        result = _cartoon(src, strength, use_cv2)
        return blend(result)

    if style_key == 'detail':
        result = None
        if use_cv2:
            try:
                bgr = src[..., ::-1]
                de = _cv2.detailEnhance(bgr, sigma_s=12, sigma_r=0.15)
                result = _np.ascontiguousarray(de[..., ::-1])
            except Exception:
                result = None
        if result is None:
            # fallback: a strong unsharp-style local-contrast boost.
            blur = _gaussian_blur_rgb(src, 3.0, force_fallback=True).astype(_np.float32)
            boosted = src.astype(_np.float32) + 1.2 * (src.astype(_np.float32) - blur)
            result = _np.clip(_saturate(boosted, 1.08), 0, 255).astype(_np.uint8)
        return blend(result)

    return src.copy()                                 # unknown key: no-op


def _pencil_numpy(rgb, coloured=False):
    """NumPy/PIL pencil-sketch fallback. The 'colour-dodge of a blurred inverted grey'
    trick: edges stay dark, flats go white — a convincing graphite look. When
    `coloured` the grey sketch is tinted by the photo's own (desaturated) colour."""
    grey = _luma(rgb.astype(_np.float32))
    inv = 255.0 - grey
    blur = _np.asarray(Image.fromarray(inv.astype('uint8'), 'L').filter(
        ImageFilter.GaussianBlur(12))).astype(_np.float32)
    # colour dodge: base * 255 / (255 - top)
    dodge = _np.clip(grey * 255.0 / _np.maximum(255.0 - blur, 1.0), 0, 255)
    sk = dodge
    if not coloured:
        return _np.dstack([sk, sk, sk]).astype(_np.uint8)
    # tint the sketch with the photo's own colour (softened), multiply-blend
    colour = _saturate(rgb.astype(_np.float32), 0.6)
    tinted = sk[..., None] / 255.0 * colour
    return _np.clip(tinted, 0, 255).astype(_np.uint8)


def _cartoon(rgb, strength, use_cv2):
    """Cartoon / comic: flatten colour into bands and overlay bold dark outlines.
    cv2 path = bilateral smoothing + adaptive-threshold edges; NumPy path =
    edge-preserving smooth + posterise + a local-contrast edge map."""
    src = rgb.astype(_np.uint8)
    quant_levels = 8
    if use_cv2:
        try:
            colour = src[..., ::-1].copy()
            for _ in range(2):
                colour = _cv2.bilateralFilter(colour, 9, 75, 75)
            colour = colour[..., ::-1]
            grey = _cv2.cvtColor(src[..., ::-1], _cv2.COLOR_BGR2GRAY)
            grey = _cv2.medianBlur(grey, 5)
            block = 9
            edges = _cv2.adaptiveThreshold(grey, 255, _cv2.ADAPTIVE_THRESH_MEAN_C,
                                           _cv2.THRESH_BINARY, block, 2 + int(strength * 6))
            q = (colour.astype(_np.int32) // (256 // quant_levels)) * (256 // quant_levels) + (256 // quant_levels) // 2
            q = _np.clip(q, 0, 255).astype(_np.uint8)
            out = _np.where(edges[..., None] == 0, 0, q)
            return out.astype(_np.uint8)
        except Exception:
            pass
    # NumPy fallback
    smooth = _edge_preserving_smooth(src, 5, force_fallback=True).astype(_np.int32)
    step = 256 // quant_levels
    q = (smooth // step) * step + step // 2
    q = _np.clip(q, 0, 255).astype(_np.uint8)
    grey = _luma(src.astype(_np.float32)).astype(_np.uint8)
    edges = _edges_numpy(grey, block=9, c=2 + int(strength * 8))
    out = _np.where(edges[..., None] == 0, 0, q)
    return out.astype(_np.uint8)


# ---------------------------------------------------------------- Effects studio
# A clean-room, from-first-principles reimagining of the classic graphics-effect
# *set* that plug-ins like Alien Skin Eye Candy made famous — bevels, chrome,
# glass, gradient glow, motion trails, twirls and procedural wood / marble / weave
# textures. Every recipe below is ORIGINAL code: edge/shape effects are driven by a
# distance transform of the layer's own alpha, shaded through surface normals;
# distortions remap the layer's pixels; textures are built from a small seedable
# value-noise / fractal-turbulence generator we write ourselves. All the heavy
# lifting lives in pure module-level functions that take and return HxWx(3 or 4)
# uint8 ndarrays (no Qt), so they can be unit-tested headless — exactly like
# smart_mask / smooth_skin / smart_enlarge / the Photo FX transforms, and following
# the same HAS_CV2 guard (an OpenCV fast path with a NumPy/PIL fallback) throughout.

def _ensure_rgba(arr):
    """Return a contiguous HxWx4 uint8 copy of an HxWx3-or-4 array (alpha=255 if 3)."""
    a = _np.ascontiguousarray(arr)
    if a.ndim == 2:
        a = _np.dstack([a, a, a])
    if a.shape[2] == 3:
        a = _np.dstack([a, _np.full(a.shape[:2], 255, _np.uint8)])
    return a.astype(_np.uint8)


def _distance_transform(binary, force_fallback=False):
    """Euclidean distance (in px) from every True pixel to the nearest False pixel of
    a boolean HxW mask. Prefers cv2.distanceTransform; otherwise a two-pass
    chamfer / jump-flood-free NumPy approximation good enough for shading. Returns a
    float32 HxW array (0 on / outside the shape edge, growing into the interior)."""
    binary = _np.ascontiguousarray(binary.astype(bool))
    if not binary.any():
        return _np.zeros(binary.shape, _np.float32)
    if HAS_CV2 and not force_fallback:
        src = _np.where(binary, 255, 0).astype(_np.uint8)
        try:
            d = _cv2.distanceTransform(src, _cv2.DIST_L2, 5)
            return d.astype(_np.float32)
        except Exception:
            pass
    return _chamfer_distance(binary)


def _chamfer_distance(binary):
    """Pure-NumPy two-pass chamfer distance transform (3-4-5 weights, scaled to ~px).
    Not exact Euclidean but smooth and monotone — ideal for bevel shading."""
    h, w = binary.shape
    INF = float(h + w) * 5.0
    d = _np.where(binary, INF, 0.0).astype(_np.float32)
    # forward pass (top-left to bottom-right)
    for y in range(h):
        row = d[y]
        up = d[y - 1] if y > 0 else None
        for x in range(w):
            if row[x] == 0.0:
                continue
            best = row[x]
            if x > 0:
                best = min(best, row[x - 1] + 3.0)
            if up is not None:
                best = min(best, up[x] + 3.0)
                if x > 0:
                    best = min(best, up[x - 1] + 4.0)
                if x < w - 1:
                    best = min(best, up[x + 1] + 4.0)
            row[x] = best
    # backward pass (bottom-right to top-left)
    for y in range(h - 1, -1, -1):
        row = d[y]
        dn = d[y + 1] if y < h - 1 else None
        for x in range(w - 1, -1, -1):
            if row[x] == 0.0:
                continue
            best = row[x]
            if x < w - 1:
                best = min(best, row[x + 1] + 3.0)
            if dn is not None:
                best = min(best, dn[x] + 3.0)
                if x < w - 1:
                    best = min(best, dn[x + 1] + 4.0)
                if x > 0:
                    best = min(best, dn[x - 1] + 4.0)
            row[x] = best
    return (d / 3.0).astype(_np.float32)   # 3-weight ≈ 1px orthogonal step


def _bevel_height(alpha, width, smoothness, profile, force_fallback=False):
    """Build a 0..1 HxW *height field* for a raised bevel on the shape described by an
    HxW uint8 alpha. The height rises from the shape edge inward over `width` px,
    shaped by `profile` ('round'/'flat'/'button'), then softened by `smoothness`.
    Returns (height, inside) where inside is the bool shape mask."""
    inside = alpha > 127
    dist = _distance_transform(inside, force_fallback=force_fallback)
    width = max(1.0, float(width))
    t = _np.clip(dist / width, 0.0, 1.0)            # 0 at edge .. 1 at `width` inward
    if profile == 'flat':
        h = t                                       # linear ramp → chamfered edge
    elif profile == 'button':
        # rounded pillow that flattens on top (ease-out then plateau)
        h = _np.sin(t * (math.pi / 2.0))
    else:                                           # 'round' — spherical cap
        h = _np.sqrt(_np.clip(1.0 - (1.0 - t) ** 2, 0.0, 1.0))
    if smoothness > 0:
        sig = float(smoothness)
        h = _np.asarray(Image.fromarray((h * 255).astype('uint8'), 'L')
                        .filter(ImageFilter.GaussianBlur(sig))).astype(_np.float32) / 255.0
    h = h * inside                                  # height is 0 outside the shape
    return h.astype(_np.float32), inside


def _surface_normals(height, scale=3.0):
    """Surface normals (nx,ny,nz) of a height field, from its gradient. `scale`
    exaggerates the slope (steeper bevel). Returns three HxW float arrays, normalised."""
    gy, gx = _np.gradient(height.astype(_np.float32))
    nx = -gx * scale
    ny = -gy * scale
    nz = _np.ones_like(height)
    norm = _np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    return nx / norm, ny / norm, nz / norm


def _light_vector(angle_deg, elevation_deg):
    """Unit light direction from a compass angle (0°=right, CCW) and an elevation."""
    a = math.radians(angle_deg)
    e = math.radians(elevation_deg)
    lx = math.cos(a) * math.cos(e)
    ly = -math.sin(a) * math.cos(e)                 # screen y grows downward
    lz = math.sin(e)
    n = math.sqrt(lx * lx + ly * ly + lz * lz) + 1e-9
    return lx / n, ly / n, lz / n


def bevel(rgba, width=10, smoothness=2.0, profile='round', angle=135,
          elevation=45, intensity=0.7, force_fallback=False):
    """EFFECT 1 — raise a 3D bevel on the layer's alpha shape. Shades the shape with
    diffuse + specular lighting of the surface normals derived from a distance-to-edge
    height field, so the rim catches the light and the far side falls into shadow.
    Takes/returns an HxWx(3 or 4) uint8 ndarray; the alpha is preserved. Pure (no Qt)."""
    out = _ensure_rgba(rgba).astype(_np.float32)
    alpha = out[..., 3]
    height, inside = _bevel_height(alpha, width, smoothness, profile,
                                   force_fallback=force_fallback)
    nx, ny, nz = _surface_normals(height, scale=2.5 + intensity * 4.0)
    lx, ly, lz = _light_vector(angle, elevation)
    diff = _np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    # specular (Blinn-ish): reflect the light off the normal towards the viewer (+z)
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
    spec = _np.clip(nx * (hx / hn) + ny * (hy / hn) + nz * (hz / hn), 0.0, 1.0) ** 24
    rgb = out[..., :3]
    # shade = darken/lighten the existing colour by the diffuse term, add a highlight
    shade = (0.5 + (diff - 0.5) * (0.6 + intensity))[..., None]
    lit = rgb * shade + spec[..., None] * 255.0 * intensity
    # only reshape the bevel band (where height ramps); the flat interior keeps colour
    band = _np.clip(1.0 - height, 0.0, 1.0)[..., None]   # strongest at the edge
    res = rgb * (1.0 - band) + lit * band
    orig = _ensure_rgba(rgba).astype(_np.float32)[..., :3]
    out[..., :3] = _np.where(inside[..., None], _np.clip(res, 0, 255), orig)  # outside untouched
    return out.astype(_np.uint8)


def _ramp_from_stops(stops, n=256):
    """Build an n×3 float lookup ramp by linearly interpolating (pos0..1, (r,g,b)) stops."""
    stops = sorted(stops, key=lambda s: s[0])
    xs = [s[0] for s in stops]
    cols = _np.array([s[1] for s in stops], _np.float32)
    t = _np.linspace(0.0, 1.0, n)
    ramp = _np.empty((n, 3), _np.float32)
    for c in range(3):
        ramp[:, c] = _np.interp(t, xs, cols[:, c])
    return ramp


CHROME_RAMPS = {
    'sky': [(0.0, (18, 22, 40)), (0.45, (70, 110, 170)), (0.55, (210, 230, 255)),
            (0.72, (120, 130, 150)), (0.85, (235, 240, 250)), (1.0, (40, 45, 60))],
    'steel': [(0.0, (20, 20, 24)), (0.4, (90, 95, 105)), (0.5, (240, 245, 250)),
              (0.62, (70, 75, 85)), (1.0, (200, 205, 215))],
    'gold': [(0.0, (40, 26, 6)), (0.4, (150, 110, 30)), (0.55, (255, 240, 180)),
             (0.7, (170, 120, 40)), (1.0, (90, 60, 12))],
    'rainbow': [(0.0, (40, 0, 60)), (0.25, (0, 80, 220)), (0.5, (0, 210, 180)),
                (0.7, (240, 200, 40)), (1.0, (220, 40, 60))],
}
CHROME_RAMP_ORDER = ['sky', 'steel', 'gold', 'rainbow']


def chrome(rgba, ramp='sky', width=12, angle=135, contrast=0.6, shine=0.7,
           force_fallback=False):
    """EFFECT 2 — map a metallic light-to-dark ramp onto the bevel normals for a
    reflective-metal look. The vertical component of the lit normal indexes a
    sky/ground chrome gradient; `contrast` stretches it and `shine` adds a specular
    hotspot. Pure; takes/returns HxWx(3 or 4) uint8."""
    out = _ensure_rgba(rgba).astype(_np.float32)
    alpha = out[..., 3]
    height, inside = _bevel_height(alpha, width, 1.5, 'round', force_fallback=force_fallback)
    nx, ny, nz = _surface_normals(height, scale=5.0)
    lx, ly, lz = _light_vector(angle, 55)
    # reflect the view ray (+z) about the normal; its tilt drives the ramp coordinate
    refl = _np.clip(nx * lx + ny * ly + nz * lz, -1.0, 1.0)
    coord = (refl * 0.5 + 0.5)
    coord = _np.clip((coord - 0.5) * (1.0 + contrast * 2.0) + 0.5, 0.0, 1.0)
    ramp_tbl = _ramp_from_stops(CHROME_RAMPS.get(ramp, CHROME_RAMPS['sky']))
    idx = _np.clip((coord * 255).astype(_np.int32), 0, 255)
    metal = ramp_tbl[idx]
    # specular hotspot for extra shine
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
    spec = _np.clip(nx * (hx / hn) + ny * (hy / hn) + nz * (hz / hn), 0.0, 1.0) ** 40
    metal = metal + spec[..., None] * 255.0 * shine
    out[..., :3] = _np.clip(metal, 0, 255)
    out[~inside, 3] = alpha[~inside]
    return out.astype(_np.uint8)


def _warp_remap(rgb, map_x, map_y, force_fallback=False):
    """Sample an HxWx3/4 uint8 image at float coordinate maps (map_x, map_y). Prefers
    cv2.remap (bilinear, border-reflect); else a NumPy nearest-ish gather."""
    h, w = rgb.shape[:2]
    if HAS_CV2 and not force_fallback:
        try:
            return _cv2.remap(rgb, map_x.astype(_np.float32), map_y.astype(_np.float32),
                              _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_REFLECT)
        except Exception:
            pass
    xi = _np.clip(_np.round(map_x).astype(_np.int32), 0, w - 1)
    yi = _np.clip(_np.round(map_y).astype(_np.int32), 0, h - 1)
    return rgb[yi, xi]


def glass(rgba, width=10, refraction=6.0, opacity=0.8, angle=135, force_fallback=False):
    """EFFECT 3 — a glassy inner bevel: a soft inner-bevel shading, a small refraction
    that displaces the underlying pixels sideways near the edge (as light bends through
    the glass rim), and a crisp specular highlight. Pure; HxWx(3 or 4) uint8 in/out."""
    out = _ensure_rgba(rgba).astype(_np.float32)
    alpha = out[..., 3]
    height, inside = _bevel_height(alpha, width, 1.0, 'round', force_fallback=force_fallback)
    nx, ny, nz = _surface_normals(height, scale=6.0)
    h, w = alpha.shape
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    # refraction: push the sampling coordinate along the surface-normal tilt
    map_x = xx + nx * refraction
    map_y = yy + ny * refraction
    refr = _warp_remap(out[..., :3].astype(_np.uint8), map_x, map_y,
                       force_fallback=force_fallback).astype(_np.float32)
    # glass tint + inner-bevel shading (brighten the lit rim, darken the far rim)
    lx, ly, lz = _light_vector(angle, 50)
    diff = _np.clip(nx * lx + ny * ly + nz * lz, -1.0, 1.0)
    rim = _np.clip(1.0 - height, 0.0, 1.0)[..., None]
    shaded = refr * (1.0 + diff[..., None] * 0.5 * rim)
    hx, hy, hz = lx, ly, lz + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
    spec = _np.clip(nx * (hx / hn) + ny * (hy / hn) + nz * (hz / hn), 0.0, 1.0) ** 32
    shaded = shaded + spec[..., None] * 255.0
    glassed = out[..., :3] * (1.0 - opacity) + shaded * opacity
    out[..., :3] = _np.clip(glassed, 0, 255)
    out[~inside, :3] = _ensure_rgba(rgba)[~inside, :3].astype(_np.float32)
    out[..., 3] = alpha
    return out.astype(_np.uint8)


def gradient_glow(rgba, stops=None, width=16, softness=0.6, opacity=0.85,
                  force_fallback=False):
    """EFFECT 4 — a multi-stop coloured glow OUTSIDE the alpha shape (a richer Outer
    Glow). A distance transform of the *background* maps each ring of pixels around
    the shape to a colour stop, fading out over `width` px. `stops` is a list of
    (pos0..1, (r,g,b)); `softness` blurs the falloff. Pure; HxWx(3 or 4) uint8."""
    src = _ensure_rgba(rgba)
    alpha = src[..., 3]
    if stops is None:
        stops = [(0.0, (255, 240, 120)), (0.5, (255, 120, 40)), (1.0, (180, 20, 60))]
    inside = alpha > 127
    outside = ~inside
    dist = _distance_transform(outside, force_fallback=force_fallback)   # 0 at edge → out
    width = max(1.0, float(width))
    t = _np.clip(dist / width, 0.0, 1.0)             # 0 at shape edge .. 1 at glow reach
    ramp = _ramp_from_stops(stops)
    idx = _np.clip((t * 255).astype(_np.int32), 0, 255)
    glow_rgb = ramp[idx]
    # intensity fades to zero at the glow's outer reach; softness eases the profile
    gi = 1.0 - t
    gi = gi ** (0.4 + (1.0 - softness) * 2.0)
    gi = _np.where(outside, gi, 0.0).astype(_np.float32)
    if softness > 0:
        gi = _np.asarray(Image.fromarray((gi * 255).astype('uint8'), 'L')
                         .filter(ImageFilter.GaussianBlur(softness * width * 0.3))
                         ).astype(_np.float32) / 255.0
    gi = gi * opacity
    # composite: glow underneath, original shape on top
    out = src.astype(_np.float32)
    a = (alpha.astype(_np.float32) / 255.0)[..., None]
    base_rgb = glow_rgb * gi[..., None]
    base_a = gi
    comp_rgb = out[..., :3] * a + base_rgb * (1.0 - a)
    comp_a = _np.clip(alpha.astype(_np.float32) + base_a * 255.0 * (1.0 - a[..., 0]), 0, 255)
    out[..., :3] = comp_rgb
    out[..., 3] = comp_a
    return _np.clip(out, 0, 255).astype(_np.uint8)


def motion_trail(rgba, angle=0, length=24, echoes=8, falloff=0.7, force_fallback=False):
    """EFFECT 5 — a directional motion smear/echo of the whole layer: stamp `echoes`
    progressively fainter, progressively offset copies of the layer along `angle`
    (compass degrees), spread over `length` px, with each echo dimmed by `falloff`.
    Pure; HxWx(3 or 4) uint8 in/out (alpha is smeared too)."""
    src = _ensure_rgba(rgba).astype(_np.float32)
    h, w = src.shape[:2]
    echoes = max(1, int(echoes))
    a = math.radians(angle)
    dx = math.cos(a); dy = -math.sin(a)
    acc = _np.zeros((h, w, 4), _np.float32)
    wsum = 0.0
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    for i in range(echoes):
        frac = i / max(1, echoes - 1) if echoes > 1 else 0.0
        off = frac * length
        weight = falloff ** i
        map_x = xx - dx * off
        map_y = yy - dy * off
        sample = _warp_remap(src, map_x, map_y, force_fallback=force_fallback).astype(_np.float32)
        # outside-the-frame samples (reflected) shouldn't bleed colour: gate by whether
        # the source coordinate was in-bounds
        inb = ((map_x >= 0) & (map_x < w) & (map_y >= 0) & (map_y < h)).astype(_np.float32)
        sample = sample * inb[..., None]
        acc += sample * weight
        wsum += weight
    out = acc / max(1e-6, wsum)
    # keep the crisp original on top of the trail so the leading edge stays sharp
    a0 = (src[..., 3] / 255.0)[..., None]
    out[..., :3] = out[..., :3] * (1.0 - a0) + src[..., :3] * a0
    out[..., 3] = _np.maximum(out[..., 3], src[..., 3])
    return _np.clip(out, 0, 255).astype(_np.uint8)


def twirl(rgba, angle=120, radius=None, falloff=1.0, force_fallback=False):
    """EFFECT 6 — a radial twist (swirl) around the layer centre. Each pixel is rotated
    about the centre by an amount that is `angle` degrees at the centre and eases to 0
    at `radius`; `falloff` shapes how quickly the twist relaxes outward. Uses cv2.remap
    when present, else a NumPy coordinate map. Pure; HxWx(3 or 4) uint8."""
    src = _ensure_rgba(rgba)
    h, w = src.shape[:2]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    if radius is None:
        radius = min(w, h) / 2.0
    radius = max(1.0, float(radius))
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    dx = xx - cx; dy = yy - cy
    r = _np.sqrt(dx * dx + dy * dy)
    theta = _np.arctan2(dy, dx)
    # twist strength: full at centre, 0 beyond radius, eased by falloff
    s = _np.clip(1.0 - r / radius, 0.0, 1.0) ** max(0.1, falloff)
    rot = math.radians(angle) * s
    ct = _np.cos(rot); st = _np.sin(rot)
    # sample FROM the un-rotated source (inverse map): rotate the sample coord back
    map_x = cx + (dx * ct + dy * st)
    map_y = cy + (-dx * st + dy * ct)
    out = _warp_remap(src, map_x, map_y, force_fallback=force_fallback)
    return _ensure_rgba(out)


def apply_liquify_dab(dx, dy, mode, cx, cy, radius, strength, drag=(0.0, 0.0)):
    """Accumulate one Liquify brush dab into the displacement map (float32 HxW `dx`/`dy`,
    the per-pixel SOURCE offset added to the base coord grid). A soft (cosine-feathered)
    falloff `f` = 1 at the centre → 0 at `radius` weights every dab. Modes:
      push    — shove pixels along the drag vector `drag` (+= drag * f * strength);
      bloat   — push outward from (cx,cy)  (offset along +radial unit);
      pinch   — pull inward toward (cx,cy) (offset along -radial unit);
      twirlL  — rotate the local offset CCW about the centre by strength*f radians;
      twirlr  — rotate CW;
      reconstruct — relax the existing displacement toward zero (*= 1 - f*strength).
    Returns the (mutated) dx, dy. Pure NumPy; the full warp reuses `_warp_remap`."""
    h, w = dx.shape
    r = max(1.0, float(radius))
    y0 = max(0, int(cy - r)); y1 = min(h, int(cy + r) + 1)
    x0 = max(0, int(cx - r)); x1 = min(w, int(cx + r) + 1)
    if y0 >= y1 or x0 >= x1:
        return dx, dy
    yy, xx = _np.mgrid[y0:y1, x0:x1].astype(_np.float32)
    ox = xx - cx; oy = yy - cy
    dist = _np.sqrt(ox * ox + oy * oy)
    f = _np.clip(0.5 + 0.5 * _np.cos(_np.pi * _np.clip(dist / r, 0.0, 1.0)), 0.0, 1.0)
    f = (f * (dist <= r)).astype(_np.float32)
    s = float(strength)
    if mode == 'push':
        ddx, ddy = drag
        dx[y0:y1, x0:x1] += ddx * s * f
        dy[y0:y1, x0:x1] += ddy * s * f
    elif mode in ('bloat', 'pinch'):
        sign = 1.0 if mode == 'bloat' else -1.0
        inv = 1.0 / (dist + 1e-6)
        amt = sign * s * r * 0.35 * f
        dx[y0:y1, x0:x1] += ox * inv * amt
        dy[y0:y1, x0:x1] += oy * inv * amt
    elif mode in ('twirll', 'twirlr'):
        sign = 1.0 if mode == 'twirll' else -1.0
        ang = sign * s * f
        ct = _np.cos(ang); st = _np.sin(ang)
        cdx = dx[y0:y1, x0:x1]; cdy = dy[y0:y1, x0:x1]
        # rotate the point's radial position: new offset = R*offset - offset, added in
        nx = ox * ct - oy * st; ny = ox * st + oy * ct
        dx[y0:y1, x0:x1] = cdx + (nx - ox)
        dy[y0:y1, x0:x1] = cdy + (ny - oy)
    elif mode == 'reconstruct':
        keep = (1.0 - _np.clip(f * s, 0.0, 1.0)).astype(_np.float32)
        dx[y0:y1, x0:x1] *= keep
        dy[y0:y1, x0:x1] *= keep
    return dx, dy


def liquify_warp(rgba, dx, dy, force_fallback=False):
    """Apply a displacement map (`dx`/`dy`, float32 HxW = per-pixel source offset) to an
    HxWx(3/4) uint8 image by reusing `_warp_remap`: sample at (X+dx, Y+dy). Pure."""
    src = _ensure_rgba(rgba)
    h, w = src.shape[:2]
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    out = _warp_remap(src, xx + dx, yy + dy, force_fallback=force_fallback)
    return _ensure_rgba(out)


# ---- seedable value-noise / fractal turbulence (for the procedural textures) ----
def _value_noise(h, w, scale, seed=0):
    """A single octave of smooth value noise: a coarse grid of random values at `scale`
    px spacing, bilinearly interpolated up to HxW. Deterministic for a given `seed`.
    Returns a float HxW array in 0..1."""
    scale = max(2.0, float(scale))
    gh = int(math.ceil(h / scale)) + 2
    gw = int(math.ceil(w / scale)) + 2
    rng = _np.random.default_rng(seed)
    grid = rng.random((gh, gw)).astype(_np.float32)
    # bilinear upsample via Pillow's resize (smooth, deterministic)
    big = Image.fromarray((grid * 255).astype('uint8'), 'L').resize((w, h), Image.BILINEAR)
    return _np.asarray(big).astype(_np.float32) / 255.0


def _turbulence(h, w, scale, octaves=4, seed=0):
    """Fractal turbulence: sum several octaves of value noise at halving scale and
    halving amplitude. Deterministic for a given `seed`. Returns float HxW in ~0..1."""
    total = _np.zeros((h, w), _np.float32)
    amp = 1.0; amp_sum = 0.0; s = float(scale)
    for o in range(max(1, int(octaves))):
        total += _value_noise(h, w, s, seed=seed + o * 101) * amp
        amp_sum += amp
        amp *= 0.5
        s = max(2.0, s / 2.0)
    return total / max(1e-6, amp_sum)


def _blend_two(c0, c1, t):
    """Blend two (r,g,b) colours by a float HxW weight t (0→c0, 1→c1). Returns HxWx3."""
    c0 = _np.asarray(c0, _np.float32); c1 = _np.asarray(c1, _np.float32)
    return c0 + (c1 - c0) * t[..., None]


def wood(h, w, spacing=18, turb=0.5, color_a=(150, 95, 45), color_b=(95, 55, 22),
         angle=0, seed=0):
    """EFFECT 7 — procedural wood grain. Concentric growth rings (a sinusoid of the
    distance from a grain axis) are perturbed by fractal turbulence, then the ring
    phase picks between two wood colours. `spacing` sets the ring period (px); `turb`
    warps the rings; `angle` tilts the grain. Deterministic for a given `seed`.
    Returns a fresh HxWx4 uint8 texture (fully opaque)."""
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    a = math.radians(angle)
    # distance from a grain axis running through the centre, rotated by `angle`
    cx, cy = w / 2.0, h / 2.0
    u = (xx - cx) * math.cos(a) + (yy - cy) * math.sin(a)
    v = -(xx - cx) * math.sin(a) + (yy - cy) * math.cos(a)
    rings = _np.sqrt(u * u + (v * 0.25) ** 2)        # elongated rings → plank look
    t = _turbulence(h, w, max(6.0, spacing * 2.0), octaves=4, seed=seed)
    rings = rings + t * spacing * turb * 4.0
    phase = _np.sin(rings / max(1.0, spacing) * math.pi * 2.0) * 0.5 + 0.5
    phase = phase ** 1.3                              # sharpen the dark lines a touch
    rgb = _blend_two(color_a, color_b, phase)
    # a faint lengthwise fibre streak for realism
    fibre = (_value_noise(h, w, 3.0, seed=seed + 7) - 0.5) * 18.0
    rgb = _np.clip(rgb + fibre[..., None], 0, 255)
    return _ensure_rgba(rgb.astype(_np.uint8))


def marble(h, w, scale=40, turb=0.6, sharpness=4.0, vein=(240, 240, 245),
           bg=(60, 70, 90), seed=0):
    """EFFECT 8 — procedural marble veining. A sinusoid across the image is distorted by
    fractal turbulence so the stripes buckle into marble veins; `sharpness` tightens the
    veins, `scale` sets their spacing, `turb` their waviness. Deterministic for `seed`.
    Returns a fresh HxWx4 uint8 texture (opaque)."""
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    t = _turbulence(h, w, max(6.0, float(scale)), octaves=5, seed=seed)
    val = xx / max(1.0, float(scale)) + t * turb * 8.0
    veins = _np.abs(_np.sin(val * math.pi))
    veins = veins ** max(0.2, 1.0 / max(0.2, sharpness))   # higher sharpness → thinner veins
    rgb = _blend_two(bg, vein, veins)
    return _ensure_rgba(rgb.astype(_np.uint8))


def weave(h, w, strand=14, gap=3, color_a=(170, 120, 70), color_b=(120, 80, 45),
          seed=0):
    """EFFECT 9 (stretch) — a basket-weave over/under pattern. Horizontal and vertical
    strands of width `strand` separated by `gap` cross in a checkerboard of which strand
    passes OVER, shaded with a cylindrical highlight so each strand looks rounded.
    Deterministic for `seed` (used only for a faint colour jitter). Returns HxWx4 uint8."""
    yy, xx = _np.mgrid[0:h, 0:w].astype(_np.float32)
    period = float(strand + gap)
    cx = (xx % period); cy = (yy % period)
    in_x = cx < strand                               # on a vertical strand
    in_y = cy < strand                               # on a horizontal strand
    # which strand is on top alternates per cell (basket weave)
    cell_x = _np.floor(xx / period).astype(_np.int32)
    cell_y = _np.floor(yy / period).astype(_np.int32)
    v_over = ((cell_x + cell_y) % 2 == 0)            # vertical strand over here
    # cylindrical shading across each strand (bright centre, dark edges)
    shade_x = _np.sin(_np.clip(cx / max(1.0, strand), 0, 1) * math.pi)
    shade_y = _np.sin(_np.clip(cy / max(1.0, strand), 0, 1) * math.pi)
    rgb = _np.zeros((h, w, 3), _np.float32)
    # base: the gap (shadow between strands)
    rgb[:] = _np.asarray((30, 22, 14), _np.float32)
    # horizontal strands
    horiz = in_y & (~in_x | ~v_over | ~in_y)
    hcol = _np.asarray(color_b, _np.float32)
    rgb = _np.where((in_y & (~in_x | ~v_over))[..., None],
                    hcol * (0.55 + 0.45 * shade_y[..., None]), rgb)
    # vertical strands
    vcol = _np.asarray(color_a, _np.float32)
    rgb = _np.where((in_x & (~in_y | v_over))[..., None],
                    vcol * (0.55 + 0.45 * shade_x[..., None]), rgb)
    rng = _np.random.default_rng(seed)
    jit = (rng.random((h, w, 1)).astype(_np.float32) - 0.5) * 10.0
    rgb = _np.clip(rgb + jit, 0, 255)
    return _ensure_rgba(rgb.astype(_np.uint8))


EXPORT_FORMATS = [
    # (label, pillow format, extension, supports_alpha, has_quality)
    ('PNG', 'PNG', '.png', True, False),
    ('JPEG', 'JPEG', '.jpg', False, True),
    ('WEBP', 'WEBP', '.webp', True, True),
    ('GIF', 'GIF', '.gif', True, False),
    ('BMP', 'BMP', '.bmp', False, False),
]


def _flatten_white(img):
    """Composite `img` (ARGB) over a white background (for formats with no alpha)."""
    flat = QImage(img.size(), QImage.Format_RGB32); flat.fill(QColor('#ffffff'))
    p = QPainter(flat); p.drawImage(0, 0, img); p.end()
    return flat


def export_bytes(img, fmt, quality=90, keep_alpha=True):
    """Encode a QImage to `fmt` (a Pillow format name) and return the file bytes.
    Prefers Pillow so WEBP/GIF/quality all work the same across platforms; falls back
    to Qt's QImage.save via a buffer when Pillow is unavailable."""
    alpha = keep_alpha and fmt in ('PNG', 'WEBP', 'GIF')
    if not alpha:
        img = _flatten_white(img)
    if HAS_PIL:
        import io
        pil = q2pil(img)
        if not alpha:
            pil = pil.convert('RGB')
        buf = io.BytesIO()
        kw = {}
        if fmt == 'JPEG':
            kw = dict(quality=int(quality), optimize=True, progressive=True)
        elif fmt == 'WEBP':
            kw = dict(quality=int(quality))
            if alpha: pil = pil.convert('RGBA')
        elif fmt == 'GIF':
            pil = pil.convert('RGBA') if alpha else pil.convert('RGB')
        pil.save(buf, fmt, **kw)
        return buf.getvalue()
    # Qt fallback
    from PySide6.QtCore import QBuffer, QByteArray
    ba = QByteArray(); b = QBuffer(ba); b.open(QBuffer.WriteOnly)
    qfmt = {'PNG': 'PNG', 'JPEG': 'JPG', 'WEBP': 'WEBP', 'GIF': 'GIF', 'BMP': 'BMP'}[fmt]
    img.save(b, qfmt, int(quality) if fmt in ('JPEG', 'WEBP') else -1)
    return bytes(ba)


# ---- Reduce File Size (optimise / save for web) engine -----------------------
# Modern codecs — AVIF and WebP — beat JPEG badly at equal quality, so the
# optimiser recommends them. AVIF is only offered if this Pillow build can
# actually encode it (older builds, or ones without libavif, can't).
_AVIF_OK = None


def avif_available():
    """True only if this Pillow can genuinely SAVE an AVIF (probed once, lazily).
    Guards the whole feature so we never offer a format that would error on save."""
    global _AVIF_OK
    if _AVIF_OK is None:
        _AVIF_OK = False
        if HAS_PIL:
            try:
                import io
                b = io.BytesIO()
                Image.new('RGB', (8, 8), (90, 120, 160)).save(b, 'AVIF', quality=50)
                _AVIF_OK = len(b.getvalue()) > 0
            except Exception:
                _AVIF_OK = False
    return _AVIF_OK


# (label, pillow format, extension, lossy?)  — PNG is lossless.
def optimise_formats():
    """The formats the optimiser can offer HERE, best-first. AVIF leads when the
    build supports it; WebP/JPEG/PNG always follow (JPEG/WebP need no extra libs)."""
    fmts = []
    if avif_available():
        fmts.append(('AVIF ⭐ (smallest)', 'AVIF', '.avif', True))
    fmts += [
        ('WebP (modern, small)', 'WEBP', '.webp', True),
        ('JPEG (universal)', 'JPEG', '.jpg', True),
        ('PNG (lossless)', 'PNG', '.png', False),
    ]
    return fmts


def _opt_encode(pil, fmt, quality, strip_meta):
    """Encode a prepared RGB/RGBA PIL image to `fmt` bytes at `quality`.
    Lossless PNG uses optimize=True and, for flat (few-colour) images, an adaptive
    palette which is a huge win. strip_meta simply means we never pass exif/icc."""
    import io
    buf = io.BytesIO()
    if fmt == 'JPEG':
        pil.convert('RGB').save(buf, 'JPEG', quality=int(quality), optimize=True, progressive=True)
    elif fmt == 'WEBP':
        pil.save(buf, 'WEBP', quality=int(quality), method=6)
    elif fmt == 'AVIF':
        pil.save(buf, 'AVIF', quality=int(quality))
    elif fmt == 'PNG':
        candidate = pil
        # Palette-quantise flat images (<=256 distinct colours) for a big saving;
        # keep truecolour PNG otherwise so photos don't band.
        try:
            colors = pil.convert('RGB').getcolors(256)
        except Exception:
            colors = None
        if colors is not None:
            mode = 'RGBA' if pil.mode == 'RGBA' else 'RGB'
            candidate = pil.convert(mode).convert('P', palette=Image.ADAPTIVE, colors=256)
        candidate.save(buf, 'PNG', optimize=True)
    else:
        raise ValueError(f'unknown optimise format {fmt}')
    return buf.getvalue()


def optimize_bytes(pil_image, fmt, quality=None, target_kb=None, max_dim=None, strip_meta=True):
    """Encode `pil_image` (a PIL Image) to `fmt` ('AVIF'/'WEBP'/'JPEG'/'PNG') as small
    as sensible, returning the file bytes.

    - max_dim: if set and the longest side is bigger, downscale (Lanczos) so the
      longest side <= max_dim BEFORE encoding — usually the biggest file-size win.
    - strip_meta: never carry EXIF/ICC/other metadata into the output.
    - target_kb (lossy formats): binary-search quality 1..95 to land JUST under the
      target size. When `quality` is given instead, encode at exactly that quality.
      PNG ignores both (lossless) — downscaling/palette do the shrinking.
    """
    if not HAS_PIL:
        raise RuntimeError('Pillow is required for optimize_bytes')
    pil = pil_image
    # Flatten alpha onto white for formats people won't want transparency from here;
    # keep alpha for WebP/AVIF/PNG which support it.
    if fmt == 'JPEG' and pil.mode in ('RGBA', 'LA', 'P'):
        base = Image.new('RGB', pil.size, (255, 255, 255))
        tmp = pil.convert('RGBA')
        base.paste(tmp, mask=tmp.split()[-1])
        pil = base
    # Downscale to cap the longest side.
    if max_dim:
        w, h = pil.size
        longest = max(w, h)
        if longest > max_dim:
            scale = max_dim / float(longest)
            pil = pil.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    if strip_meta:
        # Re-wrap the pixels in a fresh Image so no info/exif tags ride along.
        clean = Image.new(pil.mode, pil.size)
        clean.putdata(list(pil.getdata()))
        pil = clean

    lossy = fmt in ('AVIF', 'WEBP', 'JPEG')
    if lossy and target_kb is not None:
        target = int(target_kb) * 1024
        best = None
        lo, hi = 1, 95
        # Binary-search the highest quality whose output still fits under target.
        while lo <= hi:
            mid = (lo + hi) // 2
            data = _opt_encode(pil, fmt, mid, strip_meta)
            if len(data) <= target:
                best = data; lo = mid + 1          # fits — try for better quality
            else:
                hi = mid - 1                        # too big — drop quality
        if best is None:
            best = _opt_encode(pil, fmt, 1, strip_meta)   # even q=1 overshoots: smallest we can do
        return best

    q = 80 if quality is None else int(quality)
    return _opt_encode(pil, fmt, q, strip_meta)


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

def adj_channelmixer(params):
    """Full 3x3 channel mixer. `params` is a dict:
        mono      -> bool; when True one weight set (mr/mg/mb + moff) drives R=G=B
        rr,rg,rb,roff  -> Red-output   weights (% of each source) + constant (0..255)
        gr,gg,gb,goff  -> Green-output weights + constant
        br,bg,bb,boff  -> Blue-output  weights + constant
        mr,mg,mb,moff  -> monochrome weights + constant (used only when mono)
    Weights are percentages (-200..200 => -2.0..2.0). NumPy matrix multiply on the RGB
    array, then clip to 0..255. Alpha is preserved via _merge_a."""
    g = lambda k, d=0.0: float(params.get(k, d))
    if params.get('mono'):
        wr, wg, wb = g('mr', 40) / 100.0, g('mg', 40) / 100.0, g('mb', 20) / 100.0
        mat = _np.array([[wr, wg, wb]] * 3, _np.float32)                 # same row ->R=G=B
        off = _np.array([g('moff'), g('moff'), g('moff')], _np.float32)
    else:
        mat = _np.array([[g('rr', 100) / 100.0, g('rg') / 100.0, g('rb') / 100.0],
                         [g('gr') / 100.0, g('gg', 100) / 100.0, g('gb') / 100.0],
                         [g('br') / 100.0, g('bg') / 100.0, g('bb', 100) / 100.0]], _np.float32)
        off = _np.array([g('roff'), g('goff'), g('boff')], _np.float32)

    def f(p):
        rgb = _np.asarray(p.convert('RGB')).astype(_np.float32)
        out = rgb @ mat.T + off                                          # (H,W,3)@(3,3)->(H,W,3)
        out = _np.clip(out, 0, 255).astype('uint8')
        return _merge_a(p, Image.fromarray(out, 'RGB'))
    return f


def adj_vibrance(amount):
    """Vibrance: a smart saturation that boosts LOW-saturated pixels more than ones that
    are already vivid (so skin tones and already-colourful areas are protected). `amount`
    is -100..100. Per-pixel saturation s (0..1) is pushed by a gain scaled by (1 - s):
    de-saturated pixels get (1+k) while fully-saturated pixels are left ~unchanged."""
    k = float(amount) / 100.0

    def f(p):
        rgb = _np.asarray(p.convert('RGB')).astype(_np.float32)
        mx = rgb.max(axis=2); mn = rgb.min(axis=2)
        s = _np.where(mx > 0, (mx - mn) / _np.maximum(mx, 1.0), 0.0)     # HSV saturation 0..1
        y = _luma(rgb)                                                   # grey axis to scale about
        gain = 1.0 + k * (1.0 - s)                                       # less boost where s is high
        out = y[..., None] + (rgb - y[..., None]) * gain[..., None]
        out = _np.clip(out, 0, 255).astype('uint8')
        return _merge_a(p, Image.fromarray(out, 'RGB'))
    return f


def _soft_disc(h, w, cx, cy, radius):
    """A feathered circular alpha (HxW float 0..1) centred at (cx,cy): 1 in the core,
    falling smoothly to 0 at `radius`. Used as the soft-dab weight for retouch brushes."""
    yy, xx = _np.ogrid[0:h, 0:w]
    d = _np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return _np.clip(1.0 - d / max(1.0, radius), 0.0, 1.0) ** 1.4


def heal_patch(rgb, cx, cy, radius, strength=1.0):
    """Spot-heal one dab, returning a NEW HxWx3 float/uint array (same dtype in → uint8-safe
    float out). Unlike Clone it does NOT copy verbatim: it rebuilds the dab from the texture
    JUST OUTSIDE the brush via frequency separation.
      low  = heavy Gaussian blur of the neighbourhood (lighting / colour gradient)
      high = neighbourhood − low (fine texture / grain)
    healed = low + strength*high, sampled at the dab, blended over the original by a soft disc.
    The 'clean surround' is the ring outside the circle: the low-freq there is extended across
    the blemish by the blur (the blemish barely perturbs a heavily-blurred field), so a small
    bright spot is replaced by the surrounding colour + a little preserved grain.
    Pure NumPy+Pillow, no GUI; testable on any image array."""
    a = _np.asarray(rgb).astype(_np.float32)
    H, W = a.shape[:2]
    r = max(1.0, float(radius))
    pad = int(r * 1.6) + 2                                   # margin so the surround is real texture
    x0, y0 = max(0, int(cx - r - pad)), max(0, int(cy - r - pad))
    x1, y1 = min(W, int(cx + r + pad) + 1), min(H, int(cy + r + pad) + 1)
    if x1 <= x0 or y1 <= y0: return a
    box = a[y0:y1, x0:x1, :3].copy()
    bh, bw = box.shape[:2]
    lx, ly = cx - x0, cy - y0                                # dab centre in box coords
    # mask the blemish OUT before estimating the field, so it can't bias low/high
    disc = _soft_disc(bh, bw, lx, ly, r)
    hole = disc > 0.02
    blur_r = max(2.0, r * 0.9)
    filled = box.copy()
    if hole.any():
        # seed the hole with the mean of the surrounding ring so the blur interpolates across it
        ring = (~hole)
        if ring.any():
            surround_mean = box[ring].mean(axis=0)
        else:
            surround_mean = box.reshape(-1, 3).mean(axis=0)
        filled[hole] = surround_mean
    low_src = Image.fromarray(_np.clip(filled, 0, 255).astype('uint8'), 'RGB') \
                   .filter(ImageFilter.GaussianBlur(blur_r))
    low = _np.asarray(low_src).astype(_np.float32)           # smooth field, blemish removed
    # high-freq texture taken from the ORIGINAL surround (blurred-field subtracted)
    orig_low = _np.asarray(Image.fromarray(_np.clip(box, 0, 255).astype('uint8'), 'RGB')
                           .filter(ImageFilter.GaussianBlur(blur_r))).astype(_np.float32)
    high = box - orig_low
    high *= (1.0 - disc[..., None])                          # drop the blemish's own high-freq spike
    healed = low + float(strength) * high
    wgt = disc[..., None]
    box[:] = healed * wgt + box * (1.0 - wgt)
    a[y0:y1, x0:x1, :3] = _np.clip(box, 0, 255)
    return a


def sponge_patch(rgb, cx, cy, radius, amount):
    """Local saturation brush, returning a NEW HxWx3 array. amount>0 saturates, <0 desaturates
    (-100..100-ish). Pushes each pixel's RGB toward (amount>0) or away from (amount<0) its own
    luma — the same grey-axis scaling adj_vibrance/adj_saturation use — within a soft disc so
    repeated dabs are seamless. Pixels outside `radius` are untouched. Pure NumPy."""
    a = _np.asarray(rgb).astype(_np.float32)
    H, W = a.shape[:2]
    r = max(1.0, float(radius))
    x0, y0 = max(0, int(cx - r)), max(0, int(cy - r))
    x1, y1 = min(W, int(cx + r) + 1), min(H, int(cy + r) + 1)
    if x1 <= x0 or y1 <= y0: return a
    box = a[y0:y1, x0:x1, :3]
    bh, bw = box.shape[:2]
    disc = _soft_disc(bh, bw, cx - x0, cy - y0, r)
    gain = 1.0 + (float(amount) / 100.0) * disc                    # >1 saturate, <1 desaturate
    y = _luma(box)[..., None]
    out = y + (box - y) * gain[..., None]
    a[y0:y1, x0:x1, :3] = _np.clip(out, 0, 255)
    return a


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

def adj_shadow_highlight(shadow_amt, highlight_amt, radius=30, mid=0):
    """PhotoPlus-style Shadow/Highlight: lift shadows and recover highlights independently,
    each gated by a luminance mask so only the matching tonal zone moves.
      L  = luma/255 (0..1).  shadow_mask = (1-L)^k, highlight_mask = L^k  (k=2, soft zones).
      When `radius`>0 the masks are Gaussian-blurred so the correction follows local tonal
      regions (the signature local/adaptive behaviour) rather than a flat per-pixel curve.
      shadow_amt (0..100):  out += a_s * shadow_mask * (255 - L*255)      -> brightens darks,
                            scaled by the headroom so near-white shadows barely move.
      highlight_amt (0..100): out -= a_h * highlight_mask * (L*255)        -> pulls brights down.
      mid (-100..100): optional midtone-contrast term, S-curve about 128 weighted by 4L(1-L).
    All in float then clipped 0..255; alpha preserved via _merge_a."""
    a_s = max(0.0, float(shadow_amt)) / 100.0
    a_h = max(0.0, float(highlight_amt)) / 100.0
    m = float(mid) / 100.0
    r = max(0.0, float(radius))

    def f(p):
        rgb = _np.asarray(p.convert('RGB')).astype(_np.float32)
        L = _luma(rgb) / 255.0                                  # 0..1 luminance
        shadow_mask = (1.0 - L) ** 2
        highlight_mask = L ** 2
        if r > 0:                                               # local tonal-zone masks
            shadow_mask = _np.asarray(Image.fromarray((shadow_mask * 255).astype('uint8'), 'L')
                                      .filter(ImageFilter.GaussianBlur(r)), _np.float32) / 255.0
            highlight_mask = _np.asarray(Image.fromarray((highlight_mask * 255).astype('uint8'), 'L')
                                         .filter(ImageFilter.GaussianBlur(r)), _np.float32) / 255.0
        out = rgb.copy()
        out += (a_s * shadow_mask * (255.0 - L * 255.0))[..., None]      # lift shadows
        out -= (a_h * highlight_mask * (L * 255.0))[..., None]           # recover highlights
        if abs(m) > 1e-6:                                                # midtone contrast
            mid_w = 4.0 * L * (1.0 - L)                                  # peaks at mid grey
            out += (m * mid_w * (L * 255.0 - 128.0))[..., None]
        out = _np.clip(out, 0, 255).astype('uint8')
        return _merge_a(p, Image.fromarray(out, 'RGB'))
    return f


# Hue-family centres (degrees) for Selective Colour. Neutrals/whites/blacks are value-gated.
SELECTIVE_RANGES = ['Reds', 'Yellows', 'Greens', 'Cyans', 'Blues', 'Magentas',
                    'Whites', 'Neutrals', 'Blacks']
_SELECTIVE_HUE = {'Reds': 0, 'Yellows': 60, 'Greens': 120,
                  'Cyans': 180, 'Blues': 240, 'Magentas': 300}

def adj_selective_color(color_range, c, m, y, k):
    """PhotoPlus-style Selective Colour: nudge one colour family by CMYK percentages.
    `color_range` is one of SELECTIVE_RANGES. c/m/y/k are -100..100 (relative mode).
      Hue families (Reds..Magentas): per-pixel membership = triangular falloff of the HSV
        hue distance to the family centre (full within ±30°, zero by ±60°), gated by
        saturation*value so grey/near-black pixels don't count as a colour.
      Whites: membership = high value AND low saturation.  Blacks: low value.
        Neutrals: low saturation across the midtones.
      CMYK mapping (subtractive, applied scaled by membership w, relative to headroom):
        cyan+   darkens Red   : R -= c * w * R
        magenta+ darkens Green: G -= m * w * G
        yellow+ darkens Blue  : B -= y * w * B
        black+  darkens all   : RGB -= k * w * RGB     (negatives lighten toward 255)
    Clamped 0..255; alpha preserved."""
    cc, mm, yy, kk = (float(c) / 100.0, float(m) / 100.0, float(y) / 100.0, float(k) / 100.0)

    def f(p):
        rgb = _np.asarray(p.convert('RGB')).astype(_np.float32)
        hsv = _np.asarray(p.convert('HSV')).astype(_np.float32)
        H = hsv[..., 0] * 360.0 / 255.0                         # hue degrees 0..360
        S = hsv[..., 1] / 255.0
        V = hsv[..., 2] / 255.0
        if color_range in _SELECTIVE_HUE:
            centre = _SELECTIVE_HUE[color_range]
            d = _np.abs(((H - centre + 180.0) % 360.0) - 180.0)        # circular hue distance
            w = _np.clip(1.0 - (d - 30.0) / 30.0, 0.0, 1.0)            # full ≤30°, 0 by 60°
            w = w * S * V                                              # only real, lit colour
        elif color_range == 'Whites':
            w = _np.clip((V - 0.6) / 0.4, 0.0, 1.0) * _np.clip(1.0 - S / 0.3, 0.0, 1.0)
        elif color_range == 'Blacks':
            w = _np.clip(1.0 - V / 0.4, 0.0, 1.0)
        else:                                                          # Neutrals
            w = _np.clip(1.0 - S / 0.35, 0.0, 1.0) * (4.0 * V * (1.0 - V))
        out = rgb.copy()
        def shift(ch, amt):                                            # subtractive nudge on one channel
            if amt >= 0:  return -amt * w * out[..., ch]               # darken toward 0
            return -amt * w * (255.0 - out[..., ch])                   # lighten toward 255
        out[..., 0] += shift(0, cc)
        out[..., 1] += shift(1, mm)
        out[..., 2] += shift(2, yy)
        if abs(kk) > 1e-6:
            for ch in range(3):
                out[..., ch] += shift(ch, kk)
        out = _np.clip(out, 0, 255).astype('uint8')
        return _merge_a(p, Image.fromarray(out, 'RGB'))
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


# ----------------------------------------------------------------------------
# Lens Flare — a clean-room Knoll-Light-Factory-style flare renderer.
#
# A flare is a bright light source at (lx, ly) that scatters a chain of lens
# artefacts along the axis running from the source, through the frame centre and
# out the far side: a glowing core, star spikes / streaks, a string of hexagonal
# and circular iris (aperture) reflections at decreasing size and opacity, an
# optional rainbow (diffraction) ring and a faint halo. Everything is drawn onto
# a transparent ARGB32 image with QPainter, meant to be composited Screen over the
# picture. It's all gradients and polygons — fast at normal canvas sizes.
# ----------------------------------------------------------------------------

# Preset parameter bundles for the dialog. Each is a full `params` dict; the
# dialog fills missing keys from LENS_FLARE_DEFAULTS.
LENS_FLARE_DEFAULTS = {
    'brightness': 1.0,     # master gain, ~0.2..2.0
    'scale': 1.0,          # overall size multiplier, ~0.4..2.0
    'hue': 42.0,           # tint hue in degrees (0 red, 42 warm gold, 210 blue)
    'warmth': 0.5,         # 0 = white/neutral core, 1 = fully tinted
    'spikes': True,        # star spikes / streaks from the source
    'spike_count': 6,      # number of radial spikes
    'anamorphic': False,   # extra long horizontal streak (cinematic)
    'reflections': True,   # chain of iris reflections along the axis
    'rainbow': False,      # diffraction (hue-swept) ring near the axis
    'halo': True,          # faint ring around the frame centre
    'seed': 7,             # arrangement seed (reflection placement/tint)
}

LENS_FLARE_PRESETS = {
    'Subtle': {'brightness': 0.6, 'scale': 0.85, 'hue': 44, 'warmth': 0.45,
               'spikes': True, 'spike_count': 4, 'anamorphic': False,
               'reflections': True, 'rainbow': False, 'halo': True, 'seed': 3},
    'Sunny': {'brightness': 1.15, 'scale': 1.1, 'hue': 40, 'warmth': 0.7,
              'spikes': True, 'spike_count': 8, 'anamorphic': False,
              'reflections': True, 'rainbow': True, 'halo': True, 'seed': 7},
    'Anamorphic': {'brightness': 1.0, 'scale': 1.0, 'hue': 205, 'warmth': 0.8,
                   'spikes': True, 'spike_count': 2, 'anamorphic': True,
                   'reflections': True, 'rainbow': False, 'halo': True, 'seed': 11},
    'Sci-fi': {'brightness': 1.3, 'scale': 1.25, 'hue': 190, 'warmth': 0.85,
               'spikes': True, 'spike_count': 12, 'anamorphic': True,
               'reflections': True, 'rainbow': True, 'halo': True, 'seed': 19},
}


def _flare_tint(hue, warmth, light=0.55):
    """A tint colour from hue (deg) and warmth (0 neutral white .. 1 saturated)."""
    c = QColor()
    c.setHslF((hue % 360) / 360.0, max(0.0, min(1.0, warmth)), max(0.0, min(1.0, light)))
    return c


def render_lens_flare(w, h, lx, ly, params=None):
    """Render a lens flare over a transparent `w`x`h` ARGB32 QImage and return it.

    The light source sits at (lx, ly); artefacts stream along the axis from the
    source through the image centre. `params` keys (see LENS_FLARE_DEFAULTS) tune
    brightness, scale, hue/warmth, spike count and which elements are drawn. The
    result is transparent except for the flare, so composite it Screen / Add over
    the picture. Uses only QPainter — no Pillow required."""
    p = dict(LENS_FLARE_DEFAULTS); p.update(params or {})
    out = QImage(int(w), int(h), QImage.Format_ARGB32); out.fill(Qt.transparent)
    q = QPainter(out)
    q.setRenderHint(QPainter.Antialiasing, True)
    q.setCompositionMode(QPainter.CompositionMode_Plus)   # lights add up

    cx, cy = w / 2.0, h / 2.0
    lx = float(lx); ly = float(ly)
    diag = (w * w + h * h) ** 0.5
    bright = max(0.0, float(p['brightness']))
    scale = max(0.05, float(p['scale']))
    hue = float(p['hue']); warmth = max(0.0, min(1.0, float(p['warmth'])))
    unit = diag * 0.06 * scale                      # base element radius

    def a(x):                                        # clamp an alpha 0..255
        return int(max(0, min(255, round(x * bright))))

    # --- glow core: a bright near-white centre fading through the tint ---
    core_r = unit * 2.4
    g = QRadialGradient(QPointF(lx, ly), core_r)
    tint = _flare_tint(hue, warmth)
    inner = QColor(255, 255, 255, a(255))
    mid = QColor(tint.red(), tint.green(), tint.blue(), a(150))
    g.setColorAt(0.0, inner)
    g.setColorAt(0.18, QColor(255, 255, 255, a(200)))
    g.setColorAt(0.5, mid)
    g.setColorAt(1.0, QColor(tint.red(), tint.green(), tint.blue(), 0))
    q.setBrush(QBrush(g)); q.setPen(Qt.NoPen)
    q.drawEllipse(QPointF(lx, ly), core_r, core_r)

    # a tight hot centre on top
    g2 = QRadialGradient(QPointF(lx, ly), unit * 0.7)
    g2.setColorAt(0.0, QColor(255, 255, 255, a(255)))
    g2.setColorAt(1.0, QColor(255, 255, 255, 0))
    q.setBrush(QBrush(g2)); q.drawEllipse(QPointF(lx, ly), unit * 0.7, unit * 0.7)

    # --- star spikes / streaks radiating from the source ---
    if p['spikes']:
        n = max(1, int(p['spike_count']))
        base_len = unit * 5.5
        for i in range(n):
            ang = (math.pi * i / n) + 0.3      # spikes come in opposite pairs
            dx, dy = math.cos(ang), math.sin(ang)
            length = base_len * (0.7 + 0.6 * ((i * 37) % 10) / 10.0)
            _draw_spike(q, lx, ly, dx, dy, length, unit * 0.12, tint, a(170))
            _draw_spike(q, lx, ly, -dx, -dy, length, unit * 0.12, tint, a(170))
        # a short fat 4-way glint
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            _draw_spike(q, lx, ly, dx, dy, unit * 2.6, unit * 0.22,
                        QColor(255, 255, 255), a(150))

    # --- anamorphic horizontal streak (cinematic blue bar) ---
    if p['anamorphic']:
        streak_len = w * 0.9
        lg = QLinearGradient(QPointF(lx - streak_len, ly), QPointF(lx + streak_len, ly))
        bar = _flare_tint(hue if warmth > 0 else 205, max(0.6, warmth), 0.6)
        for pos, al in ((0.0, 0), (0.5, a(130)), (1.0, 0)):
            c = QColor(bar); c.setAlpha(al if pos == 0.5 else 0); lg.setColorAt(pos, c)
        q.setBrush(QBrush(lg)); q.setPen(Qt.NoPen)
        q.drawRect(QRectF(lx - streak_len, ly - unit * 0.14, streak_len * 2, unit * 0.28))

    # --- chain of iris reflections along source -> centre -> far side ---
    if p['reflections']:
        rng = random.Random(int(p['seed']))
        axis_dx, axis_dy = cx - lx, cy - ly
        # parametric spots along the axis: t=0 at source, t=1 at centre, >1 beyond.
        spots = [0.45, 0.75, 1.0, 1.28, 1.6, 1.95, 2.35]
        for i, t in enumerate(spots):
            x = lx + axis_dx * t
            y = ly + axis_dy * t
            # size shrinks then the far discs grow a little — natural-looking
            sz = unit * (1.5 - 0.28 * i) if i < 4 else unit * (0.5 + 0.22 * (i - 3))
            sz = max(unit * 0.3, abs(sz)) * (0.8 + rng.random() * 0.5)
            op = a((0.5 - 0.045 * i) * 140)
            if op <= 0:
                continue
            spot_hue = (hue + rng.uniform(-60, 90)) % 360
            col = _flare_tint(spot_hue, min(1.0, warmth + 0.2), 0.55)
            if i % 2 == 0:
                _draw_hexagon(q, x, y, sz, col, op, rng.uniform(0, math.pi))
            else:
                _draw_soft_disc(q, x, y, sz, col, op)

    # --- rainbow diffraction ring (hue-swept arc near the axis) ---
    if p['rainbow']:
        rx = lx + (cx - lx) * 1.15
        ry = ly + (cy - ly) * 1.15
        _draw_rainbow_ring(q, rx, ry, unit * 2.2, a(90))

    # --- faint halo ring around the frame centre ---
    if p['halo']:
        halo_r = unit * 3.6
        hg = QRadialGradient(QPointF(cx, cy), halo_r)
        ht = _flare_tint(hue, warmth * 0.7, 0.5)
        hg.setColorAt(0.0, QColor(ht.red(), ht.green(), ht.blue(), 0))
        hg.setColorAt(0.82, QColor(ht.red(), ht.green(), ht.blue(), 0))
        hg.setColorAt(0.9, QColor(ht.red(), ht.green(), ht.blue(), a(70)))
        hg.setColorAt(1.0, QColor(ht.red(), ht.green(), ht.blue(), 0))
        q.setBrush(QBrush(hg)); q.setPen(Qt.NoPen)
        q.drawEllipse(QPointF(cx, cy), halo_r, halo_r)

    q.end()
    return out


def _draw_spike(q, x, y, dx, dy, length, halfw, color, alpha):
    """A tapered needle of light from (x,y) in direction (dx,dy)."""
    nx, ny = -dy, dx                                 # perpendicular
    tip = QPointF(x + dx * length, y + dy * length)
    base_l = QPointF(x + nx * halfw, y + ny * halfw)
    base_r = QPointF(x - nx * halfw, y - ny * halfw)
    poly = QPolygonF([base_l, tip, base_r])
    lg = QLinearGradient(QPointF(x, y), tip)
    c0 = QColor(color); c0.setAlpha(alpha)
    c1 = QColor(color); c1.setAlpha(0)
    lg.setColorAt(0.0, c0); lg.setColorAt(1.0, c1)
    q.setBrush(QBrush(lg)); q.setPen(Qt.NoPen)
    q.drawPolygon(poly)


def _draw_hexagon(q, x, y, r, color, alpha, rot=0.0):
    """A flat, slightly soft-edged hexagonal iris reflection."""
    pts = []
    for k in range(6):
        ang = rot + math.pi / 3.0 * k
        pts.append(QPointF(x + math.cos(ang) * r, y + math.sin(ang) * r))
    poly = QPolygonF(pts)
    g = QRadialGradient(QPointF(x, y), r)
    c_in = QColor(color); c_in.setAlpha(alpha)
    c_edge = QColor(color); c_edge.setAlpha(int(alpha * 0.85))
    c_out = QColor(color); c_out.setAlpha(0)
    g.setColorAt(0.0, c_in); g.setColorAt(0.75, c_edge); g.setColorAt(1.0, c_out)
    q.setBrush(QBrush(g)); q.setPen(QPen(QColor(color.red(), color.green(), color.blue(),
                                               int(alpha * 0.6)), max(1.0, r * 0.04)))
    q.drawPolygon(poly)


def _draw_soft_disc(q, x, y, r, color, alpha):
    """A soft circular reflection (fuzzy aperture ghost)."""
    g = QRadialGradient(QPointF(x, y), r)
    c_in = QColor(color); c_in.setAlpha(alpha)
    c_mid = QColor(color); c_mid.setAlpha(int(alpha * 0.4))
    c_out = QColor(color); c_out.setAlpha(0)
    g.setColorAt(0.0, c_in); g.setColorAt(0.6, c_mid); g.setColorAt(1.0, c_out)
    q.setBrush(QBrush(g)); q.setPen(Qt.NoPen)
    q.drawEllipse(QPointF(x, y), r, r)


def _draw_rainbow_ring(q, x, y, r, alpha):
    """A thin hue-swept diffraction ring (clean-room — a conical sweep, masked to a
    ring band by stroking a circle)."""
    cg = QConicalGradient(QPointF(x, y), 0)
    for k in range(13):
        c = QColor(); c.setHslF((k / 12.0) % 1.0, 0.9, 0.55); c.setAlpha(alpha)
        cg.setColorAt(k / 12.0, c)
    pen = QPen(QBrush(cg), max(2.0, r * 0.14)); pen.setCapStyle(Qt.FlatCap)
    q.setBrush(Qt.NoBrush); q.setPen(pen)
    q.drawEllipse(QPointF(x, y), r, r)


BLENDS = {
    'normal': QPainter.CompositionMode_SourceOver, 'multiply': QPainter.CompositionMode_Multiply,
    'screen': QPainter.CompositionMode_Screen, 'overlay': QPainter.CompositionMode_Overlay,
    'darken': QPainter.CompositionMode_Darken, 'lighten': QPainter.CompositionMode_Lighten,
    'add': QPainter.CompositionMode_Plus, 'difference': QPainter.CompositionMode_Difference,
}
# Modes Qt can't do natively — composited by hand via blend_arrays() (NumPy). The
# first eight above stay on the fast Qt CompositionMode path and are byte-identical.
NP_BLENDS = ['soft-light', 'hard-light', 'color-dodge', 'color-burn', 'linear-burn',
             'linear-light', 'vivid-light', 'pin-light', 'exclusion', 'subtract', 'divide',
             'hue', 'saturation', 'color', 'luminosity']
BLEND_NAMES = ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'add',
               'difference'] + NP_BLENDS


# ---- NumPy compositing (PhotoPlus blend modes Qt lacks) --------------------
def _hsl_lum(c):
    """Luma of RGB float array (…,3) per the W3C non-separable blend spec."""
    return 0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2]


def _hsl_set_lum(c, lum):
    """Return c (…,3) shifted so its luma equals `lum` (…), clipped into gamut."""
    d = (lum - _hsl_lum(c))[..., None]
    c = c + d
    l = _hsl_lum(c)[..., None]
    mn = c.min(axis=-1, keepdims=True); mx = c.max(axis=-1, keepdims=True)
    lo = l + (c - l) * l / _np.where(l - mn == 0, 1.0, l - mn)
    hi = l + (c - l) * (1.0 - l) / _np.where(mx - l == 0, 1.0, mx - l)
    c = _np.where(mn < 0, lo, c)
    c = _np.where(mx > 1, hi, c)
    return c


def _hsl_sat(c):
    return c.max(axis=-1) - c.min(axis=-1)


def _hsl_set_sat(c, sat):
    """Scale c (…,3) so its mid/max/min span equals `sat` (…), per W3C SetSat."""
    c = c.copy(); sat = sat[..., None]
    mn = c.min(axis=-1, keepdims=True); mx = c.max(axis=-1, keepdims=True)
    span = mx - mn
    scaled = _np.where(span == 0, 0.0, (c - mn) * sat / _np.where(span == 0, 1.0, span))
    return scaled  # min→0, max→sat, mid interpolated


def blend_arrays(base, top, mode):
    """Blend two RGB float arrays (…,3) in 0..1 by `mode`, returning a new RGB array.
    `base` is the backdrop, `top` the layer painted over it. Separable modes act
    channel-wise; hue/saturation/color/luminosity are the W3C non-separable modes."""
    b = base; s = top
    if mode == 'soft-light':                    # W3C formula
        d = _np.where(b <= 0.25, ((16 * b - 12) * b + 4) * b, _np.sqrt(_np.clip(b, 0, 1)))
        r = _np.where(s <= 0.5, b - (1 - 2 * s) * b * (1 - b),
                      b + (2 * s - 1) * (d - b))
    elif mode == 'hard-light':                  # overlay with layers swapped
        r = _np.where(s <= 0.5, 2 * b * s, 1 - 2 * (1 - b) * (1 - s))
    elif mode == 'color-dodge':
        r = _np.where(s >= 1, 1.0, _np.minimum(1.0, b / (1 - s + 1e-12)))
        r = _np.where(b <= 0, 0.0, r)
    elif mode == 'color-burn':
        r = _np.where(s <= 0, 0.0, 1 - _np.minimum(1.0, (1 - b) / (s + 1e-12)))
        r = _np.where(b >= 1, 1.0, r)
    elif mode == 'linear-burn':
        r = b + s - 1
    elif mode == 'linear-light':
        r = b + 2 * s - 1
    elif mode == 'vivid-light':                 # dodge/burn by the layer
        burn = _np.where(s <= 0, 0.0, 1 - _np.minimum(1.0, (1 - b) / (2 * s + 1e-12)))
        dodge = _np.where(s >= 1, 1.0, _np.minimum(1.0, b / (2 * (1 - s) + 1e-12)))
        r = _np.where(s <= 0.5, burn, dodge)
    elif mode == 'pin-light':
        r = _np.where(s > 0.5, _np.maximum(b, 2 * s - 1), _np.minimum(b, 2 * s))
    elif mode == 'exclusion':
        r = b + s - 2 * b * s
    elif mode == 'subtract':
        r = b - s
    elif mode == 'divide':
        r = _np.minimum(1.0, b / (s + 1e-12))
    elif mode in ('hue', 'saturation', 'color', 'luminosity'):
        if mode == 'hue':
            r = _hsl_set_lum(_hsl_set_sat(s, _hsl_sat(b)), _hsl_lum(b))
        elif mode == 'saturation':
            r = _hsl_set_lum(_hsl_set_sat(b, _hsl_sat(s)), _hsl_lum(b))
        elif mode == 'color':
            r = _hsl_set_lum(s, _hsl_lum(b))
        else:  # luminosity
            r = _hsl_set_lum(b, _hsl_lum(s))
    else:
        r = s                                   # unknown → plain normal
    return _np.clip(r, 0.0, 1.0)


def composite_np(base_q, top_q, mode, opacity):
    """Composite the top QImage over the base QImage (both ARGB32, same size) using a
    NumPy blend `mode` at `opacity` (0..1), honouring the top layer's own alpha. The
    blended colour is formed per the W3C rule  out = (1-αs)·Cb + αs·B(Cb,Cs),  then
    alpha-composited over the backdrop so transparent top pixels leave the base shown.
    Returns a NEW ARGB32 QImage."""
    base = _np.asarray(q2pil(base_q).convert('RGBA')).astype(_np.float32) / 255.0
    tp = _np.asarray(q2pil(top_q).convert('RGBA')).astype(_np.float32) / 255.0
    cb, ab = base[..., :3], base[..., 3:4]
    cs, as_ = tp[..., :3], tp[..., 3:4] * float(opacity)
    blended = blend_arrays(cb, cs, mode)                 # B(Cb, Cs)
    # colour the top "paints" = mix of straight layer colour and the blended result,
    # weighted by how opaque the backdrop is underneath (W3C: Cs = (1-ab)·Cs + ab·B)
    src = (1.0 - ab) * cs + ab * blended
    out_a = as_ + ab * (1.0 - as_)
    out_rgb = _np.where(out_a > 0, (as_ * src + ab * (1.0 - as_) * cb) / _np.where(out_a > 0, out_a, 1.0), 0.0)
    out = _np.concatenate([out_rgb, out_a], axis=-1)
    return pil2q(Image.fromarray((_np.clip(out, 0, 1) * 255.0 + 0.5).astype('uint8'), 'RGBA'))


# ---- Gradient Map adjustment -----------------------------------------------
def _stops_lut(stops):
    """Build a 256x3 uint8 LUT by sampling a sorted multi-stop gradient
    ([{pos 0..1, color '#rrggbb'}]) across luminance 0..255. Dark→first, light→last."""
    ss = sorted(stops, key=lambda s: max(0.0, min(1.0, float(s['pos']))))
    pos = [max(0.0, min(1.0, float(s['pos']))) for s in ss]
    cols = [QColor(s['color']) for s in ss]
    xs = _np.arange(256) / 255.0
    r = _np.interp(xs, pos, [c.red() for c in cols])
    g = _np.interp(xs, pos, [c.green() for c in cols])
    b = _np.interp(xs, pos, [c.blue() for c in cols])
    return _np.stack([r, g, b], axis=1).round().clip(0, 255).astype(_np.uint8)


def adj_gradientmap(stops):
    """Map image luminance through a colour gradient: build a 256-entry LUT from
    `stops`, index it by each pixel's luma. Preserves alpha."""
    lut = _stops_lut(stops)

    def f(p):
        a = _np.asarray(p.convert('RGB')).astype(_np.float32)
        y = _luma(a).round().clip(0, 255).astype(_np.intp)
        return _merge_a(p, Image.fromarray(lut[y], 'RGB'))
    return f


GRADMAP_PRESETS = {
    'Black → White': [{'pos': 0.0, 'color': '#000000'}, {'pos': 1.0, 'color': '#ffffff'}],
    'Sepia duotone': [{'pos': 0.0, 'color': '#1b1008'}, {'pos': 0.5, 'color': '#8a5a2b'},
                      {'pos': 1.0, 'color': '#f5e6c8'}],
    'Cold → Warm': [{'pos': 0.0, 'color': '#0b1e4d'}, {'pos': 0.5, 'color': '#b14b7a'},
                    {'pos': 1.0, 'color': '#ffd27f'}],
    'Violet → Lime': [{'pos': 0.0, 'color': '#2a0845'}, {'pos': 0.5, 'color': '#6441a5'},
                      {'pos': 1.0, 'color': '#c6f432'}],
}


class Layer:
    def __init__(self, img, name='Layer', visible=True, opacity=1.0, blend='normal', mask=None):
        self.img = img; self.name = name; self.visible = visible
        self.opacity = opacity; self.blend = blend
        # mask: optional greyscale QImage (Format_Grayscale8, white=opaque, black=hidden)
        # the same pixel size as img, or None for no mask.
        self.mask = mask

    def masked_img(self):
        """The layer image with its mask baked into the alpha channel (white=opaque,
        black=hidden), or the plain image if there is no mask. Non-destructive — the
        stored img/mask are untouched; a fresh QImage is returned for compositing."""
        if self.mask is None:
            return self.img
        return apply_mask(self.img, self.mask)


class Canvas(QWidget):
    HIST = 24

    def __init__(self, win, w=1000, h=700):
        super().__init__()
        self.win = win
        base = QImage(w, h, QImage.Format_ARGB32); base.fill(QColor('#ffffff'))
        self.layers = [Layer(base, 'Background')]
        self.active = 0
        self.zoom = 1.0
        self.edit_mask = False          # when True, brush/eraser paint the layer's mask
        self.shape_fill = 'stroke'      # rect/ellipse mode: 'stroke' | 'fill' | 'both'
        self.shape_fill_color = None    # None = use current colour for the fill
        self.grad_start = QColor('#1f2a30')   # gradient tool start colour
        self.grad_end = QColor('#ffffff')     # gradient tool end colour
        self.grad_end_transparent = False      # True = fade end to transparent (legacy)
        self.tool = 'brush'
        self.color = QColor('#1f2a30')
        self.size = 6
        self.cutout_tol = 45
        self.heal_strength = 0.6       # Heal brush: how much surround texture to add back (0..1)
        self.sponge_mode = 'saturate'  # Sponge brush: 'saturate' | 'desaturate'
        self.sponge_flow = 25          # Sponge strength per dab (0..100)
        self.wand_tol = 32             # magic-wand colour tolerance (0..255-ish)
        self.wand_contiguous = True    # wand selects a connected region vs. the whole image
        # Smart Mask (Fluid-Mask-style) scribbles: two bool HxW overlays painted over
        # the image (never altering it) — KEEP marks the subject, REMOVE the background.
        self.sm_keep = None            # bool HxW ndarray or None
        self.sm_remove = None          # bool HxW ndarray or None
        self.sm_brush = 18             # scribble brush diameter (px)
        self.sm_mode = 'keep'          # which scribble the left-drag paints: 'keep' | 'remove'
        self.last = None
        self.start = None
        self.preview = None            # (tool, QPoint start, QPoint cur) while dragging a shape
        # Selection. Either None, a marquee {'rect':QRect,'kind':'rect'|'ellipse'}, or a
        # free-form mask {'kind':'mask','mask':uint8 HxW ndarray (0..255; >0 = selected,
        # intermediate values = feathered edge)}. sel_mask() turns any of them into a mask.
        self.sel = None
        self.sel_drag = None           # (start, cur) while dragging a marquee
        self.lasso_pts = None          # [QPoint,...] while dragging a freehand Lasso
        self.poly_pts = None           # [QPoint,...] vertices placed by the Polygon tool
        self.poly_cur = None           # live cursor point for the Polygon rubber line
        self.clone_src = None          # clone-tool source anchor (Ctrl-click)
        self.clone_off = None          # clone offset once a stroke begins
        self.clone_base = None         # snapshot of the layer cloned FROM
        # --- Free Transform (tool 'transform') live state. When active, tf holds
        # a dict: base (cached original QImage of the active layer), bbox (content
        # rect x,y,w,h), sx/sy scale, angle deg, skew (kx,ky), plus drag bookkeeping.
        self.tf = None
        self.undo, self.redo = [], []
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)     # so the Polygon tool can get Enter/Escape
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
        for i, l in enumerate(self.layers):
            if not l.visible or l.opacity <= 0: continue
            if self.tf is not None and i == self.active: continue   # hidden; shown transformed in paintEvent
            if HAS_PIL and l.blend in NP_BLENDS:
                # NumPy blend: hand the accumulator + this layer to composite_np, then
                # resume drawing onto the result. Qt-native modes keep the fast path.
                p.end()
                base = composite_np(base, l.masked_img(), l.blend, l.opacity)
                p = QPainter(base)
                continue
            p.setOpacity(l.opacity)
            p.setCompositionMode(BLENDS.get(l.blend, QPainter.CompositionMode_SourceOver))
            p.drawImage(0, 0, l.masked_img())
        p.end()
        return base

    def _copy_layers(self):
        return [Layer(l.img.copy(), l.name, l.visible, l.opacity, l.blend,
                      l.mask.copy() if l.mask is not None else None) for l in self.layers]

    def _unique_name(self, stem):
        taken = {l.name for l in self.layers}; i = 1
        while f'{stem} {i}' in taken: i += 1
        return f'{stem} {i}'

    def set_active(self, i):
        if 0 <= i < len(self.layers) and i != self.active:
            self.active = i
            if not self.has_mask(): self.edit_mask = False
            self.win.refresh_layers(); self.update()

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
        self.layers.insert(self.active + 1, Layer(s.img.copy(), s.name + ' copy', s.visible, s.opacity, s.blend,
                                                  s.mask.copy() if s.mask is not None else None))
        self.active += 1; self.update(); self.win.refresh_layers()

    def _scaled_layer_image(self, path, fit='cover'):
        """Load `path` and render it into a fresh canvas-sized ARGB32 QImage, scaled to
        either 'cover' the document (preserve aspect, fill, centred — may crop) or 'fit'
        it inside. Large sources are read straight into the canvas-sized buffer, so memory
        stays bounded by the document size, not the source file. Returns None on failure."""
        src = QImage(path)
        if src.isNull():
            return None
        dw, dh = self.doc_w(), self.doc_h()
        out = QImage(dw, dh, QImage.Format_ARGB32); out.fill(Qt.transparent)
        sw, sh = src.width(), src.height()
        if sw <= 0 or sh <= 0:
            return None
        if fit == 'fit':
            scale = min(dw / sw, dh / sh)
        else:  # cover
            scale = max(dw / sw, dh / sh)
        tw, th = max(1, round(sw * scale)), max(1, round(sh * scale))
        ox, oy = (dw - tw) / 2.0, (dh - th) / 2.0
        p = QPainter(out)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(ox, oy, tw, th), src, QRectF(0, 0, sw, sh))
        p.end()
        return out

    def add_overlay_layer(self, path, blend='screen', opacity=1.0):
        """Drop the image at `path` onto a NEW layer scaled to cover the document
        (aspect preserved, centred), with the given blend mode and opacity. Non-
        destructive. Returns the new Layer, or None if the image couldn't be loaded."""
        im = self._scaled_layer_image(path, fit='cover')
        if im is None:
            return None
        self.snapshot_full()
        name = os.path.splitext(os.path.basename(path))[0] or 'Overlay'
        layer = Layer(im, self._unique_name(name), True,
                      max(0.0, min(1.0, opacity)), blend if blend in BLEND_NAMES else 'screen')
        self.active += 1; self.layers.insert(self.active, layer)
        self.update(); self.win.refresh_layers()
        return layer

    def place_texture_layer(self, path, blend='normal', opacity=1.0):
        """Place the texture at `path` as a NEW layer scaled to cover the whole canvas
        (aspect preserved, centred), with the given blend mode and opacity. Non-
        destructive. Returns the new Layer, or None if the image couldn't be loaded."""
        im = self._scaled_layer_image(path, fit='cover')
        if im is None:
            return None
        self.snapshot_full()
        name = os.path.splitext(os.path.basename(path))[0] or 'Texture'
        layer = Layer(im, self._unique_name(name), True,
                      max(0.0, min(1.0, opacity)), blend if blend in BLEND_NAMES else 'normal')
        self.active += 1; self.layers.insert(self.active, layer)
        self.update(); self.win.refresh_layers()
        return layer

    def delete_layer(self):
        if len(self.layers) <= 1: return
        self.snapshot_full(); del self.layers[self.active]
        self.active = min(self.active, len(self.layers) - 1); self.update(); self.win.refresh_layers()

    def merge_down(self):
        if self.active == 0: return
        self.snapshot_full()
        top = self.layers[self.active]; bot = self.layers[self.active - 1]
        if top.visible:
            # bake the bottom layer's own mask in first, then the (masked) top over it
            if bot.mask is not None:
                bot.img = bot.masked_img(); bot.mask = None
            if HAS_PIL and top.blend in NP_BLENDS:
                bot.img = composite_np(bot.img, top.masked_img(), top.blend, top.opacity)
            else:
                p = QPainter(bot.img); p.setOpacity(top.opacity)
                p.setCompositionMode(BLENDS.get(top.blend, QPainter.CompositionMode_SourceOver))
                p.drawImage(0, 0, top.masked_img()); p.end()
        del self.layers[self.active]; self.active -= 1; self.update(); self.win.refresh_layers()

    # ---- layer masks ----
    def paint_target(self):
        """The QImage the painting tools write to: the active layer's mask when mask
        editing is on (and a mask exists), otherwise the layer image itself."""
        l = self.layers[self.active]
        if self.edit_mask and l.mask is not None:
            return l.mask
        return l.img

    def has_mask(self):
        return self.layers[self.active].mask is not None

    def add_mask(self, from_selection=False):
        """Give the active layer a mask. from_selection seeds it from the current
        selection (selected area visible, the rest hidden); otherwise it starts white
        (fully visible). Turns on mask editing so the next brush strokes shape it."""
        l = self.layers[self.active]
        if l.mask is not None:
            self.edit_mask = True; self.win.refresh_layers(); return
        self.snapshot_full()
        w, h = l.img.width(), l.img.height()
        if from_selection and HAS_PIL and self.sel is not None:
            sm = self.sel_mask()
            if sm is not None:
                m = QImage(w, h, QImage.Format_Grayscale8)
                if sm.shape != (h, w):
                    sm = _np.asarray(Image.fromarray(sm, 'L').resize((w, h), Image.NEAREST))
                buf = _np.ascontiguousarray(sm.astype('uint8'))
                m = QImage(buf.data, w, h, w, QImage.Format_Grayscale8).copy()
                l.mask = m
            else:
                l.mask = new_mask(w, h, True)
        else:
            l.mask = new_mask(w, h, True)
        self.edit_mask = True
        self.update(); self.win.refresh_layers()

    def delete_mask(self, apply_it=False):
        """Remove the active layer's mask. apply_it bakes it into the image first
        (so hidden areas become transparent); otherwise it is simply discarded."""
        l = self.layers[self.active]
        if l.mask is None: return
        self.snapshot_full()
        if apply_it:
            l.img = l.masked_img()
        l.mask = None; self.edit_mask = False
        self.update(); self.win.refresh_layers()

    def set_edit_mask(self, on):
        if on and not self.has_mask(): return
        self.edit_mask = bool(on); self.win.refresh_layers(); self.update()

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
            if tool in ('rect', 'ellipse') and self.shape_fill in ('fill', 'both'):
                fc = QColor(self.shape_fill_color or self.color); fc.setAlpha(140)
                p.setBrush(QBrush(fc))
                if self.shape_fill == 'fill': p.setPen(Qt.NoPen)
            if tool == 'line': p.drawLine(a, b)
            elif tool == 'rect': p.drawRect(QRectF(a, b).normalized())
            elif tool == 'ellipse': p.drawEllipse(QRectF(a, b).normalized())
            elif tool == 'gradient':
                gp = QPen(QColor('#000'), 1, Qt.DashLine); gp.setCosmetic(True); p.setPen(gp); p.drawLine(a, b)
            p.restore()
        if self.lasso_pts or self.poly_pts:              # live freehand / polygon outline
            p.save(); p.scale(self.zoom, self.zoom)
            if self.lasso_pts:
                poly = QPolygonF([QPointF(pt) for pt in self.lasso_pts])
            else:
                pts = list(self.poly_pts)
                if self.poly_cur is not None: pts = pts + [self.poly_cur]
                poly = QPolygonF([QPointF(pt) for pt in pts])
            for col, style in ((QColor('#ffffff'), Qt.SolidLine), (QColor('#000000'), Qt.DashLine)):
                pen = QPen(col, 1, style); pen.setCosmetic(True); p.setPen(pen); p.setBrush(Qt.NoBrush)
                p.drawPolyline(poly)
            if self.poly_pts:                            # dots on placed vertices
                p.setPen(Qt.NoPen); p.setBrush(QColor('#ffffff'))
                for pt in self.poly_pts:
                    p.drawEllipse(QPointF(pt), 2.5 / self.zoom, 2.5 / self.zoom)
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
        if self.tool == 'smartmask':
            sov = self._sm_overlay()
            if sov is not None:
                p.drawImage(r, sov, QRectF(0, 0, sov.width(), sov.height()))
        if self.tool == 'transform' and self.tf is not None:
            # live preview of the transformed active layer, then box + handles
            prev = apply_transform(self.tf['base'], self.tf_matrix(),
                                   (self.doc_w(), self.doc_h()))
            p.drawImage(QRectF(0, 0, prev.width() * self.zoom, prev.height() * self.zoom),
                        prev, QRectF(0, 0, prev.width(), prev.height()))
            hs = self._tf_handles()
            box = QPolygonF([hs['tl'] * self.zoom, hs['tr'] * self.zoom,
                             hs['br'] * self.zoom, hs['bl'] * self.zoom])
            pen = QPen(QColor('#2b9ff5'), 1); pen.setCosmetic(True)
            p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPolygon(box)
            # rotate stalk + handle
            p.drawLine(hs['t'] * self.zoom, hs['rot'] * self.zoom)
            p.setBrush(QColor('#ffffff'))
            for name, pt in hs.items():
                c = pt * self.zoom
                if name == 'rot':
                    p.drawEllipse(c, 4, 4)
                else:
                    p.drawRect(QRectF(c.x() - 3.5, c.y() - 3.5, 7, 7))
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
        if self.tool == 'smartmask' and e.button() in (Qt.LeftButton, Qt.RightButton):
            pos = self.img_pos(e)
            mode = 'remove' if e.button() == Qt.RightButton else self.sm_mode
            self._sm_active = mode
            self.last = pos; self._sm_paint(pos, pos, mode); return
        if self.tool == 'transform':
            if e.button() != Qt.LeftButton: return
            if self.tf is None: self.tf_begin()
            self._tf_press(self.img_pos(e), e.modifiers()); return
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
        if self.tool == 'lasso':                         # freehand selection — not an image edit
            self.lasso_pts = [pos]; self.update(); return
        if self.tool == 'polyselect':                    # click to drop a vertex
            pts = self.poly_pts or []
            if len(pts) >= 3 and (pos - pts[0]).manhattanLength() <= max(6, int(8 / self.zoom)):
                self._pts_to_sel(pts); self.poly_pts = None; self.poly_cur = None; self.update(); return
            pts.append(pos); self.poly_pts = pts; self.poly_cur = pos; self.update(); return
        if self.tool in ('mrect', 'mellipse'):          # marquee selection — not an image edit
            self.start = pos; self.sel_drag = (pos, pos); self.update(); return
        if self.tool == 'clone' and (e.modifiers() & Qt.ControlModifier):
            self.clone_src = pos; self.clone_off = None
            self.win.status.showMessage('Clone source set — now paint to copy from it.', 3000); return
        if self.tool == 'redeye':
            if HAS_PIL: self.snapshot(); self.red_eye(pos); self.update()
            return
        # editing a mask changes layer.mask (not .img), so snapshot the whole stack
        self.snapshot_full() if (self.edit_mask and self.has_mask()) else self.snapshot()
        if self.tool in ('brush', 'eraser', 'dodge', 'burn', 'oil', 'smudge', 'heal', 'sponge'):
            if self.tool in ('oil', 'smudge'):
                self._wet_begin(pos)
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
        if self.tool == 'transform':
            if (e.buttons() & Qt.LeftButton) and self.tf is not None:
                self._tf_drag(pos, e.modifiers())
            return
        if self.tool == 'smartmask':
            if (e.buttons() & (Qt.LeftButton | Qt.RightButton)) and self.last is not None:
                self._sm_paint(self.last, pos, getattr(self, '_sm_active', self.sm_mode))
                self.last = pos
            return
        if self.tool == 'polyselect' and self.poly_pts:   # live rubber line to the cursor
            self.poly_cur = pos; self.update(); return
        if not (e.buttons() & Qt.LeftButton): return
        if self.tool == 'lasso' and self.lasso_pts is not None:
            self.lasso_pts.append(pos); self.update(); return
        if self.tool in ('brush', 'eraser', 'dodge', 'burn', 'clone', 'oil', 'smudge', 'heal', 'sponge') and self.last is not None:
            self._stroke(self.last, pos); self.last = pos; self.update()
        elif self.tool in ('line', 'rect', 'ellipse', 'gradient') and self.start is not None:
            self.preview = (self.tool, self.start, pos); self.update()
        elif self.tool in ('mrect', 'mellipse') and self.start is not None:
            self.sel_drag = (self.start, pos); self.update()

    def mouseReleaseEvent(self, e):
        if self.tool == 'transform':
            if self.tf is not None: self.tf['grab'] = None
            return
        if self.tool == 'smartmask':
            self.last = None; return
        if e.button() != Qt.LeftButton: return
        pos = self.img_pos(e)
        if self.tool == 'lasso' and self.lasso_pts is not None:
            self.lasso_pts.append(pos)
            if len(self.lasso_pts) >= 3:
                self._pts_to_sel(self.lasso_pts)
            self.lasso_pts = None; self.update(); return
        if self.tool in ('mrect', 'mellipse') and self.start is not None:
            r = QRect(self.start, pos).normalized()
            self.sel = ({'rect': r, 'kind': 'ellipse' if self.tool == 'mellipse' else 'rect'}
                        if r.width() > 2 and r.height() > 2 else None)
            self.start = self.sel_drag = None; self.update(); return
        if self.tool == 'gradient' and self.start is not None:
            self._draw_gradient(self.start, pos)
        elif self.tool in ('line', 'rect', 'ellipse') and self.start is not None:
            target = self.paint_target()
            p = QPainter(target); p.setRenderHint(QPainter.Antialiasing)
            if self.tool == 'line':
                p.setPen(self._pen()); p.setBrush(Qt.NoBrush); p.drawLine(self.start, pos)
            else:
                # rect / ellipse honour the fill mode: 'stroke' | 'fill' | 'both'
                mode = self.shape_fill
                if mode in ('fill', 'both'):
                    fc = self.shape_fill_color or self.color
                    if target is not self.img:          # mask: use the colour's grey
                        g = QColor(fc).lightness(); fc = QColor(g, g, g)
                    p.setBrush(QBrush(QColor(fc)))
                else:
                    p.setBrush(Qt.NoBrush)
                p.setPen(Qt.NoPen if mode == 'fill' else self._pen())
                r = QRect(self.start, pos).normalized()
                p.drawRect(r) if self.tool == 'rect' else p.drawEllipse(r)
            p.end()
        self.last = self.start = self.preview = None
        self.clone_base = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.tool == 'polyselect' and self.poly_pts:
            self._close_poly()
        elif self.tool == 'transform' and self.tf is not None:
            self.tf_commit()

    def keyPressEvent(self, e):
        if self.tool == 'transform' and self.tf is not None:
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.tf_commit(); return
            if e.key() == Qt.Key_Escape:
                self.tf_cancel(); return
        if self.tool == 'polyselect' and self.poly_pts:
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._close_poly(); return
            if e.key() == Qt.Key_Escape:
                self.poly_pts = None; self.poly_cur = None; self.update(); return
        super().keyPressEvent(e)

    def _close_poly(self):
        """Close the in-progress Polygon selection -> mask selection (shared rasteriser)."""
        pts = self.poly_pts or []
        if len(pts) >= 3:
            self._pts_to_sel(pts)
        self.poly_pts = None; self.poly_cur = None; self.update()

    # ---- Free Transform (tool 'transform') ----
    def tf_begin(self):
        """Enter Free Transform on the active layer: cache the original image and
        its content bbox, reset the transform to identity. No-op if already live."""
        if self.tf is not None: return
        base = self.img.copy()
        bbox = None
        if HAS_PIL:
            try:
                bbox = alpha_bbox(_np.asarray(q2pil(base)))
            except Exception:
                bbox = None
        if not bbox:
            bbox = (0, 0, base.width(), base.height())
        cx = bbox[0] + bbox[2] / 2.0; cy = bbox[1] + bbox[3] / 2.0
        self.tf = {'base': base, 'bbox': bbox, 'sx': 1.0, 'sy': 1.0,
                   'angle': 0.0, 'skew': (0.0, 0.0), 'anchor': (cx, cy),
                   'grab': None, 'start': None, 'p0': None}
        self.update()

    def tf_matrix(self):
        if self.tf is None: return QTransform()
        t = self.tf
        return build_transform(t['bbox'], t['sx'], t['sy'], t['angle'], t['skew'], t['anchor'])

    def _tf_handles(self):
        """Screen-space (image-coord) positions of the 8 scale handles + rotate
        handle after the current matrix. Returns dict name -> QPointF. Corners:
        tl,tr,br,bl; edges: t,r,b,l; plus 'rot' above the top edge midpoint."""
        if self.tf is None: return {}
        x, y, w, h = self.tf['bbox']
        m = self.tf_matrix()
        pts = {'tl': (x, y), 'tr': (x + w, y), 'br': (x + w, y + h), 'bl': (x, y + h),
               't': (x + w / 2, y), 'r': (x + w, y + h / 2),
               'b': (x + w / 2, y + h), 'l': (x, y + h / 2)}
        out = {k: m.map(QPointF(px, py)) for k, (px, py) in pts.items()}
        # rotate handle: 26px (image coords) above the top-edge midpoint, along the
        # box's local up direction so it tracks rotation.
        up = m.map(QPointF(x + w / 2, y)) - m.map(QPointF(x + w / 2, y + h / 2))
        ln = math.hypot(up.x(), up.y()) or 1.0
        out['rot'] = out['t'] + QPointF(up.x() / ln, up.y() / ln) * (26.0 / self.zoom)
        return out

    def tf_hit(self, pos):
        """Which handle (name) is under `pos` (image coords), or None."""
        tol = max(6.0, 9.0 / self.zoom)
        for name, pt in self._tf_handles().items():
            if math.hypot(pt.x() - pos.x(), pt.y() - pos.y()) <= tol:
                return name
        return None

    def _tf_press(self, pos, mods):
        grab = self.tf_hit(pos)
        self.tf['grab'] = grab
        self.tf['p0'] = QPointF(pos)
        self.tf['start'] = dict(sx=self.tf['sx'], sy=self.tf['sy'],
                                angle=self.tf['angle'], skew=self.tf['skew'])
        # remember the pointer's angle/offset from the anchor for rotate/skew math
        ax, ay = self.tf['anchor']
        self.tf['a0'] = math.degrees(math.atan2(pos.y() - ay, pos.x() - ax))

    def _tf_drag(self, pos, mods):
        t = self.tf
        if t['grab'] is None or t['start'] is None: return
        x, y, w, h = t['bbox']; ax, ay = t['anchor']
        g = t['grab']; st = t['start']
        if g == 'rot':
            a1 = math.degrees(math.atan2(pos.y() - ay, pos.x() - ax))
            t['angle'] = st['angle'] + (a1 - t['a0'])
            if mods & Qt.ShiftModifier:                      # snap to 15°
                t['angle'] = round(t['angle'] / 15.0) * 15.0
        elif (mods & Qt.ControlModifier) and g in ('t', 'b', 'l', 'r'):
            # skew: drag an edge handle sideways with Ctrl held
            if g in ('l', 'r'):
                t['skew'] = (st['skew'][0], (pos.y() - t['p0'].y()) / max(1.0, w) + st['skew'][1])
            else:
                t['skew'] = ((pos.x() - t['p0'].x()) / max(1.0, h) + st['skew'][0], st['skew'][1])
        else:
            # scale about the anchor (box centre). Compare pointer distance to the
            # grabbed handle's original distance along each axis.
            hx = w / 2.0 or 1.0; hy = h / 2.0 or 1.0
            dx = (pos.x() - ax); dy = (pos.y() - ay)
            # NOTE: anchor is centre so a handle sits hx/hy from it at identity.
            new_sx, new_sy = st['sx'], st['sy']
            if g in ('tl', 'tr', 'br', 'bl', 'l', 'r'):
                new_sx = dx / hx * (1 if g in ('tr', 'br', 'r') else -1)
            if g in ('tl', 'tr', 'br', 'bl', 't', 'b'):
                new_sy = dy / hy * (1 if g in ('bl', 'br', 'b') else -1)
            if g in ('tl', 'tr', 'br', 'bl') and (mods & Qt.ShiftModifier):
                s = max(abs(new_sx), abs(new_sy))            # keep aspect
                new_sx = math.copysign(s, new_sx); new_sy = math.copysign(s, new_sy)
            t['sx'], t['sy'] = new_sx, new_sy
        self.update()

    def tf_commit(self):
        """Bake the live transform into the active layer (doc-sized output), push
        undo. The layer stays doc-sized; content transformed past the canvas edge
        is clipped (matches crop/canvas semantics). No-op if identity / inactive."""
        if self.tf is None: return
        t = self.tf
        identity = (abs(t['sx'] - 1) < 1e-6 and abs(t['sy'] - 1) < 1e-6
                    and abs(t['angle']) < 1e-6 and abs(t['skew'][0]) < 1e-6
                    and abs(t['skew'][1]) < 1e-6)
        if not identity:
            self.snapshot()
            out = apply_transform(t['base'], self.tf_matrix(),
                                  (self.doc_w(), self.doc_h()))
            self.img = out
        self.tf = None
        self.update(); self.win.refresh_layers()

    def tf_cancel(self):
        if self.tf is None: return
        self.tf = None; self.update()

    def _grad_brush(self, a, b):
        """A QLinearGradient for the gradient tool: start colour at the drag start,
        end colour (or transparent) at the drag end."""
        g = QLinearGradient(QPointF(a), QPointF(b))
        c0 = QColor(self.grad_start)
        c1 = QColor(self.grad_start if self.grad_end_transparent else self.grad_end)
        if self.grad_end_transparent: c1.setAlpha(0)
        g.setColorAt(0, c0); g.setColorAt(1, c1)
        return g

    def _draw_gradient(self, a, b):
        g = self._grad_brush(a, b)
        target = self.paint_target()
        mask = self.sel_mask() if (self.sel and self.sel.get('kind') == 'mask') else None
        if mask is not None and target is self.img:   # mask / feathered selection — blend in
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
        p = QPainter(target); p.setRenderHint(QPainter.Antialiasing)
        if target is self.img:
            reg = self.sel_region()
            if reg:
                r, kind = reg; path = QPainterPath()
                path.addEllipse(QRectF(r)) if kind == 'ellipse' else path.addRect(QRectF(r))
                p.setClipPath(path)
        p.fillRect(target.rect(), QBrush(g)); p.end()

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
        if self.tool in ('oil', 'smudge'):
            self._wet_stroke(a, b, self.tool); return
        if self.tool in ('heal', 'sponge'):
            self._retouch_stroke(a, b, self.tool); return
        target = self.paint_target()
        if target is not self.img:          # painting into a greyscale mask
            p = QPainter(target); p.setRenderHint(QPainter.Antialiasing)
            if self.tool == 'eraser':
                col = QColor('#ffffff')          # eraser reveals (white) on a mask
            elif self.tool in ('dodge', 'burn'):
                col = QColor('#ffffff') if self.tool == 'dodge' else QColor('#000000')
            else:
                v = QColor(self.color); g = v.lightness(); col = QColor(g, g, g)  # brush = colour's grey
            pen = QPen(col, self.size); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen); p.drawLine(a, b); p.end(); return
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

    # ---- natural-media wet brushes (Oil / Smudge), in the spirit of ArtRage ----
    # The brush carries colour and blends with the paint already on the canvas:
    # the Oil brush mixes your colour with what it picks up (wet-on-wet), and the
    # Smudge/palette-knife just drags existing colour. Done in NumPy on the layer.
    def _wet_begin(self, pos):
        self._wet = {'buf': self._img_to_rgba_f(self.img), 'carry': None}

    def _img_to_rgba_f(self, img):
        import numpy as np
        im = img.convertToFormat(QImage.Format_RGBA8888)
        w, h = im.width(), im.height()
        return np.frombuffer(im.constBits().tobytes(), np.uint8).reshape(h, w, 4).astype(np.float32)

    def _blit_rgba_f(self, buf):
        import numpy as np
        h, w = buf.shape[:2]
        data = np.clip(buf, 0, 255).astype(np.uint8).tobytes()
        qb = QImage(data, w, h, QImage.Format_RGBA8888).convertToFormat(QImage.Format_ARGB32)
        p = QPainter(self.img); p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(0, 0, qb); p.end()

    def _wet_stroke(self, a, b, mode):
        import numpy as np, math
        w = getattr(self, '_wet', None)
        if not w:
            self._wet_begin(a); w = self._wet
        buf = w['buf']; H, W = buf.shape[:2]
        r = max(1.0, self.size / 2.0)
        c = QColor(self.color); bcol = np.array([c.red(), c.green(), c.blue()], np.float32)
        dist = math.hypot(b.x() - a.x(), b.y() - a.y())
        steps = max(1, int(dist / max(1.0, r * 0.25)))
        for i in range(steps + 1):
            t = i / steps if steps else 0.0
            cx = a.x() + (b.x() - a.x()) * t
            cy = a.y() + (b.y() - a.y()) * t
            x0, y0, x1, y1 = int(cx - r), int(cy - r), int(cx + r) + 1, int(cy + r) + 1
            gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            if gx1 <= gx0 or gy1 <= gy0:
                continue
            patch = buf[gy0:gy1, gx0:gx1]
            yy, xx = np.ogrid[gy0:gy1, gx0:gx1]
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            m = np.clip(1.0 - d / r, 0.0, 1.0) ** 1.4
            mm = m[..., None]
            rgb = patch[..., :3]; alpha = patch[..., 3:4]
            if w['carry'] is None:
                aw = alpha[..., 0] * m; tot = float(aw.sum())
                w['carry'] = ((rgb * aw[..., None]).sum(axis=(0, 1)) / tot) if tot > 1 else bcol.copy()
            carry = w['carry']
            if mode == 'smudge':
                s = 0.55
                patch[..., :3] = rgb * (1 - mm * s) + carry * (mm * s)
                patch[..., 3:4] = np.maximum(alpha, mm * 255.0)
                local = (patch[..., :3] * mm).sum(axis=(0, 1)) / (float(mm.sum()) + 1e-6)
                w['carry'] = carry * 0.7 + local * 0.3
            else:  # oil — wet paint: your colour mixed with what the brush picks up
                load, s = 0.6, 0.5
                paint = bcol * load + carry * (1 - load)
                patch[..., :3] = rgb * (1 - mm * s) + paint * (mm * s)
                patch[..., 3:4] = np.maximum(alpha, mm * 255.0)
                local = (patch[..., :3] * mm).sum(axis=(0, 1)) / (float(mm.sum()) + 1e-6)
                w['carry'] = carry * 0.6 + local * 0.4
        self._blit_rgba_f(buf)

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

    def _retouch_stroke(self, a, b, mode):
        """Heal / Sponge: stamp soft dabs along the segment, editing the active layer's
        RGB in NumPy via heal_patch / sponge_patch, then blit back. The snapshot is already
        pushed at stroke start (mousePress), matching the other brushes. Alpha is preserved."""
        if not HAS_PIL: return
        im = q2pil(self.img)
        a4 = _np.asarray(im).astype(_np.float32)          # HxWx4
        rgb = a4[..., :3]
        r = max(1.0, self.size / 2.0)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        n = max(1, int((dx * dx + dy * dy) ** 0.5 / max(1.0, r * 0.4)))
        for i in range(n + 1):
            cx = a.x() + dx * i / n; cy = a.y() + dy * i / n
            if mode == 'heal':
                rgb = heal_patch(rgb, cx, cy, r, self.heal_strength)
            else:
                amt = self.sponge_flow if self.sponge_mode == 'saturate' else -self.sponge_flow
                rgb = sponge_patch(rgb, cx, cy, r, amt)
        a4[..., :3] = rgb
        out = Image.fromarray(_np.clip(a4, 0, 255).astype('uint8'), 'RGBA')
        self.img = pil2q(out)

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

    def _pts_to_sel(self, pts):
        """Rasterise a polygon of QPoints to a mask selection (Lasso / Polygon tools),
        stored exactly like the wand's via set_mask_sel so feather/grow/invert/fill all
        work unchanged. <3 points just clears any selection."""
        if not HAS_PIL: return
        w, h = self.img.width(), self.img.height()
        mask = points_to_mask([(p.x(), p.y()) for p in pts], w, h)
        self.set_mask_sel(mask)

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

    def trim_transparent(self, padding=0, threshold=0):
        """Photo Trimming: crop the whole document to the bounding box of the
        non-transparent pixels in the COMPOSITED image (+ optional padding),
        clamped to the canvas. Returns (x,y,w,h) of the crop, or None if the
        image is fully opaque / fully transparent (nothing to trim). Reuses the
        _map_layers crop machinery so every layer and the doc shrink together."""
        if not HAS_PIL: return None
        bbox = alpha_bbox(_np.asarray(q2pil(self.composited())), threshold)
        if bbox is None: return None
        x, y, w, h = bbox
        pad = max(0, int(padding))
        x0 = max(0, x - pad); y0 = max(0, y - pad)
        x1 = min(self.doc_w(), x + w + pad); y1 = min(self.doc_h(), y + h + pad)
        if x0 == 0 and y0 == 0 and x1 == self.doc_w() and y1 == self.doc_h():
            return None                                   # nothing to trim (fully opaque)
        r = QRect(x0, y0, x1 - x0, y1 - y0)
        self._map_layers(lambda im: im.copy(r))
        return (x0, y0, r.width(), r.height())

    def resize_image(self, w, h):
        self._map_layers(lambda im: im.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32))

    def smart_enlarge_doc(self, w, h, sharpen=0.5, denoise=0.0):
        """Image ▸ Enlarge: smart-upscale the WHOLE document (every layer, canvas and
        all) to (w, h). Each layer's colour is enlarged with smart_enlarge() so edges
        stay crisp; its alpha channel and any layer mask are Lanczos-resized to match.
        Snapshots for undo and refits. Needs numpy (HAS_PIL)."""
        def up(im):
            src = im.convertToFormat(QImage.Format_ARGB32)
            rgba = _np.asarray(q2pil(src))                       # HxWx4 uint8
            rgb = smart_enlarge(rgba[..., :3], w, h, sharpen=sharpen, denoise=denoise)
            a = Image.fromarray(rgba[..., 3], 'L').resize((w, h), Image.LANCZOS)
            out = _np.dstack([rgb, _np.asarray(a).astype(_np.uint8)])
            return pil2q(Image.fromarray(out, 'RGBA'))
        self.snapshot_full()
        for l in self.layers:
            l.img = up(l.img)
            if l.mask is not None:
                l.mask = l.mask.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.sel = None; self._fit()

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

    # ---- Smart Mask (Fluid-Mask-style scribble cut-out) ----
    def _sm_ensure(self):
        """Make sure the two scribble overlays exist at the current image size (reset
        them if the geometry changed)."""
        h, w = self.img.height(), self.img.width()
        if self.sm_keep is None or self.sm_keep.shape != (h, w):
            self.sm_keep = _np.zeros((h, w), bool)
            self.sm_remove = _np.zeros((h, w), bool)

    def sm_clear(self):
        """Forget all Smart Mask scribbles."""
        self.sm_keep = self.sm_remove = None
        self.update()

    def _sm_paint(self, a, b, mode):
        """Stamp a line of the scribble brush (diameter self.sm_brush) from a to b onto
        the KEEP or REMOVE overlay. Painting one clears the overlapping bit of the other."""
        if not HAS_PIL: return
        self._sm_ensure()
        h, w = self.sm_keep.shape
        # rasterise the stroke into a temporary 8-bit image via QPainter, then OR it in
        stroke = QImage(w, h, QImage.Format_Grayscale8); stroke.fill(QColor('#000000'))
        p = QPainter(stroke)
        pen = QPen(QColor('#ffffff'), max(1, self.sm_brush))
        pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen); p.drawLine(a, b); p.end()
        painted = _np.asarray(q2pil(stroke).convert('L')) > 127
        if mode == 'keep':
            self.sm_keep |= painted; self.sm_remove &= ~painted
        else:
            self.sm_remove |= painted; self.sm_keep &= ~painted
        self.update()

    def _sm_overlay(self):
        """A translucent RGBA QImage showing KEEP (green) / REMOVE (red) scribbles over
        the canvas, for paintEvent. None if there are no scribbles."""
        if not HAS_PIL or self.sm_keep is None: return None
        if not self.sm_keep.any() and not self.sm_remove.any(): return None
        h, w = self.sm_keep.shape
        ov = _np.zeros((h, w, 4), _np.uint8)
        ov[self.sm_keep] = (60, 220, 90, 120)
        ov[self.sm_remove] = (235, 70, 70, 120)
        return pil2q(Image.fromarray(ov, 'RGBA'))

    def smart_mask_result(self, feather=0, force_fallback=False):
        """Run smart_mask() on the current flattened document using the stored
        scribbles. Returns a uint8 HxW mask (255 = subject), or None if there are
        no KEEP scribbles / no NumPy."""
        if not HAS_PIL or self.sm_keep is None or not self.sm_keep.any():
            return None
        rgb = _np.asarray(q2pil(self.composited()).convert('RGB'))
        return smart_mask(rgb, self.sm_keep, self.sm_remove,
                          feather=feather, force_fallback=force_fallback)

    def smart_mask_to_selection(self, mask):
        """Adopt a Smart Mask result as the current selection (so adjustments / cut
        apply to the subject)."""
        if mask is None or not mask.any(): return
        self.set_mask_sel(mask)

    def smart_mask_cutout_layer(self, mask):
        """Copy the masked subject of the flattened document onto a NEW transparent
        layer (non-destructive). Returns the new Layer, or None."""
        if not HAS_PIL or mask is None or not mask.any(): return None
        self.snapshot_full()
        rgba = _np.asarray(q2pil(self.composited())).astype(_np.uint16).copy()
        rgba[..., 3] = (rgba[..., 3] * mask // 255).astype(_np.uint16)
        cut = pil2q(Image.fromarray(rgba.astype('uint8'), 'RGBA'))
        layer = Layer(cut, self._unique_name('Cut-out'))
        self.active += 1; self.layers.insert(self.active, layer)
        self.update(); self.win.refresh_layers()
        return layer

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
        self.layers = [Layer(base, 'Background')]; self.active = 0; self.sel = None; self.edit_mask = False
        self._fit(); self.win.refresh_layers()

    def load(self, img):
        self.snapshot_full()
        base = img.convertToFormat(QImage.Format_ARGB32)
        self.layers = [Layer(base, 'Background')]; self.active = 0; self.sel = None; self.edit_mask = False
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


class ChannelMixerDialog(QDialog):
    """Full 3x3 Channel Mixer with live canvas preview (PhotoPlus-style). An output-channel
    picker (Red/Green/Blue) switches which set of source weights + constant the four sliders
    edit; a Monochrome checkbox collapses to a single weight set driving R=G=B. All values
    live in self.vals and are fed to adj_channelmixer. Mirrors AdjustDialog's apply/accept."""
    OUT = [('r', 'Red'), ('g', 'Green'), ('b', 'Blue')]

    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Channel Mixer'); self.setMinimumWidth(360)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()
        # defaults: identity matrix (each output = 100% its own source), mono = greyscale-ish
        self.vals = {'rr': 100, 'rg': 0, 'rb': 0, 'roff': 0,
                     'gr': 0, 'gg': 100, 'gb': 0, 'goff': 0,
                     'br': 0, 'bg': 0, 'bb': 100, 'boff': 0,
                     'mr': 40, 'mg': 40, 'mb': 20, 'moff': 0}
        v = QVBoxLayout(self)
        self.mono_cb = QCheckBox('Monochrome'); self.mono_cb.toggled.connect(self._mono_toggled)
        v.addWidget(self.mono_cb)
        row = QHBoxLayout(); row.addWidget(QLabel('Output channel:'))
        self.out_cb = QComboBox(); self.out_cb.addItems([n for _, n in self.OUT])
        self.out_cb.currentIndexChanged.connect(self._reload)
        row.addWidget(self.out_cb, 1); v.addLayout(row)
        form = QFormLayout(); v.addLayout(form)
        self.sliders = {}       # suffix ('r'/'g'/'b'/'off') -> (QSlider, QLabel)
        for suf, label, lo, hi in (('r', 'Red source:', -200, 200), ('g', 'Green source:', -200, 200),
                                   ('b', 'Blue source:', -200, 200), ('off', 'Constant:', -255, 255)):
            s = QSlider(Qt.Horizontal); s.setRange(lo, hi)
            val = QLabel(); val.setMinimumWidth(46); val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            s.valueChanged.connect(lambda _=0, k=suf: self._slider_changed(k))
            rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
            holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250)
            form.addRow(label, holder); self.sliders[suf] = (s, val)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._reload()

    def _cur_prefix(self):
        return 'm' if self.mono_cb.isChecked() else self.OUT[self.out_cb.currentIndex()][0]

    def _mono_toggled(self, on):
        self.out_cb.setEnabled(not on); self._reload()

    def _reload(self):
        """Load self.vals into the sliders for the currently-selected output set."""
        self._loading = True
        pre = self._cur_prefix()
        for suf, (s, val) in self.sliders.items():
            s.setValue(int(self.vals[pre + suf])); val.setText(f'{int(self.vals[pre + suf])}')
        self._loading = False
        self._apply()

    def _slider_changed(self, suf):
        if getattr(self, '_loading', False): return
        pre = self._cur_prefix()
        s, val = self.sliders[suf]
        self.vals[pre + suf] = s.value(); val.setText(f'{s.value()}')
        self._apply()

    def _params(self):
        p = dict(self.vals); p['mono'] = self.mono_cb.isChecked(); return p

    def _apply(self):
        try:
            self.canvas.img = self.canvas._apply_to(self.base, adj_channelmixer(self._params()))
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()

    def accept(self):
        self.canvas.push_undo_layer(self.active_idx, self.base); super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class SelectiveColorDialog(QDialog):
    """Adjust ▸ Selective Colour (PhotoPlus-style). A colour-range combo picks the hue family
    (or Whites/Neutrals/Blacks); four C/M/Y/K sliders (-100..100) nudge just that family. The
    C/M/Y/K values are stored per range so switching ranges keeps each family's edit. Live,
    selection-aware preview like ChannelMixerDialog; feeds adj_selective_color."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Selective Colour'); self.setMinimumWidth(360)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()
        self.vals = {r: {'c': 0, 'm': 0, 'y': 0, 'k': 0} for r in SELECTIVE_RANGES}
        v = QVBoxLayout(self)
        row = QHBoxLayout(); row.addWidget(QLabel('Colours:'))
        self.range_cb = QComboBox(); self.range_cb.addItems(SELECTIVE_RANGES)
        self.range_cb.currentIndexChanged.connect(self._reload)
        row.addWidget(self.range_cb, 1); v.addLayout(row)
        form = QFormLayout(); v.addLayout(form)
        self.sliders = {}       # 'c'/'m'/'y'/'k' -> (QSlider, QLabel)
        for key, label in (('c', 'Cyan:'), ('m', 'Magenta:'), ('y', 'Yellow:'), ('k', 'Black:')):
            s = QSlider(Qt.Horizontal); s.setRange(-100, 100)
            val = QLabel(); val.setMinimumWidth(46); val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            s.valueChanged.connect(lambda _=0, k=key: self._slider_changed(k))
            rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
            holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250)
            form.addRow(label, holder); self.sliders[key] = (s, val)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._reload()

    def _cur_range(self):
        return SELECTIVE_RANGES[self.range_cb.currentIndex()]

    def _reload(self):
        self._loading = True
        d = self.vals[self._cur_range()]
        for k, (s, val) in self.sliders.items():
            s.setValue(int(d[k])); val.setText(f'{int(d[k])}')
        self._loading = False
        self._apply()

    def _slider_changed(self, key):
        if getattr(self, '_loading', False): return
        s, val = self.sliders[key]
        self.vals[self._cur_range()][key] = s.value(); val.setText(f'{s.value()}')
        self._apply()

    def _apply(self):
        """Compose every range that has a non-zero edit so the preview shows them all."""
        try:
            def build(p):
                out = p
                for r, d in self.vals.items():
                    if any(d.values()):
                        out = adj_selective_color(r, d['c'], d['m'], d['y'], d['k'])(out)
                return out
            self.canvas.img = self.canvas._apply_to(self.base, build)
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()

    def accept(self):
        self.canvas.push_undo_layer(self.active_idx, self.base); super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class FlarePreview(QWidget):
    """A scaled preview of the composited image with the flare drawn on top (Screen),
    plus a draggable crosshair marking the light source. Dragging it calls `moved(x, y)`
    with document-space coordinates."""
    def __init__(self, base, moved):
        super().__init__()
        self.base = base                 # composited document QImage (RGB-ish)
        self.flare = None                # current flare QImage (document size) or None
        self.moved = moved
        self.lx = base.width() * 0.33
        self.ly = base.height() * 0.3
        self.setMinimumSize(360, 260)
        self.setCursor(Qt.CrossCursor)

    def set_flare(self, flare):
        self.flare = flare; self.update()

    def set_light(self, lx, ly):
        self.lx = lx; self.ly = ly; self.update()

    def _rect(self):
        bw, bh = self.base.width(), self.base.height()
        s = min(self.width() / bw, self.height() / bh)
        dw, dh = bw * s, bh * s
        ox, oy = (self.width() - dw) / 2, (self.height() - dh) / 2
        return QRectF(ox, oy, dw, dh), s

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#14181d'))
        r, s = self._rect()
        p.drawImage(r, self.base, QRectF(0, 0, self.base.width(), self.base.height()))
        if self.flare is not None:
            p.setCompositionMode(QPainter.CompositionMode_Screen)
            p.drawImage(r, self.flare, QRectF(0, 0, self.flare.width(), self.flare.height()))
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        # crosshair at the light source
        mx = r.x() + self.lx * s; my = r.y() + self.ly * s
        p.setPen(QPen(QColor(0, 0, 0, 160), 3)); self._cross(p, mx, my)
        p.setPen(QPen(QColor(255, 255, 255, 230), 1)); self._cross(p, mx, my)
        p.end()

    def _cross(self, p, mx, my):
        p.drawEllipse(QPointF(mx, my), 9, 9)
        p.drawLine(QPointF(mx - 14, my), QPointF(mx + 14, my))
        p.drawLine(QPointF(mx, my - 14), QPointF(mx, my + 14))

    def _to_doc(self, pt):
        r, s = self._rect()
        x = (pt.x() - r.x()) / max(1e-6, s)
        y = (pt.y() - r.y()) / max(1e-6, s)
        x = max(0, min(self.base.width(), x)); y = max(0, min(self.base.height(), y))
        return x, y

    def mousePressEvent(self, e):
        self.lx, self.ly = self._to_doc(e.position()); self.moved(self.lx, self.ly)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.lx, self.ly = self._to_doc(e.position()); self.moved(self.lx, self.ly)


class LensFlareDialog(QDialog):
    """Knoll-Light-Factory-style Lens Flare studio: a live preview of the picture with
    the flare composited Screen, a draggable light-source marker (or X/Y sliders),
    brightness / size / hue / warmth sliders, element toggles, and presets. On OK the
    flare lands on its own non-destructive Screen layer."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Lens Flare'); self.resize(760, 520)
        w, h = self.canvas.doc_w(), self.canvas.doc_h()
        self.params = dict(LENS_FLARE_DEFAULTS)
        self._busy = False

        top = QHBoxLayout(self)
        base = self.canvas.composited().convertToFormat(QImage.Format_ARGB32)
        self.preview = FlarePreview(base, self._light_moved)
        top.addWidget(self.preview, 1)

        panel = QVBoxLayout(); top.addLayout(panel)
        panel.addWidget(QLabel('<b>Lens Flare</b>'))

        self.preset_cb = QComboBox(); self.preset_cb.addItem('— Preset —')
        for name in LENS_FLARE_PRESETS: self.preset_cb.addItem(name)
        self.preset_cb.currentTextChanged.connect(self._apply_preset)
        panel.addWidget(self.preset_cb)

        form = QFormLayout(); panel.addLayout(form)
        self.sx = self._slider(0, w, int(self.preview.lx)); form.addRow('Light X:', self._wrap(self.sx))
        self.sy = self._slider(0, h, int(self.preview.ly)); form.addRow('Light Y:', self._wrap(self.sy))
        self.sx.valueChanged.connect(self._slider_light)
        self.sy.valueChanged.connect(self._slider_light)
        self.sb = self._slider(10, 200, 100); form.addRow('Brightness:', self._wrap(self.sb))
        self.ss = self._slider(40, 200, 100); form.addRow('Size:', self._wrap(self.ss))
        self.sh = self._slider(0, 359, int(self.params['hue'])); form.addRow('Hue:', self._wrap(self.sh))
        self.sw = self._slider(0, 100, int(self.params['warmth'] * 100)); form.addRow('Warmth:', self._wrap(self.sw))
        self.spc = self._slider(1, 16, int(self.params['spike_count'])); form.addRow('Spikes:', self._wrap(self.spc))
        for s in (self.sb, self.ss, self.sh, self.sw, self.spc):
            s.valueChanged.connect(self._refresh)

        self.cb_spikes = QCheckBox('Star spikes'); self.cb_spikes.setChecked(True)
        self.cb_refl = QCheckBox('Reflections'); self.cb_refl.setChecked(True)
        self.cb_rain = QCheckBox('Rainbow ring')
        self.cb_halo = QCheckBox('Halo'); self.cb_halo.setChecked(True)
        self.cb_ana = QCheckBox('Anamorphic streak')
        for cb in (self.cb_spikes, self.cb_refl, self.cb_rain, self.cb_halo, self.cb_ana):
            cb.toggled.connect(self._refresh); panel.addWidget(cb)

        hint = QLabel('Drag the crosshair on the preview to place the light.')
        hint.setWordWrap(True); hint.setStyleSheet('color:#889'); panel.addWidget(hint)
        panel.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Add flare layer')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); panel.addWidget(bb)
        self._refresh()

    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

    def _wrap(self, s):
        w = QWidget(); w.setMinimumWidth(200); lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(s); return w

    def _light_moved(self, lx, ly):
        if self._busy: return
        self._busy = True
        self.sx.setValue(int(lx)); self.sy.setValue(int(ly))
        self._busy = False
        self._refresh()

    def _slider_light(self):
        if self._busy: return
        self.preview.set_light(self.sx.value(), self.sy.value())
        self._refresh()

    def _apply_preset(self, name):
        if name not in LENS_FLARE_PRESETS: return
        self._busy = True
        pr = LENS_FLARE_PRESETS[name]
        self.sb.setValue(int(pr['brightness'] * 100)); self.ss.setValue(int(pr['scale'] * 100))
        self.sh.setValue(int(pr['hue'])); self.sw.setValue(int(pr['warmth'] * 100))
        self.spc.setValue(int(pr['spike_count']))
        self.cb_spikes.setChecked(pr['spikes']); self.cb_refl.setChecked(pr['reflections'])
        self.cb_rain.setChecked(pr['rainbow']); self.cb_halo.setChecked(pr['halo'])
        self.cb_ana.setChecked(pr['anamorphic'])
        self.params['seed'] = pr['seed']
        self._busy = False
        self._refresh()

    def _collect(self):
        return {
            'brightness': self.sb.value() / 100.0, 'scale': self.ss.value() / 100.0,
            'hue': float(self.sh.value()), 'warmth': self.sw.value() / 100.0,
            'spikes': self.cb_spikes.isChecked(), 'spike_count': self.spc.value(),
            'anamorphic': self.cb_ana.isChecked(), 'reflections': self.cb_refl.isChecked(),
            'rainbow': self.cb_rain.isChecked(), 'halo': self.cb_halo.isChecked(),
            'seed': self.params.get('seed', 7),
        }

    def _refresh(self):
        if self._busy: return
        self.params = self._collect()
        w, h = self.canvas.doc_w(), self.canvas.doc_h()
        self.preview.set_flare(render_lens_flare(w, h, self.sx.value(), self.sy.value(), self.params))

    def accept(self):
        self.win.apply_lens_flare(self.sx.value(), self.sy.value(), self._collect())
        super().accept()


class EnlargeDialog(QDialog):
    """Image ▸ Enlarge — smart up-scaling in the spirit of PhotoZoom. Pick a target as
    a scale factor (2×/3×/4×), a custom %, or an explicit width/height (with aspect
    lock); dial Sharpen and Denoise; the resulting pixel size is shown live. A small
    100%-crop before/after preview shows how crisp the enlarge keeps the edges. On OK
    the whole document (every layer) is resampled with smart_enlarge()."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Enlarge (smart upscale)'); self.setMinimumWidth(420)
        self.ow, self.oh = self.canvas.doc_w(), self.canvas.doc_h()
        self._busy = False

        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Enlarge — smart upscale</b>'))
        engine = 'OpenCV Lanczos4' if HAS_CV2 else 'Pillow Lanczos'
        info = QLabel('Make a small photo bigger while keeping edges crisp. The image is '
                      'resampled with a high-quality Lanczos filter, then an edge-aware '
                      'sharpen restores the detail a plain resize would blur — far better '
                      'than ordinary resizing for blowing a picture up.<br>'
                      f'<i>Resampler: {engine}.</i>')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)

        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        form = QFormLayout(); v.addLayout(form)

        # target mode: scale factor / custom % / explicit size
        self.rb_factor = QRadioButton('Scale factor'); self.rb_factor.setChecked(True)
        self.rb_pct = QRadioButton('Custom %')
        self.rb_size = QRadioButton('Width × Height')
        grp = QButtonGroup(self)
        for rb in (self.rb_factor, self.rb_pct, self.rb_size):
            grp.addButton(rb); rb.toggled.connect(self._mode_changed)

        self.cb_factor = QComboBox(); self.cb_factor.addItems(['2×', '3×', '4×'])
        self.cb_factor.currentIndexChanged.connect(self._from_factor)
        frow = QHBoxLayout(); frow.addWidget(self.rb_factor); frow.addWidget(self.cb_factor, 1)
        fw = QWidget(); fw.setLayout(frow); form.addRow(fw)

        self.sp_pct = QSpinBox(); self.sp_pct.setRange(100, 800); self.sp_pct.setValue(200)
        self.sp_pct.setSuffix(' %'); self.sp_pct.valueChanged.connect(self._from_pct)
        prow = QHBoxLayout(); prow.addWidget(self.rb_pct); prow.addWidget(self.sp_pct, 1)
        pw = QWidget(); pw.setLayout(prow); form.addRow(pw)

        self.sp_w = QSpinBox(); self.sp_w.setRange(1, 40000); self.sp_w.setValue(self.ow * 2)
        self.sp_h = QSpinBox(); self.sp_h.setRange(1, 40000); self.sp_h.setValue(self.oh * 2)
        self.cb_lock = QCheckBox('Lock aspect'); self.cb_lock.setChecked(True)
        self.sp_w.valueChanged.connect(lambda: self._from_size('w'))
        self.sp_h.valueChanged.connect(lambda: self._from_size('h'))
        srow = QHBoxLayout(); srow.addWidget(self.rb_size)
        srow.addWidget(self.sp_w); srow.addWidget(QLabel('×')); srow.addWidget(self.sp_h)
        srow.addWidget(self.cb_lock)
        sw = QWidget(); sw.setLayout(srow); form.addRow(sw)

        self.s_sharpen = self._slider(0, 100, 50)
        self.s_denoise = self._slider(0, 100, 0)
        self.l_sharpen = self._val(); self.l_denoise = self._val()
        form.addRow('Sharpen:', self._row(self.s_sharpen, self.l_sharpen))
        form.addRow('Denoise:', self._row(self.s_denoise, self.l_denoise))
        self.s_sharpen.valueChanged.connect(self._update_preview)
        self.s_denoise.valueChanged.connect(self._update_preview)

        self.dims = QLabel(); self.dims.setStyleSheet('color:#ccd; font-weight:bold')
        v.addWidget(self.dims)

        # 100%-crop before/after preview (a centre crop, blown up through the engine)
        prow2 = QHBoxLayout()
        self.pv_before = QLabel('before'); self.pv_after = QLabel('after')
        for lab, pv in (('Before (100%)', self.pv_before), ('After (100%)', self.pv_after)):
            col = QVBoxLayout(); cap = QLabel(lab); cap.setStyleSheet('color:#889')
            pv.setFixedSize(150, 110); pv.setAlignment(Qt.AlignCenter)
            pv.setStyleSheet('border:1px solid #556; background:#222')
            col.addWidget(cap); col.addWidget(pv); cw = QWidget(); cw.setLayout(col)
            prow2.addWidget(cw)
        v.addLayout(prow2)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Enlarge')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)

        self._mode_changed(); self._from_factor(); self._update_preview()

    # ---- widget helpers (match SmoothSkinDialog) ----
    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

    def _val(self):
        l = QLabel(); l.setMinimumWidth(46); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter); return l

    def _row(self, s, val):
        rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
        holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250); return holder

    # ---- target-size plumbing ----
    def _mode_changed(self):
        self.cb_factor.setEnabled(self.rb_factor.isChecked())
        self.sp_pct.setEnabled(self.rb_pct.isChecked())
        self.sp_w.setEnabled(self.rb_size.isChecked())
        self.sp_h.setEnabled(self.rb_size.isChecked())
        self.cb_lock.setEnabled(self.rb_size.isChecked())

    def _set_size(self, w, h):
        self._busy = True
        self.sp_w.setValue(int(w)); self.sp_h.setValue(int(h))
        self._busy = False
        self._update_preview()

    def _from_factor(self, *a):
        f = self.cb_factor.currentIndex() + 2        # 2,3,4
        self._set_size(self.ow * f, self.oh * f)

    def _from_pct(self, *a):
        if self._busy: return
        f = self.sp_pct.value() / 100.0
        self._set_size(round(self.ow * f), round(self.oh * f))

    def _from_size(self, which):
        if self._busy: return
        if self.cb_lock.isChecked():
            self._busy = True
            if which == 'w':
                self.sp_h.setValue(max(1, round(self.sp_w.value() * self.oh / self.ow)))
            else:
                self.sp_w.setValue(max(1, round(self.sp_h.value() * self.ow / self.oh)))
            self._busy = False
        self._update_preview()

    def target(self):
        return int(self.sp_w.value()), int(self.sp_h.value())

    def params(self):
        return self.s_sharpen.value() / 100.0, self.s_denoise.value() / 100.0

    def _update_preview(self):
        if self._busy: return
        nw, nh = self.target(); sharpen, denoise = self.params()
        self.l_sharpen.setText(f'{self.s_sharpen.value()}')
        self.l_denoise.setText(f'{self.s_denoise.value()}')
        self.dims.setText(f'{self.ow} × {self.oh} px  →  {nw} × {nh} px'
                          f'   ({nw / max(1, self.ow):.2f}×)')
        try:
            full = q2pil(self.canvas.composited()).convert('RGB')
            rgb = _np.asarray(full)
            # a small centre crop, enlarged through the engine at the chosen factor.
            cw = min(self.ow, max(16, self.ow // 4)); ch = min(self.oh, max(16, self.oh // 4))
            x = (self.ow - cw) // 2; y = (self.oh - ch) // 2
            crop = rgb[y:y + ch, x:x + cw]
            factor = max(1.0, nw / max(1, self.ow))
            ncw, nch = max(1, round(cw * factor)), max(1, round(ch * factor))
            after = smart_enlarge(crop, ncw, nch, sharpen=sharpen, denoise=denoise)
            self._show(self.pv_before, crop)
            self._show(self.pv_after, after)
        except Exception:
            pass

    def _show(self, label, rgb):
        rgb = _np.ascontiguousarray(rgb.astype(_np.uint8))
        h, w = rgb.shape[:2]
        qi = QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format_RGB888)
        pm = QPixmap.fromImage(qi).scaled(label.width(), label.height(),
                                           Qt.KeepAspectRatio, Qt.FastTransformation)
        label.setPixmap(pm)

    def accept(self):
        nw, nh = self.target(); sharpen, denoise = self.params()
        self.canvas.smart_enlarge_doc(nw, nh, sharpen=sharpen, denoise=denoise)
        self.win.refresh_layers()
        super().accept()


class SmoothSkinDialog(QDialog):
    """Portrait skin-retouch studio with a live preview on the canvas. Sliders for
    Amount, Smoothing radius and Detail preserve; a "Skin only (auto-detect)"
    checkbox (off = retouch the current selection, or the whole picture); and a
    "Show skin mask" peek. On OK the retouched picture lands on its own new layer so
    the strength can be dialled back later with the layer opacity."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Smooth Skin'); self.setMinimumWidth(360)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()           # the layer we preview over
        self._busy = False

        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Smooth skin — portrait retouch</b>'))
        engine = 'OpenCV bilateral (edge-preserving)' if HAS_CV2 else 'NumPy median + blur'
        info = QLabel('Skin is detected by its tone and smoothed with an edge-preserving '
                      'filter, so eyes, lips, brows and hair stay sharp. Keep some Detail so '
                      'the skin does not look plastic.<br>'
                      f'<i>Engine: {engine}.</i>')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)

        form = QFormLayout(); v.addLayout(form)
        self.s_amount = self._slider(0, 100, 70)
        self.s_radius = self._slider(1, 30, 8)
        self.s_detail = self._slider(0, 100, 30)
        self.l_amount = self._val(); self.l_radius = self._val(); self.l_detail = self._val()
        form.addRow('Amount:', self._row(self.s_amount, self.l_amount))
        form.addRow('Smoothing radius:', self._row(self.s_radius, self.l_radius))
        form.addRow('Detail preserve:', self._row(self.s_detail, self.l_detail))
        for s in (self.s_amount, self.s_radius, self.s_detail):
            s.valueChanged.connect(self._refresh)

        self.cb_skin = QCheckBox('Skin only (auto-detect)'); self.cb_skin.setChecked(True)
        self.cb_mask = QCheckBox('Show skin mask')
        self.cb_newlayer = QCheckBox('Put the result on a new layer'); self.cb_newlayer.setChecked(True)
        for cb in (self.cb_skin, self.cb_mask, self.cb_newlayer):
            cb.toggled.connect(self._refresh); v.addWidget(cb)
        note = QLabel('With "Skin only" off, the retouch is limited to the current selection '
                      '(or the whole picture if nothing is selected).')
        note.setWordWrap(True); note.setStyleSheet('color:#889'); v.addWidget(note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._refresh()

    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

    def _val(self):
        l = QLabel(); l.setMinimumWidth(46); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter); return l

    def _row(self, s, val):
        rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
        holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250); return holder

    def _values(self):
        return (self.s_amount.value() / 100.0, self.s_radius.value(), self.s_detail.value() / 100.0,
                self.cb_skin.isChecked())

    def _compute(self):
        """The retouched RGBA PIL image for the current settings (whole layer)."""
        amount, radius, detail, skin_only = self._values()
        base = q2pil(self.base)
        rgb = _np.asarray(base.convert('RGB'))
        extra = None
        if not skin_only:
            extra = self.canvas.sel_mask()           # limit to the selection when not auto-skin
        out = smooth_skin(rgb, amount=amount, radius=radius, detail=detail,
                           skin_only=skin_only, extra_mask=extra)
        alpha = _np.asarray(base.convert('RGBA'))[..., 3]
        return Image.fromarray(_np.dstack([out, alpha]).astype('uint8'), 'RGBA')

    def _refresh(self):
        if self._busy: return
        self._busy = True
        for s, l in ((self.s_amount, self.l_amount), (self.s_radius, self.l_radius),
                     (self.s_detail, self.l_detail)):
            l.setText(f'{s.value()}')
        try:
            if self.cb_mask.isChecked():
                rgb = _np.asarray(q2pil(self.base).convert('RGB'))
                m = skin_mask(rgb)
                vis = _np.dstack([m, m, m, _np.full_like(m, 255)])
                self.canvas.img = pil2q(Image.fromarray(vis.astype('uint8'), 'RGBA'))
            else:
                self.canvas.img = pil2q(self._compute())
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()
        self._busy = False

    def accept(self):
        try:
            retouched = pil2q(self._compute())
        except Exception:
            self.canvas.img = self.base; self.canvas._fit(); super().reject(); return
        c = self.canvas
        self.canvas.img = self.base                  # undo the preview before committing
        if self.cb_newlayer.isChecked():
            c.snapshot_full()
            layer = Layer(retouched, c._unique_name('Smooth Skin'))
            c.active += 1; c.layers.insert(c.active, layer)
            c.update(); self.win.refresh_layers()
        else:
            c.push_undo_layer(self.active_idx, self.base.copy())
            c.img = retouched; c._fit()
        super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class _PhotoFXDialog(QDialog):
    """Shared base for the two Photo FX studios (Film Look / Art Style). Both show a
    preset chooser, strength slider(s) and a live preview on the canvas, and commit
    the result to the active layer (undoable), in the spirit of SmoothSkinDialog.
    Subclasses supply the preset list, the slider rows and the transform."""
    def __init__(self, win, title):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle(title); self.setMinimumWidth(380)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()           # the layer we preview over
        self._busy = False

    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

    def _val(self):
        l = QLabel(); l.setMinimumWidth(46); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter); return l

    def _row(self, s, val):
        rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
        holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250); return holder

    # ---- subclass hooks ----
    def _transform(self, rgb):
        """Return the stylised HxWx3 uint8 array for the current settings."""
        raise NotImplementedError

    def _compute(self):
        """The stylised RGBA PIL image for the current settings (whole layer)."""
        base = q2pil(self.base)
        rgb = _np.asarray(base.convert('RGB'))
        out = self._transform(rgb)
        alpha = _np.asarray(base.convert('RGBA'))[..., 3]
        return Image.fromarray(_np.dstack([out, alpha]).astype('uint8'), 'RGBA')

    def _refresh(self):
        if self._busy: return
        self._busy = True
        self._update_labels()
        try:
            self.canvas.img = pil2q(self._compute())
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()
        self._busy = False

    def _update_labels(self):
        pass

    def accept(self):
        try:
            result = pil2q(self._compute())
        except Exception:
            self.canvas.img = self.base; self.canvas._fit(); super().reject(); return
        c = self.canvas
        self.canvas.img = self.base                  # undo the preview before committing
        if self.cb_newlayer.isChecked():
            c.snapshot_full()
            layer = Layer(result, c._unique_name(self._layer_stem()))
            c.active += 1; c.layers.insert(c.active, layer)
            c.update(); self.win.refresh_layers()
        else:
            c.push_undo_layer(self.active_idx, self.base.copy())
            c.img = result; c._fit()
        super().accept()

    def _layer_stem(self):
        return 'Photo FX'

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class FilmLookDialog(_PhotoFXDialog):
    """Photo FX ▸ Film Look — one-click VirtualPhotographer-style photographic presets
    (B&W filters, vintage, cross-process, cinematic, sepia…), each a tone curve +
    colour grade with Grain and Vignette sliders, previewed live on the picture. On
    Apply the graded picture lands on its own new layer (so it can be dialled back
    with the layer opacity) or replaces the active layer."""
    def __init__(self, win):
        super().__init__(win, 'Film Look')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Film Look — photographic presets</b>'))
        info = QLabel('One-click photographic grades in the spirit of a film-emulation plug-in: each is a '
                      'combination of tone curve, colour grade / split-tone, grain and vignette. Pick a look, '
                      'then dial the Grain and Vignette to taste.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)

        self.preset_cb = QComboBox()
        for key in FILM_LOOK_ORDER:
            self.preset_cb.addItem(FILM_LOOKS[key]['label'], key)
        self.preset_cb.currentIndexChanged.connect(self._preset_changed)
        v.addWidget(self.preset_cb)
        self.desc = QLabel(); self.desc.setWordWrap(True); self.desc.setStyleSheet('color:#aab; font-style:italic')
        v.addWidget(self.desc)

        form = QFormLayout(); v.addLayout(form)
        self.s_grain = self._slider(0, 100, 18)
        self.s_vig = self._slider(0, 100, 20)
        self.l_grain = self._val(); self.l_vig = self._val()
        form.addRow('Grain:', self._row(self.s_grain, self.l_grain))
        form.addRow('Vignette:', self._row(self.s_vig, self.l_vig))
        for s in (self.s_grain, self.s_vig):
            s.valueChanged.connect(self._refresh)

        self.cb_newlayer = QCheckBox('Put the result on a new layer'); self.cb_newlayer.setChecked(True)
        v.addWidget(self.cb_newlayer)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._preset_changed()                       # seed defaults + first preview

    def _preset_key(self):
        return self.preset_cb.currentData()

    def _preset_changed(self):
        key = self._preset_key()
        preset = FILM_LOOKS[key]
        self.desc.setText(preset.get('desc', ''))
        self._busy = True                            # set the preset's default grain/vignette
        self.s_grain.setValue(int(round(preset.get('grain', 0.0) * 100)))
        self.s_vig.setValue(int(round(preset.get('vignette', 0.0) * 100)))
        self._busy = False
        self._refresh()

    def _update_labels(self):
        self.l_grain.setText(f'{self.s_grain.value()}')
        self.l_vig.setText(f'{self.s_vig.value()}')

    def _transform(self, rgb):
        return apply_film_look(rgb, self._preset_key(),
                               grain=self.s_grain.value() / 100.0,
                               vignette=self.s_vig.value() / 100.0)

    def _layer_stem(self):
        return FILM_LOOKS[self._preset_key()]['label']


class ArtStyleDialog(_PhotoFXDialog):
    """Photo FX ▸ Art Style — turn a photo into art (PhotoArtMaster-style): Oil
    Painting, Watercolour, Pencil Sketch (grey/colour), Cartoon/Comic, Detail Boost —
    with a Strength slider and a live preview. Prefers OpenCV's non-photorealistic
    filters, with a NumPy/PIL fallback. On Apply the art lands on its own new layer or
    replaces the active layer."""
    def __init__(self, win):
        super().__init__(win, 'Art Style')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Art Style — turn a photo into art</b>'))
        engine = 'OpenCV non-photorealistic filters' if HAS_CV2 else 'NumPy / PIL fallback'
        info = QLabel('Re-render your photo as a painting, drawing or comic, in the spirit of a photo-to-art '
                      'plug-in. Pick a style and set how strongly it is applied.<br>'
                      f'<i>Engine: {engine}.</i>')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)

        self.style_cb = QComboBox()
        for key in ART_STYLE_ORDER:
            self.style_cb.addItem(ART_STYLES[key]['label'], key)
        self.style_cb.currentIndexChanged.connect(self._style_changed)
        v.addWidget(self.style_cb)
        self.desc = QLabel(); self.desc.setWordWrap(True); self.desc.setStyleSheet('color:#aab; font-style:italic')
        v.addWidget(self.desc)

        form = QFormLayout(); v.addLayout(form)
        self.s_strength = self._slider(0, 100, 80)
        self.l_strength = self._val()
        form.addRow('Strength:', self._row(self.s_strength, self.l_strength))
        self.s_strength.valueChanged.connect(self._refresh)

        self.cb_newlayer = QCheckBox('Put the result on a new layer'); self.cb_newlayer.setChecked(True)
        v.addWidget(self.cb_newlayer)
        note = QLabel('A larger picture takes a moment to render each time you change a setting.')
        note.setWordWrap(True); note.setStyleSheet('color:#889'); v.addWidget(note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._style_changed()

    def _style_key(self):
        return self.style_cb.currentData()

    def _style_changed(self):
        self.desc.setText(ART_STYLES[self._style_key()].get('desc', ''))
        self._refresh()

    def _update_labels(self):
        self.l_strength.setText(f'{self.s_strength.value()}')

    def _transform(self, rgb):
        return apply_art_style(rgb, self._style_key(), strength=self.s_strength.value() / 100.0)

    def _layer_stem(self):
        return ART_STYLES[self._style_key()]['label']


class _EffectDialog(QDialog):
    """Shared base for the new Effects studios (Bevel / Chrome / Glass / Gradient Glow /
    Motion Trail / Twirl / Wood / Marble / Weave). Each shows a preset/slider panel and
    a live preview on the active layer, then commits the result to that layer, undoably —
    the same spirit as SmoothSkinDialog / _PhotoFXDialog. Subclasses build the controls
    and supply _transform(rgba)->rgba (HxWx4 uint8). A small live preview THUMBNAIL (like
    EnlargeDialog) also shows the result, so it reads even on a tiny or off-screen layer."""
    def __init__(self, win, title):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle(title); self.setMinimumWidth(400)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()           # the layer we preview over
        self._busy = False

    # ---- widget helpers (match the other studios) ----
    def _slider(self, lo, hi, val):
        s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

    def _val(self):
        l = QLabel(); l.setMinimumWidth(50); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter); return l

    def _row(self, s, val):
        rw = QHBoxLayout(); rw.addWidget(s, 1); rw.addWidget(val)
        holder = QWidget(); holder.setLayout(rw); holder.setMinimumWidth(250); return holder

    def _colour_btn(self, holder, key, default):
        """A colour-swatch button backed by self._cols[key]; updates preview on change."""
        if not hasattr(self, '_cols'):
            self._cols = {}
        self._cols[key] = QColor(*default) if isinstance(default, (tuple, list)) else QColor(default)
        btn = QPushButton('Colour')
        def tint():
            c = self._cols[key]
            btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"};padding:3px 10px')
        def pick():
            c = QColorDialog.getColor(self._cols[key], self, 'Colour')
            if c.isValid():
                self._cols[key] = c; tint(); self._refresh()
        btn.clicked.connect(pick); tint()
        return btn

    def _col_rgb(self, key):
        c = self._cols[key]; return (c.red(), c.green(), c.blue())

    def _finish_ui(self, v):
        """Add the preview thumbnail, the 'new layer' checkbox and the OK/Cancel box."""
        self.cb_newlayer = QCheckBox('Put the result on a new layer'); self.cb_newlayer.setChecked(False)
        v.addWidget(self.cb_newlayer)
        self.preview = QLabel('preview'); self.preview.setFixedHeight(120)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet('border:1px solid #556; background:#222')
        v.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply')
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)

    # ---- subclass hook ----
    def _transform(self, rgba):
        raise NotImplementedError

    def _update_labels(self):
        pass

    def _compute(self):
        """The result RGBA PIL image for the current settings (whole layer)."""
        base = q2pil(self.base)
        rgba = _np.asarray(base.convert('RGBA'))
        out = self._transform(rgba)
        return Image.fromarray(_ensure_rgba(out), 'RGBA')

    def _refresh(self):
        if self._busy: return
        self._busy = True
        self._update_labels()
        try:
            res = self._compute()
            self.canvas.img = pil2q(res)
            # thumbnail over a checker so transparency reads
            self._show_thumb(res)
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()
        self._busy = False

    def _show_thumb(self, pil):
        pm = QPixmap.fromImage(pil2q(pil))
        sw, sh = self.preview.width() or 360, self.preview.height()
        self.preview.setPixmap(pm.scaled(sw, sh, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self):
        try:
            result = pil2q(self._compute())
        except Exception:
            self.canvas.img = self.base; self.canvas._fit(); super().reject(); return
        c = self.canvas
        self.canvas.img = self.base                  # undo the preview before committing
        if self.cb_newlayer.isChecked():
            c.snapshot_full()
            layer = Layer(result, c._unique_name(self._layer_stem()))
            c.active += 1; c.layers.insert(c.active, layer)
            c.update(); self.win.refresh_layers()
        else:
            c.push_undo_layer(self.active_idx, self.base.copy())
            c.img = result; c._fit()
        super().accept()

    def _layer_stem(self):
        return 'Effect'

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class BevelDialog(_EffectDialog):
    """Effects ▸ Bevel… — raise a lit 3D bevel on the active layer's alpha shape."""
    def __init__(self, win):
        super().__init__(win, 'Bevel')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Bevel — a raised 3D edge</b>'))
        info = QLabel('Raises a bevelled, lit edge on the opaque shape of the active layer, '
                      'as if it were embossed out of the page. Works best on a cut-out subject '
                      'or lettering on a transparent layer.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.profile = QComboBox(); self.profile.addItems(['Round', 'Flat', 'Button'])
        self.profile.currentIndexChanged.connect(self._refresh)
        form.addRow('Profile:', self.profile)
        self.s_width = self._slider(1, 60, 12); self.l_width = self._val()
        self.s_smooth = self._slider(0, 20, 2); self.l_smooth = self._val()
        self.s_angle = self._slider(0, 359, 135); self.l_angle = self._val()
        self.s_elev = self._slider(5, 85, 45); self.l_elev = self._val()
        self.s_int = self._slider(0, 100, 70); self.l_int = self._val()
        form.addRow('Width:', self._row(self.s_width, self.l_width))
        form.addRow('Smoothness:', self._row(self.s_smooth, self.l_smooth))
        form.addRow('Light angle:', self._row(self.s_angle, self.l_angle))
        form.addRow('Light elevation:', self._row(self.s_elev, self.l_elev))
        form.addRow('Intensity:', self._row(self.s_int, self.l_int))
        for s in (self.s_width, self.s_smooth, self.s_angle, self.s_elev, self.s_int):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_width.setText(f'{self.s_width.value()} px')
        self.l_smooth.setText(f'{self.s_smooth.value()}')
        self.l_angle.setText(f'{self.s_angle.value()}°')
        self.l_elev.setText(f'{self.s_elev.value()}°')
        self.l_int.setText(f'{self.s_int.value()}')

    def _transform(self, rgba):
        prof = ['round', 'flat', 'button'][self.profile.currentIndex()]
        return bevel(rgba, width=self.s_width.value(), smoothness=self.s_smooth.value(),
                     profile=prof, angle=self.s_angle.value(), elevation=self.s_elev.value(),
                     intensity=self.s_int.value() / 100.0)

    def _layer_stem(self):
        return 'Bevel'


class ChromeDialog(_EffectDialog):
    """Effects ▸ Chrome… — a reflective-metal look mapped onto the shape's bevel."""
    def __init__(self, win):
        super().__init__(win, 'Chrome')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Chrome — reflective metal</b>'))
        info = QLabel('Turns the active layer’s shape into polished metal by mapping a '
                      'sky-to-ground reflection ramp across a bevelled edge.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.ramp = QComboBox()
        for k in CHROME_RAMP_ORDER:
            self.ramp.addItem(k.capitalize(), k)
        self.ramp.currentIndexChanged.connect(self._refresh)
        form.addRow('Metal:', self.ramp)
        self.s_width = self._slider(1, 60, 14); self.l_width = self._val()
        self.s_angle = self._slider(0, 359, 135); self.l_angle = self._val()
        self.s_contrast = self._slider(0, 100, 60); self.l_contrast = self._val()
        self.s_shine = self._slider(0, 100, 70); self.l_shine = self._val()
        form.addRow('Bevel width:', self._row(self.s_width, self.l_width))
        form.addRow('Light angle:', self._row(self.s_angle, self.l_angle))
        form.addRow('Contrast:', self._row(self.s_contrast, self.l_contrast))
        form.addRow('Shine:', self._row(self.s_shine, self.l_shine))
        for s in (self.s_width, self.s_angle, self.s_contrast, self.s_shine):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_width.setText(f'{self.s_width.value()} px')
        self.l_angle.setText(f'{self.s_angle.value()}°')
        self.l_contrast.setText(f'{self.s_contrast.value()}')
        self.l_shine.setText(f'{self.s_shine.value()}')

    def _transform(self, rgba):
        return chrome(rgba, ramp=self.ramp.currentData(), width=self.s_width.value(),
                      angle=self.s_angle.value(), contrast=self.s_contrast.value() / 100.0,
                      shine=self.s_shine.value() / 100.0)

    def _layer_stem(self):
        return 'Chrome'


class GlassDialog(_EffectDialog):
    """Effects ▸ Glass… — a glassy inner bevel with edge refraction and a highlight."""
    def __init__(self, win):
        super().__init__(win, 'Glass')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Glass — a clear glassy bevel</b>'))
        info = QLabel('Gives the layer’s shape a clear-glass edge: a soft inner bevel, a small '
                      'refraction that bends the pixels at the rim, and a bright specular highlight.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.s_width = self._slider(1, 60, 12); self.l_width = self._val()
        self.s_refr = self._slider(0, 40, 6); self.l_refr = self._val()
        self.s_op = self._slider(0, 100, 80); self.l_op = self._val()
        self.s_angle = self._slider(0, 359, 135); self.l_angle = self._val()
        form.addRow('Bevel width:', self._row(self.s_width, self.l_width))
        form.addRow('Refraction:', self._row(self.s_refr, self.l_refr))
        form.addRow('Opacity:', self._row(self.s_op, self.l_op))
        form.addRow('Light angle:', self._row(self.s_angle, self.l_angle))
        for s in (self.s_width, self.s_refr, self.s_op, self.s_angle):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_width.setText(f'{self.s_width.value()} px')
        self.l_refr.setText(f'{self.s_refr.value()} px')
        self.l_op.setText(f'{self.s_op.value()} %')
        self.l_angle.setText(f'{self.s_angle.value()}°')

    def _transform(self, rgba):
        return glass(rgba, width=self.s_width.value(), refraction=float(self.s_refr.value()),
                     opacity=self.s_op.value() / 100.0, angle=self.s_angle.value())

    def _layer_stem(self):
        return 'Glass'


class GradientGlowDialog(_EffectDialog):
    """Effects ▸ Gradient Glow… — a multi-stop coloured glow outside the shape."""
    def __init__(self, win):
        super().__init__(win, 'Gradient Glow')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Gradient Glow — a coloured halo</b>'))
        info = QLabel('Surrounds the layer’s shape with a halo that fades through up to four '
                      'colours as it spreads out — a richer Outer Glow. Needs transparency around '
                      'the artwork for the glow to show.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        crow = QHBoxLayout()
        self.b1 = self._colour_btn(self, 's1', (255, 240, 120))
        self.b2 = self._colour_btn(self, 's2', (255, 120, 40))
        self.b3 = self._colour_btn(self, 's3', (180, 20, 60))
        self.b4 = self._colour_btn(self, 's4', (60, 0, 80))
        self.use3 = QCheckBox('3rd'); self.use4 = QCheckBox('4th')
        self.use3.setChecked(True)
        self.use3.toggled.connect(self._refresh); self.use4.toggled.connect(self._refresh)
        for wdg in (QLabel('Inner'), self.b1, self.b2, self.use3, self.b3, self.use4, self.b4):
            crow.addWidget(wdg)
        cw = QWidget(); cw.setLayout(crow); form.addRow('Colours:', cw)
        self.s_width = self._slider(2, 80, 18); self.l_width = self._val()
        self.s_soft = self._slider(0, 100, 60); self.l_soft = self._val()
        self.s_op = self._slider(0, 100, 85); self.l_op = self._val()
        form.addRow('Width:', self._row(self.s_width, self.l_width))
        form.addRow('Softness:', self._row(self.s_soft, self.l_soft))
        form.addRow('Opacity:', self._row(self.s_op, self.l_op))
        for s in (self.s_width, self.s_soft, self.s_op):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_width.setText(f'{self.s_width.value()} px')
        self.l_soft.setText(f'{self.s_soft.value()}')
        self.l_op.setText(f'{self.s_op.value()} %')

    def _stops(self):
        cols = [self._col_rgb('s1'), self._col_rgb('s2')]
        if self.use3.isChecked(): cols.append(self._col_rgb('s3'))
        if self.use4.isChecked(): cols.append(self._col_rgb('s4'))
        n = len(cols)
        return [(i / (n - 1), c) for i, c in enumerate(cols)]

    def _transform(self, rgba):
        return gradient_glow(rgba, stops=self._stops(), width=self.s_width.value(),
                             softness=self.s_soft.value() / 100.0,
                             opacity=self.s_op.value() / 100.0)

    def _layer_stem(self):
        return 'Gradient Glow'


class MotionTrailDialog(_EffectDialog):
    """Effects ▸ Motion Trail… — a directional smear/echo of the whole layer."""
    def __init__(self, win):
        super().__init__(win, 'Motion Trail')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Motion Trail — a sense of speed</b>'))
        info = QLabel('Smears the active layer into a directional trail of fading echoes, as if it '
                      'were moving fast. Works on the whole layer.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.s_angle = self._slider(0, 359, 0); self.l_angle = self._val()
        self.s_len = self._slider(1, 200, 28); self.l_len = self._val()
        self.s_echo = self._slider(2, 24, 8); self.l_echo = self._val()
        self.s_fall = self._slider(10, 95, 70); self.l_fall = self._val()
        form.addRow('Angle:', self._row(self.s_angle, self.l_angle))
        form.addRow('Length:', self._row(self.s_len, self.l_len))
        form.addRow('Echoes:', self._row(self.s_echo, self.l_echo))
        form.addRow('Falloff:', self._row(self.s_fall, self.l_fall))
        for s in (self.s_angle, self.s_len, self.s_echo, self.s_fall):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_angle.setText(f'{self.s_angle.value()}°')
        self.l_len.setText(f'{self.s_len.value()} px')
        self.l_echo.setText(f'{self.s_echo.value()}')
        self.l_fall.setText(f'{self.s_fall.value() / 100.0:.2f}')

    def _transform(self, rgba):
        return motion_trail(rgba, angle=self.s_angle.value(), length=self.s_len.value(),
                            echoes=self.s_echo.value(), falloff=self.s_fall.value() / 100.0)

    def _layer_stem(self):
        return 'Motion Trail'


class TwirlDialog(_EffectDialog):
    """Effects ▸ Twirl… — a radial swirl around the layer centre."""
    def __init__(self, win):
        super().__init__(win, 'Twirl')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Twirl — a radial swirl</b>'))
        info = QLabel('Twists the active layer around its centre, strongest in the middle and easing '
                      'out to the chosen radius.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.s_angle = self._slider(-720, 720, 150); self.l_angle = self._val()
        self.s_radius = self._slider(5, 100, 70); self.l_radius = self._val()
        self.s_fall = self._slider(10, 300, 100); self.l_fall = self._val()
        form.addRow('Twist angle:', self._row(self.s_angle, self.l_angle))
        form.addRow('Radius:', self._row(self.s_radius, self.l_radius))
        form.addRow('Falloff:', self._row(self.s_fall, self.l_fall))
        for s in (self.s_angle, self.s_radius, self.s_fall):
            s.valueChanged.connect(self._refresh)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_angle.setText(f'{self.s_angle.value()}°')
        self.l_radius.setText(f'{self.s_radius.value()} %')
        self.l_fall.setText(f'{self.s_fall.value() / 100.0:.2f}')

    def _transform(self, rgba):
        h, w = rgba.shape[:2]
        rad = self.s_radius.value() / 100.0 * (min(w, h) / 2.0)
        return twirl(rgba, angle=self.s_angle.value(), radius=rad,
                     falloff=self.s_fall.value() / 100.0)

    def _layer_stem(self):
        return 'Twirl'


class _TextureDialog(_EffectDialog):
    """Shared base for the procedural-texture fills (Wood / Marble / Weave). The texture
    is generated at the layer size, then filled into the current selection (or the whole
    layer if nothing is selected). A Seed spin lets the user reroll the pattern."""
    def _texture(self, h, w, seed):
        raise NotImplementedError

    def _seed_row(self, form):
        from PySide6.QtWidgets import QSpinBox as _QS
        self.sp_seed = _QS(); self.sp_seed.setRange(0, 9999); self.sp_seed.setValue(0)
        self.sp_seed.valueChanged.connect(self._refresh)
        reroll = QPushButton('Reroll')
        reroll.clicked.connect(lambda: self.sp_seed.setValue((self.sp_seed.value() + 1) % 10000))
        row = QHBoxLayout(); row.addWidget(self.sp_seed, 1); row.addWidget(reroll)
        hw = QWidget(); hw.setLayout(row); form.addRow('Seed:', hw)

    def _transform(self, rgba):
        src = _ensure_rgba(rgba)
        h, w = src.shape[:2]
        tex = self._texture(h, w, self.sp_seed.value())
        # fill into the current selection, else the whole opaque layer
        mask = self.canvas.sel_mask()
        if mask is None:
            # confine to the layer's own opaque pixels so it reads as a fill of the shape
            m = (src[..., 3] > 0).astype(_np.float32)
            if not m.any():
                m = _np.ones(src.shape[:2], _np.float32)
        else:
            if mask.shape != (h, w):
                mask = _np.asarray(Image.fromarray(mask.astype('uint8'), 'L').resize((w, h), Image.NEAREST))
            m = (mask.astype(_np.float32) / 255.0) * (src[..., 3] > 0)
        wgt = m[..., None]
        out = src.astype(_np.float32)
        out[..., :3] = out[..., :3] * (1.0 - wgt) + tex[..., :3].astype(_np.float32) * wgt
        return out.astype(_np.uint8)


class WoodDialog(_TextureDialog):
    """Effects ▸ Wood… — fill with procedural wood grain."""
    def __init__(self, win):
        super().__init__(win, 'Wood')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Wood — procedural grain</b>'))
        info = QLabel('Fills the current selection (or the opaque pixels of the active layer) with '
                      'generated wood grain — turbulent growth rings between two wood tones.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.ba = self._colour_btn(self, 'a', (150, 95, 45))
        self.bb = self._colour_btn(self, 'b', (95, 55, 22))
        crow = QHBoxLayout(); crow.addWidget(self.ba); crow.addWidget(self.bb)
        cw = QWidget(); cw.setLayout(crow); form.addRow('Wood tones:', cw)
        self.s_space = self._slider(4, 80, 18); self.l_space = self._val()
        self.s_turb = self._slider(0, 100, 50); self.l_turb = self._val()
        self.s_angle = self._slider(0, 359, 0); self.l_angle = self._val()
        form.addRow('Ring spacing:', self._row(self.s_space, self.l_space))
        form.addRow('Grain:', self._row(self.s_turb, self.l_turb))
        form.addRow('Angle:', self._row(self.s_angle, self.l_angle))
        for s in (self.s_space, self.s_turb, self.s_angle):
            s.valueChanged.connect(self._refresh)
        self._seed_row(form)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_space.setText(f'{self.s_space.value()} px')
        self.l_turb.setText(f'{self.s_turb.value()}')
        self.l_angle.setText(f'{self.s_angle.value()}°')

    def _texture(self, h, w, seed):
        return wood(h, w, spacing=self.s_space.value(), turb=self.s_turb.value() / 100.0,
                    color_a=self._col_rgb('a'), color_b=self._col_rgb('b'),
                    angle=self.s_angle.value(), seed=seed)

    def _layer_stem(self):
        return 'Wood'


class MarbleDialog(_TextureDialog):
    """Effects ▸ Marble… — fill with procedural marble veining."""
    def __init__(self, win):
        super().__init__(win, 'Marble')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Marble — procedural veining</b>'))
        info = QLabel('Fills the current selection (or the opaque pixels of the active layer) with '
                      'generated marble — turbulent veins over a stone background.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.bv = self._colour_btn(self, 'vein', (240, 240, 245))
        self.bg = self._colour_btn(self, 'bg', (60, 70, 90))
        crow = QHBoxLayout(); crow.addWidget(QLabel('Vein')); crow.addWidget(self.bv)
        crow.addWidget(QLabel('Stone')); crow.addWidget(self.bg)
        cw = QWidget(); cw.setLayout(crow); form.addRow('Colours:', cw)
        self.s_scale = self._slider(8, 120, 40); self.l_scale = self._val()
        self.s_turb = self._slider(0, 100, 60); self.l_turb = self._val()
        self.s_sharp = self._slider(10, 120, 40); self.l_sharp = self._val()
        form.addRow('Scale:', self._row(self.s_scale, self.l_scale))
        form.addRow('Waviness:', self._row(self.s_turb, self.l_turb))
        form.addRow('Vein sharpness:', self._row(self.s_sharp, self.l_sharp))
        for s in (self.s_scale, self.s_turb, self.s_sharp):
            s.valueChanged.connect(self._refresh)
        self._seed_row(form)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_scale.setText(f'{self.s_scale.value()} px')
        self.l_turb.setText(f'{self.s_turb.value()}')
        self.l_sharp.setText(f'{self.s_sharp.value() / 10.0:.1f}')

    def _texture(self, h, w, seed):
        return marble(h, w, scale=self.s_scale.value(), turb=self.s_turb.value() / 100.0,
                      sharpness=self.s_sharp.value() / 10.0, vein=self._col_rgb('vein'),
                      bg=self._col_rgb('bg'), seed=seed)

    def _layer_stem(self):
        return 'Marble'


class WeaveDialog(_TextureDialog):
    """Effects ▸ Weave… — fill with a basket-weave over/under pattern."""
    def __init__(self, win):
        super().__init__(win, 'Weave')
        v = QVBoxLayout(self)
        v.addWidget(QLabel('<b>Weave — a basket-weave pattern</b>'))
        info = QLabel('Fills the current selection (or the opaque pixels of the active layer) with '
                      'an interlaced basket weave — two colours of strand passing over and under.')
        info.setWordWrap(True); info.setStyleSheet('color:#889'); v.addWidget(info)
        form = QFormLayout(); v.addLayout(form)
        self.ba = self._colour_btn(self, 'a', (170, 120, 70))
        self.bb = self._colour_btn(self, 'b', (120, 80, 45))
        crow = QHBoxLayout(); crow.addWidget(self.ba); crow.addWidget(self.bb)
        cw = QWidget(); cw.setLayout(crow); form.addRow('Strand colours:', cw)
        self.s_strand = self._slider(3, 50, 14); self.l_strand = self._val()
        self.s_gap = self._slider(0, 20, 3); self.l_gap = self._val()
        form.addRow('Strand width:', self._row(self.s_strand, self.l_strand))
        form.addRow('Gap:', self._row(self.s_gap, self.l_gap))
        for s in (self.s_strand, self.s_gap):
            s.valueChanged.connect(self._refresh)
        self._seed_row(form)
        self._finish_ui(v); self._refresh()

    def _update_labels(self):
        self.l_strand.setText(f'{self.s_strand.value()} px')
        self.l_gap.setText(f'{self.s_gap.value()} px')

    def _texture(self, h, w, seed):
        return weave(h, w, strand=self.s_strand.value(), gap=self.s_gap.value(),
                     color_a=self._col_rgb('a'), color_b=self._col_rgb('b'), seed=seed)

    def _layer_stem(self):
        return 'Weave'


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


class GradientMapDialog(QDialog):
    """Adjust ▸ Gradient Map — maps image luminance through a multi-stop colour ramp
    (dark→first stop, light→last). A preset picker plus an add/remove/reposition/recolour
    stop editor, live-previewed and selection-aware in AdjustDialog's spirit."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Gradient Map'); self.setMinimumWidth(340)
        self.active_idx = self.canvas.active
        self.base = self.canvas.img.copy()
        self.stops = [dict(s) for s in GRADMAP_PRESETS['Black → White']]
        v = QVBoxLayout(self)
        prow = QHBoxLayout(); prow.addWidget(QLabel('Preset:'))
        self.preset_cb = QComboBox(); self.preset_cb.addItems(list(GRADMAP_PRESETS))
        self.preset_cb.activated.connect(self._load_preset); prow.addWidget(self.preset_cb, 1)
        v.addLayout(prow)
        self.bar = QLabel(); self.bar.setFixedHeight(18); v.addWidget(self.bar)
        box = QGroupBox('Colour stops'); bl = QVBoxLayout(box)
        self.rows_host = QWidget(); self.rows_lay = QVBoxLayout(self.rows_host)
        self.rows_lay.setContentsMargins(0, 0, 0, 0); bl.addWidget(self.rows_host)
        add = QPushButton('Add stop'); add.clicked.connect(self._add_stop); bl.addWidget(add)
        v.addWidget(box)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._rebuild()

    def _load_preset(self, i):
        self.stops = [dict(s) for s in GRADMAP_PRESETS[self.preset_cb.itemText(i)]]
        self._rebuild()

    def _add_stop(self):
        self.stops.append(dict(pos=0.5, color='#888888')); self._rebuild()

    def _rebuild(self):
        while self.rows_lay.count():
            it = self.rows_lay.takeAt(0); w = it.widget()
            if w: w.setParent(None)
        def tint(btn, st):
            c = QColor(st['color']); btn.setStyleSheet(
                f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')
        for i, st in enumerate(self.stops):
            row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0, 0, 0, 0)
            pos = QDoubleSpinBox(); pos.setRange(0.0, 1.0); pos.setSingleStep(0.05); pos.setDecimals(2)
            pos.setValue(float(st['pos']))
            pos.valueChanged.connect(lambda val, s=st: (s.__setitem__('pos', val), self._apply()))
            cb = QPushButton('Colour'); tint(cb, st)
            def mkpick(s, b):
                def go():
                    c = QColorDialog.getColor(QColor(s['color']), self, 'Stop colour')
                    if c.isValid(): s['color'] = c.name(); tint(b, s); self._apply()
                return go
            cb.clicked.connect(mkpick(st, cb))
            rm = QPushButton('✕'); rm.setFixedWidth(28); rm.setEnabled(len(self.stops) > 2)
            def mkremove(s):
                def go():
                    if len(self.stops) > 2: self.stops.remove(s); self._rebuild()
                return go
            rm.clicked.connect(mkremove(st))
            rl.addWidget(QLabel(f'{i + 1}.')); rl.addWidget(pos, 1); rl.addWidget(cb, 1); rl.addWidget(rm)
            self.rows_lay.addWidget(row)
        self._apply()

    def _preview_bar(self):
        lut = _stops_lut(self.stops)                 # 256x3; stretch across the label
        strip = _np.repeat(lut[None, :, :], 16, axis=0)
        self.bar.setPixmap(QPixmap.fromImage(
            pil2q(Image.fromarray(strip, 'RGB')).scaled(self.bar.width() or 300, 16)))

    def _apply(self):
        self._preview_bar()
        try:
            self.canvas.img = self.canvas._apply_to(self.base, adj_gradientmap(self.stops))
        except Exception:
            self.canvas.img = self.base.copy()
        self.canvas.update()

    def accept(self):
        self.canvas.push_undo_layer(self.active_idx, self.base); super().accept()

    def reject(self):
        self.canvas.img = self.base; self.canvas._fit(); super().reject()


class _LiquifyCanvas(QWidget):
    """The paintable preview surface inside the Liquify Studio: shows the warped image
    scaled to fit, and turns mouse drags into brush dabs on the owning dialog."""
    def __init__(self, dlg):
        super().__init__(); self.dlg = dlg; self.setMouseTracking(True)
        self.setMinimumSize(360, 300); self._last = None

    def paintEvent(self, _e):
        qp = QPainter(self); qp.fillRect(self.rect(), QColor(40, 40, 40))
        pm = self.dlg.preview_pm
        if pm is None: return
        scaled = pm.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._ox = (self.width() - scaled.width()) // 2
        self._oy = (self.height() - scaled.height()) // 2
        self._scale = scaled.width() / max(1, pm.width())
        qp.drawPixmap(self._ox, self._oy, scaled)

    def _to_map(self, pos):
        # widget pixel -> working-resolution map coordinate
        if getattr(self, '_scale', 0) <= 0: return None
        mx = (pos.x() - self._ox) / self._scale; my = (pos.y() - self._oy) / self._scale
        return mx, my

    def mousePressEvent(self, e):
        p = self._to_map(e.position()); self._last = p
        if p: self.dlg.dab(p[0], p[1], 0.0, 0.0)

    def mouseMoveEvent(self, e):
        p = self._to_map(e.position())
        if p is None: return
        if e.buttons() & Qt.LeftButton:
            ddx = ddy = 0.0
            if self._last is not None:
                ddx = p[0] - self._last[0]; ddy = p[1] - self._last[1]
            self.dlg.dab(p[0], p[1], ddx, ddy); self._last = p

    def mouseReleaseEvent(self, _e):
        self._last = None; self.dlg.commit_preview()


class LiquifyStudio(QDialog):
    """Effects ▸ Distort ▸ Liquify… — an interactive warp studio. Maintains a float32
    displacement map (dx, dy) at a capped working resolution; each brush dab mutates it
    via the pure `apply_liquify_dab`; the live preview and the final OK apply it with
    `liquify_warp`/`_warp_remap`. On OK the map is upscaled to full res and written back
    to the active layer with an undo push."""
    CAP = 1000
    MODES = [('Push / Smudge', 'push'), ('Bloat / Expand', 'bloat'), ('Pinch / Shrink', 'pinch'),
             ('Twirl Left', 'twirll'), ('Twirl Right', 'twirlr'), ('Reconstruct / Restore', 'reconstruct')]

    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Liquify Studio'); self.resize(720, 560)
        self.active_idx = self.canvas.active
        self.base_q = self.canvas.img.copy()           # full-res original QImage
        full = _np.asarray(q2pil(self.base_q))         # HxWx4 uint8
        self.full_h, self.full_w = full.shape[:2]
        # working-resolution copy (cap the longest side for responsiveness)
        scale = min(1.0, self.CAP / max(self.full_w, self.full_h))
        self.wk_w = max(1, int(round(self.full_w * scale)))
        self.wk_h = max(1, int(round(self.full_h * scale)))
        if (self.wk_w, self.wk_h) != (self.full_w, self.full_h):
            self.orig = _np.asarray(q2pil(self.base_q).resize((self.wk_w, self.wk_h), Image.BILINEAR))
        else:
            self.orig = full
        self.orig = _ensure_rgba(self.orig)
        self.dx = _np.zeros((self.wk_h, self.wk_w), _np.float32)
        self.dy = _np.zeros((self.wk_h, self.wk_w), _np.float32)
        self.preview_pm = None

        from PySide6.QtWidgets import QSpinBox
        root = QHBoxLayout(self)
        self.view = _LiquifyCanvas(self); root.addWidget(self.view, 1)
        side = QVBoxLayout(); root.addLayout(side)
        side.addWidget(QLabel('<b>Liquify</b> — drag on the image to warp it.'))
        side.addWidget(QLabel('Brush:'))
        self.mode_cb = QComboBox(); self.mode_cb.addItems([n for n, _ in self.MODES]); side.addWidget(self.mode_cb)
        side.addWidget(QLabel('Size:'))
        self.size_s = QSlider(Qt.Horizontal); self.size_s.setRange(5, max(20, min(self.wk_w, self.wk_h)))
        self.size_s.setValue(max(20, min(self.wk_w, self.wk_h) // 6)); side.addWidget(self.size_s)
        side.addWidget(QLabel('Strength:'))
        self.str_s = QSlider(Qt.Horizontal); self.str_s.setRange(1, 100); self.str_s.setValue(50); side.addWidget(self.str_s)
        rbtn = QPushButton('Reset'); rbtn.clicked.connect(self.reset); side.addWidget(rbtn)
        side.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); side.addWidget(bb)
        self._render_preview()

    def _mode(self):
        return self.MODES[self.mode_cb.currentIndex()][1]

    def _render_preview(self):
        warped = liquify_warp(self.orig, self.dx, self.dy)
        self.preview_pm = QPixmap.fromImage(pil2q(Image.fromarray(warped, 'RGBA')))
        self.view.update()

    def dab(self, cx, cy, ddx, ddy):
        # strength scales per-mode; push drives the drag delta directly
        s = self.str_s.value() / 100.0
        mode = self._mode()
        strength = s * (3.0 if mode == 'push' else 1.0)
        apply_liquify_dab(self.dx, self.dy, mode, cx, cy, self.size_s.value(), strength, drag=(ddx, ddy))
        self._render_preview()

    def commit_preview(self):
        self._render_preview()

    def reset(self):
        self.dx[:] = 0.0; self.dy[:] = 0.0; self._render_preview()

    def accept(self):
        # upscale the working displacement map to full resolution (offsets scale with size)
        if (self.wk_w, self.wk_h) != (self.full_w, self.full_h):
            sx = self.full_w / self.wk_w; sy = self.full_h / self.wk_h
            fdx = _np.asarray(Image.fromarray(self.dx).resize((self.full_w, self.full_h), Image.BILINEAR)) * sx
            fdy = _np.asarray(Image.fromarray(self.dy).resize((self.full_w, self.full_h), Image.BILINEAR)) * sy
        else:
            fdx, fdy = self.dx, self.dy
        full = _ensure_rgba(_np.asarray(q2pil(self.base_q)))
        warped = liquify_warp(full, fdx.astype(_np.float32), fdy.astype(_np.float32))
        self.canvas.push_undo_layer(self.active_idx, self.base_q)
        self.canvas.img = pil2q(Image.fromarray(warped, 'RGBA')); self.canvas._fit()
        super().accept()


class ExportDialog(QDialog):
    """File ▸ Export… — pick a format (PNG/JPEG/WEBP/GIF/BMP), a quality for the lossy
    ones with a live estimated file size, and (PNG) a transparency toggle. Writes via
    Pillow/QImage. The flattened composite is the thing exported."""
    def __init__(self, win):
        super().__init__(win)
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Export Image'); self.setMinimumWidth(380)
        self.img = self.canvas.composited()
        v = QVBoxLayout(self); form = QFormLayout(); v.addLayout(form)
        self.fmt_cb = QComboBox()
        for label, *_ in EXPORT_FORMATS: self.fmt_cb.addItem(label)
        self.fmt_cb.setCurrentIndex(0)
        self.fmt_cb.currentIndexChanged.connect(self._fmt_changed)
        form.addRow('Format:', self.fmt_cb)
        # quality
        qrow = QHBoxLayout()
        self.q_sl = QSlider(Qt.Horizontal); self.q_sl.setRange(1, 100); self.q_sl.setValue(90)
        self.q_lbl = QLabel('90'); self.q_lbl.setMinimumWidth(32)
        self.q_sl.valueChanged.connect(lambda x: (self.q_lbl.setText(str(x)), self._estimate()))
        qrow.addWidget(self.q_sl, 1); qrow.addWidget(self.q_lbl)
        self.q_holder = QWidget(); self.q_holder.setLayout(qrow)
        form.addRow('Quality:', self.q_holder)
        # transparency
        self.alpha_cb = QCheckBox('Keep transparency')
        self.alpha_cb.setChecked(True)
        self.alpha_cb.toggled.connect(lambda _=0: self._estimate())
        form.addRow('', self.alpha_cb)
        # estimate
        self.size_lbl = QLabel('—'); self.size_lbl.setStyleSheet('color:#8a94a0')
        form.addRow('Estimated size:', self.size_lbl)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Save).setText('Export…')
        bb.accepted.connect(self._do_export); bb.rejected.connect(self.reject); v.addWidget(bb)
        self._fmt_changed()

    def _fmt(self):
        return EXPORT_FORMATS[self.fmt_cb.currentIndex()]

    def _fmt_changed(self):
        _, pf, ext, supports_alpha, has_quality = self._fmt()
        self.q_holder.setEnabled(has_quality)
        self.alpha_cb.setEnabled(supports_alpha)
        if not supports_alpha: self.alpha_cb.setChecked(False)
        elif pf == 'PNG': self.alpha_cb.setChecked(True)
        self._estimate()

    def _encode(self):
        _, pf, ext, supports_alpha, has_quality = self._fmt()
        return export_bytes(self.img, pf, self.q_sl.value(),
                            keep_alpha=self.alpha_cb.isChecked() and supports_alpha)

    def _estimate(self):
        try:
            n = len(self._encode())
            self.size_lbl.setText(f'{n/1024:.0f} KB' if n < 1024*1024 else f'{n/1024/1024:.1f} MB')
        except Exception as e:
            self.size_lbl.setText('—')

    def _do_export(self):
        _, pf, ext, supports_alpha, has_quality = self._fmt()
        start = self.win.path or os.path.join(_just_dir('pics'), 'image')
        start = os.path.splitext(start)[0] + ext
        path, _sel = QFileDialog.getSaveFileName(self, 'Export image', start,
                                                 f'{self._fmt()[0]} (*{ext})')
        if not path:
            return
        if not path.lower().endswith(ext): path += ext
        try:
            data = self._encode()
            with open(path, 'wb') as fh: fh.write(data)
            self.win.status.showMessage(f'Exported to {path}', 4000); _justapps_recent('paint', path)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, APP, f"Couldn't export the image.\n{e}")


class OptimiseDialog(QDialog):
    """File ▸ Reduce File Size (optimise)… — shrink a photo's file size for web/email
    using a modern codec (AVIF/WebP, much smaller than JPEG), a target-size OR quality
    mode, an optional max-dimension cap, and metadata stripping. Shows a live
    "Original → Optimised (−%)" readout and saves the flattened composite."""
    def __init__(self, win):
        super().__init__(win)
        from PySide6.QtCore import QTimer
        self.win = win; self.canvas = win.canvas
        self.setWindowTitle('Reduce File Size (optimise)'); self.setMinimumWidth(420)
        self.img = self.canvas.composited()
        self.pil = q2pil(self.img) if HAS_PIL else None
        self.fmts = optimise_formats() if HAS_PIL else []

        v = QVBoxLayout(self); form = QFormLayout(); v.addLayout(form)

        self.fmt_cb = QComboBox()
        for label, *_ in self.fmts: self.fmt_cb.addItem(label)
        self.fmt_cb.currentIndexChanged.connect(self._on_change)
        form.addRow('Format:', self.fmt_cb)

        # mode switch
        mrow = QHBoxLayout()
        self.mode_cb = QComboBox(); self.mode_cb.addItems(['Target size', 'Quality'])
        self.mode_cb.currentIndexChanged.connect(self._mode_changed)
        mrow.addWidget(self.mode_cb, 1)
        mh = QWidget(); mh.setLayout(mrow)
        form.addRow('Mode:', mh)

        # target size (KB)
        trow = QHBoxLayout()
        self.tgt_sp = QSpinBox(); self.tgt_sp.setRange(5, 20000); self.tgt_sp.setValue(100); self.tgt_sp.setSuffix(' KB')
        self.tgt_sp.valueChanged.connect(lambda _=0: self._on_change())
        trow.addWidget(self.tgt_sp, 1)
        self.tgt_holder = QWidget(); self.tgt_holder.setLayout(trow)
        form.addRow('Target size:', self.tgt_holder)

        # quality
        qrow = QHBoxLayout()
        self.q_sl = QSlider(Qt.Horizontal); self.q_sl.setRange(1, 95); self.q_sl.setValue(75)
        self.q_lbl = QLabel('75'); self.q_lbl.setMinimumWidth(28)
        self.q_sl.valueChanged.connect(lambda x: (self.q_lbl.setText(str(x)), self._on_change()))
        qrow.addWidget(self.q_sl, 1); qrow.addWidget(self.q_lbl)
        self.q_holder = QWidget(); self.q_holder.setLayout(qrow)
        form.addRow('Quality:', self.q_holder)

        # max dimension
        drow = QHBoxLayout()
        self.dim_cb = QCheckBox('Limit longest side to')
        self.dim_cb.toggled.connect(lambda _=0: self._on_change())
        self.dim_sp = QSpinBox(); self.dim_sp.setRange(16, 20000)
        self.dim_sp.setValue(min(1600, max(self.img.width(), self.img.height())))
        self.dim_sp.setSuffix(' px')
        self.dim_sp.valueChanged.connect(lambda _=0: self._on_change())
        drow.addWidget(self.dim_cb); drow.addWidget(self.dim_sp, 1)
        dh = QWidget(); dh.setLayout(drow)
        form.addRow('Max dimension:', dh)
        note = QLabel('Shrinking the dimensions is the single biggest way to cut file size.')
        note.setWordWrap(True); note.setStyleSheet('color:#8a94a0;font-size:11px')
        form.addRow('', note)

        # strip metadata
        self.meta_cb = QCheckBox('Strip metadata (EXIF / colour profile)')
        self.meta_cb.setChecked(True)
        self.meta_cb.toggled.connect(lambda _=0: self._on_change())
        form.addRow('', self.meta_cb)

        # live readout
        self.read_lbl = QLabel('—'); self.read_lbl.setWordWrap(True)
        self.read_lbl.setStyleSheet('color:#cdd3da')
        form.addRow('Savings:', self.read_lbl)

        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_btn = bb.button(QDialogButtonBox.Save); self.save_btn.setText('Save…')
        bb.accepted.connect(self._do_save); bb.rejected.connect(self.reject); v.addWidget(bb)

        # baseline original size (encode once): PNG for lossless-ish images, else JPEG q92.
        self._baseline = None
        self._last_bytes = None
        # debounce so dragging sliders doesn't re-encode on every tick
        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(220)
        self._timer.timeout.connect(self._recompute)

        if not HAS_PIL:
            self.read_lbl.setText('Optimising needs Pillow (not installed).')
            self.save_btn.setEnabled(False)
            return
        self._compute_baseline()
        self._mode_changed()

    def _fmt(self):
        return self.fmts[self.fmt_cb.currentIndex()]

    def _compute_baseline(self):
        """Encode the current image once as a fair 'before' size: JPEG q92 for photos
        (what the old shrink-a-JPEG plugin produced), which is a sensible reference."""
        try:
            self._baseline = len(optimize_bytes(self.pil, 'JPEG', quality=92, strip_meta=False))
        except Exception:
            self._baseline = None

    def _mode_changed(self):
        target = (self.mode_cb.currentIndex() == 0)
        _, pf, ext, lossy = self._fmt()
        # PNG is lossless → neither target nor quality applies; dimensions/palette do.
        self.tgt_holder.setEnabled(target and lossy)
        self.q_holder.setEnabled((not target) and lossy)
        self.mode_cb.setEnabled(lossy)
        self._on_change()

    def _on_change(self):
        self._timer.start()

    def _max_dim(self):
        return self.dim_sp.value() if self.dim_cb.isChecked() else None

    def _encode(self):
        _, pf, ext, lossy = self._fmt()
        target = (self.mode_cb.currentIndex() == 0)
        kw = dict(max_dim=self._max_dim(), strip_meta=self.meta_cb.isChecked())
        if lossy and target:
            kw['target_kb'] = self.tgt_sp.value()
        elif lossy:
            kw['quality'] = self.q_sl.value()
        return optimize_bytes(self.pil, pf, **kw)

    def _recompute(self):
        if not HAS_PIL: return
        try:
            data = self._encode()
            self._last_bytes = data
            n = len(data)
            out = f'{n/1024:.0f} KB' if n < 1024*1024 else f'{n/1024/1024:.1f} MB'
            if self._baseline:
                o = self._baseline
                orig = f'{o/1024:.0f} KB' if o < 1024*1024 else f'{o/1024/1024:.1f} MB'
                pct = (1 - n / o) * 100
                self.read_lbl.setText(f'Original ≈ {orig} → Optimised ≈ {out}  (−{pct:.0f}%)')
            else:
                self.read_lbl.setText(f'Optimised ≈ {out}')
        except Exception as e:
            self._last_bytes = None
            self.read_lbl.setText(f'—  ({e})')

    def _do_save(self):
        _, pf, ext, lossy = self._fmt()
        try:
            data = self._encode()
        except Exception as e:
            QMessageBox.warning(self, APP, f"Couldn't optimise the image.\n{e}"); return
        start = self.win.path or os.path.join(_just_dir('pics'), 'image')
        start = os.path.splitext(start)[0] + '-web' + ext
        path, _sel = QFileDialog.getSaveFileName(self, 'Save optimised image', start,
                                                 f'{self._fmt()[0]} (*{ext})')
        if not path:
            return
        if not path.lower().endswith(ext): path += ext
        try:
            with open(path, 'wb') as fh: fh.write(data)
            kb = len(data) / 1024
            self.win.status.showMessage(f'Saved optimised {kb:.0f} KB to {path}', 4000)
            _justapps_recent('paint', path)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, APP, f"Couldn't save the image.\n{e}")


class Main(QMainWindow):
    TOOLS = [('brush', 'Brush', '🖌'), ('eraser', 'Eraser', '◻'), ('line', 'Line', '╱'),
             ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'), ('fill', 'Fill', '🪣'),
             ('gradient', 'Gradient fill (drag)', '▨'), ('picker', 'Pick colour', '🎯'),
             ('text', 'Text', 'A'), ('clone', 'Clone — Ctrl-click to set source', '❏'),
             ('redeye', 'Red-eye removal', '◉'), ('dodge', 'Dodge — lighten', '☀'),
             ('burn', 'Burn — darken', '◐'),
             ('heal', 'Heal / Spot-heal — blend out blemishes with surrounding texture', '🩹'),
             ('sponge', 'Sponge — saturate / desaturate locally', '🧽'),
             ('oil', 'Oil brush — wet paint that blends (natural media)', '🎨'),
             ('smudge', 'Smudge / palette knife — drag and mix paint', '👆'),
             ('transform', 'Free Transform — scale / rotate (Shift=aspect) / skew (Ctrl+edge); Enter or double-click to apply, Esc to cancel', '⤡'),
             ('mrect', 'Select — rectangle', '⬚'), ('mellipse', 'Select — ellipse', '◌'),
             ('lasso', 'Lasso — drag a freehand selection', '➰'),
             ('polyselect', 'Polygon select — click vertices, double-click / Enter to close', '△'),
             ('wand', 'Magic wand — click to select by colour', '✦'),
             ('cutout', 'Cutout — click a background to erase it to transparency', '✂'),
             ('smartmask', 'Smart Mask — scribble KEEP (subject) / REMOVE (background), then Apply', '✎')]

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
        # ---- mask panel ----
        mbox = QWidget(); mv = QVBoxLayout(mbox); mv.setContentsMargins(0, 2, 0, 0); mv.setSpacing(4)
        line = QLabel('Layer mask'); line.setStyleSheet('font-weight:600;color:#9aa4ad')
        mv.addWidget(line)
        mrow = QHBoxLayout()
        self.mask_thumb = QLabel(); self.mask_thumb.setFixedSize(48, 36)
        self.mask_thumb.setStyleSheet('border:1px solid #556; background:#333')
        self.mask_thumb.setAlignment(Qt.AlignCenter)
        mrow.addWidget(self.mask_thumb)
        self.edit_mask_cb = QCheckBox('Edit mask')
        self.edit_mask_cb.setToolTip('Paint the mask (black hides, white reveals) instead of the layer')
        self.edit_mask_cb.toggled.connect(lambda on: None if self._layer_sync else self.canvas.set_edit_mask(on))
        mrow.addWidget(self.edit_mask_cb); mrow.addStretch(1); mv.addLayout(mrow)
        mbtns = QHBoxLayout()
        self.add_mask_btn = QPushButton('Add Mask'); self.add_mask_btn.setToolTip('Give this layer a white (reveal-all) mask')
        self.add_mask_btn.clicked.connect(lambda: self.canvas.add_mask(False))
        self.add_mask_sel_btn = QPushButton('From Selection'); self.add_mask_sel_btn.setToolTip('Mask the layer to the current selection')
        self.add_mask_sel_btn.clicked.connect(lambda: self.canvas.add_mask(True))
        self.del_mask_btn = QPushButton('Delete Mask'); self.del_mask_btn.setToolTip('Remove the mask (hidden areas are discarded)')
        self.del_mask_btn.clicked.connect(lambda: self.canvas.delete_mask(False))
        for b in (self.add_mask_btn, self.add_mask_sel_btn, self.del_mask_btn):
            mbtns.addWidget(b)
        mv.addLayout(mbtns)
        v.addWidget(mbox)
        dock.setWidget(w); self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.layers_dock = dock

    def refresh_layers(self):
        if not hasattr(self, 'layer_list'): return
        self._layer_sync = True
        self.layer_list.clear()
        for l in reversed(self.canvas.layers):
            it = QListWidgetItem(l.name + ('  ◧' if l.mask is not None else ''))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if l.visible else Qt.Unchecked)
            self.layer_list.addItem(it)
        n = len(self.canvas.layers)
        self.layer_list.setCurrentRow(n - 1 - self.canvas.active)
        al = self.canvas.layers[self.canvas.active]
        self.opacity_sl.setValue(int(al.opacity * 100))
        self.blend_cb.setCurrentIndex(BLEND_NAMES.index(al.blend) if al.blend in BLEND_NAMES else 0)
        self._refresh_mask_panel(al)
        self._layer_sync = False

    def _refresh_mask_panel(self, al):
        if not hasattr(self, 'mask_thumb'): return
        has = al.mask is not None
        self.add_mask_btn.setEnabled(not has)
        self.add_mask_sel_btn.setEnabled(not has)
        self.del_mask_btn.setEnabled(has)
        self.edit_mask_cb.setEnabled(has)
        self.edit_mask_cb.setChecked(has and self.canvas.edit_mask)
        if has:
            pm = QPixmap.fromImage(al.mask.convertToFormat(QImage.Format_ARGB32)) \
                     .scaled(48, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.mask_thumb.setPixmap(pm)
        else:
            self.mask_thumb.clear(); self.mask_thumb.setText('—')

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
        # --- Smart Mask controls (scribble cut-out) ---
        self.sm_lbl = QLabel(' Smart Mask ')
        self.sm_mode_cb = QComboBox(); self.sm_mode_cb.addItems(['Paint KEEP (subject)', 'Paint REMOVE (background)'])
        self.sm_mode_cb.setToolTip('What the left-drag paints (right-drag always paints REMOVE)')
        self.sm_mode_cb.currentIndexChanged.connect(
            lambda i: setattr(self.canvas, 'sm_mode', 'remove' if i else 'keep'))
        self.sm_brush_spin = QSpinBox(); self.sm_brush_spin.setRange(1, 200)
        self.sm_brush_spin.setValue(int(self.canvas.sm_brush)); self.sm_brush_spin.setSuffix(' px')
        self.sm_brush_spin.setToolTip('Scribble brush size')
        self.sm_brush_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'sm_brush', v))
        self.sm_apply_btn = QPushButton('Apply…'); self.sm_apply_btn.setToolTip('Build the cut-out mask from your scribbles')
        self.sm_apply_btn.clicked.connect(self.smart_mask_apply)
        self.sm_clear_btn = QPushButton('Clear scribbles'); self.sm_clear_btn.clicked.connect(lambda: self.canvas.sm_clear())
        for wdg in (self.sm_lbl, self.sm_mode_cb, self.sm_brush_spin, self.sm_apply_btn, self.sm_clear_btn):
            top.addWidget(wdg); wdg.setVisible(False)
        # --- shape fill controls (rect / ellipse) ---
        self.fill_lbl = QLabel(' Shape ')
        self.fill_cb = QComboBox(); self.fill_cb.addItems(['Outline', 'Fill', 'Both'])
        self.fill_cb.setToolTip('How rectangle and ellipse are drawn')
        _FILLMODE = ['stroke', 'fill', 'both']
        self.fill_cb.currentIndexChanged.connect(lambda i: setattr(self.canvas, 'shape_fill', _FILLMODE[i]))
        self.fill_col_btn = QPushButton('Fill colour'); self.fill_col_btn.setToolTip('Fill colour (default: the current colour)')
        self.fill_col_btn.clicked.connect(self._pick_fill_color)
        for wdg in (self.fill_lbl, self.fill_cb, self.fill_col_btn):
            top.addWidget(wdg); wdg.setVisible(False)
        # --- gradient colour controls ---
        self.grad_lbl = QLabel(' Gradient ')
        self.grad_a_btn = QPushButton('Start'); self.grad_a_btn.clicked.connect(lambda: self._pick_grad('start'))
        self.grad_b_btn = QPushButton('End'); self.grad_b_btn.clicked.connect(lambda: self._pick_grad('end'))
        self.grad_trans_cb = QCheckBox('Fade to clear')
        self.grad_trans_cb.setToolTip('Fade the end colour to transparent instead of a second colour')
        self.grad_trans_cb.toggled.connect(self._grad_trans)
        for wdg in (self.grad_lbl, self.grad_a_btn, self.grad_b_btn, self.grad_trans_cb):
            top.addWidget(wdg); wdg.setVisible(False)
        # --- Heal controls ---
        self.heal_lbl = QLabel(' Heal detail ')
        self.heal_spin = QSpinBox(); self.heal_spin.setRange(0, 100); self.heal_spin.setValue(int(self.canvas.heal_strength * 100))
        self.heal_spin.setSuffix(' %'); self.heal_spin.setToolTip('How much surrounding texture/grain to keep (0 = smooth, 100 = full)')
        self.heal_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'heal_strength', v / 100.0))
        for wdg in (self.heal_lbl, self.heal_spin):
            top.addWidget(wdg); wdg.setVisible(False)
        # --- Sponge controls ---
        self.sponge_lbl = QLabel(' Sponge ')
        self.sponge_mode_cb = QComboBox(); self.sponge_mode_cb.addItems(['Saturate', 'Desaturate'])
        self.sponge_mode_cb.setToolTip('Push saturation up or down')
        self.sponge_mode_cb.currentIndexChanged.connect(
            lambda i: setattr(self.canvas, 'sponge_mode', 'desaturate' if i else 'saturate'))
        self.sponge_flow_spin = QSpinBox(); self.sponge_flow_spin.setRange(1, 100); self.sponge_flow_spin.setValue(int(self.canvas.sponge_flow))
        self.sponge_flow_spin.setSuffix(' %'); self.sponge_flow_spin.setToolTip('Flow / strength per dab')
        self.sponge_flow_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'sponge_flow', v))
        for wdg in (self.sponge_lbl, self.sponge_mode_cb, self.sponge_flow_spin):
            top.addWidget(wdg); wdg.setVisible(False)
        self._tint_grad_btns()
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
        f.addAction(self.act('Open from &Library…', self.open_from_library))
        f.addAction(self.act('Merge Photos to &Panorama…', self.merge_panorama))
        f.addAction(self.act('&Save', self.save, QKeySequence.Save))
        f.addAction(self.act('Save &As…', self.save_as, QKeySequence.SaveAs))
        f.addAction(self.act('&Export…', self.export, 'Ctrl+Shift+E'))
        f.addAction(self.act('&Reduce File Size (optimise)…', self.reduce_filesize, 'Ctrl+Shift+R'))
        f.addSeparator(); f.addAction(self.act('&Quit', self.close, QKeySequence.Quit))
        e = m.addMenu('&Edit')
        e.addAction(self.act('&Undo', self.canvas.do_undo, QKeySequence.Undo))
        e.addAction(self.act('&Redo', self.canvas.do_redo, QKeySequence.Redo))
        img = m.addMenu('&Image')
        img.addAction(self.act('&Resize Image…', self.resize_image))
        img.addAction(self.act('&Enlarge (smart upscale)…', self.dlg_enlarge))
        img.addAction(self.act('&Canvas Size…', self.canvas_size))
        img.addAction(self.act('Crop to &Selection', lambda: self.canvas.crop_to_sel()))
        img.addAction(self.act('&Trim Transparent Border…', self.trim_photo))
        img.addAction(self.act('&Straighten…', self.dlg_straighten))
        img.addSeparator()
        img.addAction(self.act('Rotate 90° &Right', lambda: self.canvas.rotate(90)))
        img.addAction(self.act('Rotate 90° &Left', lambda: self.canvas.rotate(-90)))
        img.addAction(self.act('Rotate &180°', lambda: self.canvas.rotate(180)))
        img.addAction(self.act('Flip &Horizontal', lambda: self.canvas.flip(True)))
        img.addAction(self.act('Flip &Vertical', lambda: self.canvas.flip(False)))
        img.addSeparator()
        img.addAction(self.act('Add &Overlay…', self.add_overlay_dialog))
        img.addAction(self.act('&Place Texture…', self.place_texture_dialog))
        img.addAction(self.act('Add &Frame / Edge…', self.add_frame_dialog))
        img.addSeparator()
        img.addAction(self.act('Cu&tout Studio… (remove background)', self.cutout_studio))
        img.addAction(self.act('Smart &Mask (cut out subject)…', self.smart_mask_apply))
        img.addSeparator()
        img.addAction(self.act('Lens &Flare…', self.dlg_lens_flare))

        adj = m.addMenu('&Adjust')
        adj.addAction(self.act('&Brightness / Contrast…', self.dlg_brightness))
        adj.addAction(self.act('&Levels…', self.dlg_levels))
        adj.addAction(self.act('Cur&ves…', self.dlg_curves))
        adj.addAction(self.act('&Hue / Saturation…', self.dlg_huesat))
        adj.addAction(self.act('Vi&brance…', self.dlg_vibrance))
        adj.addAction(self.act('Channel &Mixer…', self.dlg_channelmixer))
        adj.addAction(self.act('Colour &Temperature…', self.dlg_temperature))
        adj.addAction(self.act('Colour &Balance…', self.dlg_colorbalance))
        adj.addAction(self.act('&Threshold…', self.dlg_threshold))
        adj.addAction(self.act('&Posterize…', self.dlg_posterize))
        adj.addAction(self.act('&Gradient Map…', self.dlg_gradientmap))
        adj.addAction(self.act('S&hadow / Highlight…', self.dlg_shadow_highlight))
        adj.addAction(self.act('Selective Colo&ur…', self.dlg_selective_color))
        adj.addSeparator()
        adj.addAction(self.act('Auto &Contrast', lambda: self.canvas.apply_region(adj_autocontrast)))
        adj.addAction(self.act('&Equalize', lambda: self.canvas.apply_region(adj_equalize)))
        adj.addAction(self.act('&Greyscale', lambda: self.canvas.apply_region(adj_grayscale)))
        adj.addAction(self.act('&Invert (Negative)', lambda: self.canvas.apply_region(adj_invert)))
        adj.addAction(self.act('Se&pia', lambda: self.canvas.apply_region(adj_sepia)))
        adj.addSeparator()
        adj.addAction(self.act('Smooth &Skin (portrait retouch)…', self.dlg_smooth_skin))

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

        fx = m.addMenu('&Photo FX')
        fx.addAction(self.act('&Film Look…', self.dlg_film_look))
        fx.addAction(self.act('&Art Style…', self.dlg_art_style))

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
        lay.addSeparator()
        lay.addAction(self.act('Add Layer &Mask', lambda: self.canvas.add_mask(False)))
        lay.addAction(self.act('Add Mask From &Selection', lambda: self.canvas.add_mask(True)))
        lay.addAction(self.act('&Apply Mask', lambda: self.canvas.delete_mask(True)))
        lay.addAction(self.act('De&lete Mask', lambda: self.canvas.delete_mask(False)))

        fx = m.addMenu('Effe&cts')
        fx.addAction(self.act('Drop &Shadow…', lambda: self._fx_dialog('shadow')))
        fx.addAction(self.act('Outer &Glow…', lambda: self._fx_dialog('glow')))
        fx.addSeparator()
        edges = fx.addMenu('&Bevels && edges')
        edges.addAction(self.act('&Bevel…', lambda: self._effect_dialog(BevelDialog)))
        edges.addAction(self.act('&Chrome…', lambda: self._effect_dialog(ChromeDialog)))
        edges.addAction(self.act('G&lass…', lambda: self._effect_dialog(GlassDialog)))
        edges.addAction(self.act('&Gradient Glow…', lambda: self._effect_dialog(GradientGlowDialog)))
        dist = fx.addMenu('&Distort')
        dist.addAction(self.act('&Motion Trail…', lambda: self._effect_dialog(MotionTrailDialog)))
        dist.addAction(self.act('&Twirl…', lambda: self._effect_dialog(TwirlDialog)))
        dist.addAction(self.act('&Liquify Studio…', self.liquify_studio))
        tex = fx.addMenu('&Textures')
        tex.addAction(self.act('&Wood…', lambda: self._effect_dialog(WoodDialog)))
        tex.addAction(self.act('&Marble…', lambda: self._effect_dialog(MarbleDialog)))
        tex.addAction(self.act('W&eave…', lambda: self._effect_dialog(WeaveDialog)))
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
                                       QSpinBox, QDialogButtonBox)
        dlg = QDialog(self); dlg.setWindowTitle('Add Text'); dlg.resize(440, 180)
        v = QVBoxLayout(dlg)
        le = QLineEdit(); le.setPlaceholderText('Text to add…')
        fc = GroupedFontCombo(); fc.setCurrentFamily(getattr(self, '_text_font', 'Noto Sans'))
        sp = QSpinBox(); sp.setRange(6, 400); sp.setSuffix(' px'); sp.setValue(getattr(self, '_text_px', max(16, self.canvas.size * 4)))
        form = QFormLayout(); form.addRow('Text:', le); form.addRow('Font:', fc); form.addRow('Size:', sp)
        v.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        le.setFocus()
        if dlg.exec() != QDialog.Accepted or not le.text().strip():
            return None
        self._text_font = fc.currentFamily(); self._text_px = sp.value()
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

    def smart_mask_apply(self):
        """Build a cut-out mask from the Smart Mask scribbles, then let the user send it
        to a selection and/or a new transparent layer, with a feather control."""
        if not self._need_pil(): return
        self.set_tool('smartmask')
        c = self.canvas
        if c.sm_keep is None or not c.sm_keep.any():
            QMessageBox.information(self, APP,
                'Scribble over your subject with the Smart Mask tool first (green = KEEP), '
                'and over the background (red = REMOVE — right-drag, or switch the mode), '
                'then Apply.')
            return
        engine = 'OpenCV grabCut' if HAS_CV2 else 'NumPy colour model'
        dlg = QDialog(self); dlg.setWindowTitle('Smart Mask — cut out subject'); dlg.resize(440, 300)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel('<b>Separate your subject from the background.</b>'))
        info = QLabel('Green KEEP scribbles mark the subject, red REMOVE scribbles mark the '
                      'background. Raise the feather for soft edges (hair, foliage).<br>'
                      f'<i>Engine: {engine}.</i>')
        info.setWordWrap(True); v.addWidget(info)
        frow = QHBoxLayout(); frow.addWidget(QLabel('Edge feather:'))
        fs = QSlider(Qt.Horizontal); fs.setRange(0, 30); fs.setValue(2)
        fval = QLabel('2 px'); fs.valueChanged.connect(lambda x: fval.setText(f'{x} px'))
        frow.addWidget(fs, 1); frow.addWidget(fval); v.addLayout(frow)
        sel_cb = QCheckBox('Set the subject as the selection'); sel_cb.setChecked(True)
        cut_cb = QCheckBox('Cut the subject out to a new layer'); cut_cb.setChecked(False)
        v.addWidget(sel_cb); v.addWidget(cut_cb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Apply')
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        feather = fs.value()
        mask = c.smart_mask_result(feather=feather)
        if mask is None or not mask.any():
            QMessageBox.information(self, APP,
                'The Smart Mask could not find a subject — add more KEEP and REMOVE scribbles and try again.')
            return
        cov = int((mask > 127).sum())
        if cut_cb.isChecked():
            c.smart_mask_cutout_layer(mask)      # pushes its own full snapshot
        if sel_cb.isChecked():
            c.smart_mask_to_selection(mask)
        c.update()
        self.status.showMessage(f'Smart Mask: {cov} subject pixels ({engine}).', 4000)

    # ---- state ----
    def set_tool(self, t):
        if t != 'transform' and self.canvas.tf is not None:   # bake pending Free Transform
            self.canvas.tf_commit()
        if t != 'polyselect':                         # abandon any half-built polygon
            self.canvas.poly_pts = None; self.canvas.poly_cur = None
        if t != 'lasso':
            self.canvas.lasso_pts = None
        self.canvas.tool = t
        self.canvas.update()
        if hasattr(self, 'wand_spin'):
            for wdg in (self.wand_lbl, self.wand_spin, self.wand_cb):
                wdg.setVisible(t == 'wand')
        if hasattr(self, 'sm_apply_btn'):
            for wdg in (self.sm_lbl, self.sm_mode_cb, self.sm_brush_spin, self.sm_apply_btn, self.sm_clear_btn):
                wdg.setVisible(t == 'smartmask')
        if hasattr(self, 'fill_cb'):
            for wdg in (self.fill_lbl, self.fill_cb, self.fill_col_btn):
                wdg.setVisible(t in ('rect', 'ellipse'))
            for wdg in (self.grad_lbl, self.grad_a_btn, self.grad_b_btn, self.grad_trans_cb):
                wdg.setVisible(t == 'gradient')
        if hasattr(self, 'heal_spin'):
            for wdg in (self.heal_lbl, self.heal_spin):
                wdg.setVisible(t == 'heal')
        if hasattr(self, 'sponge_mode_cb'):
            for wdg in (self.sponge_lbl, self.sponge_mode_cb, self.sponge_flow_spin):
                wdg.setVisible(t == 'sponge')
        if t == 'transform':
            self.canvas.setFocus(); self.canvas.tf_begin()
    def set_pos(self, p): self.pos_lbl.setText(f'{p.x()}, {p.y()}   ')

    def _pick_fill_color(self):
        start = self.canvas.shape_fill_color or self.canvas.color
        c = QColorDialog.getColor(start, self, 'Fill colour')
        if c.isValid():
            self.canvas.shape_fill_color = c
            self.fill_col_btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"}')

    def _pick_grad(self, which):
        start = self.canvas.grad_start if which == 'start' else self.canvas.grad_end
        c = QColorDialog.getColor(start, self, f'Gradient {which} colour')
        if c.isValid():
            setattr(self.canvas, 'grad_start' if which == 'start' else 'grad_end', c)
            self._tint_grad_btns()

    def _grad_trans(self, on):
        self.canvas.grad_end_transparent = on
        self.grad_b_btn.setEnabled(not on); self._tint_grad_btns()

    def _tint_grad_btns(self):
        if not hasattr(self, 'grad_a_btn'): return
        for btn, col in ((self.grad_a_btn, self.canvas.grad_start), (self.grad_b_btn, self.canvas.grad_end)):
            c = QColor(col)
            btn.setStyleSheet(f'background:{c.name()};color:{"#fff" if c.lightness() < 140 else "#000"};padding:3px 8px')

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

    def _effect_dialog(self, cls):
        """Open one of the new Effects studios (Bevel/Chrome/Glass/Gradient Glow/Motion
        Trail/Twirl/Wood/Marble/Weave). They need Pillow+NumPy for their maths."""
        if not self._need_pil():
            return
        cls(self).exec()

    def liquify_studio(self):
        """Open the interactive Warp / Liquify Studio on the active layer."""
        if not self._need_pil():
            return
        LiquifyStudio(self).exec()

    def dlg_lens_flare(self):
        """Open the Lens Flare studio (live preview over the composited image)."""
        LensFlareDialog(self).exec()

    def apply_lens_flare(self, lx, ly, params):
        """Composite a lens flare onto a NEW 'screen'-blend layer at (lx, ly).
        Non-destructive: snapshots, inserts a fresh layer above the active one,
        paints the flare into it and refreshes. Returns the new Layer."""
        c = self.canvas
        w, h = c.doc_w(), c.doc_h()
        flare = render_lens_flare(w, h, lx, ly, params)
        c.snapshot_full()
        layer = Layer(flare, c._unique_name('Lens Flare'), True, 1.0, 'screen')
        c.active += 1; c.layers.insert(c.active, layer)
        c.update(); self.refresh_layers()
        return layer

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

    def dlg_vibrance(self):
        if self._need_pil():
            AdjustDialog(self, 'Vibrance', [('v', 'Vibrance:', -100, 100, 0, 1.0)],
                         lambda vals: adj_vibrance(vals['v'])).exec()

    def dlg_channelmixer(self):
        if self._need_pil():
            ChannelMixerDialog(self).exec()

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

    def dlg_gradientmap(self):
        if self._need_pil():
            GradientMapDialog(self).exec()

    def dlg_shadow_highlight(self):
        if self._need_pil():
            AdjustDialog(self, 'Shadow / Highlight',
                         [('shadow', 'Lighten shadows:', 0, 100, 0, 1.0),
                          ('highlight', 'Recover highlights:', 0, 100, 0, 1.0),
                          ('radius', 'Radius:', 0, 200, 30, 1.0),
                          ('mid', 'Midtone contrast:', -100, 100, 0, 1.0)],
                         lambda v: adj_shadow_highlight(v['shadow'], v['highlight'],
                                                        v['radius'], v['mid'])).exec()

    def dlg_selective_color(self):
        if self._need_pil():
            SelectiveColorDialog(self).exec()

    def dlg_smooth_skin(self):
        """Open the Smooth Skin portrait-retouch studio (live preview on the canvas)."""
        if self._need_pil():
            SmoothSkinDialog(self).exec()

    def dlg_film_look(self):
        """Open the Film Look studio — one-click photographic presets (live preview)."""
        if self._need_pil():
            FilmLookDialog(self).exec()

    def dlg_art_style(self):
        """Open the Art Style studio — photo-to-art re-renderers (live preview)."""
        if self._need_pil():
            ArtStyleDialog(self).exec()

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

    def dlg_enlarge(self):
        """Image ▸ Enlarge — smart up-scale the whole document (PhotoZoom-style)."""
        if self._need_pil():
            EnlargeDialog(self).exec()

    def canvas_size(self):
        w, h = self.canvas.img.width(), self.canvas.img.height()
        nw, ok = QInputDialog.getInt(self, 'Canvas Size', 'Canvas width (px):', w, 1, 20000)
        if not ok: return
        nh, ok = QInputDialog.getInt(self, 'Canvas Size', 'Canvas height (px):', h, 1, 20000)
        if ok: self.canvas.set_canvas_size(nw, nh)

    def trim_photo(self):
        """Image ▸ Trim Transparent Border — auto-crop the transparent margin."""
        if not self._need_pil(): return
        pad, ok = QInputDialog.getInt(self, 'Trim Transparent Border',
                                      'Padding to keep around content (px):', 0, 0, 2000)
        if not ok: return
        res = self.canvas.trim_transparent(pad)
        if res is None:
            QMessageBox.information(self, APP,
                'There is no transparent border to trim — the image is fully opaque.')
        else:
            x, y, w, h = res
            self.status.showMessage(f'Trimmed to {w}×{h} px.', 4000)

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

    def add_overlay_dialog(self):
        self._library_picker_dialog(
            title='Add Overlay',
            libdir=os.path.expanduser('~/.local/share/justapps/overlays'),
            intro=('Drop a light leak, grunge, frame or bokeh overlay onto a NEW layer '
                   '(non-destructive). It is scaled to cover the canvas; set a blend mode '
                   'and opacity to taste, then refine with a layer mask.'),
            libname='overlay library',
            default_blend='screen', default_opacity=100,
            apply_fn=self.canvas.add_overlay_layer,
            done='Overlay added on a new layer — tweak its blend/opacity in the Layers panel.')

    def place_texture_dialog(self):
        self._library_picker_dialog(
            title='Place Texture',
            libdir=os.path.expanduser('~/.local/share/justapps/textures'),
            intro=('Place a texture as a NEW layer covering the whole canvas. It lands at '
                   'Normal / 100% so you can then blend it (Multiply, Overlay…) or mask it in.'),
            libname='texture library',
            default_blend='normal', default_opacity=100,
            apply_fn=self.canvas.place_texture_layer,
            done='Texture placed on a new layer — blend or mask it in via the Layers panel.')

    def add_frame_dialog(self):
        """Image ▸ Add Frame / Edge… — pick a decorative edge/frame (a transparent PNG
        whose centre is clear) from the deeply nested frame library and lay it over the
        photo on a NEW layer at Normal / 100%, so the image shows through the clear centre.
        Non-destructive; reposition/scale/opacity in the Layers panel afterwards."""
        self._library_picker_dialog(
            title='Add Frame / Edge',
            libdir=FRAME_LIBRARY_DIR,
            intro=('Lay a decorative edge or frame — torn, distressed, film-strip, darkroom, '
                   'vignette… — over your photo on a NEW layer (non-destructive). The frame '
                   'is cover-fitted at Normal / 100%, so its clear centre reveals the image '
                   'through it. Browse your own installed frame library by category below.'),
            libname='frame &amp; edge library',
            default_blend='normal', default_opacity=100,
            apply_fn=self.canvas.add_overlay_layer,
            done='Frame added on a new layer — reposition/scale/opacity in the Layers panel.',
            recursive=True)

    def _library_picker_dialog(self, title, libdir, intro, libname,
                               default_blend, default_opacity, apply_fn, done,
                               recursive=False):
        """Shared picker for Add Overlay / Place Texture / Add Frame: Browse-for-image OR a
        categorised swatch grid reading the live library at `libdir`, plus a blend-mode and
        opacity control. Calls apply_fn(path, blend, opacity) on OK.

        With recursive=True the library is scanned for LEAF directories that directly contain
        images (via scan_frame_library) — categories are labelled by their ' / '-joined path
        relative to the root — which is how the deeply nested frame/edge library is browsed.
        Swatches decode small/fast via library_thumbnail (QImageReader scaled size) so the
        ~1.3 MB frame PNGs are never loaded full-size for the grid."""
        from PySide6.QtWidgets import (QScrollArea, QGridLayout, QToolButton, QWidget)
        chosen = {'path': None}
        dlg = QDialog(self); dlg.setWindowTitle(title); dlg.resize(580, 640)
        v = QVBoxLayout(dlg)
        lbl = QLabel(intro); lbl.setWordWrap(True); v.addWidget(lbl)
        sel_lbl = QLabel('Nothing chosen yet.'); sel_lbl.setStyleSheet('color:#5c6b73')
        row = QHBoxLayout(); bbrowse = QPushButton('Browse for an image…')
        row.addWidget(bbrowse); row.addWidget(sel_lbl, 1); v.addLayout(row)

        def choose(path):
            chosen['path'] = path; sel_lbl.setText('Chosen: ' + os.path.basename(path))
            okbtn.setEnabled(True)

        def browse():
            p, _ = QFileDialog.getOpenFileName(dlg, 'Choose an image', _just_dir('pics'),
                                               'Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*)')
            if p: choose(p)
        bbrowse.clicked.connect(browse)

        if recursive:
            # (label, dirpath) leaf categories from the deeply nested library
            scanned = scan_frame_library(libdir)
            cats = [c[0] for c in scanned]
            dir_for = dict(scanned)
        else:
            cats = sorted([d for d in os.listdir(libdir) if os.path.isdir(os.path.join(libdir, d))]) \
                if os.path.isdir(libdir) else []
            dir_for = {c: os.path.join(libdir, c) for c in cats}
        if cats:
            v.addWidget(QLabel('<b>Your %s</b> — click a swatch to use it:' % libname))
            catcombo = QComboBox(); catcombo.addItems(cats); v.addWidget(catcombo)
            area = QScrollArea(); area.setWidgetResizable(True); area.setMinimumHeight(300); v.addWidget(area, 1)
            holder = QWidget(); hv = QGridLayout(holder); area.setWidget(holder)

            def load_cat(cat):
                while hv.count():
                    it = hv.takeAt(0); w = it.widget()
                    if w: w.deleteLater()
                d = dir_for.get(cat, os.path.join(libdir, cat))
                try:
                    files = sorted([f for f in os.listdir(d)
                                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])[:120]
                except OSError:
                    files = []
                for i, fn in enumerate(files):
                    fp = os.path.join(d, fn)
                    tb = QToolButton()
                    # small/fast scaled decode — frame PNGs are ~1.3 MB, never full-size here
                    pm = library_thumbnail(fp, 96)
                    if not pm.isNull():
                        pm = pm.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    tb.setIcon(QIcon(pm)); tb.setIconSize(QSize(90, 90)); tb.setToolTip(fn)
                    tb.setCursor(Qt.PointingHandCursor); tb.setAutoRaise(True)
                    tb.clicked.connect(lambda _=0, fp=fp: choose(fp))
                    hv.addWidget(tb, i // 4, i % 4)
            catcombo.currentTextChanged.connect(load_cat); load_cat(cats[0])
        else:
            note = QLabel('<span style="color:gray">No %s found at %s — use Browse for an '
                          'image instead.</span>' % (libname, libdir))
            note.setWordWrap(True); v.addWidget(note)

        orow = QHBoxLayout()
        orow.addWidget(QLabel('Blend:'))
        blend_cb = QComboBox(); blend_cb.addItems(BLEND_NAMES)
        blend_cb.setCurrentIndex(BLEND_NAMES.index(default_blend)); orow.addWidget(blend_cb)
        orow.addSpacing(16); orow.addWidget(QLabel('Opacity:'))
        op_sl = QSlider(Qt.Horizontal); op_sl.setRange(0, 100); op_sl.setValue(default_opacity)
        orow.addWidget(op_sl, 1)
        op_lbl = QLabel('%d%%' % default_opacity); op_lbl.setMinimumWidth(42); orow.addWidget(op_lbl)
        op_sl.valueChanged.connect(lambda val: op_lbl.setText('%d%%' % val))
        v.addLayout(orow)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        okbtn = bb.button(QDialogButtonBox.Ok); okbtn.setText('Add to new layer'); okbtn.setEnabled(False)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted or not chosen['path']:
            return
        layer = apply_fn(chosen['path'], blend_cb.currentText(), op_sl.value() / 100.0)
        if layer is None:
            QMessageBox.warning(self, APP, "Couldn't load that image."); return
        self.status.showMessage(done, 4000)

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open image', _just_dir('pics'),
                                              'Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)')
        if not path: return
        self.open_path(path)

    def open_path(self, path):
        """Core (testable) open: load `path` as a new document. Returns True on success.
        Reused by File ▸ Open… and File ▸ Open from Library…."""
        if not path: return False
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, APP, "Couldn't open that image."); return False
        self.canvas.load(img); self.path = path; self.update_title(); _justapps_recent('paint', path)
        return True

    def open_from_library(self):
        """File ▸ Open from Library… — pick a photo from the local stock library (or Browse)
        and open it as a new document through the normal open path."""
        path = library_picker(self, 'Open from Library')
        if path: self.open_path(path)

    def merge_panorama(self):
        """File ▸ Merge Photos to Panorama… — stitch several overlapping photos into one
        wide panorama (in the spirit of Serif PanoramaPlus) and open it as a new document.
        Uses OpenCV's automatic stitcher (feature match → warp → blend)."""
        if not HAS_CV2:
            QMessageBox.warning(self, APP, "Photo Merge needs OpenCV, which isn't installed.\n\n"
                                "Install it and reopen PAINTcanvas:\n"
                                "    pip install opencv-python-headless\n"
                                "    (or: sudo pacman -S python-opencv)")
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Choose 2 or more overlapping photos to stitch', _just_dir('pics'),
            'Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff);;All files (*)')
        if not paths:
            return
        if len(paths) < 2:
            QMessageBox.information(self, APP, 'Pick at least two overlapping photos to stitch.')
            return
        import numpy as _np
        self.statusBar().showMessage(f'Stitching {len(paths)} photos…'); QApplication.processEvents()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            imgs = []
            for p in paths:
                try:    # np.fromfile+imdecode handles non-ASCII paths cv2.imread chokes on
                    arr = _cv2.imdecode(_np.fromfile(p, dtype=_np.uint8), _cv2.IMREAD_COLOR)
                except Exception:
                    arr = _cv2.imread(p)
                if arr is not None:
                    imgs.append(arr)
            if len(imgs) < 2:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, APP, 'Could not read enough of those photos to stitch.')
                return
            stitcher = _cv2.Stitcher_create(_cv2.Stitcher_PANORAMA)
            status, pano = stitcher.stitch(imgs)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, APP, f'Stitching failed:\n{e}')
            return
        QApplication.restoreOverrideCursor()
        if status != 0 or pano is None:
            QMessageBox.warning(self, APP,
                                'Those photos could not be stitched automatically.\n\n'
                                'Panoramas work best when consecutive shots overlap by about a third, '
                                'are taken from the same spot, and keep the same exposure.')
            self.statusBar().showMessage('Stitch cancelled.', 4000)
            return
        rgb = _cv2.cvtColor(pano, _cv2.COLOR_BGR2RGB)
        full_h, full_w = rgb.shape[:2]
        # Auto Min Crop (PanoramaPlus): offer to trim the ragged black border the
        # warp leaves to the largest gap-free rectangle, instead of making the user
        # do it by hand. Content = any channel above 0 (the stitcher fills gaps pure black).
        cropped = False
        rect = None
        if HAS_PIL:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.statusBar().showMessage('Finding the best crop…'); QApplication.processEvents()
            try:
                rect = _largest_content_rect(rgb.max(axis=2) > 0)
            finally:
                QApplication.restoreOverrideCursor()
        if rect and (rect[2] - rect[0] < full_w or rect[3] - rect[1] < full_h):
            ans = QMessageBox.question(
                self, APP,
                'Square off the ragged edges automatically?\n\n'
                'Stitching leaves uneven black borders. Auto Min Crop trims the picture to '
                'the largest rectangle with no gaps. Choose No to keep the full stitched '
                'image and crop it yourself.',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if ans == QMessageBox.Yes:
                x0, y0, x1, y1 = rect
                rgb = _np.ascontiguousarray(rgb[y0:y1, x0:x1])
                cropped = True
        h, w = rgb.shape[:2]
        qi = QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format_RGB888).convertToFormat(QImage.Format_ARGB32).copy()
        self.canvas.load(qi); self.path = None; self.update_title()
        msg = (f'Stitched {len(imgs)} photos → {w}×{h}, auto-cropped. Adjust and Save.' if cropped
               else f'Stitched {len(imgs)} photos → {w}×{h}. Crop the ragged edges, then Save.')
        self.statusBar().showMessage(msg, 8000)

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

    def export(self):
        """Export the flattened picture in a chosen format with quality/transparency
        options — PNG / JPEG / WEBP / GIF / BMP."""
        ExportDialog(self).exec()

    def reduce_filesize(self):
        """Shrink the picture's file size for web/email — modern codec (AVIF/WebP),
        a target size or quality, optional downscale, metadata stripping."""
        OptimiseDialog(self).exec()

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
