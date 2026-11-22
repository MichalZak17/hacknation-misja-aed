"""Cut the scene recordings into the demo videos (several versions from the same footage).

Reads out/<scene>.mkv + out/<scene>.json (marks written by lib.mjs). Each version is a list of items: a title card, or a
window of one recording with its own chapter chip, speed ranges, zooms and caption placement. Captions come from the
marks (rendered from card.html), with the corrections in CAPTION_FIX applied everywhere.

    FFMPEG=/path/to/ffmpeg python3 assemble.py            # every version
    FFMPEG=/path/to/ffmpeg python3 assemble.py A C        # some versions
    python3 assemble.py --marks                           # mark times per recording

Times are seconds from the first frame of that recording. Output: ../../deliverables/demo/<file>.mp4 (1080p master)
and out/previews/<file>-720p.mp4 (small copy for phones).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DELIVER = HERE.parent.parent / "deliverables" / "demo"
PREVIEWS = OUT / "previews"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FPS = 30
FADE = 0.3

SCENES = ["citizen", "sync", "admin", "portal-admin", "portal", "brand", "scope", "compliance", "onboard", "night",
          "story", "dga"]

# Captions recorded with a claim that turned out wrong or vague: original text → (text, sub). None keeps the original.
CAPTION_FIX = {
    "6 źródeł, każde w innym formacie": ("6 źródeł, każde z własnymi kolumnami",
                                         "OpenStreetMap, Warszawa, Krosno, Legionowo, Marki, Przemyśl · CSV i GeoJSON"),
    "Eksport do dane.gov.pl": (None, "CSV, GeoJSON, JSON, JSON-LD, API i plik XML harwestera"),
    "Na telefonie: jeden przycisk i najbliższe AED": (None, "WCAG 2.2 AA, „Zadzwoń 112” na samej górze"),
    "Obrócone o 90° serce z dwóch części, które się nie domykają": (
        "„<3” obrócone o 90°: serce z dwóch części, które się nie domykają", None),
    "Kolory z kontrastem WCAG i niedozwolone użycia znaku": (
        "Kolorystyka i niedozwolone użycia znaku", "kontrast kolorów sprawdzony z WCAG 2.2, opisany w księdze"),
    "Naklejka na szafkę AED: „Ten AED jest na dane.gov.pl”": (None, "kod QR prowadzi do mapy Misji AED"),
    "Nowy dysponent dołącza w kilka minut": ("Nowy dysponent dołącza bez programowania", None),
}

SYNC_ZOOM = [(36.0, 50.6, (190, 560, 924, 520))]  # the model's live answers
SYNC_TOP = [(34.0, 50.6)]
ADMIN_ZOOM = [(22.6, 26.0, (192, 380, 1100, 619))]  # floor "4 · AI z opisu"
XML_ZOOM = (0, 0, 1200, 675)
DGA_TOP = [(9.0, 15.3)]  # keep the containsProtectedData line visible under the caption
DGA_ZOOM = [(6.0, 15.3, (0, 160, 1120, 630)), (28.5, 999, (300, 280, 1280, 720))]  # DGA dataset in the XML; the table
ONBOARD_ZOOM = [(8.3, 27.5, (600, 260, 1100, 619))]  # the "Dodaj dysponenta" dialog


def crit(w, t, s, d=2.6):
    return {"card": {"kind": "criterion", "w": w, "t": t, "s": s}, "dur": d}


def section(n, t, s, d=2.5):
    return {"card": {"kind": "section", "n": n, "t": t, "s": s}, "dur": d}


INTRO = {"card": {"kind": "intro"}, "dur": 3.5}
OUTRO = {"card": {"kind": "outro"}, "dur": 4.5}

VERSIONS = {
    # The walkthrough asked for: citizen → manual sync with live AI → admin → reference scope → dane.gov.pl import →
    # public portal.
    "A": {
        "file": "misja-aed-demo-A-pelna-sciezka",
        "title": "A · Pełna ścieżka",
        "items": [
            INTRO,
            {"scene": "citizen", "from": 4.3, "to": 46.0, "chip": "1 · Mieszkaniec"},
            {"scene": "sync", "from": 2.7, "to": 999, "chip": "2 · Synchronizacja i klasyfikacja AI",
             "speeds": [(4.0, 12.0, 2.5)], "mark_speed": {10: 16}, "zoom": SYNC_ZOOM, "caption_top": SYNC_TOP},
            {"scene": "admin", "from": 5.5, "to": 37.9, "chip": "3 · Panel dysponenta", "zoom": ADMIN_ZOOM},
            {"scene": "scope", "from": 2.5, "to": 16.5, "chip": "4 · Wzorcowy zakres danych"},
            section("PUBLIKACJA", "dane.gov.pl", "Portal sam pobiera nasz zbiór, codziennie."),
            {"scene": "portal-admin", "from": 2.8, "to": 999, "chip": "5 · dane.gov.pl · import XML",
             "speeds": [(9.6, 35.0, 1.6)]},
            {"scene": "portal", "from": 8.0, "to": 999, "chip": "6 · dane.gov.pl · portal"},
            {"scene": "dga", "from": 3.1, "to": 999, "chip": "7 · dane.gov.pl · wykaz chronionych danych", "zoom": DGA_ZOOM, "caption_top": DGA_TOP},
            OUTRO,
        ],
    },
    # Chapters follow the jury's criteria and their weights.
    "B": {
        "file": "misja-aed-demo-B-kryteria-jury",
        "title": "B · Kryteria oceny",
        "items": [
            {**INTRO, "dur": 3.0},
            crit("15%", "Zgodność z tematem", "Gdzie jest najbliższy AED, czy jest teraz dostępny i czy działa?"),
            {"scene": "citizen", "from": 4.3, "to": 26.5, "chip": "15% · Zgodność z tematem wyzwania"},
            {"scene": "citizen", "from": 35.0, "to": 46.0, "chip": "15% · Zgodność z tematem wyzwania"},
            crit("30%", "Zgodność z dane.gov.pl", "Import XML, walidacja schematem portalu, codzienne wersje, wykaz chronionych danych (DGA)."),
            {"scene": "portal-admin", "from": 2.8, "to": 70.0, "chip": "30% · Zgodność z zasadami dane.gov.pl",
             "speeds": [(8.8, 35.0, 2.0), (35.0, 46.1, 1.3)]},
            {"scene": "compliance", "from": 2.4, "to": 14.0, "chip": "30% · Zgodność z zasadami dane.gov.pl",
             "zoom": [(2.4, 14.0, XML_ZOOM)]},
            {"scene": "portal", "from": 8.0, "to": 999, "chip": "30% · Zgodność z zasadami dane.gov.pl",
             "speeds": [(8.0, 46.0, 1.35)]},
            {"scene": "dga", "from": 3.1, "to": 999, "chip": "30% · Zgodność z zasadami dane.gov.pl", "zoom": DGA_ZOOM, "caption_top": DGA_TOP,
             "speeds": [(3.1, 15.3, 1.2)]},
            crit("10%", "Wzorcowy zakres danych", "59 pól, 3 poziomy, słowniki wartości: jeden format dla wszystkich."),
            {"scene": "scope", "from": 2.5, "to": 999, "chip": "10% · Wzorcowy zakres danych",
             "speeds": [(3.1, 32.6, 1.4)]},
            crit("15%", "Kreatywność i innowacyjność", "Lokalny model AI czyta opisy ze źródeł. Każde pole ma znane pochodzenie."),
            {"scene": "sync", "from": 26.0, "to": 999, "chip": "15% · Kreatywność i innowacyjność",
             "mark_speed": {10: 24}, "zoom": SYNC_ZOOM, "caption_top": SYNC_TOP},
            {"scene": "admin", "from": 18.0, "to": 26.5, "chip": "15% · Kreatywność i innowacyjność", "zoom": ADMIN_ZOOM},
            {"scene": "admin", "from": 31.0, "to": 37.9, "chip": "15% · Kreatywność i innowacyjność"},
            crit("25%", "Logotyp i hasło", "Otwarte AED. Pokaż AED, zanim ktoś będzie go szukał."),
            {"scene": "brand", "from": 3.0, "to": 999, "chip": "25% · Logotyp i hasło", "speeds": [(18.0, 30.6, 1.3)]},
            OUTRO,
        ],
    },
    # Story first: the brief's Warsaw story, the night search on a phone, then how the data got there, the portal and
    # the campaign that brings more data holders in.
    "C": {
        "file": "misja-aed-demo-C-historia-ratunku",
        "title": "C · Historia ratunku",
        "items": [
            {"scene": "story", "from": 2.7, "to": 999, "captions": False},
            {"scene": "night", "from": 5.2, "to": 999, "captions": False},
            section("SKĄD TO WIEMY", "Dane z 6 źródeł", "Jeden rekord na urządzenie. AI czyta opisy, człowiek decyduje."),
            {"scene": "sync", "from": 27.0, "to": 999, "chip": "Dane z 6 źródeł · klasyfikacja AI",
             "mark_speed": {10: 18}, "zoom": SYNC_ZOOM, "caption_top": SYNC_TOP},
            {"scene": "admin", "from": 18.0, "to": 26.5, "chip": "Jeden rekord · znane pochodzenie", "zoom": ADMIN_ZOOM},
            section("PUBLIKACJA", "dane.gov.pl", "Portal sam pobiera nasz zbiór, codziennie."),
            {"scene": "portal-admin", "from": 2.8, "to": 999, "chip": "dane.gov.pl · import XML",
             "speeds": [(8.8, 35.4, 2.2), (35.4, 46.1, 1.4)]},
            {"scene": "portal", "from": 8.0, "to": 999, "chip": "dane.gov.pl · portal", "speeds": [(8.0, 46.0, 1.2)]},
            {"scene": "dga", "from": 3.1, "to": 999, "chip": "dane.gov.pl · wykaz chronionych danych", "zoom": DGA_ZOOM, "caption_top": DGA_TOP,
             "speeds": [(3.1, 15.3, 1.2)]},
            section("KAMPANIA", "Otwarte AED", "Zaproszenie dla każdego dysponenta: opublikuj swoje AED."),
            {"scene": "brand", "from": 3.0, "to": 18.0, "chip": "Otwarte AED · znak i hasło"},
            {"scene": "brand", "from": 30.0, "to": 999, "chip": "Otwarte AED · znak i hasło"},
            {"scene": "scope", "from": 2.5, "to": 10.4, "chip": "Otwarte AED · wzorcowy zakres danych"},
            {"scene": "onboard", "from": 5.4, "to": 999, "chip": "Otwarte AED · nowy dysponent", "speeds": [(5.4, 30.0, 1.3)],
             "zoom": ONBOARD_ZOOM},
            OUTRO,
        ],
    },
}


def run(args, **kw):
    subprocess.run(args, check=True, **kw)


def video_start(path):
    """Timestamp of the first frame (the recordings keep wall-clock timestamps)."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    for part in r.stderr.split(","):
        if part.strip().startswith("start:"):
            return float(part.split(":")[1])
    raise RuntimeError(f"no start time in {path}")


_loaded = {}


def load(name):
    if name not in _loaded:
        mkv = OUT / f"{name}.mkv"
        start = video_start(mkv)
        end = os.path.getmtime(mkv) - start - 0.4
        marks = [{**m, "t": m["t"] - start} for m in json.loads((OUT / f"{name}.json").read_text())["marks"]]
        _loaded[name] = (mkv, end, marks)
    return _loaded[name]


def segments(item, end, marks):
    """Intervals of the recording to keep, each with (start, end, speed, crop)."""
    t0, t1 = max(0.0, item["from"]), min(end, item["to"])
    cuts, open_cut = list(item.get("cuts", [])), None
    for m in marks:
        if m.get("cut") == "start":
            open_cut = m["t"]
        elif m.get("cut") == "end" and open_cut is not None:
            cuts.append((open_cut, m["t"]))
            open_cut = None
    speed_marks = [(m["t"], item.get("mark_speed", {}).get(m["speed"], m["speed"]))
                   for m in marks if m.get("speed") is not None]
    ranges = item.get("speeds", [])
    zooms = item.get("zoom", [])
    points = {t0, t1}
    points.update(t for c in cuts for t in c)
    points.update(t for t, _ in speed_marks)
    points.update(t for r in ranges for t in r[:2])
    points.update(t for z in zooms for t in z[:2])
    points = sorted(p for p in points if t0 <= p <= t1)

    def attrs(t):
        if any(a <= t < b for a, b in cuts):
            return None
        speed = 1.0
        for mt, sp in speed_marks:
            if mt <= t:
                speed = sp
        for a, b, sp in ranges:
            if a <= t < b:
                speed = sp
        crop = next((z[2] for z in zooms if z[0] <= t < z[1]), None)
        return speed, crop

    segs = []
    for a, b in zip(points, points[1:]):
        if b - a < 0.05:
            continue
        at = attrs((a + b) / 2)
        if at is None:
            continue
        if segs and segs[-1][2:] == at and abs(segs[-1][1] - a) < 1e-6:
            segs[-1] = (segs[-1][0], b, *at)
        else:
            segs.append((a, b, *at))
    return segs


def out_time(segs, t):
    """Where recording time t lands in the edited clip."""
    acc = 0.0
    for a, b, sp, _ in segs:
        if t < a:
            return acc
        if t <= b:
            return acc + (t - a) / sp
        acc += (b - a) / sp
    return acc


def render_cards(jobs, work):
    if not jobs:
        return
    path = work / "cards.json"
    path.write_text(json.dumps(jobs, ensure_ascii=False))
    run(["node", str(HERE / "render-cards.mjs"), str(path)], cwd=HERE, stdout=subprocess.DEVNULL)


def captions(item, segs, marks, end):
    """(text, sub, start, stop) in clip time for every caption that overlaps the kept footage."""
    caps = [m for m in marks if "cap" in m]
    out = []
    for i, m in enumerate(caps):
        if not m["cap"]:
            continue
        stop_rec = caps[i + 1]["t"] if i + 1 < len(caps) else end
        a, b = max(m["t"], item["from"]), min(stop_rec, item["to"])
        if b <= a:
            continue
        s, e = out_time(segs, a), out_time(segs, b)
        if e - s < 0.8:
            continue
        text, sub = m["cap"], m.get("sub") or ""
        fix = CAPTION_FIX.get(text)
        if fix:
            text, sub = fix[0] or text, fix[1] if fix[1] is not None else sub
        top = any(x <= m["t"] < y for x, y in item.get("caption_top", []))
        out.append((text, sub, s + (0.15 if a == m["t"] else 0.0), e, top))
    return out


def encode_scene(item, target, work):
    mkv, end, marks = load(item["scene"])
    segs = segments(item, end, marks)
    parts = []
    for i, (a, b, sp, crop) in enumerate(segs):
        part = work / f"{target.stem}-seg{i:02d}.mp4"
        vf = [f"setpts=(PTS-STARTPTS)/{sp}"]
        if crop:
            x, y, w, h = crop
            vf.append(f"crop={w}:{h}:{x}:{y},scale=1920:1080:flags=lanczos")
        vf.append(f"fps={FPS}")
        run([FFMPEG, "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(mkv), "-vf", ",".join(vf),
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(part)])
        parts.append(part)
    lst = work / f"{target.stem}-parts.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    duration = sum((b - a) / sp for a, b, sp, _ in segs)

    jobs, overlays = [], []
    if item.get("captions", True):
        for k, (text, sub, s, e, top) in enumerate(captions(item, segs, marks, end)):
            png = work / f"{target.stem}-cap{k:02d}.png"
            jobs.append({"file": str(png), "transparent": True, "query": {
                "kind": "caption", "chip": item.get("chip", ""), "t": text, "s": sub, "pos": "top" if top else ""}})
            overlays.append((png, s, e))
    for i, (a, b, sp, _) in enumerate(segs):
        if sp >= 4:
            png = work / f"{target.stem}-speed{i:02d}.png"
            jobs.append({"file": str(png), "transparent": True, "query": {"kind": "speed", "t": f"×{sp:g}"}})
            overlays.append((png, out_time(segs, a), out_time(segs, b)))
    render_cards(jobs, work)

    inputs = ["-f", "concat", "-safe", "0", "-i", str(lst)]
    graph, last = [], "[0:v]"
    for k, (png, s, e) in enumerate(overlays, start=1):
        inputs += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(png)]
        fade_out = max(s, e - 0.25)
        graph.append(f"[{k}:v]format=rgba,fade=t=in:st={s:.3f}:d=0.25:alpha=1,"
                     f"fade=t=out:st={fade_out:.3f}:d=0.25:alpha=1[c{k}]")
        graph.append(f"{last}[c{k}]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'[v{k}]")
        last = f"[v{k}]"
    graph.append(f"{last}fade=t=in:st=0:d={FADE},fade=t=out:st={duration - FADE:.3f}:d={FADE},format=yuv420p,{TO_709}[out]")
    run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]", "-t",
         f"{duration:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         *TAGS_709, str(target)])
    return duration


# Every clip ends with the same BT.709 conversion and tags. Compositing happens in ffmpeg's default (BT.601) matrix;
# without one common set of tags, the card clips (from PNG, tagged sRGB) and the screen clips (untagged) change the
# colour metadata at each join, which resets decoders and can shift colours in some players.
TO_709 = ("scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,"
          "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709")
TAGS_709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def encode_card(item, target, work):
    png = work / f"{target.stem}.png"
    render_cards([{"file": str(png), "query": item["card"]}], work)
    d = item["dur"]
    run([FFMPEG, "-v", "error", "-y", "-loop", "1", "-t", f"{d}", "-i", str(png), "-vf",
         f"fade=t=in:st=0:d={FADE},fade=t=out:st={d - FADE}:d={FADE},format=yuv420p,{TO_709}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "stillimage", *TAGS_709, str(target)])
    return d


def build(key):
    v = VERSIONS[key]
    work = OUT / "edit" / key
    if work.exists():
        for f in work.iterdir():
            f.unlink()
    work.mkdir(parents=True, exist_ok=True)
    clips, timeline, t = [], [], 0.0
    for idx, item in enumerate(v["items"]):
        name = item.get("scene") or f"card-{item['card']['kind']}"
        target = work / f"{idx:02d}-{name}.mp4"
        d = encode_card(item, target, work) if "card" in item else encode_scene(item, target, work)
        clips.append(target)
        timeline.append({"at": round(t, 1), "dur": round(d, 1), "item": name, "chip": item.get("chip", "")})
        t += d
    lst = work / "final.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    DELIVER.mkdir(parents=True, exist_ok=True)
    final = DELIVER / f"{v['file']}.mp4"
    run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-f", "lavfi", "-i",
         "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
         "-shortest", "-movflags", "+faststart", "-metadata", f"title=Misja AED · demo {v['title']}", str(final)])
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    run([FFMPEG, "-v", "error", "-y", "-i", str(final), "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264",
         "-preset", "slow", "-crf", "27", *TAGS_709, "-c:a", "copy", "-movflags", "+faststart",
         str(PREVIEWS / f"{v['file']}-720p.mp4")])
    (work / "timeline.json").write_text(json.dumps(timeline, indent=1, ensure_ascii=False))
    print(f"== {v['title']}: {t:.1f}s → {final.name}")
    for row in timeline:
        print(f"  {int(row['at'] // 60)}:{row['at'] % 60:04.1f}  {row['dur']:5.1f}s  {row['item']:<13} {row['chip']}")
    return t


def main():
    if "--marks" in sys.argv:
        for name in SCENES:
            _, end, marks = load(name)
            print(f"== {name} ({end:.1f}s)")
            for m in marks:
                print(f"  {m['t']:7.1f}  {m.get('cap') or m.get('cut') or 'speed ' + str(m.get('speed'))}")
        return
    keys = [a for a in sys.argv[1:] if a in VERSIONS] or list(VERSIONS)
    for key in keys:
        build(key)


if __name__ == "__main__":
    main()
