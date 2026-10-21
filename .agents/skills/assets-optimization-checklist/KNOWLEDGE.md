---
domain: Image and media delivery
last_reviewed: 2026-10-20
---

# Optimize images, SVGs and icons

Use `SKILL.md` to review the files. Measure delivery at the sizes and devices the project supports.

## 1. Choose formats

Compare format, quality, transparency and browser support for the actual asset. Modern formats can reduce transfer size. Google Search supports JPEG, PNG, WebP, SVG and AVIF, among other formats. Do not reject an image solely because its extension differs from a preferred format.

## 2. Size responsive images

Match delivered dimensions to the rendered size and device pixel density. Use `srcset` and `sizes` where appropriate. Review transfer bytes and visual quality together. Set a project budget from measurements instead of treating a fixed kilobyte limit as a Google requirement.

## 3. Load the LCP resource

Identify the actual LCP element in a trace. If it is an image, avoid lazy-loading it and make the resource discoverable early. Test priority or preload changes before keeping them. Lazy-load offscreen images when appropriate.

## 4. Reserve space

Set image dimensions or a suitable aspect ratio so the browser can reserve space. Inspect layout shifts during loading and interaction. Font changes, embeds and inserted content can also move the layout.

## 5. Review SVG files

Remove unnecessary editor metadata and check for personal information in comments or identifiers. Preserve IDs needed by paths, gradients or accessible names. Sanitize untrusted markup before inlining it. Keep informative images named accessibly and decorative images out of the accessibility tree.

## 6. Keep icons usable

Follow the consuming project's icon conventions. Check clarity at the intended size, consistent treatment and accessible names for controls. Do not mistake a visual preference for a search requirement.

## 7. Check image context

Use meaningful filenames and alt text that describes the image in context. Keep nearby text relevant. Review preview images against the project's intended consumer and layout instead of imposing one universal size.

## 8. Rights and replacement

Check the license and required notices before using an image. Preserve mandatory attribution. For a broken image, recover the original or obtain a suitable licensed replacement. Keep any removal or layout decision explicit.

## Google technical references

| Reference | URL | Last checked |
| --- | --- | --- |
| Image SEO | https://developers.google.com/search/docs/appearance/google-images | 2026-10-20 |
| Responsive images | https://web.dev/learn/images/responsive-images | 2026-10-20 |
| Images and accessibility | https://web.dev/learn/accessibility/images | 2026-10-20 |
| Optimize LCP | https://web.dev/articles/optimize-lcp | 2026-10-20 |
| Optimize CLS | https://web.dev/articles/optimize-cls | 2026-10-20 |

## Changelog

- 2026-10-20: Clarified format choices, measured budgets, accessible images and loading checks.
