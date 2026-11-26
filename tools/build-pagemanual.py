#!/usr/bin/env python3
"""Build PAGEdesigner's illustrated docs — a proper book-length User Guide and a
Quick Start — entirely from the running app.

    python3 tools/build-pagemanual.py            # both docs (HTML + PDF)
    python3 tools/build-pagemanual.py --quick    # just the Quick Start
    python3 tools/build-pagemanual.py --no-pdf   # HTML only (fast; skip printing)

Every picture is produced by the program itself: workspace and panel screenshots
are grabbed from a live (offscreen) window, every dialog is captured by driving the
real menu command, and the template / asset / QuickShape catalogues are rendered
with the app's own page painter. Images embed as data URIs, so each HTML file is
self-contained and installs with no extra assets.

Modelled on the structure and depth of Serif's PagePlus User Guide — step-by-step
procedures, callouts, worked projects and a full reference section — but describing
*this* program's real menus and features throughout.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "pagecreator" / "pagecreator.py"
OUT = ROOT / "apps" / "pagecreator"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-pagemanual", "--no-startup"]

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtCore import Qt                                      # noqa: E402

app = QApplication.instance() or QApplication([])

# Silence modal message boxes so a driver call never blocks.
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))

# Capture every dialog the app opens: when a command calls dlg.exec(), show the
# dialog offscreen, grab it, then return "rejected" so nothing is actually inserted.
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
    spec = importlib.util.spec_from_file_location("pagecreator", APP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PC = _load()
mk = PC.mk

try:
    from PIL import Image
except Exception:
    Image = None

_TMP = ROOT / "tools" / "_tmp_grab.png"


def _grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGB").copy()


def _pil(qt_obj) -> "Image.Image":
    """PIL image from a QPixmap or QImage."""
    qt_obj.save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGBA").copy()


def _win():
    w = PC.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1200, 960)
    w.show()
    for _ in range(16):
        app.processEvents()
    return w


# ------------------------------------------------------------------- demo pages
# All demo pages are plain (type, x, y, w, h, props) lists — the same shape the
# template and asset libraries use — so the app's page painter renders them.

SAMPLE = [
    ("shape", 0, 0, 794, 118, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("artistic", 40, 26, 500, 60, dict(html="<p>The Quayside Gazette</p>", size=40, color="#ffffff", bold=True)),
    ("text", 44, 86, 600, 28, dict(html="<p>Spring issue · news from the harbour community</p>", size=14, color="#ddeae6", pad=0)),
    ("artistic", 40, 150, 420, 40, dict(html="<p>New boardwalk opens</p>", size=26, color="#243137", bold=True)),
    ("text", 40, 200, 350, 420, dict(pad=0, size=13, color="#243137", html=(
        "<p>After a winter of work, the restored boardwalk along Mill Lane is open "
        "again. The council and dozens of volunteers rebuilt every plank by hand.</p>"
        "<p>“It is the best it has looked in thirty years,” said one resident.</p>"
        "<p>A small ceremony is planned for the May bank holiday, with tea, cake and "
        "a brass band.</p>"))),
    ("picture", 410, 150, 344, 210, dict(fill="#cfe0e6", stroke="#9fb8c0", strokeW=1)),
    ("text", 410, 366, 344, 28, dict(pad=0, size=11, color="#5c6b73", html="<p><i>The new boardwalk at first light.</i></p>")),
    ("artistic", 410, 408, 320, 34, dict(html="<p>Dates for the diary</p>", size=20, color="#243137", bold=True)),
    ("table", 410, 450, 344, 150, dict(head="#dff0eb", cells=[["Event", "When"], ["Boardwalk opening", "3 May"], ["Harbour market", "17 May"], ["Regatta", "31 May"]])),
    ("shape", 40, 648, 714, 3, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("text", 40, 662, 714, 28, dict(pad=0, size=11, color="#5c6b73", html="<p>The Quayside Gazette · delivered free to every home on the harbour · issue 42</p>")),
]

SHAPES_DEMO = [
    ("artistic", 40, 36, 560, 44, dict(html="<p>Shapes, lines &amp; QuickShapes</p>", size=30, color="#243137", bold=True)),
    ("shape", 40, 110, 150, 108, dict(shape="rect", fill="#9fc3d6", stroke="#2b3a42", strokeW=2)),
    ("shape", 212, 110, 150, 108, dict(shape="rect", fill="#cfe0e6", stroke="#2b3a42", strokeW=2, radius=18)),
    ("shape", 384, 110, 150, 108, dict(shape="ellipse", fill="#f4c96b", stroke="#8a6d1f", strokeW=2)),
    ("line", 560, 164, 190, 0, dict(stroke="#2b3a42", strokeW=3)),
    ("shape", 40, 250, 120, 120, dict(shape="star5", fill="#f4c96b", stroke="#c8851b", strokeW=2)),
    ("shape", 180, 250, 120, 120, dict(shape="arrow", fill="#5b8def", stroke="#2f5fb0", strokeW=2)),
    ("shape", 320, 250, 128, 120, dict(shape="heart", fill="#e8556b", stroke="#b2374b", strokeW=2)),
    ("shape", 470, 250, 150, 120, dict(shape="speech", fill="#ffffff", stroke="#2a7df0", strokeW=3)),
    ("shape", 640, 250, 120, 120, dict(shape="hexagon", fill="#49c5b6", stroke="#2a8577", strokeW=2)),
    ("shape", 40, 410, 160, 110, dict(shape="rect", fill="#2a7d6b", strokeW=0, shadow=dict(color="#000000", blur=16, dx=7, dy=9, opacity=40))),
    ("shape", 240, 410, 160, 110, dict(shape="rect", fill="#f4c96b", strokeW=0, glow=dict(color="#ffe08a", blur=22, opacity=85))),
    ("text", 40, 540, 360, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>A filled rectangle (left) carries a drop shadow; the gold one has an outer glow.</p>")),
]

TEXT_DEMO = [
    ("artistic", 40, 36, 560, 44, dict(html="<p>Working with text</p>", size=30, color="#243137", bold=True)),
    ("text", 40, 104, 350, 300, dict(size=13, color="#243137", html=(
        "<p><span style='font-size:230%'>O</span>nce upon a time a paragraph began with a large "
        "dropped capital, set into the first few lines. Frame text wraps neatly inside its frame "
        "and can flow on to a second, linked frame when it overruns.</p>"
        "<p>This is a second paragraph. Notice how the text keeps an even left edge and a comfortable "
        "line height for reading.</p>"))),
    ("text", 410, 104, 344, 300, dict(size=13, color="#243137", html=(
        "<p><b>A short checklist</b></p><ul><li>Type straight into a frame</li>"
        "<li>Link frames to flow long text</li><li>Give a heading its own style</li>"
        "<li>Add a bulleted or numbered list</li><li>Check spelling before you print</li></ul>"))),
    ("artistic", 40, 430, 500, 56, dict(html="<p>Big artistic headlines</p>", size=38, color="#2a7d6b", bold=True)),
    ("text", 40, 500, 714, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>Artistic text is a single line you scale freely — ideal for titles and mastheads.</p>")),
]

CHART_DEMO = [
    ("artistic", 40, 36, 560, 44, dict(html="<p>Charts &amp; QR codes</p>", size=30, color="#243137", bold=True)),
    ("chart", 40, 110, 360, 240, dict(kind="bar", title="Quarterly sales", data=[["Q1", 12], ["Q2", 19], ["Q3", 9], ["Q4", 16]])),
    ("chart", 420, 110, 300, 240, dict(kind="pie", title="Market share", data=[["North", 34], ["South", 22], ["East", 28], ["West", 16]])),
    ("chart", 40, 372, 360, 220, dict(kind="line", title="Visitors", data=[["Jan", 5], ["Feb", 8], ["Mar", 7], ["Apr", 12], ["May", 15]])),
    ("qr", 470, 392, 180, 180, dict(text="https://janszafranski.github.io/just-a-collection-of-apps/")),
    ("text", 40, 600, 714, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>Bar, line and pie charts from a short table of data — and a scannable QR code.</p>")),
]

# A colour / gradient / transparency showcase page.
COLOUR_DEMO = [
    ("artistic", 40, 30, 560, 44, dict(html="<p>Colour, gradients &amp; transparency</p>", size=28, color="#243137", bold=True)),
    ("shape", 40, 100, 220, 150, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("shape", 287, 100, 220, 150, dict(shape="rect", strokeW=0, grad=dict(c1="#8ad0c4", c2="#1d5c50", angle=90))),
    ("shape", 534, 100, 220, 150, dict(shape="rect", strokeW=0, grad=dict(c1="#f6d98a", c2="#d6893a", angle=45))),
    ("text", 40, 258, 220, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Flat colour</p>")),
    ("text", 287, 258, 220, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Linear gradient</p>")),
    ("text", 534, 258, 220, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Angled gradient</p>")),
    ("picture", 40, 310, 714, 240, dict(fill="#9fb8c0", stroke="#7f98a0", strokeW=1)),
    ("shape", 40, 420, 714, 130, dict(shape="rect", fill="#13303a", strokeW=0, opacity=0.55)),
    ("artistic", 70, 452, 600, 50, dict(html="<p>White text on a half-transparent panel</p>", size=26, color="#ffffff", bold=True)),
    ("text", 40, 560, 714, 28, dict(pad=0, size=12, color="#5c6b73", html="<p>A semi-transparent dark panel over a photo makes any text readable.</p>")),
]


# ------------------------------------------------------------------- capture
def capture(full=True):
    """Return {key: PIL image} for every picture the guide needs."""
    IM = {}
    SA = PC.StartupAssistant.__new__(PC.StartupAssistant)   # for _tpl_thumb (no __init__ needed)

    def page_img(objs, w=794, h=1123, px=820):
        return _pil(SA._tpl_thumb({"w": w, "h": h, "objs": objs}, px)).convert("RGB")

    # --- rendered demo pages (crisp, full-page) ---------------------------
    IM["sample"] = page_img(SAMPLE, px=900)
    IM["build1"] = page_img(SAMPLE[:1], px=820)
    IM["build2"] = page_img(SAMPLE[:3], px=820)
    IM["build3"] = page_img(SAMPLE[:6], px=820)
    IM["build4"] = page_img(SAMPLE[:9], px=820)
    IM["shapes"] = page_img(SHAPES_DEMO, px=860)
    IM["textpage"] = page_img(TEXT_DEMO, px=860)
    IM["charts"] = page_img(CHART_DEMO, px=860)
    IM["colourpage"] = page_img(COLOUR_DEMO, px=860)

    # picture / texture fill demo (uses the app banner as a sample texture)
    try:
        tex = ""
        bp = OUT / "banner.png"
        if bp.exists():
            b = io.BytesIO(); Image.open(str(bp)).convert("RGB").save(b, "JPEG", quality=80)
            tex = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        BIT = [
            ("artistic", 40, 28, 640, 44, dict(html="<p>Picture &amp; texture fills</p>", size=28, color="#243137", bold=True)),
            ("shape", 40, 108, 300, 236, dict(shape="star5", fillimg=tex, fillmode="stretch", stroke="#1f2a30", strokeW=3)),
            ("shape", 380, 108, 360, 112, dict(shape="rect", fillimg=tex, fillmode="stretch", strokeW=0, radius=12)),
            ("shape", 380, 236, 360, 108, dict(shape="rect", fillimg=tex, fillmode="tile", strokeW=0, radius=12)),
            ("text", 40, 352, 300, 24, dict(pad=0, size=12, color="#5c6b73", align="center", html="<p>Stretched into a QuickShape</p>")),
            ("text", 380, 352, 360, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Stretched (top) and tiled (bottom)</p>")),
        ]
        IM["bitmap_demo"] = page_img(BIT, w=794, h=404, px=860)
    except Exception as e:
        print("bitmap demo failed:", e)

    # --- QuickShape catalogue: all shapes in a labelled grid --------------
    qs = PC.QUICKSHAPES
    grid, cols, cw, ch = [], 4, 185, 150
    palette = ["#2a7d6b", "#5b8def", "#e8556b", "#f4c96b", "#49c5b6", "#9b6bd8"]
    for i, (key, label) in enumerate(qs):
        cx, cy = 20 + (i % cols) * cw, 20 + (i // cols) * ch
        col = palette[i % len(palette)]
        grid.append(("shape", cx + 22, cy + 10, cw - 70, ch - 70, dict(shape=key, fill=col, stroke="#1f2a30", strokeW=2)))
        grid.append(("text", cx, cy + ch - 48, cw - 24, 24, dict(pad=0, size=12, color="#243137", align="center", html=f"<p>{H.escape(label)}</p>")))
    rows = (len(qs) + cols - 1) // cols
    IM["qshapes"] = page_img(grid, w=cols * cw + 40, h=rows * ch + 40, px=900)

    # --- template catalogue ----------------------------------------------
    tpls = []
    try:
        p = OUT / "page_templates.py"
        spec = importlib.util.spec_from_file_location("page_templates", p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        tpls = mod.TEMPLATES()
    except Exception as e:
        print("templates unavailable:", e)
    IM["_templates"] = tpls
    for t in tpls:
        IM["tpl:" + t["name"]] = _pil(SA._tpl_thumb(t, 560)).convert("RGB")

    # --- asset catalogue --------------------------------------------------
    assets = []
    try:
        p = OUT / "page_assets.py"
        spec = importlib.util.spec_from_file_location("page_assets", p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        assets = mod.ASSETS()
    except Exception as e:
        print("assets unavailable:", e)
    IM["_assets"] = assets
    for a in assets:
        img = _pil(SA._tpl_thumb({"w": a["w"], "h": a["h"], "objs": a["objs"]}, 320)).convert("RGB")
        IM["asset:" + a["name"]] = img

    # --- workspace & panels (live window) ---------------------------------
    w = _win()
    try:
        w.view.fit_width()
    except Exception:
        pass
    for _ in range(8):
        app.processEvents()
    full_ws = _grab(w)
    IM["workspace"] = full_ws
    W, Hh = full_ws.size
    IM["toolrail"] = full_ws.crop((0, 70, 54, min(Hh, 720)))
    IM["stdbar"] = full_ws.crop((44, 28, W, 74))
    IM["panelstack"] = full_ws.crop((max(0, W - 300), 74, W, min(Hh, 520)))
    IM["statusbar"] = full_ws.crop((0, Hh - 32, W, Hh))

    # Fonts panel — draw each bundled family as a pangram sample (what the panel shows)
    try:
        from PySide6.QtGui import QFont, QPainter, QColor, QImage
        fams = getattr(w, "bundled_fonts", [])[:14]
        if fams:
            fi = QImage(760, 46 * len(fams) + 16, QImage.Format_RGB32); fi.fill(QColor("#ffffff"))
            qp = QPainter(fi); y = 8
            for fam in fams:
                qp.setPen(QColor("#8b97a0")); nf = QFont("Noto Sans"); nf.setPixelSize(10); qp.setFont(nf)
                qp.drawText(14, y + 12, fam)
                qp.setPen(QColor("#243137")); sf = QFont(fam); sf.setPixelSize(24); qp.setFont(sf)
                qp.drawText(12, y + 40, "The quick brown fox jumps over the lazy dog")
                y += 46
            qp.end()
            IM["fonts_panel"] = _pil(fi).convert("RGB")
    except Exception as e:
        print("fonts panel image failed:", e)

    # Startup Assistant pages
    try:
        dlg = PC.StartupAssistant(w)
        dlg.setAttribute(Qt.WA_DontShowOnScreen, True); dlg.resize(940, 660)
        dlg.nav.setCurrentRow(0); dlg.show()
        for _ in range(14):
            app.processEvents()
        IM["templates_gallery"] = _grab(dlg)
        dlg.nav.setCurrentRow(1)
        for _ in range(10):
            app.processEvents()
        IM["startup_sizes"] = _grab(dlg)
    except Exception as e:
        print("startup capture failed:", e)

    # --- dialogs: drive the real commands; _cap_exec stores them ----------
    def drive(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            print("drive failed:", getattr(fn, "__name__", fn), e)
        for _ in range(6):
            app.processEvents()

    w2 = _win()
    # a selected shape for transform / effects / gradient
    try:
        shp = mk("shape", 120, 120, 320, 200, shape="rect", fill="#2a7d6b", strokeW=0)
        w2.layer().append(shp); w2.sel = [shp["id"]]; w2.refresh()
        for _ in range(4):
            app.processEvents()
    except Exception as e:
        print("seed shape failed:", e)
    drive(w2.chart_dialog)
    drive(w2.qr_dialog)
    drive(w2.transform_dialog)
    drive(w2.effects_dialog)
    drive(w2.gradient_dialog, "linear")
    drive(w2.replace_colour_dialog)
    drive(w2.print_preview_dialog)
    drive(w2.export_canva)              # File ▸ Export ▸ For Canva…  (title "For Canva")
    drive(w2.guides_dialog)
    drive(w2.spell_dialog)
    drive(w2.find_replace_dialog)       # Edit ▸ Find & Replace (Ctrl+H)
    # Table of Contents — the document already has a couple of pages seeded, so the
    # dialog captures with real content behind it.
    try:
        PC.add_page(w2.site, "About")
        PC.add_page(w2.site, "Contact")
        w2.refresh()
    except Exception as e:
        print("seed TOC pages failed:", e)
    drive(w2.insert_toc)                # Insert ▸ Table of Contents…
    drive(w2.insert_asset_dialog)   # this one .show()s rather than .exec()s
    try:
        ad = w2._asset_dlg
        ad.setAttribute(Qt.WA_DontShowOnScreen, True); ad.resize(760, 650); ad.show()
        for _ in range(14):
            app.processEvents()
        IM["asset_dlg"] = _grab(ad); ad.hide()
    except Exception as e:
        print("asset dialog grab failed:", e)
    try:
        tbl = mk("table", 100, 100, 360, 160, head="#dff0eb", cells=[["Item", "Price"], ["Tea", "£2"], ["Cake", "£3"]])
        drive(w2.table_dialog, tbl)
    except Exception as e:
        print("table dialog failed:", e)
    # page / document setup
    for nm in ("page_setup", "doc_setup", "document_setup", "page_properties"):
        if hasattr(w2, nm):
            drive(getattr(w2, nm)); break

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


def crop(im, box):
    return im.crop(box)


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

    parts = []

    # ============================================================ PART I
    ch = []
    ch.append(("Welcome to PAGEdesigner",
      "<p class='lede'>PAGEdesigner is a <b>desktop-publishing</b> (DTP) program: a tool for "
      "arranging text, pictures, shapes and tables on a page exactly where you want them, and then "
      "printing the result or saving it as a PDF. It belongs to the <i>just a…</i> family of apps and "
      "works in the tradition of Serif's PagePlus — the same ideas, the same menus, in the same "
      "places.</p>", [
      ("What desktop publishing is", f"""
<p>A word processor pours text down a page from top to bottom. A <b>page-layout</b> program is
different: the page is a canvas, and everything on it — a headline, a column of body text, a photo,
a price table, a logo — is a separate <b>object</b> you position freely. That freedom is what lets
you make posters, flyers, newsletters, menus, business cards and booklets that look designed rather
than typed.</p>
{fig(IM.get('sample'), 'A one-page newsletter laid out in PAGEdesigner — headline, columns, a photo frame and a table, each an independent object.')}
<p>If you have used Canva, Microsoft Publisher or Serif's PagePlus, you already know the idea. If you
have only ever used a word processor, the single thing to unlearn is this: you no longer type <i>down</i>
a page — you place things <i>on</i> it.</p>"""),
      ("The object model", """
<p>Everything you put on a page is an object, and there are only a handful of kinds:</p>
<ul>
<li><b>Text frames</b> — a box that holds a paragraph of body text, wrapping inside its edges;</li>
<li><b>Artistic text</b> — a single line of display type you scale freely, for titles and mastheads;</li>
<li><b>Picture frames</b> — a box that holds a photograph or image;</li>
<li><b>Shapes and lines</b> — rectangles, ellipses, QuickShapes, rules and connectors;</li>
<li><b>Tables</b> — a grid of cells for data;</li>
<li><b>Charts and QR codes</b> — a picture generated from data you type.</li>
</ul>
<p>Because they are all objects, the skills are shared: whatever the kind, you select it, move it,
resize it, colour it, align it and layer it in exactly the same way. Learn those moves once (Chapter
on <i>Working with Objects</i>) and they apply everywhere.</p>"""),
      ("The just a… family", """
<p>PAGEdesigner has a growing family of companions, built to work together:</p>
<ul>
<li><b>WEBcreator</b> makes websites the same way PAGEdesigner makes printed pages;</li>
<li><b>PAINTcanvas</b> is the image editor — PAGEdesigner hands a photo to it for retouching and gets
the result straight back;</li>
<li><b>DRAWmaster</b> is for vector illustration and logos;</li>
<li><b>VIDEOeditor</b> — a video editor in the spirit of Serif MoviePlus — is in the works.</li>
</ul>
<p>They share the <b>CREATORsuite</b> launcher and a common <i>Documents/just a…</i> folder, so your
work is always easy to find. Once you know one app, the others feel familiar.</p>"""),
      ("About this guide", f"""
<p>This User Guide is the complete reference. It is organised in parts: the first gets you working,
the middle teaches each skill in depth with step-by-step procedures, then come worked projects you
can follow start to finish, output and publishing, and finally a reference section — menus, shortcuts,
a catalogue of every template, asset and shape, and a glossary.</p>
{note('Throughout, a numbered <b>“To …”</b> box is a procedure you can follow exactly. A <b>Tip</b> suggests a faster or better way. A <b>Remember</b> box flags something easy to forget.')}
<p>For a gentler first read, start with the <b>Quick Start Guide</b> (Help ▸ Quick Start), which takes
you from a blank page to a finished newsletter in about a dozen short steps.</p>"""),
      ("Conventions used here", f"""
<p>A few conventions keep the instructions short:</p>
<ul>
<li><b>Menu ▸ Command</b> means “open this menu and choose this command”, e.g. <b>File ▸ Export PDF…</b>.</li>
<li>Keys are shown like {K('Ctrl')}+{K('S')}; on a Mac read {K('Ctrl')} as {K('Cmd')}.</li>
<li><b>Click</b> means the left mouse button; <b>right-click</b> opens a context menu; <b>double-click</b>
opens whatever the object is for (a dialog, or edit-in-place for text).</li>
<li><b>Drag</b> means press, move, release.</li>
</ul>""")]))

    ch.append(("Starting Out",
      "<p class='lede'>This chapter covers the very first things: launching the program, the Startup "
      "Assistant that greets you, and the two ways to begin a document — from a ready-made design, or "
      "from a blank sheet of a chosen size.</p>", [
      ("Launching the program", """
<p>Open <b>just a… PAGEdesigner</b> from the CREATORsuite launcher, from your system's application
menu, or by running <code>pagecreator</code> in a terminal. The first time it opens it may take a
moment to settle; after that it starts quickly.</p>"""),
      ("The Startup Assistant", f"""
<p>Each time it launches, PAGEdesigner shows the <b>Startup Assistant</b> — your hub for beginning
work. Down its left side are its sections; the large area on the right shows what each offers.</p>
{fig(IM.get('templates_gallery'), 'The Startup Assistant, open on the Design Templates gallery.')}
{proc('begin from the Startup Assistant',
  'Choose <b>Start from a design</b> to pick a ready-made template (see the next chapter), or',
  '<b>New Publication</b> to choose a blank paper size, or',
  '<b>Open</b> to reopen recent work or browse for a saved file.',
  'Click your choice to open a document and close the Assistant.')}
{tip('Prefer to start on a blank page every time? Untick <b>Show this at startup</b> at the bottom. You can always summon the Assistant again from <b>File ▸ New</b>.')}"""),
      ("Starting from a blank paper size", f"""
<p>Choose <b>New Publication</b> to begin with an empty page at a standard size.</p>
{fig(IM.get('startup_sizes'), 'New Publication — pick a paper size, grouped by purpose, or set your own.')}
<p>The presets are grouped so the right one is easy to find:</p>
<ul>
<li><b>Documents</b> — A4, A4 Landscape, A5, A3, US Letter, US Legal;</li>
<li><b>Business</b> — business cards, letterhead, DL flyers, postcards, compliment slips;</li>
<li><b>Booklet &amp; Folded</b> — A5 and A4 booklets, greeting cards, tri-folds;</li>
<li><b>Large Format</b> — A3, A2 and A1 posters.</li>
</ul>
{proc('start a custom-sized document',
  'In <b>New Publication</b>, choose <b>Custom size</b>.',
  'Type a <b>width</b> and <b>height</b> (in millimetres) and a <b>page count</b>.',
  'Click <b>Create</b>. Your blank document opens at exactly that size.')}
{note('Every thumbnail is drawn to the sheet’s true proportions, so a business card looks like a card and a poster like a poster — handy for choosing at a glance.')}"""),
      ("Opening and saving", f"""
<p>PAGEdesigner documents are saved with a <code>.pagc</code> extension.</p>
{proc('save your work',
  'Choose <b>File ▸ Save</b> or press ' + K('Ctrl') + '+' + K('S') + '.',
  'The first time, give the document a name. It is saved into your shared <i>Documents/just a…</i> folder by default, so the launcher can find it.',
  'Use <b>File ▸ Save As…</b> to keep a separate copy under a new name.')}
{proc('open an existing document',
  'Choose <b>File ▸ Open</b> (' + K('Ctrl') + '+' + K('O') + ') and browse to a <code>.pagc</code> file, or',
  'pick a recent file from <b>File ▸ Open Recent</b>, or from the <b>Open</b> page of the Startup Assistant.')}
<p>PAGEdesigner also opens files from the programs it stands in for: <b>File ▸ Open PagePlus…</b> reads a
Serif PagePlus <code>.ppp</code> publication, and it can import a WebPlus site or a PDF, each as an
editable document. Your original file is never altered.</p>""")]))

    ch.append(("The Workspace",
      "<p class='lede'>Everything you do happens in the workspace: your page in the middle, the tools "
      "down the left, the menus and toolbars along the top, and the panels on the right. This chapter "
      "names every part so the rest of the guide can refer to them.</p>", [
      ("A tour of the window", f"""
<p>A new document opens with the page centred and everything you need arranged around it.</p>
{fig(IM.get('workspace'), 'The PAGEdesigner workspace: tool palette (left), menus and toolbars (top), the page (centre) and the tabbed panels (right).')}
<p>The parts are:</p>
<ul>
<li>the <b>menu bar</b> and <b>toolbars</b> across the top;</li>
<li>the <b>tool palette</b> down the left edge;</li>
<li>the <b>rulers</b> framing the page;</li>
<li>the <b>page</b> itself in the centre, on its pasteboard;</li>
<li>the tabbed <b>panels</b> on the right;</li>
<li>the <b>status bar</b> along the bottom.</li>
</ul>"""),
      ("The tool palette", f"""
<p>The vertical <b>tool palette</b> on the left holds the tools you draw and edit with.</p>
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}
<p>From the top: the <b>Pointer</b> (select and move), the <b>Pan</b> and <b>Zoom</b> tools for getting
around, then the object tools — <b>Artistic text</b>, <b>Text frame</b>, <b>Picture</b>, <b>Table</b>,
<b>Rectangle</b>, <b>Ellipse</b>, <b>Line</b> and the <b>QuickShapes</b>. Lower down sit <b>Rotate</b>
and <b>Crop</b>, and shortcuts to a bulleted list and the companion apps. Click a tool to select it;
its name and a hint appear in the status bar.</p>
{tip('Press ' + K('Esc') + ' or click the Pointer at any time to stop drawing and go back to selecting.')}"""),
      ("Menus and toolbars", f"""
<p>The <b>menu bar</b> gathers every command under <b>File</b>, <b>Edit</b>, <b>View</b>, <b>Insert</b>,
<b>Format</b>, <b>Arrange</b>, the two <b>Export</b> items and <b>Help</b>. The complete menu reference
is Appendix A.</p>
{fig(IM.get('stdbar'), 'The Standard toolbar: new, open and save; undo and redo; cut, copy and paste.')}
<p>Below the menus, the <b>Standard</b> toolbar carries the everyday buttons, and an <b>Insert</b>
toolbar sits alongside it. Toolbars can be shown or hidden from <b>View</b>, and dragged to re-dock.</p>"""),
      ("The panels", f"""
<p>The tabbed <b>panels</b> on the right are where you inspect and fine-tune whatever is selected.</p>
{fig(IM.get('panelstack'), 'The panels: Pages, Colour, Swatches, Line, Transparency, Transform and Layers.')}
<ul>
<li><b>Pages</b> — add, delete and reorder pages, and manage master pages;</li>
<li><b>Colour</b> — set a fill, line or text colour with sliders or a hex value;</li>
<li><b>Swatches</b> — a palette of saved colours, one click away;</li>
<li><b>Line</b> — outline width, dashes and arrowheads;</li>
<li><b>Transparency</b> — how much of what is behind an object shows through;</li>
<li><b>Transform</b> — exact position, size and rotation;</li>
<li><b>Layers</b> — stacking and grouping of objects.</li>
</ul>
{tip('Any panel can be shown or hidden from the <b>View</b> menu, and dragged out into its own floating window if you like more room.')}"""),
      ("Moving around and zooming", f"""
<p>You will zoom in to place things precisely and out to judge the whole page.</p>
{proc('change the zoom',
  'Type or pick a level in the <b>zoom box</b> at the bottom-right, or',
  'hold ' + K('Ctrl') + ' and scroll the mouse wheel, or',
  'choose <b>View ▸ Zoom In</b> / <b>Zoom Out</b> (' + K('Ctrl') + '+' + K('+') + ' / ' + K('Ctrl') + '+' + K('−') + ').')}
<p><b>View ▸ Fit Page</b> and <b>Fit Width</b> frame the whole page or its full width at once. The
<b>Pan</b> tool — or holding the space bar and dragging — slides the page around when you are zoomed in.</p>
{fig(IM.get('statusbar'), 'The status bar: a hint on the left, the cursor position and current page, and the zoom control on the right.')}"""),
      ("Rulers, guides and the grid", f"""
<p>The <b>rulers</b> along the top and left show position in your document's units. Drag out from a
ruler to drop a <b>guide line</b>; objects snap to guides as you move them, which is how you keep
columns, margins and rows of objects lined up.</p>
{proc('set up column and row guides',
  'Choose <b>View ▸ Guides…</b> to open the Guides &amp; Columns dialog.',
  'Set the number of <b>columns</b> and their <b>gutter</b> (the gap between them), and rows if you want them.',
  'Tick <b>Show guides</b> and click <b>OK</b>. Non-printing guide lines divide the page for you to lay text and pictures against.')}
{fig(dlg('Guides & Columns', 'Guides and Columns'), 'The Guides &amp; Columns dialog lays a non-printing layout grid inside the page margin.')}
<p>Turn snapping, the grid and the rulers themselves on or off from the <b>View</b> menu.</p>""")]))

    parts.append(("Part I", "Getting Started", ch))

    # ============================================================ PART II
    ch = []
    ch.append(("Setting Up Pages",
      "<p class='lede'>A publication is a stack of pages that share a size and, usually, a common "
      "background. This chapter covers adding and arranging pages, and the master pages that carry "
      "anything meant to repeat — a logo, a footer, a page number.</p>", [
      ("The Pages panel", f"""
<p>Open the <b>Pages</b> panel to see every page in the document as a list.</p>
{proc('add, remove and reorder pages',
  'Click <b>Add page</b> beneath the list to insert a new page after the current one.',
  'Select a page and click <b>Delete</b> to remove it.',
  'Drag a page up or down the list, or use the move buttons, to change the running order.',
  'Double-click a page to go straight to it.')}
{note('A booklet (from the Booklet &amp; Folded sizes) keeps its pages in printing order for you, so a folded A5 booklet imposes correctly when you print it.')}"""),
      ("Master pages", f"""
<p>Anything that should appear on <i>every</i> page — a logo, a footer, a watermark, a page number —
belongs on a <b>master page</b>. A master sits <i>behind</i> the ordinary pages that use it, so you
draw the object once and it shows through everywhere.</p>
{proc('put a logo on every page',
  'In the Pages panel, choose <b>New master page</b>.',
  'On the master, place the logo (or footer, or whatever repeats) where you want it.',
  'Return to an ordinary page: the item now shows on it, and on every other page that uses this master.',
  'To change it later, choose <b>Edit master page</b>, adjust it once, and every page updates.')}
{tip('Already built a page and only then realised several items repeat on others? <b>Arrange ▸ Move Repeated Objects to Master Page…</b> finds them and lifts them onto the master for you.')}"""),
      ("Page numbers", """
<p>Automatic page numbers live on a master page, so every page shows its own number without any
manual updating.</p>
<p>Add a small text frame to the master where the number should sit, then choose <b>Insert ▸ Page
Number</b>. Each page that uses the master then prints its own number; insert or delete a page and the
rest renumber themselves.</p>"""),
      ("Document setup and margins", """
<p><b>File ▸ Document Setup</b> lets you revisit the page size, orientation and margins after you have
started. Margins are guide lines, not hard limits — content can sit in the margin — but keeping body
text inside them is what gives a page its comfortable, professional border of white space.</p>""")]))

    ch.append(("Working with Objects",
      "<p class='lede'>Text frames, pictures, shapes, tables and charts are all <b>objects</b>, and "
      "they are handled the same way. Master the moves in this chapter — select, move, size, rotate, "
      "align, order, group, lock — and they serve you everywhere in the program.</p>", [
      ("Selecting objects", f"""
{proc('select objects',
  'Choose the <b>Pointer</b> tool.',
  'Click an object to select it — a frame of handles appears around it.',
  'Hold ' + K('Shift') + ' and click more objects to add them to the selection.',
  'Or drag a box across empty space to select everything it touches.',
  'Press ' + K('Esc') + ' (or click empty space) to deselect; ' + K('Ctrl') + '+' + K('A') + ' selects everything on the page.')}"""),
      ("Moving and resizing", f"""
<p>With one or more objects selected:</p>
<ul>
<li><b>Move</b> — drag any selected object; the whole selection moves together.</li>
<li><b>Resize</b> — drag a corner or edge handle. Dragging a corner keeps the proportions of a picture.</li>
<li><b>Nudge</b> — tap the arrow keys to move a small, exact step at a time.</li>
<li><b>Rotate</b> — drag the round handle above the object, or use the <b>Rotate</b> tool. Hold {K('Shift')} to snap to 15° steps.</li>
</ul>
{tip('Guides and other objects give off a gentle snap as you drag past their edges and centres — let it do the aligning for you.')}"""),
      ("The Transform panel", f"""
<p>When “close enough” is not enough, the <b>Transform</b> panel (and <b>Arrange ▸ Transform…</b>) lets
you type exact numbers.</p>
{fig(dlg('Transform', 'Transform Objects', 'Transform objects'), 'The Transform dialog: exact X and Y position, width, height and rotation angle.')}
{proc('place an object precisely',
  'Select the object.',
  'Open <b>Transform</b> and type its <b>X</b> and <b>Y</b> position, its <b>width</b> and <b>height</b>, or a <b>rotation</b> angle.',
  'Press ' + K('Enter') + '. This is the reliable way to make two objects exactly the same size, or to sit something a precise distance from the edge.')}"""),
      ("Aligning and distributing", """
<p>Alignment is what turns a rough arrangement into a crisp one. Select two or more objects, then use
<b>Arrange ▸ Align</b>:</p>
<ul>
<li><b>Left / Centre / Right</b> lines up their vertical edges or centres;</li>
<li><b>Top / Middle / Bottom</b> lines up their horizontal edges or centres;</li>
<li><b>Centre on Page</b> centres the selection on the sheet;</li>
<li><b>Distribute</b> spaces three or more objects evenly.</li>
</ul>
<p>A row of buttons, a grid of photos, a stack of headings — all look intentional once aligned.</p>"""),
      ("Order, grouping and locking", f"""
<p>Objects stack in the order you create them, newest on top. Use <b>Arrange</b> to change that:</p>
<ul>
<li><b>Bring to Front / Send to Back</b>, and <b>Forward / Back One</b>, so a caption can sit over a photo;</li>
<li><b>Group</b> ties several objects together so they move and resize as one — ungroup to edit a part;</li>
<li><b>Lock / Unlock</b> ({K('Ctrl')}+{K('L')}) pins something so you cannot nudge it by accident.</li>
</ul>
{caution('Locked objects cannot be selected by dragging a box — that is the point. Unlock from <b>Arrange ▸ Lock / Unlock</b> when you need to move one again.')}"""),
      ("Cut, copy, paste and duplicate", f"""
<p>The usual editing commands all apply to objects:</p>
<ul>
<li>{K('Ctrl')}+{K('X')} / {K('Ctrl')}+{K('C')} / {K('Ctrl')}+{K('V')} cut, copy and paste;</li>
<li><b>Duplicate</b> ({K('Ctrl')}+{K('D')}) drops a copy a little offset from the original;</li>
<li>{K('Ctrl')}+{K('Z')} undoes, {K('Ctrl')}+{K('Shift')}+{K('Z')} redoes — there is a deep undo history, so experiment freely.</li>
</ul>
{tip('Copying an object and pasting it onto another page is the simplest way to reuse something you have built — a styled heading, a logo lock-up, a coloured panel.')}""")]))

    ch.append(("Text",
      "<p class='lede'>Text is the heart of most publications. PAGEdesigner handles it the PagePlus "
      "way: body copy lives in frames you can link and flow, headlines are artistic text you scale "
      "freely, and styles keep a long document consistent.</p>", [
      ("Frame text", f"""
{proc('add a block of body text',
  'Choose the <b>Text frame</b> tool.',
  'Drag a rectangle on the page — that is a text frame.',
  'Type, or paste; the text wraps inside the frame’s edges automatically.',
  'Switch to the <b>Pointer</b> to move or resize the frame; the text re-wraps to fit.')}
{fig(IM.get('textpage'), 'Frame text with a dropped capital and a bulleted list (left), beside an artistic headline.')}"""),
      ("Flowing text between frames", f"""
<p>When a frame holds more text than it can show, a red <b>overflow</b> marker appears in its corner.
You can make the text continue in another frame — exactly how a newspaper runs a story across columns
and pages.</p>
{proc('flow a long story across two frames',
  'Draw a second text frame where the story should continue.',
  'Click the overflow marker on the first frame, then click the second frame.',
  'The overflowing text flows into the second frame. Resize or delete either frame and the text re-flows through the chain automatically.')}"""),
      ("Artistic text", """
<p>Where frame text is for paragraphs, <b>artistic text</b> is a single line you can scale to any size
— the tool for mastheads, titles and pull-quotes. Choose the Artistic text tool, click, and type; then
drag a corner handle to make it as large as you like. Because it is vector, it stays razor-sharp at any
size, unlike a picture of type.</p>"""),
      ("Fonts, size, colour and alignment", f"""
<p>Select some text — a word, a line or a whole frame — and set its look from the <b>Format</b> menu and
the text controls:</p>
<ul>
<li><b>Font</b> and <b>size</b>;</li>
<li><b>Bold</b> ({K('Ctrl')}+{K('B')}), <b>Italic</b> ({K('Ctrl')}+{K('I')}) and <b>Underline</b> ({K('Ctrl')}+{K('U')});</li>
<li><b>Colour</b>, from the Colour panel;</li>
<li><b>Alignment</b> — left, centred, right or justified;</li>
<li><b>Line spacing</b>, to open a dense block up or draw a loose one in.</li>
</ul>
{tip('For running text, left-aligned is easiest to read; reserve centred text for short headings and justified text for narrow columns where you want a clean right edge.')}"""),
      ("Drop caps and lists", f"""
<p>Two classic touches live in the Format menu:</p>
{proc('start a paragraph with a drop cap',
  'Click in the paragraph.',
  'Choose <b>Format ▸ Drop Cap</b>. The first letter enlarges and sets into the lines below — the traditional way to open an article.')}
{proc('turn paragraphs into a bulleted or numbered list',
  'Select the paragraphs.',
  'Choose a style from <b>Format ▸ Lists / Bullets</b> — a disc, circle or square bullet, or 1-2-3, a-b-c or i-ii-iii numbering.',
  'The list indents neatly; a numbered list renumbers itself if you add or remove an item.')}"""),
      ("The Fonts panel and special fonts", f"""
<p>PAGEdesigner ships with a set of distinctive <b>display, script and slab fonts</b> — the kind you
reach for on a poster title, a certificate or a café menu — the same open-licence faces the old Serif
packages bundled. They are installed with the app, so they are there even on a computer that has never
seen them, and they appear in every font list.</p>
<p>The quickest way to choose one is the <b>Fonts</b> panel in the studio (the tab beside Layers). It
shows each font as a large sample so you can see it before you commit:</p>
{fig(IM.get('fonts_panel'), 'The Fonts panel shows each bundled font as a sample; click one to apply it to the selected text.')}
{proc('apply a special font',
  'Select a text frame or artistic text (or highlight some words while editing).',
  'Open the <b>Fonts</b> panel and click a sample.',
  'The text takes on that font at once. The same fonts are also in the ordinary font drop-down, listed by name.')}
{tip('Pair a decorative font for the headline with a plain one (such as Open Sans) for the body — one personality per page is plenty.')}"""),
      ("Text styles", """
<p>When a document has several headings, you want them to match without setting each by hand. <b>Text
styles</b> do that: apply a named style — <i>Heading</i>, <i>Subheading</i>, <i>Body</i> — from
<b>Format ▸ Text Styles</b>, and every piece of text with that style looks the same. Restyle the
document later by changing the style once, and everything using it updates. Styles are what keep a long,
multi-page document consistent and quick to re-skin.</p>"""),
      ("Find &amp; Replace", f"""
<p>In a long document, changing a word everywhere by hand is slow and easy to get wrong — miss one, and
the inconsistency shows. <b>Find &amp; Replace</b> does it in one pass, searching the text on
<i>every</i> page (and the master pages) at once.</p>
{proc('change a word or phrase throughout the document',
  'Choose <b>Edit ▸ Find &amp; Replace…</b> or press ' + K('Ctrl') + '+' + K('H') + '.',
  'Type the text to look for in <b>Find what</b>, and its replacement in <b>Replace with</b>.',
  'Tick <b>Match case</b> if the capitals matter (so <i>Rose</i> the name is not caught by <i>rose</i> the flower).',
  'Click <b>Replace</b> to change the first match, or <b>Replace All</b> to change every one. PAGEdesigner reports how many it changed.')}
{fig(dlg('Find & Replace'), 'Find & Replace searches the text across every page and swaps it in one step.')}
{note('Replacement is <b>tag-safe</b>: it only ever changes the words you see, never the hidden formatting around them, so bold, colour and links survive untouched. And it is a single undo — one ' + K('Ctrl') + '+' + K('Z') + ' puts every change back.')}"""),
      ("Table of Contents", f"""
<p>A multi-page document — a booklet, a report, a programme — deserves a contents page. PAGEdesigner
builds one from your page list, so you never have to type titles and page numbers by hand or keep them
in step as the document grows.</p>
{proc('insert a table of contents',
  'Go to the page where the contents should appear.',
  'Choose <b>Insert ▸ Table of Contents…</b>.',
  'Give it a heading (<i>Contents</i> by default) and choose whether to leave out the page it sits on.',
  'Click <b>OK</b>. A text frame drops in, listing every page with its page number, each line linked to its page.')}
{fig(dlg('Table of Contents'), 'The Table of Contents dialog builds a contents list from the document’s pages.')}
<p>Once inserted it is an <b>ordinary text frame</b>: restyle it, change the type, move it — whatever you
would do to any text. When you later add, rename or reorder pages, rebuild it in one step:</p>
{proc('update the contents after changing pages',
  'Choose <b>Insert ▸ Update Table of Contents</b>.',
  'Every contents frame in the document is regenerated from the current page list, with the right titles and numbers.')}
{note('The page numbers follow the same counting as a <b>Page Number Field</b> — a page’s position in the document — so the contents and the running page numbers always agree.')}"""),
      ("Wrapping text, and spell check", f"""
<p>Text can <b>wrap</b> around a picture or shape, so words flow around the artwork rather than
disappearing behind it — give the object a wrap setting and place it over the text column.</p>
{proc('check spelling before you print',
  'Choose <b>Format ▸ Check Spelling…</b> or press ' + K('F7') + '.',
  'Step through each flagged word; choose a suggestion, ignore it, or add it to the dictionary.')}
{fig(dlg('Spell Check', 'Check Spelling', 'Spelling'), 'The spell checker steps through flagged words with suggestions.')}""")]))

    ch.append(("Pictures",
      "<p class='lede'>Pictures bring a page to life. PAGEdesigner keeps them in frames you can crop "
      "and style, and hands off to PAINTcanvas when a photo needs real editing.</p>", [
      ("Picture frames", f"""
{proc('place a photograph',
  'Choose the <b>Picture</b> tool and drag a box — a picture frame, shown as a grey placeholder.',
  'Double-click the frame and choose an image file.',
  'The picture fits the frame. Design the layout first with empty frames, and drop the photos in later — a frame can wait.')}
{note('Keeping images in frames (rather than loose on the page) is what lets you resize the hole and the picture independently, and swap one photo for another without disturbing the layout.')}"""),
      ("Fitting, cropping and borders", f"""
<p>A picture either <b>fills</b> its frame (cropping to the edges) or sits <b>inside</b> it. To show only
part of a photo, use the <b>Crop</b> tool:</p>
{proc('crop a picture',
  'Select the picture and choose the <b>Crop</b> tool.',
  'Drag the handles inward to hide the parts you do not want.',
  'Switch back to the Pointer. The hidden area is kept, so you can re-crop later.')}
<p>Round the frame's corners or give it an outline from the <b>Line</b> panel to finish it off.</p>"""),
      ("Editing a photo in PAINTcanvas", f"""
<p>When a photo needs more than cropping — brightening, retouching, removing a background —
PAGEdesigner sends it to its sister app.</p>
{proc('edit a picture in PAINTcanvas',
  'Select the picture.',
  'Click <b>Edit in PAINTcanvas</b> on the Apps toolbar.',
  'Make your edits in PAINTcanvas and save. The edited version comes straight back into your page, in place.')}
{tip('No photo to hand? <b>Create an image with AI</b> can generate one from a short description, dropped straight into the selected frame.')}""")]))

    ch.append(("Shapes, Lines and QuickShapes",
      "<p class='lede'>Shapes and lines give a page structure and emphasis — a coloured band for a "
      "masthead, a rule between stories, a star on an offer. PAGEdesigner's QuickShapes give you two "
      "dozen ready outlines, each with a fill, an outline and optional effects.</p>", [
      ("Drawing shapes and lines", f"""
{proc('draw a shape or a line',
  'Choose the <b>Rectangle</b>, <b>Ellipse</b> or <b>Line</b> tool (or a QuickShape).',
  'Drag on the page to draw it. Hold ' + K('Shift') + ' to constrain a perfect square, circle, or a straight / 45° line.',
  'Switch to the Pointer to move, resize or recolour it.')}
{fig(IM.get('shapes'), 'Basic shapes, a line, a row of QuickShapes, and the same rectangle with a drop shadow and with an outer glow.')}
<p>A thin filled rectangle makes a neat rule between stories — the green bars in the sample newsletter
are exactly that.</p>"""),
      ("The QuickShape catalogue", f"""
<p><b>QuickShapes</b> are ready-made outlines. Pick one from the tool palette or from <b>Insert ▸
QuickShapes</b>, drag it out, then resize and recolour it like any other shape.</p>
{fig(IM.get('qshapes'), 'All of PAGEdesigner’s QuickShapes.')}
<p>They cover geometry (triangles, diamonds, polygons), stars and bursts, arrows and a chevron, and the
expressive shapes — heart, lightning bolt, speech bubble, cloud — plus banner shapes (ribbon, pennant,
seal) ready for a badge or a title bar.</p>"""),
      ("Fills, outlines, dashes and arrowheads", """
<p>Every shape has a <b>fill</b> and an <b>outline</b>, set from the Colour and Line panels. A line can
be made <b>dashed</b> and finished with <b>arrowheads</b> at either or both ends — a dashed line with an
arrowhead is the simplest callout you can draw. Set the outline <b>width</b> in the Line panel; set it to
zero for a shape with no border at all.</p>"""),
      ("Drop shadow and glow", f"""
<p>Filter effects lift an object off the page.</p>
{proc('add a drop shadow or a glow',
  'Select the shape (or picture, or text).',
  'Open the <b>Effects</b> dialog.',
  'Tick <b>drop shadow</b> and set its colour, blur, offset and strength — or tick <b>outer glow</b> for a soft halo.',
  'Click <b>OK</b>.')}
{fig(dlg('Effects — Shadow & Glow', 'Effects'), 'The Effects dialog controls a drop shadow and an outer glow.')}
<p>A drop shadow adds depth behind a panel; an outer glow draws the eye to a price or a highlight.</p>""")]))

    ch.append(("Colour, Fills and Transparency",
      "<p class='lede'>Colour ties a publication together. PAGEdesigner offers solid colours, swatches "
      "you keep to hand, smooth gradient fills, coordinated colour schemes, and adjustable "
      "transparency.</p>", [
      ("Applying colour", f"""
{proc('colour an object',
  'Select it.',
  'Open the <b>Colour</b> panel and choose the <b>Fill</b>, <b>Line</b> or <b>Text</b> tab, to say which part you are colouring.',
  'Pick a colour with the sliders, or type a <b>hex</b> value like <code>#2a7d6b</code>.')}
{fig(IM.get('colourpage'), 'Flat colour, a linear gradient and an angled gradient; below, a semi-transparent panel makes white text readable over a photo.')}"""),
      ("Swatches and colour schemes", """
<p>The <b>Swatches</b> panel keeps a palette of colours one click away, so a document stays consistent —
save a colour you use often and reuse it everywhere rather than matching hex values by hand.</p>
<p>A <b>colour scheme</b> goes further: it is a small set of coordinated colours applied across the whole
publication at once. Pick a different scheme and every object that uses it recolours together, so you can
try a document warm, then cool, then monochrome, in seconds.</p>"""),
      ("Gradient fills", f"""
<p>A <b>gradient</b> fades one colour smoothly into another across a shape — a sky behind a headline, a
soft panel behind text.</p>
{proc('fill a shape with a gradient',
  'Select the shape.',
  'Open the <b>Gradient Fill</b> dialog.',
  'Choose a <b>start</b> and <b>end</b> colour, and for a linear gradient, an <b>angle</b>.',
  'Click <b>OK</b>. The gradient scales with the object as you resize it.')}
{fig(dlg('Linear Gradient', 'Radial Gradient', 'Gradient'), 'The gradient dialog: a start colour, an end colour and an angle.')}"""),
      ("Picture and texture fills", f"""
<p>A shape need not be filled with a flat colour or a gradient — it can be filled with a <b>picture</b>.
Drop a photo into a heading banner, a paper texture behind a certificate, a pattern inside a star.</p>
{proc('fill a shape with a picture',
  'Select the shape (or a text box or button).',
  'Choose <b>Format ▸ Picture Fill…</b> and pick an image file.',
  'Choose how it should fit — <b>Stretch to fill</b> the shape, or <b>Tile</b> it (repeat the picture).',
  'Click <b>OK</b>. The outline, corners and any shadow or glow still apply over the top.')}
{fig(IM.get('bitmap_demo'), 'The same star and banner filled with a picture — stretched (left) and tiled (right).')}
{tip('To go back to a plain colour, choose <b>Format ▸ Remove Picture Fill</b>.')}"""),
      ("Replacing a colour everywhere", f"""
<p>Change your mind about a colour after building a whole publication? You do not have to re-select every
object. <b>Replace Colour</b> swaps one colour for another across every page at once — fills, outlines,
text, gradients, tables and charts included.</p>
{proc('replace a colour across the whole publication',
  'Choose <b>Format ▸ Replace Colour…</b>.',
  'From the list of colours actually used in the document, click the one you want to change (each shows how many times it is used).',
  'Pick the colour to change it to.',
  'Click <b>Replace</b>. Every instance updates at once — and Undo (' + K('Ctrl') + '+' + K('Z') + ') reverts it if you change your mind.')}
{fig(dlg('Replace Colour'), 'Replace Colour lists every colour in use; pick one and the colour to change it to.')}
{note('This is the quick way to re-brand a finished document, or to fix a colour that prints differently from how it looked on screen.')}"""),
      ("Transparency", """
<p><b>Transparency</b> lets what is behind an object show through it. A half-transparent coloured
rectangle laid over a photo makes a tint you can read white text on; a faint shape becomes a watermark.
Set an object's transparency from the <b>Transparency</b> panel — from fully solid to barely there.</p>""")]))

    ch.append(("Tables, Charts, QR Codes and More",
      "<p class='lede'>Beyond free text, PAGEdesigner builds the structured pieces a real publication "
      "needs: tables for data, charts that picture it, scannable QR codes, a calendar wizard and a mail "
      "merge for personalised runs.</p>", [
      ("Tables", f"""
{proc('insert a table',
  'Choose <b>Insert ▸ Table</b> (or the Table tool).',
  'Set the number of <b>rows</b> and <b>columns</b>.',
  'Type straight into the cells; press ' + K('Tab') + ' to move to the next cell.',
  'Give the header row its own fill, and drag the borders to size the table or individual columns.')}
{fig(dlg('Edit Table', 'Table', 'Insert Table'), 'The table editor: set rows and columns and type the cell contents.')}
<p>A table is ideal for a price list, a timetable, or the “Dates for the diary” box in the sample
newsletter.</p>"""),
      ("Charts", f"""
{proc('insert a chart',
  'Choose <b>Insert ▸ Chart…</b>.',
  'Pick a type — <b>bar</b>, <b>line</b> or <b>pie</b>.',
  'Type the data, one “label, value” per line, and give the chart a title.',
  'Click <b>OK</b>. Double-click the chart any time to change its data or type.')}
{fig(dlg('Chart', 'Insert Chart', 'Chart'), 'The chart dialog turns a short list of figures into a bar, line or pie chart.')}
{fig(IM.get('charts'), 'Bar, pie and line charts, and a QR code, inserted on one page — all vector, all sharp in the PDF.')}"""),
      ("QR codes", f"""
{proc('add a QR code',
  'Choose <b>Insert ▸ QR Code…</b>.',
  'Type what it should link to — a web address, an email (<code>mailto:…</code>), a phone number (<code>tel:…</code>) or any text.',
  'Click <b>OK</b>, then resize it like a picture. It stays sharp, so a phone camera reads it from a printed flyer or poster.')}
{fig(dlg('QR Code', 'QR code', 'Insert QR Code'), 'The QR Code dialog builds a scannable code from any text or link.')}"""),
      ("Calendars and mail merge", """
<p><b>Insert ▸ Calendar…</b> generates a monthly or yearly calendar you can drop onto a page and style —
handy for a community newsletter or a printed planner.</p>
<p><b>Insert ▸ Mail Merge…</b> takes a list of names and addresses from a CSV file and produces one copy
of the document per row, filling placeholder fields with each person's details — for letters, labels or
personalised flyers.</p>""")]))

    parts.append(("Part II", "Core Skills", ch))

    # ============================================================ PART III
    ch = []
    tpls = IM.get("_templates", [])
    assets = IM.get("_assets", [])

    # --- template catalogue chapter (auto-generated from the library) ---
    tpl_secs = [("Starting from a template", f"""
<p>The fastest way to a finished document is to start from a <b>design template</b> — a complete layout
you make your own. When PAGEdesigner opens, the Startup Assistant shows the gallery; click a template
and it opens as an ordinary document, fully editable.</p>
{fig(IM.get('templates_gallery'), 'The Design Templates gallery, grouped by kind.')}
{proc('build a document from a template',
  'In the Startup Assistant, choose <b>Start from a design</b>.',
  'Click a template that is close to what you want. It opens laid out.',
  'Replace the placeholder headings and body text with your own words.',
  'Double-click a picture frame to drop in your photo.',
  'Recolour, move or delete anything; then print or export a PDF.')}
{caution('A template is just a normal document once it opens — there is nothing special or locked about it. Change everything freely.')}""")]
    # group templates by category for the catalogue
    bycat = {}
    for t in tpls:
        bycat.setdefault(t.get("cat", "Other"), []).append(t)
    for cat in sorted(bycat):
        cards = []
        for t in bycat[cat]:
            img = IM.get("tpl:" + t["name"])
            cards.append(f'<div class="cat-card">{fig(img, H.escape(t["name"]))}</div>')
        tpl_secs.append((cat, f'<div class="catgrid">{"".join(cards)}</div>'))
    ch.append(("The Template Library",
      f"<p class='lede'>PAGEdesigner ships with {len(tpls)} ready-made design templates — posters, "
      "flyers, newsletters, menus, cards, a certificate and social-media posts. This chapter is an "
      "illustrated catalogue of every one; pick the nearest fit and make it yours.</p>", tpl_secs))

    # --- asset catalogue chapter ---
    asset_secs = [("What the asset library is", f"""
<p>Where a template is a whole page, an <b>asset</b> is a single ready-made graphic you drop onto a page
you are already building — the finishing touches that make a poster or flyer pop.</p>
{proc('add an asset to a page',
  'Choose <b>Insert ▸ Asset…</b>.',
  'Browse the gallery and click one; it lands in the middle of the page, selected.',
  'Drag it where you want it, resize it, recolour it from the Colour panel, and — on a badge or banner — click the words and retype them.')}
{fig(IM.get('asset_dlg'), 'The Insert Asset gallery — callouts, badges, banners, arrows and decorations.')}
{tip('A “SALE” badge becomes a “½ PRICE” badge in seconds, and a green ribbon becomes a red one with a single colour change — assets are built from the same editable shapes as everything else.')}""")]
    bycat = {}
    for a in assets:
        bycat.setdefault(a.get("cat", "Other"), []).append(a)
    for cat in ("Callouts", "Badges", "Banners", "Arrows & pointers", "Decorative"):
        if cat not in bycat:
            continue
        cards = []
        for a in bycat[cat]:
            img = IM.get("asset:" + a["name"])
            cards.append(f'<div class="cat-card asset">{fig(img, H.escape(a["name"]))}</div>')
        asset_secs.append((cat, f'<div class="catgrid assets">{"".join(cards)}</div>'))
    ch.append(("The Asset Library",
      f"<p class='lede'>The asset library holds {len(assets)} drop-in graphics — callouts, badges, "
      "banners, arrows and decorations — grouped by kind. This chapter illustrates every one.</p>",
      asset_secs))

    # --- design principles chapter ---
    ch.append(("Designing a Page",
      "<p class='lede'>The tools are only half the job; the other half is using them well. This chapter "
      "distils the handful of principles that separate a page that looks designed from one that looks "
      "typed — the same instincts a Canva or a PagePlus user relies on.</p>", [
      ("Start with a grid", """
<p>Before placing anything, set up column guides (View ▸ Guides…). Laying every object against the same
few lines — even when the page looks busy — is the single biggest thing that makes a layout feel calm
and intentional. Two or three columns suit most flyers and newsletters.</p>"""),
      ("Alignment and white space", """
<p>Line things up, and give them room. Nothing should sit a few stray pixels off from its neighbour —
select and <b>Align</b>. And resist filling every corner: generous margins and space around a headline
make a page look confident, not empty. Crowding is what reads as amateur.</p>"""),
      ("A limited palette and two fonts", """
<p>Pick two or three colours and stick to them — a colour scheme makes this effortless. Do the same with
type: one font for headings, one for body, and vary <i>size</i> and <i>weight</i> rather than adding more
fonts. Restraint looks professional; variety for its own sake looks noisy.</p>"""),
      ("Hierarchy: lead the eye", """
<p>Decide what the reader should see first, second, third — and make the sizes say so. A big headline, a
clear subhead, calm body text. A poster has a loud first line and little else; a newsletter has a masthead,
then story headings, then columns. If everything shouts, nothing is heard.</p>"""),
      ("Contrast and emphasis", """
<p>Use contrast deliberately: dark text on a light panel, one accent colour on an otherwise quiet page, a
single badge or burst to mark the one thing that matters (the price, the date, the offer). A drop shadow
or a filled band behind a headline is often all the emphasis a page needs.</p>""")]))

    parts.append(("Part III", "Templates, Assets & Design", ch))

    # ============================================================ PART IV
    ch = []
    ch.append(("Project: A Community Newsletter",
      "<p class='lede'>This project builds the one-page newsletter you have seen throughout the guide, "
      "from a blank A4 page to a finished layout — putting the skills of Part II to work in order.</p>", [
      ("Set up the page", f"""
{proc('start the newsletter',
  'In the Startup Assistant choose <b>New Publication ▸ A4</b>.',
  'Open <b>View ▸ Guides…</b> and set two columns with a 5&nbsp;mm gutter, so you have a frame to work against.')}
{fig(IM.get('build1'), 'Step 1 — a coloured band across the top will become the masthead.')}
<p>Draw a filled rectangle across the full width of the top of the page, with no outline, in your main
colour. This band is the masthead's background.</p>"""),
      ("Add the masthead", f"""
<p>With the <b>Artistic text</b> tool, type the paper's name over the band and scale it large and white.
Add a small frame of text beneath it for the issue line.</p>
{fig(IM.get('build2'), 'Step 2 — the masthead title and strap line sit on the band.')}"""),
      ("Place the lead story", f"""
{proc('lay out the lead story',
  'Add an <b>artistic text</b> headline below the masthead.',
  'Draw a <b>text frame</b> in the left column and type (or paste) the story; it wraps to the column.',
  'Draw a <b>picture frame</b> in the right column and drop in a photo; add a small caption frame beneath it.')}
{fig(IM.get('build3'), 'Step 3 — headline, body column and a picture frame with its caption.')}"""),
      ("Add the diary table", f"""
<p>Below the photo, add a second heading and an <b>Insert ▸ Table</b> grid for the list of dates. Give its
header row the light tint from your scheme.</p>
{fig(IM.get('build4'), 'Step 4 — a “Dates for the diary” heading and a two-column table.')}"""),
      ("Finish and export", f"""
<p>Rule a thin coloured line across the foot of the page and add a small footer frame. Run a spell check
({K('F7')}), then <b>File ▸ Export PDF…</b>.</p>
{fig(IM.get('sample'), 'The finished newsletter, ready to print or send.')}
{tip('Save this as your own template: next issue, open it, change the words and the photo, and you are done in minutes.')}""")]))

    # Project chapters that reuse real templates as the illustration
    def tpl_img(name):
        return IM.get("tpl:" + name)

    ch.append(("Project: An Event Poster",
      "<p class='lede'>A poster has one job: to be read across a room. This short project shows the "
      "poster way of thinking — one loud message, little else — using a large-format page.</p>", [
      ("A poster is mostly one thing", f"""
<p>Start from <b>New Publication</b> at A3 or A2 (or the <b>Event poster</b> template as a head start).
A poster is built around a single dominant element: the event name, huge, and the one fact the reader
must take away — the date, or the price.</p>
{fig(tpl_img('Event poster') or tpl_img('Gig poster') or tpl_img('Workshop poster'), 'An event-poster layout: a dominant title, a strong image or colour field, and the essential details.')}"""),
      ("Build it", f"""
{proc('lay out the poster',
  'Fill the page with a background — a bold colour, a gradient, or a full-bleed photo in a picture frame.',
  'Add the event name as <b>artistic text</b>, as large as it will go.',
  'Add a second line for the single key fact, and a smaller block for the details at the foot.',
  'Drop a <b>badge</b> asset (a burst or seal) on the one thing you want noticed.',
  'Add a <b>QR code</b> that links to tickets or more information.')}
{caution('If you find yourself shrinking the title to fit more words in, cut the words instead. A poster that tries to say everything says nothing.')}""")]))

    ch.append(("Project: Business Cards and Folded Cards",
      "<p class='lede'>Small formats have their own discipline: every millimetre counts, and the piece "
      "will be cut and sometimes folded. This project covers a business card and a folded greeting "
      "card.</p>", [
      ("A business card", f"""
<p>Start from a <b>Business card</b> size or template. The whole design is a name, a role, and two or
three ways to reach you — balanced, aligned, and sitting clear of the edges.</p>
{fig(tpl_img('Business card — classic') or tpl_img('Business card — bold'), 'A business-card template: name and role, contact details, and room to breathe.')}
{proc('make a business card',
  'Choose the business-card page size.',
  'Keep all text a few millimetres inside the edge — a guillotine is never perfectly accurate.',
  'Use the <b>Insert ▸ Contact detail</b> items to pull your name, email and phone from Settings.',
  'Export a PDF; for a print shop, turn on bleed and crop marks in the export options.')}"""),
      ("A folded card", f"""
<p>For a greeting card or thank-you card, start from a folded size. Remember that the panels print on one
sheet and fold — the front is not the first thing in reading order.</p>
{fig(tpl_img('Thank-you card') or tpl_img('Party invitation'), 'A folded-card template.')}
{note('Booklet and folded sizes impose the pages in the right printing order for you, so you can design in reading order and trust the print to come out folded correctly.')}""")]))

    ch.append(("Project: A Certificate or Voucher",
      "<p class='lede'>A certificate is a landscape page built around symmetry and a little ceremony — "
      "a good exercise in centring, borders and restrained ornament.</p>", [
      ("Build a certificate", f"""
{fig(tpl_img('Certificate') or tpl_img('Gift voucher'), 'A certificate template: a border, a centred title, a name line and a place to sign.')}
{proc('make a certificate',
  'Start from the <b>Certificate</b> template, or a landscape A4 page.',
  'Add a decorative border (a shape with a thick outline, or a <b>banner</b> asset at the top).',
  'Centre everything: title, “awarded to”, the name line, and the reason, using <b>Align ▸ Centre on Page</b>.',
  'Add a <b>seal</b> or <b>star badge</b> asset, and lines for a signature and date.')}
{tip('A voucher is the same idea at a smaller size, with a value and an expiry date — and a QR code the till can scan.')}""")]))

    parts.append(("Part IV", "Worked Projects", ch))

    # ============================================================ PART V
    ch = []
    ch.append(("Checking Your Work",
      "<p class='lede'>A few minutes checking before you publish saves a reprint later. PAGEdesigner "
      "gives you a spell check and a preflight look-over.</p>", [
      ("Spell check and proofreading", f"""
<p>Run <b>Format ▸ Check Spelling…</b> ({K('F7')}) as a last pass. Then read the page itself: a spell
checker cannot tell you that a headline is missing a word, or that a date is wrong. Read every heading
and every number aloud.</p>"""),
      ("Preflight", """
<p><b>File ▸ Preflight</b> looks over the document for the common problems — an overflowing text frame, an
object hanging off the page edge, a very low-resolution picture — and lists anything worth a second look
before you commit it to paper or PDF.</p>""")]))

    ch.append(("Printing and Exporting",
      "<p class='lede'>When the layout is ready, you put it into the world — on paper, as a PDF, or as "
      "an eBook. This chapter covers each, and importing work from other programs.</p>", [
      ("Previewing before you print", f"""
<p>Before committing a document to paper or PDF, look it over whole. <b>File ▸ Print / PDF Preview</b>
shows every page exactly as it will come out, one after another, so you can catch a stray object or a
page in the wrong order.</p>
{fig(dlg('Print / PDF Preview'), 'The preview shows every page as it will print; print or save a PDF straight from here.')}
<p>From the preview you can go straight to <b>Print…</b> or <b>Export PDF…</b>, or close it and keep
editing.</p>"""),
      ("Printing", f"""
{proc('print the document',
  'Choose <b>File ▸ Print</b>.',
  'Pick the printer, the pages and the number of copies.',
  'Check the preview, then print.')}"""),
      ("Exporting a PDF", f"""
<p>A PDF is the standard way to send a document to a print shop or share it online.</p>
{proc('export a PDF',
  'Choose <b>File ▸ Export PDF…</b> (' + K('Ctrl') + '+' + K('E') + ').',
  'Choose a file name and location.',
  'For professional printing, turn on <b>bleed</b> and <b>crop marks</b> so the printer can trim to the edge cleanly.',
  'Click <b>Export</b>.')}
{note('PAGEdesigner’s PDF is <b>vector</b>: text and shapes stay razor-sharp at any size, and the file is small. It is the best format for anything that will be printed.')}"""),
      ("Imposition and booklet printing", f"""
<p><b>Imposition</b> is the printer's art of arranging several document pages onto one larger sheet, so
that after printing, folding and trimming they end up in the right order. PAGEdesigner offers it both in
the <b>Export PDF</b> dialog (the <b>Layout</b> drop-down) and from the <b>Print / PDF Preview</b>, which
shows the composed sheets before you commit.</p>
<ul>
<li><b>1-up (normal)</b> — one document page per sheet. This is the default, and what you want for
ordinary printing or sending a PDF to a print shop.</li>
<li><b>2-up</b> — two pages side by side on each sheet: a quick way to proof, or to print a simple
landscape leaflet.</li>
<li><b>4-up</b> — four pages (two across, two down) on each sheet, for thumbnails, labels or small cards.</li>
<li><b>Booklet</b> — pages reordered into <b>saddle-stitch</b> folding sequence: print double-sided, fold
the stack in half and staple the spine, and the pages read 1, 2, 3… in order. PAGEdesigner pads the
count to a multiple of four with blank pages, as the fold requires.</li>
</ul>
{proc('print a folded booklet',
  'Choose <b>File ▸ Print / PDF Preview</b> and set <b>Layout</b> to <b>Booklet</b> to see the imposed sheets.',
  'Choose <b>Export PDF…</b> (or <b>Print…</b>) from the preview, keeping the Booklet layout.',
  'Print the PDF double-sided (flip on the short edge), fold the stack in half, and staple along the fold.')}
{fig(dlg('Print / PDF Preview'), 'The Print / PDF Preview with a Layout selector — here showing imposed sheets.')}
{caution('For a booklet, your document should read in simple page order (1, 2, 3…). PAGEdesigner does the folding arithmetic; you supply the pages in reading order.')}"""),
      ("Exporting an eBook", """
<p><b>File ▸ Export eBook…</b> writes a reflowable <b>EPUB</b> from the text on your pages — each page
becomes a chapter, with a contents list, ready to read on a phone, tablet or e-reader. Where a PDF
preserves your exact layout, an eBook lets the reader's device choose the type size and re-flow the words
to fit its screen — right for a long, text-led document, less so for a poster.</p>"""),
      ("Importing from PagePlus, WebPlus and PDF", """
<p>PAGEdesigner opens work from the programs it stands in for. <b>File ▸ Open PagePlus…</b> reads a Serif
PagePlus <code>.ppp</code> publication; it can import a WebPlus site, and place a PDF as an editable
document. In each case your original file is left untouched, so there is no risk in trying.</p>"""),
      ("Working with Canva", f"""
<p><b>Canva</b> is a popular online design tool, and you can move work both ways between it and
PAGEdesigner. There is one honest thing to know first: <b>Canva has no design file you can open directly</b>
— no <code>.canva</code> on your disk to double-click. What Canva <i>does</i> let you do is <b>Upload</b>
and <b>Download</b> designs as <b>PowerPoint (<code>.pptx</code>), PDF and images</b>. PAGEdesigner
bridges through exactly those formats, and of them <b>PowerPoint is the round-trip format</b>: Canva both
reads and writes it, so text survives the journey and stays editable.</p>
{proc('send a document to Canva',
  'Choose <b>File ▸ Export ▸ For Canva (PowerPoint / PDF / Images)…</b>.',
  'Pick <b>PowerPoint (.pptx)</b> — this is the default, and the one Canva reads best.',
  'Save the file, then in Canva choose <b>Create a design ▸ Import file</b> (or drag the <code>.pptx</code> onto Canva) and upload it.')}
{fig(dlg('For Canva'), 'The “For Canva” export chooser: PowerPoint keeps your text editable; PDF and images are also offered.')}
<p>You get one <b>slide per page</b>. Each slide carries a full-page picture of your design as its
background, and then every <b>text frame</b> is laid over the top as a <b>real, editable PowerPoint text
box</b> — so once it is in Canva you can retype and restyle the words in place. Pictures and shapes come
across baked into the background picture in this first version; the text is what stays live.</p>
{note('The three formats suit different needs. <b>PowerPoint (.pptx)</b> is the round-trip choice — use it whenever you may edit the text again in Canva. <b>PDF</b> is best when the look must not change. <b>Images</b> (one PNG per page) are handy for a quick post or a background.')}
{proc('bring a Canva design into PAGEdesigner',
  'In Canva, choose <b>Share ▸ Download</b> and pick <b>PowerPoint (PPTX)</b> (or a PDF, or a PNG/JPG image).',
  'In PAGEdesigner choose <b>File ▸ From Canva (PowerPoint / PDF / Image)…</b>.',
  'Pick the downloaded file. A <code>.pptx</code> becomes one page per slide with its text as text frames and its pictures placed; a PDF opens with each page placed; an image becomes a one-page document.')}
{caution('Because a <code>.pptx</code> carries only so much, imported pages are a faithful starting point rather than a pixel-perfect copy — check each page and nudge anything that shifted. A Canva <b>SVG</b> download is flattened, so PAGEdesigner brings it in as a full-page picture rather than separate objects.')}""")]))

    parts.append(("Part V", "Output & Publishing", ch))

    # ============================================================ PART VI (reference)
    ch = []
    ch.append(("Appendix A — Menu Reference", "<p class='lede'>Every menu and the command on it.</p>", [
      ("File", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>New…</td><td>Start a new document via the Startup Assistant</td></tr>
<tr><td>Open… / Open Recent</td><td>Open a saved <code>.pagc</code> document, or a recent one</td></tr>
<tr><td>Open PagePlus…</td><td>Import a Serif PagePlus <code>.ppp</code> publication</td></tr>
<tr><td>From Canva (PowerPoint / PDF / Image)…</td><td>Import a Canva-downloaded <code>.pptx</code>, PDF or image as a new document</td></tr>
<tr><td>Save / Save As…</td><td>Save the document, or save a copy under a new name</td></tr>
<tr><td>Export ▸ For Canva (PowerPoint / PDF / Images)…</td><td>Write a <code>.pptx</code> (editable text over the design), a PDF, or one PNG per page to upload to Canva</td></tr>
<tr><td>Document Setup…</td><td>Page size, orientation and margins</td></tr>
<tr><td>Preflight…</td><td>Check the document for common problems before output</td></tr>
<tr><td>Print…</td><td>Send the document to a printer</td></tr>
<tr><td>Export PDF… / Export eBook…</td><td>Write a vector PDF (with 1-up / 2-up / 4-up / booklet imposition), or a reflowable EPUB</td></tr>
<tr><td>Quit</td><td>Close the program (prompts to save)</td></tr></table>"""),
      ("Edit", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Undo / Redo</td><td>Step back and forward through your changes</td></tr>
<tr><td>Cut / Copy / Paste</td><td>Move or copy the selection via the clipboard</td></tr>
<tr><td>Duplicate</td><td>Drop a copy of the selection, slightly offset</td></tr>
<tr><td>Delete</td><td>Remove the selection</td></tr>
<tr><td>Find &amp; Replace… (Ctrl+H)</td><td>Find and replace text across every page, tag-safe</td></tr>
<tr><td>Select All</td><td>Select every object on the page</td></tr></table>"""),
      ("View", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Booklet view</td><td>Show facing pages, as a reader would see them</td></tr>
<tr><td>Rulers / Grid / Snap / Crosshair</td><td>Toggle the on-screen aids</td></tr>
<tr><td>Guides…</td><td>Set up column and row guides</td></tr>
<tr><td>Zoom In / Out / 100% / Fit</td><td>Change the zoom level</td></tr></table>"""),
      ("Insert", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>New Page / Page Number</td><td>Add a page; insert an automatic page-number field</td></tr>
<tr><td>Place PDF…</td><td>Drop a PDF onto the page as a picture</td></tr>
<tr><td>Text, Picture, Table, shapes…</td><td>Insert each kind of object</td></tr>
<tr><td>QuickShapes ▸</td><td>The full gallery of preset shapes</td></tr>
<tr><td>Asset…</td><td>The callout / badge / banner / decoration gallery</td></tr>
<tr><td>Chart… / QR Code…</td><td>A data chart; a scannable QR code</td></tr>
<tr><td>Calendar… / Mail Merge…</td><td>A calendar grid; a personalised run from a CSV</td></tr>
<tr><td>Table of Contents… / Update Table of Contents</td><td>Insert a contents list built from the pages; rebuild it after changes</td></tr>
<tr><td>Contact detail ▸</td><td>A text frame showing a field from Settings (name, email, phone…)</td></tr></table>"""),
      ("Format", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bold / Italic / Underline</td><td>Character styling for selected text</td></tr>
<tr><td>Align Left / Centre / Right / Justify</td><td>Paragraph alignment</td></tr>
<tr><td>Text Styles ▸</td><td>Apply a named style (Heading, Body…)</td></tr>
<tr><td>Lists / Bullets ▸</td><td>Bulleted or numbered list styles</td></tr>
<tr><td>Drop Cap</td><td>Enlarge and inset a paragraph's first letter</td></tr>
<tr><td>Check Spelling… (F7)</td><td>Run the spell checker</td></tr>
<tr><td>Page Properties…</td><td>Settings for the current page</td></tr></table>"""),
      ("Arrange", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bring to Front / Forward One</td><td>Move the selection up the stack</td></tr>
<tr><td>Send to Back / Back One</td><td>Move the selection down the stack</td></tr>
<tr><td>Align ▸</td><td>Line up or distribute selected objects</td></tr>
<tr><td>Lock / Unlock (Ctrl+L)</td><td>Pin the selection, or release it</td></tr>
<tr><td>Move Repeated Objects to Master Page…</td><td>Promote shared items onto the master</td></tr></table>"""),
      ("Help", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>User Guide / Quick Start</td><td>This book, and the short guide</td></tr>
<tr><td>Check for Updates… / Settings…</td><td>Update the app; change preferences</td></tr>
<tr><td>About</td><td>Version and credits</td></tr>
<tr><td>Buy Me a Coffee ☕</td><td>Support the maker</td></tr></table>""")]))

    ch.append(("Appendix B — Keyboard Shortcuts", "<p class='lede'>The keys worth learning.</p>", [
      ("Everyday", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>New / Open / Save</td><td>{K('Ctrl')}+{K('N')} · {K('Ctrl')}+{K('O')} · {K('Ctrl')}+{K('S')}</td></tr>
<tr><td>Undo / Redo</td><td>{K('Ctrl')}+{K('Z')} · {K('Ctrl')}+{K('Shift')}+{K('Z')}</td></tr>
<tr><td>Cut / Copy / Paste</td><td>{K('Ctrl')}+{K('X')} · {K('Ctrl')}+{K('C')} · {K('Ctrl')}+{K('V')}</td></tr>
<tr><td>Duplicate</td><td>{K('Ctrl')}+{K('D')}</td></tr>
<tr><td>Select all / Deselect</td><td>{K('Ctrl')}+{K('A')} · {K('Esc')}</td></tr>
<tr><td>Delete</td><td>{K('Delete')}</td></tr></table>"""),
      ("Text, objects and view", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>Bold / Italic / Underline</td><td>{K('Ctrl')}+{K('B')} · {K('Ctrl')}+{K('I')} · {K('Ctrl')}+{K('U')}</td></tr>
<tr><td>Check spelling</td><td>{K('F7')}</td></tr>
<tr><td>Lock / Unlock</td><td>{K('Ctrl')}+{K('L')}</td></tr>
<tr><td>Nudge selection</td><td>{K('↑')} {K('↓')} {K('←')} {K('→')}</td></tr>
<tr><td>Constrain while drawing/rotating</td><td>hold {K('Shift')}</td></tr>
<tr><td>Export PDF</td><td>{K('Ctrl')}+{K('E')}</td></tr>
<tr><td>Zoom in / out</td><td>{K('Ctrl')}+{K('+')} · {K('Ctrl')}+{K('−')}</td></tr></table>""")]))

    ch.append(("Appendix C — Tools and Panels", "<p class='lede'>A reference to the tool palette and the panels.</p>", [
      ("The tool palette", f"""
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}
<table class="ref"><tr><th>Tool</th><th>Use</th></tr>
<tr><td>Pointer</td><td>Select, move and resize objects</td></tr>
<tr><td>Pan / Zoom</td><td>Move around the page; change the zoom</td></tr>
<tr><td>Artistic text</td><td>A single scalable line — titles and mastheads</td></tr>
<tr><td>Text frame</td><td>A box of body text that wraps and can flow</td></tr>
<tr><td>Picture</td><td>A frame to hold a photograph</td></tr>
<tr><td>Table</td><td>A grid of cells</td></tr>
<tr><td>Rectangle / Ellipse / Line</td><td>Basic shapes and rules</td></tr>
<tr><td>QuickShapes</td><td>Two dozen preset shapes</td></tr>
<tr><td>Rotate / Crop</td><td>Turn an object; trim a picture</td></tr></table>"""),
      ("The panels", f"""
{fig(IM.get('panelstack'), 'The panel stack.')}
<table class="ref"><tr><th>Panel</th><th>Use</th></tr>
<tr><td>Pages</td><td>Add, delete, reorder pages; master pages</td></tr>
<tr><td>Colour / Swatches</td><td>Set and save fill, line and text colours</td></tr>
<tr><td>Line</td><td>Outline width, dashes, arrowheads</td></tr>
<tr><td>Transparency</td><td>How much shows through</td></tr>
<tr><td>Transform</td><td>Exact position, size and rotation</td></tr>
<tr><td>Layers</td><td>Stacking and grouping</td></tr></table>""")]))

    ch.append(("Appendix D — Glossary", "<p class='lede'>The desktop-publishing words used in this guide.</p>", [
      ("A–Z", """<dl class="gloss">
<dt>Artistic text</dt><dd>A single line of display type you scale freely; vector, so always sharp.</dd>
<dt>Bleed</dt><dd>Extra colour or image past the trim edge, so a cut leaves no white sliver.</dd>
<dt>Crop marks</dt><dd>Corner ticks on a PDF that show a print shop where to trim.</dd>
<dt>Drop cap</dt><dd>An enlarged first letter set into the opening lines of a paragraph.</dd>
<dt>Flow</dt><dd>Running text on from one frame to the next, newspaper-style.</dd>
<dt>Frame</dt><dd>A box that holds text or a picture; you size the box and its contents independently.</dd>
<dt>Gradient</dt><dd>A smooth fade from one colour to another across a shape.</dd>
<dt>Gutter</dt><dd>The gap between two columns.</dd>
<dt>Master page</dt><dd>A page behind the others whose content repeats on every page that uses it.</dd>
<dt>Object</dt><dd>Anything you place on a page — text, picture, shape, table, chart.</dd>
<dt>Preflight</dt><dd>An automatic check for common problems before output.</dd>
<dt>QuickShape</dt><dd>A ready-made shape outline (star, arrow, speech bubble…).</dd>
<dt>Swatch</dt><dd>A saved colour kept one click away.</dd>
<dt>Vector</dt><dd>Artwork defined by maths, not pixels — sharp at any size.</dd>
</dl>""")]))

    ch.append(("Appendix E — Troubleshooting", "<p class='lede'>Quick answers to common snags.</p>", [
      ("Common questions", """<dl class="gloss">
<dt>A red mark shows in the corner of a text frame.</dt><dd>The frame holds more text than it can show. Make the frame bigger, shrink the text, or flow it into a second frame.</dd>
<dt>My picture looks fuzzy in the PDF.</dt><dd>The image file is too low-resolution for the size you have printed it. Use a larger original, or make the frame smaller.</dd>
<dt>Text or colour is being cut off at the page edge when printed.</dt><dd>Keep content a few millimetres inside the edge, and turn on bleed in the PDF export if a design is meant to run to the edge.</dd>
<dt>I can't select an object.</dt><dd>It may be locked (Arrange ▸ Lock / Unlock) or on a master page (edit the master), or behind another object (use the Layers panel).</dd>
<dt>Everything I type goes into one line and won't wrap.</dt><dd>You are using Artistic text, which is a single line. Use a Text frame for anything more than a title.</dd>
<dt>The app won't start on Linux Mint.</dt><dd>Run the installer again from a terminal; it sets up its own private Python environment automatically if the system one is missing.</dd>
</dl>""")]))

    parts.append(("Part VI", "Reference", ch))
    return parts


# ------------------------------------------------------------------- quickstart
def quickstart_sections(IM):
    def f(k, cap):
        return fig(IM.get(k), cap)
    S = []
    S.append(("Welcome to PAGEdesigner", f"""
<p class="lede">PAGEdesigner is a <b>desktop-publishing</b> program: you lay a page out by placing text,
pictures, shapes and tables exactly where you want them, then print it or export a PDF. It works the way
Serif's <b>PagePlus</b> did — the same menus, in the same places.</p>
<p>This Quick Start takes you from a blank page to a finished, printable newsletter in a dozen short
steps. For the complete reference — every feature, worked projects and a full menu guide — open the
<b>User Guide</b> (Help ▸ User Guide).</p>
{f('sample', 'A finished one-page newsletter, laid out entirely in PAGEdesigner.')}"""))
    S.append(("Start a publication", f"""
<p>When PAGEdesigner opens it shows the <b>Startup Assistant</b>. Choose <b>Start from a design</b> to
build on a ready-made template, or <b>New Publication</b> for a blank paper size — A4, a card, a booklet
or a poster.</p>
{f('startup_sizes', 'The Startup Assistant: start from a design, a paper size, or recent work.')}"""))
    S.append(("The workspace", f"""
<p>Your page sits in the middle, the <b>tools</b> down the left, the <b>menus and toolbars</b> across the
top, and the <b>panels</b> on the right.</p>
{f('workspace', 'Tools on the left, your page in the middle, panels on the right.')}"""))
    S.append(("Start from a template", f"""
<p>The quickest route to a finished piece is <b>Start from a design</b>. Pick a layout, then make it your
own — change the words, swap the photo, recolour anything.</p>
{f('templates_gallery', 'The Design Templates gallery.')}"""))
    S.append(("Add text", f"""
<p>Drag out a <b>text frame</b> and type; the text wraps inside it. For a headline or masthead, use
<b>Artistic text</b> — a single line you scale freely. A frame that overflows can <b>flow</b> into a
second, linked frame.</p>
{f('textpage', 'Frame text with a drop cap and a list, beside an artistic headline.')}"""))
    S.append(("Add pictures", """
<p>Draw a <b>picture frame</b> with the Picture tool, then double-click it to drop in a photo. Crop it or
round its corners; for real edits, <b>Edit in PAINTcanvas</b> sends it across and brings the result
back.</p>"""))
    S.append(("Shapes and QuickShapes", f"""
<p>Draw rectangles, ellipses and <b>QuickShapes</b> — stars, arrows, speech bubbles and more. Each has a
fill and an outline, and can carry a drop shadow or glow.</p>
{f('shapes', 'Basic shapes, a line and a row of QuickShapes.')}"""))
    S.append(("Tables, charts and QR codes", f"""
<p><b>Insert ▸ Table</b> drops a grid you type into; <b>Insert ▸ Chart…</b> turns figures into a bar, line
or pie chart; <b>Insert ▸ QR Code…</b> makes a scannable code for a flyer.</p>
{f('charts', 'Charts and a QR code on one page.')}"""))
    S.append(("Arrange and align", """
<p>With the <b>Pointer</b>, click to select, drag to move, pull the handles to resize. <b>Arrange ▸
Align</b> lines objects up; <b>Transform</b> sets exact positions; <b>Lock</b> stops accidental nudges.</p>"""))
    S.append(("Colour and transparency", f"""
<p>The <b>Colour</b> panel sets a fill, line or text colour; <b>Swatches</b> keeps favourites handy. Add a
<b>gradient</b> fill, or make something <b>transparent</b> so what's behind shows through.</p>
{f('colourpage', 'Flat colour, gradients, and a transparent panel over a photo.')}"""))
    S.append(("Add finishing touches from the Asset library", f"""
<p><b>Insert ▸ Asset…</b> drops in ready-made callouts, badges, banners and decorations — a SALE burst, a
ribbon, an arrow. Everything stays editable: recolour it, retype the words.</p>
{f('qshapes', 'Shapes and assets give a page emphasis and polish.')}"""))
    S.append(("Check, then print or export", f"""
<p>Run <b>Check Spelling…</b> ({K('F7')}) and a quick <b>Preflight</b>. Then <b>Export PDF…</b>
({K('Ctrl')}+{K('E')}) for a crisp vector PDF, or <b>File ▸ Print</b> to send it to your printer.</p>"""))
    S.append(("Where to go next", """
<p>That is the whole round trip: new page → text, pictures, shapes and tables → arrange → export. The
<b>User Guide</b> covers every feature in depth, with worked projects and a full reference. And the other
<i>just a…</i> apps work the same way — once you know one, you know them all.</p>"""))
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
    top = f'<img class="cv-banner" src="{uri}" alt="">' if uri else '<div style="font-size:3rem;font-weight:800;color:var(--accent)">PAGEdesigner</div>'
    return (f'<section class="cover"><div class="cv-inner">{top}'
            f'<div class="cv-kind">{kind}</div><div class="cv-rule"></div>'
            f'<div class="cv-sub">just a&hellip; PAGEdesigner &mdash; a page-layout program in the spirit of Serif PagePlus</div>'
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
<title>just a… PAGEdesigner — Quick Start Guide</title>
<style>{CSS}{COVER_CSS}{QS_CSS}</style>
<div class="page">
{cover('Quick Start Guide')}
<header class="mast"><h1>PAGEdesigner — Quick Start</h1>
<p>From a blank page to a finished, printable document — in a dozen steps.</p></header>
<h2 style="border:0">Contents</h2><ol class="toc">{toc}</ol>
{body}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… PAGEdesigner Quick Start · generated {date.today().isoformat()} · every picture is produced by the app itself.
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
    TERMS = ["drop cap", "master page", "text frame", "artistic text", "gradient fill", "bitmap fill",
             "picture fill", "replace colour", "QR code", "mail merge", "calendar", "chart", "table",
             "bleed", "crop marks", "preflight", "colour scheme", "swatch", "transparency", "QuickShape",
             "asset", "template", "eBook", "EPUB", "PDF", "spell check", "page number", "align", "group",
             "lock", "guides", "drop shadow", "outer glow", "text wrap", "crop", "picture frame",
             "Startup Assistant", "rulers", "margins", "booklet"]
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
<title>just a… PAGEdesigner — User Guide</title>
<style>{CSS}{COVER_CSS}{MANUAL_CSS}</style>
<div class="page">
{cover('User Guide')}
<header class="mast"><h1>PAGEdesigner</h1><p>User Guide — the complete reference for designing,
checking and publishing a document.</p></header>
<nav class="contents"><h2 style="border:0;font-size:1.6rem">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… PAGEdesigner User Guide · generated {date.today().isoformat()} · every picture is produced by the app itself ·
in the spirit of Serif PagePlus.</footer>
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
