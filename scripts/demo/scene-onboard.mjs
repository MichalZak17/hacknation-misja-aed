// A new data holder joins: the "Dodaj dysponenta" form (filled, then cancelled: nothing is saved).
import path from "node:path";

import { HERE, readEnvFile, run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
const env = { ...readEnvFile(path.join(HERE, "../../backend/.env")), ...process.env };

await run("onboard", async (s, page) => {
  s.cutStart();
  await s.goto(B + "/login");
  await page.fill("input[type=email]", env.DEMO_EMAIL ?? env.ADMIN_EMAIL);
  await page.fill("input[type=password]", env.DEMO_PASSWORD ?? env.ADMIN_PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/panel/, { timeout: 30000 });
  await s.goto(B + "/integrations");
  await sleep(1200);
  s.cutEnd();
  await s.cap("Nowy dysponent dołącza w kilka minut", "gmina, szkoła, szpital: plik CSV lub XLSX we wzorcowym zakresie");
  await sleep(1200);
  await s.click(page.getByRole("button", { name: /Dodaj dysponenta/ }));
  const dlg = page.getByRole("dialog");
  await dlg.waitFor();
  await sleep(1200);
  const inputs = dlg.locator("input");
  await s.type(inputs.nth(0), "Gmina Przykładowo — defibrylatory", 45);
  await s.type(inputs.nth(1), "Gmina Przykładowo", 45);
  await sleep(600);
  await s.cap("Ta sama ścieżka co każde źródło", "test bez zapisu, walidacja, scalanie, publikacja na dane.gov.pl");
  await s.hover(dlg.getByRole("button", { name: /Dodaj dysponenta/ }), 900);
  await sleep(3000);
  await s.click(dlg.getByRole("button", { name: "Anuluj" }));
  await sleep(1200);
});
