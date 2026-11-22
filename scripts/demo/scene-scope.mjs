// The reference data scope: the real xlsx deliverable (rendered by gen-scope.py) sheet by sheet, then the same
// template published as a resource on the dane.gov.pl test portal.
import { run, sleep } from "./lib.mjs";

const XLSX_RES = process.env.XLSX_RES
  ?? "https://dane.hackstorm.eu/pl/dataset/4214,defibrylatory-aed-w-polsce-zbior-ogolnokrajowy/resource/40228";

await run("scope", async (s, page) => {
  s.cutStart();
  await s.goto(new URL("./out/scope.html", import.meta.url).href);
  await page.evaluate(() => document.fonts.ready);
  await sleep(800);
  s.cutEnd();
  await s.cap("Wzorcowy zakres danych AED (xlsx)", "szablon dla dysponenta: jeden wiersz na urządzenie, przykłady na żółto");
  await s.hover(page.locator("tr.ex td").first(), 900);
  await sleep(1500);
  await page.mouse.move(900, 400);
  for (let i = 0; i < 20; i++) { await page.mouse.wheel(60, 0); await sleep(40); }
  await sleep(1800);

  await s.click(page.locator(".tab", { hasText: "Słownik pól" }));
  await sleep(900);
  await s.cap("Słownik: 59 pól w 3 poziomach", "14 podstawowych, 24 rozszerzone, 21 pełnych · opis, typ, format, przykład");
  await s.click(page.locator(".sheet.on tbody tr").nth(10).locator("td").nth(2), { pause: 120 });
  await sleep(1200);
  await s.moveTo(900, 600, 500);
  await s.scroll(700, 2600);
  await sleep(1200);
  await s.scroll(700, 2600);
  await sleep(1000);

  await s.click(page.locator(".tab", { hasText: "Dozwolone wartości" }));
  await sleep(900);
  await s.cap("Dozwolone wartości: jeden słownik dla całej Polski", "dostępność, stan, gotowość, warunki dostępu, umiejscowienie…");
  await s.moveTo(900, 600, 500);
  await s.scroll(900, 2400);
  await sleep(1500);

  await s.click(page.locator(".tab", { hasText: "Instrukcja" }));
  await sleep(900);
  await s.cap("Instrukcja wypełnienia w tym samym pliku");
  await sleep(3000);

  s.cutStart();
  await s.goto(XLSX_RES);
  const rodo = page.getByRole("button", { name: "Zamknij" }).first();
  await rodo.waitFor({ timeout: 15000 }).then(() => rodo.click()).catch(() => {});
  await sleep(1500);
  await s.park();
  s.cutEnd();
  await s.cap("Ten sam szablon opublikowany na dane.gov.pl", "zasób XLSX w zbiorze AED, z podglądem tabeli");
  await sleep(2000);
  await s.moveTo(150, 700, 500);
  await s.scroll(640, 1500);
  await sleep(3500);
});
