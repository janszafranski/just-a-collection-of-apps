#!/usr/bin/env python3
"""Build PAGEdesigner's illustrated docs: quickstart.html (and, in progress, the
full manual.html) from real screenshots captured by driving the app itself.

    python3 tools/build-pagemanual.py            # both docs
    python3 tools/build-pagemanual.py --quick    # just quickstart.html

Every picture is grabbed from the running app (offscreen), so the guide always
matches what the program actually looks like. Images are embedded as data URIs,
so each HTML file is self-contained and installs with no extra assets.

Modelled on Serif's PagePlus Quick Start / User Guide structure, describing
*this* app's real menus and features.
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
sys.argv = ["build-pagemanual", "--no-startup"]   # the app reads this to skip its Startup Assistant

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtCore import Qt                                      # noqa: E402

app = QApplication.instance() or QApplication([])
QDialog.exec = lambda self, *a, **k: 0
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))


def _load():
    spec = importlib.util.spec_from_file_location("pagecreator", APP)
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
    ("shape", 0, 0, None, 118, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
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


def _add_sample(w, upto=None):
    pw = w.site.get("width", 794)
    for i, (t, x, y, ww, hh, p) in enumerate(SAMPLE):
        if upto is not None and i >= upto:
            break
        if ww is None:
            ww = pw
        w.add_object(mk(t, x, y, ww, hh, **p))
    w.sel = []
    if hasattr(w, "set_tool"):
        w.set_tool("pointer")


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

    # 3) Finished newsletter in the workspace
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
    """13 short chapters, PagePlus-Quick-Start style, for THIS app. Returns a list
    of (heading, html-body)."""
    S = []
    S.append(("Welcome to PAGEdesigner", f"""
<p class="lede">PAGEdesigner is a <b>desktop publishing</b> program: you lay a page out by placing
text, pictures, shapes and tables exactly where you want them, then print it or export a PDF.
It works the way the old Serif <b>PagePlus</b> did — the same menus, in the same places.</p>
<p>This Quick Start walks you from a blank page to a finished, printable newsletter in about
thirteen short steps. For the complete reference, open <b>Help ▸ User Guide</b>.</p>
{figure(IM['sample'], 'A finished one-page newsletter, laid out entirely in PAGEdesigner.')}"""))

    S.append(("Starting a publication", f"""
<p>When PAGEdesigner opens it shows the <b>Startup Assistant</b>. Choose a paper size —
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
placeholder in the newsletter). Double-click it to drop in a photo; the picture fits the frame,
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
<title>just a… PAGEdesigner — Quick Start Guide</title>
<style>{CSS}</style>
<div class="page">
<header class="mast"><h1>PAGEdesigner — Quick Start</h1>
<p>From a blank page to a finished, printable document — in thirteen steps.</p></header>
<ol class="toc">{toc}</ol>
{''.join(body)}
<footer>just a… PAGEdesigner Quick Start · generated {date.today().isoformat()} ·
every picture is produced by the app itself. See <b>Help ▸ User Guide</b> for the full manual.</footer>
</div>
</html>
"""
    (OUT / "quickstart.html").write_text(doc, encoding="utf-8")
    print("wrote quickstart.html:", len(doc) // 1024, "KiB,", len(S), "sections")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(_REAL_ARGS)
    if Image is None:
        sys.exit("Pillow required")
    IM = capture()
    build_quickstart(IM)
    try:
        _TMP.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
