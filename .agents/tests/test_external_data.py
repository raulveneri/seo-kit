"""Read-only API adapter tests with fixed HTTP fixtures."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from crawl_store import CrawlStore
from external_data import enrich
from live_http import Response


ORIGIN = 'https://example.org'


class ApiFixture:
    def __init__(self):
        self.calls = []

    def fetch(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if 'analyticsdata' in url:
            data = {'rows': [{'dimensionValues': [{'value': ORIGIN + '/'}], 'metricValues': [{'value': '10'}, {'value': '5'}]}], 'rowCount': 1}
        elif 'searchAnalytics' in url:
            data = {'rows': [{'keys': [ORIGIN + '/'], 'clicks': 3, 'impressions': 40, 'ctr': 0.075, 'position': 8.5}]}
        elif 'pagespeedonline' in url:
            data = {'analysisUTCTimestamp': '2026-10-19T12:00:00Z', 'lighthouseResult': {'lighthouseVersion': '12', 'categories': {'performance': {'score': 0.9}}, 'audits': {'largest-contentful-paint': {'numericValue': 2300}}}}
        elif 'api.moz' in url:
            data = {'result': {'links': [{'anchor_text': 'Example'}]}}
        else:
            raise AssertionError(url)
        return Response(url, 200, {'content-type': 'application/json'}, json.dumps(data).encode(), [])


class ExternalDataTests(unittest.TestCase):
    def test_empty_pagespeed_response_remains_unmeasured(self):
        class EmptyApi:
            def fetch(self, url, **kwargs):
                return Response(url, 200, {}, b'{}', [])

        with tempfile.TemporaryDirectory() as directory:
            store = CrawlStore(str(Path(directory) / 'crawl.sqlite'))
            selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
            with patch.dict(os.environ, {'SEO_KIT_PSI_API_KEY': 'test'}, clear=True):
                result = enrich(store, selected, ORIGIN, [ORIGIN + '/'], EmptyApi(), psi_limit=1)
            self.assertEqual(result['sources']['pagespeed_lab']['status'], 'unmeasured')
            self.assertEqual(store.db.execute('SELECT COUNT(*) FROM external_data').fetchone()[0], 0)
            store.close()

    def test_absent_credentials_leave_sources_unmeasured_without_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CrawlStore(str(Path(directory) / 'crawl.sqlite'))
            selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
            fixture = ApiFixture()
            with patch.dict(os.environ, {}, clear=True):
                result = enrich(store, selected, ORIGIN, [ORIGIN + '/'], fixture, ga4_property='123', gsc_property=ORIGIN + '/', period=('2026-09-01', '2026-09-28'), psi_limit=1, moz_limit=1)
            self.assertEqual(result['sources'], {})
            self.assertEqual(len(result['warnings']), 4)
            self.assertEqual(fixture.calls, [])
            store.close()

    def test_sources_record_property_period_and_lab_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CrawlStore(str(Path(directory) / 'crawl.sqlite'))
            selected, _ = store.start(ORIGIN, ORIGIN + '/', '100', {})
            fixture = ApiFixture()
            environment = {'SEO_KIT_GA4_ACCESS_TOKEN': 'test', 'SEO_KIT_GSC_ACCESS_TOKEN': 'test', 'SEO_KIT_PSI_API_KEY': 'test', 'SEO_KIT_MOZ_TOKEN': 'test'}
            with patch.dict(os.environ, environment, clear=True):
                result = enrich(store, selected, ORIGIN, [ORIGIN + '/'], fixture, ga4_property='123', gsc_property=ORIGIN + '/', period=('2026-09-01', '2026-09-28'), psi_limit=1, moz_limit=1)
            self.assertEqual(len(result['sources']), 4)
            rows = list(store.db.execute('SELECT source,property,period,data_json FROM external_data ORDER BY source'))
            self.assertEqual(len(rows), 6)
            self.assertEqual(json.loads(next(row['data_json'] for row in rows if row['source'] == 'pagespeed_lab'))['kind'], 'lab')
            self.assertEqual(next(row['property'] for row in rows if row['source'] == 'ga4'), '123')
            self.assertTrue(all('test' not in row['data_json'] for row in rows))
            calls = len(fixture.calls)
            with patch.dict(os.environ, environment, clear=True):
                enrich(store, selected, ORIGIN, [ORIGIN + '/'], fixture, ga4_property='123', gsc_property=ORIGIN + '/', period=('2026-09-01', '2026-09-28'), psi_limit=1, moz_limit=1)
            self.assertEqual(len(fixture.calls), calls)
            store.close()


if __name__ == '__main__':
    unittest.main()
