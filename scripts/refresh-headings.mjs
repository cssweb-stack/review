import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const workspace = path.dirname(project);
const units = JSON.parse(fs.readFileSync(path.join(workspace, 'css-shared/src/data/common/review-units.json'), 'utf8')).current;
const requested = [...new Set(process.argv.slice(2))];
if (!requested.length || requested.some(unit => !units.includes(unit))) {
throw new Error('Specify affected reviewed unit(s), for example: npm run refresh:headings -- geo');
}
const start = performance.now();
for (const unit of requested) {
execFileSync('npm', ['run', 'build'], { cwd: path.join(workspace, unit), stdio: 'pipe' });
}
execFileSync(process.execPath, ['node_modules/@11ty/eleventy/cmd.cjs'], {
cwd: project,
env: { ...process.env, REVIEW_HEADINGS_ONLY: '1' },
stdio: 'pipe'
});
for (const unit of requested) {
if (!fs.existsSync(path.join(project, '_site/headings', unit + '.html'))) {
throw new Error('Missing rebuilt Review naming page for ' + unit);
}
}
console.log('Rebuilt ' + requested.join(', ') + ' and Review naming pages in ' + ((performance.now() - start) / 1000).toFixed(1) + ' seconds. Refresh the browser.');
