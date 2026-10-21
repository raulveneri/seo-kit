"""Real Chromium integration: no mocked browser and no remote requests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from live_audit import get_browser, render_page, run_live
from live_http import Response
from robots_policy import RobotsPolicy
from crawl_store import CrawlStore
from test_crawl_store import options, ORIGIN


@unittest.skipUnless(os.environ.get('SEO_KIT_TEST_BROWSER') == '1', 'opt-in real Chromium suite. Run npm run test:browser')
class ChromiumTests(unittest.TestCase):
    def setUp(self):
        self.pair = None
        if self._testMethodName != 'test_full_live_pipeline_persists_raw_dom_and_axe_findings':
            self.pair, note = get_browser('always')

    def tearDown(self):
        if self.pair:
            self.pair[1].close(); self.pair[0].stop()

    def test_kernel_blocks_unrouted_requests_and_retains_javascript(self):
        page = self.pair[1].new_page()
        try:
            for target in ('http://127.0.0.1:8765/private','https://example.org/'):
                with self.assertRaises(Exception):
                    page.goto(target,timeout=3000)
            page.set_content('<title>Works</title><script>document.title="JavaScript works"</script>')
            self.assertEqual(page.title(),'JavaScript works')
        finally: page.close()

    def test_rendered_dom_resources_errors_and_axe_evidence(self):
        class Fixture:
            max_bytes = 2000000
            def __init__(self): self.calls=[]
            def fetch(self,url,**kwargs):
                self.calls.append(url)
                if url.endswith('/robots.txt'):
                    return Response(url,200,{},b'User-agent: *\nAllow: /',[])
                if url.endswith('/app.js'):
                    body = b'document.title="Rendered title"; document.querySelector("main").textContent="Rendered content"; fetch("https://127.0.0.1/private").catch(()=>{});fetch("/write",{method:"POST",body:"x"}).catch(()=>{});throw new Error("fixture script error");'
                    return Response(url,200,{'content-type':'application/javascript'},body,[])
                if url == ORIGIN+'/':
                    body = b'<!doctype html><html lang="en"><head><title>Raw title</title></head><body><main>Raw content</main><button></button><script src="/app.js"></script><script src="https://outside.example/blocked.js"></script></body></html>'
                    return Response(url,200,{'content-type':'text/html'},body,[])
                raise AssertionError(url)
        client=Fixture(); observations={}; warnings=[]
        html=render_page(ORIGIN+'/',client,ORIGIN,RobotsPolicy('User-agent: *\nAllow: /'),self.pair[1],warnings,
                         observation=lambda kind,status,data: observations.update({kind:{'status':status,'data':data}}))
        self.assertIn('<title>Rendered title</title>',html)
        self.assertIn('Rendered content',html)
        self.assertNotIn('https://127.0.0.1/private',client.calls)
        self.assertNotIn(ORIGIN+'/write',client.calls)
        self.assertTrue(observations['render_runtime']['data']['script_errors'])
        self.assertGreaterEqual(len(observations['render_runtime']['data']['blocked_resources']),3)
        self.assertIn('button-name',{v['id'] for v in observations['axe_accessibility']['data']['violations']})

    def test_full_live_pipeline_persists_raw_dom_and_axe_findings(self):
        class Fixture:
            max_bytes=2000000
            def __init__(self): self.requests=0
            def fetch(self,url,**kwargs):
                self.requests+=1
                if url.endswith('/robots.txt'): return Response(url,200,{},b'User-agent: *\nAllow: /',[])
                if url.endswith('/sitemap.xml'): return Response(url,404,{},b'',[])
                return Response(url,200,{'content-type':'text/html'},b'<!doctype html><html lang="en"><head><title>Raw</title><meta name="description" content="Fixture"><meta name="viewport" content="width=device-width"><link rel="canonical" href="https://example.org/"></head><body><main><h1>Before</h1><button></button></main><script>document.title="Rendered";document.querySelector("h1").textContent="After"</script></body></html>',[])
        with tempfile.TemporaryDirectory() as directory:
            database=str(Path(directory)/'crawl.sqlite')
            report=run_live(options(database,render='always'),Fixture())
            store=CrawlStore(database)
            try:
                page=store.db.execute('SELECT raw_html,rendered_html FROM pages').fetchone()
                self.assertIn(b'<title>Raw</title>',page[0]);self.assertIn(b'<title>Rendered</title>',page[1])
                rules={row[0] for row in store.db.execute('SELECT rule_id FROM issues')}
                self.assertIn('render.dom_difference',rules)
                self.assertIn('accessibility.axe.button-name',rules)
                self.assertTrue(report['crawl_complete'])
            finally: store.close()


if __name__=='__main__': unittest.main()
