// Scene 5, anyone on dane.gov.pl (test copy): finds the nationwide AED dataset imported from Misja AED, opens the CSV
// as a table and on the portal's own map, and sees the API resource.
import { run, sleep } from "./lib.mjs";

const P = "https://dane.hackstorm.eu";
const TITLE = /Defibrylatory AED w Polsce/;

await run("portal", async (s, page) => {
  s.cutStart();
  await s.goto(P + "/pl");
  const rodo = page.getByRole("button", { name: "Zamknij" }).first();
  await rodo.waitFor({ timeout: 15000 }).then(() => rodo.click()).catch(() => {});
  await sleep(1500);
  s.cutEnd();
  await s.cap("dane.gov.pl: zbiór widzi każdy", "dane.hackstorm.eu · kopia testowa portalu z kodu Ministerstwa");
  const search = page.locator("input[type=search], input[placeholder*='Wyszukaj'], input[name=q]").first();
  await s.type(search, "defibrylatory AED", 70);
  await sleep(500);
  await page.keyboard.press("Enter");
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(2000);
  const hit = page.getByRole("link", { name: TITLE }).first();
  await s.click(hit);
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(1500);
  await s.cap("Dostawca, źródło, aktualizacja codziennie", "metadane i zasoby z naszego pliku XML");
  await sleep(2500);
  await s.scroll(520, 1500);
  await sleep(2500);
  await s.click(page.getByRole("link", { name: /Defibrylatory AED w Polsce \(CSV\)/ }).first());
  await page.waitForLoadState("networkidle");
  await s.park();
  await sleep(1500);
  await s.cap("Tabela 18 tys. defibrylatorów prosto w portalu", "wyszukiwanie, sortowanie, pobieranie CSV i JSON");
  await s.scroll(700, 1600);
  await sleep(3000);
  const mapTab = page.locator("a, button", { hasText: /^\s*Mapa\s*$/ }).first();
  if (await mapTab.count()) {
    await s.scroll(-250, 600);
    await s.cap("Mapa portalu z tych samych danych", "współrzędne WGS84, jeden wiersz na urządzenie");
    await s.click(mapTab);
    await sleep(1800);
    // scroll from the margin: a wheel over the map would zoom it instead
    await s.moveTo(150, 700, 500);
    await s.scroll(640, 1400);
    await sleep(1200);
    await s.moveTo(1040, 900, 900);
    await sleep(4000);
  }
});
