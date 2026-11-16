import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(work, 'css-shared/.local-notes/exports/portrait-grid');
fs.mkdirSync(output, { recursive: true });
const inventory = JSON.parse(fs.readFileSync(path.join(work, 'review/_site/grids-inventory.json')));
const patterns = inventory.patterns.filter(p => p.classes === 'portrait-card-grid');
if (patterns.length !== 1) throw new Error('Review must show one Portrait Card Grid.');
const browser = await chromium.launch({ executablePath: process.env.GRID_BROWSER || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const context = await browser.newContext({ reducedMotion: 'reduce' });
await context.route('https://**', route => route.request().url().endsWith('bootstrap.min.css') && process.env.GRID_BOOTSTRAP_CSS ? route.fulfill({ path: process.env.GRID_BOOTSTRAP_CSS, contentType: 'text/css' }) : route.abort());
await context.route('http://*.portrait.test/**', route => {
const url = new URL(route.request().url());
const file = path.join(work, url.hostname.split('.')[0], '_site', decodeURIComponent(url.pathname), url.pathname.endsWith('/') ? 'index.html' : '');
return route.fulfill(fs.existsSync(file) ? { path: file } : { status: 404, body: 'Missing local asset' });
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push({ url: page.url(), message: error.message }));
const readings = [];
async function inspect(unit, url, width, enlarged = false) {
await page.setViewportSize({ width, height: 1000 });
await page.goto(`http://${unit}.portrait.test${url}`, { waitUntil: 'load' });
if (unit === 'review') await page.getByRole('tab', { name: 'Portrait Card Grid', exact: true }).click();
if (enlarged) await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
await page.evaluate(() => document.fonts.ready);
const result = await page.evaluate(() => {
const columns = innerWidth >= 1600 ? 5 : innerWidth >= 1200 ? 4 : innerWidth >= 992 ? 3 : innerWidth >= 768 ? 2 : 1;
const grids = [...document.querySelectorAll('.portrait-card-grid')].filter(grid => grid.getClientRects().length).map(grid => {
const style = getComputedStyle(grid), rect = grid.getBoundingClientRect();
const cards = [...grid.children].map(child => { const r = child.getBoundingClientRect(); return { width: r.width, left: r.left, top: r.top, bottom: r.bottom }; });
const rows = [];
for (const card of cards) {
let row = rows.find(r => Math.abs(r[0].top - card.top) < 1);
if (!row) rows.push(row = []);
row.push(card);
}
const targetWidth = (rect.width - (columns - 1) * 33) / columns;
const horizontal = rows.every(row => Math.abs(row[0].left - rect.left) < 1 && row.every((card, i) => i === 0 || Math.abs(card.left - row[i - 1].left - card.width - 33) < 1));
const vertical = rows.every((row, i) => i === 0 || Math.abs(row[0].top - Math.max(...rows[i - 1].map(card => card.bottom)) - 33) < 1);
const images = [...grid.querySelectorAll('.profile-directory-photo')].map(img => ({ width: img.getBoundingClientRect().width, parent: img.closest('.profile-link').getBoundingClientRect().width }));
const photosFit = images.every(img => Math.abs(img.width / img.parent - (innerWidth < 768 ? .75 : 1)) < .01);
const pass = style.display === 'grid' && style.gridTemplateColumns.split(' ').length === columns && style.columnGap === '33px' && style.rowGap === '33px' && cards.every(card => Math.abs(card.width - targetWidth) < 1) && horizontal && vertical && photosFit;
return { columns, cardCount: cards.length, width: rect.width, gap: style.gap, targetWidth, rows: rows.map(row => row.length), horizontal, vertical, photosFit, pass };
});
return { overflow: document.documentElement.scrollWidth > innerWidth + 1, grids };
});
readings.push({ unit, url, width, enlarged, ...result });
if (unit === 'review' && !enlarged && [375, 820, 1200, 1800].includes(width)) await page.locator('.portrait-card-grid').screenshot({ path: path.join(output, `portrait-grid-${width}.png`) });
}
try {
for (const use of patterns[0].uses) for (const width of [375, 768, 992, 1200, 1600]) await inspect(use.unit, use.url, width);
for (const width of [320, 375, 575, 576, 767, 768, 820, 991, 992, 1199, 1200, 1599, 1600, 1800]) await inspect('review', '/grids.html', width);
for (const width of [375, 820, 1200, 1800]) await inspect('review', '/grids.html', width, true);
const failures = readings.filter(r => r.overflow || !r.grids.length || r.grids.some(grid => !grid.pass));
const summary = { consumerPages: patterns[0].uses.length, cases: readings.length, gridMeasurements: readings.reduce((sum, r) => sum + r.grids.length, 0), failures, errors };
fs.writeFileSync(path.join(output, 'layout-audit.json'), JSON.stringify({ date: '2026-11-16', browser: browser.version(), summary, readings }, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
if (failures.length || errors.length) process.exitCode = 1;
} finally {
await browser.close();
}
