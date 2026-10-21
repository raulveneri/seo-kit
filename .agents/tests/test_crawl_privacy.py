import json
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from crawl_privacy import sanitize, redact_text, sensitive_url, sharing_rows
from crawl_store import CrawlStore
from crawl_query import extract, compare
from live_http import Response
from live_audit import run_live, main as live_main
from audit_schedule import load_job, run_job
from test_crawl_store import options, FixtureClient, html, ORIGIN


class CrawlPrivacyTests(unittest.TestCase):
    def test_filter_preserves_seo_parameters_and_redacts_credentials(self):
        secret = 'fixtureCredentialValue'
        data = {'Set-Cookie': 'sid=' + secret, 'authorization': 'Bearer ' + secret,
                'nested': {'access_token': secret},
                'url': ORIGIN + '/?category=books&access_token=' + secret,
                'message': 'request failed: token=' + secret}
        filtered = sanitize(data)
        self.assertNotIn(secret, json.dumps(filtered))
        self.assertIn('category=books', filtered['url'])
        self.assertTrue(sensitive_url(data['url']))
        self.assertFalse(sensitive_url(ORIGIN + '/?category=books'))
        self.assertNotIn(secret, redact_text(ORIGIN + '/?page=1&amp;token=' + secret))
        self.assertNotIn(secret, redact_text('<input name="csrf-token" value="' + secret + '"><input type="password" value=' + secret + '><meta name="api-key" content="' + secret + '">'))

    def test_all_persistence_surfaces_filter_secrets_and_exclude_private_queue_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'crawl.sqlite'
            store = CrawlStore(path, store_html='both')
            try:
                selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
                secret = 'fixturePersistenceSecret'
                url = ORIGIN + '/?token=' + secret
                body = '<html><script>const token="' + secret + '"</script><p>owner@example.test</p></html>'
                response = Response(ORIGIN + '/', 200, {'content-type': 'text/html', 'Set-Cookie': secret}, body.encode(), [{'to': url}])
                store.save_page(selected, ORIGIN + '/', 0, response, body, body, {'password': secret})
                store.resource(selected, url, 'script', response)
                store.add_references(selected, [(ORIGIN + '/', url, 'token=' + secret, 'internal')], [(url, 1, 'link')])
                store.observation(selected, url, 'test', 'measured', {'token': secret})
                store.issue(selected, url, 'test.rule', 'warning', {'url': url})
                store.external(selected, url, 'fixture', 'property', 'period', {'access_token': secret})
                store.finish(selected, False, ['token=' + secret])
                self.assertNotIn(secret, '\n'.join(store.db.iterdump()))
                self.assertIn('owner@example.test', store.db.execute('SELECT raw_html FROM pages').fetchone()[0].decode())
                self.assertEqual(store.db.execute('SELECT state FROM queue').fetchone()[0], 'excluded')
                if os.name != 'nt':
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            finally:
                store.close()

    def test_html_storage_modes_keep_fingerprints_for_comparisons(self):
        for mode in ('none', 'raw', 'rendered', 'both'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                store = CrawlStore(Path(directory) / 'crawl.sqlite', store_html=mode)
                try:
                    selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
                    store.save_page(selected, ORIGIN + '/', 0, raw='<html>Raw</html>', rendered='<html>DOM</html>')
                    row = store.db.execute('SELECT * FROM pages').fetchone()
                    self.assertEqual(row['raw_html'] is not None, mode in ('raw', 'both'))
                    self.assertEqual(row['rendered_html'] is not None, mode in ('rendered', 'both'))
                    self.assertTrue(row['raw_sha256'])
                    self.assertTrue(row['rendered_sha256'])
                    self.assertEqual(compare(store, selected, store, selected)['changes'], [])
                    if mode == 'none':
                        with self.assertRaisesRegex(ValueError, 'HTML was not retained'):
                            list(extract(store, selected, 'h1'))
                finally:
                    store.close()

    def test_metadata_only_crawl_resumes_by_refetching_html_without_retaining_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'crawl.sqlite')
            pages = {ORIGIN + '/': (200, html('Home')), ORIGIN + '/about/?a=1&b=2': (200, html('About'))}
            first = run_live(options(database, store_html='none'), FixtureClient(pages, stop_after=3))
            self.assertFalse(first['crawl_complete'])
            second = run_live(options(database, store_html='none', resume=True), FixtureClient(pages))
            self.assertEqual(first['crawl_id'], second['crawl_id'])
            self.assertTrue(second['crawl_complete'])
            store = CrawlStore(database)
            try:
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM pages WHERE raw_html IS NOT NULL OR rendered_html IS NOT NULL').fetchone()[0], 0)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM pages WHERE raw_sha256 IS NOT NULL').fetchone()[0], 2)
                self.assertEqual(second['pages'], 2)
                full = run_live(options(str(Path(directory) / 'full.sqlite'), store_html='both'), FixtureClient(pages))
                self.assertEqual(second['score'], full['score'])
                self.assertEqual(second['coverage'], full['coverage'])
                self.assertEqual({item['id']: item['status'] for item in second['checks']}, {item['id']: item['status'] for item in full['checks']})
            finally:
                store.close()

    def test_sharing_export_omits_query_values_html_evidence_and_provider_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'crawl.sqlite')
            store = CrawlStore(database)
            try:
                selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
                url = ORIGIN + '/?customer=123456'
                response = Response(url, 200, {'content-type': 'text/html'}, b'<html>Private body</html>', [])
                store.save_page(selected, url, 0, response, '<html>Private body</html>', metadata={'title': 'Private title'})
                store.issue(selected, url, 'metadata.test', 'warning', {'text': 'Private evidence'})
                store.external(selected, url, 'fixture', 'property', 'period', {'payload': 'Private provider data'})
                exported = json.dumps(list(sharing_rows(store, selected)))
                for value in ('123456', 'Private body', 'Private title', 'Private evidence', 'Private provider data', 'headers_json'):
                    self.assertNotIn(value, exported)
                self.assertIn('metadata.test', exported)
                self.assertIn('customer=123456', store.db.execute('SELECT url FROM pages').fetchone()[0])
            finally:
                store.close()

    def test_retention_preview_protection_and_apply_preserve_unfinished_and_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CrawlStore(Path(directory) / 'crawl.sqlite')
            try:
                ids = [store.start(ORIGIN, ORIGIN + '/', '100', {})[0] for _ in range(4)]
                for selected in ids:
                    store.enqueue(selected, ORIGIN + '/', 0, 'start')
                    store.save_page(selected, ORIGIN + '/', 0, raw='old body')
                    store.finish(selected, True, [])
                store.db.execute("UPDATE crawls SET finished_at='2020-01-01T00:00:00+00:00'")
                store.db.execute("UPDATE crawls SET status='interrupted' WHERE id=?", (ids[2],))
                store.db.execute("UPDATE crawls SET finished_at='2026-10-20T00:00:00+00:00' WHERE id=?", (ids[3],))
                store.protect(ids[1], True)
                store.reserve_quota('moz', '2026-10', 1, 50)
                reference = datetime(2026, 10, 20, tzinfo=timezone.utc)
                preview = store.retention(30, reference=reference)
                self.assertEqual(preview['crawl_ids'], [ids[0]])
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM crawls').fetchone()[0], 4)
                result = store.retention(30, apply=True, reference=reference)
                self.assertTrue(result['applied'])
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM crawls').fetchone()[0], 3)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM pages WHERE crawl_id=?', (ids[0],)).fetchone()[0], 0)
                self.assertEqual(store.db.execute('SELECT consumed FROM api_usage').fetchone()[0], 1)
            finally:
                store.close()

    def test_management_cli_defaults_to_preview_and_supports_share_and_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'crawl.sqlite')
            store = CrawlStore(database)
            selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
            store.save_page(selected, ORIGIN + '/', 0, raw='<html>Fixture</html>')
            store.finish(selected, True, [])
            store.close()
            for args in (['lock', '--crawl-id', str(selected)], ['crawls'], ['share', '--crawl-id', str(selected)], ['retention', '--days', '30'], ['unlock', '--crawl-id', str(selected)]):
                result = subprocess.run([sys.executable, str(SCRIPTS / 'crawl_query.py'), *args, '--database', database], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsInstance(json.loads(result.stdout), list)

    def test_cli_defaults_and_scheduled_privacy_options(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'crawl.sqlite')
            with patch('live_audit.run_live', return_value={'ok': True}) as run, patch('sys.stdout', new_callable=io.StringIO):
                live_main(['--url', ORIGIN + '/', '--database', database, '--format', 'json'])
            self.assertEqual(run.call_args.args[0].store_html, 'none')
            self.assertIsNone(run.call_args.args[0].retention_days)
            job_file = Path(directory) / 'job.json'
            job_file.write_text(json.dumps({'url': ORIGIN + '/', 'database': database, 'output_directory': directory, 'store_html': 'both', 'retention_days': 30}))
            job = load_job(job_file)
            with patch('audit_schedule.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')) as process:
                run_job(job)
            command = process.call_args.args[0]
            self.assertIn('--store-html', command)
            self.assertIn('--retention-days', command)

    def test_sensitive_start_url_rejected_before_network_and_missing_management_db_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'absent.sqlite'
            client = FixtureClient({})
            with self.assertRaisesRegex(ValueError, 'sensitive parameters'):
                run_live(options(str(path), url=ORIGIN + '/?token=fixture'), client)
            self.assertEqual(client.requests, 0)
            result = subprocess.run([sys.executable, str(SCRIPTS / 'crawl_query.py'), 'retention', '--database', str(path), '--days', '30', '--apply'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
