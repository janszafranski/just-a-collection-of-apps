#!/usr/bin/env python3
"""Build docs/ — the site at janszafranski.github.io/just-a-collection-of-apps.

Everything on the site is generated from the apps themselves. The template
pictures are not screenshots and not anybody else's artwork: each one is the
home page *just a... WEBcreator* actually builds when you pick that template,
rendered by the app's own painting code through PySide6.

    python3 tools/build-site.py            # docs/
    python3 tools/build-site.py --fast     # skip the 92 renders

Needs pyside6. Runs headless.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "webcreator" / "webcreator.py"
DOCS = ROOT / "docs"
SITE = "just a... CREATORsuite"
BASE = "https://janszafranski.github.io/just-a-collection-of-apps/"  # trailing slash
AUTHOR = "Jan Szafranski"
REPO = "https://github.com/janszafranski/just-a-collection-of-apps"
OG_DEFAULT = "assets/shot-hub.png"

# One-line, plain-text SEO descriptions (≈155 chars) keyed by page slug.
DESC = {
    "index.html": "A small family of simple, familiar creative apps for Linux — website designer, "
        "print & PDF, photo editor and vector drawing. Ground-up recreations you already know how "
        "to use. No subscription, no cloud.",
    "creatorsuite.html": "CREATORsuite: the launcher and file hub for the just a… creative apps on "
        "Linux — your apps on one side, everything you have made on the other.",
    "webcreator.html": "Design a website by laying pages out and publish plain HTML, on Linux — a "
        "ground-up recreation in the spirit of WebPlus, starting from 92 templates. Saves .webc.",
    "pagedesigner.html": "Lay out print documents and newsletters page by page and export a vector "
        "PDF, on Linux — text that flows between columns, master pages and guides. Saves .pagc.",
    "paintcanvas.html": "A layer-based photo and image editor for Linux — paint, retouch, "
        "adjustments and filters, in the spirit of PhotoPlus. Saves PNG and JPEG.",
    "drawmaster.html": "A vector drawing editor for Linux — shapes, freehand, a QuickShapes gallery "
        "and effects — saved as editable, scalable SVG.",
}
# schema.org applicationCategory per slug.
CATEGORY = {
    "creatorsuite.html": "UtilitiesApplication", "webcreator.html": "DesignApplication",
    "pagedesigner.html": "DesignApplication", "paintcanvas.html": "DesignApplication",
    "drawmaster.html": "DesignApplication",
}

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def load_app():
    spec = importlib.util.spec_from_file_location("webcreator", APP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["webcreator"] = mod
    spec.loader.exec_module(mod)
    return mod


CSS = """
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #1b1d1f; --mute: #5c6368;
  --line: #e2e5e8; --card: #f7f8f9; --accent: #1d6f63;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #15181a; --fg: #e8eaec; --mute: #9aa3a9;
          --line: #2a2f33; --card: #1c2023; --accent: #6fc3b4; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6
       system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px 72px; }
header.top { border-bottom: 1px solid var(--line); margin-bottom: 40px; }
header.top .wrap { padding-top: 28px; padding-bottom: 28px; }
h1 { font-size: 2.1rem; margin: 0 0 .2em; letter-spacing: -.01em; }
h2 { font-size: 1.4rem; margin: 2.4em 0 .6em; }
h3 { font-size: 1.05rem; margin: 0 0 .3em; }
a { color: var(--accent); }
p { max-width: 70ch; }
.lede { font-size: 1.12rem; color: var(--fg); }
.mute { color: var(--mute); }
.small { font-size: .88rem; }
nav.crumbs { font-size: .9rem; margin-bottom: 1rem; }
img.shot { width: 100%; border: 1px solid var(--line); border-radius: 8px;
           display: block; margin: 1.5rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { text-align: left; padding: .55rem .7rem; border-bottom: 1px solid var(--line);
         vertical-align: top; }
th { font-size: .82rem; text-transform: uppercase; letter-spacing: .05em; color: var(--mute); }
pre { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
      padding: 14px 16px; overflow-x: auto; font-size: .9rem; }
code { font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; font-size: .92em; }
.apps { display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.app { border: 1px solid var(--line); border-radius: 10px; padding: 20px; background: var(--card); }
.filter { position: sticky; top: 0; background: var(--bg); padding: 14px 0 12px;
          border-bottom: 1px solid var(--line); z-index: 2; margin-bottom: 18px; }
.filter input { width: 100%; max-width: 420px; padding: 9px 12px; font: inherit;
                border: 1px solid var(--line); border-radius: 7px;
                background: var(--card); color: var(--fg); }
.grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
.tile { border: 1px solid var(--line); border-radius: 9px; overflow: hidden;
        background: var(--card); display: flex; flex-direction: column; }
.tile img { width: 100%; display: block; border-bottom: 1px solid var(--line);
            background: #fff; }
.tile .body { padding: 11px 13px 13px; }
.tile .name { font-weight: 600; }
.tile .meta { color: var(--mute); font-size: .83rem; margin-top: .15em; }
.tile details { margin-top: .5em; font-size: .85rem; }
.tile summary { cursor: pointer; color: var(--accent); }
.tile ol { margin: .5em 0 0; padding-left: 1.3em; color: var(--mute); }
.swatches { display: flex; gap: 3px; margin-top: .55em; }
.swatches i { width: 14px; height: 14px; border-radius: 3px; display: block;
              border: 1px solid rgba(128,128,128,.35); }
footer { border-top: 1px solid var(--line); margin-top: 56px; padding-top: 20px;
         color: var(--mute); font-size: .88rem; }
.none { color: var(--mute); padding: 2rem 0; display: none; }
"""

FILTER_JS = """
(function () {
  var box = document.getElementById('q'), none = document.getElementById('none');
  if (!box) return;
  var tiles = [].slice.call(document.querySelectorAll('.tile'));
  var heads = [].slice.call(document.querySelectorAll('[data-section]'));
  function run() {
    var q = box.value.trim().toLowerCase(), hits = 0;
    tiles.forEach(function (t) {
      var on = !q || t.dataset.find.indexOf(q) !== -1;
      t.style.display = on ? '' : 'none';
      if (on) hits++;
    });
    heads.forEach(function (h) {
      var live = [].slice.call(document.querySelectorAll(
        '.tile[data-section="' + h.dataset.section + '"]'))
        .some(function (t) { return t.style.display !== 'none'; });
      h.style.display = live ? '' : 'none';
      var g = document.getElementById('g-' + h.dataset.section);
      if (g) g.style.display = live ? '' : 'none';
    });
    none.style.display = hits ? 'none' : 'block';
  }
  box.addEventListener('input', run);
  run();
})();
"""


def _head(title, desc, slug, og_image, jsonld=""):
    """The full <head>: unique title/description, canonical, Open Graph, Twitter,
    favicon and optional JSON-LD structured data."""
    canonical = BASE + ("" if slug == "index.html" else slug)
    og_abs = BASE + (og_image or OG_DEFAULT)
    e = html.escape
    tags = [
        f'<title>{e(title)}</title>',
        f'<meta name="description" content="{e(desc)}">',
        '<meta name="robots" content="index, follow">',
        f'<meta name="author" content="{e(AUTHOR)}">',
        f'<link rel="canonical" href="{e(canonical)}">',
        '<meta name="theme-color" content="#1d6f63">',
        '<link rel="icon" href="assets/icon.png" sizes="any">',
        '<link rel="apple-touch-icon" href="assets/icon.png">',
        '<link rel="stylesheet" href="style.css">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{e(SITE)}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(canonical)}">',
        f'<meta property="og:image" content="{e(og_abs)}">',
        '<meta property="og:locale" content="en_GB">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(desc)}">',
        f'<meta name="twitter:image" content="{e(og_abs)}">',
    ]
    if jsonld:
        tags.append(f'<script type="application/ld+json">{jsonld}</script>')
    return "\n".join(tags)


def jsonld_app(name, slug, desc, og_image):
    data = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": name, "description": desc,
        "applicationCategory": CATEGORY.get(slug, "DesignApplication"),
        "operatingSystem": "Linux", "url": BASE + slug,
        "screenshot": BASE + (og_image or OG_DEFAULT),
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Person", "name": AUTHOR},
        "isAccessibleForFree": True,
    }
    return json.dumps(data, ensure_ascii=False)


def jsonld_site():
    return json.dumps({
        "@context": "https://schema.org", "@type": "WebSite",
        "name": SITE, "url": BASE, "description": DESC["index.html"],
        "author": {"@type": "Person", "name": AUTHOR},
    }, ensure_ascii=False)


def page(title, body, crumbs="", *, desc=None, slug="index.html",
         og_image=None, jsonld=""):
    if desc is None:
        desc = DESC.get(slug, DESC["index.html"])
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{_head(title, desc, slug, og_image, jsonld)}
<header class="top"><div class="wrap">
<h1><a href="index.html" style="color:inherit;text-decoration:none">{html.escape(SITE)}</a></h1>
<p class="mute" style="margin:0">Simple applications for Linux, each one a ground-up recreation.</p>
</div></header>
<div class="wrap">
{crumbs}
{body}
<footer>Built from the source in
<a href="{REPO}">janszafranski/just-a-collection-of-apps</a>
on {date.today().isoformat()}. Every template picture on this site is rendered
by the app itself.</footer>
</div>
</html>
"""


# Jan's own wording, as he left it in README.md. Kept verbatim on purpose: the
# git page and the front page are meant to say the same thing, and the README is
# the one he edits. If you change it there, change it here.
# (Four typos fixed on 12 Nov 2026 at his request, in both places at once.)
INTRO = """
<p class="lede">Simple applications for people who want to work using old
familiar workflows but don't want to learn a new workflow from a more powerful, but
complex app like the <strong>ARTcraft</strong> ones. Use familiar menus,
toolbars, a page in front of you: open it and get on with the job. No
subscription, no account, no cloud, no tutorial, just save ordinary files to
ordinary folders on your own disk.</p>

<p>Each one is a <strong>ground-up recreation</strong> of an easy-to-use app,
written for Linux. Not a port, nor wrapper, nor fork: new code that borrows the
shape of a retired old app, rather than the thing itself. If you already know
how to do something in one of these popular British apps, you should be able to
do it here without learning anything new &mdash; the same menus in the same
places, the same words for the same jobs, the same order of operations.</p>

<p>The excellent ARTcraft suites do a great deal, and are perfect for familiar
users but for those of us used to apps that are no longer with us, this isn't a
replacement for tools like those of ARTcraft... they are a re-creation of
British alternatives many of us used and brings them back and makes them
quick.</p>

<p class="mute">These are not a replacement for the big suites and not trying to
be. If you need what ARTcraft can do, use ARTcraft.</p>
"""


# Each app: its page, banner, one-line tag, blurb, feature bullets, deps, and an
# optional real screenshot. The site is a card per app plus a page per app.
APPS_META = [
    dict(key="webcreator", slug="webcreator.html", title="WEBcreator",
         banner="banner-webcreator.png", tag="Website designer", ext=".webc",
         blurb="Design a website by laying pages out — drag text, pictures, buttons and "
               "menus where you want them, share the header on a master page, preview in your "
               "browser, and publish plain HTML you can upload anywhere.",
         feats=["Lay pages out freely; master pages for shared headers and menus",
                "Text, pictures, shapes, nav bars, galleries, forms, tables, a news feed",
                "QuickShapes, drop shadow & glow, dashed lines & arrowheads",
                "Drop cap, spell check, convert text to a table",
                "Edit any picture in PAINTcanvas and it updates on save",
                "Publishes plain HTML/CSS; opens Serif WebPlus .wpp sites"],
         deps="sudo pacman -S --needed pyside6 python-beautifulsoup4 qt6-webengine"),
    dict(key="pagecreator", slug="pagedesigner.html", title="PAGEdesigner",
         banner="banner-pagecreator.png", tag="Print documents & PDF", ext=".pagc",
         blurb="Design print documents page by page — text frames that flow between columns, "
               "master pages, guides and page numbers — then export a vector PDF.",
         feats=["Linked text frames (newspaper-style text flow), booklet view",
                "Master pages, guides, columns, page numbers",
                "QuickShapes, effects, drop cap, spell check, tables",
                "Calendar wizard and CSV mail merge",
                "Edit pictures in PAINTcanvas; opens Serif PagePlus files",
                "Vector PDF export with bleed & crop marks"],
         based="PagePlus",
         grid=dict(dir="page", heading="Start from the right size",
                   note="Every paper size the Startup Assistant offers — A-sizes, business stationery, "
                        "booklets and large-format posters. Each thumbnail is drawn to the sheet's real "
                        "proportions. Pick one and start laying out.",
                   ph="Filter sizes by name or category…"),
         gallery=[("shot-page.png", "Lay out pages with rulers and guides, the tool palette down the "
                   "left, and the Pages, Layers and Transform panels to the right of the canvas."),
                  ("shot-page-start.png", "Start from a paper size — A-sizes, business cards, booklets "
                   "or posters — or set your own, then open a blank page ready to lay out.")],
         deps="sudo pacman -S --needed pyside6 python-beautifulsoup4"),
    dict(key="paint", slug="paintcanvas.html", title="PAINTcanvas",
         banner="banner-paint.png", tag="Photo & image editor", ext=".png / .jpg",
         shot="shot-paint.png",
         blurb="A layer-based image editor — paint and draw, retouch photos, and apply "
               "adjustments and filters — in the spirit of PhotoPlus.",
         feats=["Layers with blend modes, opacity and visibility",
                "Adjust: brightness/contrast, levels, hue/saturation, colour balance, "
                "temperature, threshold, posterize, greyscale, sepia, invert",
                "Filters: Gaussian blur, unsharp mask, median, sharpen, emboss, find edges",
                "Rectangular & elliptical selections; crop, resize, straighten, rotate, flip",
                "Retouch: clone, red-eye, dodge, burn, and a gradient tool",
                "Drop shadow & outer glow on a transparent canvas"],
         based="PhotoPlus",
         grid=dict(dir="paint", heading="Adjustments & filters, on one photo",
                   note="The same picture through every adjustment and filter in the app. None of these "
                        "is a stock example — each one is produced by PAINTcanvas's own image code.",
                   ph="Filter effects by name…"),
         gallery=[("shot-paint.png", "Paint and retouch with layers, blend modes and the Adjust and "
                   "Filter menus — the familiar darkroom, on Linux.")],
         deps="sudo pacman -S --needed pyside6 python-pillow python-numpy"),
    dict(key="draw", slug="drawmaster.html", title="DRAWmaster",
         banner="banner-draw.png", tag="Vector drawing", ext=".svg",
         blurb="A vector editor — shapes, lines, freehand and polylines, a QuickShapes gallery "
               "and drop-shadow/glow effects — saved as scalable SVG it can re-open and keep editing.",
         feats=["Rectangles, ellipses, lines, pen (polyline) and freehand paths",
                "A gallery of 20 QuickShapes; drop shadow & outer glow",
                "Re-opens its own SVGs losslessly (the drawing is stored in the file)",
                "Export PNG, or send the drawing to PAINTcanvas for raster work",
                "Infinitely scalable SVG output"],
         based="DrawPlus",
         grid=dict(dir="draw", heading="The QuickShapes",
                   note="Twenty ready-made shapes, each one drawn by the app itself. Drag a shape onto "
                        "the page, then resize, recolour and add effects.",
                   ph="Filter shapes by name…"),
         gallery=[("shot-draw.png", "QuickShapes with fills and outlines, a hand-drawn line, and "
                   "drop-shadow and glow effects — all on one canvas."),
                  ("shot-quickshapes.png", "The QuickShapes gallery: twenty ready-made shapes to drag "
                   "straight onto the page.")],
         deps="sudo pacman -S --needed pyside6"),
]

HUB_META = dict(key="collectionofapps", slug="creatorsuite.html", title="CREATORsuite",
    banner="banner-collectionofapps.png", tag="The launcher & file hub", ext="",
    shot="shot-hub.png",
    blurb="The home for the whole family: a two-pane hub with your apps on the left and "
          "everything you have made on the right — a Recent list and a browser of your "
          "“just a…” folders, so you can jump straight back into a project.",
    feats=["Launch any app, or filter the file list to one app",
           "Recent files across every app, newest first",
           "Import older files you saved before the shared folders existed",
           "Updates each app from GitHub, and installs ones you don't have yet",
           "One place for everything you make"],
    gallery=[("shot-hub.png", "Your apps down one side, everything you have made down the other — "
              "a Recent list and a browser of your “just a…” folders.")],
    deps="sudo pacman -S --needed pyside6")


def _install_block(meta):
    return f"""<h2>Install {html.escape(meta['title'])}</h2>
<p class="small mute">Install the dependencies for your distribution, then clone and run the
installer. Nothing needs root except the dependency line.</p>
<p class="small mute">Arch / CachyOS / Manjaro:</p>
<pre><code>{html.escape(meta['deps'])}</code></pre>
<p class="small mute">Then, on any distribution:</p>
<pre><code>git clone https://github.com/janszafranski/just-a-collection-of-apps.git
just-a-collection-of-apps/apps/{meta['key']}/install.sh</code></pre>
<p class="small mute">Only PySide6 is strictly required &mdash; use your distribution's package,
not pip, so the app follows your desktop theme. The installer checks the rest and tells you
what, if anything, is missing. There is an <code>uninstall.sh</code> beside it.</p>"""


def build_index(counts):
    cards = []
    for m in APPS_META:
        feats = "".join(f"<li>{html.escape(f)}</li>" for f in m["feats"][:3])
        cards.append(f"""<div class="app">
  <a href="{m['slug']}"><img src="assets/{m['banner']}" alt="just a… {html.escape(m['title'])}"
     style="width:100%;border-radius:8px;display:block;margin-bottom:12px"></a>
  <h3><a href="{m['slug']}">just a&hellip; {html.escape(m['title'])}</a></h3>
  <p class="mute small" style="margin:.1em 0 .5em">{html.escape(m['tag'])}{' &middot; saves <code>'+html.escape(m['ext'])+'</code>' if m['ext'] else ''}</p>
  <p class="small">{html.escape(m['blurb'])}</p>
  <ul class="small mute" style="margin:.3em 0 .6em;padding-left:1.2em">{feats}</ul>
  <p class="small"><a href="{m['slug']}">Features &amp; install &rsaquo;</a></p>
</div>""")
    hub = HUB_META
    callout = """
<p class="lede" style="border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:10px;background:var(--card);padding:16px 18px;margin:1.6em 0">
Want the quick tour? <a href="welcome.html"><b>See the whole family &mdash; creative apps and
desktop tools &mdash; on one page &rsaquo;</b></a>
</p>"""
    body = INTRO + callout + f"""
<h2>The apps</h2>
<div class="apps">
{''.join(cards)}
</div>

<h2 style="margin-top:2em">just a&hellip; {html.escape(hub['title'])} &mdash; the launcher</h2>
<p>{html.escape(hub['blurb'])}</p>
<a href="{hub['slug']}"><img class="shot" src="assets/{hub['shot']}" alt="The CREATORsuite hub"></a>
<p class="small"><a href="{hub['slug']}">About the launcher &amp; how to install it &rsaquo;</a></p>

<h2>Install</h2>
<p>Each app installs and updates on its own. Clone once, then run whichever installers you
want &mdash; nothing needs root beyond the dependency line.</p>
<pre><code>git clone https://github.com/janszafranski/just-a-collection-of-apps.git
cd just-a-collection-of-apps
apps/collectionofapps/install.sh   # the launcher / hub
apps/webcreator/install.sh
apps/pagecreator/install.sh
apps/paint/install.sh
apps/draw/install.sh</code></pre>
<p class="mute small">Each app checks the repository for a newer version of itself (and the
launcher shows an Update button), and each has an <code>uninstall.sh</code> beside its installer.</p>
"""
    (DOCS / "index.html").write_text(
        page(f"{SITE} — familiar creative apps for Linux", body,
             slug="index.html", og_image=OG_DEFAULT, jsonld=jsonld_site()),
        encoding="utf-8")


def _og_for(m):
    if m.get("gallery"):
        return f"assets/{m['gallery'][0][0]}"
    return f"assets/{m['shot']}" if m.get("shot") else f"assets/{m['banner']}"


GRID_JS = """
(function(){
  var q=document.getElementById('gq'), grid=document.getElementById('ggrid'),
      none=document.getElementById('gnone'), tiles=[].slice.call(grid.children);
  function run(){var v=q.value.trim().toLowerCase(), n=0;
    tiles.forEach(function(t){var m=t.getAttribute('data-text').indexOf(v)>=0;
      t.style.display=m?'':'none'; if(m)n++;});
    none.style.display=n?'none':'block';}
  q.addEventListener('input', run); run();
})();
"""


def _grid_section(m):
    g = m.get("grid")
    if not g:
        return ""
    manifest = DOCS / "assets" / g["dir"] / "manifest.json"
    if not manifest.exists():
        return ""
    import json as _json
    items = _json.loads(manifest.read_text())
    e = html.escape
    tiles = "".join(
        f'<div class="tile" data-text="{e(it["tags"].lower())}">'
        f'<img src="assets/{it["file"]}" alt="{e(it["label"])}" loading="lazy">'
        f'<div class="body"><div class="name">{e(it["label"])}</div>'
        f'<div class="meta">{e(it["meta"])}</div></div></div>'
        for it in items)
    return f"""<h2>{e(g['heading'])} <span class="mute" style="font-weight:400">&middot; {len(items)}</span></h2>
<p class="small mute">{e(g['note'])}</p>
<div class="filter"><input id="gq" type="search" placeholder="{e(g['ph'])}" autocomplete="off"></div>
<p class="none" id="gnone">Nothing matches that.</p>
<div class="grid" id="ggrid">{tiles}</div>
<script>{GRID_JS}</script>
"""


def _app_body(m):
    e = html.escape
    based = (f'<p class="mute" style="margin:-.3em 0 1em">A ground-up recreation in the spirit of '
             f'Serif&rsquo;s <b>{e(m["based"])}</b> &mdash; the same menus, in the same places.</p>'
             if m.get("based") else "")
    gallery = ""
    for img, cap in m.get("gallery", []):
        gallery += (f'<figure style="margin:0 0 1.8em"><img class="shot" style="margin-bottom:.5em" '
                    f'src="assets/{img}" alt="{e(cap)}">'
                    f'<figcaption class="mute small">{e(cap)}</figcaption></figure>\n')
    feats = "".join(f"<li>{e(f)}</li>" for f in m["feats"])
    tour = f"<h2>A closer look</h2>\n{gallery}" if gallery else ""
    return f"""<nav class="crumbs mute"><a href="index.html">{e(SITE)}</a> &rsaquo; just a&hellip; {e(m['title'])}</nav>
<h2 style="margin-top:0">just a&hellip; {e(m['title'])}</h2>
<img class="shot" src="assets/{m['banner']}" alt="just a… {e(m['title'])}">
{based}
<p class="lede">{e(m['blurb'])}</p>
{tour}
{_grid_section(m)}
<h2>What it does</h2>
<ul>{feats}</ul>
{_install_block(m)}
<p class="small mute"><a href="index.html">&lsaquo; Back to all the apps</a></p>
"""


def build_app_pages(counts):
    for m in APPS_META + [HUB_META]:
        if m["key"] == "webcreator":
            continue   # WEBcreator's own rich page (templates gallery) is built separately
        name = f"just a... {m['title']}"
        og = _og_for(m)
        desc = DESC.get(m["slug"], m["blurb"])
        (DOCS / m["slug"]).write_text(
            page(name, _app_body(m), slug=m["slug"], og_image=og, desc=desc,
                 jsonld=jsonld_app(name, m["slug"], desc, og)),
            encoding="utf-8")


SECTIONS = (
    ("ours", "Basic Templates", "Three originals that ship with the app &mdash; "
     "a small business, a community group and a portfolio."),
    ("theme-desktop", "Theme Layouts &mdash; Desktop", "Thirty-two starting points: "
     "a full page tree, three colour schemes of their own, and room to work."),
    ("theme-mobile", "Theme Layouts &mdash; Mobile", "The same thirty-two as "
     "narrow, single-column sites."),
    ("pro-desktop", "Pro Templates &mdash; Desktop", "Seven complete sites rather "
     "than starting points &mdash; longer page trees, deeper structure."),
    ("pro-mobile", "Pro Templates &mdash; Mobile", "The same seven, narrow."),
    ("samples", "Sample Sites", "Eleven more page trees from the same catalogue. "
     "They were sample documents rather than things to start a site from, and "
     "they are here because a page tree is a page tree."),
)

SECTION_OF = {
    ("Theme Layouts", "Desktop Websites"): "theme-desktop",
    ("Theme Layouts", "Mobile Websites"): "theme-mobile",
    ("WebPlus X8 Pro Templates", "Desktop Websites"): "pro-desktop",
    ("WebPlus X8 Pro Templates", "Mobile Websites"): "pro-mobile",
}


def render_previews(wc, fast):
    """One JPEG per template: the home page the app actually builds."""
    out = DOCS / "previews"
    out.mkdir(parents=True, exist_ok=True)
    tiles = []

    def shot(site, key):
        name = f"{key}.jpg"
        if not fast:
            img = wc.render_page_image(site, site['pages'][0], 460,
                                       crop=int(site['width'] * 1.5))
            img.save(str(out / name), "JPG", 84)
        return name

    for i, (nm, kind, fn) in enumerate(wc.TEMPLATES):
        site = fn()
        key = "ours-" + nm.lower()
        tiles.append(dict(section="ours", name=nm, sub=kind, key=key,
                          picture=shot(site, key), scheme="", colours=site['palette'],
                          pages=[p['title'] for p in site['pages']]))

    for row in wc.serif_catalogue().get("templates", []):
        section = SECTION_OF.get((row["category"], row["surface"]), "samples")
        site = wc.serif_site(row)
        scheme = site["serif"]["scheme"]
        cols = wc.serif_catalogue()["schemes"].get(scheme, [])
        tiles.append(dict(
            section=section, name=row["name"],
            sub=f"{len(row['pages'])} pages · {row['surface'] or row['category']}",
            key=row["key"], picture=shot(site, row["key"]), scheme=scheme,
            colours=list(dict.fromkeys(cols))[:8],
            pages=[p["name"] for p in wc.serif_pages(row)]))
        print(f"   {row['key']}", flush=True)
    return tiles


def build_webcreator(tiles):
    by_section = {}
    for t in tiles:
        by_section.setdefault(t["section"], []).append(t)

    chunks = []
    for key, title, blurb in SECTIONS:
        rows = by_section.get(key) or []
        if not rows:
            continue
        chunks.append(f'<h2 data-section="{key}">{title} '
                      f'<span class="mute small">({len(rows)})</span></h2>'
                      f'<p class="mute small" data-section="{key}">{blurb}</p>'
                      f'<div class="grid" id="g-{key}">')
        for t in rows:
            find = " ".join([t["name"], t["sub"], t["scheme"]] + t["pages"]).lower()
            sw = "".join(f'<i style="background:{html.escape(c)}"></i>'
                         for c in (t["colours"] or [])[:8])
            pages = "".join(f"<li>{html.escape(p)}</li>" for p in t["pages"])
            scheme = (f'<div class="meta">{html.escape(t["scheme"])}</div>'
                      if t["scheme"] else "")
            chunks.append(f"""<div class="tile" data-section="{key}" data-find="{html.escape(find)}">
<img src="previews/{html.escape(t['picture'])}" alt="{html.escape(t['name'])} home page" loading="lazy">
<div class="body"><div class="name">{html.escape(t['name'])}</div>
<div class="meta">{html.escape(t['sub'])}</div>{scheme}
<div class="swatches">{sw}</div>
<details><summary>{len(t['pages'])} pages</summary><ol>{pages}</ol></details>
</div></div>""")
        chunks.append("</div>")

    total = len(tiles)
    body = f"""<nav class="crumbs mute"><a href="index.html">{html.escape(SITE)}</a> &rsaquo; just a&hellip; WEBcreator</nav>
<h2 style="margin-top:0">just a&hellip; WEBcreator</h2>
<p class="lede">A desktop website designer for Linux. Lay pages out freely, put
the header and the menu on a master page so every page shares them, preview in
your browser, and publish plain HTML to a folder you can upload anywhere.</p>
<p>It is a <strong>ground-up recreation</strong> of the easy end of a desktop web
designer: menus where you expect them, a toolbar, a page in front of you, and a
Site tree down the side. If you have used one of the <strong>ARTcraft</strong>
apps to lay out a page, nothing here should need learning. The powerful,
complicated half &mdash; the parts most people never open &mdash; is not here on
purpose.</p>
<img class="shot" src="assets/screenshot.png" alt="just a... WEBcreator: menu bar, toolbar, tool palette, canvas and the Site tree">

<h2>What it does</h2>
<table>
<tr><th>New site</th><td>From any of {total} templates, or empty, through the Startup Assistant</td></tr>
<tr><th>Pages</th><td>Add, delete, reorder, nest &mdash; the Site tab draws the tree to whatever depth it has</td></tr>
<tr><th>Master pages</th><td>Create, edit and assign per page, so headers and menus are written once</td></tr>
<tr><th>Objects</th><td>Text, pictures, shapes, buttons, navigation bars, tables, forms, embedded HTML &mdash; drag, resize, rotate, align</td></tr>
<tr><th>Publish</th><td>Plain HTML and CSS into a folder, with your own filenames. No build step, nothing to host but files</td></tr>
<tr><th>Opens</th><td>Its own <code>.webc</code> sites, a website folder, and a Serif <strong>WebPlus</strong> <code>.wpp</code> publication &mdash; read-only on your original</td></tr>
</table>

<h2>Install</h2>
<p class="small mute">Install the dependencies for your distribution, then clone and run the
installer. Nothing here needs root &mdash; only the dependency line uses <code>sudo</code>.</p>

<h3>Arch / CachyOS / Manjaro</h3>
<pre><code>sudo pacman -S --needed pyside6 python-beautifulsoup4 qt6-webengine</code></pre>

<h3>Debian / Ubuntu / Mint / Pop!_OS</h3>
<pre><code>sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtwebenginewidgets python3-bs4</code></pre>

<details><summary>Other distributions</summary>
<p class="small mute" style="margin-top:.6em">Fedora:</p>
<pre><code>sudo dnf install python3-pyside6 python3-beautifulsoup4</code></pre>
<p class="small mute">openSUSE:</p>
<pre><code>sudo zypper install python3-PySide6 python3-beautifulsoup4</code></pre>
<p class="small mute">Any distro (last resort &mdash; see the note below about pip):</p>
<pre><code>pip install --user pyside6 beautifulsoup4</code></pre>
</details>

<p class="small mute" style="margin-top:1em">Then, on any distro:</p>
<pre><code>git clone https://github.com/janszafranski/just-a-collection-of-apps.git
just-a-collection-of-apps/apps/webcreator/install.sh</code></pre>

<p class="small mute">Only PySide6 is required. <strong>Use your distribution's package, not
pip</strong> &mdash; the pip wheel ships its own Qt, so the app will not pick up your
desktop theme (fonts, colours, dark mode). <code>beautifulsoup4</code> is for
importing a website folder, and the Qt WebEngine package makes such an import match
the original layout. The installer checks for each and tells you what, if anything,
is missing &mdash; it never needs root itself.</p>

<h2 id="templates">{total} templates</h2>
<img class="shot" src="assets/chooser.png" alt="The Startup Assistant: the template tree, a preview, the colour scheme picker and the page tick boxes">
<p>Pick one on the left, pick a colour scheme, untick any pages you don't want,
and open it. Eighty-nine of these follow the page trees of the templates
<strong>Serif WebPlus X8</strong> shipped &mdash; the page names, the filenames
each page publishes as, which page hangs off which, and the colour schemes that
template was drawn in, read off the install disc.</p>
<p><strong>The pictures below are not Serif's.</strong> No artwork, copy or code
of theirs is used or redistributed here. Every picture on this page is the home
page WEBcreator itself builds from that template, drawn by the app in its own
procedural artwork, in that template's first colour scheme. The structure is the
part that was worth recreating; the drawing is ours.</p>

<div class="filter"><input id="q" type="search" placeholder="Filter {total} templates by name, page or colour scheme&hellip;" autocomplete="off"></div>
<p class="none" id="none">Nothing matches that.</p>
{''.join(chunks)}
<script>{FILTER_JS}</script>
"""
    wc_name, wc_slug, wc_og = "just a... WEBcreator", "webcreator.html", "assets/screenshot.png"
    wc_desc = DESC[wc_slug]
    (DOCS / "webcreator.html").write_text(
        page(wc_name, body, slug=wc_slug, og_image=wc_og, desc=wc_desc,
             jsonld=jsonld_app(wc_name, wc_slug, wc_desc, wc_og)),
        encoding="utf-8")


def grab_chooser(wc):
    """A real screenshot of the Startup Assistant, taken off-screen."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidgetItemIterator
    win = wc.MainWindow()
    dlg = wc.StartupAssistant(win)
    dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
    dlg.resize(1040, 660)
    dlg.show()
    it = QTreeWidgetItemIterator(dlg.ttree)
    while it.value():
        data = it.value().data(0, Qt.UserRole)
        if data and data[0] == "serif" and data[1].endswith("stack-stone"):
            dlg.ttree.setCurrentItem(it.value())
            break
        it += 1
    dlg.show_template()
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    dlg.grab().save(str(DOCS / "assets" / "chooser.png"))
    # The app's own README shows the same picture.
    shutil.copy2(DOCS / "assets" / "chooser.png",
                 ROOT / "apps" / "webcreator" / "assets" / "chooser.png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fast", action="store_true",
                    help="rewrite the HTML without re-rendering the previews")
    args = ap.parse_args(argv)

    from PySide6.QtWidgets import QApplication
    wc = load_app()
    app = QApplication.instance() or QApplication([])

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "style.css").write_text(CSS, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "apps" / "webcreator" / "assets" / "screenshot.png",
                 DOCS / "assets" / "screenshot.png")
    # favicon: the suite's own 2×2 family icon
    favicon_src = ROOT / "apps" / "collectionofapps" / "icon-256.png"
    if favicon_src.exists():
        shutil.copy2(favicon_src, DOCS / "assets" / "icon.png")
    # each app's banner becomes its card header / page hero
    for key in ("collectionofapps", "webcreator", "pagecreator", "paint", "draw"):
        src = ROOT / "apps" / key / "banner.png"
        if src.exists():
            shutil.copy2(src, DOCS / "assets" / f"banner-{key}.png")
    grab_chooser(wc)

    tiles = render_previews(wc, args.fast)
    counts = {"total": len(tiles)}
    build_index(counts)
    build_app_pages(counts)
    build_webcreator(tiles)

    # sitemap.xml + robots.txt
    pages = sorted(p.name for p in DOCS.glob("*.html"))
    urls = "".join(
        f"  <url><loc>{BASE}{'' if p == 'index.html' else p}</loc>"
        f"<lastmod>{date.today().isoformat()}</lastmod>"
        f"<priority>{'1.0' if p == 'index.html' else '0.7'}</priority></url>\n"
        for p in pages)
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n", encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")

    print(f":: {len(tiles)} templates, {len(APPS_META)} app pages, "
          f"{len(pages)} pages + sitemap/robots -> {DOCS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
