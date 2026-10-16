// Screenshots of the sign-in box: node scripts/signin-box.mjs <out> [base]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://localhost:8080";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: "msedge" });
for (const [theme, width] of [["light", 1280], ["dark", 1280], ["light", 375]]) {
  const page = await browser.newPage({ viewport: { width, height: 820 }, colorScheme: theme });
  await page.goto(base + "/account?next=/library/kadane");
  await page.getByRole("button", { name: /with google/i }).waitFor();
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(out, `box-${theme}-${width}.png`) });
  if (width === 1280 && theme === "light") {
    await page.getByRole("button", { name: "Sign up", pressed: false }).click();
    await page.getByRole("heading", { name: "Create your account" }).waitFor();
    await page.waitForTimeout(300);
    await page.screenshot({ path: join(out, `box-signup-${width}.png`) });
    await page.getByRole("button", { name: "Log in", pressed: false }).click();
    await page.getByLabel(/your email/i).fill("someone@example.com");
    await page.getByRole("button", { name: /with email/i }).click();
    await page.getByText(/code sent to/i).waitFor();
    await page.screenshot({ path: join(out, `box-code-${width}.png`) });
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 0) console.log(`${theme} ${width}: scrolls sideways by ${overflow}px`);
  await page.close();
}
await browser.close();
console.log("done");
