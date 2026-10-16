// Checks a pasted problem's player highlights the C++ line too:
// node scripts/cpp-highlight.mjs <out> <problem id> [base]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [out = "shots", problemId, base = "http://localhost:8080"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto(`${base}/problems/${problemId}`);
await page.getByRole("button", { name: /watch it run step by step/i }).last().click();
for (let i = 0; i < 5; i++) await page.locator("button[aria-keyshortcuts=ArrowRight]").click();
await page.getByRole("region", { name: "Code" }).getByRole("button", { name: "C++" }).click();
const current = await page.evaluate(() => {
  const el = document.querySelector('section[aria-label="Code"] [aria-current="step"]');
  return el ? el.textContent?.trim().slice(0, 80) : null;
});
console.log("highlighted C++ line:", current);
await page.locator("#player, [class*=layout]").last().scrollIntoViewIfNeeded();
await page.screenshot({ path: join(out, "cpp-highlight.png") });
await browser.close();
