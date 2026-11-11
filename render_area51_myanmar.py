#!/usr/bin/env python3
"""G.I KO KO — Area 51: 2026 files | 5 min | Deepgram English voice + Myanmar subtitles | 9:16."""
import asyncio, hashlib, io, json, os, subprocess, time
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
WORK = ROOT / "work_area51"
IMAGES = WORK / "images"
OUT = ROOT / "output"
STORY = json.loads((ROOT / "area51_story.json").read_text(encoding="utf-8"))
W, H, FPS, CLIP = 720, 1280, 24, 30
VIDEO = OUT / "GI-KO-KO-AREA51-2026-MYANMAR-5MIN-720x1280.mp4"
DEEPGRAM_MODEL = os.environ.get("DEEPGRAM_MODEL", "aura-2-orion-en")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
UA = {"User-Agent": "GIKOKO-AI-Documentary-Studio/1.0 (educational documentary)"}
USED = set()

def run(cmd):
    subprocess.run(cmd, check=True)

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/padauk/Padauk-Bold.ttf" if bold else "/usr/share/fonts/truetype/padauk/Padauk-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMyanmar-VF.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def commons_image(queries, index):
    endpoint = "https://commons.wikimedia.org/w/api.php"
    for query in queries:
        params = {
            "action": "query", "generator": "search",
            "gsrsearch": query + " filetype:bitmap", "gsrnamespace": 6,
            "gsrlimit": 40, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 1600, "format": "json"
        }
        try:
            data = None
            for attempt in range(4):
                data = requests.get(endpoint, params=params, headers=UA, timeout=50)
                if data.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    retry_after = data.headers.get("Retry-After", "")
                    try:
                        wait_seconds = float(retry_after)
                    except (TypeError, ValueError):
                        wait_seconds = 2 ** attempt
                    wait_seconds = min(max(wait_seconds, 1), 20)
                    print(f"Commons HTTP {data.status_code}; retrying in {wait_seconds:.0f}s")
                    time.sleep(wait_seconds)
                    continue
                data.raise_for_status()
                break
            pages = data.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"Commons query failed ({query}): {exc}")
            continue
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            meta = info.get("extmetadata", {})
            license_name = meta.get("LicenseShortName", {}).get("value", "")
            lic = license_name.upper()
            reusable = ("PUBLIC DOMAIN" in lic or "CC0" in lic or
                        ("CC BY" in lic and "NC" not in lic and "ND" not in lic))
            url = info.get("thumburl") or info.get("url")
            if not reusable or not url:
                continue
            try:
                response = None
                for attempt in range(4):
                    response = requests.get(url, headers=UA, timeout=60)
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                        retry_after = response.headers.get("Retry-After", "")
                        try:
                            wait_seconds = float(retry_after)
                        except (TypeError, ValueError):
                            wait_seconds = 2 ** attempt
                        wait_seconds = min(max(wait_seconds, 1), 20)
                        print(f"Image server HTTP {response.status_code}; retrying in {wait_seconds:.0f}s")
                        time.sleep(wait_seconds)
                        continue
                    response.raise_for_status()
                    break
                raw = response.content
                digest = hashlib.sha256(raw).hexdigest()
                if digest in USED:
                    continue
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                if im.width < 650 or im.height < 400:
                    continue
                USED.add(digest)
                target = IMAGES / f"source_{index:02d}.jpg"
                im.save(target, quality=94)
                artist = meta.get("Artist", {}).get("value", "Unknown author")
                source = info.get("descriptionurl", "")
                with (ASSETS / "ATTRIBUTION_AREA51.txt").open("a", encoding="utf-8") as f:
                    f.write(f"Scene {index:02d}: {page.get('title','Untitled')}\nAuthor: {artist}\nLicense: {license_name}\nSource: {source}\n\n")
                print(f"Image {index:02d}: {page.get('title')} [{license_name}]")
                return target
            except Exception as exc:
                print(f"Skipping image candidate: {exc}")
    print(f"No reusable Commons image found for scene {index}; creating original scene artwork.")
    return None

def make_original_scene_art(index, scene):
    """Create a distinct, topic-matched fallback visual; never reuse another scene's photo."""
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / max(1, H - 1)
        top = (7, 18, 35)
        bottom = (105, 82, 57) if index in (2, 5, 9, 10) else (24, 47, 68)
        color = tuple(int(top[k] * (1 - t) + bottom[k] * t) for k in range(3))
        for x in range(W):
            px[x, y] = color
    d = ImageDraw.Draw(im, "RGBA")
    # Star field and distant mountain silhouettes.
    for n in range(95):
        x = (n * 97 + index * 53) % W
        y = (n * 43 + index * 29) % 520
        r = 1 + (n % 3 == 0)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(210, 225, 235, 150))
    d.polygon([(0, 690), (110, 510), (235, 700), (390, 470), (560, 700), (720, 520), (720, 850), (0, 850)],
              fill=(24, 35, 43, 255))
    d.polygon([(0, 790), (170, 650), (310, 820), (500, 630), (720, 800), (720, 1000), (0, 1000)],
              fill=(48, 48, 43, 255))
    d.rectangle((0, 850, W, H), fill=(75, 65, 51, 255))
    # Scene-specific, original vector motifs.
    if index == 5:  # Restricted perimeter and warning sign
        for x in range(35, 710, 55):
            d.line((x, 640, x, 1100), fill=(30, 35, 39, 255), width=8)
        for y in (730, 850, 970):
            d.line((20, y, 700, y-25), fill=(28, 33, 38, 255), width=7)
        d.rounded_rectangle((205, 500, 515, 720), radius=12, fill=(180, 145, 70, 255), outline=(25, 28, 30, 255), width=9)
        d.text((235, 545), "RESTRICTED", font=font(32, True), fill=(20, 24, 27, 255))
        d.text((265, 600), "AREA 51", font=font(38, True), fill=(20, 24, 27, 255))
    elif index in (3, 4, 6):  # Aircraft silhouette
        cx, cy = 360, 650
        d.polygon([(cx-250, cy), (cx-40, cy-24), (cx+15, cy-175), (cx+55, cy-180),
                   (cx+40, cy-28), (cx+250, cy), (cx+40, cy+25), (cx+5, cy+105),
                   (cx-25, cy+105), (cx-35, cy+25)], fill=(8, 14, 20, 245))
        d.line((cx-220, cy+5, cx+220, cy+5), fill=(130, 190, 210, 150), width=3)
        d.ellipse((cx-5, cy-18, cx+20, cy+8), fill=(95, 180, 205, 200))
    elif index in (7, 8):  # UAP sensor/radar graphic
        cx, cy = 360, 690
        for radius in (120, 220, 320):
            d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=(80, 210, 190, 180), width=3)
        d.line((cx, cy-340, cx, cy+340), fill=(80, 210, 190, 150), width=2)
        d.line((cx-340, cy, cx+340, cy), fill=(80, 210, 190, 150), width=2)
        d.line((cx, cy, cx+210, cy-170), fill=(120, 240, 210, 230), width=5)
        d.ellipse((cx+185, cy-195, cx+215, cy-165), fill=(255, 220, 120, 255))
    elif index == 9:  # Hangar / runway
        d.polygon([(120, 720), (210, 560), (510, 560), (600, 720)], fill=(17, 25, 31, 255), outline=(115, 145, 155, 255))
        d.rectangle((210, 650, 510, 850), fill=(8, 15, 22, 255), outline=(110, 135, 145, 255), width=5)
        d.polygon([(330, 850), (390, 850), (570, 1280), (150, 1280)], fill=(110, 103, 87, 255))
        for yy in range(900, 1250, 90):
            d.line((360, yy, 360, yy+35), fill=(230, 210, 160, 200), width=5)
    elif index == 10:  # Sunset close
        d.ellipse((235, 430, 485, 680), fill=(240, 170, 90, 220))
        d.polygon([(0, 780), (190, 650), (330, 790), (520, 620), (720, 770), (720, 1280), (0, 1280)],
                  fill=(35, 38, 37, 255))
    else:
        # Abstract intelligence dossier motif for any other missing scene.
        d.rounded_rectangle((150, 470, 570, 930), radius=20, fill=(9, 24, 36, 235), outline=(90, 190, 205, 220), width=4)
        d.text((195, 530), "CLASSIFIED FILE", font=font(30, True), fill=(140, 220, 230, 255))
        for yy in (620, 690, 760, 830):
            d.line((200, yy, 520, yy), fill=(170, 190, 195, 190), width=5)
    target = IMAGES / f"original_scene_{index:02d}.jpg"
    im.save(target, quality=94, optimize=True)
    with (ASSETS / "ATTRIBUTION_AREA51.txt").open("a", encoding="utf-8") as f:
        f.write(f"Scene {index:02d}: Original scene-specific artwork generated by G.I KO KO Documentary Studio; no external image source.\n\n")
    print(f"Original fallback artwork created for scene {index}: {scene['title']}")
    return target

def make_scene_image(index, scene):
    source = commons_image(scene["visual_queries"], index)
    if source is None:
        source = make_original_scene_art(index, scene)
    im = Image.open(source).convert("RGB")
    iw, ih = im.size
    scale = max(W / iw, H / ih)
    im = im.resize((int(iw * scale), int(ih * scale)), Image.Resampling.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    # restrained cinematic grade, without changing the documentary subject
    tint = Image.new("RGB", (W, H), (5, 14, 24))
    im = Image.blend(im, tint, 0.16)
    # chapter slate, kept above the subtitle safe area
    overlay = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle((20, 18, W - 20, 132), radius=18,
                        fill=(3, 10, 20, 175), outline=(70, 180, 210, 190), width=2)
    d.text((40, 30), f"AREA 51  /  2026 FILES  /  {index:02d}",
           font=font(20, True), fill=(140, 225, 245, 255))
    d.text((40, 70), scene["title"], font=font(28, True), fill=(255, 255, 255, 255))
    im = im.convert("RGBA")
    im.alpha_composite(overlay, (0, 20))
    path = IMAGES / f"scene_{index:02d}.jpg"
    im.convert("RGB").save(path, quality=92, optimize=True)
    return path

def make_logo():
    logo = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((2, 2, 298, 98), radius=18,
                        fill=(2, 18, 24, 190), outline=(65, 210, 170, 230), width=2)
    d.text((18, 8), "G.I KO KO", font=font(34, True), fill=(120, 240, 200, 255))
    d.text((20, 56), "POWERED BY I KO KO", font=font(14, True), fill=(245, 250, 250, 255))
    p = WORK / "gi_koko_watermark.png"
    logo.save(p)
    return p

def make_voice(text, output):
    if not DEEPGRAM_API_KEY:
        raise RuntimeError("Missing DEEPGRAM_API_KEY GitHub Secret. English narration must use Deepgram.")
    url = f"https://api.deepgram.com/v1/speak?model={DEEPGRAM_MODEL}&encoding=mp3"
    response = requests.post(
        url,
        headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
        json={"text": text},
        timeout=180
    )
    if response.status_code != 200:
        raise RuntimeError(f"Deepgram TTS failed ({response.status_code}): {response.text[:800]}")
    if len(response.content) < 1000:
        raise RuntimeError("Deepgram returned an empty audio response")
    output.write_bytes(response.content)
    seconds = duration(output)
    if seconds > 28.0:
        raise RuntimeError(f"English narration is too long for its 30-second scene: {seconds:.2f}s")
    print(f"Deepgram voice verified: model={DEEPGRAM_MODEL}, duration={seconds:.2f}s")


def srt_stamp(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def myanmar_graphemes(text):
    # Keep Myanmar combining marks and kinzi/stacked consonants together.
    import unicodedata
    clusters, current = [], ""
    previous = ""
    for ch in text:
        category = unicodedata.category(ch)
        if not current or category.startswith("M") or previous in ("\u1039", "\u200d"):
            current += ch
        else:
            clusters.append(current)
            current = ch
        previous = ch
    if current:
        clusters.append(current)
    return clusters


def wrap_myanmar_pixels(text, max_width=610, size=20):
    face = font(size)
    lines, current = [], ""
    for cluster in myanmar_graphemes(text):
        candidate = current + cluster
        if current and face.getlength(candidate) > max_width:
            lines.append(current.rstrip())
            current = cluster.lstrip()
        else:
            current = candidate
    if current.strip():
        lines.append(current.rstrip())
    return lines or [text]


def make_subtitle(text, audio_seconds, path):
    # Burmese has no spaces between every word; wrap by Padauk pixel width,
    # not Python character count. This prevents captions running off-screen.
    sentences = [x.strip() for x in text.replace("။", "။|").split("|") if x.strip()]
    if not sentences:
        sentences = [text.strip()]
    weights = [max(1, len(myanmar_graphemes(x))) for x in sentences]
    total = sum(weights)
    cursor = 0.35
    end_limit = max(cursor + 1.0, min(audio_seconds, 29.5))
    entries = []
    for i, (sentence, weight) in enumerate(zip(sentences, weights)):
        end = end_limit if i == len(sentences) - 1 else cursor + (end_limit - 0.35) * weight / total
        wrapped = wrap_myanmar_pixels(sentence, max_width=610, size=20)
        # Keep all text; long captions can use 2–3 compact lines.
        caption = "\n".join(wrapped)
        entries.append(f"{i+1}\n{srt_stamp(cursor)} --> {srt_stamp(end)}\n{caption}\n")
        cursor = end
    path.write_text("\n".join(entries), encoding="utf-8")


def main():
    for tool in ("ffmpeg", "ffprobe"):
        subprocess.run(["bash", "-lc", f"command -v {tool} >/dev/null"], check=True)
    if len(STORY) != 10 or any(not x.get("narration_en") or not x.get("narration_mm") for x in STORY):
        raise RuntimeError("Expected 10 scenes, each with English narration and Burmese subtitle text")
    ASSETS.mkdir(exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    credits = ASSETS / "ATTRIBUTION_AREA51.txt"
    credits.write_text("G.I KO KO AREA 51 DOCUMENTARY — image credits\nOnly public-domain / CC0 / compatible CC BY images are accepted.\n\n", encoding="utf-8")
    logo = make_logo()
    clips = []
    for i, scene in enumerate(STORY, 1):
        print(f"Preparing scene {i}/10: {scene['title']}")
        image = make_scene_image(i, scene)
        audio = WORK / f"voice_{i:02d}.mp3"
        make_voice(scene["narration_en"], audio)
        subs = WORK / f"subtitle_{i:02d}.srt"
        make_subtitle(scene["narration_mm"], duration(audio), subs)
        clip = WORK / f"clip_{i:02d}.mp4"
        vf = (
            "zoompan=z='min(zoom+0.00025,1.06)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            "d=1:s=720x1280:fps=24,"
            f"subtitles=filename='{subs.as_posix()}':fontsdir='/usr/share/fonts/truetype/padauk':"
            "force_style='FontName=Padauk,FontSize=20,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&HCC000000,BorderStyle=1,Outline=2,Shadow=1,"
            "Alignment=2,MarginL=55,MarginR=55,MarginV=125'"
        )
        fc = (
            "[1:a]aresample=44100,apad=pad_dur=30,atrim=duration=30,volume=1.0[voice];"
            "anoisesrc=color=brown:amplitude=0.004:sample_rate=44100:duration=30,"
            "lowpass=f=500,volume=0.20[amb];"
            "[voice][amb]amix=inputs=2:duration=longest:normalize=0,"
            "alimiter=limit=0.92[a]"
        )
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-framerate", "24", "-i", str(image),
            "-i", str(audio), "-filter_complex", fc, "-vf", vf,
            "-map", "0:v:0", "-map", "[a]", "-t", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
            "-maxrate", "1600k", "-bufsize", "3200k", "-pix_fmt", "yuv420p",
            "-r", "24", "-threads", "2", "-c:a", "aac", "-b:a", "128k",
            "-ar", "44100", "-movflags", "+faststart", str(clip)
        ])
        clips.append(clip)
        print(f"Rendered scene {i}/10; voice duration {duration(audio):.2f}s")
    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in clips), encoding="utf-8")
    joined = WORK / "joined.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
         "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(joined)])
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined),
        "-i", str(logo), "-filter_complex", "[0:v][1:v]overlay=W-w-18:22:format=auto[v]",
        "-map", "[v]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "25", "-maxrate", "1600k", "-bufsize", "3200k",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "copy", "-t", "300",
        "-movflags", "+faststart", str(VIDEO)
    ])
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,width,height,r_frame_rate:format=duration,size",
        "-of", "json", str(VIDEO)
    ], text=True))
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_name") == "h264"), None)
    audio = next((s for s in streams if s.get("codec_name") == "aac"), None)
    seconds = float(info["format"]["duration"])
    if not video or not audio or video.get("width") != 720 or video.get("height") != 1280:
        raise RuntimeError("Final MP4 codec or resolution verification failed")
    if not 299.0 <= seconds <= 301.0:
        raise RuntimeError(f"Final duration verification failed: {seconds:.2f}s")
    if video.get("r_frame_rate") != "24/1":
        raise RuntimeError(f"Unexpected frame rate: {video.get('r_frame_rate')}")
    print(f"VERIFIED MP4: {VIDEO} | {seconds:.2f}s | {int(info['format']['size'])/1048576:.1f} MB")
    print(f"VOICE: Deepgram {DEEPGRAM_MODEL} (English) | Burmese Unicode subtitles | 10 unique credited visuals")
    # Thumbnail uses the first documentary scene, with the final brand overlay.
    thumb = OUT / "GI-KO-KO-AREA51-2026-THUMBNAIL.jpg"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "00:00:04",
         "-i", str(VIDEO), "-frames:v", "1", "-q:v", "2", str(thumb)])
    if not thumb.exists() or thumb.stat().st_size < 10000:
        raise RuntimeError("Thumbnail verification failed")

if __name__ == "__main__":
    main()
