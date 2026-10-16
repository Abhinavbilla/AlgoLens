// Email sign-in end to end, with ALGOLENS_EMAIL_DEV_LOG on (the code is read from the API log):
// node scripts/signin-shots.mjs <out> [base]
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://localhost:8080";
const email = `trial.${Date.now()}@example.com`;
mkdirSync(out, { recursive: true });

function codeFromLog() {
  const log = execFileSync("wsl", ["-d", "Ubuntu", "-e", "sh", "-c",
    "cd /mnt/d/AlgolLens && docker compose logs api --since 2m 2>&1"]).toString().replace(/\0/g, "");
  const m = [...log.matchAll(new RegExp(`sign-in code for ${email.replace(/\./g, "\\.")} is (\\d{6})`, "g"))];
  return m.length ? m[m.length - 1][1] : null;
}

const browser = await chromium.launch({ channel: "msedge" });
for (const width of [1280, 375]) {
  const page = await browser.newPage({ viewport: { width, height: 860 } });
  await page.goto(base + "/library/kadane");
  await page.getByRole("link", { name: "Log in" }).click();
  await page.getByLabel(/your email/i).waitFor();
  await page.screenshot({ path: join(out, `signin-${width}.png`) });
  if (width === 1280) {
    await page.getByLabel(/your email/i).fill(email);
    await page.getByRole("button", { name: /with email/i }).click();
    await page.getByText(/code sent to/i).waitFor();
    await page.screenshot({ path: join(out, `code-${width}.png`) });
    let code = null;
    for (let i = 0; i < 10 && !code; i++) {
      await page.waitForTimeout(500);
      code = codeFromLog();
    }
    if (!code) throw new Error("no code in the log");
    await page.getByLabel("Code").fill(code);
    await page.getByRole("button", { name: "Verify & log in" }).click();
    await page.waitForURL(/\/library\/kadane$/);
    await page.getByRole("link", { name: /your account/i }).waitFor();
    console.log("signed in and back on", new URL(page.url()).pathname);
    await page.getByRole("link", { name: /your account/i }).click();
    await page.getByRole("button", { name: "Sign out" }).waitFor();
    await page.screenshot({ path: join(out, `account-${width}.png`) });
    // Clean up: this was only a trial account.
    await page.getByRole("button", { name: /delete my account/i }).click();
    await page.getByRole("button", { name: /yes, delete everything/i }).click();
    await page.getByText(/continue without an account/i).waitFor();
    console.log("trial account deleted");
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 0) console.log(`${width}: scrolls sideways by ${overflow}px`);
  await page.close();
}
await browser.close();
console.log("done");
