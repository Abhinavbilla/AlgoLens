// Which elements stick out past the viewport: node scripts/overflow.mjs <url> [width]
import { chromium } from "playwright";

const url = process.argv[2];
const width = Number(process.argv[3] ?? 375);
const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width, height: 900 } });
await page.goto(url);
await page.waitForLoadState("networkidle");
await page.waitForTimeout(800);
const found = await page.evaluate((w) => {
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.right > w + 1 && r.width > 0) {
      const cls = typeof el.className === "string" ? el.className : el.className.baseVal;
      out.push(`${el.tagName.toLowerCase()}.${cls.split(" ")[0]} right=${Math.round(r.right)} w=${Math.round(r.width)}`);
    }
  }
  return out.slice(0, 15);
}, width);
console.log(found.join("\n") || "nothing overflows");
await browser.close();
