#!/usr/bin/env python3
"""Evidence-based HTML audit. Live acquisition is in live_audit.py."""

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, parse_qsl, urlencode
from xml.etree import ElementTree

from audit_io import output_stream
from audit_scoring import REVIEW_ITEMS, reviewed_items, refresh_report
from robots_policy import RobotsPolicy


CHECKS = {
    "technical.canonical": (7, "technical"),
    "technical.internal_links": (5, "technical"),
    "technical.sitemap": (4, "technical"),
    "technical.robots": (4, "technical"),
    "technical.language": (2, "technical"),
    "technical.viewport": (2, "technical"),
    "technical.structured_data": (2, "technical"),
    "technical.indexing": (5, "technical"),
    "technical.http": (4, "technical"),
    "onpage.title": (7, "onpage"),
    "onpage.description": (4, "onpage"),
    "onpage.heading_one": (5, "onpage"),
    "onpage.heading_order": (3, "onpage"),
    "onpage.unique_title": (3, "onpage"),
    "onpage.image_alt": (3, "onpage"),
    "onpage.link_text": (3, "onpage"),
    "onpage.intent_review": (7, "onpage"),
    "geo.review": (10, "geo"),
    "performance.lcp": (4, "performance"),
    "performance.inp": (3, "performance"),
    "performance.cls": (3, "performance"),
    "offpage.review": (10, "offpage"),
}
assert sum(weight for weight, _ in CHECKS.values()) == 100
EXTERNAL = {"technical.indexing", "technical.http", "onpage.intent_review", "geo.review", "performance.lcp", "performance.inp", "performance.cls", "offpage.review"}
CWV_LIMITS = {"performance.lcp": 2500, "performance.inp": 200, "performance.cls": 0.1}


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self._capture = []
        self.title = ""
        self.title_count = 0
        self.headings = []
        self.links = []
        self.images = []
        self.canonicals = []
        self.meta = []
        self.lang = ""
        self.json_ld = []
        self.link_elements = []
        self.html_attributes = {}
        self.ids = set()
        self.labels_for = set()
        self.form_controls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == "title":
            self.title_count += 1
        if tag == "html":
            self.lang = attrs.get("lang", "")
            self.html_attributes = attrs
        elif tag == 'label' and attrs.get('for'):
            self.labels_for.add(attrs['for'])
        elif tag in {'input', 'select', 'textarea'}:
            self.form_controls.append({'tag': tag, 'id': attrs.get('id', ''), 'type': attrs.get('type', ''),
                                       'aria_label': attrs.get('aria-label', ''), 'aria_labelledby': attrs.get('aria-labelledby', ''),
                                       'title': attrs.get('title', ''), 'nested_label': 'label' in self.tags})
        elif tag == "meta":
            self.meta.append(attrs)
        elif tag == "link":
            self.link_elements.append(attrs)
            if "canonical" in attrs.get("rel", "").lower().split():
                self.canonicals.append(attrs.get("href", ""))
        elif tag == "img":
            self.images.append(attrs)
            for capture in self._capture:
                if capture[0] == 'a' and attrs.get('alt'):
                    capture[1].append(attrs['alt'])
        elif tag == "a":
            self.links.append({"href": attrs.get("href", ""), "text": "", "aria": attrs.get("aria-label", ""), "rel": attrs.get('rel', '')})
        if tag in {"title", "a", "script", "style"} or re.fullmatch(r"h[1-6]", tag):
            self._capture.append([tag, [], attrs])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._capture:
            for capture in self._capture:
                capture[1].append(data)
        if not self._capture or self._capture[-1][0] not in {"script", "style"}:
            self.text.append(data)

    def handle_endtag(self, tag):
        for index in range(len(self._capture) - 1, -1, -1):
            if self._capture[index][0] == tag:
                _, parts, attrs = self._capture.pop(index)
                value = " ".join("".join(parts).split())
                if tag == "title":
                    self.title = value
                elif tag == "a" and self.links:
                    self.links[-1]["text"] = value
                elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
                    self.json_ld.append(value)
                elif re.fullmatch(r"h[1-6]", tag):
                    self.headings.append((int(tag[1]), value))
                break
        if tag in self.tags:
            self.tags.remove(tag)

    def metas(self, name):
        return [m.get("content", "").strip() for m in self.meta if m.get("name", "").lower() == name]


def page_url(root, file):
    relative = file.relative_to(root).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[:-10]
    return "/" + relative


def normalize_url(url):
    parsed = urlparse(url)
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True), key=lambda item: item[0]))
    return (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", query)


def global_robots_block(text):
    agents = []
    rules_started = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip().lower() for part in line.split(":", 1)]
        if key == "user-agent":
            if rules_started:
                agents = []
                rules_started = False
            agents.append(value)
        elif key in {"allow", "disallow"}:
            rules_started = True
            if key == "disallow" and value == "/" and "*" in agents:
                return True
    return False


def validate_json_ld(payload):
    """Check JSON-LD structure without claiming rich-result eligibility."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        return False, f"invalid JSON: {error.msg}"

    def nodes(value, inherited_context=False):
        if isinstance(value, list):
            if not value:
                return False, "empty JSON-LD array"
            for item in value:
                valid, detail = nodes(item, inherited_context)
                if not valid:
                    return valid, detail
            return True, "valid JSON-LD structure"
        if not isinstance(value, dict):
            return False, "JSON-LD root must be an object or nonempty array"
        context = value.get("@context")
        has_context = inherited_context or context == "https://schema.org" or context == "http://schema.org" or (isinstance(context, dict) and "schema.org" in json.dumps(context))
        if not has_context:
            return False, "missing Schema.org @context"
        if "@graph" in value:
            return nodes(value["@graph"], has_context)
        node_type = value.get("@type")
        if not (isinstance(node_type, str) and node_type.strip() or isinstance(node_type, list) and node_type and all(isinstance(item, str) and item.strip() for item in node_type)):
            return False, "missing or empty @type"
        if len(set(value) - {"@context", "@type", "@id"}) == 0:
            return False, "typed node has no properties"
        return True, "valid Schema.org context, type and node structure. Feature eligibility needs external validation"

    return nodes(data)


def audit(root, base_url, evidence=None, *, live=False, link_status=None, page_urls=None):
    root = Path(root).resolve(strict=True)
    base = base_url.rstrip("/") + "/"
    parsed_base = urlparse(base)
    if parsed_base.scheme != "https" or not parsed_base.netloc or parsed_base.path != "/":
        raise ValueError("--base-url must be an HTTPS origin, e.g. https://example.org")
    files = sorted(p for p in root.rglob("*.html") if p.is_file() and not p.is_symlink() and root in p.parents)
    if not files:
        raise ValueError("no HTML files found in --site")
    if len(files) > 10000 and not live:
        raise ValueError("audit limit is 10,000 HTML files")
    pages = {}
    for file in files:
        route = page_url(root, file)
        if route in pages:
            raise ValueError(f"duplicate route: {route}")
        document = Document()
        document.feed(file.read_text(encoding="utf-8"))
        pages[route] = (document, file.relative_to(root).as_posix())

    findings = {key: [] for key in CHECKS}

    def add(key, passed, location, detail, *, status=None):
        findings[key].append({"status": status or ("pass" if passed else "fail"), "location": location, "detail": detail})

    page_locations = {(page_urls or {}).get(route, urljoin(base, route.lstrip("/"))): file
                      for route, (_, file) in pages.items()}

    def noindex(doc):
        tokens = {token for value in doc.metas("robots") + doc.metas("googlebot")
                  for token in re.split(r"[\s,]+", value.lower())}
        return bool(tokens & {"noindex", "none"})

    titles = {}
    for route, (doc, file) in pages.items():
        expected = (page_urls or {}).get(route, urljoin(base, route.lstrip("/")))
        if not noindex(doc):
            targets = {normalize_url(urljoin(expected, value)) for value in doc.canonicals if value.strip()}
            valid = bool(targets) and len(targets) == 1 and all(
                value.strip() and urlparse(urljoin(expected, value)).scheme in {"http", "https"}
                and urlparse(urljoin(expected, value)).netloc for value in doc.canonicals)
            add("technical.canonical", valid, file,
                f"canonical declarations={doc.canonicals}, target selection still needs review",
                status="unmeasured" if not doc.canonicals else None)
        else:
            add("technical.canonical", False, file, "Page declares noindex. Canonical target policy requires review", status="not_applicable")
        add("technical.language", bool(doc.lang.strip()), file, f"html lang={doc.lang!r}")
        add("technical.viewport", any("width=device-width" in value.lower() for value in doc.metas("viewport")), file, "responsive viewport meta")
        for payload in doc.json_ld:
            valid, detail = validate_json_ld(payload)
            add("technical.structured_data", valid, file, detail)
        if not doc.json_ld:
            add("technical.structured_data", False, file, "no JSON-LD to validate. Feature relevance remains a review task", status="not_applicable")

        add("onpage.title", bool(doc.title) and doc.title_count == 1, file, f"title={doc.title!r}, {len(doc.title)} characters")
        descriptions = doc.metas("description")
        add("onpage.description", len(descriptions) == 1 and bool(descriptions[0]), file, f"descriptions={descriptions}")
        add("onpage.heading_one", any(level == 1 and bool(value) for level, value in doc.headings), file, f"headings={doc.headings}")
        levels = [level for level, _ in doc.headings]
        ordered = all(current <= previous + 1 for previous, current in zip(levels, levels[1:])) and (not levels or levels[0] == 1)
        add("onpage.heading_order", ordered, file, f"levels={levels}")
        titles.setdefault(doc.title.casefold(), []).append(file)
        for image in doc.images:
            add("onpage.image_alt", "alt" in image, file, f"image={image.get('src', '')}")
        if not doc.images:
            add("onpage.image_alt", False, file, "no images", status="not_applicable")
        for link in doc.links:
            href = link["href"]
            if href.startswith(("mailto:", "tel:", "javascript:")) or not href or href.startswith("#"):
                continue
            target = urlparse(urljoin(expected, href))
            if target.netloc == parsed_base.netloc:
                path = unquote(target.path)
                if live:
                    status = (link_status or {}).get(normalize_url(target.geturl()))
                    if status is not None:
                        add("technical.internal_links", 200 <= status < 400, file, f"{href} returned HTTP {status}")
                else:
                    asset = (root / path.lstrip("/")).resolve()
                    found = path in pages or (path.rstrip("/") + "/") in pages or (path.rstrip("/") + ".html") in pages or (asset.is_relative_to(root) and asset.is_file())
                    add("technical.internal_links", found, file, f"{href} resolves to {path}")
            label = link["text"] or link["aria"]
            add("onpage.link_text", bool(label) and label.casefold() not in {"click here", "read more", "here"}, file, f"link={href}, text={label!r}")
        if not doc.links:
            add("onpage.link_text", False, file, "no links", status="not_applicable")
    if not findings["technical.internal_links"] and not live:
        add("technical.internal_links", False, "site", "no internal links to validate. Discovery needs review", status="not_applicable")
    for files_with_title in titles.values():
        for file in files_with_title:
            add("onpage.unique_title", len(files_with_title) == 1, file, f"same title in {files_with_title}")

    robots_file = root / "robots.txt"
    robots = robots_file.read_text(encoding="utf-8") if robots_file.is_file() else ""
    if robots:
        policy = RobotsPolicy(robots)
        for route, (doc, file) in pages.items():
            if not noindex(doc):
                target = (page_urls or {}).get(route, urljoin(base, route.lstrip("/")))
                add("technical.robots", policy.can_fetch("Googlebot", target), file,
                    f"Googlebot robots policy for {target}, sitemap declaration is optional")
    else:
        add("technical.robots", False, "robots.txt", "No robots file supplied. Absence alone is not a Google violation. Deployed policy is unmeasured", status="unmeasured")

    sitemap_file = root / "sitemap.xml"
    if sitemap_file.is_file():
        try:
            tree = ElementTree.parse(sitemap_file)
            sitemap_urls = [child.text.strip() for entry in tree.getroot() if entry.tag.rsplit("}", 1)[-1] == "url" for child in entry if child.tag.rsplit("}", 1)[-1] == "loc" and child.text]
            root_tag = tree.getroot().tag.rsplit("}", 1)[-1]
            if root_tag == "sitemapindex":
                add("technical.sitemap", False, "sitemap.xml", "Sitemap index requires child-file inspection", status="unmeasured")
            elif root_tag != "urlset":
                add("technical.sitemap", False, "sitemap.xml", "Expected urlset or sitemapindex")
            else:
                known = {normalize_url(url): pages[route][0] for route, (doc, file) in pages.items()
                         for url in [(page_urls or {}).get(route, urljoin(base, route.lstrip("/"))) ]}
                invalid = [url for url in sitemap_urls if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).netloc
                           or (normalize_url(url) in known and noindex(known[normalize_url(url)]))]
                add("technical.sitemap", bool(sitemap_urls) and not invalid, "sitemap.xml",
                    f"{len(sitemap_urls)} submitted URLs, invalid or known noindex targets={invalid}, sitemap completeness and unseen targets require review")

        except ElementTree.ParseError as error:
            add("technical.sitemap", False, "sitemap.xml", f"invalid XML: {error}")
    else:
        add("technical.sitemap", False, "sitemap.xml", "No sitemap supplied. Applicability and deployed submission require review", status="unmeasured")

    if evidence is not None and (not isinstance(evidence, dict) or not isinstance(evidence.get("checks"), dict)):
        raise ValueError("--evidence must contain a checks object")
    evidence_checks = (evidence or {}).get("checks", {})
    unknown = set(evidence_checks) - EXTERNAL
    if unknown:
        raise ValueError(f"unknown external check IDs: {', '.join(sorted(unknown))}")
    for key in EXTERNAL:
        item = evidence_checks.get(key)
        if item is None:
            if key == "onpage.intent_review":
                findings[key].extend(reviewed_items(key, {"scope": base.rstrip("/"), "source": "not supplied",
                                                        "date": "not supplied", "period": "not supplied"}, page_locations))
            continue
        if not isinstance(item, dict) or not all(isinstance(item.get(field), str) and item[field].strip() for field in ("source", "date", "scope", "period")):
            raise ValueError(f"{key}: external evidence requires source, date, scope and period")
        try:
            reviewed = date.fromisoformat(item["date"])
        except ValueError as error:
            raise ValueError(f"{key}: date must be YYYY-MM-DD") from error
        if reviewed > date.today():
            raise ValueError(f"{key}: future evidence date")
        if urlparse(item["scope"]).scheme != "https" or urlparse(item["scope"]).netloc.lower() != parsed_base.netloc.lower():
            raise ValueError(f"{key}: evidence scope must match --base-url origin")
        if key == "onpage.intent_review" or key in REVIEW_ITEMS:
            findings[key].extend(reviewed_items(key, item, page_locations))
            continue
        if key in CWV_LIMITS:
            value = item.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or item.get("kind") != "field_p75":
                raise ValueError(f"{key}: require non-negative numeric value and kind=field_p75")
            passed = value <= CWV_LIMITS[key]
            detail = f"field p75={value}, threshold={CWV_LIMITS[key]}, source={item['source']}, date={item['date']}, period={item['period']}"
        else:
            if item.get("status") not in {"pass", "fail"} or not isinstance(item.get("detail"), str) or not item["detail"].strip():
                raise ValueError(f"{key}: reviewed evidence requires status pass/fail and detail")
            passed = item["status"] == "pass"
            detail = f"{item['detail']}, source={item['source']}, date={item['date']}, period={item['period']}"
        add(key, passed, item["scope"], detail)

    checks = [{"id": key, "category": category, "weight": weight, "findings": findings[key]}
              for key, (weight, category) in CHECKS.items()]
    content_pages = (evidence_checks.get("onpage.intent_review") or {}).get("pages", {})
    page_types = {url: value.get("page_type", "generic") for url, value in content_pages.items()}
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "scope": "sampled_live_html" if live else "built_static_html", "site": None if live else str(root),
              "base_url": base, "pages": len(pages), "routes": sorted(pages),
              "page_locations": page_locations, "page_types": page_types, "checks": checks}
    return refresh_report(report)


def compare(current, baseline):
    if not isinstance(baseline, dict) or baseline.get("schema_version") != 1 or baseline.get("base_url") != current["base_url"] or not isinstance(baseline.get("checks"), list):
        raise ValueError("--baseline must be a compatible report for the same base URL")
    previous = {item["id"]: item for item in baseline["checks"] if isinstance(item, dict) and item.get("id") in CHECKS}
    latest = {item["id"]: item for item in current["checks"]}
    shared = sorted(key for key in CHECKS if key in previous and previous[key].get("measured_weight", 0) > 0 and latest[key].get("measured_weight", 0) > 0)

    def failures(checks):
        return {(key, finding["location"], finding.get("item", "")) for key in shared for finding in checks[key].get("findings", []) if finding.get("status") == "fail" and isinstance(finding.get("location"), str)}

    old_failures = failures(previous)
    new_failures = failures(latest)

    def items(values):
        return [{"check": key, "location": location, **({"item": item} if item else {})} for key, location, item in sorted(values)]

    same_routes = baseline.get("routes") == current["routes"]
    same_scope = baseline.get("scope") == current["scope"]
    same_scoring = baseline.get("scoring_version") == current.get("scoring_version")

    def measurement_signature(checks):
        return {key: (item.get("weight"), sorted((f.get("location", ""), f.get("item", ""),
                    f.get("status") == "not_applicable", f.get("status") == "unmeasured")
                    for f in item.get("findings", []))) for key, item in checks.items()}

    same_measurements = measurement_signature(previous) == measurement_signature(latest)
    comparable_score = same_routes and same_scope and same_scoring and same_measurements and isinstance(baseline.get("score"), int) and isinstance(current.get("score"), int)
    return {
        "same_routes": same_routes,
        "same_scope": same_scope,
        "same_scoring_version": same_scoring,
        "same_measurements": same_measurements,
        "comparable_checks": shared,
        "score_delta": current["score"] - baseline["score"] if comparable_score else None,
        "coverage_delta": round(current["coverage"] - baseline.get("coverage", 0), 2) if isinstance(baseline.get("coverage"), (int, float)) else None,
        "new_failures": items(new_failures - old_failures),
        "persistent_failures": items(new_failures & old_failures),
        "resolved_failures": items(old_failures - new_failures),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit built HTML and score verified SEO evidence from 0 to 100")
    parser.add_argument("--site", required=True, help="directory containing built HTML, robots.txt and sitemap.xml")
    parser.add_argument("--base-url", required=True, help="production HTTPS origin")
    parser.add_argument("--evidence", help="JSON file with dated external checks")
    parser.add_argument("--baseline", help="previous JSON report for follow-up comparison")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--output", help="report file, stdout by default")
    args = parser.parse_args(argv)
    try:
        repository = Path(__file__).resolve().parents[2]
        for label in ('site', 'evidence', 'baseline', 'output'):
            value = getattr(args, label)
            if value and Path(value).resolve().is_relative_to(repository):
                parser.error(f'--{label} must be outside the seo-kit repository')
        if args.output and any(Path(args.output).resolve() == Path(value).resolve()
                               for value in (args.evidence, args.baseline) if value):
            parser.error('--output must not overwrite evidence or baseline')
        evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else None
        report = audit(args.site, args.base_url, evidence)
        if args.baseline:
            baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
            report["comparison"] = compare(report, baseline)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.format == "json":
        result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    else:
        lines = [f"SEO audit: {report['base_url']} ({report['pages']} pages)", f"Score: {report['score']}/100 | Coverage: {report['coverage']}% | {'complete' if report['complete'] else 'provisional'} | Rubric: {report['scoring_version']}",
                 f"Checklist score bounds: {report['score_bounds']} | Critical failures: {len(report['critical_failures'])}, not a ranking prediction"]
        for check in report["checks"]:
            lines.append(f"[{check['status'].upper()}] {check['id']} ({check['weight']} points, {check['passed']}/{check['total']})")
            for item in check["findings"]:
                if item["status"] == "fail":
                    lines.append(f"  {item['location']}: {item['detail']}")
        if "comparison" in report:
            comparison = report["comparison"]
            lines.append(f"Follow-up: score delta={comparison['score_delta']}, new={len(comparison['new_failures'])}, persistent={len(comparison['persistent_failures'])}, resolved={len(comparison['resolved_failures'])}")
        result = "\n".join(lines) + "\n"
    try:
        with output_stream(args.output) as stream:
            stream.write(result)
    except OSError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
