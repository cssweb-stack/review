import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import nunjucks from 'nunjucks';
import { build } from 'esbuild';
import { EleventyRenderPlugin } from '@11ty/eleventy';
import { formatGeneratedHtml } from '../css-shared/scripts/unit-site/html-format.mjs';
const project = path.dirname(fileURLToPath(import.meta.url));
const shared = path.resolve(project, '../css-shared/src');
const headingsOnly = process.env.REVIEW_HEADINGS_ONLY === '1';
const reviewInput = headingsOnly ? '_generated/headings' : '_generated';
const reviewOutput = headingsOnly ? '_site/headings' : '_site';
const pathPrefix = '/' + (process.env.SITE_PATH_PREFIX || '').split('/').filter(Boolean).join('/') + '/';
const prefix = pathPrefix === '//' ? '/' : pathPrefix;
const reviewUrl = value => typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && prefix !== '/' && !value.startsWith(prefix) ? prefix + value.slice(1) : value;

export default function(eleventyConfig) {
eleventyConfig.setUseGitIgnore(false);
eleventyConfig.addPlugin(EleventyRenderPlugin);
// Read the user's source afresh on every render; never cache or write this document.
eleventyConfig.addFilter('readRuleDocument', filename => {
if (!['code-cleanup.md', 'language-writing.md'].includes(filename)) throw new Error('Unknown rule document');
return fs.readFileSync(path.join(shared, '../docs/rules', filename), 'utf8').replace(/^# [^\r\n]+\r?\n/, '').trimStart();
});
if (['serve', 'watch'].includes(process.env.ELEVENTY_RUN_MODE)) eleventyConfig.setUseTemplateCache(false);
eleventyConfig.addGlobalData('eleventyComputed', {
permalink: data => `${data.page.filePathStem}.html`
});
eleventyConfig.setServerOptions({
domDiff: false,
messageOnStart: ({ localhostUrl }) => { console.log(`Local server: ${localhostUrl}`); return false; }
});
const environment = new nunjucks.Environment(new nunjucks.FileSystemLoader([path.join(shared, 'includes'), shared], { noCache: true }), { autoescape: false });
eleventyConfig.setLibrary('njk', environment);
eleventyConfig.addTransform('formatGeneratedHtml', function(content) {
return this.page.outputPath?.endsWith('.html') ? formatGeneratedHtml(content) : content;
});
eleventyConfig.addFilter('url', reviewUrl);
eleventyConfig.addFilter('telephone', value => {
const cleaned = String(value || '').replace(/[^\d+]/g, '');
if (/^\d{10}$/.test(cleaned)) return '+1' + cleaned;
if (/^1\d{10}$/.test(cleaned)) return '+' + cleaned;
return cleaned;
});
eleventyConfig.addTransform('reviewProjectUrls', function(content) {
if (!this.page.outputPath?.endsWith('.html') || prefix === '/') return content;
return content.replace(/\b(href|src|action)=(['"])(\/(?!\/)[^'"]*)\2/g, (_, attribute, quote, url) => `${attribute}=${quote}${reviewUrl(url)}${quote}`);
});
eleventyConfig.addGlobalData('site', { shortName: 'CSS Review', showUHLinks: false, portraitCardGrid: true, equalColumnGrids: true });
eleventyConfig.addGlobalData('navigation', () => JSON.parse(fs.readFileSync(path.join(shared, 'data/common/review-navigation.json'), 'utf8')));
eleventyConfig.addWatchTarget('../css-shared/src/data/common/review-navigation.json', { resetConfig: true });
eleventyConfig.addGlobalData('reviewNavigation', () => {
const units = fs.readdirSync(path.join(shared, 'data/units')).filter(key => key !== 'style-guide' && fs.existsSync(path.join(project, '..', key, 'src')) && fs.existsSync(path.join(shared, 'data/units', key, 'unit-details.json'))).sort();
const current = JSON.parse(fs.readFileSync(path.join(shared, 'data/common/review-units.json'), 'utf8')).current;
const first = units.filter(key => current.includes(key));
const remaining = units.filter(key => !current.includes(key));
const sections = Object.fromEntries(['heroes', 'redirects-404s'].map(section => [section, {
label: 'Review units',
pages: [...first, ...remaining].map(key => ({ label: key.toUpperCase(), url: `/${section}/${key}.html`, groupStart: first.length > 0 && key === remaining[0] }))
}]));
sections.headings = {
label: 'Page Headings',
pages: current.map(key => ({ label: key.toUpperCase(), url: `/headings/${key}.html` }))
};
return sections;
});
const prepare = () => execFileSync('python3', ['scripts/build.py'], {
stdio: 'inherit',
env: { ...process.env, REVIEW_OUTPUT: '_generated' }
});
prepare();
eleventyConfig.on('eleventy.before', async () => {
await build({
entryPoints: [path.join(shared, 'css/review.css')],
outfile: path.join(project, '_site/review.css'),
bundle: true,
minify: true,
loader: { '.woff2': 'file', '.svg': 'file' },
assetNames: 'assets/[name]-[hash]',
plugins: [{
name: 'disable-review-layout-guides',
setup(builder) {
builder.onResolve({ filter: /(?:^|\/)diagnostics\.css$/ }, args => ({ path: args.path, namespace: 'disabled-layout-guides' }));
builder.onLoad({ filter: /.*/, namespace: 'disabled-layout-guides' }, () => ({ contents: '', loader: 'css' }));
}
}]
});
});
eleventyConfig.addWatchTarget('scripts', { resetConfig: true });
eleventyConfig.addWatchTarget('data', { resetConfig: true });
eleventyConfig.addWatchTarget('../css-shared/src/data', { resetConfig: true });
eleventyConfig.addWatchTarget('../css-shared/src/css');
eleventyConfig.addWatchTarget('../css-shared/src/includes');
eleventyConfig.addWatchTarget('../css-shared/docs/rules/code-cleanup.md');
eleventyConfig.addWatchTarget('../css-shared/docs/rules/language-writing.md');
eleventyConfig.addPassthroughCopy({ '_generated/heroes/media': 'heroes/media' });
eleventyConfig.addPassthroughCopy({ '_generated/grids-inventory.json': 'grids-inventory.json' });
eleventyConfig.addPassthroughCopy({ [path.join(shared, 'assets/js/review-grids.js')]: 'assets/js/review-grids.js' });
eleventyConfig.addPassthroughCopy({ [path.join(shared, 'assets/review/grid-placeholder.svg')]: 'assets/grid-placeholder.svg' });
eleventyConfig.addPassthroughCopy({ [path.join(shared, 'assets/js/site.js')]: 'assets/js/site.js' });
return {
dir: { input: reviewInput, output: reviewOutput, layouts: path.relative(path.join(project, reviewInput), path.join(shared, 'includes')) },
templateFormats: ['html', 'md'],
markdownTemplateEngine: 'njk',
htmlTemplateEngine: 'njk',
pathPrefix: prefix
};
}
