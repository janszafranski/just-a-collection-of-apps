#!/usr/bin/env python3
"""Build PAINTcanvas's illustrated docs — a book-length User Guide and a Quick Start
— entirely from the running app.

    python3 tools/build-paintmanual.py            # both docs (HTML + PDF)
    python3 tools/build-paintmanual.py --quick    # just the Quick Start
    python3 tools/build-paintmanual.py --no-pdf   # HTML only (fast; skip printing)

Every picture is produced by the program itself: the workspace, the vertical tool
palette and the Layers panel are grabbed from a live (offscreen) window; every
dialog is captured by driving the real menu command; and the worked demo images
are painted by driving the real Canvas and grabbing its composited result. Images
embed as data URIs, so each HTML file is self-contained and installs with no extra
assets.

Modelled on the structure and depth of Serif's PhotoPlus guides — step-by-step
procedures, worked projects and a full reference section — but describing *this*
program's real menus and features throughout. PAINTcanvas is a raster image editor
(QImage + layers), so in place of a page catalogue we show painted demonstrations.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "paint" / "paint.py"
OUT = ROOT / "apps" / "paint"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-paintmanual"]

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QToolBar   # noqa: E402
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QBrush, QFont, QLinearGradient, QPainterPath  # noqa: E402
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF   # noqa: E402

app = QApplication.instance() or QApplication([])

# Silence modal message boxes and input dialogs so a driver call never blocks.
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))

# Capture every dialog the app opens: when a command calls dlg.exec(), show the
# dialog offscreen, grab it, then return "rejected" so nothing is actually applied.
DGRABS: dict = {}


def _cap_exec(self, *a, **k):
    try:
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        if self.size().width() < 80 or self.size().height() < 60:
            self.adjustSize()
        self.show()
        for _ in range(14):
            app.processEvents()
        key = self.windowTitle() or ("dialog%d" % len(DGRABS))
        DGRABS[key] = _grab(self)
        self.hide()
    except Exception:
        pass
    return 0


QDialog.exec = _cap_exec


def _load():
    spec = importlib.util.spec_from_file_location("paint", APP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PC = _load()

try:
    from PIL import Image
except Exception:
    Image = None

_TMP = ROOT / "tools" / "_tmp_grab.png"


def _grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGB").copy()


def _pil(qt_obj) -> "Image.Image":
    """PIL image from a QPixmap or QImage (keeps alpha)."""
    qt_obj.save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGBA").copy()


def _win():
    w = PC.Main()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1180, 820)
    w.show()
    for _ in range(16):
        app.processEvents()
    return w


# ----------------------------------------------------------------- demo painting
# All demo images are painted by hand onto a real Canvas's QImage with QPainter —
# the same drawing primitives the app's own tools use — then grabbed as the
# composited result. No text is drawn into a canvas (offscreen Qt can abort on
# some glyph work); captions carry the words instead.

def _blank(w, h, bg="#ffffff"):
    im = QImage(w, h, QImage.Format_ARGB32)
    im.fill(QColor(bg) if bg else Qt.transparent)
    return im


def _scene(w=560, h=360):
    """A small colourful scene used as the running 'photo' in demos."""
    im = _blank(w, h, "#eaf2f6")
    p = QPainter(im); p.setRenderHint(QPainter.Antialiasing)
    # sky gradient
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor("#9ad0ec")); g.setColorAt(1, QColor("#dff1fb"))
    p.fillRect(QRectF(0, 0, w, h * 0.62), QBrush(g))
    # ground
    p.fillRect(QRectF(0, h * 0.62, w, h * 0.38), QColor("#7bb662"))
    # sun
    p.setBrush(QColor("#ffd34e")); p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(w * 0.80, h * 0.22), 46, 46)
    # hills
    p.setBrush(QColor("#5a9e52"))
    path = QPainterPath(); path.moveTo(0, h * 0.62)
    path.cubicTo(w * 0.25, h * 0.40, w * 0.40, h * 0.66, w * 0.55, h * 0.56)
    path.cubicTo(w * 0.72, h * 0.46, w * 0.85, h * 0.64, w, h * 0.58)
    path.lineTo(w, h * 0.62); path.closeSubpath(); p.drawPath(path)
    # a little house
    p.setBrush(QColor("#f1e3cf")); p.setPen(QPen(QColor("#8a6b4a"), 2))
    p.drawRect(QRectF(w * 0.14, h * 0.50, 96, 74))
    p.setBrush(QColor("#c0533b"))
    roof = QPainterPath(); roof.moveTo(w * 0.14 - 8, h * 0.50)
    roof.lineTo(w * 0.14 + 48, h * 0.50 - 40); roof.lineTo(w * 0.14 + 104, h * 0.50)
    roof.closeSubpath(); p.drawPath(roof)
    p.setBrush(QColor("#7a5a3a")); p.drawRect(QRectF(w * 0.14 + 38, h * 0.50 + 40, 20, 34))
    p.end()
    return im


def _shapes_demo(w=560, h=300):
    im = _blank(w, h, "#ffffff")
    p = QPainter(im); p.setRenderHint(QPainter.Antialiasing)
    # brush squiggle
    pen = QPen(QColor("#2a7df0"), 10); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.NoBrush)
    path = QPainterPath(); path.moveTo(30, 70)
    for i, y in enumerate((40, 100, 40, 100, 40)):
        path.cubicTo(30 + i * 24 + 12, y, 30 + i * 24 + 24, y, 30 + (i + 1) * 24, 70)
    p.drawPath(path)
    # straight line
    pen2 = QPen(QColor("#e8556b"), 6); pen2.setCapStyle(Qt.RoundCap); p.setPen(pen2)
    p.drawLine(QPointF(180, 30), QPointF(300, 120))
    # rectangle outline
    pen3 = QPen(QColor("#1f9d6b"), 5); p.setPen(pen3); p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(330, 30, 90, 90))
    # ellipse outline
    pen4 = QPen(QColor("#9b6bd8"), 5); p.setPen(pen4)
    p.drawEllipse(QRectF(440, 30, 100, 90))
    # filled (bucket) blobs
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffd34e")); p.drawRect(QRectF(30, 160, 110, 110))
    p.setBrush(QColor("#49c5b6")); p.drawEllipse(QRectF(170, 160, 110, 110))
    # gradient swatch (what the Gradient tool draws: a two-colour linear blend)
    g = QLinearGradient(310, 160, 540, 160)
    g.setColorAt(0, QColor("#e8556b")); g.setColorAt(1, QColor("#2a7df0"))
    p.fillRect(QRectF(310, 160, 230, 110), QBrush(g))
    p.end()
    return im


def _fill_demo(w=560, h=190):
    """Outline vs. fill vs. both for a rectangle and an ellipse, plus a two-colour
    gradient — the new shape and gradient options."""
    im = _blank(w, h, "#ffffff")
    p = QPainter(im); p.setRenderHint(QPainter.Antialiasing)
    # rectangle: outline / fill / both
    stroke = QColor("#1f9d6b"); fillc = QColor("#9be3c8")
    # outline
    p.setBrush(Qt.NoBrush); pen = QPen(stroke, 5); p.setPen(pen)
    p.drawRect(QRectF(24, 30, 92, 92))
    # fill only
    p.setPen(Qt.NoPen); p.setBrush(QColor("#9be3c8")); p.drawRect(QRectF(150, 30, 92, 92))
    # both
    p.setBrush(QColor("#9be3c8")); p.setPen(QPen(stroke, 5)); p.drawRect(QRectF(276, 30, 92, 92))
    # a filled ellipse
    p.setBrush(QColor("#c9b6ef")); p.setPen(QPen(QColor("#7b53c9"), 5)); p.drawEllipse(QRectF(410, 30, 120, 92))
    # two-colour gradient band along the foot
    g = QLinearGradient(24, 150, 536, 150)
    g.setColorAt(0, QColor("#e8556b")); g.setColorAt(1, QColor("#2a7df0"))
    p.fillRect(QRectF(24, 142, 512, 34), QBrush(g))
    p.end()
    return im


def _apply_pil(qimg, func):
    """Run a pil->pil engine function over a whole QImage and return a QImage."""
    return PC.pil2q(func(PC.q2pil(qimg)))


# ----------------------------------------------------------------- capture
def capture(full=True):
    """Return {key: PIL image} for every picture the guide needs."""
    IM = {}

    # --- painted demo scenes (crisp, composited) --------------------------
    scene = _scene()
    IM["scene"] = _pil(scene).convert("RGB")
    IM["shapes"] = _pil(_shapes_demo()).convert("RGB")
    IM["fills"] = _pil(_fill_demo()).convert("RGB")

    # layer-mask demo: an orange circle layer over a scene, masked so a diagonal band
    # is hidden — drives the real composited() path to prove the mask hides pixels.
    try:
        import types as _t
        mw, mh = 420, 280
        bottom = _scene(mw, mh)
        top = _blank(mw, mh, None)
        pp = QPainter(top); pp.setRenderHint(QPainter.Antialiasing); pp.setPen(Qt.NoPen)
        pp.setBrush(QColor("#ff8a3d")); pp.drawEllipse(QRectF(90, 50, 240, 180)); pp.end()
        cv = PC.Canvas.__new__(PC.Canvas)
        cv.layers = [PC.Layer(bottom, "Background"),
                     PC.Layer(top, "Orange")]
        cv.active = 1; cv.sel = None; cv.edit_mask = False
        cv.update = _t.MethodType(lambda self: None, cv)
        cv.win = None
        # build a mask: white everywhere, a black wedge cut out of the orange
        m = PC.new_mask(mw, mh, True)
        qp = QPainter(m); qp.setRenderHint(QPainter.Antialiasing); qp.setBrush(QColor("#000000")); qp.setPen(Qt.NoPen)
        path = QPainterPath(); path.moveTo(0, 0); path.lineTo(mw, 0); path.lineTo(0, mh); path.closeSubpath()
        qp.drawPath(path); qp.end()
        cv.layers[1].mask = m
        IM["mask_demo"] = _pil(cv.composited()).convert("RGB")
        # the mask thumbnail itself (greyscale swatch)
        IM["mask_swatch"] = _pil(m).convert("RGB")
    except Exception as e:
        print("mask demo failed:", e)

    # before/after adjustment strip: original vs. a warm, higher-contrast version
    if PC.HAS_PIL:
        try:
            warm = _apply_pil(scene, lambda p: PC.adj_contrast(1.35)(PC.adj_temperature(55)(p)))
            IM["adjust_after"] = _pil(warm).convert("RGB")
            grey = _apply_pil(scene, PC.adj_grayscale)
            IM["adjust_grey"] = _pil(grey).convert("RGB")
            sep = _apply_pil(scene, PC.adj_sepia)
            IM["adjust_sepia"] = _pil(sep).convert("RGB")
            inv = _apply_pil(scene, PC.adj_invert)
            IM["adjust_invert"] = _pil(inv).convert("RGB")
            blur = _apply_pil(scene, PC.flt_gaussian(3.0))
            IM["filter_blur"] = _pil(blur).convert("RGB")
            edges = _apply_pil(scene, PC.flt_edges)
            IM["filter_edges"] = _pil(edges).convert("RGB")
            emb = _apply_pil(scene, PC.flt_emboss)
            IM["filter_emboss"] = _pil(emb).convert("RGB")
            # Curves: a classic S-curve (lift mids, deepen shadows) via the LUT engine
            scurve = PC.curve_lut([(0, 0), (64, 40), (128, 140), (192, 220), (255, 255)])
            IM["curves_after"] = _pil(_apply_pil(scene, PC.adj_curves(scurve, "rgb"))).convert("RGB")
        except Exception as e:
            print("adjust/filter demo failed:", e)

    # magic-wand selection demo: flood a colour region into a mask, then show the
    # original beside a version with only that region recoloured (adjustment clipped
    # to the wand's mask) — proof the selection drives the edit.
    try:
        ww, wh = 420, 300
        base = _blank(ww, wh, "#eaf2f6")
        p = QPainter(base); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        p.fillRect(QRectF(0, wh * 0.6, ww, wh * 0.4), QColor("#7bb662"))   # green ground
        p.setBrush(QColor("#e8556b")); p.drawEllipse(QRectF(150, 90, 120, 120))  # red ball
        p.end()
        IM["wand_before"] = _pil(base).convert("RGB")
        import types as _t
        cv = PC.Canvas.__new__(PC.Canvas)
        cv.layers = [PC.Layer(base.convertToFormat(QImage.Format_ARGB32), "bg")]
        cv.active = 0; cv.sel = None
        cv.update = _t.MethodType(lambda self: None, cv)   # throwaway Canvas has no QWidget
        cv.wand_select(QPoint(210, 150), 40, True)         # click the red ball
        img2 = cv._apply_to(cv.img, PC.adj_hue(120))       # recolour just the ball
        IM["wand_after"] = _pil(img2).convert("RGB")
    except Exception as e:
        print("wand demo failed:", e)

    # cutout demo: paint a subject on a flat background, then flood the bg to
    # transparency the same way the Cutout tool does — show the result on checker.
    try:
        cw, ch = 420, 300
        base = _blank(cw, ch, "#4aa3d6")                 # solid blue backdrop
        p = QPainter(base); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e86a3b")); p.drawEllipse(QRectF(130, 70, 160, 160))   # subject
        p.setBrush(QColor("#2b3238")); p.drawEllipse(QRectF(170, 120, 24, 24))
        p.setBrush(QColor("#2b3238")); p.drawEllipse(QRectF(226, 120, 24, 24))
        p.end()
        IM["cutout_before"] = _pil(base).convert("RGB")
        # flood-remove the blue background via a throwaway Canvas
        cv = PC.Canvas.__new__(PC.Canvas)
        cv.layers = [PC.Layer(base.convertToFormat(QImage.Format_ARGB32), "bg")]
        cv.active = 0; cv.sel = None
        seeds = [(0, 0), (cw - 1, 0), (0, ch - 1), (cw - 1, ch - 1)]
        px = base.pixel(0, 0)
        cv._flood_transparent(seeds, ((px >> 16) & 0xff, (px >> 8) & 0xff, px & 0xff), 50)
        IM["cutout_after"] = _pil(cv.layers[0].img)       # keep alpha → checker in CSS
    except Exception as e:
        print("cutout demo failed:", e)

    # Smart Mask demo: scribble KEEP over a subject and REMOVE over a textured
    # background, then run smart_mask() — show the scribbles, then the cut-out on
    # checker. Everything is self-made synthetic imagery.
    try:
        sw, sh = 420, 300
        base = _blank(sw, sh, "#dfe8ee")
        p = QPainter(base); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        # a gently textured background (soft stripes) so the result isn't trivial
        for i in range(0, sw, 34):
            p.fillRect(QRectF(i, 0, 17, sh), QColor("#c7d6e0"))
        p.setBrush(QColor("#e07a3b")); p.drawEllipse(QRectF(120, 70, 170, 170))   # subject
        p.setBrush(QColor("#2b3238")); p.drawEllipse(QRectF(165, 120, 22, 22))
        p.setBrush(QColor("#2b3238")); p.drawEllipse(QRectF(225, 120, 22, 22))
        p.end()
        import numpy as _np
        rgb = _np.asarray(PC.q2pil(base).convert("RGB"))
        keep = _np.zeros((sh, sw), bool); remove = _np.zeros((sh, sw), bool)
        keep[140:180, 180:230] = True                  # scribble on the subject
        remove[20:50, 10:40] = True                    # scribble on the background
        remove[250:285, 370:405] = True
        # "before" with the scribbles drawn translucently (green keep, red remove)
        ov = _np.zeros((sh, sw, 4), _np.uint8)
        ov[keep] = (60, 220, 90, 150); ov[remove] = (235, 70, 70, 150)
        before = PC.q2pil(base).convert("RGBA")
        before.alpha_composite(Image.fromarray(ov, "RGBA"))
        IM["smartmask_before"] = before.convert("RGB")
        # run the engine (uses cv2 grabCut if available, else NumPy fallback)
        mask = PC.smart_mask(rgb, keep, remove, feather=2)
        rgba = _np.dstack([rgb, mask]).astype("uint8")
        IM["smartmask_after"] = Image.fromarray(rgba, "RGBA")     # alpha → checker in CSS
        IM["smartmask_engine"] = "OpenCV grabCut" if PC.HAS_CV2 else "NumPy colour model"
    except Exception as e:
        print("smart mask demo failed:", e)

    # Smooth Skin demo: a self-made face-ish patch — a skin-tone oval with heavy
    # noise (uneven, blotchy skin) plus sharp non-skin features (eyes, lips). Show the
    # auto-detected skin mask and the before/after of smooth_skin(). All synthetic.
    try:
        import numpy as _np
        kw, kh = 360, 300
        rng = _np.random.default_rng(11)
        canvasrgb = _np.full((kh, kw, 3), (223, 225, 230), _np.float32)  # pale backdrop
        yy, xx = _np.ogrid[0:kh, 0:kw]
        face = ((xx - kw / 2) / 120.0) ** 2 + ((yy - kh / 2) / 135.0) ** 2 <= 1.0
        # blotchy skin tone + strong noise so the smoothing has something to do
        skin = _np.array([226, 182, 162], _np.float32)
        noise = rng.normal(0, 26, (kh, kw, 3))
        blotch = (18 * _np.sin(xx / 22.0) * _np.cos(yy / 26.0))[..., None]
        canvasrgb[face] = _np.clip(skin + noise + blotch, 0, 255)[face]
        img = canvasrgb.astype(_np.uint8).copy()
        # sharp features that must stay crisp: two dark eyes and a red mouth
        def disc(cx, cy, r, col):
            d = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r
            img[d] = col
        disc(kw * 0.40, kh * 0.44, 15, (40, 42, 50))
        disc(kw * 0.60, kh * 0.44, 15, (40, 42, 50))
        mouth = (((xx - kw / 2) / 48.0) ** 2 + ((yy - kh * 0.66) / 14.0) ** 2) <= 1.0
        img[mouth] = (176, 70, 78)
        IM["smooth_before"] = Image.fromarray(img, "RGB")
        mask = PC.skin_mask(img)
        IM["smooth_mask"] = Image.fromarray(mask, "L").convert("RGB")
        after = PC.smooth_skin(img, amount=0.75, radius=9, detail=0.3, skin_only=True)
        IM["smooth_after"] = Image.fromarray(after, "RGB")
        IM["smooth_engine"] = ("OpenCV bilateral (edge-preserving)" if PC.HAS_CV2
                               else "NumPy median smoothing")
    except Exception as e:
        print("smooth skin demo failed:", e)

    # effects demo: a shape on transparent bg with a drop shadow composited in.
    try:
        ew, eh = 420, 260
        tr = _blank(ew, eh, None)                          # transparent
        p = QPainter(tr); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e8556b")); p.drawEllipse(QRectF(120, 70, 150, 120))
        p.end()
        cv = PC.Canvas.__new__(PC.Canvas)
        cv.layers = [PC.Layer(tr, "fx")]; cv.active = 0; cv.sel = None
        # replicate apply_fx without the undo/win plumbing
        import types
        cv.snapshot = types.MethodType(lambda self: None, cv)
        cv._fit = types.MethodType(lambda self: None, cv)
        cv.apply_fx("#000000", 16, 10, 12, 60)
        shadow = QImage(ew, eh, QImage.Format_ARGB32); shadow.fill(QColor("#ffffff"))
        q = QPainter(shadow); q.drawImage(0, 0, cv.layers[0].img); q.end()
        IM["effects"] = _pil(shadow).convert("RGB")
    except Exception as e:
        print("effects demo failed:", e)

    # lens-flare demo: a self-made dusk scene, before and after a warm 'Sunny' flare
    # composited Screen onto its own layer (exactly what the dialog's OK does).
    try:
        lfw, lfh = 480, 300
        scn = _blank(lfw, lfh, None)
        p = QPainter(scn); p.setPen(Qt.NoPen)
        sky = QLinearGradient(0, 0, 0, lfh)
        sky.setColorAt(0.0, QColor("#2a3b6b")); sky.setColorAt(0.55, QColor("#8a5a7a"))
        sky.setColorAt(1.0, QColor("#d98a52"))
        p.fillRect(QRectF(0, 0, lfw, lfh), QBrush(sky))
        p.setBrush(QColor("#1b2030")); p.drawRect(QRectF(0, lfh * 0.72, lfw, lfh * 0.28))  # dark foreground
        p.end()
        IM["flare_before"] = _pil(scn).convert("RGB")
        lx, ly = int(lfw * 0.68), int(lfh * 0.28)
        pr = dict(PC.LENS_FLARE_DEFAULTS); pr.update(PC.LENS_FLARE_PRESETS["Sunny"])
        flare = PC.render_lens_flare(lfw, lfh, lx, ly, pr)
        cv = PC.Canvas.__new__(PC.Canvas)
        cv.layers = [PC.Layer(scn.copy(), "Background"),
                     PC.Layer(flare, "Lens Flare", True, 1.0, "screen")]
        cv.active = 1
        IM["flare_after"] = _pil(cv.composited()).convert("RGB")
    except Exception as e:
        print("lens flare demo failed:", e)

    # layers demo: two stacked layers (scene + a translucent coloured wash).
    try:
        lw, lh = 420, 280
        cv = PC.Canvas.__new__(PC.Canvas)
        bottom = _scene(lw, lh)
        top = _blank(lw, lh, None)
        p = QPainter(top); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ff8a3d")); p.drawEllipse(QRectF(40, 40, 150, 150))
        p.end()
        cv.layers = [PC.Layer(bottom, "Background"),
                     PC.Layer(top, "Glow", True, 0.55, "screen")]
        cv.active = 1; cv.sel = None
        IM["layers_demo"] = _pil(cv.composited()).convert("RGB")
    except Exception as e:
        print("layers demo failed:", e)

    # overlays & textures demo: build our OWN demo overlay (a diagonal light leak) and
    # texture (a woven weave), never the user's licensed library, and show before/after
    # of dropping each onto a scene via the real add_overlay_layer / place_texture_layer.
    try:
        import types as _t, tempfile as _tf
        ow, oh = 460, 300
        base = _scene(ow, oh)
        IM["ovtx_before"] = _pil(base).convert("RGB")

        # a light-leak overlay PNG: a warm diagonal gradient wash with soft bright streaks
        leak = QImage(ow, oh, QImage.Format_ARGB32); leak.fill(Qt.transparent)
        lp = QPainter(leak)
        g = QLinearGradient(0, oh, ow, 0)
        g.setColorAt(0.0, QColor(255, 90, 40, 0)); g.setColorAt(0.55, QColor(255, 150, 60, 150))
        g.setColorAt(0.8, QColor(255, 225, 150, 220)); g.setColorAt(1.0, QColor(255, 255, 240, 120))
        lp.fillRect(0, 0, ow, oh, QBrush(g))
        lp.setPen(Qt.NoPen); lp.setBrush(QColor(255, 255, 220, 120))
        lp.drawEllipse(QRectF(ow * 0.62, oh * 0.05, 220, 220)); lp.end()
        tmpd = _tf.mkdtemp()
        leakp = os.path.join(tmpd, "demo_leak.png"); leak.save(leakp)

        # a texture JPG: a simple woven over/under weave in two warm tones
        tex = QImage(360, 240, QImage.Format_RGB32); tex.fill(QColor("#c9a24b"))
        txp = QPainter(tex); txp.setPen(Qt.NoPen)
        cell = 24
        for yy in range(0, 240, cell):
            for xx in range(0, 360, cell):
                over = ((xx // cell) + (yy // cell)) % 2 == 0
                txp.setBrush(QColor("#a06b2e") if over else QColor("#e3c178"))
                txp.drawRect(xx + 2, yy + 2, cell - 4, cell - 4)
        txp.end()
        texp = os.path.join(tmpd, "demo_weave.jpg"); tex.save(texp, "JPEG", 90)

        def _throwaway_canvas(bg):
            c = PC.Canvas.__new__(PC.Canvas)
            c.layers = [PC.Layer(bg.convertToFormat(QImage.Format_ARGB32), "Background")]
            c.active = 0; c.sel = None; c.undo = []; c.redo = []
            c.update = _t.MethodType(lambda self: None, c)
            c.snapshot_full = _t.MethodType(lambda self: None, c)
            c.win = _t.SimpleNamespace(refresh_layers=lambda: None, update_title=lambda: None)
            c.doc_w = _t.MethodType(lambda self: self.layers[0].img.width(), c)
            c.doc_h = _t.MethodType(lambda self: self.layers[0].img.height(), c)
            return c

        cov = _throwaway_canvas(base)
        cov.add_overlay_layer(leakp, "screen", 0.85)
        IM["overlay_after"] = _pil(cov.composited()).convert("RGB")

        ctx = _throwaway_canvas(base)
        ctx.place_texture_layer(texp, "multiply", 0.7)
        IM["texture_after"] = _pil(ctx.composited()).convert("RGB")
        # the plain texture swatch, so the reader sees the raw tile
        IM["texture_swatch"] = _pil(tex).convert("RGB")

        # frames & edges demo: build our OWN synthetic transparent-centre frame (a torn /
        # distressed dark border with a clear middle), never the user's licensed library,
        # and drop it onto the same scene via the real add_overlay_layer at Normal / 100%,
        # so the photo shows through the clear centre.
        import random as _rnd
        frame = QImage(ow, oh, QImage.Format_ARGB32); frame.fill(Qt.transparent)
        fp2 = QPainter(frame); fp2.setPen(Qt.NoPen)
        fp2.fillRect(0, 0, ow, oh, QColor(18, 14, 10, 255))        # opaque dark border fill
        # ragged inner edge: carve a clear centre with a jittered torn margin
        _rnd.seed(7)
        inset = 34
        fp2.setCompositionMode(QPainter.CompositionMode_Clear)
        for xx in range(inset, ow - inset):
            top = inset + _rnd.randint(-6, 6); bot = oh - inset + _rnd.randint(-6, 6)
            fp2.fillRect(xx, max(0, top), 1, max(1, bot - top), Qt.transparent)
        fp2.end()
        IM["frame_swatch"] = _pil(frame).convert("RGBA")

        frp = os.path.join(tmpd, "demo_frame.png"); frame.save(frp)
        cfr = _throwaway_canvas(base)
        cfr.add_overlay_layer(frp, "normal", 1.0)
        IM["frame_after"] = _pil(cfr.composited()).convert("RGB")
    except Exception as e:
        print("overlay/texture demo failed:", e)

    # --- live window, tool palette, layers dock --------------------------
    w = _win()
    IM["workspace"] = _grab(w)
    # the vertical tools toolbar
    try:
        tools_tb = None
        for tb in w.findChildren(QToolBar):
            if tb.orientation() == Qt.Vertical:
                tools_tb = tb; break
        if tools_tb is not None:
            IM["toolpalette"] = _grab(tools_tb)
    except Exception as e:
        print("tool palette grab failed:", e)
    # the top (paint) toolbar — colour / size / zoom
    try:
        for tb in w.findChildren(QToolBar):
            if tb.orientation() == Qt.Horizontal:
                IM["topbar"] = _grab(tb); break
    except Exception as e:
        print("top bar grab failed:", e)
    # the Layers dock
    try:
        IM["layers_dock"] = _grab(w.layers_dock.widget())
    except Exception as e:
        print("layers dock grab failed:", e)

    # --- dialogs: drive the real commands; _cap_exec stores them ----------
    def drive(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            print("drive failed:", getattr(fn, "__name__", fn), e)
        for _ in range(6):
            app.processEvents()

    w2 = _win()
    # give it a real picture so the live-preview dialogs have something to chew on
    try:
        w2.canvas.load(_scene())
        for _ in range(4):
            app.processEvents()
    except Exception as e:
        print("seed scene failed:", e)

    drive(w2.dlg_brightness)
    drive(w2.dlg_levels)
    drive(w2.dlg_curves)
    drive(w2.dlg_huesat)
    drive(w2.dlg_temperature)
    drive(w2.dlg_colorbalance)
    drive(w2.dlg_threshold)
    drive(w2.dlg_posterize)
    drive(w2.dlg_blur)
    drive(w2.dlg_unsharp)
    drive(w2.dlg_median)
    drive(w2._fx_dialog, "shadow")
    drive(w2._fx_dialog, "glow")
    drive(w2.dlg_lens_flare)      # Image ▸ Lens Flare… studio
    try:                          # Smooth Skin — seed a skin-tone picture so the preview has skin
        if IM.get("smooth_before") is not None:
            from PIL import Image as _PI
            w2.canvas.load(PC.pil2q(IM["smooth_before"]))
            for _ in range(4):
                app.processEvents()
    except Exception as e:
        print("smooth skin seed failed:", e)
    drive(w2.dlg_smooth_skin)     # Adjust ▸ Smooth Skin… studio
    drive(w2.new)                 # New Image dialog
    drive(w2.cutout_studio)       # Cutout Studio
    try:                          # Smart Mask — seed scribbles so the dialog (not the hint) opens
        import numpy as _np
        h, w = w2.canvas.img.height(), w2.canvas.img.width()
        k = _np.zeros((h, w), bool); r = _np.zeros((h, w), bool)
        k[h // 2 - 20:h // 2 + 20, w // 2 - 20:w // 2 + 20] = True
        r[5:25, 5:25] = True
        w2.canvas.sm_keep = k; w2.canvas.sm_remove = r
    except Exception as e:
        print("smart mask scribble seed failed:", e)
    drive(w2.smart_mask_apply)    # Smart Mask dialog
    drive(w2.export)              # Export dialog
    drive(w2.add_overlay_dialog)  # Add Overlay picker
    drive(w2.place_texture_dialog)  # Place Texture picker

    # Add Frame / Edge picker — seed a tiny NESTED temp frame library so the swatch grid is
    # populated for the capture (the real library at ~/.local/share/justapps/frames is read
    # live and may be partial / still streaming in). Frames are transparent-centre PNGs.
    try:
        import tempfile as _tf2
        _frroot = _tf2.mkdtemp(prefix="paintmanual_framelib_")
        for _vol, _col in (("Vol. 1 Artistic Edges", (24, 20, 16)),
                           ("Vol. 3 Film Strip Edges", (12, 12, 12))):
            _d = os.path.join(_frroot, "Extreme Edges", _vol); os.makedirs(_d)
            for _i in range(4):
                _fi = QImage(300, 220, QImage.Format_ARGB32); _fi.fill(Qt.transparent)
                _fp = QPainter(_fi); _fp.setPen(Qt.NoPen)
                _fp.fillRect(0, 0, 300, 220, QColor(*_col, 255))
                _fp.setCompositionMode(QPainter.CompositionMode_Clear)
                _m = 26 + _i * 4
                _fp.fillRect(_m, _m, 300 - 2 * _m, 220 - 2 * _m, Qt.transparent); _fp.end()
                _fi.save(os.path.join(_d, "edge%d.png" % (_i + 1)))
        PC.FRAME_LIBRARY_DIR = _frroot
        drive(w2.add_frame_dialog)    # Image ▸ Add Frame / Edge…
    except Exception as e:
        print("frame picker capture failed:", e)

    # Open from Library picker — seed a tiny temp library so the swatch grid is populated
    # for the capture (the real library at ~/.local/share/justapps/images is read live
    # and may be empty / still streaming in).
    try:
        import tempfile
        from PIL import Image as _PI
        _libroot = tempfile.mkdtemp(prefix="paintmanual_imglib_")
        for _cat, _cols in (("People", [(204, 68, 68), (210, 150, 90), (120, 150, 190)]),
                            ("Nature", [(80, 150, 90), (60, 120, 160), (200, 180, 90)]),
                            ("City",   [(110, 110, 120), (160, 120, 90), (90, 120, 150)])):
            _d = os.path.join(_libroot, "Premium Image Collection 6", _cat); os.makedirs(_d)
            for _i, _c in enumerate(_cols):
                _PI.new("RGB", (480, 360), _c).save(os.path.join(_d, "photo%d.jpg" % (_i + 1)), "JPEG")
        PC.IMAGE_LIBRARY_DIR = _libroot
        drive(w2.open_from_library)   # File ▸ Open from Library…
    except Exception as e:
        print("library picker capture failed:", e)

    IM["_dialogs"] = dict(DGRABS)
    return IM


# ----------------------------------------------------------------- image out
def datauri(im, maxw=1100, quality=82):
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
        im = bg
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def datauri_png(im, maxw=1100):
    """Lossless PNG data URI — for pictures with transparency (the cutout result)."""
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ----------------------------------------------------------------- content DSL
def fig(im, cap, cls=""):
    if im is None:
        return ""   # a capture that didn't happen degrades to no figure, not a broken box
    if isinstance(im, str):
        uri = im
    elif im.mode in ("RGBA", "LA"):
        uri = datauri_png(im)
    else:
        uri = datauri(im)
    c = f" {cls}" if cls else ""
    return f'<figure class="f{c}"><img src="{uri}" alt="{H.escape(cap)}"><figcaption>{cap}</figcaption></figure>'


def proc(title, *steps, intro=""):
    lis = "".join(f"<li>{s}</li>" for s in steps)
    pre = f"<p>{intro}</p>" if intro else ""
    return f'<div class="proc"><p class="proc-h">To {title}</p>{pre}<ol class="steps">{lis}</ol></div>'


def note(body):
    return f'<div class="cal note"><span class="cal-k">Note</span>{body}</div>'


def tip(body):
    return f'<div class="cal tip"><span class="cal-k">Tip</span>{body}</div>'


def caution(body):
    return f'<div class="cal caution"><span class="cal-k">Remember</span>{body}</div>'


def K(x):
    return f"<kbd>{x}</kbd>"


# ----------------------------------------------------------------- the manual
def manual_parts(IM):
    """Returns a list of parts. Each part: (part_title, blurb, [chapters]).
    Each chapter: (title, intro_html, [(heading, body_html), ...])."""
    D = IM.get("_dialogs", {})

    def dlg(*names):
        for n in names:
            if n in D:
                return D[n]
        return None

    parts = []

    # ============================================================ PART I
    ch = []
    ch.append(("Welcome to PAINTcanvas",
      "<p class='lede'>PAINTcanvas is a <b>raster image editor</b> — a program for painting, retouching "
      "and adjusting pictures made of pixels. It belongs to the <i>just a…</i> family of apps and works in "
      "the tradition of Serif's PhotoPlus: paint with brushes, draw shapes, correct colour, apply filters, "
      "stack layers, cut a subject out from its background, and save a PNG or JPEG.</p>", [
      ("What a raster editor is", f"""
<p>A picture on a screen is a grid of coloured dots called <b>pixels</b>. A <b>raster</b> (or
<i>bitmap</i>) editor lets you change those pixels directly — darken them, blur them, paint new ones over
the top. That is exactly how a photograph works, which is why raster editors are the natural home for
retouching photos, painting digital artwork, and preparing images for a web page or a printed layout.</p>
{fig(IM.get('scene'), 'A picture open in PAINTcanvas. Everything you see is a grid of pixels you can paint over, adjust and filter.')}
<p>Its vector sibling, <b>DRAWmaster</b>, is different: there a circle stays a mathematical circle you can
resize forever without blurring. In PAINTcanvas a circle is <i>painted</i> into the pixels — perfect for
photographs, textures and painterly work, but it is the pixels, not shapes, that you edit from then on.</p>"""),
      ("What you can do with it", f"""
<p>PAINTcanvas gathers the everyday tools of a photo editor into one small window:</p>
<ul>
<li><b>Paint and draw</b> — a brush, an eraser, straight lines, rectangles, ellipses, a flood fill and a
gradient;</li>
<li><b>Retouch</b> — a clone (rubber-stamp) tool, red-eye removal, and dodge and burn for lightening and
darkening by hand;</li>
<li><b>Adjust colour and tone</b> — brightness and contrast, levels, hue and saturation, colour temperature
and balance, and one-click fixes like auto-contrast, greyscale and sepia;</li>
<li><b>Apply filters</b> — blur, sharpen, unsharp mask, despeckle, emboss, find-edges and more;</li>
<li><b>Work in layers</b> — stack images, blend them, change their opacity;</li>
<li><b>Cut out a subject</b> — the <b>Cutout</b> tool and <b>Cutout Studio</b> erase a background to
transparency;</li>
<li><b>Add effects</b> — a soft drop shadow or outer glow behind your artwork.</li>
</ul>
{note('Adjustments and filters are powered by the Pillow and NumPy libraries. If they are not installed, those menus explain how to add them; painting, shapes and layers work regardless.')}"""),
      ("The just a… family", """
<p>PAINTcanvas has three companions, built to work together:</p>
<ul>
<li><b>PAGEdesigner</b> lays out printed pages — and hands a photo to PAINTcanvas for retouching, taking
the result straight back;</li>
<li><b>WEBcreator</b> builds websites the same way;</li>
<li><b>DRAWmaster</b> is for vector illustration and logos.</li>
</ul>
<p>They share the <b>CREATORsuite</b> launcher and a common <i>Pictures/just a…</i> folder, so a picture
you save here is one click away in the others. A list of your recent files is shared too.</p>"""),
      ("About this guide", f"""
<p>This User Guide is the complete reference. It is organised in parts: the first gets you working; the
middle teaches each group of tools in depth, with step-by-step procedures; then come worked projects you
can follow start to finish, and finally a reference section — menus, shortcuts, a tool reference, a
glossary and troubleshooting.</p>
{note('Throughout, a numbered <b>“To …”</b> box is a procedure you can follow exactly. A <b>Tip</b> suggests a faster or better way. A <b>Remember</b> box flags something easy to forget.')}
<p>For a gentler first read, start with the <b>Quick Start Guide</b> (Help ▸ Quick Start), which paints,
adjusts and cuts out a picture in about a dozen short steps.</p>"""),
      ("Conventions used here", f"""
<p>A few conventions keep the instructions short:</p>
<ul>
<li><b>Menu ▸ Command</b> means “open this menu and choose this command”, e.g. <b>Image ▸ Resize Image…</b>.</li>
<li>Keys are shown like {K('Ctrl')}+{K('S')}; on a Mac read {K('Ctrl')} as {K('Cmd')}.</li>
<li><b>Click</b> means the left mouse button; <b>drag</b> means press, move, release.</li>
<li><b>Ctrl-click</b> means hold {K('Ctrl')} while you click — used to set the clone tool's source.</li>
</ul>""")]))

    ch.append(("Starting Out",
      "<p class='lede'>This chapter covers the very first things: opening the program, starting a new "
      "picture (including a transparent one), opening an existing image, and saving your work as a PNG "
      "or JPEG.</p>", [
      ("Launching the program", """
<p>Open <b>just a… PAINTcanvas</b> from the CREATORsuite launcher, from your system's application menu, or
by running <code>paint</code> in a terminal. You can also start it on a picture directly — drag an image
onto its icon, or pass the file on the command line — and it opens with that image loaded.</p>"""),
      ("Starting a new picture", f"""
<p>Choose <b>File ▸ New…</b> ({K('Ctrl')}+{K('N')}) to begin a fresh canvas.</p>
{fig(dlg('New Image'), 'The New Image dialog: pick a size preset, a background colour, or a transparent background.')}
{proc('start a new picture',
  'Choose <b>File ▸ New…</b>.',
  'Pick a size from the list — 1000×700, HD (1920×1080), a square, A4 at 150 dpi, or a 1080×1080 social-media square.',
  'Choose a <b>background colour</b>, or tick <b>Transparent background</b> for a canvas with no backdrop at all.',
  'Click <b>Create</b>.')}
{tip('A <b>transparent background</b> is the right choice for a logo, a cut-out, or anything you will drop on top of another picture later — the empty areas stay see-through when you save a PNG. The transparent squares you see are just a checkerboard marking “nothing here”.')}"""),
      ("Opening an existing image", f"""
{proc('open a picture',
  'Choose <b>File ▸ Open…</b> (' + K('Ctrl') + '+' + K('O') + ').',
  'Browse to a PNG, JPEG, BMP, GIF or WebP file and choose it.',
  'The picture loads onto a single <b>Background</b> layer, ready to edit.')}
{note('PAINTcanvas opens in your shared <i>Pictures/just a…</i> folder by default, so pictures saved by the other apps are easy to find.')}"""),
      ("Opening from your image library", f"""
<p>If you keep a local stock-photo library, <b>File ▸ Open from Library…</b> lets you browse it by category
and open a photo straight into PAINTcanvas — no hunting through folders.</p>
{proc('open a photo from your library',
  'Choose <b>File ▸ Open from Library…</b>.',
  'Pick a <b>category</b> from the drop-down — each is one folder of your library (e.g. “Premium Image Collection 6 / People”).',
  'Click a <b>thumbnail</b> to choose that photo, then <b>Open this photo</b>.',
  'The picture loads onto a single <b>Background</b> layer, exactly as File ▸ Open would.')}
{fig(dlg('Open from Library'), 'The Image Library picker: browse your stock-photo collections by category and click a thumbnail to open it.')}
{note('Thumbnails are decoded small and fast, so even a library of thousands of high-resolution photos scrolls smoothly. The library is read straight from disk — nothing is copied until you edit and save.')}
{tip('No library yet? The same dialog has a <b>Browse for an image…</b> button to open any image file on your computer.')}"""),
      ("Saving your work", f"""
<p>Save with <b>File ▸ Save</b> ({K('Ctrl')}+{K('S')}) or <b>Save As…</b>. PAINTcanvas writes two formats:</p>
<ul>
<li><b>PNG</b> — lossless, and it keeps transparency. Use it for artwork, logos, cut-outs and anything with
sharp edges or see-through areas.</li>
<li><b>JPEG</b> — smaller files, but no transparency and a little quality lost to compression. Use it for
photographs you want to share or email.</li>
</ul>
{caution('Saving a layered picture <b>flattens</b> all its layers into the one image in the file — PNG and JPEG cannot store separate layers. Keep a master PNG if you expect to re-edit, and remember that saving as JPEG fills any transparent areas with white.')}"""),
      ("Exporting to other formats", f"""
<p>For anything beyond the everyday PNG and JPEG, <b>File ▸ Export…</b> ({K('Ctrl')}+{K('Shift')}+{K('E')})
opens a dialog that gives you the choice of format and the controls that go with it.</p>
{fig(dlg('Export Image'), 'The Export dialog: a format menu, a quality slider with a live estimated file size, and a transparency toggle.')}
<p>The <b>Format</b> menu offers five formats, and the other controls enable or grey out to suit the one you pick:</p>
<ul>
<li><b>PNG</b> — lossless, with transparency. The <b>Keep transparency</b> box lets you flatten onto white instead if you prefer a solid picture.</li>
<li><b>JPEG</b> — small photographic files; the <b>Quality</b> slider trades file size against compression, and there is no transparency.</li>
<li><b>WEBP</b> — a modern web format that is smaller than both and keeps transparency; it has a <b>Quality</b> slider too.</li>
<li><b>GIF</b> — a simple, widely-supported format (limited colours), with transparency.</li>
<li><b>BMP</b> — an uncompressed bitmap for programs that need one.</li>
</ul>
<p>As you change the format, quality or transparency, an <b>Estimated size</b> line updates so you can see
roughly how big the file will be before you commit.</p>
{proc('export a picture',
  'Choose <b>File ▸ Export…</b>.',
  'Pick the <b>Format</b>. The quality slider and transparency box enable themselves to suit it.',
  'For JPEG or WEBP, drag the <b>Quality</b> slider — watch the estimated file size change — and for PNG decide whether to <b>Keep transparency</b>.',
  'Click <b>Export…</b>, choose a name and place, and confirm.')}
{tip('Exporting never touches your working picture — it only writes a copy in the chosen format. Use <b>Save</b> for your ordinary PNG/JPEG working file and <b>Export</b> when you need WEBP for the web, a GIF, or a tuned-down JPEG for email.')}""")]))

    ch.append(("The Workspace",
      "<p class='lede'>Everything happens in one window: your picture in the middle, the tools down the "
      "left, the colour and size controls across the top, and the Layers panel on the right. This chapter "
      "names every part so the rest of the guide can refer to them.</p>", [
      ("A tour of the window", f"""
<p>A new picture opens centred on a dark pasteboard, with everything you need around it.</p>
{fig(IM.get('workspace'), 'The PAINTcanvas workspace: the tool palette (left), the paint toolbar (top), the picture (centre) and the Layers panel (right).')}
<p>The parts are:</p>
<ul>
<li>the <b>menu bar</b> across the top — File, Edit, Image, Adjust, Filter, Select, Layer, Effects, Help;</li>
<li>the <b>paint toolbar</b> below it — the current colour, the brush size, and zoom;</li>
<li>the vertical <b>tool palette</b> down the left edge;</li>
<li>the <b>picture</b> itself in the centre, on its pasteboard;</li>
<li>the <b>Layers</b> panel on the right;</li>
<li>the <b>status bar</b> along the bottom, which shows hints and the cursor's pixel position.</li>
</ul>"""),
      ("The tool palette", f"""
<p>The vertical <b>tool palette</b> on the left holds every tool you paint and edit with. Click one to
select it; its name appears as a tooltip and in the status bar.</p>
{fig(IM.get('toolpalette'), 'The tool palette — from Brush at the top to the Smart Mask tool at the foot.', 'tall')}
<p>From the top: <b>Brush</b>, <b>Eraser</b>, <b>Line</b>, <b>Rectangle</b>, <b>Ellipse</b>,
<b>Fill</b> (the bucket), <b>Gradient</b>, <b>Pick colour</b> (the eyedropper), <b>Text</b>,
<b>Clone</b>, <b>Red-eye</b>, <b>Dodge</b>, <b>Burn</b>, the two marquee selection tools (<b>rectangle</b> and
<b>ellipse</b>), the <b>Magic Wand</b> (select by colour), and the <b>Cutout</b> tool. Each is covered in the
chapters that follow.</p>"""),
      ("The paint toolbar", f"""
<p>The horizontal toolbar below the menus carries the settings shared by most tools.</p>
{fig(IM.get('topbar'), 'The paint toolbar: the colour swatch, the brush size, and the zoom buttons.')}
<ul>
<li>The <b>Colour</b> button shows and sets the current colour — click it for a full colour picker.</li>
<li><b>Size</b> sets the brush/line/eraser width in pixels, from 1 to 200.</li>
<li><b>Zoom +</b>, <b>Zoom −</b> and <b>100%</b> change how large the picture appears on screen — without
changing the picture itself.</li>
</ul>
{tip('Zoom is just magnification for your eyes. To change the real pixel size of a picture, use <b>Image ▸ Resize Image…</b> instead.')}"""),
      ("The Layers panel", f"""
<p>The <b>Layers</b> panel on the right stacks your picture's layers, topmost at the top, and controls each
one. Layers get a chapter of their own; for now, note the parts.</p>
{fig(IM.get('layers_dock'), 'The Layers panel: a blend-mode menu and opacity slider at the top, the list of layers, and the layer buttons beneath.')}
<ul>
<li>A <b>blend</b> menu and an <b>opacity</b> slider at the top set how the active layer mixes with those
below it;</li>
<li>the <b>list</b> shows every layer — tick its box to show or hide it, double-click to rename it, click to
make it active;</li>
<li>the row of buttons adds, duplicates, merges down, moves up or down, and deletes a layer.</li>
</ul>"""),
      ("Moving around and zooming", f"""
{proc('change the zoom',
  'Click <b>Zoom +</b> or <b>Zoom −</b> on the paint toolbar, or',
  'click <b>100%</b> to return to actual size.',
  'Scroll bars appear automatically when the picture is larger than the window.')}
<p>The <b>status bar</b> at the foot shows the cursor's position in pixels as you move over the picture —
useful for placing something precisely, or reading off a size.</p>"""),
      ("Undo, redo and the history", f"""
<p>PAINTcanvas keeps a generous <b>undo history</b>, so you can paint and experiment freely.</p>
{proc('undo and redo',
  'Choose <b>Edit ▸ Undo</b> (' + K('Ctrl') + '+' + K('Z') + ') to step back, one change at a time.',
  'Choose <b>Edit ▸ Redo</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K('Z') + ') to step forward again.')}
{note('The history remembers the last two dozen changes. It is cleared when you start or open a new picture.')}""")]))

    parts.append(("Part I", "Getting Started", ch))

    # ============================================================ PART II
    ch = []
    ch.append(("Painting and Drawing",
      "<p class='lede'>The painting tools put colour on the canvas directly: a freehand brush, an eraser, "
      "straight lines and shapes, a flood fill, and a gradient. Colour and size on the paint toolbar apply "
      "to them all.</p>", [
      ("Choosing a colour and size", f"""
{proc('set the colour and brush size',
  'Click the <b>Colour</b> button on the paint toolbar and pick a colour (by swatch, by sliders, or by typing a hex value).',
  'Set the <b>Size</b> spinner to the width you want, in pixels.',
  'Both apply to the brush, eraser, line, rectangle, ellipse and gradient from now on.')}
{tip('To match a colour already in the picture, use the <b>Pick colour</b> (eyedropper) tool and click the pixel you want — the colour becomes the current colour.')}"""),
      ("The Brush and Eraser", f"""
<p>The <b>Brush</b> paints a soft round stroke in the current colour; drag to draw freehand. The
<b>Eraser</b> works the same way but removes pixels instead — on a layer with transparency it erases to
see-through; on the solid Background it reveals whatever is beneath.</p>
{fig(IM.get('shapes'), 'A brush squiggle and a straight line (top), with outlined and filled shapes and a gradient below.')}
{proc('paint a freehand stroke',
  'Choose the <b>Brush</b>, set a colour and size.',
  'Press and drag on the canvas; release to end the stroke.',
  'Each stroke is one undo step, so a mistake is one ' + K('Ctrl') + '+' + K('Z') + ' away.')}"""),
      ("Lines, rectangles and ellipses", f"""
<p>Three tools draw crisp shapes in the current colour and size. Each previews as you drag, so you see
the result before you let go.</p>
{proc('draw a line or shape',
  'Choose the <b>Line</b>, <b>Rectangle</b> or <b>Ellipse</b> tool.',
  'Press where it should start and drag to where it should end.',
  'Release to paint it. The outline width follows the <b>Size</b> setting.')}"""),
      ("Filled shapes", f"""
<p>When the <b>Rectangle</b> or <b>Ellipse</b> tool is chosen, a <b>Shape</b> menu and a <b>Fill colour</b>
button appear on the paint toolbar. The menu offers three ways to draw the shape:</p>
<ul>
<li><b>Outline</b> — an unfilled outline in the current colour and size (the classic behaviour);</li>
<li><b>Fill</b> — a solid shape with no outline;</li>
<li><b>Both</b> — a filled shape <i>and</i> an outline around it.</li>
</ul>
<p>By default the fill uses the current colour; click <b>Fill colour</b> to pick a different colour just for
the fill, so you can outline in one colour and fill with another.</p>
{fig(IM.get('fills'), 'A rectangle drawn as outline, fill, and both; a filled ellipse; and a two-colour gradient band.')}
{proc('draw a solid shape',
  'Choose the <b>Rectangle</b> or <b>Ellipse</b> tool.',
  'Set the <b>Shape</b> menu to <b>Fill</b> (solid) or <b>Both</b> (solid with an outline).',
  'Leave the fill as the current colour, or click <b>Fill colour</b> to choose a separate one.',
  'Drag out the shape and release. It is painted solid.')}
{tip('The Line tool is always a stroke — only rectangles and ellipses have an interior to fill.')}"""),
      ("The Fill (bucket) tool", f"""
<p>The <b>Fill</b> tool floods a connected area of one colour with the current colour — the classic paint
bucket. Click inside a region and every touching pixel of the same colour changes at once.</p>
{proc('fill an area with colour',
  'Choose the <b>Fill</b> tool and set the colour you want.',
  'Click inside the area to flood.',
  'Only the connected same-coloured pixels change, so a shape’s outline keeps the fill contained.')}
{tip('Fill works on exact colour matches. If a photo’s “flat” area is really many slightly different pixels, the fill may stop early — flatten the colour first with <b>Posterize</b> or <b>Threshold</b>, or paint by hand.')}"""),
      ("The Gradient tool", f"""
<p>The <b>Gradient</b> tool paints a smooth two-colour blend across the canvas. When it is chosen, a
<b>Gradient</b> label with <b>Start</b> and <b>End</b> colour buttons and a <b>Fade to clear</b> tick box
appear on the paint toolbar. Pick a start colour and an end colour, then drag: the start of the drag is the
start colour and the end of the drag is the end colour, blended evenly between. It is ideal for a sky wash, a
two-tone background, or a coloured fade behind a subject.</p>
{proc('paint a two-colour gradient',
  'Choose the <b>Gradient</b> tool.',
  'Click <b>Start</b> and pick the first colour; click <b>End</b> and pick the second.',
  'Drag across the canvas in the direction you want the blend to run; release to paint it.')}
{tip('Tick <b>Fade to clear</b> to fade the start colour out to transparent instead of to a second colour — the way to make a soft vignette or feather an overlay out at one edge. If a selection is active, the gradient is confined to it.')}"""),
      ("Adding text", f"""
<p>The <b>Text</b> tool stamps a line of text into the picture as pixels.</p>
{proc('add a line of text',
  'Choose the <b>Text</b> tool and set the colour.',
  'Click where the text should start.',
  'Type the text in the little box that appears and confirm. It is painted at a size based on the brush size (roughly four times it).')}
{caution('Because the text becomes pixels immediately, you cannot re-edit the words afterwards — only paint over them or undo. For headline text you will keep tweaking, set it in PAGEdesigner or DRAWmaster instead, where text stays editable.')}""")]))

    ch.append(("Retouching",
      "<p class='lede'>These tools repair and refine a photograph: the Clone stamp copies one part of a "
      "picture over another, Red-eye removal fixes flash-reddened eyes, Dodge and Burn lighten and darken by "
      "brushing, and Smooth Skin gives a portrait a tasteful retouch automatically.</p>", [
      ("The Clone tool", f"""
<p>The <b>Clone</b> (rubber-stamp) tool paints with pixels copied from somewhere else in the picture —
the standard way to cover a blemish, remove an object, or extend a texture.</p>
{proc('clone out a blemish',
  'Choose the <b>Clone</b> tool.',
  'Hold ' + K('Ctrl') + ' and click a clean area to set the <b>source</b> — the place to copy from.',
  'Let go of ' + K('Ctrl') + ' and paint over the spot you want to hide. Pixels from the source are stamped under your brush, the source moving in step with you.',
  'Re-set the source (Ctrl-click) whenever you want to copy from somewhere new.')}
{tip('Clone from an area with similar colour and texture, and keep strokes short — it looks most natural when the copied pixels blend into their surroundings.')}"""),
      ("Red-eye removal", f"""
<p>Flash photography can turn eyes red. <b>Red-eye</b> removal neutralises it in one click.</p>
{proc('remove red-eye',
  'Choose the <b>Red-eye</b> tool.',
  'Set the <b>Size</b> large enough to cover the red part of the eye.',
  'Click on the red pupil. Strongly red pixels in a small area around the click are darkened to a natural grey, leaving the rest of the eye untouched.')}"""),
      ("Dodge and Burn", f"""
<p><b>Dodge</b> lightens and <b>Burn</b> darkens, applied by brushing — the darkroom technique for lifting a
shadow or deepening a highlight a little at a time.</p>
{proc('lighten or darken an area by hand',
  'Choose <b>Dodge</b> to lighten or <b>Burn</b> to darken.',
  'Set a generous brush size.',
  'Brush gently over the area. The effect builds up as you go over it, so start light and repeat.')}
{note('Dodge and burn are subtle on purpose — each pass changes the pixels only a little, so you keep control. For a big, even change, reach for <b>Adjust ▸ Brightness / Contrast</b> instead.')}"""),
      ("Smooth skin (portrait retouch)", f"""
<p><b>Smooth Skin</b> is an automatic portrait retouch, in the spirit of a professional skin-smoothing
plug-in. It finds the skin in a photo by its <b>tone</b>, smooths it with an <b>edge-preserving</b> filter —
one that evens out blotches, shine and fine blemishes while leaving the sharp features (eyes, brows, lips,
nostrils, the hairline) crisp — and blends the result back by an amount you control. It lives on
<b>Adjust ▸ Smooth Skin (portrait retouch)…</b>.</p>
{fig(IM.get('smooth_mask'), 'The skin is detected automatically by its tone (white = full retouch, black = left alone). Eyes and lips fall outside the mask and stay sharp.')}
<div class="imgrow">
{fig(IM.get('smooth_before'), 'Before: blotchy, noisy skin.')}
{fig(IM.get('smooth_after'), 'After: the skin is evened out, but the eyes and mouth stay crisp.')}
</div>
{fig(dlg('Smooth Skin'), 'The Smooth Skin studio, previewed live on the picture: Amount, Smoothing radius and Detail preserve, with auto skin detection and a mask peek.')}
<p>Three sliders shape the look:</p>
<ul>
<li><b>Amount</b> — how strongly the smoothed skin is blended back in. The master control; ease it up until
blemishes fade but the face still looks real.</li>
<li><b>Smoothing radius</b> — how large an area each smoothing step samples. Small for freckly or finely
textured skin; larger to even out big blotches (too large starts to flatten the face).</li>
<li><b>Detail preserve</b> — adds a fraction of the original fine texture (pores, grain) back on top of the
smooth result. This is the trick that stops the retouch looking plastic — keep a little of it.</li>
</ul>
{proc('retouch a portrait',
  'Choose <b>Adjust ▸ Smooth Skin (portrait retouch)…</b>.',
  'Leave <b>Skin only (auto-detect)</b> ticked so only the skin is touched — the eyes, lips and hair are left alone. (Untick it to retouch the current selection, or the whole picture, instead.)',
  'Raise <b>Amount</b> until the skin evens out, watching the live preview; nudge <b>Smoothing radius</b> for blotchy skin.',
  'Keep a little <b>Detail preserve</b> so the skin does not look plastic.',
  'Tick <b>Show skin mask</b> at any time to check what the auto-detect has selected.',
  'Click <b>Apply</b>. The retouch lands on its own new layer, so you can ease the whole effect back later with the layer’s opacity, or hide it to compare.')}
{note('Smooth Skin uses OpenCV’s bilateral filter for the best edge-preserving result, and the installer adds OpenCV automatically. If it is not present the tool falls back to a built-in NumPy smoother — a little less refined, but it needs nothing extra and always works.')}
{tip('The classic advice: do not over-smooth. A retouched face should still have skin texture — the goal is to remove blemishes and even out tone, not to turn the subject into a mannequin. Leave some Detail, and lower the layer opacity if the effect feels too strong.')}""")]))

    ch.append(("Selecting (Magic Wand, Feather, Invert)",
      "<p class='lede'>A selection fences off part of the picture so the next thing you do affects only "
      "that area. PAINTcanvas offers three ways to select — a rectangle marquee, an ellipse marquee and the "
      "<b>Magic Wand</b> (select by colour) — and a set of Select-menu commands to invert, feather, grow and "
      "shrink whatever you have selected. Every adjustment, filter, the Gradient tool and Crop respect the "
      "selection if one is active.</p>", [
      ("The marquee tools", f"""
{proc('select a rectangular or oval area',
  'Choose the <b>Select — rectangle</b> or <b>Select — ellipse</b> tool from the tool palette.',
  'Drag across the picture to mark the area. A dashed outline shows the selection.',
  'Apply an adjustment or filter — it now affects only inside the marquee.')}
{note('The dashed “marching ants” outline is a marker, not part of the picture; it never prints or saves.')}"""),
      ("The Magic Wand — select by colour", f"""
<p>The <b>Magic Wand</b> ({K('✦')} in the tool palette) selects an area by its <b>colour</b> rather than by
dragging a box. Click a pixel and it grows a selection outward to cover every neighbouring pixel of a similar
colour — perfect for grabbing a sky, a flat background, or one coloured object.</p>
{proc('select an area by colour',
  'Choose the <b>Magic Wand</b> tool. A <b>Wand tol</b> (tolerance) box and a <b>Contiguous</b> checkbox appear in the top toolbar.',
  'Click a pixel in the colour you want. The matching region becomes the selection, shown as a soft blue tint with a bright outline.',
  'Raise <b>Wand tol</b> to catch more shades (a wider colour range); lower it to be stricter.',
  'Leave <b>Contiguous</b> ticked to select only the connected patch you clicked; untick it to select <i>every</i> matching pixel in the picture at once.')}
<div class="imgrow">
{fig(IM.get('wand_before'), 'Before: a red ball on a plain background.')}
{fig(IM.get('wand_after'), 'After clicking the ball with the Magic Wand and applying a hue shift — only the selected colour changed.')}
</div>
{tip('The wand makes a free-form selection (a “mask”), not a box — so it follows the exact edge of whatever you clicked. Every adjustment, filter and the Gradient tool then apply only inside it.')}"""),
      ("Invert, Feather, Grow and Shrink", f"""
<p>Once you have a selection, the <b>Select</b> menu reshapes it:</p>
<ul>
<li><b>Invert</b> ({K('Ctrl')}+{K('Shift')}+{K('I')}) swaps selected for unselected — select a subject with the wand, invert, and you now have its background (ideal for blurring or darkening <i>everything but</i> the subject);</li>
<li><b>Feather…</b> softens the selection edge by a radius you type, so the next adjustment fades smoothly in and out instead of stopping at a hard line;</li>
<li><b>Grow…</b> expands the selection outward by a few pixels;</li>
<li><b>Shrink…</b> pulls it inward.</li>
</ul>
{proc('blend an adjustment at the edges with Feather',
  'Make a selection (wand or marquee).',
  'Choose <b>Select ▸ Feather…</b> and enter a radius in pixels — larger means a softer, wider fade.',
  'Apply an adjustment or filter. Instead of a crisp border, the effect now blends gradually across the feathered edge.')}
{note('Feather, Invert, Grow and Shrink all work on a free-form mask internally — applying any of them to a rectangle or ellipse marquee automatically converts it to a mask first, which is why the outline changes from a clean box to a traced edge.')}"""),
      ("Select All and Deselect", f"""
<p>Two menu commands round out selecting:</p>
<ul>
<li><b>Select ▸ Select All</b> ({K('Ctrl')}+{K('A')}) selects the whole picture;</li>
<li><b>Select ▸ Deselect</b> ({K('Ctrl')}+{K('D')}) clears the selection so changes affect everything again.</li>
</ul>
{caution('If an adjustment or filter seems to touch only part of the picture, you probably have a selection active. <b>Deselect</b> and try again.')}"""),
      ("What a selection affects", """
<p>A selection confines the <b>Adjust</b> and <b>Filter</b> commands and the <b>Gradient</b> tool to its
area, and <b>Image ▸ Crop to Selection</b> trims the whole picture down to it (for a wand/mask selection,
down to its bounding box). The painting tools (brush, eraser, shapes) are not fenced in by a selection —
they paint wherever you drag.</p>""")]))

    parts.append(("Part II", "Painting, Retouching and Selecting", ch))

    # ============================================================ PART III
    ch = []
    ch.append(("Adjusting Colour and Tone",
      "<p class='lede'>The Adjust menu corrects and transforms colour and brightness across the whole "
      "picture — or, if one is active, just the selection. Most open a dialog with a live preview; the "
      "one-click fixes at the foot of the menu apply at once.</p>", [
      ("Brightness and Contrast", f"""
<p>The everyday fix for a photo that is too dark, too flat, or too washed out.</p>
{fig(dlg('Brightness / Contrast'), 'Brightness / Contrast — drag the sliders and watch the picture update live.')}
{proc('brighten and add punch',
  'Choose <b>Adjust ▸ Brightness / Contrast…</b>.',
  'Drag <b>Brightness</b> up to lighten the whole picture.',
  'Drag <b>Contrast</b> up to make darks darker and lights lighter — more “snap”.',
  'Click <b>OK</b> to keep the change, or <b>Cancel</b> to leave the picture as it was.')}
{fig(IM.get('adjust_after'), 'The sample scene after a warmer, higher-contrast adjustment.')}"""),
      ("Levels", f"""
<p><b>Levels</b> gives finer control over the tonal range by setting the black point, the white point, and
the mid-tone gamma.</p>
{fig(dlg('Levels'), 'The Levels dialog: black point, white point and gamma.')}
{proc('set the black and white points',
  'Choose <b>Adjust ▸ Levels…</b>.',
  'Raise the <b>Black point</b> so the darkest pixels become true black.',
  'Lower the <b>White point</b> so the brightest become true white.',
  'Nudge <b>Gamma</b> to lighten or darken the mid-tones without moving the ends.')}
{tip('Levels is the most precise way to fix a dull, low-contrast photo: pull the black and white points inward to the edges of the picture’s real tonal range.')}"""),
      ("Curves", f"""
<p><b>Curves</b> is the most powerful tone and colour control of all. Instead of a few sliders it gives you a
graph: the horizontal axis is the <b>input</b> brightness (shadows on the left, highlights on the right) and
the vertical axis is the <b>output</b>. A straight diagonal changes nothing; bend it and you remap every tone
at once.</p>
{fig(dlg('Curves'), 'The Curves dialog: drag points on the graph to reshape the tonal range. Pick RGB (all channels) or an individual Red, Green or Blue channel.')}
{proc('shape tone and colour with Curves',
  'Choose <b>Adjust ▸ Curves…</b>.',
  'Click anywhere on the line to add a control point, then drag it. Pull the middle up to lighten, down to darken.',
  'For the classic “S-curve” that adds contrast, raise the upper part and lower the lower part — brightening highlights and deepening shadows.',
  'Switch the <b>Channel</b> box to <b>Red</b>, <b>Green</b> or <b>Blue</b> to shift a single colour channel (for example, lowering Blue in the shadows warms them).',
  'Right-click a point to remove it, or press <b>Reset</b> to return to the straight line. Click <b>OK</b> to apply.')}
{fig(IM.get('curves_after'), 'The sample scene after a contrast-boosting S-curve.')}
{tip('Curves does everything Brightness, Contrast and Levels do, and more, in one place — but a gentle bend goes a long way. Like every adjustment it respects an active selection, so you can reshape the tones of just one area.')}"""),
      ("Hue and Saturation", f"""
<p>Shift every colour around the wheel, and make colours more or less vivid.</p>
{fig(dlg('Hue / Saturation'), 'Hue / Saturation: a hue shift and a saturation control.')}
{proc('boost or shift colour',
  'Choose <b>Adjust ▸ Hue / Saturation…</b>.',
  'Drag <b>Hue shift</b> to rotate all the colours — greens toward blue, reds toward orange, and so on.',
  'Drag <b>Saturation</b> up for richer colour, or all the way down toward grey.')}"""),
      ("Colour Temperature and Colour Balance", f"""
<p>Two tools correct a colour cast.</p>
{fig(dlg('Colour Temperature'), 'Colour Temperature warms or cools the whole picture on one slider.')}
{proc('warm up or cool down a picture',
  'Choose <b>Adjust ▸ Colour Temperature…</b>.',
  'Drag toward <b>Warm</b> to add orange (sunset, indoor light) or toward <b>Cool</b> to add blue (shade, overcast).')}
{fig(dlg('Colour Balance'), 'Colour Balance shifts the cyan–red, magenta–green and yellow–blue axes independently.')}
{proc('remove a colour cast',
  'Choose <b>Adjust ▸ Colour Balance…</b>.',
  'Nudge the three sliders — <b>Cyan–Red</b>, <b>Magenta–Green</b>, <b>Yellow–Blue</b> — until the cast is gone and neutral areas look neutral.')}"""),
      ("Threshold and Posterize", f"""
<p>Two tools that simplify colour deliberately.</p>
{fig(dlg('Threshold'), 'Threshold reduces the picture to pure black and white at a chosen level.')}
<p><b>Threshold</b> turns every pixel either black or white, split at a level you choose — a stark,
high-graphic look, and a quick way to make a stencil or a line mask.</p>
{fig(dlg('Posterize'), 'Posterize cuts the number of tonal levels for a poster-like, banded look.')}
<p><b>Posterize</b> reduces each colour channel to a few levels (1–8), giving flat bands of colour like a
screen-printed poster.</p>"""),
      ("One-click fixes", f"""
<p>The lower half of the Adjust menu applies at once, with no dialog:</p>
<ul>
<li><b>Auto Contrast</b> — stretches the tonal range automatically; the fastest first fix for a flat photo;</li>
<li><b>Equalize</b> — spreads tones evenly for maximum contrast;</li>
<li><b>Greyscale</b> — removes all colour, leaving a neutral black-and-white image;</li>
<li><b>Invert (Negative)</b> — flips every colour to its opposite, like a film negative;</li>
<li><b>Sepia</b> — a warm brown monochrome, for a vintage feel.</li>
</ul>
<div class="imgrow">
{fig(IM.get('adjust_grey'), 'Greyscale')}
{fig(IM.get('adjust_sepia'), 'Sepia')}
{fig(IM.get('adjust_invert'), 'Invert (Negative)')}
</div>
{tip('All of these respect a selection — greyscale just one object in a colour photo by selecting it first, for a spot-colour effect.')}""")]))

    ch.append(("Filters",
      "<p class='lede'>Filters transform the texture of a picture rather than its colour — softening, "
      "sharpening, cleaning up noise, or producing an artistic effect. Three open a dialog with a radius or "
      "size; the rest apply in one click. All honour an active selection.</p>", [
      ("Gaussian Blur", f"""
<p>The all-purpose softening filter — for a dreamy background, a soft shadow, or to hide noise.</p>
{fig(dlg('Gaussian Blur'), 'Gaussian Blur: one Radius slider, previewed live.')}
{proc('soften a picture or a selection',
  'Choose <b>Filter ▸ Gaussian Blur…</b>.',
  'Drag <b>Radius</b> up for more blur, watching the preview.',
  'Click <b>OK</b>. Select a background first to blur only it, keeping the subject sharp.')}
{fig(IM.get('filter_blur'), 'The sample scene with a gentle Gaussian blur.')}"""),
      ("Unsharp Mask and Median", f"""
<p><b>Unsharp Mask</b> is the professional sharpener: it increases edge contrast by a radius you set, which
makes a slightly soft photo look crisp without the harsh halos of a blunt sharpen.</p>
{fig(dlg('Unsharp Mask'), 'Unsharp Mask sharpens by increasing contrast along edges.')}
<p><b>Median (Despeckle)</b> replaces each pixel with the median of its neighbours over a chosen size —
superb at removing speckle and small blemishes while keeping edges reasonably clean.</p>
{fig(dlg('Median (Despeckle)'), 'Median (Despeckle) cleans up noise and speckle.')}"""),
      ("One-click filters", f"""
<p>The rest of the Filter menu applies instantly:</p>
<ul>
<li><b>Sharpen</b> — a quick edge boost;</li>
<li><b>Soften</b> — a gentle smoothing;</li>
<li><b>Detail</b> — lifts fine detail;</li>
<li><b>Emboss</b> — turns the picture into a grey relief, as if pressed into metal;</li>
<li><b>Find Edges</b> — traces the outlines on a dark ground, like a pen drawing;</li>
<li><b>Contour</b> — a lighter line-art effect.</li>
</ul>
<div class="imgrow">
{fig(IM.get('filter_edges'), 'Find Edges')}
{fig(IM.get('filter_emboss'), 'Emboss')}
</div>""")]))

    parts.append(("Part III", "Adjustments and Filters", ch))

    # ============================================================ PART IV
    ch = []
    ch.append(("Layers",
      "<p class='lede'>Layers are sheets of picture stacked one above another. Paint on one without "
      "disturbing the rest, slide a layer’s opacity, and choose how it blends with those below. The Layers "
      "panel on the right runs the whole stack.</p>", [
      ("Why layers help", f"""
<p>Keeping parts of a picture on separate layers means you can change your mind. Put a caption on its own
layer and you can move or delete it without touching the photo. Put a colour wash on a layer above and you
can dial its strength down, or hide it, at any time.</p>
{fig(IM.get('layers_demo'), 'Two layers: a scene below and a translucent orange wash above, set to the Screen blend at 55% opacity.')}
{fig(IM.get('layers_dock'), 'The Layers panel runs the stack.')}"""),
      ("Creating and managing layers", f"""
{proc('add, duplicate and delete layers',
  'Click <b>＋</b> in the Layers panel (or <b>Layer ▸ New Layer</b>) for a new, transparent layer above the active one.',
  'Click <b>⧉</b> (or <b>Layer ▸ Duplicate Layer</b>) to copy the active layer.',
  'Click <b>🗑</b> (or <b>Layer ▸ Delete Layer</b>) to remove it — the last remaining layer cannot be deleted.',
  'Double-click a layer’s name to rename it.')}
{proc('restack layers',
  'Click the <b>↑</b> and <b>↓</b> buttons to move the active layer up or down the stack.',
  'A layer higher in the list sits in front of those below it.')}"""),
      ("Showing, hiding and the active layer", f"""
<p>The <b>tick box</b> beside each layer shows or hides it without deleting anything — handy for comparing a
before and after, or temporarily getting a layer out of the way. Click a layer in the list to make it the
<b>active</b> layer: that is the one every tool, adjustment and filter works on.</p>
{caution('A common surprise is painting and seeing nothing happen — because a different layer is active, or the active layer is hidden. Glance at the Layers panel to check which layer is selected and visible.')}"""),
      ("Opacity and blend modes", f"""
<p>Two controls at the top of the panel change how the active layer mixes with the layers beneath.</p>
<ul>
<li><b>Opacity</b> — from 100% (solid) down to 0% (invisible). Lower it to let what is below show through.</li>
<li><b>Blend</b> — how the layer’s colours combine with those below: <b>Multiply</b> darkens, <b>Screen</b>
lightens, <b>Overlay</b> boosts contrast, and <b>Darken</b>, <b>Lighten</b>, <b>Add</b> and <b>Difference</b>
give further effects.</li>
</ul>
{tip('A quick vignette or tint: add a layer, paint or fill it with colour, then try the <b>Multiply</b> or <b>Screen</b> blend and ease the opacity down until it looks right.')}"""),
      ("Overlays and textures", f"""
<p>Two commands on the <b>Image</b> menu drop a ready-made picture straight onto a <b>new layer</b> for you,
so you can blend it over your work without disturbing anything beneath. They are the quick way to add the
kind of finishing effect Serif's PhotoPlus called an <i>instant effect</i>.</p>
<p><b>Image ▸ Add Overlay…</b> adds an <b>overlay</b> — a light leak, a grunge or paper grain, a decorative
frame, a drift of bokeh. The overlay arrives on its own layer, scaled to cover the canvas, and is set to the
<b>Screen</b> blend at full strength by default so its bright marks glow over the picture while its dark areas
drop away. Both the dialog's <b>Browse</b> button (for any image on disk) and a <b>category + swatch grid</b>
reading your installed overlay library are offered.</p>
<div class="imgrow">
{fig(IM.get('ovtx_before'), 'Before: the plain scene.')}
{fig(IM.get('overlay_after'), 'After: a warm light-leak overlay dropped on a new layer at the Screen blend — the picture below is untouched.')}
</div>
{fig(dlg('Add Overlay'), 'The Add Overlay dialog: Browse for an image or click a swatch from your overlay library, then set a blend mode (Screen by default) and opacity.')}
{proc('add an overlay',
  'Choose <b>Image ▸ Add Overlay…</b>.',
  'Either click <b>Browse for an image…</b> and pick a file, or choose a <b>category</b> and click a <b>swatch</b> from your overlay library.',
  'Pick a <b>Blend</b> mode (<b>Screen</b> suits most light leaks and glows; try <b>Overlay</b> or <b>Multiply</b> for grunge and frames) and set the <b>Opacity</b>.',
  'Click <b>Add to new layer</b>. The overlay lands on its own layer, which you can then re-blend, fade, move or mask like any other.')}
<p><b>Image ▸ Place Texture…</b> works the same way over your <b>texture</b> library — paper, concrete, metal,
fabric, wood and so on — but places the texture to <b>cover</b> the whole canvas at <b>Normal</b> / 100% so
that you choose how to blend it. Set it to <b>Multiply</b> to let a grain or weave sink into the picture, or
add a mask to show the texture only where you want it.</p>
<div class="imgrow">
{fig(IM.get('texture_swatch'), 'A texture tile — here a simple woven weave.')}
{fig(IM.get('texture_after'), 'The same texture placed on a new layer and set to Multiply, so the weave grain sinks into the scene.')}
</div>
{fig(dlg('Place Texture'), 'The Place Texture dialog: the same browse-or-swatch picker over your texture library, placed Normal / 100% to cover the canvas.')}
{proc('place a texture',
  'Choose <b>Image ▸ Place Texture…</b>.',
  'Browse for an image, or choose a category and click a swatch from your texture library.',
  'Click <b>Add to new layer</b> — the texture covers the canvas on a new layer at Normal / 100%.',
  'Now blend it: set the layer’s <b>blend</b> to <b>Multiply</b> or <b>Overlay</b> and ease the opacity down, or add a <b>mask</b> to reveal the texture only in places.')}
{note('The overlay and texture libraries live outside the app, at <code>~/.local/share/justapps/overlays</code> and <code>~/.local/share/justapps/textures</code>, and are read live — nothing is copied in. If a library is not installed, the dialog still offers <b>Browse</b> so you can use your own images.')}"""),
      ("Frames and edges", f"""
<p>A <b>frame</b> or <b>edge</b> is the classic photographic finish — a torn, distressed, film-strip, darkroom
or vignette border laid <i>around</i> the picture, so the photo shows through a clear centre. <b>Image ▸ Add
Frame / Edge…</b> does exactly that: it drops a decorative edge onto a <b>new layer</b> over your photo,
non-destructively.</p>
<p>A frame is a transparent PNG whose middle is clear and whose border is the artwork. It arrives at the
<b>Normal</b> blend and full opacity, cover-fitted to the canvas, so the opaque border sits over the edges of
your picture while the clear centre reveals the image straight through. Because it is just another layer, you
can afterwards <b>reposition</b> or <b>scale</b> it, ease its <b>opacity</b>, or <b>mask</b> it — all without
touching the photo beneath.</p>
<div class="imgrow">
{fig(IM.get('frame_swatch'), 'A frame swatch — an artistic torn edge. The chequered middle is transparent; only the border carries ink.')}
{fig(IM.get('frame_after'), 'The same frame dropped on a new layer over a photo: the ragged border frames the picture, which shows through the clear centre.')}
</div>
{fig(dlg('Add Frame / Edge'), 'The Add Frame / Edge picker: Browse for an image, or choose a category and click a swatch from your installed frame library. Frames are laid at Normal / 100%.')}
{proc('add a frame or edge',
  'Choose <b>Image ▸ Add Frame / Edge…</b>.',
  'Either click <b>Browse for an image…</b> and pick a frame PNG, or choose a <b>category</b> and click a <b>swatch</b> from your frame library.',
  'Click <b>Add to new layer</b>. The frame lands on its own layer at Normal / 100%, framing the photo through its clear centre.',
  'Fine-tune if you like: move or resize the frame layer, lower its <b>opacity</b> for a softer edge, or mask parts of it away.')}
{note('The frame / edge library is your own installed collection, read live from <code>~/.local/share/justapps/frames</code>. It is deeply nested — sets such as <i>Extreme Edges / Vol. 1 Artistic Edges</i> — and the picker lists each folder of frames as its own category. If the library is not installed, the dialog still offers <b>Browse</b> so you can use any transparent-centre PNG of your own.')}"""),
      ("Merging and flattening", f"""
<p><b>Layer ▸ Merge Down</b> (or the <b>⌄</b> button) fuses the active layer into the one below, baking in its
opacity and blend. Merge when you are happy with a combination and want to simplify the stack.</p>
{note('Saving a picture flattens every layer into the single image the file holds. Keep a layered master as a PNG only if you will re-edit — remembering that even a PNG stores just the flattened result, not the separate layers. Merge deliberately while the layers are still live.')}"""),
      ("Layer masks", f"""
<p>A <b>layer mask</b> hides parts of a layer <i>without erasing them</i>. Instead of rubbing pixels out with
the eraser — which is permanent — a mask is a separate greyscale picture attached to the layer: where the
mask is <b>white</b> the layer shows in full; where it is <b>black</b> the layer is hidden; greys in between
make it partly see-through. Paint the mask and the layer fades in and out; paint it white again and the
pixels come straight back. It is the non-destructive way to blend two layers, feather an edge, or try a
composite you can always undo.</p>
<div class="imgrow">
{fig(IM.get('mask_swatch'), 'A mask: white reveals, black hides.')}
{fig(IM.get('mask_demo'), 'The orange layer with that mask applied — the black wedge of the mask hides that corner, letting the scene below show through.')}
</div>
<p>The mask controls live at the foot of the <b>Layers</b> panel: an <b>Add Mask</b> / <b>From Selection</b> /
<b>Delete Mask</b> row, a small mask thumbnail, and an <b>Edit mask</b> tick box. The same commands are on the
<b>Layer</b> menu.</p>
{proc('mask part of a layer away',
  'Select the layer in the <b>Layers</b> panel.',
  'Click <b>Add Mask</b> (or <b>Layer ▸ Add Layer Mask</b>). A white, reveal-everything mask is attached and <b>Edit mask</b> switches on.',
  'With <b>Edit mask</b> ticked, paint on the picture: the <b>Brush</b> paints the mask in the current colour’s shade (paint with <b>black</b> to hide, grey to half-hide), and the <b>Eraser</b> paints it white to reveal again.',
  'Untick <b>Edit mask</b> to go back to painting the layer’s pixels as normal.')}
{proc('mask a layer to a selection',
  'Make a selection — a marquee, or the Magic Wand around the part you want to keep.',
  'Click <b>From Selection</b> (or <b>Layer ▸ Add Mask From Selection</b>).',
  'The layer is masked to the selection: the selected area stays visible, everything else is hidden — the quick way to drop a cut-out subject onto the layers below.')}
{note('<b>Layer ▸ Apply Mask</b> bakes the mask into the layer for good (hidden areas become transparent), then removes it. <b>Delete Mask</b> (or the panel button) simply throws the mask away and brings the whole layer back. Saving or merging also bakes masks in — the file holds the flattened, masked result.')}
{tip('A soft mask is the classic way to blend two photos: put one above the other, add a mask, and paint a soft black-to-white gradient across the join so one fades smoothly into the other.')}""")]))

    ch.append(("Cutting Out a Background",
      "<p class='lede'>Removing a background to transparency — so a subject can sit on another picture, a "
      "coloured panel, or a web page — is one of the most-wanted jobs in any image editor. PAINTcanvas does "
      "it with the Cutout tool and Cutout Studio.</p>", [
      ("How cutout works", f"""
<p>A cutout replaces background pixels with <b>transparency</b> — nothing at all, shown as a checkerboard.
PAINTcanvas works by colour: you point at the background, and it erases the connected run of similar-coloured
pixels, stopping where the colour changes sharply — at the edge of your subject.</p>
<div class="imgrow">
{fig(IM.get('cutout_before'), 'Before: a subject on a flat blue background.')}
{fig(IM.get('cutout_after'), 'After: the background erased to transparency (the checkerboard is “nothing here”).')}
</div>
{note('Cutout works best when the background is a fairly even colour clearly different from the subject. A busy or similar-coloured background needs more clicks, a higher tolerance, or some hand-painting with the eraser.')}"""),
      ("The Cutout tool", f"""
{proc('erase a background by clicking',
  'Choose the <b>Cutout</b> tool from the foot of the tool palette.',
  'Click a patch of background. The connected area of that colour is erased to transparency.',
  'Click any remaining patches of background to clear them too.',
  'If it eats into your subject, undo (' + K('Ctrl') + '+' + K('Z') + ') and lower the tolerance in Cutout Studio first.')}"""),
      ("Cutout Studio", f"""
<p><b>Image ▸ Cutout Studio…</b> opens a small panel that controls the Cutout tool and offers a one-click
auto-remove.</p>
{fig(dlg('Cutout Studio'), 'Cutout Studio: a tolerance slider, plus a one-click “remove background from the edges”.')}
{proc('remove a background with Cutout Studio',
  'Choose <b>Image ▸ Cutout Studio…</b>. It picks the Cutout tool for you, adding transparency to the picture if it had none.',
  'Set the <b>Tolerance</b>: higher catches more shades of the background in one click; lower protects the fine edges of your subject.',
  'Click the background in the picture to erase it, patch by patch, or',
  'click <b>Remove background from the edges now</b> to clear in one go whatever colour touches the four edges of the picture.',
  'Close the Studio when the subject stands alone on transparency.')}
{tip('Save a cutout as a <b>PNG</b> to keep the transparency. Saved as JPEG, the see-through areas fill with white.')}"""),
      ("Tidying the edges", """
<p>After an automatic cutout a few stray pixels often cling to the subject, or a thin halo of the old
background remains. Switch to the <b>Eraser</b>, zoom in, set a small size, and clean them off by hand.
For a background that is too varied for one tolerance, raise the tolerance and click each distinct region in
turn, or paint the awkward parts away with the eraser.</p>""")]))

    ch.append(("Smart Mask — cutting out tricky subjects",
      "<p class='lede'>The Cutout tool works by colour, so it struggles with a busy background or wispy "
      "edges like hair and foliage. <b>Smart Mask</b> takes a different approach, borrowed from Vertus "
      "Fluid&nbsp;Mask: you simply scribble on what to keep and what to remove, and an edge-aware "
      "engine separates the subject from the background for you.</p>", [
      ("How Smart Mask works", f"""
<p>You paint two kinds of rough scribble over the picture — <b>green KEEP</b> strokes over the subject and
<b>red REMOVE</b> strokes over the background. You do not have to be neat or trace the edge; a few strokes in
each area are enough. When you press <b>Apply</b>, the engine studies the colours and edges around your
scribbles and works out the precise boundary for itself.</p>
<div class="imgrow">
{fig(IM.get('smartmask_before'), 'Scribbles only: green KEEP on the subject, red REMOVE on the background — rough strokes, not a traced edge.')}
{fig(IM.get('smartmask_after'), 'The result: the subject cut out cleanly onto transparency (the checkerboard is “nothing here”).')}
</div>
{note('Smart Mask uses OpenCV’s grabCut for the sharpest, Fluid-Mask-grade edges, and the installer adds OpenCV automatically. If it is not present the tool falls back to a built-in NumPy colour model — a little softer on cluttered backgrounds, but it needs nothing extra and always works.')}"""),
      ("Painting the scribbles", f"""
{proc('mark your subject and background',
  'Choose the <b>Smart Mask</b> tool (the ✎ at the foot of the tool palette).',
  'Left-drag <b>over the subject</b> to paint green <b>KEEP</b> scribbles — a stroke or two through the middle is plenty.',
  'Right-drag <b>over the background</b> (or switch the top toolbar to <b>Paint REMOVE</b> and left-drag) to paint red <b>REMOVE</b> scribbles.',
  'Use the <b>size</b> box on the toolbar for a fatter or finer scribble brush, and <b>Clear scribbles</b> to start over.')}
{tip('Scribbles float <i>above</i> the picture — they never paint on it. Add a few strokes in any area the first Apply got wrong, then Apply again; the engine refines the result from the extra guidance.')}"""),
      ("Applying — selection or cut-out", f"""
<p>Press <b>Apply…</b> on the toolbar (or choose <b>Image ▸ Smart Mask (cut out subject)…</b>) to open the
dialog and turn your scribbles into a mask.</p>
{fig(dlg('Smart Mask — cut out subject'), 'The Smart Mask dialog: an edge-feather slider, and a choice of what to do with the result.')}
{proc('cut out a subject with Smart Mask',
  'Scribble KEEP over the subject and REMOVE over the background, then click <b>Apply…</b>.',
  'Set the <b>Edge feather</b> — a few pixels softens the boundary for hair or fuzzy edges; leave it at zero for a crisp cut.',
  'Tick <b>Set the subject as the selection</b> to make the subject the active selection, so every adjustment, filter and the Crop command then affect only the subject.',
  'Tick <b>Cut the subject out to a new layer</b> to copy the subject onto its own transparent layer, leaving the original untouched.',
  'Click <b>Apply</b>. You can undo (' + K('Ctrl') + '+' + K('Z') + ') and try again with more scribbles at any time.')}
{note('“Set as selection” and “Cut out to a new layer” are independent — tick either, both, or neither. The cut-out is non-destructive: the subject lands on a new layer called <b>Cut-out</b> and your original layers are left as they were.')}"""),
      ("Feathering tricky edges", f"""
<p>Hair, fur and foliage never have a hard edge, so a razor-sharp mask around them looks cut out with
scissors. The <b>Edge feather</b> slider blurs the mask boundary by a few pixels, fading the subject into
whatever you place behind it — the difference between an obvious paste-up and a believable composite.</p>
{tip('Feather little and often: 1–3&nbsp;px suits most portraits. Too much feather eats into solid edges, so raise it only where the subject is genuinely soft.')}""")]))

    ch.append(("Effects",
      "<p class='lede'>The finishing touches: a soft drop shadow or outer glow behind everything you have "
      "drawn to lift a logo or cut-out subject off the page, and a photographic lens flare dropped over the "
      "whole picture.</p>", [
      ("Drop Shadow", f"""
<p>A <b>drop shadow</b> casts a soft, offset shadow of the drawing’s opaque pixels behind them, giving a
sense of depth.</p>
{fig(dlg('Drop Shadow'), 'The Drop Shadow dialog: offset across and down, blur, strength and colour.')}
{proc('add a drop shadow',
  'Choose <b>Effects ▸ Drop Shadow…</b>.',
  'Set the <b>Offset across</b> and <b>down</b> — how far the shadow falls.',
  'Set the <b>Blur</b> for a soft or crisp edge, the <b>Strength</b> for how dark it is, and a <b>Colour</b> (black is usual).',
  'Click <b>OK</b>.')}
{fig(IM.get('effects'), 'A shape with a soft drop shadow applied.')}"""),
      ("Outer Glow", f"""
<p>An <b>outer glow</b> surrounds the drawing with a soft halo of colour — good for a highlight, a sticker
edge, or making a subject pop against a dark background.</p>
{fig(dlg('Outer Glow'), 'The Outer Glow dialog: blur, strength and colour.')}
{proc('add an outer glow',
  'Choose <b>Effects ▸ Outer Glow…</b>.',
  'Set the <b>Blur</b> (how far the glow spreads), the <b>Strength</b> and a <b>Colour</b>.',
  'Click <b>OK</b>.')}"""),
      ("Lens flare", f"""
<p>A <b>lens flare</b> drops a bright light source into the picture — the glowing core, radiating star
spikes, a chain of hexagonal and circular lens reflections streaming across the frame, an optional rainbow
diffraction ring and a soft halo — the kind of sunlight-in-the-lens look you see in photographs and films.
It lives on <b>Image ▸ Lens Flare…</b> and is applied on its own layer, so the picture underneath is never
altered.</p>
{fig(dlg('Lens Flare'), 'The Lens Flare studio: a live preview of your picture with the flare on top, a draggable light marker, a preset menu, and brightness / size / hue / warmth sliders with element toggles.')}
<p>The dialog shows a <b>live preview</b> of your picture with the flare composited over it. Drag the
crosshair to place the light source, or type positions into the <b>Light X</b> / <b>Light Y</b> sliders.</p>
{proc('add a lens flare',
  'Choose <b>Image ▸ Lens Flare…</b>.',
  'Pick a <b>Preset</b> to start — <b>Subtle</b> for a gentle glint, <b>Sunny</b> for a warm daylight flare, <b>Anamorphic</b> for the wide blue streak of a cinema lens, or <b>Sci-fi</b> for a bright, busy spread.',
  'Drag the crosshair on the preview to place the light (the upper third of the frame usually looks most natural).',
  'Tune <b>Brightness</b> and <b>Size</b>, and shift the <b>Hue</b> and <b>Warmth</b> to match the light in your photo.',
  'Turn individual elements on or off — <b>Star spikes</b>, <b>Reflections</b>, <b>Rainbow ring</b>, <b>Halo</b> and the <b>Anamorphic streak</b>.',
  'Click <b>Add flare layer</b>.')}
{fig(IM.get('flare_before'), 'Before: a plain dusk scene.')}
{fig(IM.get('flare_after'), 'After: a warm Sunny flare, placed upper-right, on its own Screen layer — the scene below is untouched.')}
{note('The flare arrives on a new layer set to the <b>Screen</b> blend, so only its bright parts show and the picture beneath stays intact. Lower that layer’s <b>Opacity</b> in the Layers panel to dial the whole effect back, or hide and delete the layer to remove it.')}"""),
      ("Working on transparency", f"""
{caution('The drop shadow and outer glow show <i>through</i> transparent areas, so they only look right on a layer that has transparency around the artwork. Start from <b>File ▸ New</b> with a <b>Transparent background</b>, or cut the backdrop away first — otherwise the shadow or glow has nowhere to show. (The lens flare is different: it floats over whatever is beneath it, so it works on any picture.)')}
<p>So the natural workflow is: make or cut out a subject on transparency, then apply the shadow or glow, then
place the result on its new background.</p>""")]))

    parts.append(("Part IV", "Layers, Cutouts and Effects", ch))

    # ============================================================ PART V
    ch = []
    ch.append(("Resizing, Cropping and Rotating",
      "<p class='lede'>The Image menu changes the picture as a whole: its pixel dimensions, its canvas, "
      "its orientation. These are the housekeeping jobs you do before output.</p>", [
      ("Resize Image vs. Canvas Size", f"""
<p>Two commands sound alike but do opposite things.</p>
{proc('resize the whole picture',
  'Choose <b>Image ▸ Resize Image…</b>.',
  'Type a new <b>width</b>; the height is suggested to keep the proportions.',
  'Type the <b>height</b> and confirm. Every pixel — and every layer — is scaled to the new size.')}
{proc('change the canvas without scaling',
  'Choose <b>Image ▸ Canvas Size…</b>.',
  'Type a new <b>width</b> and <b>height</b>.',
  'The picture keeps its pixels at their current size; the canvas grows (adding transparent margin) or shrinks (cropping) around them.')}
{note('<b>Resize Image</b> makes the picture itself bigger or smaller. <b>Canvas Size</b> changes the area you have to work on, leaving the existing pixels untouched — use it to add room around a subject.')}"""),
      ("Cropping to a selection", f"""
{proc('crop to a selection',
  'Choose a marquee tool and drag out the area you want to keep.',
  'Choose <b>Image ▸ Crop to Selection</b>.',
  'The picture is trimmed to the selection’s bounds, across every layer.')}"""),
      ("Rotating and flipping", f"""
<p>The Image menu turns and mirrors the whole picture:</p>
<ul>
<li><b>Rotate 90° Right / Left</b> and <b>Rotate 180°</b> — quarter and half turns, for a photo shot sideways;</li>
<li><b>Flip Horizontal</b> and <b>Flip Vertical</b> — mirror the picture.</li>
</ul>"""),
      ("Straightening", f"""
<p><b>Image ▸ Straighten…</b> rotates by a small angle and crops back to the original size — the fix for a
tilted horizon.</p>
{proc('straighten a crooked photo',
  'Choose <b>Image ▸ Straighten…</b>.',
  'Enter a small angle (between −45° and 45°).',
  'The picture rotates by that amount and is trimmed to fill the original frame, so no transparent corners are left.')}""")]))

    ch.append(("Worked Project — Retouch and Share a Photo",
      "<p class='lede'>A complete pass over a photograph, from import to a finished JPEG, using the skills "
      "from the earlier chapters in the order you would really use them.</p>", [
      ("1 · Open and straighten", f"""
{proc('start the project',
  'Choose <b>File ▸ Open…</b> and load the photo.',
  'If the horizon is tilted, use <b>Image ▸ Straighten…</b> with a degree or two.',
  'Crop in if you like: drag a rectangle marquee and choose <b>Image ▸ Crop to Selection</b>.')}"""),
      ("2 · Correct the tone and colour", f"""
{proc('fix exposure and colour',
  'Try <b>Adjust ▸ Auto Contrast</b> first — it fixes many photos instantly.',
  'If it needs more, open <b>Adjust ▸ Levels…</b> and pull the black and white points to the edges of the tonal range.',
  'Warm or cool the picture with <b>Adjust ▸ Colour Temperature…</b>, and lift the colour with <b>Hue / Saturation…</b> if it looks flat.')}
{fig(IM.get('adjust_after'), 'After tone and colour correction — warmer and with more contrast.')}"""),
      ("3 · Retouch and sharpen", f"""
{proc('clean up and finish',
  'Remove any blemish or stray object with the <b>Clone</b> tool (Ctrl-click a clean source, then paint).',
  'Fix any red-eye with the <b>Red-eye</b> tool.',
  'Finish with <b>Filter ▸ Unsharp Mask…</b> for a crisp result — a small radius is usually enough.')}"""),
      ("4 · Save and share", f"""
{proc('export the finished photo',
  'Choose <b>File ▸ Save As…</b>.',
  'Pick <b>JPEG</b> for a small, shareable file (fine for a photo with no transparency).',
  'Keep a <b>PNG</b> master too if you might re-edit — it loses no quality.')}
{tip('Need the photo in a newsletter or on a web page? Save it, then open PAGEdesigner or WEBcreator — it is waiting in your shared <i>Pictures/just a…</i> folder and your recent files.')}""")]))

    ch.append(("Worked Project — A Cut-Out Logo on Transparency",
      "<p class='lede'>Building a reusable graphic with a transparent background and a soft shadow — the "
      "kind of asset you drop onto a page, a banner or a slide.</p>", [
      ("1 · Start transparent", f"""
{proc('begin on a clear canvas',
  'Choose <b>File ▸ New…</b>, pick a size, and tick <b>Transparent background</b>.',
  'The canvas opens as a checkerboard — nothing but transparency.')}"""),
      ("2 · Paint the mark", f"""
{proc('draw the artwork',
  'Use the <b>Brush</b>, the shape tools and the <b>Fill</b> bucket to build your mark.',
  'Work on one or more <b>layers</b> so parts stay independent.',
  'Add a line of <b>Text</b> if the logo needs a word.')}"""),
      ("3 · (Or) cut a subject out of a photo", f"""
{proc('reuse a photographed object instead',
  'Open a photo of the object on a plain background.',
  'Open <b>Image ▸ Cutout Studio…</b>, set a tolerance and click the background — or use <b>Remove background from the edges</b>.',
  'Tidy the edges with the <b>Eraser</b> at a small size.')}"""),
      ("4 · Add a shadow and save", f"""
{proc('finish and save',
  'Choose <b>Effects ▸ Drop Shadow…</b> (or <b>Outer Glow…</b>) — because the surround is transparent, it shows correctly.',
  'Save as a <b>PNG</b> to keep the transparency.',
  'Drop the PNG into PAGEdesigner, WEBcreator or DRAWmaster; the clear areas let whatever is behind show through.')}
{fig(IM.get('effects'), 'A finished mark on transparency with a soft drop shadow.')}""")]))

    parts.append(("Part V", "Image-Wide Edits and Projects", ch))

    # ============================================================ PART VI — reference
    ch = []
    ch.append(("Appendix A — Menu Reference", "<p class='lede'>Every menu and what each command does.</p>", [
      ("File and Edit", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>File ▸ New…</td><td>Start a new picture — size preset, background colour or transparent</td></tr>
<tr><td>File ▸ Open…</td><td>Open a PNG, JPEG, BMP, GIF or WebP</td></tr>
<tr><td>File ▸ Save / Save As…</td><td>Save as PNG (keeps transparency) or JPEG</td></tr>
<tr><td>File ▸ Export…</td><td>Export as PNG / JPEG / WEBP / GIF / BMP with a quality slider and transparency toggle</td></tr>
<tr><td>File ▸ Quit</td><td>Close the program</td></tr>
<tr><td>Edit ▸ Undo / Redo</td><td>Step back and forward through recent changes</td></tr></table>"""),
      ("Image", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Resize Image…</td><td>Scale the whole picture to new pixel dimensions</td></tr>
<tr><td>Canvas Size…</td><td>Change the canvas area without scaling the pixels</td></tr>
<tr><td>Crop to Selection</td><td>Trim the picture to the current marquee</td></tr>
<tr><td>Straighten…</td><td>Rotate by a small angle and crop back to size</td></tr>
<tr><td>Rotate 90° Right / Left · 180°</td><td>Quarter and half turns</td></tr>
<tr><td>Flip Horizontal / Vertical</td><td>Mirror the picture</td></tr>
<tr><td>Cutout Studio…</td><td>Remove a background to transparency</td></tr></table>"""),
      ("Adjust", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Brightness / Contrast…</td><td>The everyday exposure and punch fix</td></tr>
<tr><td>Levels…</td><td>Set black point, white point and mid-tone gamma</td></tr>
<tr><td>Hue / Saturation…</td><td>Shift colours round the wheel; change vividness</td></tr>
<tr><td>Colour Temperature…</td><td>Warm (orange) ↔ cool (blue)</td></tr>
<tr><td>Colour Balance…</td><td>Cyan–red, magenta–green, yellow–blue shifts</td></tr>
<tr><td>Threshold…</td><td>Reduce to pure black and white at a level</td></tr>
<tr><td>Posterize…</td><td>Cut colour to a few banded levels</td></tr>
<tr><td>Auto Contrast · Equalize</td><td>Automatic tonal fixes</td></tr>
<tr><td>Greyscale · Invert · Sepia</td><td>One-click colour transforms</td></tr></table>"""),
      ("Filter, Select, Layer and Effects", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Filter ▸ Gaussian Blur…</td><td>Soften by a radius</td></tr>
<tr><td>Filter ▸ Unsharp Mask…</td><td>Sharpen by increasing edge contrast</td></tr>
<tr><td>Filter ▸ Median (Despeckle)…</td><td>Remove noise and speckle</td></tr>
<tr><td>Filter ▸ Sharpen · Soften · Detail</td><td>One-click texture tweaks</td></tr>
<tr><td>Filter ▸ Emboss · Find Edges · Contour</td><td>Artistic / line-art effects</td></tr>
<tr><td>Select ▸ Select All · Deselect</td><td>Select the whole picture; clear the selection</td></tr>
<tr><td>Layer ▸ New · Duplicate · Merge Down · Delete</td><td>Manage the layer stack</td></tr>
<tr><td>Layer ▸ Add Layer Mask · From Selection · Apply · Delete Mask</td><td>Attach, apply or remove a non-destructive layer mask</td></tr>
<tr><td>Effects ▸ Drop Shadow… · Outer Glow…</td><td>A soft shadow or halo behind the artwork</td></tr></table>""")]))

    ch.append(("Appendix B — Keyboard Shortcuts", "<p class='lede'>The shortcuts worth learning.</p>", [
      ("Files and editing", f"""<table class="ref"><tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>New / Open / Save / Save As</td><td>{K('Ctrl')}+{K('N')} · {K('Ctrl')}+{K('O')} · {K('Ctrl')}+{K('S')} · {K('Ctrl')}+{K('Shift')}+{K('S')}</td></tr>
<tr><td>Export…</td><td>{K('Ctrl')}+{K('Shift')}+{K('E')}</td></tr>
<tr><td>Undo / Redo</td><td>{K('Ctrl')}+{K('Z')} · {K('Ctrl')}+{K('Shift')}+{K('Z')}</td></tr>
<tr><td>Quit</td><td>{K('Ctrl')}+{K('Q')}</td></tr></table>"""),
      ("Selecting and the clone source", f"""<table class="ref"><tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>Select All</td><td>{K('Ctrl')}+{K('A')}</td></tr>
<tr><td>Deselect</td><td>{K('Ctrl')}+{K('D')}</td></tr>
<tr><td>Set the clone source</td><td>{K('Ctrl')}+click with the Clone tool</td></tr></table>""")]))

    ch.append(("Appendix C — Tool Reference", "<p class='lede'>Every tool on the palette at a glance.</p>", [
      ("The tool palette", f"""
{fig(IM.get('toolpalette'), 'The tool palette.', 'tall')}
<table class="ref"><tr><th>Tool</th><th>Use</th></tr>
<tr><td>Brush</td><td>Paint a freehand stroke in the current colour</td></tr>
<tr><td>Eraser</td><td>Remove pixels (to transparency on a clear layer)</td></tr>
<tr><td>Line</td><td>Draw a straight line</td></tr>
<tr><td>Rectangle / Ellipse</td><td>Draw an outlined shape</td></tr>
<tr><td>Fill</td><td>Flood a connected area of one colour</td></tr>
<tr><td>Gradient</td><td>Drag a fade from the current colour to transparent</td></tr>
<tr><td>Pick colour</td><td>Eyedropper — take a colour from the picture</td></tr>
<tr><td>Text</td><td>Stamp a line of text into the pixels</td></tr>
<tr><td>Clone</td><td>Copy pixels from a source (Ctrl-click) to where you paint</td></tr>
<tr><td>Red-eye</td><td>Darken flash-reddened pupils</td></tr>
<tr><td>Dodge / Burn</td><td>Lighten / darken by brushing</td></tr>
<tr><td>Select — rectangle / ellipse</td><td>Marquee off an area for the next edit</td></tr>
<tr><td>Cutout</td><td>Click a background to erase it to transparency</td></tr></table>""")]))

    ch.append(("Appendix D — Glossary", "<p class='lede'>The image-editing words used in this guide.</p>", [
      ("A–Z", """<dl class="gloss">
<dt>Alpha / transparency</dt><dd>A pixel’s see-through-ness. Fully transparent pixels show as a checkerboard and let whatever is behind show through.</dd>
<dt>Blend mode</dt><dd>The rule for how a layer’s colours combine with those below — Multiply, Screen, Overlay and so on.</dd>
<dt>Canvas</dt><dd>The working area your picture occupies, measured in pixels.</dd>
<dt>Clone</dt><dd>Painting with pixels copied from another part of the picture.</dd>
<dt>Cutout</dt><dd>Removing a background to transparency, isolating a subject.</dd>
<dt>Flatten</dt><dd>Merging all layers into one image — what happens when you save.</dd>
<dt>Gamma</dt><dd>The mid-tone brightness control in Levels.</dd>
<dt>Gradient</dt><dd>A smooth fade between two colours (or from a colour to transparent) across an area.</dd>
<dt>Layer</dt><dd>One sheet of a stacked picture, editable on its own.</dd>
<dt>Layer mask</dt><dd>A greyscale picture attached to a layer that hides it (black) or reveals it (white) without erasing any pixels.</dd>
<dt>Marquee</dt><dd>A selection outline — the “marching ants”.</dd>
<dt>Opacity</dt><dd>How solid a layer or stroke is, from 100% to 0%.</dd>
<dt>Pixel</dt><dd>One coloured dot; the atom of a raster picture.</dd>
<dt>Posterize</dt><dd>Reducing colour to a few banded levels.</dd>
<dt>Raster / bitmap</dt><dd>A picture made of a grid of pixels.</dd>
<dt>Threshold</dt><dd>Forcing every pixel to pure black or white at a chosen level.</dd>
<dt>Tolerance</dt><dd>How wide a range of colours a fill or cutout treats as “the same”.</dd>
<dt>Unsharp mask</dt><dd>A sharpening filter that increases edge contrast.</dd>
</dl>""")]))

    ch.append(("Appendix E — Troubleshooting", "<p class='lede'>Quick answers to common snags.</p>", [
      ("Common questions", """<dl class="gloss">
<dt>I paint but nothing appears.</dt><dd>A different layer is probably active, or the active layer is hidden. Check the Layers panel — click the layer you mean to paint on and make sure its tick box is on.</dd>
<dt>An adjustment or filter only changed part of the picture.</dt><dd>You have a selection active. Choose <b>Select ▸ Deselect</b> (Ctrl+D) and try again.</dd>
<dt>The Fill bucket leaves specks or stops too soon.</dt><dd>Fill matches an exact colour; a “flat” photo area is really many near-colours. Posterize or threshold it first, or paint by hand.</dd>
<dt>My cutout ate into the subject.</dt><dd>The tolerance is too high. Undo, lower the tolerance in Cutout Studio, and click again.</dd>
<dt>The transparent areas went white when I saved.</dt><dd>You saved as JPEG, which has no transparency. Save as PNG to keep it.</dd>
<dt>The drop shadow or glow doesn’t show.</dt><dd>The effect shows through transparency only. Start from a transparent background, or cut the backdrop away first.</dd>
<dt>The Adjust and Filter menus say they need libraries.</dt><dd>They use Pillow and NumPy. Install them with your package manager (e.g. <code>sudo pacman -S python-pillow python-numpy</code>); painting and layers work without them.</dd>
</dl>""")]))

    parts.append(("Part VI", "Reference", ch))
    return parts


# ----------------------------------------------------------------- quickstart
def quickstart_sections(IM):
    def f(k, cap):
        return fig(IM.get(k), cap)
    S = []
    S.append(("Welcome to PAINTcanvas", f"""
<p class="lede">PAINTcanvas is a <b>raster image editor</b>: you paint, retouch and adjust pictures made of
pixels, then save a PNG or JPEG. It works the way Serif's <b>PhotoPlus</b> did — paint, correct, filter,
layer and cut out.</p>
<p>This Quick Start takes you from a blank canvas to a finished, cut-out graphic in a dozen short steps. For
the complete reference — every tool, worked projects and a full menu guide — open the <b>User Guide</b>
(Help ▸ User Guide).</p>
{f('scene', 'A picture open in PAINTcanvas — a grid of pixels you can paint over, adjust and filter.')}"""))
    S.append(("Start a picture", f"""
<p>Choose <b>File ▸ New…</b> and pick a size — or tick <b>Transparent background</b> for a logo or cut-out.
Or <b>File ▸ Open…</b> an existing photo.</p>
{f('workspace', 'The workspace: tools on the left, the paint toolbar on top, Layers on the right.')}"""))
    S.append(("Meet the tools", f"""
<p>The vertical <b>tool palette</b> holds every tool — brush, eraser, shapes, fill, gradient, the
eyedropper, text, clone, red-eye, dodge and burn, the selection marquees, and the Cutout tool.</p>
{fig(IM.get('toolpalette'), 'The tool palette, top to bottom.', 'tall')}"""))
    S.append(("Paint and draw", f"""
<p>Set a <b>Colour</b> and <b>Size</b> on the paint toolbar, then draw: the <b>Brush</b> for freehand
strokes, the <b>Line</b>, <b>Rectangle</b> and <b>Ellipse</b> for shapes, the <b>Fill</b> bucket for solid
areas, and the <b>Gradient</b> for a smooth fade.</p>
{f('shapes', 'A brush stroke, a line, outlined and filled shapes, and a gradient.')}"""))
    S.append(("Retouch", """
<p>Clean a photo up with the <b>Clone</b> stamp (Ctrl-click a source, then paint over the blemish), fix
flash eyes with <b>Red-eye</b>, and brush light or dark with <b>Dodge</b> and <b>Burn</b>.</p>"""))
    S.append(("Adjust colour and tone", f"""
<p>The <b>Adjust</b> menu corrects a picture: <b>Brightness / Contrast</b>, <b>Levels</b>, <b>Hue /
Saturation</b>, <b>Colour Temperature</b> and one-click <b>Auto Contrast</b>, <b>Greyscale</b> and
<b>Sepia</b>.</p>
{f('adjust_after', 'The sample scene after a warmer, higher-contrast adjustment.')}"""))
    S.append(("Apply a filter", f"""
<p>The <b>Filter</b> menu changes texture: <b>Gaussian Blur</b> to soften, <b>Unsharp Mask</b> to sharpen,
<b>Median</b> to despeckle, and artistic effects like <b>Find Edges</b> and <b>Emboss</b>.</p>
{f('filter_blur', 'A gentle Gaussian blur on the sample scene.')}"""))
    S.append(("Work in layers", f"""
<p>The <b>Layers</b> panel stacks sheets of picture. Add a layer, set its <b>opacity</b> and a <b>blend</b>
mode, and mix it with the layers below — all non-destructively.</p>
{f('layers_demo', 'Two layers: a scene with a translucent colour wash on Screen blend above.')}"""))
    S.append(("Select an area", """
<p>The rectangle and ellipse <b>marquee</b> tools fence off part of the picture, so the next adjustment or
filter affects only that area. <b>Ctrl+D</b> deselects when you are done.</p>"""))
    S.append(("Cut out a background", f"""
<p>Open <b>Image ▸ Cutout Studio…</b>, set a tolerance, and click the background with the <b>Cutout</b> tool
— or let it remove whatever touches the edges. The background becomes transparent.</p>
<div class="imgrow">
{fig(IM.get('cutout_before'), 'Before')}
{fig(IM.get('cutout_after'), 'After — the background erased to transparency.')}
</div>"""))
    S.append(("Add a finishing effect", f"""
<p>With your subject on transparency, add a soft <b>Effects ▸ Drop Shadow…</b> or <b>Outer Glow…</b> behind
it — the touch that lifts a logo or cut-out off the page.</p>
{f('effects', 'A shape with a soft drop shadow.')}"""))
    S.append(("Save and share", f"""
<p>Save with <b>File ▸ Save As…</b>: a <b>PNG</b> keeps transparency and loses no quality; a <b>JPEG</b> is
smaller, for photos to share. Your file lands in the shared <i>Pictures/just a…</i> folder, ready for the
other <i>just a…</i> apps.</p>"""))
    S.append(("Where to go next", """
<p>That is the whole round trip: new or open → paint and retouch → adjust and filter → layer, cut out and
finish → save. The <b>User Guide</b> covers every feature in depth, with worked projects and a full
reference. And the other <i>just a…</i> apps work alongside this one — a picture saved here is one click
away in PAGEdesigner, WEBcreator and DRAWmaster.</p>"""))
    return S


# ----------------------------------------------------------------- CSS
CSS = """
:root{ --ink:#232b31; --mute:#64737c; --line:#d7dee3; --accent:#2a7d6b; --accent2:#1d5c50;
  --paper:#ffffff; --band:#eef3f2; --warn:#b5651d; }
*{box-sizing:border-box} body{margin:0;background:#e8edf0;color:var(--ink);
  font:16px/1.62 "Noto Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.page{max-width:840px;margin:28px auto;background:var(--paper);padding:54px 62px;
  box-shadow:0 2px 20px -8px rgba(20,40,50,.35);border-radius:4px;}
h1{font-size:2.3rem;margin:.1em 0 .1em;letter-spacing:-.01em}
.lede{font-size:1.12rem;color:#374249}
p{max-width:68ch} ul,ol,dl{max-width:68ch} li{margin:.22em 0}
code{background:var(--band);padding:1px 5px;border-radius:4px;font-size:.92em}
kbd{display:inline-block;background:#f6f8f9;border:1px solid #c4ced4;border-bottom-width:2px;
  border-radius:5px;padding:0 6px;font:600 .82em/1.5 "Noto Sans",sans-serif;color:#2b3a42;white-space:nowrap}
figure.f{margin:1.3em auto;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--band);max-width:470px}
figure.f img{width:100%;display:block}
/* a transparent-picture figure shows a checkerboard behind it */
figure.f.alpha img{background:
  linear-gradient(45deg,#d7dade 25%,transparent 25%,transparent 75%,#d7dade 75%) 0 0/20px 20px,
  linear-gradient(45deg,#d7dade 25%,#fff 25%,#fff 75%,#d7dade 75%) 10px 10px/20px 20px,#fff}
/* the tool rail is a tall, thin strip: cap it by HEIGHT so it can't balloon down the page */
figure.f.tall{max-width:none;width:max-content;margin:1.2em auto}
figure.f.tall img{width:auto;max-height:430px}
figcaption{font-size:.85rem;color:var(--mute);padding:8px 12px;background:var(--band);border-top:1px solid var(--line)}
.fig-missing{color:#b24;font-size:.85rem;border:1px dashed #c99;padding:8px;border-radius:6px;margin:1em 0}
/* a row of small comparison figures */
.imgrow{display:flex;flex-wrap:wrap;gap:14px;margin:1.3em 0;align-items:flex-start}
.imgrow figure.f{margin:0;flex:1 1 180px;max-width:230px}
/* procedures */
.proc{background:#f7fbfa;border:1px solid #cfe2dd;border-left:4px solid var(--accent);
  border-radius:8px;padding:12px 18px 14px;margin:1.3em 0}
.proc-h{font-weight:700;color:var(--accent2);margin:.1em 0 .5em;max-width:none}
ol.steps{margin:.3em 0;padding-left:1.3em} ol.steps li{margin:.3em 0}
/* callouts */
.cal{border-radius:8px;padding:10px 14px 10px 14px;margin:1.1em 0;font-size:.97rem;max-width:68ch;position:relative}
.cal-k{display:inline-block;font-weight:700;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;
  margin-right:.6em;padding:1px 7px;border-radius:999px;vertical-align:1px}
.cal.note{background:#eef3f6;border:1px solid #cdd9e0}.cal.note .cal-k{background:#3a5566;color:#fff}
.cal.tip{background:#eef7f1;border:1px solid #c7e3d1}.cal.tip .cal-k{background:#2a7d4f;color:#fff}
.cal.caution{background:#fbf2e8;border:1px solid #e8d2b4}.cal.caution .cal-k{background:var(--warn);color:#fff}
/* reference tables */
table.ref{border-collapse:collapse;width:100%;max-width:68ch;margin:1em 0;font-size:.95rem}
table.ref th,table.ref td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
table.ref th{background:var(--band)}
dl.gloss dt{font-weight:700;margin-top:.7em;color:#17323a} dl.gloss dd{margin:.1em 0 .1em 1.3em;color:#374249}
/* catalogue grids */
.cat-card figure.f{margin:0;max-width:none}
/* back-of-book index */
.index{columns:2;gap:30px}
.idx-let{font-weight:800;color:var(--accent);font-size:1.1rem;margin:.7em 0 .15em;break-after:avoid}
ul.idx{list-style:none;padding:0;margin:0 0 .5em}
ul.idx li{margin:.12em 0;font-size:.92rem;break-inside:avoid;padding-left:1.1em;text-indent:-1.1em}
ul.idx a{color:var(--accent);text-decoration:none}
"""

COVER_CSS = """
.cover{min-height:980px;display:flex;align-items:center;justify-content:center;text-align:center;break-after:page;page-break-after:always}
.cv-inner{max-width:640px;padding:0 40px}
.cv-banner{width:100%;max-width:560px;margin:0 auto 12px;display:block;border-radius:8px}
.cv-kind{font-size:2.5rem;font-weight:800;color:var(--accent);letter-spacing:.01em;margin-top:.3em}
.cv-rule{height:3px;width:120px;background:var(--accent);margin:18px auto}
.cv-sub{color:var(--mute);font-size:1.08rem;max-width:48ch;margin:0 auto}
.cv-date{color:var(--mute);margin-top:2.4em;font-size:.95rem}
/* part divider */
.part{min-height:720px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;break-before:page;page-break-before:always;break-after:page;page-break-after:always}
.part .pn{color:var(--accent);font-size:1rem;letter-spacing:.3em;text-transform:uppercase;font-weight:700}
.part .pt{font-size:2.6rem;font-weight:800;margin:.25em 0;color:#17323a;max-width:none}
.part .prule{height:3px;width:90px;background:var(--accent);margin:14px auto}
"""

MANUAL_CSS = """
.contents{margin:1.3em 0 0}
.booktoc{list-style:none;padding:0;margin:0}
.booktoc .part-h{font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);
  font-weight:800;margin:1.1em 0 .3em;border-bottom:2px solid var(--line);padding-bottom:3px}
.booktoc .ch{margin:.35em 0;font-weight:600}.booktoc .ch>a{color:var(--ink);text-decoration:none}
.booktoc .n{color:var(--accent);margin-right:.5em;font-variant-numeric:tabular-nums}
.booktoc ul{list-style:none;padding:0 0 0 1.7em;margin:.15em 0 .4em;font-weight:400;font-size:.93rem;columns:2;gap:24px}
.booktoc ul li{margin:.08em 0;break-inside:avoid}.booktoc a:hover{color:var(--accent)}
.chapter{break-before:page;page-break-before:always;margin-top:1em}
.chrule{border-top:4px solid var(--accent);margin-bottom:.4em}
.chrule .cn{display:block;color:var(--accent);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;margin-top:.5em}
.chrule h2{border:0;margin:.05em 0 .35em;padding:0;font-size:2rem;max-width:none}
h3{font-size:1.2rem;margin:1.7em 0 .4em;color:#17323a;max-width:none}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:28px 34px;margin:0 0 .4em}
header.mast h1{margin:0;color:#fff}header.mast p{margin:.3em 0 0;color:#d7ece7;max-width:none}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none;padding:38px 46px}
  h3{break-after:avoid} figure.f{break-inside:avoid} .proc{break-inside:avoid} .cal{break-inside:avoid}
  table.ref{break-inside:auto} .cat-card{break-inside:avoid} .imgrow{break-inside:avoid} }
"""

QS_CSS = """
.toc{columns:2;gap:28px;margin:1em 0 0;padding:0;list-style:none}
.toc li{margin:.25em 0;break-inside:avoid}.toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--accent)}.toc .n{color:var(--accent);font-weight:700;margin-right:.5em}
h2{font-size:1.5rem;margin:2.2em 0 .5em;padding-top:.5em;border-top:3px solid var(--accent);max-width:none}
h2 .n{color:var(--accent);margin-right:.5em;font-weight:700}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:28px 34px}
header.mast h1{margin:0;color:#fff}header.mast p{margin:.3em 0 0;color:#d7ece7;max-width:none}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none} h2{break-after:avoid} figure.f{break-inside:avoid} .imgrow{break-inside:avoid} }
"""


def _banner_uri():
    p = OUT / "banner.png"
    if Image and p.exists():
        return datauri(Image.open(str(p)).convert("RGB"), 900)
    return ""


def cover(kind):
    uri = _banner_uri()
    top = f'<img class="cv-banner" src="{uri}" alt="">' if uri else '<div style="font-size:3rem;font-weight:800;color:var(--accent)">PAINTcanvas</div>'
    return (f'<section class="cover"><div class="cv-inner">{top}'
            f'<div class="cv-kind">{kind}</div><div class="cv-rule"></div>'
            f'<div class="cv-sub">just a&hellip; PAINTcanvas &mdash; a raster image editor in the spirit of Serif PhotoPlus</div>'
            f'<div class="cv-date">{date.today().strftime("%B %Y")}</div></div></section>')


# ----------------------------------------------------------------- assembly
def build_quickstart(IM):
    S = quickstart_sections(IM)
    toc = "".join(f'<li><span class="n">{i+1}</span><a href="#s{i+1}">{H.escape(t)}</a></li>'
                  for i, (t, _) in enumerate(S))
    body = "".join(f'<h2 id="s{i+1}"><span class="n">{i+1}</span>{H.escape(t)}</h2>\n{b}'
                   for i, (t, b) in enumerate(S))
    doc = f"""<!DOCTYPE html><html lang="en-GB"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… PAINTcanvas — Quick Start Guide</title>
<style>{CSS}{COVER_CSS}{QS_CSS}</style>
<div class="page">
{cover('Quick Start Guide')}
<header class="mast"><h1>PAINTcanvas — Quick Start</h1>
<p>From a blank canvas to a finished, cut-out graphic — in a dozen steps.</p></header>
<h2 style="border:0">Contents</h2><ol class="toc">{toc}</ol>
{body}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… PAINTcanvas Quick Start · generated {date.today().isoformat()} · every picture is produced by the app itself.
See <b>Help ▸ User Guide</b> for the full manual.</footer>
</div></html>"""
    (OUT / "quickstart.html").write_text(doc, encoding="utf-8")
    print("wrote quickstart.html:", len(doc) // 1024, "KiB,", len(S), "sections")


def build_index(numbered):
    """A back-of-book index: every section heading plus a curated term list, each
    linked to the chapter/section that covers it, grouped A–Z."""
    import re as _re
    from collections import defaultdict
    entries = {}
    secs = []
    for _pt, _pb, pc in numbered:
        for (n, title, intro, secitems) in pc:
            for si, (h, b) in enumerate(secitems, 1):
                anchor = f"c{n}s{si}"
                plain = _re.sub(r"<[^>]+>", " ", h + " " + b)
                secs.append((n, anchor, plain))
                term = _re.sub(r"\s+", " ", h).strip().rstrip("…").strip()
                if term and len(term) < 46 and not term.lower().startswith(("appendix", "1 ", "2 ", "3 ", "4 ")):
                    entries.setdefault(term, set()).add((n, anchor))
    TERMS = ["brush", "eraser", "line", "rectangle", "ellipse", "fill", "gradient", "pick colour",
             "text", "clone", "red-eye", "dodge", "burn", "selection", "marquee", "cutout",
             "cutout studio", "smart mask", "scribble", "feather", "grabcut", "transparency",
             "layer", "opacity", "blend", "merge", "flatten",
             "brightness", "contrast", "levels", "hue", "saturation", "temperature", "colour balance",
             "threshold", "posterize", "greyscale", "invert", "sepia", "auto contrast", "equalize",
             "gaussian blur", "unsharp mask", "median", "sharpen", "emboss", "find edges", "contour",
             "drop shadow", "outer glow", "resize", "canvas size", "crop", "rotate", "flip", "straighten",
             "undo", "zoom", "PNG", "JPEG", "pixel", "raster"]
    for t in TERMS:
        for (n, anchor, plain) in secs:
            if _re.search(r"\b" + _re.escape(t) + r"\b", plain, _re.I):
                entries.setdefault(t[0].upper() + t[1:], set()).add((n, anchor))
                break
    groups = defaultdict(list)
    for term in sorted(entries, key=lambda s: s.lower()):
        refs = sorted(entries[term])
        links = ", ".join(f'<a href="#{a}">Ch&nbsp;{n}</a>' for (n, a) in refs)
        letter = term[0].upper() if term[:1].isalpha() else "#"
        groups[letter].append(f"<li>{H.escape(term)} &nbsp;{links}</li>")
    out = ['<div class="index">']
    for letter in sorted(groups):
        out.append(f'<div class="idx-let">{letter}</div><ul class="idx">{"".join(groups[letter])}</ul>')
    out.append("</div>")
    return "".join(out)


def build_manual(IM):
    parts = manual_parts(IM)
    # number chapters sequentially across parts
    chno = 0
    numbered = []
    for ptitle, pblurb, chapters in parts:
        pc = []
        for (title, intro, secs) in chapters:
            chno += 1
            pc.append((chno, title, intro, secs))
        numbered.append((ptitle, pblurb, pc))

    # contents
    toc = []
    for ptitle, pblurb, pc in numbered:
        toc.append(f'<li class="part-h">{H.escape(ptitle)} · {H.escape(pblurb)}</li>')
        for (n, title, intro, secs) in pc:
            subs = "".join(f'<li><a href="#c{n}s{si}">{H.escape(h)}</a></li>'
                           for si, (h, _b) in enumerate(secs, 1))
            toc.append(f'<li class="ch"><span class="n">{n}</span>'
                       f'<a href="#c{n}">{H.escape(title)}</a><ul>{subs}</ul></li>')

    # body
    body = []
    for ptitle, pblurb, pc in numbered:
        body.append(f'<section class="part"><div class="pn">{H.escape(ptitle)}</div>'
                    f'<div class="pt">{H.escape(pblurb)}</div><div class="prule"></div></section>')
        for (n, title, intro, secs) in pc:
            body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Chapter {n}</span>'
                        f'<h2 id="c{n}">{H.escape(title)}</h2></div>\n{intro}')
            for si, (h, b) in enumerate(secs, 1):
                body.append(f'<h3 id="c{n}s{si}">{H.escape(h)}</h3>\n{b}')
            body.append("</section>")

    # back-of-book index
    toc.append('<li class="part-h">Index</li>')
    body.append('<section class="part"><div class="pn">Reference</div><div class="pt">Index</div><div class="prule"></div></section>')
    body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Reference</span>'
                f'<h2 id="bookindex">Index</h2></div>{build_index(numbered)}</section>')

    doc = f"""<!DOCTYPE html><html lang="en-GB"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… PAINTcanvas — User Guide</title>
<style>{CSS}{COVER_CSS}{MANUAL_CSS}</style>
<div class="page">
{cover('User Guide')}
<header class="mast"><h1>PAINTcanvas</h1><p>User Guide — the complete reference for painting, retouching,
adjusting and cutting out images.</p></header>
<nav class="contents"><h2 style="border:0;font-size:1.6rem">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… PAINTcanvas User Guide · generated {date.today().isoformat()} · every picture is produced by the app itself ·
in the spirit of Serif PhotoPlus.</footer>
</div></html>"""
    (OUT / "manual.html").write_text(doc, encoding="utf-8")
    nch = sum(len(pc) for _, _, pc in numbered)
    print("wrote manual.html:", len(doc) // 1024, "KiB,", len(numbered), "parts,", nch, "chapters")


def render_pdf(html_path, pdf_path):
    from PySide6.QtCore import QUrl, QEventLoop, QMarginsF, QTimer
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtWebEngineCore import QWebEnginePage
    pg = QWebEnginePage(); loop = QEventLoop(); res = {}

    def finished(_ok):
        lay = QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(12, 12, 12, 12))
        pg.printToPdf(str(pdf_path), lay)

    def pdfdone(_path, good):
        res['ok'] = good; loop.quit()

    pg.loadFinished.connect(finished); pg.pdfPrintingFinished.connect(pdfdone)
    pg.load(QUrl.fromLocalFile(os.path.abspath(str(html_path))))
    QTimer.singleShot(90000, loop.quit); loop.exec()
    sz = os.path.getsize(pdf_path) // 1024 if os.path.exists(pdf_path) else 0
    print(f"wrote {os.path.basename(str(pdf_path))}: {sz} KiB", "OK" if res.get('ok') else "FAILED")
    return res.get('ok', False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args(_REAL_ARGS)
    if Image is None:
        sys.exit("Pillow required")
    IM = capture(full=not args.quick)
    build_quickstart(IM)
    if not args.no_pdf:
        render_pdf(OUT / "quickstart.html", OUT / "quickstart.pdf")
    if not args.quick:
        build_manual(IM)
        if not args.no_pdf:
            render_pdf(OUT / "manual.html", OUT / "manual.pdf")
    try:
        _TMP.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
