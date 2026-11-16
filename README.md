# Review

Local review pages for the shared unit websites. The style-guide site is unchanged.

Run `go` (the standard clean/dev alias), or `npm run dev`. Dev rebuilds the pages, starts the local server, and prints http://localhost:8090/ for copying into a browser.

- `redirects-404s/`: one page per unit, bullet lists from shared migration data.
- `heroes/`: one page per unit, main/faculty/policy groups alphabetized by page title.

Links test the GitHub unit previews. Upload unit/shared changes before expecting those tests to reflect local edits. Units without migration mappings say so. Rebuild Review after changing unit source, heroes or migration data.

Uses the same Eleventy, Nunjucks and esbuild dependencies as the unit sites. No tracking or API keys. Publishing uses the manual workflow described below. Output is generated in `_site`.

Layout comes from `../css-shared/src/includes/layouts/review/shell.njk`. Its stylesheet bundles `../css-shared/src/css/review.css`, which imports the shared common stylesheet. The main navigation and unit-switching submenu reuse the shared unit-navigation and degree-navigation components. Review omits the UH branding/header/footer; its banner uses the shared blue token. No independent local stylesheet is maintained.

Startup uses the standard Eleventy scripts: `go` runs clean/dev, and `npm run build` creates the static output. Eleventy prints the local URL and serves port 8090. The Python script only prepares the review content; it does not run the server.

## Grids

`/grids.html` shows the current general page-layout arrangements across SSRI, PUBA, ES, ANTH
and SOC. Colored placeholders use production classes; media rows use the shared
macro. Use the Sidebars, Equal Columns, Cards & Tiles, and Combined Layouts tabs.
Common patterns appear first; faculty bios stay with Sidebars. Expand an example
to see its source pages. The small live readout reports
current column widths and gaps. This is a baseline, not the final grid standard. Responsive data tables and
record directories are excluded; portrait/card grids and contact columns remain.

Build those five sites before rebuilding Review; the inventory reads their built
main content, including shared layouts. Build Review again after consumer changes.
Generator changes and shared CSS/includes are watched during development.
`npm run audit:grids` measures examples at breakpoint boundaries and checks them
against representative consumers using headless Chrome. Development dependencies
include Playwright Core and axe-core; `GRID_BROWSER` selects another Chrome binary.
See `../css-shared/docs/shared/grid-system-review.md` for scope and limitations.

Keep this repository and css-shared synchronized when moving work between machines.

## GitHub Pages

Repository: https://github.com/cssweb-stack/review
Expected published address: https://cssweb-stack.github.io/review/

Set GitHub Settings > Pages > Source to GitHub Actions. Push required changes in
css-shared and Review, then use Actions > Build and publish Review > Run workflow.
Publishing is manual; no push or scheduled triggers. The workflow requires ANTH, ES, PUBA, SOC and SSRI sources as siblings and builds
those five sites before Review. GEO, POLS, PSY, SCI and WGSS are optional: an
unavailable repository produces a warning and its listings are omitted. This means
layout inventory and heading/hero listings do not depend on a developer's
local generated files. The summary records all source revisions. It publishes
only Review's output, not the unit outputs. Shared sources use css-shared main;
unit sources use each repository's default branch.

`SITE_PATH_PREFIX=/review/ npm run build` builds for GitHub Pages. With no prefix,
`go` retains the normal local address. GitHub Pages is public; noindex remains set.
