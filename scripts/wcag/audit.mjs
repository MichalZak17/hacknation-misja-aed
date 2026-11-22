// axe-core WCAG 2.2 AA audit of the Misja AED frontend: every page × viewport (desktop, mobile) × theme (light, dark).
//
//   cd scripts/wcag && npm install            # once: Playwright 1.49.1 (Chromium build 1148 in ~/.cache/ms-playwright)
//   node audit.mjs [label] [baseUrl] [pageRegex]
//
//   label      output folder deliverables/wcag/<label>/ (default "after"); a path if it contains "/"
//   baseUrl    running frontend, e.g. http://localhost:3000 (default $BASE or http://localhost:3000)
//   pageRegex  only audit pages whose name matches (optional)
//
// Admin pages log in with ADMIN_EMAIL / ADMIN_PASSWORD from the environment or backend/.env.
// DEVICE=<id> and SLUG=<integration slug> pin the detail pages (otherwise picked from the API).
// Writes one JSON per run (axe violations + incomplete) and summary.json with counts per run.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const label = process.argv[2] ?? "after";
const BASE = (process.argv[3] ?? process.env.BASE ?? "http://localhost:3000").replace(/\/$/, "");
const only = process.argv[4] ? new RegExp(process.argv[4]) : null;

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"];
const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } };
// Stub the public geocoder so the audit neither depends on nor loads Nominatim.
const NOMINATIM_ANSWER = [
  {
    display_name: "Plac Defilad 1, Śródmieście Północne, Śródmieście, Warszawa, 00-901, Polska",
    lat: "52.231838",
    lon: "21.005995",
  },
];

function readEnvFile(file) {
  const env = {};
  try {
    for (const line of fs.readFileSync(file, "utf8").split("\n")) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  } catch {}
  return env;
}
const dotenv = readEnvFile(path.join(REPO, "backend/.env"));
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? dotenv.ADMIN_EMAIL ?? "admin@admin.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD ?? dotenv.ADMIN_PASSWORD ?? "admin123";

// a label with a slash is used as the output path itself
const outDir = label.includes("/") ? path.resolve(label) : path.join(REPO, "deliverables/wcag", label);
fs.mkdirSync(outDir, { recursive: true });
const axeDir = path.join(REPO, "frontend/node_modules/axe-core");
const axeSource = fs.readFileSync(path.join(axeDir, "axe.min.js"), "utf8");
const axeVersion = JSON.parse(fs.readFileSync(path.join(axeDir, "package.json"), "utf8")).version;

async function newContext(browser, { viewport = "desktop", theme = "light", storageState } = {}) {
  const ctx = await browser.newContext({
    viewport: VIEWPORTS[viewport],
    deviceScaleFactor: viewport === "mobile" ? 2 : 1,
    isMobile: viewport === "mobile",
    hasTouch: viewport === "mobile",
    colorScheme: theme,
    locale: "pl-PL",
    timezoneId: "Europe/Warsaw",
    storageState,
  });
  await ctx.addInitScript((t) => {
    try {
      localStorage.setItem("theme", t);
    } catch {}
  }, theme);
  await ctx.route("https://nominatim.openstreetmap.org/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(NOMINATIM_ANSWER) }),
  );
  return ctx;
}

async function settle(page, ms = 1500) {
  await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

async function login(browser) {
  const ctx = await newContext(browser);
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#email", ADMIN_EMAIL);
  await page.fill("#password", ADMIN_PASSWORD);
  await page.click("button[type=submit]");
  await page.waitForURL(/\/panel/, { timeout: 30000 });
  const state = await ctx.storageState();
  await ctx.close();
  return state;
}

/** Search the public page for Plac Defilad and wait for the nearest-AED answer. */
async function searchNearest(page) {
  await page.fill("#address", "Warszawa, Plac Defilad 1");
  await page.click("form[role=search] button[type=submit]");
  await page.waitForSelector("#answer-heading", { timeout: 30000 });
  await settle(page, 2500);
}

const browser = await chromium.launch({ headless: true });
const auth = await login(browser);

// A device with several sources and an integration slug for the detail pages
const probe = await (await newContext(browser, { storageState: auth })).newPage();
await probe.goto(`${BASE}/login`);
const ids = await probe.evaluate(async () => {
  const devs = await (await fetch("/api/devices?limit=200&city=Warszawa")).json();
  const multi = devs.items.find((d) => d.source_count > 1) ?? devs.items[0];
  const srcs = await (await fetch("/api/integrations")).json();
  const list = Array.isArray(srcs) ? srcs : (srcs.items ?? []);
  return { device: multi?.id, slug: list.find((s) => s.slug === "um-warszawa")?.slug ?? list[0]?.slug };
});
await probe.context().close();
if (process.env.DEVICE) ids.device = process.env.DEVICE;
if (process.env.SLUG) ids.slug = process.env.SLUG;
console.log("base", BASE, "ids", ids, "→", path.relative(REPO, outDir));

// optional: skipped (not counted) when the route answers 404, e.g. a page that is not merged yet
const PAGES = [
  { name: "home", path: "/", public: true },
  { name: "home-results", path: "/", public: true, action: searchNearest },
  { name: "export", path: "/export", public: true },
  { name: "docs", path: "/docs", public: true },
  { name: "docs-slownik-danych", path: "/docs/slownik-danych", public: true },
  { name: "docs-publikacja", path: "/docs/publikacja", public: true },
  { name: "docs-godziny-dostepnosci", path: "/docs/godziny-dostepnosci", public: true },
  { name: "developers", path: "/developers", public: true },
  { name: "report", path: "/zglos", public: true, optional: true },
  { name: "login", path: "/login", public: true },
  { name: "not-found", path: "/nie-ma-takiej-strony", public: true },
  { name: "panel", path: "/panel" },
  { name: "map", path: "/map" },
  { name: "devices", path: "/devices" },
  { name: "device-detail", path: `/devices/${ids.device}` },
  { name: "integrations", path: "/integrations" },
  { name: "integration-detail", path: `/integrations/${ids.slug}` },
  { name: "matches", path: "/matches" },
];

const summary = { axeVersion, base: BASE, tags: TAGS, date: new Date().toISOString(), ids, runs: [] };

for (const p of PAGES) {
  if (only && !only.test(p.name)) continue;
  for (const viewport of ["desktop", "mobile"]) {
    for (const theme of ["light", "dark"]) {
      const ctx = await newContext(browser, { viewport, theme, storageState: p.public ? undefined : auth });
      const page = await ctx.newPage();
      const consoleErrors = [];
      page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text().slice(0, 300)));
      try {
        const response = await page.goto(`${BASE}${p.path}`, { waitUntil: "domcontentloaded", timeout: 60000 });
        if (p.optional && response?.status() === 404) {
          console.log("skip", p.name, "(404)");
          await ctx.close();
          continue;
        }
        await settle(page, 2500);
        if (p.action) await p.action(page);
        await page.addScriptTag({ content: axeSource });
        const result = await page.evaluate(async (tags) => {
          // eslint-disable-next-line no-undef
          return await axe.run(document, { runOnly: { type: "tag", values: tags }, resultTypes: ["violations", "incomplete"] });
        }, TAGS);
        const title = await page.title();
        const counts = { critical: 0, serious: 0, moderate: 0, minor: 0 };
        const nodeCounts = { critical: 0, serious: 0, moderate: 0, minor: 0 };
        for (const v of result.violations) {
          counts[v.impact] += 1;
          nodeCounts[v.impact] += v.nodes.length;
        }
        const file = `${p.name}--${viewport}--${theme}.json`;
        fs.writeFileSync(
          path.join(outDir, file),
          JSON.stringify(
            {
              page: p.path,
              title,
              viewport,
              theme,
              testEngine: result.testEngine,
              timestamp: result.timestamp,
              url: result.url,
              violations: result.violations,
              incomplete: result.incomplete,
              passes: result.passes.map((r) => r.id),
            },
            null,
            1,
          ),
        );
        const rules = result.violations.map((v) => `${v.impact}:${v.id}(${v.nodes.length})`);
        summary.runs.push({
          page: p.name,
          path: p.path,
          title,
          viewport,
          theme,
          counts,
          nodeCounts,
          rules,
          incomplete: result.incomplete.map((v) => `${v.id}(${v.nodes.length})`),
          consoleErrors: consoleErrors.slice(0, 5),
          file,
        });
        console.log(p.name, viewport, theme, JSON.stringify(counts), rules.join(" "));
      } catch (e) {
        console.log("ERROR", p.name, viewport, theme, e.message.split("\n")[0]);
        summary.runs.push({ page: p.name, path: p.path, viewport, theme, error: e.message.split("\n")[0] });
      }
      await ctx.close();
    }
  }
}

const total = { critical: 0, serious: 0, moderate: 0, minor: 0 };
const totalNodes = { critical: 0, serious: 0, moderate: 0, minor: 0 };
const byRule = {};
for (const r of summary.runs) {
  if (!r.counts) continue;
  for (const k of Object.keys(total)) {
    total[k] += r.counts[k];
    totalNodes[k] += r.nodeCounts[k];
  }
  for (const s of r.rules) {
    const [, id, n] = s.match(/^\w+:(.+)\((\d+)\)$/);
    byRule[id] ??= { runs: 0, nodes: 0 };
    byRule[id].runs += 1;
    byRule[id].nodes += Number(n);
  }
}
summary.total = total;
summary.totalNodes = totalNodes;
summary.byRule = byRule;
fs.writeFileSync(path.join(outDir, "summary.json"), JSON.stringify(summary, null, 1));
console.log("TOTAL (rule violations per page-run)", total, "nodes", totalNodes);
console.log("BY RULE (page-runs / nodes)", byRule);
await browser.close();
const errors = summary.runs.filter((r) => r.error).length;
process.exitCode = errors ? 2 : 0;
