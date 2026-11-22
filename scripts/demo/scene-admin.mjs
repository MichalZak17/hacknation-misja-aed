// Scene 3, the administrator's tour: dashboard, one merged device with per-field provenance (incl. the AI-read
// floor), duplicates to decide, citizen reports, exports for dane.gov.pl.
import path from "node:path";

import { HERE, readEnvFile, run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
const env = { ...readEnvFile(path.join(HERE, "../../backend/.env")), ...process.env };
const EMAIL = env.DEMO_EMAIL ?? env.ADMIN_EMAIL;
const PASSWORD = env.DEMO_PASSWORD ?? env.ADMIN_PASSWORD;
const DEVICE = process.env.DEVICE ?? "AED-PL-018472";

await run("admin", async (s, page) => {
  // log in off camera (cut in the edit)
  s.cutStart();
  await s.goto(B + "/login");
  await page.fill("input[type=email]", EMAIL);
  await page.fill("input[type=password]", PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/panel/, { timeout: 30000 });
  await page.waitForLoadState("networkidle");
  await sleep(1500);
  await s.park();
  s.cutEnd();

  await s.cap("Przegląd: stan rejestru i synchronizacji", "18 tys. defibrylatorów z 6 źródeł, codzienna wersja danych");
  await sleep(2500);
  await s.scroll(650, 1600);
  await sleep(1500);
  await s.cap("Kompletność danych: czego brakuje, żeby odpowiedzieć „gdzie, kiedy, czy działa”");
  await s.scroll(500, 1300);
  await sleep(2500);

  await s.goto(B + `/devices/${DEVICE}`);
  await sleep(1200);
  await s.cap("Jedno urządzenie, wiele źródeł", "przy każdym polu: skąd pochodzi i jaką metodą");
  await sleep(2500);
  const floor = page.getByText(/AI\s*z opisu/).first();
  if (await floor.count()) {
    await s.hover(floor, 900);
    await s.cap("Piętro „4” odczytane przez AI z opisu „IV piętro PKiN”", "niższy priorytet niż dane źródła, z zapisanym pochodzeniem");
    await sleep(3500);
  }
  await s.scroll(600, 1400);
  await sleep(2000);

  await s.goto(B + "/matches");
  await sleep(1000);
  await s.cap("Duplikaty z różnych źródeł: decyzja administratora", "scal w jedno albo oznacz jako różne urządzenia");
  await s.hover(page.getByRole("button", { name: /Scal w jedno/ }).first(), 900);
  await sleep(3000);


  await s.goto(B + "/export");
  await sleep(1000);
  await s.cap("Eksport do dane.gov.pl", "CSV, XLSX, GeoJSON, JSON-LD, API oraz plik XML harwestera");
  await s.scroll(700, 1500);
  await sleep(3000);
});
