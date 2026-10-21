"""Advanced, bounded observations. Never infer eligibility or manual WCAG compliance."""

import io
import json
import re
import subprocess
import sys
from collections import Counter, deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from crawl_store import url_key

DEFAULT_THRESHOLDS = {'title_max': 60, 'description_max': 160, 'image_max_bytes': 200000}


def html_tree(html):
    from lxml import html as parser
    from lxml.html import HTMLParser
    return parser.fromstring(html or '<html/>', parser=HTMLParser(no_network=True, huge_tree=False))


def main_text(tree):
    main = tree.xpath('//main|//article')
    elements = main or [tree]
    return ' '.join(' '.join(element.xpath('.//text()[not(ancestor::script or ancestor::style or ancestor::nav or ancestor::header or ancestor::footer)]')) for element in elements)


def advanced_metadata(html, response):
    tree = html_tree(html)
    canonicals = re.findall(r'<([^>]+)>\s*;\s*rel\s*=\s*[\"\']?canonical\b', response.headers.get('link', ''), re.I)
    return {'titles': tree.xpath('//title/text()'), 'http_canonicals': canonicals,
            'images': [dict(element.attrib) for element in tree.xpath('//img')],
            'anchors': [dict(element.attrib) for element in tree.xpath('//a[@href]')],
            'main_text': ' '.join(main_text(tree).split())[:200000]}


def inspect_advanced(store, crawl, url, response, html, metadata, thresholds=None):
    limits = DEFAULT_THRESHOLDS | (thresholds or {})
    tree = html_tree(html)
    def issue(rule, evidence, severity='warning'):
        store.issue(crawl, url, rule, severity, evidence)
    titles = metadata['titles']
    if len(titles) > 1:
        issue('metadata.multiple_titles', {'values': titles})
    for key, values, limit in [('title', titles, limits['title_max']), ('description', metadata['description'], limits['description_max'])]:
        if any(len(value) > limit for value in values):
            issue('metadata.' + key + '_length', {'values': values, 'configured_max': limit, 'policy': 'configurable heuristic, not a search engine limit'})
        if key == 'description' and len(values) > 1:
            issue('metadata.multiple_descriptions', {'values': values})
    headings = metadata['headings']
    if sum(level == 1 for level, _ in headings) > 1:
        issue('headings.multiple_heading_one', {'values': headings})
    if not any(level == 2 for level, _ in headings):
        issue('headings.heading_two_absent', {'headings': headings}, 'info')
    if any(b[0] > a[0] + 1 for a, b in zip(headings, headings[1:])):
        issue('headings.skipped_level', {'headings': headings})
    canonical = metadata['canonicals'] + metadata['http_canonicals']
    absolute = {url_key(urljoin(response.url, value)) for value in canonical}
    if len(absolute) > 1:
        issue('indexability.canonical_conflict', {'html': metadata['canonicals'], 'http': metadata['http_canonicals']})
    directives = metadata['meta_robots'] + [response.headers.get('x-robots-tag', '')]
    tokens = {part for value in directives for part in re.split(r'[\s,:]+', value.lower())}
    if 'none' in tokens:
        tokens |= {'noindex', 'nofollow'}
    metadata['effective_directives'] = sorted(tokens - {''})
    if tokens & {'noindex', 'nofollow'}:
        issue('indexability.restrictive_directive', {'sources': directives, 'effective': metadata['effective_directives']}, 'info')
    if any({positive, negative} <= tokens for positive, negative in [('index', 'noindex'), ('follow', 'nofollow')]):
        issue('indexability.directive_conflict', {'sources': directives, 'effective': 'restrictive directives prevail'})
    refresh = tree.xpath('//meta[translate(@http-equiv,"REFSH","refsh")="refresh"]/@content')
    for value in refresh:
        match = re.search(r'url\s*=\s*[\"\']?(.*?)[\"\']?$', value, re.I)
        issue('http.meta_refresh', {'content': value, 'target': urljoin(url, match[1]) if match else None}, 'info')
    redirects = []
    for script in tree.xpath('//script[not(@src)]/text()'):
        redirects.extend(re.findall(r'(?:location(?:\.href)?\s*=|location\.(?:replace|assign)\()\s*[\"\']([^\"\']+)', script))
    if redirects:
        issue('http.javascript_redirect_candidate', {'targets': [urljoin(url, item) for item in redirects], 'review_required': True}, 'info')
    ids = Counter(tree.xpath('//*[@id]/@id'))
    duplicates = [identifier for identifier, count in ids.items() if count > 1]
    if duplicates:
        issue('accessibility.duplicate_id', {'ids': duplicates})
    if not metadata['language']:
        issue('accessibility.language_missing', {'element': 'html', 'wcag': '3.1.1'})
    for tag, xpath, rule in [('iframe', '//iframe[not(normalize-space(@title))]', 'frame_title_missing'),
                            ('button', '//button[not(normalize-space(string())) and not(@aria-label) and not(@aria-labelledby)]', 'button_name_missing')]:
        elements = tree.xpath(xpath)
        if elements:
            issue('accessibility.' + rule, {'elements': [dict(item.attrib) for item in elements[:100]], 'tag': tag})
    for link in metadata['link_elements']:
        language = link.get('hreflang')
        from langcodes import tag_is_valid
        if language and language != 'x-default' and (not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|\d{3}))?', language) or not tag_is_valid(language)):
            issue('hreflang.invalid_tag', {'value': language, 'href': link.get('href')})
    structured = []
    required = {'Article': ('headline',), 'NewsArticle': ('headline',), 'BlogPosting': ('headline',),
                'Product': ('name',), 'Organization': ('name',), 'Person': ('name',),
                'BreadcrumbList': ('itemListElement',), 'FAQPage': ('mainEntity',), 'Recipe': ('name',)}
    visible = ' '.join(tree.xpath('//body//text()[not(ancestor::script or ancestor::style)]')).casefold()
    for payload in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            pending = deque([json.loads(payload)])
        except ValueError:
            continue
        while pending:
            value = pending.popleft()
            if isinstance(value, list):
                pending.extend(value)
            elif isinstance(value, dict):
                pending.extend(item for item in value.values() if isinstance(item, (dict, list)))
                kinds = value.get('@type', [])
                for kind in ([kinds] if isinstance(kinds, str) else kinds if isinstance(kinds, list) else []):
                    if not isinstance(kind, str):
                        continue
                    missing = [name for name in required.get(kind, ()) if not value.get(name)]
                    invisible = [name for name in ('name', 'headline') if isinstance(value.get(name), str) and value[name].casefold() not in visible]
                    structured.append({'type': kind, 'missing_profile_properties': missing, 'text_not_found': invisible,
                                       'eligibility': 'unmeasured', 'profile': 'seo-kit observation profile v1'})
    store.observation(crawl, url, 'structured_data', 'measured' if structured else 'not_present', {'nodes': structured, 'eligibility': 'unmeasured'})
    if any(item['missing_profile_properties'] or item['text_not_found'] for item in structured):
        issue('structured_data.profile_review', {'nodes': structured, 'review_required': True}, 'info')
    store.observation(crawl, url, 'accessibility_manual', 'unmeasured', {'reason': 'automated rules cannot establish WCAG conformance'})


def site_advanced(store, crawl):
    metadata = {r['url']: json.loads(r['metadata_json'] or '{}') for r in store.db.execute('SELECT url,metadata_json FROM pages WHERE crawl_id=? AND raw_sha256 IS NOT NULL', (crawl,))}
    descriptions = {}
    for url, data in metadata.items():
        value = tuple(data.get('description', []))
        if value:
            descriptions.setdefault(value, []).append(url)
        relations = data.get('link_elements', [])
        alternatives = [item for item in relations if item.get('hreflang')]
        if alternatives and not any(url_key(urljoin(url, item.get('href', ''))) == url for item in alternatives):
            store.issue(crawl, url, 'hreflang.self_reference_missing', 'warning', {'alternates': alternatives})
        for item in relations:
            rel = set(item.get('rel', '').lower().split())
            for direction, reverse in [('next', 'prev'), ('prev', 'next')]:
                if direction not in rel:
                    continue
                target = url_key(urljoin(url, item.get('href', '')))
                other = metadata.get(target)
                if target == url:
                    store.issue(crawl, url, 'pagination.self_loop', 'warning', {'target': target})
                elif other is None:
                    store.issue(crawl, url, 'pagination.target_unmeasured', 'info', {'target': target})
                elif not any(reverse in edge.get('rel', '').lower().split() and url_key(urljoin(target, edge.get('href', ''))) == url for edge in other.get('link_elements', [])):
                    store.issue(crawl, url, 'pagination.return_missing', 'warning', {'target': target, 'expected': reverse})
    for group in descriptions.values():
        if len(group) > 1:
            for url in group:
                store.issue(crawl, url, 'metadata.duplicate_description', 'warning', {'urls': group})
    # Actual link distance ignores sitemap seeds. Unreachable URLs retain null depth.
    start = store.db.execute('SELECT start_url FROM crawls WHERE id=?', (crawl,)).fetchone()[0]
    distances, incoming, outgoing = {url_key(start): 0}, Counter(), {}
    for row in store.db.execute('SELECT DISTINCT source_url,target_url FROM links WHERE crawl_id=? AND source_kind="internal"', (crawl,)):
        outgoing.setdefault(row[0], set()).add(row[1])
        incoming[row[1]] += 1
    pending = deque(distances)
    while pending:
        source = pending.popleft()
        for target in outgoing.get(source, ()):
            if target not in distances:
                distances[target] = distances[source] + 1
                pending.append(target)
    for url in metadata:
        store.observation(crawl, url, 'architecture', 'measured', {'link_depth': distances.get(url), 'inlinks': incoming[url], 'outlinks': len(outgoing.get(url, ())), 'orphan_in_sample': url not in distances})


def inspect_binary(kind, body):
    if kind == 'image':
        from PIL import Image
        if body.lstrip().startswith(b'<svg') or b'<svg' in body[:500]:
            from lxml import etree
            tree = etree.fromstring(body, parser=etree.XMLParser(resolve_entities=False, no_network=True))
            return {'format': 'SVG', 'width': tree.get('width'), 'height': tree.get('height'), 'viewbox': tree.get('viewBox'), 'bytes': len(body)}
        with Image.open(io.BytesIO(body)) as image:
            return {'format': image.format, 'width': image.width, 'height': image.height, 'bytes': len(body)}
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(body), strict=True)
    if reader.is_encrypted:
        return {'status': 'unmeasured', 'reason': 'encrypted PDF'}
    pages, text, links = len(reader.pages), [], []
    for page in (reader.pages[index] for index in range(min(pages,100))):
        contents = page.get_contents()
        if contents is not None and len(contents.get_data()) > 5000000:
            raise ValueError('PDF content stream exceeds extraction budget')
        text.append((page.extract_text() or '')[:100000])
        for annotation in page.get('/Annots', []):
            action = annotation.get_object().get('/A', {})
            if action.get('/URI'):
                links.append(str(action['/URI']))
    return {'pages': pages, 'extracted_pages': min(pages, 100), 'metadata': {str(k): str(v) for k, v in (reader.metadata or {}).items()},
            'text': '\n'.join(text)[:1000000], 'links': links[:10000], 'truncated': pages > 100}


def binary_worker(kind, body):
    # Parse untrusted binary documents in a time/memory bounded subprocess.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), kind], input=body, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError('binary extraction failed: ' + result.stderr.decode('utf-8', 'replace')[-300:])
    return json.loads(result.stdout)


def inspect_references(store, crawl, client, origin, robots, allowed_hosts, limit=100, image_max_bytes=200000):
    from live_audit import read_robots, same_origin
    from live_http import USER_AGENT, checked_url
    from crawl_privacy import sensitive_url
    policies = {urlsplit(origin).hostname: robots}
    used = 0
    for row in store.db.execute('SELECT DISTINCT target_url,source_kind FROM links WHERE crawl_id=? AND source_kind IN ("image","external","document_relation_external") ORDER BY target_url', (crawl,)).fetchall():
        target, kind = row
        if sensitive_url(target):
            store.observation(crawl, target, kind, 'unmeasured', {'reason': 'sensitive URL excluded by privacy policy'})
            continue
        prior = store.db.execute('SELECT status FROM observations WHERE crawl_id=? AND url=? AND kind=?', (crawl, target, kind)).fetchone()
        if prior and prior[0] == 'measured':
            continue
        if used >= limit:
            store.observation(crawl, target, kind, 'unmeasured', {'reason': 'resource query limit'})
            continue
        host = urlsplit(target).hostname
        if kind != 'external' and not same_origin(target, origin) and host not in allowed_hosts:
            store.observation(crawl, target, kind, 'unmeasured', {'reason': 'resource host not authorized'})
            continue
        try:
            checked_url(target)
            used += 1
            if host not in policies:
                policies[host], _ = read_robots(client, 'https://' + host)
            policy = policies[host]
            delay = policy.crawl_delay(USER_AGENT)
            if delay:
                client.delay = max(client.delay, delay)
            response = client.fetch(target, method='HEAD' if kind == 'external' else 'GET', authorize=lambda url: policy.can_fetch(USER_AGENT, url))
            if kind == 'external' and response.status in (405, 501):
                response = client.fetch(target, authorize=lambda url: policy.can_fetch(USER_AGENT, url))
            store.resource(crawl, target, kind, response)
            detail = {'http_status': response.status, 'final_url': response.url, 'redirects': response.redirects}
            if kind == 'document_relation_external' and response.status == 200 and 'text/html' in response.headers.get('content-type', ''):
                tree = html_tree(response.body)
                detail['alternates'] = [dict(item.attrib) for item in tree.xpath('//link[@hreflang]')]
                for source in store.db.execute('SELECT source_url FROM links WHERE crawl_id=? AND target_url=? AND source_kind=?', (crawl, target, kind)):
                    reverse = any(url_key(urljoin(target, item.get('href',''))) == source[0] for item in detail['alternates'])
                    if not reverse:
                        store.issue(crawl, source[0], 'hreflang.return_link_missing', 'warning', {'target': target})
                    store.db.execute('DELETE FROM issues WHERE crawl_id=? AND url=? AND rule_id="hreflang.external_target_unmeasured"', (crawl, source[0]))
                    store.commit()
            if kind == 'image' and response.status == 200:
                detail.update(binary_worker('image', response.body))
                if len(response.body) > image_max_bytes:
                    store.issue(crawl, target, 'images.size_threshold', 'warning', {'bytes': len(response.body), 'configured_max': image_max_bytes})
            if response.status >= 400:
                store.issue(crawl, target, 'links.broken_external' if kind == 'external' else 'images.response', 'warning', detail)
            store.observation(crawl, target, kind, 'measured', detail)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            store.observation(crawl, target, kind, 'unmeasured', {'reason': str(error)})


if __name__ == '__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    print(json.dumps(inspect_binary(sys.argv[1], sys.stdin.buffer.read(10000001))))
