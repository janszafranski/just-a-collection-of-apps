#!/usr/bin/env python3
# page_assets.py — a library of ready-made graphic assets for just a... PAGEdesigner:
# callouts, badges, banners, arrows and decorative pieces to drop onto a poster,
# flyer, advert or newsletter. In the spirit of PagePlus's Assets tab, but all
# original: each asset is built from the app's own shapes and text, so it stays
# fully editable (recolour it, retype the words, resize it) once on the page.
#
# An asset is a dict:  name, cat (category), w, h, and objs: a list of
# (type, x, y, w, h, props) tuples in the asset's own 0..w, 0..h space. Insert
# drops the objects onto the page (centred) as an editable group.

INK = '#243137'


def _badge(shape, fill, text, color='#ffffff', stroke='', strokeW=0, size=34, s=180):
    objs = [('shape', 0, 0, s, s, dict(shape=shape, fill=fill, stroke=stroke, strokeW=strokeW))]
    if text:
        lines = text.count('<br>') + 1
        th = size * 1.25 * lines
        objs.append(('text', s * 0.14, (s - th) / 2, s * 0.72, th,
                     dict(pad=0, size=size, bold=True, color=color, align='center', html=f'<p>{text}</p>')))
    return objs


def ASSETS():
    A = []

    # ---- Callouts ----------------------------------------------------------
    A.append(dict(name='Speech bubble', cat='Callouts', w=250, h=180, objs=[
        ('shape', 0, 0, 250, 150, dict(shape='speech', fill='#ffffff', stroke=INK, strokeW=2)),
        ('text', 18, 34, 214, 70, dict(pad=0, size=17, color=INK, align='center', html='<p>Say something!</p>')),
    ]))
    A.append(dict(name='Thought bubble', cat='Callouts', w=250, h=170, objs=[
        ('shape', 0, 0, 250, 170, dict(shape='cloud', fill='#ffffff', stroke=INK, strokeW=2)),
        ('text', 36, 56, 178, 60, dict(pad=0, size=16, color=INK, align='center', html='<p>Hmm…</p>')),
    ]))
    A.append(dict(name='Tag callout', cat='Callouts', w=260, h=90, objs=[
        ('shape', 0, 0, 260, 64, dict(shape='rect', radius=10, fill='#2a7d6b', strokeW=0)),
        ('shape', 118, 56, 24, 24, dict(shape='triangle', fill='#2a7d6b', strokeW=0, rot=180)),
        ('text', 14, 16, 232, 36, dict(pad=0, size=18, bold=True, color='#ffffff', align='center', html='<p>Read this</p>')),
    ]))

    # ---- Badges ------------------------------------------------------------
    A.append(dict(name='SALE burst', cat='Badges', w=200, h=200,
                  objs=_badge('burst', '#d84f3a', 'SALE', size=34, s=200)))
    A.append(dict(name='50% OFF burst', cat='Badges', w=200, h=200,
                  objs=_badge('burst', '#e8a33d', '50%<br>OFF', color='#20343f', size=26, s=200)))
    A.append(dict(name='NEW circle', cat='Badges', w=170, h=170, objs=[
        ('shape', 0, 0, 170, 170, dict(shape='ellipse', fill='#2a7d6b', strokeW=0)),
        ('shape', 12, 12, 146, 146, dict(shape='ellipse', fill='', stroke='#ffffff', strokeW=3)),
        ('text', 20, 60, 130, 44, dict(pad=0, size=38, bold=True, color='#ffffff', align='center', html='<p>NEW</p>')),
    ]))
    A.append(dict(name='Quality seal', cat='Badges', w=180, h=180, objs=[
        ('shape', 0, 0, 180, 180, dict(shape='seal', fill='#b8902a', strokeW=0)),
        ('shape', 18, 18, 144, 144, dict(shape='ellipse', fill='', stroke='#fff3d0', strokeW=2)),
        ('text', 26, 58, 128, 64, dict(pad=0, size=26, bold=True, color='#fff3d0', align='center', html='<p>100%</p>')),
    ]))
    A.append(dict(name='Star badge', cat='Badges', w=180, h=180,
                  objs=_badge('star5', '#f4c96b', 'WOW', color='#8a5a12', size=30, s=180)))

    # ---- Banners & ribbons -------------------------------------------------
    A.append(dict(name='Ribbon banner', cat='Banners', w=420, h=110, objs=[
        ('shape', 0, 0, 420, 90, dict(shape='ribbon', fill='#2a7d6b', strokeW=0)),
        ('text', 50, 26, 320, 40, dict(pad=0, size=26, bold=True, color='#ffffff', align='center', html='<p>HEADLINE</p>')),
    ]))
    A.append(dict(name='Pennant flag', cat='Banners', w=300, h=120, objs=[
        ('shape', 0, 0, 300, 120, dict(shape='pennant', fill='#d84f3a', strokeW=0)),
        ('text', 20, 44, 200, 36, dict(pad=0, size=24, bold=True, color='#ffffff', align='left', html='<p>Today only</p>')),
    ]))
    A.append(dict(name='Title bar', cat='Banners', w=460, h=80, objs=[
        ('shape', 0, 0, 460, 70, dict(shape='rect', fill='#20343f', strokeW=0)),
        ('shape', 0, 0, 10, 70, dict(shape='rect', fill='#e8a33d', strokeW=0)),
        ('text', 28, 18, 410, 36, dict(pad=0, size=26, bold=True, color='#ffffff', align='left', html='<p>Section title</p>')),
    ]))

    # ---- Arrows & pointers -------------------------------------------------
    A.append(dict(name='Arrow', cat='Arrows & pointers', w=220, h=120, objs=[
        ('shape', 0, 0, 220, 120, dict(shape='arrow', fill='#2a7d6b', strokeW=0))]))
    A.append(dict(name='Double arrow', cat='Arrows & pointers', w=240, h=110, objs=[
        ('shape', 0, 0, 240, 110, dict(shape='darrow', fill='#5b8def', strokeW=0))]))
    A.append(dict(name='Chevron', cat='Arrows & pointers', w=130, h=160, objs=[
        ('shape', 0, 0, 130, 160, dict(shape='chevron', fill='#e8a33d', strokeW=0))]))
    A.append(dict(name='Lightning', cat='Arrows & pointers', w=120, h=190, objs=[
        ('shape', 0, 0, 120, 190, dict(shape='lightning', fill='#f4c96b', stroke='#c8851b', strokeW=2))]))

    # ---- Decorative --------------------------------------------------------
    A.append(dict(name='Sunburst', cat='Decorative', w=220, h=220, objs=[
        ('shape', 0, 0, 220, 220, dict(shape='burst', fill='#ffe3a3', strokeW=0))]))
    A.append(dict(name='Star', cat='Decorative', w=170, h=170, objs=[
        ('shape', 0, 0, 170, 170, dict(shape='star5', fill='#f4c96b', stroke='#c8851b', strokeW=2))]))
    A.append(dict(name='Heart', cat='Decorative', w=170, h=160, objs=[
        ('shape', 0, 0, 170, 160, dict(shape='heart', fill='#e8556b', stroke='#b2374b', strokeW=2))]))
    A.append(dict(name='Divider', cat='Decorative', w=420, h=20, objs=[
        ('line', 0, 10, 420, 0, dict(stroke='#2a7d6b', strokeW=3)),
        ('shape', 196, 2, 28, 16, dict(shape='diamond', fill='#2a7d6b', strokeW=0))]))
    A.append(dict(name='Dotted rule', cat='Decorative', w=420, h=12, objs=[
        ('line', 0, 6, 420, 0, dict(stroke='#8a949b', strokeW=3, dash='dotted'))]))

    return A
