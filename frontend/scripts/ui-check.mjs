// Screenshots and layout checks for the library pages, using the system's Microsoft Edge
// (no browser download needed). The stack must be running: docker compose up.
//
//   node scripts/ui-check.mjs <output-dir> [base-url]
//
// For every entry, width (375, 1280) and theme (light, dark) it saves screenshots and, at
// every step of the animation, checks:
//   - the page never scrolls sideways (document wider than the window)
//   - pointer labels never overlap each other
//   - the narration box and the panels below it don't move between steps
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const out = process.argv[2] ?? "ui-check";
const base = process.argv[3] ?? "http://localhost:8080";
// Every library entry, as the API lists them.
const SLUGS = (await (await fetch(`${base}/api/library`)).json()).map((e) => e.slug);
const WIDTHS = [375, 1280];
const THEMES = ["light", "dark"];
mkdirSync(out, { recursive: true });

const problems = [];
const report = (where, what) => problems.push(`${where}: ${what}`);

const browser = await chromium.launch({ channel: "msedge" });

async function measure(page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    const rects = [...document.querySelectorAll("[data-pointer]")].map((el) => ({
      label: el.dataset.pointer,
      r: el.getBoundingClientRect(),
      clipped: el.scrollWidth > el.clientWidth + 1,
    }));
    const overlaps = [];
    for (let i = 0; i < rects.length; i++)
      for (let j = i + 1; j < rects.length; j++) {
        const a = rects[i].r, b = rects[j].r;
        if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5)
          overlaps.push(`${rects[i].label}/${rects[j].label}`);
      }
    const narration = document.querySelector("[data-current-narration]")?.closest("[aria-live]");
    const firstPanel = document.querySelector('section[aria-label]:not([aria-label="Code"]):not([aria-label="Call stack"])');
    const controls = document.querySelector('[role="group"][aria-label="Playback"]');
    return {
      overflow: doc.scrollWidth - window.innerWidth,
      overlaps,
      clipped: rects.filter((r) => r.clipped).map((r) => r.label),
      narrationHeight: narration?.getBoundingClientRect().height ?? 0,
      panelTop: firstPanel ? firstPanel.getBoundingClientRect().top + window.scrollY : 0,
      controlsTop: controls ? controls.getBoundingClientRect().top + window.scrollY : 0,
      text: document.querySelector("[data-current-narration] p")?.textContent ?? "",
    };
  });
}

for (const theme of THEMES) {
  for (const width of WIDTHS) {
    const context = await browser.newContext({
      viewport: { width, height: width < 600 ? 812 : 900 },
      colorScheme: theme,
    });
    const page = await context.newPage();
    const tag = `${theme}-${width}`;

    await page.goto(`${base}/`);
    await page.getByRole("heading", { name: "Algorithm library" }).waitFor();
    await page.locator("li a").first().waitFor();
    if ((await measure(page)).overflow > 0) report(`library ${tag}`, "page scrolls sideways");
    await page.screenshot({ path: join(out, `library-${tag}.png`), fullPage: true });

    for (const slug of SLUGS) {
      await page.goto(`${base}/library/${slug}`);
      await page.getByRole("slider", { name: "Step" }).waitFor();
      const count = Number(await page.getByRole("slider", { name: "Step" }).getAttribute("max")) + 1;
      await page.screenshot({ path: join(out, `${slug}-${tag}-start.png`), fullPage: true });
      const first = await measure(page);
      const heights = new Set(), panelTops = new Set(), controlTops = new Set();
      let longest = "";
      for (let i = 0; i < count; i++) {
        const m = await measure(page);
        const where = `${slug} ${tag} step ${i + 1}`;
        if (m.overflow > 0) report(where, `page scrolls sideways by ${m.overflow}px`);
        if (m.overlaps.length) report(where, `pointer labels overlap: ${m.overlaps.join(", ")}`);
        if (m.clipped.length) report(where, `pointer labels clipped: ${m.clipped.join(", ")}`);
        heights.add(Math.round(m.narrationHeight));
        panelTops.add(Math.round(m.panelTop));
        controlTops.add(Math.round(m.controlsTop));
        if (m.text.length > longest.length) longest = m.text;
        if (m.overlaps.length && !problems.some((p) => p.startsWith(`${slug} ${tag}`) && p.includes("shot")))
          await page.screenshot({ path: join(out, `${slug}-${tag}-overlap-step${i + 1}.png`), fullPage: true });
        await page.keyboard.press("ArrowRight");
      }
      if (heights.size > 1) report(`${slug} ${tag}`, `narration box changes height between steps: ${[...heights].join(", ")}px`);
      if (panelTops.size > 1) report(`${slug} ${tag}`, `panels move between steps: tops ${[...panelTops].join(", ")}px`);
      if (controlTops.size > 1) report(`${slug} ${tag}`, `controls move between steps: tops ${[...controlTops].join(", ")}px`);
      await page.screenshot({ path: join(out, `${slug}-${tag}-end.png`), fullPage: true });
      writeFileSync(join(out, `${slug}-${tag}.txt`), `${count} steps; first: ${first.text}\nlongest: ${longest}\n`);
    }
    await context.close();
  }
}
await browser.close();

writeFileSync(join(out, "problems.txt"), problems.join("\n") + "\n");
console.log(problems.length ? `${problems.length} problem(s):\n` + [...new Set(problems)].slice(0, 60).join("\n") : "no problems found");
