// Scene 2, the administrator runs a sync of a city source by hand and watches the LLM classify its free text live.
// CONFIRM=1 really starts the re-classification (~3.5 min of the shared GPU for warszawa-19115); without it the scene
// stops at the confirmation dialog (rehearsal).
import path from "node:path";

import { HERE, readEnvFile, run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
const SLUG = process.env.SLUG ?? "warszawa-19115";
const env = { ...readEnvFile(path.join(HERE, "../../backend/.env")), ...process.env };
const EMAIL = env.DEMO_EMAIL ?? env.ADMIN_EMAIL;
const PASSWORD = env.DEMO_PASSWORD ?? env.ADMIN_PASSWORD;
const CONFIRM = !!process.env.CONFIRM;

await run("sync", async (s, page) => {
  await s.goto(B + "/login");
  await sleep(800);
  await s.cap("Panel dysponenta danych", "logowanie administratora");
  await s.type(page.locator("input[type=email]"), EMAIL, 35);
  await s.type(page.locator("input[type=password]"), PASSWORD, 25);
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/panel/, { timeout: 30000 });
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(600);

  await s.goto(B + "/integrations");
  await sleep(1000);
  await s.cap("6 źródeł, każde w innym formacie", "OpenStreetMap, Warszawa, Krosno, Legionowo, Marki, Przemyśl");
  await s.hover(page.getByText("Warszawa 19115", { exact: false }).first(), 900);
  await sleep(2500);
  await s.click(page.getByRole("link", { name: /Warszawa 19115/ }).first());
  await page.waitForURL(new RegExp(`/integrations/${SLUG}`));
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(800);
  await s.cap("Synchronizacja ręczna: rejestr miasta Warszawy", "708 rekordów, GeoJSON z ArcGIS");
  await sleep(2500);
  await s.click(page.getByRole("link", { name: /Klasyfikacja AI/ }).last());
  await page.waitForURL(/\/ai/);
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(1000);
  await s.cap("Klasyfikacja AI opisów w trakcie synchronizacji", "lokalny model Qwen na serwerze GPU, bez wysyłania danych na zewnątrz");
  await s.hover(page.locator("#ai-source"), 700);
  await sleep(1500);
  await s.click(page.getByRole("button", { name: "Klasyfikuj ponownie" }));
  await page.getByRole("alertdialog").waitFor();
  await sleep(1800);
  const go = page.getByRole("alertdialog").getByRole("button", { name: "Klasyfikuj", exact: true });
  if (!CONFIRM) {
    await s.hover(go);
    await s.snap("dialog");
    return;
  }
  await s.click(go);

  // the run starts: pipeline phases, then the model's answers stream into the terminal
  await page.getByText("Klasyfikacja AI").first().waitFor();
  await sleep(4000);
  await s.cap("Na żywo: tekst ze źródła → pola zbioru", "piętro, godziny, warunki dostępu, umiejscowienie");
  const term = page.locator("text=odpowiedzi").first();
  await s.hover(term, 900).catch(() => {});
  await sleep(14000);
  await s.snap("streaming");
  s.speed(10, "×10");
  await s.cap("Każda odpowiedź jest sprawdzana; wartości spoza słownika są odrzucane");
  // wait for the end of the run
  await page.getByText(/Klasyfikacja zakończona|Synchronizacja zakończona/).first().waitFor({ timeout: 8 * 60000 });
  s.speed(1);
  await sleep(1200);
  await s.cap("Gotowe: pola z AI mają niższy priorytet niż dane podane przez źródło", "i zapisane pochodzenie: „AI, z opisu”");
  await s.scroll(700, 1500);
  await sleep(3500);
  await s.snap("done");
});
