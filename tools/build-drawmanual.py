#!/usr/bin/env python3
"""Build DRAWmaster's illustrated docs — a book-length User Guide and a Quick Start —
entirely from the running app.

    python3 tools/build-drawmanual.py            # both docs (HTML + PDF)
    python3 tools/build-drawmanual.py --quick    # just the Quick Start
    python3 tools/build-drawmanual.py --no-pdf   # HTML only (fast; skip printing)

Every picture is produced by the program itself: the workspace and the tool palette
are grabbed from a live (offscreen) window, the QuickShape catalogue and every demo
drawing are rendered with the app's own object painter, and each dialog is captured
by driving the real menu command. Images embed as data URIs, so each HTML file is
self-contained and installs with no extra assets.

Modelled on the structure and depth of Serif's DrawPlus User Guide — step-by-step
procedures, worked projects and a full reference section — but describing *this*
program's real tools and features throughout.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "draw" / "draw.py"
OUT = ROOT / "apps" / "draw"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-drawmanual"]

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QInputDialog   # noqa: E402
from PySide6.QtGui import QImage, QPainter, QColor                 # noqa: E402
from PySide6.QtCore import Qt, QRectF                              # noqa: E402

app = QApplication.instance() or QApplication([])

# Silence modal message boxes so a driver call never blocks.
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))

# QInputDialog's static getInt/getText/getDouble/getItem spin their own modal loop
# that does NOT go through the patched QDialog.exec — so offscreen they would block
# forever. Stub them to return a cancelled result immediately.
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, False))
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))

# Capture every dialog the app opens: when a command calls dlg.exec(), show the
# dialog offscreen, grab it, then return "rejected" so nothing is actually applied.
DGRABS: dict = {}
_orig_exec = QDialog.exec


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
    spec = importlib.util.spec_from_file_location("drawmaster", APP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DM = _load()

try:
    from PIL import Image
except Exception:
    Image = None

_TMP = ROOT / "tools" / "_tmp_grab.png"


def _grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGB").copy()


def _pil(qt_obj) -> "Image.Image":
    """PIL image from a QImage or QPixmap."""
    qt_obj.save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGBA").copy()


def _win():
    w = DM.Main()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1180, 820)
    w.show()
    for _ in range(16):
        app.processEvents()
    return w


# ------------------------------------------------------------------- drawing render
# A "drawing" here is a list of plain object dicts — exactly the shape DRAWmaster's
# own Canvas.objs holds — so the app's paint_object() renders them to a crisp image.
def render_drawing(objs, w, h, px=900, bg="#ffffff"):
    """Render a list of DRAWmaster objects to a PIL image at the given pixel width."""
    scale = px / w
    W, Hh = int(round(w * scale)), int(round(h * scale))
    img = QImage(W, Hh, QImage.Format_ARGB32)
    img.fill(QColor(bg))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(scale, scale)
    for o in objs:
        DM.paint_object(p, o, False)
    p.end()
    return _pil(img).convert("RGB")


# Convenience object constructors matching the app's model.
def rect(x, y, w, h, fill="#cfe3ef", stroke="#1f2a30", sw=2, **k):
    return dict(type="rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, **k)


def ellipse(x, y, w, h, fill="#cfe3ef", stroke="#1f2a30", sw=2, **k):
    return dict(type="ellipse", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, **k)


def quick(shape, x, y, w, h, fill="#cfe3ef", stroke="#1f2a30", sw=2, **k):
    return dict(type="quick", shape=shape, x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, **k)


def line(pts, stroke="#1f2a30", sw=3, **k):
    return dict(type="line", pts=pts, stroke=stroke, sw=sw, fill=None, **k)


def path(pts, stroke="#1f2a30", sw=3, closed=False, fill=None, **k):
    return dict(type="path", pts=pts, stroke=stroke, sw=sw, closed=closed, fill=fill, **k)


def poly(pts, stroke="#1f2a30", sw=3, closed=True, fill="#cfe3ef", **k):
    return dict(type="poly", pts=pts, stroke=stroke, sw=sw, closed=closed, fill=fill, **k)


def text(s, x, y, size=64, family="Noto Sans", fill="#1f2a30", stroke=None, sw=0, **k):
    return dict(type="text", text=s, x=x, y=y, size=size, family=family, fill=fill, stroke=stroke, sw=sw, **k)


def grad(c1, c2, angle=90, type="linear"):
    return dict(c1=c1, c2=c2, angle=angle, type=type)


def nodes_obj(nodes, closed=False, stroke="#1f2a30", sw=3, fill=None, **k):
    return dict(type="nodes", nodes=nodes, closed=closed, stroke=stroke, sw=sw, fill=fill, **k)


def _node(x, y, hin=(0, 0), hout=(0, 0), smooth=True):
    return dict(x=x, y=y, hin=list(hin), hout=list(hout), smooth=smooth)


# ------------------------------------------------------------------- demo drawings
# A hand-drawn-looking freehand wave, for the freehand/pencil illustration.
def _wave(x0, y0, amp, length, n=60):
    import math
    return [(x0 + length * i / n, y0 + amp * math.sin(i / n * math.pi * 3)) for i in range(n + 1)]


SELECT_TOOLS_DEMO = [
    rect(60, 70, 200, 130, fill="#9fc3d6", stroke="#2b3a42", sw=2),
    ellipse(300, 60, 170, 150, fill="#f4c96b", stroke="#8a6d1f", sw=2),
    quick("star5", 500, 50, 150, 150, fill="#e8556b", stroke="#b2374b", sw=2),
    line([(70, 250), (640, 250)], stroke="#2a7d6b", sw=4),
]

SHAPES_DEMO = [
    rect(40, 50, 150, 110, fill="#9fc3d6", stroke="#2b3a42", sw=2),
    ellipse(220, 50, 150, 110, fill="#f4c96b", stroke="#8a6d1f", sw=2),
    quick("star5", 400, 44, 120, 120, fill="#e8556b", stroke="#b2374b", sw=2),
    quick("hexagon", 560, 44, 120, 120, fill="#49c5b6", stroke="#2a8577", sw=2),
    line([(40, 210), (260, 210)], stroke="#2a7d6b", sw=5),
    line([(300, 230), (470, 190)], stroke="#5b8def", sw=3),
    path(_wave(500, 210, 26, 190), stroke="#9b6bd8", sw=4),
]

LINES_DEMO = [
    line([(40, 60), (320, 60)], stroke="#2b3a42", sw=2),
    line([(40, 110), (320, 110)], stroke="#2a7d6b", sw=6),
    path(_wave(40, 200, 34, 300), stroke="#5b8def", sw=4),
    poly([(400, 60), (560, 110), (520, 240), (420, 230), (380, 140)], fill="#f4c96b", stroke="#8a6d1f", sw=3),
    poly([(400, 280), (560, 280), (480, 180)], fill=None, stroke="#e8556b", sw=4, closed=False),
]

STYLE_DEMO = [
    # same star, three ways: fill only, outline only, both
    quick("star5", 40, 50, 150, 150, fill="#f4c96b", stroke=None, sw=0),
    quick("star5", 250, 50, 150, 150, fill=None, stroke="#b2374b", sw=4),
    quick("star5", 460, 50, 150, 150, fill="#e8556b", stroke="#7a2232", sw=6),
    rect(40, 240, 180, 40, fill="#2a7d6b", stroke=None, sw=0),
    rect(250, 240, 180, 40, fill="#2a7d6b", stroke="#13303a", sw=2),
    rect(460, 240, 180, 40, fill="#2a7d6b", stroke="#13303a", sw=10),
]

EFFECTS_DEMO = [
    rect(40, 60, 180, 130, fill="#2a7d6b", stroke=None, sw=0,
         shadow=dict(color="#000000", blur=16, dx=10, dy=12, opacity=45)),
    quick("star5", 280, 44, 150, 150, fill="#f4c96b", stroke="#c8851b", sw=2,
          glow=dict(color="#ffe08a", blur=24, opacity=90)),
    ellipse(480, 60, 160, 130, fill="#5b8def", stroke=None, sw=0,
            shadow=dict(color="#1a2740", blur=20, dx=0, dy=14, opacity=55),
            glow=dict(color="#bcd4ff", blur=18, opacity=60)),
]

FILLSTROKE_DEMO = [
    rect(40, 50, 160, 120, fill="#e8556b", stroke="#7a2232", sw=3),
    rect(230, 50, 160, 120, fill="#49c5b6", stroke="#176b60", sw=3),
    rect(420, 50, 160, 120, fill="#f4c96b", stroke="#8a6d1f", sw=3),
    rect(610, 50, 160, 120, fill="#9b6bd8", stroke="#5a3a86", sw=3),
    line([(40, 220), (770, 220)], stroke="#2b3a42", sw=1),
    line([(40, 260), (770, 260)], stroke="#2b3a42", sw=4),
    line([(40, 300), (770, 300)], stroke="#2b3a42", sw=10),
]

# --- new in 1.4: text, gradients, layers -----------------------------
TEXT_DEMO = [
    text("DRAWmaster", 30, 30, size=86, fill="#2a7d6b"),
    text("artistic text", 34, 150, size=58, fill=None, stroke="#b2374b", sw=3),
    text("gradient", 34, 250, size=72, grad=grad("#e8556b", "#5b8def", 20)),
]

GRADIENT_DEMO = [
    rect(30, 50, 180, 150, stroke="#1f2a30", sw=2, grad=grad("#f4c96b", "#e8556b", 90)),
    rect(240, 50, 180, 150, stroke="#1f2a30", sw=2, grad=grad("#5b8def", "#9b6bd8", 20)),
    ellipse(450, 50, 170, 150, stroke=None, sw=0, grad=grad("#ffffff", "#2a7d6b", type="radial")),
    quick("star5", 650, 44, 160, 160, stroke="#8a6d1f", sw=2, grad=grad("#fff0b0", "#c8851b", 60)),
]

# Three overlapping shapes, re-ordered three ways, to show z-order / layers.
def _zset(order):
    shp = {
        "A": quick("star5", 40, 40, 150, 150, fill="#e8556b", stroke="#b2374b", sw=2),
        "B": ellipse(110, 90, 150, 130, fill="#5b8def", stroke="#2b3a42", sw=2),
        "C": rect(170, 120, 150, 110, fill="#f4c96b", stroke="#8a6d1f", sw=2),
    }
    return [shp[k] for k in order]

LAYERS_DEMO = _zset("ABC")    # drawn in order: star, then ellipse, then rect on top
LAYERS_FRONT = _zset("BCA")   # the star brought to the front

# --- new in 1.5: transform (rotate), group/align/distribute, grid & guides ----
# Rotation: the same arrow at a run of angles, like a fan.
TRANSFORM_DEMO = [
    quick("arrow", 40 + i * 120, 80, 100, 70, fill=c, stroke="#1f2a30", sw=2, rot=a)
    for i, (a, c) in enumerate([(0, "#9fc3d6"), (20, "#f4c96b"), (45, "#e8556b"),
                                (90, "#49c5b6"), (135, "#9b6bd8")])
]
# Resize-vs-rotate: one rectangle plain, one scaled, one rotated.
RESIZE_DEMO = [
    rect(40, 70, 150, 110, fill="#5b8def", stroke="#2b3a42", sw=2),
    rect(230, 50, 230, 150, fill="#5b8def", stroke="#2b3a42", sw=2),
    rect(520, 70, 150, 110, fill="#5b8def", stroke="#2b3a42", sw=2, rot=30),
]

# Grouping: three parts of a little "robot", treated as one.
GROUP_DEMO = [
    rect(90, 40, 120, 100, fill="#9fc3d6", stroke="#2b3a42", sw=2, gid=1),
    ellipse(110, 60, 30, 30, fill="#2b3a42", stroke=None, sw=0, gid=1),
    ellipse(160, 60, 30, 30, fill="#2b3a42", stroke=None, sw=0, gid=1),
    rect(70, 150, 160, 70, fill="#5b8def", stroke="#2b3a42", sw=2, gid=1),
]

# Align: scattered boxes (left), then flush-left and evenly distributed (right).
ALIGN_BEFORE = [
    rect(60, 30, 80, 50, fill="#e8556b", stroke="#b2374b", sw=2),
    rect(140, 110, 80, 50, fill="#f4c96b", stroke="#8a6d1f", sw=2),
    rect(30, 190, 80, 50, fill="#49c5b6", stroke="#2a8577", sw=2),
    rect(190, 260, 80, 50, fill="#5b8def", stroke="#2b3a42", sw=2),
]
ALIGN_AFTER = [
    rect(40, 30, 80, 50, fill="#e8556b", stroke="#b2374b", sw=2),
    rect(40, 123, 80, 50, fill="#f4c96b", stroke="#8a6d1f", sw=2),
    rect(40, 216, 80, 50, fill="#49c5b6", stroke="#2a8577", sw=2),
    rect(40, 309, 80, 50, fill="#5b8def", stroke="#2b3a42", sw=2),
]

# A finished worked example: a simple logo / badge.
LOGO_DEMO = [
    quick("octagon", 70, 40, 260, 260, fill="#2a7d6b", stroke="#143f36", sw=6,
          shadow=dict(color="#000000", blur=18, dx=8, dy=10, opacity=35)),
    quick("star5", 120, 95, 160, 160, fill="#f4c96b", stroke="#c8851b", sw=3,
          glow=dict(color="#fff0b0", blur=18, opacity=80)),
    quick("heart", 420, 70, 150, 140, fill="#e8556b", stroke="#b2374b", sw=3),
    quick("speech", 420, 230, 180, 120, fill="#ffffff", stroke="#2a7df0", sw=4),
    line([(600, 120), (760, 120)], stroke="#2a7d6b", sw=8),
    line([(600, 300), (760, 260)], stroke="#5b8def", sw=4),
]

# Stepwise build of the logo, for the worked project.
LOGO_STEP1 = LOGO_DEMO[:1]
LOGO_STEP2 = LOGO_DEMO[:2]
LOGO_STEP3 = LOGO_DEMO[:4]

# --- new in 1.6: images, node/Bézier curves, PDF/print, opacity/dash/arrows/combine ----

# A smooth Bézier wave drawn as a node path, next to a shape "converted to curves".
CURVES_DEMO = [
    nodes_obj([
        _node(40, 160, hout=(60, -90)),
        _node(230, 120, hin=(-70, 60), hout=(70, -60)),
        _node(420, 170, hin=(-60, -80), hout=(0, 0), smooth=False),
    ], closed=False, stroke="#9b3b57", sw=5),
    # a star converted to curves (shown with its nodes implied by the smooth corners)
    nodes_obj([
        _node(520, 60, hout=(0, 0), smooth=False),
        _node(600, 200, hout=(0, 0), smooth=False),
        _node(460, 110, hout=(0, 0), smooth=False),
        _node(640, 110, hout=(0, 0), smooth=False),
        _node(500, 200, hout=(0, 0), smooth=False),
    ], closed=True, stroke="#c8851b", sw=3, fill="#f4c96b"),
]

# A rounded "blob" built only from smooth Bézier nodes — what the Pen tool makes.
BEZIER_BLOB = [
    nodes_obj([
        _node(130, 40, hin=(-70, 0), hout=(70, 0)),
        _node(300, 110, hin=(0, -60), hout=(0, 60)),
        _node(150, 210, hin=(70, 10), hout=(-70, -10)),
        _node(30, 110, hin=(0, 60), hout=(0, -60)),
    ], closed=True, stroke="#2a7d6b", sw=3, fill="#9fd6c9"),
]

# Opacity: three overlapping discs, each half-transparent, so the overlaps blend.
OPACITY_DEMO = [
    ellipse(40, 40, 160, 160, fill="#e8556b", stroke=None, sw=0, opacity=0.55),
    ellipse(140, 40, 160, 160, fill="#5b8def", stroke=None, sw=0, opacity=0.55),
    ellipse(90, 120, 160, 160, fill="#f4c96b", stroke=None, sw=0, opacity=0.55),
]

# Dash styles and arrowheads on lines.
DASH_DEMO = [
    line([(40, 50), (360, 50)], stroke="#2b3a42", sw=4),                     # solid
    dict(type="line", pts=[(40, 110), (360, 110)], stroke="#2a7d6b", sw=4, fill=None, dash="dashed"),
    dict(type="line", pts=[(40, 170), (360, 170)], stroke="#9b3b57", sw=4, fill=None, dash="dotted"),
    dict(type="line", pts=[(40, 240), (360, 240)], stroke="#5b8def", sw=4, fill=None, arrow="end"),
    dict(type="line", pts=[(40, 300), (360, 300)], stroke="#c8851b", sw=4, fill=None, arrow="both", dash="dashed"),
]

# Combine: two overlapping rounded shapes, then union / subtract / intersect of them.
def _two(off=0):
    return [quick("speech", 20, 30, 150, 120, fill="#9fc3d6", stroke="#2b3a42", sw=2),
            ellipse(110, 70, 140, 120, fill="#f4c96b", stroke="#8a6d1f", sw=2)]

# the booleans are rendered live from real QPainterPaths in capture()


# --- new in 1.7: flip, lock/duplicate, texture fill, text-on-path, dimension, connector, units ---

# Flip: an asymmetric "flag" shape, and its horizontal mirror beside it.
FLIP_BEFORE = [
    poly([(40, 40), (200, 70), (120, 120), (210, 170), (40, 200)], fill="#5b8def", stroke="#2b3a42", sw=2),
    text("F", 70, 70, size=90, fill="#ffffff"),
]
def _flip_h(objs, cx):
    out = []
    for o in objs:
        c = {k: v for k, v in o.items()}
        if c["type"] == "text":
            c = dict(c); c["x"] = 2 * cx - c["x"] - 40
        else:
            c = dict(c); c["pts"] = [(2 * cx - x, y) for x, y in o["pts"]]
        out.append(c)
    return out

# Duplicate / clone: one shape, then a run of offset copies like a cascade.
DUPLICATE_DEMO = [
    quick("star5", 40 + i * 34, 40 + i * 24, 120, 120,
          fill=["#e8556b", "#ef7a88", "#f49ca6", "#f8bcc3"][i], stroke="#b2374b", sw=2)
    for i in range(4)
][::-1]

# Lock: a "background" rectangle behind freely-moved shapes (conceptual).
LOCK_DEMO = [
    rect(30, 30, 420, 240, fill="#eef3f6", stroke="#9fb4c0", sw=2),      # the locked backdrop
    quick("star5", 70, 70, 110, 110, fill="#f4c96b", stroke="#c8851b", sw=2),
    ellipse(230, 120, 120, 100, fill="#49c5b6", stroke="#2a8577", sw=2),
    text("locked backdrop", 60, 235, size=26, fill="#6c8390"),
]

# Text on a path: a word flowing along an arc, built as a text object with pathpts.
import math as _m
_ARC = [(40 + i * 10, 200 - 120 * _m.sin(i / 42 * _m.pi)) for i in range(43)]
TEXTPATH_DEMO = [
    dict(type="path", pts=_ARC, stroke="#d7dee3", sw=2, closed=False, fill=None),
    dict(type="text", x=40, y=200, text="curving headline", family="Noto Sans",
         size=42, fill="#2a7d6b", stroke=None, sw=0, pathpts=_ARC),
]

# Dimension lines: a box measured on two sides.
DIM_DEMO = [
    rect(90, 70, 260, 150, fill="#eaf1f4", stroke="#2b3a42", sw=2),
    dict(type="dim", pts=[(90, 245), (350, 245)], stroke="#9b3b57", sw=2, fill=None, unit="px"),
    dict(type="dim", pts=[(60, 70), (60, 220)], stroke="#9b3b57", sw=2, fill=None, unit="px"),
]

# Connectors: two boxes joined by a connector line with an arrow.
CONN_DEMO = [
    rect(40, 60, 130, 90, fill="#9fc3d6", stroke="#2b3a42", sw=2, cid=1),
    rect(330, 160, 130, 90, fill="#f4c96b", stroke="#8a6d1f", sw=2, cid=2),
    dict(type="conn", a={"anchor": 1}, b={"anchor": 2}, stroke="#2a7d6b", sw=3, arrow="end", fill=None),
    text("Start", 60, 80, size=30, fill="#1f2a30"),
    text("End", 355, 185, size=30, fill="#1f2a30"),
]


# ------------------------------------------------------------------- capture
def capture(full=True):
    """Return {key: PIL image} for every picture the guide needs."""
    IM = {}

    # --- rendered demo drawings ------------------------------------------
    IM["select_demo"] = render_drawing(SELECT_TOOLS_DEMO, 700, 300, px=840)
    IM["shapes_demo"] = render_drawing(SHAPES_DEMO, 720, 420, px=860)
    IM["lines_demo"] = render_drawing(LINES_DEMO, 620, 330, px=820)
    IM["style_demo"] = render_drawing(STYLE_DEMO, 660, 300, px=820)
    IM["effects_demo"] = render_drawing(EFFECTS_DEMO, 680, 220, px=860)
    IM["fillstroke_demo"] = render_drawing(FILLSTROKE_DEMO, 810, 330, px=880)
    IM["logo_demo"] = render_drawing(LOGO_DEMO, 800, 380, px=880)
    IM["logo1"] = render_drawing(LOGO_STEP1, 800, 340, px=760)
    IM["logo2"] = render_drawing(LOGO_STEP2, 800, 340, px=760)
    IM["logo3"] = render_drawing(LOGO_STEP3, 800, 380, px=760)
    IM["text_demo"] = render_drawing(TEXT_DEMO, 620, 330, px=820)
    IM["gradient_demo"] = render_drawing(GRADIENT_DEMO, 830, 220, px=880)
    IM["layers_demo"] = render_drawing(LAYERS_DEMO, 360, 260, px=600)
    IM["layers_front"] = render_drawing(LAYERS_FRONT, 360, 260, px=600)
    IM["transform_demo"] = render_drawing(TRANSFORM_DEMO, 700, 240, px=860)
    IM["resize_demo"] = render_drawing(RESIZE_DEMO, 720, 240, px=860)
    IM["group_demo"] = render_drawing(GROUP_DEMO, 300, 240, px=560)
    IM["align_before"] = render_drawing(ALIGN_BEFORE, 300, 330, px=440)
    IM["align_after"] = render_drawing(ALIGN_AFTER, 300, 380, px=440)

    # --- new in 1.6 ------------------------------------------------------
    IM["curves_demo"] = render_drawing(CURVES_DEMO, 680, 240, px=860)
    IM["bezier_blob"] = render_drawing(BEZIER_BLOB, 340, 260, px=560)
    IM["opacity_demo"] = render_drawing(OPACITY_DEMO, 300, 300, px=520)
    IM["dash_demo"] = render_drawing(DASH_DEMO, 400, 340, px=640)

    # --- new in 1.7 -----------------------------------------------------
    IM["flip_demo"] = render_drawing(FLIP_BEFORE + _flip_h(FLIP_BEFORE, 310), 580, 240, px=820)
    IM["duplicate_demo"] = render_drawing(DUPLICATE_DEMO, 300, 230, px=560)
    IM["lock_demo"] = render_drawing(LOCK_DEMO, 480, 290, px=720)
    # connectors & text-on-path need the module's paint-object list set so anchors resolve
    DM._PAINT_OBJS = CONN_DEMO
    IM["conn_demo"] = render_drawing(CONN_DEMO, 500, 280, px=740)
    DM._PAINT_OBJS = TEXTPATH_DEMO
    IM["textpath_demo"] = render_drawing(TEXTPATH_DEMO, 480, 230, px=760)
    DM._PAINT_OBJS = DIM_DEMO
    IM["dim_demo"] = render_drawing(DIM_DEMO, 420, 280, px=700)
    DM._PAINT_OBJS = []

    # Texture fill: prefer a real library texture, else a generated checker, on two shapes
    try:
        texpath = None
        for cat in ("Wood", "Marble", "Paper Textures", "Bricks & Tiles", "Metal"):
            cd = os.path.join(DM.TEXTURE_LIB, cat)
            if os.path.isdir(cd):
                files = sorted(f for f in os.listdir(cd)
                               if f.lower().endswith((".jpg", ".jpeg", ".png")))
                if files:
                    texpath = os.path.join(cd, files[0]); break
        if texpath is None:
            # synthesise a small checker tile so the demo always renders
            chk = QImage(40, 40, QImage.Format_ARGB32)
            qp = QPainter(chk); qp.fillRect(0, 0, 40, 40, QColor("#c8851b"))
            qp.fillRect(0, 0, 20, 20, QColor("#f4c96b")); qp.fillRect(20, 20, 20, 20, QColor("#f4c96b"))
            qp.end()
            texpath = str(ROOT / "tools" / "_tmp_tex.png"); chk.save(texpath)
        uri = DM.image_data_uri(texpath)
        tex_tile = quick("star5", 30, 30, 200, 200, fill="#ccc", stroke="#1f2a30", sw=3,
                         texfill={"src": uri, "mode": "tile"})
        tex_stretch = rect(270, 40, 220, 180, fill="#ccc", stroke="#1f2a30", sw=3,
                           texfill={"src": uri, "mode": "stretch"})
        IM["texture_demo"] = render_drawing([tex_tile, tex_stretch], 520, 250, px=780)
    except Exception as ee:
        print("texture demo failed:", ee)

    # Combine: render union / subtract / intersect from real QPainterPaths, via the app
    try:
        import copy as _copy

        def _combine_img(opname):
            cw = _win2.canvas
            shapes = _copy.deepcopy(_two())
            for s in shapes:
                s["layer"] = cw.active_layer
            cw.objs = shapes
            cw.set_selection(shapes)
            cw.combine_selection(opname)
            objs = _copy.deepcopy(cw.objs)
            return render_drawing(objs, 270, 210, px=460)

        _win2 = _win()
        IM["combine_before"] = render_drawing([s | {"layer": 1} for s in _copy.deepcopy(_two())], 270, 210, px=460)
        IM["combine_union"] = _combine_img("union")
        IM["combine_subtract"] = _combine_img("subtract")
        IM["combine_intersect"] = _combine_img("intersect")
    except Exception as e:
        print("combine render failed:", e)

    # A placed image: build a tiny generated picture, embed it, render the image object.
    try:
        pic = QImage(220, 150, QImage.Format_ARGB32)
        qp = QPainter(pic)
        qp.fillRect(0, 0, 220, 150, QColor("#7cc5de"))
        qp.setBrush(QColor("#f4c96b")); qp.setPen(QColor("#8a6d1f"))
        qp.drawEllipse(30, 30, 90, 90)
        qp.setBrush(QColor("#2a7d6b")); qp.setPen(QColor("#143f36"))
        qp.drawRect(120, 60, 70, 60)
        qp.end()
        _pic_path = str(ROOT / "tools" / "_tmp_pic.png")
        pic.save(_pic_path)
        uri = DM.image_data_uri(_pic_path)
        img_obj = dict(type="image", x=40, y=30, w=220, h=150, src=uri, stroke="#2b3a42", sw=2, fill=None)
        framed = dict(img_obj); framed["x"] = 300
        IM["image_demo"] = render_drawing([img_obj,
                                           rect(300, 30, 220, 150, fill=None, stroke="#2b3a42", sw=2),
                                           dict(type="image", x=300, y=30, w=220, h=150, src=uri, stroke=None, sw=0, fill=None, opacity=0.55)],
                                          560, 210, px=760)
        try:
            os.unlink(_pic_path)
        except OSError:
            pass
    except Exception as e:
        print("image demo failed:", e)

    # --- QuickShape catalogue: every shape in a labelled grid ------------
    # Rendered shapes only (no text drawn via Qt — offscreen text can abort).
    qs = DM.QUICKSHAPES
    cols, cw, ch = 4, 180, 150
    palette = ["#2a7d6b", "#5b8def", "#e8556b", "#f4c96b", "#49c5b6", "#9b6bd8"]
    grid = []
    for i, (key, label) in enumerate(qs):
        cx, cy = 14 + (i % cols) * cw, 14 + (i // cols) * ch
        col = palette[i % len(palette)]
        grid.append(quick(key, cx + 26, cy + 8, cw - 76, ch - 60, fill=col, stroke="#1f2a30", sw=2))
    rows = (len(qs) + cols - 1) // cols
    IM["qshapes"] = render_drawing(grid, cols * cw + 28, rows * ch + 28, px=900, bg="#f4f6f7")
    # keep the shape list so the manual can caption each one in an HTML table
    IM["_quickshapes"] = list(qs)

    # --- workspace & tool palette (live window) --------------------------
    w = _win()
    for _ in range(8):
        app.processEvents()
    full_ws = _grab(w)
    IM["workspace"] = full_ws

    # the vertical tool palette: grab the Tools toolbar widget itself → 'tall'
    try:
        tb = None
        for child in w.findChildren(DM.QToolBar):
            if child.windowTitle() == "Tools" or child.orientation() == Qt.Vertical:
                tb = child
                break
        if tb is not None:
            for _ in range(4):
                app.processEvents()
            IM["toolrail"] = _grab(tb)
    except Exception as e:
        print("tool palette grab failed:", e)

    # the top Style toolbar (fill/line/width/shape/gradient/effects/zoom)
    try:
        for child in w.findChildren(DM.QToolBar):
            if child.windowTitle() == "Style":
                IM["stylebar"] = _grab(child)
                break
    except Exception as e:
        print("style bar grab failed:", e)

    # the Layers dock — seed a second layer so the panel shows a real stack
    try:
        w.canvas.add_layer()
        w.canvas.rename_layer(w.canvas.layers[-1]["id"], "Text & labels")
        w.canvas.rename_layer(w.canvas.layers[0]["id"], "Background")
        w.refresh_layers()
        w.layers_dock.setFloating(True)
        w.layers_dock.widget().setMinimumWidth(240)
        w.layers_dock.widget().adjustSize()
        for _ in range(6):
            app.processEvents()
        IM["layerpanel"] = _grab(w.layers_dock.widget())
    except Exception as e:
        print("layers panel grab failed:", e)

    # --- a live canvas with grid, a guide, a selected object and its handles
    try:
        w3 = _win()
        cv = w3.canvas
        cv.set_grid(on=True, spacing=40)
        cv.add_guide("v", 360)
        cv.add_guide("h", 220)
        shp = quick("star5", 150, 90, 240, 240, fill="#f4c96b", stroke="#c8851b", sw=3, layer=cv.active_layer)
        shp["rot"] = 18
        cv.objs.append(shp)
        cv.set_selection([shp])
        cv.setMinimumSize(620, 460)
        cv.resize(620, 460)
        for _ in range(8):
            app.processEvents()
        cv.repaint()
        for _ in range(4):
            app.processEvents()
        # grab just the drawn area (canvas region), not the whole scrolled widget
        IM["canvas_handles"] = _grab(cv)
    except Exception as e:
        print("canvas handles grab failed:", e)

    # --- dialogs: drive the real commands; _cap_exec stores them ---------
    def drive(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            print("drive failed:", getattr(fn, "__name__", fn), e)
        for _ in range(6):
            app.processEvents()

    w2 = _win()
    # New Drawing dialog
    drive(w2.new)
    # Effects dialog needs a selected object
    try:
        shp = quick("star5", 120, 120, 220, 220, fill="#f4c96b", stroke="#c8851b", sw=2)
        w2.canvas.objs.append(shp)
        w2.canvas.sel = shp
        for _ in range(4):
            app.processEvents()
    except Exception as e:
        print("seed shape failed:", e)
    drive(w2.effects_dialog)
    # Gradient dialog (same selected shape works)
    drive(w2.gradient_dialog)
    # Texture / Pattern Fill dialog (same selected shape works)
    drive(w2.texture_fill_dialog)
    # Add Text dialog — the Text tool opens it on a canvas click
    drive(w2.place_text, (120, 120))
    # Edit Text dialog — needs a selected text object
    try:
        t = text("Headline", 80, 80, size=72, fill="#2a7d6b")
        w2.canvas.objs.append(t)
        w2.canvas.sel = t
        for _ in range(4):
            app.processEvents()
    except Exception as e:
        print("seed text failed:", e)
    drive(w2.edit_text)
    # Line Style (dashes & arrows) dialog — needs a line selected
    try:
        ln = line([(60, 120), (360, 120)], stroke="#2a7d6b", sw=4)
        w2.canvas.objs.append(ln)
        w2.canvas.sel = ln
        for _ in range(4):
            app.processEvents()
    except Exception as e:
        print("seed line failed:", e)
    drive(w2.line_style_dialog)

    IM["_dialogs"] = dict(DGRABS)
    return IM


# ------------------------------------------------------------------- image out
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


# ------------------------------------------------------------------- content DSL
def fig(im, cap, cls=""):
    if im is None:
        return ""   # a capture that didn't happen degrades to no figure, not a broken box
    uri = im if isinstance(im, str) else datauri(im)
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


# ------------------------------------------------------------------- the manual
def manual_parts(IM):
    """Returns a list of parts. Each part: (part_title, blurb, [chapters]).
    Each chapter: (title, intro_html, [(heading, body_html), ...])."""
    D = IM.get("_dialogs", {})

    def dlg(*names):
        for n in names:
            if n in D:
                return D[n]
        return None

    qs = IM.get("_quickshapes", [])
    qs_rows = "".join(f"<tr><td>{H.escape(lbl)}</td></tr>" for _k, lbl in qs)

    parts = []

    # ============================================================ PART I
    ch = []
    ch.append(("Welcome to DRAWmaster",
      "<p class='lede'>DRAWmaster is a <b>vector drawing</b> program: a tool for building pictures out of "
      "shapes, lines and paths that stay perfectly sharp at any size. It belongs to the <i>just a…</i> "
      "family of apps and works in the tradition of Serif's DrawPlus — the same ideas, the same way of "
      "drawing.</p>", [
      ("What vector drawing is", f"""
<p>There are two kinds of picture on a computer. A <b>bitmap</b> (or raster) image — a photograph, or
anything you paint in PAINTcanvas — is a grid of coloured dots; blow it up and the dots show as fuzzy
squares. A <b>vector</b> image is different: it is stored as <i>instructions</i> — “a red star here, a
blue line there” — so the computer re-draws it crisply at whatever size you ask. Zoom in a hundred
times and the edges stay razor-sharp.</p>
{fig(IM.get('logo_demo'), 'A simple badge drawn in DRAWmaster — shapes, lines and effects, every edge perfectly crisp because it is vector.')}
<p>That makes vector drawing the right tool for logos, icons, diagrams, maps, badges and illustrations —
anything that must look clean at any size, from a business-card corner to a banner across a wall.</p>"""),
      ("The object model", """
<p>Everything you draw in DRAWmaster is an <b>object</b>, and there are only a handful of kinds:</p>
<ul>
<li><b>Rectangles</b> and <b>ellipses</b> — the two basic boxed shapes;</li>
<li><b>QuickShapes</b> — ready-made outlines such as stars, arrows, hearts and speech bubbles;</li>
<li><b>Lines</b> — a single straight segment;</li>
<li><b>Freehand paths</b> — a flowing line you draw by hand, as if with a pencil;</li>
<li><b>Pen polylines</b> — a shape built point by point, which you can leave open or close into a filled outline;</li>
<li><b>Text</b> — artistic text that behaves like a shape (fill, outline, gradient and effects all apply), and can be flowed along a path;</li>
<li><b>Images</b> — a bitmap picture placed on the canvas, embedded in the drawing;</li>
<li><b>Dimension lines</b> and <b>connectors</b> — technical-drawing objects: a measured line with a length label, and a link between two objects that follows them as they move.</li>
</ul>
<p>Because they are all objects, the skills are shared: whatever the kind, you select it, move it, give
it a fill and an outline, and lift it off the page with a shadow or glow — all in exactly the same way.
Learn those moves once and they apply to everything you draw.</p>"""),
      ("The just a… family", """
<p>DRAWmaster has three companions, and they are built to work together:</p>
<ul>
<li><b>PAINTcanvas</b> is the raster image editor — DRAWmaster can hand a finished drawing across to it
for photo-style touch-ups;</li>
<li><b>PAGEdesigner</b> lays out printed pages — posters, flyers, newsletters;</li>
<li><b>WEBcreator</b> builds websites the same way.</li>
</ul>
<p>They share the <b>CREATORsuite</b> launcher and a common <i>Documents/just a…</i> folder, so your work
is always easy to find. Once you know one app, the others feel familiar.</p>"""),
      ("About this guide", f"""
<p>This User Guide is the complete reference. It is organised in parts: the first gets you working, the
middle teaches each skill in depth with step-by-step procedures, then come worked projects you can follow
start to finish, output and sharing, and finally a reference section — menus, shortcuts, a catalogue of
every QuickShape, and a glossary.</p>
{note('Throughout, a numbered <b>“To …”</b> box is a procedure you can follow exactly. A <b>Tip</b> suggests a faster or better way. A <b>Remember</b> box flags something easy to forget.')}
<p>For a gentler first read, start with the <b>Quick Start Guide</b> (Help ▸ Quick Start Guide), which
takes you from a blank canvas to a finished drawing in a dozen short steps.</p>"""),
      ("Conventions used here", f"""
<p>A few conventions keep the instructions short:</p>
<ul>
<li><b>Menu ▸ Command</b> means “open this menu and choose this command”, e.g. <b>File ▸ Save as SVG…</b>.</li>
<li>Keys are shown like {K('Ctrl')}+{K('S')}; on a Mac read {K('Ctrl')} as {K('Cmd')}.</li>
<li><b>Click</b> means the left mouse button; <b>drag</b> means press, move, release;
<b>double-click</b> finishes a pen shape.</li>
</ul>""")]))

    ch.append(("Starting Out",
      "<p class='lede'>This chapter covers the very first things: launching the program, the canvas you "
      "draw on, and starting a new drawing at the size you want.</p>", [
      ("Launching the program", """
<p>Open <b>just a… DRAWmaster</b> from the CREATORsuite launcher, from your system's application menu, or
by running <code>draw</code> in a terminal. It opens straight onto a blank white canvas, ready to draw.</p>"""),
      ("Starting a new drawing", f"""
<p>DRAWmaster opens with a default canvas, but you can start fresh at a chosen size at any time.</p>
{proc('start a new drawing',
  'Choose <b>File ▸ New…</b> (' + K('Ctrl') + '+' + K('N') + ').',
  'Pick a <b>canvas size</b> from the list — a general 1000 × 700, an A4 page (794 × 1123), full-HD 1920 × 1080, or a square 800 × 800.',
  'Click <b>Create</b>. The canvas clears to the new size, ready for your first shape.')}
{fig(dlg('New Drawing'), 'The New Drawing dialog offers a few ready canvas sizes, including A4 and a square.')}
{note('The canvas size sets the drawing’s coordinate space and the proportions of an exported PNG. Because the drawing is vector, you can still scale the result up or down afterwards without losing sharpness.')}"""),
      ("Saving and opening", f"""
<p>DRAWmaster saves your work as an <b>SVG</b> file — the standard vector format, readable by browsers,
other drawing programs and the web.</p>
{proc('save your drawing',
  'Choose <b>File ▸ Save as SVG…</b> (' + K('Ctrl') + '+' + K('S') + ').',
  'Give it a name. It is saved into your shared <i>Documents/just a…</i> folder by default, so the launcher can find it.',
  'DRAWmaster quietly tucks the full, editable drawing inside the SVG, so it can re-open its own files with every shape intact.')}
{proc('open a drawing',
  'Choose <b>File ▸ Open SVG…</b> (' + K('Ctrl') + '+' + K('O') + ') and pick an <code>.svg</code> file.',
  'A drawing DRAWmaster saved itself opens fully editable.')}
{caution('DRAWmaster can re-open the SVGs <i>it</i> saved with every object editable, because it stores its object list inside the file. A plain SVG made by another program still displays as a picture elsewhere, but DRAWmaster cannot break it back into editable shapes.')}""")]))

    ch.append(("The Workspace",
      "<p class='lede'>Everything you do happens in the workspace: your canvas in the middle, the drawing "
      "tools down the left, the style controls across the top, and a status bar below. This chapter names "
      "every part so the rest of the guide can refer to them.</p>", [
      ("A tour of the window", f"""
<p>A new drawing opens with the white canvas centred on a grey pasteboard and everything you need arranged
around it.</p>
{fig(IM.get('workspace'), 'The DRAWmaster workspace: the tool palette down the left, the Style toolbar across the top, the canvas in the centre and the status bar below.')}
<p>The parts are:</p>
<ul>
<li>the <b>menu bar</b> across the top — <b>File</b>, <b>Edit</b> and <b>Help</b>;</li>
<li>the <b>Style toolbar</b> below it — fill, line, width, QuickShape, effects and zoom;</li>
<li>the vertical <b>tool palette</b> down the left edge;</li>
<li>the <b>canvas</b> itself in the centre;</li>
<li>the <b>status bar</b> along the bottom, which shows the pointer's position.</li>
</ul>"""),
      ("The tool palette", f"""
<p>The vertical <b>tool palette</b> on the left holds the tools you draw and edit with. Click one to
select it; it stays active until you choose another.</p>
{fig(IM.get('toolrail'), 'The tool palette, from the top: Select, Node, Freehand, Pen, Line, Rectangle, Ellipse, QuickShape, Text, Image, Dimension line and Connector.', 'tall')}
<p>From the top, the tools are the <b>Select</b> pointer, the <b>Node</b> tool (for reshaping curves),
<b>Freehand</b> (a pencil), the <b>Pen</b> (for Bézier curves), <b>Line</b>, <b>Rectangle</b>,
<b>Ellipse</b>, <b>QuickShape</b>, <b>Text</b>, <b>Image</b>, the <b>Dimension line</b> (a measured line
with end ticks and an automatic length label) and the <b>Connector</b> (a line that links two objects and
stays attached as they move). Each is covered in detail in Part II.</p>
{tip('Choosing the Select tool is the quickest way to stop drawing and go back to picking things up and moving them.')}"""),
      ("The Style toolbar", f"""
<p>The horizontal <b>Style toolbar</b> along the top sets how the next shape will look — and restyles the
selected one.</p>
{fig(IM.get('stylebar'), 'The Style toolbar: the Fill and Line colour buttons, the line Width, the QuickShape chooser, the Effects button and the zoom controls.')}
<ul>
<li><b>Fill</b> — the colour inside a shape (the button shows the current colour);</li>
<li><b>Line</b> — the colour of the outline;</li>
<li><b>Width</b> — the outline thickness, in pixels (0 for no outline);</li>
<li><b>Shape</b> — which QuickShape the QuickShape tool draws;</li>
<li><b>Effects…</b> — the drop shadow and glow for the selected object;</li>
<li><b>Zoom</b> — zoom in, zoom out, and back to 100%.</li>
</ul>"""),
      ("Moving around and zooming", f"""
<p>You will zoom in to place things precisely and out to judge the whole drawing.</p>
{proc('change the zoom',
  'Click <b>Zoom +</b> or <b>Zoom −</b> on the Style toolbar to step in or out, or',
  'click <b>100%</b> to return to actual size.')}
<p>When the drawing is larger than the window, scroll bars appear around the canvas so you can slide to
any part of it. The status bar at the bottom shows the pointer's exact position in canvas coordinates —
useful for lining a shape up precisely.</p>""")]))

    parts.append(("Part I", "Getting Started", ch))

    # ============================================================ PART II
    ch = []
    ch.append(("Drawing Shapes",
      "<p class='lede'>Rectangles, ellipses and QuickShapes are the building blocks of most drawings. "
      "This chapter covers drawing each of them, and the two dozen ready-made QuickShapes.</p>", [
      ("Rectangles and ellipses", f"""
{proc('draw a rectangle or an ellipse',
  'Choose the <b>Rectangle</b> or <b>Ellipse</b> tool from the tool palette.',
  'Press on the canvas where one corner should be, drag to the opposite corner, and release.',
  'The shape appears with the current fill and outline, and is left selected so you can adjust it at once.')}
{fig(IM.get('shapes_demo'), 'A rectangle, an ellipse, two QuickShapes, a straight line, a short line and a freehand curve.')}
<p>Each new shape takes the <b>Fill</b> and <b>Line</b> colours and the <b>Width</b> currently shown on
the Style toolbar — so set those first if you know the look you want, or change them afterwards with the
shape selected.</p>"""),
      ("QuickShapes", f"""
<p><b>QuickShapes</b> are ready-made outlines — you do not draw their edges by hand, you simply drag out a
box and the shape fills it. DRAWmaster has {len(qs)} of them.</p>
{proc('draw a QuickShape',
  'On the Style toolbar, pick a shape from the <b>Shape</b> list (choosing one switches to the QuickShape tool automatically).',
  'Drag a box on the canvas; the shape is drawn to fit it.',
  'Resize, recolour or move it afterwards like any other object.')}
{fig(IM.get('qshapes'), 'Every QuickShape DRAWmaster offers, each drawn into an equal box.')}
<p>They cover geometry (triangle, right triangle, diamond, pentagon, hexagon, octagon, parallelogram,
trapezoid), stars (five- and six-point), arrows (single, double and a chevron), a cross, and the
expressive shapes — heart, lightning bolt, speech bubble and cloud — ready for a badge, a diagram or a
caption.</p>"""),
      ("The QuickShape catalogue", f"""
<p>For reference, here is every QuickShape by name, in the order they appear in the Shape list:</p>
<table class="ref"><tr><th>QuickShape</th></tr>{qs_rows}</table>
{tip('A speech bubble makes an instant caption; a star or a seal draws the eye to the one thing that matters; arrows and a chevron turn a set of boxes into a diagram or a flow chart.')}""")]))

    ch.append(("Drawing Lines and Paths",
      "<p class='lede'>Where shapes give a drawing its solid forms, lines and paths give it movement and "
      "detail — a rule, a connector, a flowing hand-drawn stroke, or a custom outline you build point by "
      "point.</p>", [
      ("Straight lines", f"""
{proc('draw a straight line',
  'Choose the <b>Line</b> tool.',
  'Press where the line should start, drag to where it should end, and release.',
  'A line has no fill — only a colour and a width, both set on the Style toolbar.')}
{fig(IM.get('lines_demo'), 'Straight lines of different weights and colours, a flowing freehand curve, and a closed and an open pen shape.')}
<p>A line is the simplest object there is: two points, a colour and a thickness. Set the <b>Width</b> high
for a bold rule, or to 1 for a hairline.</p>"""),
      ("Freehand drawing", f"""
<p>The <b>Freehand</b> tool is a pencil: it records your pointer's path as you drag, giving a natural,
hand-drawn stroke.</p>
{proc('draw a freehand stroke',
  'Choose the <b>Freehand</b> tool.',
  'Press and hold, then draw — the line follows your pointer exactly.',
  'Release to finish. The stroke becomes a path object you can recolour, re-weight, move or delete.')}
{tip('Freehand is ideal for signatures, sketchy underlines, loose doodles and the organic lines that a perfectly straight tool cannot give you. Zoom in first for finer control.')}"""),
      ("The Pen: point-by-point polylines", f"""
<p>The <b>Pen</b> tool builds a shape one corner at a time — the precise way to draw an exact outline, a
polygon, a zig-zag or a many-sided star of your own.</p>
{proc('draw with the Pen',
  'Choose the <b>Pen</b> tool.',
  'Click once for each corner; a line follows your pointer so you can see the next segment before you place it.',
  'To finish as a <b>closed, filled</b> shape, <b>double-click</b> — the outline joins up and fills with the current fill colour.',
  'To finish as an <b>open line</b> instead, press ' + K('Enter') + ' — the points stay joined but the shape is not closed and not filled.')}
{note('A closed pen shape behaves like any other filled object — it takes a fill, an outline and effects. An open pen line behaves like a multi-segment line. Choose which you want by how you finish: double-click to close, ' + K('Enter') + ' to leave open.')}""")]))

    ch.append(("Editing Nodes and Curves",
      "<p class='lede'>Straight segments only take a drawing so far. The <b>Pen</b> tool draws true "
      "<b>Bézier curves</b>, and the <b>Node</b> tool reshapes any path by dragging its nodes and control "
      "handles — the heart of precise vector drawing. Any shape can be turned into an editable curve with "
      "<b>Convert to Curves</b>.</p>", [
      ("Drawing curves with the Pen", f"""
<p>The <b>Pen</b> tool lays down a path one <b>node</b> at a time. How you place each node decides the
shape of the curve that flows through it:</p>
{proc('draw a Bézier curve',
  'Choose the <b>Pen</b> tool.',
  '<b>Click</b> to drop a <b>corner</b> node — the path turns sharply through it.',
  '<b>Click and drag</b> to drop a <b>smooth</b> node — dragging pulls out a pair of control handles, and the path curves gracefully through the node.',
  'Carry on clicking and dragging to build the path; a live preview follows your pointer.',
  '<b>Double-click</b> to finish as a <b>closed, filled</b> shape, or press ' + K('Enter') + ' to finish as an <b>open</b> curve.')}
{fig(IM.get('bezier_blob'), 'A smooth closed shape drawn entirely with the Pen — every corner is a smooth node with symmetric control handles, so the outline flows as true Bézier curves.')}
{note('A curve drawn this way is stored as real cubic Bézier segments and exported as an SVG <b>&lt;path d="M… C…"&gt;</b>, so it stays perfectly smooth at any size and in any browser.')}"""),
      ("Reshaping with the Node tool", f"""
<p>The <b>Node</b> tool (second in the palette) edits an existing path. Click a node path to show its
nodes as little squares and its control handles as small circles on stalks.</p>
{proc('reshape a path',
  'Choose the <b>Node</b> tool and click the path you want to edit.',
  'Drag a <b>node</b> (a square) to move that point of the path.',
  'Drag a <b>control handle</b> (a circle) to change how the curve bends into and out of the node — a smooth node keeps its two handles mirrored, for an unbroken curve.')}
{fig(IM.get('curves_demo'), 'A flowing Bézier curve (left) and a star converted to an editable node path (right) — both reshape by dragging their nodes and handles.')}
{tip('A smooth node gives a graceful, continuous curve; a corner node gives a sharp change of direction. Mix the two along one path for shapes that are part curved, part angular.')}"""),
      ("Convert to Curves", f"""
<p>Any ordinary object — a rectangle, an ellipse, a QuickShape, a line or a pen shape — can be turned into
an editable node path, so you can push its outline about freely.</p>
{proc('convert a shape to curves',
  'Select the object with the <b>Select</b> tool.',
  'Choose <b>Edit ▸ Convert to Curves</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K('C') + ').',
  'The shape becomes a node path and the <b>Node</b> tool switches on, ready for you to reshape it.')}
{note('Converting an ellipse gives four smooth nodes with Bézier handles — the mathematically exact curve — so you can pull a circle into an egg, a leaf or a teardrop. Converting a rectangle or a QuickShape gives corner nodes you can round off or drag into a new outline.')}""")]))

    ch.append(("Placing Pictures",
      "<p class='lede'>A vector drawing can hold <b>photographs and bitmaps</b> too. The <b>Image</b> tool "
      "brings a picture onto the canvas as an object you can move, resize, rotate and layer like any "
      "other — ideal for a logo photo, a texture, or a scan to trace over.</p>", [
      ("Importing an image", f"""
{proc('place a picture on the canvas',
  'Choose the <b>Image</b> tool (the picture icon at the foot of the tool palette) and click on the canvas — or choose <b>File ▸ Import Image…</b>.',
  'Pick a <b>PNG, JPEG, GIF, BMP</b> or <b>WebP</b> file.',
  'The picture appears, scaled to fit the canvas and left selected, ready to position.')}
{fig(IM.get('image_demo'), 'A placed picture (left), the same image given an outline, and a copy at reduced opacity (right) — an imported image behaves like any other object.')}
<p>Because an image is an object, you <b>move</b> it, <b>resize</b> it by dragging its handles, <b>rotate</b>
it, put it on a <b>layer</b>, and stack it in front of or behind your shapes.</p>"""),
      ("How images are stored", f"""
<p>When you import a picture, DRAWmaster <b>embeds it inside the drawing</b> — the file's data travels with
the SVG as a self-contained <b>data URI</b>. That means a saved drawing is a single file you can move or
share without losing its pictures.</p>
{note('An image is written into the exported SVG as a real <b>&lt;image&gt;</b> element with its embedded data, so the drawing opens complete in a browser or another program — nothing to link, nothing to lose.')}
{tip('Place a photo or a scanned sketch on a lower layer, drop its opacity, and draw over the top with the Pen and shapes — a quick way to trace a picture into clean vector artwork.')}""")]))

    ch.append(("Working with Text",
      "<p class='lede'>The <b>Text</b> tool adds <i>artistic text</i> — words that are a drawing object in "
      "their own right, so they take a fill, an outline, a gradient and effects exactly like a shape, and "
      "stay perfectly sharp at any size.</p>", [
      ("Adding text", f"""
{proc('add a line of text',
  'Choose the <b>Text</b> tool (the <b>T</b> at the foot of the tool palette).',
  'Click on the canvas where the text should begin.',
  'In the dialog, type your <b>text</b>, choose a <b>font</b> — every font bundled with the suite is offered, alongside your system fonts — and set a pixel <b>size</b>.',
  'Click <b>OK</b>. The text appears in the current fill colour and is left selected.')}
{fig(dlg('Add Text'), 'The Add Text dialog: the words, the font and the size.')}
{fig(IM.get('text_demo'), 'Artistic text: a solid heading, an outline-only line, and text filled with a gradient — all sharp vector type.')}
<p>Because text is a true object, you move it, recolour it, outline it and give it a shadow or glow just as
you would a shape — and it is exported as real, selectable <b>&lt;text&gt;</b> in the SVG, so it stays
crisp and searchable on the web.</p>"""),
      ("Editing and styling text", f"""
{proc('change the words, font or size',
  'Select the text object with the <b>Select</b> tool.',
  'Choose <b>Edit ▸ Edit Text…</b>.',
  'Change the text, font or size, and click <b>OK</b>.')}
{fig(dlg('Edit Text'), 'Edit Text re-opens the same dialog to change an existing text object.')}
<p>Set the <b>Fill</b> for the colour of the letters and, if you want an outlined look, give it a <b>Line</b>
colour and a <b>Width</b>. A <b>gradient</b> fill and the shadow/glow <b>Effects</b> both apply to text too.</p>
{tip('Outline-only text — no fill, a bold line colour and a wide width — gives a clean “stencil” headline; a gradient fill gives a bright, modern title.')}"""),
      ("Fitting text to a path", f"""
<p>Text need not run in a straight line. <b>Fit Text to Path</b> attaches a line of artistic text to a
line, a freehand or pen path, or a Bézier curve, so the letters flow along it — for a curved headline, a
badge rim, a ribbon or a wave.</p>
{proc('flow text along a path',
  'Draw the <b>path</b> the text should follow — a line, a freehand or pen stroke, or a Bézier curve (and convert a shape to curves first if you want to run text round it).',
  'Add a line of <b>Text</b> as usual.',
  'With the <b>Select</b> tool, select <b>both</b> the text and the path (click one, then ' + K('Shift') + '-click the other).',
  'Choose <b>Text ▸ Fit Text to Path</b>. The glyphs lay themselves along the path, each turned to follow its direction.')}
{fig(IM.get('textpath_demo'), 'A line of artistic text flowed along an arc with Fit Text to Path — each letter sits on the curve and turns to follow it.')}
<p>The text keeps its fill, outline and font; change the words with <b>Edit Text</b> and they re-flow along
the same path. To straighten it out again, choose <b>Text ▸ Detach Text from Path</b>.</p>
{note('Text on a path is written into the exported SVG as a real <b>&lt;textPath&gt;</b> following a path definition, so the curved text renders — and stays selectable — in a web browser.')}
{tip('Flow text around a circle you have converted to curves for a classic round “seal” or stamp; flow it along a gentle wave for a lively banner headline.')}""")]))

    ch.append(("Selecting and Moving Objects",
      "<p class='lede'>Once something is on the canvas you will want to pick it up, move it, and get rid "
      "of mistakes. Those moves all start with the Select tool.</p>", [
      ("Selecting an object", f"""
{proc('select an object',
  'Choose the <b>Select</b> tool (the pointer at the top of the palette).',
  'Click an object. A dashed blue box appears around it to show it is selected.',
  'Click a different object to select that one instead, or click empty canvas to deselect.')}
{fig(IM.get('select_demo'), 'Four objects on the canvas; clicking one with the Select tool frames it with a dashed highlight.')}
{note('Clicking picks the <i>topmost</i> object under the pointer — the one drawn most recently. To reach something behind it, move the object on top out of the way first.')}"""),
      ("Moving an object", """
<p>With the <b>Select</b> tool, press on a selected object and drag it to a new place; release to drop it.
The whole object moves together, keeping its size, colour and any effects. The status bar shows the
pointer's position as you go, so you can line something up against a coordinate.</p>"""),
      ("Deleting an object", f"""
{proc('delete an object',
  'Select it with the <b>Select</b> tool.',
  'Press ' + K('Delete') + ' (or ' + K('Backspace') + '). The object is removed.',
  'Changed your mind? <b>Edit ▸ Undo</b> (' + K('Ctrl') + '+' + K('Z') + ') brings it straight back.')}""")]))

    ch.append(("Transforming Objects",
      "<p class='lede'>Selecting an object does more than let you move it. With the <b>Select</b> tool a "
      "selected object shows a frame of <b>handles</b> — eight around the edge to resize it, and one above "
      "to spin it round. Resizing and rotating are the two <i>transforms</i> every object can take.</p>", [
      ("The selection handles", f"""
<p>Click an object with the <b>Select</b> tool and a blue frame appears, studded with handles: a small
square at each <b>corner</b> and at the middle of each <b>edge</b>, and a round <b>rotate</b> handle on a
short stalk above the top edge.</p>
{fig(IM.get('canvas_handles'), 'A selected object shows eight square resize handles around its frame and a round rotate handle above — here on a drawing with the grid and two guides switched on.')}
<p>The frame (and every handle) turns with the object, so once something is rotated its handles still line
up with its own edges — resizing stays intuitive however far it has been spun.</p>"""),
      ("Resizing an object", f"""
{proc('resize an object',
  'Select it with the <b>Select</b> tool.',
  'Drag a <b>corner</b> handle to resize both ways at once, or an <b>edge</b> handle to stretch along one axis only.',
  'Hold ' + K('Shift') + ' while dragging a corner to resize <b>proportionally</b>, keeping the original shape’s aspect ratio.',
  'Release when it is the size you want.')}
{fig(IM.get('resize_demo'), 'The same rectangle: left at its drawn size, centre stretched larger, right rotated.')}
{note('Resizing text scales its <b>point size</b> rather than squashing the letters, so type stays properly proportioned. A line or path scales by stretching the gaps between its points.')}"""),
      ("Rotating an object", f"""
{proc('rotate an object',
  'Select it, then drag the round <b>rotate</b> handle on the stalk above the top edge.',
  'The object turns about its centre as you drag; the status bar and frame follow it round.',
  'Hold ' + K('Shift') + ' to snap the angle to convenient 15° steps.')}
{fig(IM.get('transform_demo'), 'One arrow QuickShape rotated to a run of angles — 0°, 20°, 45°, 90° and 135° — each spun about its own centre.')}
<p>Rotation is stored with the object as an angle, so it survives a save and re-open, and it is written into
the exported SVG as a real transform — a shape rotates with a transform matrix, a piece of text with an
explicit <b>rotate()</b> — so it renders identically on screen, in a PNG and in any web browser.</p>
{tip('Rotation and resize combine freely: stretch a shape to the proportions you want first, then spin it to the angle you need. Undo (' + K('Ctrl') + '+' + K('Z') + ') steps back through each transform.')}"""),
      ("Flipping (mirroring)", f"""
<p><b>Flipping</b> mirrors an object — turning it into its own reflection. It is the quick way to make a
left-facing shape face right, or to build a symmetrical pair.</p>
{proc('flip an object',
  'Select one or more objects with the <b>Select</b> tool.',
  'Choose <b>Arrange ▸ Flip Horizontal</b> to mirror left-to-right,',
  'or <b>Arrange ▸ Flip Vertical</b> to mirror top-to-bottom.')}
{fig(IM.get('flip_demo'), 'An asymmetric shape (left) and its horizontal mirror (right) — Flip Horizontal reflects the artwork about the selection’s centre.')}
{note('Flipping mirrors the whole selection about its combined centre, so flipping several objects together keeps their arrangement and mirrors it as one.')}""")]))

    ch.append(("Duplicating, Cloning and Locking",
      "<p class='lede'>Three housekeeping commands make a busy drawing easier to manage: <b>Duplicate</b> "
      "makes an instant copy, and <b>Lock</b> pins an object down so you cannot select or move it by "
      "accident.</p>", [
      ("Duplicating an object", f"""
<p><b>Duplicate</b> (sometimes called <i>clone</i>) makes an exact copy of the selection, offset a little so
you can see it — the fastest way to build a row of identical buttons, a scatter of stars, or a repeated
motif.</p>
{proc('duplicate the selection',
  'Select one or more objects with the <b>Select</b> tool.',
  'Choose <b>Edit ▸ Duplicate</b> (' + K('Ctrl') + '+' + K('D') + ').',
  'A copy appears, nudged down and to the right, and is left selected — drag it into place, or duplicate again for a cascade.')}
{fig(IM.get('duplicate_demo'), 'One star duplicated three times, each copy offset — Ctrl+D is the quick way to repeat a motif.')}
{note('A duplicate is a fully independent object — recolour or reshape it without touching the original. Duplicating a <b>group</b> copies the whole group as a new, separate group.')}"""),
      ("Locking and unlocking", f"""
<p><b>Locking</b> an object pins it to the canvas: a locked object cannot be clicked, selected, dragged or
rubber-band-picked, so it stays put while you work on everything around it. It is ideal for a background,
a template or a traced reference you want to draw over without nudging.</p>
{proc('lock and unlock',
  'Select the object (or objects) you want to protect.',
  'Choose <b>Arrange ▸ Lock / Unlock</b> (' + K('Ctrl') + '+' + K('L') + '). The object is now locked and cannot be selected by clicking.',
  'To work on it again, it is still listed — select it through its layer, or choose <b>Lock / Unlock</b> again while it is selected to release it.')}
{fig(IM.get('lock_demo'), 'A locked backdrop rectangle (behind) stays put while the star and ellipse in front are moved freely — clicks pass straight through the locked object.')}
{caution('Because a locked object ignores clicks, the quickest way to reach it again is to put it on its own layer (see “Layers”), so you can always find and unlock it.')}""")]))

    ch.append(("Fill, Line and Width",
      "<p class='lede'>Every shape in DRAWmaster has two coats of colour — a <b>fill</b> inside and an "
      "<b>outline</b> around — plus an outline <b>width</b>. Those three controls, all on the Style "
      "toolbar, carry most of a drawing's style.</p>", [
      ("Setting the fill colour", f"""
{proc('set a fill colour',
  'Click the <b>Fill</b> button on the Style toolbar.',
  'Pick a colour in the colour dialog — drag in the wheel, type a hex value, or set the <b>alpha</b> (opacity) slider for a see-through fill.',
  'Click <b>OK</b>. If an object is selected, its fill changes at once; otherwise the colour waits for the next shape you draw.')}
{fig(IM.get('fillstroke_demo'), 'Four rectangles in different fills (top), and the same line at three different widths (below).')}
{note('The Fill button is tinted with the current fill colour, so you can always see what the next shape will be filled with.')}"""),
      ("Setting the line colour", f"""
{proc('set a line (outline) colour',
  'Click the <b>Line</b> button on the Style toolbar.',
  'Pick a colour and click <b>OK</b>.')}
<p>The outline sits around the edge of a shape (or <i>is</i> the whole of a line or an open pen path). A
dark, thin outline makes a shape crisp; a thick, contrasting one makes it bold.</p>"""),
      ("Setting the outline width", f"""
<p>The <b>Width</b> spin box on the Style toolbar sets the outline thickness in pixels.</p>
{proc('change the outline width',
  'Select the object (or set the width before drawing).',
  'Type a number in the <b>Width</b> box, or click its up/down arrows.',
  'A width of <b>0</b> removes the outline entirely — useful for a shape that should be a pure block of colour.')}
{tip('A shape with a bold fill and no outline (width 0) reads as a clean, modern block; a shape with no fill and a thick outline reads as a frame or a ring. The three ways — fill only, outline only, both — are shown together below.')}
{fig(IM.get('style_demo'), 'The same star three ways: filled with no outline, outline only, and both; and a bar with no outline, a thin one and a thick one.')}""")]))

    ch.append(("Gradient and Texture Fills",
      "<p class='lede'>Instead of a single flat colour, a shape can be filled with a <b>gradient</b> — a "
      "smooth blend between two colours — or with a <b>texture</b>: a tiled or stretched image. DRAWmaster "
      "offers a <b>linear</b> and a <b>radial</b> gradient, and a <b>texture / pattern fill</b> drawn from "
      "an image file or your local texture library.</p>", [
      ("Applying a gradient", f"""
{proc('fill a shape with a gradient',
  'Select the shape with the <b>Select</b> tool — a rectangle, ellipse, QuickShape, a closed pen shape, or even a piece of text.',
  'Click <b>Gradient…</b> on the Style toolbar (or <b>Edit ▸ Gradient Fill…</b>).',
  'Choose <b>Linear</b> or <b>Radial</b>, pick the <b>start</b> and <b>end</b> colours, and for a linear gradient set the <b>angle</b>.',
  'Click <b>OK</b>. The gradient fills the shape, mapped across its bounding box.')}
{fig(dlg('Gradient Fill'), 'The Gradient Fill dialog: type, two colours, and the angle for a linear blend.')}
{fig(IM.get('gradient_demo'), 'Linear gradients at two angles, a radial gradient in an ellipse, and a gradient-filled star.')}
<p>A gradient is exported as a real SVG <b>&lt;linearGradient&gt;</b> or <b>&lt;radialGradient&gt;</b>, so it
renders identically on screen, in an exported PNG, and in any web browser — and it survives a save-and-reopen
with its colours and angle intact.</p>"""),
      ("Removing a gradient", f"""
<p>To go back to a flat fill, open <b>Gradient…</b> again and click <b>Remove gradient</b> — or simply click
the <b>Fill</b> button and pick a solid colour, which replaces the gradient.</p>
{tip('A radial gradient from a pale centre to a deep edge gives a shape a soft, rounded, “lit” look; a linear gradient at a shallow angle makes a clean modern background bar.')}"""),
      ("Texture and pattern fills", f"""
<p>A shape can also be filled with a <b>texture</b> — an image painted inside its outline. DRAWmaster can
<b>tile</b> the image (repeating it at its natural size) or <b>stretch</b> one copy to fill the shape's box,
and it can draw the picture from a file you choose <i>or</i> from your <b>local texture library</b> — a set
of categorised textures (wood, marble, brick, metal, paper, foliage and more) stored on your machine.</p>
{proc('fill a shape with a texture',
  'Select a shape with the <b>Select</b> tool — a rectangle, ellipse, QuickShape or a closed pen shape.',
  'Choose <b>Edit ▸ Texture / Pattern Fill…</b>.',
  'Either pick a <b>library category</b> and a <b>texture</b> from it, or click <b>Browse for an image file…</b> to use your own picture.',
  'Choose a <b>fill mode</b> — <b>Tile</b> to repeat the image, or <b>Stretch to fit</b> to scale one copy across the shape.',
  'Click <b>OK</b>. The texture fills the shape.')}
{fig(dlg('Texture / Pattern Fill'), 'The Texture / Pattern Fill dialog: a library category and texture, or a file you browse to, plus the tile/stretch mode.')}
{fig(IM.get('texture_demo'), 'A star with a tiled texture fill (left) and a rectangle with the same texture stretched to fit (right).')}
<p>The chosen image is <b>embedded</b> in the drawing as a self-contained data URI, exactly like a placed
picture — so a texture-filled shape travels with the file and survives a save-and-reopen. In the exported
SVG the texture becomes a real <b>&lt;pattern&gt;</b> with an embedded <b>&lt;image&gt;</b>, so it renders
in any browser.</p>
{note('The texture library is read live from <code>~/.local/share/justapps/textures</code> if it is present on your machine; DRAWmaster never copies it into itself. If the folder is absent the dialog simply offers the <b>Browse for an image file…</b> route instead.')}
{tip('A texture fill replaces a gradient (and vice versa). To go back to a flat colour, open the dialog and click <b>Remove texture</b>, or pick a solid <b>Fill</b> colour.')}""")]))

    ch.append(("Opacity, Dashes, Arrowheads and Combining Shapes",
      "<p class='lede'>A handful of finishing controls give a drawing polish: making an object <b>see-through</b>, "
      "styling a line as <b>dashed</b> or <b>dotted</b> or tipping it with an <b>arrowhead</b>, and welding "
      "several shapes into one with the <b>Combine</b> commands.</p>", [
      ("Object opacity", f"""
<p>Every object can be made partly transparent, so whatever lies behind it shows through — useful for
soft overlays, tints and layered washes of colour.</p>
{proc('set an object’s opacity',
  'Select the object with the <b>Select</b> tool.',
  'Choose <b>Edit ▸ Opacity…</b> and set a value from <b>0</b> (invisible) to <b>100</b> (solid).',
  'Click <b>OK</b>.')}
{fig(IM.get('opacity_demo'), 'Three discs, each at about half opacity — where they overlap the colours blend, because each lets the others show through.')}
{note('Opacity is saved with the object and written into the exported SVG as an <b>opacity</b> value, so it renders the same on screen, in a PNG and in a browser.')}"""),
      ("Dashed and dotted lines", f"""
<p>A line, a freehand or pen path, or a node path can be drawn <b>solid</b>, <b>dashed</b> or <b>dotted</b>
— and tipped with an <b>arrowhead</b> at one or both ends, for connectors, pointers and diagrams.</p>
{proc('style a line’s dashes and arrowheads',
  'Select a line, a path or a node path.',
  'Choose <b>Edit ▸ Line Style (Dashes &amp; Arrows)…</b>.',
  'Pick a <b>dash style</b> — solid, dashed or dotted — and an <b>arrowhead</b> option — none, start, end or both ends.',
  'Click <b>OK</b>.')}
{fig(dlg('Line Style — Dashes & Arrowheads'), 'The Line Style dialog sets the dash pattern and the arrowheads for the selected line or path.')}
{fig(IM.get('dash_demo'), 'Solid, dashed and dotted lines, a line with an arrowhead at the end, and a dashed double-headed arrow.')}
<p>The dash pattern scales with the line's width, and an arrowhead is drawn in the line's own colour — both
are written into the exported SVG, so a dashed arrow looks the same everywhere.</p>"""),
      ("Combining shapes", f"""
<p>The <b>Combine</b> commands weld two or more overlapping shapes into a single editable outline, using
the three classic boolean operations.</p>
{proc('combine shapes',
  'Select <b>two or more</b> overlapping shapes.',
  'Choose <b>Arrange ▸ Combine ▸ Union</b> to merge them into one outline,',
  '<b>Subtract</b> to cut the upper shapes out of the lowest one,',
  'or <b>Intersect</b> to keep only the area they all share.')}
<div class="catgrid">
<div class="cat-card">{fig(IM.get('combine_before'), 'Two overlapping shapes.')}</div>
<div class="cat-card">{fig(IM.get('combine_union'), 'Union — merged into one outline.')}</div>
<div class="cat-card">{fig(IM.get('combine_subtract'), 'Subtract — the upper shape cut away.')}</div>
<div class="cat-card">{fig(IM.get('combine_intersect'), 'Intersect — only the shared area.')}</div>
</div>
{note('The result is a single <b>node path</b>, so you can keep reshaping it with the Node tool, give it a gradient or an effect, or combine it again. It is the quick way to build a custom shape no single QuickShape provides.')}""")]))

    ch.append(("Dimension Lines and Connectors",
      "<p class='lede'>Two tools serve technical drawing — plans, diagrams and flow charts. A "
      "<b>dimension line</b> draws a measured line with end ticks and an automatic length label; a "
      "<b>connector</b> joins two objects with a line that stays attached as they move.</p>", [
      ("Drawing a dimension line", f"""
<p>A <b>dimension line</b> is the annotation you see on a plan: a line spanning a distance, capped with a
short tick at each end, and labelled with the length it measures. DRAWmaster works the length out for you
and keeps the label upright.</p>
{proc('draw a dimension line',
  'Choose the <b>Dimension line</b> tool from the tool palette.',
  'Press where the measurement should start, drag to where it should end, and release.',
  'The line appears with end ticks and a length label showing the distance in the current <b>measurement unit</b>.')}
{fig(IM.get('dim_demo'), 'A box measured on two sides with dimension lines — each shows end ticks and an automatic length label.')}
{note('The label reads out in whatever unit is set in <b>View ▸ Measurement Units</b> — pixels, millimetres or centimetres — and updates if you change the unit while a dimension line is selected.')}
{tip('Dimension lines are at their most useful over a plan drawn to a sensible scale — a room, a garden bed, a piece of furniture. Set the measurement unit to millimetres or centimetres first so the labels read in real-world terms.')}"""),
      ("Linking objects with connectors", f"""
<p>A <b>connector</b> is a line that is <i>anchored</i> to two objects. Move or resize either object and the
connector follows, staying attached — so a flow chart or a wiring diagram keeps its links intact however
you rearrange it.</p>
{proc('join two objects with a connector',
  'Choose the <b>Connector</b> tool.',
  'Press on the first object, drag to the second, and release. Each end that lands on an object anchors to it.',
  'Now switch to the <b>Select</b> tool and drag either object — the connector stretches to keep them joined.')}
{fig(IM.get('conn_demo'), 'Two boxes joined by a connector with an arrowhead. Drag either box and the connector follows, staying attached.')}
{note('An end that is dropped on empty canvas stays a free point; an end dropped on an object anchors to that object’s centre. Connectors are saved with the drawing and exported into the SVG as real lines.')}
{tip('Build a flow chart from a row of rectangles joined by connectors, then shuffle the boxes about to find the clearest layout — the connectors redraw themselves, so you never have to.')}""")]))

    ch.append(("Effects: Shadow and Glow",
      "<p class='lede'>Two filter effects lift an object off the flat canvas: a <b>drop shadow</b> that "
      "casts it forward, and an <b>outer glow</b> that haloes it. Both are set in one dialog and can be "
      "used together.</p>", [
      ("Adding a drop shadow", f"""
{proc('add a drop shadow',
  'Select the object with the <b>Select</b> tool.',
  'Click <b>Effects…</b> on the Style toolbar.',
  'Tick <b>Enable drop shadow</b>.',
  'Set the <b>offset across</b> and <b>offset down</b> (how far the shadow is thrown), the <b>blur</b> (how soft it is), the <b>strength</b> (how dark), and a <b>colour</b>.',
  'Click <b>OK</b>.')}
{fig(dlg('Effects — Shadow & Glow'), 'The Effects dialog controls a drop shadow and an outer glow together.')}
<p>A soft shadow a little down and to the right is the classic way to make a shape look as if it floats a
few millimetres above the page.</p>"""),
      ("Adding an outer glow", f"""
{proc('add an outer glow',
  'Select the object and open <b>Effects…</b>.',
  'Tick <b>Enable outer glow</b>.',
  'Set the <b>spread</b> (how far the glow reaches) and the <b>strength</b> (how strong), and a <b>colour</b>.',
  'Click <b>OK</b>.')}
{fig(IM.get('effects_demo'), 'A rectangle with a drop shadow, a star with a warm outer glow, and an ellipse that uses both at once.')}
<p>A glow in a bright, warm colour draws the eye to a highlight; a soft white glow lifts a shape off a
dark background. An object can carry a shadow <i>and</i> a glow at the same time — tick both.</p>"""),
      ("Removing an effect", """
<p>To take an effect off again, open <b>Effects…</b> and untick the box for the shadow or the glow, then
click <b>OK</b>. The effect is removed; the object itself is untouched.</p>""")]))

    ch.append(("Layers and Arranging Objects",
      "<p class='lede'>Every object sits in a stack, and newer objects cover older ones. Two tools control "
      "that stack: <b>z-order</b> commands that shuffle one object up or down, and <b>layers</b> that group "
      "objects so you can hide, reorder or re-home a whole set at once.</p>", [
      ("Stacking order (z-order)", f"""
<p>When objects overlap, the one drawn later sits on top. The <b>Arrange</b> menu lets you change which is
in front without redrawing anything.</p>
{proc('change the stacking order',
  'Select an object with the <b>Select</b> tool.',
  'Choose <b>Arrange ▸ Bring to Front</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K(']') + ') or <b>Send to Back</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K('[') + ') to jump it to the very top or bottom,',
  'or <b>Bring Forward</b> (' + K('Ctrl') + '+' + K(']') + ') / <b>Send Backward</b> (' + K('Ctrl') + '+' + K('[') + ') to move it one step at a time.')}
<div class="catgrid">
<div class="cat-card">{fig(IM.get('layers_demo'), 'Three overlapping shapes — the yellow rectangle is on top.')}</div>
<div class="cat-card">{fig(IM.get('layers_front'), 'The same three after Bring to Front on the star — now it leads.')}</div>
</div>"""),
      ("The Layers panel", f"""
<p>For anything more than a few objects, <b>layers</b> keep a drawing organised. A layer is a named,
show/hideable group; objects on a higher layer always sit above those on a lower one.</p>
{fig(IM.get('layerpanel'), 'The Layers panel: layers front-to-back, each with a show/hide tick, plus add, delete, reorder, rename and “move selection to layer”.', 'tall')}
<p>Open it from <b>Arrange ▸ Show Layers Panel</b> if it is closed. The panel lists layers with the
front-most at the top; the row's tick shows or hides that layer.</p>
{proc('work with layers',
  'Click <b>＋</b> to add a new layer, or <b>－</b> to delete the current one (and everything on it).',
  'Use <b>▲</b> and <b>▼</b> to move the selected layer up or down the stack — which changes the paint order.',
  'Click <b>✎</b> to rename a layer; untick its box to hide it.',
  'New objects are drawn onto the <b>currently selected</b> layer. To move an existing object, select it, then pick a layer from the <b>Selection →</b> list.')}
{note('Layers are saved inside the SVG along with the drawing, so a reopened file keeps its exact layer stack, names and visibility. Older DRAWmaster files that pre-date layers still open perfectly — every object simply lands on a single default layer.')}
{tip('A common scheme: a <i>Background</i> layer for a filled rectangle or gradient, a middle layer for the main shapes, and a <i>Text &amp; labels</i> layer on top — hide the text layer while you arrange the artwork, then show it again.')}""")]))

    ch.append(("Grouping, Aligning and Distributing",
      "<p class='lede'>Once a drawing has more than a handful of objects you will want to handle several at "
      "once — pick out a set, lock them together as a <b>group</b>, and line them up tidily with the "
      "<b>Align</b> and <b>Distribute</b> commands.</p>", [
      ("Selecting more than one object", f"""
<p>Every align, distribute and group command works on the <b>current selection</b> — so the first step is
always to select the objects you mean.</p>
{proc('select several objects',
  'Choose the <b>Select</b> tool.',
  'Click the first object, then <b>' + K('Shift') + '-click</b> each of the others to add it to the selection (Shift-click a selected one again to drop it).',
  'Or drag a <b>rubber-band box</b> across empty canvas — every object it touches is selected together.')}
{note('Dragging any object in a multiple selection moves the whole set at once, keeping their relative positions. Pressing ' + K('Delete') + ' removes them all.')}"""),
      ("Grouping objects", f"""
<p>A <b>group</b> binds a set of objects into one. Click any member and the whole group selects; move,
rotate or delete it and every member follows. It is the right tool for something built from several parts —
a logo, a signpost, a little character — that you want to treat as a single thing from then on.</p>
{proc('group and ungroup',
  'Select two or more objects.',
  'Choose <b>Arrange ▸ Group</b> (' + K('Ctrl') + '+' + K('G') + '). They become one group.',
  'To break it apart again, select the group and choose <b>Arrange ▸ Ungroup</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K('G') + ').')}
{fig(IM.get('group_demo'), 'Four shapes — a head, two eyes and a body — grouped so they move and rotate as one little robot.')}
{note('Groups are saved inside the SVG with the drawing, so a reopened file keeps every group intact.')}"""),
      ("Aligning objects", f"""
<p>The <b>Align</b> commands line selected objects up against a common edge or centre, worked out from the
selection itself — so <b>Align Left</b> moves them all to the leftmost edge in the set, <b>Align Middle</b>
centres them on a shared horizontal line, and so on.</p>
{proc('align a selection',
  'Select two or more objects.',
  'Open <b>Arrange ▸ Align</b> and choose <b>Left</b>, <b>Centre</b> or <b>Right</b> to line them up sideways,',
  'or <b>Top</b>, <b>Middle</b> or <b>Bottom</b> to line them up vertically.')}
<div class="catgrid">
<div class="cat-card">{fig(IM.get('align_before'), 'Four boxes scattered across the canvas.')}</div>
<div class="cat-card">{fig(IM.get('align_after'), 'The same four after Align Left and Distribute Vertically — flush to a common edge and evenly spaced.')}</div>
</div>"""),
      ("Distributing objects", f"""
<p>Where Align lines objects up, <b>Distribute</b> spaces them out evenly. Give it three or more objects
and it keeps the two outermost where they are, then slides the ones between so the gaps are equal.</p>
{proc('distribute a selection',
  'Select <b>three or more</b> objects.',
  'Choose <b>Arrange ▸ Distribute ▸ Horizontally</b> to even out their left-to-right spacing,',
  'or <b>Distribute ▸ Vertically</b> to even out their top-to-bottom spacing.')}
{tip('Align then distribute is the quickest way to tidy a row of buttons, a column of labels or a grid of icons: align them to a shared edge first, then distribute to space them evenly.')}""")]))

    ch.append(("Grid, Guides and Snapping",
      "<p class='lede'>Precision work is far easier with something to line things up against. DRAWmaster "
      "offers a <b>grid</b>, draggable <b>guides</b>, and <b>snapping</b> that pulls objects neatly into "
      "place against the grid, the guides and each other. None of it prints — it is drawing scaffolding "
      "only.</p>", [
      ("Showing the grid", f"""
<p>The <b>grid</b> is a faint mesh of lines across the canvas, a ruler you can see.</p>
{proc('show the grid and set its spacing',
  'Choose <b>View ▸ Show Grid</b> (' + K('Ctrl') + '+' + K("'") + ') to switch it on or off.',
  'Choose <b>View ▸ Grid Spacing…</b> and type the gap between lines in pixels.')}
{fig(IM.get('canvas_handles'), 'The canvas with the grid switched on — a faint mesh you can line objects up against. It never appears in an exported PNG or SVG.')}
{note('The grid is purely a guide for your eye and for snapping. It never appears in an exported PNG or SVG — the output shows only your artwork.')}"""),
      ("Adding guides", f"""
<p><b>Guides</b> are individual lines — one across, one down — that you place exactly where you want a
shared edge or centre-line to be, then line objects up against.</p>
{proc('add and clear guides',
  'Choose <b>View ▸ Add Horizontal Guide…</b> or <b>Add Vertical Guide…</b>.',
  'Type the position in pixels and click <b>OK</b>; a dashed guide line appears.',
  'Choose <b>View ▸ Clear Guides</b> to remove them all.')}
{fig(IM.get('canvas_handles'), 'A canvas with the grid on and two guides placed — a dashed vertical and a dashed horizontal — ready to snap objects against.')}"""),
      ("Snapping", f"""
<p>With <b>snapping</b> on, an object you move or resize jumps the last few pixels to line up with the
nearest grid line, guide, or the edge or centre of another object — so things sit flush without you having
to be pixel-perfect by hand.</p>
{proc('use snapping',
  'Make sure <b>View ▸ Snap to Grid &amp; Guides</b> is ticked (it is on by default).',
  'Switch on the grid, or add a guide or two, to give snapping something to catch on.',
  'Drag an object near a grid line, a guide or another object’s edge — it snaps into alignment as you release.')}
{tip('Snapping reads an object’s edges <i>and</i> its centre, and the same for its neighbours — so you can snap two shapes centre-to-centre, or butt one flush against another, as easily as snapping to the grid.')}
{caution('If a shape refuses to sit exactly where you drop it, that is snapping doing its job. Turn it off from <b>View ▸ Snap to Grid &amp; Guides</b> for free-hand placement, then turn it back on.')}"""),
      ("Measurement units", f"""
<p>The status bar and every dimension-line label can read out in <b>pixels</b>, <b>millimetres</b> or
<b>centimetres</b>. The drawing itself is always stored in pixels — the unit only changes how lengths are
<i>shown</i>, so switching units never moves or resizes anything.</p>
{proc('choose a measurement unit',
  'Open <b>View ▸ Measurement Units</b>.',
  'Choose <b>Pixels</b>, <b>Millimetres</b> or <b>Centimetres</b>.',
  'The pointer read-out in the status bar switches at once, and any selected dimension line re-labels itself in the new unit.')}
{note('DRAWmaster converts at 96 pixels to the inch (so 96 px = 25.4 mm = 2.54 cm) — the standard screen resolution, and the same convention its PDF export uses. For a drawing whose pixel size you have chosen to match a real sheet, the millimetre and centimetre read-outs are true to size.')}
{tip('Working on a plan or a technical drawing? Switch to millimetres or centimetres before you add dimension lines, so every measured label reads in real-world units.')}""")]))

    ch.append(("Undo, Redo and Working Safely",
      "<p class='lede'>Drawing is a process of trying things. DRAWmaster keeps a deep history of your "
      "changes, so you can experiment freely and step back whenever something does not work.</p>", [
      ("Undo and redo", f"""
<p>Nearly everything you do — drawing a shape, moving it, recolouring it, adding an effect, deleting
something — is recorded.</p>
{proc('step back and forward through your work',
  'Choose <b>Edit ▸ Undo</b> (' + K('Ctrl') + '+' + K('Z') + ') to reverse the last change.',
  'Keep pressing to walk back through the history, step by step.',
  'Choose <b>Edit ▸ Redo</b> (' + K('Ctrl') + '+' + K('Shift') + '+' + K('Z') + ') to re-apply a change you undid.')}
{note('The history holds many steps, so you can undo a whole run of changes — not just the most recent one. Starting a fresh change, though, clears the “redo” branch from that point on.')}"""),
      ("A safe way to work", """
<p>Because Undo is deep and reliable, the best way to learn DRAWmaster is to <b>try things</b>. Draw a
shape, recolour it, pile on a shadow and a glow, drag it about — and if you do not like the result, undo
back to where you were. Save often (<b>Ctrl+S</b>) once a drawing is going well, so you always have a
known-good version to return to.</p>""")]))

    parts.append(("Part II", "Core Skills", ch))

    # ============================================================ PART III
    ch = []
    ch.append(("Project: A Simple Logo",
      "<p class='lede'>This project builds the badge-style logo you have seen in this guide, from an empty "
      "canvas to a finished mark — putting the skills of Part II to work in order: QuickShapes, fills and "
      "outlines, and effects.</p>", [
      ("Start with a backing shape", f"""
{proc('lay the foundation',
  'Choose <b>File ▸ New…</b> and a square 800 × 800 canvas — logos suit a square.',
  'Pick a deep colour on the <b>Fill</b> button and a darker one on <b>Line</b>, with a wide <b>Width</b>.',
  'From the <b>Shape</b> list choose <b>Octagon</b> and drag out a large backing shape.',
  'Open <b>Effects…</b> and give it a soft drop shadow so it lifts off the page.')}
{fig(IM.get('logo1'), 'Step 1 — an octagon backing shape with a drop shadow.')}"""),
      ("Add the central symbol", f"""
<p>Now place the mark the logo is built around — here, a star.</p>
{proc('add the central symbol',
  'Set a bright <b>Fill</b> (a warm gold) and a matching <b>Line</b>.',
  'Choose the <b>Star (5-point)</b> QuickShape and drag it out, centred on the octagon.',
  'Open <b>Effects…</b> and add a gentle <b>outer glow</b> in a pale version of the fill, so the star seems to shine.')}
{fig(IM.get('logo2'), 'Step 2 — a glowing star sits on the backing shape.')}"""),
      ("Finish with supporting shapes", f"""
<p>A few supporting shapes round the logo out — a heart and a speech bubble here, each in its own colour.</p>
{proc('add the finishing shapes',
  'Draw a <b>Heart</b> QuickShape in a strong accent colour.',
  'Draw a <b>Speech bubble</b> with a white fill and a coloured outline.',
  'Nudge each into place with the Select tool until the arrangement feels balanced.')}
{fig(IM.get('logo3'), 'Step 3 — supporting shapes complete the arrangement.')}"""),
      ("Export and reuse", f"""
<p>With the logo finished, save it and export it for use elsewhere.</p>
{proc('save and export the logo',
  'Choose <b>File ▸ Save as SVG…</b> so you can re-open and edit it later.',
  'Choose <b>File ▸ Export PNG…</b> for a ready-to-use bitmap — to drop into a document, a website or an email.')}
{fig(IM.get('logo_demo'), 'The finished logo — ready to save as an editable SVG and export as a PNG.')}
{tip('Keep the SVG as your master. If the brand colour ever changes, re-open it, recolour the shapes and re-export — no quality is ever lost, because it is vector.')}""")]))

    ch.append(("Project: An Icon and a Diagram",
      "<p class='lede'>Two more short projects show the range of a vector tool: a clean app-style icon, "
      "and a simple flow diagram built from shapes and arrows.</p>", [
      ("A clean icon", f"""
<p>An icon is a logo stripped to its simplest: one strong shape, one clear symbol, no clutter.</p>
{proc('draw a flat icon',
  'Start from a square canvas.',
  'Draw a <b>Rectangle</b> that fills most of the canvas, with a bold fill and no outline (<b>Width 0</b>) — the rounded modern look.',
  'Draw one simple symbol on top — a QuickShape such as a <b>Lightning bolt</b>, <b>Heart</b> or <b>Star</b> — in white or a contrasting colour.',
  'Export a PNG at the size you need it.')}
{caution('An icon is read at a tiny size. Resist adding detail that will vanish when it is 32 pixels wide — one shape and one symbol is usually plenty.')}"""),
      ("A flow diagram", f"""
<p>Vector shapes and arrows make a tidy diagram that you can always rearrange.</p>
{proc('build a flow diagram',
  'Draw a row of <b>Rectangles</b> (or ellipses) for the steps, all the same fill.',
  'Between each pair, draw an <b>Arrow</b> QuickShape, or a <b>Line</b>, pointing from one to the next.',
  'Use the <b>Pen</b> tool for a branch that bends around a corner.',
  'Keep the fills to two or three colours so the diagram reads calmly.')}
{tip('Because every box and arrow is a separate object, you can drag a step to a new place and redraw just the arrows around it — far quicker than redrawing the whole diagram.')}""")]))

    parts.append(("Part III", "Worked Projects", ch))

    # ============================================================ PART IV
    ch = []
    ch.append(("Exporting and Sharing",
      "<p class='lede'>A finished drawing is meant to be used — on a web page, in a document, in an "
      "email, or touched up as a photo. DRAWmaster exports to the two formats that cover all of those.</p>", [
      ("Saving an editable SVG", f"""
<p><b>SVG</b> is DRAWmaster's own save format — a vector file that stays editable.</p>
{proc('save as SVG',
  'Choose <b>File ▸ Save as SVG…</b> (' + K('Ctrl') + '+' + K('S') + ').',
  'Name it and save. The drawing goes to your <i>Documents/just a…</i> folder by default.')}
{note('A DRAWmaster SVG is a genuine, standard SVG — a browser or another vector program will display it. DRAWmaster also tucks its full editable object list inside, so <i>it</i> can re-open the file with every shape intact. Edit a DRAWmaster SVG in another program and that editable copy may no longer match, so keep DRAWmaster’s SVG as your master.')}"""),
      ("Exporting a PNG", f"""
<p>A <b>PNG</b> is a bitmap — the right format when you need a fixed-size picture to drop into a document,
a website, a chat or an email, where SVG might not be accepted.</p>
{proc('export a PNG',
  'Choose <b>File ▸ Export PNG…</b>.',
  'Name it and save. It is written at the canvas’s pixel size, on a white background, into your <i>Pictures/just a…</i> folder by default.')}
{tip('Need the PNG bigger and still crisp? Start a larger canvas (or scale the whole drawing up) before exporting — because the drawing is vector, a larger export is just as sharp, unlike enlarging a PNG after the fact.')}"""),
      ("Touching up in PAINTcanvas", f"""
<p>When a finished drawing needs raster-style work — a textured background, a photographic blend, a filter
— DRAWmaster hands it to its sister app.</p>
{proc('edit a drawing in PAINTcanvas',
  'Choose <b>File ▸ Edit in PAINTcanvas…</b>.',
  'DRAWmaster rasterises the drawing to a PNG and opens it in PAINTcanvas.',
  'Do your pixel-level work there and save.')}
{caution('This is a <b>one-way</b> trip: a drawing becomes a bitmap when it crosses to PAINTcanvas, and a bitmap cannot be broken back into editable vector shapes. Keep your SVG master so you can always go back to the editable version.')}""")]))

    ch.append(("Exporting to PDF and Printing",
      "<p class='lede'>For a page you mean to print, hand over or archive, DRAWmaster writes a <b>vector "
      "PDF</b> — and can send the drawing straight to a <b>printer</b>. Both keep the artwork sharp: text "
      "stays text and shapes stay crisp paths, at any size.</p>", [
      ("Exporting a PDF", f"""
<p>A <b>PDF</b> is the universal document format — it opens anywhere, prints faithfully, and (because
DRAWmaster writes it as <i>vector</i>) stays razor-sharp however far it is zoomed or scaled.</p>
{proc('export a PDF',
  'Choose <b>File ▸ Export PDF…</b>.',
  'Name the file and save. The PDF is written at the canvas size, into your <i>Documents/just a…</i> folder by default.')}
{note('The PDF is painted through the same engine that draws the screen, so every shape, gradient, effect, image and piece of text appears exactly as it does on the canvas — and text is real, selectable text in the PDF, not a picture of letters.')}
{tip('A vector PDF is the right thing to send to a print shop or to drop into a report: it scales to any paper size without a hint of blur.')}"""),
      ("Printing", f"""
<p>You can also print a drawing directly from DRAWmaster.</p>
{proc('print a drawing',
  'Choose <b>File ▸ Print…</b> (' + K('Ctrl') + '+' + K('P') + ').',
  'Pick your printer and page options in the print dialog.',
  'Click <b>Print</b>. The drawing is scaled to fit the page and printed as sharp vector artwork.')}
{caution('The drawing is sized to fit the selected paper while keeping its proportions — so a wide canvas prints landscape-wide on the page, with a margin above and below. Choose a matching paper orientation for the fullest use of the sheet.')}""")]))

    parts.append(("Part IV", "Output & Sharing", ch))

    # ============================================================ PART V (reference)
    ch = []
    ch.append(("Appendix A — Menu Reference", "<p class='lede'>Every menu and the command on it.</p>", [
      ("File", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>New… (Ctrl+N)</td><td>Start a new drawing at a chosen canvas size</td></tr>
<tr><td>Open SVG… (Ctrl+O)</td><td>Open an SVG — editable if DRAWmaster saved it</td></tr>
<tr><td>Save as SVG… (Ctrl+S)</td><td>Save the drawing as an editable vector SVG</td></tr>
<tr><td>Export PNG…</td><td>Write a fixed-size bitmap PNG on a white background</td></tr>
<tr><td>Export PDF…</td><td>Write a vector PDF at the canvas size (text stays text)</td></tr>
<tr><td>Import Image…</td><td>Place a picture on the canvas, embedded in the drawing</td></tr>
<tr><td>Print… (Ctrl+P)</td><td>Print the drawing as vector artwork, scaled to the page</td></tr>
<tr><td>Edit in PAINTcanvas…</td><td>Rasterise and hand the drawing to PAINTcanvas (one-way)</td></tr>
<tr><td>Quit</td><td>Close the program</td></tr></table>"""),
      ("Edit", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Undo (Ctrl+Z)</td><td>Reverse the last change; the history is deep</td></tr>
<tr><td>Redo (Ctrl+Shift+Z)</td><td>Re-apply a change you undid</td></tr>
<tr><td>Duplicate (Ctrl+D)</td><td>Make an offset copy of the selected object(s)</td></tr>
<tr><td>Edit Text…</td><td>Change the words, font or size of the selected text object</td></tr>
<tr><td>Gradient Fill…</td><td>Open the gradient dialog for the selected shape</td></tr>
<tr><td>Texture / Pattern Fill…</td><td>Fill the selected shape with a tiled or stretched image</td></tr>
<tr><td>Opacity…</td><td>Set the selected object’s opacity from 0 to 100%</td></tr>
<tr><td>Line Style (Dashes &amp; Arrows)…</td><td>Dash pattern and arrowheads for a line or path</td></tr>
<tr><td>Convert to Curves (Ctrl+Shift+C)</td><td>Turn the selected shape into an editable node path</td></tr></table>"""),
      ("Text", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Edit Text…</td><td>Change the words, font or size of the selected text object</td></tr>
<tr><td>Fit Text to Path</td><td>Flow a selected text object along a selected line, path or curve</td></tr>
<tr><td>Detach Text from Path</td><td>Return text-on-a-path to an ordinary straight line of text</td></tr></table>"""),
      ("Arrange", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bring to Front (Ctrl+Shift+])</td><td>Move the selected object to the very top of the stack</td></tr>
<tr><td>Send to Back (Ctrl+Shift+[)</td><td>Move it to the very bottom</td></tr>
<tr><td>Bring Forward (Ctrl+])</td><td>Move it up one step</td></tr>
<tr><td>Send Backward (Ctrl+[)</td><td>Move it down one step</td></tr>
<tr><td>Flip Horizontal / Vertical</td><td>Mirror the selection left-to-right or top-to-bottom</td></tr>
<tr><td>Lock / Unlock (Ctrl+L)</td><td>Pin the selection so it can’t be clicked or dragged, or release it</td></tr>
<tr><td>Group (Ctrl+G)</td><td>Bind the selected objects into one group</td></tr>
<tr><td>Ungroup (Ctrl+Shift+G)</td><td>Break the selected group back into its objects</td></tr>
<tr><td>Combine ▸ Union / Subtract / Intersect</td><td>Weld two or more shapes into one node path (boolean)</td></tr>
<tr><td>Align ▸ Left / Centre / Right</td><td>Line the selection up horizontally</td></tr>
<tr><td>Align ▸ Top / Middle / Bottom</td><td>Line the selection up vertically</td></tr>
<tr><td>Distribute ▸ Horizontally / Vertically</td><td>Space three or more objects evenly</td></tr>
<tr><td>Show Layers Panel</td><td>Reveal the Layers dock if it was closed</td></tr></table>"""),
      ("View", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Show Grid (Ctrl+')</td><td>Show or hide the non-printing grid</td></tr>
<tr><td>Grid Spacing…</td><td>Set the gap between grid lines, in pixels</td></tr>
<tr><td>Snap to Grid &amp; Guides</td><td>Toggle snapping of moves and resizes to the grid, guides and other objects</td></tr>
<tr><td>Add Horizontal / Vertical Guide…</td><td>Place a guide line at an exact pixel position</td></tr>
<tr><td>Clear Guides</td><td>Remove every guide</td></tr>
<tr><td>Measurement Units ▸ Pixels / Millimetres / Centimetres</td><td>Choose the unit shown in the read-out and on dimension labels</td></tr></table>"""),
      ("Help", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>User Guide</td><td>This book</td></tr>
<tr><td>Quick Start Guide</td><td>The short, get-going guide</td></tr>
<tr><td>About</td><td>Version and credits</td></tr></table>"""),
      ("The Style toolbar", """<table class="ref"><tr><th>Control</th><th>What it does</th></tr>
<tr><td>Fill</td><td>The colour inside a shape (supports an alpha / opacity value)</td></tr>
<tr><td>Line</td><td>The outline colour</td></tr>
<tr><td>Width</td><td>The outline thickness in pixels (0 = no outline)</td></tr>
<tr><td>Shape</td><td>Which QuickShape the QuickShape tool draws</td></tr>
<tr><td>Effects…</td><td>Drop shadow and outer glow for the selected object</td></tr>
<tr><td>Gradient…</td><td>Linear or radial gradient fill for the selected shape</td></tr>
<tr><td>Zoom + / − / 100%</td><td>Change the zoom level</td></tr></table>
<p>The <b>Texture / Pattern Fill</b>, <b>Fit Text to Path</b> and the dimension/connector tools are reached
from the menus and the tool palette rather than the Style toolbar.</p>""")]))

    ch.append(("Appendix B — Keyboard Shortcuts", "<p class='lede'>The keys worth learning.</p>", [
      ("Shortcuts", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>New drawing</td><td>{K('Ctrl')}+{K('N')}</td></tr>
<tr><td>Open SVG</td><td>{K('Ctrl')}+{K('O')}</td></tr>
<tr><td>Save as SVG</td><td>{K('Ctrl')}+{K('S')}</td></tr>
<tr><td>Undo / Redo</td><td>{K('Ctrl')}+{K('Z')} · {K('Ctrl')}+{K('Shift')}+{K('Z')}</td></tr>
<tr><td>Bring to Front / Send to Back</td><td>{K('Ctrl')}+{K('Shift')}+{K(']')} · {K('Ctrl')}+{K('Shift')}+{K('[')}</td></tr>
<tr><td>Bring Forward / Send Backward</td><td>{K('Ctrl')}+{K(']')} · {K('Ctrl')}+{K('[')}</td></tr>
<tr><td>Group / Ungroup</td><td>{K('Ctrl')}+{K('G')} · {K('Ctrl')}+{K('Shift')}+{K('G')}</td></tr>
<tr><td>Duplicate (clone)</td><td>{K('Ctrl')}+{K('D')}</td></tr>
<tr><td>Lock / Unlock</td><td>{K('Ctrl')}+{K('L')}</td></tr>
<tr><td>Convert to Curves</td><td>{K('Ctrl')}+{K('Shift')}+{K('C')}</td></tr>
<tr><td>Print</td><td>{K('Ctrl')}+{K('P')}</td></tr>
<tr><td>Show / hide the grid</td><td>{K('Ctrl')}+{K("'")}</td></tr>
<tr><td>Resize proportionally · snap rotation to 15°</td><td>hold {K('Shift')} while dragging a handle</td></tr>
<tr><td>Add to / remove from a multiple selection</td><td>{K('Shift')}+click</td></tr>
<tr><td>Delete the selected object(s)</td><td>{K('Delete')} · {K('Backspace')}</td></tr>
<tr><td>Finish a pen shape (closed, filled)</td><td>double-click</td></tr>
<tr><td>Finish a pen shape (open line)</td><td>{K('Enter')}</td></tr>
<tr><td>Quit</td><td>{K('Ctrl')}+{K('Q')}</td></tr></table>""")]))

    ch.append(("Appendix C — Tool Reference", "<p class='lede'>A reference to the tool palette.</p>", [
      ("The tools", f"""
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}
<table class="ref"><tr><th>Tool</th><th>Use</th></tr>
<tr><td>Select</td><td>Pick up, move, resize, rotate and delete objects; shows a dashed highlight</td></tr>
<tr><td>Node</td><td>Reshape a path by dragging its nodes and Bézier control handles</td></tr>
<tr><td>Freehand</td><td>Draw a hand-guided path, like a pencil</td></tr>
<tr><td>Pen</td><td>Draw Bézier curves: click for a corner node, click-drag for a smooth node; double-click to close and fill, Enter to leave open</td></tr>
<tr><td>Line</td><td>Draw a single straight segment</td></tr>
<tr><td>Rectangle</td><td>Drag out a rectangle</td></tr>
<tr><td>Ellipse</td><td>Drag out an ellipse or circle</td></tr>
<tr><td>QuickShape</td><td>Drag out the chosen ready-made shape</td></tr>
<tr><td>Text</td><td>Click, then type a line of artistic text (font and size in the dialog)</td></tr>
<tr><td>Image</td><td>Click, then pick a picture file to place on the canvas</td></tr>
<tr><td>Dimension line</td><td>Drag to draw a measured line with end ticks and an automatic length label</td></tr>
<tr><td>Connector</td><td>Drag from one object to another to join them with a line that follows them</td></tr></table>""")]))

    ch.append(("Appendix D — Glossary", "<p class='lede'>The drawing words used in this guide.</p>", [
      ("A–Z", """<dl class="gloss">
<dt>Alpha</dt><dd>The opacity of a colour — a low alpha makes a fill partly see-through.</dd>
<dt>Arrowhead</dt><dd>A filled triangle placed at the start or end of a line or path, for pointers and connectors.</dd>
<dt>Bézier curve</dt><dd>A smooth curve defined by nodes and their control handles — the mathematics behind every vector curve.</dd>
<dt>Bitmap (raster)</dt><dd>A picture made of a grid of coloured dots, such as a PNG or a photo; it blurs when enlarged.</dd>
<dt>Combine (boolean)</dt><dd>Weld two or more shapes into one with Union, Subtract or Intersect.</dd>
<dt>Connector</dt><dd>A line anchored to two objects that stays attached as they move or resize.</dd>
<dt>Dimension line</dt><dd>A measured line with end ticks and an automatic length label, for plans and diagrams.</dd>
<dt>Duplicate (clone)</dt><dd>An offset copy of the selection, made with Ctrl+D.</dd>
<dt>Flip</dt><dd>Mirror an object left-to-right or top-to-bottom about the selection’s centre.</dd>
<dt>Lock</dt><dd>Pin an object so it cannot be selected or moved by accident, until unlocked.</dd>
<dt>Measurement unit</dt><dd>Pixels, millimetres or centimetres — how lengths are shown; the drawing itself stays in pixels.</dd>
<dt>Texture (pattern) fill</dt><dd>A fill that paints a tiled or stretched image inside a shape.</dd>
<dt>Text on a path</dt><dd>Artistic text flowed along a line or curve so its letters follow the path.</dd>
<dt>Control handle</dt><dd>A small marker on a stalk from a node that steers how a Bézier curve bends through it.</dd>
<dt>Convert to Curves</dt><dd>Turn a shape, line or QuickShape into an editable node path.</dd>
<dt>Dash style</dt><dd>Whether a line is drawn solid, dashed or dotted.</dd>
<dt>Image</dt><dd>A bitmap picture placed on the canvas as an object and embedded in the drawing.</dd>
<dt>Node</dt><dd>A point on a path; corner nodes turn sharply, smooth nodes curve gracefully.</dd>
<dt>Opacity</dt><dd>How solid an object is, from transparent to fully opaque; lower lets what is behind show through.</dd>
<dt>PDF</dt><dd>A universal document format; DRAWmaster exports a vector PDF that stays sharp at any size.</dd>
<dt>Drop shadow</dt><dd>A soft, offset copy behind an object that makes it look raised off the page.</dd>
<dt>Align</dt><dd>Line selected objects up against a shared edge or centre.</dd>
<dt>Distribute</dt><dd>Space three or more selected objects evenly between the outermost two.</dd>
<dt>Fill</dt><dd>The colour inside a shape.</dd>
<dt>Freehand</dt><dd>A path drawn by hand, following the pointer like a pencil.</dd>
<dt>Grid</dt><dd>A faint, non-printing mesh of lines across the canvas, for lining things up and for snapping.</dd>
<dt>Group</dt><dd>Several objects bound into one, so they select, move, rotate and delete together.</dd>
<dt>Guide</dt><dd>A single non-printing line, across or down, placed to line objects up against.</dd>
<dt>Handle</dt><dd>A small marker on a selected object’s frame — eight square resize handles and one round rotate handle.</dd>
<dt>Gradient</dt><dd>A fill that blends smoothly between two colours — linear (across the shape) or radial (out from the centre).</dd>
<dt>Layer</dt><dd>A named, show/hideable group of objects; higher layers sit above lower ones in the drawing.</dd>
<dt>Object</dt><dd>Anything you draw — a shape, a line, a path or text; each is selected and styled on its own.</dd>
<dt>Outer glow</dt><dd>A soft halo of colour around an object.</dd>
<dt>Outline (line / stroke)</dt><dd>The coloured edge around a shape, or the body of a line.</dd>
<dt>Path</dt><dd>A freehand stroke, stored as the series of points it followed.</dd>
<dt>Pen / polyline</dt><dd>A shape built point by point; closed and filled, or left as an open line.</dd>
<dt>PNG</dt><dd>A common bitmap image format; DRAWmaster exports to it for fixed-size pictures.</dd>
<dt>QuickShape</dt><dd>A ready-made shape outline (star, arrow, heart, speech bubble…).</dd>
<dt>Rotate</dt><dd>Turn an object about its centre; the angle is stored and exported as an SVG transform.</dd>
<dt>Snapping</dt><dd>Pulling a moved or resized object into line with the grid, a guide or another object.</dd>
<dt>Transform</dt><dd>A change to an object’s size or angle — resizing or rotating.</dd>
<dt>SVG</dt><dd>Scalable Vector Graphics — DRAWmaster’s editable save format, and a web standard.</dd>
<dt>Text (artistic text)</dt><dd>Words as a drawing object — fillable, outlinable, gradient-fillable, and exported as real SVG text.</dd>
<dt>Vector</dt><dd>Artwork defined by maths, not pixels — sharp at any size.</dd>
<dt>Z-order</dt><dd>The front-to-back stacking of overlapping objects; set with the Arrange commands.</dd>
<dt>Width</dt><dd>The thickness of an outline, in pixels; 0 means no outline.</dd>
</dl>""")]))

    # --- the full DrawPlus X3 cross-reference ---------------------------------
    def row(topic, status, where):
        return f"<tr><td>{topic}</td><td>{status}</td><td>{where}</td></tr>"
    YES = '<b style="color:#2a7d4f">In DRAWmaster</b>'
    PART = '<span style="color:#b5651d">Partly</span>'
    NO = '<span style="color:#b24">Not in this edition</span>'

    ch.append(("Appendix E — DrawPlus X3 Cross-Reference",
      "<p class='lede'>DRAWmaster is a clean-room drawing program in the tradition of Serif's <b>DrawPlus "
      "X3</b>. This appendix walks the thirteen chapters of the DrawPlus X3 User Guide in order and says, "
      "honestly, where DRAWmaster does the same thing, where it does something close, and where a DrawPlus "
      "feature is deliberately <b>not</b> part of this edition — so you have a complete map between the "
      "two.</p>", [
      ("How to read this appendix", f"""
<p>Each section below corresponds to a DrawPlus X3 chapter. A table lists that chapter's main topics with
one of three verdicts:</p>
<ul>
<li>{YES} — DRAWmaster has the same (or an equivalent) feature; the “where” column points to the chapter of
this guide that covers it.</li>
<li>{PART} — DRAWmaster does something close but not identical.</li>
<li>{NO} — a DrawPlus feature this edition does not replicate, listed so the map is complete.</li>
</ul>
{note('DRAWmaster is a focused vector editor, not a full DrawPlus clone. The honest “Not in this edition” notes below are the features that make DrawPlus a much larger program — animation, pressure brushes, autotrace, 3D and the distortion tools — and are the natural places it could grow.')}"""),
      ("Ch. 1–2 · Welcome &amp; Getting Started", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Vector-drawing concept, object model', YES, 'Ch. 1, Welcome')}
{row('Startup Wizard', PART, 'DRAWmaster opens straight onto a canvas; File ▸ New picks a size')}
{row('Starting from a design template', NO, 'No template gallery; start from a blank canvas')}
{row('Starting a new drawing', YES, 'Ch. 2, Starting Out')}
{row('Opening a saved document', YES, 'Ch. 2 — opens its own editable SVGs')}
{row('Opening other file types', PART, 'Imports bitmap images; opens DRAWmaster SVGs for editing')}
{row('Saving your work', YES, 'Ch. 2 — saves editable SVG')}
{row('Saving templates', NO, 'Not in this edition')}
</table>"""),
      ("Ch. 3 · Working with Pages", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Setting up a document (canvas size)', YES, 'Ch. 2, New Drawing dialog')}
{row('Page and pasteboard', YES, 'Ch. 3, The Workspace — white canvas on a grey pasteboard')}
{row('Measurement units', YES, 'Ch. “Grid, Guides and Snapping” — px / mm / cm')}
{row('Drawing scale', PART, '96 px = 1 inch fixed; no arbitrary named scale')}
{row('Snapping', YES, 'Ch. “Grid, Guides and Snapping”')}
{row('Viewing pages (zoom, pan)', YES, 'Ch. 3, Moving around and zooming')}
{row('Adding and deleting pages (multi-page)', NO, 'Single-canvas drawings only — see PAGEdesigner for multi-page')}
{row('Design aids (grid, guides, rulers)', YES, 'Ch. “Grid, Guides and Snapping” (no on-screen ruler bar)')}
{row('Updating defaults', PART, 'Current Fill/Line/Width act as live defaults for new shapes')}
</table>"""),
      ("Ch. 4 · Lines, Curves and Shapes", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Selecting one or more objects', YES, 'Ch. “Selecting and Moving”, “Grouping, Aligning…”')}
{row('Drawing lines and shapes', YES, 'Ch. “Drawing Shapes”, “Drawing Lines and Paths”')}
{row('Editing lines and shapes (nodes)', YES, 'Ch. “Editing Nodes and Curves” — the Node tool')}
{row('QuickShapes', YES, 'Ch. “Drawing Shapes” — 18 QuickShapes')}
{row('The Gallery (reusable designs)', NO, 'Not in this edition')}
{row('Converting a shape to editable curves', YES, 'Ch. “Editing Nodes and Curves” — Convert to Curves')}
{row('Applying perspective', NO, 'Not in this edition')}
{row('Applying envelopes (mesh distortion)', NO, 'Not in this edition')}
{row('Connectors', YES, 'Ch. “Dimension Lines and Connectors”')}
</table>
{note('DrawPlus perspective and envelope distortions warp a shape through a draggable cage or vanishing point. DRAWmaster does not replicate these; the nearest tools are Convert to Curves plus the Node tool for freeform reshaping, and resize/rotate/flip for simple transforms.')}"""),
      ("Ch. 5 · Brushes", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Freehand drawing', YES, 'Ch. “Drawing Lines and Paths” — the Freehand tool')}
{row('Art &amp; paint brushes', NO, 'Not in this edition — strokes have a flat colour and width')}
{row('Pressure sensitivity', NO, 'Not in this edition — no pen-tablet pressure')}
</table>
{caution('DrawPlus brushes paint textured, tapering, pressure-varying strokes from a brush library. DRAWmaster’s Freehand and Pen tools draw a clean, constant-width vector stroke instead — simpler, and still fully editable as a path.')}"""),
      ("Ch. 6 · Text", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Artistic text', YES, 'Ch. “Working with Text”')}
{row('Frame (story) text', NO, 'Not in this edition — see PAGEdesigner/WEBcreator for text frames')}
{row('Fitting text to a frame', NO, 'Not in this edition')}
{row('Fitting text to a path', YES, 'Ch. “Working with Text” — Fit Text to Path')}
{row('Dimension lines and labels', YES, 'Ch. “Dimension Lines and Connectors”')}
{row('Spell-checking', NO, 'Not in this edition')}
</table>"""),
      ("Ch. 7 · Working with Objects", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Clone / duplicate', YES, 'Ch. “Duplicating, Cloning and Locking” (Ctrl+D)')}
{row('Resize, rotate, shear', PART, 'Resize &amp; rotate: Ch. “Transforming Objects”. Shear not in this edition')}
{row('Flip (mirror)', YES, 'Ch. “Transforming Objects” — Flip Horizontal/Vertical')}
{row('Crop, cut-up, erase', NO, 'Not in this edition — reshape with Node/Combine instead')}
{row('Lock / unlock', YES, 'Ch. “Duplicating, Cloning and Locking” (Ctrl+L)')}
{row('Find objects', NO, 'Not in this edition')}
{row('Group / ungroup', YES, 'Ch. “Grouping, Aligning and Distributing”')}
{row('Combine (boolean)', YES, 'Ch. “Opacity, Dashes, Arrowheads and Combining Shapes”')}
{row('Align / distribute', YES, 'Ch. “Grouping, Aligning and Distributing”')}
{row('Order (z-order)', YES, 'Ch. “Layers and Arranging Objects”')}
{row('Layers', YES, 'Ch. “Layers and Arranging Objects”')}
</table>"""),
      ("Ch. 8 · Fills, Lines, Colours and Transparency", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Solid fills &amp; line colours', YES, 'Ch. “Fill, Line and Width”')}
{row('Line width &amp; dash styles', YES, 'Ch. “Fill, Line and Width”, “Opacity, Dashes…”')}
{row('Gradient fills (linear, radial)', YES, 'Ch. “Gradient and Texture Fills”')}
{row('Bitmap / pattern fills', YES, 'Ch. “Gradient and Texture Fills” — Texture / Pattern Fill')}
{row('Plasma &amp; mesh fills', NO, 'Not in this edition')}
{row('Opacity / transparency', YES, 'Ch. “Opacity, Dashes…” — object opacity')}
{row('Transparency gradients / effects', PART, 'Per-object opacity and alpha fills; no transparency gradient')}
</table>"""),
      ("Ch. 9 · Pictures", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Importing a picture', YES, 'Ch. “Placing Pictures” — embedded as a data URI')}
{row('Scanner / camera import', NO, 'Not in this edition — import a saved file instead')}
{row('Cutout Studio (background removal)', NO, 'Not in this edition — use PAINTcanvas for raster editing')}
{row('AutoTrace (bitmap → vector)', NO, 'Not in this edition — trace by hand over a dimmed image')}
</table>
{tip('To “trace”, place a picture on a lower layer, drop its opacity, lock it, and draw over the top with the Pen and shapes — the manual route to the clean vector artwork AutoTrace would attempt automatically.')}"""),
      ("Ch. 10 · Special Effects", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Drop shadows', YES, 'Ch. “Effects: Shadow and Glow”')}
{row('Outer glow', YES, 'Ch. “Effects: Shadow and Glow”')}
{row('2D filter effects (blur, etc.)', PART, 'Shadow and glow are blurred filter effects; no general filter set')}
{row('Borders, blends, rough edges', NO, 'Not in this edition')}
{row('3D filter effects', NO, 'Not in this edition')}
{row('Paper textures', PART, 'Use a Texture / Pattern Fill with a paper texture from the library')}
{row('Instant 3D / Pseudo-3D', NO, 'Not in this edition')}
</table>"""),
      ("Ch. 11 · Animations", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Stopframe animation', NO, 'Not in this edition — DRAWmaster is a still-image editor')}
{row('Keyframe animation', NO, 'Not in this edition')}
</table>
{caution('Animation is the biggest DrawPlus feature DRAWmaster does not attempt. DRAWmaster makes still vector artwork — logos, icons, diagrams and illustrations — and exports it as SVG, PNG or PDF.')}"""),
      ("Ch. 12 · Publishing &amp; Exporting", f"""
<table class="ref"><tr><th>DrawPlus X3 topic</th><th>Status</th><th>Where in this guide</th></tr>
{row('Printing', YES, 'Ch. “Exporting to PDF and Printing”')}
{row('Exporting PDF', YES, 'Ch. “Exporting to PDF and Printing” — vector PDF')}
{row('Exporting images (PNG, etc.)', YES, 'Ch. “Exporting and Sharing” — PNG')}
{row('Exporting SVG', YES, 'Ch. “Exporting and Sharing” — editable SVG, the native format')}
{row('Web / slideshow publishing', PART, 'Exports SVG for the web; no built-in web/slideshow builder (see WEBcreator)')}
</table>"""),
      ("Ch. 13 · Index", f"""
<p>The DrawPlus X3 User Guide closes with an index. This guide has its own back-of-book
<a href="#bookindex">Index</a>, linking every topic to the chapter that covers it.</p>""")]))

    ch.append(("Appendix F — Troubleshooting", "<p class='lede'>Quick answers to common snags.</p>", [
      ("Common questions", f"""<dl class="gloss">
<dt>My shape has no outline.</dt><dd>The <b>Width</b> is set to 0, or the <b>Line</b> colour is unset. Raise the width and pick a line colour on the Style toolbar.</dd>
<dt>My shape has no fill — it is hollow.</dt><dd>Lines and open pen paths never fill. For a shape, click the <b>Fill</b> button and pick a colour; a filled object draws solid.</dd>
<dt>I can’t select the object I want.</dt><dd>Clicking picks the <i>topmost</i> object. Move the one on top aside, or delete it, to reach what is behind.</dd>
<dt>My pen shape won’t fill.</dt><dd>You pressed {K('Enter')}, which finishes an <i>open</i> line. Finish with a <b>double-click</b> to close and fill the shape instead.</dd>
<dt>I opened an SVG and couldn’t edit its shapes.</dt><dd>That SVG was made by another program. DRAWmaster can re-open with full editing only the SVGs it saved itself.</dd>
<dt>My effect vanished when I exported a PNG.</dt><dd>It should not — shadows and glows are drawn into the export. If a glow looks faint, raise its strength, then export again.</dd>
</dl>""")]))

    parts.append(("Part V", "Reference", ch))
    return parts


# ------------------------------------------------------------------- quickstart
def quickstart_sections(IM):
    def f(k, cap):
        return fig(IM.get(k), cap)

    D = IM.get("_dialogs", {})

    def dlg(*names):
        for n in names:
            if n in D:
                return D[n]
        return None

    S = []
    S.append(("Welcome to DRAWmaster", f"""
<p class="lede">DRAWmaster is a <b>vector drawing</b> program: you build a picture out of shapes, lines and
paths that stay perfectly sharp at any size, then save it as an SVG or export a PNG. It works in the
tradition of Serif's <b>DrawPlus</b>.</p>
<p>This Quick Start takes you from a blank canvas to a finished drawing in a dozen short steps. For the
complete reference — every tool, worked projects and a full menu guide — open the <b>User Guide</b>
(Help ▸ User Guide).</p>
{f('logo_demo', 'A badge drawn entirely in DRAWmaster — shapes, lines and effects, every edge crisp.')}"""))
    S.append(("Start a drawing", f"""
<p>DRAWmaster opens onto a blank canvas. To start fresh at a chosen size, choose <b>File ▸ New…</b>
({K('Ctrl')}+{K('N')}) and pick a size — a general canvas, an A4 page, full-HD, or a square.</p>
{fig(dlg('New Drawing'), 'The New Drawing dialog offers a few ready canvas sizes.')}"""))
    S.append(("The workspace", f"""
<p>Your canvas sits in the middle, the <b>tools</b> down the left, and the <b>Style toolbar</b> — fill,
line, width, shape, effects and zoom — across the top.</p>
{f('workspace', 'Tools on the left, the Style toolbar on top, your canvas in the middle.')}"""))
    S.append(("Meet the tools", f"""
<p>The <b>tool palette</b> holds everything you draw with: <b>Select</b>, <b>Node</b>, <b>Freehand</b>,
<b>Pen</b>, <b>Line</b>, <b>Rectangle</b>, <b>Ellipse</b>, <b>QuickShape</b>, <b>Text</b> and <b>Image</b>.</p>
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}"""))
    S.append(("Draw a shape", f"""
<p>Choose the <b>Rectangle</b> or <b>Ellipse</b> tool and drag a box on the canvas. The shape appears in
the current fill and outline, ready to adjust.</p>
{f('shapes_demo', 'Rectangles, ellipses, QuickShapes, a line and a freehand curve.')}"""))
    S.append(("Try the QuickShapes", f"""
<p>Pick a shape from the <b>Shape</b> list — a star, arrow, heart, speech bubble and more — then drag a
box and it is drawn to fit. There are eighteen in all.</p>
{f('qshapes', 'Every QuickShape DRAWmaster offers.')}"""))
    S.append(("Lines, freehand and the pen", """
<p>The <b>Line</b> tool draws a straight segment; <b>Freehand</b> follows your pointer like a pencil; the
<b>Pen</b> builds a shape point by point — <b>double-click</b> to close and fill it, or press <b>Enter</b>
to leave it as an open line.</p>"""))
    S.append(("Colour it in", f"""
<p>Click <b>Fill</b> for the colour inside a shape and <b>Line</b> for its outline, then set the
<b>Width</b> of the outline (0 for none). With an object selected, the change applies at once.</p>
{f('fillstroke_demo', 'Different fills, and one line at three widths.')}"""))
    S.append(("Select, move and delete", f"""
<p>Switch to the <b>Select</b> tool. Click an object to highlight it, drag to move it, and press
{K('Delete')} to remove it. <b>Edit ▸ Undo</b> ({K('Ctrl')}+{K('Z')}) reverses any mistake.</p>
{f('select_demo', 'Clicking an object with the Select tool frames it.')}"""))
    S.append(("Resize, rotate and arrange", f"""
<p>A selected object shows <b>handles</b>: drag a corner or edge to <b>resize</b> (hold {K('Shift')} on a
corner to keep its proportions), and the round handle above it to <b>rotate</b>. {K('Shift')}-click to
select several at once, then <b>Arrange ▸ Group</b> ({K('Ctrl')}+{K('G')}) to bind them, or
<b>Arrange ▸ Align</b> and <b>Distribute</b> to tidy them up.</p>
{fig(IM.get('transform_demo'), 'One arrow rotated to a run of angles.')}
<p>For precise work, turn on <b>View ▸ Show Grid</b> and add <b>guides</b> — with <b>Snap to Grid &amp;
Guides</b> on, objects line up neatly as you drag. None of it prints.</p>
{fig(IM.get('align_after'), 'Boxes aligned to a common edge and evenly distributed.')}"""))
    S.append(("Add a shadow or glow", f"""
<p>With an object selected, click <b>Effects…</b>. Tick <b>drop shadow</b> for depth or <b>outer glow</b>
for a halo — or both — and set each one's spread, strength and colour.</p>
{f('effects_demo', 'A shadow, a glow, and an object using both.')}"""))
    S.append(("Add text, gradients and layers", f"""
<p>The <b>Text</b> tool (the <b>T</b> in the palette) drops a line of artistic text — click, then type and
pick a font and size. The <b>Gradient…</b> button fills the selected shape with a two-colour blend. And the
<b>Layers</b> panel (and the <b>Arrange</b> menu) controls which objects sit in front of which.</p>
{f('text_demo', 'Artistic text — solid, outlined, and gradient-filled.')}
{f('gradient_demo', 'Linear and radial gradient fills.')}"""))
    S.append(("Curves, pictures and finishing touches", f"""
<p>The <b>Pen</b> tool draws true <b>Bézier curves</b> — click for a corner, click-drag for a smooth
curve; the <b>Node</b> tool reshapes any path, and <b>Edit ▸ Convert to Curves</b> turns any shape into an
editable one. The <b>Image</b> tool (or <b>File ▸ Import Image…</b>) places a picture. And a few finishing
controls — <b>Edit ▸ Opacity…</b>, <b>Line Style</b> (dashes and arrowheads) and
<b>Arrange ▸ Combine</b> (union, subtract, intersect) — add the polish.</p>
{f('bezier_blob', 'A smooth shape drawn with the Pen as Bézier curves.')}
{f('dash_demo', 'Solid, dashed and dotted lines, and arrowheads.')}"""))
    S.append(("Save, export and print", f"""
<p>Choose <b>File ▸ Save as SVG…</b> ({K('Ctrl')}+{K('S')}) to keep an editable master, and
<b>File ▸ Export PNG…</b> for a ready-to-use bitmap. For a sharp document to send or print, use
<b>File ▸ Export PDF…</b> or <b>File ▸ Print…</b> ({K('Ctrl')}+{K('P')}) — both stay vector-crisp.</p>"""))
    S.append(("Where to go next", """
<p>That is the whole round trip: new canvas → shapes, lines and paths → colour and effects → save and
export. The <b>User Guide</b> covers every feature in depth, with worked projects and a full reference.
And the other <i>just a…</i> apps work the same way — once you know one, you know them all.</p>"""))
    return S


# ------------------------------------------------------------------- CSS
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
/* the tool rail is a tall, thin strip: cap it by HEIGHT so it can't balloon down the page */
figure.f.tall{max-width:none;width:max-content;margin:1.2em auto}
figure.f.tall img{width:auto;max-height:430px}
figcaption{font-size:.85rem;color:var(--mute);padding:8px 12px;background:var(--band);border-top:1px solid var(--line)}
.fig-missing{color:#b24;font-size:.85rem;border:1px dashed #c99;padding:8px;border-radius:6px;margin:1em 0}
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
.catgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:1em 0}
.catgrid.assets{grid-template-columns:repeat(3,1fr)}
.cat-card figure.f{margin:0;max-width:none}
.cat-card.asset figure.f img{background:#fff;object-fit:contain;max-height:150px}
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
  table.ref{break-inside:auto} .cat-card{break-inside:avoid} }
"""

QS_CSS = """
.toc{columns:2;gap:28px;margin:1em 0 0;padding:0;list-style:none}
.toc li{margin:.25em 0;break-inside:avoid}.toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--accent)}.toc .n{color:var(--accent);font-weight:700;margin-right:.5em}
h2{font-size:1.5rem;margin:2.2em 0 .5em;padding-top:.5em;border-top:3px solid var(--accent);max-width:none}
h2 .n{color:var(--accent);margin-right:.5em;font-weight:700}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:28px 34px}
header.mast h1{margin:0;color:#fff}header.mast p{margin:.3em 0 0;color:#d7ece7;max-width:none}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none} h2{break-after:avoid} figure.f{break-inside:avoid} }
"""


def _banner_uri():
    p = OUT / "banner.png"
    if Image and p.exists():
        return datauri(Image.open(str(p)).convert("RGB"), 900)
    return ""


def cover(kind):
    uri = _banner_uri()
    top = f'<img class="cv-banner" src="{uri}" alt="">' if uri else '<div style="font-size:3rem;font-weight:800;color:var(--accent)">DRAWmaster</div>'
    return (f'<section class="cover"><div class="cv-inner">{top}'
            f'<div class="cv-kind">{kind}</div><div class="cv-rule"></div>'
            f'<div class="cv-sub">just a&hellip; DRAWmaster &mdash; a vector drawing program in the spirit of Serif DrawPlus</div>'
            f'<div class="cv-date">{date.today().strftime("%B %Y")}</div></div></section>')


# ------------------------------------------------------------------- assembly
def build_quickstart(IM):
    S = quickstart_sections(IM)
    toc = "".join(f'<li><span class="n">{i+1}</span><a href="#s{i+1}">{H.escape(t)}</a></li>'
                  for i, (t, _) in enumerate(S))
    body = "".join(f'<h2 id="s{i+1}"><span class="n">{i+1}</span>{H.escape(t)}</h2>\n{b}'
                   for i, (t, b) in enumerate(S))
    doc = f"""<!DOCTYPE html><html lang="en-GB"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… DRAWmaster — Quick Start Guide</title>
<style>{CSS}{COVER_CSS}{QS_CSS}</style>
<div class="page">
{cover('Quick Start Guide')}
<header class="mast"><h1>DRAWmaster — Quick Start</h1>
<p>From a blank canvas to a finished drawing — in a dozen steps.</p></header>
<h2 style="border:0">Contents</h2><ol class="toc">{toc}</ol>
{body}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… DRAWmaster Quick Start · generated {date.today().isoformat()} · every picture is produced by the app itself.
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
                if term and len(term) < 46:
                    entries.setdefault(term, set()).add((n, anchor))
    TERMS = ["rectangle", "ellipse", "QuickShape", "line", "freehand", "pen", "polyline",
             "fill", "outline", "line colour", "width", "drop shadow", "outer glow", "effects",
             "select", "move", "delete", "undo", "redo", "SVG", "PNG", "export", "canvas",
             "zoom", "star", "arrow", "heart", "speech bubble", "icon", "logo", "diagram",
             "PAINTcanvas", "vector", "bitmap", "alpha", "path", "rotate", "resize", "transform",
             "handle", "group", "ungroup", "align", "distribute", "grid", "guide", "snapping"]
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
<title>just a… DRAWmaster — User Guide</title>
<style>{CSS}{COVER_CSS}{MANUAL_CSS}</style>
<div class="page">
{cover('User Guide')}
<header class="mast"><h1>DRAWmaster</h1><p>User Guide — the complete reference for drawing, styling and
exporting vector artwork.</p></header>
<nav class="contents"><h2 style="border:0;font-size:1.6rem">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… DRAWmaster User Guide · generated {date.today().isoformat()} · every picture is produced by the app itself ·
in the spirit of Serif DrawPlus.</footer>
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
