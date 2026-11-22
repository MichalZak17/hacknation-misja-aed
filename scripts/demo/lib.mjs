// Shared helpers for the demo recordings: a headed Chromium in kiosk mode on an Xvfb display, recorded by ffmpeg
// (x11grab, 30 fps), with a visible cursor drawn into the page and timed marks (captions, speed changes, cuts) that
// assemble.py turns into the final edit.
//
//   Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
//   FFMPEG=/path/to/ffmpeg node scene-<name>.mjs          # writes out/<name>.mkv + out/<name>.json
//   DRY=1 node scene-<name>.mjs                           # no recording, a screenshot per mark in out/dry-<name>/
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const OUT = path.join(HERE, "out");
const DRY = !!process.env.DRY;
const DISPLAY = process.env.DISPLAY_NUM ?? ":99";
const W = 1920;
const H = 1080;
// Chrome's tab strip + toolbar; without a window manager --kiosk does nothing, so the window starts above the screen
const CHROME_TOP = Number(process.env.CHROME_TOP ?? 87);

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A cursor the viewer can follow: an arrow that tracks mousemove, with a ring on click. Lives in every frame's DOM, so
// it survives navigation once the next mouse move arrives (see Scene.park).
const CURSOR = `
(() => {
  const install = () => {
    if (document.getElementById('__demo_cursor')) return;
    const c = document.createElement('div');
    c.id = '__demo_cursor';
    c.innerHTML = '<svg width="34" height="34" viewBox="0 0 24 24"><path d="M4 2l15 9.5-6.6 1.3L16.8 21l-3 1.4-4.3-8.3L4 18.9z" fill="#14202e" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:'2147483647', pointerEvents:'none',
      transform:'translate(-200px,-200px)', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
    const r = document.createElement('div');
    r.id = '__demo_ring';
    Object.assign(r.style, {position:'fixed', left:'0', top:'0', width:'44px', height:'44px', marginLeft:'-22px',
      marginTop:'-22px', borderRadius:'50%', border:'3px solid #e4002b', zIndex:'2147483646', pointerEvents:'none',
      opacity:'0', transform:'translate(-200px,-200px) scale(.4)', transition:'opacity .35s, transform .35s'});
    document.documentElement.append(r, c);
    let x = -200, y = -200;
    addEventListener('mousemove', (e) => { x = e.clientX; y = e.clientY; c.style.display = ''; c.style.transform = 'translate(' + (x - 4) + 'px,' + (y - 2) + 'px)'; }, true);
    // an iframe draws its own cursor: hide this one while the pointer is over it
    addEventListener('mouseover', (e) => { if (e.target && e.target.tagName === 'IFRAME') c.style.display = 'none'; }, true);
    addEventListener('mousedown', () => {
      r.style.transition = 'none'; r.style.opacity = '1'; r.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(.4)';
      requestAnimationFrame(() => { r.style.transition = 'opacity .45s, transform .45s'; r.style.opacity = '0'; r.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(1.4)'; });
    }, true);
  };
  if (document.documentElement) install(); else addEventListener('DOMContentLoaded', install);
  addEventListener('DOMContentLoaded', install);
})();`;

export class Scene {
  constructor(name) {
    this.name = name;
    this.marks = [];
    this.mx = W / 2;
    this.my = H / 2;
    this.shot = 0;
    // optional (x, y) => [x, y] for targets inside a CSS-scaled iframe (Playwright's boxes ignore the scale)
    this.xform = null;
  }

  // clock: fixed wall time for the pages (e.g. a night scene recorded by day); padBottom: extra window height below the
  // screen, so Chromium's link-hover status bubble (bottom-left of the viewport) is drawn off-screen
  async start({ cookies = [], geolocation, clock, padBottom = 0 } = {}) {
    fs.mkdirSync(OUT, { recursive: true });
    this.browser = await chromium.launch({
      headless: false,
      env: { ...process.env, DISPLAY },
      ignoreDefaultArgs: ["--enable-automation"],
      args: [`--window-size=${W},${H + CHROME_TOP + padBottom}`, `--window-position=0,-${CHROME_TOP}`, "--force-device-scale-factor=1",
        "--disable-features=Translate,MediaRouter", "--no-first-run", "--password-store=basic"],
    });
    this.ctx = await this.browser.newContext({
      viewport: null,
      locale: "pl-PL",
      timezoneId: "Europe/Warsaw",
      ...(geolocation ? { geolocation, permissions: ["geolocation"] } : {}),
    });
    if (cookies.length) await this.ctx.addCookies(cookies);
    if (clock) await this.ctx.clock.setFixedTime(new Date(clock));
    await this.ctx.addInitScript(CURSOR);
    this.page = await this.ctx.newPage();
    // a neutral frame to start the recording on
    await this.page.setContent('<body style="margin:0;background:#f4f5f7"></body>');
    if (DRY) {
      this.dryDir = path.join(OUT, `dry-${this.name}`);
      fs.rmSync(this.dryDir, { recursive: true, force: true });
      fs.mkdirSync(this.dryDir, { recursive: true });
      return this.page;
    }
    const ffmpeg = process.env.FFMPEG ?? "ffmpeg";
    this.video = path.join(OUT, `${this.name}.mkv`);
    // -copyts keeps wall-clock timestamps, so the marks (Date.now) line up with the frames exactly
    this.ff = spawn(ffmpeg, ["-y", "-hide_banner", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0",
      "-framerate", "30", "-video_size", `${W}x${H}`, "-use_wallclock_as_timestamps", "1", "-i", `${DISPLAY}.0`,
      "-copyts", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14", "-pix_fmt", "yuv420p", this.video],
      { stdio: ["pipe", "inherit", "inherit"] });
    await sleep(1500);
    return this.page;
  }

  now() {
    return Date.now() / 1000;
  }

  /** Caption shown from now until the next caption (or cap(null)). */
  async cap(text, sub = null) {
    this.marks.push({ t: this.now(), cap: text, sub });
    if (DRY) await this.page.screenshot({ path: path.join(this.dryDir, `${String(++this.shot).padStart(2, "0")}.png`) });
  }

  /** Playback speed from now on (assemble.py), e.g. speed(8) for a timelapse and speed(1) after. */
  speed(x, label = null) {
    this.marks.push({ t: this.now(), speed: x, label });
  }

  /** Drop everything from cutStart() to cutEnd() (loading, waiting). */
  cutStart() {
    this.marks.push({ t: this.now(), cut: "start" });
  }
  cutEnd() {
    this.marks.push({ t: this.now(), cut: "end" });
  }

  async snap(label) {
    if (DRY) await this.page.screenshot({ path: path.join(this.dryDir, `${String(++this.shot).padStart(2, "0")}-${label}.png`) });
  }

  async moveTo(x, y, ms = 650) {
    const steps = Math.max(8, Math.round(ms / 16));
    const sx = this.mx;
    const sy = this.my;
    for (let i = 1; i <= steps; i++) {
      const k = i / steps;
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      await this.page.mouse.move(sx + (x - sx) * e, sy + (y - sy) * e);
      await sleep(ms / steps);
    }
    this.mx = x;
    this.my = y;
  }

  /** Re-show the cursor after a navigation (the new document has not seen a mousemove yet). */
  async park() {
    await this.page.mouse.move(this.mx + 1, this.my);
    await this.page.mouse.move(this.mx, this.my);
  }

  async hover(locator, ms = 650) {
    await locator.scrollIntoViewIfNeeded();
    const b = await locator.boundingBox();
    if (!b) throw new Error(`not visible: ${locator}`);
    const [x, y] = this.xform ? this.xform(b.x + b.width / 2, b.y + b.height / 2) : [b.x + b.width / 2, b.y + b.height / 2];
    await this.moveTo(x, y, ms);
  }

  async click(locator, { ms = 650, pause = 220 } = {}) {
    await this.hover(locator, ms);
    await sleep(pause);
    await this.page.mouse.down();
    await sleep(70);
    await this.page.mouse.up();
  }

  async type(locator, text, delay = 65) {
    await this.click(locator);
    await sleep(200);
    await this.page.keyboard.type(text, { delay });
  }

  /** Smooth wheel scroll by dy pixels over ms. */
  async scroll(dy, ms = 900) {
    const steps = Math.max(6, Math.round(ms / 30));
    for (let i = 0; i < steps; i++) {
      await this.page.mouse.wheel(0, dy / steps);
      await sleep(ms / steps);
    }
  }

  async goto(url, wait = "networkidle") {
    await this.page.goto(url, { waitUntil: wait, timeout: 60000 }).catch(async (e) => {
      if (!String(e).includes("Timeout")) throw e;
    });
    await this.park();
  }

  async stop() {
    await sleep(600);
    if (this.ff) {
      this.ff.stdin.write("q");
      await new Promise((r) => this.ff.on("close", r));
    }
    fs.writeFileSync(path.join(OUT, `${this.name}.json`), JSON.stringify({ name: this.name, marks: this.marks }, null, 2));
    await this.browser.close();
  }
}

/** Run a scene function, stopping the recording even when a step fails. */
export async function run(name, fn, opts) {
  const s = new Scene(name);
  const page = await s.start(opts);
  try {
    await fn(s, page);
  } catch (e) {
    await page.screenshot({ path: path.join(OUT, `fail-${name}.png`) }).catch(() => {});
    await s.stop().catch(() => {});
    console.error(e);
    process.exit(1);
  }
  await s.stop();
  console.log(`scene ${name}: ${s.marks.length} marks`);
}

export function readEnvFile(file) {
  const env = {};
  try {
    for (const line of fs.readFileSync(file, "utf8").split("\n")) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  } catch {}
  return env;
}
