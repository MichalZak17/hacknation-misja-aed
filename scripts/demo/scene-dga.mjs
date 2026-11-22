// The list of protected data (DGA): our harvester.xml carries it as a second dataset flagged containsProtectedData,
// and the portal adds its rows to the nationwide „Wykaz chronionych danych” every night, with no manual step.
import { run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
const P = "https://dane.hackstorm.eu";

// Smooth-scroll until the locator's top sits at y (the XML viewer and the portal both scroll the window).
async function scrollTo(s, page, locator, y, ms = 1600) {
  const box = await locator.boundingBox();
  if (box) await s.scroll(box.y - y, ms);
}

await run("dga", async (s, page) => {
  s.cutStart();
  await s.goto(B + "/api/export/harvester.xml");
  await sleep(1000);
  s.cutEnd();
  await s.moveTo(1500, 600, 400);
  await s.cap("Wykaz chronionych danych (DGA)", "drugi zbiór w naszym harvester.xml");
  await scrollTo(s, page, page.locator("text=misja-aed-dga >> visible=true").first(), 60, 2200);
  await sleep(1500);
  await s.hover(page.locator("text=misja-aed-dga >> visible=true").first(), 700).catch(() => {});
  await sleep(1200);
  await s.cap("Jeden zasób z flagą containsProtectedData", "plik XLSX z naszej bazy: zgłoszenia, pliki dysponentów, surowe pobrania");
  const flag = page.locator("text=containsProtectedData >> visible=true").last();
  await scrollTo(s, page, flag, 380, 1200);
  await sleep(500);
  await s.hover(flag, 800).catch(() => {});
  await sleep(3000);

  s.cutStart();
  await s.goto(P + "/pl/dga");
  const rodo = page.getByRole("button", { name: "Zamknij" }).first();
  await rodo.waitFor({ timeout: 15000 }).then(() => rodo.click()).catch(() => {});
  await sleep(1500);
  await s.moveTo(960, 640, 300);
  s.cutEnd();
  await s.cap("Punkt informacyjny DGA na dane.gov.pl", "dane.hackstorm.eu · kopia testowa portalu z kodu Ministerstwa");
  await sleep(1800);
  const tab = page.getByText(/Wykaz chronionych danych/).first();
  await s.click(tab);
  await s.moveTo(1750, 650, 500);
  s.cutStart();
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.getByText("Misja AED - instytucja testowa").first().waitFor({ timeout: 30000 });
  await sleep(1200);
  await s.park();
  s.cutEnd();
  await s.cap("Portal co noc dopisuje nasz wykaz do tabeli zbiorczej", "synchronizacja automatyczna, bez ręcznej pracy");
  await sleep(1200);
  const row = page.getByText("Misja AED - instytucja testowa").first();
  await scrollTo(s, page, row, 300, 1600);
  await sleep(600);
  await s.hover(row, 800);
  await sleep(1500);
  await s.hover(page.getByText(/kopii pobrań|kopie pobrań/).first(), 900).catch(() => {});
  await sleep(3500);
});
