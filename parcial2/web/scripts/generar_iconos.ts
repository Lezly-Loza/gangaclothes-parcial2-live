import { chromium } from '../node_modules/playwright/index.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const svg = readFileSync(new URL('../public/assets/icon.svg', import.meta.url), 'utf8');
const browser = await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
for (const size of [192,512]) {
  const page = await browser.newPage({viewport:{width:size,height:size},deviceScaleFactor:1});
  await page.setContent(`<style>html,body{margin:0;padding:0}svg{width:${size}px;height:${size}px}</style>${svg}`);
  await page.locator('svg').screenshot({path:fileURLToPath(new URL(`../public/assets/icon-${size}.png`,import.meta.url))});
  await page.close();
}
await browser.close();
