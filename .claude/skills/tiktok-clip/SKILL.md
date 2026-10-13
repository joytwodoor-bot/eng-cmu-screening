---
name: tiktok-clip
description: Turn a Thai TikTok script (Joy Psychofit style, sections like [Hook] [ปัญหา] [ความรู้] [ลงมือทำ] [ปิด], with "ข้อความบนจอ", "อ้างอิง" and optional "B-roll" lines) into a finished 9:16 short video with burned-in Thai CC, an .srt, a post caption, and B-roll images generated in Canva. Use whenever the user pastes a clip script like "คลิป N: ..." or asks to สร้างคลิปสั้น / ทำคลิปติ๊กตอก / ทำคลิปจากสคริปต์, even if they only paste the script with no instructions.
---

# TikTok clip from a script

The user pastes a script and expects the finished clip back with no further questions. Work through
every step below on your own; the only point to stop and ask is the Canva save approval in step 4.

Everything lives under `tiktok/` in this repo:
- `tiktok/tools/render.py` renders a clip: `python3 tiktok/tools/render.py tiktok/clipN/src/script.py tiktok/clipN/clipN-<slug>.mp4`.
  Along with the `.mp4` it writes `<name>.srt` and `<name>-broll.txt`, a list of time ranges for the B-roll.
- `tiktok/tools/fonts/` holds KanitI (italic) 600/800/900, Trirong 500/600/700, Mali 500/600/700 and Kanit 500/700/800 (Thai + Latin), already merged.
- Visual theme: the default is `"pop"`, the mood the user chose: Dua Lipa, confident pop/disco.
  - Look: black background with neon pink and mint glows in opposite corners; bold italic Kanit;
    glowing neon hero text in mint, pink and grey; mint-bordered CC box with pink highlights; solid
    mint or pink section chips; mint/pink disco sparkles; photos desaturated and darkened.
  - Other themes: put `THEME = "glam"` (dark gold/serif), `"soft"` (pastel pink) or `"dark"` (original)
    in script.py, or set the `CLIP_THEME` env var.
  - Write script colours with the dark palette constants (Y, W, R, G, M, B as in clip2). The renderer
    remaps them per theme: in pop, W is light grey, Y and G are mint, R is pink, M is grey and B is soft pink.
- Per-clip variation is automatic, so the feed does not look copy-pasted and the user asked for it.
  The renderer derives `VARIANT` from the clip number in `SERIES` and varies:
  - mint-led vs pink-led accents
  - one of three neon-glow layouts
  - one of three openers: rise, punch-in with flash, or wipe
  - mirrored sparkle positions

  The hook text is on screen from frame 0, so the TikTok cover is never blank. Do not set `VARIANT` by
  hand unless the user asks for a specific look.
- First frame matters most. Make the first HOOK hero short and punchy (2–4 words big). When the script
  has a B-roll for the hook, use it as beat 0's background so each clip opens on a different image.

## 0. Environment check (fast)

```bash
python3 -c "from PIL import features; assert features.check('raqm')" && which ffmpeg
```
If raqm is missing, run `pip install pillow`. Thai marks render wrong without raqm.

Text-to-speech is not available: Microsoft and Google voices are blocked by the network. The video ships
without a voiceover. Tell the user to record the voice in TikTok/CapCut by reading the on-screen CC.

## 1. Pick the clip number and slug

Use `ls tiktok/` and take the next `clipN`, or use the number given in the script title. The slug is
2–4 English words describing the topic, e.g. `clip3-sleep-and-cravings`.

## 2. Write `tiktok/clipN/src/script.py`

Module fields:
- `SERIES = "คลิป N · <title from the script>"`: the small header line on screen.
- `BEATS = [(section, hero_lines, cc_chunks, broll_note), ...]`
  - `section` is one of `"HOOK" "ปัญหา" "ความรู้" "ลงมือทำ" "ปิด"`, matching the script's tags.
  - `hero_lines` are the big words in the middle of the screen. Each line is `(text, size, color, style)`.
    - Use 2–5 lines per beat, with sizes from about 46 (attribution) to 180 (a single digit).
    - `style` is `""`, `"strike"` (struck-through text), or `"split"`. A split line uses text `"left::right"`
      and color `"#c1/#c2"`, giving two columns for comparisons.
    - Put the script's **ข้อความบนจอ** into the first HOOK beat as the hero.
  - `cc_chunks` are the subtitles: the **full script text, word for word**, split into phrases.
    - `|` starts a new line. Use at most 2 lines and about 28 Thai characters per line.
    - Break only at word boundaries.
    - Wrap 1–3 key words per chunk in `{}` to highlight them in yellow.
  - `broll_note` is the script's B-roll description, or `""`.
- `SECTION_COLORS` / `SECTION_LABELS`: copy them from clip2.

Content rules:
- Make a new beat whenever the visual idea changes; that gives about 10–14 beats per clip.
- In the ความรู้ beats, put the source as a hero line `("— Author", 46, M, "")` so the อ้างอิง is on screen.
- The fonts have no emoji, no `→` and no `♥`. Use `›` or `·` instead; the soft theme already draws its
  own hearts. To check any other symbol:
  `python3 -c "from fontTools.ttLib import TTFont; print(ord('X') in TTFont('tiktok/tools/fonts/KanitI-800.ttf').getBestCmap())"`.
- Address the viewer exactly as the script does (เธอ / คุณ). Never change the script's wording in the CC.

## 3. Render a first pass and check it

Render the clip, then pull frames from the middle of several beats into one strip and look at it:
```bash
for t in 2 15 30 45 60 75; do ffmpeg -loglevel error -y -ss $t -i OUT.mp4 -frames:v 1 -vf scale=300:-1 /tmp/f$t.png; done
ffmpeg -loglevel error -y $(for t in 2 15 30 45 60 75; do echo -i /tmp/f$t.png; done) -filter_complex hstack=6 /tmp/strip.png
```
Read the strip image. Look for:
- tofu boxes (missing glyphs)
- text overflowing the screen
- a hero overlapping the CC
- a blank hero (a frame caught mid-transition is fine; check a different time)

## 4. B-roll from Canva

For every beat with a B-roll note, except face-to-camera notes such as "หน้ากล้อง" or "ไม่มีภาพแทรก":

1. **Generate** with `mcp__Canva__generate-image`, `aspectRatio: PORTRAIT_9_16`.
   - Write the prompt in English: cinematic photo, young Thai woman when there is a person,
     mood and lighting from the note, and "no text, no brand logos". For the pop theme, add
     "moody low-key lighting, confident, editorial pop style".
   - Quick-cut notes (ภาพละ 1 วินาที, one image per item) get one image per item.
   - Split-screen notes (แบ่งจอ) get one image per side.
   - Poll `get-generate-image-job` until SUCCESS and collect each media id (`MA...`).
2. **Get full resolution.** Job results are only 112px thumbnails, so do this:
   - `create-design` with brief "plain dark 9:16 container for B-roll clip N" and format `Instagram Story`.
   - `read-design` with `open_transaction: true`.
   - `edit-design` with one `add_page` (1080×1920) per image, then `read-design` with `page_indices` to get the new page ids.
   - One `edit-design` per page: `update_fill` with `locator_id` = page id, `asset_type: image`, `asset_id` = media id.
3. **Ask the user** (AskUserQuestion) for approval to save the design; this is required before commit.
   Then call `edit-design` with `finalize: commit`.
4. **Export** with `export-design` using `{type: jpg, quality: 95, pages: [...], width: 1080, height: 1920}`.
   `curl` each URL into `tiktok/clipN/src/broll/<n>-<name>.jpg`.
5. **Map the images to beats** by appending this to script.py:
   ```python
   _BG = {0: "1-fridge.jpg", 4: "3a-left.jpg|3b-right.jpg", 9: [None, "6a.jpg", "6b.jpg", "6c.jpg"]}
   BEATS = [tuple(b) + (_BG.get(i),) for i, b in enumerate(BEATS)]
   ```
   - A string means a full-screen image.
   - `"a|b"` means a split screen.
   - A list gives one image per CC chunk; `None` shows the plain graphic background.

The renderer tints the photos to match the theme and slowly zooms them. Re-render and check again.

If Canva domains are blocked (curl gets a 403 from the proxy), the user must allow `www.canva.com`,
`design.canva.ai` and `export-download.canva.com` in the environment's Network access settings. Until
then, ship the clip without photos, together with `*-broll.txt` and the Canva links.

## 5. Write the extras

- `tiktok/clipN/caption.txt` holds the post caption. Include:
  - a hook line, one line on the takeaway, and the CTA from the script's ปิด
  - `อ้างอิง: ...` with the sources
  - 8–10 Thai and English hashtags, always including `#JoyPsychofit`
- `tiktok/clipN/README.md` holds a file table like the one in clip2's README.

## 6. Deliver

Commit and push to the working branch. Then use SendUserFile to send the `.mp4`, `.srt` and `caption.txt`.

Reply in Thai, briefly:
- clip length
- which beats got which B-roll
- what the user still has to do: voiceover, music, and any face-to-camera shots
