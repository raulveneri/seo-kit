#!/usr/bin/env python3
"""Bounded public-site SEO audit with optional rendering and Google data."""

import argparse
import csv
import json
import os
import re
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import hashlib
import gzip
import io
import importlib.util
import math
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from audit import Document, audit, compare, normalize_url
from audit_scoring import refresh_report
from live_http import SafeClient, USER_AGENT, checked_url
from crawl_store import CrawlStore, url_key, SCHEMA_VERSION
from robots_policy import RobotsPolicy
from advanced_audit import advanced_metadata, inspect_advanced, site_advanced, binary_worker, inspect_references
from external_data import enrich, api_json
from crawl_rules import content_fingerprint, inspect_page, inspect_site
from audit_io import database_lock, output_stream
from crawl_privacy import sanitize, redact_text, sensitive_url


CRUX_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
GSC_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
METRICS = {"largest_contentful_paint": "performance.lcp", "interaction_to_next_paint": "performance.inp", "cumulative_layout_shift": "performance.cls"}


def same_origin(url, origin):
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.netloc.lower() == urlsplit(origin).netloc.lower() and parsed.port in (None, 443)


def audit_url(url, origin):
    url = checked_url(urljoin(origin + "/", url))
    if sensitive_url(url):
        raise ValueError('URL contains sensitive parameters. Excluded by privacy policy')
    if not same_origin(url, origin):
        raise ValueError("URL left the selected origin")
    return url


def page_file(root, url):
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    parts = [part for part in path.split("/") if part]
    if any(part in (".", "..") or "\\" in part or "\x00" in part for part in parts):
        raise ValueError("unsafe URL path")
    if not parts or path.endswith("/") or not parts[-1].lower().endswith(".html"):
        parts.append("index.html")
    file = root.joinpath(*parts)
    if root not in file.parents:
        raise ValueError("URL escaped temporary audit directory")
    return file


def read_robots(client, origin, record=None):
    response = client.fetch(origin + "/robots.txt")
    if record:
        record(origin, 'robots', response)
    if response.status == 404:
        content = ""
    elif response.status == 200:
        content = response.body.decode("utf-8", "replace")
    else:
        raise ValueError(f"cannot establish robots policy: HTTP {response.status}")
    parser = RobotsPolicy(content)
    return parser, content


def sitemap_urls(client, origin, robots_text, warnings, max_sitemaps=5, record=None, robots=None, on_url=None):
    declared = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text)
    candidates = declared or [origin + "/sitemap.xml"]
    pending = deque(candidates)
    seen = set()
    pages = []
    while pending and len(seen) < max_sitemaps:
        url = pending.popleft()
        try:
            url = audit_url(url, origin)
            if url in seen:
                continue
            if robots and not robots.can_fetch(USER_AGENT, url):
                warnings.append(f'sitemap blocked by robots: {url}')
                continue
            seen.add(url)
            response = client.fetch(url, authorize=(lambda target: robots.can_fetch(USER_AGENT, target)) if robots else None)
            if record:
                record(origin, 'sitemap', response)
            if response.status != 200:
                warnings.append(f"sitemap {url}: HTTP {response.status}")
                continue
            body = response.body
            if body.startswith(b'\x1f\x8b'):
                with gzip.GzipFile(fileobj=io.BytesIO(body)) as archive:
                    body = archive.read(client.max_bytes + 1)
                if len(body) > client.max_bytes:
                    raise ValueError('expanded sitemap exceeds response budget')
            tree = ElementTree.fromstring(body)
            kind = tree.tag.rsplit("}", 1)[-1]
            locs = [element.text.strip() for element in tree.iter() if element.tag.rsplit("}", 1)[-1] == "loc" and element.text]
            if kind == "sitemapindex":
                pending.extend(locs)
            elif kind == "urlset":
                pages.extend(element.text.strip() for entry in tree for element in entry
                             if element.tag.rsplit('}', 1)[-1] == 'loc' and element.text)
                if on_url:
                    for entry in tree:
                        for element in entry:
                            if element.tag.rsplit('}', 1)[-1] == 'loc' and element.text:
                                on_url(element.text.strip(), response.url)
            else:
                warnings.append(f"sitemap {url}: unsupported root {kind}")
        except (OSError, ValueError, ElementTree.ParseError) as error:
            warnings.append(f"sitemap unavailable: {type(error).__name__}: {error}")
    if pending:
        warnings.append("sitemap index truncated by max_sitemaps")
    return list(dict.fromkeys(url for url in pages if same_origin(url, origin)))


def needs_render(html):
    return bool(re.search(r'<(?:div|main)[^>]+id=["\'](?:root|app|__next)["\'][^>]*>\s*</(?:div|main)>', html, re.I))


def render_page(url, client, origin, robots, browser, warnings=None, resource_hosts=(), record=None, policies=None, observation=None):
    context = browser.new_context(service_workers="block", accept_downloads=False)
    blocked = 0
    blocked_targets, script_errors = [], []
    policies = policies if policies is not None else {urlsplit(origin).hostname: robots}

    def route_request(route):
        nonlocal blocked
        request_url = route.request.url
        try:
            if route.request.method not in ('GET', 'HEAD'):
                raise ValueError('rendering permits read-only requests only')
            target = checked_url(request_url)
            if sensitive_url(target):
                raise ValueError('resource URL contains sensitive parameters')
            host = urlsplit(target).hostname
            if not same_origin(target, origin) and (host not in resource_hosts or route.request.resource_type == 'document'):
                raise ValueError('resource host is not allowed')
            if host not in policies:
                policies[host], _ = read_robots(client, 'https://' + host, record)
                declared_delay = policies[host].crawl_delay(USER_AGENT)
                if declared_delay:
                    client.delay = max(client.delay, declared_delay)
            if not policies[host].can_fetch(USER_AGENT, target):
                raise ValueError("robots disallows resource")
            response = client.fetch(target, authorize=lambda destination: policies[host].can_fetch(USER_AGENT, destination))
            if record:
                record(url, route.request.resource_type, response)
            route.fulfill(status=response.status, headers=response.headers, body=response.body)
        except (OSError, ValueError) as error:
            blocked_targets.append({'url': request_url, 'reason': str(error)})
            blocked += 1
            route.abort()

    try:
        if not hasattr(context, 'route_web_socket'):
            raise ValueError('Playwright 1.48+ is required to block browser WebSockets')
        context.route('**/*', route_request)
        context.route_web_socket('**/*', lambda websocket: websocket.close())
        context.add_init_script('''
            for (const name of ['RTCPeerConnection', 'webkitRTCPeerConnection', 'WebTransport']) {
              Object.defineProperty(globalThis, name, {value: undefined, configurable: false});
            }
        ''')
        page = context.new_page()
        if observation:
            page.on('pageerror', lambda error: script_errors.append(str(error)[:1000]))
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1200)
        html = page.content()
        if observation:
            axe = Path(__file__).resolve().parents[2] / 'node_modules/axe-core/axe.min.js'
            if axe.exists():
                page.add_script_tag(content=axe.read_text())
                result = page.evaluate("async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}); return {violations:r.violations,incomplete:r.incomplete,passes:r.passes.map(p=>p.id),inapplicable:r.inapplicable.map(p=>p.id)}; }")
                observation('axe_accessibility', 'measured', result)
            else:
                observation('axe_accessibility', 'unmeasured', {'reason': 'install npm dependencies'})
        if len(html.encode("utf-8")) > client.max_bytes:
            raise ValueError("rendered page size limit exceeded")
        if observation:
            observation('render_runtime', 'measured', {'blocked_resources': blocked_targets[:1000], 'script_errors': script_errors[:100], 'settle_time_ms': 1200})
        if blocked and warnings is not None:
            warnings.append(f"rendered {url} with {blocked} blocked or unavailable resources")
        return html
    finally:
        context.close()


def network_isolation():
    if sys.platform == 'linux':
        try:
            probe = subprocess.run([sys.executable, str(Path(__file__).with_name('browser_isolation.py'))], capture_output=True, text=True, timeout=5)
            if probe.returncode == 0 and probe.stdout.strip() == 'seccomp-network-isolated':
                return 'seccomp'
        except (OSError, subprocess.TimeoutExpired):
            pass
    executable = shutil.which('unshare')
    if sys.platform != 'linux' or not executable:
        raise ValueError('JavaScript rendering requires Linux user/network namespace isolation. Rendering skipped')
    try:
        result = subprocess.run([executable, '--user', '--map-root-user', '--net', '--', sys.executable,
                                 '-c', "import os; print(os.readlink('/proc/self/ns/net'))"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0 or result.stdout.strip() == os.readlink('/proc/self/ns/net') or not result.stdout.strip():
            raise ValueError('network namespace isolation unavailable. JavaScript rendering skipped')
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('network namespace isolation unavailable. JavaScript rendering skipped') from error
    return executable


def get_browser(render_mode):
    if render_mode == "never":
        return None, None
    try:
        unshare = network_isolation()
    except ValueError as error:
        if render_mode == 'always':
            raise
        return None, str(error)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if render_mode == "always":
            raise ValueError("Playwright is required for --render always. Install playwright and Chromium")
        return None, "Playwright unavailable. JavaScript rendering skipped"
    playwright = sync_playwright().start()
    try:
        browser_path = os.environ.get("SEO_KIT_CHROMIUM_PATH") or playwright.chromium.executable_path
        if not os.environ.get('SEO_KIT_CHROMIUM_PATH') and unshare == 'seccomp':
            installed = Path(browser_path)
            shell = installed.parents[1].with_name(installed.parents[1].name.replace('chromium-', 'chromium_headless_shell-')) / 'chrome-headless-shell-linux64' / 'chrome-headless-shell'
            if not shell.is_file():
                raise ValueError('install the matching Chromium headless shell: python -m playwright install chromium')
            browser_path = str(shell)
        browser_environment = {name: os.environ[name] for name in ('PATH','HOME','LANG','LC_ALL','TMPDIR','XDG_CACHE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME') if name in os.environ}
        launch_options = {'executable_path': str(Path(__file__).with_name('isolated_chromium.py')),
                          'env': {**browser_environment, 'SEO_KIT_UNSHARE_BINARY': unshare,
                                  'SEO_KIT_ISOLATION_BACKEND': 'seccomp' if unshare == 'seccomp' else 'namespace',
                                  'SEO_KIT_ISOLATED_CHROMIUM_BINARY': browser_path}}
        return (playwright, playwright.chromium.launch(**launch_options)), None
    except Exception as error:
        playwright.stop()
        if render_mode == "always":
            raise ValueError(f'isolated Chromium unavailable: {error}') from error
        return None, 'isolated Chromium unavailable. JavaScript rendering skipped'


def json_api(client, endpoint, payload, headers):
    return api_json(client, endpoint, payload=payload, headers=headers)


def crux_evidence(client, origin, api_key):
    if not api_key:
        return {}, "CrUX skipped: SEO_KIT_CRUX_API_KEY is absent"
    result = json_api(client, CRUX_ENDPOINT, {"origin": origin, "formFactor": "PHONE", "metrics": list(METRICS)}, {"X-Goog-Api-Key": api_key})
    record = result.get("record", {})
    metrics = record.get("metrics", {})
    period = record.get("collectionPeriod", {})
    first, last = period.get("firstDate", {}), period.get("lastDate", {})
    if not first or not last:
        return {}, "CrUX returned no collection period"
    format_date = lambda value: f"{value['year']:04d}-{value['month']:02d}-{value['day']:02d}"
    evidence = {}
    for metric, check in METRICS.items():
        value = metrics.get(metric, {}).get("percentiles", {}).get("p75")
        try:
            value = float(value)
        except (ValueError, TypeError):
            continue
        if not math.isfinite(value) or value < 0:
            continue
        evidence[check] = {"kind": "field_p75", "value": value, "source": "Chrome UX Report API, PHONE origin record", "date": datetime.now(timezone.utc).date().isoformat(), "period": f"{format_date(first)} to {format_date(last)}", "scope": origin}
    return evidence, None if evidence else "CrUX returned no Core Web Vitals p75 data"


def gsc_evidence(client, origin, urls, property_url, token, max_inspections, existing=None, on_result=None):
    if not property_url:
        return {}, [], "Search Console skipped: property or SEO_KIT_GSC_ACCESS_TOKEN is absent"
    host = urlsplit(origin).hostname
    valid_domain_property = property_url.startswith("sc-domain:") and (host == property_url[10:] or host.endswith("." + property_url[10:]))
    if not (valid_domain_property or property_url == origin + "/"):
        raise ValueError("--gsc-property must be the selected origin URL-prefix or a sc-domain property")
    existing = {item['url']: item for item in (existing or []) if item.get('url') in urls}
    selected = [url for url in urls if url not in existing][:max_inspections]
    findings = list(existing.values())
    if selected and not token:
        return {}, findings, 'Search Console skipped: SEO_KIT_GSC_ACCESS_TOKEN is absent'
    for url in selected:
        try:
            result = json_api(client, GSC_ENDPOINT, {"inspectionUrl": url, "siteUrl": property_url}, {"Authorization": "Bearer " + token})
        except (OSError, ValueError) as error:
            return {}, findings, f'Search Console sample incomplete: {error}'
        status = result.get("inspectionResult", {}).get("indexStatusResult", {})
        findings.append({"url": url, "queried_at": datetime.now(timezone.utc).isoformat(), "verdict": status.get("verdict"), "coverage_state": status.get("coverageState"), "google_canonical": status.get("googleCanonical"), "user_canonical": status.get("userCanonical"), "page_fetch_state": status.get("pageFetchState"), "rich_results": result.get("inspectionResult", {}).get("richResultsResult")})
        if on_result:
            on_result(findings[-1])
    if len(findings) != len(urls):
        return {}, findings, "Search Console inspected a sample only. Indexing score remains unmeasured"
    if not findings or any(item["verdict"] not in ("PASS", "FAIL", "NEUTRAL") for item in findings):
        return {}, findings, "Search Console returned incomplete indexing verdicts"
    passed = all(item["verdict"] == "PASS" and item["page_fetch_state"] == "SUCCESSFUL" and (not item["google_canonical"] or not item["user_canonical"] or normalize_url(item["google_canonical"]) == normalize_url(item["user_canonical"])) for item in findings)
    detail = f"Inspected {len(findings)} of {len(urls)} crawled URLs, indexed verdicts and canonicals: " + ", ".join(f"{item['url']}={item['verdict']}, Google={item['google_canonical']}, declared={item['user_canonical']}" for item in findings)
    query_dates = sorted(item.get('queried_at', datetime.now(timezone.utc).isoformat())[:10] for item in findings)
    evidence = {"technical.indexing": {"status": "pass" if passed else "fail", "detail": detail, "source": "Search Console URL Inspection API (indexed version)", "date": query_dates[-1], "period": f"indexed states queried {query_dates[0]} to {query_dates[-1]}", "scope": origin}}
    return evidence, findings, None


def backlink_summary(path, origin, source, period):
    """Summarize a bounded, normalized provider export without judging link quality."""
    file = Path(path)
    if file.stat().st_size > 10_000_000:
        raise ValueError("backlink export exceeds 10 MB")
    domains = Counter()
    anchors = Counter()
    links = 0
    with file.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"source_url", "target_url", "anchor_text"}.issubset(reader.fieldnames or []):
            raise ValueError("backlink CSV requires source_url,target_url,anchor_text columns")
        for row in reader:
            links += 1
            if links > 10000:
                raise ValueError("backlink export exceeds 10,000 rows")
            target = urlsplit(row["target_url"])
            if target.scheme != "https" or target.netloc.lower() != urlsplit(origin).netloc.lower():
                raise ValueError("backlink target is outside the audited origin")
            source_url = urlsplit(row["source_url"])
            domain = source_url.hostname
            if source_url.scheme not in ("http", "https") or not domain:
                raise ValueError("backlink row has an invalid source_url")
            domains[domain.lower()] += 1
            anchors[(row["anchor_text"] or "").strip()[:160]] += 1
    return {"source": source, "date": datetime.now(timezone.utc).date().isoformat(), "period": period, "scope": origin, "links_in_export": links, "referring_domains_in_export": len(domains), "top_referring_domains": domains.most_common(10), "top_anchors": anchors.most_common(10), "note": "Provider export sample only. Relevance, spam risk and authority require reviewed evidence."}


def run_live(args, client=None):
    database = getattr(args, 'database', None)
    if database:
        with database_lock(Path(database).resolve()):
            return _run_live(args, client)
    return _run_live(args, client)


def _run_live(args, client=None):
    missing = [name for name in ('lxml', 'PIL', 'pypdf', 'langcodes') if importlib.util.find_spec(name) is None]
    if missing:
        raise ValueError('missing audit engines: ' + ', '.join(missing) + '. Run npm run setup:audit or install .agents/requirements-audit.txt in SEO_KIT_PYTHON')
    start = checked_url(args.url)
    if sensitive_url(start):
        raise ValueError('start URL contains sensitive parameters, choose a public URL')
    parsed = urlsplit(start)
    origin = urlunsplit(("https", parsed.netloc, "", "", ""))
    if not same_origin(start, origin):
        raise ValueError("invalid start URL")
    property_url = getattr(args, 'gsc_property', None)
    if property_url:
        host = parsed.hostname
        domain = property_url.removeprefix('sc-domain:')
        if not (property_url == origin + '/' or (property_url.startswith('sc-domain:') and (host == domain or host.endswith('.' + domain)))):
            raise ValueError('--gsc-property must cover the audited origin')
    client = client or SafeClient(max_requests=args.max_requests, max_bytes=getattr(args, 'max_response_bytes', 2_000_000), delay=args.delay)
    if isinstance(client, SafeClient):
        client.disk_guard = None
    limit = getattr(args, 'crawl_limit', None) or str(getattr(args, 'max_pages', 100))
    page_limit = None if limit == 'unlimited' else int(limit)
    excluded_parameters = tuple(getattr(args, 'exclude_parameter', []) or [])
    excluded_paths = tuple(getattr(args, 'exclude_path', []) or [])
    resource_hosts = tuple(getattr(args, 'resource_host', []) or [])
    thresholds = getattr(args, 'thresholds', None) or {}
    config = {'thresholds': thresholds, 'max_sitemaps': getattr(args, 'max_sitemaps', 5), 'resource_limit': getattr(args, 'resource_limit', 100), 'excluded_parameters': list(excluded_parameters), 'excluded_paths': list(excluded_paths), 'amp_validator': str(getattr(args, 'amp_validator', '') or ''), 'render': args.render, 'resource_hosts': list(resource_hosts)}
    html_storage = getattr(args, 'store_html', 'both')
    config['privacy'] = {'version': 1, 'store_html': html_storage}
    database = getattr(args, 'database', None)
    temporary_database = tempfile.TemporaryDirectory(prefix='seo-kit-crawl-') if not database else None
    store = CrawlStore(database or str(Path(temporary_database.name) / 'crawl.sqlite'), store_html=html_storage)
    try:
        if store.disk_bytes() >= getattr(args, 'max_disk_bytes', 100_000_000):
            raise ValueError('disk budget exhausted by the existing crawl database')
        crawl_id, resumed = store.start(origin, start, limit, config, getattr(args, 'resume', False))
    except Exception:
        store.close()
        if temporary_database:
            temporary_database.cleanup()
        raise
    started = time.monotonic()
    if isinstance(client, SafeClient):
        client.deadline = started + getattr(args, 'max_seconds', 3600)
    warnings = []
    discovery_records = []
    record_discovery = lambda source, kind, response: discovery_records.append(store.resource_values(crawl_id, source, kind, response))
    try:
        record = lambda source, kind, response: store.resource(crawl_id, source, kind, response)
        def record_observation(url, kind, status, data):
            store.observation(crawl_id, url, kind, status, data)
            if kind == 'axe_accessibility':
                for violation in data.get('violations', []):
                    store.issue(crawl_id, url, 'accessibility.axe.' + violation['id'],
                                'error' if violation.get('impact') in ('critical','serious') else 'warning', violation, source='axe-core')
        robots, robots_text = read_robots(client, origin, record_discovery)
    except Exception:
        store.close()
        if temporary_database:
            temporary_database.cleanup()
        raise
    previous_robots = store.db.execute('SELECT robots_text FROM crawls WHERE id=?', (crawl_id,)).fetchone()[0]
    if resumed and previous_robots is not None and previous_robots != redact_text(robots_text):
        store.close()
        if temporary_database:
            temporary_database.cleanup()
        raise ValueError('robots.txt changed since the interrupted crawl. Start a new crawl')
    store.db.execute('UPDATE crawls SET robots_text=? WHERE id=?', (redact_text(robots_text), crawl_id))
    store.db.commit()
    declared_delay = robots.crawl_delay(USER_AGENT)
    if declared_delay:
        client.delay = max(client.delay, declared_delay)
    if not robots.can_fetch(USER_AGENT, start):
        store.close()
        if temporary_database:
            temporary_database.cleanup()
        raise ValueError("robots.txt disallows the start URL")
    sitemap_provenance = []
    discovered = sitemap_urls(client, origin, robots_text, warnings, max_sitemaps=getattr(args, 'max_sitemaps', 5), record=record_discovery, robots=robots, on_url=lambda url, source: sitemap_provenance.append((url, source)))
    if resumed:
        previous_sitemap_urls = {row[0] for row in store.db.execute('SELECT url FROM queue WHERE crawl_id=? AND source="sitemap"', (crawl_id,))}
        if {url_key(url, excluded_parameters) for url in discovered} - {url_key(start, excluded_parameters)} != previous_sitemap_urls:
            store.close()
            if temporary_database:
                temporary_database.cleanup()
            raise ValueError('sitemap URLs changed since the interrupted crawl. Start a new crawl')
    with store.batch():
        for values in discovery_records:
            store.resource_record(values)
        for url, source in sitemap_provenance:
            store.observation(crawl_id, url, 'sitemap_membership', 'measured', {'sitemap': source})
    if not resumed:
        with store.batch():
            store.enqueue(crawl_id, url_key(start, excluded_parameters), 0, 'start')
            for url in discovered:
                store.enqueue(crawl_id, url_key(url, excluded_parameters), 0, 'sitemap')
    visited = set()
    failed_pages = []
    skipped_pages = []
    fetched = {}
    used_files = set()
    link_status = {}
    link_checks_complete = True
    try:
        browser_pair, browser_note = get_browser(args.render)
    except Exception:
        store.close()
        if temporary_database:
            temporary_database.cleanup()
        raise
    if browser_note:
        warnings.append(browser_note)
    render_policies = {urlsplit(origin).hostname: robots}
    try:
        with tempfile.TemporaryDirectory(prefix="seo-kit-live-") as temporary:
            root = Path(temporary)
            (root / "robots.txt").write_text(robots_text, encoding="utf-8")
            sitemap = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            for url in discovered:
                ElementTree.SubElement(ElementTree.SubElement(sitemap, "url"), "loc").text = url
            if discovered:
                ElementTree.ElementTree(sitemap).write(root / "sitemap.xml", encoding="unicode", xml_declaration=True)
            materialized_bytes = sum(file.stat().st_size for file in root.iterdir() if file.is_file())
            if isinstance(client, SafeClient):
                client.disk_guard = lambda: store.disk_bytes() + materialized_bytes < getattr(args, 'max_disk_bytes', 100_000_000)
            while store.pending(crawl_id) and (page_limit is None or store.count(crawl_id) < page_limit):
                if time.monotonic() - started >= getattr(args, 'max_seconds', 3600):
                    warnings.append('crawl stopped by time limit')
                    break
                if store.disk_bytes() + materialized_bytes >= getattr(args, 'max_disk_bytes', 100_000_000):
                    warnings.append('crawl stopped by disk byte limit')
                    break
                item = store.next_url(crawl_id)
                url = item['url']
                depth = item['depth']
                try:
                    url = audit_url(url, origin)
                except ValueError:
                    store.mark(crawl_id, item['url'], 'excluded')
                    continue
                key = url_key(url, excluded_parameters)
                if key in visited:
                    store.mark(crawl_id, item['url'], 'done')
                    continue
                if any(re.search(pattern, urlsplit(url).path) for pattern in excluded_paths):
                    skipped_pages.append(url)
                    store.mark(crawl_id, item['url'], 'excluded')
                    continue
                visited.add(key)
                if not robots.can_fetch(USER_AGENT, url):
                    warnings.append(f"robots disallows {url}")
                    skipped_pages.append(url)
                    store.mark(crawl_id, item['url'], 'excluded')
                    continue
                try:
                    response = client.fetch(url, authorize=lambda target: robots.can_fetch(USER_AGENT, target))
                    store.db.execute('DELETE FROM issues WHERE crawl_id=? AND url=? AND source="crawler"', (crawl_id, url))
                    store.commit()
                    link_status[normalize_url(url)] = response.status
                    if response.status != 200 or "text/html" not in response.headers.get("content-type", ""):
                        warnings.append(f"page {url}: HTTP {response.status} or non-HTML response")
                        if response.status != 200:
                            failed_pages.append(f"{url}=HTTP {response.status}")
                        binary_metadata = {}
                        if response.status == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                            try:
                                binary_metadata = binary_worker('pdf', response.body)
                                store.observation(crawl_id, url, 'pdf', binary_metadata.get('status', 'measured'), binary_metadata)
                                store.add_references(crawl_id, [(url, urljoin(url, target), '', 'pdf_link') for target in binary_metadata.get('links', [])], [(url_key(urljoin(url, target)), depth + 1, 'pdf_link') for target in binary_metadata.get('links', []) if same_origin(urljoin(url, target), origin)])
                            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                                store.observation(crawl_id, url, 'pdf', 'unmeasured', {'reason': str(error)})
                        store.save_page(crawl_id, url, depth, response=response, metadata=binary_metadata)
                        store.resource(crawl_id, url, 'non_html', response)
                        if response.status >= 400:
                            store.issue(crawl_id, url, 'http.response', 'error', {'status': response.status, 'content_type': response.headers.get('content-type')})
                        elif response.status == 200:
                            store.issue(crawl_id, url, 'resource.non_html', 'info', {'content_type': response.headers.get('content-type'), 'body_size': len(response.body)})
                        store.mark(crawl_id, item['url'], 'done')
                        continue
                    raw_html = response.body.decode("utf-8", "replace")
                    html = raw_html
                    did_render = False
                    if store.disk_bytes() + materialized_bytes + 2 * len(response.body) > getattr(args, 'max_disk_bytes', 100_000_000):
                        warnings.append('crawl stopped by disk byte limit')
                        store.mark(crawl_id, item['url'], 'pending')
                        break
                    if browser_pair and (args.render == "always" or needs_render(html)):
                        try:
                            html = render_page(response.url, client, origin, robots, browser_pair[1], warnings, resource_hosts, record, render_policies, lambda kind, status, data: record_observation(url, kind, status, data))
                            did_render = True
                        except Exception as error:
                            if args.render == "always":
                                raise ValueError(f"render failed for {url}: {type(error).__name__}: {error}") from error
                            warnings.append(f"render failed for {url}, raw HTML used: {type(error).__name__}")
                    projected_bytes = len(response.body) + (len(html.encode('utf-8')) if did_render else 0)
                    if store.disk_bytes() + materialized_bytes + projected_bytes + len(html.encode('utf-8')) > getattr(args, 'max_disk_bytes', 100_000_000):
                        warnings.append('crawl stopped by disk byte limit')
                        store.mark(crawl_id, item['url'], 'pending')
                        break
                    if urlsplit(url).query:
                        file = root / '__query__' / hashlib.sha256(url.encode()).hexdigest() / 'index.html'
                    else:
                        file = page_file(root, response.url)
                    if file in used_files:
                        file = root / '__collision__' / hashlib.sha256(url.encode()).hexdigest() / 'index.html'
                    used_files.add(file)
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text(html, encoding="utf-8")
                    materialized_bytes += file.stat().st_size
                    visited.add(url_key(response.url, excluded_parameters))
                    fetched[response.url] = (response, file)
                    doc = Document()
                    doc.feed(html)
                    extra = advanced_metadata(html, response)
                    fingerprint, word_count = content_fingerprint(extra['main_text'])
                    metadata = {'title': doc.title, 'description': doc.metas('description'), 'canonicals': doc.canonicals, 'headings': doc.headings, 'language': doc.lang, 'meta_robots': doc.metas('robots'), 'link_elements': doc.link_elements, 'html_attributes': doc.html_attributes, 'content_fingerprint': fingerprint, 'word_count': word_count, 'rendered': did_render}
                    metadata.update({key: value for key, value in extra.items() if key != 'main_text'})
                    inspect_advanced(store, crawl_id, url, response, html, metadata, thresholds)
                    store.save_page(crawl_id, url, depth, response=response, raw=raw_html, rendered=html if did_render else None, metadata=metadata)
                    inspect_page(store, crawl_id, url, response, doc)
                    if 'amp' in doc.html_attributes or '⚡' in doc.html_attributes:
                        validator = getattr(args, 'amp_validator', None)
                        if validator:
                            try:
                                result = subprocess.run(['node', str(Path(__file__).with_name('validate-amp.mjs')), str(Path(validator).resolve())], input=raw_html, text=True, capture_output=True, timeout=20)
                                if result.returncode:
                                    raise ValueError('AMP validator execution failed')
                                data = json.loads(result.stdout)
                                if data.get('status') not in ('PASS','FAIL') or not isinstance(data.get('errors'),list):
                                    raise ValueError('AMP validator returned no usable result')
                                store.observation(crawl_id, url, 'amp_validation', 'measured', data)
                                if data['status'] != 'PASS':
                                    store.issue(crawl_id, url, 'amp.validation_error', 'warning', data)
                            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                                store.observation(crawl_id, url, 'amp_validation', 'unmeasured', {'reason': str(error)})
                        else:
                            store.observation(crawl_id, url, 'amp_validation', 'unmeasured', {'reason': '--amp-validator local validator bundle required'})
                    if not doc.title:
                        store.issue(crawl_id, url, 'metadata.title_missing', 'warning', {'title': doc.title})
                    if len(doc.canonicals) > 1:
                        store.issue(crawl_id, url, 'indexability.multiple_canonicals', 'warning', {'canonicals': doc.canonicals})
                    if len(doc.canonicals) == 1 and url_key(urljoin(response.url, doc.canonicals[0]), excluded_parameters) != url_key(response.url, excluded_parameters):
                        store.issue(crawl_id, url, 'indexability.canonical_other_url', 'info', {'declared': doc.canonicals[0], 'fetched': response.url})
                    if html != raw_html:
                        raw_doc = Document()
                        raw_doc.feed(raw_html)
                        differences = {name: {'raw': getattr(raw_doc, name), 'rendered': getattr(doc, name)} for name in ('title', 'links', 'canonicals', 'headings') if getattr(raw_doc, name) != getattr(doc, name)}
                        for name in ('description', 'robots'):
                            if raw_doc.metas(name) != doc.metas(name):
                                differences[name] = {'raw': raw_doc.metas(name), 'rendered': doc.metas(name)}
                        raw_content = ' '.join(' '.join(raw_doc.text).split())
                        rendered_content = ' '.join(' '.join(doc.text).split())
                        if raw_content != rendered_content:
                            differences['content'] = {'raw_sha256': hashlib.sha256(raw_content.encode()).hexdigest(),
                                                      'rendered_sha256': hashlib.sha256(rendered_content.encode()).hexdigest(),
                                                      'raw_characters': len(raw_content), 'rendered_characters': len(rendered_content)}
                        if differences:
                            store.issue(crawl_id, url, 'render.dom_difference', 'info', differences)
                    references = []
                    targets = []
                    for link in doc.links:
                        href = link["href"]
                        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                            continue
                        target = urljoin(response.url, href)
                        if same_origin(target, origin):
                            target = url_key(target, excluded_parameters)
                            references.append((url, target, link['text'] or link['aria'], 'internal'))
                            targets.append((target, depth + 1, 'link'))
                        elif urlsplit(target).scheme in ('http', 'https'):
                            references.append((url, target.split('#', 1)[0], link['text'] or link['aria'], 'external'))
                    for image in doc.images:
                        src = image.get('src')
                        if src and urlsplit(urljoin(response.url, src)).scheme in ('http', 'https'):
                            references.append((url, urljoin(response.url, src).split('#', 1)[0], image.get('alt', ''), 'image'))
                    for element in doc.link_elements:
                        href = element.get('href')
                        rel = element.get('rel', '').lower().split()
                        if href and set(rel) & {'alternate', 'next', 'prev', 'amphtml'}:
                            target = urljoin(response.url, href)
                            if same_origin(target, origin):
                                target = url_key(target, excluded_parameters)
                                references.append((url, target, element.get('hreflang', ''), 'document_relation'))
                                targets.append((target, depth + 1, 'document_relation'))
                            elif urlsplit(target).scheme in ('http', 'https'):
                                references.append((url, target.split('#', 1)[0], element.get('hreflang', ''), 'document_relation_external'))
                    store.add_references(crawl_id, references, targets)
                    store.mark(crawl_id, item['url'], 'done')
                except (OSError, ValueError) as error:
                    if args.render == "always" and "render failed" in str(error):
                        raise
                    warnings.append(f"page {url}: {type(error).__name__}: {error}")
                    failed_pages.append(f"{url}={type(error).__name__}")
                    store.save_page(crawl_id, url, depth, error=f'{type(error).__name__}: {error}')
                    store.issue(crawl_id, url, 'crawl.fetch_error', 'error', {'error': str(error)})
                    store.mark(crawl_id, item['url'], 'error' if 'budget exhausted' not in str(error) else 'pending')
                    if "budget exhausted" in str(error):
                        break
            store.db.execute("DELETE FROM issues WHERE crawl_id=? AND (rule_id LIKE 'content.%' OR rule_id='metadata.duplicate_title' OR rule_id IN ('hreflang.return_link_missing','hreflang.target_unmeasured','hreflang.external_target_unmeasured') OR rule_id IN ('amp.target_unmeasured','amp.markup_missing','amp.canonical_return_missing','links.broken_internal') OR rule_id LIKE 'sitemap.%')", (crawl_id,))
            store.commit()
            inspect_site(store, crawl_id)
            site_advanced(store, crawl_id)
            inspect_references(store, crawl_id, client, origin, robots, resource_hosts, getattr(args, 'resource_limit', 100), thresholds.get('image_max_bytes', 200000))
            failed_pages = [f"{row['url']}=HTTP {row['status']}" if row['status'] is not None else f"{row['url']}={row['error']}"
                            for row in store.db.execute('SELECT url,status,error FROM pages WHERE crawl_id=? AND (status!=200 OR error IS NOT NULL)', (crawl_id,))]
            skipped_pages = [row[0] for row in store.db.execute('SELECT url FROM queue WHERE crawl_id=? AND state="excluded"', (crawl_id,))]
            for row in store.db.execute('SELECT url,status FROM pages WHERE crawl_id=? AND status IS NOT NULL', (crawl_id,)):
                link_status[normalize_url(row['url'])] = row['status']
            for row in store.db.execute('SELECT * FROM pages WHERE crawl_id=? AND (raw_html IS NOT NULL OR rendered_html IS NOT NULL)', (crawl_id,)):
                if row['final_url'] in fetched:
                    continue
                file = root / '__stored__' / hashlib.sha256(row['url'].encode()).hexdigest() / 'index.html'
                html_bytes = row['rendered_html'] or row['raw_html']
                if store.disk_bytes() + materialized_bytes + len(html_bytes) > getattr(args, 'max_disk_bytes', 100_000_000):
                    raise ValueError('disk budget exhausted while preparing the stored report. Increase --max-disk-bytes to resume')
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(html_bytes)
                materialized_bytes += file.stat().st_size
                from live_http import Response
                response = Response(row['final_url'] or row['url'], row['status'], json.loads(row['headers_json']), row['raw_html'] or row['rendered_html'], json.loads(row['redirects_json']))
                fetched[row['final_url'] or row['url']] = (response, file)
            if not fetched:
                raise ValueError("no HTML pages could be audited")
            if store.pending(crawl_id):
                warnings.append("crawl truncated by page or request budget")
            for url, (response, _) in fetched.items():
                key = normalize_url(url)
                link_status[key] = response.status
            # Verify linked destinations that were not in the HTML sample, within the same request budget.
            for url, (_, file) in fetched.items():
                doc = Document()
                doc.feed(file.read_text(encoding="utf-8"))
                for link in doc.links:
                    target = urljoin(url, link["href"])
                    if not same_origin(target, origin):
                        continue
                    key = normalize_url(target)
                    if key in link_status:
                        continue
                    if not robots.can_fetch(USER_AGENT, target):
                        link_checks_complete = False
                        continue
                    try:
                        status = client.fetch(target, method="HEAD", authorize=lambda destination: robots.can_fetch(USER_AGENT, destination)).status
                        if status in (405, 501):
                            status = client.fetch(target, authorize=lambda destination: robots.can_fetch(USER_AGENT, destination)).status
                        link_status[normalize_url(target)] = status
                    except (OSError, ValueError):
                        warnings.append(f"link status unavailable: {target}")
                        link_checks_complete = False
            broken_by_source = {}
            for row in store.db.execute('SELECT source_url,target_url FROM links WHERE crawl_id=? AND source_kind="internal"', (crawl_id,)):
                status = link_status.get(normalize_url(row['target_url']))
                if status is not None and status >= 400:
                    broken_by_source.setdefault(row['source_url'], []).append({'target': row['target_url'], 'status': status})
            for source_url, broken in broken_by_source.items():
                store.issue(crawl_id, source_url, 'links.broken_internal', 'error', {'links': broken})
            for sitemap_url in discovered:
                row = store.db.execute('SELECT status,metadata_json,headers_json FROM pages WHERE crawl_id=? AND url=?', (crawl_id, url_key(sitemap_url, excluded_parameters))).fetchone()
                if not row:
                    store.issue(crawl_id, sitemap_url, 'sitemap.target_unmeasured', 'info', {'reason': 'outside completed crawl scope'})
                elif row['status'] != 200 or any('noindex' in value.lower() for value in json.loads(row['metadata_json'] or '{}').get('meta_robots', [])) or 'noindex' in json.loads(row['headers_json'] or '{}').get('x-robots-tag', '').lower():
                    store.issue(crawl_id, sitemap_url, 'sitemap.non_indexable_target', 'warning', {'status': row['status']})
            evidence = {"checks": {}}
            if args.evidence:
                evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
            if not isinstance(evidence, dict) or not isinstance(evidence.get("checks"), dict):
                raise ValueError("--evidence must contain a checks object")
            auto_checks = {}
            if skipped_pages:
                warnings.append(f"{len(skipped_pages)} discovered URLs were excluded by robots or path rules")
            discovery_incomplete = any('sitemap' in warning.lower() and any(term in warning.lower() for term in ('truncated', 'unavailable', 'blocked', 'unsupported', 'http 5', 'http 401', 'http 403')) for warning in warnings)
            crawl_complete = not store.pending(crawl_id) and not skipped_pages and not discovery_incomplete and not any("budget exhausted" in warning for warning in warnings)
            if crawl_complete:
                auto_checks["technical.http"] = {"status": "fail" if failed_pages else "pass", "detail": f"Checked {len(visited)} discovered pages, failures: {', '.join(failed_pages) if failed_pages else 'none'}, redirect chains and headers recorded separately", "source": "bounded live HTTPS crawl", "date": datetime.now(timezone.utc).date().isoformat(), "period": "current request", "scope": origin}
            else:
                warnings.append("HTTP site-wide score unmeasured because the crawl was incomplete")
            if args.crux:
                try:
                    stored_crux = [json.loads(row[0]) for row in store.db.execute('SELECT data_json FROM external_data WHERE crawl_id=? AND source="crux_field"', (crawl_id,))]
                    checks = {item['check']: {key: value for key, value in item.items() if key != 'check'} for item in stored_crux}
                    note = None
                    if not checks:
                        checks, note = crux_evidence(client, origin, os.environ.get("SEO_KIT_CRUX_API_KEY"))
                    auto_checks.update(checks)
                    if not stored_crux:
                        for check_id, value in checks.items():
                            store.external(crawl_id, origin, 'crux_field', origin, value['period'], {'check': check_id, **value})
                    if note:
                        warnings.append(note)
                except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                    warnings.append(f"CrUX unavailable: {type(error).__name__}: {error}")
            priorities = {url_key(url): index for index,url in enumerate(getattr(args, 'priority_url', []))}
            priority_urls = sorted(fetched, key=lambda url: (priorities.get(url_key(url), len(priorities)), url))
            inspections = []
            if args.gsc_property:
                try:
                    stored_inspections = [json.loads(row[0]) for row in store.db.execute('SELECT data_json FROM external_data WHERE crawl_id=? AND source="search_console_url_inspection" AND property=?', (crawl_id, args.gsc_property))]
                    checks, inspections, note = gsc_evidence(client, origin, priority_urls, args.gsc_property, os.environ.get("SEO_KIT_GSC_ACCESS_TOKEN"), args.max_inspections, stored_inspections, lambda item: store.external(crawl_id, item['url'], 'search_console_url_inspection', args.gsc_property, 'indexed state at query time', item))
                    auto_checks.update(checks)
                    stored_urls = {item['url'] for item in stored_inspections}
                    for item in inspections:
                        if item['url'] not in stored_urls:
                            store.external(crawl_id, item['url'], 'search_console_url_inspection', args.gsc_property, 'indexed state at query time', item)
                    if note:
                        warnings.append(note)
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    warnings.append(f"Search Console unavailable: {type(error).__name__}: {error}")
            external_summary = enrich(store, crawl_id, origin,
                priority_urls,
                client, ga4_property=getattr(args, 'ga4_property', None),
                gsc_property=args.gsc_property if getattr(args, 'gsc_performance', False) else None,
                period=(args.period_start, args.period_end) if getattr(args, 'period_start', None) and getattr(args, 'period_end', None) else None,
                psi_limit=getattr(args, 'psi_limit', 0), moz_limit=getattr(args, 'moz_limit', 0),
                api_limit=getattr(args, 'api_limit', 50), crux_limit=getattr(args, 'crux_limit', 0))
            warnings.extend(external_summary['warnings'])
            evidence["checks"] = {**auto_checks, **evidence["checks"]}
            page_urls = {"/" + file.relative_to(root).as_posix().removesuffix("index.html"): url for url, (_, file) in fetched.items()}
            report = audit(root, origin, evidence, live=True, link_status=link_status, page_urls=page_urls)
            if not link_checks_complete:
                for check in report['checks']:
                    if check['id'] == 'technical.internal_links':
                        for finding in check['findings']:
                            if finding['status'] != 'fail':
                                finding['status'] = 'unmeasured'
                        check['findings'].append({'status': 'unmeasured', 'location': 'site',
                                                  'detail': 'Some destinations were unavailable or robots-blocked'})
                        break
                refresh_report(report)
                warnings.append('internal link status check incomplete because some destinations were unavailable or robots-blocked. Confirmed failures retained')
            report["site"] = None
            report['schema_version'] = 2
            report['crawl_database_schema_version'] = SCHEMA_VERSION
            report['crawl_id'] = crawl_id
            report['database'] = database
            report["start_url"] = start
            report["crawled_urls"] = [row[0] for row in store.db.execute('SELECT url FROM pages WHERE crawl_id=? ORDER BY url', (crawl_id,))]
            report["requests"] = client.requests
            report["crawl_complete"] = crawl_complete
            report["complete"] = report["complete"] and crawl_complete
            report["warnings"] = warnings
            report["search_console_inspections"] = inspections
            report['external_data_coverage'] = external_summary
            report["rich_result_issues"] = [
                {"url": item["url"], "type": group.get("richResultType"), "item": detected.get("name"), "severity": issue.get("severity"), "message": issue.get("issueMessage")}
                for item in inspections
                for group in (item.get("rich_results") or {}).get("detectedItems", [])
                for detected in group.get("items", [])
                for issue in detected.get("issues", [])
            ]
            report["backlink_summary"] = backlink_summary(args.backlinks_export, origin, args.backlinks_source, args.backlinks_period) if args.backlinks_export else None
            report["http_observations"] = [
                {'url': row['url'], 'status': row['status'], 'final_url': row['final_url'],
                 'redirects': json.loads(row['redirects_json'] or '[]'),
                 'x_robots_tag': json.loads(row['headers_json'] or '{}').get('x-robots-tag'),
                 'error': row['error']}
                for row in store.db.execute('SELECT * FROM pages WHERE crawl_id=? ORDER BY url', (crawl_id,))]
            if args.baseline:
                baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8'))
                if baseline.get('schema_version') == 2:
                    baseline = {**baseline, 'schema_version': 1}
                report['comparison'] = compare({**report, 'schema_version': 1}, baseline)
            store.finish(crawl_id, crawl_complete, warnings)
            report['privacy'] = {'version': 1, 'store_html': html_storage, 'credential_filtering': True,
                                 'sensitive_urls': 'excluded from crawl queue',
                                 'personal_data': 'page content may still contain personal information. Review before sharing'}
            retention_days = getattr(args, 'retention_days', None)
            if retention_days is not None:
                report['retention'] = store.retention(retention_days, apply=True)
            return sanitize(report)
    finally:
        if browser_pair:
            browser_pair[1].close()
            browser_pair[0].stop()
        store.close()
        if temporary_database:
            temporary_database.cleanup()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded live SEO audit of a public HTTPS site")
    parser.add_argument("--url", required=True, help="public HTTPS page to start from")
    parser.add_argument("--crawl-limit", choices=('100', '500', 'unlimited'), default='100')
    parser.add_argument("--max-pages", type=int, help='legacy page limit, use --crawl-limit for new crawls')
    parser.add_argument('--database', help='SQLite database in a host-project approved location')
    parser.add_argument('--resume', action='store_true', help='resume the latest interrupted crawl with matching settings')
    parser.add_argument('--store-html', choices=('none', 'raw', 'rendered', 'both'), default='none', help='HTML retained in SQLite, default none. HTML is still analysed in private temporary files')
    parser.add_argument('--retention-days', type=int, help='explicitly delete completed unprotected crawls older than N days in this database')
    parser.add_argument('--max-seconds', type=int, default=3600)
    parser.add_argument('--max-disk-bytes', type=int, default=100_000_000)
    parser.add_argument('--max-response-bytes', type=int, default=2_000_000)
    parser.add_argument('--exclude-parameter', action='append', default=[])
    parser.add_argument('--exclude-path', action='append', default=[], help='regular expression matched against URL path')
    parser.add_argument('--resource-host', action='append', default=[], help='authorized HTTPS host for images, alternates and render resources')
    parser.add_argument('--amp-validator', help='official AMP validator JS bundle outside this repository, no runtime downloads')
    parser.add_argument('--resource-limit', type=int, default=100, help='maximum image/external status queries per run')
    parser.add_argument('--thresholds', type=json.loads, help='JSON object with title_max, description_max, image_max_bytes')
    parser.add_argument("--max-requests", type=int, default=2000)
    parser.add_argument("--max-inspections", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.2, help="minimum seconds between requests")
    parser.add_argument("--render", choices=("auto", "always", "never"), default="auto")
    parser.add_argument("--crux", action="store_true", help="query CrUX with SEO_KIT_CRUX_API_KEY")
    parser.add_argument("--gsc-property", help="Search Console property, token from SEO_KIT_GSC_ACCESS_TOKEN")
    parser.add_argument('--gsc-performance', action='store_true', help='query Search Console performance for --gsc-property and date range')
    parser.add_argument('--ga4-property', help='numeric GA4 property, token from SEO_KIT_GA4_ACCESS_TOKEN')
    parser.add_argument('--period-start', help='external data start date YYYY-MM-DD')
    parser.add_argument('--period-end', help='external data end date YYYY-MM-DD')
    parser.add_argument('--psi-limit', type=int, default=0, help='maximum PageSpeed laboratory queries')
    parser.add_argument('--moz-limit', type=int, default=0, help='maximum Moz link sample rows, capped at 50')
    parser.add_argument('--max-sitemaps', type=int, default=5, help='maximum sitemap documents including nested indexes')
    parser.add_argument('--priority-url', action='append', default=[], help='audited URL to prioritize for API quotas, repeat in priority order')
    parser.add_argument('--crux-limit', type=int, default=0, help='maximum URL-level CrUX field queries')
    parser.add_argument('--api-limit', type=int, default=50, help='maximum GA4/GSC rows and priority URLs')
    parser.add_argument("--evidence", help="optional reviewed evidence JSON for qualitative checks")
    parser.add_argument("--backlinks-export", help="normalized provider CSV outside this repository")
    parser.add_argument("--backlinks-source", help="provider and export identity")
    parser.add_argument("--backlinks-period", help="time range covered by the export")
    parser.add_argument("--baseline", help="previous comparable JSON report")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--output", help="write report outside this repository")
    args = parser.parse_args(argv)
    if args.retention_days is not None and args.retention_days < 1:
        parser.error('--retention-days must be positive')
    if args.max_pages is not None:
        if args.max_pages < 1:
            parser.error('--max-pages must be positive')
        args.crawl_limit = str(args.max_pages)
    if not 1 <= args.max_requests or not 1 <= args.max_inspections <= 20 or not 0 <= args.delay <= 10 or args.max_seconds < 1 or args.max_disk_bytes < 1 or args.max_response_bytes < 1:
        parser.error('request, inspection, delay, time, disk and response limits must be positive and valid')
    if not 1 <= args.max_sitemaps <= 1000:
        parser.error('--max-sitemaps must be 1..1000')
    try:
        args.priority_url = [audit_url(url, urlunsplit(('https', urlsplit(args.url).netloc, '', '', ''))) for url in args.priority_url]
    except ValueError as error:
        parser.error(redact_text(str(error)))
    if not 0 <= args.resource_limit <= 10000:
        parser.error('--resource-limit must be 0..10000')
    if args.thresholds is not None and (not isinstance(args.thresholds, dict) or any(key not in {'title_max', 'description_max', 'image_max_bytes'} or type(value) is not int or value < 1 for key, value in args.thresholds.items())):
        parser.error('--thresholds must contain supported positive integer thresholds')
    repository = Path(__file__).resolve().parents[2]
    for label in ('database', 'output', 'evidence', 'backlinks_export', 'baseline', 'amp_validator'):
        value = getattr(args, label)
        if value and Path(value).resolve().is_relative_to(repository):
            parser.error(f'--{label.replace("_", "-")} must be outside the seo-kit repository')
    if not args.database and args.output:
        args.database = str(Path(args.output).with_suffix('.sqlite'))
    if not args.database:
        parser.error('--database or --output is required to persist the crawl outside this repository')
    if args.output and any(Path(args.output).resolve() == Path(value).resolve() for value in
                           (args.database, args.evidence, args.baseline, args.backlinks_export) if value):
        parser.error('--output must differ from every input path')
    if any(not host or '/' in host or ':' in host or '@' in host for host in args.resource_host):
        parser.error('--resource-host accepts DNS hostnames only')
    for pattern in args.exclude_path:
        try:
            re.compile(pattern)
        except re.error as error:
            parser.error(f'invalid --exclude-path: {error}')
    if args.gsc_performance and not args.gsc_property:
        parser.error('--gsc-performance requires --gsc-property')
    if args.period_start or args.period_end:
        try:
            start_date = datetime.strptime(args.period_start or '', '%Y-%m-%d').date()
            end_date = datetime.strptime(args.period_end or '', '%Y-%m-%d').date()
        except ValueError:
            parser.error('--period-start and --period-end must both use YYYY-MM-DD')
        if start_date > end_date:
            parser.error('period start must not be after period end')
    if not 0 <= args.crux_limit <= args.api_limit or not 1 <= args.api_limit <= 25000 or not 0 <= args.psi_limit <= args.api_limit or not 0 <= args.moz_limit <= 50:
        parser.error('API limits must be bounded. Moz is capped at 50 rows')
    if args.backlinks_export and (not args.backlinks_source or not args.backlinks_period):
        parser.error("--backlinks-export requires --backlinks-source and --backlinks-period")
    try:
        report = run_live(args)
        if args.format == "json":
            output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        else:
            lines = [f"Live SEO audit: {report['start_url']}", f"Pages: {report['pages']} | Requests: {report['requests']} | Score: {report['score']}/100 | Coverage: {report['coverage']}% | Rubric: {report['scoring_version']}",
                     f"Checklist score bounds: {report['score_bounds']} | Critical failures: {len(report['critical_failures'])}, not a ranking prediction"]
            lines.extend(f"[{item['status'].upper()}] {item['id']}" for item in report["checks"])
            lines.extend(f"Rich result {item['severity']}: {item['url']} ({item['type']}): {item['message']}" for item in report["rich_result_issues"])
            if report["backlink_summary"]:
                links = report["backlink_summary"]
                lines.append(f"Backlink export: {links['links_in_export']} links from {links['referring_domains_in_export']} domains, off-page review remains unmeasured without reviewed evidence")
            lines.extend(f"Warning: {warning}" for warning in report["warnings"])
            output = "\n".join(lines) + "\n"
        with output_stream(args.output) as stream:
            stream.write(output)
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        parser.error(redact_text(str(error)))


if __name__ == "__main__":
    main()
