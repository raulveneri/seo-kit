#!/usr/bin/env python3
"""Query and compare versioned crawl databases without a UI."""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlencode
from xml.etree import ElementTree

from crawl_store import CrawlStore, url_key
from audit_io import output_stream, database_lock
from crawl_privacy import sanitize, sharing_rows, redact_text
from audit import Document


def crawl_id(store, selected):
    row = store.db.execute('SELECT id FROM crawls WHERE id=?' if selected else 'SELECT id FROM crawls ORDER BY id DESC LIMIT 1', (selected,) if selected else ()).fetchone()
    if not row:
        raise ValueError('crawl not found')
    return row[0]


def require_html(store, selected, source='rendered'):
    column = 'COALESCE(rendered_html,raw_html)' if source == 'rendered' else 'raw_html'
    missing = store.db.execute(f'SELECT COUNT(*) FROM pages WHERE crawl_id=? AND raw_sha256 IS NOT NULL AND {column} IS NULL', (selected,)).fetchone()[0]
    if missing:
        raise ValueError('HTML was not retained for some pages. Start a new crawl with --store-html raw or both for this operation')


def rows(store, table, selected, filters, limit=None, offset=0):
    columns = {
        'pages': ('url', 'status', 'content_type', 'depth'),
        'observations': ('url', 'kind', 'status'),
        'issues': ('url', 'rule_id', 'severity', 'state', 'source'),
        'links': ('source_url', 'target_url', 'source_kind'),
        'external_data': ('url', 'source', 'property', 'period'),
        'resources': ('url', 'source_url', 'kind', 'status', 'content_type'),
    }
    clauses, values = ['crawl_id=?'], [selected]
    for key, value in filters.items():
        if value is None:
            continue
        if key == 'status' and table == 'issues':
            key = 'state'
        if key == 'type':
            key = {'pages': 'content_type', 'issues': 'rule_id', 'links': 'source_kind', 'resources': 'kind', 'external_data': 'source', 'observations': 'kind'}[table]
        if key == 'directory':
            field = 'source_url' if table == 'links' else 'url'
            clauses.append(f'{field} LIKE ?')
            values.append(value.rstrip('/') + '/%')
        elif key == 'url':
            field = 'source_url' if table == 'links' else 'url'
            clauses.append(f'{field} LIKE ?')
            values.append('%' + value + '%')
        elif key in columns[table]:
            clauses.append(f'{key}=?')
            values.append(value)
        else:
            raise ValueError(f'filter {key} is not applicable to {table}')
    projected = ','.join(row[1] for row in store.db.execute(f'PRAGMA table_info({table})') if row[1] not in ('raw_html','rendered_html'))
    query = f"SELECT {projected} FROM {table} WHERE {' AND '.join(clauses)} ORDER BY 2,3"
    if limit is not None:
        query += ' LIMIT ? OFFSET ?'
        values.extend((limit, offset))
    elif offset:
        query += ' LIMIT -1 OFFSET ?'
        values.append(offset)
    for row in store.db.execute(query, values):
        item = dict(row)
        for key in ('raw_html', 'rendered_html'):
            item.pop(key, None)
        yield item


def comparison_pages(store, selected, mapping=None, side='first'):
    table = 'migration_urls_first' if side == 'first' else 'migration_urls_second'
    store.db.execute(f'CREATE TEMP TABLE IF NOT EXISTS {table} (old_url TEXT PRIMARY KEY,new_url TEXT NOT NULL)')
    store.db.execute(f'DELETE FROM {table}')
    if mapping:
        store.db.executemany(f'INSERT INTO {table} VALUES (?,?)', mapping.items())
    collision = store.db.execute(f'SELECT COALESCE(m.new_url,p.url) AS comparison_url FROM pages p LEFT JOIN {table} m ON m.old_url=p.url WHERE p.crawl_id=? GROUP BY comparison_url HAVING COUNT(*)>1 LIMIT 1', (selected,)).fetchone()
    if collision:
        raise ValueError('URL map collision: ' + collision[0])
    fields = 'p.url,p.final_url,p.status,p.content_type,p.headers_json,p.redirects_json,p.raw_sha256,p.rendered_sha256,p.metadata_json,p.depth,p.error'
    yield from store.db.execute(f'SELECT {fields},COALESCE(m.new_url,p.url) AS comparison_url FROM pages p LEFT JOIN {table} m ON m.old_url=p.url WHERE p.crawl_id=? ORDER BY comparison_url', (selected,))


def compare_changes(first, first_id, second, second_id, mapping=None):
    before, after = iter(comparison_pages(first,first_id,mapping)), iter(comparison_pages(second,second_id,side='second'))
    old, new = next(before,None), next(after,None)
    while old is not None or new is not None:
        if old is None or new is not None and new['comparison_url'] < old['comparison_url']:
            yield {'url': new['comparison_url'], 'change': 'added'}
            new = next(after,None)
            continue
        if new is None or old['comparison_url'] < new['comparison_url']:
            yield {'url': old['comparison_url'], 'change': 'removed'}
            old = next(before,None)
            continue
        url = new['comparison_url']
        fields = {}
        for field in ('status', 'final_url', 'raw_sha256', 'rendered_sha256', 'metadata_json', 'depth', 'redirects_json'):
            if old[field] != new[field]:
                fields[field] = {'before': old[field], 'after': new[field]}
        old_links = {mapping.get(r[0],r[0]) if mapping else r[0] for r in first.db.execute('SELECT target_url FROM links WHERE crawl_id=? AND source_url=?',(first_id,old['url']))}
        new_links = {r[0] for r in second.db.execute('SELECT target_url FROM links WHERE crawl_id=? AND source_url=?',(second_id,new['url']))}
        if old_links != new_links:
            fields['links'] = {'added':sorted(new_links-old_links), 'removed':sorted(old_links-new_links)}
        old_issues = {r[0] for r in first.db.execute('SELECT rule_id FROM issues WHERE crawl_id=? AND url=? AND state="open"',(first_id,old['url']))}
        new_issues = {r[0] for r in second.db.execute('SELECT rule_id FROM issues WHERE crawl_id=? AND url=? AND state="open"',(second_id,new['url']))}
        if old_issues != new_issues:
            fields['issues'] = {'new':sorted(new_issues-old_issues), 'resolved':sorted(old_issues-new_issues)}
        def observations(store, selected, source):
            return {r[0]:json.loads(r[1]) for r in store.db.execute('SELECT kind,data_json FROM observations WHERE crawl_id=? AND url=? AND kind="architecture"',(selected,source))}
        old_structure, new_structure = observations(first,first_id,old['url']), observations(second,second_id,new['url'])
        if old_structure != new_structure:
            fields['structure'] = {'before':old_structure,'after':new_structure}
        if old['url'] != url:
            fields['url'] = {'before':old['url'],'after':url}
        if fields:
            yield {'url':url,'mapped_from':old['url'] if old['url'] != url else None,'change':'modified','fields':fields}
        old, new = next(before,None), next(after,None)


def compare(first, first_id, second, second_id, mapping=None, streaming=False):
    changes = compare_changes(first,first_id,second,second_id,mapping)
    if not streaming:
        changes = list(changes)
    before_scope = first.db.execute('SELECT status,crawl_limit,config_json,start_url,origin FROM crawls WHERE id=?', (first_id,)).fetchone()
    after_scope = second.db.execute('SELECT status,crawl_limit,config_json,start_url,origin FROM crawls WHERE id=?', (second_id,)).fetchone()
    differences = []
    if before_scope['status'] != 'complete' or after_scope['status'] != 'complete':
        differences.append('incomplete_crawl')
    if before_scope['crawl_limit'] != after_scope['crawl_limit']:
        differences.append('crawl_limit')
    if json.loads(before_scope['config_json']) != json.loads(after_scope['config_json']):
        differences.append('crawl_configuration')
    mapped_start = (mapping or {}).get(before_scope['start_url'], before_scope['start_url'])
    if url_key(mapped_start) != url_key(after_scope['start_url']):
        differences.append('start_url')
    if before_scope['origin'] != after_scope['origin'] and not (mapping and all(row[0] in mapping for row in first.db.execute('SELECT url FROM pages WHERE crawl_id=?',(first_id,)))):
        differences.append('incomplete_origin_mapping')
    comparable = not differences
    return {'schema_version': 1, 'before_crawl_id': first_id, 'after_crawl_id': second_id,
            'scope_comparable': comparable,
            'scope_differences': differences,
            'scope_note': 'Additions and removals may reflect different origins, crawl limits or incomplete coverage' if not comparable else None,
            'changes': changes}


def output_items(items, format_name, path=None):
    with output_stream(path) as stream:
        columns = None
        if isinstance(items, dict) and format_name == 'json':
            if 'changes' in items:
                header = {key:value for key,value in items.items() if key != 'changes'}
                stream.write(json.dumps(sanitize(header),ensure_ascii=False)[:-1] + ', "changes": [')
                for index,item in enumerate(items['changes']):
                    if index:
                        stream.write(',')
                    stream.write(json.dumps(sanitize(item),ensure_ascii=False))
                stream.write(']}\n')
            else:
                json.dump(sanitize(items), stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            return
        if isinstance(items, dict):
            items = items['changes']
            columns = ['url', 'change', 'mapped_from', 'fields']
        iterator = iter(items)
        if format_name == 'json':
            stream.write('[\n')
            for index, item in enumerate(iterator):
                if index:
                    stream.write(',\n')
                stream.write(json.dumps(sanitize(item), ensure_ascii=False))
            stream.write('\n]\n')
        else:
            first = next(iterator, None)
            if first is None:
                return
            columns = columns or list(first)
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for item in _prepend(first, iterator):
                writer.writerow({key: csv_value(sanitize(value)) for key, value in item.items()})


def csv_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


def _prepend(first, iterator):
    yield first
    yield from iterator


def export_sitemap(store, selected):
    entries = []
    size = 0
    for entry in sitemap_entries(store, selected):
        size += len(entry.encode('utf-8'))
        if len(entries) >= 50000 or size > 49000000:
            raise ValueError('sitemap exceeds a single file. Use --output-directory and --public-base')
        entries.append(entry)
    return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + '\n'.join(entries) + '\n</urlset>\n'


def export_graph(store, selected):
    for row in store.db.execute('SELECT source_url,target_url,anchor_text,source_kind FROM links WHERE crawl_id=? AND source_kind="internal" ORDER BY source_url,target_url', (selected,)):
        yield dict(row)


class ElementExtractor(HTMLParser):
    def __init__(self, tag, attribute, where_attribute, where_value, limit):
        super().__init__(convert_charrefs=True)
        self.tag, self.attribute = tag, attribute
        self.where_attribute, self.where_value = where_attribute, where_value
        self.limit = limit
        self.values = []
        self.capture = None

    def handle_starttag(self, tag, attrs):
        if tag != self.tag or len(self.values) >= self.limit:
            return
        values = dict(attrs)
        if self.where_attribute and values.get(self.where_attribute) != self.where_value:
            return
        if self.attribute:
            if values.get(self.attribute) is not None:
                self.values.append(values[self.attribute][:10000])
        else:
            self.capture = []

    def handle_data(self, data):
        if self.capture is not None:
            self.capture.append(data)

    def handle_endtag(self, tag):
        if tag == self.tag and self.capture is not None:
            self.values.append(' '.join(''.join(self.capture).split())[:10000])
            self.capture = None


def extract(store, selected, tag, attribute=None, where_attribute=None, where_value=None, source='rendered', max_results=10000):
    require_html(store, selected, source)
    yielded = 0
    column = 'COALESCE(rendered_html,raw_html)' if source == 'rendered' else 'raw_html'
    for row in store.db.execute(f'SELECT url,{column} AS html FROM pages WHERE crawl_id=? AND {column} IS NOT NULL ORDER BY url', (selected,)):
        parser = ElementExtractor(tag, attribute, where_attribute, where_value, max_results - yielded)
        parser.feed(row['html'].decode('utf-8', 'replace'))
        for value in parser.values:
            yield {'url': row['url'], 'value': value, 'source': source}
            yielded += 1
        if yielded >= max_results:
            break


def spellcheck(store, selected, dictionary, language, max_results=10000):
    require_html(store, selected, 'rendered')
    path = Path(dictionary)
    if path.stat().st_size > 10_000_000:
        raise ValueError('dictionary exceeds 10 MB')
    data = path.read_bytes()
    known = {line.strip().casefold() for line in data.decode('utf-8-sig').splitlines() if line.strip() and not line.lstrip().startswith('#')}
    if not known or len(known) > 500000:
        raise ValueError('dictionary must contain 1..500000 words, one per line')
    digest = hashlib.sha256(data).hexdigest()
    yielded = 0
    for row in store.db.execute('SELECT url,metadata_json,COALESCE(rendered_html,raw_html) AS html FROM pages WHERE crawl_id=? AND COALESCE(rendered_html,raw_html) IS NOT NULL ORDER BY url', (selected,)):
        actual_language = json.loads(row['metadata_json'] or '{}').get('language', '').lower()
        common = {'url': row['url'], 'language': actual_language, 'dictionary_sha256': digest, 'grammar_status': 'unmeasured'}
        if actual_language != language.lower() and not actual_language.startswith(language.lower() + '-'):
            yield {**common, 'word': None, 'count': None, 'state': 'unmeasured', 'detail': 'page language does not match the declared dictionary language'}
            yielded += 1
        else:
            doc = Document()
            doc.feed(row['html'].decode('utf-8', 'replace'))
            words = Counter(word.casefold() for word in re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)*", ' '.join(doc.text), re.UNICODE))
            unknown = [(word, count) for word, count in words.items() if len(word) > 1 and word not in known]
            if not unknown:
                yield {**common, 'word': None, 'count': 0, 'state': 'no_candidates', 'detail': 'dictionary comparison only, human review required'}
                yielded += 1
            for word, count in sorted(unknown, key=lambda item: (-item[1], item[0])):
                yield {**common, 'word': word, 'count': count, 'state': 'candidate', 'detail': 'absent from supplied dictionary, human review required'}
                yielded += 1
                if yielded >= max_results:
                    return
        if yielded >= max_results:
            return


def main(argv=None):
    parser = argparse.ArgumentParser(description='Query and compare persistent SEO crawls')
    sub = parser.add_subparsers(dest='command', required=True)
    query = sub.add_parser('query')
    query.add_argument('--database', required=True)
    query.add_argument('--crawl-id', type=int)
    query.add_argument('--table', choices=('pages', 'issues', 'links', 'resources', 'external_data', 'observations'), default='issues')
    for name in ('url', 'directory', 'type', 'status', 'rule_id', 'severity', 'state', 'source'):
        query.add_argument('--' + name.replace('_', '-'))
    query.add_argument('--limit', type=int)
    query.add_argument('--offset', type=int, default=0)
    diff = sub.add_parser('compare')
    diff.add_argument('--before', required=True)
    diff.add_argument('--after', required=True)
    diff.add_argument('--before-id', type=int)
    diff.add_argument('--after-id', type=int)
    diff.add_argument('--url-map', help='JSON object mapping old full URLs to new full URLs')
    sitemap = sub.add_parser('sitemap')
    sitemap.add_argument('--database', required=True)
    sitemap.add_argument('--crawl-id', type=int)
    sitemap.add_argument('--output')
    sitemap.add_argument('--output-directory', help='write bounded sitemap parts and an index outside this repository')
    sitemap.add_argument('--public-base', help='public HTTPS URL prefix for the generated sitemap index')
    sitemap.add_argument('--max-urls', type=int, default=50000)
    graph = sub.add_parser('graph')
    graph.add_argument('--database', required=True)
    graph.add_argument('--crawl-id', type=int)
    graph.add_argument('--format', choices=('json', 'csv'), default='csv')
    graph.add_argument('--output')
    extraction = sub.add_parser('extract')
    extraction.add_argument('--database', required=True)
    extraction.add_argument('--crawl-id', type=int)
    extraction.add_argument('--tag', help='exact HTML tag name')
    extraction.add_argument('--fields', help='external JSON list of named CSS/XPath fields, mutually exclusive with --tag')
    extraction.add_argument('--attribute', help='attribute to collect, omit for element text')
    extraction.add_argument('--where-attribute', help='exact attribute name used as a filter')
    extraction.add_argument('--where-value', help='exact filter value')
    extraction.add_argument('--source', choices=('raw', 'rendered'), default='rendered')
    extraction.add_argument('--max-results', type=int, default=10000)
    extraction.add_argument('--format', choices=('json', 'csv'), default='csv')
    extraction.add_argument('--output')
    spelling = sub.add_parser('spellcheck')
    spelling.add_argument('--database', required=True)
    spelling.add_argument('--crawl-id', type=int)
    spelling.add_argument('--dictionary', required=True, help='host-provided UTF-8 word list, one word per line')
    spelling.add_argument('--language', required=True, help='language tag matching the supplied dictionary')
    spelling.add_argument('--max-results', type=int, default=10000)
    spelling.add_argument('--format', choices=('json', 'csv'), default='json')
    spelling.add_argument('--output')
    grammar = sub.add_parser('grammar')
    grammar.add_argument('--database', required=True)
    grammar.add_argument('--crawl-id', type=int)
    grammar.add_argument('--endpoint', required=True, help='authorized public HTTPS LanguageTool /v2/check endpoint, sends page text')
    grammar.add_argument('--language', required=True)
    grammar.add_argument('--max-pages', type=int, default=10)
    grammar.add_argument('--format', choices=('json','csv'), default='json')
    grammar.add_argument('--output')
    for name in ('share', 'crawls', 'lock', 'unlock', 'retention'):
        command = sub.add_parser(name)
        command.add_argument('--database', required=True)
        command.add_argument('--format', choices=('json', 'csv'), default='json')
        command.add_argument('--output')
        if name in ('share', 'lock', 'unlock'):
            command.add_argument('--crawl-id', type=int, required=name != 'share')
        if name == 'retention':
            command.add_argument('--days', type=int, required=True)
            command.add_argument('--apply', action='store_true', help='delete eligible crawl rows, without this flag only preview')
    for command in (query, diff):
        command.add_argument('--format', choices=('json', 'csv'), default='json')
        command.add_argument('--output')
    args = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[2]
    for label in ('database', 'before', 'after', 'url_map', 'dictionary', 'fields', 'output', 'output_directory'):
        value = getattr(args, label, None)
        if value and Path(value).resolve().is_relative_to(repository):
            parser.error(f'--{label.replace("_", "-")} must be outside the seo-kit repository')
    if args.output and any(Path(args.output).resolve() == Path(value).resolve() for value in
                           (getattr(args, 'database', None), getattr(args, 'before', None), getattr(args, 'after', None), getattr(args, 'url_map', None), getattr(args, 'dictionary', None), getattr(args, 'fields', None)) if value):
        parser.error('--output must differ from every input path')
    try:
        if args.command in ('share', 'crawls', 'lock', 'unlock', 'retention'):
            writable = args.command in ('lock', 'unlock') or (args.command == 'retention' and args.apply)
            if not Path(args.database).is_file():
                raise ValueError('crawl database does not exist')
            # Serialize mutations with the live auditor. Preview/share never mutate or migrate.
            def manage():
                store = CrawlStore(args.database, read_only=not writable)
                try:
                    if args.command == 'share':
                        result = sharing_rows(store, crawl_id(store, args.crawl_id))
                    elif args.command == 'crawls':
                        result = (dict(row) for row in store.db.execute("SELECT id,origin,started_at,finished_at,status,config_json,COALESCE((SELECT value FROM meta WHERE key='protected:' || crawls.id),'0') AS protected FROM crawls ORDER BY id"))
                    elif args.command in ('lock', 'unlock'):
                        store.protect(args.crawl_id, args.command == 'lock')
                        result = [{'crawl_id': args.crawl_id, 'protected': args.command == 'lock'}]
                    else:
                        result = [store.retention(args.days, apply=args.apply)]
                    output_items(result, args.format, args.output)
                finally:
                    store.close()
            if writable:
                with database_lock(Path(args.database).resolve()):
                    manage()
            else:
                manage()
        elif args.command == 'query':
            store = CrawlStore(args.database, read_only=True)
            try:
                filters = {key: getattr(args, key) for key in ('url', 'directory', 'type', 'status', 'rule_id', 'severity', 'state', 'source')}
                if args.offset < 0 or args.limit is not None and args.limit < 1:
                    raise ValueError('query requires a positive limit and nonnegative offset')
                output_items(rows(store, args.table, crawl_id(store, args.crawl_id), filters, args.limit, args.offset), args.format, args.output)
            finally:
                store.close()
        elif args.command in ('sitemap', 'graph', 'extract', 'spellcheck', 'grammar'):
            store = CrawlStore(args.database, read_only=True)
            try:
                selected = crawl_id(store, args.crawl_id)
                if args.command == 'sitemap':
                    if args.output_directory:
                        if args.output or not args.public_base or not args.public_base.startswith('https://') or not 1 <= args.max_urls <= 50000:
                            raise ValueError('sitemap parts require --public-base, --max-urls 1..50000 and no --output')
                        sitemap_parts(store, selected, args.output_directory, args.public_base, args.max_urls)
                        return
                    output = export_sitemap(store, selected)
                    with output_stream(args.output) as stream:
                        stream.write(output)
                elif args.command == 'graph':
                    output_items(export_graph(store, selected), args.format, args.output)
                elif args.command == 'grammar':
                    if not 1 <= args.max_pages <= 1000:
                        raise ValueError('--max-pages must be 1..1000')
                    output_items(grammar_check(store, selected, args.endpoint, args.language, args.max_pages), args.format, args.output)
                elif args.command == 'spellcheck':
                    if not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', args.language) or not 1 <= args.max_results <= 100000:
                        raise ValueError('spellcheck requires a language tag and bounded result limit')
                    output_items(spellcheck(store, selected, args.dictionary, args.language, args.max_results), args.format, args.output)
                else:
                    if args.fields:
                        if args.tag or Path(args.fields).stat().st_size > 100000:
                            raise ValueError('--fields is exclusive with --tag and limited to 100 KB')
                        fields = json.loads(Path(args.fields).read_text())
                        output_items(extract_fields(store, selected, fields, args.source, args.max_results), args.format, args.output)
                        return
                    if not args.tag or not re.fullmatch(r'[a-z][a-z0-9-]*', args.tag) or any(value and not re.fullmatch(r'[a-zA-Z_:][a-zA-Z0-9_:.-]*', value) for value in (args.attribute, args.where_attribute)):
                        raise ValueError('tag or attribute name is invalid')
                    if bool(args.where_attribute) != (args.where_value is not None) or not 1 <= args.max_results <= 100000:
                        raise ValueError('extraction requires a bounded result limit and complete where pair')
                    output_items(extract(store, selected, args.tag, args.attribute, args.where_attribute, args.where_value, args.source, args.max_results), args.format, args.output)
            finally:
                store.close()
        else:
            first = CrawlStore(args.before, read_only=True)
            try:
                second = CrawlStore(args.after, read_only=True)
                try:
                    mapping = json.loads(Path(args.url_map).read_text(encoding='utf-8')) if args.url_map else None
                    if mapping is not None and (not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) or urlsplit(k).scheme != 'https' or urlsplit(v).scheme != 'https' for k, v in mapping.items())):
                        raise ValueError('URL map must contain HTTPS URL string pairs')
                    result = compare(first, crawl_id(first, args.before_id), second, crawl_id(second, args.after_id), mapping, streaming=True)
                    output_items(result, args.format, args.output)
                finally:
                    second.close()
            finally:
                first.close()
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        parser.error(redact_text(str(error)))




def extract_fields(store, selected, fields, source='rendered', max_results=10000):
    require_html(store, selected, source)
    from advanced_audit import html_tree
    from lxml import etree
    if not isinstance(fields, list) or not 1 <= len(fields) <= 50 or not 1 <= max_results <= 100000:
        raise ValueError('requires 1..50 fields and max-results 1..100000')
    names = set()
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get('name'), str) or not field['name'] or field['name'] in names or bool(field.get('css')) == bool(field.get('xpath')):
            raise ValueError('fields require unique names and exactly one CSS or XPath selector')
        names.add(field['name'])
        selector = field.get('css', field.get('xpath'))
        if not isinstance(selector, str) or len(selector) > 1000:
            raise ValueError('selector must be a string of at most 1000 characters')
        try:
            if field.get('xpath'):
                etree.XPath(selector, regexp=False)
            else:
                html_tree('<html/>').cssselect(selector)
        except (etree.XPathError, ValueError, SyntaxError) as error:
            raise ValueError('invalid extraction selector') from error
    column = 'COALESCE(rendered_html,raw_html)' if source == 'rendered' else 'raw_html'
    count = 0
    for row in store.db.execute(f'SELECT url,{column} AS html FROM pages WHERE crawl_id=? AND {column} IS NOT NULL ORDER BY url', (selected,)):
        tree = html_tree(row['html'])
        for field in fields:
            try:
                values = tree.cssselect(field['css']) if field.get('css') else tree.xpath(field['xpath'], smart_strings=False)
            except (etree.XPathError, ValueError) as error:
                raise ValueError('selector evaluation failed') from error
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if hasattr(value, 'text_content'):
                    value = value.get(field['attribute'], '') if field.get('attribute') else ' '.join(value.text_content().split())
                yield {'url': row['url'], 'field': field['name'], 'value': str(value)[:10000], 'source': source}
                count += 1
                if count >= max_results:
                    return


def sitemap_entries(store, selected):
    for row in store.db.execute('SELECT url,metadata_json,headers_json FROM pages WHERE crawl_id=? AND status=200 AND content_type LIKE "%text/html%" ORDER BY url', (selected,)):
        metadata = json.loads(row['metadata_json'] or '{}')
        headers = json.loads(row['headers_json'] or '{}')
        if 'noindex' in metadata.get('effective_directives', []) or any('noindex' in item.lower() or item.lower() == 'none' for item in metadata.get('meta_robots', [])) or 'noindex' in headers.get('x-robots-tag', '').lower():
            continue
        canonicals = metadata.get('canonicals', []) + metadata.get('http_canonicals', [])
        if canonicals and {url_key(urljoin(row['url'], value)) for value in canonicals} != {url_key(row['url'])}:
            continue
        node = ElementTree.Element('url')
        ElementTree.SubElement(node, 'loc').text = row['url']
        for image in metadata.get('images', [])[:1000]:
            if image.get('src'):
                target = urljoin(row['url'], image['src'])
                if urlsplit(target).scheme not in ('http','https'):
                    continue
                element = ElementTree.SubElement(node, 'image:image')
                ElementTree.SubElement(element, 'image:loc').text = target
        yield ElementTree.tostring(node, encoding='unicode')


def sitemap_parts(store, selected, directory, public_base, max_urls=50000):
    import uuid
    from xml.sax.saxutils import escape
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    names, pending, size = [], [], 0
    generation = uuid.uuid4().hex[:12]
    def write_part():
        name = f'sitemap-{selected}-{generation}-{len(names) + 1:05d}.xml'
        with output_stream(destination / name) as stream:
            stream.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')
            stream.write('\n'.join(pending))
            stream.write('\n</urlset>\n')
        names.append(name)
    for entry in sitemap_entries(store, selected):
        entry_size = len(entry.encode('utf-8')) + 1
        if entry_size > 49000000:
            raise ValueError('one sitemap entry exceeds the file size limit')
        if pending and (len(pending) >= max_urls or size + entry_size > 49000000):
            write_part()
            pending, size = [], 0
        pending.append(entry)
        size += entry_size
    if pending:
        write_part()
    with output_stream(destination / 'sitemap-index.xml') as stream:
        stream.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for name in names:
            stream.write('<sitemap><loc>' + escape(public_base.rstrip('/') + '/' + name) + '</loc></sitemap>\n')
        stream.write('</sitemapindex>\n')
    return names


def grammar_check(store, selected, endpoint, language, max_pages=10, client=None):
    require_html(store, selected, 'rendered')
    from live_http import SafeClient, checked_url
    from advanced_audit import html_tree, main_text
    endpoint = checked_url(endpoint)
    if urlsplit(endpoint).query:
        raise ValueError('grammar endpoint must not contain query parameters or credentials')
    client = client or SafeClient(max_requests=max_pages, max_bytes=2000000, delay=0.5)
    for row in store.db.execute('SELECT url,metadata_json,COALESCE(rendered_html,raw_html) AS html FROM pages WHERE crawl_id=? AND COALESCE(rendered_html,raw_html) IS NOT NULL ORDER BY depth,url LIMIT ?', (selected, max_pages)):
        common = {'url': row['url'], 'source': endpoint, 'language': language, 'review_required': True}
        actual = json.loads(row['metadata_json'] or '{}').get('language','')
        if actual.lower().split('-')[0] != language.lower().split('-')[0]:
            yield common | {'status': 'unmeasured', 'detail': 'page language mismatch'}
            continue
        text = main_text(html_tree(row['html']))[:20000]
        try:
            response = client.fetch(endpoint, method='POST', body=urlencode({'text': text, 'language': language}).encode(), headers={'Content-Type':'application/x-www-form-urlencoded'}, allow_redirects=False)
            if response.status != 200:
                raise ValueError(f'grammar API returned HTTP {response.status}')
            data = json.loads(response.body)
            if not isinstance(data, dict) or not isinstance(data.get('matches'), list):
                raise ValueError('grammar API response missing matches')
            yield common | {'status': 'measured', 'matches': data['matches'], 'software': data.get('software'), 'text_truncated': len(text) == 20000}
        except (OSError, ValueError) as error:
            yield common | {'status': 'unmeasured', 'detail': str(error)}


if __name__ == '__main__':
    main()
