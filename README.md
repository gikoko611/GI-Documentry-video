# G.I KO KO — FORBIDDEN FOREST
**Version:** 0.0.1

A five-minute fictional jungle-mystery short documentary for Facebook Reels.

## Output
- 720 × 1280 (9:16), 24 fps
- English AI narration (Microsoft Edge TTS, voice: en-US-GuyNeural)
- Bilingual subtitles: English + Myanmar
- Original G.I KO KO logo overlay
- H.264 MP4 + AAC audio, bitrate-limited for a compact file
- Target duration: 5:00; target size: under 50 MB (actual size depends on encoding)

## Build on GitHub Actions
1. Open the **Actions** tab.
2. Enable Actions if GitHub asks.
3. Run **Build Forbidden Forest Reel** using **Run workflow**.
4. Download the **forbidden-forest-reel** artifact after the run succeeds.

A push to `main` also starts the workflow automatically.

## Local build
Requires Python 3.11+, FFmpeg, and fonts with Myanmar glyph support.

```bash
python -m pip install -r requirements.txt
python render_forbidden_forest.py
```

The MP4 is written to `output/forbidden_forest_gi_koko_720x1280.mp4`.

## Story note
This is an original fictional mystery. It does not claim that the depicted forest, expedition, research camp, or events are real. Reusable Wikimedia Commons images are credited in `assets/ATTRIBUTION.txt`.

## Brand
An original G.I KO KO badge is generated in code because no separate logo image was supplied for this new project. Replace `assets/gi_logo.png` with your approved logo if desired.
