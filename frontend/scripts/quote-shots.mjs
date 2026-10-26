// Screenshots of the waiting page's quote card, with a mocked job:
//   node scripts/quote-shots.mjs <out> [base]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://localhost:5199";
mkdirSync(out, { recursive: true });

const job = {
  id: "demo", status: "queued", stage: "waiting in the queue", tests_passed: 0, tests_total: 0,
  error: "", problem_id: null, queue: { ahead: 2, wait_s: 300, typical_s: 180 },
};

const browser = await chromium.launch({ channel: "msedge" });
for (const [theme, width] of [["light", 1280], ["dark", 1280], ["light", 375]]) {
  const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: theme });
  await page.route("**/api/jobs/demo/events", (r) =>
    r.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify(job)}\n\n` }),
  );
  await page.route("**/api/jobs/demo", (r) => r.fulfill({ json: job }));
  await page.route("**/api/health", (r) => r.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({ json: { enabled: false, google: false, email: false, user: null } }),
  );
  await page.goto(base + "/jobs/demo");
  await page.getByRole("figure").waitFor();
  await page.waitForTimeout(900);
  await page.screenshot({ path: join(out, `quote-${theme}-${width}.png`) });
  await page.close();
}
await browser.close();
