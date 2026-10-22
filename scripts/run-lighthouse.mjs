import lighthouse from "lighthouse";
import { chromium } from "playwright";
import * as chromeLauncher from "chrome-launcher";

const url = process.argv[2];
if (!url) {
  console.error("A URL is required");
  process.exit(2);
}

const chrome = await chromeLauncher.launch({
  chromePath: chromium.executablePath(),
  chromeFlags: ["--headless", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
});
let result;
try {
  result = await lighthouse(url, {
    port: chrome.port,
    output: "json",
    logLevel: "error",
    onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
    throttlingMethod: "simulate",
  });
} finally {
  await chrome.kill();
}

if (!result?.lhr) {
  console.error("Lighthouse returned no report");
  process.exit(1);
}

const { lhr } = result;
const audit = (id) => lhr.audits?.[id]?.numericValue ?? null;
const score = (id) => {
  const value = lhr.categories?.[id]?.score;
  return typeof value === "number" ? Math.round(value * 100) : null;
};

process.stdout.write(JSON.stringify({
  performance: score("performance"),
  accessibility: score("accessibility"),
  best_practices: score("best-practices"),
  seo: score("seo"),
  lcp_ms: audit("largest-contentful-paint"),
  cls: audit("cumulative-layout-shift"),
  inp_ms: audit("interaction-to-next-paint"),
  fcp_ms: audit("first-contentful-paint"),
  tbt_ms: audit("total-blocking-time"),
  speed_index_ms: audit("speed-index"),
}));
