# -*- coding: utf-8 -*-
import re, subprocess, sys, unicodedata, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from script import BEATS, SECTION_COLORS

FONTS = __file__.rsplit("/", 2)[0] + "/fonts/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "clip1.mp4"
SRT = OUT.rsplit(".", 1)[0] + ".srt"
WW, HH, FPS = 1080, 1920, 30
CX = 520            # slightly left of centre: keeps clear of TikTok's right-side buttons
RATE, GAP, MIN_D = 12.5, 0.30, 1.5   # Thai chars/sec reading pace
END_HOLD = 2.0
SERIES = "คลิป 1 · กินเกินไปคำเดียว ทำไมพังทั้งวัน"

def font(w, size):
    return ImageFont.truetype(f"{FONTS}Kanit-{w}.ttf", size, layout_engine=ImageFont.Layout.RAQM)

def visible_len(s):
    s = re.sub(r"[{}|“”]", "", s)
    return sum(1 for c in s if not unicodedata.category(c).startswith("M") and c != " ")

def hexrgba(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# ---------- timeline ----------
timeline = []   # (start, end, beat_idx, chunk_text)
t = 0.4
for bi, (_, _, chunks) in enumerate(BEATS):
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

# ---------- static layers ----------
def background(accent):
    bg = Image.new("RGBA", (WW, HH))
    d = ImageDraw.Draw(bg)
    top, bot = (24, 18, 44), (10, 8, 20)
    for y in range(HH):
        k = y / HH
        d.line([(0, y), (WW, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)) + (255,))
    glow = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([CX - 520, 380, CX + 520, 1180], fill=hexrgba(accent, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    bg.alpha_composite(glow)
    # header
    d = ImageDraw.Draw(bg)
    d.text((CX, 190), SERIES, font=font(500, 38), fill=(255, 255, 255, 170), anchor="mm")
    return bg

def chip(label, color):
    f = font(700, 40)
    w = int(f.getlength(label)) + 64
    im = Image.new("RGBA", (w, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 71], 36, fill=hexrgba(color))
    d.text((w // 2, 36), label, font=f, fill=(20, 14, 34, 255), anchor="mm")
    return im

def hero(lines):
    pad = 14
    hs = [int(sz * 1.32) + pad for _, sz, _, _ in lines]
    im = Image.new("RGBA", (WW, sum(hs) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 20
    for (txt, sz, col, style), h in zip(lines, hs):
        f = font(800 if sz >= 90 else 700, sz)
        while f.getlength(txt) > 900:
            sz -= 4; f = font(800 if sz >= 90 else 700, sz)
        cy = y + h // 2
        d.text((CX + 4, cy + 6), txt, font=f, fill=(0, 0, 0, 140), anchor="mm")
        d.text((CX, cy), txt, font=f, fill=hexrgba(col), anchor="mm",
               stroke_width=max(2, sz // 28), stroke_fill=(16, 10, 30, 255))
        if style == "strike":
            lw = f.getlength(txt) / 2 + 16
            d.line([(CX - lw, cy + 4), (CX + lw, cy + 4)], fill=hexrgba("#FF6B6B"), width=max(6, sz // 9))
        y += h
    return im

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
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], 28, fill=(8, 6, 16, 190))
    for i, (runs, w) in enumerate(zip(runs_per_line, widths)):
        x = (bw - w) / 2; y = 22 + i * lh + lh // 2
        for t, hl in runs:
            d.text((x, y), t, font=f, fill=hexrgba("#FFD84D" if hl else "#FFFFFF"), anchor="lm",
                   stroke_width=3, stroke_fill=(0, 0, 0, 255))
            x += f.getlength(t)
    return im

bgs = {sec: background(col) for sec, col in SECTION_COLORS.items()}
chips = {sec: chip(sec if sec != "HOOK" else "รู้ไหม?", col) for sec, col in SECTION_COLORS.items()}
heroes = [hero(b[1]) for b in BEATS]
caps = [caption(c) for _, _, _, c in timeline]

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
    frame = bgs[sec].copy()
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
    d.rectangle([0, 0, WW, 8], fill=(255, 255, 255, 40))
    d.rectangle([0, 0, int(WW * t / TOTAL), 8], fill=hexrgba(SECTION_COLORS[sec]))
    ff.stdin.write(frame.convert("RGB").tobytes())
    if fi % 300 == 0: print(f"{fi}/{N}", flush=True)
ff.stdin.close(); ff.wait()
print("done", OUT, f"{TOTAL:.1f}s", SRT)
