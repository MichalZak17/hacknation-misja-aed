# Audyt dostępności WCAG 2.2 AA — przed i po poprawkach

Automatyczny audyt [axe-core](https://github.com/dequelabs/axe-core) 4.14.1 (reguły `wcag2a`, `wcag2aa`, `wcag21a`,
`wcag21aa`, `wcag22aa`, `best-practice`) w przeglądarce Chromium. Każda strona sprawdzana jest w 4 wariantach:
desktop (1440×900) i telefon (390×844, dotyk) × motyw jasny i ciemny. Strony: wyszukiwarka AED (również z wynikami
wyszukiwania), dane do pobrania, dokumentacja (4 strony), API dla deweloperów, formularz zgłoszenia (`/zglos`, tylko
w audycie „po”), logowanie, strona 404 oraz panel dysponenta (przegląd, mapa, urządzenia, karta urządzenia,
integracje, karta integracji, dopasowania).

- `before/` — stan z 21.11.2026 (68 przebiegów, 17 stron)
- `after/` — stan po poprawkach (72 przebiegi, 18 stron)

Każdy katalog zawiera `summary.json` (liczniki na przebieg) i pełny wynik axe dla każdego przebiegu
(`<strona>--<urządzenie>--<motyw>.json`).

## Wynik

| Reguła axe | Kryterium WCAG | Waga | Przed: przebiegi / elementy | Po |
|---|---|---|---|---|
| `link-in-text-block` | 1.4.1 Użycie koloru | poważne | 36 / 48 | 0 |
| `color-contrast` | 1.4.3 Kontrast (minimum) | poważne | 17 / 36 | 0 |
| `region` | 1.3.1 / best-practice (punkty orientacyjne) | umiarkowane | 4 / 20 | 0 |
| `nested-interactive` | 4.1.2 Nazwa, rola, wartość | poważne | 4 / 8 | 0 |
| `scrollable-region-focusable` | 2.1.1 Klawiatura | poważne | 4 / 4 | 0 |
| `landmark-one-main` | best-practice (jeden `<main>`) | umiarkowane | 4 / 4 | 0 |
| **Razem** | | | **69 / 120** | **0** |

„Przebiegi” to liczba par strona × wariant, w których reguła zgłosiła błąd; „elementy” to liczba elementów HTML.

## Co poprawiliśmy

- **Linki w tekście** (`link-in-text-block`): link w akapicie był rozpoznawalny tylko po kolorze (cyjan na szarym tekście
  w trybie ciemnym ma tylko 1,6:1 względem otoczenia). Teraz każdy link w akapicie jest podkreślony — jedna reguła
  w `globals.css` (`p a.text-link`), więc dotyczy stopki, strony eksportu i wszystkich przyszłych akapitów. Link
  „© OpenStreetMap” w atrybucji mapy (styl MapLibre: szary na czarnym, bez podkreślenia) też jest podkreślony.
- **Kontrast** (`color-contrast`): token `--subtle-foreground` w jasnym motywie przyciemniony z `#5d7681` do `#566e78`
  (4,4:1 → 4,95:1 na tle strony, 4,75:1 na tle studzienek). Nowy token `--crimson-text` dla drobnego tekstu
  w kolorze marki: w jasnym motywie `#d10035`, w ciemnym `#ff5c7a` (5,3:1 zamiast 3,6:1 dla `#e6013a` na granacie).
  Używają go etykiety sekcji (`MetaLabel`) i oznaczenie „wymagany” w konsoli API. Kolor marki w przyciskach,
  logotypie i dużych liczbach bez zmian.
- **Punkty orientacyjne** (`region`, `landmark-one-main`): strona logowania jest w `<main>`; ekrany „Sprawdzanie sesji…”
  i „Brak połączenia z API” w panelu też są w `<main>` (wcześniej przez chwilę strona nie miała żadnego landmarku).
- **Zagnieżdżone elementy interaktywne** (`nested-interactive`): na karcie urządzenia link do źródła był wewnątrz
  `<summary>` rozwijanego rekordu źródłowego. Nagłówek rekordu zawiera teraz samą nazwę, a link „Źródło: …” jest
  w rozwiniętej treści.
- **Przewijane tabele** (`scrollable-region-focusable`): komponent `Table` sprawdza, czy tabela jest szersza niż
  ekran (telefon); jeśli tak, kontener przewijania dostaje `tabindex="0"`, rolę `region` i nazwę (z `aria-label` lub
  `<caption>` tabeli), więc da się go przewinąć klawiaturą. Tabela, która się mieści, nie dodaje zbędnego tabulatora.

## Pozostałe uwagi

Brak naruszeń wykrywanych automatycznie. axe oznacza część elementów jako „do ręcznej weryfikacji” (`incomplete`,
nie są to błędy): głównie `color-contrast` tam, gdzie tekst leży na mapie, obrazie lub półprzezroczystym tle i kontrastu
nie da się policzyć automatycznie, oraz `label-content-name-mismatch` (przyciski ikon z opisową etykietą
`aria-label`). Audyt automatyczny nie wykrywa wszystkich problemów WCAG; obsługę klawiaturą, czytnik ekranu i powiększenie
200% warto sprawdzić ręcznie.

## Jak powtórzyć

```bash
cd scripts/wcag && npm install        # raz: Playwright 1.49.1 (Chromium)
node audit.mjs after http://localhost:3000
```

Argumenty: `[etykieta] [adres frontendu] [regex nazw stron]`. Panel loguje się danymi `ADMIN_EMAIL` /
`ADMIN_PASSWORD` z `backend/.env`. Ten audyt: serwer deweloperski Next.js z lokalnym backendem,
`DEVICE=AED-PL-000128 SLUG=warszawa-19115` (te same strony szczegółów co w audycie „przed”).
