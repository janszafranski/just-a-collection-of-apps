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

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtGui import QImage, QPainter, QColor                 # noqa: E402
from PySide6.QtCore import Qt, QRectF                              # noqa: E402

app = QApplication.instance() or QApplication([])

# Silence modal message boxes so a driver call never blocks.
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))

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
<li><b>Text</b> — artistic text that behaves like a shape (fill, outline, gradient and effects all apply).</li>
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
{fig(IM.get('toolrail'), 'The tool palette, from the top: Select, Freehand, Pen, Line, Rectangle, Ellipse and QuickShape.', 'tall')}
<p>From the top, the tools are the <b>Select</b> pointer, <b>Freehand</b> (a pencil), the <b>Pen</b> (for
point-by-point polylines), <b>Line</b>, <b>Rectangle</b>, <b>Ellipse</b> and <b>QuickShape</b>. Each is
covered in detail in Part II.</p>
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
{tip('Outline-only text — no fill, a bold line colour and a wide width — gives a clean “stencil” headline; a gradient fill gives a bright, modern title.')}""")]))

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

    ch.append(("Gradient Fills",
      "<p class='lede'>Instead of a single flat colour, a shape can be filled with a <b>gradient</b> — a "
      "smooth blend between two colours. DRAWmaster offers a <b>linear</b> blend across the shape and a "
      "<b>radial</b> blend out from its centre.</p>", [
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
{tip('A radial gradient from a pale centre to a deep edge gives a shape a soft, rounded, “lit” look; a linear gradient at a shallow angle makes a clean modern background bar.')}""")]))

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

    parts.append(("Part IV", "Output & Sharing", ch))

    # ============================================================ PART V (reference)
    ch = []
    ch.append(("Appendix A — Menu Reference", "<p class='lede'>Every menu and the command on it.</p>", [
      ("File", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>New… (Ctrl+N)</td><td>Start a new drawing at a chosen canvas size</td></tr>
<tr><td>Open SVG… (Ctrl+O)</td><td>Open an SVG — editable if DRAWmaster saved it</td></tr>
<tr><td>Save as SVG… (Ctrl+S)</td><td>Save the drawing as an editable vector SVG</td></tr>
<tr><td>Export PNG…</td><td>Write a fixed-size bitmap PNG on a white background</td></tr>
<tr><td>Edit in PAINTcanvas…</td><td>Rasterise and hand the drawing to PAINTcanvas (one-way)</td></tr>
<tr><td>Quit</td><td>Close the program</td></tr></table>"""),
      ("Edit", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Undo (Ctrl+Z)</td><td>Reverse the last change; the history is deep</td></tr>
<tr><td>Redo (Ctrl+Shift+Z)</td><td>Re-apply a change you undid</td></tr>
<tr><td>Edit Text…</td><td>Change the words, font or size of the selected text object</td></tr>
<tr><td>Gradient Fill…</td><td>Open the gradient dialog for the selected shape</td></tr></table>"""),
      ("Arrange", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bring to Front (Ctrl+Shift+])</td><td>Move the selected object to the very top of the stack</td></tr>
<tr><td>Send to Back (Ctrl+Shift+[)</td><td>Move it to the very bottom</td></tr>
<tr><td>Bring Forward (Ctrl+])</td><td>Move it up one step</td></tr>
<tr><td>Send Backward (Ctrl+[)</td><td>Move it down one step</td></tr>
<tr><td>Show Layers Panel</td><td>Reveal the Layers dock if it was closed</td></tr></table>"""),
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
<tr><td>Zoom + / − / 100%</td><td>Change the zoom level</td></tr></table>""")]))

    ch.append(("Appendix B — Keyboard Shortcuts", "<p class='lede'>The keys worth learning.</p>", [
      ("Shortcuts", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>New drawing</td><td>{K('Ctrl')}+{K('N')}</td></tr>
<tr><td>Open SVG</td><td>{K('Ctrl')}+{K('O')}</td></tr>
<tr><td>Save as SVG</td><td>{K('Ctrl')}+{K('S')}</td></tr>
<tr><td>Undo / Redo</td><td>{K('Ctrl')}+{K('Z')} · {K('Ctrl')}+{K('Shift')}+{K('Z')}</td></tr>
<tr><td>Bring to Front / Send to Back</td><td>{K('Ctrl')}+{K('Shift')}+{K(']')} · {K('Ctrl')}+{K('Shift')}+{K('[')}</td></tr>
<tr><td>Bring Forward / Send Backward</td><td>{K('Ctrl')}+{K(']')} · {K('Ctrl')}+{K('[')}</td></tr>
<tr><td>Delete the selected object</td><td>{K('Delete')} · {K('Backspace')}</td></tr>
<tr><td>Finish a pen shape (closed, filled)</td><td>double-click</td></tr>
<tr><td>Finish a pen shape (open line)</td><td>{K('Enter')}</td></tr>
<tr><td>Quit</td><td>{K('Ctrl')}+{K('Q')}</td></tr></table>""")]))

    ch.append(("Appendix C — Tool Reference", "<p class='lede'>A reference to the tool palette.</p>", [
      ("The tools", f"""
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}
<table class="ref"><tr><th>Tool</th><th>Use</th></tr>
<tr><td>Select</td><td>Pick up, move and delete objects; shows a dashed highlight</td></tr>
<tr><td>Freehand</td><td>Draw a hand-guided path, like a pencil</td></tr>
<tr><td>Pen</td><td>Build a polyline point by point; double-click to close and fill, Enter to leave open</td></tr>
<tr><td>Line</td><td>Draw a single straight segment</td></tr>
<tr><td>Rectangle</td><td>Drag out a rectangle</td></tr>
<tr><td>Ellipse</td><td>Drag out an ellipse or circle</td></tr>
<tr><td>QuickShape</td><td>Drag out the chosen ready-made shape</td></tr>
<tr><td>Text</td><td>Click, then type a line of artistic text (font and size in the dialog)</td></tr></table>""")]))

    ch.append(("Appendix D — Glossary", "<p class='lede'>The drawing words used in this guide.</p>", [
      ("A–Z", """<dl class="gloss">
<dt>Alpha</dt><dd>The opacity of a colour — a low alpha makes a fill partly see-through.</dd>
<dt>Bitmap (raster)</dt><dd>A picture made of a grid of coloured dots, such as a PNG or a photo; it blurs when enlarged.</dd>
<dt>Drop shadow</dt><dd>A soft, offset copy behind an object that makes it look raised off the page.</dd>
<dt>Fill</dt><dd>The colour inside a shape.</dd>
<dt>Freehand</dt><dd>A path drawn by hand, following the pointer like a pencil.</dd>
<dt>Gradient</dt><dd>A fill that blends smoothly between two colours — linear (across the shape) or radial (out from the centre).</dd>
<dt>Layer</dt><dd>A named, show/hideable group of objects; higher layers sit above lower ones in the drawing.</dd>
<dt>Object</dt><dd>Anything you draw — a shape, a line, a path or text; each is selected and styled on its own.</dd>
<dt>Outer glow</dt><dd>A soft halo of colour around an object.</dd>
<dt>Outline (line / stroke)</dt><dd>The coloured edge around a shape, or the body of a line.</dd>
<dt>Path</dt><dd>A freehand stroke, stored as the series of points it followed.</dd>
<dt>Pen / polyline</dt><dd>A shape built point by point; closed and filled, or left as an open line.</dd>
<dt>PNG</dt><dd>A common bitmap image format; DRAWmaster exports to it for fixed-size pictures.</dd>
<dt>QuickShape</dt><dd>A ready-made shape outline (star, arrow, heart, speech bubble…).</dd>
<dt>SVG</dt><dd>Scalable Vector Graphics — DRAWmaster’s editable save format, and a web standard.</dd>
<dt>Text (artistic text)</dt><dd>Words as a drawing object — fillable, outlinable, gradient-fillable, and exported as real SVG text.</dd>
<dt>Vector</dt><dd>Artwork defined by maths, not pixels — sharp at any size.</dd>
<dt>Z-order</dt><dd>The front-to-back stacking of overlapping objects; set with the Arrange commands.</dd>
<dt>Width</dt><dd>The thickness of an outline, in pixels; 0 means no outline.</dd>
</dl>""")]))

    ch.append(("Appendix E — Troubleshooting", "<p class='lede'>Quick answers to common snags.</p>", [
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
<p>The <b>tool palette</b> holds everything you draw with: <b>Select</b>, <b>Freehand</b>, <b>Pen</b>,
<b>Line</b>, <b>Rectangle</b>, <b>Ellipse</b> and <b>QuickShape</b>.</p>
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
    S.append(("Save and export", f"""
<p>Choose <b>File ▸ Save as SVG…</b> ({K('Ctrl')}+{K('S')}) to keep an editable master, and
<b>File ▸ Export PNG…</b> for a ready-to-use bitmap to drop into a document, website or email.</p>"""))
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
             "PAINTcanvas", "vector", "bitmap", "alpha", "path"]
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
