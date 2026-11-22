# Otwarte AED: znak kampanii i księga znaku

Kampania zachęcająca dysponentów defibrylatorów (gminy, szkoły, firmy, szpitale, straż, operatorów) do publikowania
danych o AED na dane.gov.pl w jednym, wspólnym formacie. HackNation 2026, wyzwanie „Misja AED – Dane na ratunek”.

| | |
|---|---|
| **Nazwa** | Otwarte AED |
| **Hasło** | Pokaż AED, zanim ktoś będzie go szukał. |
| **Hashtag** | #OtwarteAED |
| **Księga znaku** | [ksiega-znaku.pdf](ksiega-znaku.pdf) (A4, 12 stron) |

## Koncepcja (5 zdań, jak w księdze)

„Otwarte AED” to kampania, która zachęca każdego dysponenta defibrylatora – gminę, szkołę, firmę, szpital, straż – do
opublikowania danych o urządzeniu na dane.gov.pl w jednym, wspólnym formacie. Słowo „otwarte” łączy trzy znaczenia:
otwarte dane, AED dostępne bez zamków i barier oraz otwartość ludzi, którzy dzielą się informacją. Znak to serce
zapisane tak, jak pisze się je w sieci – „<3” obrócone o 90° – złożone z dwóch części, które celowo się nie domykają:
serce zbudowane z danych, otwarte na kolejne wpisy. Iskra w środku przypomina o wyładowaniu, które przywraca rytm, a
czerwień i granat łączą język ratownictwa z językiem danych. Hasło „Pokaż AED, zanim ktoś będzie go szukał” mówi
wprost, po co to robimy: defibrylator, którego nie ma na mapie, nie zdąży pomóc.

## Dlaczego ta nazwa

Rozważane warianty:

| Nazwa | Hasło | Ocena |
|---|---|---|
| **Otwarte AED** (#OtwarteAED) | Pokaż AED, zanim ktoś będzie go szukał. | **wybrana**: trzy znaczenia „otwarte” (otwarte dane, dostępne AED, otwarci ludzie), krótka, działa jako hashtag i na naklejce na szafkę |
| Serce na mapie (#SerceNaMapie) | Twoje AED na mapie, czyjeś serce w rytmie. | ładna, ale nie mówi o danych ani o publikacji; motyw serca-pinezki jest bardzo częsty |
| Dane z serca (#DaneZSerca) | Udostępnij dane. Daj sercu czas. | ciepła, ale ogólna; nie wskazuje AED |
| Pokaż AED (#PokazAED) | Defibrylator, którego nie ma na mapie, nie zdąży pomóc. | mocne wezwanie, ale bez idei, z której da się zbudować znak; weszła do hasła |
| Puls danych (#PulsDanych) | Dane, które przywracają rytm. | nowoczesna, ale abstrakcyjna dla gminy czy szkoły |

Gramatycznie „Otwarte AED” to liczba mnoga („otwarte [defibrylatory] AED”), tak jak „otwarte dane”.

## Paleta

| Kolor | HEX | Rola |
|---|---|---|
| Czerwień Puls | `#E6013A` | podstawowy (ten sam co akcent HackNation w aplikacji) |
| Granat Noc | `#0B1F28` | podstawowy (tekst, podstawa znaku, ciemne tła) |
| Biel | `#FFFFFF` | podstawowy |
| Zieleń Gotowość | `#12B76A` | uzupełniający: tylko status „dostępny / sprawny”, nigdy w znaku |
| Grafit | `#5B6B73` | uzupełniający: tekst pomocniczy |
| Mgła | `#F2F4F5` | uzupełniający: tła |

RGB, CMYK, najbliższe Pantone i tabela kontrastów WCAG są w księdze (s. 7 i 9).

## Pliki

```
ksiega-znaku.pdf                       księga znaku (PDF, A4)
logo/                                  znak i wersja pozioma
  otwarte-aed-poziomy-<wariant>.svg|pdf|png|jpg   znak + nazwa
  otwarte-aed-znak-<wariant>.svg|pdf|png|jpg      sam znak
    warianty: kolor, kolor-ciemne-tlo, czerwony, mono (czarny), negatyw (biały)
    .svg  wzorzec (format otwarty, tekst zamieniony na krzywe, bez fontów)
    .pdf  wektor do druku
    .png  przezroczyste tło, 2048 px szerokości; *-512.png: 512 px
    .jpg  białe tło (kolor-ciemne-tlo i negatyw: tło Granat Noc), 2048 px
  otwarte-aed-znak-favicon.*           znak uproszczony bez iskry, do rozmiarów < 24 px
  favicon.ico, favicon-{16,32,48,180,192}.png
web/                                   kopie SVG do aplikacji (znak, favicon, wersje poziome)
src/
  build_logo.py                        geometria znaku + logotyp na krzywych + eksport PNG/JPG/PDF
  build_book.py                        rysunki konstrukcyjne, przykłady, druk księgi do PDF
  ksiega/ksiega-znaku.html             szablon księgi (HTML + CSS)
  fonts/                               Space Grotesk, Inter, JetBrains Mono + licencje SIL OFL 1.1
  requirements.txt
```

## Jak przebudować

```bash
cd marketing/src
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/playwright install chromium        # jeśli nie ma Chromium dla Playwright 1.49
.venv/bin/python build_logo.py               # logo/*, web/*
.venv/bin/python build_book.py               # ../ksiega-znaku.pdf  (--preview DIR: PNG każdej strony)
```

Znak jest konstruowany, nie rysowany: wszystkie wymiary są wielokrotnością modułu M (grubość linii), znak mieści się
w siatce 9M × 8M, płaty to łuki o promieniu 2M, ramiona podstawy biegną pod 45° stycznie do łuków. Zmiana stałych na
górze `build_logo.py` przebudowuje wszystkie pliki i rysunki w księdze.

## Licencje

Znak, logotyp i księga to oryginalny projekt zespołu (bez elementów stockowych; nie wykorzystuje znaku ISO 7010 / ILCOR
ani logo dane.gov.pl). Kroje pisma: Space Grotesk, Inter, JetBrains Mono, wszystkie na SIL Open Font License 1.1
(teksty licencji w `src/fonts/`); w plikach logo tekst jest zamieniony na krzywe.
