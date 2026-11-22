// Scene 1, the citizen: nearest AED from "my location", whether it is open now, how to get there; nationwide map;
// the same page on a phone.
import { run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
// Warszawa, the square in front of the central station
const HERE = { latitude: 52.22935, longitude: 21.00285 };

await run(
  "citizen",
  async (s, page) => {
    await s.goto(B + "/");
    await page.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }).waitFor();
    await sleep(1200);
    await s.cap("Mieszkaniec: gdzie jest najbliższy defibrylator?", "misja-aed.hackstorm.eu · bez logowania");
    await s.hover(page.locator(".maplibregl-canvas, .leaflet-container, canvas").first(), 900);
    await sleep(1800);

    await s.click(page.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }));
    await page.locator("#answer-heading").waitFor({ timeout: 20000 });
    await sleep(900);
    await s.cap("Najbliższy AED: odległość, czy jest teraz otwarty, jak dojść", "dane z 6 źródeł scalone w jeden rekord");
    await s.hover(page.locator("#answer-heading"), 700);
    await sleep(3200);

    // the list of nearest AEDs
    await s.hover(page.locator("#results-heading"), 700).catch(() => {});
    await s.scroll(520, 1400);
    await sleep(1500);
    await s.cap("Gdzie dokładnie wisi, w jakich godzinach i na jakich warunkach");
    await s.scroll(420, 1200);
    await sleep(2500);

    const onMap = page.getByRole("button", { name: /Pokaż na mapie/ }).nth(1);
    if (await onMap.count()) {
      await s.click(onMap);
      await sleep(2600);
    }

    await s.cap("Tylko urządzenia dostępne dla każdego");
    await s.scroll(-2000, 900);
    await s.click(page.locator("#public-only"));
    await sleep(2600);

    // the same page on a phone, framed on a branded backdrop
    s.cutStart();
    await page.goto(new URL("./phone.html", import.meta.url).href, { waitUntil: "networkidle" });
    await page.evaluate((u) => { document.getElementById("phone").src = u; }, B + "/");
    const phone = page.frameLocator("#phone");
    await phone.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }).waitFor({ timeout: 30000 });
    await sleep(2500);
    // the pointer now lives in the phone's iframe (its own cursor); hide the page's one
    await page.evaluate(() => { const c = document.getElementById("__demo_cursor"); if (c) c.remove(); });
    await s.moveTo(1650, 760, 10);
    s.cutEnd();
    await s.cap("Na telefonie: jeden przycisk i najbliższe AED", "WCAG 2.2 AA, „Zadzwoń 112” na samej górze");
    await sleep(1200);
    await s.click(phone.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }));
    await phone.locator("#answer-heading").waitFor({ timeout: 20000 });
    await sleep(2500);
    await s.scroll(420, 1300);
    await sleep(1800);
    await s.scroll(520, 1300);
    await sleep(1500);
    const report = phone.getByRole("link", { name: /Zgłoś błąd/ }).first();
    if (await report.count()) {
      await s.cap("Każdy może zgłosić błąd lub niedziałające AED", "zgłoszenie trafia do panelu dysponenta");
      await s.click(report);
      await sleep(3500);
      await s.scroll(380, 1100);
      await sleep(2000);
    }
  },
  { geolocation: HERE },
);
