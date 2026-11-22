# Audyt WCAG (axe-core)

`cd scripts/wcag && npm install && node audit.mjs after http://localhost:3000` — audyt axe-core 4.14 (WCAG 2.0/2.1/2.2 A+AA i best-practice) wszystkich stron × desktop/mobile × jasny/ciemny; wynik w `deliverables/wcag/after/` (`summary.json` + JSON na każdy przebieg). Argumenty: `[etykieta-lub-ścieżka] [baseUrl] [regex-stron]`; logowanie do panelu z `ADMIN_EMAIL`/`ADMIN_PASSWORD` (`backend/.env`), `DEVICE=` i `SLUG=` przypinają strony szczegółów.
