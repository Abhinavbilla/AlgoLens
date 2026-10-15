// Quick screenshots of a few pages for design review: node scripts/shots.mjs <out> [base]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://localhost:8080";
const pages = process.argv.slice(4).length ? process.argv.slice(4) : ["/", "/library/merge-sort", "/solve"];
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "msedge" });
for (const theme of ["light", "dark"]) {
  for (const width of [1280, 375]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: theme });
    for (const path of pages) {
      await page.goto(base + path);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(800);
      const name = `${path.replace(/[^a-z0-9]+/gi, "_") || "home"}-${theme}-${width}.png`;
      await page.screenshot({ path: join(out, name), fullPage: path === "/" });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow > 0) console.log(`${name}: scrolls sideways by ${overflow}px`);
    }
    await page.close();
  }
}
await browser.close();
console.log("done");
