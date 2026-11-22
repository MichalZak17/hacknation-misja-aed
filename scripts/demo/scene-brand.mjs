// Brand reel: "<3" turns into the Otwarte AED mark, the slogan, then the brand book (needs out/brand/pNN.png, the
// pages of marketing/ksiega-znaku.pdf rendered at 200 dpi, see README.md).
import { run, sleep } from "./lib.mjs";

await run("brand", async (s, page) => {
  s.cutStart();
  await page.goto(new URL("./brand.html", import.meta.url).href, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => { const c = document.getElementById("__demo_cursor"); if (c) c.remove(); });
  await sleep(1500);
  s.cutEnd();
  const step = (n) => page.evaluate((k) => window.step(k), n);
  await s.cap("Otwarte AED: znak kampanii", "serce zapisane tak, jak w sieci: „<3”");
  await sleep(1600);
  await step(1);
  await sleep(1900);
  await step(2);
  await s.cap("Obrócone o 90° serce z dwóch części, które się nie domykają", "serce z danych, otwarte na kolejne wpisy; iskra to wyładowanie AED");
  await sleep(3200);
  await step(3);
  await sleep(2200);
  await step(4);
  await s.cap("Hasło: „Pokaż AED, zanim ktoś będzie go szukał.”", "defibrylator, którego nie ma na mapie, nie zdąży pomóc");
  await sleep(2600);
  await step(5);
  await sleep(2800);
  await step(6);
  await s.cap("Księga znaku: idea i konstrukcja", "„otwarte” = otwarte dane, AED bez zamków, otwarci ludzie");
  await sleep(4200);
  await step(7);
  await s.cap("Pole ochronne, wielkość minimalna, warianty kolorystyczne");
  await sleep(4200);
  await step(8);
  await s.cap("Kolory z kontrastem WCAG i niedozwolone użycia znaku");
  await sleep(4200);
  await step(9);
  await s.cap("Naklejka na szafkę AED: „Ten AED jest na dane.gov.pl”", "kod QR prowadzi do mapy; post do mediów społecznościowych");
  await sleep(6000);
});
