// Scene for the story cut: at night the nearest AED hangs in a building that is closed (by its opening hours) and the app
// points to the nearest one accessible right now. The pages get a fixed night clock (NIGHT_AT), so the nearest AED to
// Warszawa Centralna is closed whenever this is recorded; the app computes "open now" in the browser.
// The left panel of phone.html carries the narration, so this scene needs no captions.
import { run, sleep } from "./lib.mjs";

const B = process.env.BASE ?? "https://misja-aed.hackstorm.eu";
const HERE = { latitude: 52.22935, longitude: 21.00285 };
const NIGHT_AT = process.env.NIGHT_AT ?? "2026-11-22T04:20:00+01:00";

await run(
  "night",
  async (s, page) => {
    s.cutStart();
    await page.goto(new URL("./phone.html?big=1", import.meta.url).href, { waitUntil: "networkidle" });
    await page.evaluate(() => window.set("Noc, centrum miasta.<br><span>Ktoś upada.</span>",
      "Gdzie jest najbliższy defibrylator? Czy da się go teraz wziąć?"));
    await page.evaluate((u) => { document.getElementById("phone").src = u; }, B + "/");
    const phone = page.frameLocator("#phone");
    await phone.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }).waitFor({ timeout: 30000 });
    await sleep(2500);
    await page.evaluate(() => { const c = document.getElementById("__demo_cursor"); if (c) c.remove(); });
    // the phone is scaled by CSS: map Playwright's (unscaled) boxes onto the screen
    const frame = await page.locator("#phone").boundingBox();
    const k = frame.width / 390;
    s.xform = (x, y) => [frame.x + (x - frame.x) * k, frame.y + (y - frame.y) * k];
    await s.moveTo(1560, 700, 10);
    s.cutEnd();
    s.marks.push({ t: s.now(), cap: "" });
    await sleep(3500);
    await s.hover(phone.getByRole("link", { name: /Zadzwoń 112/ }).first(), 900).catch(() => {});
    await sleep(1500);
    await s.click(phone.getByRole("button", { name: "Pokaż AED w pobliżu mnie" }));
    await phone.locator("#answer-heading").waitFor({ timeout: 20000 });

    // read what the app actually says, so the narration matches the screen
    const answer = phone.locator("section[aria-labelledby=answer-heading]");
    const text = (await answer.innerText()).replace(/\s+/g, " ");
    console.log("answer:", text);
    const closed = /zamknięte/i.test(text);
    const alt = text.match(/Najbliższy otwarty teraz[^:]*: nr (\d+), ([\d ]+ ?m)/);
    if (closed && alt) {
      // an AED is not locked away by itself: it is in a building that is closed at this hour
      const inside = /wewnątrz|w budynku|korytarz|hol\b/i.test(text);
      const why = inside ? "Wisi w środku, a budynek jest teraz zamknięty." : "Według godzin otwarcia jest teraz niedostępny.";
      await page.evaluate(([n, d, w]) => window.set("Najbliższy AED<br><span>w zamkniętym budynku</span>",
        `${w} Aplikacja od razu wskazuje najbliższy dostępny teraz: nr ${n}, ${d}.`), [alt[1], alt[2], why]);
    } else {
      await page.evaluate(() => window.set("Najbliższy AED<br><span>w kilka sekund</span>",
        "Odległość, czy jest teraz otwarty i jak do niego dojść."));
    }
    await s.hover(answer.getByText(/zamknięte|Otwarte/i).first(), 900).catch(() => {});
    await sleep(4500);
    if (alt) await s.hover(answer.getByText(/Najbliższy otwarty teraz/).first(), 700).catch(() => {});
    await sleep(2500);

    // go to the open one
    await s.click(phone.getByRole("link", { name: /Inne AED w pobliżu/ }).first());
    if (alt) {
      const item = phone.locator("ol li, ul li").filter({ hasText: /Otwarte całą dobę|Otwarte teraz/ }).first();
      await item.waitFor({ timeout: 10000 });
      const where = ((await item.locator("dd").first().innerText().catch(() => "")) || "").replace(/\s+/g, " ").trim();
      const open = /całą dobę/.test(await item.innerText()) ? "całą dobę" : "teraz";
      // the headline changes as the list scrolls to the open one, not after it
      await Promise.all([
        page.evaluate(([o, w]) => window.set(`Otwarty<br><span>${o}</span>`,
          (w ? w + ". " : "") + "Prowadzimy pieszo, krok po kroku."), [open, where]),
        item.scrollIntoViewIfNeeded().catch(() => {}),
      ]);
      await sleep(600);
      await s.hover(item.getByText(/Otwarte/).first(), 900).catch(() => {});
      await sleep(4000);
      await s.hover(item.getByRole("link", { name: /Nawiguj pieszo/ }).first(), 900).catch(() => {});
      await sleep(3500);
    } else {
      await sleep(1500);
      await s.scroll(500, 1400);
      await sleep(4000);
    }
  },
  { geolocation: HERE, clock: NIGHT_AT, padBottom: 40 },
);
