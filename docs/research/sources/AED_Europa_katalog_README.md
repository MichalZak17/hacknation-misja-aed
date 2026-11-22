# Katalog AED używanych w Europie – karty katalogowe

Hacknation 2026, zadanie 01 „Misja AED”. Stan na 21.11.2026.

**56 modeli** (aktualne i wycofane, ale wciąż wiszące), **82 plików PDF** dla 46 modeli. Dla 10 modeli PDF nie dało się pobrać (sklep blokuje lub brak publicznej karty) – w indeksie jest link.

## Zawartość
- `AED_Europa_katalog.xlsx` – arkusze: **Modele** (wszystkie cechy + kolumny kategorii tak/nie, filtr), **Pliki** (każdy PDF: źródło, URL, strony, MD5), **Podsumowanie** (liczności kategorii), **Legenda**.
- `AED_Europa_modele.csv`, `AED_Europa_pliki.csv` – to samo w CSV (UTF-8, separator `;`).
- `karty/` – PDF-y w układzie `kategoria / producent / model /`.

## Kategorie folderów
```
karty
karty/01_PAD_publiczne_aktualne
karty/01_PAD_publiczne_aktualne/A_M_I_Italia
karty/01_PAD_publiczne_aktualne/Amoul_Ambulanc
karty/01_PAD_publiczne_aktualne/Bexen_Cardio
karty/01_PAD_publiczne_aktualne/CU_Medical_Systems
karty/01_PAD_publiczne_aktualne/Defibtech
karty/01_PAD_publiczne_aktualne/Mediana
karty/01_PAD_publiczne_aktualne/Mindray
karty/01_PAD_publiczne_aktualne/Nihon_Kohden
karty/01_PAD_publiczne_aktualne/Primedic
karty/01_PAD_publiczne_aktualne/Progetti
karty/01_PAD_publiczne_aktualne/Schiller
karty/01_PAD_publiczne_aktualne/Stryker
karty/01_PAD_publiczne_aktualne/ZOLL
karty/02_PAD_publiczne_wycofane_w_uzyciu
karty/02_PAD_publiczne_wycofane_w_uzyciu/CU_Medical_Systems
karty/02_PAD_publiczne_wycofane_w_uzyciu/Cardiac_Science
karty/02_PAD_publiczne_wycofane_w_uzyciu/HeartSine
karty/02_PAD_publiczne_wycofane_w_uzyciu/Philips
karty/02_PAD_publiczne_wycofane_w_uzyciu/Physio_Control
karty/02_PAD_publiczne_wycofane_w_uzyciu/Primedic
karty/03_profesjonalne_i_PAD+EKG_aktualne
karty/03_profesjonalne_i_PAD+EKG_aktualne/Defibtech
karty/03_profesjonalne_i_PAD+EKG_aktualne/GS_corpuls
karty/03_profesjonalne_i_PAD+EKG_aktualne/Mindray
karty/03_profesjonalne_i_PAD+EKG_aktualne/Schiller
karty/03_profesjonalne_i_PAD+EKG_aktualne/Stryker
karty/03_profesjonalne_i_PAD+EKG_aktualne/Weinmann
karty/03_profesjonalne_i_PAD+EKG_aktualne/ZOLL
karty/04_profesjonalne_i_PAD+EKG_wycofane
karty/04_profesjonalne_i_PAD+EKG_wycofane/Philips
karty/04_profesjonalne_i_PAD+EKG_wycofane/Physio_Control
karty/04_profesjonalne_i_PAD+EKG_wycofane/Primedic
karty/04_profesjonalne_i_PAD+EKG_wycofane/Welch_Allyn
karty/04_profesjonalne_i_PAD+EKG_wycofane/ZOLL
```
- **01 / 02** – AED dla laików (PAD), aktualne / wycofane.
- **03 / 04** – modele z EKG, trybem ręcznym lub dla służb, aktualne / wycofane.

Pozostałe kategorie są kolumnami w XLSX: tryb (półautomat/automat), mechanizm dla dzieci, czujnik RKO, łączność (zdalny monitoring), bateria, elektrody, IP, waga, gwarancja.

## Przegląd modeli
| Producent | Model | Status | Kategoria | Tryb | Dzieci bez wymiany elektrod | Czujnik RKO | Zdalny monitoring | IP | Pliki |
|---|---|---|---|---|---|---|---|---|---|
| Philips | HeartStart FRx | Wycofany ze sprzedaży | PAD | Półautomat | tak | nie | nie | IP55 | 2 |
| Philips | HeartStart HS1 / OnSite / Home | Wycofany ze sprzedaży | PAD | Półautomat | nie | nie | nie | IP21 (IP2X + IPX1) | 3 |
| Philips | HeartStart FR3 | Wycofany ze sprzedaży | Profesjonalny AED | Półautomat (opcja override) | tak | nie | nie | IP55 | 1 |
| Philips (też Laerdal HeartStart FR2) | HeartStart FR2 / FR2+ | Wycofany ze sprzedaży | PAD + służby | Półautomat | nie | nie | nie | IP54 | 2 |
| ZOLL | AED Plus | Aktualny | PAD | Półautomat lub automat (osobne wersje) | nie | tak | nie | IP55 | 3 |
| ZOLL | AED 3 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | tak | tak | IP55 | 1 |
| ZOLL | AED 3 BLS | Aktualny | PAD + służby | Półautomat / automat / tryb ręczny (konfig.) | tak | tak | tak | IP55 | 2 |
| ZOLL | AED Pro | Wycofany ze sprzedaży | Profesjonalny AED | Półautomat / tryb ręczny | nie | tak | nie | IP55 | 1 |
| ZOLL (dawniej Cardiac Science) | Powerheart G5 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | nie | tak | nie | IP55 | 2 |
| Cardiac Science (obecnie ZOLL) | Powerheart AED G3 Plus | Wycofany ze sprzedaży | PAD | Półautomat lub automat (osobne wersje) | nie | nie | nie | b.d. | 1 |
| Cardiac Science (obecnie ZOLL) | Powerheart AED G3 | Wycofany ze sprzedaży | PAD | Półautomat lub automat (osobne wersje) | nie | nie | nie | b.d. | 1 |
| Cardiac Science (obecnie ZOLL) | Powerheart AED G3 Pro | Wycofany ze sprzedaży | Profesjonalny AED | Półautomat / tryb ręczny | nie | nie | nie | b.d. | link |
| Stryker (Physio-Control) | LIFEPAK CR2 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | nie | tak | IP55 | 2 |
| Physio-Control (Medtronic/Stryker) | LIFEPAK CR Plus | Wycofany ze sprzedaży | PAD | Półautomat lub automat (osobne wersje) | nie | nie | nie | IPX4 | 1 |
| Physio-Control (Medtronic/Stryker) | LIFEPAK EXPRESS | Wycofany ze sprzedaży | PAD | Półautomat | nie | nie | nie | IPX4 | 1 |
| Stryker (Physio-Control) | LIFEPAK 1000 | Aktualny | Profesjonalny AED | Półautomat (opcja tryb ręczny) | nie | nie | nie | IP55 | 2 |
| Physio-Control (Medtronic) | LIFEPAK 500 | Wycofany ze sprzedaży | PAD + służby | Półautomat | nie | nie | nie | IPX4 | 2 |
| Stryker (HeartSine) | HeartSine samaritan PAD 350P / 360P | Aktualny | PAD | 350P półautomat / 360P automat | nie | nie | tak | IP56 | 3 |
| Stryker (HeartSine) | HeartSine samaritan PAD 450P | Aktualny | PAD | Półautomat | nie | tak | nie | IP56 | 1 |
| Stryker (HeartSine) | HeartSine samaritan PAD 500P | Aktualny | PAD | Półautomat | nie | tak | tak | IP56 | 2 |
| HeartSine (obecnie Stryker) | HeartSine samaritan PAD 300P | Wycofany ze sprzedaży | PAD | Półautomat | nie | nie | nie | IP56 | 1 |
| Defibtech | Lifeline VIEW / VIEW AUTO | Aktualny | PAD | Półautomat lub automat (osobne wersje) | nie | nie | nie | IP55 | 3 |
| Defibtech | Lifeline ECG | Aktualny | Profesjonalny AED | Półautomat + monitor EKG | nie | nie | nie | IP55 | 2 |
| Defibtech | Lifeline PRO | Aktualny | Profesjonalny AED | Półautomat + tryb ręczny (25–200 J) | nie | nie | nie | IP55 | 1 |
| Defibtech | Lifeline AED | Aktualny | PAD | Półautomat | nie | nie | nie | IP54 | 2 |
| Defibtech | Lifeline AUTO | Aktualny | PAD | Automat | nie | nie | nie | IP54 | 2 |
| Mindray | BeneHeart C1A | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | nie | nie | IP55 | 2 |
| Mindray | BeneHeart C2 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | nie | tak | IP55 | 3 |
| Mindray | BeneHeart D1 (Public / Pro) | Aktualny | Profesjonalny AED | Półautomat (Pro: tryb ręczny + EKG 3-kanałowe) | tak | nie | nie | IP55 | 3 |
| Schiller | FRED PA-1 / PA-1 Online | Aktualny | PAD | Automat (też wersja półautomat) | nie | tak | tak | IP55 | 2 |
| Schiller | FRED easyport plus | Aktualny | Profesjonalny AED | Półautomat / tryb ręczny + EKG | nie | tak | tak | IP44 | 2 |
| Schiller | FRED easyport | Wycofany ze sprzedaży | Profesjonalny AED | Półautomat / tryb ręczny | b.d. | nie | nie | b.d. | link |
| Schiller | FRED easy / FRED easy Life | Wycofany ze sprzedaży | PAD + służby | Półautomat lub automat | b.d. | nie | nie | b.d. | link |
| CU Medical Systems | i-PAD CU-SP1 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | nie | nie | IP55 | 2 |
| CU Medical Systems | i-PAD CU-SP2 | Aktualny | PAD + służby | Półautomat (z EKG) | tak | nie | nie | b.d. | link |
| CU Medical Systems | i-PAD NF1200 | Wycofany ze sprzedaży | PAD | Półautomat | b.d. | nie | nie | b.d. | 1 |
| Nihon Kohden | Cardiolife AED-3100 | Aktualny | PAD | Półautomat | tak | nie | nie | IP55/IP66 (zależnie od karty) | 3 |
| Nihon Kohden | Cardiolife AED-2100 / 2150 | Wycofany ze sprzedaży | PAD | Półautomat | b.d. | nie | nie | b.d. | link |
| Nihon Kohden | Cardiolife AED-3150 | Aktualny | PAD | b.d. | b.d. | nie | nie | b.d. | link |
| Primedic (Metrax) | HeartSave AED-M | Wycofany ze sprzedaży | PAD + służby | Półautomat (EKG na ekranie) | nie | nie | nie | IP55 | 1 |
| Primedic (Metrax) | HeartSave PAD / HeartSave AED / HeartSave AS | Wycofany ze sprzedaży | PAD | Półautomat lub automat (osobne wersje) | tak | nie | nie | b.d. | 2 |
| Primedic (Metrax) | HeartSave Y / YA / YAS | Aktualny | PAD | Półautomat lub automat (osobne wersje) | b.d. | tak | tak | IP55 | 1 |
| GS corpuls (DE) | corpuls aed | Aktualny | PAD + służby | Półautomat lub automat; tryb profesjonalny | tak | tak | tak | IP66 | 2 |
| Bexen Cardio (ES) | Reanibex 100 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | tak | tak | IP55 | 2 |
| Bexen Cardio (ES) | Reanibex 200 | Wycofany ze sprzedaży | PAD + służby | Półautomat | b.d. | nie | nie | b.d. | link |
| Weinmann (DE) | MEDUCORE Standard² (i starszy MEDUCORE Easy) | Aktualny | Monitor-defibrylator z trybem AED | AED + defibrylacja ręczna, monitor | b.d. | nie | tak | b.d. | 1 |
| A.M.I. Italia (IT) | Saver ONE (Standard / Power / D / P) | Aktualny | PAD | Półautomat lub automat (osobne wersje) | nie | nie | tak | IP56 | 1 |
| A.M.I. Italia (IT) | Smarty Saver | Aktualny | PAD | Półautomat lub automat (osobne wersje) | tak | nie | nie | IP56 | 2 |
| Progetti (IT) | Rescue SAM 4.0 | Aktualny | PAD | Półautomat (też automat) | nie | nie | nie | IP55 | 2 |
| DefiSign (DE) | DefiSign Life | Aktualny | PAD | b.d. | b.d. | nie | nie | b.d. | link |
| Life-Point (IT/UK dystr.) | LifePoint AED Pro / Pro Screen | Aktualny | PAD | b.d. | b.d. | nie | nie | b.d. | link |
| Telefunken (Defiteq) | Telefunken AED HR1 / FA1 | Wycofany z rynku UE | PAD | Półautomat lub automat | b.d. | nie | nie | b.d. | link |
| Mediana (KR) | HeartOn A15 | Aktualny | PAD | Półautomat | tak | nie | nie | IP55 | 2 |
| Amoul / Ambulanc (CN) | AED i3 | Aktualny | PAD | Półautomat lub automat (osobne wersje) | nie | nie | tak | IP55 | 2 |
| Amoul / Ambulanc (CN) | AED i5 | Aktualny | PAD | Półautomat | b.d. | nie | nie | b.d. | 1 |
| Welch Allyn | AED 10 / AED 20 | Wycofany ze sprzedaży | PAD + służby | Automat/półautomat | b.d. | nie | nie | b.d. | 1 |

## Zastrzeżenia
- Karty są oryginałami (bez zmian), głównie po angielsku; część po niemiecku, hiszpańsku, włosku, szwedzku lub ukraińsku. Nazwy plików nadaliśmy sami.
- Gdzie producent nie publikuje karty, w paczce jest broszura lub instrukcja (typ dokumentu w nazwie pliku).
- „b.d.” = brak danych w źródle; nic nie było zgadywane. Wartości przed użyciem w produkcie warto sprawdzić z aktualną kartą.
- Lista nie jest wyczerpująca dla tanich modeli z Azji sprzedawanych tylko online; obejmuje modele faktycznie spotykane w rejestrach (OSM PL, BHF UK) i u dystrybutorów w UE.
