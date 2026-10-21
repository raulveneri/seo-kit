---
name: seo-pagespeed-optimizer
description: Iterative web performance optimization using the project's available lab and field tooling. Use for Lighthouse, PageSpeed, Core Web Vitals, bundle, loading, rendering, or console-error work without changing product behavior or design unintentionally.
---

# Web performance optimization

Choose the pages and devices to measure. Record the build mode, whether you are testing locally or on the deployed site, and the existing measurement tools. Use comparable runs to guide changes. NEVER: promise a score or infer field performance from one lab run.

## Baseline

Record tool version, URL/build SHA, device profile, throttling, run count, cache state, and median or representative metrics. Keep lab data distinct from field data and note the field-data time window.

## Loop

1. Identify the dominant bottleneck from trace evidence, coverage, network waterfall, bundle analysis, or runtime profiling.
2. Form one small hypothesis tied to a metric or console error.
3. Apply the smallest behavior-preserving change.
4. Rebuild and repeat comparable measurements enough to reduce noise.
5. Keep the change only when the evidence improves or removes the targeted problem without regressing accessibility, correctness, visual output, or other critical metrics.

Check LCP resource discovery and priority, render blocking, image/font sizing, unused JavaScript/CSS, main-thread work, hydration, caching/compression, CLS sources, interaction latency, and third-party cost as applicable.

Report before/after values with source and measurement conditions. Keep the CrUX rolling 28-day collection period separate from immediate lab checks. Repeated same-day queries do not establish a post-change field result. Scores are diagnostics, not product goals by themselves. NEVER: use destructive Git rollback commands to discard unrelated work.

## Technical SEO and accessibility

When the user targets 100, measure Performance, Accessibility, Best Practices and SEO separately for the requested mobile and desktop profiles. Aim for the requested score through verified fixes, without hiding content, removing required features or changing the test conditions to inflate a result. A 100 Lighthouse score does not establish WCAG conformance, field Core Web Vitals or search rankings. Read [KNOWLEDGE.md](KNOWLEDGE.md) for source boundaries.

Check meaningful page structure, accessible names, text alternatives, contrast, keyboard navigation, visible focus, zoom/reflow and reduced motion where the changes affect them. Use the project's automated accessibility harness and manual interaction checks. Preserve unresolved manual checks in the report even when automated scores reach 100.

Apply changes only when implementation is authorized in the consuming project. The `seo-technical` agent remains read-only: it identifies fixes and hands this skill to the owning implementation agent or developer. Use `seo-technical-checklist` for crawl/indexing checks and `assets-optimization-checklist` for search and performance assets.

Stop when the requested target is consistently measured under the agreed conditions, or when remaining changes need a product decision, unavailable evidence or an external dependency. Report those limits and the next concrete action. NEVER: claim a target was reached without comparable fresh runs.

## Save deliverables

Save baseline and follow-up performance/accessibility reports, traces and comparisons in `audits/`.

Find the selected client or website folder in the active workspace and project context. An SEO working folder without code or Git is valid. If the project root is unclear, ask for it. Create the needed directories there before writing or running the CLI. Pass absolute paths, even when running commands from the kit checkout. Resolve symlinks and check that destinations stay inside the selected project and outside the kit. Use dated files or separate run folders to preserve earlier results. Return the saved paths.

Keep deliverables outside published asset and build folders, and never switch projects silently.
