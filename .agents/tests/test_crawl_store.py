"""Persistent crawl regression tests using an in-memory HTTPS fixture."""

import argparse
import json
import csv
import sys
import subprocess
import sqlite3
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from crawl_query import compare, rows, export_sitemap, export_graph, extract, output_items, spellcheck
from crawl_store import CrawlStore, url_key
from live_audit import run_live
from live_http import Response
from audit_io import database_lock


ORIGIN = 'https://example.org'


class FixtureClient:
    max_bytes = 2_000_000

    def __init__(self, pages, stop_after=None):
        self.pages = pages
        self.requests = 0
        self.stop_after = stop_after

    def fetch(self, url, **kwargs):
        if self.stop_after is not None and self.requests >= self.stop_after:
            raise ValueError('request budget exhausted')
        self.requests += 1
        if url.endswith('/robots.txt'):
            body = f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml'.encode()
            return Response(url, 200, {'content-type': 'text/plain'}, body, [])
        if url.endswith('/sitemap.xml'):
            body = f'<urlset><url><loc>{ORIGIN}/</loc></url><url><loc>{ORIGIN}/about/?b=2&amp;a=1</loc></url></urlset>'.encode()
            return Response(url, 200, {'content-type': 'application/xml'}, body, [])
        status, html = self.pages.get(url, (404, ''))
        return Response(url, status, {'content-type': 'application/pdf' if url.endswith('.pdf') else 'text/html'}, html.encode(), [])


def options(database, **overrides):
    values = dict(url=ORIGIN + '/', crawl_limit='100', database=database, resume=False,
                  max_requests=50, max_seconds=300, max_disk_bytes=10_000_000,
                  delay=0, render='never', crux=False, gsc_property=None,
                  max_inspections=10, evidence=None, baseline=None,
                  backlinks_export=None, backlinks_source=None, backlinks_period=None,
                  exclude_parameter=[], exclude_path=[], resource_host=[])
    return argparse.Namespace(**{**values, **overrides})


def html(title, links='', canonical=ORIGIN + '/'):
    return f'<html lang="en"><head><title>{title}</title><meta name="description" content="Description"><meta name="viewport" content="width=device-width"><link rel="canonical" href="{canonical}"></head><body><h1>{title}</h1>{links}</body></html>'


class StoreTests(unittest.TestCase):
    def test_parameters_are_sorted_and_excluded_explicitly(self):
        self.assertEqual(url_key(ORIGIN + '/?b=2&a=1#x'), ORIGIN + '/?a=1&b=2')
        self.assertEqual(url_key(ORIGIN + '/?utm_source=x&a=1', ['utm_source']), ORIGIN + '/?a=1')
        self.assertNotEqual(url_key(ORIGIN + '/?tag=a&tag=b'), url_key(ORIGIN + '/?tag=b&tag=a'))
        from audit import normalize_url
        self.assertNotEqual(normalize_url(ORIGIN + '/about'), normalize_url(ORIGIN + '/about/'))
        self.assertNotEqual(normalize_url(ORIGIN + '/a%2Fb'), normalize_url(ORIGIN + '/a/b'))

    def test_resume_keeps_html_links_and_issues(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home', '<a href="/about/?a=1&b=2">About</a>')),
                     ORIGIN + '/about/?a=1&b=2': (200, html('', ''))}
            first = run_live(options(db), FixtureClient(pages, stop_after=3))
            self.assertFalse(first['crawl_complete'])
            second = run_live(options(db, resume=True), FixtureClient(pages))
            self.assertTrue(second['crawl_complete'])
            self.assertEqual(second['crawl_id'], first['crawl_id'])
            store = CrawlStore(db)
            try:
                self.assertEqual(store.count(second['crawl_id']), 2)
                self.assertEqual(store.pending(second['crawl_id']), 0)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM links').fetchone()[0], 1)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM resources WHERE kind IN ("robots","sitemap")').fetchone()[0], 2)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM issues WHERE rule_id="metadata.title_missing"').fetchone()[0], 1)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM issues WHERE rule_id="sitemap.target_unmeasured"').fetchone()[0], 0)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM issues WHERE rule_id="crawl.fetch_error"').fetchone()[0], 0)
                self.assertGreaterEqual(len(list(rows(store, 'issues', second['crawl_id'], {'severity': 'warning'}))), 1)
                row = store.db.execute('SELECT raw_html, metadata_json FROM pages WHERE url LIKE ?', ('%about%',)).fetchone()
                self.assertIn(b'<html', row['raw_html'])
                self.assertEqual(json.loads(row['metadata_json'])['title'], '')
            finally:
                store.close()

    def test_schema_one_database_migrates_to_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            store = CrawlStore(db)
            store.db.execute("UPDATE meta SET value='1' WHERE key='schema_version'")
            store.db.execute('DROP TABLE resources')
            store.db.commit()
            store.close()
            migrated = CrawlStore(db)
            self.assertEqual(migrated.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0], '3')
            self.assertIsNotNone(migrated.db.execute("SELECT name FROM sqlite_master WHERE name='resources'").fetchone())
            migrated.close()

    def test_path_exclusion_is_recorded_without_fetching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            fixture = FixtureClient({ORIGIN + '/': (200, html('Home')), ORIGIN + '/about/?a=1&b=2': (200, html('About'))})
            report = run_live(options(db, exclude_path=['^/about/']), fixture)
            store = CrawlStore(db)
            try:
                row = store.db.execute('SELECT state FROM queue WHERE crawl_id=? AND url LIKE ?', (report['crawl_id'], '%about%')).fetchone()
                self.assertEqual(row['state'], 'excluded')
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM pages WHERE url LIKE ?', ('%about%',)).fetchone()[0], 0)
                self.assertTrue(any('excluded' in warning for warning in report['warnings']))
            finally:
                store.close()

    def test_disk_budget_keeps_page_pending_for_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home') + 'x' * 1_500_000),
                     ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            with self.assertRaisesRegex(ValueError, 'no HTML pages'):
                run_live(options(db, max_disk_bytes=1_000_000), FixtureClient(pages))
            store = CrawlStore(db)
            self.assertEqual(store.pending(1), 2)
            store.close()
            resumed = run_live(options(db, resume=True, max_disk_bytes=10_000_000), FixtureClient(pages))
            self.assertTrue(resumed['crawl_complete'])

    def test_resume_rejects_changed_robots_policy(self):
        class ChangedRobots(FixtureClient):
            def fetch(self, url, **kwargs):
                if url.endswith('/robots.txt'):
                    self.requests += 1
                    return Response(url, 200, {'content-type': 'text/plain'},
                                    f'User-agent: *\nDisallow: /about/\nSitemap: {ORIGIN}/sitemap.xml'.encode(), [])
                return super().fetch(url, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home')), ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            run_live(options(db), FixtureClient(pages, stop_after=3))
            with self.assertRaisesRegex(ValueError, 'robots.txt changed'):
                run_live(options(db, resume=True), ChangedRobots(pages))

    def test_resume_retains_previous_http_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home', '<a href="/a-missing/">Missing</a><a href="/z-pending/">Pending</a>')),
                     ORIGIN + '/about/?a=1&b=2': (200, html('About')),
                     ORIGIN + '/z-pending/': (200, html('Pending'))}
            initial = run_live(options(db), FixtureClient(pages, stop_after=5))
            self.assertFalse(initial['crawl_complete'])
            resumed = run_live(options(db, resume=True), FixtureClient(pages))
            self.assertTrue(resumed['crawl_complete'])
            check = next(item for item in resumed['checks'] if item['id'] == 'technical.http')
            self.assertEqual(check['status'], 'fail')
            self.assertIn('/a-missing/=HTTP 404', check['findings'][0]['detail'])

    def test_query_exports_many_rows_without_materializing_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'many.json'
            output_items(({'url': f'https://example.org/{index}', 'status': 200} for index in range(2000)), 'json', path)
            self.assertEqual(len(json.loads(path.read_text(encoding='utf-8'))), 2000)

    def test_failed_export_preserves_previous_output(self):
        def failed_rows():
            yield {'url': ORIGIN}
            raise ValueError('fixture extraction failed')

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'existing.json'
            path.write_text('previous report', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fixture extraction failed'):
                output_items(failed_rows(), 'json', path)
            self.assertEqual(path.read_text(encoding='utf-8'), 'previous report')
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_csv_export_neutralizes_untrusted_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'anchors.csv'
            output_items([{'anchor': '=HYPERLINK("https://example.org")', 'count': -3}], 'csv', path)
            with path.open(newline='', encoding='utf-8') as stream:
                row = next(csv.DictReader(stream))
            self.assertTrue(row['anchor'].startswith("'="))
            self.assertEqual(row['count'], '-3')

    def test_comparison_csv_keeps_fields_after_added_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changes.csv'
            output_items({'changes': [{'url': ORIGIN + '/added', 'change': 'added'},
                                      {'url': ORIGIN, 'change': 'modified', 'fields': {'status': {'before': 404, 'after': 200}}}]}, 'csv', path)
            with path.open(newline='', encoding='utf-8') as stream:
                values = list(csv.DictReader(stream))
            self.assertEqual(json.loads(values[1]['fields'])['status']['after'], 200)

    def test_spelling_requires_supplied_language_and_reports_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            dictionary = Path(directory) / 'words.txt'
            dictionary.write_text('home\nabout\nuseful\ncontent\n', encoding='utf-8')
            pages = {ORIGIN + '/': (200, html('Home', '<p>Useful content mispeling mispeling</p><style>.cssnoise {color:red}</style>')),
                     ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            report = run_live(options(db), FixtureClient(pages))
            store = CrawlStore(db, read_only=True)
            try:
                candidates = list(spellcheck(store, report['crawl_id'], dictionary, 'en'))
                word = next(item for item in candidates if item['word'] == 'mispeling')
                self.assertEqual(word['count'], 2)
                self.assertEqual(word['state'], 'candidate')
                self.assertFalse(any(item['word'] == 'cssnoise' for item in candidates))
                self.assertTrue(all(item['state'] == 'unmeasured' for item in spellcheck(store, report['crawl_id'], dictionary, 'es')))
            finally:
                store.close()

    def test_read_only_queries_and_exclusive_crawl_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'crawl.sqlite')
            store = CrawlStore(path)
            store.close()
            reader = CrawlStore(path, read_only=True)
            with self.assertRaises(sqlite3.OperationalError):
                reader.db.execute("UPDATE meta SET value='99'")
            reader.close()
            with database_lock(path):
                with self.assertRaisesRegex(ValueError, 'another crawl process'):
                    run_live(options(path), FixtureClient({}))

    def test_cli_rejects_overwriting_input_database(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'crawl.sqlite'
            store = CrawlStore(str(path))
            store.close()
            previous = path.read_bytes()
            commands = [
                ['.agents/scripts/crawl_query.py', 'query', '--database', str(path), '--output', str(path)],
                ['.agents/scripts/live_audit.py', '--url', ORIGIN, '--database', str(path), '--output', str(path)],
            ]
            for command in commands:
                result = subprocess.run([sys.executable, *command], cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('must differ', result.stderr)
                self.assertEqual(path.read_bytes(), previous)

    def test_cli_guards_still_protect_repository_root_after_tooling_move(self):
        root = Path(__file__).resolve().parents[2]
        commands = [
            ['crawl_query.py', 'query', '--database', str(root / 'forbidden.sqlite')],
            ['live_audit.py', '--url', ORIGIN, '--database', str(root / 'forbidden.sqlite')],
            ['audit_schedule.py', '--job', str(root / 'forbidden.json'), '--once'],
        ]
        for script, *arguments in commands:
            result = subprocess.run([sys.executable, str(root / '.agents/scripts' / script), *arguments],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('outside', result.stderr)
        self.assertFalse((root / 'forbidden.sqlite').exists())

    def test_redirect_chain_is_recorded_with_final_response(self):
        class RedirectFixture(FixtureClient):
            def fetch(self, url, **kwargs):
                if url == ORIGIN + '/':
                    self.requests += 1
                    return Response(ORIGIN + '/final/', 200, {'content-type': 'text/html'},
                        html('Final', canonical=ORIGIN + '/final/').encode(),
                        [{'from': ORIGIN + '/', 'status': 301, 'to': ORIGIN + '/middle/'},
                         {'from': ORIGIN + '/middle/', 'status': 301, 'to': ORIGIN + '/final/'}])
                return super().fetch(url, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            report = run_live(options(db), RedirectFixture({ORIGIN + '/about/?a=1&b=2': (200, html('About'))}))
            store = CrawlStore(db)
            try:
                self.assertIsNotNone(store.db.execute('SELECT 1 FROM issues WHERE crawl_id=? AND rule_id="http.redirect_chain"', (report['crawl_id'],)).fetchone())
                row = store.db.execute('SELECT final_url,redirects_json FROM pages WHERE crawl_id=? AND url=?', (report['crawl_id'], ORIGIN + '/')).fetchone()
                self.assertEqual(row['final_url'], ORIGIN + '/final/')
                self.assertEqual(len(json.loads(row['redirects_json'])), 2)
            finally:
                store.close()

    def test_robots_disallow_prevents_fetch_and_records_exclusion(self):
        class RobotsFixture(FixtureClient):
            def fetch(self, url, **kwargs):
                if url.endswith('/robots.txt'):
                    self.requests += 1
                    data = f'User-agent: *\nDisallow: /about/\nSitemap: {ORIGIN}/sitemap.xml'.encode()
                    return Response(url, 200, {'content-type': 'text/plain'}, data, [])
                if '/about/' in url:
                    raise AssertionError('blocked URL fetched')
                return super().fetch(url, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            report = run_live(options(db), RobotsFixture({ORIGIN + '/': (200, html('Home'))}))
            store = CrawlStore(db)
            try:
                self.assertFalse(report['crawl_complete'])
                self.assertEqual(store.db.execute('SELECT state FROM queue WHERE url LIKE ?', ('%about%',)).fetchone()[0], 'excluded')
            finally:
                store.close()

    def test_compare_reports_changes_and_scope_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            old_db, new_db = str(Path(directory) / 'old.sqlite'), str(Path(directory) / 'new.sqlite')
            old = run_live(options(old_db), FixtureClient({ORIGIN + '/': (200, html('Old')), ORIGIN + '/about/?a=1&b=2': (404, '')}))
            new = run_live(options(new_db), FixtureClient({ORIGIN + '/': (200, html('New')), ORIGIN + '/about/?a=1&b=2': (200, html('About'))}))
            first, second = CrawlStore(old_db), CrawlStore(new_db)
            try:
                result = compare(first, old['crawl_id'], second, new['crawl_id'])
                self.assertTrue(result['scope_comparable'])
                self.assertEqual(len(result['changes']), 2)
                self.assertTrue(any('status' in item.get('fields', {}) for item in result['changes']))
            finally:
                first.close()
                second.close()

    def test_comparison_declares_configuration_scope_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            store = CrawlStore(db)
            first, _ = store.start(ORIGIN, ORIGIN + '/', '100', {'exclude_path': []})
            store.finish(first, True, [])
            second, _ = store.start(ORIGIN, ORIGIN + '/', '100', {'exclude_path': ['/private']})
            store.finish(second, True, [])
            result = compare(store, first, store, second)
            self.assertFalse(result['scope_comparable'])
            self.assertIn('crawl_configuration', result['scope_differences'])
            store.close()

    def test_exports_and_explicit_parameter_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home', '<a href="/about/?a=1&b=2&utm_source=mail">About</a>')),
                     ORIGIN + '/about/?a=1&b=2': (200, html('About', canonical=ORIGIN + '/about/?a=1&b=2'))}
            report = run_live(options(db, exclude_parameter=['utm_source']), FixtureClient(pages))
            store = CrawlStore(db)
            try:
                urls = [row['url'] for row in store.db.execute('SELECT url FROM pages ORDER BY url')]
                self.assertIn(ORIGIN + '/about/?a=1&b=2', urls)
                self.assertNotIn('utm_source', json.dumps(urls))
                self.assertEqual(len(list(export_graph(store, report['crawl_id']))), 1)
                self.assertIn(ORIGIN + '/about/?a=1&amp;b=2', export_sitemap(store, report['crawl_id']))
                self.assertEqual(next(extract(store, report['crawl_id'], 'title'))['value'], 'Home')
                export_path = Path(directory) / 'pages.csv'
                output_items(rows(store, 'pages', report['crawl_id'], {}), 'csv', export_path)
                self.assertIn('crawl_id', export_path.read_text(encoding='utf-8'))
            finally:
                store.close()

    def test_rules_record_objective_page_and_cross_page_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            shared = '<html lang="en"><head><title>Same</title><link rel="alternate" hreflang="en" href="/about/?a=1&b=2"></head><body><img src="/image.png"><a href="/about/?a=1&b=2"></a></body></html>'
            pages = {ORIGIN + '/': (200, shared), ORIGIN + '/about/?a=1&b=2': (200, shared)}
            report = run_live(options(db), FixtureClient(pages))
            store = CrawlStore(db)
            try:
                rule_ids = {row[0] for row in store.db.execute('SELECT rule_id FROM issues WHERE crawl_id=?', (report['crawl_id'],))}
                self.assertIn('metadata.duplicate_title', rule_ids)
                self.assertIn('content.exact_duplicate', rule_ids)
                self.assertIn('images.alt_missing', rule_ids)
                self.assertIn('links.anchor_missing', rule_ids)
                self.assertIn('hreflang.return_link_missing', rule_ids)
            finally:
                store.close()

    def test_crawl_limit_counts_responses_and_unlimited_has_no_url_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            links = ''.join(f'<a href="/page-{index}/">Page {index}</a>' for index in range(105))
            pages = {ORIGIN + '/': (200, html('Home', links))}
            pages.update({ORIGIN + f'/page-{index}/': (200, html(f'Page {index}')) for index in range(105)})
            old_db = str(Path(directory) / 'bounded.sqlite')
            limited = run_live(options(old_db, max_disk_bytes=10_000_000), FixtureClient(pages))
            self.assertFalse(limited['crawl_complete'])
            store = CrawlStore(old_db)
            self.assertEqual(store.count(limited['crawl_id']), 100)
            store.close()
            new_db = str(Path(directory) / 'unlimited.sqlite')
            complete = run_live(options(new_db, crawl_limit='unlimited', max_disk_bytes=10_000_000), FixtureClient(pages))
            self.assertTrue(complete['crawl_complete'])
            store = CrawlStore(new_db)
            self.assertEqual(store.count(complete['crawl_id']), 107)
            store.close()

    def test_non_html_success_is_not_an_http_failure_and_broken_links_keep_source(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            page_html = html('Home', '<a href="/missing/">Missing</a><a href="/document.pdf">PDF</a>')
            pages = {ORIGIN + '/': (200, page_html), ORIGIN + '/document.pdf': (200, '%PDF-1.4'),
                     ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            report = run_live(options(db), FixtureClient(pages))
            store = CrawlStore(db)
            try:
                broken = store.db.execute('SELECT url,evidence_json FROM issues WHERE rule_id="links.broken_internal"').fetchone()
                self.assertEqual(broken['url'], ORIGIN + '/')
                self.assertIn('/missing/', broken['evidence_json'])
                resource = store.db.execute('SELECT status,kind FROM resources WHERE url=?', (ORIGIN + '/document.pdf',)).fetchone()
                self.assertEqual((resource['status'], resource['kind']), (200, 'non_html'))
                http_check = next(item for item in report['checks'] if item['id'] == 'technical.http')
                self.assertEqual(http_check['status'], 'fail')
                self.assertNotIn('document.pdf=HTTP 200', http_check['findings'][0]['detail'])
            finally:
                store.close()

    def test_near_duplicate_is_only_a_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            text = ' '.join(['Content about a reusable topic for comparison.'] * 30)
            pages = {ORIGIN + '/': (200, html('First', '<main>' + text + '</main>')),
                     ORIGIN + '/about/?a=1&b=2': (200, html('Second', '<main>' + text + '</main>'))}
            report = run_live(options(db), FixtureClient(pages))
            store = CrawlStore(db)
            try:
                candidates = list(store.db.execute('SELECT severity,evidence_json FROM issues WHERE crawl_id=? AND rule_id="content.near_duplicate_candidate"', (report['crawl_id'],)))
                self.assertEqual(len(candidates), 2)
                self.assertTrue(all(item['severity'] == 'info' and 'review required' in item['evidence_json'] for item in candidates))
            finally:
                store.close()

    def test_amp_and_form_labels_have_url_level_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / 'crawl.sqlite')
            root = '<html lang="en"><head><title>Home</title><link rel="amphtml" href="/about/?a=1&b=2"></head><body><h1>Home</h1><input id="email"><label for="name">Name</label></body></html>'
            pages = {ORIGIN + '/': (200, root), ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            report = run_live(options(db), FixtureClient(pages))
            store = CrawlStore(db)
            try:
                issues = {(row['url'], row['rule_id']) for row in store.db.execute('SELECT url,rule_id FROM issues WHERE crawl_id=?', (report['crawl_id'],))}
                self.assertIn((ORIGIN + '/', 'accessibility.form_control_label_missing'), issues)
                self.assertIn((ORIGIN + '/about/?a=1&b=2', 'amp.markup_missing'), issues)
            finally:
                store.close()


if __name__ == '__main__':
    unittest.main()
