# -*- coding: utf-8 -*-
import re, subprocess, sys, unicodedata, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import importlib.util, os
# usage: python3 render.py path/to/script.py out.mp4
_spec = importlib.util.spec_from_file_location("clipscript", sys.argv[1])
S = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(S)
BEATS, SECTION_COLORS, SERIES = S.BEATS, S.SECTION_COLORS, S.SERIES
SECTION_LABELS = getattr(S, "SECTION_LABELS", {})

FONTS = os.path.dirname(os.path.abspath(__file__)) + "/fonts/"
OUT = sys.argv[2]
SRT = OUT.rsplit(".", 1)[0] + ".srt"
WW, HH, FPS = 1080, 1920, 30
CX = 520            # slightly left of centre: keeps clear of TikTok's right-side buttons
RATE, GAP, MIN_D = 12.5, 0.30, 1.5   # Thai chars/sec reading pace
END_HOLD = 2.0

# ---------- themes ----------
# Scripts are written with the "dark" palette; other themes remap those colours.
# Pick with THEME = "..." in the script or CLIP_THEME env var (default "pop").
THEMES = {
    "dark": dict(
        font="Kanit", weights={500: 500, 700: 700, 800: 800},
        bg_top=(24, 18, 44), bg_bot=(10, 8, 20), glow_alpha=70,
        colors={}, sections={},
        stroke=(16, 10, 30, 255), shadow=(0, 0, 0, 140), strike="#FF6B6B", divider=(255, 255, 255, 90),
        header=(255, 255, 255, 170), chip_text=(20, 14, 34, 255),
        cc_box=(8, 6, 16, 190), cc_border=None, cc_text="#FFFFFF", cc_hl="#FFD84D", cc_stroke=3,
        photo_shade=(8, 6, 16, 165), track=(255, 255, 255, 40), decor=False),
    "soft": dict(   # pastel, feminine
        font="Mali", weights={500: 600, 700: 700, 800: 700},
        bg_top=(255, 229, 239), bg_bot=(234, 224, 255), glow_alpha=110,
        colors={"#FFFFFF": "#5B2A4E", "#FFD84D": "#E0528A", "#FF6B6B": "#D9466F",
                "#7CF0B0": "#2E9E83", "#B9B3D9": "#9A7BB8", "#8FD3FF": "#7B6CD9"},
        sections={"HOOK": "#F27BA5", "ปัญหา": "#F4A07C", "ความรู้": "#A98BE0",
                  "ลงมือทำ": "#5CC6A8", "ปิด": "#F27BA5"},
        stroke=(255, 255, 255, 255), shadow=(224, 82, 138, 55), strike="#D9466F", divider=(91, 42, 78, 90),
        header=(91, 42, 78, 170), chip_text=(255, 255, 255, 255),
        cc_box=(255, 255, 255, 235), cc_border=(242, 123, 165, 255), cc_text="#5B2A4E", cc_hl="#E0528A", cc_stroke=0,
        photo_shade=(255, 238, 246, 180), track=(91, 42, 78, 30), decor=True),
    "glam": dict(   # dark, elegant, confident, a little sweet: serif, champagne gold + blush rose
        font="Trirong", weights={500: 500, 700: 600, 800: 700},
        bg_top=(38, 10, 24), bg_bot=(7, 3, 8), glow_alpha=55,
        colors={"#FFFFFF": "#F6EBDD", "#FFD84D": "#E8C48A", "#FF6B6B": "#E46F8F",
                "#7CF0B0": "#F3C3D0", "#B9B3D9": "#B79AA5", "#8FD3FF": "#D9B98C"},
        sections={"HOOK": "#E8C48A", "ปัญหา": "#E46F8F", "ความรู้": "#D9B98C",
                  "ลงมือทำ": "#F3C3D0", "ปิด": "#E8C48A"},
        stroke=(14, 4, 9, 255), shadow=(0, 0, 0, 170), strike="#E46F8F", divider=(232, 196, 138, 110),
        header=(246, 235, 221, 150), chip_text=(232, 196, 138, 255), chip_style="outline",
        cc_box=(14, 5, 10, 205), cc_border=(232, 196, 138, 150), cc_text="#F6EBDD", cc_hl="#E8C48A", cc_stroke=0,
        photo_shade=(22, 6, 14, 175), track=(246, 235, 221, 35), decor="glam", frame=(232, 196, 138, 90)),
    "pop": dict(    # Dua Lipa: black, neon mint + pink, grey; bold italic, glowing text
        font="KanitI", weights={500: 600, 700: 800, 800: 900},
        bg_top=(14, 14, 17), bg_bot=(4, 4, 6), glow_alpha=0, duo_glow=((255, 79, 154), (94, 242, 200)),
        colors={"#FFFFFF": "#EDEDF0", "#FFD84D": "#5EF2C8", "#FF6B6B": "#FF4F9A",
                "#7CF0B0": "#5EF2C8", "#B9B3D9": "#8E8E98", "#8FD3FF": "#FF9CC8"},
        sections={"HOOK": "#FF4F9A", "ปัญหา": "#8E8E98", "ความรู้": "#5EF2C8",
                  "ลงมือทำ": "#FF4F9A", "ปิด": "#5EF2C8"},
        stroke=(6, 6, 8, 255), shadow=(0, 0, 0, 0), strike="#FF4F9A", divider=(142, 142, 152, 120),
        header=(142, 142, 152, 220), chip_text=(8, 8, 10, 255),
        cc_box=(10, 10, 12, 215), cc_border=(94, 242, 200, 200), cc_text="#EDEDF0", cc_hl="#FF4F9A", cc_stroke=0,
        photo_shade=(6, 6, 8, 165), photo_sat=0.25, track=(142, 142, 152, 60), decor="pop", text_glow=True),
}
TH = THEMES[os.environ.get("CLIP_THEME") or getattr(S, "THEME", "pop")]
def tc(h):   # theme colour for a script colour
    return TH["colors"].get(h.upper(), h)
SECTION_COLORS = {k: TH["sections"].get(k, v) for k, v in SECTION_COLORS.items()}

def font(w, size):
    return ImageFont.truetype(f"{FONTS}{TH['font']}-{TH['weights'][w]}.ttf", size, layout_engine=ImageFont.Layout.RAQM)

def visible_len(s):
    s = re.sub(r"[{}|“”]", "", s)
    return sum(1 for c in s if not unicodedata.category(c).startswith("M") and c != " ")

def hexrgba(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# ---------- timeline ----------
timeline = []   # (start, end, beat_idx, chunk_text)
t = 0.4
for bi, (_, _, chunks, *_r) in enumerate(BEATS):
    for c in chunks:
        d = max(MIN_D, visible_len(c) / RATE) + GAP
        timeline.append((t, t + d, bi, c)); t += d
    t += 0.25
TOTAL = t + END_HOLD
beat_start = {}
for s, e, bi, _ in timeline:
    beat_start.setdefault(bi, s)
beat_end = {bi: max(e for s, e, b, _ in timeline if b == bi) for bi in beat_start}
beat_end[len(BEATS) - 1] = TOTAL
beat_start[0] = 0.0

def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
with open(SRT, "w", encoding="utf-8") as f:
    for i, (s, e, _, c) in enumerate(timeline, 1):
        f.write(f"{i}\n{ts(s)} --> {ts(e - 0.05)}\n{re.sub(r'[{}]', '', c).replace('|', chr(10))}\n\n")

BROLL = OUT.rsplit(".", 1)[0] + "-broll.txt"
with open(BROLL, "w", encoding="utf-8") as f:
    for bi, b in enumerate(BEATS):
        if len(b) > 3 and b[3]:
            f.write(f"{ts(beat_start[bi])[:8]} – {ts(beat_end[bi])[:8]}  [{SECTION_LABELS.get(b[0], b[0])}]  {b[3]}\n")

# ---------- static layers ----------
VIGNETTE = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
_v = Image.new("L", (WW, HH), 0)
ImageDraw.Draw(_v).ellipse([-260, 120, WW + 260, HH - 120], fill=255)
_v = _v.filter(ImageFilter.GaussianBlur(220)).point(lambda a: int((255 - a) * 0.75))
VIGNETTE.putalpha(_v)

def background(accent):
    bg = Image.new("RGBA", (WW, HH))
    d = ImageDraw.Draw(bg)
    top, bot = TH["bg_top"], TH["bg_bot"]
    for y in range(HH):
        k = y / HH
        d.line([(0, y), (WW, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)) + (255,))
    glow = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    if TH.get("duo_glow"):
        (p1, p2) = TH["duo_glow"]
        gd.ellipse([-380, 80, 520, 900], fill=p1 + (95,))
        gd.ellipse([560, 1100, 1460, 1980], fill=p2 + (80,))
    else:
        gd.ellipse([CX - 520, 380, CX + 520, 1180], fill=hexrgba(accent, TH["glow_alpha"]))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    bg.alpha_composite(glow)
    if TH.get("frame"):
        bg.alpha_composite(VIGNETTE)
        ImageDraw.Draw(bg).rounded_rectangle([34, 120, WW - 34, HH - 120], 28, outline=TH["frame"], width=2)
    # header
    d = ImageDraw.Draw(bg)
    d.text((CX, 190), SERIES, font=font(500, 38), fill=TH["header"], anchor="mm")
    return bg

def chip(label, color):
    f = font(700, 40)
    w = int(f.getlength(label)) + 64
    im = Image.new("RGBA", (w, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if TH.get("chip_style") == "outline":
        d.rounded_rectangle([0, 0, w - 1, 71], 36, fill=(14, 5, 10, 150), outline=hexrgba(color), width=3)
    else:
        d.rounded_rectangle([0, 0, w - 1, 71], 36, fill=hexrgba(color))
    d.text((w // 2, 36), label, font=f, fill=hexrgba(color) if TH.get("chip_style") == "outline" else TH["chip_text"], anchor="mm")
    return im

def hero(lines):
    pad = 14
    hs = [int(sz * 1.32) + pad for _, sz, _, _ in lines]
    im = Image.new("RGBA", (WW, sum(hs) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 20
    for (txt, sz, col, style), h in zip(lines, hs):
        cy = y + h // 2
        if style == "split":
            draw_split(d, txt, sz, col, cy); y += h; continue
        f = font(800 if sz >= 90 else 700, sz)
        while f.getlength(txt) > 900:
            sz -= 4; f = font(800 if sz >= 90 else 700, sz)
        cy = y + h // 2
        d.text((CX + 4, cy + 6), txt, font=f, fill=TH["shadow"], anchor="mm")
        d.text((CX, cy), txt, font=f, fill=hexrgba(tc(col)), anchor="mm",
               stroke_width=max(3, sz // 22), stroke_fill=TH["stroke"])
        if style == "strike":
            lw = f.getlength(txt) / 2 + 16
            d.line([(CX - lw, cy + 4), (CX + lw, cy + 4)], fill=hexrgba(TH["strike"]), width=max(6, sz // 9))
        y += h
    if TH.get("text_glow"):
        g = im.filter(ImageFilter.GaussianBlur(18))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(im)
        return out
    return im

def draw_split(d, txt, sz, col, cy):
    # "left::right" -> two columns with a divider; col may be "c1/c2"
    l, r = txt.split("::"); c1, c2 = (col.split("/") + [col])[:2]
    for t, c, x in ((l, c1, CX - 225), (r, c2, CX + 225)):
        f = font(800 if sz >= 80 else 700, sz)
        while f.getlength(t) > 400:
            sz -= 4; f = font(800 if sz >= 80 else 700, sz)
        d.text((x + 3, cy + 5), t, font=f, fill=TH["shadow"], anchor="mm")
        d.text((x, cy), t, font=f, fill=hexrgba(tc(c)), anchor="mm", stroke_width=max(3, sz // 22), stroke_fill=TH["stroke"])
    d.line([(CX, cy - sz * 0.6), (CX, cy + sz * 0.6)], fill=TH["divider"], width=3)

def caption(text):
    f = font(700, 54)
    lines = text.split("|")
    runs_per_line = []
    for ln in lines:
        parts = re.split(r"(\{[^}]*\})", ln)
        runs_per_line.append([(p[1:-1], True) if p.startswith("{") else (p, False) for p in parts if p])
    widths = [sum(f.getlength(t) for t, _ in r) for r in runs_per_line]
    lh = 82
    bw = int(max(widths)) + 76; bh = lh * len(lines) + 44
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], 36 if TH["cc_border"] else 28, fill=TH["cc_box"],
                        outline=TH["cc_border"], width=4 if TH["cc_border"] else 0)
    for i, (runs, w) in enumerate(zip(runs_per_line, widths)):
        x = (bw - w) / 2; y = 22 + i * lh + lh // 2
        for t, hl in runs:
            d.text((x, y), t, font=f, fill=hexrgba(TH["cc_hl"] if hl else TH["cc_text"]), anchor="lm",
                   stroke_width=TH["cc_stroke"], stroke_fill=(0, 0, 0, 255))
            x += f.getlength(t)
    return im

HEADER_LAYER = Image.new('RGBA', (WW, HH), (0, 0, 0, 0))
ImageDraw.Draw(HEADER_LAYER).text((CX, 190), SERIES, font=font(500, 38), fill=TH["header"], anchor='mm')
bgs = {sec: background(col) for sec, col in SECTION_COLORS.items()}

# ---------- optional photo B-roll (beat[4]: image name, "left|right" for split, or list per cc chunk) ----------
BROLL_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "broll")
_photo_cache = {}
def _cover(path, w, h):
    im = Image.open(path).convert("RGB")
    if TH.get("photo_sat") is not None:
        from PIL import ImageEnhance
        im = ImageEnhance.Color(im).enhance(TH["photo_sat"])
    k = max(w / im.width, h / im.height) * 1.1          # 10% headroom for the slow zoom
    im = im.resize((int(im.width * k + 0.5), int(im.height * k + 0.5)), Image.LANCZOS)
    return im
def photo_layer(spec):
    if spec not in _photo_cache:
        if "|" in spec:
            halves = [_cover(os.path.join(BROLL_DIR, n), WW // 2, HH) for n in spec.split("|")]
            _photo_cache[spec] = ("split", halves)
        else:
            _photo_cache[spec] = ("full", _cover(os.path.join(BROLL_DIR, spec), WW, HH))
    return _photo_cache[spec]
def _crop_zoom(im, w, h, z):
    k = min(im.width / w, im.height / h) / (1.1 * z)
    cw, ch = int(w * k), int(h * k)
    x0, y0 = (im.width - cw) // 2, (im.height - ch) // 2
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR)
SHADE = Image.new("RGBA", (WW, HH), TH["photo_shade"])   # wash photos so text stays readable
def photo_bg(spec, prog):
    kind, data = photo_layer(spec)
    z = 1.0 + 0.08 * prog
    if kind == "full":
        base = _crop_zoom(data, WW, HH, z)
    else:
        base = Image.new("RGB", (WW, HH))
        for i, im in enumerate(data):
            base.paste(_crop_zoom(im, WW // 2, HH, z), (i * WW // 2, 0))
    base = base.convert("RGBA")
    base.alpha_composite(SHADE)
    if TH.get("frame"):
        base.alpha_composite(VIGNETTE)
        ImageDraw.Draw(base).rounded_rectangle([34, 120, WW - 34, HH - 120], 28, outline=TH["frame"], width=2)
    if kind == "split":
        ImageDraw.Draw(base).line([(WW // 2, 340), (WW // 2, HH)], fill=TH["divider"][:3] + (140,), width=4)
    return base
def bg_spec(bi, t):
    b = BEATS[bi]
    if len(b) < 5 or not b[4]:
        return None
    spec = b[4]
    if isinstance(spec, (list, tuple)):
        idx = [ci for ci, (s, e, bb, _) in enumerate(timeline) if bb == bi]
        k = 0
        for j, ci in enumerate(idx):
            if timeline[ci][0] <= t: k = j
        spec = spec[min(k, len(spec) - 1)]
    return spec
chips = {sec: chip(SECTION_LABELS.get(sec, sec), col) for sec, col in SECTION_COLORS.items()}
heroes = [hero(b[1]) for b in BEATS]
caps = [caption(c) for _, _, _, c in timeline]

# floating hearts / sparkles for the soft theme
def heart(d, cx, cy, r, fill):
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * r / 16, cy + y * r / 16))
    d.polygon(pts, fill=fill)
def sparkle(d, cx, cy, r, fill):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)
DECOR = [  # (kind, x, y, size, rgba, phase) - kept to the screen edges, away from text
    ("h", 90, 420, 30, (242, 123, 165, 150), 0.0), ("s", 960, 360, 26, (255, 255, 255, 230), 1.1),
    ("h", 975, 1030, 22, (169, 139, 224, 140), 2.0), ("s", 70, 900, 20, (242, 123, 165, 170), 2.7),
    ("h", 120, 1620, 26, (244, 160, 124, 140), 3.3), ("s", 940, 1580, 30, (255, 255, 255, 220), 4.1),
    ("s", 230, 310, 16, (169, 139, 224, 170), 5.0), ("h", 850, 1760, 18, (242, 123, 165, 130), 5.7),
]
DECOR_GLAM = [  # sparse champagne sparkles, two tiny blush hearts
    ("s", 980, 330, 22, (232, 196, 138, 220), 0.0), ("s", 95, 470, 14, (246, 235, 221, 170), 1.4),
    ("h", 965, 1080, 14, (243, 195, 208, 150), 2.2), ("s", 80, 1560, 18, (232, 196, 138, 190), 3.1),
    ("s", 1000, 1640, 12, (246, 235, 221, 150), 4.0), ("h", 110, 960, 11, (228, 111, 143, 130), 4.9),
]
DECOR_POP = [  # disco sparkles in mint / pink / grey
    ("s", 975, 340, 26, (94, 242, 200, 230), 0.0), ("s", 90, 520, 18, (255, 79, 154, 220), 1.3),
    ("s", 990, 1060, 16, (142, 142, 152, 200), 2.1), ("s", 75, 1500, 24, (94, 242, 200, 210), 3.0),
    ("s", 960, 1650, 20, (255, 79, 154, 220), 3.8), ("s", 230, 300, 12, (237, 237, 240, 180), 4.6),
]
def draw_decor(frame, t):
    d = ImageDraw.Draw(frame)
    for kind, x, y, r, col, ph in {"glam": DECOR_GLAM, "pop": DECOR_POP}.get(TH["decor"], DECOR):
        yy = y + 14 * math.sin(t * 1.3 + ph)
        rr = r * (1 + 0.12 * math.sin(t * 2.0 + ph))
        (heart if kind == "h" else sparkle)(d, x, yy, rr, col)

def ease(x):
    x = min(1, max(0, x)); return 1 - (1 - x) ** 3

def paste_scaled(base, im, cx, cy, scale, alpha):
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ---------- render ----------
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WW}x{HH}", "-r", str(FPS), "-i", "-",
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

N = int(math.ceil(TOTAL * FPS))
for fi in range(N):
    t = fi / FPS
    bi = max(b for b in beat_start if beat_start[b] <= t)
    sec = BEATS[bi][0]
    spec = bg_spec(bi, t)
    if spec:
        frame = photo_bg(spec, (t - beat_start[bi]) / max(0.1, beat_end[bi] - beat_start[bi]))
        frame.alpha_composite(HEADER_LAYER)
    else:
        frame = bgs[sec].copy()
    if TH["decor"]:
        draw_decor(frame, t)
    # section chip
    frame.alpha_composite(chips[sec], (CX - chips[sec].width // 2, 250))
    # hero
    k = ease((t - beat_start[bi]) / 0.4)
    out = ease((t - (beat_end[bi] - 0.15)) / 0.15) if bi < len(BEATS) - 1 else 0
    breathe = 1 + 0.012 * math.sin(t * 2.2)
    paste_scaled(frame, heroes[bi], CX, 760 + 40 * (1 - k), (0.9 + 0.1 * k) * breathe, k * (1 - out))
    # caption
    for ci, (s, e, _, _) in enumerate(timeline):
        if s <= t < e:
            p = ease((t - s) / 0.15)
            paste_scaled(frame, caps[ci], CX, 1330, 0.88 + 0.12 * p, p)
            break
    # progress bar
    d = ImageDraw.Draw(frame)
    d.rectangle([0, 0, WW, 8], fill=TH["track"])
    d.rectangle([0, 0, int(WW * t / TOTAL), 8], fill=hexrgba(SECTION_COLORS[sec]))
    ff.stdin.write(frame.convert("RGB").tobytes())
    if fi % 300 == 0: print(f"{fi}/{N}", flush=True)
ff.stdin.close(); ff.wait()
print("done", OUT, f"{TOTAL:.1f}s", SRT)
