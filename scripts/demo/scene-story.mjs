// Opening of the story cut: the situation from the challenge brief, line by line. No captions.
import { run, sleep } from "./lib.mjs";

await run("story", async (s, page) => {
  s.cutStart();
  await page.goto(new URL("./story.html", import.meta.url).href, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => { const c = document.getElementById("__demo_cursor"); if (c) c.remove(); });
  await sleep(1000);
  s.cutEnd();
  s.marks.push({ t: s.now(), cap: "" });
  for (const [id, ms] of [["a", 4600], ["b", 7100], ["c", 5100], ["d", 6300]]) {
    await page.evaluate((k) => window.step(k), id);
    await sleep(ms);
  }
});
