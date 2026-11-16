import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(work, 'css-shared/.local-notes/exports/sidebars');
fs.mkdirSync(output, { recursive: true });
const inventory = JSON.parse(fs.readFileSync(path.join(work, 'review/_site/grids-inventory.json')));
const classes = ['left', 'right'].flatMap(side => ['sm', 'med', 'large'].map(size => `sidebar-${side}-${size}`));
const patterns = inventory.patterns.filter(p => classes.includes(p.classes));
if (patterns.length !== 6) throw new Error('Review must show exactly three left and three right sidebars.');
const cases = [...new Map(patterns.flatMap(p => p.uses).map(use => [use.unit + use.url, use])).values()];
const browser = await chromium.launch({ executablePath: process.env.GRID_BROWSER || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const context = await browser.newContext({ reducedMotion: 'reduce' });
await context.route('https://**', route => route.request().url().endsWith('bootstrap.min.css') && process.env.GRID_BOOTSTRAP_CSS ? route.fulfill({ path: process.env.GRID_BOOTSTRAP_CSS, contentType: 'text/css' }) : route.abort());
await context.route('http://*.sidebar.test/**', route => {
const url = new URL(route.request().url());
const unit = url.hostname.split('.')[0];
const name = decodeURIComponent(url.pathname) + (url.pathname.endsWith('/') ? 'index.html' : '');
const file = path.join(work, unit, '_site', name);
return route.fulfill(fs.existsSync(file) ? { path: file } : { status: 404, body: 'Missing local asset' });
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push({ url: page.url(), message: error.message }));
const readings = [];
async function inspect(unit, url, width) {
await page.setViewportSize({ width, height: 1000 });
await page.goto(`http://${unit}.sidebar.test${url}`, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
const result = await page.evaluate(classes => {
const grids = [...document.querySelectorAll(classes.map(c => '.' + c).join(','))].filter(grid => grid.getClientRects().length);
return { overflow: document.documentElement.scrollWidth > innerWidth + 1, grids: grids.map(grid => {
const cls = classes.find(c => grid.classList.contains(c));
const style = getComputedStyle(grid);
const rect = grid.getBoundingClientRect();
const children = [...grid.children].map(child => { const r = child.getBoundingClientRect(); return { width: r.width, left: r.left, right: r.right, top: r.top, bottom: r.bottom }; });
const gap = parseFloat(style.columnGap);
const expectedRatio = innerWidth < 768 ? 1 : innerWidth < 992 ? .33 : innerWidth < 1600 ? .25 : { sm: .17, med: .20, large: .25 }[cls.split('-').at(-1)];
const stacked = innerWidth < 768;
const sidebar = children[cls.startsWith('sidebar-right-') ? 1 : 0];
const ratio = sidebar.width / (rect.width - (stacked ? 0 : gap));
const actualGap = stacked ? children[1]?.top - children[0].bottom : children[1]?.left - children[0].right;
const pass = style.display === 'grid' && style.columnGap === '33px' && style.rowGap === '33px' && children.length === 2 && Math.abs(ratio - expectedRatio) < .002 && Math.abs(actualGap - 33) < 1 && (!stacked || Math.abs(children[1].width - rect.width) < 1);
return { cls, width: rect.width, columns: style.gridTemplateColumns, gap: style.gap, expectedRatio, ratio, actualGap, pass };
}) };
}, classes);
readings.push({ unit, url, width, ...result });
}
try {
for (const use of cases) {
for (const width of [375, 820, 1024, 1800]) await inspect(use.unit, use.url, width);
}
for (const width of [320, 767, 768, 991, 992, 1599, 1600]) await inspect('review', '/grids.html', width);
await page.setViewportSize({ width: 820, height: 1000 });
await page.goto('http://review.sidebar.test/grids.html', { waitUntil: 'load' });
await page.locator('#sidebars').screenshot({ path: path.join(output, 'review-sidebars-820.png') });
const failures = readings.filter(r => r.overflow || !r.grids.length || r.grids.some(g => !g.pass));
const summary = { consumerPages: cases.length, cases: readings.length, gridMeasurements: readings.reduce((sum, r) => sum + r.grids.length, 0), failures, errors };
fs.writeFileSync(path.join(output, 'layout-audit.json'), JSON.stringify({ date: '2026-11-16', browser: browser.version(), summary, readings }, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 2));
if (failures.length || errors.length) process.exitCode = 1;
} finally {
await browser.close();
}
