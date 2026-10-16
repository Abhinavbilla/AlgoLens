// Screenshots of the tutor panel in use: node scripts/tutor-shots.mjs <out> [base]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://localhost:8080";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "msedge" });
for (const [theme, width] of [["light", 1280], ["dark", 1280], ["light", 375]]) {
  const page = await browser.newPage({ viewport: { width, height: 860 }, colorScheme: theme });
  await page.goto(base + "/library/kadane");
  await page.waitForLoadState("networkidle");
  const name = (s) => join(out, `tutor-${s}-${theme}-${width}.png`);
  await page.screenshot({ path: name("launcher") });
  // Step forward a few times, then ask about that step.
  for (let i = 0; i < 4; i++) await page.locator("button[aria-keyshortcuts=ArrowRight]").click();
  await page.getByRole("button", { name: "Ask about this step" }).click();
  await page.getByRole("button", { name: "Send" }).click();
  await page.locator('[aria-label="The tutor is thinking"]').waitFor({ state: "detached", timeout: 60000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: name("chat") });
  await page.getByRole("tab", { name: "Check my code" }).click();
  await page.getByRole("textbox", { name: /your python code/i }).fill(
    "def max_subarray(nums):\n    best = 0\n    current = 0\n    for x in nums:\n        current = max(x, current + x)\n        best = max(best, current)\n    return best\n",
  );
  await page.getByRole("button", { name: "Run the tests" }).click();
  await page.getByText("Not yet").waitFor({ timeout: 60000 });
  await page.screenshot({ path: name("check") });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 0) console.log(`${theme} ${width}: scrolls sideways by ${overflow}px`);
  await page.close();
}
await browser.close();
console.log("done");
