#!/usr/bin/env python3
"""G.I KO KO — The Hidden Wonders of the Forest (10-minute documentary)."""
import hashlib, json, os, re, subprocess, time
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
WORK = ROOT / "work_forest_wonders"
IMAGES = WORK / "images"
OUT = ROOT / "output"
STORY = json.loads((ROOT / "forest_wonders_story.json").read_text(encoding="utf-8"))
API_KEY = os.environ.get("DEEPGRAM_API_KEY", "").strip()
TTS_MODEL = os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-orion-en")
TARGET_SECONDS = 600.0
W, H, FPS = 720, 1280, 24
VIDEO = OUT / "forest_wonders_10min_gi_koko_720x1280.mp4"
THUMB = OUT / "GI-KO-KO-FOREST-WONDERS-THUMBNAIL.jpg"
UA = {"User-Agent": "GIKOKO-ForestWonders-Documentary/0.0.2 (educational video; image attribution included)"}

def run(cmd):
    subprocess.run(cmd, check=True)

def probe_duration(path):
    value = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(value)

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def clean_html(value):
    return re.sub(r"<[^>]+>", "", str(value or "")).replace("&nbsp;", " ").strip()

def allowed_license(meta):
    lic = clean_html(meta.get("LicenseShortName", {}).get("value", "")).upper()
    return ("PUBLIC DOMAIN" in lic or "CC0" in lic or "CC BY" in lic) and "NC" not in lic and "ND" not in lic

def fetch_commons_image(queries, index, used_hashes, exact_title=None):
    if isinstance(queries, str):
        queries = [queries]
    endpoint = "https://commons.wikimedia.org/w/api.php"

    def accept_page(page):
        page_title = page.get("title", "").lower()
        if not page_title.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return None
        info = page.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})
        if not allowed_license(meta):
            return None
        url = info.get("thumburl") or info.get("url")
        if not url or not url.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp")):
            return None
        try:
            image_response = requests.get(url, headers=UA, timeout=60)
            image_response.raise_for_status()
            raw = image_response.content
            digest = hashlib.sha256(raw).hexdigest()
            if digest in used_hashes:
                return None
            import io
            im = Image.open(io.BytesIO(raw))
            if im.width < 700 or im.height < 500:
                return None
            im.verify()
            used_hashes.add(digest)
            target = IMAGES / f"source_{index:02d}.jpg"
            Image.open(io.BytesIO(raw)).convert("RGB").save(target, quality=94)
            artist = clean_html(meta.get("Artist", {}).get("value", "Unknown author"))
            license_name = clean_html(meta.get("LicenseShortName", {}).get("value", "License not stated"))
            source_url = info.get("descriptionurl", "")
            title = page.get("title", "Untitled Commons image")
            with (ASSETS / "ATTRIBUTION_FOREST_WONDERS.txt").open("a", encoding="utf-8") as f:
                f.write(f"Scene {index:02d} — {title}\nAuthor: {artist}\nLicense: {license_name}\nSource: {source_url}\n\n")
            print(f"IMAGE {index:02d}/{len(STORY)}: {title} [{license_name}]")
            return target
        except Exception as exc:
            print(f"Skipping Commons candidate: {exc}")
            return None

    # Prefer an explicitly identified Commons file when one is known.
    if exact_title:
        try:
            response = requests.get(endpoint, params={
                "action": "query", "titles": exact_title, "prop": "imageinfo",
                "iiprop": "url|extmetadata", "iiurlwidth": 1800, "format": "json"
            }, headers=UA, timeout=45)
            response.raise_for_status()
            for page in response.json().get("query", {}).get("pages", {}).values():
                found = accept_page(page)
                if found:
                    print(f"Using verified Commons file title: {exact_title}")
                    return found
        except Exception as exc:
            print(f"Exact Commons image lookup failed for {exact_title}: {exc}")

    for query in queries:
        params = {
            "action": "query", "generator": "search", "gsrsearch": query + " filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 50, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 1800, "format": "json"
        }
        try:
            response = requests.get(endpoint, params=params, headers=UA, timeout=45)
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"Commons search fallback for '{query}': {exc}")
            continue
        for page in pages.values():
            found = accept_page(page)
            if found:
                print(f"Image search match for scene {index:02d} via '{query}'")
                return found
        print(f"No suitable image found for search term: {query}; trying next alternative.")
    raise RuntimeError(f"No unique reusable Wikimedia Commons image found for scene {index}: {queries}")

def prepare_image(source, index, title):
    im = Image.open(source).convert("RGB")
    iw, ih = im.size
    target_ratio = W / H
    if iw / ih > target_ratio:
        nw = int(ih * target_ratio)
        left = (iw - nw) // 2
        im = im.crop((left, 0, left + nw, ih))
    else:
        nh = int(iw / target_ratio)
        top = (ih - nh) // 2
        im = im.crop((0, top, iw, top + nh))
    im = im.resize((W, H), Image.Resampling.LANCZOS)
    # Soft cinematic grade, retaining the original botanical colours.
    overlay = Image.new("RGB", im.size, (4, 16, 12))
    im = Image.blend(im, overlay, 0.12)
    # Small, readable botanical chapter label.
    panel = Image.new("RGBA", (W, 118), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((22, 16, W - 22, 102), radius=18, fill=(2, 12, 10, 170), outline=(208, 190, 132, 110), width=2)
    pd.text((42, 30), f"BOTANICAL FIELD NOTES  /  {index:02d}", font=font(18, True), fill=(226, 215, 174, 255))
    pd.text((42, 58), title.upper(), font=font(27, True), fill=(255, 255, 245, 255))
    im = im.convert("RGBA")
    im.alpha_composite(panel, (0, 24))
    target = IMAGES / f"scene_{index:02d}.jpg"
    im.convert("RGB").save(target, quality=92, optimize=True)
    return target

def make_brand():
    logo = Image.new("RGBA", (300, 112), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((2, 2, 298, 110), radius=18, fill=(2, 14, 11, 175), outline=(211, 187, 120, 210), width=2)
    d.text((22, 8), "G.I", font=font(52, True), fill=(246, 226, 170, 255), stroke_width=1, stroke_fill=(30, 24, 12, 255))
    d.text((24, 72), "POWERED BY I KO KO", font=font(14, True), fill=(255, 255, 244, 255))
    path = WORK / "brand_gi.png"
    logo.save(path)
    return path

def deepgram_tts(text, output):
    url = "https://api.deepgram.com/v1/speak"
    params = {"model": TTS_MODEL, "encoding": "mp3"}
    headers = {"Authorization": f"Token {API_KEY}", "Content-Type": "application/json"}
    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(url, params=params, headers=headers, json={"text": text}, timeout=180)
            if response.status_code >= 400:
                raise RuntimeError(f"Deepgram HTTP {response.status_code}: {response.text[:500]}")
            if not response.content or len(response.content) < 1000:
                raise RuntimeError("Deepgram returned an empty or invalid audio response")
            output.write_bytes(response.content)
            return
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Deepgram TTS failed: {last_error}")

def srt_time(seconds):
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

def main():
    if not API_KEY:
        raise SystemExit("DEEPGRAM_API_KEY is not available in the workflow environment.")
    for tool in ("ffmpeg", "ffprobe"):
        subprocess.run(["bash", "-lc", f"command -v {tool} >/dev/null"], check=True)
    WORK.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "ATTRIBUTION_FOREST_WONDERS.txt").write_text(
        "Image credits for The Hidden Wonders of the Forest. All image files are sourced from Wikimedia Commons; licenses and author/source pages are listed below.\n\n",
        encoding="utf-8"
    )
    (ASSETS / "RESEARCH_SOURCES_FOREST_WONDERS.md").write_text(
        "# Botanical research sources\n\n"
        "- Rafflesia arnoldii — Royal Botanic Gardens, Kew: https://www.kew.org/plants/rafflesia-arnoldi\n"
        "- Titan arum — Royal Botanic Gardens, Kew: https://www.kew.org/plants/titan-arum\n"
        "- Carnivorous plants and pitcher plants — Kew: https://www.kew.org/read-and-watch/carnivorous-plants\n"
        "- Nepenthes rajah — Kew Plants of the World Online: https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:603791-1/general-information\n"
        "- Strangler fig life cycle — NSW National Parks rainforest plant adaptations: https://www.nationalparks.nsw.gov.au/~/media/Visitor/Files/PDF/education/rainforests-of-nsw/rainforest-plant-adaptations.ashx\n"
        "- Mimosa pudica — Indiana University Biology Greenhouse: https://greenhouse.biology.indiana.edu/features/fun-plants/Mimosa-pudica.html\n"
        "- Telegraph plant — University of Connecticut Plant View: https://bcmapp.dev.i3.uconn.edu/plants/info/199800023\n",
        encoding="utf-8"
    )
    print("STEP 1/5 — Searching and licensing 15 distinct botanical images...")
    used_hashes = set()
    scene_images = []
    for i, scene in enumerate(STORY, 1):
        source = fetch_commons_image([scene["search"]] + scene.get("search_alt", []), i, used_hashes, scene.get("commons_title"))
        scene_images.append(prepare_image(source, i, scene["plant"]))
        time.sleep(0.35)

    print("STEP 2/5 — Generating narration with Deepgram Aura-2...")
    raw_audio = []
    raw_durations = []
    line_records = []
    counter = 0
    for scene_index, scene in enumerate(STORY, 1):
        scene_lines = []
        for line_index, (en, mm) in enumerate(scene["lines"], 1):
            counter += 1
            raw = WORK / f"raw_{counter:03d}.mp3"
            deepgram_tts(en, raw)
            duration = probe_duration(raw)
            raw_audio.append(raw)
            raw_durations.append(duration)
            record = {"scene": scene_index, "line": line_index, "en": en, "mm": mm, "raw": raw}
            line_records.append(record)
            scene_lines.append(record)
            print(f"Deepgram line {counter:02d}: {duration:.2f}s")
        scene["_records"] = scene_lines

    raw_total = sum(raw_durations)
    tempo = raw_total / TARGET_SECONDS
    if not 0.72 <= tempo <= 1.28:
        raise RuntimeError(f"Narration length needs script adjustment: raw {raw_total:.1f}s; required tempo factor {tempo:.3f} is outside safe range.")
    print(f"Raw narration {raw_total:.1f}s; applying natural pacing factor {tempo:.4f} to target ten minutes.")

    print("STEP 3/5 — Timing every Myanmar subtitle to its exact Deepgram line audio...")
    processed_durations = []
    for idx, record in enumerate(line_records):
        adjusted = WORK / f"timed_{idx+1:03d}.mp3"
        # Apply one consistent tempo factor to every narration line. A per-last-line
        # correction can demand extreme speed changes and break subtitle/audio sync.
        line_tempo = tempo
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(record["raw"]),
             "-af", f"atempo={line_tempo:.8f}", "-c:a", "libmp3lame", "-b:a", "128k", str(adjusted)])
        duration = probe_duration(adjusted)
        record["audio"] = adjusted
        record["duration"] = duration
        processed_durations.append(duration)
    total_audio = sum(processed_durations)
    if abs(total_audio - TARGET_SECONDS) > 1.5:
        raise RuntimeError(f"Audio duration verification failed: {total_audio:.2f}s, expected 600s.")

    # Build subtitle timings and a single continuous narration track.
    srt_entries = []
    cursor = 0.0
    for n, record in enumerate(line_records, 1):
        end = cursor + record["duration"]
        caption = record["mm"].replace("\r", "").strip()
        srt_entries.extend([str(n), f"{srt_time(cursor)} --> {srt_time(end)}", caption, ""])
        cursor = end
    srt_path = WORK / "myanmar_subtitles.srt"
    srt_path.write_text("\n".join(srt_entries), encoding="utf-8-sig")
    concat_audio_list = WORK / "audio_concat.txt"
    concat_audio_list.write_text("".join(f"file '{r['audio'].resolve()}'\n" for r in line_records), encoding="utf-8")
    narration = WORK / "narration_10min.mp3"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_audio_list), "-c:a", "libmp3lame", "-b:a", "128k", str(narration)])

    print("STEP 4/5 — Rendering 2.5D-style moving botanical scenes...")
    scene_video_paths = []
    cursor = 0.0
    for i, scene in enumerate(STORY, 1):
        scene_duration = sum(r["duration"] for r in scene["_records"])
        frames = max(1, int(round(scene_duration * FPS)))
        direction = i % 4
        if direction == 0:
            x_expr = f"(iw-iw/zoom)*(1-on/{frames})"
            y_expr = f"(ih-ih/zoom)*on/{frames}"
        elif direction == 1:
            x_expr = f"(iw-iw/zoom)*on/{frames}"
            y_expr = f"(ih-ih/zoom)*(1-on/{frames})"
        elif direction == 2:
            x_expr = f"(iw-iw/zoom)*on/{frames}"
            y_expr = f"(ih-ih/zoom)*on/{frames}"
        else:
            x_expr = f"(iw-iw/zoom)*(1-on/{frames})"
            y_expr = f"(ih-ih/zoom)*(1-on/{frames})"
        clip = WORK / f"visual_{i:02d}.mp4"
        vf = (
            "scale=900:1600:force_original_aspect_ratio=increase,crop=900:1600,"
            f"zoompan=z='min(zoom+0.000055,1.08)':x='{x_expr}':y='{y_expr}':d=1:s=720x1280:fps=24,"
            "fade=t=in:st=0:d=0.45,"
            f"fade=t=out:st={max(0.1, scene_duration-0.45):.3f}:d=0.45,format=yuv420p"
        )
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "24",
             "-i", str(scene_images[i-1]), "-vf", vf, "-t", f"{scene_duration:.4f}",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-r", "24", "-threads", "2", str(clip)])
        scene_video_paths.append(clip)
        cursor += scene_duration
        print(f"Visual scene {i:02d}/{len(STORY)} — {scene['plant']} — {scene_duration:.1f}s")

    concat_video_list = WORK / "video_concat.txt"
    concat_video_list.write_text("".join(f"file '{p.resolve()}'\n" for p in scene_video_paths), encoding="utf-8")
    joined_video = WORK / "joined_visuals.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_video_list), "-c", "copy", "-movflags", "+faststart", str(joined_video)])

    brand = make_brand()
    # Render a 16:9 auto thumbnail from the Rafflesia scene, with the new minimal brand.
    hero = Image.open(scene_images[1]).convert("RGB")
    iw, ih = hero.size
    ratio = 16 / 9
    if iw / ih < ratio:
        nh = int(iw / ratio)
        top = max(0, (ih - nh) // 2)
        hero = hero.crop((0, top, iw, top + nh))
    else:
        nw = int(ih * ratio)
        left = max(0, (iw - nw) // 2)
        hero = hero.crop((left, 0, left + nw, ih))
    hero = hero.resize((1280, 720), Image.Resampling.LANCZOS).convert("RGBA")
    shade = Image.new("RGBA", hero.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rectangle((0, 420, 1280, 720), fill=(0, 0, 0, 165))
    hero.alpha_composite(shade)
    hd = ImageDraw.Draw(hero)
    hd.text((55, 465), "THE HIDDEN WONDERS", font=font(58, True), fill=(255, 255, 246, 255), stroke_width=2, stroke_fill=(0, 0, 0, 210))
    hd.text((58, 535), "OF THE FOREST", font=font(48, True), fill=(225, 205, 150, 255), stroke_width=2, stroke_fill=(0, 0, 0, 210))
    brand_thumb = Image.open(brand).convert("RGBA").resize((240, 90), Image.Resampling.LANCZOS)
    hero.alpha_composite(brand_thumb, (990, 24))
    hero.convert("RGB").save(THUMB, quality=94, optimize=True)

    print("STEP 5/5 — Burning Padauk Myanmar subtitles and final G.I branding...")
    subtitle_filter = (
        f"subtitles=filename='{srt_path.as_posix()}':fontsdir='/usr/share/fonts/truetype/padauk':"
        "force_style='FontName=Padauk,FontSize=24,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=100'"
    )
    filter_complex = f"[0:v]{subtitle_filter}[sub];[sub][2:v]overlay=24:24:format=auto[v]"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined_video),
         "-i", str(narration), "-i", str(brand), "-filter_complex", filter_complex,
         "-map", "[v]", "-map", "1:a:0", "-t", f"{TARGET_SECONDS:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-maxrate", "1800k", "-bufsize", "3600k", "-pix_fmt", "yuv420p",
         "-r", "24", "-threads", "2", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(VIDEO)])
    meta = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,width,height,r_frame_rate:format=duration,size",
        "-of", "json", str(VIDEO)
    ], text=True))
    duration = float(meta["format"]["duration"])
    if not 598.5 <= duration <= 601.5:
        raise RuntimeError(f"Final video duration check failed: {duration:.2f}s")
    if (W, H) != (720, 1280):
        raise RuntimeError("Unexpected output dimensions")
    print(json.dumps({
        "status": "SUCCESS",
        "video": str(VIDEO),
        "thumbnail": str(THUMB),
        "duration_seconds": round(duration, 2),
        "video_size_mb": round(int(meta["format"]["size"]) / 1024 / 1024, 2),
        "resolution": "720x1280",
        "fps": "24",
        "tts": f"Deepgram {TTS_MODEL}",
        "subtitle_font": "Padauk",
        "subtitle_alignment": "per-line measured audio duration"
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
