"""Versioned, objective crawler observations. SEO judgments remain reviewed evidence."""

import json
import hashlib
import re
from collections import Counter, defaultdict
from urllib.parse import urljoin, urlsplit

from audit import validate_json_ld
from crawl_store import url_key


def content_fingerprint(text):
    words = re.findall(r'\w+', text.casefold())
    if len(words) < 80:
        return None, len(words)
    total_words = len(words)
    words = words[:5000]
    shingles = Counter(' '.join(words[index:index + 5]) for index in range(len(words) - 4))
    weights = [0] * 64
    for shingle, count in shingles.items():
        bits = int.from_bytes(hashlib.sha256(shingle.encode()).digest()[:8], 'big')
        for bit in range(64):
            weights[bit] += count if bits & (1 << bit) else -count
    fingerprint = sum(1 << bit for bit, weight in enumerate(weights) if weight >= 0)
    return f'{fingerprint:016x}', total_words


def inspect_page(store, crawl_id, url, response, doc):
    if response.redirects and len(response.redirects) > 1:
        store.issue(crawl_id, url, 'http.redirect_chain', 'warning', {'redirects': response.redirects})
    if response.headers.get('x-robots-tag'):
        store.issue(crawl_id, url, 'indexability.x_robots_directive', 'info', {'value': response.headers['x-robots-tag']})
    if doc.metas('robots'):
        store.issue(crawl_id, url, 'indexability.meta_robots_directive', 'info', {'values': doc.metas('robots')})
    if not doc.metas('description'):
        store.issue(crawl_id, url, 'metadata.description_missing', 'warning', {'description': None})
    if not any(level == 1 and value for level, value in doc.headings):
        store.issue(crawl_id, url, 'headings.heading_one_missing', 'warning', {'headings': doc.headings})
    missing_alt = [image.get('src', '') for image in doc.images if 'alt' not in image]
    if missing_alt:
        store.issue(crawl_id, url, 'images.alt_missing', 'warning', {'sources': missing_alt})
    empty_links = [link.get('href', '') for link in doc.links if not (link.get('text') or link.get('aria'))]
    if empty_links:
        store.issue(crawl_id, url, 'links.anchor_missing', 'warning', {'targets': empty_links})
    unlabeled = []
    for control in doc.form_controls:
        if control['tag'] == 'input' and control['type'].lower() in {'hidden', 'submit', 'button', 'reset', 'image'}:
            continue
        labelledby = control['aria_labelledby'].split()
        if not (control['nested_label'] or control['aria_label'].strip() or control['title'].strip() or
                (control['id'] and control['id'] in doc.labels_for) or
                (labelledby and all(reference in doc.ids for reference in labelledby))):
            unlabeled.append({'tag': control['tag'], 'id': control['id']})
    if unlabeled:
        store.issue(crawl_id, url, 'accessibility.form_control_label_missing', 'warning', {'controls': unlabeled})
    invalid = []
    for payload in doc.json_ld:
        valid, detail = validate_json_ld(payload)
        if not valid:
            invalid.append(detail)
    if invalid:
        store.issue(crawl_id, url, 'structured_data.invalid_json_ld', 'warning', {'errors': invalid})
    for element in doc.link_elements:
        rel = element.get('rel', '').lower().split()
        if 'amphtml' in rel:
            store.issue(crawl_id, url, 'amp.link_declared', 'info', {'href': element.get('href')})
        if 'next' in rel or 'prev' in rel:
            store.issue(crawl_id, url, 'pagination.link_declared', 'info', {'href': element.get('href'), 'rel': rel})


def inspect_site(store, crawl_id):
    pages = list(store.db.execute('SELECT url,raw_sha256,metadata_json FROM pages WHERE crawl_id=? AND status=200 AND raw_sha256 IS NOT NULL', (crawl_id,)))
    titles, hashes = defaultdict(list), defaultdict(list)
    raw_hash_by_url = {}
    metadata = {}
    for row in pages:
        data = json.loads(row['metadata_json'] or '{}')
        metadata[row['url']] = data
        if data.get('title'):
            titles[data['title'].casefold()].append(row['url'])
        if row['raw_sha256']:
            hashes[row['raw_sha256']].append(row['url'])
            raw_hash_by_url[row['url']] = row['raw_sha256']
    for group in titles.values():
        if len(group) > 1:
            for url in group:
                store.issue(crawl_id, url, 'metadata.duplicate_title', 'warning', {'urls': group})
    for group in hashes.values():
        if len(group) > 1:
            for url in group:
                store.issue(crawl_id, url, 'content.exact_duplicate', 'warning', {'urls': group})
    buckets = defaultdict(list)
    for url, data in metadata.items():
        fingerprint = data.get('content_fingerprint')
        if not fingerprint:
            continue
        for band in range(4):
            buckets[(band, fingerprint[band * 4:band * 4 + 4])].append(url)
    candidates = defaultdict(list)
    seen_pairs = set()
    comparisons = 0
    for group in buckets.values():
        for index, first in enumerate(group):
            for second in group[index + 1:]:
                pair = tuple(sorted((first, second)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                comparisons += 1
                if comparisons > 100000:
                    store.issue(crawl_id, 'site', 'content.similarity_limit', 'info', {'compared_pairs': 100000, 'reason': 'candidate comparison budget reached'})
                    break
                distance = (int(metadata[first]['content_fingerprint'], 16) ^ int(metadata[second]['content_fingerprint'], 16)).bit_count()
                if distance <= 3 and metadata[first].get('language') == metadata[second].get('language') and raw_hash_by_url.get(first) != raw_hash_by_url.get(second):
                    candidates[first].append({'url': second, 'hamming_distance': distance})
                    candidates[second].append({'url': first, 'hamming_distance': distance})
            if comparisons > 100000:
                break
        if comparisons > 100000:
            break
    for url, matches in candidates.items():
        store.issue(crawl_id, url, 'content.near_duplicate_candidate', 'info', {'candidates': matches[:20], 'method': '64-bit SimHash, five-word shingles, review required'})
    for url, data in metadata.items():
        for link in data.get('link_elements', []):
            if 'amphtml' not in link.get('rel', '').lower().split():
                continue
            target = url_key(urljoin(url, link.get('href', '')))
            target_data = metadata.get(target)
            if target_data is None:
                store.issue(crawl_id, url, 'amp.target_unmeasured', 'info', {'target': target})
            elif 'amp' not in target_data.get('html_attributes', {}) and '⚡' not in target_data.get('html_attributes', {}):
                store.issue(crawl_id, target, 'amp.markup_missing', 'warning', {'source': url})
            elif url_key(url) not in [url_key(urljoin(target, canonical)) for canonical in target_data.get('canonicals', [])]:
                store.issue(crawl_id, target, 'amp.canonical_return_missing', 'warning', {'source': url})
        for link in data.get('link_elements', []):
            if 'alternate' not in link.get('rel', '').lower().split() or not link.get('hreflang'):
                continue
            target = url_key(urljoin(url, link.get('href', '')))
            if urlsplit(target).netloc != urlsplit(url).netloc:
                store.issue(crawl_id, url, 'hreflang.external_target_unmeasured', 'info', {'target': target, 'reason': 'outside crawl origin'})
                continue
            reverse = metadata.get(target)
            if reverse is None:
                store.issue(crawl_id, url, 'hreflang.target_unmeasured', 'info', {'target': target})
                continue
            if not any('alternate' in item.get('rel', '').lower().split() and url_key(urljoin(target, item.get('href', ''))) == url_key(url) for item in reverse.get('link_elements', [])):
                store.issue(crawl_id, url, 'hreflang.return_link_missing', 'warning', {'target': target})
