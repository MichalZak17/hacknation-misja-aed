// What the portal reads from us: the harvester XML with dated daily versions, CSVW metadata for the CSV, and the
// public API for emergency services and apps.
import { run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";

await run("compliance", async (s, page) => {
  await s.goto(B + "/api/export/harvester.xml");
  await sleep(800);
  await s.cap("harvester.xml: nasz zbiór w schemacie portalu", "urn:otwarte-dane:harvester:1.13 · licencja, kategorie, aktualizacja codziennie");
  await s.hover(page.getByText("urn:otwarte-dane:harvester:1.13").first(), 900).catch(() => {});
  await sleep(2500);
  await s.moveTo(1500, 600, 500);
  await s.scroll(560, 1600);
  await sleep(800);
  await s.cap("Codzienne wersje zasobów pod stałymi adresami", "archiwum/RRRR-MM-DD: plik z danego dnia nigdy się nie zmienia");
  await s.hover(page.getByText(/archiwum\/\d{4}-\d{2}-\d{2}\/aeds\.csv/).first(), 900).catch(() => {});
  await sleep(3200);

  await s.goto(B + "/api/export/aeds.csv-metadata.json");
  await sleep(800);
  await s.cap("CSV opisany metadanymi CSVW (W3C)", "polskie tytuły kolumn, typy, znak umowny „.”, klucz główny");
  await s.moveTo(1500, 600, 500);
  await s.scroll(500, 1500);
  await sleep(2500);

  await s.goto(B + "/developers");
  await sleep(1000);
  await s.cap("API dla służb ratunkowych i aplikacji", "najbliższy AED i czy jest dostępny teraz, JSON w WGS84");
  await sleep(1500);
  const send = page.getByRole("button", { name: /Wyślij/ }).first();
  if (await send.count()) {
    await s.click(send);
    await sleep(3500);
  } else {
    await s.scroll(500, 1400);
    await sleep(3000);
  }
});
