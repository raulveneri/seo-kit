"""Behavioral tests for bounded live auditing without external network calls."""

import argparse
import http.client
import time
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit import validate_json_ld
from live_audit import backlink_summary, crux_evidence, gsc_evidence, run_live, render_page, get_browser, network_isolation
from live_http import Response, SafeClient, checked_url, public_address
from urllib.robotparser import RobotFileParser


ORIGIN = "https://example.org"


class FakeClient:
    max_bytes = 2_000_000

    def __init__(self, pages=None):
        self.pages = pages or {}
        self.requests = 0

    def fetch(self, url, *, method="GET", body=None, headers=None, allow_redirects=True, authorize=None):
        self.requests += 1
        if url.endswith("/robots.txt"):
            data = f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n".encode()
            return Response(url, 200, {"content-type": "text/plain"}, data, [])
        if url.endswith("/sitemap.xml"):
            data = f'<urlset><url><loc>{ORIGIN}/</loc></url><url><loc>{ORIGIN}/about/</loc></url></urlset>'.encode()
            return Response(url, 200, {"content-type": "application/xml"}, data, [])
        if url in self.pages:
            status, body = self.pages[url]
            return Response(url, status, {"content-type": "text/html"}, body.encode(), [])
        return Response(url, 404, {"content-type": "text/html"}, b"", [])


def page(title, path, links="", schema=""):
    return f'<!doctype html><html lang="en"><head><title>{title}</title><meta name="description" content="A useful test page."><meta name="viewport" content="width=device-width"><link rel="canonical" href="{ORIGIN}{path}">{schema}</head><body><h1>{title}</h1>{links}</body></html>'


def args(**values):
    defaults = dict(url=ORIGIN + "/", max_pages=10, max_requests=100, max_inspections=10, delay=0, render="never", crux=False, gsc_property=None, evidence=None, baseline=None, backlinks_export=None, backlinks_source=None, backlinks_period=None)
    return argparse.Namespace(**{**defaults, **values})


class LiveAuditTests(unittest.TestCase):
    def test_rendering_fails_closed_without_network_isolation(self):
        with patch('live_audit.network_isolation', side_effect=ValueError('isolation unavailable')):
            browser, note = get_browser('auto')
            self.assertIsNone(browser)
            self.assertIn('isolation unavailable', note)
            with self.assertRaisesRegex(ValueError, 'isolation unavailable'):
                get_browser('always')
        with patch('live_audit.shutil.which', return_value='/usr/bin/unshare'), patch('live_audit.sys.platform', 'linux'), patch('live_audit.subprocess.run') as probe, patch('live_audit.os.readlink', return_value='net:[same]'):
            probe.return_value.returncode = 0
            probe.return_value.stdout = 'net:[same]\n'
            with self.assertRaisesRegex(ValueError, 'isolation unavailable'):
                network_isolation()

    def test_public_https_only_and_private_dns_rejected(self):
        with self.assertRaises(ValueError):
            checked_url("http://example.org/")
        with patch("live_http.socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
            with self.assertRaises(ValueError):
                public_address("example.org")

    def test_redirect_cannot_leave_origin(self):
        class RedirectResponse:
            status = 302

            def getheaders(self):
                return [("Location", "https://127.0.0.1/private")]

            def read(self, limit):
                return b""

        class Connection:
            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return RedirectResponse()

            def close(self):
                pass

        with patch("live_http.public_address", return_value="93.184.215.14"), patch("live_http.PinnedHTTPSConnection", return_value=Connection()):
            with self.assertRaisesRegex(ValueError, "redirect left"):
                SafeClient(delay=0).fetch(ORIGIN + "/")

    def test_failed_http_attempt_consumes_request_budget(self):
        class BadConnection:
            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                raise http.client.BadStatusLine('invalid fixture')

            def close(self):
                pass

        with patch('live_http.public_address', return_value='93.184.215.14'), patch('live_http.PinnedHTTPSConnection', return_value=BadConnection()):
            client = SafeClient(max_requests=1, delay=0)
            with self.assertRaisesRegex(ValueError, 'invalid HTTP response'):
                client.fetch(ORIGIN)
            self.assertEqual(client.requests, 1)
            with self.assertRaisesRegex(ValueError, 'budget exhausted'):
                client.fetch(ORIGIN)

    def test_robots_policy_is_checked_before_redirect_fetch(self):
        class RedirectResponse:
            status = 302

            def getheaders(self):
                return [('Location', ORIGIN + '/blocked/')]

            def read(self, limit):
                return b''

        class Connection:
            calls = 0

            def request(self, *args, **kwargs):
                self.calls += 1

            def getresponse(self):
                return RedirectResponse()

            def close(self):
                pass

        connection = Connection()
        with patch('live_http.public_address', return_value='93.184.215.14'), patch('live_http.PinnedHTTPSConnection', return_value=connection):
            with self.assertRaisesRegex(ValueError, 'disallowed by crawl policy'):
                SafeClient(delay=0).fetch(ORIGIN, authorize=lambda url: '/blocked/' not in url)
        self.assertEqual(connection.calls, 1)

    def test_declared_delay_cannot_exceed_remaining_time_budget(self):
        client = SafeClient(delay=100, deadline=time.monotonic() + 1)
        client.last_request = time.monotonic()
        with patch('live_http.public_address', return_value='93.184.215.14'), patch('live_http.time.sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'time budget exhausted'):
                client.fetch(ORIGIN)
        sleep.assert_not_called()

    def test_crawls_pages_and_reports_failed_live_http(self):
        pages = {
            ORIGIN + "/": (200, page("Home", "/", '<a href="/about/">About</a><a href="/missing/">Missing page</a>')),
            ORIGIN + "/about/": (200, page("About", "/about/")),
        }
        report = run_live(args(), FakeClient(pages))
        self.assertEqual(report["pages"], 2)
        self.assertEqual(report["scope"], "sampled_live_html")
        self.assertTrue(report["crawl_complete"])
        self.assertEqual(next(item for item in report["checks"] if item["id"] == "technical.http")["status"], "fail")
        self.assertEqual(next(item for item in report["checks"] if item["id"] == "technical.internal_links")["status"], "fail")

    def test_rendered_markup_enters_audit(self):
        raw = '<!doctype html><html><head></head><body><div id="root"></div></body></html>'
        rendered = page("Rendered", "/", schema='<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Rendered"}</script>')
        pages = {ORIGIN + "/": (200, raw), ORIGIN + "/about/": (200, page("About", "/about/"))}
        class Closable:
            def close(self):
                pass

            def stop(self):
                pass

        with patch("live_audit.get_browser", return_value=((Closable(), Closable()), None)), patch("live_audit.render_page", return_value=rendered) as render:
            report = run_live(args(render="auto"), FakeClient(pages))
        render.assert_called_once()
        self.assertEqual(next(item for item in report["checks"] if item["id"] == "technical.structured_data")["status"], "pass")
        self.assertEqual(next(item for item in report["checks"] if item["id"] == "onpage.title")["status"], "pass")

    def test_browser_context_blocks_unapproved_network_channels(self):
        class Route:
            request = type('Request', (), {'url': 'https://outside.example/script.js', 'resource_type': 'script', 'method': 'GET'})()
            aborted = False

            def abort(self):
                self.aborted = True

        class WebSocket:
            closed = False

            def close(self):
                self.closed = True

        class Page:
            def __init__(self, context):
                self.context = context

            def goto(self, *args, **kwargs):
                self.context.route_handler(self.context.route_obj)

            def wait_for_timeout(self, *args):
                pass

            def content(self):
                return '<html></html>'

        class Context:
            def __init__(self):
                self.route_obj = Route()
                self.socket = WebSocket()

            def route_web_socket(self, pattern, handler):
                handler(self.socket)

            def route(self, pattern, handler):
                self.route_handler = handler

            def add_init_script(self, script):
                self.script = script

            def new_page(self):
                return Page(self)

            def close(self):
                pass

        class Browser:
            def __init__(self):
                self.context = Context()

            def new_context(self, **kwargs):
                return self.context

        browser = Browser()
        robots = RobotFileParser()
        robots.parse(['User-agent: *', 'Allow: /'])
        client = FakeClient()
        render_page(ORIGIN + '/', client, ORIGIN, robots, browser)
        self.assertTrue(browser.context.route_obj.aborted)
        self.assertTrue(browser.context.socket.closed)
        self.assertIn('RTCPeerConnection', browser.context.script)
        self.assertEqual(client.requests, 0)

    def test_json_ld_structure_is_checked(self):
        self.assertFalse(validate_json_ld('{"@context":"https://schema.org"}')[0])
        self.assertFalse(validate_json_ld('{"@context":"https://schema.org","@type":"Thing"}')[0])
        self.assertTrue(validate_json_ld('{"@context":"https://schema.org","@graph":[{"@type":"WebPage","name":"A"}]}')[0])

    def test_crux_and_search_console_connectors(self):
        class ApiClient:
            def fetch(self, url, **kwargs):
                if "chromeuxreport" in url:
                    data = {"record": {"metrics": {"largest_contentful_paint": {"percentiles": {"p75": 2300}}, "interaction_to_next_paint": {"percentiles": {"p75": 170}}, "cumulative_layout_shift": {"percentiles": {"p75": "0.08"}}}, "collectionPeriod": {"firstDate": {"year": 2026, "month": 9, "day": 1}, "lastDate": {"year": 2026, "month": 9, "day": 28}}}}
                else:
                    data = {"inspectionResult": {"indexStatusResult": {"verdict": "PASS", "pageFetchState": "SUCCESSFUL", "googleCanonical": ORIGIN + "/", "userCanonical": ORIGIN + "/"}}}
                import json
                return Response(url, 200, {"content-type": "application/json"}, json.dumps(data).encode(), [])

        checks, note = crux_evidence(ApiClient(), ORIGIN, "test-key")
        self.assertIsNone(note)
        self.assertEqual(checks["performance.lcp"]["value"], 2300)
        self.assertEqual(checks["performance.cls"]["period"], "2026-09-01 to 2026-09-28")
        checks, findings, note = gsc_evidence(ApiClient(), ORIGIN, [ORIGIN + "/"], ORIGIN + "/", "test-token", 10)
        self.assertIsNone(note)
        self.assertEqual(checks["technical.indexing"]["status"], "pass")
        self.assertEqual(len(findings), 1)
        class NoRequests:
            def fetch(self, *args, **kwargs):
                raise AssertionError('cached inspection must not consume quota')

        cached_checks, cached_findings, note = gsc_evidence(NoRequests(), ORIGIN, [ORIGIN + '/'], ORIGIN + '/', None, 10, findings)
        self.assertIsNone(note)
        self.assertEqual(cached_checks['technical.indexing']['status'], 'pass')
        self.assertEqual(cached_findings, findings)

    def test_backlink_export_summarizes_without_assigning_quality(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "links.csv"
            file.write_text("source_url,target_url,anchor_text\nhttps://referrer.example/a,https://example.org/,Example\nhttps://referrer.example/b,https://example.org/about/,Example\n", encoding="utf-8")
            summary = backlink_summary(file, ORIGIN, "reviewed provider export", "2026-09-01 to 2026-09-28")
            self.assertEqual(summary["links_in_export"], 2)
            self.assertEqual(summary["referring_domains_in_export"], 1)
            self.assertNotIn("status", summary)


if __name__ == "__main__":
    unittest.main()
