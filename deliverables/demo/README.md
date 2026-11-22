# Demo videos for the pitch

Three cuts made from the same live recordings, with different storylines. Each is 1920×1080, 30 fps, H.264, with
Polish captions, no voice-over (you talk over it) and a silent audio track so presentation software accepts it.

| File | Length | Storyline | Pick it when |
|---|---|---|---|
| [misja-aed-demo-A-pelna-sciezka.mp4](misja-aed-demo-A-pelna-sciezka.mp4) | 4:23 | **The full path:** citizen → manual sync with live AI → admin → reference scope → dane.gov.pl import → public portal → list of protected data (DGA) | You narrate the product step by step, as asked: user first, then admin, then the portal |
| [misja-aed-demo-B-kryteria-jury.mp4](misja-aed-demo-B-kryteria-jury.mp4) | 4:25 | **The jury's scorecard:** one chapter per criterion with its weight (15% fit, 30% dane.gov.pl, 10% scope, 15% creativity, 25% logo and slogan) | You want every criterion visibly ticked, including the brand book and the xlsx scope, which A barely shows |
| [misja-aed-demo-C-historia-ratunku.mp4](misja-aed-demo-C-historia-ratunku.mp4) | 3:47 | **The rescue story:** the brief's Warsaw story (AEDs nearby, but in closed buildings) → at night the nearest AED is in a closed building and the app points to the one accessible now → how we know (AI) → dane.gov.pl → the Otwarte AED campaign | You open with emotion and want the most memorable pitch; it leaves a little time to talk |

Everything was recorded on 22.11.2026 between 03:00 and 04:30 against the live systems: `misja-aed.hackstorm.eu` and
the dane.gov.pl test copy at `dane.hackstorm.eu` / `admin.dane.hackstorm.eu`. Nothing is mocked except the visitor's
location (Warszawa Centralna). It was night, so the nearest AED really shows „Teraz zamknięte” and the app really points
to the nearest one open now (nr 3, 73 m, open 24/7). Version C is built on that. Its night scene was re-recorded on
22.11 at 07:15 with the pages' clock fixed at 04:20 (Playwright clock; the app works out "open now" in the browser),
everything else in it live.

## List of protected data (DGA), added 22.11 at 09:15

A and B end their dane.gov.pl part with scene `dga` (A at 3:50, B at 1:52): our `harvester.xml` carries a second
dataset `misja-aed-dga` with `containsProtectedData=true`, and the portal's DGA information point shows our rows in the
nationwide „Wykaz chronionych danych” table, which the portal rebuilds every night. C does not have it yet (not
re-cut for lack of time). The clips below were cut from the previous B and do not include it; `cut-clips.py` already
has the new item numbers and a `09-dane-gov-pl-wykaz-chronionych-danych` clip for the next run.

## Clips for the slides

Cut from B by [scripts/demo/cut-clips.py](../../scripts/demo/cut-clips.py) into [clips/](clips): 1080p, captions
burned in, short fades, silent audio track.

| Clip | Length | In B |
|---|---|---|
| `01-mieszkaniec-najblizszy-aed.mp4` | 33 s | 0:05.6–0:38.8 |
| `02-dane-gov-pl-import-xml.mp4` | 31 s | 0:41.4–1:12.6 |
| `03-dane-gov-pl-harvester-xml.mp4` | 12 s | 1:12.6–1:24.2 |
| `04-dane-gov-pl-portal-publiczny.mp4` | 28 s | 1:24.2–1:51.7 |
| `05-dane-gov-pl-caly-rozdzial.mp4` (02–04 together) | 70 s | 0:41.4–1:51.7 |
| `06-wzorcowy-zakres-xlsx.mp4` | 30 s | 1:54.3–2:24.0 |
| `07-klasyfikacja-ai-na-zywo.mp4` | 48 s | 2:26.5–3:14.2 |
| `08-znak-i-haslo.mp4` | 31 s | 3:23.7–3:54.2 |

The pitch deck embeds clips 01, 05, 07 and 08 by file name, so keep the names stable.

On the portal map (clips 04, 05), the two blue pins near Grodno and Lutsk are real AEDs inside Poland: four in Krynki
(~3 km from the border) and one in the OSP Teletyn fire truck. At country zoom the portal draws a tile with few points
as one large pin, so it seems to cross the border.

## A · Pełna ścieżka (3:55)

| Time | On screen | Say (suggested) |
|---|---|---|
| 0:00 | Title card | Who we are, the challenge |
| 0:03 | **1 · Citizen.** „Pokaż AED w pobliżu mnie” → nearest AED, distance, closed now → nearest open one → where exactly it hangs, hours, access, source → map → only public ones → the same on a phone | The brief's question: where is it, is it accessible now, does it work. No login |
| 0:41 | **2 · Sync + AI.** Login → 6 integrations → Warszawa 19115 (708 records) → „Klasyfikuj ponownie” → live pipeline → close-up of answers → ×16 → result: hours, „Wydaje personel lub ochrona”, „Trzeba zadzwonić” | Sources describe access in prose. A local model (no data leaves our server) turns it into fields; answers are validated, rank below the source's own data and keep provenance |
| 1:43 | **3 · Admin.** Dashboard, completeness → PKiN device: floor „4 · AI z opisu” (close-up) → duplicates | Per-field provenance; people decide duplicates |
| 2:15 | **4 · Reference scope.** The xlsx: template, „Słownik pól” (59 fields, 3 levels) | One format for every data holder |
| 2:28 | Card „dane.gov.pl” | |
| 2:31 | **5 · Portal admin.** New XML data source → portal's own XSD validation passes → institution, daily, active → save → import **OK** | The ministry adds us once; the portal pulls the file daily. Real portal code (mcod) |
| 3:13 | **6 · Public portal.** Search → dataset → CSV as a table (18,821 rows) → portal map | Anyone can find, preview, download, or use the API |
| 3:50 | Outro: URLs, formats, slogan | |

## B · Kryteria oceny (3:59)

Each chapter opens with a 2.6 s card showing the criterion and its weight, and the chip above every caption repeats it.

| Chapter | On screen |
|---|---|
| 15% · Fit with the challenge | Citizen search on desktop (closed → nearest open, details), the phone view |
| 30% · dane.gov.pl compliance | Portal admin: add XML source, XSD validation, import OK → `harvester.xml` close-up (schema 1.13, daily dated versions) → public portal: dataset, table, map |
| 10% · Reference data scope | The xlsx sheet by sheet (template, 59-field dictionary, allowed values, instructions) → the same template published on the portal |
| 15% · Creativity and innovation | Live AI classification (×24) → floor „4 · AI z opisu” → duplicates for a human decision |
| 25% · Logo and slogan | Brand reel: „<3” turns into the Otwarte AED mark, the slogan, brand book pages (idea, construction, clear space and minimum size, variants, colours, misuse), the AED cabinet sticker |

## C · Historia ratunku (3:47)

| Part | On screen |
|---|---|
| Story | „Warszawa, 3 marca. Zawał w centrum miasta.” → „Są w pobliżu, ale w zamkniętych budynkach.” (the brief says „zamknięte na klucz”; in Poland an AED itself is not locked, the building it hangs in is) → „Nie ma kompletnej mapy AED.” → Misja AED |
| Night | Big phone: „Noc, centrum miasta. Ktoś upada.” → „Najbliższy AED w zamkniętym budynku” (inside a kindergarten closed at night) → nearest accessible now, 73 m → „Otwarty całą dobę”, Galeria wschodnia, level −1 → walk there |
| Where the data comes from | Card, then live AI classification and the AI-read floor with provenance |
| dane.gov.pl | Card, then portal admin import (XSD validation, OK) and the public dataset with table and map |
| Otwarte AED | Card, then the logo and slogan, the AED sticker, the xlsx template, and a new data holder in „Dodaj dysponenta” (filled, then cancelled) |

## What the recordings changed on the live systems

- **Misja AED:** run #14 re-classified `warszawa-19115` (647 LLM calls, ~3.5 min of the shared GPU). No integration was
  added: the „Dodaj dysponenta” form was cancelled.
- **dane.gov.pl test copy (mcod):** before the import take, the old XML source (id 5) was deactivated and deleted.
  Deleting a data source makes mcod mark its datasets and resources as permanently removed, so the old dataset 4211
  went with it. The take created **source 7** and **dataset 4214**
  (`/pl/dataset/4214,defibrylatory-aed-w-polsce-zbior-ogolnokrajowy`). The new CSV resource 40222 got the old one's
  column types (house_number „dowolny typ”, teryt as text, lat/lon as map coordinates) and was revalidated, so its table
  and map work. The screenshots in [../screenshots](../screenshots) still show the old ids.

## Re-recording and re-cutting

Scripts: [scripts/demo](../../scripts/demo). Each `scene-*.mjs` drives a headed Chromium on an Xvfb display, recorded
by ffmpeg (x11grab, 30 fps), and writes timed marks (captions, cuts, speed changes). `assemble.py` cuts the versions
from those marks; versions, windows, speeds, zooms and caption corrections are at its top.

```bash
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
cd scripts/demo
export FFMPEG=/path/to/ffmpeg     # needs libx264 and x11grab (e.g. the imageio-ffmpeg static build)
export DEMO_EMAIL=admin@misja-aed.hackstorm.eu DEMO_PASSWORD="$(dokku config:get misja-aed-api ADMIN_PASSWORD)"
python -I gen-scope.py            # out/scope.html from deliverables/wzorcowy-zakres-danych-aed.xlsx (needs openpyxl)
# brand book pages for the reel: render marketing/ksiega-znaku.pdf at 200 dpi to out/brand/p01.png … p12.png (PyMuPDF)
node scene-citizen.mjs; node scene-night.mjs; node scene-story.mjs; node scene-brand.mjs
node scene-scope.mjs; node scene-compliance.mjs; node scene-admin.mjs; node scene-onboard.mjs
CONFIRM=1 node scene-sync.mjs     # starts a real re-classification (~3.5 min of GPU)
SAVE=1 MCOD_SESSION=<local_sessionid> node scene-portal-admin.mjs   # the institution must have no XML source first
node scene-portal.mjs
python3 assemble.py               # all versions; `python3 assemble.py B` for one; `--marks` prints mark times
```

`DRY=1` runs a scene without recording and saves a screenshot per caption into `out/dry-<scene>/`. `scene-night.mjs`
fixes the pages' clock at night (`NIGHT_AT`, default 22.11.2026 04:20), so it can be recorded at any hour. `MCOD_SESSION` is a session
minted in the portal container for `admin@mcod.local` (Django `SessionStore`, cookie `local_sessionid` on
`.dane.hackstorm.eu`), so no portal password is needed or changed. 720p copies for phones land in `out/previews/`.
