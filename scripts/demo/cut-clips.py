"""Cut short per-slide clips for the pitch deck out of the finished version B (run after `assemble.py B`).

Clip boundaries come from out/edit/B/timeline.json, so they follow any re-cut of B. Each clip is re-encoded (exact
frame cuts), gets a short fade in and out, BT.709 tags like the masters, and a silent audio track.

    FFMPEG=/path/to/ffmpeg python3 cut-clips.py
"""

import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MASTER = ROOT / "deliverables" / "demo" / "misja-aed-demo-B-kryteria-jury.mp4"
OUT = ROOT / "deliverables" / "demo" / "clips"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FADE = 0.4

# The pitch deck's build (make-aed.sh, AED_CLIP_MAP) picks clips by these names: keep them stable.
# file name → (first timeline item, last timeline item), by position in B's timeline (see assemble.py VERSIONS["B"])
CLIPS = {
    "01-mieszkaniec-najblizszy-aed": (2, 3),  # citizen search on desktop and phone
    "02-dane-gov-pl-import-xml": (5, 5),  # portal admin: new XML source, XSD validation, import OK
    "03-dane-gov-pl-harvester-xml": (6, 6),  # harvester.xml, CSV metadata, API
    "04-dane-gov-pl-portal-publiczny": (7, 7),  # public portal: dataset, table, map
    "05-dane-gov-pl-caly-rozdzial": (5, 8),  # the four in one clip (with the DGA list)
    "06-wzorcowy-zakres-xlsx": (10, 10),  # the xlsx template sheet by sheet
    "07-klasyfikacja-ai-na-zywo": (12, 13),  # live AI classification, then the AI-read floor with provenance
    "08-znak-i-haslo": (16, 16),  # brand reel: mark, slogan, brand book, sticker
    "09-dane-gov-pl-wykaz-chronionych-danych": (8, 8),  # DGA: second dataset in harvester.xml, rows in the portal's table
}


def main():
    timeline = json.loads((HERE / "out" / "edit" / "B" / "timeline.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (first, last) in CLIPS.items():
        start = timeline[first]["at"]
        end = timeline[last]["at"] + timeline[last]["dur"]
        d = end - start
        target = OUT / f"{name}.mp4"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{start:.2f}", "-i", str(MASTER), "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-t", f"{d:.2f}", "-map", "0:v", "-map", "1:a",
                        "-vf", f"fade=t=in:st=0:d={FADE},fade=t=out:st={d - FADE:.2f}:d={FADE}",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-color_range", "tv", "-c:a", "aac", "-b:a", "64k", "-shortest",
                        "-movflags", "+faststart", str(target)], check=True)
        print(f"{target.name:42s} {start:6.1f}–{end:6.1f}  {d:5.1f}s  ({timeline[first]['item']}…{timeline[last]['item']})")


if __name__ == "__main__":
    main()
