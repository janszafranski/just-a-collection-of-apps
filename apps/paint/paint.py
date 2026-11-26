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
                                   QDockWidget, QListWidget, QListWidgetItem)
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
VERSION = "1.10-00"
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


def _merge_a(src, rgb):
    """Put an RGB result back together with the source's alpha channel."""
    return Image.merge('RGBA', rgb.convert('RGB').split() + (src.split()[3],))


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
BLEND_NAMES = ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'add', 'difference']


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
        # editing a mask changes layer.mask (not .img), so snapshot the whole stack
        self.snapshot_full() if (self.edit_mask and self.has_mask()) else self.snapshot()
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
        if self.tool == 'smartmask':
            if (e.buttons() & (Qt.LeftButton | Qt.RightButton)) and self.last is not None:
                self._sm_paint(self.last, pos, getattr(self, '_sm_active', self.sm_mode))
                self.last = pos
            return
        if not (e.buttons() & Qt.LeftButton): return
        if self.tool in ('brush', 'eraser', 'dodge', 'burn', 'clone') and self.last is not None:
            self._stroke(self.last, pos); self.last = pos; self.update()
        elif self.tool in ('line', 'rect', 'ellipse', 'gradient') and self.start is not None:
            self.preview = (self.tool, self.start, pos); self.update()
        elif self.tool in ('mrect', 'mellipse') and self.start is not None:
            self.sel_drag = (self.start, pos); self.update()

    def mouseReleaseEvent(self, e):
        if self.tool == 'smartmask':
            self.last = None; return
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


class Main(QMainWindow):
    TOOLS = [('brush', 'Brush', '🖌'), ('eraser', 'Eraser', '◻'), ('line', 'Line', '╱'),
             ('rect', 'Rectangle', '▭'), ('ellipse', 'Ellipse', '◯'), ('fill', 'Fill', '🪣'),
             ('gradient', 'Gradient fill (drag)', '▨'), ('picker', 'Pick colour', '🎯'),
             ('text', 'Text', 'A'), ('clone', 'Clone — Ctrl-click to set source', '❏'),
             ('redeye', 'Red-eye removal', '◉'), ('dodge', 'Dodge — lighten', '☀'),
             ('burn', 'Burn — darken', '◐'),
             ('mrect', 'Select — rectangle', '⬚'), ('mellipse', 'Select — ellipse', '◌'),
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
        f.addAction(self.act('&Save', self.save, QKeySequence.Save))
        f.addAction(self.act('Save &As…', self.save_as, QKeySequence.SaveAs))
        f.addAction(self.act('&Export…', self.export, 'Ctrl+Shift+E'))
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
        img.addAction(self.act('Add &Overlay…', self.add_overlay_dialog))
        img.addAction(self.act('&Place Texture…', self.place_texture_dialog))
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
        self.canvas.tool = t
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

    def dlg_smooth_skin(self):
        """Open the Smooth Skin portrait-retouch studio (live preview on the canvas)."""
        if self._need_pil():
            SmoothSkinDialog(self).exec()

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

    def _library_picker_dialog(self, title, libdir, intro, libname,
                               default_blend, default_opacity, apply_fn, done):
        """Shared picker for Add Overlay / Place Texture: Browse-for-image OR a categorised
        swatch grid reading the live library at `libdir`, plus a blend-mode and opacity
        control. Calls apply_fn(path, blend, opacity) on OK."""
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

        cats = sorted([d for d in os.listdir(libdir) if os.path.isdir(os.path.join(libdir, d))]) \
            if os.path.isdir(libdir) else []
        if cats:
            v.addWidget(QLabel('<b>Your %s</b> — click a swatch to use it:' % libname))
            catcombo = QComboBox(); catcombo.addItems(cats); v.addWidget(catcombo)
            area = QScrollArea(); area.setWidgetResizable(True); area.setMinimumHeight(300); v.addWidget(area, 1)
            holder = QWidget(); hv = QGridLayout(holder); area.setWidget(holder)

            def load_cat(cat):
                while hv.count():
                    it = hv.takeAt(0); w = it.widget()
                    if w: w.deleteLater()
                d = os.path.join(libdir, cat)
                try:
                    files = sorted([f for f in os.listdir(d)
                                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])[:120]
                except OSError:
                    files = []
                for i, fn in enumerate(files):
                    fp = os.path.join(d, fn)
                    tb = QToolButton(); pm = QPixmap(fp)
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
