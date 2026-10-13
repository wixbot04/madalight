// Exporte l'affiche au format Facebook (4:5, 1080 × 1350).
//   node communication/facebook-liane/render.mjs
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

// require() suit NODE_PATH, ce qui permet d'utiliser un Playwright installé globalement.
const { chromium } = createRequire(import.meta.url)("playwright");

const ici = path.dirname(fileURLToPath(import.meta.url));
const sortie = path.join(ici, "export", "madalight-facebook-1080x1350");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(ici, "affiche.html")).href);
await page.evaluate(() => document.fonts.ready);
await page.waitForLoadState("networkidle");
const affiche = page.locator(".affiche");
// PNG pour l'archive et les retouches, JPEG léger pour la publication.
await affiche.screenshot({ path: `${sortie}.png` });
await affiche.screenshot({ path: `${sortie}.jpg`, type: "jpeg", quality: 92 });
await browser.close();
console.log(`${sortie}.png\n${sortie}.jpg`);
