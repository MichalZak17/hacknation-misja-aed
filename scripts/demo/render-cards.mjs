// Renders card.html variants to PNG (title cards opaque, captions transparent).
//   node render-cards.mjs jobs.json      jobs: [{file, query, transparent}]
import fs from "node:fs";

import { chromium } from "playwright";

const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const card = new URL("./card.html", import.meta.url).href;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
for (const j of jobs) {
  await page.goto(`${card}?${new URLSearchParams(j.query)}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: j.file, omitBackground: !!j.transparent });
}
await browser.close();
console.log(`rendered ${jobs.length} cards`);
