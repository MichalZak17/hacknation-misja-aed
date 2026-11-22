# Research for the presentation

Team research collected on 21.11.2026 from the shared drive (`smb://100.89.5.110/exchange`), plus a check of it
against our own database on 22.11.2026. Use this when building the slides and the pitch. This folder is plain `.md`
on purpose: only `*.mdx` under `docs/` is published on the public docs site.

## Submission rules (HackNation "Wymagania do projektów", all tasks)

- Hard deadline: **Sunday 22.11.2026, 11:00**. Fields and materials can be edited until then.
- Final presentation is uploaded to HackTribe as **PDF, under 10 MB** (error 413 = too big). Larger decks or a deck
  hosted elsewhere (e.g. Canva) and the **link to the working prototype** go into the "additional materials" link field.
  Check that jurors can open every link.
- **Demo video: at most 2 minutes.** Jurors have a few minutes per entry: show the problem, that it works and how to
  check it. "Not just a good mock-up but a solid technical base."
- Task rules (§2.8): the submission **must state how AI was used**.
- Task guide checklist (`sources/misja_aed_przewodnik_hackathon.pdf`): machine-readable exports, reference scope
  (GPS, availability, contact), brand book (HEX/RGB/CMYK, clear space, minimum size, misuse rules, 3–5 sentence
  concept), responsive + WCAG UI, AI-use statement, one person named to sign the copyright transfer (7 days).
  Suggested campaign extra: a sticker for sites, "Tu ratujemy życie – AED zarejestrowane w dane.gov.pl", with a QR code
  to report or update the AED.

## Pitch facts (source: `sources/AED_Norwegia_Dania_UK_research.pdf`)

Mentors named Norway, Denmark and the UK as the models to follow.

| | Norway | Denmark | UK | Poland today |
|---|---|---|---|---|
| Register | Hjertestarterregisteret (NAKOS, state) | Hjertestarter-Netværket (TrygFonden) | The Circuit (BHF + NHS) | none; OSM + local lists |
| AEDs | 11,322 (II 2026) | 26,719 (III 2026), 72% 24/7 | 123,967 (XI 2026) | ~18k in OSM |
| Mandatory registration | no | no | no | no |
| Caretaker contact | yes | yes | yes (guardians) | phone on 25% |
| Freshness | confirm every 6 months, else "inactive" | removed after failed validation | email every 3 months, pad expiry alerts, escalation | none |
| Expiry dates | battery, pads, child pads | pads | pads | none |
| Linked to dispatch | 113 / 110 | 112, all regions | 999, sync every 60 s | unknown |
| Open data / API | OAuth API for partners, ODbL via OSM since 2026 | map only | monthly Excel, no commercial use or public apps | OSM (ODbL) |

Quotable lines:

- **Copenhagen 2019 (Karlsson et al., Resuscitation):** when the nearest AED was accessible at the time of the arrest,
  30-day survival was **28.8%**; when it was locked, **16.4%**. Half (51%) of AEDs in range were inaccessible at the
  time; offices 18% and schools 30% available 24/7. Opening hours are life-saving data.
- **UK:** after the national network launched, **54% of registered AEDs were previously unknown to the ambulance
  service**. Dispatchers sent someone for an AED 113,811 times by end of 2023. 13% of AEDs were "out of service" on the
  day measured.
- **Denmark:** bystander CPR 19% (2001) → 76% (2023); survival 4% → 14%; defibrillation before the ambulance 1.3% → ~11%.
  Volunteers (Hjerteløber) arrive in 3–5 min on average, the ambulance in 8–9 min.
- **Norway:** 20% of patients defibrillated before the ambulance in 2025 (13% in 2018).
- **Our opening:** none of the three publishes its register on a national open-data portal with a public API. Poland on
  dane.gov.pl can be first, and with battery dates from day one (only Norway collects them).

Answers to likely jury questions:

- *Do we need a law?* Not to start: registration is voluntary in all three countries. A duty could apply to AEDs bought
  with public money.
- *Where does the data come from?* OSM import, city registers, public tenders, a campaign to caretakers, later
  manufacturers' connected AEDs (LIFEPAK CR2, ZOLL AED 3 report self-tests over Wi-Fi/4G).
- *How does it stay current?* Quarterly reminders and an automatic "inactive" status, as in the UK and Norway.
- *Personal data?* The UK publishes without caretaker data; we do the same: contact stays in the system, the open
  dataset has the role or institution.

Corrections to things heard on site: Norway's register is run by NAKOS for Helsedirektoratet, not Norsk Luftambulanse
(which made the Hjelp 113 app); Denmark has no mandatory registration law (2026 sources say voluntary); the UK BHF file
is not open data (its terms forbid apps and public maps).

## Checked against our database (22.11.2026, 18,809 active devices)

The research's Polish OSM figures match our snapshot (18,298 OSM nodes), so they are safe to quote:

| Field in OSM | Research | Our snapshot |
|---|---|---|
| manufacturer tagged | 2% | 353 = 1.9% |
| opening_hours | 38% | 37% |
| check_date | 33% | 33% |
| phone | 25% | 24.5% |

Our merged dataset: manufacturer text on 944 devices (5.0%; 708 from Warszawa 19115, 236 from OSM), model on 146
(0.8%), opening hours 39.5%, operator and verified date ~32%. **No source gives serial number, pad or battery expiry,
child mode, self-test or inspection data**: every such field is empty. These are what the caretaker form must collect.

Model catalogue (`sources/AED_Europa_katalog.xlsx`, 56 models with battery and pad lifetimes, child mode, IP, status):

- Brand recognisable on 860 devices, exact catalogue model on **537 (2.9%)**: CU Medical i-PAD SP1 212, Philips FRx 65,
  Philips HS1 65, ZOLL AED Plus 59, ZOLL AED 3 29, HeartSine 350P/360P 15, others below 15.
- **161 of the 537 (30%) are discontinued models** (all Philips: Philips left the AED market in 2024). Usable as a
  readiness-risk line in the pitch.
- 3 OSM entries are "AED trainer XFT-120C" training units mapped as real AEDs.
- Decided not to build a catalogue lookup: it would touch under 3% of devices, and expiry cannot be estimated without
  install or manufacture dates (and dates should come from the label anyway).

Polish market estimate (`sources/AED_udzialy_modeli_Polska.pdf`, from OSM, tenders and shops): Philips 25–32%, ZOLL
18–25%, CU Medical 14–22%, HeartSine 6–10%, LIFEPAK 4–7%, Defibtech 3–6%. New sales lean to cheap models (one shop
2023: i-PAD SP1 ~40%, Amoul i3 ~25%).

## Schema fields the research supports (reference scope, 10%)

Our `Device` model already has battery and pad expiry, pads type, child pads available, child mode, self-test,
inspection, cabinet, seasonal and mobile. Fields the research adds, each backed by a registry or data sheets
(`sources/AED_pola_rejestrow_NO_UK_DK.xlsx` has the full NO/UK/DK field lists):

- child pad expiry date (Norway collects it)
- integrated cartridge flag: HeartSine Pad-Pak has one date for battery and pads
- operating mode: semi-automatic / automatic
- child mode mechanism: key / button / separate pads / separate cartridge (today a yes/no)
- remote monitoring: none / Wi-Fi / GSM
- inspection interval in days (HeartSine 7, default 30) and manufacturer service interval (e.g. Schiller FRED PA-1 every
  3 years)
- visibility: public / dispatcher only; access code never public
- accessibility (from `sources/AED_normy_i_standardy.txt`): step-free access, cabinet height, Braille/tactile signage

Why two dates and not "next inspection": Polish law (medical devices act, Dz.U. 2022 poz. 974, art. 16) forbids using a
device past the manufacturer's safe-use period and sets no fixed inspection interval. Batteries last 4–6 years, pads
2–5 (Philips FRx only 2). Outdoor AEDs need a heated cabinet: operating temperature starts at 0 °C (Mindray, Schiller
from 5 °C).

## Standards worth naming on a slide (`sources/AED_normy_i_standardy.txt`)

DCAT-AP PL (portal metadata), the open data act 2021 and KRI, ISO 8601 dates, WGS84 / EPSG:4326, TERYT and PRG,
ISO/IEC 25012 data quality, **ISO 7010 E010** (the AED sign: keep the logo close to it), ERC 2025 guidelines,
WCAG 2.1 AA / EN 301 549 (digital accessibility act 2019), GDPR (no caretaker personal data in the open set).

Accessibility ideas: status by icon and text, not colour alone; a list as an alternative to the map (we have it);
**link to the Alarm112 app (text reporting) next to "call 112"** for deaf users; walking directions as text.

## Files

`sources/`:

- `AED_Norwegia_Dania_UK_research.pdf`: the NO/DK/UK comparison, schema table, recommendations, pitch lines, sources
- `AED_modele_karty_katalogowe.pdf`: 7 models sold in Poland compared (battery, pads, child mode, connectivity, PLN
  prices), Polish law on inspections, proposed schema fields
- `AED_udzialy_modeli_Polska.pdf`: brand and model share estimate for Poland, OSM field completeness
- `AED_pola_rejestrow_NO_UK_DK.xlsx`: field lists of the Norwegian API, Rogaland dataset, The Circuit and hjertestarter.dk
- `AED_Europa_katalog.xlsx`, `AED_Europa_modele.csv`, `AED_Europa_katalog_README.md`: catalogue of 56 AED models
- `AED_normy_i_standardy.txt`, `normy_pelne_teksty_README.md`: standards list and the index of full texts
- `misja_aed_przewodnik_hackathon.pdf`: task guide with criteria and the submission checklist
- `Norwegia_zrodla_README.md`: Norwegian register sources and API notes

Left on the shared drive (too big or not ours to republish): the 82 manufacturer data sheet PDFs
(`01 - Karty Katalogowe/karty/`, 105 MB), full texts of standards and laws (`01 - Standardy/Wszystkie_normy_pobrane/`,
104 MB), the BHF defibrillator file (27 MB; its terms forbid public apps and maps, analysis only), the Norwegian AEDs
from OSM (ODbL, 2.3 MB), and the scanned HackNation requirements PDF summarised above.
