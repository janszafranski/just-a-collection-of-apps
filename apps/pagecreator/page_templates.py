#!/usr/bin/env python3
# page_templates.py — real design templates for just a... PAGEdesigner, in the
# spirit of Serif PagePlus's Theme Layouts: pre-laid-out posters, flyers, cards,
# newsletters, menus, certificates and more. Each is a list of objects with
# placeholder text and picture frames the user edits, then prints or exports.
#
# A template is a dict:  name, cat (category), w, h (page size in px @96dpi),
# and objs: a list of (type, x, y, w, h, props) tuples — the same object model
# the app uses. The Startup Assistant renders a thumbnail of each and creates a
# document from it on click.
#
# px @ 96 dpi:  A4 794x1123 · A4 landscape 1123x794 · A5 559x794 ·
#               A3 1123x1587 · business card 334x213 · square 800x800 · DL 390x824

SANS = 'Noto Sans'
SERIF = 'DejaVu Serif'


def _pic(x, y, w, h, fill='#dfe6ea', stroke='#b9c6cd'):
    return ('picture', x, y, w, h, dict(fill=fill, stroke=stroke, strokeW=1))


def TEMPLATES():
    T = []

    # ---- Event poster (A4) -------------------------------------------------
    T.append(dict(name='Event poster', cat='Posters', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 470, dict(shape='rect', fill='#20343f', strokeW=0)),
        ('shape', 0, 440, 794, 60, dict(shape='rect', fill='#e8a33d', strokeW=0)),
        ('text', 60, 60, 674, 30, dict(pad=0, size=16, color='#e8a33d', html='<p>SATURDAY 14 JUNE · 7PM</p>')),
        ('artistic', 60, 110, 674, 180, dict(size=92, bold=True, color='#ffffff', html='<p>Summer<br>Festival</p>')),
        ('text', 60, 330, 620, 90, dict(pad=0, size=22, color='#dfe6ea', html='<p>Live music, street food and a makers’ market down on the harbour.</p>')),
        _pic(60, 540, 674, 380),
        ('artistic', 60, 950, 500, 44, dict(size=30, bold=True, color='#20343f', html='<p>Quay Street Green</p>')),
        ('text', 60, 1000, 500, 60, dict(pad=0, size=16, color='#4b5a63', html='<p>Free entry · all welcome · quaysidefestival.example</p>')),
        ('qr', 600, 960, 134, 134, dict(text='https://quaysidefestival.example')),
    ]))

    # ---- Sale / promo flyer (A4) ------------------------------------------
    T.append(dict(name='Sale flyer', cat='Flyers', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 1123, dict(shape='rect', fill='#fff6ef', strokeW=0)),
        ('shape', 40, 40, 714, 300, dict(shape='rect', fill='#d84f3a', strokeW=0, radius=14)),
        ('artistic', 70, 70, 400, 120, dict(size=120, bold=True, color='#ffffff', html='<p>SALE</p>')),
        ('artistic', 70, 210, 640, 70, dict(size=54, bold=True, color='#ffe6c8', html='<p>Up to 50% off</p>')),
        _pic(40, 380, 340, 300),
        _pic(414, 380, 340, 300),
        ('artistic', 40, 720, 714, 50, dict(size=34, bold=True, color='#20343f', html='<p>This weekend only</p>')),
        ('text', 40, 790, 714, 160, dict(pad=0, size=19, color='#4b5a63', html='<p>Everything must go — kitchens, timber, tools and offcuts. Doors open 9am Saturday and Sunday.</p><p>Harbour &amp; Co., Unit 4, Quay Street.</p>')),
        ('line', 40, 970, 714, 0, dict(stroke='#d84f3a', strokeW=3)),
        ('text', 40, 990, 714, 40, dict(pad=0, size=16, color='#8a949b', html='<p>01234 567890 · harbourandco.example</p>')),
    ]))

    # ---- Gig / concert poster (A4, dark) ----------------------------------
    T.append(dict(name='Gig poster', cat='Posters', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 1123, dict(shape='rect', fill='#141019', strokeW=0)),
        ('shape', 0, 150, 794, 6, dict(shape='rect', fill='#e5407a', strokeW=0)),
        ('text', 60, 70, 674, 30, dict(pad=0, size=18, color='#e5407a', html='<p>THE OLD BOATHOUSE · FRI 20 SEPT</p>')),
        ('artistic', 50, 190, 694, 330, dict(size=110, bold=True, color='#ffffff', html='<p>THE<br>HARBOUR<br>LIGHTS</p>')),
        ('text', 60, 560, 674, 40, dict(pad=0, size=24, color='#c9b7e0', html='<p>with The Quaysiders · Low Tide · Marram</p>')),
        _pic(60, 640, 674, 300, '#241b33', '#3a2d52'),
        ('artistic', 60, 970, 400, 48, dict(size=34, bold=True, color='#e5407a', html='<p>Doors 8pm</p>')),
        ('text', 60, 1030, 674, 60, dict(pad=0, size=16, color='#9a8fb0', html='<p>£8 adv / £10 door · 18+ · tickets at harbourlights.example</p>')),
    ]))

    # ---- Community newsletter (A4) ----------------------------------------
    T.append(dict(name='Community newsletter', cat='Newsletters', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 120, dict(shape='rect', fill='#2a7d6b', strokeW=0)),
        ('artistic', 40, 28, 500, 60, dict(size=40, bold=True, color='#ffffff', html='<p>The Quayside Gazette</p>')),
        ('text', 44, 88, 600, 26, dict(pad=0, size=14, color='#ddeae6', html='<p>Spring issue · news from the harbour community</p>')),
        ('artistic', 40, 150, 500, 40, dict(size=26, bold=True, color='#243137', html='<p>New boardwalk opens</p>')),
        ('text', 40, 200, 360, 460, dict(pad=0, size=14, color='#243137', html='<p>After a winter of work, the restored boardwalk is open again. Volunteers rebuilt every plank by hand.</p><p>“It is the best it has looked in thirty years,” said one resident.</p><p>A ceremony is planned for the May bank holiday, with tea, cake and a brass band.</p>')),
        _pic(420, 150, 334, 220, '#cfe0e6', '#9fb8c0'),
        ('text', 420, 378, 334, 26, dict(pad=0, size=12, color='#5c6b73', html='<p><i>The new boardwalk at first light.</i></p>')),
        ('artistic', 420, 420, 320, 34, dict(size=20, bold=True, color='#243137', html='<p>Dates for the diary</p>')),
        ('table', 420, 462, 334, 160, dict(head='#dff0eb', cells=[['Event', 'When'], ['Boardwalk opening', '3 May'], ['Harbour market', '17 May'], ['Regatta', '31 May']])),
        ('line', 40, 1040, 714, 0, dict(stroke='#2a7d6b', strokeW=2)),
        ('text', 40, 1055, 714, 28, dict(pad=0, size=11, color='#5c6b73', html='<p>The Quayside Gazette · delivered free to every home on the harbour · issue 42</p>')),
    ]))

    # ---- Café / restaurant menu (A4) --------------------------------------
    T.append(dict(name='Café menu', cat='Menus', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 1123, dict(shape='rect', fill='#fbf7f0', strokeW=0)),
        ('line', 80, 110, 634, 0, dict(stroke='#b08445', strokeW=2)),
        ('artistic', 80, 56, 634, 60, dict(size=52, bold=True, color='#5a3d1e', align='center', html='<p>The Boathouse</p>')),
        ('text', 80, 124, 634, 26, dict(pad=0, size=16, color='#9a7b52', align='center', html='<p>— coffee · brunch · cake —</p>')),
        ('artistic', 80, 200, 300, 34, dict(size=24, bold=True, color='#5a3d1e', html='<p>Breakfast</p>')),
        ('text', 80, 244, 634, 200, dict(pad=0, size=16, color='#3c3228', html='<p>Bacon bap &nbsp;·&nbsp; 4.50<br>Eggs on toast &nbsp;·&nbsp; 4.00<br>Porridge &amp; honey &nbsp;·&nbsp; 3.50<br>Full harbour breakfast &nbsp;·&nbsp; 8.50</p>')),
        ('artistic', 80, 470, 300, 34, dict(size=24, bold=True, color='#5a3d1e', html='<p>Cake &amp; pastries</p>')),
        ('text', 80, 514, 634, 160, dict(pad=0, size=16, color='#3c3228', html='<p>Victoria sponge &nbsp;·&nbsp; 3.00<br>Lemon drizzle &nbsp;·&nbsp; 3.00<br>Scone, jam &amp; cream &nbsp;·&nbsp; 3.50</p>')),
        ('artistic', 80, 700, 300, 34, dict(size=24, bold=True, color='#5a3d1e', html='<p>Drinks</p>')),
        ('text', 80, 744, 634, 160, dict(pad=0, size=16, color='#3c3228', html='<p>Flat white &nbsp;·&nbsp; 2.80<br>Pot of tea &nbsp;·&nbsp; 2.40<br>Hot chocolate &nbsp;·&nbsp; 3.20</p>')),
        ('line', 80, 1010, 634, 0, dict(stroke='#b08445', strokeW=2)),
        ('text', 80, 1030, 634, 30, dict(pad=0, size=13, color='#9a7b52', align='center', html='<p>Quay Street · open 8–4 daily</p>')),
    ]))

    # ---- Business letterhead (A4) -----------------------------------------
    T.append(dict(name='Letterhead', cat='Stationery', w=794, h=1123, objs=[
        ('shape', 0, 0, 794, 10, dict(shape='rect', fill='#2a5d9f', strokeW=0)),
        ('artistic', 60, 54, 420, 40, dict(size=30, bold=True, color='#1f3a5f', html='<p>Harbour &amp; Co.</p>')),
        ('text', 60, 100, 420, 24, dict(pad=0, size=13, color='#6b7680', html='<p>Joinery &amp; restoration</p>')),
        ('text', 500, 54, 234, 90, dict(pad=0, size=12, color='#6b7680', align='right', html='<p>Unit 4, Quay Street<br>01234 567890<br>hello@harbourandco.example</p>')),
        ('line', 60, 150, 674, 0, dict(stroke='#d6dde4', strokeW=1)),
        ('text', 60, 200, 674, 760, dict(pad=0, size=15, color='#2b2b2b', html='<p>Dear …,</p><p>&nbsp;</p><p>Start your letter here. This frame flows as you type, so just write.</p>')),
        ('line', 60, 1000, 674, 0, dict(stroke='#d6dde4', strokeW=1)),
        ('text', 60, 1016, 674, 30, dict(pad=0, size=11, color='#9aa4ac', align='center', html='<p>Harbour &amp; Co. · registered in England · harbourandco.example</p>')),
    ]))

    # ---- Award certificate (A4 landscape) ---------------------------------
    T.append(dict(name='Certificate', cat='Certificates', w=1123, h=794, objs=[
        ('shape', 0, 0, 1123, 794, dict(shape='rect', fill='#ffffff', stroke='#c9a227', strokeW=0)),
        ('shape', 30, 30, 1063, 734, dict(shape='rect', fill='', stroke='#c9a227', strokeW=3, radius=4)),
        ('shape', 44, 44, 1035, 706, dict(shape='rect', fill='', stroke='#e4cf86', strokeW=1, radius=2)),
        ('artistic', 100, 110, 923, 50, dict(size=24, bold=True, color='#9a7b1e', align='center', html='<p>CERTIFICATE OF ACHIEVEMENT</p>')),
        ('text', 100, 210, 923, 30, dict(pad=0, size=18, color='#6b7680', align='center', html='<p>This is proudly presented to</p>')),
        ('artistic', 100, 250, 923, 80, dict(size=58, bold=True, color='#20343f', align='center', html='<p>Your Name Here</p>')),
        ('line', 360, 350, 403, 0, dict(stroke='#c9a227', strokeW=2)),
        ('text', 160, 400, 803, 90, dict(pad=0, size=18, color='#3c4650', align='center', html='<p>in recognition of outstanding work and dedication throughout the year.</p>')),
        ('text', 150, 640, 300, 26, dict(pad=0, size=15, color='#3c4650', align='center', html='<p>Date</p>')),
        ('line', 150, 630, 300, 0, dict(stroke='#9aa4ac', strokeW=1)),
        ('text', 673, 640, 300, 26, dict(pad=0, size=15, color='#3c4650', align='center', html='<p>Signature</p>')),
        ('line', 673, 630, 300, 0, dict(stroke='#9aa4ac', strokeW=1)),
    ]))

    # ---- Party invitation (A5) --------------------------------------------
    T.append(dict(name='Party invitation', cat='Invitations', w=559, h=794, objs=[
        ('shape', 0, 0, 559, 794, dict(shape='rect', fill='#2b1f3a', strokeW=0)),
        ('shape', 30, 30, 499, 734, dict(shape='rect', fill='', stroke='#e5b84b', strokeW=1.5, radius=6)),
        ('text', 60, 90, 439, 30, dict(pad=0, size=18, color='#e5b84b', align='center', html='<p>PLEASE JOIN US</p>')),
        ('artistic', 50, 150, 459, 150, dict(size=66, bold=True, color='#ffffff', align='center', html='<p>You’re<br>Invited</p>')),
        ('line', 200, 330, 159, 0, dict(stroke='#e5b84b', strokeW=1)),
        ('text', 60, 380, 439, 200, dict(pad=0, size=20, color='#e8e1f2', align='center', html='<p>to celebrate<br><b>Sam’s 30th</b></p><p>Saturday 12 July · 7pm<br>The Old Boathouse</p>')),
        ('text', 60, 660, 439, 60, dict(pad=0, size=15, color='#b9add0', align='center', html='<p>RSVP by 1 July · 01234 567890</p>')),
    ]))

    # ---- Classic business card --------------------------------------------
    T.append(dict(name='Business card — classic', cat='Business cards', w=334, h=213, objs=[
        ('shape', 0, 0, 334, 213, dict(shape='rect', fill='#ffffff', stroke='#e2e6ea', strokeW=1)),
        ('shape', 0, 0, 10, 213, dict(shape='rect', fill='#2a7d6b', strokeW=0)),
        ('artistic', 34, 34, 266, 34, dict(size=22, bold=True, color='#20343f', html='<p>Alex Harbour</p>')),
        ('text', 34, 72, 266, 22, dict(pad=0, size=12, color='#2a7d6b', html='<p>Master Joiner</p>')),
        ('line', 34, 104, 150, 0, dict(stroke='#e2e6ea', strokeW=1)),
        ('text', 34, 122, 266, 70, dict(pad=0, size=11, color='#5c6b73', html='<p>01234 567890<br>alex@harbourandco.example<br>Unit 4, Quay Street</p>')),
    ]))

    # ---- Bold business card -----------------------------------------------
    T.append(dict(name='Business card — bold', cat='Business cards', w=334, h=213, objs=[
        ('shape', 0, 0, 334, 213, dict(shape='rect', fill='#20343f', strokeW=0)),
        ('shape', 0, 150, 334, 63, dict(shape='rect', fill='#e8a33d', strokeW=0)),
        ('artistic', 24, 40, 286, 40, dict(size=26, bold=True, color='#ffffff', html='<p>Alex Harbour</p>')),
        ('text', 24, 88, 286, 22, dict(pad=0, size=12, color='#e8a33d', html='<p>JOINERY &amp; RESTORATION</p>')),
        ('text', 24, 162, 286, 44, dict(pad=0, size=11, color='#20343f', html='<p>01234 567890 · harbourandco.example</p>')),
    ]))

    # ---- Instagram quote (square) -----------------------------------------
    T.append(dict(name='Social — quote', cat='Social posts', w=800, h=800, objs=[
        ('shape', 0, 0, 800, 800, dict(shape='rect', fill='#114b5f', strokeW=0)),
        ('shape', 60, 60, 680, 680, dict(shape='rect', fill='', stroke='#88c0a0', strokeW=2, radius=10)),
        ('artistic', 110, 180, 580, 360, dict(size=56, bold=True, color='#ffffff', align='center', html='<p>“Measure twice,<br>cut once.”</p>')),
        ('line', 350, 560, 100, 0, dict(stroke='#88c0a0', strokeW=3)),
        ('text', 110, 600, 580, 40, dict(pad=0, size=22, color='#88c0a0', align='center', html='<p>Harbour &amp; Co.</p>')),
    ]))

    # ---- Instagram promo (square) -----------------------------------------
    T.append(dict(name='Social — promo', cat='Social posts', w=800, h=800, objs=[
        ('shape', 0, 0, 800, 800, dict(shape='rect', fill='#fff3e8', strokeW=0)),
        _pic(60, 60, 680, 420),
        ('shape', 520, 420, 220, 220, dict(shape='star5', fill='#e8556b', strokeW=0)),
        ('text', 540, 500, 180, 70, dict(pad=0, size=30, bold=True, color='#ffffff', align='center', html='<p>20%<br>OFF</p>')),
        ('artistic', 60, 520, 460, 50, dict(size=40, bold=True, color='#20343f', html='<p>New this week</p>')),
        ('text', 60, 580, 460, 120, dict(pad=0, size=20, color='#5c6b73', html='<p>Handmade oak chopping boards, finished in our workshop. While they last.</p>')),
        ('text', 60, 720, 680, 30, dict(pad=0, size=16, color='#8a949b', html='<p>@harbourandco · link in bio</p>')),
    ]))

    return T
