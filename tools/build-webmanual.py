#!/usr/bin/env python3
"""Build WEBcreator's illustrated docs: quickstart.html (and, in progress, the
full manual.html) from real screenshots captured by driving the app itself.

    python3 tools/build-pagemanual.py            # both docs
    python3 tools/build-pagemanual.py --quick    # just quickstart.html

Every picture is grabbed from the running app (offscreen), so the guide always
matches what the program actually looks like. Images are embedded as data URIs,
so each HTML file is self-contained and installs with no extra assets.

Modelled on Serif WebPlus Quick Start / User Guide structure, describing
*this* app's real menus and features.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "webcreator" / "webcreator.py"
OUT = ROOT / "apps" / "webcreator"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-pagemanual", "--no-startup"]   # the app reads this to skip its Startup Assistant

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtCore import Qt                                      # noqa: E402

app = QApplication.instance() or QApplication([])
QDialog.exec = lambda self, *a, **k: 0
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))


def _load():
    spec = importlib.util.spec_from_file_location("webcreator", APP)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


PC = _load()
mk = PC.mk

try:
    from PIL import Image
except Exception:
    Image = None


# ---------------------------------------------------------------- screenshots
_TMP = ROOT / "tools" / "_tmp_grab.png"


def grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    im = Image.open(str(_TMP)).convert("RGB")
    return im.copy()


def _win():
    w = PC.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1180, 940); w.show()
    for _ in range(14):
        app.processEvents()
    return w


SAMPLE = [
    # header bar + logo + a simple nav
    ("shape", 0, 0, None, 70, dict(shape="rect", fill="#ffffff", stroke="#e4e9ec", strokeW=1)),
    ("artistic", 40, 18, 320, 36, dict(html="<p>Harbour &amp; Co.</p>", size=26, color="#2a7d6b", bold=True)),
    ("text", 560, 24, 360, 26, dict(pad=0, size=15, color="#394650", align="right", html="<p>Home&nbsp;&nbsp;·&nbsp;&nbsp;Work&nbsp;&nbsp;·&nbsp;&nbsp;About&nbsp;&nbsp;·&nbsp;&nbsp;Contact</p>")),
    # hero
    ("shape", 0, 70, None, 360, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("artistic", 60, 150, 860, 70, dict(html="<p>Handmade joinery, built to last</p>", size=42, color="#ffffff", bold=True)),
    ("text", 62, 250, 560, 60, dict(pad=0, size=18, color="#d7ece7", html="<p>Kitchens, staircases and restoration, made by hand in our harbourside workshop.</p>")),
    ("button", 62, 330, 190, 48, dict(html="<p>Get a free quote</p>", size=15, bold=True)),
    # three services
    ("artistic", 60, 470, 300, 34, dict(html="<p>What we do</p>", size=24, color="#243137", bold=True)),
    ("text", 60, 524, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Kitchens</b></p><p>Fitted kitchens in solid timber, designed around your room and built to measure.</p>")),
    ("text", 350, 524, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Staircases</b></p><p>New stairs and balustrades, and careful repairs to period originals.</p>")),
    ("text", 640, 524, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Restoration</b></p><p>Doors, windows and panelling brought back to life with traditional methods.</p>")),
    # picture + caption
    ("picture", 60, 700, 850, 300, dict(fill="#cfe0e6", stroke="#9fb8c0", strokeW=1)),
    ("text", 60, 1008, 850, 26, dict(pad=0, size=12, color="#5c6b73", html="<p><i>A recent kitchen, photographed on site.</i></p>")),
    # footer
    ("shape", 0, 1060, None, 90, dict(shape="rect", fill="#243137", strokeW=0)),
    ("text", 60, 1088, 850, 40, dict(pad=0, size=13, color="#c7d2d8", html="<p>Harbour &amp; Co. Joinery · Unit 4, Quay Street · 01234 567890 · © 2026</p>")),
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
        "<li>Add a bulleted or numbered list</li><li>Check spelling before you publish</li></ul>"))),
    ("artistic", 40, 430, 500, 56, dict(html="<p>Big artistic headlines</p>", size=38, color="#2a7d6b", bold=True)),
    ("text", 40, 500, 714, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>Artistic text is a single line you scale freely — ideal for titles and mastheads.</p>")),
]


def _add(w, objs, upto=None):
    pw = w.site.get("width", 794)
    for i, (t, x, y, ww, hh, p) in enumerate(objs):
        if upto is not None and i >= upto:
            break
        w.add_object(mk(t, x, y, pw if ww is None else ww, hh, **p))
    w.sel = []
    if hasattr(w, "set_tool"):
        w.set_tool("pointer")


def _add_sample(w, upto=None):
    _add(w, SAMPLE, upto)


def capture():
    """Return {key: PIL image} for every picture the guide needs."""
    imgs = {}

    # 1) Startup Assistant
    w = _win()
    dlg = PC.StartupAssistant(w)
    dlg.setAttribute(Qt.WA_DontShowOnScreen, True); dlg.resize(900, 640); dlg.nav.setCurrentRow(0); dlg.show()
    for _ in range(10):
        app.processEvents()
    imgs["startup"] = grab(dlg)

    # 2) Blank workspace (fresh document)
    w = _win()
    try: w.view.fit_width()
    except Exception: pass
    for _ in range(6):
        app.processEvents()
    imgs["workspace"] = grab(w)

    # 3) Finished home page in the workspace
    w = _win()
    _add_sample(w)
    for _ in range(8):
        app.processEvents()
    try: w.view.fit_width()
    except Exception: pass
    for _ in range(8):
        app.processEvents()
    imgs["sample"] = grab(w)

    # 4) Mid-build (masthead + headline only) — "adding objects"
    w = _win()
    _add_sample(w, upto=4)
    for _ in range(6):
        app.processEvents()
    try: w.view.fit_width()
    except Exception: pass
    for _ in range(6):
        app.processEvents()
    imgs["building"] = grab(w)

    # 5) Shapes / QuickShapes demo page
    w = _win()
    _add(w, SHAPES_DEMO)
    for _ in range(8):
        app.processEvents()
    try: w.view.fit_width()
    except Exception: pass
    for _ in range(8):
        app.processEvents()
    imgs["shapes"] = grab(w)

    # 6) Text demo page
    w = _win()
    _add(w, TEXT_DEMO)
    for _ in range(8):
        app.processEvents()
    try: w.view.fit_width()
    except Exception: pass
    for _ in range(8):
        app.processEvents()
    imgs["textpage"] = grab(w)

    return imgs


# ---------------------------------------------------------------- image helpers
def crop(im, box):
    return im.crop(box)


def datauri(im, maxw=1000, quality=84):
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- content model
def figure(uri_or_im, cap):
    uri = uri_or_im if isinstance(uri_or_im, str) else datauri(uri_or_im)
    return f'<figure><img src="{uri}" alt="{H.escape(cap)}"><figcaption>{cap}</figcaption></figure>'


def quickstart_sections(IM):
    """13 short chapters, WebPlus-Quick-Start style, for THIS app. Returns a list
    of (heading, html-body)."""
    S = []
    S.append(("Welcome to WEBcreator", f"""
<p class="lede">WEBcreator is a <b>desktop publishing</b> program: you lay a page out by placing
text, pictures, shapes and tables exactly where you want them, then preview it in your browser and publish it as plain HTML.
It works the way the old Serif <b>WebPlus</b> did — the same menus, in the same places.</p>
<p>This Quick Start walks you from a blank page to a finished, working website in about
thirteen short steps. For the complete reference, open <b>Help ▸ User Guide</b>.</p>
{figure(IM['sample'], 'A finished home page, built entirely in WEBcreator.')}"""))

    S.append(("Starting a publication", f"""
<p>When WEBcreator opens it shows the <b>Startup Assistant</b>. Choose a paper size —
A4, A5, a business card, a booklet or a large-format poster — or set your own under
<b>Custom size</b>, then click it to begin. You can also reopen a recent publication here.</p>
{figure(IM['startup'], 'The Startup Assistant: pick a paper size, or open recent work.')}
<p class="tip"><b>Tip</b> &mdash; turn the assistant off with the tick box at the bottom; bring it
back any time from <b>File ▸ New</b>.</p>"""))

    S.append(("The workspace", f"""
<p>A new document opens with your blank page in the middle. Around it:</p>
<ul>
<li>the <b>menu bar</b> and <b>toolbar</b> along the top;</li>
<li>the <b>tool palette</b> down the left (pointer, text, picture, shapes, lines);</li>
<li>the <b>rulers</b> framing the page;</li>
<li>the <b>Pages</b>, <b>Transform</b>, <b>Colour</b>, <b>Swatches</b> and <b>Layers</b> tabs on the right.</li>
</ul>
{figure(IM['workspace'], 'The workspace: tools on the left, your page in the middle, panels on the right.')}"""))

    S.append(("Pages and master pages", """
<p>Open the <b>Pages</b> tab to add, delete or reorder pages. Items you want on
<i>every</i> page — a logo, a footer, page numbers — go on a <b>master page</b>: choose
<b>Master properties</b>, add the object once, and it repeats behind every page that uses it.</p>
<p>Already built a page and want its shared parts promoted? <b>Arrange ▸ Move Repeated
Objects to Master Page…</b> does it for you.</p>"""))

    S.append(("Adding text", f"""
<p>Pick the <b>Text</b> tool and drag a rectangle: that is a <b>text frame</b>. Type into it and
the text wraps inside the frame. A frame that overflows shows a red marker — drag a link to a
second frame and the text <b>flows</b> on, newspaper-style.</p>
<p>For a headline or a masthead, use <b>Artistic text</b> instead — it is a single line you can
scale freely, like the “<i>The Quayside Gazette</i>” title here.</p>
{figure(IM['building'], 'A coloured shape makes the masthead; artistic text sits on top of it.')}"""))

    S.append(("Formatting text", """
<p>Select some text and use the <b>Format</b> menu and the text panel to set the font, size,
colour and alignment. You can also:</p>
<ul>
<li>give a paragraph a <b>drop cap</b>;</li>
<li>start a <b>bulleted or numbered list</b>;</li>
<li>run <b>Check Spelling…</b> (F7) before you print.</li>
</ul>"""))

    S.append(("Pictures", """
<p>Choose the <b>Picture</b> tool and drag a box to make a <b>picture frame</b> (the grey
placeholder on the sample page). Double-click it to drop in a photo; the picture fits the frame,
and you can <b>crop</b> it or round its corners. Need to touch the photo up? <b>Edit in
PAINTcanvas</b> sends it across and brings your edit back on save.</p>"""))

    S.append(("Shapes and lines", """
<p>The shape tools draw rectangles, ellipses and <b>QuickShapes</b> — stars, arrows, speech
bubbles and more. Each shape has a <b>fill</b> and an <b>outline</b> you set in the Colour and
Line panels, and you can add a <b>drop shadow</b> or <b>glow</b>. Use a thin filled rectangle as
a rule between stories, as the green bars do here.</p>"""))

    S.append(("Tables", f"""
<p><b>Insert ▸ Table</b> drops a grid you can type straight into — ideal for a price list or the
“Dates for the diary” box here. Set the number of rows and columns, give the header row its own
fill, and drag the edges to size it.</p>
{figure(crop_uri(IM['sample'], (403, 300, 700, 470)), 'A simple table with a coloured header row.')}"""))

    S.append(("Arranging objects", """
<p>With the <b>pointer</b>, click to select, drag to move, and pull the handles to resize. Then:</p>
<ul>
<li><b>Arrange ▸ Align</b> lines objects up with each other or the page;</li>
<li><b>Arrange</b> order sends things in front or behind;</li>
<li><b>Transform</b> sets an exact position, size or rotation;</li>
<li><b>Lock / Unlock</b> fixes something so you can’t nudge it by accident.</li>
</ul>"""))

    S.append(("Colour, fills and schemes", """
<p>The <b>Colour</b> tab sets a solid fill or outline; <b>Swatches</b> keeps colours to hand. Beyond
flat colour you can use a <b>gradient</b> fill and adjust an object’s <b>transparency</b> from the
panels of the same name. A <b>colour scheme</b> recolours the whole publication at once.</p>"""))

    S.append(("Check, then print or export", """
<p>Before you share it, run a <b>preflight check</b> and a final <b>spell check</b>. Then:</p>
<ul>
<li><b>Export PDF…</b> writes a crisp, vector PDF — the usual way to send a document to print;</li>
<li><b>File ▸ Print</b> sends it straight to your printer.</li>
</ul>
<p>Because the PDF is vector, text stays sharp at any size.</p>"""))

    S.append(("Where to go next", """
<p>That is the whole round trip: new page → text, pictures, shapes and tables → arrange → export.
Everything here is covered in far more depth in the <b>User Guide</b> (Help ▸ User Guide), and the
other apps in the family — WEBcreator, PAINTcanvas and DRAWmaster — work the same way, so once you
know one you know them all.</p>"""))
    return S


def crop_uri(im, box):
    return datauri(crop(im, box), maxw=800)


# ---------------------------------------------------------------- html assembly
CSS = """
:root{ --ink:#232b31; --mute:#64737c; --line:#d7dee3; --accent:#2a7d6b; --paper:#ffffff; --band:#eef3f2; }
*{box-sizing:border-box} body{margin:0;background:#e8edf0;color:var(--ink);
  font:16px/1.65 "Noto Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.page{max-width:820px;margin:28px auto;background:var(--paper);padding:56px 64px;
  box-shadow:0 2px 20px -8px rgba(20,40,50,.35);border-radius:4px;}
h1{font-size:2.3rem;margin:.1em 0 .1em;letter-spacing:-.01em}
.sub{color:var(--mute);margin:0 0 1.4em;font-size:1.05rem}
h2{font-size:1.5rem;margin:2.3em 0 .5em;padding-top:.5em;border-top:3px solid var(--accent);}
h2 .n{color:var(--accent);font-variant-numeric:tabular-nums;margin-right:.5em;font-weight:700}
.lede{font-size:1.1rem}
p{max-width:66ch} ul{max-width:66ch} li{margin:.2em 0}
figure{margin:1.3em 0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--band)}
figure img{width:100%;display:block}
figcaption{font-size:.86rem;color:var(--mute);padding:8px 12px;background:var(--band);border-top:1px solid var(--line)}
.tip{background:var(--band);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px;font-size:.95rem}
.toc{columns:2;gap:28px;margin:1.2em 0 0;padding:0;list-style:none}
.toc li{margin:.25em 0;break-inside:avoid} .toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--accent);text-decoration:underline} .toc .n{color:var(--accent);font-weight:700;margin-right:.5em}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:30px 36px;margin-bottom:0}
header.mast h1{margin:0;color:#fff} header.mast p{margin:.3em 0 0;color:#d7ece7}
footer{color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none} h2{break-after:avoid} figure{break-inside:avoid} }
"""


def build_quickstart(IM):
    S = quickstart_sections(IM)
    toc = "".join(f'<li><span class="n">{i+1}</span><a href="#s{i+1}">{H.escape(t)}</a></li>'
                  for i, (t, _) in enumerate(S))
    body = []
    for i, (t, html) in enumerate(S):
        body.append(f'<h2 id="s{i+1}"><span class="n">{i+1}</span>{H.escape(t)}</h2>\n{html}')
    doc = f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… WEBcreator — Quick Start Guide</title>
<style>{CSS}</style>
<div class="page">
<header class="mast"><h1>WEBcreator — Quick Start</h1>
<p>From a blank page to a finished, printable document — in thirteen steps.</p></header>
<ol class="toc">{toc}</ol>
{''.join(body)}
<footer>just a… WEBcreator Quick Start · generated {date.today().isoformat()} ·
every picture is produced by the app itself. See <b>Help ▸ User Guide</b> for the full manual.</footer>
</div>
</html>
"""
    (OUT / "quickstart.html").write_text(doc, encoding="utf-8")
    print("wrote quickstart.html:", len(doc) // 1024, "KiB,", len(S), "sections")


def manual_chapters(IM):
    """The full User Guide. Each chapter: (title, intro_html, [(heading, body_html)])."""
    W = IM["workspace"]
    tools = crop(W, (0, 76, 48, 900))
    toolbar = crop(W, (248, 34, 1178, 78))
    colour = crop(W, (700, 76, 1178, 470))
    pages = crop(W, (700, 470, 1178, 905))

    C = []

    C.append(("Getting Started",
      "<p class='lede'>WEBcreator is a page-layout program in the tradition of Serif’s "
      "WebPlus. You place text, pictures, shapes and tables on a page exactly where you want "
      "them, then preview in a browser and publish plain HTML you can upload anywhere. This chapter introduces the workspace and the "
      "everyday jobs of opening, saving and viewing a publication.</p>", [
      ("Starting the program", f"""
<p>Launch WEBcreator from the CREATORsuite launcher or by running <code>webcreator</code>.
It opens on the <b>Startup Assistant</b>, where you choose how to begin.</p>
{figure(IM['startup'], 'The Startup Assistant appears each time you start the program.')}"""),
      ("Starting from a template", """
<p>WEBcreator opens on the Startup Assistant, where you choose a starting point. The quickest way
to begin is from one of the <b>92 built-in templates</b> — complete little sites, each with a page
tree, colour schemes and placeholder content you simply replace. Ninety of them follow the page
structures Serif’s <b>WebPlus X8</b> shipped, so if you knew those you will feel at home.</p>
<p>Pick a template on the left, choose a colour scheme, untick any pages you don’t need, and open
it. Prefer a clean slate? Start a <b>blank site</b> and build the pages yourself.</p>"""),
      ("Opening and saving", """
<p>Use <b>File ▸ Open</b> for an existing <code>.webc</code> site, or the <b>Open</b> page of the
Startup Assistant for recent work. <b>File ▸ Save</b> (Ctrl+S) stores your site; <b>Save As</b>
makes a copy. By default sites are saved to your shared <i>Documents/just a…</i> folder, so the
CREATORsuite launcher can find them again.</p>
<p>WEBcreator also opens a Serif <b>WebPlus</b> site: <b>File ▸ Open WebPlus Site…</b> imports a
<code>.wpp</code> site as an editable document (your original is never touched), and
<b>Import Website Folder…</b> pulls in an existing set of HTML pages.</p>"""),
      ("The workspace", f"""
<p>A new document opens with the page in the centre and everything you need around it.</p>
{figure(IM['workspace'], 'The WEBcreator workspace.')}
<p>Down the left is the <b>tool palette</b>; along the top, the <b>menu bar</b> and <b>toolbar</b>;
to the right, the tabbed <b>panels</b> (Pages, Swatches, Line, Transparency, Transform, Layers and
the Colour picker). The <b>rulers</b> frame the page, and the status bar along the bottom shows the
current page and zoom.</p>
{figure(tools, 'The tool palette: pointer, pan, zoom, text, picture, table, shapes and lines.')}"""),
      ("Moving around and zooming", """
<p>Change the zoom with the control at the bottom-right, with Ctrl+scroll, or with the <b>Zoom</b>
tool. <b>View ▸ Fit Page</b> and <b>Fit Width</b> frame the page quickly. The <b>Pan</b> tool (or
holding the space bar) slides the page around when you are zoomed in.</p>""")]))

    C.append(("Setting Up Pages",
      "<p class='lede'>Every publication is a stack of pages that share a paper size and, usually, a "
      "common background. This chapter covers adding and arranging pages, master pages for repeating "
      "content, and the guides and rulers that keep a layout tidy.</p>", [
      ("Pages and the Pages tab", f"""
<p>The <b>Pages</b> tab lists every page in the document. Use the buttons beneath it to add a page,
delete the current one, or move a page up or down the running order. Double-click a page to go to it.</p>
{figure(pages, 'The Pages tab, with the page list above and master pages below.')}"""),
      ("Master pages", """
<p>Anything that should appear on <i>every</i> page — a logo, a footer, a page number, a watermark —
belongs on a <b>master page</b>. A master sits behind the ordinary pages that use it, so you draw the
object once and it shows through everywhere.</p>
<p>Create one with <b>New master page</b>, edit it with <b>Edit master page</b>, and set which master a
page uses from <b>Master properties</b>. Built a page already and realised several items repeat?
<b>Arrange ▸ Move Repeated Objects to Master Page…</b> lifts them onto the master for you.</p>"""),
      ("Rulers, guides and the grid", """
<p>Drag out from a ruler to drop a <b>guide line</b>; objects snap to guides as you move them, which
makes columns and margins easy to keep even. The ruler’s corner toggles between measurement origins.
Turn snapping and the layout grid on or off from the <b>View</b> menu.</p>"""),
      ("Headers, footers and page numbers", """
<p>Put headers and footers on a master page so they repeat. For automatic page numbers, add a text
frame to the master and insert a page-number field — each page then shows its own number without any
manual updating.</p>""")]))

    C.append(("Working with Objects",
      "<p class='lede'>Text frames, pictures, shapes and tables are all <b>objects</b>. Whatever the "
      "kind, you select, move, size, arrange and align them in the same way — the skills in this "
      "chapter apply everywhere in the program.</p>", [
      ("Selecting and moving", """
<p>With the <b>Pointer</b> tool, click an object to select it; Shift-click to add more to the
selection, or drag a band across several at once. Drag any selected object to move it; the handles
around it resize it, and the round handle above it rotates it.</p>"""),
      ("The Transform panel", """
<p>For exact control, open the <b>Transform</b> tab and type an object’s position, width, height or
rotation angle. This is the reliable way to make two objects the same size, or to place something a
precise distance from the page edge.</p>"""),
      ("Aligning and distributing", """
<p><b>Arrange ▸ Align</b> lines selected objects up — left edges, centres, right edges, tops or
bottoms — either to each other or to the page. <b>Distribute</b> spaces three or more objects evenly.
Alignment is what turns a rough arrangement into a crisp one.</p>"""),
      ("Order, grouping and locking", """
<p>Objects stack in the order you create them. <b>Arrange</b> sends a selection to the front or back,
or forward and back one step at a time, so a caption can sit over a picture. <b>Group</b> ties several
objects together so they move as one; <b>Lock / Unlock</b> pins something in place so you can’t nudge
it by accident.</p>""")]))

    C.append(("Text",
      "<p class='lede'>Text is the heart of most publications. WEBcreator handles it the WebPlus "
      "way — in frames you can link and flow, with artistic text for headlines, and full control over "
      "fonts, paragraphs and styles.</p>", [
      ("Text frames", f"""
<p>Choose the <b>Text</b> tool and drag a rectangle to make a <b>text frame</b>. Type into it and the
text wraps inside the frame’s edges. A frame is the basic container for body copy.</p>
{figure(IM['textpage'], 'Frame text with a drop capital and a bulleted list, beside an artistic headline.')}"""),
      ("Flowing and linking frames", """
<p>When a frame holds more text than it can show, an overflow marker appears. Drag a link from that
marker to another frame and the text <b>flows</b> on — exactly how a newspaper runs a story across
columns and pages. Resize or delete a frame and the text re-flows through the chain automatically.</p>"""),
      ("Artistic text", """
<p>Where frame text is for paragraphs, <b>artistic text</b> is a single line you can scale to any
size — the tool for mastheads, titles and pull-quotes. It stays crisp at any size because it is
vector, not a picture of type.</p>"""),
      ("Fonts, paragraphs and styles", """
<p>Select text and use the <b>Format</b> menu and the text panel to set the font, size, weight,
colour, alignment and line spacing. A <b>drop cap</b> enlarges the first letter of a paragraph into
the lines below it; <b>bulleted and numbered lists</b> structure a sequence of points. Running the
same look across a document is easier with text styles, so a heading is always the same heading.</p>"""),
      ("Wrapping and checking", """
<p>Text can <b>wrap</b> around a picture or shape so the two sit together neatly. Before you print,
run <b>Format ▸ Check Spelling…</b> (F7); you can also turn a tab-separated block of text into a real
table with <b>convert text to a table</b>.</p>""")]))

    C.append(("Navigation, Links and Interactive Parts",
      "<p class='lede'>A website is more than a single page — it is pages joined by links, with a few "
      "interactive pieces a printed document could never have. This chapter covers the parts that make "
      "a page a <i>web</i> page.</p>", [
      ("Navigation bars", f"""
<p>A <b>navigation bar</b> is the row of links that lets visitors move around your site. Drop one in
with the <b>nav</b> tool; it builds itself from your page tree, so adding a page adds a button, and it
updates everywhere at once. Put the nav bar on a master page and every page inherits the same menu.</p>
{figure(IM['sample'], 'A home page with a logo and a simple menu across the top.')}"""),
      ("Buttons and links", """
<p>Any object can be a <b>link</b>: select it, and point it at another page in your site, a web
address, an email or a file to download. A <b>button</b> is a ready-styled link — the “Get a free
quote” button on the sample home page — that you can colour to match your design.</p>"""),
      ("Pictures that enlarge, galleries and slideshows", """
<p>A <b>gallery</b> cycles through a set of photos as a slideshow, and a <b>lightbox</b> picture opens
full-size when a visitor clicks it — ideal for a portfolio. Both are objects you drop on the page and
fill with images.</p>"""),
      ("Forms, search and embedded media", """
<p>A <b>contact form</b> lets visitors send you a message; a <b>search</b> box helps them find a page;
and you can embed a <b>YouTube</b> or <b>Vimeo</b> video, a <b>map</b> or an <b>audio</b> clip straight
into the layout. A <b>news feed</b> keeps a running list of updates.</p>"""),
      ("Tables", """
<p>Websites use tables too. <b>Insert ▸ Table</b> drops a grid you type straight into — a price list
or an opening-hours panel — with its own header row and adjustable columns.</p>""")]))

    C.append(("Pictures",
      "<p class='lede'>Pictures bring a page to life. WEBcreator keeps them in frames you can crop "
      "and style, and hands off to PAINTcanvas when a photo needs real editing.</p>", [
      ("Picture frames", """
<p>Choose the <b>Picture</b> tool and drag a box to create a <b>picture frame</b>. A new frame shows
a placeholder until you give it an image; double-click it to choose a photo. Keeping pictures in
frames means you can design the layout first and drop the photographs in later.</p>"""),
      ("Fitting, cropping and borders", """
<p>A picture <b>fits</b> its frame — filling it or sitting inside it — and you can <b>crop</b> to show
just the part you want. Round the frame’s corners or give it an outline from the Line panel to finish
it off.</p>"""),
      ("Editing a photo", """
<p>Need to brighten, retouch or cut out a photo? <b>Edit in PAINTcanvas</b> sends the picture across
to the image editor; when you save there, the edited version comes straight back into your page.</p>""")]))

    C.append(("Shapes, Lines and QuickShapes",
      "<p class='lede'>Shapes and lines structure a page and add visual interest — a coloured band "
      "for a masthead, a rule between stories, a star on a special offer. WEBcreator’s QuickShapes "
      "give you twenty ready outlines, each with a fill, an outline and optional effects.</p>", [
      ("Drawing shapes and lines", f"""
<p>The shape tools draw rectangles (with optional rounded corners), ellipses and straight lines. Hold
a modifier while dragging to constrain a square or circle. A thin filled rectangle makes a neat rule.</p>
{figure(IM['shapes'], 'Basic shapes, a line, and a row of QuickShapes.')}"""),
      ("QuickShapes", """
<p><b>QuickShapes</b> are ready-made outlines — triangles, diamonds, polygons, stars, arrows, a
chevron, a cross, a heart, a lightning bolt, a speech bubble and a cloud. Pick one and drag it out,
then resize and recolour it like any other shape.</p>"""),
      ("Fills, outlines, dashes and arrowheads", """
<p>Every shape has a <b>fill</b> and an <b>outline</b>; lines can be <b>dashed</b> and finished with
<b>arrowheads</b>. Set them in the Colour and Line panels — a dashed line with an arrowhead makes a
simple callout.</p>"""),
      ("Drop shadow and glow", f"""
<p>Filter effects lift an object off the page. A <b>drop shadow</b> adds depth; an <b>outer glow</b>
draws the eye to a highlight or a price. Both are adjustable — colour, blur, offset and strength.</p>
{figure(crop(IM['shapes'], (258, 540, 700, 700)), 'The same rectangle with a drop shadow (left) and an outer glow (right).')}""")]))

    C.append(("Colour, Fills and Transparency",
      "<p class='lede'>Colour ties a publication together. WEBcreator offers solid colours, "
      "swatches you keep to hand, gradient fills and adjustable transparency.</p>", [
      ("Applying colour", f"""
<p>The <b>Colour</b> picker sets a solid fill or outline for the selected object — choose a colour
with the sliders or type a hex value. The <b>Fill</b>, <b>Line</b> and <b>Text</b> tabs at the top of
the picker say which part of the object you are colouring.</p>
{figure(colour, 'The Colour picker, with Fill / Line / Text tabs and RGB controls.')}"""),
      ("Swatches", """
<p>The <b>Swatches</b> tab keeps a palette of colours one click away, so a document stays consistent.
Save a colour you use often and reuse it across every object.</p>"""),
      ("Gradients and transparency", """
<p>Beyond flat colour, a <b>gradient</b> fades one colour into another across a shape, and
<b>transparency</b> lets what is behind show through — for a tint over a photo or a soft watermark.
Both are set from the panels of the same name.</p>""")]))

    C.append(("Search Engines and SEO",
      "<p class='lede'>A website is only useful if people can find it. WEBcreator builds search-engine "
      "basics into every page so your site reads well to Google and to visitors alike.</p>", [
      ("Page titles and descriptions", """
<p>Each page carries a <b>title</b> and a short <b>description</b> — the words a search engine shows in
its results. Set them from <b>This Page’s SEO…</b>, and site-wide defaults from <b>Site-wide SEO…</b>.</p>"""),
      ("Auto-generated SEO", """
<p>In a hurry? <b>Auto-generate SEO for all pages…</b> reads each page’s own headings and text and
fills in sensible titles and descriptions for the whole site at once — a good starting point you can
then refine.</p>""")]))

    C.append(("Preview and Publish",
      "<p class='lede'>When the site is ready, WEBcreator shows you exactly what a visitor will see, "
      "then writes plain HTML you can put online anywhere.</p>", [
      ("Preview in your browser", """
<p>Before publishing, <b>Preview</b> opens your site in a real web browser, so you see it exactly as a
visitor will — links, nav bar, galleries and all. Run a final <b>Check Spelling…</b> (F7) too.</p>"""),
      ("View the HTML", """
<p>Curious what the program writes? <b>View HTML</b> shows the code for the current page. You never
have to touch it — WEBcreator writes clean, standards-based HTML and CSS for you.</p>"""),
      ("Publish your site", f"""
<p><b>Publish</b> writes your whole site — every page, picture and stylesheet — as ordinary HTML files
into a folder on your disk. Upload that folder to any web host, or open it straight from disk. There is
no account, no lock-in and no monthly fee: the files are yours.</p>
{figure(IM['sample'], 'The finished home page — previewed in a browser, then published as plain HTML.')}""")]))

    C.append(("Keyboard Shortcuts and Reference", "<p class='lede'>A quick reference to the "
      "shortcuts and menus you will reach for most.</p>", [
      ("Common shortcuts", """
<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>New / Open / Save</td><td>Ctrl+N · Ctrl+O · Ctrl+S</td></tr>
<tr><td>Undo / Redo</td><td>Ctrl+Z · Ctrl+Shift+Z</td></tr>
<tr><td>Cut / Copy / Paste</td><td>Ctrl+X · Ctrl+C · Ctrl+V</td></tr>
<tr><td>Select all / Deselect</td><td>Ctrl+A · Esc</td></tr>
<tr><td>Check spelling</td><td>F7</td></tr>
<tr><td>Preview site</td><td>in your browser</td></tr>
<tr><td>Zoom in / out</td><td>Ctrl++ · Ctrl+−</td></tr>
</table>"""),
      ("The menus at a glance", """
<ul>
<li><b>File</b> — new, open, save, preview, publish HTML, SEO, import a site;</li>
<li><b>Edit</b> — undo/redo, cut/copy/paste, select;</li>
<li><b>Insert</b> — text, picture, table, calendar, shapes;</li>
<li><b>Format</b> — font and paragraph settings, drop cap, lists, spell check;</li>
<li><b>Arrange</b> — align, order, group, lock, move repeated objects to master;</li>
<li><b>View</b> — zoom, fit, rulers, guides, grid, snapping;</li>
<li><b>Help</b> — this User Guide, the Quick Start, and About.</li>
</ul>""")]))
    return C


def build_manual(IM):
    C = manual_chapters(IM)
    # table of contents
    toc = []
    for ci, (title, _intro, secs) in enumerate(C, 1):
        subs = "".join(f'<li><a href="#c{ci}s{si}">{H.escape(h)}</a></li>'
                       for si, (h, _b) in enumerate(secs, 1))
        toc.append(f'<li class="ch"><span class="n">{ci}</span>'
                   f'<a href="#c{ci}">{H.escape(title)}</a><ul>{subs}</ul></li>')
    # body
    body = []
    for ci, (title, intro, secs) in enumerate(C, 1):
        body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Chapter {ci}</span>'
                    f'<h2 id="c{ci}">{H.escape(title)}</h2></div>\n{intro}')
        for si, (h, b) in enumerate(secs, 1):
            body.append(f'<h3 id="c{ci}s{si}">{H.escape(h)}</h3>\n{b}')
        body.append("</section>")
    doc = f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… WEBcreator — User Guide</title>
<style>{CSS}{MANUAL_CSS}</style>
<div class="page">
<header class="mast"><h1>WEBcreator</h1><p>User Guide — the complete reference for laying out,
checking and publishing a document.</p></header>
<nav class="contents"><h2 style="border:0">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer>just a… WEBcreator User Guide · generated {date.today().isoformat()} ·
every picture is produced by the app itself · in the spirit of Serif WebPlus.</footer>
</div>
</html>
"""
    (OUT / "manual.html").write_text(doc, encoding="utf-8")
    print("wrote manual.html:", len(doc) // 1024, "KiB,", len(C), "chapters")


MANUAL_CSS = """
.contents{margin:1.5em 0 2em} .booktoc{list-style:none;padding:0;margin:0}
.booktoc .ch{margin:.6em 0;font-weight:600} .booktoc .ch>a{color:var(--ink);text-decoration:none}
.booktoc .n{color:var(--accent);margin-right:.5em} .booktoc ul{list-style:none;padding:0 0 0 1.6em;margin:.2em 0;font-weight:400;columns:2;gap:24px}
.booktoc ul li{margin:.1em 0} .booktoc a:hover{color:var(--accent)}
.chapter{margin-top:2.6em} .chrule{border-top:4px solid var(--accent);margin-bottom:.4em}
.chrule .cn{display:block;color:var(--accent);font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;margin-top:.4em}
.chrule h2{border:0;margin:.05em 0 .3em;padding:0;font-size:1.9rem}
h3{font-size:1.18rem;margin:1.6em 0 .4em;color:#17323a}
table.ref{border-collapse:collapse;width:100%;max-width:66ch;margin:1em 0}
table.ref th,table.ref td{border:1px solid var(--line);padding:7px 10px;text-align:left;font-size:.95rem}
table.ref th{background:var(--band)}
@media print{ .chapter{break-before:page} .contents{break-after:page} }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(_REAL_ARGS)
    if Image is None:
        sys.exit("Pillow required")
    IM = capture()
    build_quickstart(IM)
    if not args.quick:
        build_manual(IM)
    try:
        _TMP.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
