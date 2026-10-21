---
name: assets-optimization-checklist
description: Asset quality gate. Validates image optimization (format, size, dimensions, lazy vs LCP), clean/accessible SVGs, and icons. Use when adding or processing images, icons, or SVGs for the site.
allowed-tools: Read, Grep, Glob, Bash
---

# Check images, SVGs and icons

Mark each item PASS/FAIL. Report FAIL with the file and the fix.

## Blockers (MUST / NEVER)

- [ ] MUST: optimize and size content images before delivery, using the site's image pipeline when it has one. NEVER: serve heavy unoptimized originals from a static directory.
- [ ] MUST: size images for their rendered use and compare format, quality and transfer size. Use modern formats where appropriate without treating the extension or one pixel size as a universal rule.
- [ ] MUST: give every `<img>` explicit `width` and `height`, or an aspect ratio, to avoid CLS.
- [ ] NEVER: apply `loading="lazy"` to the LCP image (above-the-fold hero). Below-the-fold images DO get `loading="lazy"`.
- [ ] MUST: remove unnecessary editor metadata and private comments from inline SVGs. Keep document IDs unique and preserve functional references. Give informative SVGs `role="img"` and a `<title>` or `aria-label`. Use `aria-hidden="true"` for decorative SVGs.
- [ ] MUST: replace a broken image (404) with the recovered original or commercially licensed stock. NEVER: delete it without a replacement.
- [ ] NEVER: use images without commercial usage rights. Check the rights for the specific photo.

## Recommendations (SHOULD)

- [ ] SHOULD: preview images match the intended consumer and remain legible at the rendered size.
- [ ] SHOULD: icons as a consistent SVG set (same grid, stroke), not loose PNGs.
- [ ] SHOULD: descriptive kebab-case filenames (helps image SEO).

## Scope and limits
- Doesn't define project-specific accessibility prose. Coordinate semantic `alt` decisions with `seo-onpage-checklist` and the host project's accessibility rules.
- Doesn't touch image build configuration.

## When you need more detail
Start with this checklist. For more detail (format decision AVIF/WebP/SVG,
responsive sizing/srcset, LCP eager-load, CLS dimensions, SVG hygiene/security, icon consistency,
OG and image SEO, rights/replacement), open sibling `KNOWLEDGE.md`. Consult it to decide format and
loading, not just check. Use the host project's documentation for framework-specific implementation.

---
Sources: Responsive images (web.dev) <https://web.dev/learn/images/responsive-images> · Google image SEO <https://developers.google.com/search/docs/appearance/google-images>

## Save deliverables

Save asset audit reports and measurement evidence in `audits/`. Implementation changes belong in the website's declared source paths.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.
