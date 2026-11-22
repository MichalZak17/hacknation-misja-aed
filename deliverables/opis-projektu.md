# Otwarte AED — jeden ogólnopolski zbiór defibrylatorów na dane.gov.pl

HackNation 2026, wyzwanie Ministerstwa Cyfryzacji „Misja AED — Dane na ratunek”.

- Prototyp (bez logowania): https://misja-aed.hackstorm.eu
- Dane do pobrania i metadane dla portalu: https://misja-aed.hackstorm.eu/export
- API zgodne ze Standardem API: https://misja-aed.hackstorm.eu/api/v1/aeds (dokumentacja: `/api/v1/docs`)
- Plik dla harvestera dane.gov.pl: https://misja-aed.hackstorm.eu/api/export/harvester.xml

## Problem

Przy nagłym zatrzymaniu krążenia liczy się każda minuta. Świadek musi wiedzieć, gdzie jest najbliższy AED, czy jest
teraz dostępny i czy działa. W Polsce nie ma jednego rejestru: dane są rozproszone między OpenStreetMap, miejskie
portale i arkusze dysponentów, w różnych formatach i bez wspólnego zakresu.

## Rozwiązanie

1. **Zbieranie danych z wielu źródeł.** Każde źródło ma własny konektor w kodzie: OpenStreetMap (OpenAEDMap),
   Warszawa 19115, Krosno, Przemyśl, Marki i Legionowo, czyli wszystkie zbiory AED dostępne dziś na dane.gov.pl, oraz
   pliki dysponentów (CSV/XLSX według wzorcowego zakresu). Synchronizacja co 24 godziny, każda także na żądanie
   i w trybie próbnym (bez zapisu).
2. **Walidacja.** Współrzędne w granicach Polski i gminy, naprawa zamienionych współrzędnych, wykrywanie duplikatów
   identyfikatorów i wspólnych punktów. Błędne rekordy nie trafiają do zbioru, a ich problemy widać w panelu.
3. **Scalanie w jeden rekord na urządzenie.** Rekordy łączą się przez stałe identyfikatory (np. OSM
   `ref:api-um-warszawa-pl` ↔ Warszawa `defib_id`). Dla każdego pola wygrywa źródło o najwyższym priorytecie:
   dysponent 90, miasto 50–60, OSM 10. Pochodzenie każdej wartości jest zapisane. Punkty bliżej niż 25 m trafiają do
   przeglądu, bo różne AED mogą stać na różnych piętrach.
4. **Uzupełnianie bez zgadywania.**
   - Gminę (TERYT) i miejscowość ustalamy ze współrzędnych i Państwowego Rejestru Granic, tylko gdy wynik jest pewny.
   - Cechę ulicy w Warszawie bierzemy z miejskiego rejestru adresów.
   - Umiejscowienie, piętro, godziny i warunki dostępu odczytuje z opisów tekstowych lokalny model językowy.
     Wartość z modelu ma najniższy priorytet i jest oznaczona jako wywnioskowana.
5. **Wzorcowy zakres danych.** 59 pól na trzech poziomach (podstawowy, rozszerzony, pełny) odpowiadają na trzy
   pytania ratownika: gdzie (położenie, adres, piętro, opis miejsca), czy dostępny (godziny w składni OSM, warunki
   dostępu, szafka, sezonowość) i czy działa (stan, gotowość, ważność elektrod i baterii, autotest, przegląd).
   Szablon XLSX dla dysponentów ma polskie nagłówki, przykłady, słownik pól, dozwolone wartości i instrukcję.
6. **Publikacja zgodna z dane.gov.pl.**
   - Zasoby: CSV z metadanymi CSVW (jedna wartość w komórce), powiązania ze źródłami (CSV), GeoJSON, JSON,
     JSON-LD (5★ w ocenie portalu), API v1 i jednoarkuszowy szablon XLSX.
   - Każdy dzień danych ma własny, niezmienny adres (`/api/export/archiwum/RRRR-MM-DD/…`), a poprzednie wersje
     zostają dostępne.
   - Dokumenty uzupełniające: słownik TXT oraz „Informacje o zbiorze” z uzasadnieniem odstępstw od zaleceń.
   - Pełne metadane w schemacie harvestera XML 1.13 z sumą MD5. Portal importuje zbiór automatycznie, raz na dobę.
7. **Wyszukiwarka dla każdego.** Najbliższe AED od lokalizacji, adresu lub punktu na mapie. Przy każdym widać, czy
   jest otwarty teraz, jak się do niego dostać, gdzie dokładnie stoi i czy jest sprawny. Do tego wskazówki dojścia.
8. **Zgłoszenia.** Każdy może zgłosić brakujący AED, błąd lub AED zamknięty albo niedziałający. Dysponent może zgłosić
   chęć przekazania danych. Zgłoszenia trafiają do skrzynki w panelu, a nie prosto do zbioru.
9. **Panel administracyjny.** Źródła i ich synchronizacje, rekordy z problemami, przegląd duplikatów, zdarzenia
   serwisowe, import pliku dysponenta, pokrycie danych według województw i gmin.

## Kroki użytkownika

**Osoba szukająca AED**
1. Otwiera stronę główną.
2. Udostępnia lokalizację, wpisuje adres albo klika na mapie.
3. Widzi najbliższe AED z odległością, informacją „otwarte teraz”, opisem miejsca i stanem gotowości.
4. Wybiera AED i otwiera wskazówki dojścia.
5. Jeśli coś się nie zgadza, wybiera „Zgłoś błąd”.

**Dysponent AED**
1. Pobiera szablon `schema.xlsx` ze strony „Dane do pobrania”.
2. Wypełnia arkusz, kierując się przykładami i słownikiem pól.
3. Przekazuje plik. Administrator wgrywa go w panelu (Integracje → Nowy dysponent), uruchamia przebieg próbny,
   a potem synchronizację.
4. Dane dysponenta mają najwyższy priorytet i od następnej synchronizacji są w zbiorze i na portalu.

**Administrator portalu dane.gov.pl**
1. Dodaje źródło danych typu XML z adresem `harvester.xml` i częstotliwością „codziennie”.
2. Portal sam pobiera metadane, zasoby i dokumenty, a potem codziennie je odświeża.

**Programista**
1. Korzysta z API `/api/v1/aeds`: filtrowanie `filter[...]`, sortowanie, wybór pól, stronicowanie z linkami.
2. Alternatywnie pobiera pliki zbioru.

## Liczby (22.11.2026)

| | |
|---|---|
| Urządzenia w zbiorze | ok. 18,8 tys. |
| Źródła | 6 otwartych + pliki dysponentów |
| Godziny dostępności | ok. 40% urządzeń |
| Umiejscowienie (wewnątrz / na zewnątrz) | ok. 87% |
| Gmina (TERYT) | 99,7% |
| Adres | ok. 5% (OSM rzadko go podaje) |
| Stan gotowości | 0% w otwartych źródłach: dają go tylko dysponenci |

## Ograniczenia

- **Brak danych o sprawności.** Żadne otwarte źródło nie podaje stanu urządzenia, ważności elektrod ani baterii.
  Pola są gotowe w zakresie i w imporcie dysponenta (zob. `przyklad-plik-dysponenta.csv`). Wypełnią się, gdy
  dysponenci zaczną przekazywać dane, i do tego służy kampania „Otwarte AED”.
- **Adres tylko przy ok. 5% urządzeń.** OSM opisuje punkt na budynku, nie adres. Ulicy, numeru i kodu pocztowego ze
  współrzędnych nie zgadujemy, bo kod pocztowy zależy od ulicy i numeru.
- **Licencja CC BY-SA 4.0.** Około 96% danych pochodzi z OSM (ODbL 1.0), a portal nie oferuje ODbL. Wybraliśmy
  najbliższą licencję z listy portalu i dodaliśmy atrybucję OSM. Uzasadnienie jest w dokumencie „Informacje
  o zbiorze”.
- **Model językowy może się pomylić.** Dlatego jego wartości mają najniższy priorytet, są oznaczone jako
  wywnioskowane i nie zastępują wartości podanych przez źródło.
- **Duplikaty bez wspólnego identyfikatora.** AED z różnych źródeł bez wspólnego identyfikatora scala się po
  przeglądzie w panelu, nie automatycznie.
- **API w domenie serwisu.** API działa pod `/api/v1` w domenie serwisu, a nie w subdomenie `api.`. To jedno z dwóch
  odstępstw od zaleceń portalu, obok licencji. Pozostałe zalecenia Standardu technicznego zbiór spełnia: jedna
  wartość w komórce, „.” w każdej pustej komórce, osobny zasób powiązań ze źródłami, codzienne wersje pod własnymi
  adresami, metadane CSVW, kontekst JSON-LD w nagłówku odpowiedzi API.

## Technologia

Django 6, django-ninja, PostgreSQL z PostGIS, Redis, Celery, Next.js 16 (system projektowy HackNation), lokalny model
Qwen3.8-27B uruchomiony w vLLM. Wdrożenie: Dokku. Testy: pytest na prawdziwej bazie, z zapisanymi kopiami źródeł
zamiast pobierania na żywo.
