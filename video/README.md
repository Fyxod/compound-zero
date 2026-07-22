# Compound Zero video production guide

Use `live_production.json` for the current 03:40 sentence-level narration and live-capture edit. `docs/demo-video-script.md` and `docs/demo-storyboard.md` retain the written narrative and choreography. This folder is the landing place for recording assets and final exports; do not commit large raw captures unless repository policy explicitly allows it.

## Suggested asset layout

```text
video/
  captures/          # lossless or high-bitrate screen plates
  audio/             # narration, licensed music, UI accents
  edit/              # editor project and generated graphics
  exports/
    compound-zero-demo-under-50mb.mp4
    compound-zero-demo-drive-1440p.mp4
    compound-zero-live-demo-drive-1440p.mp4
  README.md
```

## Generated live master

The primary Drive deliverable is `exports/compound-zero-live-demo-drive-1440p.mp4`. It is assembled from real browser-driven screen recordings: replay controls, the causal-evidence view, response studio, bounded-intelligence approvals, model evidence and the safety case. The persistent top strip discloses simulated data, prototype status and the lack of field validation. The submission master burns in concise sentence-level subtitles, with matching SRT and WebVTT files available as accessibility tracks.

```powershell
python .\video\scripts\generate_live_audio.py --force
python .\video\scripts\assemble_live_video.py --force
```

Narration is generated as one audio asset per complete sentence. Leading and trailing TTS padding is removed, then editorially chosen pauses vary from 180 to 874 ms according to meaning and scene rhythm. Automated silence detection must report no one-second-or-longer gap during the narrated programme. The result writes sentence-aligned SRT and WebVTT files and burns them into the submission master. Use `--no-burn-captions` only for a separately labelled uncaptioned derivative.

## Capture specification

- Record a clean browser viewport at **2560×1440, 60 fps**, OS scaling 100%, browser zoom 100%. Deliver at 30 fps; 60 fps capture keeps native motion and cursor moves smooth during reframing.
- Capture with OBS in **MKV** using NVENC/AMF/Quick Sync H.264 at CQP/CQ 16–20, then remux to MP4. Record the microphone separately as 48 kHz / 24-bit WAV.
- Close bookmarks, downloads, password managers, notifications, devtools, and unrelated apps. Use a fresh browser profile with no personal avatar or saved credentials.
- Use a 2560×1440 product capture rather than browser-level zoom. The interface is dense; downsampling into the 1080p submission export preserves text better.
- Record each page as a 10–20 second clean plate plus the action take. Capture the deterministic replay at least three times.
- Record narration after the picture timing is locked, then make only sub-second picture trims to preserve the exact 03:40 runtime.

## Edit master

- Timeline: **2560×1440, 30 fps, 48 kHz**, exactly 03:40:00.
- Working master: ProRes 422, DNxHR HQ, or visually lossless H.264/H.265.
- Color: Rec.709 / gamma 2.4. Do not crush the app's dark gray detail.
- Narration: target −16 LUFS integrated and −1 dBTP. Duck music 8–12 dB under speech; verify on laptop speakers and inexpensive earbuds.
- Burn concise, sentence-level captions into the primary master and provide matching WebVTT/SRT accessibility tracks alongside it.

## Submission export under 50 MB

The **1440p Drive-quality export is the primary judged deliverable**. Create an under-50 MiB upload copy only after side-by-side QA confirms that small UI text, the disclosure strip and metric qualifiers remain readable. If that copy visibly compromises the presentation, submit the Drive link and keep the form upload optional; do not degrade the master merely to cross the 50 MiB boundary.

For a 220-second film, a 1,450 kb/s video stream plus 96 kb/s audio targets roughly 42.5 MB before container overhead, leaving a safe margin below 50 MB. Export 1920×1080 at 30 fps, H.264 High Profile, 4:2:0, AAC audio, and progressive scan.

PowerShell / FFmpeg two-pass example:

```powershell
ffmpeg -y -i .\video\exports\compound-zero-master-1440p.mov `
  -vf "scale=1920:1080:flags=lanczos,fps=30" `
  -c:v libx264 -preset slow -profile:v high -pix_fmt yuv420p `
  -b:v 1450k -maxrate 1900k -bufsize 2900k -pass 1 -an -f mp4 NUL

ffmpeg -y -i .\video\exports\compound-zero-master-1440p.mov `
  -vf "scale=1920:1080:flags=lanczos,fps=30" `
  -c:v libx264 -preset slow -profile:v high -pix_fmt yuv420p `
  -b:v 1450k -maxrate 1900k -bufsize 2900k -pass 2 `
  -c:a aac -b:a 96k -ar 48000 -movflags +faststart `
  .\video\exports\compound-zero-demo-under-50mb.mp4
```

Validate size, duration, streams, and decode:

```powershell
$videoPath = Resolve-Path .\video\exports\compound-zero-demo-under-50mb.mp4
$sizeMiB = (Get-Item -LiteralPath $videoPath).Length / 1MB
"Size: {0:N2} MiB" -f $sizeMiB
ffprobe -v error -show_entries format=duration,size -show_streams -of json $videoPath
ffmpeg -v error -i $videoPath -f null NUL
```

If the file exceeds 49 MiB, lower video bitrate to 1,350 kb/s and repeat both passes. Do not shorten the disclosure or remove metric qualifiers to save time.

## Drive-quality export

Export `compound-zero-demo-drive-1440p.mp4` at 2560×1440, 30 fps, H.264 High Profile, `-crf 18 -preset slow`, AAC 192 kb/s, and `-movflags +faststart`. This version will usually be several hundred MB and preserves small UI type better. Upload it to Drive, set access to **Anyone with the link — Viewer**, test the link in a signed-out/incognito window, and copy the final share URL into the optional form field.

```powershell
ffmpeg -y -i .\video\exports\compound-zero-master-1440p.mov `
  -vf "scale=2560:1440:flags=lanczos,fps=30" `
  -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p `
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart `
  .\video\exports\compound-zero-demo-drive-1440p.mp4
```

## Thumbnail

- Canvas: **1280×720**.
- Background: the alert-state Replay twin, blurred 2–3 px and darkened 35%, with the fused-risk ring and four worker markers still recognizable.
- Foreground left: Compound Zero mark and `COMPOUND ZERO`.
- Main copy, no more than five words: **BEFORE THE ALARM**.
- Supporting chip: `0 LEGACY ALARMS · COMPOUND RISK FOUND`.
- Bottom disclosure: `SIMULATED PROTOTYPE`.
- Avoid tiny benchmark numbers in the thumbnail; they will not survive mobile display.

## Final acceptance checklist

- [ ] Runtime is 03:35–03:45 and target export is exactly 03:40.
- [ ] The 1440p Drive master opens from beginning to end and contains H.264 video plus AAC audio; an under-50 MiB copy is accepted only if side-by-side QA shows no material readability loss.
- [ ] Drive link works for a signed-out viewer without requesting access.
- [ ] Persistent simulated-data disclosure is readable from 00:12 through the final product montage and repeated on the end card.
- [ ] The cut includes the model's first T+09 warning with 13 minutes to simulated harmful-state onset, then a distinct T+18 compound-risk state with four minutes remaining.
- [ ] No caption or narration claims a later device alarm; the recorded scenario keeps every individual device alarm clear.
- [ ] ScenarioBench metrics match `artifacts/metrics.json` exactly.
- [ ] No claim of field performance, certification, autonomous control, or causal proof appears.
- [ ] No personal data, keys, local paths, notifications, or unlicensed media appears.
- [ ] Captions are spell-checked, including “ScenarioBench,” “counterfactual,” “calibrated,” and “pseudonymized.”
- [ ] Watch once muted for visual clarity, once audio-only for narrative clarity, and once on a phone at 720p.
