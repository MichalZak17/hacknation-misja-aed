# Norwegia – Hjertestarterregisteret: źródła i dane

## Kto prowadzi rejestr
- helsenorge.no (Helsedirektoratet): treść o rejestracji AED „levert og kvalitetssikret av Nasjonalt senter for prehospital akuttmedisin (NAKOS)”: https://www.helsenorge.no/forstehjelp/registrer-din-hjertestarter/
- Sanitetskvinnene (V 2026): „Hjertestarterregisteret driftes av helsemyndighetene”, NAKOS „drifter Hjertestarterregisteret” (aed@nakos.no): https://sanitetskvinnene.no/sites/default/files/2026-05/Registrering%20av%20hjertestartere.pdf
- Tidsskriftet 2019 (szef rejestru w NAKOS): https://tidsskriftet.no/en/node/57891/pdf
- Rejestr: https://hjertestarterregister.113.no/ (formularz: ords/f?p=120:STEP1, logowanie: ords/f?p=130:LOGIN_DESKTOP). Strona blokuje automatyczne pobieranie (robots.txt), więc formularza nie odczytaliśmy bezpośrednio.
- Wymóg: dane trzeba aktualizować lub potwierdzać co 6 miesięcy („hver sjette måned”, helsenorge).

## Hjelp 113 (Stiftelsen Norsk Luftambulanse + Helsedirektoratet)
- https://norskluftambulanse.no/hjelp113/ , FAQ: https://norskluftambulanse.no/ofte-stilte-sporsmal-om-hjelp-113-appen/
- Pozycja dzwoniącego: wysyła ją telefon przez AML (Advanced Mobile Location), tylko gdy trwa połączenie alarmowe. Aplikacja pokazuje też współrzędne na ekranie, żeby je podyktować.
- Dzwoni do 110 / 112 / 113, za granicą proponuje 112. Pokazuje aktywne AED z rejestru i prowadzi do najbliższego.
- Fundacja: „har ikke ansvar for informasjonen om hjertestarterne” (dane AED pochodzą z rejestru 113.no).
- Od 2010 r., ponad 2,8 mln pobrań.

## API i model danych
- API REST z OAuth2 (client credentials), dostęp nadaje rejestr: https://hjertestarterregister.113.no/ords/api/v1/ (assets/search, assets/deleted, assets/inactive, zapis rekordów, wiadomości e-mail/SMS do właścicieli).
- Pełna lista pól: plik ../AED_pola_rejestrow_NO_UK_DK.xlsx, arkusz NO_API_pola. Źródło: typy w otwartym kliencie API https://github.com/Johannes-Andersen/Hjertestarterregister2OSM

## Pliki w tym folderze
- AED_Norwegia_z_rejestru_via_OSM_2026-05-31.csv / .geojson: 11 336 AED z rejestru, zaimportowanych do OpenStreetMap za zgodą rejestru (ODbL 1.0, „© OpenStreetMap contributors”). Stan bazy OSM: 31.05.2026 (serwer Overpass private.coffee). Pola: nazwa, opis miejsca, godziny, piętro, identyfikator rejestru. Bez danych o urządzeniu (te są tylko w API).
- Zbioru Rogaland z opencom.no (NLOD) nie udało się pobrać: portal blokuje automatyczne pobieranie. Jego 31 kolumn znamy ze skryptu, który go generuje (arkusz NO_Rogaland_kolumny). Pobranie ręczne: https://opencom.no/dataset/hjertestartere-i-rogaland-2023-05-08
